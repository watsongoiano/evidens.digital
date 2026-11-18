"""Conferência do pedido pelo check-up (/operadoras): por enquanto, só o administrador vê e envia."""
import io
import json

from tests.test_operadora import FORMATO_C, _pdf

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
