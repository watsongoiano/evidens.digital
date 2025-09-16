import json

def get_hypertension_recommendations_v2(data):
    """
    Gera uma lista de exames recomendados para pacientes hipertensos com base nas diretrizes unificadas AHA/ACC 2025 e SBC 2020.
    """
    recommendations = []
    
    def add_recommendation(rec_data):
        if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
            recommendations.append(rec_data)

    hipertenso = data.get("hipertensao") == "on"
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
    add_recommendation({
        "titulo": "Potássio, soro",
        "descricao": "Exame de rotina para avaliação inicial, essencial para guiar a terapia (especialmente com diuréticos) e investigar causas secundárias como hiperaldosteronismo.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Creatinina, soro com TFGe",
        "descricao": "Exame fundamental para avaliar a função renal, que pode ser tanto causa quanto consequência da hipertensão, e para monitorar o efeito de medicamentos.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Perfil Lipídico, soro",
        "descricao": "Exame essencial para estratificar o risco cardiovascular global em todos os pacientes com hipertensão.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Glicemia de Jejum, plasma",
        "descricao": "Exame de rotina para rastrear diabetes e pré-diabetes, comorbidades frequentes que elevam o risco cardiovascular do hipertenso.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Hemoglobina Glicada, sangue total",
        "descricao": "Alternativa ou complemento à glicemia de jejum para rastrear e diagnosticar diabetes em pacientes hipertensos.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Urina Tipo I",
        "descricao": "Exame de rotina para avaliação inicial de possíveis danos renais ou doenças associadas.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Eletrocardiograma (ECG)",
        "descricao": "Exame de rotina para investigar hipertrofia ventricular esquerda (HVE) e outras anormalidades cardíacas.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Avaliação cardiológica"
    })
    
    add_recommendation({
        "titulo": "Ácido Úrico, soro",
        "descricao": "Exame para avaliação do risco cardiovascular e metabólico. Considerado de rotina pela diretriz brasileira.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Laboratorial"
    })

    # 2. Avaliação de Rotina (Apenas AHA/ACC)
    add_recommendation({
        "titulo": "Hemograma Completo",
        "descricao": "Exame laboratorial básico para avaliação geral da saúde do paciente com hipertensão.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Sódio, soro",
        "descricao": "Parte da avaliação eletrolítica inicial para identificar desequilíbrios que possam influenciar a pressão arterial e o tratamento.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "Cálcio, soro",
        "descricao": "Avaliação de rotina para investigar possíveis causas secundárias de hipertensão, como hiperparatireoidismo.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025",
        "categoria": "Laboratorial"
    })
    
    add_recommendation({
        "titulo": "TSH, soro",
        "descricao": "Exame de rotina para identificar disfunções tireoidianas como possíveis causas secundárias de hipertensão.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025",
        "categoria": "Laboratorial"
    })

    # 3. Avaliação para Populações Indicadas, Comorbidades e HAR
    if alteracao_ecg or suspeita_ic:
        add_recommendation({
            "titulo": "Ecocardiograma",
            "descricao": "Recomendado na presença de alterações no ECG ou suspeita clínica de insuficiência cardíaca para avaliar hipertrofia e função ventricular.",
            "prioridade": "alta",
            "referencia": "AHA/ACC 2025 e SBC 2020",
            "categoria": "Imagem"
        })
    
    if diabetes or sindrome_metabolica or multiplos_fatores_risco:
        add_recommendation({
            "titulo": "Relação Albumina/Creatinina, urina",
            "descricao": "Recomendado para avaliação de lesão renal, especialmente em pacientes com diabetes, síndrome metabólica ou múltiplos fatores de risco.",
            "prioridade": "alta",
            "referencia": "AHA/ACC 2025 e SBC 2020",
            "categoria": "Laboratorial"
        })
    
    add_recommendation({
        "titulo": "MAPA de 24h ou MRPA",
        "descricao": "Indicado para confirmar o diagnóstico de hipertensão e identificar fenótipos como hipertensão do avental branco e mascarada.",
        "prioridade": "alta",
        "referencia": "AHA/ACC 2025 e SBC 2020",
        "categoria": "Monitoramento Pressórico"
    })

    if has_resistente or suspeita_hiperaldosteronismo:
        add_recommendation({
            "titulo": "Relação Aldosterona/Renina, plasma",
            "descricao": "Principal rastreio para aldosteronismo primário, recomendado na investigação de hipertensão resistente ou secundária.",
            "prioridade": "alta",
            "referencia": "AHA/ACC 2025 e SBC 2020",
            "categoria": "Laboratorial - Hipertensão Secundária"
        })
    
    if has_resistente or suspeita_apneia_sono:
        add_recommendation({
            "titulo": "Polissonografia",
            "descricao": "Padrão-ouro para investigar AOS, uma causa comum de hipertensão resistente.",
            "prioridade": "alta",
            "referencia": "AHA/ACC 2025 e SBC 2020",
            "categoria": "Diagnóstico - Hipertensão Secundária"
        })
    
    if has_resistente or suspeita_estenose_arteria_renal:
        add_recommendation({
            "titulo": "Ultrassom com Doppler de Artérias Renais",
            "descricao": "Exame de imagem não invasivo para rastreio de estenose de artéria renal na investigação de HAR.",
            "prioridade": "média",
            "referencia": "AHA/ACC 2025 e SBC 2020",
            "categoria": "Imagem - Hipertensão Secundária"
        })

    return recommendations
