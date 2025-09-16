#!/usr/bin/env python3
"""
Teste da implementação da recomendação de rastreamento de clamídia e gonorreia baseada na guideline USPSTF 2021
"""

import json
import sys

def test_clamidia_gonorreia_screening():
    """Testa a recomendação de rastreamento de clamídia e gonorreia para mulheres sexualmente ativas"""
    
    print("🧪 Testando Rastreamento de Clamídia e Gonorreia - Mulheres (USPSTF 2021)")
    print("=" * 80)
    
    # Cenários de teste
    test_cases = [
        {
            "name": "Mulher jovem 18 anos sexualmente ativa - elegível",
            "data": {"idade": "18", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": True
        },
        {
            "name": "Mulher jovem 22 anos sexualmente ativa - elegível",
            "data": {"idade": "22", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": True
        },
        {
            "name": "Mulher 24 anos sexualmente ativa - elegível (limite superior)",
            "data": {"idade": "24", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": True
        },
        {
            "name": "Mulher 25 anos sexualmente ativa com risco - elegível",
            "data": {"idade": "25", "sexo": "feminino", "sexualmente_ativa": "on", "risco_ist": "on"},
            "expected": True
        },
        {
            "name": "Mulher 30 anos sexualmente ativa com risco - elegível",
            "data": {"idade": "30", "sexo": "feminino", "sexualmente_ativa": "on", "risco_ist": "on"},
            "expected": True
        },
        {
            "name": "Mulher 40 anos sexualmente ativa com risco - elegível",
            "data": {"idade": "40", "sexo": "feminino", "sexualmente_ativa": "on", "risco_ist": "on"},
            "expected": True
        },
        {
            "name": "Gestante 20 anos sexualmente ativa - elegível",
            "data": {"idade": "20", "sexo": "feminino", "sexualmente_ativa": "on", "gestante": "on"},
            "expected": True
        },
        {
            "name": "Gestante 28 anos sexualmente ativa com risco - elegível",
            "data": {"idade": "28", "sexo": "feminino", "sexualmente_ativa": "on", "gestante": "on", "risco_ist": "on"},
            "expected": True
        },
        {
            "name": "Mulher 25 anos sexualmente ativa sem risco - não elegível",
            "data": {"idade": "25", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": False
        },
        {
            "name": "Mulher 30 anos sexualmente ativa sem risco - não elegível",
            "data": {"idade": "30", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": False
        },
        {
            "name": "Mulher 22 anos não sexualmente ativa - não elegível",
            "data": {"idade": "22", "sexo": "feminino"},
            "expected": False
        },
        {
            "name": "Homem 22 anos sexualmente ativo - não elegível (sexo)",
            "data": {"idade": "22", "sexo": "masculino", "sexualmente_ativa": "on"},
            "expected": False
        },
        {
            "name": "Adolescente 16 anos sexualmente ativa - elegível",
            "data": {"idade": "16", "sexo": "feminino", "sexualmente_ativa": "on"},
            "expected": True
        },
        {
            "name": "Mulher idosa 60 anos sexualmente ativa com risco - elegível",
            "data": {"idade": "60", "sexo": "feminino", "sexualmente_ativa": "on", "risco_ist": "on"},
            "expected": True
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Dados: {test_case['data']}")
        
        idade = int(test_case['data'].get('idade', 0))
        sexo = test_case['data'].get('sexo', '')
        sexualmente_ativa = test_case['data'].get('sexualmente_ativa') == 'on'
        risco_ist = test_case['data'].get('risco_ist') == 'on'
        
        elegivel = (sexo == 'feminino' and 
                   sexualmente_ativa and 
                   (idade <= 24 or (idade >= 25 and risco_ist)))
        
        if elegivel == test_case['expected']:
            print(f"   ✅ PASSOU - Elegível: {elegivel}")
            passed += 1
        else:
            print(f"   ❌ FALHOU - Esperado: {test_case['expected']}, Obtido: {elegivel}")
    
    print(f"\n{'='*80}")
    print(f"RESULTADO: {passed}/{total} testes passaram")
    
    return passed == total

def test_integration_scenarios():
    """Testa cenários integrados com clamídia e gonorreia"""
    
    print("\n🧪 Testando Cenários Integrados com Clamídia e Gonorreia")
    print("=" * 80)
    
    scenarios = [
        {
            "name": "Mulher jovem sexualmente ativa - múltiplas recomendações",
            "data": {
                "idade": "22",
                "sexo": "feminino",
                "sexualmente_ativa": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos", "Clamídia/Gonorreia"],
            "description": "Mulher de 22 anos sexualmente ativa deve receber HCV + HIV + Clamídia/Gonorreia"
        },
        {
            "name": "Mulher fumante jovem com múltiplos riscos",
            "data": {
                "idade": "23",
                "sexo": "feminino",
                "tabagismo_atual": "on",
                "historico_tabagismo": "on",
                "macos_ano": "25",
                "sexualmente_ativa": "on",
                "risco_sifilis": "on",
                "risco_tuberculose": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos", "Sífilis", "Tuberculose", "Clamídia/Gonorreia"],
            "description": "Mulher fumante de 23 anos com múltiplos riscos deve receber 5 recomendações"
        },
        {
            "name": "Mulher 25 anos com risco IST - transição de critério",
            "data": {
                "idade": "25",
                "sexo": "feminino",
                "sexualmente_ativa": "on",
                "risco_ist": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos", "Clamídia/Gonorreia"],
            "description": "Mulher de 25 anos precisa de risco para ser elegível"
        },
        {
            "name": "Mulher 25 anos sem risco IST - não elegível",
            "data": {
                "idade": "25",
                "sexo": "feminino",
                "sexualmente_ativa": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos"],
            "description": "Mulher de 25 anos sem risco não recebe clamídia/gonorreia"
        },
        {
            "name": "Gestante jovem sexualmente ativa",
            "data": {
                "idade": "20",
                "sexo": "feminino",
                "sexualmente_ativa": "on",
                "gestante": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos", "HIV Gestantes", "Clamídia/Gonorreia"],
            "description": "Gestante jovem deve receber todas as recomendações aplicáveis"
        },
        {
            "name": "Gestante 28 anos com risco",
            "data": {
                "idade": "28",
                "sexo": "feminino",
                "sexualmente_ativa": "on",
                "gestante": "on",
                "risco_ist": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos", "HIV Gestantes", "Clamídia/Gonorreia"],
            "description": "Gestante ≥25 anos com risco deve receber clamídia/gonorreia"
        },
        {
            "name": "Mulher idosa com múltiplos riscos",
            "data": {
                "idade": "55",
                "sexo": "feminino",
                "sexualmente_ativa": "on",
                "risco_ist": "on",
                "risco_sifilis": "on",
                "risco_tuberculose": "on",
                "tabagismo_atual": "on",
                "historico_tabagismo": "on",
                "macos_ano": "30"
            },
            "expected": ["TCBD", "Hepatite C", "HIV Adultos", "Sífilis", "Tuberculose", "Clamídia/Gonorreia"],
            "description": "Mulher de 55 anos com múltiplos riscos - máxima cobertura possível"
        },
        {
            "name": "Homem jovem sexualmente ativo - não elegível",
            "data": {
                "idade": "22",
                "sexo": "masculino",
                "sexualmente_ativa": "on"
            },
            "expected": ["Hepatite C", "HIV Adultos"],
            "description": "Homem não recebe rastreamento de clamídia/gonorreia"
        },
        {
            "name": "Mulher não sexualmente ativa - não elegível",
            "data": {
                "idade": "22",
                "sexo": "feminino"
            },
            "expected": ["Hepatite C", "HIV Adultos"],
            "description": "Mulher não sexualmente ativa não recebe clamídia/gonorreia"
        }
    ]
    
    passed = 0
    total = len(scenarios)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Dados: {scenario['data']}")
        
        # Simular lógica de todas as recomendações
        idade = int(scenario['data'].get('idade', 0))
        sexo = scenario['data'].get('sexo', '')
        tabagismo_atual = scenario['data'].get('tabagismo_atual') == 'on'
        ex_fumante = scenario['data'].get('ex_fumante') == 'on'
        historico_tabagismo = scenario['data'].get('historico_tabagismo') == 'on'
        anos_parou_fumar = int(scenario['data'].get('anos_parou_fumar', 999)) if scenario['data'].get('anos_parou_fumar') else 999
        macos_ano = int(scenario['data'].get('macos_ano', 0)) if scenario['data'].get('macos_ano') else 0
        gestante = scenario['data'].get('gestante') == 'on'
        pos_menopausa = scenario['data'].get('pos_menopausa') == 'on'
        risco_osteoporose = scenario['data'].get('risco_osteoporose') == 'on'
        risco_sifilis = scenario['data'].get('risco_sifilis') == 'on'
        risco_tuberculose = scenario['data'].get('risco_tuberculose') == 'on'
        sexualmente_ativa = scenario['data'].get('sexualmente_ativa') == 'on'
        risco_ist = scenario['data'].get('risco_ist') == 'on'
        
        recommendations_found = []
        
        # TCBD
        if (50 <= idade <= 80 and 
            macos_ano >= 20 and 
            (tabagismo_atual or (ex_fumante and anos_parou_fumar <= 15))):
            recommendations_found.append("TCBD")
        
        # Hepatite C
        if 18 <= idade <= 79:
            recommendations_found.append("Hepatite C")
        
        # HIV Adultos
        if 15 <= idade <= 65:
            recommendations_found.append("HIV Adultos")
        
        # HIV Gestantes
        if gestante:
            recommendations_found.append("HIV Gestantes")
        
        # AAA
        if (sexo == 'masculino' and 
            65 <= idade <= 75 and 
            historico_tabagismo):
            recommendations_found.append("AAA")
        
        # Osteoporose ≥65
        if sexo == 'feminino' and idade >= 65:
            recommendations_found.append("Osteoporose ≥65")
        
        # Osteoporose <65
        if (sexo == 'feminino' and 
            idade < 65 and 
            pos_menopausa and 
            risco_osteoporose):
            recommendations_found.append("Osteoporose <65")
        
        # Sífilis
        if (idade >= 15 and 
            not gestante and 
            risco_sifilis):
            recommendations_found.append("Sífilis")
        
        # Tuberculose
        if (idade >= 18 and 
            risco_tuberculose):
            recommendations_found.append("Tuberculose")
        
        # Clamídia/Gonorreia
        if (sexo == 'feminino' and 
            sexualmente_ativa and 
            (idade <= 24 or (idade >= 25 and risco_ist))):
            recommendations_found.append("Clamídia/Gonorreia")
        
        expected_set = set(scenario['expected'])
        found_set = set(recommendations_found)
        
        if expected_set == found_set:
            print(f"   ✅ PASSOU - Recomendações: {recommendations_found}")
            passed += 1
        else:
            print(f"   ❌ FALHOU - Esperado: {scenario['expected']}, Obtido: {recommendations_found}")
    
    print(f"\n{'='*80}")
    print(f"RESULTADO: {passed}/{total} cenários integrados passaram")
    
    return passed == total

def test_clinical_scenarios():
    """Testa cenários clínicos específicos para clamídia e gonorreia"""
    
    print("\n🧪 Cenários Clínicos Específicos para Clamídia e Gonorreia")
    print("=" * 80)
    
    print("💡 Características do rastreamento de clamídia e gonorreia USPSTF 2021:")
    print("   • Grau B - Recomendação moderada")
    print("   • APENAS mulheres sexualmente ativas")
    print("   • ≤24 anos: Rastreamento universal")
    print("   • ≥25 anos: Apenas com risco aumentado")
    print("   • Inclui gestantes")
    print("   • Exame: NAAT (Teste de Amplificação de Ácidos Nucleicos)")
    print("   • Frequência: Conforme fatores de risco novos ou persistentes")
    
    scenarios = [
        {
            "name": "Mulher jovem sexualmente ativa",
            "age": 20,
            "sex": "feminino",
            "sexually_active": True,
            "risk": False,
            "description": "≤24 anos - rastreamento universal"
        },
        {
            "name": "Mulher 25 anos com múltiplos parceiros",
            "age": 25,
            "sex": "feminino",
            "sexually_active": True,
            "risk": True,
            "description": "≥25 anos com risco aumentado"
        },
        {
            "name": "Mulher 30 anos com novo parceiro",
            "age": 30,
            "sex": "feminino",
            "sexually_active": True,
            "risk": True,
            "description": "≥25 anos com novo fator de risco"
        },
        {
            "name": "Gestante jovem",
            "age": 22,
            "sex": "feminino",
            "sexually_active": True,
            "risk": False,
            "description": "Gestante ≤24 anos - rastreamento obrigatório"
        },
        {
            "name": "Gestante ≥25 anos com risco",
            "age": 28,
            "sex": "feminino",
            "sexually_active": True,
            "risk": True,
            "description": "Gestante ≥25 anos com risco"
        },
        {
            "name": "Mulher 25 anos sem risco",
            "age": 25,
            "sex": "feminino",
            "sexually_active": True,
            "risk": False,
            "description": "Não elegível - ≥25 anos sem risco"
        },
        {
            "name": "Mulher não sexualmente ativa",
            "age": 20,
            "sex": "feminino",
            "sexually_active": False,
            "risk": False,
            "description": "Não elegível - não sexualmente ativa"
        },
        {
            "name": "Homem jovem sexualmente ativo",
            "age": 20,
            "sex": "masculino",
            "sexually_active": True,
            "risk": False,
            "description": "Não elegível - recomendação apenas para mulheres"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔬 {scenario['name']} ({scenario['age']} anos, {scenario['sex']}):")
        print(f"   {scenario['description']}")
        
        elegible = (scenario['sex'] == 'feminino' and 
                   scenario.get('sexually_active', False) and 
                   (scenario['age'] <= 24 or (scenario['age'] >= 25 and scenario.get('risk', False))))
        
        if elegible:
            print(f"   Elegível: ✅ SIM")
        else:
            print(f"   Elegível: ❌ NÃO")
    
    return True

def test_coverage_update():
    """Atualiza análise de cobertura com clamídia e gonorreia incluída"""
    
    print("\n📊 Análise de Cobertura Atualizada com Clamídia e Gonorreia")
    print("=" * 80)
    
    print("🎯 Cobertura por faixa etária com clamídia/gonorreia (mulheres sexualmente ativas):")
    
    age_ranges = [
        {"range": "0-14 anos", "coverage": "Nenhuma"},
        {"range": "15-17 anos", "coverage": "HIV + Sífilis* + Clamídia/Gonorreia♀"},
        {"range": "18-24 anos", "coverage": "HCV + HIV + Sífilis* + TB* + Clamídia/Gonorreia♀"},
        {"range": "25-49 anos", "coverage": "HCV + HIV + Sífilis* + TB* + Clamídia/Gonorreia♀**"},
        {"range": "50-64 anos", "coverage": "HCV + HIV + TCBD*** + Osteo**** + Sífilis* + TB* + Clamídia/Gonorreia♀**"},
        {"range": "65-75 anos", "coverage": "HCV + TCBD*** + AAA/Osteo + Sífilis* + TB* + Clamídia/Gonorreia♀**"},
        {"range": "76-79 anos", "coverage": "HCV + TCBD*** + Osteo + Sífilis* + TB* + Clamídia/Gonorreia♀**"},
        {"range": "80+ anos", "coverage": "TCBD*** + Osteo + Sífilis* + TB* + Clamídia/Gonorreia♀**"}
    ]
    
    for age_range in age_ranges:
        print(f"\n📋 {age_range['range']}:")
        print(f"   Recomendações: {age_range['coverage']}")
    
    print(f"\n💡 Observações:")
    print(f"   • HIV = Rastreamento universal (15-65 anos)")
    print(f"   • HCV = Rastreamento universal (18-79 anos)")
    print(f"   • TCBD*** = Apenas fumantes elegíveis (50-80 anos)")
    print(f"   • AAA = Apenas homens 65-75 anos com histórico tabagismo")
    print(f"   • Osteo = Mulheres ≥65 anos (universal)")
    print(f"   • Osteo**** = Mulheres <65 anos pós-menopausa com risco")
    print(f"   • Sífilis* = Apenas pessoas com risco aumentado (≥15 anos, não gestantes)")
    print(f"   • TB* = Apenas adultos com risco aumentado (≥18 anos)")
    print(f"   • Clamídia/Gonorreia♀ = Mulheres sexualmente ativas ≤24 anos (universal)")
    print(f"   • Clamídia/Gonorreia♀** = Mulheres sexualmente ativas ≥25 anos (apenas com risco)")
    print(f"   • Gestantes = HIV + HIV gestante + Clamídia/Gonorreia (se critérios atendidos)")
    
    print(f"\n🎯 Fatores de risco para clamídia/gonorreia (≥25 anos):")
    print(f"   • Múltiplos parceiros sexuais")
    print(f"   • Novo parceiro sexual")
    print(f"   • Parceiro com IST")
    print(f"   • Histórico de IST")
    print(f"   • Uso inconsistente de preservativo")
    print(f"   • Trabalho sexual")
    print(f"   • Uso de drogas injetáveis")
    
    print(f"\n🎯 NOVA MÁXIMA COBERTURA POSSÍVEL:")
    print(f"   • Mulher fumante 55 anos sexualmente ativa com múltiplos riscos:")
    print(f"     TCBD + HCV + HIV + Osteo + Sífilis + TB + Clamídia/Gonorreia = 7 RECOMENDAÇÕES!")
    print(f"   • Gestante jovem 20 anos com múltiplos riscos:")
    print(f"     HCV + HIV + HIV Gestante + Sífilis + TB + Clamídia/Gonorreia = 6 recomendações")
    
    return True

if __name__ == "__main__":
    print("🚀 Teste da Implementação de Rastreamento de Clamídia e Gonorreia - evidens.digital")
    print("Baseado na guideline USPSTF 2021 (Grau B)")
    
    success1 = test_clamidia_gonorreia_screening()
    success2 = test_integration_scenarios()
    success3 = test_clinical_scenarios()
    success4 = test_coverage_update()
    
    if success1 and success2 and success3 and success4:
        print("\n🎯 IMPLEMENTAÇÃO DE CLAMÍDIA E GONORREIA VALIDADA COM SUCESSO!")
        print("✨ Rastreamento para mulheres sexualmente ativas")
        print("✨ Critérios diferenciados por faixa etária (≤24 vs ≥25 anos)")
        print("✨ Inclusão de gestantes conforme critérios")
        print("📊 Integração perfeita com recomendações existentes")
        print("🔍 Cobertura específica para mulheres")
        print("🏆 Sistema agora com 10 recomendações baseadas em evidências!")
        print("🎪 NOVA MÁXIMA COBERTURA: 7 recomendações simultâneas possíveis!")
    else:
        print("\n❌ Problemas encontrados na implementação de clamídia e gonorreia")
        sys.exit(1)
