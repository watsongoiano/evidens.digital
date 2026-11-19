"""Conferência do pedido pelo check-up (/operadoras): por enquanto, só o administrador vê e envia."""
import io
import json
from pathlib import Path

from tests.test_operadora import FORMATO_C, _pdf

RAIZ = Path(__file__).resolve().parent.parent
ROTA = '/api/admin/operadoras/conferir'
PACIENTE = {'idade': 61, 'sexo': 'masculino', 'tabagismo': 'nunca_fumou'}


def _envio(cliente, paciente=PACIENTE, pdfs=None, **cabecalhos):
    dados = {}
    if paciente is not None:
        dados['paciente'] = paciente if isinstance(paciente, str) else json.dumps(paciente)
    if pdfs is None:
        pdfs = [(_pdf(FORMATO_C), 'pedido-7.pdf')]
    if pdfs:
        dados['pedido'] = [(io.BytesIO(conteudo), nome) for conteudo, nome in pdfs]
    return cliente.post(ROTA, data=dados, content_type='multipart/form-data',
                        headers={'Origin': 'http://localhost', **cabecalhos})


def _por_exame(resposta):
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    return {linha['exame']: linha for linha in resposta.get_json()['linhas']}


def test_pagina_e_rota_sao_so_do_administrador(client, admin, app):
    assert admin.get('/operadoras').status_code == 200
    assert client.get('/operadoras').status_code == 302                    # médica comum volta ao check-up
    assert app.test_client().get('/operadoras').status_code == 302         # sem login
    assert _envio(client).status_code == 403
    assert _envio(app.test_client()).status_code == 401
    assert _envio(admin, Origin='https://outro.exemplo').status_code == 403


def test_conferencia_e_o_check_up_do_paciente_sem_regra_a_mais(admin):
    """Cada exame pedido é indicado se, e só se, o check-up o recomenda para aquele paciente."""
    from src.utils import periodicidade
    sem = _por_exame(_envio(admin))
    com = _por_exame(_envio(admin, {**PACIENTE, 'comorbidades': ['hipertensao', 'diabetes'], 'nome_paciente': 'não entra'}))
    assert set(sem) == set(com) and len(com) >= 5
    for paciente, linhas in ((PACIENTE, sem), ({**PACIENTE, 'comorbidades': ['hipertensao', 'diabetes']}, com)):
        resposta = admin.post('/api/checkup-intelligent', json=paciente).get_json()
        recomendados = {chave for rec in resposta['recommendations'] if rec['categoria'] in ('laboratorio', 'imagem')
                        for chave in periodicidade.chaves(rec['titulo'], 'masculino')}
        for exame, linha in linhas.items():
            esperado = 'indicado' if periodicidade.cobertos(exame, 'masculino') & recomendados else 'nao_indicado'
            assert linha['veredito'] == esperado, (exame, linha)
    passaram_a_indicados = [e for e in com if com[e]['veredito'] == 'indicado' and sem[e]['veredito'] != 'indicado']
    assert passaram_a_indicados                      # a hipertensão e o diabetes informados mudam a conferência
    indicado = com[passaram_a_indicados[0]]
    assert indicado['motivo'] and indicado['referencias'] and indicado['referencias'][0]['url'].startswith('https://')
    for linha in com.values():                       # nada do modo em lote: sem cor nem finalidade
        assert 'cor' not in linha and 'finalidade_usada' not in linha


def test_exame_nao_indicado_traz_justificativa_formal_com_fonte(admin):
    """Não basta "não está no check-up": cada exame não indicado traz o que a diretriz diz, com link, e as situações
    em que o check-up o indica."""
    linhas = _por_exame(_envio(admin))
    nao_indicados = [linha for linha in linhas.values() if linha['estado'] == 'sem_indicacao']
    assert len(nao_indicados) >= 5
    for linha in nao_indicados:
        assert linha['motivo'] != 'O check-up não indica este exame para este paciente.'
        if linha['sem_justificativa']:
            assert 'Ainda não há justificativa de diretriz registrada' in linha['motivo']
        else:
            assert len(linha['motivo']) > 60 and linha['referencias'], linha
            assert all(fonte['url'].startswith('https://') and fonte['label'] for fonte in linha['referencias']), linha
    com_justificativa = [linha for linha in nao_indicados if not linha['sem_justificativa']]
    assert len(com_justificativa) >= 5
    sodio = linhas['Sódio, soro']
    assert sodio['motivo'].startswith('Sem recomendação de rastreio: a USPSTF não inclui o sódio entre os rastreios')
    assert 'Adultos com HAS' in sodio['indicado_para']['grupos'] and sodio['indicado_para']['grupos'][0].startswith('Adultos')
    # Cada situação vem com a referência que o check-up usa nela (a nossa), com link.
    situacoes = {s['grupo']: s['referencias'] for s in sodio['indicado_para']['situacoes']}
    assert list(situacoes) == sodio['indicado_para']['grupos']
    assert any(f['label'].startswith('AHA') for f in situacoes['Adultos com HAS'])
    assert all(f['label'] and f['url'].startswith('https://') for fontes in situacoes.values() for f in fontes)


