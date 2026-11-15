"""Termos de Uso: página pública, aceite no cadastro e aceite pendente bloqueando o uso até ser dado."""
import itertools
import re

import pytest

from conftest import RAIZ, SENHA_DE_TESTE
from src.utils import termos

_seq = itertools.count(1)
PACIENTE = dict(idade=50, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], historia_familiar=[], medicacoes=[])


def _conta_sem_aceite(app, contas):
    """Conta já existente que ainda não aceitou a versão em vigor (como as contas antigas no deploy)."""
    n = next(_seq)
    u = contas.criar(f'termos{n}@exemplo.test', f'Dra. Termos {n}', f'CRM-GO 8{n:04d}', 'medico', SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    cliente = app.test_client()
    r = cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE})
    assert r.status_code == 200 and r.get_json()['termos_pendentes'] is True
    return cliente, u


def test_pagina_dos_termos_e_publica_e_oferece_o_pdf(anonimo):
    r = anonimo.get('/termos')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert f'data-versao="{termos.VERSAO}"' in html and f'datetime="{termos.DATA}"' in html
    assert f'href="/{termos.ARQUIVO}" download' in html and 'data-imprimir' in html
    for trecho in ('Rodolfo Cambraia Frota', 'CRM-GO 26.815', 'não substitui consulta nem julgamento médico',
                   'Resolução CFM nº 2.454/2026', 'Goiânia'):
        assert trecho in html, trecho
    # Referências legais com link clicável.
    for url in ('https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm',
                'https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2026/2454_2026.pdf'):
        assert f'href="{url}"' in html
    assert anonimo.get('/static/termos.js').status_code == 200


def test_pdf_dos_termos_e_servido_e_tem_a_pagina_de_assinatura(anonimo):
    from io import BytesIO
    from pypdf import PdfReader
    r = anonimo.get('/' + termos.ARQUIVO)
    assert r.status_code == 200 and r.mimetype == 'application/pdf'
    pdf = PdfReader(BytesIO(r.data))
    texto = ' '.join(p.extract_text() for p in pdf.pages)
    assert 'Termos de Uso' in texto and 'VERSÃO 2.0' in texto
    assert 'Declaração de leitura e aceite' in pdf.pages[-1].extract_text()
    assert 'Assinatura' in pdf.pages[-1].extract_text()
    links = {a.get_object()['/A'].get('/URI') for p in pdf.pages for a in (p.get('/Annots') or [])
             if '/A' in a.get_object()}
    assert 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm' in links


def test_paginas_linkam_os_termos():
    for pagina in ('index.html', 'cadastro.html', 'login.html', 'configurar.html', 'contact.html', 'conta.html',
                   'intelligent-tools.html'):
        assert 'href="/termos' in (RAIZ / pagina).read_text(encoding='utf-8'), pagina


def test_cadastro_sem_aceite_e_recusado_e_com_aceite_fica_registrado(anonimo, contas):
    dados = dict(email='aceite@exemplo.test', nome='Pessoa Aceite', perfil='medico', crm_uf='GO', crm_numero='5151',
                 senha=SENHA_DE_TESTE)
    r = anonimo.post('/api/auth/cadastro', json=dados)
    assert r.status_code == 400 and 'Termos de Uso' in ' '.join(r.get_json()['erros'])
    assert not any(u['email'] == 'aceite@exemplo.test' for u in contas.listar())
    assert anonimo.post('/api/auth/cadastro', json=dict(dados, aceite_termos='on')).status_code == 201
    u = next(u for u in contas.listar() if u['email'] == 'aceite@exemplo.test')
    assert contas.aceitou(u['id'], termos.VERSAO)


def test_conta_antiga_sem_aceite_nao_usa_nada_ate_aceitar(app, contas):
    cliente, u = _conta_sem_aceite(app, contas)
    # Páginas levam aos termos; API recusa com o aviso no cabeçalho.
    assert cliente.get('/intelligent-tools').headers['Location'] == '/termos?aceitar=1'
    assert cliente.get('/conta').headers['Location'].startswith('/termos?aceitar=1')
    r = cliente.post('/api/checkup-intelligent', json=PACIENTE)
    assert r.status_code == 403 and r.headers[termos.CABECALHO] == 'pendente'
    assert cliente.get('/api/auth/credenciamentos').status_code == 403
    assert cliente.get('/api/auth/eu').get_json()['termos_pendentes'] is True
    # Aceite de versão diferente da atual é recusado.
    assert cliente.post('/api/auth/termos/aceitar', json={'versao': '2000-01-01'}).status_code == 409
    assert cliente.post('/api/auth/termos/aceitar', json={'versao': termos.VERSAO}).status_code == 200
    assert cliente.get('/intelligent-tools').status_code == 200
    assert cliente.post('/api/checkup-intelligent', json=PACIENTE).status_code == 200
    assert cliente.get('/api/auth/eu').get_json()['termos_pendentes'] is False
    # Aceitar de novo não duplica.
    assert cliente.post('/api/auth/termos/aceitar', json={'versao': termos.VERSAO}).status_code == 200
    with contas._conexao() as executar:
        assert executar('SELECT COUNT(*) FROM aceites_termos WHERE usuario_id = ?', (u['id'],)).fetchone()[0] == 1


def test_administrador_tambem_aceita(app, contas, tmp_path, monkeypatch):
    """Banco vazio: só pode haver um administrador."""
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path / 'admin.sqlite'}")
    u = contas.criar('rt-termos@exemplo.test', 'Responsável', 'CRM-GO 3', 'medico', SENHA_DE_TESTE, administrador=True)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).get_json()['termos_pendentes']
    assert cliente.get('/admin').headers['Location'] == '/termos?aceitar=1&destino=admin'
    assert cliente.get('/api/admin/usuarios').status_code == 403
    cliente.post('/api/auth/termos/aceitar', json={'versao': termos.VERSAO})
    assert cliente.get('/api/admin/usuarios').status_code == 200


def test_nova_versao_pede_novo_aceite(app, contas, monkeypatch):
    cliente, _ = _conta_sem_aceite(app, contas)
    cliente.post('/api/auth/termos/aceitar', json={'versao': termos.VERSAO})
    assert cliente.get('/intelligent-tools').status_code == 200
    monkeypatch.setattr(termos, 'VERSAO', '2099-01-01')
    assert cliente.get('/intelligent-tools').status_code == 302


def test_aceite_exige_sessao(anonimo):
    assert anonimo.post('/api/auth/termos/aceitar', json={'versao': termos.VERSAO}).status_code == 401


def test_versao_do_modulo_e_a_da_pagina():
    html = (RAIZ / 'termos.html').read_text(encoding='utf-8')
    assert re.search(r'data-versao="([^"]+)"', html).group(1) == termos.VERSAO
    assert (RAIZ / termos.ARQUIVO).is_file() and termos.VERSAO in termos.ARQUIVO


def test_checkup_leva_aos_termos_quando_a_api_pede_aceite():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert "headers.get('X-Evidens-Termos')" in html and termos.CABECALHO == 'X-Evidens-Termos'
