"""
Módulo de Gerenciamento de Referências Médicas
"""
import json
import unicodedata
from pathlib import Path

# Carregar configurações
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config' / 'medical_references.json'

def load_references():
    """Carrega referências do arquivo de configuração"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar referências médicas: {e}")
        return None

def normalize_text(value: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if not value:
        return ''
    normalized = unicodedata.normalize('NFD', str(value))
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn').lower().strip()

def build_reference_links(referencia: str):
    """
    Constrói lista de links de referência a partir de uma string
    
    Args:
        referencia (str): String de referência (ex: "USPSTF 2024", "ADA 2024")
    
    Returns:
        list: Lista de dicionários com 'label' e 'url'
    """
    if not referencia:
        return []
    
    config = load_references()
    if not config:
        return [{'label': referencia, 'url': '#'}]
    
    references_db = config.get('references', {})
    links = []
    
    # Dividir por vírgula ou "e"
    parts = referencia.replace(' e ', ',').split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Tentar encontrar referência no banco de dados
        found = False
        for key, ref_data in references_db.items():
            if key.upper() in part.upper():
                links.append({
                    'label': part,
                    'url': ref_data['url']
                })
                found = True
                break
        
        if not found:
            # Se não encontrar, adicionar sem link
            links.append({
                'label': part,
                'url': '#'
            })
    
    return links if links else [{'label': referencia, 'url': '#'}]

def build_reference_html(referencias: list) -> str:
    """
    Constrói HTML com links clicáveis para referências
    
    Args:
        referencias (list): Lista de dicionários com 'label' e 'url'
    
    Returns:
        str: HTML formatado com links
    """
    if not referencias:
        return ''
    
    html_parts = []
    for i, ref in enumerate(referencias):
        label = ref.get('label', '')
        url = ref.get('url', '#')
        
        if url and url != '#':
            html_parts.append(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')
        else:
            html_parts.append(label)
    
    return ', '.join(html_parts)

def apply_reference_overrides(recommendations):
    """
    Aplica regras de override para referências específicas
    
    Args:
        recommendations (list): Lista de recomendações
    """
    if not isinstance(recommendations, list):
        return
    
    config = load_references()
    if not config:
        return
    
    override_rules = config.get('override_rules', [])
    
    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        
        title_norm = normalize_text(rec.get('titulo', ''))
        if not title_norm:
            continue
        
        # Verificar regras de override
        for rule in override_rules:
            keywords = rule.get('keywords', [])
            if all(keyword in title_norm for keyword in keywords):
                label = rule['label']
                url = rule['url']
                rec['referencia'] = label
                rec['referencias'] = [{'label': label, 'url': url}]
                rec['referencia_html'] = build_reference_html(rec['referencias'])
                break

