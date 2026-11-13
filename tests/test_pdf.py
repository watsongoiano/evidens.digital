"""Perigos P-08 e P-09 e a segunda linha de defesa de P-02 a P-04 nos PDFs.

Os PDFs são gerados de verdade (fpdf2) e lidos de volta com pypdf.
"""
import io

import pytest
from pypdf import PdfReader

from src.utils import pdf_minutas


def _texto_do_pdf(dados):
    assert dados.startswith(b'%PDF')
    return '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(dados)).pages)

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
    """Guarda o texto de cada PDF gerado (lista vazia quando nenhum PDF foi gerado)."""
    gerados = []
    for nome in ('gerar_pdf_exames_laboratoriais', 'gerar_pdf_exames_imagem', 'gerar_pdf_vacinas'):
        original = getattr(pdf_minutas, nome)

        def registrar(dados_paciente, itens, _original=original):
            pdf = _original(dados_paciente, itens)
            gerados.append(_texto_do_pdf(pdf))
            return pdf

        monkeypatch.setattr(pdf_minutas, nome, registrar)
    return gerados


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
    assert resposta.data.startswith(b'%PDF')
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
    assert 'assinatura e carimbo do médico' in html.lower()


def test_sexo_ausente_nao_e_impresso_como_masculino(client, html_enviado):
    _pedir(client, '/api/gerar-pdf-exames-laboratoriais', {'nome': 'Teste', 'idade': '40'}, [EXAME])
    assert 'Não informado' in html_enviado[0]
    assert 'Masculino' not in html_enviado[0]


# --- P-08: o que vem do navegador é impresso como texto, nunca interpretado ---

def test_nome_e_titulos_viram_texto_simples(client, html_enviado):
    paciente = {**HOMEM, 'nome': '<img src=x onerror=alert(1)>'}
    itens = [{'titulo': "<iframe src='http://169.254.169.254/latest/meta-data/'></iframe>", 'categoria': 'laboratorio'}]

    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', paciente, itens)

    assert resposta.status_code == 200
    texto = html_enviado[0]
    assert '<img src=x onerror=alert(1)>' in texto          # impresso tal qual
    assert '<iframe' in texto
    assert b'/JavaScript' not in resposta.data and b'/JS' not in resposta.data and b'/URI' not in resposta.data


def test_caracteres_de_controle_nao_quebram_o_pdf(client, html_enviado):
    itens = [{'titulo': 'Creatinina\x00\x07, soro\u2028x', 'categoria': 'laboratorio'}]
    assert _pedir(client, '/api/gerar-pdf-exames-laboratoriais', HOMEM, itens).status_code == 200
    assert 'Creatinina' in html_enviado[0]


def test_acentos_e_simbolos_sao_preservados(client, html_enviado):
    itens = [{'titulo': 'Tríplice Viral – SCR (Priorix® ou M-M-R® II) ≥ 18 anos', 'categoria': 'vacina'}]
    _pedir(client, '/api/gerar-pdf-vacinas', MULHER_LIBERADA, itens)
    assert 'TRÍPLICE VIRAL – SCR (PRIORIX® OU M-M-R® II) ≥ 18 ANOS' in html_enviado[0]


def test_lista_longa_ganha_mais_paginas_com_assinatura_na_ultima(client):
    itens = [{'titulo': f'Exame número {i} com um nome razoavelmente comprido para ocupar a linha', 'categoria': 'laboratorio'} for i in range(60)]
    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', HOMEM, itens)
    paginas = PdfReader(io.BytesIO(resposta.data)).pages
    assert len(paginas) >= 2
    assert 'Assinatura e Carimbo do Médico' in paginas[-1].extract_text()
    assert 'Exame número 59' in paginas[-1].extract_text() or 'Exame número 59' in paginas[-2].extract_text()


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


# --- Falha na geração ------------------------------------------------------------

def test_falha_na_geracao_nao_expoe_detalhes(client, monkeypatch):
    def quebra(dados_paciente, itens):
        raise Exception('Erro interno: /var/task/assets/fonts/DejaVuSans.ttf')

    monkeypatch.setattr(pdf_minutas, 'gerar_pdf_exames_laboratoriais', quebra)
    resposta = _pedir(client, '/api/gerar-pdf-exames-laboratoriais', HOMEM, [EXAME])

    assert resposta.status_code == 502
    dados = resposta.get_json()
    assert dados['codigo'] == 'falha_na_geracao'
    assert 'DejaVu' not in dados['error'] and '/var/task' not in dados['error']
    assert 'Gotenberg' not in dados['error']


# --- Requisição ao Gotenberg --------------------------------------------------

class _RespostaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return PDF_FALSO


@pytest.mark.parametrize('titulo, esperado', [
    ('Meningocócica ACWY (Menactra® ou Menveo®)', 'Reforço a cada 5 anos'),
    ('Meningocócica B (Bexsero® ou Trumenba®)', 'duas doses'),
    ('Bexsero', 'intervalo de 1 mês'),
])
def test_posologia_meningococica_por_tipo(titulo, esperado):
    from src.utils.pdf_minutas import posologia_da_vacina
    assert esperado in posologia_da_vacina(titulo)


def test_meningococica_sem_esquema_proprio_usa_posologia_padrao():
    from src.utils.pdf_minutas import POSOLOGIA_PADRAO, posologia_da_vacina
    assert posologia_da_vacina('Meningocócica C conjugada') == POSOLOGIA_PADRAO
    assert 'Reforço a cada 5 anos' not in posologia_da_vacina('Meningocócica B (Bexsero® ou Trumenba®)')
