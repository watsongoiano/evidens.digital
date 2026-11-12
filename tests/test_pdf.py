"""Perigos P-08 e P-09 e a segunda linha de defesa de P-02 a P-04 nos PDFs.

O Gotenberg não é chamado: a função que fala com ele é substituída por uma que
guarda o HTML recebido.
"""
import urllib.request

import pytest

from src.utils import pdf_service_gotenberg

PDF_FALSO = b'%PDF-1.4\n% teste\n'

HOMEM = {'nome': 'Paciente de Teste', 'idade': '40', 'sexo': 'masculino', 'imunossupressao': 'nao'}
MULHER_LIBERADA = {
    'nome': 'Paciente de Teste', 'idade': '30', 'sexo': 'feminino',
    'gestante': 'nao', 'lactante': 'nao', 'imunossupressao': 'nao',
}

EXAME = {'titulo': 'Creatinina, soro', 'categoria': 'laboratorio'}
IMAGEM = {'titulo': 'Eletrocardiograma de repouso', 'categoria': 'imagem'}
INFLUENZA = {'titulo': 'Influenza Tetravalente (Fluarix®, Vaxigrip® ou similar)', 'categoria': 'vacina'}
TRIPLICE = {'titulo': 'Tríplice Viral - SCR (Priorix® ou M-M-R® II)', 'categoria': 'vacina'}
FEBRE_AMARELA = {'titulo': 'Febre Amarela (Stamaril®)', 'categoria': 'vacina'}


@pytest.fixture()
def html_enviado(monkeypatch):
    """Substitui a chamada ao Gotenberg e devolve a lista de HTMLs que seriam enviados."""
    enviados = []

    def falso(html):
        enviados.append(html)
        return PDF_FALSO

    monkeypatch.setattr(pdf_service_gotenberg, 'gerar_pdf_via_gotenberg', falso)
    return enviados


def _pedir(client, rota, dados_paciente, recomendacoes):
    return client.post(rota, json={'dados_paciente': dados_paciente, 'recomendacoes': recomendacoes})


# --- Funcionamento básico ---------------------------------------------------

@pytest.mark.parametrize('rota, item', [
    ('/api/gerar-pdf-exames-laboratoriais', EXAME),
    ('/api/gerar-pdf-exames-imagem', IMAGEM),
    ('/api/gerar-pdf-vacinas', INFLUENZA),
])
def test_gera_pdf_da_categoria_pedida(client, html_enviado, rota, item):
    resposta = _pedir(client, rota, HOMEM, [EXAME, IMAGEM, INFLUENZA])

    assert resposta.status_code == 200
    assert resposta.mimetype == 'application/pdf'
    assert resposta.data == PDF_FALSO
    html = html_enviado[0]
    assert item['titulo'].split(' (')[0].upper() in html.upper()
    outros = [i for i in (EXAME, IMAGEM, INFLUENZA) if i is not item]
    assert all(o['titulo'].split(' (')[0].upper() not in html.upper() for o in outros)


@pytest.mark.parametrize('rota', [
    '/api/gerar-pdf-exames-laboratoriais',
    '/api/gerar-pdf-exames-imagem',
    '/api/gerar-pdf-vacinas',
])
def test_minuta_traz_campo_de_assinatura_e_nao_declara_assinatura_digital(client, html_enviado, rota):
    _pedir(client, rota, HOMEM, [EXAME, IMAGEM, INFLUENZA])
    html = html_enviado[0]

    assert 'Assinatura e Carimbo do Médico' in html
    assert 'Documento sem assinatura digital' in html
    assert 'assinado digitalmente' not in html.lower()
    assert 'CRM' not in html


def test_sexo_ausente_nao_e_impresso_como_masculino(client, html_enviado):
    _pedir(client, '/api/gerar-pdf-exames-laboratoriais', {'nome': 'Teste', 'idade': '40'}, [EXAME])
    assert 'Não informado' in html_enviado[0]
    assert 'Masculino' not in html_enviado[0]


# --- P-08: o que vem do navegador não vira HTML -----------------------------

def test_nome_e_titulos_sao_escapados(client, html_enviado):
    paciente = {**HOMEM, 'nome': '<img src=x onerror=alert(1)>'}
    itens = [{'titulo': "<iframe src='http://169.254.169.254/latest/meta-data/'></iframe>", 'categoria': 'laboratorio'}]

    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', paciente, itens)

    assert resposta.status_code == 200
    html = html_enviado[0]
    assert '<img' not in html
    assert '<iframe' not in html
    assert '&lt;img src=x onerror=alert(1)&gt;' in html
    assert '&lt;iframe' in html


def test_titulo_de_vacina_e_escapado(client, html_enviado):
    itens = [{'titulo': 'Influenza <script>alert(1)</script>', 'categoria': 'vacina'}]
    _pedir(client, '/api/gerar-pdf-vacinas', HOMEM, itens)
    assert '<script' not in html_enviado[0].lower()


@pytest.mark.parametrize('dados_paciente, recomendacoes', [
    (HOMEM, [EXAME] * 81),                                             # itens demais
    (HOMEM, [{'titulo': 'x' * 301, 'categoria': 'laboratorio'}]),      # título longo demais
    (HOMEM, [{'titulo': '', 'categoria': 'laboratorio'}]),
    (HOMEM, [{'titulo': {'a': 1}, 'categoria': 'laboratorio'}]),
    (HOMEM, ['Creatinina']),                                           # item que não é objeto
    (HOMEM, 'Creatinina'),
    ({**HOMEM, 'nome': 'n' * 151}, [EXAME]),
    ({**HOMEM, 'nome': ['a']}, [EXAME]),
    ('paciente', [EXAME]),
])
def test_pedido_malformado_e_recusado(client, html_enviado, dados_paciente, recomendacoes):
    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', dados_paciente, recomendacoes)

    assert resposta.status_code == 400
    assert resposta.get_json()['codigo'] == 'pedido_invalido'
    assert html_enviado == []


