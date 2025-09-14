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


def _corsify(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp


def parse_date_ymd(date_str):
    """
    Parse date string in multiple formats: YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD
    Returns datetime object or None if invalid
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
    Calculate PREVENT 2024 cardiovascular risk
    """
    try:
        # Extract patient data
        age = float(patient_data.get('age', 0))
        sex = patient_data.get('sex', '').lower()

        # Clinical parameters
        sbp = float(patient_data.get('systolic_bp', 120))
        total_chol = float(patient_data.get('total_cholesterol', 200))
        hdl_chol = float(patient_data.get('hdl_cholesterol', 50))

        # Calculate non-HDL cholesterol
        non_hdl_chol = total_chol - hdl_chol

        # PREVENT 2024 coefficients (simplified version)
        if sex == 'masculino' or sex == 'male':
            # Male coefficients
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
        linear_pred = (
            coef_age * age
            + coef_sbp * sbp
            + coef_non_hdl * non_hdl_chol
        )

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
        print(f"Erro no c\u00e1lculo PREVENT: {e}")
        return {
            'risk_10_year': 0.0,
            'risk_30_year': 0.0,
        }


def get_risk_classification(risk_10yr):
    """
    Classify cardiovascular risk based on 10-year risk
    """
    if risk_10yr < 5:
        return {
            'level': 'Baixo Risco',
            'color': '#28a745',
            'interpretation': 'Baixo Risco. Manter estilo de vida saud\u00e1vel e acompanhamento de rotina.',
        }
    elif risk_10yr < 20:
        return {
            'level': 'Risco Intermedi\u00e1rio',
            'color': '#ffc107',
            'interpretation': 'Risco Intermedi\u00e1rio. Biomarcadores recomendados e interven\u00e7\u00e3o terap\u00e9utica.',
        }
    else:
        return {
            'level': 'Alto Risco',
            'color': '#dc3545',
            'interpretation': 'Alto Risco. Interven\u00e7\u00e3o terap\u00e9tica imediata e acompanhamento rigoroso.',
        }


def generate_recommendations(patient_data, risk_level):
    """
    Generate medical recommendations based on patient data and risk level
    """
    recommendations = []
    age = int(patient_data.get('age', 0))
    sex = patient_data.get('sex', '').lower()

    # Basic lab tests
    recommendations.extend([
        {
            'category': 'Exames Laboratoriais',
            'name': 'Glicemia de jejum',
            'priority': 'ALTA',
            'reference': 'ADA 2024',
        },
        {
            'category': 'Exames Laboratoriais',
            'name': 'Colesterol total e fra\u00e7\u00f5es',
            'priority': 'ALTA',
            'reference': 'AHA/ACC 2019',
        },
    ])

    # Age-specific recommendations
    if age >= 50:
        recommendations.append(
            {
                'category': 'Rastreamento de C\u00e2ncer',
                'name': 'Colonoscopia de Rastreio',
                'priority': 'ALTA',
                'reference': 'USPSTF 2021',
            }
        )

    # Sex-specific recommendations
    if sex in ['feminino', 'female'] and age >= 40:
        recommendations.append(
            {
                'category': 'Rastreamento de C\u00e2ncer',
                'name': 'Mamografia Digital Bilateral',
                'priority': 'ALTA',
                'reference': 'USPSTF 2016',
            }
        )

    if sex in ['masculino', 'male'] and age >= 50:
        recommendations.append(
            {
                'category': 'Rastreamento de C\u00e2ncer',
                'name': 'PSA total, soro',
                'priority': 'M\u00c9DIA',
                'reference': 'USPSTF 2018',
            }
        )

    # Risk-based recommendations
    if risk_level in ['Risco Intermedi\u00e1rio', 'Alto Risco']:
        recommendations.extend([
            {
                'category': 'Exames Laboratoriais',
                'name': 'Anti-HIV 1 e 2, soro',
                'priority': 'ALTA',
                'reference': 'CDC 2021',
            },
            {
                'category': 'Exames Laboratoriais',
                'name': 'HbA1c, soro',
                'priority': 'ALTA',
                'reference': 'ADA 2024',
            },
        ])

    # Vaccines
    recommendations.extend([
        {
            'category': 'Vacinas',
            'name': 'Vacina Influenza Tetravalente',
            'priority': 'ALTA',
            'reference': 'SBIm/ANVISA 2024',
        },
    ])

    return recommendations


@app.route('/checkup-intelligent', methods=['POST', 'OPTIONS'])
def handle_intelligent_checkup():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        # Get patient data from request (tolerante a JSON inv\u00e1lido/ausente)
        patient_data = request.get_json(silent=True) or {}

        # Normalizar tabagismo se helper existir neste contexto
        try:
            tabagismo_status, macos_ano = _parse_smoking_status_intelligent(
                patient_data.get('tabagismo'), patient_data
            )
            # Opcionalmente incorporar no patient_data normalizado
            patient_data['tabagismo_status'] = tabagismo_status
            patient_data['tabagismo_macos_ano'] = macos_ano
        except NameError:
            # Helper ausente; seguir sem quebrar
            pass

        # Calcular risco PREVENT
        risk_result = calculate_prevent_risk(patient_data)
        risk_classification = get_risk_classification(risk_result['risk_10_year'])

        # Gerar recomenda\u00e7\u00f5es
        recommendations = generate_recommendations(patient_data, risk_classification['level'])

        # Montar resposta
        response_data = {
            'success': True,
            'prevent_risk': risk_result,
            'risk_classification': risk_classification,
            'recommendations': recommendations,
            'total_recommendations': len(recommendations),
        }

        resp = jsonify(response_data)
        return _corsify(resp), 200

    except Exception as e:
        print(f"Erro na gera\u00e7\u00e3o de recomenda\u00e7\u00f5es: {e}")
        error_response = jsonify(
            {
                'success': False,
                'error': str(e),
                'message': 'Erro interno do servidor',
            }
        )
        return _corsify(error_response), 500
