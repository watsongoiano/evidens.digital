"""Área de acesso: quem entra, quem não entra e o que cada um alcança."""
import itertools

import pytest

from conftest import SENHA_DE_TESTE

_seq = itertools.count(1)
PACIENTE = dict(idade=52, sexo='masculino', tabagismo='nunca')


def _novo(anonimo, **extra):
    """Envia um cadastro novo e devolve (e-mail, resposta)."""
    email = f'pessoa{next(_seq)}@exemplo.test'
    dados = dict(email=email, nome='Pessoa de Teste', registro='CRM-GO 22222', perfil='medico', senha=SENHA_DE_TESTE)
    dados.update(extra)
    return dados['email'], anonimo.post('/api/auth/cadastro', json=dados)


def _entrar(cliente, email, senha=SENHA_DE_TESTE):
    return cliente.post('/api/auth/login', json={'email': email, 'senha': senha})


def _id(contas, email):
    return next(u['id'] for u in contas.listar() if u['email'] == email)


# --- Sem login, nada do check-up ---------------------------------------------

@pytest.mark.parametrize('rota', ['/api/checkup-intelligent', '/api/gerar-pdf-exames-laboratoriais',
                                  '/api/gerar-pdf-exames-imagem', '/api/gerar-pdf-vacinas'])
def test_api_do_checkup_exige_login(anonimo, rota):
    resposta = anonimo.post(rota, json=PACIENTE)
    assert resposta.status_code == 401
    assert 'recommendations' not in resposta.get_json()


@pytest.mark.parametrize('rota', ['/intelligent-tools', '/conta', '/admin', '/analytics'])
def test_paginas_internas_mandam_para_o_login(anonimo, rota):
    resposta = anonimo.get(rota)
    assert resposta.status_code == 302 and resposta.headers['Location'].startswith('/login')


@pytest.mark.parametrize('rota', ['/', '/login', '/cadastro', '/contact', '/configurar'])
def test_paginas_publicas_abrem_sem_login(anonimo, rota):
    assert anonimo.get(rota).status_code == 200


def test_painel_de_uso_e_lista_de_usuarios_sao_so_do_administrador(anonimo, client, admin):
    for rota in ('/api/analytics/stats', '/api/analytics/full', '/api/admin/usuarios'):
        assert anonimo.get(rota).status_code == 401, rota
        assert client.get(rota).status_code == 403, rota
        assert admin.get(rota).status_code == 200, rota
    assert client.get('/admin').status_code == 302


# --- Cadastro com aprovação ---------------------------------------------------

def test_cadastro_fica_pendente_e_so_entra_depois_de_aprovado(anonimo, admin, contas):
    email, resposta = _novo(anonimo)
    assert resposta.status_code == 202
    assert _entrar(anonimo, email).status_code == 403                      # senha certa, conta pendente
    assert anonimo.post('/api/checkup-intelligent', json=PACIENTE).status_code == 401

    assert admin.post(f'/api/admin/usuarios/{_id(contas, email)}/aprovar').status_code == 200
    assert _entrar(anonimo, email).status_code == 200
    assert anonimo.post('/api/checkup-intelligent', json=PACIENTE).status_code == 200
    assert anonimo.get('/intelligent-tools').status_code == 200


def test_cadastro_repetido_responde_igual_e_nao_troca_a_senha(anonimo, contas):
    email, primeira = _novo(anonimo)
    segunda = anonimo.post('/api/auth/cadastro', json=dict(email=email.upper(), nome='Outra Pessoa', registro='CRM-SP 1',
                                                             perfil='medico', senha='outra-senha-bem-longa'))
    assert (segunda.status_code, segunda.get_json()) == (primeira.status_code, primeira.get_json())
    u = contas.por_id(_id(contas, email))
    assert u['nome'] == 'Pessoa de Teste' and contas.senha_confere(u, SENHA_DE_TESTE)


@pytest.mark.parametrize('extra', [dict(email='sem-arroba'), dict(senha='curta'), dict(perfil='administrador'),
                                   dict(nome=''), dict(registro='')])
def test_cadastro_invalido_e_recusado(anonimo, extra):
    _, resposta = _novo(anonimo, **extra)
    assert resposta.status_code == 400 and resposta.get_json()['erros']


def test_cadastro_nunca_cria_administrador(anonimo, contas):
    email, _ = _novo(anonimo, administrador=True, situacao='aprovado')
    u = contas.por_id(_id(contas, email))
    assert not u['administrador'] and u['situacao'] == 'pendente'


# --- Login ---------------------------------------------------------------------

def test_senha_errada_e_email_inexistente_respondem_igual(anonimo, medica_aprovada):
    errada = _entrar(anonimo, medica_aprovada['email'], 'senha-errada-000')
    inexistente = _entrar(anonimo, 'ninguem@exemplo.test', 'senha-errada-000')
    assert errada.status_code == inexistente.status_code == 401
    assert errada.get_json() == inexistente.get_json()


