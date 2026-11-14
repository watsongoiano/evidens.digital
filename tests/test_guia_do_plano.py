"""Vínculo com planos de saúde, etapa 1: credenciamentos do médico, códigos TUSS e guia SP/SADT."""
import io
import itertools
import re

import pytest
from pypdf import PdfReader

from conftest import SENHA_DE_TESTE
from src.utils import catalogo, pdf_minutas, tuss

_seq = itertools.count(1)
PLANO = dict(operadora='Unimed Goiânia', registro_ans='123456', codigo_prestador='0012345',
             nome_contratado='Clínica de Teste Ltda.', cbo='225125')
PACIENTE = {'nome': 'Maria de Teste', 'idade': '65', 'sexo': 'feminino'}
EXAMES = [{'titulo': t, 'categoria': 'laboratorio'} for t in
          ('Hemograma completo', 'Creatinina, soro', 'TGO e TGP, soro', 'Colesterol total e frações, soro')]


def _paginas(dados):
    assert dados.startswith(b'%PDF')
    return [p.extract_text() for p in PdfReader(io.BytesIO(dados)).pages]


def _conta(app, contas, perfil='medico'):
    """Cliente logado numa conta nova e aprovada."""
    n = next(_seq)
    registro = 'CRM-GO 4321' + str(n) if perfil != 'estudante' else '2023001 · UFG'
    u = contas.criar(f'plano{n}@exemplo.test', f'Dra. Plano {n}', registro, perfil, SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


# --- Códigos TUSS -------------------------------------------------------------

@pytest.mark.parametrize('categoria', ['laboratorio', 'imagem'])
def test_todo_exame_tem_codigo_tuss_ou_motivo_declarado(categoria):
    """Nenhum exame fica sem destino: ou tem código conferido, ou está em SEM_CODIGO com o motivo."""
    sem_destino = [t for t in catalogo.catalogo()[categoria]
                   if tuss._chave(t) not in tuss._POR_CHAVE and t not in tuss.SEM_CODIGO]
    assert not sem_destino, f'exames sem código TUSS nem motivo: {sem_destino}'


def test_codigos_tem_oito_digitos_e_descricao():
    usados = set()
    for titulo, itens in tuss.CODIGOS.items():
        assert itens, titulo
        for item in itens:
            quantidade = 1
            if isinstance(item, tuple):
                item, quantidade = item
            assert quantidade in (1, 2), titulo
            usados.update(item.values() if isinstance(item, dict) else [item])
    assert usados == set(tuss.DESCRICOES)
    assert all(re.fullmatch(r'\d{8}', c) for c in usados)
    assert all(motivo.strip() for motivo in tuss.SEM_CODIGO.values())
    assert not set(map(tuss._chave, tuss.SEM_CODIGO)) & set(tuss._POR_CHAVE)


def test_linhas_da_guia():
    assert tuss.linhas_da_guia('Creatinina, soro') == [
        {'codigo': '40301630', 'descricao': 'Creatinina - pesquisa e/ou dosagem', 'quantidade': 1}]
    assert [l['codigo'] for l in tuss.linhas_da_guia('  tgo e tgp, SORO ')] == ['40302504', '40302512']
    # por lado: sai com quantidade 2
    assert tuss.linhas_da_guia('Ressonância magnética de mamas')[0]['quantidade'] == 2
    # o código depende do sexo; sem sexo, não se escolhe um
    assert tuss.linhas_da_guia('Ultrassonografia de vias urinárias', 'feminino')[0]['codigo'] == '40901157'
    assert tuss.linhas_da_guia('Ultrassonografia de vias urinárias', 'masculino')[0]['codigo'] == '40901165'
    assert tuss.linhas_da_guia('Ultrassonografia de vias urinárias')[0]['codigo'] == ''
    # sem código conferido, ou digitado à mão: sai sem código, nunca com um inventado
    for titulo in ('Ácido fólico, soro', 'Exame que o médico digitou'):
        assert tuss.linhas_da_guia(titulo) == [{'codigo': '', 'descricao': titulo, 'quantidade': 1}]


# --- Credenciamentos ----------------------------------------------------------

def test_medico_cadastra_lista_e_remove_plano(app, contas):
    cliente, _ = _conta(app, contas)
    assert cliente.get('/api/auth/credenciamentos').get_json() == {'credenciamentos': [], 'disponivel': True}
    resposta = cliente.post('/api/auth/credenciamentos', json=dict(PLANO, registro_ans='12.345-6', cbo='2251-25'))
    assert resposta.status_code == 201
    salvo = resposta.get_json()['credenciamento']
    assert {k: salvo[k] for k in PLANO} == PLANO          # pontuação sai do registro ANS e do CBO
    assert [c['id'] for c in cliente.get('/api/auth/credenciamentos').get_json()['credenciamentos']] == [salvo['id']]
    assert cliente.post(f'/api/auth/credenciamentos/{salvo["id"]}/excluir').status_code == 200
    assert cliente.get('/api/auth/credenciamentos').get_json()['credenciamentos'] == []
    assert cliente.post(f'/api/auth/credenciamentos/{salvo["id"]}/excluir').status_code == 404


def test_plano_invalido_diz_o_que_corrigir(app, contas):
    cliente, _ = _conta(app, contas)
    resposta = cliente.post('/api/auth/credenciamentos',
                            json=dict(operadora='', registro_ans='123', codigo_prestador=' ', nome_contratado='', cbo='1'))
    assert resposta.status_code == 400
    assert len(resposta.get_json()['erros']) == 5
    assert cliente.get('/api/auth/credenciamentos').get_json()['credenciamentos'] == []


def test_registro_ans_e_cbo_sao_opcionais(app, contas):
    cliente, _ = _conta(app, contas)
    resposta = cliente.post('/api/auth/credenciamentos', json=dict(PLANO, registro_ans='', cbo=''))
    assert resposta.status_code == 201


def test_plano_de_um_medico_nao_aparece_nem_e_removido_por_outro(app, contas):
    dona, _ = _conta(app, contas)
    outro, _ = _conta(app, contas)
    cid = dona.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    assert outro.get('/api/auth/credenciamentos').get_json()['credenciamentos'] == []
    assert outro.post(f'/api/auth/credenciamentos/{cid}/excluir').status_code == 404
    pedido = {'dados_paciente': PACIENTE, 'recomendacoes': EXAMES, 'guia': {'credenciamento_id': cid}}
    resposta = outro.post('/api/gerar-pdf-exames-laboratoriais', json=pedido)
    assert resposta.status_code == 400 and resposta.get_json()['codigo'] == 'guia_indisponivel'
    assert len(dona.get('/api/auth/credenciamentos').get_json()['credenciamentos']) == 1


def test_estudante_nao_tem_credenciamento_nem_guia(app, contas):
    aluno, _ = _conta(app, contas, perfil='estudante')
    assert aluno.get('/api/auth/credenciamentos').get_json() == {'credenciamentos': [], 'disponivel': False}
    assert aluno.post('/api/auth/credenciamentos', json=PLANO).status_code == 403
    pedido = {'dados_paciente': PACIENTE, 'recomendacoes': EXAMES, 'guia': {'credenciamento_id': 1}}
    assert aluno.post('/api/gerar-pdf-exames-laboratoriais', json=pedido).status_code == 400


def test_credenciamentos_exigem_login(anonimo):
    assert anonimo.get('/api/auth/credenciamentos').status_code == 401
    assert anonimo.post('/api/auth/credenciamentos', json=PLANO).status_code == 401
    assert anonimo.post('/api/auth/credenciamentos/1/excluir').status_code == 401


def test_limite_de_planos_por_conta(app, contas, monkeypatch):
    monkeypatch.setattr(contas, 'MAX_CREDENCIAMENTOS', 2)
    cliente, _ = _conta(app, contas)
    assert cliente.post('/api/auth/credenciamentos', json=PLANO).status_code == 201
    assert cliente.post('/api/auth/credenciamentos', json=dict(PLANO, operadora='CASSI')).status_code == 201
    assert cliente.post('/api/auth/credenciamentos', json=dict(PLANO, operadora='Ipasgo Saúde')).status_code == 400


# --- Guia SP/SADT no PDF do pedido --------------------------------------------

def test_pedido_sem_guia_continua_igual(app, contas):
    cliente, _ = _conta(app, contas)
    cliente.post('/api/auth/credenciamentos', json=PLANO)
    resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais', json={'dados_paciente': PACIENTE, 'recomendacoes': EXAMES})
    paginas = _paginas(resposta.data)
    assert len(paginas) == 1 and 'SP/SADT' not in paginas[0]


@pytest.mark.parametrize('rota', ['/api/gerar-pdf-exames-laboratoriais', '/api/gerar-pdf-exames-imagem'])
def test_guia_sai_depois_do_pedido_com_os_dados_do_medico_e_do_plano(app, contas, rota):
    cliente, medico = _conta(app, contas)
    cid = cliente.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    itens = EXAMES + [{'titulo': 'Eletrocardiograma de repouso', 'categoria': 'imagem'}]
    guia = {'credenciamento_id': cid, 'carteira': '0064 0012 3456 7890', 'indicacao': 'Check-up — 65 anos, diabetes tipo 2'}
    resposta = cliente.post(rota, json={'dados_paciente': PACIENTE, 'recomendacoes': itens, 'guia': guia})
    assert resposta.status_code == 200
    pedido, *guias = _paginas(resposta.data)
    assert 'SOLICITAÇÃO DE EXAMES' in pedido and 'SP/SADT' not in pedido
    texto = '\n'.join(guias)
    for esperado in ('SP/SADT', 'Unimed Goiânia', '123456', '0012345', 'Clínica de Teste Ltda.', '225125',
                     medico['nome'], 'CRM', medico['registro'].split()[-1], 'GO', 'Maria de Teste',
                     '0064 0012 3456 7890', 'Check-up — 65 anos, diabetes tipo 2', '1 - Eletivo'):
        assert esperado in texto, esperado
    if 'laboratoriais' in rota:
        # 8 códigos (hemograma, creatinina, TGO, TGP e os 4 do perfil lipídico): 5 por guia = 2 guias
        assert len(guias) == 2 and 'Guia 1 de 2' in guias[0] and 'Guia 2 de 2' in guias[1]
        for codigo in ('40304361', '40301630', '40302504', '40302512', '40301605', '40301583', '40301591', '40302547'):
            assert texto.count(codigo) == 1, codigo
        assert '40101010' not in texto          # o ECG é do pedido de imagem
    else:
        assert len(guias) == 1 and '40101010' in texto and '40304361' not in texto


def test_guia_sem_indicacao_sai_como_check_up_e_exame_sem_codigo_sai_em_branco(app, contas):
    cliente, _ = _conta(app, contas)
    cid = cliente.post('/api/auth/credenciamentos', json=dict(PLANO, registro_ans='', cbo='')).get_json()['credenciamento']['id']
    itens = [{'titulo': 'Ácido fólico, soro', 'categoria': 'laboratorio'}, {'titulo': 'Exame digitado', 'categoria': 'laboratorio'}]
    resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais',
                            json={'dados_paciente': PACIENTE, 'recomendacoes': itens, 'guia': {'credenciamento_id': cid}})
    _, guia = _paginas(resposta.data)
    assert 'Check-up' in guia and 'Ácido fólico, soro' in guia and 'Exame digitado' in guia
    assert not re.search(r'\b\d{8}\b', guia)


