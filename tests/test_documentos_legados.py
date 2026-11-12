"""Perigo P-01: documento que declara assinatura digital sem assinatura real.

Os endpoints legados devolviam "Receita Simples" e "Solicitação de Exame" com
identificação fixa de médico e a frase de assinatura digital, a partir de
conteúdo enviado por qualquer cliente, sem autenticação. Estes testes impedem
que voltem.
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

ROTAS_DESATIVADAS = [
    '/api/gerar-receita-vacinas',
    '/api/gerar-solicitacao-exames',
    '/api/generate-pdf',
]

CORPO = {
    'patient_data': {'nome': 'Paciente de Teste', 'sexo': 'masculino'},
    'recommendations': [
        {'titulo': 'Item arbitrário enviado pelo cliente', 'categoria': 'vacina'},
        {'titulo': 'Outro item arbitrário', 'categoria': 'laboratorio'},
    ],
}

# Trechos que só fazem sentido em um documento efetivamente assinado.
MARCAS_DE_ASSINATURA = [
    'assinado digitalmente',
    'validar.iti.gov.br',
    'CFMP-',
    'prescricao.cfm.org.br/api/documento',
]


@pytest.mark.parametrize('rota', ROTAS_DESATIVADAS)
@pytest.mark.parametrize('metodo', ['post', 'get'])
def test_endpoint_legado_responde_410(client, rota, metodo):
    if metodo == 'post':
        resposta = client.post(rota, json=CORPO)
    else:
        resposta = client.get(rota)

    assert resposta.status_code == 410
    assert resposta.get_json()['codigo'] == 'endpoint_desativado'


@pytest.mark.parametrize('rota', ROTAS_DESATIVADAS)
@pytest.mark.parametrize('aceita', ['application/json', 'text/html'])
def test_endpoint_legado_nao_devolve_documento(client, rota, aceita):
    resposta = client.post(rota, json=CORPO, headers={'Accept': aceita})
    corpo = resposta.get_data(as_text=True)

    assert 'Item arbitrário enviado pelo cliente' not in corpo
    assert '<html' not in corpo.lower()
    for marca in MARCAS_DE_ASSINATURA:
        assert marca not in corpo


def _arquivos_do_projeto():
    ignorar = {'.git', 'tests', 'docs', 'node_modules', '__pycache__', '.venv', 'venv'}
    extensoes_binarias = {'.png', '.ico', '.jpg', '.jpeg', '.db', '.pdf', '.svg'}
    for caminho in RAIZ.rglob('*'):
        if not caminho.is_file():
            continue
        if ignorar & set(caminho.relative_to(RAIZ).parts):
            continue
        if caminho.suffix.lower() in extensoes_binarias:
            continue
        yield caminho


def test_nenhum_arquivo_declara_assinatura_digital():
    """Nenhum template ou cópia antiga pode voltar a declarar assinatura."""
    achados = []
    for caminho in _arquivos_do_projeto():
        try:
            texto = caminho.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for marca in MARCAS_DE_ASSINATURA:
            if marca in texto:
                achados.append(f'{caminho.relative_to(RAIZ)}: {marca}')
    assert achados == []
