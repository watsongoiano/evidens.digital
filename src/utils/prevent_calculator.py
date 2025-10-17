"""
Módulo de Cálculo de Risco Cardiovascular PREVENT 2024
Baseado em: https://www.ahajournals.org/doi/10.1161/CIR.0000000000001315
"""
import json
import math
from pathlib import Path

# Carregar configurações
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config' / 'prevent_coefficients.json'

def load_coefficients():
    """Carrega coeficientes do arquivo de configuração"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar coeficientes PREVENT: {e}")
        return None

def calculate_prevent_risk(patient_data):
    """
    Calcula o risco cardiovascular usando o algoritmo PREVENT 2024
    
    Args:
        patient_data (dict): Dados do paciente incluindo:
            - age (int): Idade
            - sex (str): 'masculino' ou 'feminino'
            - totalCholesterol (float): Colesterol total em mg/dL
            - hdlCholesterol (float): HDL colesterol em mg/dL
            - systolicBP (float): Pressão arterial sistólica em mmHg
            - diabetes (bool): Presença de diabetes
            - smoking (bool): Tabagismo
            - weight (float, opcional): Peso em kg
            - height (float, opcional): Altura em cm
            - creatinine (float, opcional): Creatinina em mg/dL
    
    Returns:
        dict: Resultados incluindo risk10Year, risk30Year, egfr, bmi
    """
    try:
        # Carregar coeficientes
        config = load_coefficients()
        if not config:
            return None
        
        # Extrair dados do paciente
        age = patient_data.get('age', 0)
        sex = patient_data.get('sex', 'masculino').lower()
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
        
        # Calcular eGFR (se creatinina disponível)
        egfr = None
        if creatinine and creatinine > 0:
            egfr = 175 * (creatinine ** -1.154) * (age ** -0.203)
            if sex == 'feminino':
                egfr *= 0.742
        
        # Calcular BMI (se peso e altura disponíveis)
        bmi = None
        if weight and height:
            height_m = height / 100
            bmi = weight / (height_m ** 2)
        
        # Obter coeficientes para o sexo
        coeffs = config['coefficients'].get(sex)
        if not coeffs:
            return None
        
        # Calcular log odds
        log_odds = (
            coeffs['intercept'] +
            coeffs['beta_age'] * age +
            coeffs['beta_chol'] * total_chol +
            coeffs['beta_hdl'] * hdl_chol +
            coeffs['beta_sbp'] * systolic_bp +
            (coeffs['beta_diabetes'] if diabetes else 0) +
            (coeffs['beta_smoking'] if smoking else 0)
        )
        
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
    """
    Classifica o risco cardiovascular
    
    Args:
        risk_10_year (float): Risco em 10 anos (%)
    
    Returns:
        str: Classificação do risco
    """
    try:
        config = load_coefficients()
        if not config:
            # Fallback para classificação padrão
            if risk_10_year < 5:
                return 'baixo'
            elif risk_10_year < 7.5:
                return 'borderline'
            elif risk_10_year < 20:
                return 'intermediario'
            else:
                return 'alto'
        
        # Usar classificação do arquivo de configuração
        classifications = config['risk_classification']
        if risk_10_year < classifications['baixo']['threshold']:
            return 'baixo'
        elif risk_10_year < classifications['borderline']['threshold']:
            return 'borderline'
        elif risk_10_year < classifications['intermediario']['threshold']:
            return 'intermediario'
        else:
            return 'alto'
            
    except Exception as e:
        print(f"Erro na classificação de risco: {e}")
        return 'desconhecido'

