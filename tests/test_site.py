"""O que o site publica, o que a página do check-up contém e o que foi desativado.

Cobre P-06 (risco cardiovascular), P-10 (persistência) e a exposição de arquivos
internos e telas antigas por URL.
"""
import importlib.util
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

PAGINAS = ['/', '/intelligent-tools', '/contact', '/analytics']


# --- Arquivos publicados ----------------------------------------------------

@pytest.mark.parametrize('rota', PAGINAS + [
    '/index.html',
    '/intelligent-tools.html',
    '/favicon.ico',
    '/favicon.png',
    '/src/static/styles/base.css',
])
def test_paginas_e_recursos_publicos_respondem(client, rota):
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize('rota', [
    '/src/static/index.html',                 # tela antiga, com cálculo de risco próprio
    '/dist/index.html',
    '/src/static/database_dashboard.html',
    '/config/base_recommendations.json',
    '/config/medical_references.json',
    '/package.json',
    '/vercel.json',
    '/prevent_calculator.js',
    '/src/routes/checkup_intelligent.py',
    '/requirements.txt',
    '/.env',
    '/../api/index.py',
])
def test_arquivos_internos_e_telas_antigas_nao_sao_servidos(client, rota):
    assert client.get(rota).status_code == 404


def _referencias_locais(html):
    for atributo, valor in re.findall(r'\b(src|href)="([^"]+)"', html):
        if valor.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'data:')):
            continue
        if valor.startswith('/_vercel/'):   # injetado pela plataforma em produção
            continue
        yield valor


@pytest.mark.parametrize('pagina', PAGINAS)
def test_toda_referencia_local_das_paginas_existe(client, pagina):
    """Nenhuma página pode apontar para um arquivo que o site não publica."""
    html = client.get(pagina).get_data(as_text=True)
    for referencia in _referencias_locais(html):
        caminho = referencia if referencia.startswith('/') else '/' + referencia
        assert client.get(caminho).status_code == 200, f'{pagina} -> {referencia}'


# --- P-06: risco cardiovascular desativado -----------------------------------

PERFIL_COMPLETO = {
    'idade': '55', 'sexo': 'masculino', 'tabagismo': 'atual', 'macos_ano': '30',
    'pas': '132', 'pad': '80', 'colesterol': '200', 'hdl': '45', 'creatinina': '1.0',
    'comorbidades': ['diabetes'], 'medicacoes': ['anti_hipertensivos'], 'imunossupressao': 'nao',
}


def test_api_nao_devolve_risco_cardiovascular(client):
    dados = client.post('/api/checkup-intelligent', json=PERFIL_COMPLETO).get_json()

    assert dados['prevent_risk'] is None
    assert dados['risk_classification'] is None
    assert dados['risco_cardiovascular']['status'] == 'desativado'
    assert dados['risco_cardiovascular']['motivo']


def test_calculadoras_de_risco_foram_removidas():
    assert importlib.util.find_spec('src.utils.prevent_calculator') is None
    assert not (RAIZ / 'prevent_calculator.js').exists()
    assert not (RAIZ / 'config' / 'prevent_coefficients.json').exists()


def test_pagina_nao_calcula_nem_exibe_risco(client):
    html = client.get('/intelligent-tools').get_data(as_text=True)

    for trecho in ('prevent_calculator', 'PreventCalculator', 'risk_10yr', 'Estimated 10-year', 'eGFR calculado'):
        assert trecho not in html
    assert 'risco cardiovascular está temporariamente desativado' in html


# --- Página do check-up -------------------------------------------------------

@pytest.fixture()
def pagina(client):
    return client.get('/intelligent-tools').get_data(as_text=True)


def _select(html, nome):
    bloco = re.search(rf'<select id="{nome}"[^>]*>(.*?)</select>', html, re.S)
    assert bloco, f'select {nome} não encontrado'
    return bloco.group(0), re.findall(r'<option value="([^"]*)"', bloco.group(1))


@pytest.mark.parametrize('campo, opcoes', [
    ('imunossupressao', ['desconhecido', 'nao', 'sim']),
    ('gestante', ['desconhecido', 'nao', 'sim']),
    ('lactante', ['desconhecido', 'nao', 'sim_menor_6m', 'sim_6m_ou_mais']),
])
def test_triagem_tem_tres_valores_e_comeca_em_nao_informado(pagina, campo, opcoes):
    _, valores = _select(pagina, campo)
    assert valores == opcoes


def test_tabagismo_exige_escolha_explicita(pagina):
    marcacao, valores = _select(pagina, 'tabagismo')
    assert 'required' in marcacao.split('>')[0]
    assert valores == ['', 'nunca', 'atual', 'ex']
    assert '<option value="" selected disabled>' in marcacao


def test_nome_do_paciente_e_opcional_e_nao_vai_com_as_recomendacoes(pagina):
    campo = re.search(r'<input[^>]*id="nome_paciente"[^>]*>', pagina).group(0)
    assert 'required' not in campo
    assert 'delete payload.nome_paciente' in pagina


def test_seletor_de_pais_sem_efeito_foi_retirado(pagina):
    assert 'name="pais"' not in pagina


def test_pagina_avisa_que_a_saida_e_sugestao_e_que_o_pdf_e_minuta(pagina):
    assert 'não constituem prescrição' in pagina
    assert 'minutas sem assinatura digital' in pagina


def test_pagina_nao_chama_endpoints_desativados(pagina):
    for rota in ('gerar-receita-vacinas', 'gerar-solicitacao-exames', 'generate-pdf'):
        assert rota not in pagina


# --- P-10: nada é gravado ------------------------------------------------------

def test_motor_nao_tem_acesso_a_banco_de_dados():
    import src.routes.checkup_intelligent as motor

    for nome in ('db', 'Patient', 'Checkup', 'Recomendacao'):
        assert not hasattr(motor, nome)
    fonte = Path(motor.__file__).read_text(encoding='utf-8')
    assert 'db.session' not in fonte
    assert 'src.models' not in fonte


def test_resposta_pendente_e_descartada_se_o_formulario_mudar(pagina):
    """A resposta de um envio só vale se o formulário não mudou enquanto ela chegava."""
    invalidar = re.search(r'function invalidarResultados\(evento\) \{(.*?)\n        \}', pagina, re.S).group(1)
    # O contador avança antes do teste de "resultado visível": vale também com resposta pendente.
    assert invalidar.index('revisaoDoFormulario += 1') < invalidar.index("recommendationsDiv.style.display === 'block'")

    envio = re.search(r"checkupForm\.addEventListener\('submit'.*?\n        \}\);", pagina, re.S).group(0)
    assert 'const revisaoDoEnvio = revisaoDoFormulario;' in envio
    conferencia = envio.index('if (revisaoDoEnvio !== revisaoDoFormulario)')
    assert envio.index("await fetch('/api/checkup-intelligent'") < conferencia
    assert conferencia < envio.index('currentRecommendations = result.recommendations')
    assert conferencia < envio.index('mostrarErros(')
