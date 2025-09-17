# -*- coding: utf-8 -*-
"""
Lightweight smoke tests for key endpoints and behaviors:
- /checkup-intelligent returns recommendations with expected vaccines and reference links
- /gerar-solicitacao-exames and /gerar-receita-vacinas support HTML/JSON content negotiation

Run:
  python scripts/test_smoke.py
"""
from __future__ import annotations
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from app import app
except Exception as e:
    print(f"[FAIL] Could not import app: {e}")
    sys.exit(1)


def assert_true(cond: bool, msg: str):
    if not cond:
        print(f"[FAIL] {msg}")
        sys.exit(1)


def assert_no_private_network_header(resp, label: str):
    header_value = resp.headers.get('Access-Control-Allow-Private-Network')
    if header_value is None:
        return
    if isinstance(header_value, str) and header_value.strip().lower() == 'false':
        return
    assert_true(False, f"{label} leaked Access-Control-Allow-Private-Network={header_value!r}")


def post_json(client, path: str, payload: dict, headers: dict | None = None):
    return client.post(path, data=json.dumps(payload),
                       content_type='application/json', headers=headers or {})


def main():
    client = app.test_client()

    # 1) Male, 25y (HPV up to 45y, Hep B always)
    payload_25m = {
        'nome': 'Teste 25M',
        'idade': 25,
        'sexo': 'masculino',
        'pais_guideline': 'BR'
    }
    API = '/api'
    r1 = post_json(client, f'{API}/checkup-intelligent', payload_25m)
    assert_true(r1.status_code == 200, f"/checkup-intelligent 25M HTTP {r1.status_code}")
    assert_no_private_network_header(r1, '/checkup-intelligent (25M)')
    data1 = r1.get_json() or {}
    recs1 = data1.get('recommendations') or []
    titles1 = [(rec.get('titulo') or '').lower() for rec in recs1]
    assert_true(any('gardasil 9' in t for t in titles1), "HPV (Gardasil 9) not found for 25M")
    assert_true(any('hepatite b' in t for t in titles1), "Hepatite B not found for 25M")

    # Reference HTML presence (at least one rec with referencia_html)
    assert_true(any((rec.get('referencia_html') or '') for rec in recs1),
                "No referencia_html found in recommendations (25M)")

    # 2) Male, 55y (Pneumococcal >=50y)
    payload_55m = {
        'nome': 'Teste 55M',
        'idade': 55,
        'sexo': 'masculino',
        'pais_guideline': 'BR'
    }
    r2 = post_json(client, f'{API}/checkup-intelligent', payload_55m)
    assert_true(r2.status_code == 200, f"/checkup-intelligent 55M HTTP {r2.status_code}")
    assert_no_private_network_header(r2, '/checkup-intelligent (55M)')
    data2 = r2.get_json() or {}
    recs2 = data2.get('recommendations') or []
    titles2 = [(rec.get('titulo') or '').lower() for rec in recs2]
    assert_true(any('vpc15' in t or 'vpc13' in t for t in titles2),
                "Pneumococcal VPC15/VPC13 not found for 55M")
    assert_true(any('vpp23' in t for t in titles2),
                "Pneumococcal VPP23 not found for 55M")

    # Generate documents inputs
    patient_doc = {'nome': 'Paciente Teste', 'sexo': 'masculino'}
    sample_lab = {
        'titulo': 'Hemoglobina glicada (HbA1c), soro',
        'descricao': 'Avaliação do controle glicêmico',
        'categoria': 'laboratorio',
        'referencia_html': 'Diretriz MS 2024'
    }
    sample_imagem = {
        'titulo': 'Mamografia bilateral digital',
        'descricao': 'Rastreamento de neoplasia de mama',
        'categoria': 'imagem',
        'referencia_html': 'Diretriz MS 2024'
    }
    doc_payload = {
        'recommendations': recs2 + [sample_lab, sample_imagem],
        'patient_data': patient_doc
    }

    # 3) Exams request: JSON
    r3_json = post_json(client, f'{API}/gerar-solicitacao-exames', doc_payload,
                        headers={'Accept': 'application/json'})
    assert_true(r3_json.status_code == 200, f"/gerar-solicitacao-exames JSON HTTP {r3_json.status_code}")
    assert_true((r3_json.content_type or '').startswith('application/json'),
                f"Expected JSON content-type, got {r3_json.content_type}")
    assert_no_private_network_header(r3_json, '/gerar-solicitacao-exames (JSON)')
    data3 = r3_json.get_json() or {}
    available_docs = data3.get('available_documents') or []
    lab_doc = data3.get('laboratorial') or {}
    img_doc = data3.get('imagem') or {}
    assert_true('laboratorial' in available_docs,
                "Laboratory document not advertised in JSON response")
    assert_true('imagem' in available_docs,
                "Imaging document not advertised in JSON response")
    assert_true(bool(lab_doc.get('html')),
                "JSON response missing laboratory document HTML for /gerar-solicitacao-exames")
    assert_true(bool(img_doc.get('html')),
                "JSON response missing imaging document HTML for /gerar-solicitacao-exames")
    assert_true(lab_doc.get('document_code', '').startswith('CFMP-SE-LAB-'),
                "Laboratory document code missing or incorrect")
    assert_true(img_doc.get('document_code', '').startswith('CFMP-SE-IMG-'),
                "Imaging document code missing or incorrect")
    assert_true(lab_doc.get('filename') and img_doc.get('filename') and lab_doc.get('filename') != img_doc.get('filename'),
                "Document filenames should be distinct between lab and imaging")

    # 4) Exams request: HTML (laboratory)
    r3_lab_html = post_json(client, f'{API}/gerar-solicitacao-exames?documento=laboratorial', doc_payload,
                            headers={'Accept': 'text/html'})
    assert_true(r3_lab_html.status_code == 200, f"/gerar-solicitacao-exames HTML lab HTTP {r3_lab_html.status_code}")
    assert_true((r3_lab_html.content_type or '').startswith('text/html'),
                f"Expected HTML content-type, got {r3_lab_html.content_type}")
    lab_html_text = (r3_lab_html.get_data(as_text=True) or '').lstrip()
    assert_true(lab_html_text.startswith('<!DOCTYPE html>'),
                "Laboratory HTML response does not look like HTML")
    assert_true('CFMP-SE-LAB-' in lab_html_text,
                "Laboratory HTML missing unique identifier")
    assert_no_private_network_header(r3_lab_html, '/gerar-solicitacao-exames (HTML-LAB)')

    # 5) Exams request: HTML (imaging)
    r3_img_html = post_json(client, f'{API}/gerar-solicitacao-exames?documento=imagem', doc_payload,
                            headers={'Accept': 'text/html'})
    assert_true(r3_img_html.status_code == 200, f"/gerar-solicitacao-exames HTML imagem HTTP {r3_img_html.status_code}")
    assert_true((r3_img_html.content_type or '').startswith('text/html'),
                f"Expected HTML content-type, got {r3_img_html.content_type}")
    img_html_text = (r3_img_html.get_data(as_text=True) or '').lstrip()
    assert_true(img_html_text.startswith('<!DOCTYPE html>'),
                "Imaging HTML response does not look like HTML")
    assert_true('CFMP-SE-IMG-' in img_html_text,
                "Imaging HTML missing unique identifier")
    assert_no_private_network_header(r3_img_html, '/gerar-solicitacao-exames (HTML-IMG)')

    # 6) Exams request: HTML selection page when no tipo specified
    r3_select = post_json(client, f'{API}/gerar-solicitacao-exames', doc_payload,
                          headers={'Accept': 'text/html'})
    assert_true(r3_select.status_code == 200, f"/gerar-solicitacao-exames HTML selection HTTP {r3_select.status_code}")
    assert_true((r3_select.content_type or '').startswith('text/html'),
                f"Expected HTML content-type, got {r3_select.content_type}")
    selection_html = r3_select.get_data(as_text=True) or ''
    assert_true('documento=laboratorial' in selection_html and 'documento=imagem' in selection_html,
                "Selection HTML does not list both document links")
    assert_no_private_network_header(r3_select, '/gerar-solicitacao-exames (HTML-selection)')

    # 7) Vaccine prescription: JSON
    r4_json = post_json(client, f'{API}/gerar-receita-vacinas', doc_payload,
                        headers={'Accept': 'application/json'})
    assert_true(r4_json.status_code == 200, f"/gerar-receita-vacinas JSON HTTP {r4_json.status_code}")
    assert_true((r4_json.content_type or '').startswith('application/json'),
                f"Expected JSON content-type, got {r4_json.content_type}")
    assert_no_private_network_header(r4_json, '/gerar-receita-vacinas (JSON)')
    data4 = r4_json.get_json() or {}
    assert_true(bool(data4.get('html')),
                "JSON response missing 'html' for /gerar-receita-vacinas")

    # 8) Vaccine prescription: HTML
    r4_html = post_json(client, f'{API}/gerar-receita-vacinas', doc_payload,
                        headers={'Accept': 'text/html'})
    assert_true(r4_html.status_code == 200, f"/gerar-receita-vacinas HTML HTTP {r4_html.status_code}")
    assert_true((r4_html.content_type or '').startswith('text/html'),
                f"Expected HTML content-type, got {r4_html.content_type}")
    assert_true((r4_html.get_data(as_text=True) or '').lstrip().startswith('<!DOCTYPE html>'),
                "HTML response does not look like HTML for /gerar-receita-vacinas")
    assert_no_private_network_header(r4_html, '/gerar-receita-vacinas (HTML)')

    print("[OK] Smoke tests passed.")


if __name__ == '__main__':
    main()
