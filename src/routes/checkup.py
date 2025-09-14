from flask import Blueprint, request, jsonify

checkup_bp = Blueprint('checkup', __name__)


def _parse_smoking_status(tabagismo, data=None):
    """
    Normaliza tabagismo aceitando dict, string e campos achatados do payload.
    Sempre retorna (status_normalizado, macos_ano_int).
    """
    # Inicializar com defaults seguros
    status = 'nunca_fumou'
    macos = 0
    
    try:
        # Se tabagismo é um dict (formato objeto)
        if isinstance(tabagismo, dict):
            status = tabagismo.get('status') or tabagismo.get('estado') or 'nunca_fumou'
            macos = int(tabagismo.get('macos_ano') or tabagismo.get('pack_years') or 0)
        # Se tabagismo é uma string
        elif isinstance(tabagismo, str):
            status = tabagismo
        
        # Verificar campos achatados no payload principal se data foi fornecido
        if data:
            # Priorizar campos achatados se existirem
            flattened_status = data.get('tabagismo_status')
            flattened_macos = data.get('tabagismo_macos_ano')
            
            if flattened_status:
                status = flattened_status
            if flattened_macos is not None:
                macos = int(flattened_macos)
        
    except (ValueError, TypeError, AttributeError):
        # Em caso de erro, manter defaults seguros
        status = 'nunca_fumou'
        macos = 0
    
    # Normalizar status se for string
    if isinstance(status, str):
        status = status.replace('-', '_').lower()
        # Mapear variações para valores padronizados
        if status in ['fumante', 'fumante_atual']:
            status = 'fumante_atual'
        elif status in ['ex-fumante', 'ex_fumante']:
            status = 'ex_fumante'
        elif status not in ['nunca_fumou', 'fumante_atual', 'ex_fumante']:
            status = 'nunca_fumou'  # Default seguro para valores desconhecidos
    else:
        status = 'nunca_fumou'  # Default se não for string
    
    return status, macos