def test_registro_de_justificativas_e_precedencia_do_parecer_de_sociedade():
    from src.utils import operadora, tuss
    for codigo, item in operadora.SEM_INDICACAO_DE_ROTINA.items():
        assert codigo in tuss.DESCRICOES or codigo in tuss.DA_TABELA, codigo
        assert len(item['texto']) > 60 and item['referencias'], codigo
        assert all(f['url'].startswith('https://') and f['label'] for f in item['referencias']), codigo
    tgo = operadora.justificativa_de_nao_indicacao({'40302504'}, 'masculino', 40)
    assert 'TGO' in tgo['texto'] and [f['label'] for f in tgo['referencias']] == ['CSCC 2024 (Choosing Wisely Canada)', 'AASLD 2023']
    # A vitamina D tem parecer de sociedade (Endocrine Society 2024): ele vem antes do registro próprio, com o aviso.
    vitamina_d = operadora.justificativa_de_nao_indicacao({'40302830'}, 'feminino', 40)
    assert vitamina_d['texto'].startswith('Endocrine Society 2024') and vitamina_d['aviso'].startswith('Divergência')
    assert operadora.justificativa_de_nao_indicacao({'nome:exame que ninguem pesquisou'}, 'feminino', 40) is None
    # Correções do responsável clínico (17/11/2026): creatinina pela KDIGO, não pelo ACP; ureia e bilirrubinas sem a
    # Choosing Wisely Canada; coagulograma pela NICE NG45, que o pré-operatório já usa.
    def fontes(codigo):
        return [f['label'] for f in operadora.justificativa_de_nao_indicacao({codigo}, 'masculino', 40)['referencias']]
    assert fontes('40301630') == ['KDIGO 2024', 'USPSTF (recomendações A e B)']
    assert fontes('40302580') == fontes('40301397') == fontes('40302423') == ['USPSTF (recomendações A e B)']
    assert fontes('40304590') == fontes('40304639') == ['USPSTF (recomendações A e B)', 'NICE NG45']
    assert fontes('40302512') == ['AASLD 2023', 'USPSTF (recomendações A e B)']
    # Grupo só de gestante não aparece para homem.
    homem, mulher = (operadora.indicado_para({'40304361'}, sexo)['grupos'] for sexo in ('masculino', 'feminino'))
    assert not [g for g in homem if 'estant' in g] and len(mulher) >= len(homem)
    resultado, _ = operadora.conferir_pedido(PACIENTE, [{'exame': 'Exame que ninguém pesquisou', 'codigos': None}])
    assert resultado['linhas'][0]['sem_justificativa'] and resultado['linhas'][0]['veredito'] == 'nao_indicado'


def test_resumo_e_lista_do_check_up_acompanham_a_resposta(admin):
    dados = _envio(admin, {**PACIENTE, 'comorbidades': ['hipertensao']}).get_json()
    resumo = dados['resumo']
    assert resumo['pedidos'] == len(dados['linhas']) == resumo['indicados'] + resumo['nao_indicados']
    assert resumo['do_checkup'] == len(dados['do_checkup']) > 0
    pedidos_do_checkup = {item['titulo'] for item in dados['do_checkup'] if item['pedido']}
    assert pedidos_do_checkup == {linha['no_checkup'] for linha in dados['linhas'] if linha['veredito'] == 'indicado'}


