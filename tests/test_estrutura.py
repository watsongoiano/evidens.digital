"""Estrutura do repositório: nada de código sem uso.

O repositório chegou a ter três pontos de entrada, três geradores de PDF e
cópias `.original`/`.new` de vários arquivos. Uma revisão externa tirou uma
conclusão errada sobre o comportamento em produção por ter lido uma dessas
telas antigas. Estes testes impedem que o acúmulo recomece.
"""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / 'api' / 'index.py'

# Código que não faz parte da aplicação em produção, mantido de propósito.
FERRAMENTAS = {
    'scripts/gerar_catalogo.py',   # gera src/data/catalogo_motor.json
    'scripts/gerar_listas.py',     # regera as listas com busca de intelligent-tools.html
    'scripts/generate_favicon.py',
}

IGNORAR = {'.git', 'tests', '__pycache__', '.venv', 'venv', 'node_modules'}


def _arquivo_do_modulo(nome):
    base = RAIZ.joinpath(*nome.split('.'))
    if base.with_suffix('.py').is_file():
        return base.with_suffix('.py')
    if (base / '__init__.py').is_file():
        return base / '__init__.py'
    return None


def _modulos_importados(arquivo):
    """Nomes de módulo importados por um arquivo, inclusive imports dentro de funções e relativos."""
    pacote = '.'.join(arquivo.relative_to(RAIZ).with_suffix('').parts[:-1])
    for no in ast.walk(ast.parse(arquivo.read_text(encoding='utf-8'))):
        if isinstance(no, ast.Import):
            for alias in no.names:
                yield alias.name
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                partes = pacote.split('.') if pacote else []
                partes = partes[:len(partes) - (no.level - 1)]
                base = '.'.join(partes + ([no.module] if no.module else []))
            else:
                base = no.module or ''
            if base:
                yield base
                for alias in no.names:
                    yield f'{base}.{alias.name}'


def _alcancaveis():
    visitados, fila = set(), [ENTRADA]
    while fila:
        arquivo = fila.pop()
        if arquivo in visitados:
            continue
        visitados.add(arquivo)
        for nome in _modulos_importados(arquivo):
            alvo = _arquivo_do_modulo(nome)
            if alvo and alvo not in visitados:
                fila.append(alvo)
    return {str(a.relative_to(RAIZ)) for a in visitados}


def _arquivos(sufixos=None):
    for caminho in RAIZ.rglob('*'):
        if not caminho.is_file() or IGNORAR & set(caminho.relative_to(RAIZ).parts):
            continue
        if sufixos is None or caminho.suffix in sufixos:
            yield str(caminho.relative_to(RAIZ))


def test_todo_arquivo_python_e_usado_pela_aplicacao():
    alcancaveis = _alcancaveis()
    sem_uso = []
    for arquivo in _arquivos({'.py'}):
        if arquivo in alcancaveis or arquivo in FERRAMENTAS:
            continue
        if Path(arquivo).name == '__init__.py':
            continue
        sem_uso.append(arquivo)
    assert sem_uso == [], (
        'Arquivos Python que a aplicação (api/index.py) não importa. Remova-os ou, se forem '
        f'ferramentas, declare-os em FERRAMENTAS: {sem_uso}'
    )


def test_modulos_essenciais_sao_alcancaveis():
    """Garante que a verificação acima está de fato percorrendo os imports."""
    alcancaveis = _alcancaveis()
    for esperado in (
        'src/routes/checkup_intelligent.py',
        'src/utils/validacao.py',
        'src/utils/seguranca_vacinas.py',
        'src/utils/pdf_minutas.py',
    ):
        assert esperado in alcancaveis


def test_nao_ha_copias_antigas_nem_banco_de_dados_versionado():
    proibidos = [a for a in _arquivos() if a.endswith(('.original', '.new', '.bak', '.db', '.sqlite', '.sqlite3'))]
    assert proibidos == []


def test_ha_um_unico_ponto_de_entrada():
    """Só api/index.py cria a aplicação Flask."""
    criadores = []
    for arquivo in _arquivos({'.py'}):
        fonte = (RAIZ / arquivo).read_text(encoding='utf-8')
        if 'Flask(__name__' in fonte:
            criadores.append(arquivo)
    assert criadores == ['api/index.py']


def test_vercel_aponta_para_a_entrada_testada():
    import json

    config = json.loads((RAIZ / 'vercel.json').read_text(encoding='utf-8'))
    assert [b['src'] for b in config['builds']] == ['api/index.py']
    assert all(rota['dest'] == '/api/index.py' for rota in config['routes'])
