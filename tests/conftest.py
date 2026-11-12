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


@pytest.fixture(scope='session')
def app():
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location('evidens_api_index', RAIZ / 'api' / 'index.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo.app.config.update(TESTING=True)
    return modulo.app


@pytest.fixture()
def client(app):
    return app.test_client()