def test_exame_ja_feito_e_em_dia_sai_como_nao_indicado_agora(admin):
    """"Exames já realizados" vai ao motor como no check-up: o que está em dia não é indicado de novo."""
    paciente = {**PACIENTE, 'comorbidades': ['hipertensao']}
    assert _por_exame(_envio(admin, paciente))['Creatinina, soro']['veredito'] == 'indicado'
    from src.utils import periodicidade
    ontem = (periodicidade.hoje()).isoformat()
    em_dia = _por_exame(_envio(admin, {**paciente, 'exames_anteriores': [{'exame': 'Creatinina, soro', 'data': ontem}]}))
    linha = em_dia['Creatinina, soro']
    assert (linha['veredito'], linha['estado']) == ('nao_indicado', 'em_dia')
    assert linha['motivo'].startswith('Já feito e ainda em dia. Feito em ')


def test_calcio_total_conta_como_calcio_ionico_e_exame_registrado_traz_a_fonte():
    from src.utils import operadora
    paciente = {**PACIENTE, 'comorbidades': ['hipertensao']}
    pedidos = [{'exame': 'Cálcio', 'nome_no_pedido': 'CÁLCIO', 'codigos': None},
               {'exame': 'Ácido láctico (lactato)', 'nome_no_pedido': 'LACTATO', 'codigos': None}]
    resultado, erro = operadora.conferir_pedido(paciente, pedidos)
    assert erro is None
    calcio, lactato = resultado['linhas']
    assert calcio['veredito'] == 'indicado' and calcio['no_checkup'] == 'Cálcio iônico, soro'
    assert lactato['veredito'] == 'nao_indicado' and 'sepse' in lactato['motivo']
    assert lactato['referencias'][0]['url'].startswith('https://doi.org/')


def test_pedido_em_lista_de_nomes_ou_de_codigos_tuss_e_lido():
    """PDF que não é laudo de laboratório: lista de exames, com marcador, vírgula ou código TUSS."""
    from src.utils import operadora
    texto = ['Solicito:', '1. Hemograma completo', '- Creatinina, ureia', 'TSH (40316521)', '40302830', 'Retorno em 30 dias']
    pedidos, soltos, regime = operadora.exames_do_pedido(_pdf([texto]), 'pedido')
    nomes = {p['exame'] for p in pedidos}
    assert {'Hemograma completo com plaquetas', 'Creatinina, soro', 'Ureia, soro', 'Hormônio Tireoestimulante (TSH), soro',
            '25-hidroxivitamina D, soro'} <= nomes, nomes
    assert regime is None and all(p['arquivo'] == 'pedido' and p['data'] == '' for p in pedidos)
    # Nome em maiúsculas (que o leitor de laudos reconhece sozinho) junto de códigos e de nomes separados por vírgula:
    # nada fica de fora.
    misto, _, _ = operadora.exames_do_pedido(_pdf([['HEMOGRAMA COMPLETO', '40302830', 'Creatinina, ureia']]), 'pedido')
    assert {p['exame'] for p in misto} == {'Hemograma completo com plaquetas', '25-hidroxivitamina D, soro',
                                           'Creatinina, soro', 'Ureia, soro'}, misto
    # Laudo de laboratório (exames com data de coleta) continua lido só pelo leitor de laudos.
    do_laudo, _, _ = operadora.exames_do_pedido(_pdf(FORMATO_C), 'laudo')
    assert do_laudo and all(p['data'] for p in do_laudo)


def test_envio_incompleto_invalido_ou_ilegivel_volta_com_mensagem(admin):
    assert _envio(admin, paciente=None).status_code == 400
    assert _envio(admin, paciente='{').status_code == 400
    assert _envio(admin, pdfs=[]).status_code == 400
    invalido = _envio(admin, {**PACIENTE, 'idade': 300})
    assert invalido.status_code == 422 and invalido.get_json()['error'].startswith('Dados inválidos')
    ilegivel = _envio(admin, pdfs=[(b'nao e pdf', 'ruim.pdf')])
    assert ilegivel.status_code == 422 and 'ruim: não lido' in ilegivel.get_json()['error']
    muitos = _envio(admin, pdfs=[(_pdf(FORMATO_C), f'p{n}.pdf') for n in range(9)])
    assert muitos.status_code == 413
    # Um arquivo ruim não derruba os demais: vira aviso.
    misto = _envio(admin, pdfs=[(_pdf(FORMATO_C), 'pedido-7.pdf'), (b'nao e pdf', 'ruim.pdf')])
    assert misto.status_code == 200 and any(aviso.startswith('ruim: não lido') for aviso in misto.get_json()['avisos'])


