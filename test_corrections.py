#!/usr/bin/env python3
"""
Script de teste para verificar as correções implementadas no sistema evidens.digital
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.routes.checkup_intelligent import generate_age_sex_recommendations, generate_biomarker_recommendations

def test_recommendations_generation():
    """Testa a geração de recomendações"""
    print("=== Testando geração de recomendações ===")
    
    # Teste 1: Homem de 45 anos
    print("\n1. Testando homem de 45 anos:")
    recs_45m = generate_age_sex_recommendations(45, 'masculino')
    print(f"   Recomendações geradas: {len(recs_45m)}")
    
    for i, rec in enumerate(recs_45m[:5]):  # Mostrar apenas as primeiras 5
        print(f"   {i+1}. {rec.get('titulo', 'SEM TÍTULO')}")
        print(f"      Categoria: {rec.get('categoria', 'SEM CATEGORIA')}")
        print(f"      Subtítulo: '{rec.get('subtitulo', 'SEM SUBTÍTULO')}'")
        print(f"      Grau evidência: '{rec.get('grau_evidencia', 'SEM GRAU')}'")
        print()
    
    # Teste 2: Mulher de 50 anos
    print("\n2. Testando mulher de 50 anos:")
    recs_50f = generate_age_sex_recommendations(50, 'feminino')
    print(f"   Recomendações geradas: {len(recs_50f)}")
    
    # Teste 3: Verificar se há campos None ou vazios
    print("\n3. Verificando campos obrigatórios:")
    problemas = 0
    for rec in recs_45m + recs_50f:
        if rec.get('subtitulo') is None:
            print(f"   PROBLEMA: subtitulo None em '{rec.get('titulo')}'")
            problemas += 1
        if rec.get('grau_evidencia') is None:
            print(f"   PROBLEMA: grau_evidencia None em '{rec.get('titulo')}'")
            problemas += 1
        if not rec.get('categoria'):
            print(f"   PROBLEMA: categoria vazia em '{rec.get('titulo')}'")
            problemas += 1
    
    if problemas == 0:
        print("   ✅ Todos os campos obrigatórios estão preenchidos!")
    else:
        print(f"   ❌ Encontrados {problemas} problemas")
    
    # Teste 4: Verificar categorias específicas
    print("\n4. Verificando categorias:")
    categorias = {}
    for rec in recs_45m + recs_50f:
        cat = rec.get('categoria', 'sem_categoria')
        if cat not in categorias:
            categorias[cat] = 0
        categorias[cat] += 1
    
    for cat, count in categorias.items():
        print(f"   {cat}: {count} recomendações")

def test_biomarker_recommendations():
    """Testa recomendações de biomarcadores"""
    print("\n=== Testando recomendações de biomarcadores ===")
    
    bio_recs = generate_biomarker_recommendations('alto', 55, 'masculino')
    print(f"Recomendações de biomarcadores: {len(bio_recs)}")
    
    for rec in bio_recs:
        print(f"   - {rec.get('titulo')}")
        print(f"     Categoria: {rec.get('categoria')}")
        print(f"     Subtítulo: '{rec.get('subtitulo', '')}'")
        print(f"     Grau: '{rec.get('grau_evidencia', '')}'")

if __name__ == "__main__":
    print("Iniciando testes das correções...")
    test_recommendations_generation()
    test_biomarker_recommendations()
    print("\nTestes concluídos!")
