"""
Módulo para Carregar e Processar Recomendações Médicas
"""
import json
from pathlib import Path
from typing import List, Dict, Optional

# Carregar configurações
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config' / 'base_recommendations.json'

def load_base_recommendations():
    """Carrega recomendações base do arquivo de configuração"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar recomendações base: {e}")
        return None

def filter_recommendations_by_criteria(
    recommendations: List[Dict],
    age: int,
    sex: str,
    conditions: Optional[Dict] = None
) -> List[Dict]:
    """
    Filtra recomendações baseadas em critérios do paciente
    
    Args:
        recommendations: Lista de recomendações
        age: Idade do paciente
        sex: Sexo do paciente ('masculino' ou 'feminino')
        conditions: Condições médicas adicionais (opcional)
    
    Returns:
        Lista de recomendações filtradas
    """
    filtered = []
    
    for rec in recommendations:
        # Verificar idade mínima
        if 'idade_minima' in rec and age < rec['idade_minima']:
            continue
        
        # Verificar idade máxima
        if 'idade_maxima' in rec and age > rec['idade_maxima']:
            continue
        
        # Verificar sexo
        if 'sexo' in rec and rec['sexo'] != sex:
            continue
        
        # Adicionar recomendação
        filtered.append(rec.copy())
    
    return filtered

def get_recommendations_for_patient(age: int, sex: str, country: str = 'BR') -> List[Dict]:
    """
    Obtém recomendações personalizadas para um paciente
    
    Args:
        age: Idade do paciente
        sex: Sexo do paciente
        country: País para guidelines (BR ou US)
    
    Returns:
        Lista de recomendações personalizadas
    """
    config = load_base_recommendations()
    if not config:
        return []
    
    all_recommendations = []
    recommendations_data = config.get('recommendations', {})
    
    # Adicionar recomendações de laboratório básico
    lab_basic = recommendations_data.get('laboratorio_basico', [])
    all_recommendations.extend(filter_recommendations_by_criteria(lab_basic, age, sex))
    
    # Adicionar rastreamento de câncer
    if sex == 'feminino':
        cancer_fem = recommendations_data.get('rastreamento_cancer_feminino', [])
        all_recommendations.extend(filter_recommendations_by_criteria(cancer_fem, age, sex))
    elif sex == 'masculino':
        cancer_masc = recommendations_data.get('rastreamento_cancer_masculino', [])
        all_recommendations.extend(filter_recommendations_by_criteria(cancer_masc, age, sex))
    
    # Adicionar rastreamento de câncer geral
    cancer_geral = recommendations_data.get('rastreamento_cancer_geral', [])
    all_recommendations.extend(filter_recommendations_by_criteria(cancer_geral, age, sex))
    
    # Adicionar vacinação
    vacinas = recommendations_data.get('vacinacao_adulto', [])
    all_recommendations.extend(filter_recommendations_by_criteria(vacinas, age, sex))
    
    return all_recommendations

def add_reference_links(recommendations: List[Dict]) -> List[Dict]:
    """
    Adiciona links de referência às recomendações
    
    Args:
        recommendations: Lista de recomendações
    
    Returns:
        Lista de recomendações com links adicionados
    """
    from src.utils.reference_links import build_reference_links, build_reference_html
    
    for rec in recommendations:
        if 'referencia' in rec and rec['referencia']:
            rec['referencias'] = build_reference_links(rec['referencia'])
            rec['referencia_html'] = build_reference_html(rec['referencias'])
    
    return recommendations

