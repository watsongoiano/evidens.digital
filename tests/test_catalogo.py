"""Catálogo de itens para acrescentar aos pedidos."""
import json

from src.utils import catalogo


def test_catalogo_do_motor_esta_atualizado(app, medica_aprovada):
    """src/data/catalogo_motor.json precisa refletir o motor (rode scripts/gerar_catalogo.py)."""
    import io
    from contextlib import redirect_stdout
    from conftest import SENHA_DE_TESTE

    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': 'medica@exemplo.test', 'senha': SENHA_DE_TESTE}).status_code == 200

    class _App:
        def test_client(self):
            return cliente

    with redirect_stdout(io.StringIO()):
        atual = catalogo.titulos_do_motor(_App())
    gravado = json.loads(catalogo.ARQUIVO_DO_MOTOR.read_text(encoding='utf-8'))
    assert gravado == atual, 'Rode: python scripts/gerar_catalogo.py'


def test_catalogo_une_motor_e_extras_sem_repetir(client):
    dados = client.get('/api/catalogo').get_json()
    assert set(dados) == {'laboratorio', 'imagem', 'vacina'}
    for categoria, itens in dados.items():
        assert itens == sorted(itens, key=str.lower)
        assert len({i.lower() for i in itens}) == len(itens), categoria
    assert 'Hemograma completo' in dados['laboratorio']
    assert 'Glicose, soro' in dados['laboratorio']
    assert 'Tríplice Viral - SCR (Priorix® ou M-M-R® II)' in dados['vacina']


def test_catalogo_exige_login(anonimo):
    assert anonimo.get('/api/catalogo').status_code == 401


def test_gerador_do_catalogo_nao_usa_o_banco_configurado(tmp_path):
    """O gerador cria e aprova uma conta para varrer o motor: isso só pode acontecer num banco descartável."""
    import os
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    banco = tmp_path / 'banco-real.sqlite'
    sqlite3.connect(banco).close()
    copia = tmp_path / 'repo'
    import shutil
    shutil.copytree(raiz, copia, ignore=shutil.ignore_patterns('.git', 'node_modules', '__pycache__'))
    ambiente = {**os.environ, 'DATABASE_URL': f'sqlite:///{banco}', 'POSTGRES_URL': f'sqlite:///{banco}'}
    subprocess.run([sys.executable, str(copia / 'scripts' / 'gerar_catalogo.py')], env=ambiente,
                   check=True, capture_output=True, timeout=600)
    tabelas = sqlite3.connect(banco).execute("select name from sqlite_master where type='table'").fetchall()
    assert tabelas == []   # nada foi criado no banco "real"
