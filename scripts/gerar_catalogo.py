"""Gera src/data/catalogo_motor.json com os títulos que o motor recomenda.

Rode depois de mudar as recomendações do motor:  python scripts/gerar_catalogo.py
O teste tests/test_catalogo.py falha se o arquivo estiver desatualizado.
"""
import importlib.util
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(RAIZ / 'catalogo-tmp.sqlite'))
os.environ.setdefault('SECRET_KEY', 'chave-apenas-para-gerar-o-catalogo')

from src.utils import catalogo  # noqa: E402

spec = importlib.util.spec_from_file_location('evidens_api_index', RAIZ / 'api' / 'index.py')
modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modulo)
app = modulo.app
app.config.update(TESTING=True)

from src.utils import contas  # noqa: E402

usuario = contas.criar('catalogo@exemplo.test', 'Gerador do catálogo', 'CRM-GO 0', 'medico', 'senha-do-gerador-1')
if usuario:
    contas.definir_situacao(usuario['id'], 'aprovado')
cliente = app.test_client()
cliente.post('/api/auth/login', json={'email': 'catalogo@exemplo.test', 'senha': 'senha-do-gerador-1'})


class _App:
    def test_client(self):
        return cliente


with redirect_stdout(io.StringIO()):
    titulos = catalogo.titulos_do_motor(_App())

catalogo.ARQUIVO_DO_MOTOR.write_text(json.dumps(titulos, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
try:
    os.remove(RAIZ / 'catalogo-tmp.sqlite')
except FileNotFoundError:
    pass
print({c: len(v) for c, v in titulos.items()})
