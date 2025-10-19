from flask import Blueprint, request, jsonify, render_template_string, Response
import json
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.utils.analytics import analytics
from src.utils.reference_links import build_reference_links, build_reference_html
from src.utils.prevent_calculator import calculate_prevent_risk, get_risk_classification
from src.utils.reference_manager import apply_reference_overrides
try:
    from src.models.user import db
    from src.models.medical import Patient, Checkup, Recomendacao
except ImportError:
    # Modelos não disponíveis em ambiente serverless
    db = None
    Patient = None
    Checkup = None
    Recomendacao = None

checkup_intelligent_bp = Blueprint('checkup_intelligent', __name__)

def _wants_html(req: request) -> bool:
    """Detect if the client expects HTML output.
    Priority: explicit query param (format/response_type) > Accept header.
    """
    try:
        fmt = (req.args.get('format') or req.args.get('response_type') or '').lower()
        if fmt == 'html':
            return True
        if fmt == 'json':
            return False
    except Exception:
        pass
    accept = (req.headers.get('Accept') or '').lower()
    return 'text/html' in accept and 'application/json' not in accept

def _html_error_page(title: str, message: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset=\"UTF-8\"><title>{title}</title>
    <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color:#111; }}
    .wrap {{ max-width: 720px; margin: 0 auto; }}
    .card {{ background:#fff; border:1px solid #eee; border-radius:8px; padding:24px; }}
    h1 {{ font-size:18px; margin:0 0 12px; }}
    p {{ margin: 6px 0; }}
    .muted {{ color:#666; font-size: 12px; margin-top:12px; }}
    </style></head>
    <body><div class=\"wrap\"><div class=\"card\">
    <h1>{title}</h1>
    <p>{message}</p>
    <p class=\"muted\">Tente novamente ou volte e ajuste os dados.</p>
    </div></div></body></html>
    """

def parse_date_ymd(date_str):
    """
    Parse date string in multiple formats: YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD
    Returns datetime object or None if invalid
    """
    if not date_str or date_str is None:
        return None
        
    try:
        # Remove any extra whitespace
        date_str = str(date_str).strip()
        if not date_str or date_str.lower() in ['null', 'none', '']:
            return None
            
        # Try YYYY-MM-DD format first
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            pass
            
        # Try DD/MM/YYYY format
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            pass
            
        # Try YYYY/MM/DD format
        try:
            return datetime.strptime(date_str, '%Y/%m/%d')
        except ValueError:
            pass
            
    except (ValueError, TypeError, AttributeError):
        pass
        
    return None

# Funções calculate_prevent_risk e get_risk_classification agora são importadas de src.utils.prevent_calculator

def generate_biomarker_recommendations(risk_level, age, sex):
    """Gera recomendações de biomarcadores baseadas no nível de risco"""
    recommendations = []
    
    if risk_level in ['borderline', 'intermediario', 'alto']:
        recommendations.extend([
            {
                'titulo': 'Anti-HIV 1 e 2, soro',
                'descricao': 'Teste para detecção de HIV',
                'subtitulo': 'Rastreamento de HIV',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'MS 2024',
                'grau_evidencia': 'A'
            },
            {
                'titulo': 'Anti-HCV IgG, soro',
                'descricao': 'Teste para detecção de Hepatite C',
                'subtitulo': 'Rastreamento de Hepatite C',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'MS 2024',
                'grau_evidencia': 'A'
            },
            {
                'titulo': 'TOTG-75g, soro',
                'descricao': 'Teste oral de tolerância à glicose',
                'subtitulo': 'Avaliação de intolerância à glicose',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'A'
            },
            {
                'titulo': 'HbA1c, soro',
                'descricao': 'Hemoglobina glicada',
                'subtitulo': 'Rastreamento de diabetes',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'A'
            }
        ])
    
    return recommendations

def generate_age_sex_recommendations(age, sex, country='BR', has_hypertension=False, has_resistant_hypertension=False):
    """Gera recomendações baseadas em idade, sexo e condições clínicas
    
    Args:
        age: Idade do paciente
        sex: Sexo do paciente
        country: País para guidelines
        has_hypertension: Se o paciente tem hipertensão (detectado por PA ou checkboxes)
        has_resistant_hypertension: Se o paciente tem hipertensão resistente
    """
    recommendations = []

    def _add_rec(rec):
        # Evita duplicados pelo título (case-insensitive) dentro desta função
        title = (rec.get('titulo') or '').strip().lower()
        if not title:
            print(f"Recomendação ignorada: título vazio - {rec}")
            return
        
        # Verificar se já existe uma recomendação com título similar
        existing_titles = [(r.get('titulo') or '').strip().lower() for r in recommendations]
        if title in existing_titles:
            print(f"Recomendação duplicada ignorada: {title}")
            return
            
        # Garantir que campos obrigatórios estão presentes
        if 'subtitulo' not in rec or rec['subtitulo'] is None:
            rec['subtitulo'] = ''
        if 'grau_evidencia' not in rec or rec['grau_evidencia'] is None:
            rec['grau_evidencia'] = ''
            
        recommendations.append(rec)
        print(f"Recomendação adicionada: {title}")
    
    # Exames laboratoriais básicos - Rastreamento de Diabetes (3 exames separados)
    _add_rec({
        'titulo': 'Glicemia de jejum, soro',
        'descricao': 'Rastreamento de pré-diabetes e diabetes tipo 2. Valores de referência: <100 mg/dL normal, 100-125 mg/dL pré-diabetes, ≥126 mg/dL diabetes.',
        'subtitulo': 'Adultos ≥35 anos | A cada 3 anos se normal',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'ADA 2024',
        'grau_evidencia': 'A'
    })
    
    _add_rec({
        'titulo': 'Hemoglobina glicada (HbA1c), soro',
        'descricao': 'Rastreamento de pré-diabetes e diabetes tipo 2. Valores de referência: <5,7% normal, 5,7-6,4% pré-diabetes, ≥6,5% diabetes. Reflete controle glicêmico dos últimos 2-3 meses.',
        'subtitulo': 'Adultos ≥35 anos | A cada 3 anos se normal',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'ADA 2024',
        'grau_evidencia': 'A'
    })
    
    _add_rec({
        'titulo': 'TOTG-75g (Teste Oral de Tolerância à Glicose), soro',
        'descricao': 'Teste confirmatório para diabetes gestacional e rastreamento de diabetes tipo 2 quando glicemia de jejum e HbA1c são inconclusivos. Valores 2h pós-carga: <140 mg/dL normal, 140-199 mg/dL pré-diabetes, ≥200 mg/dL diabetes.',
        'subtitulo': 'Adultos ≥35 anos com glicemia/HbA1c limítrofes | Conforme indicação',
        'categoria': 'laboratorio',
        'prioridade': 'media',
        'referencia': 'ADA 2024',
        'grau_evidencia': 'A'
    })
    
    # Painel lipídico - recomendação ajustada por idade
    if age >= 40:
        # Adultos ≥40 anos
        _add_rec({
            'titulo': 'Colesterol total e frações, soro',
            'descricao': 'Painel lipídico completo (não jejum): Colesterol total, HDL-C, triglicerídeos, LDL-C calculado e non-HDL-C. Rastreamento a cada 4-6 anos. Considerar ApoB se triglicerídeos altos, diabetes ou obesidade.',
            'subtitulo': 'Adultos ≥40 anos | A cada 4-6 anos',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ACC/AHA 2019 / ESC/EAS 2019',
            'grau_evidencia': 'A'
        })
    elif age >= 20:
        # Adultos 20-39 anos
        _add_rec({
            'titulo': 'Colesterol total e frações, soro',
            'descricao': 'Colesterol total, HDL-C, triglicerídeos, LDL-C calculado e non-HDL-C. Rastreamento a cada 4-6 anos.',
            'subtitulo': 'Adultos 20-39 anos | A cada 4-6 anos',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ACC/AHA 2019',
            'grau_evidencia': 'A'
        })
    
    # Lipoproteína(a) - recomendação única na vida adulta
    if age >= 20:
        _add_rec({
            'titulo': 'Lipoproteína(a) - Lp(a), soro',
            'descricao': 'Medição única na vida adulta para refinamento de risco cardiovascular. Preferir ensaio independente de isoforma.',
            'subtitulo': 'Adultos ≥20 anos | Dose única na vida',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'ESC/EAS 2019 / EAS 2022',
            'grau_evidencia': 'B'
        })
    
    # Hemograma e TSH removidos - não há evidência para rastreamento universal
    # TSH: USPSTF grau I (evidência insuficiente)
    # Hemograma: sem guideline que recomende rastreamento universal
    
    _add_rec({
        'titulo': 'Creatinina, soro',
        'descricao': 'Avaliação da função renal',
        'subtitulo': 'Adultos ≥18 anos | Anual',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'KDIGO 2024',
        'grau_evidencia': 'A'
    })
    
    # TGO/TGP removido: sem evidência para rastreamento universal em assintomáticos
    # Apenas indicado para pacientes com fatores de risco específicos
    
    # HIV: Rastreamento para adolescentes e jovens ≤30 anos (PCDT-IST 2022)
    if age <= 30:
        _add_rec({
            'titulo': 'Anti-HIV 1 e 2, soro',
            'descricao': 'Rastreamento de HIV conforme PCDT-IST MS 2022. Adolescentes e jovens devem realizar teste anualmente.',
            'subtitulo': 'Adolescentes e jovens ≤30 anos | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'PCDT-IST MS 2022',
            'grau_evidencia': 'A'
        })
    
    _add_rec({
        'titulo': 'Anti-HCV IgG, soro',
        'descricao': 'Teste para detecção de Hepatite C',
        'subtitulo': 'Adultos ≥18 anos | Pelo menos 1x na vida',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'USPSTF 2024',
        'grau_evidencia': 'A'
    })
    
    # Exames para avaliação de hipertensão arterial (AHA 2025 / SBC 2025)
    # Apenas adicionar se o paciente tiver hipertensão
    if has_hypertension and age >= 18:
        _add_rec({
            'titulo': 'Potássio, soro',
            'descricao': 'Avaliação de distúrbios eletrolíticos e investigação de hipertensão secundária',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
        
        _add_rec({
            'titulo': 'Ácido úrico, soro',
            'descricao': 'Avaliação de risco cardiovascular e renal em pacientes hipertensos',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'B'
        })
        
        _add_rec({
            'titulo': 'EAS - Elementos Anormais e Sedimentoscopia',
            'descricao': 'Análise de urina para avaliação de lesão renal e investigação de hipertensão secundária',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
        
        _add_rec({
            'titulo': 'Razão albumina/creatinina, urina',
            'descricao': 'Avaliação de albuminúria para detecção precoce de lesão renal em hipertensos',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
    
    # Exames de imagem
    _add_rec({
        'titulo': 'Eletrocardiograma de repouso',
        'descricao': 'ECG de 12 derivações - Rastreamento cardiovascular para hipertensão, diabetes ou ≥40 anos',
        'subtitulo': 'Adultos ≥40 anos | Anual',
        'categoria': 'imagem',
        'prioridade': 'alta',
        'referencia': 'AHA 2025 / SBC 2025 / AHA 2022 / SBC 2018',
        'grau_evidencia': 'B'
    })
    
    # Exames de imagem para avaliação de hipertensão (AHA 2025 / SBC 2025)
    # Apenas adicionar se o paciente tiver hipertensão
    if has_hypertension and age >= 18:
        _add_rec({
            'titulo': 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)',
            'descricao': 'Confirmação diagnóstica de hipertensão arterial, investigação de hipertensão do avental branco e hipertensão mascarada',
            'subtitulo': 'Adultos com suspeita de HAS | Conforme necessidade',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
        
        _add_rec({
            'titulo': 'Ecocardiograma transtorácico',
            'descricao': 'Avaliação de hipertrofia ventricular esquerda, função diastólica e lesão de órgão-alvo em hipertensos',
            'subtitulo': 'Adultos com HAS | Inicial e a cada 1-2 anos',
            'categoria': 'imagem',
            'prioridade': 'media',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'B'
        })
    
    # Rastreamento de câncer por idade e sexo
    if sex == 'feminino':
        if 40 <= age <= 74:
            _add_rec({
                'titulo': 'Mamografia Digital - Bilateral',
                'descricao': 'Mamografia bienal (40-74 anos)',
                'subtitulo': 'Mulheres 40-74 anos | Bienal',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'USPSTF 2024',
                'grau_evidencia': 'B'
            })
        
        if 21 <= age <= 65:
            _add_rec({
                'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular',
                'descricao': 'Papanicolaou a cada 3 anos (21-65 anos)',
                'subtitulo': 'Mulheres 21-65 anos | A cada 3 anos',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'USPSTF',
                'grau_evidencia': 'A'
            })
    
    if sex == 'masculino' and age >= 50:
        _add_rec({
            'titulo': 'PSA total, soro',
            'descricao': 'Rastreamento de câncer de próstata (≥50 anos)',
            'subtitulo': 'Homens ≥50 anos | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'USPSTF 2018',
            'grau_evidencia': 'C'
        })
    
    # Densitometria óssea (Osteoporose)
    if sex == 'feminino' and age >= 65:
        _add_rec({
            'titulo': 'Densitometria óssea (DEXA)',
            'descricao': 'Rastreamento de osteoporose para prevenir fraturas osteoporóticas. Mulheres ≥65 anos.',
            'subtitulo': 'Mulheres ≥65 anos | A cada 2 anos',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2024',
            'grau_evidencia': 'B'
        })
    
    # Densitometria para mulheres pós-menopausa <65 anos com fatores de risco
    # Nota: Requer avaliação individualizada de fatores de risco
    
    # Colonoscopia
    if 45 <= age <= 75:
        _add_rec({
            'titulo': 'Colonoscopia de Rastreio com ou sem biópsia',
            'descricao': 'Colonoscopia a cada 10 anos (45-75 anos)',
            'subtitulo': 'Adultos 45-75 anos | A cada 10 anos',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2021',
            'grau_evidencia': 'B'
        })
    
    # Aneurisma de Aorta Abdominal (AAA)
    if sex == 'masculino' and 65 <= age <= 75:
        _add_rec({
            'titulo': 'Ultrassonografia de aorta abdominal',
            'descricao': 'Rastreamento de aneurisma de aorta abdominal. Homens 65-75 anos que já fumaram.',
            'subtitulo': 'Homens 65-75 anos que já fumaram | Dose única',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2019',
            'grau_evidencia': 'B'
        })
    
    # Vacinas
    # Influenza - nome comercial varia conforme idade
    if age >= 65:
        _add_rec({
            'titulo': 'Efluelda® (Influenza Tetravalente de Alta Dose)',
            'descricao': 'Dose anual. Vacina de alta dose ou adjuvantada recomendada para idosos. Aplicar em dose única, INTRAMUSCULAR, anualmente.',
            'subtitulo': 'Adultos ≥65 anos | Anual | Reforço: anual',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })
    else:
        _add_rec({
            'titulo': 'Influenza Tetravalente (Fluarix®, Vaxigrip® ou similar)',
            'descricao': 'Dose anual. Aplicar em dose única, INTRAMUSCULAR, anualmente.',
            'subtitulo': 'Todos ≥6 meses | Anual | Reforço: anual',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })

    # HPV (masculino e feminino) até 45 anos
    if age <= 45:
        prioridade_hpv = 'alta' if age <= 26 else 'media'
        _add_rec({
            'titulo': 'Gardasil 9® (Vacina HPV 9-Valente)',
            'descricao': '2 doses (9-14 anos) ou 3 doses (15-45 anos). Esquema 0-2-6 meses para 3 doses ou 0-6 meses para 2 doses.',
            'subtitulo': '9-45 anos | 2-3 doses conforme idade | Sem reforço',
            'categoria': 'vacina',
            'prioridade': prioridade_hpv,
            'referencia': 'SBIm 2024',
            'grau_evidencia': 'A'
        })

    # Hepatite B (adultos não vacinados)
    _add_rec({
        'titulo': 'Hepatite B (Engerix-B® ou Euvax B®)',
        'descricao': 'Esquema de 3 doses (0, 1, 6 meses) em não vacinados. Adultos até 59 anos devem ser vacinados.',
        'subtitulo': 'Adultos 19-59 anos não imunizados | 3 doses',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2025 / CDC 2025',
        'grau_evidencia': 'A'
    })

    # dTpa (Tétano, difteria, coqueluche)
    _add_rec({
        'titulo': 'dTpa (Adacel® ou Boostrix®)',
        'descricao': '1 dose de dTpa, depois reforço com dT ou dTpa a cada 10 anos. Gestantes devem receber dTpa a cada gestação.',
        'subtitulo': 'Adultos ≥18 anos | 1 dose inicial + reforços | Reforço: 10 anos (+ cada gestação)',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2025 / CDC 2025',
        'grau_evidencia': 'A'
    })

    # Tríplice viral (Sarampo, caxumba, rubéola)
    if age <= 59:  # Prioridade para adultos jovens não vacinados
        _add_rec({
            'titulo': 'Tríplice viral - SCR (Priorix® ou M-M-R® II)',
            'descricao': '1 ou 2 doses para adultos não vacinados ou sem comprovação vacinal. Adultos até 68 anos.',
            'subtitulo': 'Adultos 19-68 anos não imunizados | 1-2 doses | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })

    # Hepatite A
    _add_rec({
        'titulo': 'Hepatite A (Havrix® ou Vaqta®)',
        'descricao': '2 doses com intervalo de 6 meses. Recomendada para grupos de risco, viajantes e áreas endêmicas.',
        'subtitulo': 'Grupos de risco e viajantes | 2 doses',
        'categoria': 'vacina',
        'prioridade': 'media',
        'referencia': 'SBIm 2025 / CDC 2025',
        'grau_evidencia': 'A'
    })

    # Febre amarela (para áreas endêmicas)
    _add_rec({
        'titulo': 'Febre amarela (Stamaril®)',
        'descricao': 'Dose única ou 2 doses com intervalo de 10 anos (SBIm recomenda 2 doses). Indicada para residentes ou viajantes para áreas endêmicas.',
        'subtitulo': 'Áreas endêmicas | 1-2 doses | Reforço: 10 anos (se 2 doses)',
        'categoria': 'vacina',
        'prioridade': 'media',
        'referencia': 'SBIm 2025',
        'grau_evidencia': 'A'
    })

    # Meningocócica ACWY
    if age <= 59:
        _add_rec({
            'titulo': 'Meningocócica ACWY (Menactra® ou Menveo®)',
            'descricao': 'Dose única ou reforço a cada 5 anos para grupos de risco. Adolescentes: dose aos 11-12 anos e reforço aos 16 anos.',
            'subtitulo': 'Adolescentes 11-12 anos e adultos ≤59 anos | 1 dose | Reforço: 5 anos (grupos de risco)',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'B'
        })

    # Meningocócica B (19-23 anos)
    if 19 <= age <= 23:
        _add_rec({
            'titulo': 'Meningocócica B (Bexsero® ou Trumenba®)',
            'descricao': '2 doses conforme esquema do fabricante. Bexsero®: intervalo de 1 mês. Trumenba®: intervalo de 6 meses.',
            'subtitulo': 'Adolescentes 16-23 anos | 2 doses | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'B'
        })

    # Dengue (Qdenga)
    _add_rec({
        'titulo': 'Dengue (Qdenga®)',
        'descricao': '2 doses com intervalo de 3 meses. Indicada para áreas endêmicas. Licenciada para 4-60 anos.',
        'subtitulo': '4-60 anos (áreas endêmicas) | 2 doses (0-3 meses) | Sem reforço',
        'categoria': 'vacina',
        'prioridade': 'media',
        'referencia': 'SBIm 2025',
        'grau_evidencia': 'B'
    })

    # COVID-19
    _add_rec({
        'titulo': 'COVID-19 (Comirnaty®, Spikevax® ou outras)',
        'descricao': 'Dose de reforço anual conforme vacina disponível. Idosos ≥65 anos: pelo menos 2 doses da vacina atual.',
        'subtitulo': 'Todos ≥6 meses | Anual (atualizada)',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'CDC 2025',
        'grau_evidencia': 'A'
    })

    # Herpes zóster a partir de 50 anos
    if age >= 50:
        _add_rec({
            'titulo': 'Herpes zóster (Shingrix®)',
            'descricao': '2 doses com intervalo de 2 a 6 meses.',
            'subtitulo': 'Adultos ≥50 anos | 2 doses (0-2 a 6 meses) | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'A'
        })

    # Pneumocócicas a partir de 50 anos
    if age >= 50:
        _add_rec({
            'titulo': 'Pneumocócica Conjugada 20V (Prevenar 20®) OU 15V (Vaxneuvance®)',
            'descricao': 'VPC20 em dose única OU esquema sequencial VPC15 seguida de VPP23 após 6-12 meses. Pode ser coadministrada com Shingrix®, Efluelda® e Arexvy®.',
            'subtitulo': 'Adultos ≥50 anos | Dose única ou esquema sequencial | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })
        _add_rec({
            'titulo': 'Pneumocócica Polissacarídica 23V (Pneumovax 23®)',
            'descricao': '1 dose 6-12 meses após VPC15 (se esquema sequencial escolhido). Reforço 5 anos após a primeira dose de VPP23. Não necessária se VPC20 foi utilizada.',
            'subtitulo': 'Adultos ≥50 anos | Esquema sequencial (se VPC15) | Reforço: 5 anos',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })
    
    # Vírus Sincicial Respiratório (RSV) a partir de 50 anos
    if age >= 50:
        # Prioridade alta para ≥75 anos, média para 50-74 anos
        prioridade_rsv = 'alta' if age >= 75 else 'media'
        _add_rec({
            'titulo': 'Vírus Sincicial Respiratório - RSV (Arexvy® ou Abrysvo®)',
            'descricao': 'Dose única. Recomendada para adultos ≥50 anos com maior risco de evolução grave (cardiopatia, pneumopatia, diabetes, obesidade, nefropatia). Obrigatória para ≥75 anos. Pode ser coadministrada com Shingrix®, Efluelda® e vacinas pneumocócicas.',
            'subtitulo': 'Adultos ≥50 anos (obrigatória ≥75 anos) | Dose única | Sem reforço',
            'categoria': 'vacina',
            'prioridade': prioridade_rsv,
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })
    
    # Varicela (catapora) para suscetíveis não vacinados
    if age <= 45:  # Prioridade para adultos jovens nascidos nos EUA
        _add_rec({
            'titulo': 'Varicela (Varilrix® ou Varivax®)',
            'descricao': '2 doses com intervalo de 1-2 meses para adultos suscetíveis (sem história de doença ou vacinação prévia). Contraindicada para gestantes.',
            'subtitulo': 'Adultos suscetíveis ≤45 anos | 2 doses (0-1 a 2 meses) | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2025 / CDC 2025',
            'grau_evidencia': 'A'
        })
    
    # Hepatites A e B combinada (Twinrix) - alternativa para quem precisa das duas
    if age >= 18:
        _add_rec({
            'titulo': 'Hepatites A e B combinada (Twinrix®)',
            'descricao': '3 doses (esquema 0-1-6 meses) ou esquema acelerado (0-7-21 dias + reforço aos 12 meses). Alternativa para adultos que precisam de ambas as vacinas.',
            'subtitulo': 'Adultos não imunizados | 3-4 doses (0-1-6 meses) | Sem reforço',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2025',
            'grau_evidencia': 'A'
        })
    
    # Exames específicos para hipertensão resistente (AHA 2025 / SBC 2025)
    # Apenas adicionar se o paciente tiver hipertensão resistente
    if has_resistant_hypertension and age >= 18:
        _add_rec({
            'titulo': 'Polissonografia',
            'descricao': 'Investigação de apneia obstrutiva do sono, causa comum de hipertensão resistente. Indicada para pacientes com ronco, sonolência diurna excessiva ou pausas respiratórias durante o sono.',
            'subtitulo': 'Adultos com HAS resistente | Conforme necessidade',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
        
        _add_rec({
            'titulo': 'Doppler de artérias renais',
            'descricao': 'Investigação de estenose de artéria renal como causa de hipertensão secundária. Indicado em pacientes com hipertensão resistente, início abrupto de hipertensão grave, ou piora da função renal após IECA/BRA.',
            'subtitulo': 'Adultos com HAS resistente | Conforme necessidade',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'B'
        })
        
        _add_rec({
            'titulo': 'Relação Aldosterona/Renina (A/R)',
            'descricao': 'Rastreamento de hiperaldosteronismo primário, causa importante de hipertensão resistente. Coletar pela manhã após 2 horas em pé. Relação >20-30 sugere hiperaldosteronismo.',
            'subtitulo': 'Adultos com HAS resistente | Conforme necessidade',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
        
        _add_rec({
            'titulo': 'Metanefrinas, plasma ou urina de 24h',
            'descricao': 'Rastreamento de feocromocitoma em pacientes com hipertensão resistente, especialmente se crises hipertensivas, cefaleia, palpitações ou sudorese excessiva.',
            'subtitulo': 'Adultos com HAS resistente | Conforme necessidade',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'B'
        })
    
    return recommendations

@checkup_intelligent_bp.route('/checkup-intelligent', methods=['POST'])
def generate_intelligent_recommendations():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Extrair dados do paciente
        age = int(data.get('idade', 0))
        sex = data.get('sexo', 'masculino')
        weight = float(data.get('peso', 0)) if data.get('peso') else None
        height = float(data.get('altura', 0)) if data.get('altura') else None
        
        # Aceitar tanto 'pas' quanto 'pressao_sistolica' (compatibilidade com formulário)
        sbp_value = data.get('pas') or data.get('pressao_sistolica') or 0
        dbp_value = data.get('pad') or data.get('pressao_diastolica') or 0
        
        # Dados clínicos para PREVENT
        patient_data = {
            'age': age,
            'sex': sex,
            'totalCholesterol': float(data.get('colesterol_total', 0) or data.get('colesterol', 0)) if (data.get('colesterol_total') or data.get('colesterol')) else 0,
            'hdlCholesterol': float(data.get('hdl_colesterol', 0) or data.get('hdl', 0)) if (data.get('hdl_colesterol') or data.get('hdl')) else 0,
            'systolicBP': float(sbp_value) if sbp_value else 0,
            'diabetes': 'diabetes_tipo_2' in data.get('comorbidades', []) or 'diabetes' in data.get('comorbidades', []),
            'smoking': data.get('tabagismo') == 'fumante_atual',
            'weight': weight,
            'height': height,
            'creatinine': float(data.get('creatinina', 1.0)) if data.get('creatinina') else 1.0
        }
        
        # Calcular risco PREVENT
        risk_result = calculate_prevent_risk(patient_data)
        risk_level = 'baixo'
        
        if risk_result:
            risk_level = get_risk_classification(risk_result['risk10Year'])
        
        # Detectar hipertensão automaticamente
        has_hypertension = False
        has_resistant_hypertension = False
        
        # 1. Detecção por valores de PA (SBP >130 ou DBP >90)
        sbp = float(sbp_value) if sbp_value else 0
        dbp = float(dbp_value) if dbp_value else 0
        if sbp > 130 or dbp > 90:
            has_hypertension = True
            print(f"[DEBUG] Hipertensão detectada por PA: SBP={sbp}, DBP={dbp}")
        
        # 2. Detecção por checkboxes clínicos
        comorbidades = data.get('comorbidades', [])
        # Garantir que comorbidades é uma lista
        if isinstance(comorbidades, str):
            comorbidades = [comorbidades]
        elif not isinstance(comorbidades, list):
            comorbidades = []
        
        medicacoes_checkboxes = data.get('medicacoes', [])
        # Garantir que medicacoes é uma lista
        if isinstance(medicacoes_checkboxes, str):
            medicacoes_checkboxes = [medicacoes_checkboxes]
        elif not isinstance(medicacoes_checkboxes, list):
            medicacoes_checkboxes = []
        
        # Campo de texto de medicações contínuas
        medicacoes_continuo = (data.get('medicacoes_continuo', '') or '').lower()
        
        # Verificar se tem hipertensão nas comorbidades
        if 'hipertensao' in comorbidades or 'hipertensão' in comorbidades:
            has_hypertension = True
        
        # Verificar se tem hipertensão resistente
        if 'hipertensao_resistente' in comorbidades or 'has_resistente' in comorbidades:
            has_hypertension = True
            has_resistant_hypertension = True
        
        # Verificar se tem cardiopatia (frequentemente associada a HAS)
        if 'cardiopatia' in comorbidades:
            has_hypertension = True
        
        # Verificar se marcou checkbox de anti-hipertensivos
        if 'anti_hipertensivos' in medicacoes_checkboxes:
            has_hypertension = True
        
        # Verificar se usa medicações anti-hipertensivas no campo de texto
        anti_htn_keywords = ['losartan', 'enalapril', 'captopril', 'valsartan', 'anlodipino', 
                             'hidroclorotiazida', 'atenolol', 'propranolol', 'carvedilol',
                             'metoprolol', 'bisoprolol', 'espironolactona', 'furosemida',
                             'anti-hipertensiv', 'antihipertensiv']
        for keyword in anti_htn_keywords:
            if keyword in medicacoes_continuo:
                has_hypertension = True
                break
        
        # Gerar recomendações
        recommendations = []
        
        # Recomendações baseadas em idade, sexo e status de hipertensão
        age_sex_recs = generate_age_sex_recommendations(age, sex, country='BR', 
                                                         has_hypertension=has_hypertension,
                                                         has_resistant_hypertension=has_resistant_hypertension)
        recommendations.extend(age_sex_recs)
        
        # Recomendações de biomarcadores se necessário
        if risk_level in ['borderline', 'intermediario', 'alto']:
            biomarker_recs = generate_biomarker_recommendations(risk_level, age, sex)
            recommendations.extend(biomarker_recs)
        
        # Rastreamento de câncer de pulmão (LDCT)
        tabagismo = data.get('tabagismo', 'nunca_fumou')
        macos_ano = float(data.get('macos_ano', 0)) if data.get('macos_ano') else 0
        
        if (50 <= age <= 80 and 
            macos_ano >= 20 and 
            tabagismo in ['fumante_atual', 'ex_fumante']):
            recommendations.append({
                'titulo': 'Tomografia computadorizada de tórax de baixa dose (LDCT)',
                'descricao': 'Rastreamento anual de câncer de pulmão. Indicado para adultos 50-80 anos com história de tabagismo de 20 maços-ano e que atualmente fumam ou pararam nos últimos 15 anos. Descontinuar se não fumou por 15 anos ou desenvolveu problema de saúde que limita substancialmente expectativa de vida.',
                'subtitulo': 'Adultos 50-80 anos com 20 maços-ano | Anual',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'USPSTF 2021',
                'grau_evidencia': 'B'
            })
        
        # Rastreamento de pré-diabetes e diabetes tipo 2
        imc = None
        if weight and height:
            altura_m = height / 100
            imc = weight / (altura_m ** 2)
        
        if (35 <= age <= 70 and 
            imc and imc >= 25 and 
            'diabetes_tipo_2' not in data.get('comorbidades', [])):
            # Verifica se já não tem glicemia nas recomendações
            tem_glicemia = any('glicemia' in rec.get('titulo', '').lower() for rec in recommendations)
            if not tem_glicemia:
                recommendations.append({
                    'titulo': 'Glicemia de jejum, soro',
                    'descricao': 'Rastreamento de pré-diabetes e diabetes tipo 2. Indicado para adultos 35-70 anos com sobrepeso ou obesidade (IMC ≥25). Considerar rastreamento em idade mais precoce se história familiar, etnia de alto risco (Afro-americano, Hispânico/Latino, Asiático-americano) ou história de diabetes gestacional.',
                    'subtitulo': 'Adultos 35-70 anos com IMC ≥25 | A cada 3 anos',
                    'categoria': 'laboratorio',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021',
                    'grau_evidencia': 'B'
                })
        
    # Salvar no banco de dados se possível
        try:
            # Criar ou encontrar paciente
            patient = Patient(
                nome=data.get('nome', f'Paciente {age} anos'),
                idade=age,
                sexo=sex,
                peso=weight,
                altura=height
            )
            db.session.add(patient)
            db.session.flush()  # Para obter o ID
            
            # Criar checkup
            checkup = Checkup(
                patient_id=patient.id,
                pressao_sistolica=patient_data['systolicBP'],
                pressao_diastolica=float(data.get('pressao_diastolica', 0)) if data.get('pressao_diastolica') else None,
                colesterol_total=patient_data['totalCholesterol'],
                hdl_colesterol=patient_data['hdlCholesterol'],
                creatinina=patient_data['creatinine'],
                hba1c=float(data.get('hba1c', 0)) if data.get('hba1c') else None,
                risco_10_anos=risk_result['risk10Year'] if risk_result else None,
                risco_30_anos=risk_result['risk30Year'] if risk_result else None,
                classificacao_risco=risk_level,
                comorbidades=json.dumps(data.get('comorbidades', [])),
                historia_familiar=json.dumps(data.get('historia_familiar', [])),
                tabagismo=data.get('tabagismo', 'nunca_fumou'),
                medicacoes=data.get('medicacoes', ''),
                pais_guideline=data.get('pais_guideline', 'BR')
            )
            db.session.add(checkup)
            db.session.flush()
            
            # Salvar recomendações
            for rec in recommendations:
                recomendacao = Recomendacao(
                    checkup_id=checkup.id,
                    titulo=rec['titulo'],
                    descricao=rec['descricao'],
                    subtitulo=rec.get('subtitulo'),
                    categoria=rec['categoria'],
                    prioridade=rec['prioridade'],
                    referencia=rec['referencia'],
                    grau_evidencia=rec.get('grau_evidencia')
                )
                db.session.add(recomendacao)
            
            db.session.commit()
            
        except Exception as db_error:
            print(f"Erro ao salvar no banco: {db_error}")
            db.session.rollback()
        
        # Enriquecer recomendações com links (referencia_html)
        try:
            for rec in recommendations:
                titulo = rec.get('titulo', '')
                ref_str = rec.get('referencia', '')
                links = build_reference_links(titulo, ref_str)
                if links:
                    rec['referencias'] = links
                    rec['referencia_html'] = build_reference_html(links)
        except Exception as _e:
            # Não bloquear resposta por erro de link
            pass

        # Registrar analytics
        analytics.track_recommendation()
        
        # Preparar resposta
        response = {
            'success': True,
            'prevent_risk': risk_result,
            'risk_classification': risk_level,
            'recommendations': recommendations,
            'total_recommendations': len(recommendations)
        }
        
        # Deduplicar por título antes de responder
        try:
            seen = set()
            unique = []
            for rec in recommendations:
                key = (rec.get('titulo') or '').strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                unique.append(rec)
            response['recommendations'] = unique
            response['total_recommendations'] = len(unique)
        except Exception:
            pass

        # Garantir chaves opcionais presentes em todas as recomendações
        try:
            for rec in response.get('recommendations', []) or []:
                if 'subtitulo' not in rec or rec['subtitulo'] is None:
                    rec['subtitulo'] = ''
                if 'grau_evidencia' not in rec or rec['grau_evidencia'] is None:
                    rec['grau_evidencia'] = ''
        except Exception:
            pass

        return jsonify(response)
        
    except Exception as e:
        print(f"Erro na geração de recomendações: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@checkup_intelligent_bp.route('/generate-pdf', methods=['POST'])
def generate_pdf_report():
    """Gera relatório em PDF das recomendações"""
    try:
        data = request.get_json()
        
        # Aqui você pode implementar a geração de PDF
        # Por enquanto, retornamos uma resposta de sucesso
        
        analytics.track_pdf_generated()
        
        return jsonify({
            'success': True,
            'message': 'PDF gerado com sucesso',
            'download_url': '/download/relatorio.pdf'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@checkup_intelligent_bp.route('/gerar-receita-vacinas', methods=['POST'])
def gerar_receita_vacinas():
    try:
        data = request.get_json(silent=True) or {}
        recommendations = data.get('recommendations', []) or []
        patient_data = data.get('patient_data', {}) or {}

        nome_paciente = patient_data.get('nome', 'Paciente')
        sexo = (patient_data.get('sexo') or '').strip()

        data_atual = datetime.now().strftime("%d/%m/%Y")
        data_validade = (datetime.now() + relativedelta(months=1)).strftime("%d/%m/%Y")

        vacinas = []
        for rec in recommendations:
            try:
                if (rec.get('categoria') or '').lower() == 'vacina':
                    vacinas.append(rec)
            except Exception:
                continue

        if not vacinas:
            msg = 'Nenhuma vacina encontrada para gerar receita'
            if _wants_html(request):
                return Response(_html_error_page('Não foi possível gerar', msg), status=400, mimetype='text/html')
            return jsonify({'error': msg}), 400

        try:
            analytics.track_vaccine_prescription()
        except Exception:
            pass

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset=\"UTF-8\">
            <title>Receita de Vacinas - {nome_paciente}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.4; color: #000; }}
                .document-container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ font-size: 18px; margin-bottom: 20px; text-decoration: underline; }}
                .clinic-info {{ font-size: 12px; margin-bottom: 20px; }}
                .doctor-info {{ margin: 20px 0; font-weight: bold; }}
                .patient-info {{ margin: 20px 0; }}
                .vaccine-item {{ margin: 15px 0; font-size: 11px; }}
                .signature {{ margin-top: 50px; font-size: 10px; line-height: 1.3; }}
                .print-actions {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
                .print-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 24px; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: 600; margin: 0 10px; transition: all 0.3s ease; }}
                .print-btn:hover {{ transform: translateY(-2px); }}
                .close-btn {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }}
                @media print {{ .print-actions {{ display: none; }} body {{ margin: 0; padding: 0; }} .document-container {{ padding: 20px; }} }}
            </style>
        </head>
        <body>
            <div class=\"print-actions\">
                <button class=\"print-btn\" onclick=\"window.print()\">🖨️ Imprimir / Salvar PDF</button>
                <button class=\"print-btn close-btn\" onclick=\"window.close()\">✖️ Fechar</button>
            </div>
            <div class=\"document-container\">
                <div class=\"header\">
                    <h1>Receita Simples</h1>
                    <div class=\"clinic-info\">
                        <p><strong>Órion Business and Health</strong> &nbsp;&nbsp;&nbsp;&nbsp; Data de emissão: {data_atual}</p>
                        <p>Endereço: Avenida Portugal, 1148, Setor Marista, Goiânia - GO</p>
                        <p>Telefone: (62) 3225-5885</p>
                    </div>
                </div>
                <div class=\"doctor-info\">
                    <p>Dr(a). RODOLFO CAMBRAIA FROTA</p>
                    <p>CRM: 26815 - GO</p>
                </div>
                <div class=\"patient-info\">
                    <p><strong>Paciente:</strong> {nome_paciente} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Sexo:</strong> {sexo.capitalize()}</p>
                    <p><strong>Data de Validade:</strong> {data_validade}</p>
                </div>
                <div class=\"prescription\">
        """

        for i, vacina in enumerate(vacinas, 1):
            titulo = vacina.get('titulo', 'Vacina')
            descricao = vacina.get('descricao', 'Aplicar conforme orientação médica.')
            ref_html = vacina.get('referencia_html')
            html_content += f"""
                    <div class=\"vaccine-item\">
                        <p><strong>{i} {titulo.upper()}</strong> ---------------------------------------------------- 1 dose</p>
                        <p>{descricao}</p>"""
            if ref_html:
                html_content += f"<p><small>Ref.: {ref_html}</small></p>"
            html_content += "</div>"

        html_content += f"""
                </div>
                <div class=\"signature\">
                    <p>Receituário Simples assinado digitalmente por <strong>RODOLFO CAMBRAIA FROTA</strong> em</p>
                    <p>{data_atual} {datetime.now().strftime('%H:%M')}, conforme MP nº 2.200-2/2001, Resolução Nº CFM 2.299/2021 e</p>
                    <p>Resolução CFM Nº 2.381/2024.</p>
                    <br>
                    <p>O documento médico poderá ser validado em https://validar.iti.gov.br.</p>
                    <p>Farmacêutico, realize a dispensação em: https://prescricao.cfm.org.br/api/documento</p>
                    <br>
                    <p>Acesse o documento em:</p>
                    <p>https://prescricao.cfm.org.br/api/documento?_format=application/pdf</p>
                    <p><strong>CFMP-RE-{datetime.now().strftime('%Y%m%d%H%M')}</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        if _wants_html(request):
            return Response(html_content, mimetype='text/html')
        return jsonify({'success': True, 'html': html_content})

    except Exception as e:
        err = str(e)
        if _wants_html(request):
            return Response(_html_error_page('Erro ao gerar receita', err), status=500, mimetype='text/html')
        return jsonify({'error': err}), 500


@checkup_intelligent_bp.route('/gerar-solicitacao-exames', methods=['POST'])
def gerar_solicitacao_exames():
    try:
        data = request.get_json(silent=True) or {}
        recommendations = data.get('recommendations', []) or []
        patient_data = data.get('patient_data', {}) or {}

        nome_paciente = patient_data.get('nome', 'Paciente')
        sexo = (patient_data.get('sexo') or '').strip()

        # Data atual
        data_atual = datetime.now().strftime("%d/%m/%Y")

        # Filtrar exames (laboratoriais, rastreamento e imagem) e organizar por tipo
        exames_laboratoriais = []
        exames_imagem = []

        for rec in recommendations:
            try:
                categoria = (rec.get('categoria') or '').lower()
                titulo = (rec.get('titulo') or '').lower()
                
                # Categorizar exames laboratoriais
                if (categoria in ['laboratorial', 'laboratorio'] or
                    'soro' in titulo or 'sangue' in titulo or 'urina' in titulo or
                    'jejum' in titulo or 'glicemia' in titulo or 'colesterol' in titulo or
                    'hba1c' in titulo or 'creatinina' in titulo or 'hiv' in titulo or
                    'hepatite' in titulo or 'totg' in titulo):
                    exames_laboratoriais.append(rec)
                    print(f"Exame laboratorial adicionado: {rec.get('titulo')}")
                    
                # Categorizar exames de imagem e rastreamento
                elif (categoria in ['rastreamento', 'imagem'] or
                      'mamografia' in titulo or 'colonoscopia' in titulo or 
                      'eletrocardiograma' in titulo or 'ultrassom' in titulo or
                      'tomografia' in titulo or 'densitometria' in titulo):
                    exames_imagem.append(rec)
                    print(f"Exame de imagem/rastreamento adicionado: {rec.get('titulo')}")
                else:
                    print(f"Exame não categorizado: {rec.get('titulo')} - categoria: {categoria}")
            except Exception as e:
                print(f"Erro ao processar recomendação: {e}")
                continue

        exames = exames_laboratoriais + exames_imagem

        if not exames:
            msg = 'Nenhum exame encontrado para gerar solicitação'
            if _wants_html(request):
                return Response(_html_error_page('Não foi possível gerar', msg), status=400, mimetype='text/html')
            return jsonify({'error': msg}), 400

        # Rastrear geração de solicitação de exames
        try:
            analytics.track_exam_request()
        except Exception:
            pass

        # Gerar HTML para impressão
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset=\"UTF-8\">
            <title>Solicitação de Exames - {nome_paciente}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.4;
                    color: #000;
                }}
                .document-container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    font-size: 18px;
                    margin-bottom: 20px;
                    text-decoration: underline;
                }}
                .clinic-info {{
                    font-size: 12px;
                    margin-bottom: 20px;
                }}
                .doctor-info {{
                    margin: 20px 0;
                    font-weight: bold;
                }}
                .patient-info {{
                    margin: 20px 0;
                }}
                .exam-list {{
                    margin: 20px 0;
                }}
                .exam-list ul {{
                    list-style: none;
                    padding: 0;
                }}
                .exam-list li {{
                    margin: 8px 0;
                    padding-left: 20px;
                }}
                .signature {{
                    margin-top: 50px;
                    font-size: 10px;
                    line-height: 1.3;
                }}
                .print-actions {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                }}
                .print-btn {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    margin: 0 10px;
                    transition: all 0.3s ease;
                }}
                .print-btn:hover {{
                    transform: translateY(-2px);
                }}
                .close-btn {{
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                }}
                @media print {{
                    .print-actions {{
                        display: none;
                    }}
                    body {{
                        margin: 0;
                        padding: 0;
                    }}
                    .document-container {{
                        padding: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class=\"print-actions\">
                <button class=\"print-btn\" onclick=\"window.print()\">🖨️ Imprimir / Salvar PDF</button>
                <button class=\"print-btn close-btn\" onclick=\"window.close()\">✖️ Fechar</button>
            </div>
            
            <div class=\"document-container\">
                <div class=\"header\">
                    <h1>SOLICITAÇÃO DE EXAME</h1>
                    <div class=\"clinic-info\">
                        <p><strong>Órion Business and Health</strong> &nbsp;&nbsp;&nbsp;&nbsp; Data de emissão: {data_atual}</p>
                        <p>Endereço: Avenida Portugal, 1148, Setor Marista, Goiânia - GO</p>
                        <p>Telefone: (62) 3225-5885</p>
                    </div>
                </div>

                <div class=\"doctor-info\">
                    <p>Dr(a). RODOLFO CAMBRAIA FROTA</p>
                    <p>CRM: 26815 - GO</p>
                </div>

                <div class=\"patient-info\">
                    <p><strong>Paciente:</strong> {nome_paciente} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Sexo:</strong> {sexo.capitalize()}</p>
                </div>

                <div class=\"exam-list\">
                    <p><strong>Solicito:</strong></p>
                    <ul>
        """

        for exam in exames:
            titulo = exam.get('titulo', 'Exame')
            ref_html = exam.get('referencia_html')
            html_content += f"                        <li>• {titulo}"
            if ref_html:
                html_content += f"<br><small>Ref.: {ref_html}</small>"
            html_content += "</li>\n"

        html_content += f"""
                    </ul>
                </div>

                <div class=\"signature\">
                    <p>Solicitação de exame assinado digitalmente por <strong>RODOLFO CAMBRAIA FROTA</strong> em</p>
                    <p>{data_atual} {datetime.now().strftime('%H:%M')}, conforme MP nº 2.200-2/2001, Resolução Nº CFM 2.299/2021 e</p>
                    <p>Resolução CFM Nº 2.381/2024.</p>
                    <br>
                    <p>O documento médico poderá ser validado em https://validar.iti.gov.br.</p>
                    <br>
                    <p>Acesse o documento em:</p>
                    <p>https://prescricao.cfm.org.br/api/documento?_format=application/pdf</p>
                    <p><strong>CFMP-SE-{datetime.now().strftime('%Y%m%d%H%M')}</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        if _wants_html(request):
            return Response(html_content, mimetype='text/html')
        return jsonify({'success': True, 'html': html_content})

    except Exception as e:
        err = str(e)
        if _wants_html(request):
            return Response(_html_error_page('Erro ao gerar solicitação', err), status=500, mimetype='text/html')
        return jsonify({'error': err}), 500






# ==================== ENDPOINTS DE GERAÇÃO DE PDFs ====================

@checkup_intelligent_bp.route('/gerar-pdf-exames-laboratoriais', methods=['POST'])
def gerar_pdf_exames_laboratoriais_endpoint():
    """
    Endpoint para gerar PDF de solicitação de exames laboratoriais.
    
    Recebe JSON com:
    - dados_paciente: {nome, idade, sexo, comorbidades}
    - recomendacoes: lista de recomendações (filtra apenas laboratoriais)
    
    Retorna: PDF binário
    """
    try:
        from src.utils.pdf_service_gotenberg import gerar_pdf_exames_laboratoriais, gerar_pdf_exames_imagem, gerar_pdf_vacinas
        from flask import send_file
        import io
        from datetime import datetime
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        dados_paciente = data.get('dados_paciente', {})
        recomendacoes = data.get('recomendacoes', [])
        
        # Filtrar apenas exames laboratoriais
        exames_lab = [
            rec for rec in recomendacoes 
            if rec.get('tipo') == 'exame' and rec.get('categoria') == 'laboratorio'
        ]
        
        if not exames_lab:
            return jsonify({'error': 'Nenhum exame laboratorial encontrado'}), 400
        
        # Gerar PDF
        pdf_bytes = gerar_pdf_exames(dados_paciente, exames_lab, tipo_exame="LABORATORIAIS")
        
        # Retornar PDF
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'exames_laboratoriais_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF laboratoriais: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao gerar PDF de exames laboratoriais: {str(e)}'}), 500


@checkup_intelligent_bp.route('/gerar-pdf-exames-imagem', methods=['POST'])
def gerar_pdf_exames_imagem_endpoint():
    """
    Endpoint para gerar PDF de solicitação de exames de imagem.
    
    Recebe JSON com:
    - dados_paciente: {nome, idade, sexo, comorbidades}
    - recomendacoes: lista de recomendações (filtra apenas imagem)
    
    Retorna: PDF binário
    """
    try:
        from src.utils.pdf_service_gotenberg import gerar_pdf_exames_laboratoriais, gerar_pdf_exames_imagem, gerar_pdf_vacinas
        from flask import send_file
        import io
        from datetime import datetime
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        dados_paciente = data.get('dados_paciente', {})
        recomendacoes = data.get('recomendacoes', [])
        
        # Filtrar apenas exames de imagem
        exames_imagem = [
            rec for rec in recomendacoes 
            if rec.get('tipo') == 'exame' and rec.get('categoria') == 'imagem'
        ]
        
        if not exames_imagem:
            return jsonify({'error': 'Nenhum exame de imagem encontrado'}), 400
        
        # Gerar PDF
        pdf_bytes = gerar_pdf_exames(dados_paciente, exames_imagem, tipo_exame="DE IMAGEM")
        
        # Retornar PDF
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'exames_imagem_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF imagem: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao gerar PDF de exames de imagem: {str(e)}'}), 500


@checkup_intelligent_bp.route('/gerar-pdf-vacinas', methods=['POST'])
def gerar_pdf_vacinas_endpoint():
    """
    Endpoint para gerar PDF de prescrição de vacinas.
    
    Recebe JSON com:
    - dados_paciente: {nome, idade, sexo}
    - recomendacoes: lista de recomendações (filtra apenas vacinas)
    
    Retorna: PDF binário
    """
    try:
        from src.utils.pdf_service_gotenberg import gerar_pdf_exames_laboratoriais, gerar_pdf_exames_imagem, gerar_pdf_vacinas
        from flask import send_file
        import io
        from datetime import datetime
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        dados_paciente = data.get('dados_paciente', {})
        recomendacoes = data.get('recomendacoes', [])
        
        # Filtrar apenas vacinas
        vacinas = [
            rec for rec in recomendacoes 
            if rec.get('tipo') == 'vacina'
        ]
        
        if not vacinas:
            return jsonify({'error': 'Nenhuma vacina encontrada'}), 400
        
        # Gerar PDF
        pdf_bytes = gerar_pdf_vacinas(dados_paciente, vacinas)
        
        # Retornar PDF
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'vacinas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar PDF vacinas: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erro ao gerar PDF de vacinas: {str(e)}'}), 500
