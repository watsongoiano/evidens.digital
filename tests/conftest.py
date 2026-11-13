"""Configuração comum dos testes.

Os testes exercitam a aplicação pela mesma entrada usada em produção
(`api/index.py`, apontada pelo `vercel.json`), e não pelos pontos de entrada
alternativos do repositório.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


SENHA_DE_TESTE = 'senha-de-teste-123'


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    import os
    # Contas em um arquivo SQLite descartável; chave de sessão própria dos testes.
    banco = tmp_path_factory.mktemp('contas') / 'contas.sqlite'
    os.environ['DATABASE_URL'] = f'sqlite:///{banco}'
    os.environ['SECRET_KEY'] = 'chave-apenas-para-os-testes'
    os.environ['SETUP_TOKEN'] = 'codigo-de-instalacao-dos-testes'
    os.environ.pop('VERCEL', None)
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location('evidens_api_index', RAIZ / 'api' / 'index.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.app.config.update(TESTING=True)
    return modulo.app


@pytest.fixture(scope='session')
def contas(app):
    from src.utils import contas as modulo
    return modulo


@pytest.fixture(scope='session')
def medica_aprovada(contas):
    u = contas.criar('medica@exemplo.test', 'Médica de Teste', 'CRM-GO 00000', 'medico', SENHA_DE_TESTE)
    return contas.definir_situacao(u['id'], 'aprovado')


def _entrar(cliente, email, senha=SENHA_DE_TESTE):
    return cliente.post('/api/auth/login', json={'email': email, 'senha': senha})


@pytest.fixture()
def anonimo(app):
    """Navegador sem sessão."""
    return app.test_client()


@pytest.fixture()
def client(app, medica_aprovada):
    """Navegador de uma médica com conta aprovada (o check-up inteiro exige login)."""
    cliente = app.test_client()
    assert _entrar(cliente, medica_aprovada['email']).status_code == 200
    return cliente


@pytest.fixture(scope='session')
def administrador(contas):
    return contas.criar('admin@exemplo.test', 'Administrador de Teste', 'CRM-GO 11111', 'medico', SENHA_DE_TESTE, administrador=True)


@pytest.fixture()
def admin(app, administrador):
    """Navegador do administrador."""
    cliente = app.test_client()
    assert _entrar(cliente, administrador['email']).status_code == 200
    return cliente
