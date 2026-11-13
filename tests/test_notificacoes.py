"""Aviso por e-mail ao administrador a cada novo pedido de conta."""
import json
import urllib.error

import pytest

from conftest import SENHA_DE_TESTE
from src.utils import notificacoes


class _Resposta:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture()
def resend(monkeypatch, contas):
    """Liga o aviso e captura o que seria enviado à Resend (o banco de teste é compartilhado: zera a contagem da hora)."""
    enviados = []

    def falso(pedido, timeout=None):
        enviados.append({'url': pedido.full_url, 'cabecalhos': dict(pedido.header_items()),
                         'corpo': json.loads(pedido.data.decode('utf-8')), 'timeout': timeout})
        return _Resposta()

    monkeypatch.setattr(contas, 'criados_desde', lambda instante: 1)
    monkeypatch.setenv('RESEND_API_KEY', 're_teste_123')
    monkeypatch.delenv('AVISO_CADASTRO_PARA', raising=False)
    monkeypatch.delenv('AVISO_CADASTRO_DE', raising=False)
    monkeypatch.setattr(notificacoes.urllib.request, 'urlopen', falso)
    return enviados


def _cadastrar(anonimo, email, **extra):
    dados = dict(email=email, nome='Pessoa Nova', perfil='medico', crm_uf='GO', crm_numero='4321', senha=SENHA_DE_TESTE)
    dados.update(extra)
    return anonimo.post('/api/auth/cadastro', json=dados)


