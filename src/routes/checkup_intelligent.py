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
from src.utils.seguranca_vacinas import aplicar_triagem_vacinas
from src.utils.validacao import EntradaInvalida, SIM, ler_numero, normalizar_triagem, validar_entrada

checkup_intelligent_bp = Blueprint('checkup_intelligent', __name__)

def generate_age_sex_recommendations(age, sex, country='BR', has_hypertension=False, has_resistant_hypertension=False, is_pregnant=False, tabagismo='nunca_fumou', macos_ano=0, has_dpoc=False, has_cardiopatia_cronica=False,
                                     pa_alterada=False, rastreio_dm=None, risco_drc=False, rastrear_hbv=False, prep=False, fatores_osso=False):
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

    # Sífilis: o PCDT-IST 2022 (Quadro 5) não deixa clara a periodicidade fora da gestação e das populações-chave;
    # o motor indica o teste só com risco que o formulário identifica (uso de PrEP) e orienta nos demais casos.
    if prep:
        _add_rec({
            'titulo': 'Anti-HIV 1 e 2, soro',
            'descricao': 'Uso de PrEP: teste de HIV a cada retorno, na periodicidade do protocolo de PrEP do serviço.',
            'subtitulo': 'Em uso de PrEP | Conforme protocolo de PrEP',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'PCDT-IST MS 2022',
            'grau_evidencia': 'A'
        })
        _add_rec({
            'titulo': 'Sífilis: teste treponêmico ou VDRL, soro',
            'descricao': 'Uso de PrEP é risco aumentado de IST: oferecer teste para sífilis junto do teste de HIV, na '
                         'periodicidade do protocolo de PrEP do serviço.',
            'subtitulo': 'Em uso de PrEP | Conforme protocolo de PrEP',
            'categoria': 'laboratorio',
            'prioridade': 'alta',
            'referencia': 'PCDT-IST MS 2022 / USPSTF 2022',
            'grau_evidencia': 'A'
        })

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
        
        # Colo do útero: regras em src/utils/colo_utero.py (dependem de imunossupressão e do último resultado).

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
                         'e pedir a densitometria se o risco estiver elevado. Confirme que a paciente está na pós-menopausa.',
            'subtitulo': 'Pós-menopausa <65 anos com fator de risco | Fator de risco',
            'categoria': 'imagem',
            'prioridade': 'media',
            'referencia': 'USPSTF 2025 / BHOF 2022',
            'grau_evidencia': 'B'
        })
    
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
        'descricao': 'Esquema completo: reforço com dTpa a cada 10 anos. Incompleto: 1 dose de dTpa e completar com dT até 3 doses com componente tetânico. Não vacinado/desconhecido: 1 dTpa + 2 dT (0-2-4 a 8 meses). Contactante de lactente: considerar antecipar o reforço para 5 anos. Viagem a área com pólio: dTpa-VIP.',
        'subtitulo': 'Rotina | Reforço a cada 10 anos (+ cada gestação)',
        'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
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
            'descricao': '2 doses com intervalo de 3 meses (0-3), independentemente de contato prévio com dengue. Licenciada de 4 a 60 anos. Contraindicada em gestantes e lactantes.',
            'subtitulo': 'Até 60 anos | 2 doses (0-3m) | Rede privada',
            'categoria': 'vacina', 'prioridade': 'media', 'referencia': REF_SBIM, 'grau_evidencia': 'B'
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
                + ')') + ' | Dose única | PNI: grupos de risco (CRIE)',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })

    # Vírus sincicial respiratório
    if is_pregnant and sex == 'feminino':
        _add_rec({
            'titulo': 'RSV - Vírus Sincicial Respiratório (Abrysvo®)',
            'descricao': 'Dose única a cada gestação. SBIm/PNI: a partir de 28 semanas (24-27 a critério médico). ACOG/CDC: 32 a 36 semanas, preferencialmente na sazonalidade. Única vacina VSR licenciada para gestantes.',
            'subtitulo': 'Gestantes ≥28 sem (SBIm) ou 32-36 sem (ACOG) | Dose única por gestação | PNI: sim',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM + ' / ACOG 2025', 'grau_evidencia': 'A'
        })
    elif age >= 70:
        _add_rec({
            'titulo': 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)',
            'descricao': 'Dose única, em qualquer época do ano. Rotina a partir de 70 anos, independentemente de fator de risco. Pode ser aplicada junto com as outras vacinas da idade.',
            'subtitulo': 'A partir de 70 anos | Rotina | Dose única | Rede privada',
            'categoria': 'vacina', 'prioridade': 'alta', 'referencia': REF_SBIM, 'grau_evidencia': 'A'
        })
    elif idoso:
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
                            fatores_osso):
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
                     'Com PA de 130-139/80-89 mmHg, o motor segue a AHA/ACC 2025 (HAS estágio 1, a confirmar com MRPA ou '
                     'MAPA). A SBC 2025 chama essa faixa de pré-hipertensão e só considera HAS a partir de 140/90 mmHg.',
                     'AHA 2025 / SBC 2025')
    if has_hypertension and not has_resistant_hypertension:
        orientar('Divergência entre diretrizes: ecocardiograma na HAS',
                 'O motor segue a AHA/ACC 2025: ecocardiograma só com indicação (ECG com sobrecarga ventricular esquerda, '
                 'suspeita de insuficiência cardíaca, HAS de difícil controle). A SBC 2025 inclui o ecocardiograma na '
                 'avaliação de lesão de órgão-alvo cardíaca.', 'AHA 2025 / SBC 2025')
    if is_diabetic and not has_hypertension:
        orientar('Divergência entre diretrizes: ECG no diabetes',
                 'Sem HAS, o motor não pede ECG ao diabético assintomático (ADA 2026: não rastrear doença coronariana em '
                 'assintomático). A ACCF/AHA 2010 considera razoável um ECG basal (IIa): pedir se o médico optar por ele.',
                 'ADA 2026 (seção 10) / ACCF/AHA 2010')
    if not is_diabetic:
        if rastreio_dm == 'Adultos 35-70 anos' and (imc is None or imc < 25):
            orientar('Divergência entre diretrizes: rastreio de diabetes sem sobrepeso',
                     'O motor segue a ADA 2026 (rastreio a partir dos 35 anos, qualquer que seja o peso). A USPSTF 2021 '
                     'restringe o rastreio dos 35 aos 70 anos a quem tem sobrepeso ou obesidade.', 'ADA 2026 / USPSTF 2021')
        elif rastreio_dm is None and idade > 70:
            orientar('Divergência entre diretrizes: rastreio de diabetes depois dos 70 anos',
                     'Acima de 70 anos o motor só rastreia com IMC ≥ 25 e fator de risco (USPSTF 2021: rastreio dos 35 aos 70 '
                     'anos). A ADA 2026 não tem idade de parada: considerar se a expectativa de vida justificar.',
                     'USPSTF 2021 / ADA 2026')
    if not hiv:
        if idade <= 30 and not gestante:
            orientar('Divergência entre diretrizes: frequência do teste de HIV',
                     'Até 30 anos o motor segue o PCDT-IST 2022 (teste anual). A USPSTF 2019 pede pelo menos um teste dos 15 '
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
                 'O motor segue o MS 2026 (PCDT Hepatite C), sem idade limite para o teste único. A USPSTF 2020 recomenda '
                 'rastrear hepatite C dos 18 aos 79 anos.', 'MS 2026 (PCDT Hepatite C) / USPSTF 2020')
    if rastrear_hbv and adulto:
        orientar('Divergência entre diretrizes: rastreio de hepatite B',
                 'O motor segue o CDC 2023 e o MS (painel uma vez em adulto sem vacinação documentada). A USPSTF 2020 '
                 'recomenda rastrear só quem tem risco aumentado (B).', 'CDC 2023 (hepatite B) / USPSTF 2020')
    if sexo == 'masculino' and 65 <= idade <= 75 and tabagismo == 'nunca':
        orientar('Aneurisma de aorta: homem que nunca fumou',
                 'Ultrassonografia de aorta como oferta seletiva (USPSTF C): decidir com o paciente, considerando história '
                 'familiar de aneurisma, outros aneurismas, DPOC ou doença cardiovascular.', 'USPSTF 2019')
    if sexo == 'masculino' and idade >= 70:
        orientar('Divergência entre diretrizes: densitometria no homem',
                 'O motor não pede densitometria ao homem sem fator de risco (USPSTF 2025: evidência insuficiente). A BHOF '
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
        if not any(c.startswith('nome:') for c in chaves):
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
        return (not r.get('gestacao'), (r.get('titulo') or '').strip() != preferido, -len(r.get('titulo') or ''))
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
    try:
        r = prevent.estimar(
            idade=idade, sexo=sexo, colesterol_total=float(data['colesterol']), hdl=float(data['hdl']),
            pas=float(data['pas']), diabetes=is_diabetic, fumante=data.get('tabagismo') == 'atual',
            imc_valor=imc_valor, egfr=egfr, anti_hipertensivo='anti_hipertensivos' in medicacoes,
            estatina='estatinas' in medicacoes, hba1c=hba1c)
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
    }


