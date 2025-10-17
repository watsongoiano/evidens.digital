#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste direto do código do método do_POST
"""

import sys
import os
import json

# Adicionar o diretório da API ao path
sys.path.insert(0, '/home/ubuntu/evidens-deploy/api')

def test_direct():
    """Testa diretamente o código do método do_POST"""
    try:
        print("=== Testando código do_POST diretamente ===")
        
        # Importar módulos necessários
        from checkup_hypertension import get_hypertension_recommendations_v2
        from prevent_calculator import calculate_prevent_risk
        
        # Dados de teste
        data = {
            'idade': 45,
            'sexo': 'feminino',
            'peso': 70,
            'altura': 165,
            'pressao_sistolica': 130,
            'colesterol_total': 200,
            'hdl_colesterol': 50,
            'creatinina': 1.0,
            'comorbidades': ['hipertensao'],
            'medicacoes_especificas': [],
            'tabagismo': 'nunca_fumou',
            'hipertensao': 'on'
        }
        
        print(f"Dados de entrada: {json.dumps(data, indent=2)}")
        
        # Executar o código do método do_POST linha por linha
        idade = int(data.get("idade", 0))
        sexo = data.get("sexo", "")
        comorbidades = data.get("comorbidades", [])
        if isinstance(comorbidades, str):
            comorbidades = [comorbidades]
        elif not isinstance(comorbidades, list):
            comorbidades = []

        print(f"Idade: {idade}, Sexo: {sexo}, Comorbidades: {comorbidades}")

        # Detectar condições
        hipertenso = (data.get("hipertensao") == "on" or "hipertensao" in comorbidades)
        has_resistente = (data.get("has_resistente") == "on" or "has_resistente" in comorbidades)
        diabetico = (data.get("diabetes") == "on" or "diabetes" in comorbidades)
        gestante = data.get("gestante") == "on"
        
        print(f"Hipertenso: {hipertenso}, HAS Resistente: {has_resistente}, Diabético: {diabetico}, Gestante: {gestante}")
        
        # Calcular risco cardiovascular PREVENT
        print("Calculando risco PREVENT...")
        cardiovascular_risk = calculate_prevent_risk(data)
        print(f"Risco cardiovascular: {cardiovascular_risk}")
        
        recommendations = []
        
        def add_recommendation(rec_data):
            # Evitar duplicações baseadas no título
            if not any(rec["titulo"] == rec_data["titulo"] for rec in recommendations):
                recommendations.append(rec_data)
                print(f"Adicionada recomendação: {rec_data['titulo']}")

        print("Gerando recomendações...")
        
        # Teste de uma recomendação simples
        if idade >= 18:
            add_recommendation({
                "titulo": "MAPA de 24h ou MRPA",
                "descricao": "Monitorização ambulatorial da pressão arterial para diagnóstico e acompanhamento da hipertensão arterial.",
                "prioridade": "alta",
                "referencia": "SBC 2020",
                "categoria": "Exames de Imagem"
            })
        
        # Testar módulo de hipertensão
        if hipertenso:
            print("Chamando módulo de hipertensão...")
            hypertension_recs = get_hypertension_recommendations_v2(data)
            print(f"Recomendações de hipertensão: {len(hypertension_recs)}")
            for rec in hypertension_recs:
                add_recommendation(rec)
        
        print(f"Total de recomendações: {len(recommendations)}")
        
        # Montar resposta
        response = {
            "recommendations": recommendations,
            "cardiovascular_risk": cardiovascular_risk,
            "patient_summary": {
                "idade": idade,
                "sexo": sexo,
                "hipertenso": hipertenso,
                "diabetico": diabetico
            }
        }
        
        print("✅ Código executado com sucesso!")
        print(f"Resposta final: {json.dumps(response, indent=2, ensure_ascii=False)}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct()
    sys.exit(0 if success else 1)
