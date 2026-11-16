"""Receituário em três modos (src/utils/receituario.py): modelo enviado (PDF ou imagem), montado na tela
e papel já timbrado. Dados e imagens fictícios."""
import io
import itertools

import pytest
from PIL import Image, ImageDraw
from pypdf import PdfReader

from conftest import SENHA_DE_TESTE, aceitar_termos
from src.utils import receituario, timbrado

_seq = itertools.count(1)
PACIENTE = {'nome': 'Maria de Teste', 'idade': '65', 'sexo': 'feminino'}
EXAMES = [{'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}]
MONTADO = {'nome': 'Dra. Exemplo de Teste', 'registro': 'CRM-GO 12345 · RQE 6789', 'especialidade': 'Clínica Médica',
           'endereco': 'Rua Exemplo, 100 - Goiânia/GO', 'contato': '(62) 3000-0000', 'tema': 'linha',
           'alinhamento': 'esquerda', 'cor': 'teal'}


def _png(desenhar, tamanho=(1240, 1754), modo='RGB'):
    imagem = Image.new(modo, tamanho, 'white' if modo == 'RGB' else (0, 0, 0, 0))
    desenhar(ImageDraw.Draw(imagem))
    saida = io.BytesIO()
    imagem.save(saida, 'PNG')
    return saida.getvalue()


def _timbrado_escaneado(d):
    d.rectangle((80, 60, 500, 220), fill=(20, 60, 120))          # cabeçalho até 220 px (37 mm)
    d.rectangle((80, 1650, 1160, 1680), fill=(20, 60, 120))      # rodapé a partir de 1650 px
    d.rectangle((300, 700, 900, 1000), fill=(235, 240, 250))     # marca-d'água clara no meio


LOGO = _png(lambda d: d.ellipse((5, 5, 95, 95), fill=(14, 151, 181, 255)), (100, 100), 'RGBA')


def _conta(app, contas, perfil='medico'):
    n = next(_seq)
    registro = f'CRM-GO 6{n:04d}' if perfil != 'estudante' else '2023001 · UFG'
    u = contas.criar(f'receita{n}@exemplo.test', f'Dra. Receita {n}', registro, perfil, SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def _texto_do_pedido(cliente):
    r = cliente.post('/api/gerar-pdf-exames-laboratoriais', json={'dados_paciente': PACIENTE, 'recomendacoes': EXAMES})
    assert r.status_code == 200, r.get_json()
    return PdfReader(io.BytesIO(r.data)).pages[0].extract_text(), r.data


# ── Modelo em imagem ──────────────────────────────────────────────────────────

def test_imagem_do_timbrado_vira_pagina_a4_e_a_area_livre_e_medida_pelos_pixels():
    pdf = timbrado.imagem_para_pdf(_png(_timbrado_escaneado))
    assert timbrado.dimensoes(pdf) == (210.0, 297.0)
    topo, base = timbrado.margens_sugeridas(pdf)
    assert 39 <= topo <= 44           # cabeçalho termina a ~37 mm; a marca-d'água clara não conta
    assert 19 <= base <= 24           # rodapé começa a ~17,6 mm da base


def test_imagem_invalida_e_recusada():
    with pytest.raises(timbrado.TimbradoInvalido):
        timbrado.imagem_para_pdf(b'\x89PNG\r\n\x1a\n' + b'0' * 100)


def test_envio_de_png_pela_conta_passa_a_valer(app, contas):
    cliente, _ = _conta(app, contas)
    r = cliente.post('/api/auth/timbrado', data={'arquivo': (io.BytesIO(_png(_timbrado_escaneado)), 'timbrado.png')},
                     content_type='multipart/form-data')
    assert r.status_code == 201, r.get_json()
    estado = r.get_json()
    assert estado['modo'] == 'modelo' and estado['ativo']['altura'] == 297.0
    _, pdf = _texto_do_pedido(cliente)
    assert '/XObject' in str(PdfReader(io.BytesIO(pdf)).pages[0]['/Resources'])   # fundo aplicado


# ── Montado na tela ───────────────────────────────────────────────────────────

@pytest.mark.parametrize('tema', receituario.TEMAS)
@pytest.mark.parametrize('alinhamento', receituario.ALINHAMENTOS)
def test_receituario_montado_deixa_espaco_para_o_pedido(tema, alinhamento):
    dados = receituario.validar_montado(dict(MONTADO, tema=tema, alinhamento=alinhamento), LOGO)
    pdf = receituario.montar(dados, LOGO)
    texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert 'Dra. Exemplo de Teste' in texto and 'CRM-GO 12345' in texto and 'Rua Exemplo' in texto
    topo, base = timbrado.margens_sugeridas(pdf)
    assert 297 - topo - base >= timbrado.AREA_MINIMA


def test_montado_exige_nome_e_opcoes_validas():
    with pytest.raises(receituario.ReceituarioInvalido):
        receituario.validar_montado(dict(MONTADO, nome=' '))
    for campo in ('tema', 'alinhamento', 'cor'):
        with pytest.raises(receituario.ReceituarioInvalido):
            receituario.validar_montado(dict(MONTADO, **{campo: 'outro'}))
    with pytest.raises(receituario.ReceituarioInvalido):
        receituario.validar_montado(MONTADO, b'%PDF-1.4 nao e imagem')
    assert len(receituario.validar_montado(dict(MONTADO, endereco='x' * 500))['endereco']) == 140


def test_montado_pela_conta_com_logo_sai_no_pedido(app, contas):
    cliente, u = _conta(app, contas)
    r = cliente.post('/api/auth/timbrado/montado', data={**MONTADO, 'logo': (io.BytesIO(LOGO), 'logo.png')},
                     content_type='multipart/form-data')
    assert r.status_code == 200, r.get_json()
    estado = r.get_json()
    assert estado['modo'] == 'montado' and estado['montado']['tem_logo'] and estado['montado']['nome'] == MONTADO['nome']
    texto, _ = _texto_do_pedido(cliente)
    assert 'Dra. Exemplo de Teste' in texto and 'Hemograma' in texto and 'evidēns' not in texto.lower()
    # trocar só o tema mantém o logo; remover_logo apaga
    cliente.post('/api/auth/timbrado/montado', data=dict(MONTADO, tema='faixa'), content_type='multipart/form-data')
    assert contas.receituario_de(u['id'])['logo'] == LOGO
    cliente.post('/api/auth/timbrado/montado', data=dict(MONTADO, remover_logo='1'), content_type='multipart/form-data')
    assert contas.receituario_de(u['id'])['logo'] is None


# ── Papel já timbrado ─────────────────────────────────────────────────────────

def test_papel_ja_timbrado_sai_sem_fundo_e_respeita_as_margens(app, contas):
    cliente, _ = _conta(app, contas)
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'papel'}).status_code == 200
    r = cliente.post('/api/auth/timbrado/margens', json={'margem_topo': 55, 'margem_base': 35})
    assert r.status_code == 200 and r.get_json()['ativo']['margem_topo'] == 55
    texto, pdf = _texto_do_pedido(cliente)
    pagina = PdfReader(io.BytesIO(pdf)).pages[0]
    assert 'Hemograma' in texto and 'evidēns' not in texto.lower()
    assert '/XObject' not in str(pagina.get('/Resources', {}))       # nenhum fundo
    assert cliente.post('/api/auth/timbrado/margens', json={'margem_topo': 150, 'margem_base': 35}).status_code == 400


# ── Modos, imagem para ajuste e permissões ────────────────────────────────────

def test_troca_de_modo_e_volta_ao_padrao(app, contas):
    cliente, _ = _conta(app, contas)
    estado = cliente.get('/api/auth/timbrado').get_json()
    assert estado['modo'] == 'padrao' and estado['ativo'] is None and 'teal' in estado['opcoes']['cores']
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'modelo'}).status_code == 400   # sem modelo enviado
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'montado'}).status_code == 400  # nada montado
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'outro'}).status_code == 400
    cliente.post('/api/auth/timbrado/montado', data=MONTADO, content_type='multipart/form-data')
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'padrao'}).get_json()['modo'] == 'padrao'
    texto, _ = _texto_do_pedido(cliente)
    assert 'Dra. Exemplo de Teste' not in texto
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'montado'}).get_json()['modo'] == 'montado'
    assert cliente.post('/api/auth/timbrado/margens', json={'margem_topo': 50, 'margem_base': 30}).status_code == 200


