#!/usr/bin/env python3
import json
import sys
import os
import unicodedata
from http.server import BaseHTTPRequestHandler

# Adicionar o diretório atual ao path para importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.')
try:
    from checkup_hypertension import get_hypertension_recommendations_v2
except ImportError:
    # Fallback se a importação falhar
    def get_hypertension_recommendations_v2(data):
        return []

try:
    from prevent_calculator import calculate_prevent_risk as _calculate_prevent_risk
except ImportError:
    # Fallback se a importação falhar
    def _calculate_prevent_risk(data):
        return {
            "success": False,
            "error": "Módulo PREVENT não disponível",
            "risk_10yr": 0,
            "risk_30yr": 0,
            "classification": {"category": ""},
        }


def calculate_prevent_risk(data):
    try:
        result = _calculate_prevent_risk(data)
    except Exception as exc:  # pragma: no cover - segurança adicional
        result = {
            "success": False,
            "error": str(exc),
            "risk_10yr": 0,
            "risk_30yr": 0,
            "classification": {"category": ""},
        }

    if not isinstance(result, dict):
        result = {}

    classification = result.get("classification")
    if not isinstance(classification, dict):
        classification = {}
        result["classification"] = classification

    classification.setdefault("category", "")
    return result


TABAGISMO_NORMALIZATION = {
    "nunca": "nunca",
    "nunca-fumou": "nunca",
    "nunca-fumei": "nunca",
    "nunca-fumador": "nunca",
    "nunca-fumadora": "nunca",
    "never": "nunca",
    "never-smoked": "nunca",
    "never-smoker": "nunca",
    "never-smoke": "nunca",
    "nao": "nunca",
    "na": "nunca",
    "n-a": "nunca",
    "none": "nunca",
    "sem": "nunca",
    "no": "nunca",
    "": "nunca",
    "0": "nunca",
    "false": "nunca",
    "fumante": "fumante",
    "fumante-atual": "fumante",
    "fumanteatual": "fumante",
    "atual": "fumante",
    "current": "fumante",
    "current-smoker": "fumante",
    "smoker": "fumante",
    "smoking": "fumante",
    "ex": "ex-fumante",
    "ex-fumante": "ex-fumante",
    "exfumante": "ex-fumante",
    "ex-smoker": "ex-fumante",
    "former": "ex-fumante",
    "former-smoker": "ex-fumante",
    "previous-smoker": "ex-fumante",
    "former-smoke": "ex-fumante",
}