def test_arquivo_enviado_nao_passa_para_o_disco(app):
    """O Werkzeug grava em arquivo temporário o envio com mais de 500 KiB; aqui ele fica na memória."""
    grande = io.BytesIO(b'x' * 700 * 1024)
    with app.test_request_context(ROTA, method='POST', data={'pedido': (grande, 'pedido.pdf')},
                                  content_type='multipart/form-data'):
        from flask import request
        assert isinstance(request.files['pedido'].stream, io.BytesIO)


def test_formulario_do_check_up_fica_na_pagina_das_operadoras(admin):
    operadoras = admin.get('/operadoras').get_data(as_text=True)
    assert 'src="/intelligent-tools?modo=operadora&amp;embutido=1"' in operadoras and 'data-pedido-pdf' in operadoras
    assert 'href="/intelligent-tools?' not in operadoras                  # sem link que leve para fora da página
    for antigo in ('data-form-csv', 'data-form-laudos', 'Finalidade', 'Regime', 'modo sombra'):
        assert antigo not in operadoras, antigo
    checkup = admin.get('/intelligent-tools').get_data(as_text=True)
    assert "classList.add('embutido')" in checkup and "'/api/admin/operadoras/conferir'" in checkup
    assert "window.location.replace('/operadoras')" in checkup            # fora do quadro, o modo operadora não vale
    assert 'operadoraPedido' not in checkup and 'operadoras_resultado' in checkup
    # Resposta de um envio cujo paciente ou PDF mudou é descartada, como no check-up.
    assert "conferirPedidoDaOperadora(data, revisaoDoEnvio)" in checkup and "tipo: 'operadoras_descartado'" in checkup


def test_justificativa_so_cita_sociedade_que_o_algoritmo_ja_cita():
    """Decisão do responsável clínico (17/11/2026): a fonte da justificativa é só sociedade que o check-up já cita.
    Referência é a sociedade (USPSTF, AHA/ACC, KDIGO), não uma diretriz específica. Aceitas à parte: a Surviving
    Sepsis Campaign e, só na TGO, a CSCC."""
    from src.utils import operadora
    assert operadora.sociedades_da_fonte('AHA/ACC 2018 (colesterol)') == {'AHA', 'ACC'}
    assert operadora.sociedades_da_fonte('NICE NG45') == {'NICE'}
    assert operadora.sociedades_da_fonte('CSEM (Choosing Wisely Canada), ASCP 2015 e SBPC/ML 2019') == {'CSEM', 'ASCP', 'SBPC', 'ML'}
    do_algoritmo = operadora.sociedades_do_algoritmo()
    assert {'USPSTF', 'AHA', 'ACC', 'KDIGO', 'AASLD', 'NICE', 'Endocrine Society', 'Surviving Sepsis Campaign'} <= do_algoritmo
    assert not {'ACP', 'CSCC', 'CFPC', 'BCSH', 'CAMB', 'ASCP', 'CRA', 'CSEM', 'SBI'} & do_algoritmo
    for codigo, item in operadora.SEM_INDICACAO_DE_ROTINA.items():
        for fonte in item['referencias']:
            assert operadora.fonte_aceita(fonte['label'], codigo), (codigo, fonte['label'])
        for de_fora in ('ACP', 'CFPC', 'BCSH', 'Choosing Wisely'):
            assert codigo == '40302504' or de_fora not in item['texto'], (codigo, de_fora)
    assert operadora.fonte_aceita('CSCC 2024 (Choosing Wisely Canada)', '40302504')          # só na TGO
    assert not operadora.fonte_aceita('CSCC 2024 (Choosing Wisely Canada)', '40302580')
    # Parecer de sociedade que o algoritmo não cita (CAMB, ASCP, CRA, CSEM) não vai para a tela: fica a USPSTF.
    for codigo in ('40304370', '40301150', '40301761', '40306852', '40312127', '40306437', '40304612', '40306909', '40301087'):
        vai = operadora.justificativa_de_nao_indicacao({codigo}, 'feminino', 40)
        assert [f['label'] for f in vai['referencias']] == ['USPSTF (recomendações A e B)'], codigo
        assert 'Choosing Wisely' not in vai['texto'], codigo
    t4 = operadora.justificativa_de_nao_indicacao({'40316491'}, 'feminino', 40)
    assert t4['texto'].startswith('USPSTF 2015 (grau I)') and [f['label'] for f in t4['referencias']] == ['USPSTF 2015']
    # Parecer de sociedade do algoritmo continua valendo, e o texto não cita sociedade de fora.
    for codigo, sexo, inicio in (('40302830', 'feminino', 'Endocrine Society 2024'), ('40316513', 'masculino', 'Endocrine Society 2018'),
                                 ('40307085', 'feminino', 'USPSTF 2023'), ('40310213', 'masculino', 'USPSTF 2019')):
        vai = operadora.justificativa_de_nao_indicacao({codigo}, sexo, 55)
        assert vai['texto'].startswith(inicio), codigo
        assert not any(fora in vai['texto'] for fora in ('SBI', 'CUA', 'ASCP', 'CFPC', 'SBMFC')), codigo


