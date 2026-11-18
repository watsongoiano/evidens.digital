"""Cabeçalhos de segurança de toda resposta (api/index.py, `_cabecalhos_de_seguranca`).

Além de conferir que os cabeçalhos saem, os testes leem as páginas para garantir que a política não quebra
o que elas usam: formulário com destino externo, PDF exibido por <object>, moldura do próprio site e
scripts e estilos servidos com o tipo certo (exigido pelo `nosniff`).
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from flask import Response

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS_HTML = sorted(RAIZ.glob('*.html'))


@pytest.fixture(scope='module')
def indice(app):
    """Variáveis do módulo api/index.py (o mesmo que a Vercel executa)."""
    return app.view_functions['index'].__globals__


def _politica(indice):
    """Diretivas da Content-Security-Policy: {nome: [valores]}."""
    partes = [d.split() for d in indice['CABECALHOS_DE_SEGURANCA']['Content-Security-Policy'].split(';')]
    return {p[0]: p[1:] for p in partes if p}


def _conferir(resposta, indice):
    for nome, valor in indice['CABECALHOS_DE_SEGURANCA'].items():
        assert resposta.headers.get(nome) == valor, nome


@pytest.mark.parametrize('rota, status', [
    ('/', 200),                                               # página pública
    ('/intelligent-tools', 200),                              # página que exige login
    ('/intelligent-tools?modo=operadora&embutido=1', 200),    # a mesma página, embutida pela página das operadoras
    ('/login', 302),                                          # redirecionamento
    ('/static/evidens.css', 200),                             # arquivo publicado
    ('/static/termos/evidens-termos-de-uso-v2.0.pdf', 200),   # PDF exibido por <object> na página dos Termos
    ('/vercel.json', 404),                                    # arquivo não publicado
    ('/api/rota-que-nao-existe', 404),
])
def test_toda_resposta_leva_os_cabecalhos(client, indice, rota, status):
    resposta = client.get(rota)
    assert resposta.status_code == status
    _conferir(resposta, indice)


def test_respostas_da_api_e_recusas_levam_os_cabecalhos(anonimo, client, indice):
    sem_login = anonimo.post('/api/checkup-intelligent', json={})
    assert sem_login.status_code == 401
    _conferir(sem_login, indice)
    de_outro_site = client.post('/api/checkup-intelligent', json={}, headers={'Origin': 'https://outro-site.example'})
    assert de_outro_site.status_code == 403
    _conferir(de_outro_site, indice)


def test_paginas_so_podem_ser_emolduradas_pelo_proprio_site(indice):
    """A página das operadoras embute o check-up: a moldura do próprio site é permitida, a de fora não."""
    assert indice['CABECALHOS_DE_SEGURANCA']['X-Frame-Options'] == 'SAMEORIGIN'
    assert _politica(indice)['frame-ancestors'] == ["'self'"]
    assert 'data-formulario src="/intelligent-tools' in (RAIZ / 'operadoras.html').read_text(encoding='utf-8')


def test_rota_que_define_o_proprio_cabecalho_o_mantem(app, indice):
    """A página de retorno da assinatura digital pede `no-referrer`; o padrão não a sobrescreve."""
    with app.test_request_context('/'):
        resposta = app.process_response(Response('ok', headers={'Referrer-Policy': 'no-referrer'}))
    assert resposta.headers['Referrer-Policy'] == 'no-referrer'
    assert resposta.headers['X-Content-Type-Options'] == 'nosniff'
    assert resposta.headers.getlist('Referrer-Policy') == ['no-referrer']


def test_formularios_das_paginas_so_enviam_para_destinos_liberados(indice):
    """`form-action` barra o envio de formulário para fora: todo destino externo das páginas precisa estar na lista,
    e a lista não guarda destino que nenhuma página usa."""
    liberados = set(_politica(indice)['form-action']) - {"'self'"}
    assert liberados == set(indice['DESTINOS_DE_FORMULARIO'])
    usados = set()
    for pagina in PAGINAS_HTML:
        for destino in re.findall(r'<form\b[^>]*\baction="([^"]+)"', pagina.read_text(encoding='utf-8'), re.IGNORECASE):
            if destino.startswith(('http://', 'https://', '//')):
                partes = urlsplit(destino)
                usados.add(f'{partes.scheme}://{partes.netloc}')
    assert usados == liberados


def test_objetos_e_molduras_das_paginas_sao_do_proprio_site(indice):
    """`object-src 'self'` e a moldura só do próprio site: nenhuma página embute conteúdo de outro endereço."""
    assert _politica(indice)['object-src'] == ["'self'"]
    encontrados = []
    for pagina in PAGINAS_HTML:
        html = pagina.read_text(encoding='utf-8')
        encontrados += re.findall(r'<(?:object\b[^>]*\bdata|embed\b[^>]*\bsrc|iframe\b[^>]*\bsrc)="([^"]+)"', html, re.IGNORECASE)
    assert encontrados, 'esperava ao menos o PDF dos Termos e o formulário embutido das operadoras'
    assert all(endereco.startswith('/') and not endereco.startswith('//') for endereco in encontrados), encontrados


def test_paginas_nao_definem_base(indice):
    assert _politica(indice)['base-uri'] == ["'self'"]
    for pagina in PAGINAS_HTML:
        assert not re.search(r'<base\b', pagina.read_text(encoding='utf-8'), re.IGNORECASE), pagina.name


def test_scripts_e_estilos_publicados_saem_com_o_tipo_certo(client, indice):
    """Com `nosniff`, o navegador recusa script ou folha de estilo servidos com outro tipo."""
    tipos = {'.js': {'text/javascript', 'application/javascript'}, '.css': {'text/css'}}
    conferidos = 0
    for arquivo in sorted(indice['ARQUIVOS_PUBLICOS']):
        esperado = tipos.get(Path(arquivo).suffix)
        if esperado:
            resposta = client.get('/' + arquivo)
            assert resposta.status_code == 200 and resposta.mimetype in esperado, (arquivo, resposta.mimetype)
            conferidos += 1
    assert conferidos >= 5
