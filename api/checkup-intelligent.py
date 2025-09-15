from flask import Flask, request, jsonify, make_response
import sys
import os
import json
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

app = Flask(__name__)
@app.route('/health', methods=['GET'])
def health():
    return make_response('ok', 200)


def _corsify(resp):
    """Add basic CORS headers to a Flask response object."""
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp


def parse_date_ymd(date_str):
    """
    Parse date string in multiple formats: YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD.
    Returns a datetime object or None if invalid.
    """
    if not date_str or date_str is None:
        return None

    try:
        # Remove any extra whitespace
        date_str = str(date_str).strip()
        if not date_str or date_str.lower() in ['null', 'none', '']:
            return None

        # Try YYYY-MM-DD format first
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            pass

        # Try DD/MM/YYYY format
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            pass

        # Try YYYY/MM/DD format
        try:
            return datetime.strptime(date_str, '%Y/%m/%d')
        except ValueError:
            pass

    except (ValueError, TypeError, AttributeError):
        pass

    return None


def calculate_prevent_risk(patient_data):
    """
    Calculate PREVENT 2024 cardiovascular risk.

    Attempts to cast the age to float; if conversion fails, defaults to 0.0.
    """
    try:
        # Extract patient data
        age_raw = patient_data.get('age', 0)
        try:
            age = float(age_raw) if age_raw not in (None, '') else 0.0
        except (ValueError, TypeError):
            age = 0.0
        sex = patient_data.get('sex', '').lower()

        # Clinical parameters with safe conversion
        try:
            sbp = float(patient_data.get('systolic_bp', 120))
        except (ValueError, TypeError):
            sbp = 120.0
        try:
            total_chol = float(patient_data.get('total_cholesterol', 200))
        except (ValueError, TypeError):
            total_chol = 200.0
        try:
            hdl_chol = float(patient_data.get('hdl_cholesterol', 50))
        except (ValueError, TypeError):
            hdl_chol = 50.0

        # Calculate non-HDL cholesterol
        non_hdl_chol = total_chol - hdl_chol

        # PREVENT 2024 coefficients (simplified version)
        if sex in ['masculino', 'male']:
            coef_age = 0.0654
            coef_sbp = 0.0089
            coef_non_hdl = 0.0039
            baseline_survival_10yr = 0.9533
            baseline_survival_30yr = 0.7663
        else:
            # Female coefficients
            coef_age = 0.0711
            coef_sbp = 0.0134
            coef_non_hdl = 0.0042
            baseline_survival_10yr = 0.9665
            baseline_survival_30yr = 0.8353

        # Calculate linear predictor
        linear_pred = (coef_age * age) + (coef_sbp * sbp) + (coef_non_hdl * non_hdl_chol)

        # Calculate 10-year risk
        risk_10yr = 1 - (baseline_survival_10yr ** math.exp(linear_pred))
        risk_10yr_percent = risk_10yr * 100

        # Calculate 30-year risk
        risk_30yr = 1 - (baseline_survival_30yr ** math.exp(linear_pred))
        risk_30yr_percent = risk_30yr * 100

        return {
            'risk_10_year': round(risk_10yr_percent, 1),
            'risk_30_year': round(risk_30yr_percent, 1),
        }

    except Exception as e:
        print(f"Erro no cálculo PREVENT: {e}")
        return {
            'risk_10_year': 0.0,
            'risk_30_year': 0.0,
        }


def get_risk_classification(risk_10yr):
    """
    Classify cardiovascular risk based on 10-year risk.
    """
    if risk_10yr < 5:
        return {
            'level': 'Baixo Risco',
            'color': '#28a745',
            'interpretation': 'Baixo Risco. Manter estilo de vida saudável e acompanhamento de rotina.',
        }
    elif risk_10yr < 20:
        return {
            'level': 'Risco Intermediário',
            'color': '#ffc107',
            'interpretation': 'Risco Intermediário. Biomarcadores recomendados e intervenção terapêutica.',
        }
    else:
        return {
            'level': 'Alto Risco',
            'color': '#dc3545',
            'interpretation': 'Alto Risco. Intervenção terapêutica imediata e acompanhamento rigoroso.',
        }


