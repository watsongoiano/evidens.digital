"""Papel timbrado do médico como fundo dos pedidos (src/utils/timbrado.py e rotas /api/auth/timbrado)."""
import io
import itertools

import pytest
from fpdf import FPDF
from pypdf import PdfReader

from conftest import SENHA_DE_TESTE, aceitar_termos
from src.utils import pdf_minutas, timbrado

_seq = itertools.count(1)
PACIENTE = {'nome': 'Maria de Teste', 'idade': '65', 'sexo': 'feminino'}
EXAMES = [{'titulo': t, 'categoria': 'laboratorio'} for t in ('Hemograma completo', 'Creatinina, soro')]
PLANO = dict(operadora='Unimed Goiânia', registro_ans='123456', codigo_prestador='0012345',
             nome_contratado='Clínica de Teste Ltda.', cbo='225125')


def _timbrado(formato='A4', rodape=True):
    """Timbrado fictício: faixa colorida e nome no topo (até 34 mm) e endereço no rodapé."""
    pdf = FPDF(format=formato)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_fill_color(14, 151, 181)
    pdf.rect(15, 10, 30, 20, 'F')
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_xy(50, 12)
    pdf.cell(0, 8, 'Clinica Exemplo Timbrado')
    pdf.line(15, 34, pdf.w - 15, 34)
    if rodape:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_y(-22)
        pdf.cell(0, 5, 'Rua Exemplo 100 Goiania', align='C')
    return bytes(pdf.output())


