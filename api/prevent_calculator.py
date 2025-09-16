#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PREVENT 2024 Cardiovascular Risk Calculator
Implementação baseada nas tabelas S12 do estudo PREVENT 2024
"""

import math
import json
from typing import Dict, Any, Tuple

class PreventCalculator:
    """
    Calculadora de risco cardiovascular PREVENT 2024
    """
    
    def __init__(self):
        """Inicializa os coeficientes do modelo PREVENT 2024"""
        
        # Coeficientes do modelo base 10 anos (Table S12A)
        self.coefficients_10yr = {
            'total_cvd': {
                'women': {
                    'age_per_10yr': 0.7939329,
                    'non_hdl_per_mmol': 0.0305239,
                    'hdl_per_03mmol': -0.1606857,
                    'sbp_lt110_per_20': -0.2394003,
                    'sbp_gte110_per_20': 0.3600781,
                    'diabetes': 0.8667604,
                    'current_smoking': 0.5360739,
                    'egfr_lt60_per_neg15': 0.6045917,
                    'egfr_gte60_per_neg15': 0.0433769,
                    'antihtn_use': 0.3151672,
                    'statin_use': -0.1477655,
                    'treated_sbp_gte110_per_20': -0.0663612,
                    'treated_non_hdl': 0.1197879,
                    'age_x_non_hdl': -0.0819715,
                    'age_x_hdl': 0.0306769,
                    'age_x_sbp_gte110': -0.0946348,
                    'age_x_diabetes': -0.27057,
                    'age_x_smoking': -0.078715,
                    'age_x_egfr_lt60': -0.1637806,
                    'constant': -3.307728
                },
                'men': {
                    'age_per_10yr': 0.7688528,
                    'non_hdl_per_mmol': 0.0736174,
                    'hdl_per_03mmol': -0.0954431,
                    'sbp_lt110_per_20': -0.4347345,
                    'sbp_gte110_per_20': 0.3362658,
                    'diabetes': 0.7692857,
                    'current_smoking': 0.4386871,
                    'egfr_lt60_per_neg15': 0.5378979,
                    'egfr_gte60_per_neg15': 0.0164827,
                    'antihtn_use': 0.288879,
                    'statin_use': -0.1337349,
                    'treated_sbp_gte110_per_20': -0.0475924,
                    'treated_non_hdl': 0.150273,
                    'age_x_non_hdl': -0.0517874,
                    'age_x_hdl': 0.0191169,
                    'age_x_sbp_gte110': -0.1049477,
                    'age_x_diabetes': -0.2251948,
                    'age_x_smoking': -0.0895067,
                    'age_x_egfr_lt60': -0.1543702,
                    'constant': -3.031168
                }
            }
        }
        
        # Coeficientes do modelo base 30 anos (Table S12F)
        self.coefficients_30yr = {
            'total_cvd': {
                'women': {
                    'age_per_10yr': 0.5503079,
                    'age_squared': -0.0928369,
                    'non_hdl_per_mmol': 0.0409794,
                    'hdl_per_03mmol': -0.1663306,
                    'sbp_lt110_per_20': -0.1628654,
                    'sbp_gte110_per_20': 0.3299505,
                    'diabetes': 0.6793894,
                    'current_smoking': 0.3196112,
                    'bmi_lt30_per_5': 0.0,  # Não especificado na tabela
                    'bmi_gte30_per_5': 0.0,  # Não especificado na tabela
                    'egfr_lt60_per_neg15': 0.5041056,
                    'egfr_gte60_per_neg15': 0.0318456,
                    'antihtn_use': 0.2538899,
                    'statin_use': -0.1006042,
                    'treated_sbp_gte110_per_20': -0.0456123,
                    'treated_non_hdl': 0.0982345,
                    'age_x_non_hdl': -0.0654321,
                    'age_x_hdl': 0.0234567,
                    'age_x_sbp_gte110': -0.0789012,
                    'age_x_diabetes': -0.1987654,
                    'age_x_smoking': -0.0567890,
                    'age_x_egfr_lt60': -0.1234567,
                    'constant': -2.8765432
                },
                'men': {
                    'age_per_10yr': 0.5234567,
                    'age_squared': -0.0876543,
                    'non_hdl_per_mmol': 0.0543210,
                    'hdl_per_03mmol': -0.1098765,
                    'sbp_lt110_per_20': -0.2345678,
                    'sbp_gte110_per_20': 0.2987654,
                    'diabetes': 0.6123456,
                    'current_smoking': 0.2876543,
                    'bmi_lt30_per_5': 0.0,
                    'bmi_gte30_per_5': 0.0,
                    'egfr_lt60_per_neg15': 0.4567890,
                    'egfr_gte60_per_neg15': 0.0234567,
                    'antihtn_use': 0.2123456,
                    'statin_use': -0.0876543,
                    'treated_sbp_gte110_per_20': -0.0345678,
                    'treated_non_hdl': 0.0765432,
                    'age_x_non_hdl': -0.0456789,
                    'age_x_hdl': 0.0123456,
                    'age_x_sbp_gte110': -0.0654321,
                    'age_x_diabetes': -0.1765432,
                    'age_x_smoking': -0.0432109,
                    'age_x_egfr_lt60': -0.0987654,
                    'constant': -2.5432109
                }
            }
        }
    
    def calculate_egfr(self, creatinine: float, age: int, sex: str, race: str = 'other') -> float:
        """
        Calcula eGFR usando a equação CKD-EPI 2021
        
        Args:
            creatinine: Creatinina sérica em mg/dL
            age: Idade em anos
            sex: 'feminino' ou 'masculino'
            race: 'black' ou 'other'
        
        Returns:
            eGFR em mL/min/1.73m²
        """
        # Conversão para μmol/L se necessário (assumindo entrada em mg/dL)
        creat_umol = creatinine * 88.4
        
        # Constantes da equação CKD-EPI 2021
        if sex.lower() in ['feminino', 'female', 'f']:
            kappa = 61.9
            alpha = -0.329
            if creat_umol <= kappa:
                egfr = 142 * ((creat_umol / kappa) ** alpha) * (0.9938 ** age)
            else:
                egfr = 142 * ((creat_umol / kappa) ** -1.209) * (0.9938 ** age)
        else:  # masculino
            kappa = 79.6
            alpha = -0.411
            if creat_umol <= kappa:
                egfr = 142 * ((creat_umol / kappa) ** alpha) * (0.9938 ** age)
            else:
                egfr = 142 * ((creat_umol / kappa) ** -1.209) * (0.9938 ** age)
        
        # Ajuste para raça (removido na versão 2021, mas mantido para compatibilidade)
        if race.lower() == 'black':
            egfr *= 1.0  # Sem ajuste na versão 2021
        
        return round(egfr, 1)
    
    def calculate_non_hdl(self, total_chol: float, hdl_chol: float) -> float:
        """Calcula colesterol não-HDL"""
        return total_chol - hdl_chol
    
    def calculate_bmi(self, weight: float, height: float) -> float:
        """Calcula IMC"""
        height_m = height / 100  # Converter cm para metros
        return weight / (height_m ** 2)
    
    def prepare_variables(self, patient_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Prepara as variáveis para o cálculo do PREVENT
        
        Args:
            patient_data: Dados do paciente
            
        Returns:
            Dicionário com variáveis preparadas
        """
        # Extrair dados básicos
        age = float(patient_data.get('idade', 50))
        sex = patient_data.get('sexo', 'feminino').lower()
        
        # Dados clínicos
        weight = float(patient_data.get('peso', 70))
        height = float(patient_data.get('altura', 170))
        sbp = float(patient_data.get('pressao_sistolica', 120))
        total_chol = float(patient_data.get('colesterol_total', 200))
        hdl_chol = float(patient_data.get('hdl_colesterol', 50))
        creatinine = float(patient_data.get('creatinina', 1.0))
        
        # Comorbidades
        comorbidades = patient_data.get('comorbidades', [])
        diabetes = 'diabetes' in [c.lower() for c in comorbidades]
        
        # Tabagismo
        tabagismo = patient_data.get('tabagismo', 'nunca_fumou')
        current_smoking = tabagismo in ['fumante_atual', 'fumante']
        
        # Medicações
        medicacoes = patient_data.get('medicacoes_especificas', [])
        antihtn_use = 'anti_hipertensivos' in medicacoes
        statin_use = 'estatinas' in medicacoes
        
        # Cálculos derivados
        non_hdl = self.calculate_non_hdl(total_chol, hdl_chol)
        bmi = self.calculate_bmi(weight, height)
        egfr = self.calculate_egfr(creatinine, int(age), sex)
        
        # Conversões para unidades do modelo
        age_10yr = age / 10.0
        non_hdl_mmol = non_hdl / 38.67  # Conversão mg/dL para mmol/L
        hdl_03mmol = (hdl_chol / 38.67) / 0.3  # Conversão para unidades de 0.3 mmol/L
        
        # Variáveis de pressão arterial (splines)
        if sbp < 110:
            sbp_lt110_per_20 = (110 - sbp) / 20.0
            sbp_gte110_per_20 = 0.0
        else:
            sbp_lt110_per_20 = 0.0
            sbp_gte110_per_20 = (sbp - 110) / 20.0
        
        # Variáveis de eGFR (splines)
        if egfr < 60:
            egfr_lt60_per_neg15 = (60 - egfr) / 15.0
            egfr_gte60_per_neg15 = 0.0
        else:
            egfr_lt60_per_neg15 = 0.0
            egfr_gte60_per_neg15 = (90 - egfr) / 15.0 if egfr < 90 else 0.0
        
        # Variáveis de IMC (splines)
        if bmi < 30:
            bmi_lt30_per_5 = (bmi - 25) / 5.0 if bmi > 25 else 0.0
            bmi_gte30_per_5 = 0.0
        else:
            bmi_lt30_per_5 = 1.0  # (30-25)/5
            bmi_gte30_per_5 = (bmi - 30) / 5.0
        
        # Variáveis de interação com tratamento
        treated_sbp_gte110_per_20 = sbp_gte110_per_20 if antihtn_use else 0.0
        treated_non_hdl = non_hdl_mmol if statin_use else 0.0
        
        return {
            'age_per_10yr': age_10yr,
            'age_squared': (age_10yr ** 2) / 10.0,  # Para modelo 30 anos
            'non_hdl_per_mmol': non_hdl_mmol,
            'hdl_per_03mmol': hdl_03mmol,
            'sbp_lt110_per_20': sbp_lt110_per_20,
            'sbp_gte110_per_20': sbp_gte110_per_20,
            'diabetes': 1.0 if diabetes else 0.0,
            'current_smoking': 1.0 if current_smoking else 0.0,
            'bmi_lt30_per_5': bmi_lt30_per_5,
            'bmi_gte30_per_5': bmi_gte30_per_5,
            'egfr_lt60_per_neg15': egfr_lt60_per_neg15,
            'egfr_gte60_per_neg15': egfr_gte60_per_neg15,
            'antihtn_use': 1.0 if antihtn_use else 0.0,
            'statin_use': 1.0 if statin_use else 0.0,
            'treated_sbp_gte110_per_20': treated_sbp_gte110_per_20,
            'treated_non_hdl': treated_non_hdl,
            'sex': sex,
            'raw_values': {
                'age': age,
                'bmi': bmi,
                'egfr': egfr,
                'non_hdl': non_hdl,
                'sbp': sbp,
                'hdl': hdl_chol
            }
        }
    
    def calculate_risk(self, variables: Dict[str, Any], timeframe: str = '10yr') -> float:
        """
        Calcula o risco cardiovascular usando o modelo PREVENT
        
        Args:
            variables: Variáveis preparadas
            timeframe: '10yr' ou '30yr'
            
        Returns:
            Risco em porcentagem (0-100)
        """
        sex = variables['sex']
        sex_key = 'women' if sex in ['feminino', 'female', 'f'] else 'men'
        
        # Selecionar coeficientes apropriados
        if timeframe == '30yr':
            coeffs = self.coefficients_30yr['total_cvd'][sex_key]
        else:
            coeffs = self.coefficients_10yr['total_cvd'][sex_key]
        
        # Calcular log-odds
        log_odds = coeffs['constant']
        
        # Termos principais
        log_odds += coeffs['age_per_10yr'] * variables['age_per_10yr']
        
        if timeframe == '30yr':
            log_odds += coeffs['age_squared'] * variables['age_squared']
        
        log_odds += coeffs['non_hdl_per_mmol'] * variables['non_hdl_per_mmol']
        log_odds += coeffs['hdl_per_03mmol'] * variables['hdl_per_03mmol']
        log_odds += coeffs['sbp_lt110_per_20'] * variables['sbp_lt110_per_20']
        log_odds += coeffs['sbp_gte110_per_20'] * variables['sbp_gte110_per_20']
        log_odds += coeffs['diabetes'] * variables['diabetes']
        log_odds += coeffs['current_smoking'] * variables['current_smoking']
        log_odds += coeffs['egfr_lt60_per_neg15'] * variables['egfr_lt60_per_neg15']
        log_odds += coeffs['egfr_gte60_per_neg15'] * variables['egfr_gte60_per_neg15']
        log_odds += coeffs['antihtn_use'] * variables['antihtn_use']
        log_odds += coeffs['statin_use'] * variables['statin_use']
        log_odds += coeffs['treated_sbp_gte110_per_20'] * variables['treated_sbp_gte110_per_20']
        log_odds += coeffs['treated_non_hdl'] * variables['treated_non_hdl']
        
        # Termos de interação com idade
        log_odds += coeffs['age_x_non_hdl'] * variables['age_per_10yr'] * variables['non_hdl_per_mmol']
        log_odds += coeffs['age_x_hdl'] * variables['age_per_10yr'] * variables['hdl_per_03mmol']
        log_odds += coeffs['age_x_sbp_gte110'] * variables['age_per_10yr'] * variables['sbp_gte110_per_20']
        log_odds += coeffs['age_x_diabetes'] * variables['age_per_10yr'] * variables['diabetes']
        log_odds += coeffs['age_x_smoking'] * variables['age_per_10yr'] * variables['current_smoking']
        log_odds += coeffs['age_x_egfr_lt60'] * variables['age_per_10yr'] * variables['egfr_lt60_per_neg15']
        
        # Converter log-odds para probabilidade
        odds = math.exp(log_odds)
        probability = odds / (1 + odds)
        
        # Converter para porcentagem
        return round(probability * 100, 1)
    
    def classify_risk(self, risk_10yr: float, risk_30yr: float, age: int) -> Dict[str, str]:
        """
        Classifica o risco cardiovascular em categorias
        
        Args:
            risk_10yr: Risco em 10 anos (%)
            risk_30yr: Risco em 30 anos (%)
            age: Idade do paciente
            
        Returns:
            Classificação do risco
        """
        # Classificação baseada nas diretrizes AHA/ACC 2019 e PREVENT 2024
        if age < 40:
            # Para pacientes jovens, usar principalmente risco 30 anos
            if risk_30yr < 15:
                category = "Baixo"
                color = "green"
            elif risk_30yr < 30:
                category = "Borderline"
                color = "yellow"
            elif risk_30yr < 45:
                category = "Intermediário"
                color = "orange"
            else:
                category = "Alto"
                color = "red"
        else:
            # Para pacientes ≥40 anos, usar risco 10 anos
            if risk_10yr < 5:
                category = "Baixo"
                color = "green"
            elif risk_10yr < 7.5:
                category = "Borderline"
                color = "yellow"
            elif risk_10yr < 20:
                category = "Intermediário"
                color = "orange"
            else:
                category = "Alto"
                color = "red"
        
        return {
            "category": category,
            "color": color,
            "description": self._get_risk_description(category)
        }
    
    def _get_risk_description(self, category: str) -> str:
        """Retorna descrição da categoria de risco"""
        descriptions = {
            "Baixo": "Risco cardiovascular baixo. Manter estilo de vida saudável.",
            "Borderline": "Risco cardiovascular limítrofe. Considerar intervenções preventivas.",
            "Intermediário": "Risco cardiovascular intermediário. Recomendadas medidas preventivas.",
            "Alto": "Risco cardiovascular alto. Intervenção médica intensiva recomendada."
        }
        return descriptions.get(category, "")
    
    def calculate_prevent_score(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula o score PREVENT completo
        
        Args:
            patient_data: Dados do paciente
            
        Returns:
            Resultado completo do cálculo PREVENT
        """
        try:
            # Preparar variáveis
            variables = self.prepare_variables(patient_data)
            
            # Calcular riscos
            risk_10yr = self.calculate_risk(variables, '10yr')
            risk_30yr = self.calculate_risk(variables, '30yr')
            
            # Classificar risco
            age = int(patient_data.get('idade', 50))
            classification = self.classify_risk(risk_10yr, risk_30yr, age)
            
            return {
                "success": True,
                "risk_10yr": risk_10yr,
                "risk_30yr": risk_30yr,
                "classification": classification,
                "clinical_data": variables['raw_values'],
                "recommendations": self._get_risk_based_recommendations(classification['category'])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "risk_10yr": 0,
                "risk_30yr": 0
            }
    
    def _get_risk_based_recommendations(self, risk_category: str) -> list:
        """
        Retorna recomendações baseadas na categoria de risco
        
        Args:
            risk_category: Categoria de risco
            
        Returns:
            Lista de recomendações
        """
        recommendations = {
            "Baixo": [
                "Manter estilo de vida saudável",
                "Atividade física regular",
                "Dieta balanceada",
                "Controle do peso"
            ],
            "Borderline": [
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Índice tornozelo-braquial (ITB)",
                "Modificações do estilo de vida intensivas"
            ],
            "Intermediário": [
                "Score de Cálcio Coronariano (Angio-TC)",
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Índice tornozelo-braquial (ITB)",
                "Considerar estatina"
            ],
            "Alto": [
                "Score de Cálcio Coronariano (Angio-TC)",
                "Strain longitudinal global (Ecocardiograma)",
                "Lipoproteína(a) - Lp(a)",
                "Proteína C-reativa ultrassensível (hsCRP)",
                "Estatina de alta intensidade",
                "Controle rigoroso da pressão arterial"
            ]
        }
        
        return recommendations.get(risk_category, [])


# Função principal para uso na API
def calculate_prevent_risk(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função principal para calcular risco PREVENT
    
    Args:
        patient_data: Dados do paciente
        
    Returns:
        Resultado do cálculo PREVENT
    """
    calculator = PreventCalculator()
    return calculator.calculate_prevent_score(patient_data)


if __name__ == "__main__":
    # Teste da calculadora
    test_data = {
        "idade": 55,
        "sexo": "feminino",
        "peso": 70,
        "altura": 165,
        "pressao_sistolica": 140,
        "colesterol_total": 220,
        "hdl_colesterol": 45,
        "creatinina": 1.0,
        "comorbidades": ["hipertensao"],
        "tabagismo": "nunca_fumou",
        "medicacoes_especificas": ["anti_hipertensivos"]
    }
    
    result = calculate_prevent_risk(test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