def test_glicemia_de_jejum_vale_pela_hba1c_no_rastreio():
    """Decisão do responsável clínico (18/11/2026): a glicemia de jejum pedida conta como indicada quando o check-up
    recomenda a HbA1c e a própria recomendação a cita como alternativa. Um exame basta: com a HbA1c no mesmo pedido,
    a glicemia não entra."""
    from src.utils import operadora
    paciente = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca_fumou', 'peso': '90', 'altura': '170'}
    def conferir(*exames):
        resultado, erro = operadora.conferir_pedido(paciente, [{'exame': e} for e in exames])
        assert erro is None
        return {linha['exame']: linha for linha in resultado['linhas']}, resultado
    linhas, resultado = conferir('Glicose, soro')
    glicemia = linhas['Glicose, soro']
    assert glicemia['veredito'] == 'indicado' and glicemia['no_checkup'] == 'Hemoglobina glicada (HbA1c), soro'
    assert 'aceita a glicemia de jejum como alternativa' in glicemia['motivo'] and glicemia['grau'] == 'B'
    assert any(f['url'].startswith('https://') for f in glicemia['referencias'])
    assert next(r for r in resultado['do_checkup'] if r['titulo'].startswith('Hemoglobina glicada'))['pedido'] is True
    linhas, _ = conferir('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro')
    assert linhas['Hemoglobina glicada (HbA1c), soro']['veredito'] == 'indicado'
    assert linhas['Glicose, soro']['veredito'] == 'nao_indicado' and 'um exame basta' in linhas['Glicose, soro']['motivo']
    assert linhas['Glicose, soro']['referencias']
    # No diabético a glicemia não é alternativa à HbA1c: o check-up a recomenda por si, junto da HbA1c.
    paciente = dict(paciente, comorbidades=['diabetes_tipo_2'])
    linhas, _ = conferir('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro')
    assert linhas['Glicose, soro']['veredito'] == 'indicado' and linhas['Glicose, soro']['no_checkup'] == 'Glicose, soro'


# --- Exames já realizados saem da página; vacinas já tomadas entram; vacinas a avisar, em bloco à parte ---------------
# Decisão do responsável clínico (18/11/2026): a página das operadoras não pergunta os exames já realizados. No lugar,
# "Vacinas já tomadas"; no resultado, as vacinas que o check-up recomenda (pela SBIm), fora da conferência do pedido.

def _so_no_modo_operadora(checkup):
    """O trecho do script do formulário que só roda quando ele está embutido na página das operadoras."""
    inicio = checkup.index('if (MODO_OPERADORA && EMBUTIDO) {')
    return checkup[inicio:checkup.index('// Vacinas já tomadas (só na página das operadoras)', inicio)]