@checkup_intelligent_bp.route('/checkup-intelligent', methods=['POST'])
def generate_intelligent_recommendations():
    try:
        # Validar e normalizar a entrada. Nada é presumido: idade, sexo e tabagismo são
        # obrigatórios, valores impossíveis são recusados e dado ausente não vira valor padrão.
        try:
            data, triagem = validar_entrada(request.get_json(silent=True))
        except EntradaInvalida as exc:
            return jsonify({
                'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                'codigo': 'entrada_invalida',
                'erros': exc.erros,
            }), 400

        # Exames que o paciente já fez (opcional): o que estiver em dia não é pedido de novo.
        from src.utils import periodicidade
        exames_anteriores, erros_exames = periodicidade.ler_exames_anteriores(
            (request.get_json(silent=True) or {}).get('exames_anteriores'))
        if erros_exames:
            return jsonify({
                'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in erros_exames),
                'codigo': 'entrada_invalida',
                'erros': erros_exames,
            }), 400

        # Dados do paciente (já normalizados)
        age = data['idade']
        sex = data['sexo']
        is_pregnant = triagem['gestante'] == SIM
        gestacao = None
        if is_pregnant:
            try:
                gestacao = prenatal.normalizar(request.get_json(silent=True) or {})
            except prenatal.GestacaoInvalida as exc:
                return jsonify({
                    'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                    'codigo': 'entrada_invalida',
                    'erros': exc.erros,
                }), 400
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
            detalhes_doses = doses.ler(request.get_json(silent=True) or {}, escolhidas)
        except doses.DetalheInvalido as exc:
            return jsonify({'error': 'Dados inválidos: ' + ' '.join(e['mensagem'] for e in exc.erros),
                            'codigo': 'entrada_invalida', 'erros': exc.erros}), 400
        # Dose e duração (corticoide, metotrexato, azatioprina, hidroxicloroquina, bisfosfonato) ajustam as
        # classes: a exclusão vale só para o medicamento avaliado, não para outro que traga a mesma classe.
        mais, excluir_por_medicamento, orientacoes_doses = doses.avaliar(
            escolhidas, detalhes_doses, peso=data.get('peso'),
            rotulos={k: medicamentos.MEDICAMENTOS[k]['rotulo'] for k in escolhidas if k in medicamentos.MEDICAMENTOS})
        medicacoes_checkboxes = medicamentos.classes_de(escolhidas, excluir_por_medicamento)
        medicacoes_checkboxes += [c for c in sorted(mais) if c not in medicacoes_checkboxes]
        comorbidades, medicacoes_checkboxes, inferencias = coerencia.inferir(
            {**data, 'comorbidades': comorbidades, 'medicacoes': medicacoes_checkboxes}, egfr=egfr_inferencia,
            gestante=is_pregnant, recusados=_lista_curta((request.get_json(silent=True) or {}).get('inferencias_recusadas')),
            escolhidas=escolhidas)
        familia = data.get('historia_familiar') or []
        familia = [k for k, v in familia.items() if v] if isinstance(familia, dict) else list(familia)
        # Itens que implicam imunossupressão valem como "Sim" na triagem de vacinas.
        if condicoes.imunossupressao_implicada(comorbidades, medicacoes_checkboxes):
            triagem['imunossupressao'] = SIM
        pa_classificacao = coerencia.classificar_pa(data.get('pas'), data.get('pad'))
        
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
        ja_diabetico = (bool(set(condicoes.TIPOS_DE_DIABETES) & set(comorbidades)) or 'insulina' in medicacoes_checkboxes
                        or (data.get('hba1c') is not None and float(data['hba1c']) >= 6.5))
        pa_alterada = coerencia.pa_a_confirmar(pa_classificacao, comorbidades, gestante=is_pregnant)
        rastreio_dm = None if ja_diabetico else criterio_rastreio_dm(
            age, imc, fatores_risco_dm(data, comorbidades, medicacoes_checkboxes, familia, has_hypertension))
        risco_drc = has_hypertension or has_dcv_aterosclerotica or has_ic or 'rim_policistico' in familia
        prep = 'hiv' not in comorbidades and bool({'tenofovir_entricitabina', 'cabotegravir'} & set(escolhidas))
        alcool = (request.get_json(silent=True) or {}).get('alcoolismo')
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
                                                         rastrear_hbv=not is_pregnant and 'hepatite_b_cronica' not in comorbidades)
        recommendations.extend(age_sex_recs)

        # Colo do útero: teste de DNA-HPV e colposcopia (MS 2025, SBOC 2026, ACOG 2026).
        orientacoes_colo = []
        if sex == 'feminino':
            recs_colo, orientacoes_colo = colo_utero.recomendar(
                age, imunossuprimida='hiv' in comorbidades or triagem.get('imunossupressao') == SIM,
                resultado=data.get('hpv_resultado'), histerectomizada=colo_utero.HISTERECTOMIA in comorbidades)
            recommendations.extend(recs_colo)
        
        # Rastreamento de câncer de pulmão (LDCT) - USPSTF 2021
        # tabagismo e macos_ano já extraídos acima
        anos_parou_fumar = float(data.get('anos_parou_fumar', 0)) if data.get('anos_parou_fumar') else 0
        
        # Critérios: 50-80 anos, ≥20 maços-ano, fumante atual OU parou há <15 anos
        elegivel_ldct = False
        if 50 <= age <= 80 and macos_ano >= 20:
            if tabagismo == 'atual':
                elegivel_ldct = True
            elif tabagismo == 'ex' and anos_parou_fumar < 15:
                elegivel_ldct = True
        
        if elegivel_ldct:
            recommendations.append({
                'titulo': 'Tomografia computadorizada de tórax de baixa dose (LDCT)',
                'descricao': 'Rastreamento anual de câncer de pulmão. Indicado para adultos 50-80 anos com história de tabagismo de 20 maços-ano e que atualmente fumam ou pararam nos últimos 15 anos. Descontinuar se não fumou por 15 anos ou desenvolveu problema de saúde que limita substancialmente expectativa de vida.',
                'subtitulo': 'Adultos 50-80 anos com ≥20 maços-ano | Anual',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'USPSTF 2021',
                'link': 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/lung-cancer-screening',
                'grau_evidencia': 'B'
            })
        
        # ========== DIABETES SCREENING E MANAGEMENT (ADA 2024) ==========
        
        # Verificar se já é diabético
        # Qualquer tipo de diabetes (ADA 2026); insulina em uso indica diabetes mesmo sem o tipo marcado.
        is_diabetic = bool(set(condicoes.TIPOS_DE_DIABETES) & set(comorbidades)) or 'insulina' in medicacoes_checkboxes
        
        # Verificar HbA1C se fornecido
        hba1c = float(data.get('hba1c', 0)) if data.get('hba1c') else None
        diabetes_por_hba1c = False
        if hba1c is not None and hba1c >= 6.5 and not set(condicoes.TIPOS_DE_DIABETES) & set(comorbidades):
            # ADA: HbA1c ≥ 6,5% é critério diagnóstico de diabetes (confirmar com 2º exame se não houver
            # hiperglicemia inequívoca), mas não diz o tipo: o paciente é tratado como diabético sem marcar
            # tipo 1, tipo 2 ou outro. "diabetes_sem_tipo" é só um marcador interno, não existe na tela.
            diabetes_por_hba1c = True
            is_diabetic = True
            comorbidades.append('diabetes_sem_tipo')
        
        # TOTG só com indicação: glicemia ou HbA1c limítrofes (pré-diabetes marcado ou HbA1c de 5,7 a 6,4%),
        # para confirmar o diagnóstico. Não entra no check-up de rotina e nunca em quem já tem diabetes
        # (tipo 1, tipo 2, em uso de insulina ou antidiabético). O TOTG da gestação é o do pré-natal.
        if is_diabetic or 'pre_diabetes' not in comorbidades:
            recommendations = [r for r in recommendations if not (r.get('titulo') or '').startswith('TOTG-75g')]
        if is_diabetic:
            # Quem já tem diabetes não faz rastreamento: glicemia e HbA1c passam a ser acompanhamento do controle.
            controle = {
                'Hemoglobina glicada (HbA1c), soro': {
                    'descricao': 'Controle glicêmico no diabetes: pelo menos 2 vezes ao ano em quem está na meta e a cada '
                                 '3 meses após mudança de tratamento ou fora da meta.',
                    'subtitulo': 'Diabéticos | A cada 3-6 meses', 'referencia': 'ADA 2025', 'grau_evidencia': 'A'},
                'Glicose, soro': {
                    'descricao': 'Glicemia de jejum no acompanhamento do diabetes, junto da HbA1c.',
                    'subtitulo': 'Diabéticos | Junto da HbA1c', 'referencia': 'ADA 2025', 'grau_evidencia': 'B'},
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
            # Perfil lipídico (ADA 2026, seção 10): na avaliação inicial; sem estatina e < 40 anos, a cada 5 anos;
            # com estatina, 4-12 semanas após iniciar ou ajustar e depois anualmente. Soma o motivo ao item que já existe.
            if 'estatinas' in medicacoes_checkboxes:
                condicoes._garantir(recommendations, condicoes._rec(
                    'Colesterol total e frações, soro', 'laboratorio',
                    'Diabetes em uso de estatina: perfil lipídico 4-12 semanas após iniciar ou ajustar a dose e depois anualmente.',
                    'Diabéticos em uso de estatina | Anual', 'ADA 2026 (seção 10)', 'A', 'alta'))
            else:
                condicoes._garantir(recommendations, condicoes._rec(
                    'Colesterol total e frações, soro', 'laboratorio',
                    'Diabetes: perfil lipídico no diagnóstico e na avaliação inicial; sem estatina e com menos de 40 anos, a '
                    'cada 5 anos. Ao iniciar ou ajustar a estatina, repetir em 4-12 semanas e depois anualmente.',
                    'Diabéticos | Avaliação inicial', 'ADA 2026 (seção 10)', 'A', 'alta'))

            # Função hepática (TGO, TGP)
            recommendations.append({
                'titulo': 'Aspartato aminotransferase, soro',
                'descricao': 'Avaliação da função hepática em pacientes diabéticos. Importante antes de iniciar estatinas e para rastreamento de esteatose hepática não alcoólica (NAFLD).',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': '<a href="https://diabetesjournals.org/care/article/47/Supplement_1/S1/153904/Standards-of-Care-in-Diabetes-2024" target="_blank">ADA 2024</a>',
                'grau_evidencia': 'A'
            })
            recommendations.append({
                'titulo': 'Alanina aminotransferase, soro',
                'descricao': 'Avaliação da função hepática em pacientes diabéticos. Importante antes de iniciar estatinas e para rastreamento de esteatose hepática não alcoólica (NAFLD).',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'B'
            })
            
            # Relação albumina/creatinina urinária (microalbuminúria)
            recommendations.append({
                'titulo': 'Relação albumina/creatinina urinária (uACR)',
                'descricao': 'Rastreamento de nefropatia diabética. Valores ≥30 mg/g indicam albuminúria e risco aumentado de doença renal. Realizar anualmente.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'ADA 2024',
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
            
            # Vitamina B12 (se em uso de metformina)
            medicacoes_continuo_lower = medicacoes_continuo.lower()
            if 'metformina' in medicacoes_continuo_lower or 'metformin' in medicacoes_continuo_lower:
                recommendations.append({
                    'titulo': 'Vitamina B12, soro',
                    'descricao': 'Monitoramento de deficiência de vitamina B12 em pacientes em uso de metformina. A metformina pode reduzir a absorção de B12, especialmente em uso prolongado.',
                    'subtitulo': 'Diabéticos em uso de metformina | Periódico',
                    'categoria': 'laboratorio',
                    'prioridade': 'media',
                    'referencia': 'ADA 2024',
                    'grau_evidencia': 'B'
                })
            
            # Hemograma completo
            recommendations.append({
                'titulo': 'Hemograma completo com plaquetas',
                'descricao': 'Avaliação hematológica em pacientes diabéticos. Importante para detectar anemia, infecções e outras alterações hematológicas.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'E'
            })
            
            # Potássio sérico (se em uso de IECA/BRA/diuréticos)
            # Palavra inteira: "bra" por substring casava com "brasil", "cobra" etc.
            usa_ieca_bra = bool(re.search(r'\b(enalapril|captopril|ramipril|lisinopril|losartan[a]?|valsartan[a]?|olmesartana|candesartana|telmisartana|ieca|bra)\b', medicacoes_continuo_lower))
            usa_diuretico = any(keyword in medicacoes_continuo_lower for keyword in ['hidroclorotiazida', 'furosemida', 'espironolactona', 'diurético', 'diuretico'])
            
            if usa_ieca_bra or usa_diuretico:
                recommendations.append({
                    'titulo': 'Potássio, soro',
                    'descricao': 'Monitoramento de potássio em pacientes diabéticos em uso de IECA, BRA ou diuréticos. Importante para prevenir hiper ou hipocalemia.',
                    'subtitulo': 'Diabéticos em uso de IECA/BRA/diuréticos | Periódico',
                    'categoria': 'laboratorio',
                    'prioridade': 'alta',
                    'referencia': 'ADA 2024',
                    'grau_evidencia': 'E'
                })
            
            # Cálcio, vitamina D e fósforo (para pacientes apropriados)
            recommendations.append({
                'titulo': 'Cálcio iônico, soro',
                'descricao': 'Avaliação do metabolismo ósseo e risco de osteoporose em pacientes diabéticos.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': '<a href="https://diabetesjournals.org/care/article/47/Supplement_1/S1/153904/Standards-of-Care-in-Diabetes-2024" target="_blank">ADA 2024</a>',
                'grau_evidencia': 'B'
            })
            recommendations.append({
                'titulo': '25-hidroxivitamina D, soro',
                'descricao': 'Avaliação do metabolismo ósseo e risco de osteoporose em pacientes diabéticos.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': '<a href="https://diabetesjournals.org/care/article/47/Supplement_1/S1/153904/Standards-of-Care-in-Diabetes-2024" target="_blank">ADA 2024</a>',
                'grau_evidencia': 'B'
            })
            recommendations.append({
                'titulo': 'Fósforo, soro',
                'descricao': 'Avaliação do metabolismo ósseo em pacientes diabéticos, especialmente com doença renal ou osteoporose. Deficiência de vitamina D é comum em diabéticos.',
                'subtitulo': 'Diabéticos com doença renal ou osteoporose | Conforme necessidade',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'E'
            })
            
            # EXAMES DE IMAGEM PARA DIABÉTICOS
            
            # Fundoscopia (exame oftalmológico)
            recommendations.append({
                'titulo': 'Fundoscopia (Exame de fundo de olho)',
                'descricao': 'Rastreamento de retinopatia diabética. Realizar exame oftalmológico completo com dilatação pupilar anualmente. A retinopatia diabética é a principal causa de cegueira em adultos.',
                'subtitulo': 'Diabéticos | Anual',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'ADA 2024',
                'grau_evidencia': 'A'
            })
            
            # ECG: a ADA não recomenda rastrear doença coronariana no diabético assintomático; a ACCF/AHA 2010 acha
            # razoável um ECG basal (IIa). Não entra sozinho: orientação de divergência (orientacoes_rastreio).

        # ========== HIV: src/utils/hiv.py (MS 2024 PCDT HIV / HIVMA/IDSA 2024) ==========
        is_hiv_positive = 'hiv' in comorbidades
        orientacoes_hiv = []
        if is_hiv_positive:
            hiv_data = data.get('hiv_data') or {}
            meds_texto = (medicacoes_continuo + ' ' + ' '.join(str(m) for m in medicacoes_checkboxes)).lower()
            recs_hiv, orientacoes_hiv = hiv.recomendar(
                age, sex, cd4=hiv_data.get('cd4') or data.get('cd4'),
                carga_viral=hiv_data.get('carga_viral') or data.get('carga_viral'),
                em_tarv='sim' in (hiv_data.get('em_tarv'), data.get('em_tarv')),
                supressao_viral='sim' in (hiv_data.get('supressao_viral'), data.get('supressao_viral')),
                gestante=is_pregnant, tenofovir='tenofovir' in meds_texto,
                risco_renal=any(c in comorbidades for c in ('diabetes', 'hipertensao', 'doenca_renal')))
            recommendations.extend(recs_hiv)

        # ========== DPOC MANAGEMENT (GOLD COPD 2023) ==========
        
        is_dpoc = 'dpoc' in comorbidades
        
        if is_dpoc:
            # Espirometria - exame fundamental para diagnóstico e monitoramento
            recommendations.append({
                'titulo': 'Espirometria, com broncodilatador',
                'descricao': 'Exame essencial para confirmar o diagnóstico de DPOC, avaliar gravidade da obstrução do fluxo aéreo e monitorar progressão da doença. Deve ser realizada após broncodilatador.',
                'subtitulo': 'DPOC | Anual ou conforme sintomas',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'A'
            })
            
            # Teste de caminhada de 6 minutos
            recommendations.append({
                'titulo': 'Teste de caminhada de 6 minutos',
                'descricao': 'Avalia capacidade funcional e tolerância ao exercício em pacientes com DPOC. Útil para avaliar resposta ao tratamento e prognóstico.',
                'subtitulo': 'DPOC | Anual ou conforme indicação',
                'categoria': 'imagem',
                'prioridade': 'media',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'B'
            })
            
            # Gasometria arterial
            recommendations.append({
                'titulo': 'Gasometria arterial, sangue arterial',
                'descricao': 'Avalia oxigenação e ventilação em pacientes com DPOC, especialmente em exacerbações ou doença avançada. Indica necessidade de oxigenoterapia.',
                'subtitulo': 'DPOC | Conforme indicação clínica',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'A'
            })
            
            # Eletrólitos
            recommendations.append({
                'titulo': 'Sódio, soro',
                'descricao': 'Avaliação de distúrbios eletrolíticos. Importante em pacientes com DPOC grave ou em uso de diuréticos.',
                'subtitulo': 'DPOC | Anual ou conforme indicação',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': '<a href="https://goldcopd.org/2023-gold-report/" target="_blank">GOLD COPD 2023</a>',
                'grau_evidencia': 'B'
            })
            recommendations.append({
                'titulo': 'Potássio, soro',
                'descricao': 'Avaliação de distúrbios eletrolíticos. Importante em pacientes com DPOC grave ou em uso de diuréticos.',
                'subtitulo': 'DPOC | Anual ou conforme indicação',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': '<a href="https://goldcopd.org/2023-gold-report/" target="_blank">GOLD COPD 2023</a>',
                'grau_evidencia': 'B'
            })
            recommendations.append({
                'titulo': 'Cloreto, soro',
                'descricao': 'Monitoramento de eletrólitos em pacientes com DPOC, especialmente aqueles em uso de diuréticos ou corticosteroides. Hipocalemia pode ocorrer com beta-agonistas.',
                'subtitulo': 'DPOC | Conforme uso de medicações',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'B'
            })
            
            # Radiografia de tórax
            recommendations.append({
                'titulo': 'Radiografia de tórax',
                'descricao': 'Exame de imagem para avaliar complicações (pneumonia, pneumotórax, insuficiência cardíaca) e excluir outros diagnósticos diferenciais.',
                'subtitulo': 'DPOC | Conforme indicação clínica',
                'categoria': 'imagem',
                'prioridade': 'media',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'B'
            })
            
            # Hemograma completo
            recommendations.append({
                'titulo': 'Hemograma completo, sangue total',
                'descricao': 'Avaliar policitemia secundária à hipoxemia crônica e descartar anemia que pode agravar dispneia.',
                'subtitulo': 'DPOC | Anual',
                'categoria': 'laboratorio',
                'prioridade': 'media',
                'referencia': 'GOLD COPD 2023',
                'link': 'https://goldcopd.org/2023-gold-report-2/',
                'grau_evidencia': 'B'
            })
        
        # Nenhum dado do paciente é gravado: a consulta é calculada e descartada.

        # Uso do sistema (painel /analytics): quem gerou o check-up, sem dado do paciente
        from src.routes.auth import usuario_atual
        from src.utils import uso
        uso.registrar('checkup', usuario_atual())
        
        # Listas de comorbidades, medicações e história familiar (src/utils/condicoes.py)
        orientacoes = condicoes.aplicar(recommendations, age, sex, comorbidades, medicacoes_checkboxes, familia,
                                        gestante=is_pregnant, tabagismo=tabagismo, imc=imc)

        # Gestação: rotina do pré-natal pela idade gestacional; itens do check-up geral que
        # não se aplicam na gestação saem da lista e aparecem como "adiados".
        adiados_gestacao, proximas_gestacao = [], []
        if gestacao is not None:
            if 'diabetes_gestacional_previo' in comorbidades and 'dmg_previo' not in gestacao['condicoes']:
                gestacao['condicoes'].append('dmg_previo')  # mesma informação, marcada na lista de comorbidades
            exames_pn, proximas_gestacao = prenatal.programacao(gestacao, age, hipertensa=has_hypertension,
                                                                diabetica=is_diabetic, hiv='hiv' in comorbidades)
            titulos_pn = {r['titulo'].lower() for r in exames_pn}
            recommendations = [r for r in recommendations if (r.get('titulo') or '').lower() not in titulos_pn]
            recommendations, adiados_gestacao = prenatal.adiar(recommendations, diabetica=is_diabetic)
            recommendations = prenatal.sem_equivalentes(recommendations, exames_pn)
            recommendations = exames_pn + recommendations

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
        contexto_vacinas = {'idade': age, 'hiv': is_hiv_positive, 'cd4': data.get('cd4')}
        mantidas, nao_incluidas = aplicar_triagem_vacinas(response['recommendations'], triagem, contexto_vacinas)
        if gestacao is not None:
            mantidas, vacinas_futuras = prenatal.vacinas_fora_da_janela(mantidas, gestacao['ig'])
            proximas_gestacao = sorted(proximas_gestacao + vacinas_futuras, key=lambda x: x['semana'])
        # Periodicidade: exame já feito e ainda dentro do intervalo da própria regra sai do pedido
        # e aparece em "não incluídos", com a data e a data a partir da qual volta a ser indicado.
        mantidas, em_dia = periodicidade.aplicar(mantidas, exames_anteriores, sex)
        nao_incluidas = nao_incluidas + em_dia
        response['recommendations'] = mantidas
        response['total_recommendations'] = len(mantidas)
        response['nao_incluidas'] = nao_incluidas
        response['adiados_gestacao'] = adiados_gestacao
        response['diabetes_por_hba1c'] = diabetes_por_hba1c
        response['inferencias'] = inferencias
        orientacoes_rastreio = orientacoes_de_rastreio(
            age, sex, gestante=is_pregnant, pa_informada=bool(sbp or dbp), pa_classificacao=pa_classificacao or {},
            pa_alterada=pa_alterada, has_hypertension=has_hypertension, has_resistant_hypertension=has_resistant_hypertension,
            is_diabetic=is_diabetic, rastreio_dm=rastreio_dm, imc=imc, hiv=is_hiv_positive, prep=prep,
            rastrear_hbv=not is_pregnant and 'hepatite_b_cronica' not in comorbidades, tabagismo=tabagismo,
            fatores_osso=fatores_osso)
        response['orientacoes'] = orientacoes_doses + orientacoes + orientacoes_colo + orientacoes_hiv + orientacoes_rastreio
        aviso_exames = periodicidade.orientacao_dos_nao_reconhecidos(exames_anteriores)
        if aviso_exames:
            response['orientacoes'] = response['orientacoes'] + [aviso_exames]
        # Orientações também levam a fonte clicável.
        for o in response['orientacoes']:
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
        return jsonify(response)
        
    except Exception as e:
        print(f"Erro na geração de recomendações: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

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
    contexto = {
        'idade': idade,
        'hiv': bool(dados_paciente.get('hiv')),
        'cd4': ler_numero(dados_paciente.get('cd4')),
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


def _timbrado_do_medico(usuario):
    """{'timbrado': ...} se o médico enviou o papel timbrado; um timbrado que não abre não impede o pedido."""
    from src.utils import contas, timbrado
    if not usuario or not contas.pode_ter_credenciamento(usuario):
        return {}
    try:
        registro = contas.timbrado_de(usuario['id'])
        return {'timbrado': timbrado.para_o_pdf(registro)} if registro else {}
    except timbrado.TimbradoInvalido:
        return {}


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
            guia = _ler_guia_do_plano(usuario)
            if guia:
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
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{prefixo_arquivo}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )


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
