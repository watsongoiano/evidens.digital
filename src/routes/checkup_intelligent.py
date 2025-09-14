from flask import Blueprint, request, jsonify
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.utils.analytics import analytics
from src.utils.reference_links import build_reference_links, build_reference_html

checkup_intelligent_bp = Blueprint('checkup_intelligent', __name__)

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

def _parse_smoking_status_intelligent(tabagismo, data=None):
    """
    Normaliza tabagismo vindo como string, dict ou campos achatados para (status, macos_ano).
    Similar ao helper de checkup.py mas adaptado para checkup_intelligent.
    """
    status = 'nunca_fumou'
    macos = 0
    
    try:
        # Priorizar dict tabagismo se disponível
        if isinstance(tabagismo, dict):
            status = tabagismo.get('status') or tabagismo.get('estado') or 'nunca_fumou'
            macos_value = tabagismo.get('macos_ano') or tabagismo.get('pack_years') or 0
            try:
                macos = int(macos_value) if macos_value else 0
            except (ValueError, TypeError):
                macos = 0
        elif isinstance(tabagismo, str):
            status = tabagismo
        
        # Verificar campos achatados no payload principal se data fornecido
        if data:
            flat_status = data.get('tabagismo_status')
            flat_macos = data.get('tabagismo_macos_ano')
            
            if flat_status:
                status = flat_status
            if flat_macos:
                try:
                    macos = int(flat_macos) if flat_macos else 0
                except (ValueError, TypeError):
                    macos = 0
                    
    except Exception:
        # Em caso de qualquer erro, usar valores padrão seguros
        status = 'nunca_fumou'
        macos = 0
    
    # Normalizar status
    if isinstance(status, str):
        status = status.replace('-', '_').lower().strip()
        if status == 'fumante':
            status = 'fumante_atual'
        elif status == 'ex_fumante' or status == 'ex-fumante':
            status = 'ex_fumante'
        elif status not in ['fumante_atual', 'ex_fumante', 'nunca_fumou']:
            status = 'nunca_fumou'
    else:
        status = 'nunca_fumou'
        
    return status, macos

