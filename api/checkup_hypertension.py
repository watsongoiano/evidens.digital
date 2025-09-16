import json

def get_hypertension_recommendations_v2(data):
    """
    Gera uma lista de exames recomendados para pacientes hipertensos com base nas diretrizes unificadas AHA/ACC 2025 e SBC 2020.
    """
    recommendations = []
    
    def add_recommendation(rec_data):
        if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
            recommendations.append(rec_data)

    hipertenso = data.get("hipertenso") == "on"
    alteracao_ecg = data.get("alteracao_ecg") == "on"
    suspeita_ic = data.get("suspeita_ic") == "on"
    diabetes = data.get("diabetes") == "on"
    sindrome_metabolica = data.get("sindrome_metabolica") == "on"
    multiplos_fatores_risco = data.get("multiplos_fatores_risco") == "on"
    has_resistente = data.get("has_resistente") == "on"
    suspeita_hiperaldosteronismo = data.get("suspeita_hiperaldosteronismo") == "on"
    suspeita_apneia_sono = data.get("suspeita_apneia_sono") == "on"
    suspeita_estenose_arteria_renal = data.get("suspeita_estenose_arteria_renal") == "on"

    if not hipertenso:
        return []

    # 1. Avaliação de Rotina (Ambas as Sociedades)
    add_recommendation({"titulo": "Potássio, soro", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Creatinina, soro com TFGe", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Perfil Lipídico, soro", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Glicemia de Jejum, plasma", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Hemoglobina Glicada, sangue total", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Urina Tipo I", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Eletrocardiograma (ECG)", "categoria": "Avaliação cardiológica"})
    add_recommendation({"titulo": "Ácido Úrico, soro", "categoria": "Laboratorial"})

    # 2. Avaliação de Rotina (Apenas AHA/ACC)
    add_recommendation({"titulo": "Hemograma Completo", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Sódio, soro", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "Cálcio, soro", "categoria": "Laboratorial"})
    add_recommendation({"titulo": "TSH, soro", "categoria": "Laboratorial"})

    # 3. Avaliação para Populações Indicadas, Comorbidades e HAR
    if alteracao_ecg or suspeita_ic:
        add_recommendation({"titulo": "Ecocardiograma", "categoria": "Imagem"})
    if diabetes or sindrome_metabolica or multiplos_fatores_risco:
        add_recommendation({"titulo": "Relação Albumina/Creatinina, urina", "categoria": "Laboratorial"})
    
    add_recommendation({"titulo": "MAPA de 24h ou MRPA", "categoria": "Monitoramento Pressórico"})

    if has_resistente or suspeita_hiperaldosteronismo:
        add_recommendation({"titulo": "Relação Aldosterona/Renina, plasma", "categoria": "Laboratorial - Hipertensão Secundária"})
    if has_resistente or suspeita_apneia_sono:
        add_recommendation({"titulo": "Polissonografia", "categoria": "Diagnóstico - Hipertensão Secundária"})
    if has_resistente or suspeita_estenose_arteria_renal:
        add_recommendation({"titulo": "Ultrassom com Doppler de Artérias Renais", "categoria": "Imagem - Hipertensão Secundária"})

    return recommendations

