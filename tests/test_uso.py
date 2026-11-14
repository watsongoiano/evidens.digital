"""Painel de uso (/analytics): eventos gravados no banco, por usuário, sem dado de paciente."""
import itertools
from datetime import datetime

import pytest

from conftest import SENHA_DE_TESTE
from src.utils import uso

_seq = itertools.count(1)
PACIENTE = {'nome': 'Paciente de Teste', 'idade': '50', 'sexo': 'feminino'}
CHECKUP = dict(idade=50, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
               comorbidades=[], historia_familiar=[], medicacoes=[])


def _medico(app, contas):
    n = next(_seq)
    u = contas.criar(f'uso{n}@exemplo.test', f'Dr. Uso {n}', f'CRM-GO 7{n:04d}', 'medico', SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def _linha(admin, uid):
    return next(l for l in admin.get('/api/analytics/stats').get_json()['usuarios'] if l['id'] == uid)


def test_cada_acao_do_medico_e_contada_no_nome_dele(app, contas, admin):
    cliente, u = _medico(app, contas)
    assert cliente.get('/intelligent-tools').status_code == 200
    for _ in range(2):
        assert cliente.post('/api/checkup-intelligent', json=CHECKUP).status_code == 200
    itens = [{'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}]
    assert cliente.post('/api/gerar-pdf-exames-laboratoriais', json={'dados_paciente': PACIENTE, 'recomendacoes': itens}).status_code == 200
    imagem = [{'titulo': 'Radiografia de tórax', 'categoria': 'imagem'}]
    assert cliente.post('/api/gerar-pdf-exames-imagem', json={'dados_paciente': PACIENTE, 'recomendacoes': imagem}).status_code == 200
    linha = _linha(admin, u['id'])
    assert linha['nome'] == u['nome'] and linha['email'] == u['email'] and linha['perfil'] == 'medico'
    assert linha['total'] == linha['ultimos_30_dias'] == linha['mes'] == linha['sete_dias'] == linha['hoje']
    assert {k: v for k, v in linha['total'].items() if v} == {
        'login': 1, 'acesso': 1, 'checkup': 2, 'pdf_laboratorio': 1, 'pdf_imagem': 1}
    datetime.fromisoformat(linha['ultima_atividade'])


def test_guia_do_plano_e_contada(app, contas, admin):
    cliente, u = _medico(app, contas)
    plano = dict(operadora='CASSI', codigo_prestador='1', nome_contratado='Clínica')
    cid = cliente.post('/api/auth/credenciamentos', json=plano).get_json()['credenciamento']['id']
    itens = [{'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}]
    cliente.post('/api/gerar-pdf-exames-laboratoriais',
                 json={'dados_paciente': PACIENTE, 'recomendacoes': itens, 'guia': {'credenciamento_id': cid}})
    total = _linha(admin, u['id'])['total']
    assert total['pdf_laboratorio'] == 1 and total['guia_plano'] == 1


def test_falha_nao_conta(app, contas, admin):
    """Pedido recusado (dados inválidos) não vira check-up nem PDF."""
    cliente, u = _medico(app, contas)
    assert cliente.post('/api/checkup-intelligent', json={'idade': 'x'}).status_code == 400
    assert cliente.post('/api/gerar-pdf-exames-laboratoriais', json={'dados_paciente': PACIENTE, 'recomendacoes': 'x'}).status_code == 400
    total = _linha(admin, u['id'])['total']
    assert total['checkup'] == 0 and total['pdf_laboratorio'] == 0


def test_visita_a_home_conta_sem_medico_e_robo_nao_conta(app, admin):
    antes = admin.get('/api/analytics/stats').get_json()['periodos']['total']['visita']
    navegador = app.test_client()
    navegador.get('/', headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'})
    navegador.get('/', headers={'User-Agent': 'WhatsApp/2.23.20.0'})
    navegador.get('/', headers={'User-Agent': 'Googlebot/2.1'})
    dados = admin.get('/api/analytics/stats').get_json()
    assert dados['periodos']['total']['visita'] == antes + 1
    assert dados['periodos']['hoje']['visita'] >= 1


def test_periodos_e_serie_usam_o_horario_de_brasilia(app, contas):
    """Evento às 23h30 de Brasília (02h30 UTC do dia seguinte) é do dia em Brasília."""
    from datetime import timedelta
    u = contas.criar('fuso@exemplo.test', 'Dra. Fuso', 'CRM-GO 99990', 'medico', SENHA_DE_TESTE)
    agora = datetime(2030, 3, 10, 12, 0, tzinfo=uso.FUSO)
    noite = datetime(2030, 3, 9, 23, 30, tzinfo=uso.FUSO)
    uso.registrar('checkup', u, quando=noite.timestamp())
    uso.registrar('checkup', u, quando=agora.timestamp())
    uso.registrar('checkup', u, quando=(agora - timedelta(days=40)).timestamp())
    dados = uso.resumo(agora=agora)
    serie = {d['dia']: d['checkup'] for d in dados['serie']}
    assert serie['2030-03-09'] >= 1 and serie['2030-03-10'] >= 1 and '2030-01-29' not in serie
    linha = next(l for l in dados['usuarios'] if l['id'] == u['id'])
    assert linha['total']['checkup'] == 3 and linha['ultimos_30_dias']['checkup'] == 2
    assert linha['hoje']['checkup'] == 1 and linha['sete_dias']['checkup'] == 2 and linha['mes']['checkup'] == 2
    assert dados['periodos']['hoje']['checkup'] >= 1


def test_registrar_nunca_quebra_a_requisicao(monkeypatch):
    def quebra():
        raise RuntimeError('banco fora')
    monkeypatch.setattr(uso.contas, '_conexao', quebra)
    uso.registrar('checkup', {'id': 1})          # não levanta
    uso.registrar('tipo-que-nao-existe', None)   # ignorado


def test_painel_nao_grava_nem_devolve_dado_de_paciente(app, contas, admin):
    cliente, u = _medico(app, contas)
    cliente.post('/api/checkup-intelligent', json=dict(CHECKUP, nome_paciente='Fulana Paciente Secreta'))
    cliente.post('/api/gerar-pdf-exames-laboratoriais', json={
        'dados_paciente': dict(PACIENTE, nome='Fulana Paciente Secreta'),
        'recomendacoes': [{'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}]})
    resposta = admin.get('/api/analytics/stats').get_data(as_text=True)
    assert 'Fulana' not in resposta and 'Hemograma' not in resposta
    with contas._conexao() as executar:
        colunas = [c[1] for c in executar('PRAGMA table_info(eventos_uso)').fetchall()]
    assert colunas == ['id', 'usuario_id', 'tipo', 'criado_em']


@pytest.mark.parametrize('ua, robo', [('Mozilla/5.0 (Windows NT 10.0) Chrome/120', False), ('', True),
                                      ('facebookexternalhit/1.1', True), ('vercel-screenshot', True), ('curl/8.0', True)])
def test_eh_robo(ua, robo):
    assert uso.eh_robo(ua) is robo


def test_tabela_por_medico_usa_o_mesmo_periodo_dos_cartoes(contas):
    """No dia 2, "Este mês" não inclui o fim do mês anterior (os últimos 30 dias incluem)."""
    u = contas.criar('mes@exemplo.test', 'Dra. Mês', 'CRM-GO 99991', 'medico', SENHA_DE_TESTE)
    agora = datetime(2031, 5, 2, 12, 0, tzinfo=uso.FUSO)
    uso.registrar('pdf_vacinas', u, quando=datetime(2031, 4, 28, 10, 0, tzinfo=uso.FUSO).timestamp())
    uso.registrar('pdf_vacinas', u, quando=datetime(2031, 5, 1, 10, 0, tzinfo=uso.FUSO).timestamp())
    linha = next(l for l in uso.resumo(agora=agora)['usuarios'] if l['id'] == u['id'])
    assert linha['mes']['pdf_vacinas'] == 1 and linha['ultimos_30_dias']['pdf_vacinas'] == 2
    assert linha['sete_dias']['pdf_vacinas'] == 2 and linha['hoje']['pdf_vacinas'] == 0
