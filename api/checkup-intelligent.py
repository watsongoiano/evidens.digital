from flask import Flask, request, jsonify
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
        linear_pred = (coef_age * age + 
                      coef_sbp * sbp + 
                      coef_non_hdl * non_hdl_chol)
        
        # Calculate 10-year risk
        risk_10yr = 1 - (baseline_survival_10yr ** math.exp(linear_pred))
        risk_10yr_percent = risk_10yr * 100
        
        # Calculate 30-year risk
        risk_30yr = 1 - (baseline_survival_30yr ** math.exp(linear_pred))
        risk_30yr_percent = risk_30yr * 100
        
        return {
            'risk_10_year': round(risk_10yr_percent, 1),
            'risk_30_year': round(risk_30yr_percent, 1)
        }
        
    except Exception as e:
        print(f"Erro no cálculo PREVENT: {e}")
        return {
            'risk_10_year': 0.0,
            'risk_30_year': 0.0
        }

def get_risk_classification(risk_10yr):
    """
    Classify cardiovascular risk based on 10-year risk
    """
    if risk_10yr < 5:
        return {
            'level': 'Baixo Risco',
            'color': '#28a745',
            'interpretation': 'Baixo Risco. Manter estilo de vida saudável e acompanhamento de rotina.'
        }
    elif risk_10yr < 20:
        return {
            'level': 'Risco Intermediário',
            'color': '#ffc107',
            'interpretation': 'Risco Intermediário. Biomarcadores recomendados e intervenção terapêutica.'
        }
    else:
        return {
            'level': 'Alto Risco',
            'color': '#dc3545',
            'interpretation': 'Alto Risco. Intervenção terapêutica imediata e acompanhamento rigoroso.'
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
            'reference': 'ADA 2024'
        },
        {
            'category': 'Exames Laboratoriais',
            'name': 'Colesterol total e frações',
            'priority': 'ALTA',
            'reference': 'AHA/ACC 2019'
        }
    ])
    
    # Age-specific recommendations
    if age >= 50:
        recommendations.append({
            'category': 'Rastreamento de Câncer',
            'name': 'Colonoscopia de Rastreio',
            'priority': 'ALTA',
            'reference': 'USPSTF 2021'
        })
    
    # Sex-specific recommendations
    if sex in ['feminino', 'female'] and age >= 40:
        recommendations.append({
            'category': 'Rastreamento de Câncer',
            'name': 'Mamografia Digital Bilateral',
            'priority': 'ALTA',
            'reference': 'USPSTF 2016'
        })
    
    if sex in ['masculino', 'male'] and age >= 50:
        recommendations.append({
            'category': 'Rastreamento de Câncer',
            'name': 'PSA total, soro',
            'priority': 'MÉDIA',
            'reference': 'USPSTF 2018'
        })
    
    # Risk-based recommendations
    if risk_level in ['Risco Intermediário', 'Alto Risco']:
        recommendations.extend([
            {
                'category': 'Exames Laboratoriais',
                'name': 'Anti-HIV 1 e 2, soro',
                'priority': 'ALTA',
                'reference': 'CDC 2021'
            },
            {
                'category': 'Exames Laboratoriais',
                'name': 'HbA1c, soro',
                'priority': 'ALTA',
                'reference': 'ADA 2024'
            }
        ])
    
    # Vaccines
    recommendations.extend([
        {
            'category': 'Vacinas',
            'name': 'Vacina Influenza Tetravalente',
            'priority': 'ALTA',
            'reference': 'SBIm/ANVISA 2024'
        }
    ])
    
    return recommendations

@app.route('/checkup-intelligent', methods=['POST', 'OPTIONS'])
def handle_intelligent_checkup():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Get patient data from request
        patient_data = request.get_json() or {}
        
        # Calculate PREVENT risk
        risk_result = calculate_prevent_risk(patient_data)
        risk_classification = get_risk_classification(risk_result['risk_10_year'])
        
        # Generate recommendations
        recommendations = generate_recommendations(patient_data, risk_classification['level'])
        
        # Prepare response
        response_data = {
            'success': True,
            'prevent_risk': risk_result,
            'risk_classification': risk_classification,
            'recommendations': recommendations,
            'total_recommendations': len(recommendations)
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Erro na geração de recomendações: {e}")
        error_response = jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro interno do servidor'
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

def handler(req):
    with app.test_request_context(path=req.path, method=req.method, 
                                   data=req.get_data(), headers=req.headers):
        return app.full_dispatch_request()