def test_mesmo_codigo_pedido_duas_vezes_sai_numa_linha_so():
    guia = {'credenciamento': PLANO, 'carteira': '', 'indicacao': 'Check-up'}
    exames = [{'titulo': 'TGO e TGP, soro'}, {'titulo': 'Alanina aminotransferase, soro'}]
    pdf = pdf_minutas.gerar_pdf_exames_laboratoriais(PACIENTE, exames, guia=guia)
    assert '\n'.join(_paginas(pdf)[1:]).count('40302512') == 1


@pytest.mark.parametrize('guia', [
    'unimed', {'credenciamento_id': '1'}, {'credenciamento_id': True}, {'credenciamento_id': 10 ** 9},
    {'carteira': '1'},
])
def test_guia_malformada_e_recusada(app, contas, guia):
    cliente, _ = _conta(app, contas)
    cliente.post('/api/auth/credenciamentos', json=PLANO)
    resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais',
                            json={'dados_paciente': PACIENTE, 'recomendacoes': EXAMES, 'guia': guia})
    assert resposta.status_code == 400


def test_carteira_e_indicacao_longas_sao_recusadas(app, contas):
    cliente, _ = _conta(app, contas)
    cid = cliente.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    for extra in ({'carteira': '9' * 31}, {'indicacao': 'x' * 301}, {'indicacao': 5}):
        resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais', json={
            'dados_paciente': PACIENTE, 'recomendacoes': EXAMES, 'guia': dict({'credenciamento_id': cid}, **extra)})
        assert resposta.status_code == 400, extra