def test_muitas_senhas_erradas_bloqueiam_ate_a_senha_certa(anonimo, admin, contas):
    email, _ = _novo(anonimo)
    admin.post(f'/api/admin/usuarios/{_id(contas, email)}/aprovar')
    for _ in range(contas.MAX_FALHAS_POR_EMAIL):
        assert _entrar(anonimo, email, 'senha-errada-000').status_code == 401
    assert _entrar(anonimo, email).status_code == 429


def test_resposta_do_login_e_sessao_nao_expoem_a_senha(anonimo, medica_aprovada):
    resposta = _entrar(anonimo, medica_aprovada['email'])
    assert 'senha_hash' not in resposta.get_data(as_text=True)
    assert 'senha_hash' not in anonimo.get('/api/auth/eu').get_data(as_text=True)
    cookie = resposta.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie


def test_sair_encerra_a_sessao(client):
    assert client.post('/api/auth/logout').status_code == 200
    assert client.post('/api/checkup-intelligent', json=PACIENTE).status_code == 401


def test_envio_vindo_de_outro_site_e_recusado(client):
    resposta = client.post('/api/checkup-intelligent', json=PACIENTE, headers={'Origin': 'https://outro-site.example'})
    assert resposta.status_code == 403
    assert client.post('/api/checkup-intelligent', json=PACIENTE, headers={'Origin': 'http://localhost'}).status_code == 200


# --- Bloqueio e senha ------------------------------------------------------------

def test_bloquear_derruba_a_sessao_aberta(app, anonimo, admin, contas):
    email, _ = _novo(anonimo)
    uid = _id(contas, email)
    admin.post(f'/api/admin/usuarios/{uid}/aprovar')
    assert _entrar(anonimo, email).status_code == 200
    assert admin.post(f'/api/admin/usuarios/{uid}/bloquear').status_code == 200
    assert anonimo.post('/api/checkup-intelligent', json=PACIENTE).status_code == 401
    assert _entrar(anonimo, email).status_code == 403


def test_trocar_a_senha_derruba_as_outras_sessoes(app, anonimo, admin, contas):
    email, _ = _novo(anonimo)
    admin.post(f'/api/admin/usuarios/{_id(contas, email)}/aprovar')
    outro = app.test_client()
    assert _entrar(anonimo, email).status_code == 200 and _entrar(outro, email).status_code == 200

    assert anonimo.post('/api/auth/senha', json=dict(senha_atual='errada-errada', nova_senha='nova-senha-123456')).status_code == 400
    assert anonimo.post('/api/auth/senha', json=dict(senha_atual=SENHA_DE_TESTE, nova_senha='curta')).status_code == 400
    assert anonimo.post('/api/auth/senha', json=dict(senha_atual=SENHA_DE_TESTE, nova_senha='nova-senha-123456')).status_code == 200

    assert anonimo.get('/api/auth/eu').get_json()['usuario']['email'] == email      # quem trocou continua
    assert outro.post('/api/checkup-intelligent', json=PACIENTE).status_code == 401  # a outra sessão caiu
    assert _entrar(outro, email).status_code == 401
    assert _entrar(outro, email, 'nova-senha-123456').status_code == 200


def test_senha_temporaria_gerada_pelo_administrador(app, anonimo, admin, contas):
    email, _ = _novo(anonimo)
    uid = _id(contas, email)
    admin.post(f'/api/admin/usuarios/{uid}/aprovar')
    temporaria = admin.post(f'/api/admin/usuarios/{uid}/redefinir-senha').get_json()['senha_temporaria']
    assert len(temporaria) >= 12
    assert _entrar(anonimo, email).status_code == 401
    assert _entrar(app.test_client(), email, temporaria).status_code == 200


def test_administrador_nao_e_alterado_pelo_painel(admin, administrador):
    for acao in ('bloquear', 'aprovar', 'redefinir-senha'):
        assert admin.post(f"/api/admin/usuarios/{administrador['id']}/{acao}").status_code == 400


# --- Instalação (primeiro administrador) -------------------------------------------

def test_instalacao_exige_o_codigo_e_so_vale_sem_administrador(anonimo, administrador):
    dados = dict(nome='Intruso', email='intruso@exemplo.test', registro='CRM-GO 9', senha=SENHA_DE_TESTE)
    assert anonimo.post('/api/auth/configurar', json=dict(dados, codigo='errado')).status_code == 403
    assert anonimo.post('/api/auth/configurar', json=dados).status_code == 403
    # Com o código certo, mas já existe administrador:
    assert anonimo.post('/api/auth/configurar', json=dict(dados, codigo='codigo-de-instalacao-dos-testes')).status_code == 409


