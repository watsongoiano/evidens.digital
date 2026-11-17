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


def test_listas_do_check_up_e_dados_do_paciente_no_envio_dos_laudos(admin, client):
    assert client.get('/api/admin/operadoras/listas').status_code == 403
    listas = admin.get('/api/admin/operadoras/listas').get_json()
    assert {'valor': 'hipertensao', 'rotulo': 'Hipertensão'} in listas['comorbidades']
    assert any(item['valor'] == 'sinvastatina' for item in listas['medicacoes'])

    def cores(**campos):
        resposta = _envio(admin, laudos=[(io.BytesIO(_pdf(FORMATO_C)), 'beneficiario-7.pdf')], finalidade='rastreio',
                          regime='ambulatorial', **campos)
        assert resposta.status_code == 200, resposta.get_data(as_text=True)
        return {linha['exame']: linha['cor'] for linha in resposta.get_json()['linhas']}

    sem, com = cores(), cores(comorbidades=['hipertensao', 'chave_inventada'], medicacoes=['sinvastatina'])
    liberados = [exame for exame in com if com[exame] == 'verde' and sem[exame] != 'verde']
    assert liberados, (sem, com)                  # a hipertensão informada libera exames que sem ela seriam barrados


def test_dados_completos_do_paciente_no_formato_do_check_up(admin):
    """O formulário completo do check-up (ou, no futuro, o cadastro da operadora) envia `paciente` em JSON."""
    import json

    def envio(paciente):
        return _envio(admin, laudos=[(io.BytesIO(_pdf(FORMATO_C)), 'beneficiario-7.pdf')], finalidade='rastreio',
                      regime='ambulatorial', paciente=json.dumps(paciente))

    base = {'idade': 61, 'sexo': 'masculino', 'tabagismo': 'nunca_fumou'}
    sem = envio(base)
    assert sem.status_code == 200, sem.get_data(as_text=True)
    com = envio({**base, 'comorbidades': ['hipertensao', 'diabetes'], 'nome_paciente': 'não entra',
                 'exames_anteriores': [{'exame': 'Creatinina, soro', 'data': '2026-11-01'}]})
    assert com.status_code == 200, com.get_data(as_text=True)
    cores = lambda r: {l['exame']: l['cor'] for l in r.get_json()['linhas']}
    assert [e for e in cores(com) if cores(com)[e] == 'verde' and cores(sem)[e] != 'verde']
    assert com.get_json()['avisos'][0].startswith('Comparado com o check-up do paciente')
    assert {l['id_pedido'][:14] for l in com.get_json()['linhas']} == {'beneficiario-7'}
    # Dado inválido volta com a mensagem do motor; JSON quebrado é recusado.
    assert envio({'idade': 300, 'sexo': 'masculino', 'tabagismo': 'nunca_fumou'}).status_code == 422
    assert _envio(admin, laudos=[(io.BytesIO(_pdf(FORMATO_C)), 'x.pdf')], paciente='{').status_code == 400


def test_check_up_tem_o_modo_operadora_ligado_a_rota_do_administrador(admin):
    pagina = admin.get('/intelligent-tools?modo=operadora').get_data(as_text=True)
    assert 'id="operadoraPedido"' in pagina and "/api/admin/operadoras/classificar" in pagina
    assert 'href="/intelligent-tools?modo=operadora"' in admin.get('/operadoras').get_data(as_text=True)