def test_sem_chave_nada_e_enviado_e_o_cadastro_segue(anonimo, monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    chamadas = []
    monkeypatch.setattr(notificacoes.urllib.request, 'urlopen', lambda *a, **k: chamadas.append(1))
    assert _cadastrar(anonimo, 'semchave@exemplo.test').status_code == 202
    assert not chamadas and not notificacoes.configurado()


def test_novo_pedido_avisa_o_administrador(anonimo, administrador, resend):
    assert _cadastrar(anonimo, 'aviso1@exemplo.test').status_code == 202
    assert len(resend) == 1
    envio = resend[0]
    assert envio['url'] == 'https://api.resend.com/emails' and envio['timeout'] == notificacoes.TEMPO_LIMITE
    assert envio['cabecalhos']['Authorization'] == 'Bearer re_teste_123'
    corpo = envio['corpo']
    assert corpo['to'] == [administrador['email']] and corpo['from'] == notificacoes.REMETENTE_PADRAO
    assert 'Pessoa Nova' in corpo['subject']
    for trecho in ('Pessoa Nova', 'Médico(a)', 'CRM-GO 4321', 'aviso1@exemplo.test', 'https://evidens.life/admin'):
        assert trecho in corpo['text'], trecho
    assert SENHA_DE_TESTE not in json.dumps(corpo)


def test_email_ja_cadastrado_nao_gera_aviso(anonimo, administrador, resend):
    _cadastrar(anonimo, 'aviso2@exemplo.test')
    _cadastrar(anonimo, 'aviso2@exemplo.test')
    assert len(resend) == 1


def test_destinatario_e_remetente_por_variavel(anonimo, administrador, resend, monkeypatch):
    monkeypatch.setenv('AVISO_CADASTRO_PARA', 'a@exemplo.test, b@exemplo.test')
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <avisos@exemplo.test>')
    _cadastrar(anonimo, 'aviso3@exemplo.test')
    assert resend[0]['corpo']['to'] == ['a@exemplo.test', 'b@exemplo.test']
    assert resend[0]['corpo']['from'] == 'Evidēns <avisos@exemplo.test>'


def test_falha_no_envio_nao_impede_o_cadastro(anonimo, administrador, monkeypatch, contas):
    monkeypatch.setenv('RESEND_API_KEY', 're_teste_123')

    def quebra(*a, **k):
        raise urllib.error.URLError('sem rede')

    monkeypatch.setattr(notificacoes.urllib.request, 'urlopen', quebra)
    assert _cadastrar(anonimo, 'aviso4@exemplo.test').status_code == 202
    assert any(u['email'] == 'aviso4@exemplo.test' for u in contas.listar())


def test_nome_com_quebra_de_linha_nao_forja_campos_no_email():
    assunto, texto = notificacoes.mensagem_de_cadastro(
        {'nome': 'Fulano\nE-mail: outro@exemplo.test', 'perfil': 'medico', 'registro': 'CRM-GO 1', 'email': 'f@exemplo.test'},
        'https://evidens.life/admin')
    assert '\n' not in assunto
    assert texto.count('\nE-mail: ') == 1


def test_painel_mostra_o_estado_e_envia_teste(admin, administrador, resend):
    estado = admin.get('/api/admin/aviso').get_json()
    assert estado == {'configurado': True, 'destinatarios': [administrador['email']], 'boas_vindas': False}
    r = admin.post('/api/admin/aviso/teste', json={})
    assert r.status_code == 200 and r.get_json()['destinatarios'] == [administrador['email']]
    assert 'teste' in resend[-1]['corpo']['subject']


def test_teste_sem_chave_explica_o_motivo(admin, monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    r = admin.post('/api/admin/aviso/teste', json={})
    assert r.status_code == 502 and 'RESEND_API_KEY' in r.get_json()['error']


def test_aviso_e_restrito_ao_administrador(client, anonimo):
    assert client.get('/api/admin/aviso').status_code == 403
    assert client.post('/api/admin/aviso/teste', json={}).status_code == 403
    assert anonimo.get('/api/admin/aviso').status_code in (401, 403)


def test_enxurrada_de_cadastros_nao_lota_a_caixa_do_administrador(anonimo, administrador, resend, contas, monkeypatch):
    """Até o limite por hora, um aviso por pedido; depois, um único aviso de volume e mais nada."""
    monkeypatch.setattr(contas, 'criados_desde', lambda instante: contador[0])
    contador = [0]
    for n in range(1, notificacoes.LIMITE_POR_HORA + 5):
        contador[0] = n
        assert _cadastrar(anonimo, f'enxurrada{n}@exemplo.test').status_code == 202
    assert len(resend) == notificacoes.LIMITE_POR_HORA + 1
    assert 'muitos pedidos' in resend[-1]['corpo']['subject']
    assert all('novo pedido de conta' in e['corpo']['subject'] for e in resend[:-1])


def test_contagem_de_cadastros_recentes(contas):
    import time
    antes = contas.criados_desde(time.time() - 3600)
    contas.criar('recente@exemplo.test', 'Pessoa Recente', 'CRM-GO 77', 'medico', SENHA_DE_TESTE)
    assert contas.criados_desde(time.time() - 3600) == antes + 1
    assert contas.criados_desde(time.time() + 60) == 0


# ---------------------------------------------------------------------------
# Boas-vindas a quem pede a conta
# ---------------------------------------------------------------------------
def test_boas_vindas_desligadas_sem_remetente_do_dominio(anonimo, administrador, resend):
    """Com o remetente padrão da Resend só sai o aviso ao administrador."""
    assert not notificacoes.boas_vindas_ligadas()
    _cadastrar(anonimo, 'bv0@exemplo.test')
    assert [e['corpo']['to'] for e in resend] == [[administrador['email']]]


def test_boas_vindas_vao_para_quem_se_cadastrou(anonimo, administrador, resend, monkeypatch):
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    monkeypatch.setenv('EMAIL_CONTATO', 'retorno@exemplo.test')
    assert _cadastrar(anonimo, 'bv1@exemplo.test', nome='Maria Nova Silva').status_code == 202
    assert len(resend) == 2
    bv = next(e['corpo'] for e in resend if e['corpo']['to'] == ['bv1@exemplo.test'])
    assert bv['subject'] == 'Bem-vindo(a) ao Evidēns' and bv['from'] == 'Evidēns <contato@exemplo.test>'
    assert bv['reply_to'] == 'retorno@exemplo.test'
    for trecho in ('Olá, Maria.', 'fase de desenvolvimento', 'feedback', 'https://evidens.life/login',
                   'https://evidens.life/contact ou pelo e-mail retorno@exemplo.test', 'conferir o cadastro',
                   'cerca de 30% dos exames laboratoriais', 'PLOS ONE, 2013',
                   'https://hms.harvard.edu/news/unnecessary-testing', 'Criador e responsável técnico'):
        assert trecho in bv['text'], trecho
    assert SENHA_DE_TESTE not in bv['text'] and administrador['email'] not in bv['text']


def test_boas_vindas_sem_email_de_contato_mostram_so_a_pagina(monkeypatch):
    monkeypatch.delenv('EMAIL_CONTATO', raising=False)
    _, texto = notificacoes.mensagem_de_boas_vindas({'nome': 'Ana'}, 'https://evidens.life')
    assert 'https://evidens.life/contact\n' in texto and 'pelo e-mail' not in texto


def test_email_ja_cadastrado_nao_recebe_boas_vindas(anonimo, administrador, resend, monkeypatch):
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    _cadastrar(anonimo, 'bv2@exemplo.test')
    antes = len(resend)
    _cadastrar(anonimo, 'bv2@exemplo.test')
    assert len(resend) == antes


def test_boas_vindas_respeitam_o_limite_por_hora(anonimo, administrador, resend, contas, monkeypatch):
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    monkeypatch.setattr(contas, 'criados_desde', lambda instante: notificacoes.LIMITE_POR_HORA + 3)
    _cadastrar(anonimo, 'bv3@exemplo.test')
    assert resend == []


def test_painel_informa_e_testa_as_boas_vindas(admin, administrador, resend, monkeypatch):
    assert admin.get('/api/admin/aviso').get_json()['boas_vindas'] is False
    assert admin.post('/api/admin/boas-vindas/teste', json={}).status_code == 502
    monkeypatch.setenv('AVISO_CADASTRO_DE', 'Evidēns <contato@exemplo.test>')
    assert admin.get('/api/admin/aviso').get_json()['boas_vindas'] is True
    r = admin.post('/api/admin/boas-vindas/teste', json={})
    assert r.status_code == 200 and r.get_json()['destinatarios'] == [administrador['email']]
    assert resend[-1]['corpo']['subject'] == 'Bem-vindo(a) ao Evidēns'


def test_teste_de_boas_vindas_e_restrito_ao_administrador(client):
    assert client.post('/api/admin/boas-vindas/teste', json={}).status_code == 403