@checkup_intelligent_bp.route('/checkup-intelligent', methods=['POST'])
def generate_intelligent_recommendations():
    try:
        data = request.json

        # Defesa: garantir payload JSON válido
        if not isinstance(data, dict):
            return jsonify({'error': 'JSON inválido'}), 400
        
        # Extrair dados do formulário com defaults seguros
        idade = int(data.get('idade', 0)) if data.get('idade') else 0
        sexo = data.get('sexo', '')
        pais = data.get('pais', 'BR')  # Padrão Brasil
        comorbidades = data.get('comorbidades', []) if data.get('comorbidades') else []
        historia_familiar = data.get('historia_familiar', []) if data.get('historia_familiar') else []
        
        # Processar tabagismo de forma robusta
        tabagismo_raw = data.get('tabagismo', 'nunca_fumou')
        macos_ano_raw = data.get('macos_ano', 0)
        
        # Normalizar tabagismo usando helper resiliente
        tabagismo, macos_ano = _parse_smoking_status_intelligent(tabagismo_raw, data)
        
        # Se macos_ano não foi extraído do tabagismo, usar o campo direto
        if macos_ano == 0 and macos_ano_raw:
            try:
                macos_ano = int(macos_ano_raw) if macos_ano_raw else 0
            except (ValueError, TypeError):
                macos_ano = 0
        
        print(f"DEBUG: tabagismo normalizado = {tabagismo}, macos_ano = {macos_ano}")
        
        outras_comorbidades = data.get('outras_comorbidades', '').lower() if data.get('outras_comorbidades') else ''
        outras_condicoes_familiares = data.get('outras_condicoes_familiares', '').lower() if data.get('outras_condicoes_familiares') else ''
        medicacoes_uso_continuo = data.get('medicacoes_uso_continuo', '').lower() if data.get('medicacoes_uso_continuo') else ''
        exames_anteriores = data.get('exames_anteriores', []) if data.get('exames_anteriores') else []
        
        recommendations = []
        alerts = []
        

        def should_have_received_single_dose(keyword, previous_exams):
            """Return False (do NOT recommend) if a prior dose/exam with keyword exists."""
            if not previous_exams:
                return True, None
                
            for exam in previous_exams or []:
                if not exam or not isinstance(exam, dict):
                    continue
                exam_name = exam.get('name', '')
                if exam_name and keyword.lower() in exam_name.lower():
                    return False, f"Já realizado anteriormente"
            return True, None
        
        # Intervalos recomendados (em dias)
        intervals = {
            'HbA1c': 180,  # 6 meses para diabéticos
            'Perfil Lipídico': 1825,  # 5 anos
            'Creatinina': 365,  # 1 ano
            'Mamografia': 730,  # 2 anos
            'Colonoscopia': 3650,  # 10 anos
            'Citologia Cervical': 1095,  # 3 anos
            'Densitometria': 730,  # 2 anos
            'PSA': 365,  # 1 ano
        }
        
        # Função para verificar se deve recomendar exame
        def should_recommend_exam(exam_name, previous_exams, interval_days):
            for exam in previous_exams:
                if not exam or not isinstance(exam, dict):
                    continue
                    
                exam_name_field = exam.get('name', '')
                exam_date_field = exam.get('date')
                
                if not exam_name_field or exam_name.lower() not in exam_name_field.lower():
                    continue
                    
                # Usar função robusta de parsing de data
                exam_date = parse_date_ymd(exam_date_field)
                
                if exam_date is None:
                    # Se não há data válida, recomendar exame
                    return True, "Sem data anterior válida"
                
                days_since = (datetime.now() - exam_date).days
                
                if days_since < interval_days:
                    return False, f"Último exame há {days_since} dias"
                elif days_since > interval_days + 30:  # 30 dias de tolerância
                    return True, f"Em atraso - último exame há {days_since} dias"
                else:
                    return True, f"Devido - último exame há {days_since} dias"
            
            return True, None
        
        def calculate_days_since_exam(exam_date_str):
            exam_date = parse_date_ymd(exam_date_str)
            if exam_date:
                return (datetime.now() - exam_date).days
            return None
        
        # Mapeamento de condições para exames específicos
        condition_mapping = {
            'dpoc': {
                'exames': ['Espirometria'],
                'descricoes': ['Espirometria anual para acompanhamento de DPOC'],
                'referencias': ['GOLD 2024']
            },
            'hipotireoidismo': {
                'exames': ['TSH'],
                'descricoes': ['TSH anual para acompanhamento de hipotireoidismo'],
                'referencias': ['ATA 2014']
            },
            'depressão': {
                'exames': ['PHQ-9'],
                'descricoes': ['PHQ-9 semestral para acompanhamento de depressão'],
                'referencias': ['USPSTF Grau B']
            },
            'artrite reumatoide': {
                'exames': ['VHS', 'PCR'],
                'descricoes': ['VHS e PCR para monitoramento de atividade inflamatória'],
                'referencias': ['ACR 2021']
            }
        }
        
        # Processar outras comorbidades
        for condition, mapping in condition_mapping.items():
            if condition in outras_comorbidades:
                for i, exam in enumerate(mapping['exames']):
                    should_rec, status = should_recommend_exam(exam, exames_anteriores, 365)
                    if should_rec:
                        rec = {
                            'titulo': exam,
                            'descricao': mapping['descricoes'][i],
                            'prioridade': 'media',
                            'referencia': mapping['referencias'][0],
                            'categoria': 'laboratorial'
                        }
                        if status:
                            rec['status'] = status
                        recommendations.append(rec)
        
        # === EXAMES LABORATORIAIS ===
        
        # HIV - USPSTF 2019 Grau A
        if 15 <= idade <= 65:
            should_rec, status = should_recommend_exam('HIV', exames_anteriores, 1095)  # 3 anos
            if should_rec:
                rec = {
                    'titulo': 'Anti-HIV 1 e 2, soro',
                    'descricao': 'Rastreamento de HIV - Teste antígeno/anticorpo (4ª geração)',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2019 Grau A',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Hepatite C - USPSTF 2020
        if 18 <= idade <= 79:
            should_rec, status = should_recommend_exam('Hepatite C', exames_anteriores, 1095)  # 3 anos
            if should_rec:
                rec = {
                    'titulo': 'Anti-HCV IgG, soro',
                    'descricao': 'Anti-HCV - Rastreamento universal 18-79 anos',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2020 Grau B',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Tuberculose Latente - USPSTF 2023 Grau B
        tb_risk_factors = [
            'nascido em país alta prevalência', 'profissional de saúde', 'profissional saúde',
            'imunossuprimido', 'hiv', 'diabetes', 'doença renal crônica',
            'contactante tuberculose', 'prisão', 'abrigo', 'asiático', 'africano'
        ]
        has_tb_risk = any(factor in outras_comorbidades for factor in tb_risk_factors)
        has_tb_comorbid = any(comorbid in ['diabetes_tipo_2', 'doenca_renal_cronica'] for comorbid in comorbidades)
        
        if has_tb_risk or has_tb_comorbid:
            should_rec_tb, status_tb = should_recommend_exam('Tuberculose Latente', exames_anteriores, 365)
            if should_rec_tb:
                rec = {
                    'titulo': 'Rastreamento Tuberculose Latente',
                    'descricao': 'IGRA ou TST - Populações de risco aumentado',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2023 Grau B',
                    'categoria': 'laboratorial'
                }
                if status_tb:
                    rec['status'] = status_tb
                recommendations.append(rec)
        
        # Rastreamento Diabetes/Pré-diabetes - USPSTF 2021 + ADA 2024
        diabetes_screening_needed = False
        diabetes_reason = ""
        
        # USPSTF: Adultos 35-70 anos com sobrepeso/obesidade
        if 35 <= idade <= 70:
            has_overweight = any(condition in outras_comorbidades for condition in 
                               ['sobrepeso', 'obesidade', 'bmi', 'imc'])
            if 'obesidade' in comorbidades or has_overweight:
                diabetes_screening_needed = True
                diabetes_reason = "USPSTF 2021: 35-70 anos com sobrepeso/obesidade"
        
        # ADA: Fatores de risco adicionais
        ada_risk_factors = [
            'familiar diabetes', 'parente diabetes', 'história familiar diabetes',
            'afro', 'latino', 'nativo americano', 'asiático', 'ilhéu pacífico',
            'cardiopatia', 'doença cardiovascular', 'infarto', 'avc',
            'hipertensão', 'pressão alta',
            'hdl baixo', 'triglicérides alto', 'dislipidemia',
            'ovário policístico', 'sop',
            'sedentário', 'inatividade física',
            'acantose nigricans', 'resistência insulina'
        ]
        
        has_ada_risk = any(factor in outras_comorbidades for factor in ada_risk_factors)
        has_ada_comorbid = any(comorbid in ['hipertensao', 'dislipidemia', 'cardiopatia'] for comorbid in comorbidades)
        
        if has_ada_risk or has_ada_comorbid:
            if not diabetes_screening_needed:
                diabetes_screening_needed = True
                diabetes_reason = "ADA 2024: Fatores de risco para diabetes"
        
        # Rastreamento universal ≥35 anos (ADA)
        if idade >= 35 and not diabetes_screening_needed:
            diabetes_screening_needed = True
            diabetes_reason = "ADA 2024: Rastreamento universal ≥35 anos"
        
        # Implementar recomendação se necessário
        if diabetes_screening_needed and 'diabetes_tipo_2' not in comorbidades:
            should_rec_glic, status_glic = should_recommend_exam('Glicemia de Jejum', exames_anteriores, 1095)  # 3 anos
            
            if should_rec_glic:
                # Adicionar os três exames separadamente
                rec1 = {
                    'titulo': 'TOTG-75g, soro',
                    'descricao': f'Teste de tolerância oral à glicose - {diabetes_reason}',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021 Grau B / ADA 2024',
                    'categoria': 'laboratorial'
                }
                if status_glic:
                    rec1['status'] = status_glic
                recommendations.append(rec1)
                
                rec2 = {
                    'titulo': 'HbA1C, soro',
                    'descricao': f'Hemoglobina glicada - {diabetes_reason}',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021 Grau B / ADA 2024',
                    'categoria': 'laboratorial'
                }
                if status_glic:
                    rec2['status'] = status_glic
                recommendations.append(rec2)
                
                rec3 = {
                    'titulo': 'Glicemia de jejum de 8 horas, soro',
                    'descricao': f'Glicemia de jejum - {diabetes_reason}',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021 Grau B / ADA 2024',
                    'categoria': 'laboratorial'
                }
                if status_glic:
                    rec3['status'] = status_glic
                recommendations.append(rec3)
        
        # Sífilis - USPSTF 2022 Grau A
        syphilis_risk_factors = [
            'hsh', 'homens que fazem sexo com homens', 'múltiplos parceiros',
            'udi', 'usuário de drogas injetáveis', 'trabalho sexual', 'profissional do sexo',
            'hiv', 'ist', 'infecção sexualmente transmissível', 'prisão', 'encarceramento',
            'militar', 'serviço militar'
        ]
        has_syphilis_risk = any(factor in outras_comorbidades for factor in syphilis_risk_factors)
        
        if has_syphilis_risk:
            should_rec, status = should_recommend_exam('Sífilis', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'VDRL, soro',
                    'descricao': 'VDRL/RPR - Populações de alto risco para infecção',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2022 Grau A',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Hepatite B - USPSTF 2020 Grau B
        hepb_risk_factors = [
            'nascido em país alta prevalência', 'ásia', 'áfrica', 'pacífico',
            'hiv', 'hemodiálise', 'imunossuprimido', 'transplante',
            'udi', 'usuário de drogas injetáveis', 'múltiplos parceiros',
            'hsh', 'homens que fazem sexo com homens', 'profissional saúde',
            'contactante hepatite b', 'parceiro hepatite b'
        ]
        has_hepb_risk = any(factor in outras_comorbidades for factor in hepb_risk_factors)
        
        if has_hepb_risk:
            should_rec, status = should_recommend_exam('Hepatite B', exames_anteriores, 1095)  # 3 anos
            if should_rec:
                rec = {
                    'titulo': 'HBsAg, soro',
                    'descricao': 'HBsAg - Populações de alto risco para infecção',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2020 Grau B',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Gonorreia/Clamídia - Mulheres jovens
        if sexo == 'feminino' and idade <= 25:
            should_rec, status = should_recommend_exam('Gonorreia/Clamídia', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Pesquisa de Chlamydia trachomatis e Neisseria gonorrhoeae, urina',
                    'descricao': 'Rastreamento anual em mulheres ≤25 anos sexualmente ativas',
                    'prioridade': 'media',
                    'referencia': 'USPSTF Grau B',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Diabetes - HbA1c para diabéticos
        if 'diabetes_tipo_2' in comorbidades:
            should_rec, status = should_recommend_exam('HbA1c', exames_anteriores, intervals['HbA1c'])
            if should_rec:
                rec = {
                    'titulo': 'HbA1c',
                    'descricao': 'Hemoglobina glicada a cada 3-6 meses',
                    'prioridade': 'alta',
                    'referencia': 'ADA 2024',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
            
            # Microalbuminúria para diabéticos
            should_rec, status = should_recommend_exam('Microalbuminúria', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Relação albumina/creatinina, urina',
                    'descricao': 'Relação albumina/creatinina urinária anual',
                    'prioridade': 'alta',
                    'referencia': 'ADA 2024',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Dislipidemia
        if 'dislipidemia' in comorbidades or idade >= 40:
            should_rec, status = should_recommend_exam('Perfil Lipídico', exames_anteriores, intervals['Perfil Lipídico'])
            if should_rec:
                rec = {
                    'titulo': 'Colesterol total e frações, soro',
                    'descricao': 'Colesterol total, HDL, LDL e triglicérides',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2019',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)

        # ===== BIOMARQUEURS LIPIDIQUES AVANCÉS (ASCVD Guidelines) =====
        def has_risk_enhancers():
            """Verificar presença de fatores de melhoria do risco ASCVD"""
            enhancers = []
            
            # História familiar de ASCVD prematuro
            if any(hf in historia_familiar for hf in ['cardiopatia']):
                enhancers.append("História familiar de cardiopatia")
            
            # Doença renal crônica
            if 'doenca_renal_cronica' in comorbidades:
                enhancers.append("Doença renal crônica")
            
            # Síndrome metabólica (aproximação: diabetes + hipertensão + obesidade)
            metabolic_conditions = sum([
                'diabetes_tipo_2' in comorbidades,
                'hipertensao' in comorbidades or 'has_resistente' in comorbidades,
                'obesidade' in comorbidades
            ])
            if metabolic_conditions >= 2:
                enhancers.append("Síndrome metabólica")
            
            # Condições inflamatórias
            inflammatory_conditions = ['artrite', 'reumat', 'psoria', 'lupus', 'hiv']
            if any(cond in outras_comorbidades for cond in inflammatory_conditions):
                enhancers.append("Condições inflamatórias")
            
            # Tabagismo atual
            if tabagismo == 'fumante_atual':
                enhancers.append("Tabagismo atual")
            
            return enhancers

        def get_ascvd_risk_from_prevent():
            """Obter o risco ASCVD calculado pelo PREVENT (passado via formulário)"""
            try:
                # Obter o valor do campo hidden do formulário
                prevent_risk_str = data.get('prevent_risk_10yr', '')
                print(f"DEBUG: prevent_risk_str = '{prevent_risk_str}'")
                
                if prevent_risk_str and prevent_risk_str.strip():
                    # Converter para float
                    prevent_risk = float(prevent_risk_str)
                    print(f"DEBUG: prevent_risk convertido = {prevent_risk}")
                    
                    # Validar que está em um range razoável (0-100%)
                    if 0 <= prevent_risk <= 100:
                        print(f"DEBUG: Retornando risco válido = {prevent_risk}")
                        return prevent_risk
                    else:
                        print(f"DEBUG: Risco PREVENT fora do range válido: {prevent_risk}")
                        return None
                else:
                    print("DEBUG: Campo prevent_risk_10yr vazio ou não encontrado")
                    return None
                    
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Erro ao converter risco PREVENT: {e}")
                return None

        
        # Doença Renal Crônica
        if 'doenca_renal_cronica' in comorbidades:
            should_rec, status = should_recommend_exam('Creatinina', exames_anteriores, intervals['Creatinina'])
            if should_rec:
                rec = {
                    'titulo': 'Creatinina e eGFR, soro',
                    'descricao': 'Função renal e taxa de filtração glomerular',
                    'prioridade': 'alta',
                    'referencia': 'KDIGO 2024',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        
        # Aneurisma de Aorta Abdominal – homens 65–75 que já fumaram (USPSTF 2019)
        if sexo == 'masculino' and 65 <= idade <= 75 and tabagismo in ('fumante_atual','ex_fumante'):
            ok, status = should_recommend_exam('Aorta Abdominal', exames_anteriores, 36500)
            if ok:
                rec = {
                    'titulo': 'Ultrassom de Aorta Abdominal',
                    'descricao': 'Triagem única em homens 65–75 que fumaram (ever smokers)',
                    'prioridade': 'media',
                    'referencia': 'USPSTF 2019 Grau B',
                    'categoria': 'rastreamento'
                }
                if status: rec['status'] = status
                recommendations.append(rec)
        # === RASTREAMENTO DE CÂNCER ===
        
        # Mamografia - USPSTF 2024
        if sexo == 'feminino':
            if 40 <= idade <= 74:
                should_rec, status = should_recommend_exam('Mamografia', exames_anteriores, intervals['Mamografia'])
                if should_rec:
                    # Determinar prioridade baseada na idade - USPSTF 2024
                    priority = 'alta'
                    grade = 'B'
                    desc = 'Mamografia bienal (40-74 anos)'
                    
                    # História familiar pode antecipar
                    if 'cancer_mama' in historia_familiar and idade >= 40:
                        desc = f'{desc} - História familiar positiva'
                    
                    rec = {
                        'titulo': 'Mamografia Digital - Bilateral',
                        'descricao': desc,
                        'prioridade': priority,
                        'referencia': f'USPSTF 2024 Grau {grade}',
                        'categoria': 'rastreamento'
                    }
                    if status:
                        rec['status'] = status
                    recommendations.append(rec)
            elif idade >= 75:
                # USPSTF Grau I - Evidência insuficiente
                should_rec, status = should_recommend_exam('Mamografia', exames_anteriores, intervals['Mamografia'])
                if should_rec:
                    rec = {
                        'titulo': 'Mamografia Digital - Bilateral',
                        'descricao': 'Mamografia ≥75 anos - Decisão individualizada (evidência insuficiente)',
                        'prioridade': 'baixa',
                        'referencia': 'USPSTF 2024 Grau I',
                        'categoria': 'rastreamento'
                    }
                    if status:
                        rec['status'] = status
                    recommendations.append(rec)
        
        # Avaliação de Risco BRCA1/2 - USPSTF 2019 Grau B
        if sexo == 'feminino':
            brca_family_history = [
                'câncer mama', 'câncer ovário', 'câncer tuba', 'câncer peritoneal',
                'brca1', 'brca2', 'mutação brca', 'síndrome hereditário',
                'câncer mama masculino', 'câncer mama homem'
            ]
            
            # Verificar história familiar
            has_brca_family = any(factor in outras_condicoes_familiares for factor in brca_family_history)
            has_brca_checkbox = 'cancer_mama' in historia_familiar or 'cancer_ovario' in historia_familiar
            
            if has_brca_family or has_brca_checkbox:
                should_rec, status = should_recommend_exam('Avaliação BRCA', exames_anteriores, 1825)  # 5 anos
                if should_rec:
                    rec = {
                        'titulo': 'Avaliação de Risco BRCA1/2',
                        'descricao': 'Ferramenta de avaliação de risco familiar para aconselhamento genético',
                        'prioridade': 'alta',
                        'referencia': 'USPSTF 2019 Grau B',
                        'categoria': 'outras'
                    }
                    if status:
                        rec['status'] = status
                    recommendations.append(rec)
        
        # Colonoscopia - USPSTF 2021
        idade_inicio_colo = 45
        if 'cancer_colorretal' in historia_familiar:
            idade_inicio_colo = 40
        
        if 45 <= idade <= 85:
            should_rec, status = should_recommend_exam('Colonoscopia', exames_anteriores, intervals['Colonoscopia'])
            if should_rec:
                # Determinar prioridade baseada na idade - USPSTF 2021
                if 45 <= idade <= 49:
                    priority = 'alta'
                    grade = 'B'
                    desc = 'Colonoscopia a cada 10 anos (45-49 anos)'
                elif 50 <= idade <= 75:
                    priority = 'alta'
                    grade = 'A'
                    desc = 'Colonoscopia a cada 10 anos (50-75 anos)'
                elif 76 <= idade <= 85:
                    priority = 'media'
                    grade = 'C'
                    desc = 'Colonoscopia (76-85 anos) - Decisão individualizada'
                
                # História familiar pode antecipar
                if 'cancer_colorretal' in historia_familiar and idade >= 40:
                    desc = f'{desc} - História familiar positiva (início aos 40 anos)'
                
                rec = {
                    'titulo': 'Colonoscopia de Rastreio com ou sem biopsia',
                    'descricao': desc,
                    'prioridade': priority,
                    'referencia': f'USPSTF 2021 Grau {grade}',
                    'categoria': 'rastreamento'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Citologia Cervical - Recommendations by age
        if sexo == 'feminino' and 21 <= idade <= 65:
            if 21 <= idade <= 29:
                # 21-29: Pap (citologia) every 3 years
                should_rec, status = should_recommend_exam('Citologia Cervical', exames_anteriores, intervals['Citologia Cervical'])
                if should_rec:
                    rec = {
                        'titulo': 'Citologia oncótica (Papanicolaou)',
                        'descricao': 'Papanicolaou a cada 3 anos (21-29 anos)',
                        'prioridade': 'alta',
                        'referencia': 'USPSTF Grau A',
                        'categoria': 'rastreamento'
                    }
                    if status:
                        rec['status'] = status
                    recommendations.append(rec)
            elif 30 <= idade <= 65:
                # 30-65: HPV primary test every 5 years (use 1825 days = 5 years)
                should_rec, status = should_recommend_exam('Teste de HPV', exames_anteriores, 1825)
                if should_rec:
                    rec = {
                        'titulo': 'Teste de HPV (primário)',
                        'descricao': 'Teste de HPV primário a cada 5 anos (30-65 anos)',
                        'prioridade': 'alta',
                        'referencia': 'USPSTF Grau A',
                        'categoria': 'rastreamento'
                    }
                    if status:
                        rec['status'] = status
                    recommendations.append(rec)
        
        # PSA
        if sexo == 'masculino' and 50 <= idade <= 70:
            should_rec, status = should_recommend_exam('PSA', exames_anteriores, intervals['PSA'])
            if should_rec:
                rec = {
                    'titulo': 'PSA total, soro',
                    'descricao': 'Antígeno prostático específico (50-70 anos)',
                    'prioridade': 'media',
                    'referencia': 'USPSTF Grau C',
                    'categoria': 'rastreamento'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Câncer de Pulmão
        if tabagismo in ['fumante_atual', 'ex_fumante'] and macos_ano >= 20 and 50 <= idade <= 80:
            should_rec, status = should_recommend_exam('TC Tórax', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Tomografia computadorizada de tórax, baixa dose',
                    'descricao': f'Rastreamento de câncer de pulmão ({macos_ano} maços-ano)',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF Grau B',
                    'categoria': 'rastreamento'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # === VACINAS        # Outras Recomendações
        if idade >= 18:
            rec_us_carotidas = {
                'titulo': 'US de carótidas (assintomáticos)',
                'descricao': 'Não rastrear estenose em adultos assintomáticos de baixo risco',
                'prioridade': 'baixa',
                'referencia': 'USPSTF 2021 Grau D',
                'categoria': 'outras'
            }
            recommendations.append(rec_us_carotidas)
            
            rec_ca125 = {
                'titulo': 'Rastreamento de câncer de ovário (CA125/US transvaginal)',
                'descricao': 'Não rastrear mulheres assintomáticas de risco habitual',
                'prioridade': 'baixa',
                'referencia': 'USPSTF 2018 Grau D',
                'categoria': 'outras'
            }
            recommendations.append(rec_ca125)
            
            rec_vitamina_d = {
                'titulo': 'Vitamina D sérica de rotina',
                'descricao': 'Evidência insuficiente para rastreio de deficiência em adultos assintomáticos',
                'prioridade': 'baixa',
                'referencia': 'USPSTF 2021 Grau I',
                'categoria': 'outras'
            }
            recommendations.append(rec_vitamina_d)

        # Biomarqueurs avancés baseados no risco ASCVD e guidelines
        print(f"DEBUG: Verificando biomarqueurs - idade = {idade}")
        if idade >= 40 and idade <= 75:
            print("DEBUG: Idade válida para biomarqueurs (40-75)")
            risk_enhancers = has_risk_enhancers()
            ascvd_risk = get_ascvd_risk_from_prevent()  # Integrar com cálculo PREVENT
            
            print(f"DEBUG: risk_enhancers = {risk_enhancers}")
            print(f"DEBUG: ascvd_risk = {ascvd_risk}")
            print(f"DEBUG: comorbidades = {comorbidades}")
            
            # Lógica baseada nas guidelines ASCVD e novas indicações específicas
            recommend_biomarkers = False
            biomarker_priority = 'baixa'
            biomarker_indication = ''
            biomarker_indications = []
            
            # 1. Pacientes com Diabetes Mellitus ou Síndrome Metabólica
            if 'diabetes_tipo_2' in comorbidades:
                print("DEBUG: Diabetes detectado - recomendando biomarqueurs")
                recommend_biomarkers = True
                biomarker_priority = 'alta'
                biomarker_indications.append("Diabetes Mellitus")
            
            # 2. Avaliação de Risco em Pacientes Obesos
            if 'obesidade' in comorbidades:
                print("DEBUG: Obesidade detectada - recomendando biomarqueurs")
                recommend_biomarkers = True
                if biomarker_priority != 'alta':
                    biomarker_priority = 'media'
                biomarker_indications.append("Obesidade")
            
            # 3. Fatores de melhoria do risco ou dislipidemia
            if risk_enhancers or 'dislipidemia' in comorbidades:
                print("DEBUG: Risk enhancers ou dislipidemia detectados - recomendando biomarqueurs")
                recommend_biomarkers = True
                
                if len(risk_enhancers) >= 2:
                    biomarker_priority = 'alta'
                    biomarker_indications.append("Múltiplos fatores de risco")
                elif risk_enhancers:
                    if biomarker_priority != 'alta':
                        biomarker_priority = 'media'
                    biomarker_indications.extend(risk_enhancers[:2])
                elif 'dislipidemia' in comorbidades:
                    if biomarker_priority != 'alta':
                        biomarker_priority = 'media'
                    biomarker_indications.append("Dislipidemia")
            
            # 4. Risco Cardiovascular Intermediário e Borderline (baseado no cálculo PREVENT)
            # CORREÇÃO: Esta condição deve ser INDEPENDENTE das outras
            if ascvd_risk is not None:
                print(f"DEBUG: Avaliando risco ASCVD = {ascvd_risk}")
                if ascvd_risk >= 5 and ascvd_risk < 7.5:
                    # Risco borderline - SEMPRE recomendar biomarqueurs
                    print("DEBUG: Risco borderline detectado - FORÇANDO recomendação de biomarqueurs")
                    recommend_biomarkers = True
                    if biomarker_priority not in ['alta']:
                        biomarker_priority = 'media'
                    biomarker_indications.append(f"Risco Borderline ({ascvd_risk:.1f}%)")
                elif ascvd_risk >= 7.5 and ascvd_risk < 20:
                    # Risco intermediário - SEMPRE recomendar biomarqueurs
                    print("DEBUG: Risco intermediário detectado - FORÇANDO recomendação de biomarqueurs")
                    recommend_biomarkers = True
                    biomarker_priority = 'alta'
                    biomarker_indications.append(f"Risco Intermediário ({ascvd_risk:.1f}%)")
                elif ascvd_risk >= 20:
                    # Risco alto - biomarqueurs menos prioritários pois tratamento já indicado
                    print("DEBUG: Risco alto detectado")
                    if not biomarker_indications:  # Só se não há outras indicações
                        recommend_biomarkers = True
                        biomarker_priority = 'baixa'
                        biomarker_indications.append(f"Alto Risco ({ascvd_risk:.1f}%) - tratamento já indicado")
            else:
                print("DEBUG: ascvd_risk é None - não foi possível calcular")
            
            print(f"DEBUG: recommend_biomarkers = {recommend_biomarkers}")
            print(f"DEBUG: biomarker_priority = {biomarker_priority}")
            print(f"DEBUG: biomarker_indications = {biomarker_indications}")
            
            # Construir indicação final
            if biomarker_indications:
                biomarker_indication = f"Indicações: {', '.join(biomarker_indications)}"

            if recommend_biomarkers:
                print("DEBUG: Adicionando biomarqueurs às recomendações")
                # hsCRP (Proteína C-Reativa de alta sensibilidade)
                rec_hscrp = {
                    'titulo': 'Proteína C-Reativa de alta sensibilidade (hsCRP)',
                    'descricao': 'Marcador inflamatório para refinamento do risco cardiovascular',
                    'prioridade': biomarker_priority,
                    'referencia': 'AHA/ACC 2019 ASCVD Guidelines',
                    'categoria': 'laboratorial',
                    'indicacao': biomarker_indication
                }
                recommendations.append(rec_hscrp)
                print("DEBUG: hsCRP adicionado")

                # Lipoproteína(a) - Lp(a)
                rec_lpa = {
                    'titulo': 'Lipoproteína(a) - Lp(a), soro',
                    'descricao': 'Fator de risco genético independente para doença cardiovascular',
                    'prioridade': biomarker_priority,
                    'referencia': 'AHA/ACC 2019 ASCVD Guidelines',
                    'categoria': 'laboratorial',
                    'indicacao': biomarker_indication
                }
                recommendations.append(rec_lpa)
                print("DEBUG: Lp(a) adicionado")

                # Apolipoproteína B (apoB)
                rec_apob = {
                    'titulo': 'Apolipoproteína B (apoB), soro',
                    'descricao': 'Marcador de partículas aterogênicas para avaliação de risco',
                    'prioridade': biomarker_priority,
                    'referencia': 'AHA/ACC 2019 ASCVD Guidelines',
                    'categoria': 'laboratorial',
                    'indicacao': biomarker_indication
                }
                recommendations.append(rec_apob)
                print("DEBUG: apoB adicionado")

                # Score de Cálcio Coronário (CAC) - para risco borderline e intermediário
                if ascvd_risk is not None and ascvd_risk >= 5:
                    rec_cac = {
                        'titulo': 'Score de Cálcio Coronário (CAC)',
                        'descricao': 'Tomografia computadorizada para quantificação de cálcio coronário',
                        'prioridade': biomarker_priority,
                        'referencia': 'AHA/ACC 2019 ASCVD Guidelines',
                        'categoria': 'imagem',
                        'indicacao': 'Considerar se decisão de tratamento incerta após avaliação inicial'
                    }
                    recommendations.append(rec_cac)
                    print("DEBUG: CAC adicionado")
            else:
                print("DEBUG: Biomarqueurs NÃO recomendados")
        else:
            print(f"DEBUG: Idade {idade} fora da faixa 40-75 para biomarqueurs")
        
        # === VACINAS ===
        # Influenza - Diferenciada por idade
        should_rec, status = should_recommend_exam('Vacina Influenza', exames_anteriores, 365)
        if should_rec:
            if idade >= 65:
                rec = {
                    'titulo': 'HD4V (Vacina p/Influenza de Alta dose - Efluelda®)',
                    'descricao': 'Dose anual\nAplicar em dose única, INTRAMUSCULAR, anualmente. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Arexvy® e Shingrix®; de preferência, aguardar 15 dias de intervalo para vacinação com a QDenga®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
            else:
                rec = {
                    'titulo': 'Vacina Influenza Tetravalente',
                    'descricao': 'Dose anual\nAplicar em dose única, INTRAMUSCULAR, anualmente. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Arexvy® e Shingrix®; de preferência, aguardar 15 dias de intervalo para vacinação com a QDenga®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
            if status:
                rec['status'] = status
            recommendations.append(rec)
        
        # dTpa - Tétano, difteria, coqueluche (adultos)
        should_rec, status = should_recommend_exam('Vacina Tdap', exames_anteriores, 3650)  # 10 anos
        if should_rec:
            rec = {
                'titulo': 'dTpa (Boostrix®/Adacel®)',
                'descricao': '1 dose de reforço a cada 10 anos',
                'prioridade': 'alta',
                'referencia': 'SBIm/ANVISA 2024',
                'categoria': 'vacina'
            }
            if status:
                rec['status'] = status
            recommendations.append(rec)
        
        # RSV – dose única (CDC 2025)
        if idade >= 75 or (50 <= idade <= 74 and (('doenca_renal_cronica' in comorbidades) or ('cardiopatia' in comorbidades) or ('diabetes_tipo_2' in comorbidades))):
            ok, status = should_have_received_single_dose('RSV', exames_anteriores)
            if ok:
                rec = {
                    'titulo': 'Vacina RSV (Arexvy®/Abrysvo®/mResvia®)',
                    'descricao': 'Dose única para adultos elegíveis (≥75 anos; 50–74 com risco). Aplicar preferencialmente antes do outono.',
                    'prioridade': 'alta' if idade >= 75 else 'media',
                    'referencia': 'CDC 2025',
                    'categoria': 'vacina'
                }
                if status: rec['status'] = status
                recommendations.append(rec)

        # Shingrix - Herpes Zóster (RZV)
        if idade >= 50:
            should_rec, status = should_recommend_exam('Vacina Herpes Zóster', exames_anteriores, 7300)
            if should_rec:
                rec = {
                    'titulo': 'Shingrix® (Vacina p/Herpes Zoster recombinada)',
                    'descricao': '2 doses\nAplicar uma dose de 0,5ml, INTRAMUSCULAR e repetir segunda dose após 2 meses. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Efluelda® e Arexvy®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Gardasil 9 - HPV - Papilomavírus humano
        if idade <= 45:
            should_rec, status = should_recommend_exam('Vacina HPV', exames_anteriores, 7300)
            if should_rec:
                rec = {
                    'titulo': 'Gardasil 9® (Vacina Papilomavírus Humano 9-Valente)',
                    'descricao': '3 doses\nAplicar uma dose (0,5ml), INTRAMUSCULAR, no intervalo 0, 2 e 6 meses.',
                    'prioridade': 'alta' if idade <= 26 else 'media',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # VPC15 e VPP23 - Pneumocócicas
        if idade >= 50:
            should_rec, status = should_recommend_exam('Vacina Pneumocócica', exames_anteriores, 1825)
            if should_rec:
                # Adicionar VPC15 primeiro
                rec1 = {
                    'titulo': 'VPC15 (Vaxneuvance®) ou VPC13, 0,5ml',
                    'descricao': '1 dose\nSolicito aplicação, INTRAMUSCULAR, em região deltoideana, em dose única. Obs: Pode ser coadministrada com Shingrix®, Efluelda® e Arexvy®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec1['status'] = status
                recommendations.append(rec1)
                
                # Adicionar VPP23 depois
                rec2 = {
                    'titulo': 'VPP23, 0,5ml',
                    'descricao': '1 dose\nSolicito aplicação, INTRAMUSCULAR, em região deltoideana, seis meses após aplicação de VPC15/VPC13. Obs: Pode ser coadministrada com Shingrix®, Efluelda® e Arexvy®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec2['status'] = status
                recommendations.append(rec2)
        
        # Meningocócica B
        if idade >= 16 and idade <= 65:
            should_rec, status = should_recommend_exam('Vacina Meningocócica B', exames_anteriores, 1825)  # 5 anos
            if should_rec:
                rec = {
                    'titulo': 'Meningocócica B',
                    'descricao': '1 dose\nAplicar em dose única, INTRAMUSCULAR e reforço após 5 anos.',
                    'prioridade': 'media',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Meningocócica ACWY
        if idade >= 16 and idade <= 65:
            should_rec, status = should_recommend_exam('Vacina Meningocócica ACWY', exames_anteriores, 1825)  # 5 anos
            if should_rec:
                rec = {
                    'titulo': 'Meningocócica ACWY (MenQuadfi®)',
                    'descricao': '1 dose\nAplicar em dose única, INTRAMUSCULAR.',
                    'prioridade': 'media',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # === OUTRAS RECOMENDAÇÕES ===
        
        # Função Renal - Creatinina e eGFR
        # Indicações: Hipertensão, Diabetes, Doença Renal Crônica, Cardiopatia, ≥60 anos
        needs_renal_function = (
            'hipertensao' in comorbidades or 
            'diabetes_tipo_2' in comorbidades or 
            'doenca_renal_cronica' in comorbidades or 
            'cardiopatia' in comorbidades or 
            idade >= 60
        )
        
        if needs_renal_function:
            should_rec, status = should_recommend_exam('Função Renal', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Creatinina, ureia e eGFR, soro',
                    'descricao': 'Avaliação da função renal - Indicado para hipertensão, diabetes, cardiopatia ou ≥60 anos',
                    'prioridade': 'alta',
                    'referencia': 'KDIGO 2024 / SBN 2023',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # === NOVOS EXAMES OBRIGATÓRIOS PARA HIPERTENSOS (AHA/ACC 2025) ===
        
        # Relação Albumina/Creatinina Urinária - NOVA OBRIGATÓRIA para todos hipertensos
        if 'hipertensao' in comorbidades:
            should_rec, status = should_recommend_exam('Relação Albumina/Creatinina', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Relação albumina/creatinina, urina',
                    'descricao': 'Avaliação de lesão renal precoce - OBRIGATÓRIA para todos hipertensos (AHA/ACC 2025)',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Ácido Úrico - Para hipertensos como fator de risco cardiovascular
        if 'hipertensao' in comorbidades:
            should_rec, status = should_recommend_exam('Ácido Úrico', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Ácido úrico, soro',
                    'descricao': 'Fator de risco cardiovascular em hipertensos',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # === INVESTIGAÇÃO DE HIPERTENSÃO RESISTENTE ===
        
        # Aldosteronismo Primário - NOVA RECOMENDAÇÃO CLASSE I
        # Para hipertensão resistente (checkbox específico)
        if 'has_resistente' in comorbidades:
            should_rec, status = should_recommend_exam('Aldosteronismo Primário', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Relação aldosterona/renina (ARR), soro',
                    'descricao': 'Rastreamento de aldosteronismo primário - OBRIGATÓRIO para hipertensão resistente (AHA/ACC 2025)',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025 Classe I',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
                
            # Aldosterona plasmática complementar
            should_rec_aldo, status_aldo = should_recommend_exam('Aldosterona Plasmática', exames_anteriores, 365)
            if should_rec_aldo:
                rec = {
                    'titulo': 'Aldosterona plasmática, soro',
                    'descricao': 'Complementar ao ARR para diagnóstico de aldosteronismo primário',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'laboratorial'
                }
                if status_aldo:
                    rec['status'] = status_aldo
                recommendations.append(rec)
                
            # Work-up completo para HAS resistente
            # Ecocardiograma transtorácico
            should_rec_eco, status_eco = should_recommend_exam('Ecocardiograma', exames_anteriores, 730)
            if should_rec_eco:
                rec = {
                    'titulo': 'Ecocardiograma transtorácico',
                    'descricao': 'Avaliação de hipertrofia ventricular esquerda e função cardíaca em HAS resistente',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'imagem'
                }
                if status_eco:
                    rec['status'] = status_eco
                recommendations.append(rec)
                
            # Ultrassom de artérias renais
            should_rec_renal, status_renal = should_recommend_exam('Ultrassom Artérias Renais', exames_anteriores, 1095)
            if should_rec_renal:
                rec = {
                    'titulo': 'Ultrassom com Doppler de artérias renais',
                    'descricao': 'Investigação de estenose de artéria renal em HAS resistente',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'imagem'
                }
                if status_renal:
                    rec['status'] = status_renal
                recommendations.append(rec)
                
            # Polissonografia se suspeita de apneia
            should_rec_poli, status_poli = should_recommend_exam('Polissonografia', exames_anteriores, 1825)
            if should_rec_poli:
                rec = {
                    'titulo': 'Polissonografia',
                    'descricao': 'Investigação de apneia do sono como causa de HAS resistente',
                    'prioridade': 'media',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'imagem'
                }
                if status_poli:
                    rec['status'] = status_poli
                recommendations.append(rec)
        
        # Eletrólitos (Sódio, Potássio, Cloro)
        # Indicações: Hipertensão, Diabetes, Doença Renal Crônica, Cardiopatia, uso de diuréticos
        needs_electrolytes = (
            'hipertensao' in comorbidades or 
            'diabetes_tipo_2' in comorbidades or 
            'doenca_renal_cronica' in comorbidades or 
            'cardiopatia' in comorbidades or
            'diurético' in outras_comorbidades.lower() or
            'diuretico' in outras_comorbidades.lower()
        )
        
        if needs_electrolytes:
            should_rec, status = should_recommend_exam('Eletrólitos', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Sódio, potássio e cloro, soro',
                    'descricao': 'Dosagem de eletrólitos - Indicado para hipertensão, diabetes, cardiopatia ou uso de diuréticos',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2020 / KDIGO 2024',
                    'categoria': 'laboratorial'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Eletrocardiograma (ECG)
        # Indicações: Hipertensão, Diabetes, Cardiopatia, ≥40 anos, fatores de risco cardiovascular
        needs_ecg = (
            'hipertensao' in comorbidades or 
            'diabetes_tipo_2' in comorbidades or 
            'cardiopatia' in comorbidades or 
            'dislipidemia' in comorbidades or
            idade >= 40 or
            'cardiopatia' in historia_familiar  # História familiar de doença cardiovascular
        )
        
        if needs_ecg:
            should_rec, status = should_recommend_exam('Eletrocardiograma', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Eletrocardiograma de repouso',
                    'descricao': 'ECG de 12 derivações - Rastreamento cardiovascular para hipertensão, diabetes ou ≥40 anos',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2019 / AHA/ACC 2019',
                    'categoria': 'imagem'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Ecocardiograma Transtorácico
        # Indicações: Cardiopatia conhecida, Hipertensão com sintomas, Diabetes com complicações, sopro cardíaco
        needs_echo = (
            'cardiopatia' in comorbidades or
            ('hipertensao' in comorbidades and idade >= 60) or
            ('diabetes_tipo_2' in comorbidades and idade >= 50) or
            'sopro' in outras_comorbidades.lower() or
            'insuficiencia' in outras_comorbidades.lower() or
            'arritmia' in outras_comorbidades.lower()
        )
        
        if needs_echo:
            should_rec, status = should_recommend_exam('Ecocardiograma', exames_anteriores, 730)  # A cada 2 anos
            if should_rec:
                rec = {
                    'titulo': 'Ecocardiograma transtorácico',
                    'descricao': 'Avaliação da função cardíaca - Indicado para cardiopatia, hipertensão ≥60 anos ou diabetes ≥50 anos',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2019 / ASE 2020',
                    'categoria': 'imagem'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Pressão Arterial
        should_rec, status = should_recommend_exam('Pressão Arterial', exames_anteriores, 365)
        if should_rec:
            rec = {
                'titulo': 'Medida da Pressão Arterial',
                'descricao': 'Verificação anual da pressão arterial',
                'prioridade': 'alta',
                'referencia': 'AHA/ACC 2025',
                'categoria': 'outras'
            }
            if status:
                rec['status'] = status
            recommendations.append(rec)
        
        # Densitometria
        if (sexo == 'feminino' and idade >= 65) or (sexo == 'masculino' and idade >= 70):
            should_rec, status = should_recommend_exam('Densitometria', exames_anteriores, intervals['Densitometria'])
            if should_rec:
                rec = {
                    'titulo': 'Densitometria Óssea',
                    'descricao': 'DEXA para rastreamento de osteoporose',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF Grau B',
                    'categoria': 'outras'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # PHQ-9 para depressão
        should_rec, status = should_recommend_exam('PHQ-9', exames_anteriores, 365)
        if should_rec:
            rec = {
                'titulo': 'PHQ-9',
                'descricao': 'Rastreamento de depressão',
                'prioridade': 'media',
                'referencia': 'USPSTF Grau B',
                'categoria': 'outras'
            }
            if status:
                rec['status'] = status
            recommendations.append(rec)
        
        # Fundoscopia para diabéticos
        if 'diabetes_tipo_2' in comorbidades:
            should_rec, status = should_recommend_exam('Fundoscopia', exames_anteriores, 365)
            if should_rec:
                rec = {
                    'titulo': 'Fundoscopia',
                    'descricao': 'Exame de fundo de olho anual',
                    'prioridade': 'alta',
                    'referencia': 'ADA 2024',
                    'categoria': 'imagem'
                }
                if status:
                    rec['status'] = status
                recommendations.append(rec)
        
        # Gerar alertas para exames em atraso (correção de robustez)
        for exam in exames_anteriores or []:
            if not exam or not isinstance(exam, dict):
                continue
            name = (exam.get('name') or '').lower()
            date_str = exam.get('date')
            days_since = calculate_days_since_exam(date_str)

            # Ignorar itens sem nome ou sem data válida
            if not name or days_since is None:
                continue

            if 'hba1c' in name and days_since > 180:
                alerts.append(f"HbA1c em atraso - último exame há {days_since} dias")
            elif 'mamografia' in name and days_since > 760:
                alerts.append(f"Mamografia em atraso - último exame há {days_since} dias")
            elif 'colonoscopia' in name and days_since > 3680:
                alerts.append(f"Colonoscopia em atraso - último exame há {days_since} dias")
        
        # === MONITORAMENTO DE MEDICAÇÕES ===
        
        # Função para verificar se medicação está sendo usada
        def is_using_medication(med_keywords):
            return any(keyword in medicacoes_uso_continuo for keyword in med_keywords)
        
        # Função para adicionar exame se não duplicado
        def add_medication_exam(titulo, descricao, prioridade='alta', referencia='Monitoramento medicamentoso'):
            # Verificar se já existe exame similar
            existing_titles = [rec['titulo'].lower() for rec in recommendations]
            if not any(keyword in existing_titles for keyword in titulo.lower().split()):
                recommendations.append({
                    'titulo': titulo,
                    'descricao': descricao,
                    'prioridade': prioridade,
                    'referencia': referencia,
                    'categoria': 'laboratorial'
                })
        
        # IECA/BRA (Enalapril, Losartana, Captopril, Valsartana, etc.)
        if is_using_medication(['enalapril', 'losartana', 'captopril', 'valsartana', 'lisinopril', 'telmisartana', 'olmesartana']):
            add_medication_exam(
                'Creatinina, ureia e eGFR, soro',
                'Monitoramento da função renal em uso de IECA/BRA',
                'alta'
            )
            add_medication_exam(
                'Sódio, potássio e cloro, soro',
                'Monitoramento de eletrólitos em uso de IECA/BRA (risco de hipercalemia)',
                'alta'
            )
        
        # Diuréticos (Hidroclorotiazida, Furosemida, Indapamida, etc.)
        if is_using_medication(['hidroclorotiazida', 'furosemida', 'indapamida', 'clortalidona', 'espironolactona']):
            add_medication_exam(
                'Sódio, potássio e cloro, soro',
                'Monitoramento de eletrólitos em uso de diuréticos (risco de hipocalemia/hiponatremia)',
                'alta'
            )
            add_medication_exam(
                'Creatinina, ureia e eGFR, soro',
                'Monitoramento da função renal em uso de diuréticos',
                'alta'
            )
        
        # Estatinas (Sinvastatina, Atorvastatina, Rosuvastatina, etc.)
        if is_using_medication(['sinvastatina', 'atorvastatina', 'rosuvastatina', 'pravastatina']):
            add_medication_exam(
                'ALT (TGP) e AST (TGO), soro',
                'Monitoramento de enzimas hepáticas em uso de estatinas',
                'alta'
            )
            add_medication_exam(
                'CPK (Creatinoquinase), soro',
                'Monitoramento de miopatia em uso de estatinas',
                'media'
            )
        
        # Metformina
        if is_using_medication(['metformina']):
            add_medication_exam(
                'Creatinina, ureia e eGFR, soro',
                'Monitoramento da função renal em uso de metformina (risco de acidose láctica)',
                'alta'
            )
            add_medication_exam(
                'Vitamina B12, soro',
                'Monitoramento de deficiência de B12 em uso prolongado de metformina',
                'media'
            )
        
        # Warfarina
        if is_using_medication(['varfarina', 'warfarina']):
            add_medication_exam(
                'INR (Tempo de Protrombina)',
                'Monitoramento obrigatório da anticoagulação com warfarina',
                'alta'
            )
        
        # Digoxina
        if is_using_medication(['digoxina']):
            add_medication_exam(
                'Digoxinemia, soro',
                'Monitoramento de níveis séricos de digoxina',
                'alta'
            )
            add_medication_exam(
                'Sódio, potássio e cloro, soro',
                'Monitoramento de eletrólitos em uso de digoxina (hipocalemia aumenta toxicidade)',
                'alta'
            )
        
        # Lítio
        if is_using_medication(['lítio', 'litio']):
            add_medication_exam(
                'Lítio sérico',
                'Monitoramento obrigatório de níveis séricos de lítio',
                'alta'
            )
            add_medication_exam(
                'Creatinina, ureia e eGFR, soro',
                'Monitoramento da função renal em uso de lítio',
                'alta'
            )
            add_medication_exam(
                'TSH e T4 livre, soro',
                'Monitoramento da função tireoidiana em uso de lítio',
                'alta'
            )
        
        # Amiodarona
        if is_using_medication(['amiodarona']):
            add_medication_exam(
                'TSH e T4 livre, soro',
                'Monitoramento da função tireoidiana em uso de amiodarona',
                'alta'
            )
            add_medication_exam(
                'ALT (TGP) e AST (TGO), soro',
                'Monitoramento de hepatotoxicidade em uso de amiodarona',
                'alta'
            )
        
        # Enriquecer recomendações com links clicáveis das referências
        for rec in recommendations:
            ref_str = rec.get('referencia', '')
            titulo = rec.get('titulo', '')
            links = build_reference_links(titulo, ref_str)
            if links:
                rec['referencias'] = links
                rec['referencia_html'] = build_reference_html(links)
        
        # Rastrear geração de recomendações
        analytics.track_recommendation()
        
        return jsonify({
            'recommendations': recommendations,
            'alerts': alerts,
            'total_recommendations': len(recommendations)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@checkup_intelligent_bp.route('/gerar-solicitacao-exames', methods=['POST'])
def gerar_solicitacao_exames():
    try:
        data = request.json
        recommendations = data.get('recommendations', [])
        patient_data = data.get('patient_data', {})
        
        nome_paciente = patient_data.get('nome', 'Paciente')
        idade = patient_data.get('idade', '')
        sexo = patient_data.get('sexo', '')
        
        # Data atual
        data_atual = datetime.now().strftime("%d/%m/%Y")
        
        # Filtrar exames (laboratoriais, rastreamento e imagem) e organizar por tipo
        exames_laboratoriais = []
        exames_imagem = []
        
        for rec in recommendations:
            if rec.get('categoria') == 'laboratorial':
                exames_laboratoriais.append(rec)
            elif rec.get('categoria') in ['rastreamento', 'imagem']:
                exames_imagem.append(rec)
        
        # Combinar exames na ordem: laboratoriais primeiro, depois imagem
        exames = exames_laboratoriais + exames_imagem
        
        if not exames:
            return jsonify({'error': 'Nenhum exame encontrado para gerar solicitação'}), 400
        
        # Rastrear geração de solicitação de exames
        analytics.track_exam_request()
        
        # Gerar HTML para impressão
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
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
            <div class="print-actions">
                <button class="print-btn" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
                <button class="print-btn close-btn" onclick="window.close()">✖️ Fechar</button>
            </div>
            
            <div class="document-container">
                <div class="header">
                    <h1>SOLICITAÇÃO DE EXAME</h1>
                    <div class="clinic-info">
                        <p><strong>Órion Business and Health</strong> &nbsp;&nbsp;&nbsp;&nbsp; Data de emissão: {data_atual}</p>
                        <p>Endereço: Avenida Portugal, 1148, Setor Marista, Goiânia - GO</p>
                        <p>Telefone: (62) 3225-5885</p>
                    </div>
                </div>

                <div class="doctor-info">
                    <p>Dr(a). RODOLFO CAMBRAIA FROTA</p>
                    <p>CRM: 26815 - GO</p>
                </div>

                <div class="patient-info">
                    <p><strong>Paciente:</strong> {nome_paciente} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Sexo:</strong> {sexo.capitalize()}</p>
                </div>

                <div class="exam-list">
                    <p><strong>Solicito:</strong></p>
                    <ul>
        """
        
        for exam in exames:
            html_content += f"                        <li>• {exam['titulo']}"
            if exam.get('referencia_html'):
                html_content += f"<br><small>Ref.: {exam['referencia_html']}</small>"
            html_content += "</li>\n"
        
        html_content += f"""
                    </ul>
                </div>

                <div class="signature">
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
        
        return html_content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@checkup_intelligent_bp.route('/gerar-receita-vacinas', methods=['POST'])
def gerar_receita_vacinas():
    try:
        data = request.json
        recommendations = data.get('recommendations', [])
        patient_data = data.get('patient_data', {})
        
        nome_paciente = patient_data.get('nome', 'Paciente')
        idade = patient_data.get('idade', '')
        sexo = patient_data.get('sexo', '')
        
        # Data atual
        data_atual = datetime.now().strftime("%d/%m/%Y")
        # Data de validade (1 mês após emissão)
        data_validade = (datetime.now() + relativedelta(months=1)).strftime("%d/%m/%Y")
        
        # Filtrar apenas vacinas
        vacinas = []
        for rec in recommendations:
            if rec.get('categoria') == 'vacina':
                vacinas.append(rec)
        
        if not vacinas:
            return jsonify({'error': 'Nenhuma vacina encontrada para gerar receita'}), 400
        
        # Rastrear geração de receita de vacinas
        analytics.track_vaccine_prescription()
        
        # Gerar HTML para impressão
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Receita de Vacinas - {nome_paciente}</title>
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
                .vaccine-item {{
                    margin: 15px 0;
                    font-size: 11px;
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
            <div class="print-actions">
                <button class="print-btn" onclick="window.print()">🖨️ Imprimir / Salvar PDF</button>
                <button class="print-btn close-btn" onclick="window.close()">✖️ Fechar</button>
            </div>
            
            <div class="document-container">
                <div class="header">
                    <h1>Receita Simples</h1>
                    <div class="clinic-info">
                        <p><strong>Órion Business and Health</strong> &nbsp;&nbsp;&nbsp;&nbsp; Data de emissão: {data_atual}</p>
                        <p>Endereço: Avenida Portugal, 1148, Setor Marista, Goiânia - GO</p>
                        <p>Telefone: (62) 3225-5885</p>
                    </div>
                </div>

                <div class="doctor-info">
                    <p>Dr(a). RODOLFO CAMBRAIA FROTA</p>
                    <p>CRM: 26815 - GO</p>
                </div>

                <div class="patient-info">
                    <p><strong>Paciente:</strong> {nome_paciente} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Sexo:</strong> {sexo.capitalize()}</p>
                    <p><strong>Data de Validade:</strong> {data_validade}</p>
                </div>

                <div class="prescription">
        """
        
        for i, vacina in enumerate(vacinas, 1):
            html_content += f"""
                    <div class="vaccine-item">
                        <p><strong>{i} {vacina['titulo'].upper()}</strong> ---------------------------------------------------- 1 dose</p>
                        <p>{vacina.get('descricao', 'Aplicar conforme orientação médica.')}</p>"""
            if vacina.get('referencia_html'):
                html_content += f"""<p><small>Ref.: {vacina['referencia_html']}</small></p>"""
            html_content += "</div>"
        
        html_content += f"""
                </div>

                <div class="signature">
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
        
        return html_content
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