def test_instalacao_cria_o_administrador_em_banco_vazio(app, tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path / 'vazio.sqlite'}")
    cliente = app.test_client()
    dados = dict(nome='Responsável Técnico', email='rt@exemplo.test', registro='CRM-GO 1', senha=SENHA_DE_TESTE)
    monkeypatch.setenv('SETUP_TOKEN', '')
    assert cliente.post('/api/auth/configurar', json=dict(dados, codigo='')).status_code == 403   # sem código definido, nunca
    monkeypatch.setenv('SETUP_TOKEN', 'codigo-novo')
    resposta = cliente.post('/api/auth/configurar', json=dict(dados, codigo='codigo-novo'))
    assert resposta.status_code == 201 and resposta.get_json()['usuario']['administrador']
    assert cliente.get('/api/admin/usuarios').status_code == 200
    assert cliente.post('/api/auth/configurar', json=dict(dados, codigo='codigo-novo', email='b@exemplo.test')).status_code == 409


# --- Ambiente sem banco ou sem chave ---------------------------------------------------

def test_sem_banco_o_checkup_fica_fechado(app, monkeypatch):
    monkeypatch.delenv('DATABASE_URL')
    cliente = app.test_client()
    assert cliente.post('/api/checkup-intelligent', json=PACIENTE).status_code == 503
    assert cliente.post('/api/auth/login', json=dict(email='a@b.test', senha='x')).status_code == 503
    assert cliente.get('/intelligent-tools').status_code == 302
    assert cliente.get('/').status_code == 200


def test_chave_de_sessao_padrao_nao_vale_fora_dos_testes(app, monkeypatch):
    from src.routes import auth
    monkeypatch.setitem(app.config, 'SECRET_KEY', auth.CHAVE_PADRAO)
    monkeypatch.setitem(app.config, 'TESTING', False)
    assert app.test_client().post('/api/auth/login', json=dict(email='a@b.test', senha='x')).status_code == 503


def test_banco_nao_aceita_um_segundo_administrador(contas, administrador):
    """Mesmo sem a conferência da rota (duas instalações simultâneas), o banco recusa."""
    assert contas.criar('segundo@exemplo.test', 'Segundo Admin', 'CRM-GO 2', 'medico', SENHA_DE_TESTE, administrador=True) is None
    assert sum(1 for u in contas.listar() if u['administrador']) == 1


def test_rota_de_saude_do_banco(anonimo, monkeypatch):
    assert anonimo.get('/api/auth/saude').get_json() == {'ok': True}
    monkeypatch.setenv('DATABASE_URL', 'sqlite:////caminho/que/nao/existe/x.sqlite')
    assert anonimo.get('/api/auth/saude').status_code == 503


def test_crm_em_dois_campos_vira_registro_padronizado(anonimo, contas):
    r = anonimo.post('/api/auth/cadastro', json=dict(email='doiscampos@exemplo.test', nome='Pessoa de Teste', perfil='medico',
                                                     crm_uf='go', crm_numero='26.815', senha=SENHA_DE_TESTE))
    assert r.status_code == 202
    assert next(u for u in contas.listar() if u['email'] == 'doiscampos@exemplo.test')['registro'] == 'CRM-GO 26815'


@pytest.mark.parametrize('campos', [dict(crm_uf='XX', crm_numero='123'), dict(crm_uf='GO', crm_numero='abc'),
                                    dict(crm_uf='', crm_numero='')])
def test_crm_invalido_e_recusado(anonimo, campos):
    r = anonimo.post('/api/auth/cadastro', json=dict(email='ruim@exemplo.test', nome='Pessoa de Teste', perfil='residente',
                                                     senha=SENHA_DE_TESTE, **campos))
    assert r.status_code == 400


def test_estudante_informa_matricula(anonimo, contas):
    r = anonimo.post('/api/auth/cadastro', json=dict(email='aluna@exemplo.test', nome='Aluna de Teste', perfil='estudante',
                                                     registro='2023001 · UFG', senha=SENHA_DE_TESTE))
    assert r.status_code == 202
    assert next(u for u in contas.listar() if u['email'] == 'aluna@exemplo.test')['registro'] == '2023001 · UFG'


def test_depois_do_cadastro_a_pessoa_vai_para_o_login_com_o_aviso(anonimo):
    """O formulário de cadastro leva ao login; lá, o aviso de que a conta aguarda aprovação."""
    assert 'data-form="cadastro" data-destino="/login?cadastro=recebido"' in anonimo.get('/cadastro').get_data(as_text=True)
    assert anonimo.get('/login?cadastro=recebido').status_code == 200
    js = anonimo.get('/static/conta.js').get_data(as_text=True)
    assert "get('cadastro') === 'recebido'" in js and 'Cadastro recebido.' in js