def _conta(app, contas, perfil='medico'):
    n = next(_seq)
    registro = f'CRM-GO 5{n:04d}' if perfil != 'estudante' else '2023001 · UFG'
    u = contas.criar(f'timbrado{n}@exemplo.test', f'Dra. Timbrado {n}', registro, perfil, SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def _enviar(cliente, conteudo, nome='receituario.pdf'):
    return cliente.post('/api/auth/timbrado', data={'arquivo': (io.BytesIO(conteudo), nome)},
                        content_type='multipart/form-data')


# ── Medida da área livre ──────────────────────────────────────────────────────

def test_margens_medidas_abaixo_do_cabecalho_e_acima_do_rodape():
    topo, base = timbrado.margens_sugeridas(_timbrado())
    assert 34 < topo <= 40          # a linha do cabeçalho está a 34 mm do topo
    assert 22 <= base <= 30          # o endereço termina a ~22 mm da base


def test_sem_rodape_usa_a_margem_padrao():
    assert timbrado.margens_sugeridas(_timbrado(rodape=False))[1] == timbrado.MARGEM_PADRAO


@pytest.mark.parametrize('conteudo, codigo', [(b'texto', 'nao_pdf'), (b'%PDF-1.4 quebrado', 'invalido'),
                                              (b'%PDF' + b'0' * (4 * 1024 * 1024), 'grande')])
def test_arquivo_invalido(conteudo, codigo):
    with pytest.raises(timbrado.TimbradoInvalido) as erro:
        timbrado.margens_sugeridas(conteudo)
    assert erro.value.codigo == codigo


def test_timbrado_sem_espaco_para_o_pedido_e_recusado():
    """Cabeçalho e rodapé grandes (ou página pequena) deixariam o pedido espremido: recusa no envio."""
    pdf = FPDF(format=(150, 160))
    pdf.add_page()
    pdf.rect(10, 5, 50, 40, 'F')
    pdf.rect(10, 115, 50, 40, 'F')
    with pytest.raises(timbrado.TimbradoInvalido) as erro:
        timbrado.margens_sugeridas(bytes(pdf.output()))
    assert erro.value.codigo == 'area'


@pytest.mark.parametrize('topo, base, valido', [(38, 25, True), (5, 25, False), (38, 200, False), ('x', 20, False)])
def test_conferir_margens(topo, base, valido):
    if valido:
        assert timbrado.conferir_margens(_timbrado(), topo, base) == (38.0, 25.0)
    else:
        with pytest.raises(timbrado.TimbradoInvalido):
            timbrado.conferir_margens(_timbrado(), topo, base)


# ── PDF do pedido sobre o timbrado ────────────────────────────────────────────

def _registro(conteudo=None):
    conteudo = conteudo or _timbrado()
    topo, base = timbrado.margens_sugeridas(conteudo)
    return timbrado.para_o_pdf({'arquivo': conteudo, 'margem_topo': topo, 'margem_base': base})


def test_pedido_sai_sobre_o_timbrado_sem_a_marca_evidens():
    pdf = pdf_minutas.gerar_pdf_exames_laboratoriais(PACIENTE, EXAMES, timbrado=_registro())
    texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert 'Clinica Exemplo Timbrado' in texto and 'Rua Exemplo 100' in texto
    assert 'SOLICITAÇÃO DE EXAMES' in texto and 'Hemograma completo' in texto
    assert 'evidēns' not in texto


def test_pedido_longo_repete_o_timbrado_em_cada_pagina():
    exames = [{'titulo': f'Exame de teste {n}'} for n in range(60)]
    paginas = PdfReader(io.BytesIO(pdf_minutas.gerar_pdf_exames_laboratoriais(PACIENTE, exames, timbrado=_registro()))).pages
    assert len(paginas) > 1 and all('Clinica Exemplo Timbrado' in p.extract_text() for p in paginas)


def test_timbrado_carta_define_o_tamanho_da_pagina():
    pdf = pdf_minutas.gerar_pdf_vacinas(PACIENTE, [{'titulo': 'Influenza (gripe)'}], timbrado=_registro(_timbrado('Letter')))
    pagina = PdfReader(io.BytesIO(pdf)).pages[0]
    assert round(float(pagina.mediabox.width)) == 612 and round(float(pagina.mediabox.height)) == 792


# ── Rotas ────────────────────────────────────────────────────────────────────

def test_rotas_exigem_login(anonimo):
    assert anonimo.get('/api/auth/timbrado').status_code == 401
    assert _enviar(anonimo, _timbrado()).status_code == 401


def test_estudante_nao_tem_timbrado(app, contas):
    aluno, _ = _conta(app, contas, perfil='estudante')
    assert aluno.get('/api/auth/timbrado').get_json() == {'timbrado': None, 'disponivel': False}
    assert _enviar(aluno, _timbrado()).status_code == 403


def test_enviar_ajustar_previa_e_remover(app, contas):
    cliente, u = _conta(app, contas)
    r = _enviar(cliente, _timbrado())
    assert r.status_code == 201
    t = r.get_json()['timbrado']
    assert t['nome'] == 'receituario.pdf' and t['largura'] == 210 and 34 < t['margem_topo'] <= 40
    assert cliente.post('/api/auth/timbrado/margens', json={'margem_topo': 45, 'margem_base': 30}).get_json()['timbrado']['margem_topo'] == 45
    assert cliente.post('/api/auth/timbrado/margens', json={'margem_topo': 2, 'margem_base': 30}).status_code == 400
    previa = cliente.get('/api/auth/timbrado/previa')
    assert previa.status_code == 200 and previa.mimetype == 'application/pdf'
    assert 'Clinica Exemplo Timbrado' in PdfReader(io.BytesIO(previa.data)).pages[0].extract_text()
    assert cliente.post('/api/auth/timbrado/remover').status_code == 200
    assert cliente.get('/api/auth/timbrado').get_json()['timbrado'] is None
    sem = cliente.get('/api/auth/timbrado/previa')        # volta ao modelo do Evidēns
    assert sem.status_code == 200 and 'Clinica Exemplo Timbrado' not in PdfReader(io.BytesIO(sem.data)).pages[0].extract_text()
    assert cliente.get('/api/auth/timbrado').get_json()['modo'] == 'padrao'


def test_timbrado_e_so_da_conta_de_quem_enviou(app, contas):
    dona, _ = _conta(app, contas)
    outra, _ = _conta(app, contas)
    _enviar(dona, _timbrado())
    assert outra.get('/api/auth/timbrado').get_json()['timbrado'] is None
    pedido = outra.post('/api/gerar-pdf-exames-laboratoriais', json={'dados_paciente': PACIENTE, 'recomendacoes': EXAMES})
    assert 'Clinica Exemplo Timbrado' not in PdfReader(io.BytesIO(pedido.data)).pages[0].extract_text()


def test_pedido_usa_o_timbrado_e_a_guia_continua_a4_sem_timbrado(app, contas):
    cliente, _ = _conta(app, contas)
    _enviar(cliente, _timbrado('Letter'))
    cid = cliente.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    r = cliente.post('/api/gerar-pdf-exames-laboratoriais',
                     json={'dados_paciente': PACIENTE, 'recomendacoes': EXAMES, 'guia': {'credenciamento_id': cid}})
    pedido, guia = PdfReader(io.BytesIO(r.data)).pages
    assert 'Clinica Exemplo Timbrado' in pedido.extract_text()
    assert 'SP/SADT' in guia.extract_text() and 'Clinica Exemplo Timbrado' not in guia.extract_text()
    assert round(float(guia.mediabox.width)) == 842 and round(float(guia.mediabox.height)) == 595   # A4 deitada