def test_secao_08_troca_de_exames_para_vacinas_so_na_pagina_das_operadoras(admin):
    checkup = admin.get('/intelligent-tools').get_data(as_text=True)
    # No check-up do médico nada muda: a seção 08 é a dos exames já realizados, que seguem no envio, e a das vacinas
    # já tomadas fica escondida.
    assert '<section class="secao" aria-labelledby="s-exames">' in checkup
    assert '<span class="secao-num">08</span>Exames já realizados</h2>' in checkup
    assert 'if (anteriores.length) data.exames_anteriores = anteriores;' in checkup
    assert '<section class="secao" aria-labelledby="s-vacinas-tomadas" hidden>' in checkup
    # Só o formulário embutido esconde a seção dos exames, desliga os campos dela (deixam de ir no envio) e mostra a
    # das vacinas. A numeração conta só as seções visíveis, e a das vacinas fica com o 08.
    so_na_operadora = _so_no_modo_operadora(checkup)
    for trecho in ('secaoDosExames.hidden = true', 'campo.disabled = true',
                   """document.querySelector('section[aria-labelledby="s-vacinas-tomadas"]').hidden = false"""):
        assert trecho in so_na_operadora and checkup.count(trecho) == 1, trecho
    assert 'if (secao.hidden) return;' in checkup
    assert checkup.index('aria-labelledby="s-exames"') < checkup.index('aria-labelledby="s-vacinas-tomadas"') < checkup.index('id="formErrors"')
    # As duas perguntas do rastreio anterior do colo do útero ficavam na seção 08 e não são exame já feito: saem dela
    # antes de os campos serem desligados, e continuam no formulário.
    mover = "appendChild(document.getElementById('colo-historico').parentElement)"
    assert mover in so_na_operadora and so_na_operadora.index(mover) < so_na_operadora.index('campo.disabled = true')
    operadoras = admin.get('/operadoras').get_data(as_text=True)
    assert 'com "Vacinas já tomadas" no lugar de "Exames já realizados"' in operadoras


def test_no_envio_da_operadora_nao_vai_exame_ja_realizado_so_as_vacinas_ja_tomadas(admin):
    from src.utils import i18n
    checkup = admin.get('/intelligent-tools').get_data(as_text=True)
    envio = checkup[checkup.index('async function conferirPedidoDaOperadora'):checkup.index("checkupForm.addEventListener('submit'")]
    # O que viesse dos exames já realizados é retirado; no campo deles seguem só as vacinas, no formato que o motor
    # já entende (título e data).
    assert envio.index('delete paciente.exames_anteriores;') < envio.index('if (vacinas.length) paciente.exames_anteriores = vacinas;')
    assert checkup.count('paciente.exames_anteriores') == 2
    assert '{ exame: nomeDaVacina[digitado.toLowerCase()] || digitado, data: ' in checkup
    # A vacina é escolhida no catálogo do motor, e a tela confere a escolha e a data antes de enviar.
    assert "fetch('/api/admin/operadoras/vacinas'" in checkup and 'listaDeBusca(nome, carregarVacinasDoMotor' in checkup
    assert '!doCatalogo.includes(v.exame)' in envio and '!v.data' in envio and 'v.data > hojeNoFormato()' in envio
    for texto in ('Retirar esta vacina', 'Vacina', 'Tomada em', 'Vacinas já tomadas: escolha cada vacina na lista.',
                  'Vacinas já tomadas: informe a data de cada vacina.', 'Vacinas já tomadas: a data não pode estar no futuro.'):
        assert f"'{texto}'" in checkup and i18n.coberto(texto), texto


def test_vacinas_ja_tomadas_sao_escolhidas_no_catalogo_do_motor(admin, client, app):
    do_motor = json.loads((RAIZ / 'src' / 'data' / 'catalogo_motor.json').read_text(encoding='utf-8'))['vacina']
    resposta = admin.get('/api/admin/operadoras/vacinas')
    assert resposta.status_code == 200 and len(do_motor) >= 15
    assert sorted(resposta.get_json()['vacinas']) == sorted(do_motor)
    assert client.get('/api/admin/operadoras/vacinas').status_code == 403
    assert app.test_client().get('/api/admin/operadoras/vacinas').status_code == 401


def test_vacinas_do_check_up_saem_em_bloco_a_parte_com_o_esquema_e_a_referencia_do_motor(admin):
    paciente = {**PACIENTE, 'imunossupressao': 'nao'}
    dados = _envio(admin, paciente).get_json()
    do_motor = [rec for rec in admin.post('/api/checkup-intelligent', json=paciente).get_json()['recommendations']
                if rec['categoria'] == 'vacina']
    assert len(do_motor) >= 5 and [v['titulo'] for v in dados['vacinas']] == [rec['titulo'] for rec in do_motor]
    for vacina, rec in zip(dados['vacinas'], do_motor):       # nada além do que o motor recomenda, como ele recomenda
        assert vacina == {'titulo': rec['titulo'], 'motivo': rec['subtitulo'], 'grau': rec['grau_evidencia'],
                          'referencias': rec['referencias'], 'doses_informadas': []}
        assert vacina['motivo'] and vacina['grau']
        assert all(fonte['label'] and fonte['url'].startswith('https://') for fonte in vacina['referencias'])
        assert any(fonte['label'].startswith('SBIm') for fonte in vacina['referencias']), vacina['titulo']
    assert dados['outras_vacinas_informadas'] == []
    # Fora da conferência do pedido: nenhuma vacina entre as linhas, na lista do check-up ou no resumo.
    nomes = {v['titulo'] for v in dados['vacinas']}
    assert not nomes & ({linha['exame'] for linha in dados['linhas']} | {linha['no_checkup'] for linha in dados['linhas']}
                        | {item['titulo'] for item in dados['do_checkup']})
    assert {item['categoria'] for item in dados['do_checkup']} <= {'laboratorio', 'imagem'}
    assert set(dados['resumo']) == {'pedidos', 'indicados', 'nao_indicados', 'do_checkup'}


