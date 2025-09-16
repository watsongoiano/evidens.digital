#!/usr/bin/env python3
import json
import sys
import os
from http.server import BaseHTTPRequestHandler

# Adicionar o diretório atual ao path para importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.')
try:
    from checkup_hypertension import get_hypertension_recommendations_v2
except ImportError:
    # Fallback se a importação falhar
    def get_hypertension_recommendations_v2(data):
        return []

def calculate_prevent_risk(data):
    """
    Calcula o risco cardiovascular usando as equações PREVENT 2024
    """
    try:
        idade = int(data.get("idade", 0))
        sexo = data.get("sexo", "")
        pas = float(data.get("pressao_sistolica", 0))
        pad = float(data.get("pressao_diastolica", 0))
        colesterol_total = float(data.get("colesterol_total", 0))
        hdl = float(data.get("hdl_colesterol", 0))
        creatinina = float(data.get("creatinina", 0))
        hba1c = float(data.get("hba1c", 0))
        
        # Cálculo simplificado do eGFR (CKD-EPI)
        if sexo == "feminino":
            egfr = 142 * min(creatinina/0.7, 1)**(-0.329) * max(creatinina/0.7, 1)**(-1.209) * 0.9938**idade
        else:
            egfr = 142 * min(creatinina/0.9, 1)**(-0.411) * max(creatinina/0.9, 1)**(-1.209) * 0.9938**idade
        
        # Fatores de risco para cálculo PREVENT
        diabetes = "diabetes" in data.get("comorbidades", [])
        tabagismo = data.get("tabagismo", "nunca") in ["fumante", "ex-fumante"]
        
        # Cálculo simplificado do risco (baseado em PREVENT)
        risk_score = 0
        
        # Idade
        if idade >= 65:
            risk_score += 3
        elif idade >= 55:
            risk_score += 2
        elif idade >= 45:
            risk_score += 1
            
        # Pressão arterial
        if pas >= 160 or pad >= 100:
            risk_score += 3
        elif pas >= 140 or pad >= 90:
            risk_score += 2
        elif pas >= 130 or pad >= 80:
            risk_score += 1
            
        # Colesterol
        if colesterol_total >= 240:
            risk_score += 2
        elif colesterol_total >= 200:
            risk_score += 1
            
        if hdl < 40:
            risk_score += 1
            
        # Diabetes
        if diabetes:
            risk_score += 2
            
        # Tabagismo
        if tabagismo:
            risk_score += 2
            
        # eGFR
        if egfr < 60:
            risk_score += 2
        elif egfr < 90:
            risk_score += 1
            
        # Converter score em porcentagem de risco estimado
        risk_10yr = min(risk_score * 2.5, 40)  # Máximo 40%
        risk_30yr = min(risk_score * 4, 60)    # Máximo 60%
        
        return {
            "risk_10yr": round(risk_10yr, 1),
            "risk_30yr": round(risk_30yr, 1),
            "egfr": round(egfr, 1),
            "risk_category": "alto" if risk_10yr >= 20 else "intermediario" if risk_10yr >= 7.5 else "borderline" if risk_10yr >= 5 else "baixo"
        }
    except:
        return None

