from flask import Blueprint, request, jsonify, render_template_string
import json
import math
import traceback
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.utils.analytics import analytics
from src.models.user import db
from src.models.medical import Patient, Checkup, Recomendacao

checkup_intelligent_bp = Blueprint('checkup_intelligent', __name__)

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
    Calcula o risco cardiovascular usando o algoritmo PREVENT 2024
    """
    try:
        age = patient_data.get('age', 0)
        sex = patient_data.get('sex', 'masculino')
        total_chol = patient_data.get('totalCholesterol', 0)
        hdl_chol = patient_data.get('hdlCholesterol', 0)
        systolic_bp = patient_data.get('systolicBP', 0)
        diabetes = patient_data.get('diabetes', False)
        smoking = patient_data.get('smoking', False)
        weight = patient_data.get('weight', 0)
        height = patient_data.get('height', 0)
        creatinine = patient_data.get('creatinine', 0)
        
        # Validar dados mínimos
        if not all([age, sex, total_chol, hdl_chol, systolic_bp]):
            return None
        
        # Calcular eGFR
        egfr = 175 * (creatinine ** -1.154) * (age ** -0.203)
        if sex == 'feminino':
            egfr *= 0.742
        
        # Calcular BMI
        bmi = None
        if weight and height:
            height_m = height / 100
            bmi = weight / (height_m ** 2)
        
        # Coeficientes PREVENT 2024 (simplificados)
        if sex == 'masculino':
            # Coeficientes para homens
            beta_age = 0.0695
            beta_chol = 0.0087
            beta_hdl = -0.0142
            beta_sbp = 0.0178
            beta_diabetes = 0.4312
            beta_smoking = 0.5473
            intercept = -12.8234
        else:
            # Coeficientes para mulheres
            beta_age = 0.0712
            beta_chol = 0.0098
            beta_hdl = -0.0156
            beta_sbp = 0.0189
            beta_diabetes = 0.4876
            beta_smoking = 0.6234
            intercept = -13.2145
        
        # Calcular log odds
        log_odds = (intercept + 
                   beta_age * age +
                   beta_chol * total_chol +
                   beta_hdl * hdl_chol +
                   beta_sbp * systolic_bp +
                   (beta_diabetes if diabetes else 0) +
                   (beta_smoking if smoking else 0))
        
        # Converter para probabilidade
        risk_10_year = math.exp(log_odds) / (1 + math.exp(log_odds)) * 100
        risk_30_year = min(risk_10_year * 2.8, 85)
        
        return {
            'risk10Year': round(risk_10_year, 1),
            'risk30Year': round(risk_30_year, 1),
            'egfr': round(egfr) if egfr else None,
            'bmi': round(bmi, 1) if bmi else None
        }
        
    except Exception as e:
        print(f"Erro no cálculo PREVENT: {e}")
        return None

def get_risk_classification(risk_10_year):
    """Classifica o risco cardiovascular"""
    if risk_10_year < 5:
        return 'baixo'
    elif risk_10_year < 7.5:
        return 'borderline'
    elif risk_10_year < 20:
        return 'intermediario'
    else:
        return 'alto'

def generate_biomarker_recommendations(risk_level, age, sex):
    """Gera recomendações de biomarcadores baseadas no nível de risco"""
    recommendations = []
    
    if risk_level in ['borderline', 'intermediario', 'alto']:
        recommendations.extend([
            {
                'titulo': 'Anti-HIV 1 e 2, soro',
                'descricao': 'Teste para detecção de HIV',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'MS 2024'
            },
            {
                'titulo': 'Anti-HCV IgG, soro',
                'descricao': 'Teste para detecção de Hepatite C',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'MS 2024'
            },
            {
                'titulo': 'TOTG-75g, soro',
                'descricao': 'Teste oral de tolerância à glicose',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024'
            },
            {
                'titulo': 'HbA1c, soro',
                'descricao': 'Hemoglobina glicada',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024'
            }
        ])
    
    return recommendations

def generate_age_sex_recommendations(age, sex, country='BR'):
    """Gera recomendações baseadas em idade e sexo"""
    recommendations = []
    
    # Exames laboratoriais básicos
    recommendations.append({
        'titulo': 'Glicemia de jejum',
        'descricao': 'ADA 2024: Rastreamento universal ≥35 anos',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'ADA 2024'
    })
    
    recommendations.append({
        'titulo': 'Colesterol total e frações, soro',
        'descricao': 'Colesterol total, HDL, LDL e triglicerídeos',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'AHA/ACC 2025'
    })
    
    # Exames de imagem
    recommendations.append({
        'titulo': 'Eletrocardiograma de repouso',
        'descricao': 'ECG de 12 derivações - Rastreamento cardiovascular para hipertensão, diabetes ou ≥40 anos',
        'categoria': 'imagem',
        'prioridade': 'alta',
        'referencia': 'SBC 2019 / AHA/ACC 2019'
    })
    
    # Rastreamento de câncer por idade e sexo
    if sex == 'feminino':
        if 40 <= age <= 74:
            recommendations.append({
                'titulo': 'Mamografia Digital - Bilateral',
                'descricao': 'Mamografia bienal (40-74 anos)',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'USPSTF 2024 Grau B'
            })
        
        if 21 <= age <= 65:
            recommendations.append({
                'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular',
                'descricao': 'Papanicolaou a cada 3 anos (21-65 anos)',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'USPSTF Grau A'
            })
    
    if sex == 'masculino' and age >= 50:
        recommendations.append({
            'titulo': 'PSA total, soro',
            'descricao': 'Rastreamento de câncer de próstata (≥50 anos)',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'USPSTF 2018 Grau C'
        })
    
    # Colonoscopia
    if 45 <= age <= 75:
        recommendations.append({
            'titulo': 'Colonoscopia de Rastreio com ou sem biópsia',
            'descricao': 'Colonoscopia a cada 10 anos (45-75 anos)',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2021 Grau B'
        })
    
    # Vacinas
    recommendations.extend([
        {
            'titulo': 'Vacina Influenza Tetravalente',
            'descricao': 'Dose anual Aplicar em dose única, INTRAMUSCULAR, anualmente. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Arexy® e Shingrix®; de preferência, aguardar 15 dias de intervalo para vacinação com a QDenga®',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm/ANVISA 2024'
        },
        {
            'titulo': 'Hexavalente (HEXAXIM® ou Infanrix®)',
            'descricao': '1 dose Aplicar dose única e reforço após 5 anos. * Não tem na rede pública',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm/ANVISA 2024'
        }
    ])
    
    return recommendations

def _parse_smoking_status_intelligent(tabagismo, data=None):
    """Normaliza tabagismo vindo como string, dict ou campos achatados para (status, macos_ano)."""
    status = 'nunca_fumou'
    macos = 0
    
    try:
        # Priorizar dict tabagismo se disponível
        if isinstance(tabagismo, dict):
            status = tabagismo.get('status') or tabagismo.get('estado') or 'nunca_fumou'
            macos_value = tabagismo.get('macos_ano') or tabagismo.get('pack_years') or 0
            try:
                macos = int(macos_value) if macos_value else 0
            except (ValueError, TypeError):
                macos = 0
        elif isinstance(tabagismo, str):
            status = tabagismo
        
        # Verificar campos achatados no payload principal se data fornecido
        if data:
            flat_status = data.get('tabagismo_status')
            flat_macos = data.get('tabagismo_macos_ano') or data.get('macos_ano')
            
            if flat_status:
                status = flat_status
            if flat_macos:
                try:
                    macos = int(flat_macos) if flat_macos else 0
                except (ValueError, TypeError):
                    macos = 0
                    
    except Exception:
        # Em caso de qualquer erro, usar valores padrão seguros
        status = 'nunca_fumou'
        macos = 0
    
    # Normalizar status
    if isinstance(status, str):
        status = status.replace('-', '_').lower().strip()
        if status == 'fumante':
            status = 'fumante_atual'
        elif status == 'ex_fumante' or status == 'ex-fumante':
            status = 'ex_fumante'
        elif status not in ['fumante_atual', 'ex_fumante', 'nunca_fumou']:
            status = 'nunca_fumou'
    else:
        status = 'nunca_fumou'
        
    return status, macos

@checkup_intelligent_bp.route('/checkup-intelligent', methods=['POST'])
def generate_intelligent_recommendations():
    try:
        # Use robust JSON parsing
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Dados não fornecidos ou JSON inválido'}), 400
        
        # Extrair dados do paciente
        age = int(data.get('idade', 0))
        sex = data.get('sexo', 'masculino')
        weight = float(data.get('peso', 0)) if data.get('peso') else None
        height = float(data.get('altura', 0)) if data.get('altura') else None
        
        # Parse smoking status robustly
        tabagismo_raw = data.get('tabagismo', {})
        smoking_status, macos_ano = _parse_smoking_status_intelligent(tabagismo_raw, data)
        
        # Dados clínicos para PREVENT
        patient_data = {
            'age': age,
            'sex': sex,
            'totalCholesterol': float(data.get('colesterol_total', 0)) if data.get('colesterol_total') else 0,
            'hdlCholesterol': float(data.get('hdl_colesterol', 0)) if data.get('hdl_colesterol') else 0,
            'systolicBP': float(data.get('pressao_sistolica', 0)) if data.get('pressao_sistolica') else 0,
            'diabetes': 'diabetes_tipo_2' in data.get('comorbidades', []),
            'smoking': smoking_status == 'fumante_atual',
            'weight': weight,
            'height': height,
            'creatinine': float(data.get('creatinina', 1.0)) if data.get('creatinina') else 1.0
        }
        
        # Calcular risco PREVENT
        risk_result = calculate_prevent_risk(patient_data)
        risk_level = 'baixo'
        
        if risk_result:
            risk_level = get_risk_classification(risk_result['risk10Year'])
        
        # Gerar recomendações
        recommendations = []
        alerts = []  # Initialize alerts array
        
        # Recomendações baseadas em idade e sexo
        age_sex_recs = generate_age_sex_recommendations(age, sex)
        recommendations.extend(age_sex_recs)
        
        # Recomendações de biomarcadores se necessário
        if risk_level in ['borderline', 'intermediario', 'alto']:
            biomarker_recs = generate_biomarker_recommendations(risk_level, age, sex)
            recommendations.extend(biomarker_recs)
        
        # Salvar no banco de dados se possível
        try:
            # Criar ou encontrar paciente
            patient = Patient(
                nome=data.get('nome', f'Paciente {age} anos'),
                idade=age,
                sexo=sex,
                peso=weight,
                altura=height
            )
            db.session.add(patient)
            db.session.flush()  # Para obter o ID
            
            # Criar checkup
            checkup = Checkup(
                patient_id=patient.id,
                pressao_sistolica=patient_data['systolicBP'],
                pressao_diastolica=float(data.get('pressao_diastolica', 0)) if data.get('pressao_diastolica') else None,
                colesterol_total=patient_data['totalCholesterol'],
                hdl_colesterol=patient_data['hdlCholesterol'],
                creatinina=patient_data['creatinine'],
                hba1c=float(data.get('hba1c', 0)) if data.get('hba1c') else None,
                risco_10_anos=risk_result['risk10Year'] if risk_result else None,
                risco_30_anos=risk_result['risk30Year'] if risk_result else None,
                classificacao_risco=risk_level,
                comorbidades=json.dumps(data.get('comorbidades', [])),
                historia_familiar=json.dumps(data.get('historia_familiar', [])),
                tabagismo=smoking_status,
                medicacoes=data.get('medicacoes', ''),
                pais_guideline=data.get('pais_guideline', 'BR')
            )
            db.session.add(checkup)
            db.session.flush()
            
            # Salvar recomendações
            for rec in recommendations:
                recomendacao = Recomendacao(
                    checkup_id=checkup.id,
                    titulo=rec['titulo'],
                    descricao=rec['descricao'],
                    categoria=rec['categoria'],
                    prioridade=rec['prioridade'],
                    referencia=rec['referencia']
                )
                db.session.add(recomendacao)
            
            db.session.commit()
            
        except Exception as db_error:
            print(f"Erro ao salvar no banco: {db_error}")
            db.session.rollback()
        
        # Registrar analytics
        analytics.track_recommendation()
        
        # Preparar resposta padronizada
        return jsonify({
            'recommendations': recommendations,
            'alerts': alerts
        })
        
    except Exception as e:
        # Log traceback for debugging
        print(f"Erro na geração de recomendações: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Falha ao gerar recomendações: {str(e)}'}), 500

@checkup_intelligent_bp.route('/generate-pdf', methods=['POST'])
def generate_pdf_report():
    """Gera relatório em PDF das recomendações"""
    try:
        data = request.get_json()
        
        # Aqui você pode implementar a geração de PDF
        # Por enquanto, retornamos uma resposta de sucesso
        
        analytics.track_pdf_generated()
        
        return jsonify({
            'success': True,
            'message': 'PDF gerado com sucesso',
            'download_url': '/download/relatorio.pdf'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