def test_vacina_ja_tomada_chega_ao_motor_e_so_acompanha_a_recomendacao(admin):
    """A vacina já tomada segue no formato dos exames já realizados (título e data), e o motor confere a data. Ele não
    tem regra de histórico vacinal (perigo P-19, em aberto; docs/periodicidade.md: "vacinas não passam por esta
    regra"): a vacina continua recomendada, com o mesmo esquema, e a data informada só a acompanha. Nenhuma regra de
    vacina foi criada: não há "em dia" nem data da próxima dose."""
    paciente = {**PACIENTE, 'comorbidades': ['hipertensao']}
    sem = _envio(admin, paciente).get_json()
    influenza, dtpa = (next(v['titulo'] for v in sem['vacinas'] if v['titulo'].startswith(nome)) for nome in ('Influenza', 'dTpa'))
    de_outro_perfil = 'Hepatites A e B (Twinrix® ou vacinas isoladas)'      # do catálogo do motor, não deste paciente
    assert de_outro_perfil not in {v['titulo'] for v in sem['vacinas']}
    tomadas = [{'exame': dtpa, 'data': '2024-01-10'}, {'exame': influenza, 'data': '2026-05-10'},
               {'exame': dtpa, 'data': '2014-06-01'}, {'exame': de_outro_perfil, 'data': '2010-03-02'}]
    com = _envio(admin, {**paciente, 'exames_anteriores': tomadas}).get_json()
    doses = {v['titulo']: v['doses_informadas'] for v in com['vacinas'] if v['doses_informadas']}
    assert doses == {influenza: ['2026-05-10'], dtpa: ['2014-06-01', '2024-01-10']}
    assert com['outras_vacinas_informadas'] == [{'titulo': de_outro_perfil, 'doses_informadas': ['2010-03-02']}]
    def sem_as_doses(vacinas):
        return [{campo: valor for campo, valor in vacina.items() if campo != 'doses_informadas'} for vacina in vacinas]
    assert sem_as_doses(com['vacinas']) == sem_as_doses(sem['vacinas'])
    assert all(set(vacina) == {'titulo', 'motivo', 'grau', 'referencias', 'doses_informadas'} for vacina in com['vacinas'])
    # O veredito dos exames é o mesmo com e sem vacinas informadas.
    for parte in ('resumo', 'linhas', 'do_checkup'):
        assert com[parte] == sem[parte], parte
    # A data passa pela validação do motor: futura ou em branco, o envio volta com a mensagem dele.
    for data in ('2999-01-01', ''):
        recusado = _envio(admin, {**paciente, 'exames_anteriores': [{'exame': influenza, 'data': data}]})
        assert recusado.status_code == 422 and recusado.get_json()['error'].startswith('Dados inválidos'), data


