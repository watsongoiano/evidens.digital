import re
from flask import Blueprint, request, jsonify
from datetime import datetime
from src.utils.reference_links import build_reference_links, build_reference_html
from src.utils import coerencia
from src.utils import colo_utero
from src.utils import hiv
from src.utils import condicoes
from src.utils import prenatal
from src.utils import prevent
from src.utils import rastreio_cancer
from src.utils.seguranca_vacinas import aplicar_triagem_vacinas
from src.utils.validacao import EntradaInvalida, SIM, ler_numero, normalizar_triagem, validar_entrada

checkup_intelligent_bp = Blueprint('checkup_intelligent', __name__)

def generate_age_sex_recommendations(age, sex, country='BR', has_hypertension=False, has_resistant_hypertension=False, is_pregnant=False, tabagismo='nunca_fumou', macos_ano=0, has_dpoc=False, has_cardiopatia_cronica=False,
                                     pa_alterada=False, rastreio_dm=None, risco_drc=False, rastrear_hbv=False, prep=False, fatores_osso=False,
                                     confirmar_drc=False, confirmar_dm=False):
    """Gera recomendações baseadas em idade, sexo e condições clínicas
    
    Args:
        age: Idade do paciente
        sex: Sexo do paciente
        country: País para guidelines
        has_hypertension: Se o paciente tem hipertensão (detectado por PA ou checkboxes)
        has_resistant_hypertension: Se o paciente tem hipertensão resistente
        pa_alterada: PA de consultório ≥ 130/80 sem HAS conhecida (só pede MRPA ou MAPA)
        rastreio_dm: grupo do critério de rastreio de diabetes (criterio_rastreio_dm) ou None
        risco_drc: fator de risco para DRC (TFG e albuminúria)
        rastrear_hbv: painel de hepatite B de rastreio
        prep: uso de PrEP (teste de sífilis)
        fatores_osso: mulher de 50-64 anos com fator de risco para fratura
        confirmar_drc: TFG < 60 isolada sem DRC marcada (repetir creatinina/TFG e uACR em 3 meses)
        confirmar_dm: HbA1c ≥ 6,5% isolada sem diabetes marcado (repetir HbA1c ou glicemia de jejum)
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
            # A regra repetida não entra de novo, mas a periodicidade dela continua valendo
            # (src/utils/periodicidade.py usa o menor intervalo entre as regras do mesmo exame).
            existente = recommendations[existing_titles.index(title)]
            if (rec.get('subtitulo') or '') != (existente.get('subtitulo') or ''):
                existente.setdefault('_subtitulos', []).append(rec.get('subtitulo') or '')
            return
            
        # Garantir que campos obrigatórios estão presentes
        if 'subtitulo' not in rec or rec['subtitulo'] is None:
            rec['subtitulo'] = ''
        if 'grau_evidencia' not in rec or rec['grau_evidencia'] is None:
            rec['grau_evidencia'] = ''
            
        recommendations.append(rec)
        print(f"Recomendação adicionada: {title}")
    
    # Rastreamento de pré-diabetes e diabetes tipo 2 (ADA 2026, seção 2; USPSTF 2021): o critério vem da rota
    # (criterio_rastreio_dm). Um exame basta: HbA1c, com a glicemia de jejum como alternativa na descrição.
    if rastreio_dm:
        _add_rec({
            'titulo': 'Hemoglobina glicada (HbA1c), soro',
            'descricao': 'Rastreamento de pré-diabetes e diabetes tipo 2. Um exame basta: HbA1c ou, como alternativa, '
                         'glicemia de jejum. HbA1c < 5,7% normal, 5,7-6,4% pré-diabetes, ≥ 6,5% diabetes (glicemia: < 100, '
                         '100-125 e ≥ 126 mg/dL). Repetir a cada 3 anos se normal e anualmente no pré-diabetes.',
            'subtitulo': rastreio_dm + ' | A cada 3 anos se normal',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ADA 2026 / USPSTF 2021',
            'grau_evidencia': 'B'
        })

    # HbA1c ≥ 6,5% isolada, sem diabetes marcado: confirmar antes de rotular (ADA 2026, seção 2).
    if confirmar_dm:
        _add_rec({
            'titulo': 'Hemoglobina glicada (HbA1c), soro',
            'descricao': 'HbA1c ≥ 6,5% sem diagnóstico de diabetes: repetir a HbA1c ou, como alternativa, dosar a glicemia '
                         'de jejum. Sem hiperglicemia inequívoca, o diagnóstico exige dois resultados alterados (na mesma '
                         'amostra ou em amostras separadas).',
            'subtitulo': 'HbA1c ≥ 6,5% sem diagnóstico de diabetes | Para confirmar o diagnóstico',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ADA 2026',
            'grau_evidencia': 'B'
        })

    _add_rec({
        'titulo': 'TOTG-75g (Teste Oral de Tolerância à Glicose), soro',
        'descricao': 'Indicado quando glicemia de jejum ou HbA1c estão na faixa de pré-diabetes: confirma ou afasta diabetes (SBD 2024). No rastreamento de rotina bastam glicemia de jejum e HbA1c (ADA 2026). A SBD prefere a glicemia de 1 h: <155 mg/dL normal, 155-208 pré-diabetes, ≥209 diabetes; em 2 h: <140 normal, 140-199 pré-diabetes, ≥200 diabetes. Não se pede a quem já tem diabetes.',
        'subtitulo': 'Glicemia ou HbA1c limítrofes (pré-diabetes) | Para confirmar o diagnóstico',
        'categoria': 'laboratorio',
        'prioridade': 'media',
        'referencia': 'SBD 2024 / ADA 2026',
        'grau_evidencia': 'A'
    })

    # Perfil lipídico (ACC/AHA 2026, dislipidemia). A partir dos 76 anos, fora de prevenção secundária, o
    # rastreio é decisão individual (a USPSTF 2022 sobre estatina vai até 75 anos).
    if age >= 76:
        _add_rec({
            'titulo': 'Colesterol total e frações, soro',
            'descricao': 'Painel lipídico (não jejum). A partir dos 76 anos, sem doença cardiovascular estabelecida, pedir '
                         'conforme a expectativa de vida e se o resultado mudar a conduta (início ou manutenção de estatina).',
            'subtitulo': 'Adultos ≥76 anos | Decisão individual (expectativa de vida, prevenção secundária)',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'ACC/AHA 2026 / USPSTF 2022 (estatina)',
            'grau_evidencia': 'C'
        })
    elif age >= 40:
        # Adultos ≥40 anos
        _add_rec({
            'titulo': 'Colesterol total e frações, soro',
            'descricao': 'Painel lipídico completo (não jejum): Colesterol total, HDL-C, triglicerídeos, LDL-C calculado e non-HDL-C. Rastreamento a cada 4-6 anos. Considerar ApoB se triglicerídeos altos, diabetes ou obesidade.',
            'subtitulo': 'Adultos ≥40 anos | A cada 4-6 anos',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'ACC/AHA 2026',
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
            'referencia': 'ACC/AHA 2026',
            'grau_evidencia': 'A'
        })

    # Lipoproteína(a): uma vez na vida adulta, de preferência cedo (ACC/AHA 2026)
    if 20 <= age <= 75:
        _add_rec({
            'titulo': 'Lipoproteína(a) - Lp(a), soro',
            'descricao': 'Medição única na vida adulta para refinamento de risco cardiovascular, se nunca dosada. Preferir ensaio independente de isoforma.',
            'subtitulo': 'Adultos 20-75 anos | Dose única na vida',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'ACC/AHA 2026',
            'grau_evidencia': 'B'
        })

    # Hemograma e TSH removidos - não há evidência para rastreamento universal
    # TSH: USPSTF grau I (evidência insuficiente)
    # Hemograma: sem guideline que recomende rastreamento universal

    # DRC: não há rastreio universal. Quem tem fator de risco faz TFG estimada e albuminúria juntas
    # (KDIGO 2024, Practice Point 1.1.1.1). O diabetes tem regra própria (ADA), e as medicações nefrotóxicas
    # ou que mexem no potássio, a delas (src/utils/condicoes.py).
    # TFG < 60 isolada, sem DRC marcada: confirmar a cronicidade antes de rotular (KDIGO 2024, PP 1.1.3.1-1.1.3.2).
    if confirmar_drc:
        for titulo, descricao in (
                ('Creatinina, soro', 'TFG estimada < 60 sem diagnóstico de DRC: repetir a creatinina com TFG estimada '
                                     '(CKD-EPI 2021) em 3 meses. Um resultado isolado pode ser lesão renal aguda; a DRC '
                                     'exige alteração por 3 meses ou mais.'),
                ('Relação albumina/creatinina urinária (uACR)', 'TFG estimada < 60 sem diagnóstico de DRC: albuminúria junto '
                                                                'da TFG repetida em 3 meses, para confirmar e estadiar a DRC.')):
            _add_rec({
                'titulo': titulo,
                'descricao': descricao,
                'subtitulo': 'TFG < 60 isolada, DRC a confirmar | Repetir em 3 meses',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'KDIGO 2024',
                'grau_evidencia': 'PP'
            })

    if risco_drc:
        for titulo, descricao in (
                ('Creatinina, soro', 'Creatinina com TFG estimada (CKD-EPI 2021), junto da albuminúria, em quem tem fator de '
                                     'risco para doença renal crônica.'),
                ('Relação albumina/creatinina urinária (uACR)', 'Albuminúria (relação albumina/creatinina em amostra de urina), '
                                                                'junto da TFG estimada, em quem tem fator de risco para doença renal crônica.')):
            _add_rec({
                'titulo': titulo,
                'descricao': descricao,
                'subtitulo': 'Adultos com fator de risco para DRC (HAS, DCV, insuficiência cardíaca, doença renal na família) | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'KDIGO 2024',
                'grau_evidencia': 'PP'
            })

    # TGO/TGP removido: sem evidência para rastreamento universal em assintomáticos
    # Apenas indicado para pacientes com fatores de risco específicos

    # HIV: pelo menos uma vez dos 15 aos 65 anos (USPSTF 2019, A); adolescentes e jovens até 30 anos, anual
    # (PCDT-IST MS 2022, Quadro 5). Acima de 65 anos, só com risco (orientação na rota).
    if age <= 30:
        _add_rec({
            'titulo': 'Anti-HIV 1 e 2, soro',
            'descricao': 'Rastreamento de HIV conforme PCDT-IST MS 2022. Adolescentes e jovens devem realizar teste anualmente.',
            'subtitulo': 'Adolescentes e jovens ≤30 anos | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'PCDT-IST MS 2022 / USPSTF 2019',
            'grau_evidencia': 'A'
        })
    elif age <= 65:
        _add_rec({
            'titulo': 'Anti-HIV 1 e 2, soro',
            'descricao': 'Rastreamento de HIV: pelo menos um teste na vida dos 15 aos 65 anos, independentemente de risco; '
                         'repetir em quem tem risco aumentado (populações-chave, parcerias múltiplas, IST, uso de PrEP).',
            'subtitulo': 'Adultos 15-65 anos | Pelo menos 1x na vida',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2019',
            'grau_evidencia': 'A'
        })

    _add_rec({
        'titulo': 'Anti-HCV IgG, soro',
        'descricao': 'Teste para detecção de Hepatite C: todas as pessoas a partir dos 18 anos pelo menos uma vez; '
                     'intensificar a oferta a partir dos 40 anos.',
        'subtitulo': 'Adultos ≥18 anos | Pelo menos 1x na vida',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'MS 2026 (PCDT Hepatite C) / USPSTF 2020',
        'grau_evidencia': 'B'
    })

    # Hepatite B (decisão do responsável clínico, unindo as fontes): painel triplo uma vez em adulto sem vacinação
    # documentada (CDC 2023; MS, PCDT IST 2022: rastrear suscetíveis) e repetir com fator de risco (USPSTF 2020, B).
    if rastrear_hbv:
        _add_rec({
            'titulo': 'HBsAg, anti-HBc total e anti-HBs',
            'descricao': 'Rastreamento de hepatite B com o painel triplo, uma vez, em adulto sem vacinação completa '
                         'documentada (3 doses). Anti-HBs reagente sem HBsAg e anti-HBc: imune, não precisa vacinar. Painel '
                         'todo não reagente: suscetível, vacinar. HBsAg ou anti-HBc reagente: investigar infecção. Repetir '
                         'se houver fator de risco (USPSTF 2020).',
            'subtitulo': 'Adultos ≥18 anos sem vacinação documentada | Pelo menos 1x na vida',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'CDC 2023 (hepatite B) / PCDT-IST MS 2022 / USPSTF 2020',
            'grau_evidencia': 'B'
        })

    # PrEP (HIV, sífilis, hepatites e IST na periodicidade do PCDT PrEP 2024, Quadro 5): src/utils/condicoes.py.
    # Sem PrEP, a sífilis fica como orientação para quem tem risco aumentado (orientacoes_de_rastreio).

    # Hipertensão (SBC 2025 / AHA/ACC 2025). Uma PA de consultório isolada não rotula HAS: o bloco de HAS só
    # entra com HAS marcada pelo médico, anti-hipertensivo em uso ou PA ≥ 180/110 (has_hypertension). PA
    # alterada sem HAS conhecida (pa_alterada) pede só MRPA ou MAPA para confirmar.
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
            'descricao': 'Avaliação inicial do hipertenso: a SBC 2025 o inclui na rotina; na AHA/ACC é exame opcional, não seriado.',
            'subtitulo': 'Adultos com HAS | Avaliação inicial',
            'categoria': 'laboratorio',
            'prioridade': 'baixa',
            'referencia': 'SBC 2025 / AHA 2025',
            'grau_evidencia': 'C'
        })

        _add_rec({
            'titulo': 'EAS - Elementos Anormais e Sedimentoscopia',
            'descricao': 'Análise de urina na avaliação inicial do hipertenso (lesão renal e hipertensão secundária).',
            'subtitulo': 'Adultos com HAS | Avaliação inicial',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'B'
        })

        _add_rec({
            'titulo': 'Relação albumina/creatinina urinária (uACR)',
            'descricao': 'Avaliação de albuminúria para detecção precoce de lesão renal em hipertensos',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })

        _add_rec({
            'titulo': 'Creatinina, soro',
            'descricao': 'Creatinina com TFG estimada (CKD-EPI 2021) na avaliação inicial e no seguimento da HAS.',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })

        for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
            _add_rec({
                'titulo': titulo,
                'descricao': 'Glicemia de jejum e HbA1c fazem parte dos exames de rotina da avaliação do hipertenso.',
                'subtitulo': 'Adultos com HAS | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'SBC 2025 / AHA 2025',
                'grau_evidencia': 'B'
            })

        _add_rec({
            'titulo': 'Eletrocardiograma de repouso',
            'descricao': 'ECG de 12 derivações na avaliação inicial e no seguimento da HAS (hipertrofia ventricular '
                         'esquerda, arritmias, isquemia).',
            'subtitulo': 'Adultos com HAS | Anual',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'SBC 2025 / AHA 2025',
            'grau_evidencia': 'B'
        })

        _add_rec({
            'titulo': 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)',
            'descricao': 'HAS estabelecida: MAPA de 24 h ou, como alternativa, MRPA (7 dias) para avaliar o controle, o '
                         'efeito do avental branco e a hipertensão mascarada.',
            'subtitulo': 'Adultos com HAS (avaliar controle, avental branco ou hipertensão mascarada) | Conforme necessidade',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })

        # Ecocardiograma: na AHA/ACC 2025 é exame opcional, guiado pela indicação; não há base para repetir a cada
        # 1-2 anos em toda HAS. Entra sozinho na HAS resistente; nos demais casos, orientação (rota).
        if has_resistant_hypertension:
            _add_rec({
                'titulo': 'Ecocardiograma transtorácico',
                'descricao': 'HAS resistente: avaliação de hipertrofia ventricular esquerda, função diastólica e lesão de '
                             'órgão-alvo.',
                'subtitulo': 'HAS resistente | Conforme indicação clínica',
                'categoria': 'imagem',
                'prioridade': 'media',
                'referencia': 'AHA 2025 / SBC 2025',
                'grau_evidencia': 'B'
            })
    elif pa_alterada and age >= 18:
        _add_rec({
            'titulo': 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)',
            'descricao': 'PA de consultório alterada sem diagnóstico de HAS: confirmar fora do consultório com MAPA de 24 h '
                         'ou, como alternativa, MRPA (7 dias), e repetir a PA em outra consulta. A investigação de lesão de '
                         'órgão-alvo (exames da HAS) só depois de confirmar.',
            'subtitulo': 'PA de consultório alterada, HAS a confirmar | Para confirmar o diagnóstico',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / SBC 2025',
            'grau_evidencia': 'A'
        })
    
    # Rastreamento de câncer por idade e sexo: mamografia e PSA (src/utils/rastreio_cancer.py).
    # Colo do útero: regras em src/utils/colo_utero.py (dependem de imunossupressão e do último resultado).
    for rec in rastreio_cancer.mama_e_prostata(age, sex):
        _add_rec(rec)
    
    # Densitometria óssea (Osteoporose)
    if sex == 'feminino' and age >= 65:
        _add_rec({
            'titulo': 'Densitometria óssea (DEXA)',
            'descricao': 'Rastreamento de osteoporose para prevenir fraturas osteoporóticas. Mulheres ≥65 anos. A USPSTF '
                         'não define intervalo: repetir conforme o T-score e o risco (BHOF).',
            'subtitulo': 'Mulheres ≥65 anos | Repetir conforme o resultado (T-score)',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2025 / BHOF 2022',
            'grau_evidencia': 'B'
        })

    # Mulher pós-menopausa < 65 anos com fator de risco (USPSTF 2025, B): estimar o risco (FRAX) e rastrear se
    # elevado. O formulário não pergunta a menopausa: o texto pede que o médico confirme.
    if sex == 'feminino' and 50 <= age < 65 and fatores_osso:
        _add_rec({
            'titulo': 'Densitometria óssea (DEXA)',
            'descricao': 'Mulher pós-menopausa com menos de 65 anos e fator de risco para fratura: calcular o FRAX (Brasil) '
                         'e pedir a densitometria se o risco estiver elevado. Sugerimos confirmar que a paciente está na pós-menopausa.',
            'subtitulo': 'Pós-menopausa <65 anos com fator de risco | Fator de risco',
            'categoria': 'imagem',
            'prioridade': 'media',
            'referencia': 'USPSTF 2025 / BHOF 2022',
            'grau_evidencia': 'B'
        })
    
    # Colorretal: colonoscopia ou FIT, 45-75 anos (src/utils/rastreio_cancer.py)
    for rec in rastreio_cancer.colorretal(age):
        _add_rec(rec)
    
    # Aneurisma de Aorta Abdominal (AAA), USPSTF 2019: homem de 65 a 75 anos que já fumou (100 cigarros ou mais na
    # vida), ultrassonografia uma vez (B). Homem que nunca fumou: oferta seletiva (C), em orientação na rota.
    if sex == 'masculino' and 65 <= age <= 75 and tabagismo in ('atual', 'ex'):
        _add_rec({
            'titulo': 'Ultrassonografia com Doppler de Aorta Abdominal',
            'descricao': 'Rastreamento de aneurisma de aorta abdominal: uma ultrassonografia em homens de 65 a 75 anos que '
                         'já fumaram (100 cigarros ou mais na vida), qualquer que seja a carga tabágica.',
            'subtitulo': 'Homens 65-75 anos que já fumaram | Uma vez',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2019',
            'grau_evidencia': 'B'
        })

    # ===================== VACINAS — Calendários SBIm 2026/2027 =====================
    # Adolescente (até 19 anos), Adulto (20-59) e Idoso (60+). Uma recomendação por
    # vacina: quando há alternativas (vacinas isoladas x combinada, VPC20 x esquemas
    # antigos), elas vão na descrição, não em cartões separados.
    REF_SBIM = 'SBIm 2026/2027'
    adolescente = age < 20
    idoso = age >= 60

    # Influenza
    if idoso:
        _add_rec({
            'titulo': 'Influenza trivalente de alta concentração (Efluelda®, HD3V)',
            'descricao': 'Dose única anual. Para 60+ a SBIm prefere a HD3V; se indisponível, usar 3V ou 4V padrão. Com fator de risco e situação epidemiológica, considerar 2ª dose 3 meses após.',
            'subtitulo': '60+ anos | Dose anual | PNI: 3V; rede privada: 3V, 4V, HD3V',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })
    else:
        _add_rec({
            'titulo': 'Influenza (trivalente ou quadrivalente)',
            'descricao': 'Dose única anual. Com fator de risco e situação epidemiológica, considerar 2ª dose 3 meses após a dose anual.',
            'subtitulo': 'Rotina | Dose anual | PNI: 3V (grupos de risco); rede privada: 3V, 4V',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # HPV (a triagem retira em gestantes)
    if age <= 45:
        esquema_hpv = ('2 doses (0-6 meses) para não vacinados com menos de 20 anos.' if adolescente
                       else '3 doses (0-1 a 2-6 meses) para não vacinados a partir de 20 anos.')
        _add_rec({
            'titulo': 'Gardasil 9® (Vacina HPV 9-Valente)',
            'descricao': f'{esquema_hpv} Preferir HPV9 e revacinar quem recebeu HPV2/HPV4. Contraindicada na gestação. PNI oferece HPV4 a grupos específicos (imunossuprimidos, PrEP, vítimas de violência sexual, pós-tratamento de lesão de alto grau).',
            'subtitulo': ('Até 19 anos | 2 doses (0-6m)' if adolescente else '20-45 anos | 3 doses (0-1/2-6m)') + ' | Sem reforço',
            'categoria': 'vacina', 'prioridade': 'alta' if age <= 26 else 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # dTpa
    _add_rec({
        'titulo': 'dTpa (Adacel® ou Boostrix®)',
        'descricao': 'Esquema completo: reforço com dTpa a cada 10 anos. Incompleto: 1 dose de dTpa e completar com dT até 3 doses com componente tetânico. Não vacinado/desconhecido: 1 dTpa + 2 dT (0-2-4 a 8 meses). Contactante de lactente: considerar antecipar o reforço para 5 anos. Viagem a área com pólio: dTpa-VIP.'
                     + (' Gestante: 1 dose de dTpa a cada gestação, a partir de 20 semanas; não feita na gestação, até 45 dias após o parto.' if is_pregnant else ''),
        'subtitulo': 'Gestante | 1 dose a cada gestação a partir de 20 sem | PNI: sim' if is_pregnant else 'Rotina | Reforço a cada 10 anos (+ cada gestação)',
        'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM + (' / IN CNV 2026 (MS)' if is_pregnant else ''), 'grau_evidencia': 'A'
    })

    # Hepatites: uma recomendação só
    if idoso:
        _add_rec({
            'titulo': 'Hepatite B (Engerix-B® ou Euvax B®)',
            'descricao': 'Para não vacinados previamente: 3 doses (0-1-6 meses). Hepatite A em 60+ só em situações especiais (sorologia negativa, exposição, surto).',
            'subtitulo': '60+ não vacinados | 3 doses (0-1-6m) | PNI: sim',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })
    else:
        _add_rec({
            'titulo': 'Hepatites A e B (Twinrix® ou vacinas isoladas)',
            'descricao': 'Para não vacinados: combinada A+B em 3 doses (0-1-6 meses), ou vacinas isoladas — hepatite A em 2 doses (0-6 meses) e hepatite B em 3 doses (0-1-6 meses). Hepatite B é gratuita no PNI; hepatite A e a combinada, só na rede privada. Indicar apenas o componente que faltar.',
            'subtitulo': 'Não vacinados | Combinada 0-1-6m ou isoladas | PNI: hepatite B',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # Tríplice viral e varicela: rotina até 59 anos; em 60+ só em situação especial
    if not idoso:
        _add_rec({
            'titulo': 'Tríplice Viral - SCR (Priorix® ou M-M-R® II)',
            'viva_atenuada': True,
            'descricao': '2 doses (intervalo mínimo de 1 mês) para quem não tem esquema completo. Com esquema completo não há 3ª dose de rotina (considerar em surto). Suscetível a varicela: considerar a tetraviral (SCRV).',
            'subtitulo': 'Não vacinados ou incompletos | 2 doses | PNI: 2 doses até 29 anos, 1 dose 30-59',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })
        _add_rec({
            'titulo': 'Varicela (Varilrix® ou Varivax®)',
            'viva_atenuada': True,
            'descricao': 'Para suscetíveis (sem doença ou vacinação prévia): 2 doses com intervalo de 1 a 2 meses. Considerar a tetraviral (SCRV) se também precisar da tríplice viral.',
            'subtitulo': 'Suscetíveis | 2 doses (0-1 a 2m) | PNI: sim',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # Febre amarela
    _add_rec({
        'titulo': 'Febre Amarela (Stamaril®)',
        'viva_atenuada': True,
        'descricao': 'SBIm: 2 doses com intervalo de 10 anos. PNI: dose única se a primeira foi aplicada a partir dos 5 anos. Para CIVP, aplicar até 10 dias antes da viagem.' + (' A partir de 60 anos, avaliar risco e benefício.' if idoso else ''),
        'subtitulo': 'Não vacinados | SBIm: 2 doses (intervalo de 10 anos) | PNI: sim',
        'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
    })

    # Meningocócicas: rotina no adolescente; no adulto, conforme situação epidemiológica
    if adolescente:
        _add_rec({
            'titulo': 'Meningocócica ACWY (Menactra® ou Menveo®)',
            'descricao': 'Vacinados na infância: reforço aos 11 anos ou 5 anos após a última dose. Não vacinados a partir de 16 anos: dose única. Sem ACWY, usar meningocócica C conjugada.',
            'subtitulo': 'Adolescentes | Rotina | Rede privada',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
        })
        _add_rec({
            'titulo': 'Meningocócica B (Bexsero®)',
            'descricao': '2 doses com intervalo mínimo de 1 mês. Grupos de alto risco para doença meningocócica invasiva têm esquema e reforços diferentes.',
            'subtitulo': 'Adolescentes | Rotina | 2 doses | Rede privada',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
        })
    elif not idoso:
        _add_rec({
            'titulo': 'Meningocócica ACWY (Menactra® ou Menveo®)',
            'descricao': 'Dose única, conforme situação epidemiológica (surto, viagem a área de risco). Sem ACWY, usar meningocócica C conjugada.',
            'subtitulo': 'Adultos | Conforme situação epidemiológica | Dose única',
            'categoria': 'vacina', 'prioridade': 'baixa', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
        })
        if age <= 50:
            _add_rec({
                'titulo': 'Meningocócica B (Bexsero®)',
                'descricao': '2 doses com intervalo mínimo de 1 mês, conforme situação epidemiológica. Licenciada até 50 anos.',
                'subtitulo': 'Adultos até 50 anos | Conforme situação epidemiológica | 2 doses',
                'categoria': 'vacina', 'prioridade': 'baixa', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
            })

    # Dengue (Qdenga) — triagem retira em gestante e lactante
    if 4 <= age <= 60:
        _add_rec({
            'titulo': 'Dengue (Qdenga®)',
            'viva_atenuada': True,
            'descricao': '2 doses com intervalo de 3 meses (0-3), independentemente de contato prévio com dengue. Licenciada de 4 a 60 anos. Contraindicada em gestantes, lactantes e imunossuprimidos (inclusive terapia imunossupressora). Intervalo de 30 dias com outra vacina atenuada não aplicada no mesmo dia. PNI: só de 10 a 14 anos. A Butantan-DV (dose única, 12 a 59 anos) foi aprovada pela Anvisa em 2025, mas ainda não consta da IN CNV 2026.',
            'subtitulo': 'Até 60 anos | 2 doses (0-3m) | Rede privada',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM + ' / SBIm Pacientes Especiais 2026/2027 / IN CNV 2026 (MS) / Anvisa 2025 (Butantan-DV)', 'grau_evidencia': 'B'
        })

    # COVID-19
    _add_rec({
        'titulo': 'COVID-19 (Comirnaty®, Spikevax® ou outras)',
        'descricao': ('1 dose a cada 6 meses. ' if idoso else '') + 'Conferir vacinas disponíveis e grupos contemplados pelo PNI (gov.br/saude).',
        'subtitulo': '60+ | 1 dose a cada 6 meses' if idoso else 'Rotina | Conforme PNI vigente',
        'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
    })

    # Herpes zóster a partir de 50 anos
    if age >= 50:
        _add_rec({
            'titulo': 'Herpes Zóster (Shingrix®)',
            'descricao': '2 doses com intervalo de 2 meses (0-2). Indicada mesmo após herpes-zóster (aguardar 6 meses ou a resolução). Após vacina atenuada prévia, aguardar no mínimo 2 meses.',
            'subtitulo': 'A partir de 50 anos | 2 doses (0-2m) | Rede privada',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # Pneumocócica: VPC20 em dose única (substitui o esquema VPC + VPP23). SBIm: rotina a partir
    # de 50 anos e em qualquer idade com comorbidade de risco (cardiopatia ou pneumopatia crônica).
    if age >= 50 or has_dpoc or has_cardiopatia_cronica:
        _add_rec({
            'titulo': 'Pneumocócica conjugada 20-valente (Prevenar 20®)',
            'descricao': 'Dose única. Já recebeu VPP23: aguardar 1 ano. Esquema incompleto com VPC13/VPC15 (± VPP23): completar com VPC20 (2 meses após VPC13/15 ou 1 ano após VPP23). Esquema completo (VPC13/15 + VPP23): dose adicional a critério médico.',
            'subtitulo': ('A partir de 50 anos' if age >= 50 else 'Comorbidade de risco (' + ', '.join(
                x for x, sim in (('DPOC', has_dpoc), ('doença cardiovascular crônica', has_cardiopatia_cronica)) if sim)
                + ')') + (' | Dose única | PNI: sim (≥ 85 anos)' if age >= 85 else
                        ' | Dose única | PNI: acamados/institucionalizados; CRIE p/ comorbidades' if age >= 60 else
                        ' | Dose única | PNI: grupos de risco (CRIE)'),
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM + (' / IN CNV 2026 (MS)' if age >= 60 else ''), 'grau_evidencia': 'A'
        })

    # Vírus sincicial respiratório
    if is_pregnant and sex == 'feminino':
        _add_rec({
            'titulo': 'RSV - Vírus Sincicial Respiratório (Abrysvo®)',
            'descricao': 'SBIm/PNI: a partir de 28 semanas, sem limite superior (exceto em trabalho de parto), 1 dose a cada gestação (24-27 semanas a critério médico). Bula: preferencialmente de 24 a 36 semanas. ACIP/ACOG: 32 a 36 semanas, na sazonalidade, e sem dose em gestação subsequente. Única vacina VSR licenciada para gestantes.',
            'subtitulo': 'Gestantes ≥28 sem (SBIm) ou 32-36 sem (ACOG) | Dose única por gestação | PNI: sim',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM + ' / CVE-SP/PNI 2025 (VSR na gestante) / ACOG 2023', 'grau_evidencia': 'A'
        })
    elif age >= 70:
        _add_rec({
            'titulo': 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)',
            'descricao': 'Dose única, em qualquer época do ano. Rotina a partir de 70 anos, independentemente de fator de risco. Pode ser aplicada junto com as outras vacinas da idade.',
            'subtitulo': 'A partir de 70 anos | Rotina | Dose única | Rede privada',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })
    elif idoso:
        # 60-69 anos: só com fator de risco (SBIm Idoso). Aqui, DPOC e DCV; os demais fatores e a orientação
        # para quem não tem nenhum ficam em src/utils/condicoes.py.
        if has_dpoc or has_cardiopatia_cronica:
            _add_rec({
                'titulo': 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)',
                'descricao': 'Dose única para 60-69 anos com maior risco: cardiopatia, pneumopatia, diabetes, obesidade, nefropatia, hepatopatia, imunossupressão, fragilidade ou institucionalização.',
                'subtitulo': '60-69 anos com fator de risco | Dose única | Rede privada',
                'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
            })
    elif has_dpoc or has_cardiopatia_cronica:
        qual = ' e '.join(x for x, sim in (('DPOC', has_dpoc), ('doença cardiovascular crônica', has_cardiopatia_cronica)) if sim)
        _add_rec({
            'titulo': 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)',
            'descricao': 'Dose única para adultos com doença respiratória ou cardiovascular crônica clinicamente relevante (DPOC, asma moderada/grave, insuficiência cardíaca, coronariopatia, imunodeficiência moderada/grave).',
            'subtitulo': f'Adultos com {qual} | Dose única | Rede privada',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
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
            'descricao': 'Rastreamento de hiperaldosteronismo primário, causa importante de hipertensão resistente. Aldosterona e renina (atividade ou concentração) com potássio sérico, coletados pela manhã, sentado e sem garrote prolongado; corrigir a hipocalemia antes. Pode ser feito em uso da maioria dos anti-hipertensivos; betabloqueador e agonista alfa-2 central podem dar falso-positivo. Interpretar pelos cortes do método do laboratório (imunoensaio ou espectrometria de massa; atividade ou concentração de renina): renina suprimida com aldosterona elevada.',
            'subtitulo': 'Adultos com HAS resistente | Conforme necessidade',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'AHA 2025 / Endocrine Society 2025 (hiperaldosteronismo)',
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

# Fatores de risco da ADA 2026 (seção 2, tabela 2.3) para rastrear diabetes antes dos 35 anos, com IMC ≥ 25.
# Triglicerídeos não são coletados no formulário; sedentarismo só chega por API (atividade_fisica).
def fatores_risco_dm(data, comorbidades, medicacoes, familia, has_hypertension):
    com, med = set(comorbidades), set(medicacoes)
    fatores = []
    if 'diabetes' in familia:
        fatores.append('parente de 1º grau com diabetes')
    if has_hypertension:
        fatores.append('hipertensão')
    if data.get('hdl') and float(data['hdl']) < 35:
        fatores.append('HDL < 35 mg/dL')
    for chave, rotulo in (('sop', 'SOP'), ('diabetes_gestacional_previo', 'diabetes gestacional prévio'),
                          ('dcv_aterosclerotica', 'doença cardiovascular'), ('hiv', 'HIV'), ('masld', 'MASLD')):
        if chave in com:
            fatores.append(rotulo)
    if 'antipsicotico_atipico' in med:
        fatores.append('antipsicótico de 2ª geração')
    if data.get('atividade_fisica') in ('sedentario', 'sedentário'):
        fatores.append('sedentarismo')
    return fatores


def criterio_rastreio_dm(idade, imc, fatores):
    """Grupo do subtítulo do rastreio de diabetes, ou None (ADA 2026, seção 2; USPSTF 2021).

    Automático dos 35 aos 70 anos (a USPSTF vai até 70; a ADA não tem limite: orientação na rota). Em qualquer
    idade adulta, IMC ≥ 25 com ao menos um fator de risco.
    """
    if 35 <= idade <= 70:
        return 'Adultos 35-70 anos'
    if imc is not None and imc >= 25 and fatores:
        return 'IMC ≥25 com fator de risco para diabetes'
    return None


def orientacoes_de_rastreio(idade, sexo, *, gestante, pa_informada, pa_classificacao, pa_alterada, has_hypertension,
                            has_resistant_hypertension, is_diabetic, rastreio_dm, imc, hiv, prep, rastrear_hbv, tabagismo,
                            fatores_osso, drc_a_confirmar=False, dm_a_confirmar=False):
    """Orientações do rastreamento geral, incluídos os avisos de divergência entre diretrizes (só quando a
    conduta divergente vale para este paciente). Cada aviso diz qual diretriz o motor seguiu e qual diverge."""
    o = []

    def orientar(titulo, descricao, referencia):
        o.append({'titulo': titulo, 'descricao': descricao, 'referencia': referencia})

    adulto = idade >= 18
    if not pa_informada and not gestante and adulto:
        orientar('Medir a pressão arterial',
                 'Medir a PA em todo adulto: anualmente a partir dos 40 anos ou com fator de risco (PA 130-139/85-89 mmHg, '
                 'sobrepeso ou obesidade, população negra); a cada 3-5 anos dos 18 aos 39 anos com PA normal e sem fator de '
                 'risco. Confirmar fora do consultório antes de iniciar tratamento.', 'USPSTF 2021 (hipertensão)')
    if pa_alterada:
        orientar('PA alterada: confirmar antes de rotular HAS',
                 'Uma medida de consultório não confirma HAS. Repetir a PA em outra consulta e confirmar com MRPA ou MAPA; '
                 'os exames de lesão de órgão-alvo (potássio, creatinina, EAS, albuminúria, ECG) entram depois da confirmação.',
                 'SBC 2025 / AHA 2025')
        if (pa_classificacao.get('sbc') or {}).get('categoria') == 'pre_hipertensao':
            orientar('Divergência entre diretrizes: classificação da PA',
                     'Com PA de 130-139/80-89 mmHg, nós optamos por seguir a referência da AHA/ACC 2025 (HAS estágio 1, a confirmar com MRPA ou '
                     'MAPA). A SBC 2025 chama essa faixa de pré-hipertensão e só considera HAS a partir de 140/90 mmHg.',
                     'AHA 2025 / SBC 2025')
    if drc_a_confirmar:
        orientar('TFG < 60: confirmar a doença renal crônica',
                 'Uma TFG estimada < 60 isolada não confirma DRC: a cronicidade (3 meses ou mais) tem de ser provada, e um '
                 'resultado único pode ser lesão renal aguda. Rever TFG e albuminúria anteriores; sem elas, repetir '
                 'creatinina/TFG e uACR em 3 meses. Confirmada, marque "Doença renal crônica".', 'KDIGO 2024')
    if dm_a_confirmar:
        orientar('HbA1c ≥ 6,5%: confirmar o diagnóstico de diabetes',
                 'Sem diabetes marcado e sem antidiabético, uma HbA1c ≥ 6,5% isolada não confirma diabetes: sem hiperglicemia '
                 'inequívoca são necessários dois resultados alterados. Repetir a HbA1c ou dosar a glicemia de jejum. Com '
                 'hiperglicemia inequívoca (glicemia ≥ 200 mg/dL com sintomas clássicos ou crise hiperglicêmica), que o '
                 'formulário não registra, marque o diabetes e o tipo.', 'ADA 2026')
    if has_hypertension and not has_resistant_hypertension:
        orientar('Divergência entre diretrizes: ecocardiograma na HAS',
                 'Nós optamos por seguir a referência da AHA/ACC 2025: ecocardiograma só com indicação (ECG com sobrecarga ventricular esquerda, '
                 'suspeita de insuficiência cardíaca, HAS de difícil controle). A SBC 2025 inclui o ecocardiograma na '
                 'avaliação de lesão de órgão-alvo cardíaca.', 'AHA 2025 / SBC 2025')
    if is_diabetic and not has_hypertension:
        orientar('Divergência entre diretrizes: ECG no diabetes',
                 'Sem HAS, não sugerimos ECG ao diabético assintomático (ADA 2026: não rastrear doença coronariana em '
                 'assintomático). A ACCF/AHA 2010 considera razoável um ECG basal (IIa): pedir se o médico optar por ele.',
                 'ADA 2026 (seção 10) / ACCF/AHA 2010')
    if not is_diabetic:
        if rastreio_dm == 'Adultos 35-70 anos' and (imc is None or imc < 25):
            orientar('Divergência entre diretrizes: rastreio de diabetes sem sobrepeso',
                     'Nós optamos por seguir a referência da ADA 2026 (rastreio a partir dos 35 anos, qualquer que seja o peso). A USPSTF 2021 '
                     'restringe o rastreio dos 35 aos 70 anos a quem tem sobrepeso ou obesidade.', 'ADA 2026 / USPSTF 2021')
        elif rastreio_dm is None and idade > 70:
            orientar('Divergência entre diretrizes: rastreio de diabetes depois dos 70 anos',
                     'Acima de 70 anos, só sugerimos rastrear com IMC ≥ 25 e fator de risco (USPSTF 2021: rastreio dos 35 aos 70 '
                     'anos). A ADA 2026 não tem idade de parada: considerar se a expectativa de vida justificar.',
                     'USPSTF 2021 / ADA 2026')
    if not hiv:
        if idade <= 30 and not gestante:
            orientar('Divergência entre diretrizes: frequência do teste de HIV',
                     'Até 30 anos, nós optamos por seguir a referência do PCDT-IST 2022 (teste anual). A USPSTF 2019 pede pelo menos um teste dos 15 '
                     'aos 65 anos e repetição só com risco aumentado.', 'PCDT-IST MS 2022 / USPSTF 2019')
        elif idade > 65:
            orientar('HIV depois dos 65 anos',
                     'Sem teste anterior, oferecer o anti-HIV se houver risco (parcerias novas, IST). A USPSTF 2019 recomenda '
                     'o rastreio universal até os 65 anos.', 'USPSTF 2019')
        if not gestante and not prep and adulto:
            orientar('Sífilis: testar com risco aumentado',
                     'Oferecer teste para sífilis (treponêmico ou VDRL) junto do HIV a quem tem risco aumentado: populações-chave '
                     '(HSH, pessoas trans, profissionais do sexo), IST atual ou prévia, parcerias múltiplas, sexo sem '
                     'preservativo, uso de PrEP. A periodicidade por grupo está no Quadro 5 do PCDT-IST 2022.',
                     'PCDT-IST MS 2022 / USPSTF 2022')
    if idade >= 80:
        orientar('Divergência entre diretrizes: anti-HCV depois dos 79 anos',
                 'Nós optamos por seguir a referência do MS 2026 (PCDT Hepatite C), sem idade limite para o teste único. A USPSTF 2020 recomenda '
                 'rastrear hepatite C dos 18 aos 79 anos.', 'MS 2026 (PCDT Hepatite C) / USPSTF 2020')
    if rastrear_hbv and adulto:
        orientar('Divergência entre diretrizes: rastreio de hepatite B',
                 'Nós optamos por seguir a referência do CDC 2023 e do MS (painel uma vez em adulto sem vacinação documentada). A USPSTF 2020 '
                 'recomenda rastrear só quem tem risco aumentado (B).', 'CDC 2023 (hepatite B) / USPSTF 2020')
    if sexo == 'masculino' and 65 <= idade <= 75 and tabagismo == 'nunca':
        orientar('Aneurisma de aorta: homem que nunca fumou',
                 'Ultrassonografia de aorta como oferta seletiva (USPSTF C): decidir com o paciente, considerando história '
                 'familiar de aneurisma, outros aneurismas, DPOC ou doença cardiovascular.', 'USPSTF 2019')
    if sexo == 'masculino' and idade >= 70:
        orientar('Divergência entre diretrizes: densitometria no homem',
                 'Não sugerimos densitometria ao homem sem fator de risco (USPSTF 2025: evidência insuficiente). A BHOF '
                 '2022 recomenda a partir dos 70 anos, e dos 50 aos 69 com fator de risco: decisão compartilhada.',
                 'USPSTF 2025 / BHOF 2022')
    if sexo == 'feminino' and 50 <= idade < 65 and not fatores_osso and not gestante:
        orientar('Densitometria antes dos 65 anos',
                 'Na pós-menopausa, calcular o FRAX (Brasil) se houver fator de risco para fratura (fratura prévia por '
                 'fragilidade, corticoide, tabagismo, baixo peso, álcool em excesso, artrite reumatoide, fratura de quadril '
                 'em pai ou mãe) e pedir densitometria se o risco estiver elevado.', 'USPSTF 2025 / BHOF 2022')
    return o


def _titulo_normalizado(titulo):
    """Título sem material biológico, parênteses e pontuação (chave antiga, para itens sem código TUSS)."""
    t = re.sub(r',\s*(soro|plasma|sangue.*|urina)', '', titulo, flags=re.IGNORECASE)
    t = re.sub(r'\s*\([^)]*\)', '', t)
    t = re.sub(r'[^a-z0-9\s]', '', t.lower())
    return ' '.join(t.split())


def _identidade_do_exame(rec, sexo):
    """Conjunto que identifica o exame: os códigos TUSS (src/utils/tuss.py) para laboratório e imagem; os itens sem
    código que são o mesmo exame (tuss.MESMO_EXAME_SEM_CODIGO); ou o título normalizado."""
    from src.utils import periodicidade, tuss
    titulo = (rec.get('titulo') or '').strip()
    if rec.get('categoria') in ('laboratorio', 'imagem'):
        partes = tuss.MESMO_EXAME_SEM_CODIGO.get(titulo)
        if partes:
            return frozenset(partes)
        chaves = periodicidade.chaves(titulo, sexo)
        # Código que serve a vários exames (cultura de escarro e de estreptococo do grupo B): cada título é um exame
        if not any(c.startswith('nome:') for c in chaves) and not chaves & tuss.CODIGOS_DE_VARIOS_EXAMES:
            return chaves
    return frozenset({'titulo:' + (rec.get('categoria') or '') + ':' + _titulo_normalizado(titulo)})


def deduplicar_recomendacoes(recomendacoes, sexo=None):
    """Um item por exame. Une as recomendações do mesmo exame com títulos diferentes ("Hemograma completo com
    plaquetas" e "Hemograma completo, sangue total"; "Razão albumina/creatinina" e "uACR") e absorve o exame
    pedido sozinho no exame combinado que já o contém ("Potássio, soro" em "Sódio e potássio, soro"; "Antígeno
    HBs" no painel de hepatite B). O item que fica soma prioridade, motivos (subtítulos), referências e descrições.
    """
    from src.utils import tuss
    grupos = []  # [identidade, [recs]] na ordem de chegada
    for rec in recomendacoes:
        if not (rec.get('titulo') or '').strip():
            continue
        chave = _identidade_do_exame(rec, sexo)
        for grupo in grupos:
            if grupo[0] == chave:
                grupo[1].append(rec)
                break
        else:
            grupos.append([chave, [rec]])
    # Exame contido em um combinado (só para códigos: as chaves de título não se combinam)
    maiores = sorted(grupos, key=lambda g: len(g[0]), reverse=True)
    absorvidos = set()
    for i, grupo in enumerate(maiores):
        if id(grupo) in absorvidos or any(c.startswith('titulo:') for c in grupo[0]):
            continue
        for outro in maiores[i + 1:]:
            if id(outro) not in absorvidos and len(outro[0]) < len(grupo[0]) and outro[0] < grupo[0]:
                grupo[1].extend(outro[1])
                absorvidos.add(id(outro))
    unicos = []
    for grupo in grupos:
        if id(grupo) in absorvidos:
            continue
        chave, recs = grupo
        if len(recs) == 1:
            unicos.append(recs[0])
            continue
        unicos.append(_unir(recs, chave, tuss.TITULO_PREFERIDO.get(chave), sexo))
    return unicos


def _unir(recs, chave, preferido, sexo):
    """Uma recomendação a partir de várias do mesmo exame."""
    from src.utils.condicoes import ORDEM_PRIORIDADE
    # O título que fica: o exame combinado (o que tem a identidade inteira); entre sinônimos, o do pré-natal
    # (a gestação tem regras próprias), depois o título preferido do catálogo e, por fim, o mais completo.
    completos = [r for r in recs if _identidade_do_exame(r, sexo) == chave]
    def ordem(r):
        # Entre itens do mesmo título, o motivo de grupo de risco (PrEP, medicação, doença) vem antes do rastreio
        # populacional ("Adultos ..."), que passa a "Também: ...".
        return (not r.get('gestacao'), (r.get('titulo') or '').strip() != preferido, -len(r.get('titulo') or ''),
                condicoes.eh_rastreio_populacional(r.get('subtitulo')))
    base = min(completos or recs, key=ordem)
    melhor = dict(base)
    outros = [r for r in recs if r is not base]
    for r in outros:
        if ORDEM_PRIORIDADE.get(r.get('prioridade'), 0) > ORDEM_PRIORIDADE.get(melhor.get('prioridade'), 0):
            melhor['prioridade'] = r['prioridade']
    refs = []
    for r in [base] + outros:
        for ref in (r.get('referencia') or '').split(' | '):
            if ref and ref not in refs:
                refs.append(ref)
    if refs:
        melhor['referencia'] = ' | '.join(refs)
    # Links clicáveis de cada fonte (montados por regra: a referência unida não se separa de novo)
    links = []
    for r in [base] + outros:
        for link in r.get('referencias') or build_reference_links(r.get('titulo', ''), r.get('referencia', '')):
            if link['label'] not in [x['label'] for x in links]:
                links.append(link)
    if links:
        melhor['referencias'] = links
        melhor['referencia_html'] = build_reference_html(links)
    # Todos os motivos ficam visíveis ("Também: ...") e contam na periodicidade (campo interno `_subtitulos`,
    # retirado antes de responder; src/utils/periodicidade.py usa o menor intervalo).
    subtitulo = base.get('subtitulo') or ''
    unidos = list(base.get('_subtitulos') or [])
    # O motivo de grupo de risco (PrEP, medicação, doença) abre o subtítulo; o rastreio populacional ("Adultos ...")
    # passa a "Também: ...". O título que fica continua sendo o do exame combinado.
    risco = next((r for r in outros if r.get('subtitulo') and not condicoes.eh_rastreio_populacional(r['subtitulo'])), None)
    if condicoes.eh_rastreio_populacional(subtitulo) and risco is not None:
        outros = [r for r in outros if r is not risco] + [base]
        subtitulo = risco['subtitulo']
        unidos = list(risco.get('_subtitulos') or [])
    for r in outros:
        outro = r.get('subtitulo') or ''
        unidos += [outro] + list(r.get('_subtitulos') or [])
        if outro and outro not in subtitulo:
            subtitulo = f'{subtitulo} | Também: {outro}'.strip(' |')
    melhor['subtitulo'] = subtitulo
    melhor['_subtitulos'] = unidos
    descricoes = list(dict.fromkeys(r.get('descricao') for r in [base] + outros if r.get('descricao')))
    if len(descricoes) > 1:
        melhor['descricao'] = ' '.join(descricoes[:2])  # Limitar a 2 descrições
    return melhor


def _lista_curta(valor):
    """Lista de textos curtos vinda do navegador (ou vazia)."""
    if not isinstance(valor, list):
        return set()
    return {v for v in valor[:30] if isinstance(v, str) and len(v) <= 40}


def calcular_risco_cardiovascular(data, comorbidades, medicacoes, is_diabetic, is_pregnant, agravantes=()):
    """PREVENT em 10/30 anos com as categorias SBC 2025 e ACC/AHA 2026, ou o motivo de não calcular."""
    if is_pregnant:
        return {'status': 'nao_aplicavel', 'motivo': 'PREVENT não é validado na gestação.'}
    if {'dcv_aterosclerotica', 'cardiopatia'} & set(comorbidades):
        return {'status': 'nao_aplicavel',
                'motivo': 'DCV aterosclerótica estabelecida: prevenção secundária, sem cálculo de PREVENT. '
                          'SBC 2025: risco muito alto (meta LDL < 50 mg/dL; extremo se eventos múltiplos ou '
                          'evento + 2 condições de alto risco: < 40 mg/dL).'}
    if 'insuficiencia_cardiaca' in comorbidades:
        return {'status': 'nao_aplicavel',
                'motivo': 'Insuficiência cardíaca estabelecida: o PREVENT só se aplica a quem não tem DCV conhecida.'}
    idade, sexo = data['idade'], data['sexo']
    faltando = [rotulo for chave, rotulo in (('colesterol', 'colesterol total'), ('hdl', 'HDL'),
                                              ('pas', 'pressão sistólica'), ('peso', 'peso'),
                                              ('altura', 'altura'), ('creatinina', 'creatinina'))
                if not data.get(chave)]
    if not 30 <= idade <= 79:
        return {'status': 'nao_aplicavel', 'motivo': 'PREVENT vale de 30 a 79 anos.'}
    if faltando:
        return {'status': 'incompleto', 'faltando': faltando,
                'motivo': 'Para calcular o PREVENT faltam: ' + ', '.join(faltando) + '.'}
    egfr = prevent.egfr_ckd_epi_2021(float(data['creatinina']), idade, sexo)
    imc_valor = round(prevent.imc(float(data['peso']), float(data['altura'])), 1)
    hba1c = float(data['hba1c']) if data.get('hba1c') else None
    uacr = float(data['uacr']) if data.get('uacr') else None
    try:
        r = prevent.estimar(
            idade=idade, sexo=sexo, colesterol_total=float(data['colesterol']), hdl=float(data['hdl']),
            pas=float(data['pas']), diabetes=is_diabetic, fumante=data.get('tabagismo') == 'atual',
            imc_valor=imc_valor, egfr=egfr, anti_hipertensivo='anti_hipertensivos' in medicacoes,
            estatina='estatinas' in medicacoes, hba1c=hba1c, uacr=uacr)
    except prevent.EntradaForaDaFaixa as exc:
        return {'status': 'fora_da_faixa', 'problemas': exc.problemas,
                'motivo': 'Valores fora da faixa em que o PREVENT foi derivado: ' + '; '.join(exc.problemas) + '.'}
    dcva = r['dez_anos']['dcva']
    return {
        'status': 'calculado',
        'modelo': r['modelo'],
        'egfr': egfr,
        'imc': imc_valor,
        'dez_anos': r['dez_anos'],
        'trinta_anos': r['trinta_anos'],
        'categoria_sbc_2025': prevent.categoria_sbc_2025(dcva, is_diabetic, idade, sexo, agravantes=agravantes),
        'categoria_acc_aha_2026': prevent.categoria_acc_aha_2026(dcva),
        'observacao': 'Categoria SBC pelo escore, pela idade no DM2 e pelos agravantes informados (história familiar '
                      'de DCV prematura, obesidade, MASLD, doença inflamatória crônica, HIV). Lp(a), PCR-us, fatores '
                      'femininos, estratificadores do DM2, LDL ≥ 190 e CAC também reclassificam e ficam a cargo do médico.',
        'limitacao': PREVENT_LIMITACAO,
    }


# Limite de aplicabilidade: o PREVENT foi derivado e validado em população dos EUA. A validação externa no NHANES
# mostrou boa discriminação (C 0,89) e calibração só moderadamente imperfeita; não há validação em coorte
# brasileira, e no Brasil os escores de risco concordam pouco entre si.
PREVENT_LIMITACAO = {
    'texto': 'Equações derivadas e validadas em população dos EUA, sem validação em coorte brasileira: use o '
             'resultado como estimativa. No Brasil, os escores de risco cardiovascular concordam pouco entre si.',
    'fontes': [
        {'rotulo': 'Validação externa (JAMA Netw Open 2024)',
         'link': 'https://doi.org/10.1001/jamanetworkopen.2024.38311'},
        {'rotulo': 'Escores no Brasil (Arq Bras Cardiol 2025)', 'link': 'https://doi.org/10.36660/abc.20240405'},
    ],
}


@checkup_intelligent_bp.route('/checkup-intelligent', methods=['POST'])
def generate_intelligent_recommendations():
    resposta, status = recomendar(request.get_json(silent=True), registrar_uso=True)
    try:
        return jsonify(resposta), status
    except Exception as e:                      # falha ao serializar: a mesma resposta de erro do motor
        print(f"Erro na geração de recomendações: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500


# Subtópicos das orientações na tela. A ordem é a de exibição.
GRUPOS_DE_ORIENTACAO = (
    ('divergencia', 'Divergências entre diretrizes'),
    ('indicado', 'Outros rastreios e intervenções indicados'),
    ('nao_rotina', 'Não indicado de rotina ou decisão individual'),
)
_NAO_ROTINA = re.compile(r'não recomendado|sem rastreio|decisão individual|nunca fumou|antes dos 65|depois dos 65|'
                         r'só com fator|a critério|quando encerrar', re.IGNORECASE)


def grupo_da_orientacao(orientacao):
    """Subtópico da orientação, pelo título: divergência entre diretrizes; o que não é indicado de rotina (idade
    de encerrar, decisão individual, oferta seletiva); e as demais, que são rastreios e intervenções indicados."""
    titulo = orientacao.get('titulo') or ''
    if re.search(r'diverg', titulo, re.IGNORECASE):
        return 'divergencia'
    return 'nao_rotina' if _NAO_ROTINA.search(titulo) else 'indicado'


def recomendar(bruto, registrar_uso=False):
    """O motor do check-up, sem depender do servidor: recebe o JSON do formulário e devolve (resposta, status).

    A rota acima só entrega o resultado; o modo sombra das operadoras (src/utils/operadora.py) chama esta função
    direto, sem registrar uso."""
    try:
        # Validar e normalizar a entrada. Nada é presumido: idade, sexo e tabagismo são
        # obrigatórios, valores impossíveis são recusados e dado ausente não vira valor padrão.
        try:
            data, triagem = validar_entrada(bruto)
        except EntradaInvalida as exc:
            return {
                'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                'codigo': 'entrada_invalida',
                'erros': exc.erros,
            }, 400

        # Exames que o paciente já fez (opcional): o que estiver em dia não é pedido de novo.
        from src.utils import periodicidade
        exames_anteriores, erros_exames = periodicidade.ler_exames_anteriores(
            (bruto or {}).get('exames_anteriores'))
        if erros_exames:
            return {
                'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in erros_exames),
                'codigo': 'entrada_invalida',
                'erros': erros_exames,
            }, 400

        # Dados do paciente (já normalizados)
        age = data['idade']
        sex = data['sexo']
        is_pregnant = triagem['gestante'] == SIM
        gestacao = None
        if is_pregnant:
            try:
                gestacao = prenatal.normalizar(bruto or {})
            except prenatal.GestacaoInvalida as exc:
                return {
                    'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                    'codigo': 'entrada_invalida',
                    'erros': exc.erros,
                }, 400
        weight = data.get('peso')
        height = data.get('altura')
        sbp_value = data.get('pas') or 0
        dbp_value = data.get('pad') or 0

        # Risco cardiovascular: src/utils/prevent.py (implementação única, validada nos
        # testes contra os vetores do preventr). Calculado no fim, em calcular_risco_cardiovascular.
        
        # Detectar hipertensão automaticamente
        has_hypertension = False
        has_resistant_hypertension = False
        
        # 1. PA de consultório: classificada pela AHA/ACC 2025 (e pela SBC 2025, em ``sbc``) em
        # src/utils/coerencia.py. Uma PA isolada não rotula HAS: fora da gestação só PA ≥ 180/110 marca a
        # caixa; PA ≥ 130/80 sem HAS conhecida pede só MRPA ou MAPA (coerencia.pa_a_confirmar).
        sbp = float(sbp_value) if sbp_value else 0
        dbp = float(dbp_value) if dbp_value else 0

        # 2. Detecção por checkboxes clínicos
        comorbidades = data.get('comorbidades', [])
        # Garantir que comorbidades é uma lista
        if isinstance(comorbidades, str):
            comorbidades = [comorbidades]
        elif isinstance(comorbidades, dict):
            # Se for objeto, extrair chaves onde valor é True
            comorbidades = [k for k, v in comorbidades.items() if v]
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

        # Coerência entre campos: estatina → dislipidemia, anti-hipertensivo → HAS,
        # HbA1c ≥ 6,5 → diabetes, IMC ≥ 30 → obesidade, TFG < 60 → DRC (src/utils/coerencia.py).
        egfr_inferencia = None
        if data.get('creatinina'):
            egfr_inferencia = prevent.egfr_ckd_epi_2021(float(data['creatinina']), data['idade'], data['sexo'])
        # Princípios ativos escolhidos na tela viram as classes com que o motor trabalha
        from src.utils import doses, medicamentos
        escolhidas = list(medicacoes_checkboxes)
        try:
            detalhes_doses = doses.ler(bruto or {}, escolhidas)
        except doses.DetalheInvalido as exc:
            return {'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                            'codigo': 'entrada_invalida', 'erros': exc.erros}, 400
        # Dose e duração (corticoide, metotrexato, azatioprina, hidroxicloroquina, bisfosfonato) ajustam as
        # classes: a exclusão vale só para o medicamento avaliado, não para outro que traga a mesma classe.
        mais, excluir_por_medicamento, orientacoes_doses = doses.avaliar(
            escolhidas, detalhes_doses, peso=data.get('peso'),
            rotulos={k: medicamentos.MEDICAMENTOS[k]['rotulo'] for k in escolhidas if k in medicamentos.MEDICAMENTOS})
        medicacoes_checkboxes = medicamentos.classes_de(escolhidas, excluir_por_medicamento)
        medicacoes_checkboxes += [c for c in sorted(mais) if c not in medicacoes_checkboxes]
        comorbidades, medicacoes_checkboxes, inferencias = coerencia.inferir(
            {**data, 'comorbidades': comorbidades, 'medicacoes': medicacoes_checkboxes}, egfr=egfr_inferencia,
            gestante=is_pregnant, recusados=_lista_curta((bruto or {}).get('inferencias_recusadas')),
            escolhidas=escolhidas)
        familia = data.get('historia_familiar') or []
        familia = [k for k, v in familia.items() if v] if isinstance(familia, dict) else list(familia)
        # Itens que implicam imunossupressão valem como "Sim" na triagem de vacinas.
        if condicoes.imunossupressao_implicada(comorbidades, medicacoes_checkboxes):
            triagem['imunossupressao'] = SIM
        # Na gestação, ≥ 140/90 e faixa grave ≥ 160/110, sem os estágios da AHA/ACC (src/utils/prenatal.py).
        pa_classificacao = (prenatal.classificar_pa(data.get('pas'), data.get('pad')) if is_pregnant
                            else coerencia.classificar_pa(data.get('pas'), data.get('pad')))
        
        # Verificar se tem hipertensão nas comorbidades
        if 'hipertensao' in comorbidades or 'hipertensão' in comorbidades:
            has_hypertension = True
        
        # Verificar se tem hipertensão resistente
        if 'hipertensao_resistente' in comorbidades or 'has_resistente' in comorbidades:
            has_hypertension = True
            has_resistant_hypertension = True
        
        # Doença cardiovascular estabelecida. "Cardiopatia" genérica saiu do formulário por não
        # corresponder a nenhuma diretriz; valor antigo é tratado como DCV aterosclerótica.
        has_dcv_aterosclerotica = bool({'dcv_aterosclerotica', 'cardiopatia'} & set(comorbidades))
        has_ic = 'insuficiencia_cardiaca' in comorbidades
        
        # Verificar se marcou checkbox de anti-hipertensivos
        if 'anti_hipertensivos' in medicacoes_checkboxes:
            has_hypertension = True
        
        # Extrair dados de tabagismo e DPOC
        tabagismo = data['tabagismo']
        macos_ano = float(data.get('macos_ano', 0)) if data.get('macos_ano') else 0
        has_dpoc = 'dpoc' in comorbidades
        
        # Gerar recomendações
        recommendations = []

        # Rastreamento geral (relatório de auditoria A): PA alterada sem HAS, critério de rastreio de diabetes,
        # risco de DRC, hepatite B, PrEP e fatores de risco para fratura.
        imc = None
        if weight and height:
            imc = weight / ((height / 100) ** 2)
        ja_diabetico = bool(set(condicoes.TIPOS_DE_DIABETES) & set(comorbidades)) or 'insulina' in medicacoes_checkboxes
        pa_alterada = coerencia.pa_a_confirmar(pa_classificacao, comorbidades, gestante=is_pregnant)
        # Exame isolado não confirma doença: TFG < 60 (KDIGO 2024) e HbA1c ≥ 6,5% (ADA 2026) pedem confirmação.
        drc_a_confirmar = coerencia.drc_a_confirmar(egfr_inferencia, comorbidades)
        dm_a_confirmar = coerencia.diabetes_a_confirmar(data.get('hba1c'), comorbidades, medicacoes_checkboxes)
        rastreio_dm = None if (ja_diabetico or dm_a_confirmar) else criterio_rastreio_dm(
            age, imc, fatores_risco_dm(data, comorbidades, medicacoes_checkboxes, familia, has_hypertension))
        risco_drc = has_hypertension or has_dcv_aterosclerotica or has_ic or 'rim_policistico' in familia
        prep = 'hiv' not in comorbidades and bool({'tenofovir_entricitabina', 'cabotegravir'} & set(escolhidas))
        alcool = (bruto or {}).get('alcoolismo')
        fatores_osso = (tabagismo == 'atual' or (imc is not None and imc < 20) or alcool == 'pesado'
                        or 'artrite_reumatoide' in comorbidades)

        # Recomendações baseadas em idade, sexo e status de hipertensão
        age_sex_recs = generate_age_sex_recommendations(age, sex, country='BR', 
                                                         has_hypertension=has_hypertension,
                                                         has_resistant_hypertension=has_resistant_hypertension,
                                                         is_pregnant=is_pregnant,
                                                         tabagismo=tabagismo,
                                                         macos_ano=macos_ano,
                                                         has_dpoc=has_dpoc,
                                                         has_cardiopatia_cronica=has_dcv_aterosclerotica or has_ic,
                                                         pa_alterada=pa_alterada, rastreio_dm=rastreio_dm,
                                                         risco_drc=risco_drc, prep=prep, fatores_osso=fatores_osso,
                                                         confirmar_drc=drc_a_confirmar, confirmar_dm=dm_a_confirmar,
                                                         rastrear_hbv=not is_pregnant and 'hepatite_b_cronica' not in comorbidades)
        recommendations.extend(age_sex_recs)

        # Colo do útero: teste de DNA-HPV e colposcopia (MS 2025, SBOC 2026, ACOG 2026).
        orientacoes_colo = []
        if sex == 'feminino':
            recs_colo, orientacoes_colo = colo_utero.recomendar(
                age, imunossuprimida='hiv' in comorbidades or triagem.get('imunossupressao') == SIM,
                resultado=data.get('hpv_resultado'), histerectomizada=colo_utero.HISTERECTOMIA in comorbidades,
                rastreio_adequado=data.get('colo_rastreio_adequado'), nic2_previa=data.get('colo_nic2_previa') == SIM)
            recommendations.extend(recs_colo)

        # Clamídia e gonococo em mulheres sexualmente ativas até 24 anos (USPSTF 2021, B). Na gestante, o pré-natal pede.
        orientacoes_ist = []
        if sex == 'feminino' and not is_pregnant:
            recs_ist, orientacoes_ist = prenatal.clamidia_fora_da_gestacao(age, data.get('sexualmente_ativa'))
            recommendations.extend(recs_ist)
        
        # Rastreamento de câncer de pulmão (LDCT): USPSTF 2021 / SBCT-SBPT-CBR 2024 (src/utils/rastreio_cancer.py).
        # Maços-ano ou anos desde que parou ausentes não viram zero: o item aparece como dados insuficientes.
        recs_pulmao, nao_incluidas_cancer, orientacoes_cancer = rastreio_cancer.pulmao(
            age, tabagismo, data.get('macos_ano'), data.get('anos_parou_fumar'), gestante=is_pregnant)
        recommendations.extend(recs_pulmao)
        
        # ========== DIABETES SCREENING E MANAGEMENT (ADA 2024) ==========
        
        # Verificar se já é diabético
        # Qualquer tipo de diabetes (ADA 2026); insulina em uso indica diabetes mesmo sem o tipo marcado.
        is_diabetic = bool(set(condicoes.TIPOS_DE_DIABETES) & set(comorbidades)) or 'insulina' in medicacoes_checkboxes
        
        # HbA1c ≥ 6,5% sem diabetes marcado e sem antidiabético não faz do paciente um diabético: o motor pede a
        # confirmação (ADA 2026, seção 2; ver coerencia.diabetes_a_confirmar). Campo mantido por compatibilidade.
        diabetes_por_hba1c = False

        # TOTG só com indicação: glicemia ou HbA1c limítrofes (pré-diabetes marcado ou HbA1c de 5,7 a 6,4%),
        # para confirmar o diagnóstico. Não entra no check-up de rotina e nunca em quem já tem diabetes
        # (tipo 1, tipo 2, em uso de insulina ou antidiabético). O TOTG da gestação é o do pré-natal.
        if is_diabetic or dm_a_confirmar or 'pre_diabetes' not in comorbidades:
            recommendations = [r for r in recommendations if not (r.get('titulo') or '').startswith('TOTG-75g')]
        if is_diabetic:
            # Quem já tem diabetes não faz rastreamento: glicemia e HbA1c passam a ser acompanhamento do controle.
            controle = {
                'Hemoglobina glicada (HbA1c), soro': {
                    'descricao': 'Controle glicêmico no diabetes: pelo menos 2 vezes ao ano em quem está na meta e a cada '
                                 '3 meses após mudança de tratamento ou fora da meta.',
                    'subtitulo': 'Diabéticos | A cada 3-6 meses', 'referencia': 'ADA 2026 (seção 6)', 'grau_evidencia': 'A'},
                'Glicose, soro': {
                    'descricao': 'Glicemia de jejum no acompanhamento do diabetes, junto da HbA1c.',
                    'subtitulo': 'Diabéticos | Junto da HbA1c', 'referencia': 'ADA 2026 (seção 6)', 'grau_evidencia': 'B'},
            }
            for titulo, campos in controle.items():
                rec = next((r for r in recommendations if r.get('titulo') == titulo), None)
                if rec is None:
                    rec = {'titulo': titulo, 'categoria': 'laboratorio', 'prioridade': 'alta'}
                    recommendations.append(rec)
                rec.update(campos)
                rec.pop('_subtitulos', None)

        # EXAMES PARA DIABÉTICOS (ADA 2024 - Laboratory Evaluation)
        if is_diabetic:
            # TGO e TGP: rastreio de fibrose pelo FIB-4 (DM2/pré-diabetes; DM1 só com obesidade ou MASLD), em
            # src/utils/condicoes.py (relatório D, D-22).

            # Relação albumina/creatinina urinária (microalbuminúria)
            recommendations.append({
                'titulo': 'Relação albumina/creatinina urinária (uACR)',
                'descricao': 'Rastreamento de nefropatia diabética. Valores ≥30 mg/g indicam albuminúria e risco aumentado de doença renal. Realizar anualmente.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2026 (seção 11)',
                'grau_evidencia': 'A'
            })
            
            # Creatinina sérica e eGFR (soma o motivo ao item que já existe)
            condicoes._garantir(recommendations, condicoes._rec(
                'Creatinina, soro', 'laboratorio',
                'Avaliação da função renal em pacientes diabéticos (TFG estimada com a uACR). Realizar anualmente para '
                'detecção precoce de doença renal diabética.', 'Diabéticos | Anual', 'ADA 2026 (seção 4)', 'A', 'alta'))

            # TSH: só no diabetes tipo 1 (doença tireoidiana autoimune associada); não é rotina nos outros tipos.
            if 'diabetes_tipo_1' in comorbidades:
                recommendations.append({
                    'titulo': 'Hormônio Tireoestimulante (TSH), soro',
                    'descricao': 'Diabetes tipo 1: rastrear doença tireoidiana autoimune na avaliação inicial e periodicamente.',
                    'subtitulo': 'Diabetes tipo 1 | A cada 1-2 anos',
                    'categoria': 'laboratorio',
                    'prioridade': 'media',
                    'referencia': 'ADA 2026 (seção 4)',
                    'grau_evidencia': 'E'
                })
            
            # Vitamina B12 com metformina e potássio com IECA/BRA/diurético: src/utils/condicoes.py (fonte única).
            # Cálcio, vitamina D e fósforo: só com indicação (DRC G3a+, osteoporose, bariátrica, doença celíaca), pelos
            # próprios módulos; a ADA os lista "conforme apropriado" e a Endocrine Society 2024 é contra a 25(OH)D de
            # rotina (relatório D, D-09 e D-10; relatório A, M-08).

            # Hemograma completo (ADA 2026, seção 4, Tabela 4.1): plaquetas para o FIB-4 e anemia (DRC, metformina)
            recommendations.append({
                'titulo': 'Hemograma completo com plaquetas',
                'descricao': 'Diabetes: hemograma com plaquetas na avaliação anual (plaquetas para o FIB-4; anemia da doença renal e por deficiência de B12 com metformina).',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': 'ADA 2026 (seção 4)',
                'grau_evidencia': 'E'
            })

            # EXAMES DE IMAGEM PARA DIABÉTICOS
            
            # Fundoscopia (exame oftalmológico)
            recommendations.append({
                'titulo': 'Fundoscopia (Exame de fundo de olho)',
                'descricao': 'Rastreamento de retinopatia diabética com exame de fundo de olho sob dilatação: anual; a cada 1-2 anos se não houver retinopatia em um ou mais exames e a glicemia estiver controlada. No tipo 1, o primeiro exame em até 5 anos do diagnóstico; no tipo 2, no diagnóstico.',
                'subtitulo': 'Diabéticos | A cada 1-2 anos',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'ADA 2026 (seção 12)',
                'grau_evidencia': 'A'
            })
            
            # ECG: a ADA não recomenda rastrear doença coronariana no diabético assintomático; a ACCF/AHA 2010 acha
            # razoável um ECG basal (IIa). Não entra sozinho: orientação de divergência (orientacoes_rastreio).

        # ========== HIV: src/utils/hiv.py (MS 2024 PCDT HIV / HIVMA/IDSA 2024) ==========
        is_hiv_positive = 'hiv' in comorbidades
        orientacoes_hiv = []
        if is_hiv_positive:
            hiv_data = data.get('hiv_data') or {}
            # Tenofovir pela classe do princípio ativo escolhido (src/utils/medicamentos.py); antes se procurava a palavra
            # "tenofovir" entre as classes, e a regra nunca disparava (relatório D, D-06).
            usa_tenofovir = 'tenofovir' in medicacoes_checkboxes or 'tenofovir' in medicacoes_continuo
            recs_hiv, orientacoes_hiv = hiv.recomendar(
                age, sex, cd4=hiv_data.get('cd4') or data.get('cd4'),
                carga_viral=hiv_data.get('carga_viral') or data.get('carga_viral'),
                em_tarv='sim' in (hiv_data.get('em_tarv'), data.get('em_tarv')),
                supressao_viral='sim' in (hiv_data.get('supressao_viral'), data.get('supressao_viral')),
                gestante=is_pregnant, tenofovir=usa_tenofovir,
                risco_renal=is_diabetic or has_hypertension or 'doenca_renal' in comorbidades)
            recommendations.extend(recs_hiv)
            if 'tenofovir_alafenamida' in medicacoes_checkboxes:
                orientacoes_hiv.append({
                    'titulo': 'Tenofovir alafenamida: intervalo da função renal',
                    'descricao': 'Nós optamos por seguir a referência do PCDT do MS para todo tenofovir (creatinina e EAS a cada 3-6 meses). A HIVMA/IDSA '
                                 'aceita intervalos maiores com o tenofovir alafenamida (TAF), menos nefrotóxico que o fumarato (TDF).',
                    'referencia': 'MS 2024 (PCDT HIV) / HIVMA/IDSA 2024'})

        # ========== DPOC (GOLD 2026; relatório D, D-25 e D-38) ==========
        # Graus: o GOLD não gradua a monitorização; "E" é consenso. Sódio, potássio e cloreto saíram (sem base no GOLD;
        # o diurético já os pede em src/utils/condicoes.py).
        is_dpoc = 'dpoc' in comorbidades

        if is_dpoc:
            for rec in (
                    ('Espirometria, com broncodilatador', 'imagem', 'Espirometria pós-broncodilatador para confirmar o diagnóstico e '
                     'acompanhar a evolução, pelo menos uma vez por ano.', 'DPOC | Anual ou conforme sintomas', 'alta', 'E'),
                    ('Alfa-1 antitripsina, soro', 'laboratorio', 'Toda pessoa com DPOC deve dosar a alfa-1 antitripsina uma vez '
                     '(recomendação da OMS adotada pelo GOLD); nível baixo pede genotipagem e rastreio familiar.', 'DPOC | Uma vez', 'alta', 'E'),
                    ('Teste de caminhada de 6 minutos', 'imagem', 'Capacidade funcional e tolerância ao exercício; útil para a '
                     'reabilitação pulmonar e para o prognóstico.', 'DPOC | Anual ou conforme indicação', 'media', 'E'),
                    ('Gasometria arterial, sangue arterial', 'laboratorio', 'Indicada se a saturação de O2 em repouso for ≤ 92% ou na '
                     'DPOC grave, para avaliar hipoxemia e hipercapnia e indicar oxigenoterapia.',
                     'DPOC | Se SpO2 ≤ 92% ou DPOC grave', 'media', 'E'),
                    ('Radiografia de tórax', 'imagem', 'Não confirma a DPOC, mas afasta diagnósticos alternativos e comorbidades '
                     '(bronquiectasias, câncer, insuficiência cardíaca).', 'DPOC | Conforme indicação clínica', 'media', 'E'),
                    ('Hemograma completo com plaquetas', 'laboratorio', 'Eosinófilos no sangue para decidir o corticoide inalatório '
                     '(≥ 300/µL favorece; < 100/µL desfavorece) e anemia ou policitemia, que mudam a dispneia.', 'DPOC | Anual', 'media', 'A')):
                titulo, categoria, descricao, subtitulo, prioridade, grau = rec
                recommendations.append({'titulo': titulo, 'descricao': descricao, 'subtitulo': subtitulo, 'categoria': categoria,
                                        'prioridade': prioridade, 'referencia': 'GOLD 2026', 'grau_evidencia': grau})

        # Nenhum dado do paciente é gravado: a consulta é calculada e descartada.

        # Uso do sistema (painel /analytics): quem gerou o check-up, sem dado do paciente
        if registrar_uso:
            from src.routes.auth import usuario_atual
            from src.utils import uso
            uso.registrar('checkup', usuario_atual())
        
        # Listas de comorbidades, medicações e história familiar (src/utils/condicoes.py)
        orientacoes = condicoes.aplicar(recommendations, age, sex, comorbidades, medicacoes_checkboxes, familia,
                                        gestante=is_pregnant, tabagismo=tabagismo, imc=imc, tfg=egfr_inferencia,
                                        creatinina=data.get('creatinina'), peso=weight, hipertensao=has_hypertension,
                                        imunossuprimido=triagem.get('imunossupressao') == SIM,
                                        cd4=data.get('cd4') if is_hiv_positive else None,
                                        idade_ccr_familiar=data.get('idade_ccr_familiar'),
                                        uacr=float(data['uacr']) if data.get('uacr') else None)
        # Rastreio de câncer: divergências entre diretrizes e o que vale depois da idade de parada.
        mais_orientacoes, mais_nao_incluidas = rastreio_cancer.finalizar(recommendations, age, sex, familia)
        orientacoes_cancer += mais_orientacoes
        nao_incluidas_cancer += mais_nao_incluidas

        # Gestação: rotina do pré-natal pela idade gestacional; itens do check-up geral que
        # não se aplicam na gestação saem da lista e aparecem como "adiados".
        adiados_gestacao, proximas_gestacao, orientacoes_gestacao = [], [], []
        if gestacao is not None:
            if 'diabetes_gestacional_previo' in comorbidades and 'dmg_previo' not in gestacao['condicoes']:
                gestacao['condicoes'].append('dmg_previo')  # mesma informação, marcada na lista de comorbidades
            dados_pn = dict(comorbidades=comorbidades, imc=imc, pas=data.get('pas'), pad=data.get('pad'))
            exames_pn, proximas_gestacao = prenatal.programacao(gestacao, age, hipertensa=has_hypertension,
                                                                diabetica=is_diabetic, hiv='hiv' in comorbidades, **dados_pn)
            titulos_pn = {r['titulo'].lower() for r in exames_pn}
            recommendations = [r for r in recommendations if (r.get('titulo') or '').lower() not in titulos_pn]
            recommendations, fora = prenatal.fora_da_gestacao(recommendations)
            altos_pe, _ = prenatal.fatores_pre_eclampsia(gestacao, age, has_hypertension, is_diabetic, comorbidades, imc)
            com_indicacao = bool(has_hypertension or is_diabetic or 'doenca_renal' in comorbidades or altos_pe
                                 or prenatal.suspeita_de_pre_eclampsia(gestacao, data.get('pas'), data.get('pad')))
            recommendations, adiados_gestacao = prenatal.adiar(recommendations, diabetica=is_diabetic,
                                                               com_indicacao=com_indicacao)
            adiados_gestacao = fora + [a for a in adiados_gestacao if a['titulo'] not in {f['titulo'] for f in fora}]
            recommendations = prenatal.sem_equivalentes(recommendations, exames_pn)
            recommendations = prenatal.ajustar_textos(exames_pn + recommendations, diabetica=is_diabetic)
            orientacoes_gestacao = prenatal.orientacoes(
                gestacao, age, hipertensa=has_hypertension, diabetica=is_diabetic, hiv='hiv' in comorbidades,
                agora=exames_pn, **dados_pn)
        else:
            # Amamentando criança com menos de 6 meses: TOTG pós-DMG e o que esperar do puerpério recente.
            recs_pp, orientacoes_gestacao = prenatal.pos_parto(triagem.get('lactante'), comorbidades,
                                                                  diabetica=is_diabetic)
            recommendations.extend(recs_pp)
            if sex == 'feminino':
                orientacoes_gestacao += prenatal.acido_folico(age, data.get('sexualmente_ativa'),
                                                              histerectomizada=colo_utero.HISTERECTOMIA in comorbidades)

        # Rastreio de HIV não se pede a quem já vive com HIV
        if 'hiv' in comorbidades:
            recommendations = [r for r in recommendations if (r.get('titulo') or '').lower() != 'anti-hiv 1 e 2, soro']

        # Enriquecer recomendações com links (referencia_html). Fica depois das listas e do pré-natal,
        # para que os itens acrescentados por eles também tenham a fonte clicável.
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


        # Preparar outras recomendações (FRAX, calculadoras, etc.)
        outras_recomendacoes = []
        
        # FRAX para HIV+ com ≥40 anos
        if is_hiv_positive and age >= 40:
            outras_recomendacoes.append({
                'titulo': 'FRAX - Calculadora de Risco de Fraturas',
                'descricao': 'Avaliação de risco de fraturas em homens e mulheres com mais de 40 anos. Pessoa vivendo com HIV ou aids tem alto risco de fratura por fragilidade.',
                'subtitulo': 'HIV+ com ≥40 anos | Conforme indicação',
                'tipo': 'calculadora',
                'prioridade': 'media',
                'link': 'https://www.fraxplus.org/pt/calculation-tool',
                'referencia': 'MS 2024 (PCDT HIV)',
                'grau_evidencia': 'B'
            })
        
        # Preparar resposta
        response = {
            'success': True,
            # Mantidos por compatibilidade com clientes antigos; sempre vazios.
            'risco_cardiovascular': calcular_risco_cardiovascular(
                data, comorbidades, medicacoes_checkboxes, is_diabetic, is_pregnant,
                agravantes=condicoes.agravantes_de_risco(comorbidades, familia, hiv='hiv' in comorbidades)),
            'recommendations': recommendations,
            'outras_recomendacoes': outras_recomendacoes,
            'total_recommendations': len(recommendations)
        }
        
        # Deduplicar antes de responder: um pedido por exame, pelo código TUSS (sinônimos e exames combinados)
        # e, sem código, pelo nome (deduplicar_recomendacoes).
        try:
            unique = deduplicar_recomendacoes(recommendations, sex)
            response['recommendations'] = unique
            response['total_recommendations'] = len(unique)
        except Exception as e:
            print(f"Erro na deduplicação: {e}")
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

        # Triagem de segurança das vacinas. É a última etapa de propósito: vale para
        # qualquer regra acima, inclusive as que forem acrescentadas depois.
        contexto_vacinas = {'idade': age, 'hiv': is_hiv_positive, 'cd4': data.get('cd4'), 'classes': medicacoes_checkboxes}
        mantidas, nao_incluidas = aplicar_triagem_vacinas(response['recommendations'], triagem, contexto_vacinas)
        if gestacao is not None:
            mantidas, vacinas_futuras = prenatal.vacinas_fora_da_janela(mantidas, gestacao['ig'])
            proximas_gestacao = sorted(proximas_gestacao + vacinas_futuras, key=lambda x: x['semana'])
        # Periodicidade: exame já feito e ainda dentro do intervalo da própria regra sai do pedido
        # e aparece em "não incluídos", com a data e a data a partir da qual volta a ser indicado.
        mantidas, em_dia = periodicidade.aplicar(mantidas, exames_anteriores, sex)
        nao_incluidas = nao_incluidas + em_dia + nao_incluidas_cancer
        response['recommendations'] = mantidas
        response['total_recommendations'] = len(mantidas)
        response['nao_incluidas'] = nao_incluidas
        response['adiados_gestacao'] = adiados_gestacao
        response['diabetes_por_hba1c'] = diabetes_por_hba1c
        response['diabetes_a_confirmar'] = dm_a_confirmar
        response['drc_a_confirmar'] = drc_a_confirmar
        # Função renal (CKD-EPI 2021, categorias KDIGO e KFRE na DRC marcada): cartão ao lado do PREVENT.
        from src.utils import funcao_renal
        response['funcao_renal'] = funcao_renal.avaliar(data.get('creatinina'), age, sex, data.get('uacr'),
                                                       drc='doenca_renal' in comorbidades)
        response['inferencias'] = inferencias
        orientacoes_rastreio = orientacoes_de_rastreio(
            age, sex, gestante=is_pregnant, pa_informada=bool(sbp or dbp), pa_classificacao=pa_classificacao or {},
            pa_alterada=pa_alterada, has_hypertension=has_hypertension, has_resistant_hypertension=has_resistant_hypertension,
            is_diabetic=is_diabetic, rastreio_dm=rastreio_dm, imc=imc, hiv=is_hiv_positive, prep=prep,
            rastrear_hbv=not is_pregnant and 'hepatite_b_cronica' not in comorbidades, tabagismo=tabagismo,
            fatores_osso=fatores_osso, drc_a_confirmar=drc_a_confirmar, dm_a_confirmar=dm_a_confirmar)
        from src.utils import aconselhamento
        orientacoes_aconselhamento = aconselhamento.orientacoes(
            age, sex, gestante=is_pregnant, lactante=triagem.get('lactante') in ('sim_menor_6m', 'sim_6m_ou_mais'), tabagismo=tabagismo, imc=imc,
            comorbidades=comorbidades, historia_familiar=familia, medicacoes=list(escolhidas) + list(medicacoes_checkboxes), prep=prep,
            alcool=(bruto or {}).get('alcoolismo'))
        todas = (orientacoes_gestacao + orientacoes_doses + orientacoes + orientacoes_colo + orientacoes_ist
                 + orientacoes_hiv + orientacoes_cancer + orientacoes_rastreio + orientacoes_aconselhamento)
        # Urgências (PA em faixa grave na gestação) no topo; depois as da gestação (alto risco, AAS, divergências).
        response['orientacoes'] = [o for o in todas if o.get('urgente')] + [o for o in todas if not o.get('urgente')]
        response['resultados_informados'] = periodicidade.resultados_informados(exames_anteriores)
        aviso_exames = periodicidade.orientacao_dos_nao_reconhecidos(exames_anteriores)
        if aviso_exames:
            response['orientacoes'] = response['orientacoes'] + [aviso_exames]
        # Orientações também levam a fonte clicável e o subtópico em que aparecem na tela.
        for o in response['orientacoes']:
            o['grupo'] = grupo_da_orientacao(o)
            links = build_reference_links(o.get('titulo', ''), o.get('referencia', ''))
            if links:
                o['referencias'] = links
                o['referencia_html'] = build_reference_html(links)
        response['pa_classificacao'] = pa_classificacao
        response['proximas_gestacao'] = proximas_gestacao
        response['gestacao'] = gestacao
        response['triagem_vacinas'] = triagem

        # `_subtitulos` é campo interno da conferência de periodicidade: não sai na resposta.
        for lista in ('recommendations', 'nao_incluidas', 'adiados_gestacao', 'proximas_gestacao'):
            for item in response.get(lista) or []:
                if isinstance(item, dict):
                    item.pop('_subtitulos', None)
        return response, 200
        
    except Exception as e:
        print(f"Erro na geração de recomendações: {e}")
        return {'error': 'Erro interno do servidor'}, 500

# ==================== ENDPOINTS DESATIVADOS ====================
#
# Os endpoints abaixo montavam "Receita Simples" e "Solicitação de Exame" em HTML
# com identificação fixa de médico e a declaração de assinatura digital, sem que
# existisse qualquer assinatura criptográfica (ICP-Brasil). O conteúdo vinha do
# corpo da requisição e não havia autenticação. Foram removidos. As rotas passam
# a responder 410 para deixar explícito que não voltam a existir.
#
# /generate-pdf devolvia "PDF gerado com sucesso" sem gerar nada.
#
# A emissão de documentos fica restrita aos endpoints /gerar-pdf-*, que produzem
# minutas com campo de assinatura e carimbo manuais.

_MENSAGEM_ENDPOINT_DESATIVADO = (
    'Endpoint desativado. O Evidens não emite documentos assinados digitalmente; '
    'use os PDFs de minuta, para impressão, assinatura e carimbo do médico.'
)


def _endpoint_desativado():
    return jsonify({'error': _MENSAGEM_ENDPOINT_DESATIVADO, 'codigo': 'endpoint_desativado'}), 410


for _rota in ('/gerar-receita-vacinas', '/gerar-solicitacao-exames', '/generate-pdf'):
    checkup_intelligent_bp.add_url_rule(
        _rota,
        endpoint='desativado_' + _rota.strip('/').replace('-', '_'),
        view_func=_endpoint_desativado,
        methods=['GET', 'POST'],
    )


# ==================== ENDPOINTS DE GERAÇÃO DE PDFs ====================
#
# Produzem minutas em PDF a partir da lista que o navegador devolve; com sessão de assinatura digital
# aberta e `assinar: true` no pedido, o PDF sai assinado (src/utils/assinatura.py). O pedido é validado e limitado, o conteúdo é escapado nos templates e as
# vacinas passam de novo pela triagem de segurança antes de irem para o papel.

MAX_ITENS_PDF = 80
MAX_TAMANHO_TITULO = 300
MAX_TAMANHO_NOME = 150


class PedidoDePdfInvalido(Exception):
    """O pedido de PDF não pode ser atendido; a mensagem é mostrada ao usuário."""

    def __init__(self, mensagem, codigo='pedido_invalido'):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo


def _ler_pedido_de_pdf(categoria):
    """Valida o corpo do pedido e devolve `(dados_paciente, itens)` da categoria pedida."""
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        raise PedidoDePdfInvalido('Dados não fornecidos')

    dados_paciente = corpo.get('dados_paciente') or {}
    recomendacoes = corpo.get('recomendacoes') or []
    if not isinstance(dados_paciente, dict) or not isinstance(recomendacoes, list):
        raise PedidoDePdfInvalido('Pedido em formato inválido')
    if len(recomendacoes) > MAX_ITENS_PDF:
        raise PedidoDePdfInvalido(f'Lista com mais de {MAX_ITENS_PDF} itens')

    nome = dados_paciente.get('nome')
    if nome is not None and (not isinstance(nome, str) or len(nome) > MAX_TAMANHO_NOME):
        raise PedidoDePdfInvalido('Nome do paciente inválido ou longo demais')

    itens = []
    for rec in recomendacoes:
        if not isinstance(rec, dict):
            raise PedidoDePdfInvalido('Item de recomendação em formato inválido')
        if rec.get('categoria') != categoria:
            continue
        titulo = rec.get('titulo')
        if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > MAX_TAMANHO_TITULO:
            raise PedidoDePdfInvalido('Item de recomendação com título inválido')
        quando = rec.get('quando_pdf')
        if quando is not None and (not isinstance(quando, str) or len(quando) > 160):
            raise PedidoDePdfInvalido('Item de recomendação com janela gestacional inválida')
        if rec.get('esquema_pdf') is not None and rec['esquema_pdf'] not in ESQUEMAS_DE_RISCO:
            raise PedidoDePdfInvalido('Item de recomendação com esquema vacinal inválido')
        itens.append(rec)
    return dados_paciente, itens


MAX_ITENS_LISTA_PDF = 200


def _lista_do_pedido(valor):
    """Lista de chaves (comorbidades ou medicações) dos dados do paciente; texto solto vira lista de um item."""
    if valor is None or valor == '':
        return []
    valor = [valor] if isinstance(valor, str) else valor
    if not isinstance(valor, list) or len(valor) > MAX_ITENS_LISTA_PDF or \
            not all(isinstance(v, str) and 0 < len(v) <= 80 for v in valor):
        raise PedidoDePdfInvalido('Lista de comorbidades ou medicações inválida')
    return [v.strip() for v in valor]


def _conferir_triagem_das_vacinas(dados_paciente, vacinas):
    """Segunda linha de defesa: recusa o PDF se houver vacina que a triagem não libera.

    A triagem é relida dos dados do paciente enviados no pedido (as respostas
    atuais do formulário). Resposta ausente vale como "desconhecido", de modo que
    um pedido sem triagem não consegue imprimir vacinas de vírus vivo atenuado.
    """
    sexo = dados_paciente.get('sexo')
    sexo = sexo.strip().lower() if isinstance(sexo, str) else None
    idade = ler_numero(dados_paciente.get('idade'))
    triagem, _ = normalizar_triagem(dados_paciente, sexo, idade)
    # Comorbidades e medicações (com dose e duração) entram como nas recomendações: o que implica
    # imunossupressão vale como "Sim", e corticoide sem dose ou imunossupressor de baixo grau seguem a triagem.
    comorbidades = _lista_do_pedido(dados_paciente.get('comorbidades'))
    escolhidas = _lista_do_pedido(dados_paciente.get('medicacoes'))
    from src.utils import doses, medicamentos
    try:
        detalhes = doses.ler(dados_paciente, escolhidas)
        peso = ler_numero(dados_paciente.get('peso'))
    except (doses.DetalheInvalido, TypeError, ValueError):
        raise PedidoDePdfInvalido('Dose, duração ou peso inválidos nos dados do paciente')
    mais, excluir, _ = doses.avaliar(escolhidas, detalhes, peso=peso)
    classes = medicamentos.classes_de(escolhidas, excluir)
    classes += [c for c in sorted(mais) if c not in classes]
    if condicoes.imunossupressao_implicada(comorbidades, classes):
        triagem['imunossupressao'] = SIM
    contexto = {
        'idade': idade,
        'hiv': bool(dados_paciente.get('hiv')) or 'hiv' in comorbidades,
        'cd4': ler_numero(dados_paciente.get('cd4')),
        'classes': classes,
    }
    _, bloqueadas = aplicar_triagem_vacinas(vacinas, triagem, contexto)
    if bloqueadas:
        titulos = '; '.join(item['titulo'] for item in bloqueadas)
        raise PedidoDePdfInvalido(
            'A lista contém vacinas que a triagem de segurança não libera para este paciente '
            f'({titulos}). Gere as recomendações novamente.',
            codigo='triagem_vacinas',
        )


from src.utils.pdf_minutas import ESQUEMAS_DE_RISCO  # noqa: E402


def _ler_guia_do_plano(usuario):
    """Dados da guia SP/SADT pedida junto com o PDF, ou None se o médico não pediu guia.

    Corpo: {guia: {credenciamento_id, carteira, indicacao}}. O credenciamento tem de ser do
    próprio usuário (médico ou residente). O número da carteira e a indicação clínica só
    passam por aqui para entrar no PDF: não são gravados.
    """
    corpo = request.get_json(silent=True) or {}
    pedido = corpo.get('guia')
    if pedido is None:
        return None
    from src.utils import contas, pdf_minutas
    if not isinstance(pedido, dict):
        raise PedidoDePdfInvalido('Guia do plano em formato inválido')
    if not contas.pode_ter_credenciamento(usuario):
        raise PedidoDePdfInvalido('A guia do plano de saúde é só para médicos e residentes com plano cadastrado.',
                                  codigo='guia_indisponivel')
    cid = pedido.get('credenciamento_id')
    if isinstance(cid, bool) or not isinstance(cid, int):
        raise PedidoDePdfInvalido('Escolha o plano de saúde da guia.')
    credenciamento = contas.credenciamento_de(usuario['id'], cid)
    if not credenciamento:
        raise PedidoDePdfInvalido('Plano de saúde não encontrado no seu cadastro. Confira em Minha conta.',
                                  codigo='guia_indisponivel')
    carteira = pedido.get('carteira')
    carteira = ' '.join(carteira.split()) if isinstance(carteira, str) else ''
    if len(carteira) > 30:
        raise PedidoDePdfInvalido('Número da carteira longo demais')
    indicacao = pedido.get('indicacao')
    if indicacao is not None and (not isinstance(indicacao, str) or len(indicacao) > 300):
        raise PedidoDePdfInvalido('Indicação clínica inválida ou longa demais')
    return {'credenciamento': credenciamento, 'carteira': carteira,
            'indicacao': pdf_minutas.indicacao_clinica(indicacao)}


# Dados do paciente para o laudo de APAC: só passam por aqui para entrar no PDF; não são gravados.
_CAMPOS_PACIENTE_APAC = {'cns': 20, 'nascimento': 10, 'mae': 120, 'telefone': 20, 'endereco': 150, 'municipio': 60,
                         'ibge': 7, 'uf': 2, 'cep': 9, 'prontuario': 20, 'responsavel': 120, 'raca': 20}


def _ler_apac(usuario, categoria):
    """{'apac': {'vinculo_id', 'paciente': {...}, 'cid'}} do pedido de exames (imagem ou laboratório).

    O laudo sai para cada exame que vai em APAC (src/utils/sigtap.py): os que a regulação pede e os da tabela de
    alta complexidade (PAC), que inclui exames de laboratório."""
    pedido = (request.get_json(silent=True) or {}).get('apac')
    if pedido is None:
        return None
    from src.utils import contas
    if categoria not in ('imagem', 'laboratorio'):
        raise PedidoDePdfInvalido('O laudo de APAC é só para pedidos de exames.')
    if not isinstance(pedido, dict):
        raise PedidoDePdfInvalido('Dados da APAC em formato inválido')
    if not contas.pode_ter_credenciamento(usuario):
        raise PedidoDePdfInvalido('O laudo de APAC é só para médicos e residentes.', codigo='guia_indisponivel')
    vid = pedido.get('vinculo_id')
    if isinstance(vid, bool) or not isinstance(vid, int):
        raise PedidoDePdfInvalido('Escolha o estabelecimento do SUS.')
    vinculo = contas.vinculo_sus_de(usuario['id'], vid)
    if not vinculo:
        raise PedidoDePdfInvalido('Estabelecimento do SUS não encontrado no seu cadastro. Confira em Minha conta.',
                                  codigo='guia_indisponivel')
    bruto = pedido.get('paciente') if isinstance(pedido.get('paciente'), dict) else {}
    paciente = {}
    for campo, maximo in _CAMPOS_PACIENTE_APAC.items():
        valor = bruto.get(campo)
        if valor is None:
            continue
        if not isinstance(valor, str) or len(valor) > maximo + 20:
            raise PedidoDePdfInvalido('Dados do paciente da APAC inválidos ou longos demais')
        paciente[campo] = ' '.join(valor.split())[:maximo]
    if paciente.get('cns') and not contas.cns_valido(paciente['cns']):
        raise PedidoDePdfInvalido('Confira o CNS do paciente: 15 dígitos válidos.')
    if paciente.get('nascimento'):
        try:
            nascimento = datetime.strptime(paciente['nascimento'], '%d/%m/%Y')
        except ValueError:
            nascimento = None
        if not nascimento or not 1900 <= nascimento.year or nascimento > datetime.now():
            raise PedidoDePdfInvalido('Confira a data de nascimento do paciente (dd/mm/aaaa).')
    cid = pedido.get('cid') or ''
    if not isinstance(cid, str) or not re.fullmatch(r'([A-Z]\d{2}(\.?\d)?)?', cid.strip().upper()):
        raise PedidoDePdfInvalido('Confira o CID-10 (ex.: Z12.2).')
    from src.utils import sigtap
    comorbidades = pedido.get('comorbidades') or []
    if not isinstance(comorbidades, list) or len(comorbidades) > 40:
        raise PedidoDePdfInvalido('Comorbidades da APAC inválidas')
    comorbidades = [c for c in comorbidades if isinstance(c, str) and c in sigtap.CID_DA_COMORBIDADE]
    textos = {}
    for campo, maximo in (('anamnese', 600), ('exames', 900)):       # resumo da anamnese e exames já realizados
        valor = pedido.get(campo) or ''
        if not isinstance(valor, str) or len(valor) > maximo + 100:
            raise PedidoDePdfInvalido('Texto do laudo de APAC inválido ou longo demais')
        textos[campo] = ' '.join(valor.split())[:maximo]
    return {'vinculo': vinculo, 'paciente': paciente, 'cid': cid.strip().upper(), 'comorbidades': comorbidades, **textos}


def _ler_justificativa():
    """Justificativa (indicação clínica) do pedido de exames: vai no pedido e na guia. Não é gravada."""
    texto = (request.get_json(silent=True) or {}).get('justificativa')
    if texto is None:
        return ''
    if not isinstance(texto, str) or len(texto) > 300:
        raise PedidoDePdfInvalido('Justificativa inválida ou longa demais')
    return ' '.join(texto.split())[:150]


def _timbrado_do_medico(usuario):
    """{'timbrado': ...} com o receituário do médico (modelo, montado ou papel já timbrado); um receituário
    que não abre não impede o pedido (sai no modelo do Evidēns)."""
    from src.utils import contas, receituario
    if not usuario or not contas.pode_ter_credenciamento(usuario):
        return {}
    try:
        config = receituario.para_o_pdf(contas, usuario['id'])
    except Exception as exc:
        print(f"⚠️ Receituário do médico não abriu ({type(exc).__name__}); pedido no modelo do Evidēns")
        return {}
    return {'timbrado': config} if config else {}


MSG_SEM_SESSAO_DE_ASSINATURA = 'Abra a sessão de assinatura digital para assinar este pedido.'
MSG_SESSAO_DE_ASSINATURA_VENCIDA = 'A sessão de assinatura digital terminou. Abra uma nova para assinar este pedido.'
MSG_ASSINATURA_FALHOU = ('Não foi possível assinar o pedido agora. Tente de novo em instantes '
                         'ou gere o pedido sem assinatura digital.')


def _sessao_para_assinar(usuario):
    """A sessão de assinatura do médico, se o pedido veio com `assinar: true`; None se não pediu assinatura.

    Pedido de assinatura sem sessão aberta é recusado: nunca sai um PDF sem assinatura no lugar do assinado.
    """
    corpo = request.get_json(silent=True) or {}
    if corpo.get('assinar') is not True:
        return None
    from src.routes.auth import _pode_assinar
    from src.utils import contas
    if not _pode_assinar(usuario):
        raise PedidoDePdfInvalido('A assinatura digital não está disponível nesta conta.', codigo='assinatura_indisponivel')
    sessao = contas.sessao_de_assinatura(usuario['id'])
    if not sessao:
        raise PedidoDePdfInvalido(MSG_SEM_SESSAO_DE_ASSINATURA, codigo='assinatura_sem_sessao')
    return sessao


def _assinar(pdf_bytes, sessao, usuario, categoria):
    """O PDF final (já com o timbrado) assinado com o certificado do médico no provedor."""
    from flask import current_app
    from src.utils import assinatura, contas
    token = assinatura.decifrar(sessao['token'], current_app.config['SECRET_KEY'])
    return assinatura.assinar_pdf(
        pdf_bytes, sessao['certificado'],
        lambda resumo: assinatura.assinar_resumo(sessao['provedor'], token, sessao['alias'], resumo),
        metadados=assinatura.metadados_iti(contas.crm_de(usuario), categoria), titular=sessao['titular'])


def _gerar_pdf(categoria, nome_gerador, prefixo_arquivo, mensagem_vazia, conferir=None):
    import io
    from flask import send_file
    from src.utils import pdf_minutas

    try:
        dados_paciente, itens = _ler_pedido_de_pdf(categoria)
        if not itens:
            raise PedidoDePdfInvalido(mensagem_vazia)
        if conferir:
            conferir(dados_paciente, itens)
    except PedidoDePdfInvalido as exc:
        return jsonify({'error': exc.mensagem, 'codigo': exc.codigo}), 400

    try:
        from src.routes.auth import usuario_atual
        from src.utils import i18n
        usuario = usuario_atual()
        extras = {}
        if categoria in ('laboratorio', 'imagem'):
            justificativa = _ler_justificativa()
            if justificativa:
                extras['justificativa'] = justificativa
            guia = _ler_guia_do_plano(usuario)
            apac = _ler_apac(usuario, categoria)
            if guia and apac:
                raise PedidoDePdfInvalido('Escolha o plano de saúde ou o SUS (APAC), não os dois.')
            if apac:
                extras['apac'] = apac
            if guia:
                if justificativa and not (request.get_json(silent=True) or {}).get('guia', {}).get('indicacao'):
                    guia['indicacao'] = pdf_minutas.indicacao_clinica(justificativa)
                extras['guia'] = guia
        extras.update(_timbrado_do_medico(usuario))
        sessao = _sessao_para_assinar(usuario)
        if sessao:
            extras['assinatura'] = {'titular': sessao['titular']}
    except PedidoDePdfInvalido as exc:
        return jsonify({'error': exc.mensagem, 'codigo': exc.codigo}), 409 if exc.codigo == 'assinatura_sem_sessao' else 400

    try:
        pdf_bytes = getattr(pdf_minutas, nome_gerador)(
            dados_paciente, itens, responsavel=pdf_minutas.responsavel_de(usuario),
            idioma=i18n.idioma_do_pedido(request), **extras)
    except Exception as exc:
        # O detalhe fica só no log do servidor; a resposta não expõe a infraestrutura.
        print(f"❌ Erro ao gerar PDF ({categoria}): {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Não foi possível gerar o PDF no momento. Tente novamente em instantes.',
            'codigo': 'falha_na_geracao',
        }), 502

    from src.utils import uso
    if sessao:
        from src.utils import assinatura, contas
        try:
            pdf_bytes = _assinar(pdf_bytes, sessao, usuario, categoria)
        except assinatura.SessaoExpirada:
            # O provedor não aceita mais o token (venceu ou foi encerrado no aplicativo dele).
            contas.encerrar_sessao_de_assinatura(usuario['id'])
            return jsonify({'error': MSG_SESSAO_DE_ASSINATURA_VENCIDA, 'codigo': 'assinatura_sem_sessao'}), 409
        except assinatura.FalhaNaAssinatura as exc:
            print(f"❌ Erro ao assinar PDF ({categoria}): {exc}")
            return jsonify({'error': MSG_ASSINATURA_FALHOU, 'codigo': 'assinatura_falhou'}), 502
        uso.registrar('pdf_assinado', usuario)
    uso.registrar(uso.POR_CATEGORIA_DE_PDF.get(categoria), usuario)
    if extras.get('guia'):
        uso.registrar('guia_plano', usuario)
    if extras.get('apac'):
        uso.registrar('apac', usuario)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{prefixo_arquivo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )


@checkup_intelligent_bp.route('/preoperatorio', methods=['POST'])
def preoperatorio_endpoint():
    """Avaliação pré-operatória de cirurgia não cardíaca (aba "Pré-operatório")."""
    from src.utils import periodicidade, preoperatorio, preop_medicamentos
    bruto = request.get_json(silent=True) or {}
    anteriores, erros = periodicidade.ler_exames_anteriores(bruto.get('exames_anteriores'))
    if erros:
        return jsonify({'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in erros),
                        'codigo': 'entrada_invalida', 'erros': erros}), 400
    try:
        p = preoperatorio.ler(bruto)
    except preoperatorio.EntradaInvalida as exc:
        mensagem = exc.mensagem     # texto de validação escrito por nós, nunca o rastro da exceção
        return jsonify({'error': 'Dados inválidos: ' + mensagem, 'codigo': 'entrada_invalida',
                        'erros': [{'campo': '', 'mensagem': mensagem}]}), 400
    preoperatorio.aplicar_exames_anteriores(p, anteriores)
    resultado = preoperatorio.avaliar(p)
    pas, pad = p.get('pas'), p.get('pad')
    ctx = {'idade': p['idade'], 'sexo': p['sexo'], 'peso': p['peso'], 'clcr': resultado['clcr'], 'tfg': resultado['tfg'], 'cirurgia': p['cirurgia'],
           'sangramento': p['sangramento'], 'cirurgia_risco_elevado': resultado['contexto']['cir_elev'],
           'urgencia': p['urgencia'], 'neuroaxial': p['neuroaxial'], 'condicoes': set(p['condicoes']),
           'stent': p['stent'], 'aas_indicacao': p['aas_indicacao'],
           'pa_controlada': (pas < 140 and pad < 90) if pas and pad else None}
    resultado['medicamentos'] = preop_medicamentos.condutas(p['medicacoes'], ctx)
    _links_do_preoperatorio(resultado)
    from src.routes.auth import usuario_atual
    from src.utils import uso
    uso.registrar('preoperatorio', usuario_atual())
    return jsonify(resultado)


def _links_do_preoperatorio(valor):
    """Toda entrada com 'referencias' ganha 'referencia_html' (links clicáveis)."""
    if isinstance(valor, dict):
        if isinstance(valor.get('referencias'), list):
            valor['referencia_html'] = build_reference_html(valor['referencias'])
        for v in valor.values():
            _links_do_preoperatorio(v)
    elif isinstance(valor, list):
        for v in valor:
            _links_do_preoperatorio(v)


@checkup_intelligent_bp.route('/apac/exames')
def exames_em_apac_endpoint():
    """Títulos do catálogo que saem com laudo de APAC, para a tela saber quando pedir os dados do laudo."""
    from src.utils import sigtap
    from src.utils.catalogo import catalogo
    dados = catalogo()
    return jsonify({'titulos': sigtap.titulos_em_apac(dados['laboratorio'] + dados['imagem']),
                    'fonte': sigtap.tabela_de_pac()['fonte']})


@checkup_intelligent_bp.route('/catalogo')
def catalogo_endpoint():
    """Itens que o médico pode acrescentar a um pedido ou receita, por categoria."""
    from src.utils.catalogo import catalogo
    return jsonify(catalogo())


@checkup_intelligent_bp.route('/exames-conhecidos')
def exames_conhecidos_endpoint():
    """Nomes de exame para a seção "Exames já realizados" do formulário."""
    from src.utils import periodicidade
    return jsonify({'exames': periodicidade.exames_conhecidos()})


@checkup_intelligent_bp.route('/exames-comuns')
def exames_comuns_endpoint():
    """Os exames mais pedidos, com os campos de resultado de cada um (seção "Exames já realizados")."""
    from src.utils import exames_comuns
    return jsonify(exames_comuns.para_a_tela())


@checkup_intelligent_bp.route('/laudos/ler', methods=['POST'])
def ler_laudo_endpoint():
    """Lê um laudo em PDF (campo `arquivo`) e devolve os exames e as datas de coleta para "Exames já
    realizados". O arquivo é lido em memória e descartado; nada dele é gravado nem registrado."""
    from src.utils import laudos
    request.max_content_length = laudos.TAMANHO_MAXIMO + 64 * 1024
    try:
        arquivo = request.files.get('arquivo')
    except Exception:  # corpo maior que o limite
        return jsonify({'error': 'O arquivo passa de 4 MB. Envie um laudo por vez.'}), 413
    if arquivo is None:
        return jsonify({'error': 'Anexe o laudo em PDF.'}), 400
    try:
        lido = laudos.ler(arquivo.read(laudos.TAMANHO_MAXIMO + 1))
    except laudos.LaudoIlegivel as erro:
        return jsonify({'error': laudos.MENSAGENS.get(erro.codigo, laudos.MENSAGENS['invalido'])}), 422
    return jsonify(lido)


@checkup_intelligent_bp.route('/coerencia')
def coerencia_endpoint():
    """Termos usados pela tela para marcar caixas a partir do texto (mesma lista do servidor)."""
    return jsonify({'termos': coerencia.TERMOS})


@checkup_intelligent_bp.route('/gerar-pdf-exames-laboratoriais', methods=['POST'])
def gerar_pdf_exames_laboratoriais_endpoint():
    """Minuta de solicitação de exames laboratoriais.

    Corpo: {dados_paciente: {nome, idade, sexo}, recomendacoes: [...]}.
    Só entram os itens de categoria `laboratorio`. Resposta: PDF.
    """
    return _gerar_pdf('laboratorio', 'gerar_pdf_exames_laboratoriais', 'exames_laboratoriais',
                      'Nenhum exame laboratorial encontrado')


@checkup_intelligent_bp.route('/gerar-pdf-exames-imagem', methods=['POST'])
def gerar_pdf_exames_imagem_endpoint():
    """Minuta de solicitação de exames de imagem.

    Corpo: {dados_paciente: {nome, idade, sexo}, recomendacoes: [...]}.
    Só entram os itens de categoria `imagem`. Resposta: PDF.
    """
    return _gerar_pdf('imagem', 'gerar_pdf_exames_imagem', 'exames_imagem',
                      'Nenhum exame de imagem encontrado')


@checkup_intelligent_bp.route('/gerar-pdf-vacinas', methods=['POST'])
def gerar_pdf_vacinas_endpoint():
    """Minuta de prescrição de vacinas.

    Corpo: {dados_paciente: {nome, idade, sexo, gestante, lactante, imunossupressao,
    hiv, cd4}, recomendacoes: [...]}. Só entram os itens de categoria `vacina`, e a
    triagem de segurança é conferida de novo. Resposta: PDF.
    """
    return _gerar_pdf('vacina', 'gerar_pdf_vacinas', 'vacinas',
                      'Nenhuma vacina encontrada', conferir=_conferir_triagem_das_vacinas)