def test_vacinas_nao_levam_guia(app, contas):
    cliente, _ = _conta(app, contas)
    cid = cliente.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    vacina = {'titulo': 'Influenza Tetravalente (Fluarix®, Vaxigrip® ou similar)', 'categoria': 'vacina'}
    resposta = cliente.post('/api/gerar-pdf-vacinas', json={
        'dados_paciente': dict(PACIENTE, gestante='nao', lactante='nao', imunossupressao='nao'),
        'recomendacoes': [vacina], 'guia': {'credenciamento_id': cid}})
    assert resposta.status_code == 200
    assert all('SP/SADT' not in pagina for pagina in _paginas(resposta.data))


def test_valores_no_limite_saem_inteiros_na_guia(app, contas):
    """Carteira, indicação, nomes e descrições no tamanho máximo aceito não perdem caracteres."""
    cliente, _ = _conta(app, contas)
    plano = dict(operadora='Operadora de Nome Bem Comprido de Autogestão em Saúde do Centro-Oeste Brasileiro S.A.'[:80],
                 registro_ans='123456', codigo_prestador='12345678901234567890',
                 nome_contratado=('Clínica de Medicina Interna e Check-up Baseado em Evidências ' * 3)[:120].strip(), cbo='225125')
    cid = cliente.post('/api/auth/credenciamentos', json=plano).get_json()['credenciamento']['id']
    carteira = '123456789012345678901234567890'
    indicacao = ('Check-up — 65 anos, diabetes tipo 2, hipertensão, dislipidemia, doença renal crônica, '
                 'insuficiência cardíaca, DPOC, obesidade, hipotireoidismo e osteoporose em seguimento')[:150]
    paciente = dict(PACIENTE, nome=('Maria Aparecida ' * 10)[:150].strip())
    itens = [{'titulo': 'Urocultura com antibiograma', 'categoria': 'laboratorio'},
             {'titulo': 'Exame digitado à mão com um nome muito comprido ' * 6, 'categoria': 'laboratorio'}]
    resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais', json={
        'dados_paciente': paciente, 'recomendacoes': itens,
        'guia': {'credenciamento_id': cid, 'carteira': carteira, 'indicacao': indicacao}})
    assert resposta.status_code == 200
    texto = ' '.join(' '.join(_paginas(resposta.data)[1:]).split())
    esperados = [carteira, indicacao, paciente['nome'], plano['codigo_prestador'], plano['nome_contratado'],
                 plano['operadora'], tuss.DESCRICOES['40310418'], itens[1]['titulo'].strip()]
    for esperado in esperados:
        assert ' '.join(esperado.split()) in texto, esperado
    assert '…' not in texto