@checkup_bp.route('/api/checkup', methods=['POST'])
def gerar_recomendacoes():
    """
    Gera recomendações de check-up baseadas nos dados do paciente
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Validar dados obrigatórios
        if 'idade' not in data or 'sexo' not in data:
            return jsonify({'error': 'Idade e sexo são obrigatórios'}), 400
        
        # Validar e converter tipos com defaults seguros
        try:
            idade = int(data['idade']) if data['idade'] is not None else 0
        except (ValueError, TypeError):
            idade = 0
            
        sexo = data['sexo'] if data['sexo'] is not None else ''
        comorbidades = data.get('comorbidades') or []
        if not isinstance(comorbidades, list):
            comorbidades = []
            
        outras_comorbidades = data.get('outras_comorbidades') or ''
        if not isinstance(outras_comorbidades, str):
            outras_comorbidades = ''
            
        historia_familiar = data.get('historia_familiar') or []
        if not isinstance(historia_familiar, list):
            historia_familiar = []
            
        outras_hf = data.get('outras_hf') or ''
        if not isinstance(outras_hf, str):
            outras_hf = ''
            
        tabagismo_raw = data.get('tabagismo', {})
        
        # Normalizar dados de tabagismo logo no início para evitar inconsistências
        tabagismo_status, tabagismo_macos_ano = _parse_smoking_status(tabagismo_raw, data)
        tabagismo_normalizado = {
            'status': tabagismo_status,
            'macos_ano': tabagismo_macos_ano
        }
        
        # Gerar recomendações
        recomendacoes = []
        
        # Rastreamento por idade e sexo
        recomendacoes.extend(get_age_sex_recommendations(idade, sexo, tabagismo_normalizado))
        
        # Rastreamento baseado em comorbidades
        recomendacoes.extend(get_comorbidity_recommendations(comorbidades))
        
        # Processar outras comorbidades (versão simplificada)
        if outras_comorbidades.strip():
            recomendacoes.extend(process_other_conditions_simple(outras_comorbidades, 'comorbidade'))
        
        # Rastreamento baseado em história familiar
        recomendacoes.extend(get_family_history_recommendations(historia_familiar, idade, sexo))
        
        # Processar outras condições familiares (versão simplificada)
        if outras_hf.strip():
            recomendacoes.extend(process_other_conditions_simple(outras_hf, 'historia_familiar'))
        
        # Rastreamento baseado em tabagismo
        recomendacoes.extend(get_smoking_recommendations(tabagismo_normalizado, idade))
        
        # Rastreamentos específicos por população
        recomendacoes.extend(get_population_specific_recommendations(idade, sexo, comorbidades))
        
        # Vacinação
        recomendacoes.extend(get_vaccination_recommendations(idade, comorbidades))
        
        # Remover duplicatas e ordenar por prioridade
        recomendacoes = remove_duplicates_and_sort(recomendacoes)
        
        return jsonify(recomendacoes)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_other_conditions_simple(conditions_text, condition_type):
    """Processa condições adicionais usando regras simples"""
    recomendacoes = []
    conditions_lower = conditions_text.lower()
    
    # Mapeamento de condições para recomendações
    condition_mappings = {
        'dpoc': {
            'titulo': 'Espirometria',
            'descricao': 'Avaliação da função pulmonar anual',
            'prioridade': 'alta',
            'referencia': 'GOLD 2024'
        },
        'artrite': {
            'titulo': 'VHS e PCR',
            'descricao': 'Marcadores inflamatórios para monitoramento',
            'prioridade': 'media',
            'referencia': 'ACR 2021'
        },
        'hipotireoidismo': {
            'titulo': 'TSH',
            'descricao': 'Hormônio estimulante da tireoide anual',
            'prioridade': 'alta',
            'referencia': 'ATA 2014'
        },
        'depressão': {
            'titulo': 'PHQ-9',
            'descricao': 'Questionário de depressão semestral',
            'prioridade': 'alta',
            'referencia': 'USPSTF Grau B'
        },
        'ansiedade': {
            'titulo': 'GAD-7',
            'descricao': 'Questionário de ansiedade conforme indicação',
            'prioridade': 'media',
            'referencia': 'USPSTF Grau B'
        },
        'próstata': {
            'titulo': 'PSA',
            'descricao': 'Antígeno prostático específico anual após os 50 anos',
            'prioridade': 'media',
            'referencia': 'USPSTF Grau C'
        },
        'alzheimer': {
            'titulo': 'Avaliação Cognitiva',
            'descricao': 'Rastreamento cognitivo anual após os 65 anos',
            'prioridade': 'media',
            'referencia': 'USPSTF Grau I'
        }
    }
    
    for condition, recommendation in condition_mappings.items():
        if condition in conditions_lower:
            rec = recommendation.copy()
            rec['categoria'] = f'outras_{condition_type}'
            recomendacoes.append(rec)
    
    return recomendacoes

def get_age_sex_recommendations(idade, sexo, tabagismo):
    """Recomendações baseadas em idade e sexo"""
    recomendacoes = []
    
    # Câncer de mama (mulheres 40-74 anos)
    if sexo == 'feminino' and 40 <= idade <= 74:
        recomendacoes.append({
            'titulo': 'Mamografia',
            'descricao': 'Mamografia bilateral a cada 2 anos',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cancer',
            'referencia': 'USPSTF Grau B'
        })
    
    # Câncer colorretal (45-75 anos)
    if 45 <= idade <= 49:
        recomendacoes.append({
            'titulo': 'Rastreamento Câncer Colorretal',
            'descricao': 'Colonoscopia, sigmoidoscopia ou pesquisa de sangue oculto nas fezes',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cancer',
            'referencia': 'USPSTF Grau B'
        })
    elif 50 <= idade <= 75:
        recomendacoes.append({
            'titulo': 'Rastreamento Câncer Colorretal',
            'descricao': 'Colonoscopia a cada 10 anos ou sigmoidoscopia a cada 5 anos',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cancer',
            'referencia': 'USPSTF Grau A'
        })
    
    # Câncer de colo de útero (mulheres 21-65 anos)
    if sexo == 'feminino':
        if 21 <= idade <= 29:
            recomendacoes.append({
                'titulo': 'Citologia Cervical',
                'descricao': 'Papanicolaou a cada 3 anos',
                'prioridade': 'alta',
                'categoria': 'rastreamento_cancer',
                'referencia': 'USPSTF Grau A'
            })
        elif 30 <= idade <= 65:
            recomendacoes.append({
                'titulo': 'Rastreamento Câncer Cervical',
                'descricao': 'Citologia a cada 3 anos OU co-teste (citologia + HPV) a cada 5 anos',
                'prioridade': 'alta',
                'categoria': 'rastreamento_cancer',
                'referencia': 'USPSTF Grau A'
            })
    
    # Osteoporose (mulheres ≥65 anos)
    if sexo == 'feminino' and idade >= 65:
        recomendacoes.append({
            'titulo': 'Densitometria Óssea',
            'descricao': 'DEXA para rastreamento de osteoporose',
            'prioridade': 'alta',
            'categoria': 'rastreamento_metabolico',
            'referencia': 'USPSTF Grau B'
        })
    
    # Aneurisma de aorta abdominal (homens 65-75 anos; somente se já fumou)
    if sexo == 'masculino' and 65 <= idade <= 75:
        status = tabagismo.get('status', 'nunca_fumou')
        if status in ('fumante_atual', 'ex_fumante'):
            recomendacoes.append({
                'titulo': 'Ultrassom de Aorta Abdominal',
                'descricao': 'Ultrassom uma vez na vida em homens 65–75 anos que fumaram (ever smokers)',
                'prioridade': 'media',
                'categoria': 'rastreamento_cardiovascular',
                'referencia': 'USPSTF 2019 Grau B'
            })
    
    # Hipertensão (todos os adultos ≥18 anos)
    if idade >= 18:
        recomendacoes.append({
            'titulo': 'Medida da Pressão Arterial',
            'descricao': 'Aferição no consultório com MAPA se alterada',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cardiovascular',
            'referencia': 'USPSTF Grau A'
        })
    
    return recomendacoes

def get_population_specific_recommendations(idade, sexo, comorbidades):
    """Rastreamentos específicos por população"""
    recomendacoes = []
    
    # HIV - todos 15-65 anos
    if 15 <= idade <= 65:
        recomendacoes.append({
            'titulo': 'Teste HIV',
            'descricao': 'Rastreamento de HIV pelo menos uma vez na vida',
            'prioridade': 'alta',
            'categoria': 'rastreamento_ist',
            'referencia': 'USPSTF Grau A'
        })
    
    # Sífilis - populações de risco
    if idade >= 15:
        recomendacoes.append({
            'titulo': 'Teste de Sífilis',
            'descricao': 'VDRL/RPR se risco aumentado (múltiplos parceiros, HSH, HIV+)',
            'prioridade': 'media',
            'categoria': 'rastreamento_ist',
            'referencia': 'USPSTF Grau A'
        })
    
    # Gonorreia e Clamídia - mulheres jovens
    if sexo == 'feminino' and idade <= 24:
        recomendacoes.append({
            'titulo': 'Rastreamento Gonorreia/Clamídia',
            'descricao': 'Teste anual se sexualmente ativa',
            'prioridade': 'alta',
            'categoria': 'rastreamento_ist',
            'referencia': 'USPSTF Grau B'
        })
    elif sexo == 'feminino' and idade >= 25:
        recomendacoes.append({
            'titulo': 'Rastreamento Gonorreia/Clamídia',
            'descricao': 'Teste se risco aumentado (múltiplos parceiros, novo parceiro)',
            'prioridade': 'media',
            'categoria': 'rastreamento_ist',
            'referencia': 'USPSTF Grau B'
        })
    
    # Hepatite C - todos 18-79 anos
    if 18 <= idade <= 79:
        recomendacoes.append({
            'titulo': 'Teste Hepatite C',
            'descricao': 'Anti-HCV pelo menos uma vez na vida',
            'prioridade': 'alta',
            'categoria': 'rastreamento_hepatite',
            'referencia': 'USPSTF Grau B'
        })
    
    # Depressão - todos adultos
    if idade >= 18:
        recomendacoes.append({
            'titulo': 'Rastreamento de Depressão',
            'descricao': 'PHQ-2 ou PHQ-9 anual',
            'prioridade': 'alta',
            'categoria': 'saude_mental',
            'referencia': 'USPSTF Grau B'
        })
    
    # Ansiedade - adultos 19-64 anos
    if 19 <= idade <= 64:
        recomendacoes.append({
            'titulo': 'Rastreamento de Ansiedade',
            'descricao': 'GAD-2 ou GAD-7 conforme indicação clínica',
            'prioridade': 'media',
            'categoria': 'saude_mental',
            'referencia': 'USPSTF Grau B'
        })
    
    # Abuso de álcool - todos adultos
    if idade >= 18:
        recomendacoes.append({
            'titulo': 'Rastreamento Abuso de Álcool',
            'descricao': 'AUDIT-C ou questionário similar',
            'prioridade': 'media',
            'categoria': 'uso_substancias',
            'referencia': 'USPSTF Grau B'
        })
    
    # Diabetes - adultos com fatores de risco
    if idade >= 35 or any(c in comorbidades for c in ['hipertensao', 'obesidade']):
        recomendacoes.append({
            'titulo': 'Rastreamento de Diabetes',
            'descricao': 'Glicemia de jejum, HbA1c ou TOTG a cada 3 anos',
            'prioridade': 'alta',
            'categoria': 'rastreamento_metabolico',
            'referencia': 'USPSTF Grau B'
        })
    
    return recomendacoes

def get_comorbidity_recommendations(comorbidades):
    """Recomendações baseadas em comorbidades"""
    recomendacoes = []
    
    if 'diabetes_tipo_2' in comorbidades:
        recomendacoes.extend([
            {
                'titulo': 'HbA1c',
                'descricao': 'Hemoglobina glicada a cada 3-6 meses',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_diabetes',
                'referencia': 'ADA 2024'
            },
            {
                'titulo': 'Microalbuminúria',
                'descricao': 'Relação albumina/creatinina urinária anual',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_diabetes',
                'referencia': 'ADA 2024'
            },
            {
                'titulo': 'Fundoscopia',
                'descricao': 'Exame de fundo de olho anual',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_diabetes',
                'referencia': 'ADA 2024'
            },
            {
                'titulo': 'Perfil Lipídico',
                'descricao': 'Colesterol total, HDL, LDL e triglicérides anual',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_diabetes',
                'referencia': 'ADA 2024'
            }
        ])
    
    if 'hipertensao' in comorbidades:
        recomendacoes.extend([
            {
                'titulo': 'Eletrólitos e Creatinina',
                'descricao': 'Sódio, potássio e creatinina anual',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_hipertensao',
                'referencia': 'AHA/ACC 2017'
            },
            {
                'titulo': 'Eletrocardiograma',
                'descricao': 'ECG para avaliação de hipertrofia ventricular',
                'prioridade': 'media',
                'categoria': 'acompanhamento_hipertensao',
                'referencia': 'AHA/ACC 2017'
            }
        ])
    
    if 'doenca_renal_cronica' in comorbidades:
        recomendacoes.extend([
            {
                'titulo': 'eGFR e Albuminúria',
                'descricao': 'Taxa de filtração glomerular e relação albumina/creatinina',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_drc',
                'referencia': 'KDIGO 2024'
            },
            {
                'titulo': 'Hemograma e Eletrólitos',
                'descricao': 'Hemograma, eletrólitos, cálcio, fósforo e PTH',
                'prioridade': 'alta',
                'categoria': 'acompanhamento_drc',
                'referencia': 'KDIGO 2024'
            }
        ])
    
    if 'dislipidemia' in comorbidades:
        recomendacoes.append({
            'titulo': 'Perfil Lipídico de Controle',
            'descricao': 'Colesterol total, HDL, LDL e triglicérides',
            'prioridade': 'alta',
            'categoria': 'acompanhamento_dislipidemia',
            'referencia': 'AHA/ACC 2018'
        })
    
    return recomendacoes

def get_family_history_recommendations(historia_familiar, idade, sexo):
    """Recomendações baseadas em história familiar"""
    recomendacoes = []
    
    if 'cancer_colorretal' in historia_familiar:
        if idade >= 40:
            recomendacoes.append({
                'titulo': 'Colonoscopia Precoce',
                'descricao': 'Colonoscopia a cada 5 anos (início 10 anos antes do caso familiar)',
                'prioridade': 'alta',
                'categoria': 'rastreamento_cancer_familiar',
                'referencia': 'MSTF 2017'
            })
    
    if 'cancer_mama' in historia_familiar and sexo == 'feminino':
        if idade >= 25:
            recomendacoes.append({
                'titulo': 'Rastreamento Intensivo Câncer de Mama',
                'descricao': 'Mamografia anual e considerar RM. Avaliar aconselhamento genético BRCA',
                'prioridade': 'alta',
                'categoria': 'rastreamento_cancer_familiar',
                'referencia': 'NCCN 2024'
            })
    
    if 'cancer_ovario' in historia_familiar and sexo == 'feminino':
        recomendacoes.append({
            'titulo': 'Aconselhamento Genético',
            'descricao': 'Avaliação para mutações BRCA1/BRCA2',
            'prioridade': 'alta',
            'categoria': 'aconselhamento_genetico',
            'referencia': 'USPSTF Grau B'
        })
    
    return recomendacoes

def get_smoking_recommendations(tabagismo, idade):
    """Recomendações baseadas em tabagismo"""
    recomendacoes = []
    
    status = tabagismo.get('status', 'nunca_fumou')
    macos_ano = tabagismo.get('macos_ano', 0)
    
    # Rastreamento de câncer de pulmão
    if 50 <= idade <= 80 and macos_ano >= 20:
        if status in ['fumante_atual', 'ex_fumante']:
            recomendacoes.append({
                'titulo': 'Tomografia de Tórax',
                'descricao': f'TC de baixa dose anual ({macos_ano} maços-ano)',
                'prioridade': 'alta',
                'categoria': 'rastreamento_cancer',
                'referencia': 'USPSTF Grau B'
            })
    
    # Cessação do tabagismo
    if status == 'fumante_atual':
        recomendacoes.append({
            'titulo': 'Cessação do Tabagismo',
            'descricao': 'Aconselhamento e suporte farmacológico',
            'prioridade': 'alta',
            'categoria': 'prevencao',
            'referencia': 'USPSTF Grau A'
        })
    
    return recomendacoes

def get_vaccination_recommendations(idade, comorbidades):
    """Recomendações de vacinação"""
    recomendacoes = []
    
    # Influenza - anual para todos
    recomendacoes.append({
        'titulo': 'Vacina Influenza',
        'descricao': 'Vacina anual (alta dose se ≥65 anos)',
        'prioridade': 'alta',
        'categoria': 'vacinacao',
        'referencia': 'CDC 2024'
    })
    
    # COVID-19
    recomendacoes.append({
        'titulo': 'Vacina COVID-19',
        'descricao': 'Vacina 2024-2025 conforme CDC',
        'prioridade': 'alta',
        'categoria': 'vacinacao',
        'referencia': 'CDC 2024'
    })
    
    # Pneumocócica
    if idade >= 65 or any(c in comorbidades for c in ['diabetes_tipo_2', 'cardiopatia', 'doenca_renal_cronica']):
        recomendacoes.append({
            'titulo': 'Vacina Pneumocócica',
            'descricao': 'PCV20 ou PCV15 + PPSV23',
            'prioridade': 'alta',
            'categoria': 'vacinacao',
            'referencia': 'CDC 2024'
        })
    
    # Herpes Zóster
    if idade >= 50:
        recomendacoes.append({
            'titulo': 'Vacina Herpes Zóster',
            'descricao': 'Vacina recombinante (RZV) - 2 doses',
            'prioridade': 'media',
            'categoria': 'vacinacao',
            'referencia': 'CDC 2024'
        })
    
    # Hepatite B
    if idade < 60 or 'diabetes_tipo_2' in comorbidades:
        recomendacoes.append({
            'titulo': 'Vacina Hepatite B',
            'descricao': 'Série completa se não vacinado',
            'prioridade': 'media',
            'categoria': 'vacinacao',
            'referencia': 'CDC 2024'
        })
    
    # Tétano/Difteria
    recomendacoes.append({
        'titulo': 'Vacina Tétano/Difteria',
        'descricao': 'Reforço Td ou Tdap a cada 10 anos',
        'prioridade': 'media',
        'categoria': 'vacinacao',
        'referencia': 'CDC 2024'
    })
    
    return recomendacoes

def remove_duplicates_and_sort(recomendacoes):
    """Remove duplicatas e ordena por prioridade"""
    # Remover duplicatas com base em (titulo,categoria,referencia); manter maior prioridade
    def _prio(rec):
        return {'alta': 1, 'media': 2, 'baixa': 3}.get(rec.get('prioridade','baixa'), 4)
    seen = {}
    for rec in recomendacoes:
        key = (rec.get('titulo','').strip().lower(), rec.get('categoria',''), rec.get('referencia',''))
        if key in seen:
            if _prio(rec) < _prio(seen[key]):
                if 'status' in seen[key] and 'status' not in rec:
                    rec['status'] = seen[key]['status']
                seen[key] = rec
            else:
                if 'status' in rec and 'status' not in seen[key]:
                    seen[key]['status'] = rec['status']
        else:
            seen[key] = rec
    unique_recomendacoes = list(seen.values())

    priority_order = {'alta': 1, 'media': 2, 'baixa': 3}
    unique_recomendacoes.sort(key=lambda x: priority_order.get(x.get('prioridade'), 4))
    return unique_recomendacoes