def _strip_accents(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_tabagismo_status(value):
    """Normaliza diferentes representações de tabagismo para o padrão interno."""

    if isinstance(value, dict):
        for key in ("status", "estado", "value"):
            if value.get(key):
                return normalize_tabagismo_status(value[key])
        return "nunca"

    if isinstance(value, (list, tuple)):
        for item in value:
            normalized = normalize_tabagismo_status(item)
            if normalized:
                return normalized
        return "nunca"

    if value is None:
        return "nunca"

    text = str(value).strip().lower()
    if not text:
        return "nunca"

    text = _strip_accents(text)
    text = text.replace("_", "-").replace(" ", "-")
    text = text.replace("--", "-")

    normalized = TABAGISMO_NORMALIZATION.get(text)
    if normalized:
        return normalized

    if "ex" in text and "fum" in text:
        return "ex-fumante"

    if any(keyword in text for keyword in ("fumante", "smoker", "atual", "current")):
        return "fumante"

    return "nunca"


def get_cardiovascular_stratification_exams(risk_category):
    """
    Retorna exames de estratificação cardiovascular baseados na categoria de risco PREVENT
    
    Args:
        risk_category: Categoria de risco ('Baixo', 'Borderline', 'Intermediário', 'Alto')
    
    Returns:
        Lista de exames recomendados
    """
    if not risk_category:
        return []
        
    exams = []
    
    # Exames para risco borderline
    if risk_category in ["Borderline", "Intermediário", "Alto"]:
        exams.extend([
            {
                "titulo": "Lipoproteína(a) - Lp(a), soro",
                "descricao": "Marcador de risco cardiovascular independente, especialmente útil para reclassificação de risco em pacientes borderline/intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2022",
                "categoria": "Exames Laboratoriais"
            },
            {
                "titulo": "Proteína C Reativa ultrassensível (hsCRP), soro",
                "descricao": "Marcador inflamatório para estratificação de risco cardiovascular, especialmente em pacientes com risco intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2019",
                "categoria": "Exames Laboratoriais"
            },
            {
                "titulo": "Índice Tornozelo-Braquial (ITB)",
                "descricao": "Avaliação não invasiva de doença arterial periférica como marcador de risco cardiovascular.",
                "prioridade": "média",
                "referencia": "AHA/ACC 2016",
                "categoria": "Outras recomendações"
            }
        ])
    
    # Exames para risco intermediário
    if risk_category in ["Intermediário", "Alto"]:
        exams.extend([
            {
                "titulo": "Tomografia de Coronárias para Score de Cálcio Coronariano",
                "descricao": "Exame de imagem para quantificação do cálcio coronariano, útil para reclassificação de risco em pacientes com risco intermediário.",
                "prioridade": "alta",
                "referencia": "AHA/ACC 2019",
                "categoria": "Exames de Imagem"
            }
        ])
    
    # Exames para alto risco
    if risk_category == "Alto":
        exams.extend([
            {
                "titulo": "Microalbuminúria, urina 24h",
                "descricao": "Marcador de lesão vascular e risco cardiovascular aumentado, especialmente em pacientes de alto risco.",
                "prioridade": "alta",
                "referencia": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001356",
                "categoria": "Exames Laboratoriais"
            },
            {
                "titulo": "Ecocardiograma com Strain Longitudinal Global",
                "descricao": "Avaliação avançada da função cardíaca para detecção precoce de disfunção em pacientes de alto risco.",
                "prioridade": "média",
                "referencia": "ASE 2016",
                "categoria": "Exames de Imagem"
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

            tabagismo_raw = data.get("tabagismo")
            macos_ano_raw = data.get("macos_ano")

            if (
                tabagismo_raw is None
                or (isinstance(tabagismo_raw, str) and not tabagismo_raw.strip())
            ) and data.get("tabagismo_status") is not None:
                tabagismo_raw = data.get("tabagismo_status")

            if isinstance(tabagismo_raw, dict):
                macos_ano_raw = macos_ano_raw or tabagismo_raw.get("macos_ano") or tabagismo_raw.get("pack_years")

            if (
                macos_ano_raw is None
                or (isinstance(macos_ano_raw, str) and not macos_ano_raw.strip())
            ):
                macos_ano_raw = data.get("tabagismo_macos_ano")

            tabagismo = normalize_tabagismo_status(tabagismo_raw)
            data["tabagismo"] = tabagismo

            # Detectar condições
            hipertenso = (data.get("hipertensao") == "on" or "hipertensao" in comorbidades)
            has_resistente = (data.get("has_resistente") == "on" or "has_resistente" in comorbidades)
            diabetico = (data.get("diabetes") == "on" or "diabetes" in comorbidades)
            gestante = data.get("gestante") == "on"
            
            # Calcular risco cardiovascular PREVENT
            cardiovascular_risk = calculate_prevent_risk(data)
            risk = cardiovascular_risk.get("classification", {}).get("category", "").lower()
            
            recommendations = []
            
            def add_recommendation(rec_data):
                # Evitar duplicações baseadas no título
                if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
                    recommendations.append(rec_data)

            # === RASTREAMENTOS GERAIS (SEM DUPLICAÇÃO) ===
            
            # Rastreamento de Câncer de Pulmão
            macos_ano = 0
            if macos_ano_raw is not None:
                if isinstance(macos_ano_raw, (int, float)):
                    macos_ano = float(macos_ano_raw)
                elif isinstance(macos_ano_raw, str):
                    macos_ano_str = macos_ano_raw.strip().replace(",", ".")
                    if macos_ano_str:
                        try:
                            macos_ano = float(macos_ano_str)
                        except ValueError:
                            macos_ano = 0
            tabagismo = tabagismo or "nunca"
            if 50 <= idade <= 80 and tabagismo in ["fumante", "ex-fumante"] and macos_ano >= 20:
                add_recommendation({
                    "titulo": "Tomografia Computadorizada de Baixa Dose (TCBD) de Tórax",
                    "descricao": "Rastreamento anual para câncer de pulmão em adultos de 50-80 anos com história de tabagismo ≥20 maços-ano.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Hepatite C (universal)
            if 18 <= idade <= 79:
                add_recommendation({
                    "titulo": "Rastreamento de Hepatite C",
                    "descricao": "Teste único de anticorpos anti-HCV para todos os adultos de 18-79 anos, independente de fatores de risco.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2020",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de HIV
            if 15 <= idade <= 65:
                add_recommendation({
                    "titulo": "Rastreamento de HIV",
                    "descricao": "Teste de HIV pelo menos uma vez para todos os adolescentes e adultos de 15-65 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Aneurisma de Aorta Abdominal
            if sexo == "masculino" and 65 <= idade <= 75 and tabagismo in ["fumante", "ex-fumante"]:
                add_recommendation({
                    "titulo": "Ultrassom de Aorta Abdominal",
                    "descricao": "Rastreamento único para aneurisma de aorta abdominal em homens de 65-75 anos com história de tabagismo.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Osteoporose
            if sexo == "feminino" and idade >= 65:
                add_recommendation({
                    "titulo": "Densitometria Óssea (DEXA)",
                    "descricao": "Rastreamento de osteoporose para todas as mulheres ≥65 anos.",
                    "prioridade": "alta",
                    "referencia": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/osteoporosis-screening",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Câncer Colorretal
            if 45 <= idade <= 75:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer Colorretal",
                    "descricao": "Colonoscopia a cada 10 anos, sigmoidoscopia a cada 5 anos, ou teste de sangue oculto nas fezes anual.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Câncer de Colo de Útero
            if sexo == "feminino":
                if 21 <= idade <= 29:
                    add_recommendation({
                        "titulo": "Citologia Cervical (Papanicolaou)",
                        "descricao": "Rastreamento de câncer de colo de útero a cada 3 anos para mulheres de 21-29 anos.",
                        "prioridade": "alta",
                        "referencia": "USPSTF 2018",
                        "categoria": "Outras recomendações"
                    })
                elif 30 <= idade <= 65:
                    add_recommendation({
                        "titulo": "Citologia Cervical + Teste de HPV",
                        "descricao": "Co-teste (citologia + HPV) a cada 5 anos ou citologia isolada a cada 3 anos para mulheres de 30-65 anos.",
                        "prioridade": "alta",
                        "referencia": "USPSTF 2018",
                        "categoria": "Outras recomendações"
                    })

            # Rastreamento de Câncer de Mama
            if sexo == "feminino" and 40 <= idade <= 74:
                add_recommendation({
                    "titulo": "Mamografia Digital ou Tomossíntese",
                    "descricao": "Rastreamento de câncer de mama a cada 2 anos para mulheres de 40-74 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2024",
                    "categoria": "Outras recomendações"
                })

            # Rastreamento de Câncer de Próstata
            if sexo == "masculino" and 55 <= idade <= 69:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer de Próstata (55 a 69 anos)",
                    "descricao": "A decisão de realizar o rastreamento deve ser individual, após uma conversa entre o paciente e o médico sobre os potenciais benefícios e danos. Não é um rastreio de rotina para todos.",
                    "prioridade": "baixa",
                    "referencia": "USPSTF 2018",
                    "categoria": "Outras recomendações",
                    "exame_recomendado": "Antígeno Prostático Específico (PSA), soro",
                    "frequencia_rastreio": "A frequência é periódica e deve ser individualizada após discussão com o médico.",
                    "site_referencia": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/prostate-cancer-screening"
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
                    "categoria": "Exames Laboratoriais"
                })
                
                # Hemoglobina Glicada
                add_recommendation({
                    "titulo": "Hemoglobina Glicada (HbA1c)",
                    "descricao": "Dosagem de HbA1c para rastreamento de diabetes e prediabetes. Repetir a cada 3 anos se normal, anual se prediabetes.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Exames Laboratoriais"
                })
                
                # TOTG apenas se outros exames inconclusivos
                add_recommendation({
                    "titulo": "Teste Oral de Tolerância à Glicose (TOTG 75g)",
                    "descricao": "TOTG com 75g de glicose quando glicemia de jejum e HbA1c são inconclusivos para diagnóstico de diabetes.",
                    "prioridade": "media",
                    "referencia": "ADA 2025",
                    "categoria": "Exames Laboratoriais"
                })

            # Rastreamentos específicos para gestantes
            if gestante:
                add_recommendation({
                    "titulo": "Rastreamento de Diabetes Gestacional",
                    "descricao": "TOTG 75g entre 24-28 semanas de gestação para todas as gestantes.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Outras recomendações"
                })
                add_recommendation({
                    "titulo": "Rastreamento de Bacteriúria Assintomática",
                    "descricao": "Urinocultura na primeira consulta pré-natal ou entre 12-16 semanas de gestação.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Outras recomendações"
                })

            # === MONITORAMENTO PRESSÓRICO BASEADO NO PREVENT ===
            
            # MAPA/MRPA estratificado por risco
            if idade >= 18:
                if risk in ["intermediario", "alto"]:
                    add_recommendation({
                        "titulo": "MAPA de 24h ou MRPA",
                        "descricao": "Monitorização ambulatorial prioritária para pacientes com risco cardiovascular intermediário/alto para diagnóstico preciso de hipertensão e fenótipos pressóricos.",
                        "prioridade": "alta",
                        "referencia": "AHA/ACC 2025 e SBC 2020",
                        "categoria": "Outras recomendações"
                    })
                else:
                    add_recommendation({
                        "titulo": "MAPA de 24h ou MRPA",
                        "descricao": "Monitorização ambulatorial recomendada para diagnóstico preciso de hipertensão e identificação de fenótipos pressóricos.",
                        "prioridade": "média",
                        "referencia": "AHA/ACC 2025 e SBC 2020",
                        "categoria": "Outras recomendações"
                    })

            # === MÓDULO DE HIPERTENSÃO (SEM DUPLICAÇÃO) ===
            
            if hipertenso or has_resistente:
                data["hipertensao_detectada"] = hipertenso
                data["has_resistente_detectada"] = has_resistente
                hypertension_recs = get_hypertension_recommendations_v2(data)
                for rec in hypertension_recs:
                    add_recommendation(rec)

            # === CÁLCULO PREVENT E ESTRATIFICAÇÃO CARDIOVASCULAR ===
            
            prevent_result = calculate_prevent_risk(data)
            
            if prevent_result.get("success", False):
                # Adicionar exames baseados na estratificação de risco
                risk_category = prevent_result.get("classification", {}).get("category", "Baixo")
                stratification_exams = get_cardiovascular_stratification_exams(risk_category)
                for exam in stratification_exams:
                    add_recommendation(exam)

            response_data = {
                "recommendations": recommendations,
                "prevent_score": prevent_result,
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