def test_so_o_que_nao_cabe_em_letra_legivel_e_abreviado_e_avisa():
    pdf = pdf_minutas._Minuta('SOLICITAÇÃO DE EXAMES LABORATORIAIS')
    pdf.em_guia = True
    pdf.add_page(orientation='L')
    pdf_minutas._encaixar(pdf, 10, 10, 20, 5, 'W' * 300)
    texto = ''.join(_paginas(pdf.bytes())[0].split())
    assert texto.endswith('…') and len(texto) < 300


# --- Plano de saúde na identificação do paciente (tela) ------------------------

def _tela():
    from pathlib import Path
    return (Path(__file__).resolve().parents[1] / 'intelligent-tools.html').read_text(encoding='utf-8')


def test_plano_e_carteira_ficam_na_identificacao_e_nao_vao_para_o_motor():
    tela = _tela()
    secao = tela[tela.index('id="s-identificacao"'):tela.index('aria-labelledby="s-clinicos"')]
    assert 'id="pacientePlano"' in secao and 'id="pacienteCarteira"' in secao
    # sem atributo `name`, o FormData não leva o campo: plano e carteira não entram no cálculo das recomendações
    for campo in re.findall(r'<(?:select|input)[^>]*data-plano[^>]*>', secao):
        assert ' name=' not in campo, campo
    assert len(re.findall(r'<(?:select|input)[^>]*data-plano[^>]*>', secao)) == 2
    # a lista de planos não vira botões (as opções vêm do cadastro do médico)
    assert "checkupForm.querySelectorAll('select:not([data-plano])')" in tela