def generate_recommendations(patient_data, risk_level):
    """
    Generate medical recommendations based on patient data and risk level.
    Produces items with keys: titulo, descricao, categoria, prioridade, referencia
    """
    recommendations = []
    # Normalize fields
    age_val = patient_data.get('age', 0)
    try:
        age = int(age_val) if age_val not in (None, '') else 0
    except (ValueError, TypeError):
        age = 0
    sex = (patient_data.get('sex') or '').lower()

    def add_unique(rec):
        t = (rec.get('titulo') or '').strip().lower()
        if not t:
            return
        if any((r.get('titulo') or '').strip().lower() == t for r in recommendations):
            return
        recommendations.append(rec)

    # Básicos laboratoriais
    add_unique({
        'titulo': 'Glicemia de jejum',
        'descricao': 'ADA 2024: Rastreamento universal ≥35 anos',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'ADA 2024',
    })
    add_unique({
        'titulo': 'Colesterol total e frações, soro',
        'descricao': 'Colesterol total, HDL, LDL e triglicerídeos',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'AHA/ACC 2025',
    })

    # ECG
    add_unique({
        'titulo': 'Eletrocardiograma de repouso',
        'descricao': 'ECG de 12 derivações - ≥40 anos ou com comorbidades',
        'categoria': 'imagem',
        'prioridade': 'alta',
        'referencia': 'SBC 2019 / AHA/ACC 2019',
    })

    # Sexo/Idade
    if sex in ['feminino', 'female'] and 40 <= age <= 74:
        add_unique({
            'titulo': 'Mamografia Digital - Bilateral',
            'descricao': 'Mamografia bienal (40-74 anos)',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2024 Grau B',
        })
    if sex in ['feminino', 'female'] and 21 <= age <= 65:
        add_unique({
            'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular',
            'descricao': 'Papanicolaou/HPV a cada 3 anos (21-65 anos)',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'USPSTF Grau A',
        })
    if sex in ['masculino', 'male'] and age >= 50:
        add_unique({
            'titulo': 'PSA total, soro',
            'descricao': 'Rastreamento de câncer de próstata (≥50 anos)',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'USPSTF 2018 Grau C',
        })

    # Colonoscopia (45-75)
    if 45 <= age <= 75:
        add_unique({
            'titulo': 'Colonoscopia de Rastreio com ou sem biópsia',
            'descricao': 'Colonoscopia a cada 10 anos (45-75 anos)',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2021 Grau B',
        })

    # Vacinas
    add_unique({
        'titulo': 'Vacina Influenza Tetravalente',
        'descricao': 'Dose anual. Aplicar dose única IM anualmente.',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm/ANVISA 2024',
    })

    if age <= 45:
        prioridade_hpv = 'alta' if age <= 26 else 'media'
        add_unique({
            'titulo': 'Gardasil 9® (Vacina Papilomavírus Humano 9-Valente)',
            'descricao': '3 doses. Aplicar 0, 2 e 6 meses.',
            'categoria': 'vacina',
            'prioridade': prioridade_hpv,
            'referencia': 'SBIm/ANVISA 2024',
        })

    add_unique({
        'titulo': 'Hepatite B (VHB)',
        'descricao': 'Esquema de 3 doses (0, 1, 6 meses) em não vacinados.',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm/ANVISA 2024',
    })

    if age >= 50:
        add_unique({
            'titulo': 'VPC15 (Vaxneuvance®) ou VPC13, 0,5ml',
            'descricao': '1 dose. Pode ser coadministrada com Shingrix®, Efluelda® e Arexvy®',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm/ANVISA 2024',
        })
        add_unique({
            'titulo': 'VPP23, 0,5ml',
            'descricao': '1 dose 6 meses após VPC15/VPC13; reforço após 5 anos',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm/ANVISA 2024',
        })

    # Risco intermediário/alto: biomarcadores adicionais
    if risk_level in ['Risco Intermediário', 'Alto Risco']:
        add_unique({
            'titulo': 'Anti-HIV 1 e 2, soro',
            'descricao': 'Teste para detecção de HIV',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'MS 2024 / USPSTF',
        })
        add_unique({
            'titulo': 'HbA1c, soro',
            'descricao': 'Hemoglobina glicada',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ADA 2024',
        })

    return recommendations