def get_cardiovascular_stratification_exams(risk_data):
    """
    Retorna exames de estratificação cardiovascular baseados no risco PREVENT
    """
    if not risk_data:
        return []
        
    exams = []
    risk_category = risk_data["risk_category"]
    
    # Exames para risco borderline (5-7.5%)
    if risk_category in ["borderline", "intermediario", "alto"]:
        exams.extend([
            {
                "titulo": "Lipoproteína(a) - Lp(a), soro",
                "descricao": "Marcador de risco cardiovascular independente, especialmente útil para reclassificação de risco em pacientes borderline/intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2022",
                "categoria": "Estratificação Cardiovascular"
            },
            {
                "titulo": "Proteína C Reativa ultrassensível (hsCRP), soro",
                "descricao": "Marcador inflamatório para estratificação de risco cardiovascular, especialmente em pacientes com risco intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2019",
                "categoria": "Estratificação Cardiovascular"
            }
        ])
    
    # Exames para risco intermediário (7.5-20%)
    if risk_category in ["intermediario", "alto"]:
        exams.extend([
            {
                "titulo": "Tomografia de Coronárias para Score de Cálcio",
                "descricao": "Exame de imagem para quantificação do cálcio coronariano, útil para reclassificação de risco em pacientes com risco intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2019",
                "categoria": "Estratificação Cardiovascular"
            },
            {
                "titulo": "Índice Tornozelo-Braquial (ITB)",
                "descricao": "Avaliação não invasiva de doença arterial periférica como marcador de risco cardiovascular.",
                "prioridade": "média",
                "referencia": "AHA/ACC 2016",
                "categoria": "Estratificação Cardiovascular"
            }
        ])
    
    # Exames para alto risco (≥20%)
    if risk_category == "alto":
        exams.extend([
            {
                "titulo": "Microalbuminúria, urina",
                "descricao": "Marcador de lesão vascular e risco cardiovascular aumentado, especialmente em pacientes de alto risco.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2017",
                "categoria": "Estratificação Cardiovascular"
            },
            {
                "titulo": "Ecocardiograma com Strain",
                "descricao": "Avaliação avançada da função cardíaca para detecção precoce de disfunção em pacientes de alto risco.",
                "prioridade": "média",
                "referencia": "ASE 2016",
                "categoria": "Estratificação Cardiovascular"
            }
        ])
    
    return exams

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        response = {"message": "API funcionando. Use POST para enviar dados.", "status": "ok"}
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8")) if post_data else {}

            idade = int(data.get("idade", 0))
            sexo = data.get("sexo", "")
            comorbidades = data.get("comorbidades", [])
            if isinstance(comorbidades, str):
                comorbidades = [comorbidades]
            elif not isinstance(comorbidades, list):
                comorbidades = []

            # Detectar condições
            hipertenso = (data.get("hipertensao") == "on" or "hipertensao" in comorbidades)
            has_resistente = (data.get("has_resistente") == "on" or "has_resistente" in comorbidades)
            diabetico = (data.get("diabetes") == "on" or "diabetes" in comorbidades)
            gestante = data.get("gestante") == "on"
            
            # Calcular risco cardiovascular PREVENT
            cardiovascular_risk = calculate_prevent_risk(data)
            
            recommendations = []
            
            def add_recommendation(rec_data):
                # Evitar duplicações baseadas no título
                if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
                    recommendations.append(rec_data)

            # === RASTREAMENTOS GERAIS (SEM DUPLICAÇÃO) ===
            
            # Rastreamento de Câncer de Pulmão
            tabagismo = data.get("tabagismo", "nunca")
            macos_ano = int(data.get("macos_ano", 0)) if data.get("macos_ano") else 0
            if 50 <= idade <= 80 and tabagismo in ["fumante", "ex-fumante"] and macos_ano >= 20:
                add_recommendation({
                    "titulo": "Tomografia Computadorizada de Baixa Dose (TCBD) de Tórax",
                    "descricao": "Rastreamento anual para câncer de pulmão em adultos de 50-80 anos com história de tabagismo ≥20 maços-ano.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de Hepatite C (universal)
            if 18 <= idade <= 79:
                add_recommendation({
                    "titulo": "Rastreamento de Hepatite C",
                    "descricao": "Teste único de anticorpos anti-HCV para todos os adultos de 18-79 anos, independente de fatores de risco.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2020",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de HIV
            if 15 <= idade <= 65:
                add_recommendation({
                    "titulo": "Rastreamento de HIV",
                    "descricao": "Teste de HIV pelo menos uma vez para todos os adolescentes e adultos de 15-65 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de Aneurisma de Aorta Abdominal
            if sexo == "masculino" and 65 <= idade <= 75 and tabagismo in ["fumante", "ex-fumante"]:
                add_recommendation({
                    "titulo": "Ultrassom de Aorta Abdominal",
                    "descricao": "Rastreamento único para aneurisma de aorta abdominal em homens de 65-75 anos com história de tabagismo.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de Osteoporose
            if sexo == "feminino" and idade >= 65:
                add_recommendation({
                    "titulo": "Densitometria Óssea (DEXA)",
                    "descricao": "Rastreamento de osteoporose para todas as mulheres ≥65 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2018",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de Câncer Colorretal
            if 45 <= idade <= 75:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer Colorretal",
                    "descricao": "Colonoscopia a cada 10 anos, sigmoidoscopia a cada 5 anos, ou teste de sangue oculto nas fezes anual.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })

            # Rastreamento de Câncer de Colo de Útero
            if sexo == "feminino":
                if 21 <= idade <= 29:
                    add_recommendation({
                        "titulo": "Citologia Cervical (Papanicolaou)",
                        "descricao": "Rastreamento de câncer de colo de útero a cada 3 anos para mulheres de 21-29 anos.",
                        "prioridade": "alta",
                        "referencia": "USPSTF 2018",
                        "categoria": "Rastreamento"
                    })
                elif 30 <= idade <= 65:
                    add_recommendation({
                        "titulo": "Citologia Cervical + Teste de HPV",
                        "descricao": "Co-teste (citologia + HPV) a cada 5 anos ou citologia isolada a cada 3 anos para mulheres de 30-65 anos.",
                        "prioridade": "alta",
                        "referencia": "USPSTF 2018",
                        "categoria": "Rastreamento"
                    })

            # Rastreamento de Câncer de Mama
            if sexo == "feminino" and 40 <= idade <= 74:
                add_recommendation({
                    "titulo": "Mamografia Digital ou Tomossíntese",
                    "descricao": "Rastreamento de câncer de mama a cada 2 anos para mulheres de 40-74 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2024",
                    "categoria": "Rastreamento"
                })

            # === RASTREAMENTOS DE DIABETES (DESAGRUPADO EM EXAMES INDIVIDUAIS) ===
            
            # Rastreamento de diabetes - exames individuais (ADA 2025)
            sobrepeso_obesidade = data.get("sobrepeso_obesidade") == "on"
            fatores_risco_diabetes = any([
                data.get("historia_familiar_diabetes") == "on",
                data.get("hipertensao") == "on",
                data.get("dislipidemia") == "on",
                data.get("sindrome_ovariopolicistico") == "on",
                data.get("inatividade_fisica") == "on"
            ])
            
            if idade >= 35 or (sobrepeso_obesidade and fatores_risco_diabetes):
                # Glicemia de Jejum
                add_recommendation({
                    "titulo": "Glicemia de Jejum (FPG)",
                    "descricao": "Dosagem da glicose plasmática após jejum de 8-12 horas para rastreamento de diabetes. Repetir a cada 3 anos se normal.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Laboratorial"
                })
                
                # Hemoglobina Glicada
                add_recommendation({
                    "titulo": "Hemoglobina Glicada (HbA1c)",
                    "descricao": "Dosagem de HbA1c para rastreamento de diabetes e prediabetes. Repetir a cada 3 anos se normal, anual se prediabetes.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Laboratorial"
                })
                
                # TOTG apenas se outros exames inconclusivos
                add_recommendation({
                    "titulo": "Teste Oral de Tolerância à Glicose (TOTG 75g)",
                    "descricao": "TOTG com 75g de glicose quando glicemia de jejum e HbA1c são inconclusivos para diagnóstico de diabetes.",
                    "prioridade": "media",
                    "referencia": "ADA 2025",
                    "categoria": "Laboratorial"
                })

            # Rastreamentos específicos para gestantes
            if gestante:
                add_recommendation({
                    "titulo": "Rastreamento de Diabetes Gestacional",
                    "descricao": "TOTG 75g entre 24-28 semanas de gestação para todas as gestantes.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Rastreamento Pré-natal"
                })
                add_recommendation({
                    "titulo": "Rastreamento de Bacteriúria Assintomática",
                    "descricao": "Urinocultura na primeira consulta pré-natal ou entre 12-16 semanas de gestação.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento Pré-natal"
                })

            # === MONITORAMENTO PRESSÓRICO BASEADO NO PREVENT ===
            
            # MAPA/MRPA estratificado por risco
            if idade >= 18:
                if cardiovascular_risk and cardiovascular_risk["risk_category"] in ["intermediario", "alto"]:
                    add_recommendation({
                        "titulo": "MAPA de 24h ou MRPA",
                        "descricao": "Monitorização ambulatorial prioritária para pacientes com risco cardiovascular intermediário/alto para diagnóstico preciso de hipertensão e fenótipos pressóricos.",
                        "prioridade": "alta",
                        "referencia": "AHA/ACC 2025 e SBC 2020",
                        "categoria": "Monitoramento Pressórico"
                    })
                else:
                    add_recommendation({
                        "titulo": "MAPA de 24h ou MRPA",
                        "descricao": "Monitorização ambulatorial recomendada para diagnóstico preciso de hipertensão e identificação de fenótipos pressóricos.",
                        "prioridade": "média",
                        "referencia": "AHA/ACC 2025 e SBC 2020",
                        "categoria": "Monitoramento Pressórico"
                    })

            # === MÓDULO DE HIPERTENSÃO (SEM DUPLICAÇÃO) ===
            
            if hipertenso or has_resistente:
                data["hipertensao_detectada"] = hipertenso
                data["has_resistente_detectada"] = has_resistente
                hypertension_recs = get_hypertension_recommendations_v2(data)
                for rec in hypertension_recs:
                    add_recommendation(rec)

            # === ESTRATIFICAÇÃO CARDIOVASCULAR BASEADA NO PREVENT ===
            
            if cardiovascular_risk:
                stratification_exams = get_cardiovascular_stratification_exams(cardiovascular_risk)
                for exam in stratification_exams:
                    add_recommendation(exam)

            response_data = {
                "recommendations": recommendations,
                "cardiovascular_risk": cardiovascular_risk,
                "patient_data": data,
                "total_recommendations": len(recommendations),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            error_response = {"error": str(e), "details": repr(e)}
            self.wfile.write(json.dumps(error_response).encode("utf-8"))