@pytest.mark.parametrize('corpo', [None, {}, [], 'x'])
def test_pedido_sem_corpo_valido_e_recusado(client, html_enviado, corpo):
    resposta = client.post('/api/gerar-pdf-exames-laboratoriais', json=corpo)
    assert resposta.status_code == 400
    assert html_enviado == []


def test_lista_sem_itens_da_categoria_e_recusada(client, html_enviado):
    resposta = _pedir(client, '/api/gerar-pdf-exames-imagem', HOMEM, [EXAME])
    assert resposta.status_code == 400
    assert html_enviado == []


# --- Segunda linha de defesa para vacinas atenuadas -------------------------

def test_vacina_atenuada_para_gestante_nao_vai_para_o_pdf(client, html_enviado):
    gestante = {**MULHER_LIBERADA, 'gestante': 'sim'}
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', gestante, [INFLUENZA, TRIPLICE])

    assert resposta.status_code == 400
    dados = resposta.get_json()
    assert dados['codigo'] == 'triagem_vacinas'
    assert 'Tríplice Viral' in dados['error']
    assert html_enviado == []


def test_vacina_atenuada_sem_triagem_no_pedido_nao_vai_para_o_pdf(client, html_enviado):
    """Página antiga em cache ou pedido montado à mão: sem triagem, não imprime."""
    sem_triagem = {'nome': 'Teste', 'idade': '30', 'sexo': 'feminino'}
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', sem_triagem, [TRIPLICE])

    assert resposta.status_code == 400
    assert resposta.get_json()['codigo'] == 'triagem_vacinas'
    assert html_enviado == []


def test_formulario_alterado_depois_de_gerar_e_barrado(client, html_enviado):
    """A lista foi gerada com a triagem liberada; no pedido, o formulário já diz imunossupressão."""
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', {**HOMEM, 'imunossupressao': 'sim'}, [FEBRE_AMARELA])
    assert resposta.status_code == 400
    assert html_enviado == []


def test_hiv_no_pedido_barra_atenuadas(client, html_enviado):
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', {**HOMEM, 'hiv': True, 'cd4': '150'}, [TRIPLICE])
    assert resposta.status_code == 400
    assert html_enviado == []


def test_vacina_atenuada_com_triagem_liberada_vai_para_o_pdf(client, html_enviado):
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', MULHER_LIBERADA, [INFLUENZA, TRIPLICE, FEBRE_AMARELA])

    assert resposta.status_code == 200
    assert 'TRÍPLICE VIRAL' in html_enviado[0]
    assert 'FEBRE AMARELA' in html_enviado[0]


def test_vacinas_inativadas_nao_dependem_da_triagem(client, html_enviado):
    sem_triagem = {'nome': 'Teste', 'idade': '30', 'sexo': 'feminino'}
    resposta = _pedir(client, '/api/gerar-pdf-vacinas', sem_triagem, [INFLUENZA])
    assert resposta.status_code == 200


# --- Falha do serviço de PDF -------------------------------------------------

def test_falha_do_gotenberg_nao_expoe_detalhes(client, monkeypatch):
    def quebra(html):
        raise Exception('Erro de conexão ao gerar PDF via Gotenberg: http://servico-interno.railway.internal:3000')

    monkeypatch.setattr(pdf_service_gotenberg, 'gerar_pdf_via_gotenberg', quebra)
    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', HOMEM, [EXAME])

    assert resposta.status_code == 502
    dados = resposta.get_json()
    assert dados['codigo'] == 'falha_na_geracao'
    assert 'railway' not in dados['error']
    assert 'Gotenberg' not in dados['error']


# --- Requisição ao Gotenberg --------------------------------------------------

class _RespostaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return PDF_FALSO


@pytest.fixture()
def requisicoes(monkeypatch):
    feitas = []

    def falso_urlopen(requisicao, timeout=None):
        feitas.append(requisicao)
        return _RespostaFalsa()

    monkeypatch.setattr(urllib.request, 'urlopen', falso_urlopen)
    return feitas


def test_delimitador_multipart_muda_a_cada_requisicao(requisicoes, monkeypatch):
    monkeypatch.delenv('GOTENBERG_API_BASIC_AUTH_USERNAME', raising=False)
    monkeypatch.delenv('GOTENBERG_API_BASIC_AUTH_PASSWORD', raising=False)

    pdf_service_gotenberg.gerar_pdf_via_gotenberg('<p>a</p>')
    pdf_service_gotenberg.gerar_pdf_via_gotenberg('<p>b</p>')

    tipos = [r.get_header('Content-type') for r in requisicoes]
    assert tipos[0] != tipos[1]
    for requisicao, tipo in zip(requisicoes, tipos):
        delimitador = tipo.split('boundary=')[1]
        assert requisicao.data.count(delimitador.encode()) == 2
        assert requisicao.get_header('Authorization') is None


def test_autenticacao_basica_e_enviada_quando_configurada(requisicoes, monkeypatch):
    monkeypatch.setenv('GOTENBERG_API_BASIC_AUTH_USERNAME', 'evidens')
    monkeypatch.setenv('GOTENBERG_API_BASIC_AUTH_PASSWORD', 'segredo')

    pdf_service_gotenberg.gerar_pdf_via_gotenberg('<p>a</p>')

    assert requisicoes[0].get_header('Authorization') == 'Basic ZXZpZGVuczpzZWdyZWRv'