def test_troca_de_paciente_pede_confirmacao_do_plano_antes_da_guia():
    tela = _tela()
    invalidar = re.search(r'function invalidarResultados\(evento\) \{(.*?)\n        \}', tela, re.S).group(1)
    # dado clínico mudou com resultado na tela: o plano fica, mas passa a pedir confirmação
    assert invalidar.index('limparResultados()') < invalidar.index('pedirConfirmacaoDoPlano()')
    # mexer no plano ou na carteira não apaga o resultado; nome novo com resultado na tela pede confirmação
    isento = re.search(r'function semEfeitoNasRecomendacoes\(evento\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert "campo.hasAttribute('data-plano')" in isento and 'pedirConfirmacaoDoPlano()' in isento
    # o resultado não leva mais o plano embora sozinho
    limpar = re.search(r'function limparResultados\(\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert 'limparGuia' not in limpar
    # a guia não sai enquanto o plano estiver por confirmar
    gerar = tela[tela.index("document.getElementById('acrescimoGerar').addEventListener('click'"):]
    assert gerar.index('if (guia && planoAConfirmar)') < gerar.index('fecharDialogo();') < gerar.index('baixarPdf(')
    # editar o plano ou a carteira vale como confirmação; "Limpar" zera os dois
    assert re.search(r'function planoEditado\(origem\) \{.*?planoAConfirmar = false;', tela, re.S)
    assert "['planoLimpar', 'guiaLimpar'].forEach(id => document.getElementById(id).addEventListener('click', limparGuia));" in tela


def test_dialogo_preenche_tambem_a_identificacao_se_a_primeira_carga_falhou():
    """Se a lista de planos só carregou no diálogo, o seletor da identificação tem de ganhar as mesmas opções:
    sem elas, escolher o plano no diálogo deixava a identificação vazia e a carteira era apagada a cada tecla."""
    tela = _tela()
    guia = re.search(r'async function prepararGuia\(categoria\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert guia.index('aplicarPlanosNaIdentificacao(planos)') < guia.index("preencherPlanos(seletor, planos.lista)")