def test_nenhuma_vacina_do_catalogo_vale_por_exame_e_o_exame_ja_feito_continua_valendo_na_rota():
    """A vacina viaja no campo dos exames já realizados: o nome dela não pode coincidir com exame algum."""
    from src.utils import catalogo, operadora, periodicidade
    sexos = (None, 'feminino', 'masculino')
    de_exame = {chave for categoria in ('laboratorio', 'imagem') for titulo in catalogo.catalogo()[categoria]
                for sexo in sexos for chave in periodicidade.cobertos(titulo, sexo)}
    for vacina in catalogo.vacinas_do_motor():
        for sexo in sexos:
            chaves = periodicidade.cobertos(vacina, sexo)
            assert len(chaves) == 1 and next(iter(chaves)).startswith('nome:') and not chaves & de_exame, vacina
    hoje = periodicidade.hoje().isoformat()
    paciente = {**PACIENTE, 'comorbidades': ['hipertensao', 'diabetes']}
    pedidos = [{'exame': exame} for exame in ('Creatinina, soro', 'Sódio, soro', 'Hemoglobina glicada (HbA1c), soro',
                                             'Ácido láctico (lactato)')]
    sem, _ = operadora.conferir_pedido(paciente, pedidos)
    todas = [{'exame': vacina, 'data': hoje} for vacina in catalogo.vacinas_do_motor()]
    com, erro = operadora.conferir_pedido({**paciente, 'exames_anteriores': todas}, pedidos)
    assert erro is None and com['vacinas'] and all(vacina['doses_informadas'] == [hoje] for vacina in com['vacinas'])
    assert len(com['vacinas']) + len(com['outras_vacinas_informadas']) == len(todas)
    for parte in ('resumo', 'linhas', 'do_checkup'):
        assert com[parte] == sem[parte], parte
    # Pela rota (dados que virão do cadastro da operadora), o exame já feito continua valendo, junto das vacinas.
    misto, _ = operadora.conferir_pedido({**paciente, 'exames_anteriores': todas + [{'exame': 'Creatinina, soro', 'data': hoje}]},
                                         pedidos)
    creatinina = next(linha for linha in misto['linhas'] if linha['exame'] == 'Creatinina, soro')
    assert (creatinina['veredito'], creatinina['estado']) == ('nao_indicado', 'em_dia')
    assert misto['vacinas'] == com['vacinas'] and misto['outras_vacinas_informadas'] == com['outras_vacinas_informadas']


def test_sem_vacina_recomendada_o_bloco_vem_vazio_e_a_conferencia_e_a_mesma(monkeypatch):
    from src.routes import checkup_intelligent
    from src.utils import operadora
    paciente = {**PACIENTE, 'comorbidades': ['hipertensao']}
    pedidos = [{'exame': exame} for exame in ('Creatinina, soro', 'Sódio, soro', 'Ácido láctico (lactato)')]
    com, _ = operadora.conferir_pedido(paciente, pedidos)
    assert com['vacinas']
    motor = checkup_intelligent.recomendar

    def sem_vacinas(dados):
        resposta, status = motor(dados)
        return {**resposta, 'recommendations': [rec for rec in resposta['recommendations'] if rec['categoria'] != 'vacina']}, status
    monkeypatch.setattr(checkup_intelligent, 'recomendar', sem_vacinas)
    sem, erro = operadora.conferir_pedido(paciente, pedidos)
    assert erro is None and sem['vacinas'] == [] and sem['outras_vacinas_informadas'] == []
    for parte in ('resumo', 'linhas', 'do_checkup'):
        assert sem[parte] == com[parte], parte


def test_bloco_de_vacinas_na_tela_fica_fora_do_veredito_e_do_csv(admin):
    operadoras = admin.get('/operadoras').get_data(as_text=True)
    for texto in ('Vacinas para avisar ao paciente',
                  'As vacinas não entram na conferência do pedido: não liberam nem barram exame algum.',
                  'O check-up não desconta a vacina já tomada nem calcula a data da próxima dose'):
        assert texto in operadoras, texto
    # Depois da conferência dos exames e da lista do check-up, fora dos cartões do veredito.
    assert (operadoras.index('<div data-linhas') < operadoras.index('<ul data-do-checkup')
            < operadoras.index('<div data-vacinas ') < operadoras.index('<div data-outras-vacinas '))
    script = (RAIZ / 'static' / 'operadoras.js').read_text(encoding='utf-8')
    for trecho in ('dados.vacinas || []', 'dados.outras_vacinas_informadas || []', 'fontes(v.referencias, v.grau)',
                   'Informada como já tomada em', "'Nenhuma vacina a avisar para este paciente.'"):
        assert trecho in script, trecho
    # O CSV continua só com os exames: as mesmas colunas (não há coluna de tipo) e só as linhas da conferência.
    baixar = script[script.index('function baixar()'):script.index('function desatualizar()')]
    assert ("[['exame', 'nome_no_pedido', 'data', 'arquivo', 'conferencia', 'justificativa', 'no_checkup', 'grau', "
            "'referencias', 'no_checkup_indicado_para']]") in baixar
    assert 'dados.linhas.map' in baixar and 'vacina' not in baixar.lower()
