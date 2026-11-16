"""Comunicado de novidades: texto, envio em lote uma vez por conta, cron protegido e botões do administrador."""
from datetime import datetime, timezone

import pytest

from conftest import SENHA_DE_TESTE
from src.utils import comunicados, notificacoes
from test_notificacoes import resend  # noqa: F401  (fixture)

CHAVE = next(iter(comunicados.COMUNICADOS))


@pytest.fixture()
def aprovados(contas):
    """Marca todas as contas existentes como já atendidas e cria duas aprovadas, uma pendente e uma bloqueada."""
    for u in contas.sem_comunicado(CHAVE):
        contas.reservar_comunicado(u['id'], CHAVE)
    criados = {}
    for chave, situacao in (('a', 'aprovado'), ('b', 'aprovado'), ('pendente', 'pendente'), ('bloqueada', 'bloqueado')):
        n = len(contas.listar())
        u = contas.criar(f'novidades-{chave}-{n}@exemplo.test', f'Pessoa {chave.capitalize()}', 'CRM-GO 7', 'medico', SENHA_DE_TESTE)
        criados[chave] = contas.definir_situacao(u['id'], situacao)
    return criados


def test_texto_tem_boas_vindas_em_uma_linha_e_as_novidades():
    assunto, texto = notificacoes.mensagem_de_novidades({'nome': 'Ana Souza'}, 'https://evidens.life')
    linhas = texto.split('\n')
    assert assunto == 'Evidēns: o que há de novo'
    assert linhas[0] == 'Olá, Ana.' and linhas[2].startswith('Que bom ter você no Evidēns!')
    for trecho in ('CKD-EPI 2021', 'KFRE', 'TISS 4', 'colonoscopia e FIT', 'https://evidens.life/login',
                   'fase de desenvolvimento'):
        assert trecho in texto, trecho


def test_envio_em_lote_uma_vez_so_para_aprovados(contas, aprovados, resend, monkeypatch):
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    enviados, falha, restantes = comunicados.enviar(CHAVE, 'https://evidens.life', contas)
    assert (enviados, falha, restantes) == (2, None, 0)
    assert len(resend) == 1 and resend[0]['url'].endswith('/emails/batch')
    destinos = {m['to'][0] for m in resend[0]['corpo']}
    assert destinos == {aprovados['a']['email'], aprovados['b']['email']}
    # de novo: ninguém recebe duas vezes
    assert comunicados.enviar(CHAVE, 'https://evidens.life', contas)[0] == 0 and len(resend) == 1


def test_falha_devolve_as_contas_a_fila(contas, aprovados, monkeypatch):
    monkeypatch.setattr(notificacoes, 'enviar_lote', lambda mensagens: (False, 'HTTP 500'))
    enviados, falha, restantes = comunicados.enviar(CHAVE, 'https://evidens.life', contas)
    assert enviados == 0 and falha == 'HTTP 500' and restantes == 2


def test_cron_exige_o_segredo(anonimo, monkeypatch):
    monkeypatch.delenv('CRON_SECRET', raising=False)
    assert anonimo.get('/api/cron/comunicados').status_code == 401
    monkeypatch.setenv('CRON_SECRET', 'segredo-de-teste')
    assert anonimo.get('/api/cron/comunicados').status_code == 401
    assert anonimo.get('/api/cron/comunicados', headers={'Authorization': 'Bearer outro'}).status_code == 401


def test_cron_so_envia_depois_da_hora(anonimo, contas, aprovados, resend, monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'segredo-de-teste')
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    cabecalho = {'Authorization': 'Bearer segredo-de-teste'}
    quando, montar = comunicados.COMUNICADOS[CHAVE]
    monkeypatch.setitem(comunicados.COMUNICADOS, CHAVE, (datetime(2999, 1, 1, tzinfo=timezone.utc), montar))
    r = anonimo.get('/api/cron/comunicados', headers=cabecalho).get_json()
    assert r == {'ok': True, 'comunicados': {}} and resend == []
    monkeypatch.setitem(comunicados.COMUNICADOS, CHAVE, (datetime(2000, 1, 1, tzinfo=timezone.utc), montar))
    r = anonimo.get('/api/cron/comunicados', headers=cabecalho).get_json()
    assert r['comunicados'][CHAVE]['enviados'] == 2 and r['comunicados'][CHAVE]['restantes'] == 0


def test_botoes_do_administrador(admin, client, administrador, aprovados, resend, monkeypatch):
    assert client.post('/api/admin/comunicado/teste', json={}).status_code == 403
    assert client.post('/api/admin/comunicado', json={}).status_code == 403
    assert admin.post('/api/admin/comunicado/teste', json={}).status_code == 502   # sem remetente do domínio
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    estado = admin.get('/api/admin/aviso').get_json()['comunicado']
    assert estado['chave'] == CHAVE and estado['pendentes'] == 2
    r = admin.post('/api/admin/comunicado/teste', json={})
    assert r.status_code == 200 and resend[-1]['corpo']['to'] == [administrador['email']]
    assert admin.get('/api/admin/aviso').get_json()['comunicado']['pendentes'] == 2   # o teste não gasta a fila
    r = admin.post('/api/admin/comunicado', json={}).get_json()
    assert r['enviados'] == 2 and r['restantes'] == 0


def test_cron_configurado_na_vercel():
    import json
    from conftest import RAIZ
    crons = json.loads((RAIZ / 'vercel.json').read_text(encoding='utf-8'))['crons']
    assert {'path': '/api/cron/comunicados', 'schedule': '0 10 * * *'} in crons