@pytest.mark.parametrize('modo', ['padrao', 'papel', 'montado'])
def test_imagem_para_ajustar_os_espacos(app, contas, modo):
    cliente, _ = _conta(app, contas)
    if modo == 'montado':
        cliente.post('/api/auth/timbrado/montado', data=MONTADO, content_type='multipart/form-data')
    elif modo == 'papel':
        cliente.post('/api/auth/timbrado/modo', json={'modo': 'papel'})
    r = cliente.get('/api/auth/timbrado/imagem')
    assert r.status_code == 200 and r.mimetype == 'image/png' and r.headers['Cache-Control'] == 'no-store'
    imagem = Image.open(io.BytesIO(r.data))
    assert imagem.size[0] == 620 and abs(imagem.size[1] / imagem.size[0] - 297 / 210) < 0.01


def test_estudante_nao_tem_receituario(app, contas):
    cliente, _ = _conta(app, contas, 'estudante')
    assert cliente.get('/api/auth/timbrado').get_json()['disponivel'] is False
    assert cliente.post('/api/auth/timbrado/modo', json={'modo': 'papel'}).status_code == 403
    assert cliente.post('/api/auth/timbrado/montado', data=MONTADO, content_type='multipart/form-data').status_code == 403
    assert cliente.get('/api/auth/timbrado/imagem').status_code == 403


def test_receituario_que_nao_abre_nao_impede_o_pedido(app, contas, monkeypatch):
    cliente, _ = _conta(app, contas)
    cliente.post('/api/auth/timbrado/montado', data=MONTADO, content_type='multipart/form-data')
    monkeypatch.setattr(receituario, 'montar', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('quebrou')))
    texto, _ = _texto_do_pedido(cliente)
    assert 'Hemograma' in texto


def test_rodape_longo_quebra_dentro_da_pagina():
    import pypdfium2
    dados = receituario.validar_montado(dict(MONTADO, endereco='AVENIDA ' * 20, contato='CONTATO ' * 15))
    pdf = receituario.montar(dados)
    documento = pypdfium2.PdfDocument(pdf)
    try:
        texto = documento[0].get_textpage()
        caixas = [texto.get_charbox(i) for i in range(texto.count_chars())]
    finally:
        documento.close()
    assert min(c[0] for c in caixas) >= 15 / 25.4 * 72 and max(c[2] for c in caixas) <= 195 / 25.4 * 72
    topo, base = timbrado.margens_sugeridas(pdf)
    assert 297 - topo - base >= timbrado.AREA_MINIMA
