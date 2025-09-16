from http.server import BaseHTTPRequestHandler
import json
import sys

sys.path.append("..")
from .checkup_hypertension import get_hypertension_recommendations_v2

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
            hipertensao = data.get("hipertensao") == "on"
            gestante = data.get("gestante") == "on"

            recommendations = []

            def add_recommendation(rec_data):
                if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
                    recommendations.append(rec_data)

            if hipertensao:
                hypertension_recs = get_hypertension_recommendations_v2(data)
                for rec in hypertension_recs:
                    add_recommendation(rec)

            # Lógica de rastreamento geral com descrição e referência
            tabagismo_atual = data.get("tabagismo_atual") == "on"
            ex_fumante = data.get("ex_fumante") == "on"
            anos_parou_fumar = int(data.get("anos_parou_fumar", 999)) if data.get("anos_parou_fumar") else 999
            macos_ano = int(data.get("macos_ano", 0)) if data.get("macos_ano") else 0
            
            if 50 <= idade <= 80 and macos_ano >= 20 and (tabagismo_atual or (ex_fumante and anos_parou_fumar <= 15)):
                add_recommendation({
                    "titulo": "Rastreamento de Câncer de Pulmão (TCBD)",
                    "descricao": "Tomografia computadorizada de baixa dose para rastreamento de câncer de pulmão em fumantes ou ex-fumantes com alto risco.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })
            
            if 18 <= idade <= 79:
                add_recommendation({
                    "titulo": "Rastreamento de Hepatite C",
                    "descricao": "Teste sorológico para detecção de anticorpos anti-HCV, recomendado universalmente para adultos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2020",
                    "categoria": "Rastreamento"
                })
            
            if 15 <= idade <= 65:
                add_recommendation({
                    "titulo": "Rastreamento de HIV (Adultos)",
                    "descricao": "Teste de triagem para HIV recomendado para todos os adolescentes e adultos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento"
                })
            
            if gestante:
                add_recommendation({
                    "titulo": "Rastreamento de HIV (Gestantes)",
                    "descricao": "Teste de triagem para HIV obrigatório durante o pré-natal para prevenção da transmissão vertical.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento Pré-natal"
                })
            
            historico_tabagismo = data.get("historico_tabagismo") == "on"
            if sexo == "masculino" and 65 <= idade <= 75 and historico_tabagismo:
                add_recommendation({
                    "titulo": "Rastreamento de Aneurisma de Aorta Abdominal",
                    "descricao": "Ultrassonografia abdominal única para homens de 65-75 anos com histórico de tabagismo.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2019",
                    "categoria": "Rastreamento"
                })
            
            if sexo == "feminino" and idade >= 65:
                add_recommendation({
                    "titulo": "Rastreamento de Osteoporose (≥65 anos)",
                    "descricao": "Densitometria óssea (DEXA) para mulheres com 65 anos ou mais.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2018",
                    "categoria": "Rastreamento"
                })
            
            pos_menopausa = data.get("pos_menopausa") == "on"
            risco_osteoporose = data.get("risco_osteoporose") == "on"
            if sexo == "feminino" and idade < 65 and pos_menopausa and risco_osteoporose:
                add_recommendation({
                    "titulo": "Rastreamento de Osteoporose (<65 anos)",
                    "descricao": "Densitometria óssea (DEXA) para mulheres pós-menopáusicas menores de 65 anos com fatores de risco.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2018",
                    "categoria": "Rastreamento"
                })
            
            risco_sifilis = data.get("risco_sifilis") == "on"
            if idade >= 15 and not gestante and risco_sifilis:
                add_recommendation({
                    "titulo": "Rastreamento de Sífilis",
                    "descricao": "Teste sorológico para sífilis em pessoas com fatores de risco aumentado.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2016",
                    "categoria": "Rastreamento"
                })
            
            risco_tuberculose = data.get("risco_tuberculose") == "on"
            if idade >= 18 and risco_tuberculose:
                add_recommendation({
                    "titulo": "Rastreamento de Tuberculose Latente",
                    "descricao": "Teste tuberculínico (TST) ou teste de liberação de interferon-gama (IGRA) para adultos com fatores de risco.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2016",
                    "categoria": "Rastreamento"
                })
            
            sexualmente_ativa = data.get("sexualmente_ativa") == "on"
            risco_ist = data.get("risco_ist") == "on"
            if sexo == "feminino" and sexualmente_ativa and (idade <= 24 or (idade >= 25 and risco_ist)):
                add_recommendation({
                    "titulo": "Rastreamento de Clamídia e Gonorreia",
                    "descricao": "Teste de amplificação de ácido nucleico (NAAT) para clamídia e gonorreia em mulheres sexualmente ativas.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })
            
            if 45 <= idade <= 75:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer Colorretal (45-75 anos)",
                    "descricao": "Colonoscopia, sigmoidoscopia flexível, ou teste de sangue oculto nas fezes para rastreamento de câncer colorretal.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })
            
            if 76 <= idade <= 85:
                add_recommendation({
                    "titulo": "Rastreamento Seletivo de Câncer Colorretal (76-85 anos)",
                    "descricao": "Rastreamento individualizado baseado na saúde geral, expectativa de vida e preferências do paciente.",
                    "prioridade": "média",
                    "referencia": "USPSTF 2021",
                    "categoria": "Rastreamento"
                })
            
            if sexo == "feminino" and 21 <= idade <= 29:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer de Colo de Útero (21-29 anos)",
                    "descricao": "Citologia cervical (Papanicolaou) a cada 3 anos para mulheres de 21-29 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2018",
                    "categoria": "Rastreamento"
                })
            
            if sexo == "feminino" and 30 <= idade <= 65:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer de Colo de Útero (30-65 anos)",
                    "descricao": "Citologia cervical a cada 3 anos, teste de HPV a cada 5 anos, ou co-teste a cada 5 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2018",
                    "categoria": "Rastreamento"
                })
            
            if sexo == "feminino" and 40 <= idade <= 74:
                add_recommendation({
                    "titulo": "Rastreamento de Câncer de Mama",
                    "descricao": "Mamografia digital ou tomossíntese mamária a cada 2 anos para mulheres de 40-74 anos.",
                    "prioridade": "alta",
                    "referencia": "USPSTF 2024",
                    "categoria": "Rastreamento"
                })
            
            sobrepeso_obesidade = data.get("sobrepeso_obesidade") == "on"
            risco_diabetes_adicional = data.get("risco_diabetes_adicional") == "on"
            if idade >= 35 or (sobrepeso_obesidade and risco_diabetes_adicional):
                add_recommendation({
                    "titulo": "Rastreamento de Prediabetes e Diabetes Tipo 2",
                    "descricao": "Glicemia de jejum, teste oral de tolerância à glicose ou hemoglobina glicada para rastreamento de diabetes.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Rastreamento"
                })
            
            historia_familiar_dm1 = data.get("historia_familiar_dm1") == "on"
            risco_genetico_dm1 = data.get("risco_genetico_dm1") == "on"
            if historia_familiar_dm1 or risco_genetico_dm1:
                add_recommendation({
                    "titulo": "Rastreamento de Risco para Diabetes Tipo 1",
                    "descricao": "Dosagem de autoanticorpos de ilhotas para identificação da fase pré-sintomática do diabetes tipo 1.",
                    "prioridade": "alta",
                    "referencia": "ADA 2025",
                    "categoria": "Rastreamento"
                })
            
            if gestante:
                add_recommendation({
                    "titulo": "Rastreamento de Diabetes Mellitus Gestacional",
                    "descricao": "Teste oral de tolerância à glicose entre 24-28 semanas de gestação para todas as gestantes.",
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

            response_data = {
                "recommendations": recommendations,
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