@app.route('/checkup-intelligent', methods=['POST', 'OPTIONS'])
def handle_intelligent_checkup():
    """
    Handle POST/OPTIONS requests for intelligent checkup.
    Implements CORS, safe JSON parsing, safe age normalization and error handling.
    """
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        # Get patient data from request (tolerant to missing/invalid JSON)
        patient_data = request.get_json(silent=True) or {}

        # Normalize age: treat empty string as 0; return HTTP 400 for invalid age
        idade_raw = patient_data.get('idade') or patient_data.get('age')
        # Remove whitespace and handle None
        if isinstance(idade_raw, str):
            idade_str = idade_raw.strip()
        else:
            idade_str = idade_raw
        if not idade_str:
            age = 0
        else:
            try:
                age = int(idade_str)
            except (ValueError, TypeError):
                error_response = jsonify({
                    'success': False,
                    'error': 'Idade inválida',
                    'message': 'O campo idade deve ser um número inteiro',
                })
                return _corsify(error_response), 400
        # Store sanitized age under unified key
        patient_data['age'] = age

        # Normalize smoking status if helper exists in this context
        try:
            tabagismo_status, macos_ano = _parse_smoking_status_intelligent(
                patient_data.get('tabagismo'), patient_data
            )
            patient_data['tabagismo_status'] = tabagismo_status
            patient_data['tabagismo_macos_ano'] = macos_ano
        except NameError:
            # Helper absent; continue without raising
            pass

        # Calculate PREVENT risk
        risk_result = calculate_prevent_risk(patient_data)
        risk_classification = get_risk_classification(risk_result['risk_10_year'])

        # Generate and normalize recommendations
        raw_recs = generate_recommendations(patient_data, risk_classification['level'])

        # Build reference links using shared util if available
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
            from src.utils.reference_links import build_reference_links, build_reference_html  # type: ignore
        except Exception:
            build_reference_links = None
            build_reference_html = None

        normalized = []
        for r in raw_recs:
            # Map keys
            titulo = (r.get('titulo') or r.get('name') or '').strip()
            # Categoria
            cat_raw = (r.get('categoria') or r.get('category') or '').lower()
            if 'vacina' in cat_raw:
                categoria = 'vacina'
            elif 'imagem' in cat_raw:
                categoria = 'imagem'
            elif 'rastreamento' in cat_raw or any(k in titulo.lower() for k in ['mamografia','colonoscopia','citologia','psa','tomografia']):
                categoria = 'rastreamento'
            elif 'laborator' in cat_raw or any(k in titulo.lower() for k in ['hba1c','glicemia','colesterol','hdl','ldl']):
                categoria = 'laboratorial'
            else:
                # Fallback heuristic by keywords
                categoria = 'laboratorio' if any(k in titulo.lower() for k in ['glicemia','colesterol','hiv','hbv','hcv','hba1c','psa']) else 'outras'

            prioridade = (r.get('prioridade') or r.get('priority') or 'media').strip().lower()
            # Normalize to alta|media|baixa
            if prioridade not in ['alta','media','baixa']:
                prioridade = 'media'
            descricao = r.get('descricao') or r.get('description') or ''
            referencia = r.get('referencia') or r.get('reference') or 'USPSTF/ADA/KDIGO/CDC'

            rec = {
                'titulo': titulo,
                'descricao': descricao,
                'categoria': categoria,
                'prioridade': prioridade,
                'referencia': referencia,
            }
            # Enrich references
            try:
                if build_reference_links and build_reference_html:
                    links = build_reference_links(titulo, referencia)
                    if links:
                        rec['referencias'] = links
                        rec['referencia_html'] = build_reference_html(links)
            except Exception:
                pass
            normalized.append(rec)

        # Build response
        response_data = {
            'success': True,
            'prevent_risk': risk_result,
            'risk_classification': risk_classification,
            'recommendations': normalized,
            'total_recommendations': len(normalized),
        }

        resp = jsonify(response_data)
        return _corsify(resp), 200

    except Exception as e:
        # Log error and return a generic server error
        print(f"Erro na geração de recomendações: {e}")
        error_response = jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro interno do servidor',
        })
        return _corsify(error_response), 500


@app.route('/', methods=['POST', 'OPTIONS'])
def root_checkup():
    """
    Allow posting to the function root ("/api/checkup-intelligent") on Vercel.
    This mirrors the same behavior as posting to "/checkup-intelligent".
    """
    return handle_intelligent_checkup()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000)
