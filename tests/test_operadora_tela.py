"""Tela do modo sombra das operadoras (/operadoras): só o administrador vê e envia."""
import io

from tests.test_operadora import FORMATO_C, _pdf

ROTA = '/api/admin/operadoras/classificar'
PLANILHA = ('id_pedido;id_beneficiario;idade;sexo;data_pedido;codigo_tuss;carater;regime;finalidade;cid\n'
            'P1;B1;52;F;2026-11-10;40316521;eletivo;ambulatorial;rastreio;Z00.0\n'      # TSH
            'P1;B1;52;F;2026-11-10;40302830;eletivo;ambulatorial;rastreio;Z00.0\n'      # vitamina D
            'P2;B2;52;F;2026-11-10;;eletivo;ambulatorial;rastreio;Z00.0\n')             # sem código: linha com erro


def _envio(cliente, **campos):
    return cliente.post(ROTA, data=campos, content_type='multipart/form-data', headers={'Origin': 'http://localhost'})


def _planilha(texto=PLANILHA):
    return (io.BytesIO(texto.encode('utf-8')), 'pedidos.csv')


def test_pagina_e_rota_sao_so_do_administrador(client, admin, app):
    assert admin.get('/operadoras').status_code == 200
    assert client.get('/operadoras').status_code == 302                    # médica comum volta ao check-up
    assert app.test_client().get('/operadoras').status_code == 302         # sem login
    assert _envio(client, arquivo=_planilha()).status_code == 403
    assert _envio(app.test_client(), arquivo=_planilha()).status_code == 401


def test_planilha_e_classificada_e_devolve_resumo_linhas_e_csv(admin):
    resposta = _envio(admin, arquivo=_planilha())
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    dados = resposta.get_json()
    assert dados['resumo']['linhas'] == 3 and dados['resumo']['invalidas'] == 1
    assert len(dados['linhas']) == 3
    vitamina_d = dados['linhas'][1]
    assert vitamina_d['cor'] == 'vermelho' and vitamina_d['link'].startswith('https://')
    assert dados['linhas'][2]['erro']
    assert dados['csv'].splitlines()[0].startswith('id_pedido,id_beneficiario') and len(dados['csv'].splitlines()) == 4


def test_planilha_em_windows_1252_e_lida(admin):
    texto = PLANILHA.replace('id_pedido;', 'observação;id_pedido;').replace('\nP', '\nação;P')
    resposta = admin.post(ROTA, data={'arquivo': (io.BytesIO(texto.encode('cp1252')), 'pedidos.csv')},
                          content_type='multipart/form-data', headers={'Origin': 'http://localhost'})
    assert resposta.status_code == 200 and resposta.get_json()['resumo']['linhas'] == 3


def test_laudos_em_pdf_viram_pedidos(admin):
    resposta = _envio(admin, laudos=[(io.BytesIO(_pdf(FORMATO_C)), 'beneficiario-7.pdf'), (io.BytesIO(b'nao e pdf'), 'ruim.pdf')],
                      finalidade='rastreio', regime='ambulatorial')
    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    dados = resposta.get_json()
    assert dados['linhas'] and {linha['id_beneficiario'] for linha in dados['linhas']} == {'beneficiario-7'}
    assert any('beneficiario-7' in aviso and 'identificados' in aviso for aviso in dados['avisos'])
    assert any(aviso.startswith('ruim: não lido') for aviso in dados['avisos'])


def test_envio_vazio_grande_demais_ou_de_outro_site_e_recusado(admin):
    assert _envio(admin).status_code == 400
    assert _envio(admin, arquivo=_planilha('id_pedido;id_beneficiario\n')).status_code == 422
    muitas = PLANILHA.splitlines()[0] + '\n' + (PLANILHA.splitlines()[1] + '\n') * 2001
    assert _envio(admin, arquivo=_planilha(muitas)).status_code == 413
    de_fora = admin.post(ROTA, data={'arquivo': _planilha()}, content_type='multipart/form-data',
                         headers={'Origin': 'https://outro.exemplo'})
    assert de_fora.status_code == 403


def test_arquivo_enviado_nao_passa_para_o_disco(app):
    """O Werkzeug grava em arquivo temporário o envio com mais de 500 KiB; aqui ele fica na memória."""
    grande = io.BytesIO(b'x' * 700 * 1024)
    with app.test_request_context(ROTA, method='POST', data={'arquivo': (grande, 'pedidos.csv')},
                                  content_type='multipart/form-data'):
        from flask import request
        assert isinstance(request.files['arquivo'].stream, io.BytesIO)
