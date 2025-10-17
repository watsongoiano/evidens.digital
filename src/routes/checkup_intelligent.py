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

def generate_age_sex_recommendations(age, sex, country='BR'):
    """Gera recomendações baseadas em idade e sexo"""
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
    
    # Exames laboratoriais básicos
    _add_rec({
        'titulo': 'Glicemia de jejum',
        'descricao': 'ADA 2024: Rastreamento universal ≥35 anos',
        'subtitulo': 'Rastreamento de diabetes',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'ADA 2024',
        'grau_evidencia': 'A'
    })
    
    _add_rec({
        'titulo': 'Colesterol total e frações, soro',
        'descricao': 'Colesterol total, HDL, LDL e triglicerídeos',
        'subtitulo': 'Perfil lipídico',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'AHA/ACC 2025',
        'grau_evidencia': 'B'
    })
    
    # Hemograma e TSH removidos - não há evidência para rastreamento universal
    # TSH: USPSTF grau I (evidência insuficiente)
    # Hemograma: sem guideline que recomende rastreamento universal
    
    _add_rec({
        'titulo': 'Creatinina, soro',
        'descricao': 'Avaliação da função renal',
        'subtitulo': 'Rastreamento de doença renal',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'KDIGO 2024',
        'grau_evidencia': 'A'
    })
    
    # TGO/TGP removido: sem evidência para rastreamento universal em assintomáticos
    # Apenas indicado para pacientes com fatores de risco específicos
    
    # Rastreamento de doenças infecciosas
    _add_rec({
        'titulo': 'Anti-HIV 1 e 2, soro',
        'descricao': 'Teste para detecção de HIV',
        'subtitulo': 'Rastreamento de HIV',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'USPSTF 2024',
        'grau_evidencia': 'A'
    })
    
    _add_rec({
        'titulo': 'Anti-HCV IgG, soro',
        'descricao': 'Teste para detecção de Hepatite C',
        'subtitulo': 'Rastreamento de Hepatite C',
        'categoria': 'laboratorio',
        'prioridade': 'alta',
        'referencia': 'USPSTF 2024',
        'grau_evidencia': 'A'
    })
    
    # Exames de imagem
    _add_rec({
        'titulo': 'Eletrocardiograma de repouso',
        'descricao': 'ECG de 12 derivações - Rastreamento cardiovascular para hipertensão, diabetes ou ≥40 anos',
        'subtitulo': 'ECG de 12 derivações',
        'categoria': 'imagem',
        'prioridade': 'alta',
        'referencia': 'SBC 2019 / AHA/ACC 2019',
        'grau_evidencia': 'C'
    })
    
    # Rastreamento de câncer por idade e sexo
    if sex == 'feminino':
        if 40 <= age <= 74:
            _add_rec({
                'titulo': 'Mamografia Digital - Bilateral',
                'descricao': 'Mamografia bienal (40-74 anos)',
                'subtitulo': 'Rastreamento de câncer de mama',
                'categoria': 'imagem',
                'prioridade': 'alta',
                'referencia': 'USPSTF 2024',
                'grau_evidencia': 'B'
            })
        
        if 21 <= age <= 65:
            _add_rec({
                'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular',
                'descricao': 'Papanicolaou a cada 3 anos (21-65 anos)',
                'subtitulo': 'Rastreamento de câncer do colo do útero',
                'categoria': 'laboratorio',
                'prioridade': 'alta',
                'referencia': 'USPSTF',
                'grau_evidencia': 'A'
            })
    
    if sex == 'masculino' and age >= 50:
        _add_rec({
            'titulo': 'PSA total, soro',
            'descricao': 'Rastreamento de câncer de próstata (≥50 anos)',
            'subtitulo': 'Antígeno Prostático Específico',
            'categoria': 'laboratorio',
            'prioridade': 'media',
            'referencia': 'USPSTF 2018',
            'grau_evidencia': 'C'
        })
    
    # Colonoscopia
    if 45 <= age <= 75:
        _add_rec({
            'titulo': 'Colonoscopia de Rastreio com ou sem biópsia',
            'descricao': 'Colonoscopia a cada 10 anos (45-75 anos)',
            'subtitulo': 'Rastreamento de câncer colorretal',
            'categoria': 'imagem',
            'prioridade': 'alta',
            'referencia': 'USPSTF 2021',
            'grau_evidencia': 'B'
        })
    
    # Vacinas
    _add_rec({
        'titulo': 'Vacina Influenza Tetravalente',
        'descricao': 'Dose anual. Aplicar em dose única, INTRAMUSCULAR, anualmente.',
        'subtitulo': 'Imunização sazonal contra influenza',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2024',
        'grau_evidencia': 'A'
    })

    # HPV (masculino e feminino) até 45 anos
    if age <= 45:
        prioridade_hpv = 'alta' if age <= 26 else 'media'
        _add_rec({
            'titulo': 'Gardasil 9® (Vacina Papilomavírus Humano 9-Valente)',
            'descricao': '3 doses. Aplicar 0, 2 e 6 meses.',
            'subtitulo': 'Prevenção de HPV e neoplasias relacionadas',
            'categoria': 'vacina',
            'prioridade': prioridade_hpv,
            'referencia': 'SBIm 2024',
            'grau_evidencia': 'A'
        })

    # Hepatite B (adultos não vacinados)
    _add_rec({
        'titulo': 'Hepatite B (VHB)',
        'descricao': 'Esquema de 3 doses (0, 1, 6 meses) em não vacinados.',
        'subtitulo': 'Imunização contra hepatite B',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2024',
        'grau_evidencia': 'A'
    })

    # dTpa (Tétano, difteria, coqueluche)
    _add_rec({
        'titulo': 'dTpa (Tétano, difteria, coqueluche)',
        'descricao': '1 dose de dTpa, depois reforço com dT ou dTpa a cada 10 anos.',
        'subtitulo': 'Proteção contra tétano, difteria e coqueluche',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2024 / CDC 2025',
        'grau_evidencia': 'A'
    })

    # Tríplice viral (Sarampo, caxumba, rubéola)
    if age <= 59:  # Prioridade para adultos jovens não vacinados
        _add_rec({
            'titulo': 'Tríplice viral (Sarampo, caxumba, rubéola)',
            'descricao': '1 ou 2 doses para adultos não vacinados ou sem comprovação vacinal.',
            'subtitulo': 'Imunização contra sarampo, caxumba e rubéola',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'A'
        })

    # Hepatite A
    _add_rec({
        'titulo': 'Hepatite A',
        'descricao': '2 doses com intervalo de 6 meses.',
        'subtitulo': 'Proteção contra hepatite A',
        'categoria': 'vacina',
        'prioridade': 'alta',
        'referencia': 'SBIm 2024 / CDC 2025',
        'grau_evidencia': 'A'
    })

    # Febre amarela (para áreas endêmicas)
    _add_rec({
        'titulo': 'Febre amarela',
        'descricao': 'Dose única ou reforço. Indicada para residentes ou viajantes para áreas endêmicas.',
        'subtitulo': 'Proteção contra febre amarela',
        'categoria': 'vacina',
        'prioridade': 'media',
        'referencia': 'SBIm 2024',
        'grau_evidencia': 'A'
    })

    # Meningocócica ACWY
    if age <= 59:
        _add_rec({
            'titulo': 'Meningocócica ACWY',
            'descricao': 'Dose única ou reforço a cada 5 anos para grupos de risco.',
            'subtitulo': 'Proteção contra meningite meningocócica',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'B'
        })

    # Meningocócica B (19-23 anos)
    if 19 <= age <= 23:
        _add_rec({
            'titulo': 'Meningocócica B',
            'descricao': '2 doses conforme esquema do fabricante.',
            'subtitulo': 'Proteção contra meningite meningocócica sorogrupo B',
            'categoria': 'vacina',
            'prioridade': 'media',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'B'
        })

    # Dengue (Qdenga)
    _add_rec({
        'titulo': 'Dengue (Qdenga)',
        'descricao': '2 doses com intervalo de 3 meses. Indicada para áreas endêmicas.',
        'subtitulo': 'Proteção contra dengue',
        'categoria': 'vacina',
        'prioridade': 'media',
        'referencia': 'SBIm 2024',
        'grau_evidencia': 'B'
    })

    # COVID-19
    _add_rec({
        'titulo': 'COVID-19',
        'descricao': 'Dose de reforço anual conforme vacina disponível.',
        'subtitulo': 'Proteção contra COVID-19',
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
            'subtitulo': 'Proteção contra herpes zóster (cobreiro)',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'A'
        })

    # Pneumocócicas a partir de 50 anos
    if age >= 50:
        _add_rec({
            'titulo': 'VPC15 (Vaxneuvance®) ou VPC13, 0,5ml',
            'descricao': '1 dose. Pode ser coadministrada com Shingrix®, Efluelda® e Arexvy®',
            'subtitulo': 'Vacina pneumocócica conjugada',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'A'
        })
        _add_rec({
            'titulo': 'VPP23, 0,5ml',
            'descricao': '1 dose 6 meses após VPC15/VPC13; reforço 5 anos após a primeira dose de VPC',
            'subtitulo': 'Vacina pneumocócica polissacarídica',
            'categoria': 'vacina',
            'prioridade': 'alta',
            'referencia': 'SBIm 2024 / CDC 2025',
            'grau_evidencia': 'A'
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
        
        # Dados clínicos para PREVENT
        patient_data = {
            'age': age,
            'sex': sex,
            'totalCholesterol': float(data.get('colesterol_total', 0)) if data.get('colesterol_total') else 0,
            'hdlCholesterol': float(data.get('hdl_colesterol', 0)) if data.get('hdl_colesterol') else 0,
            'systolicBP': float(data.get('pressao_sistolica', 0)) if data.get('pressao_sistolica') else 0,
            'diabetes': 'diabetes_tipo_2' in data.get('comorbidades', []),
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
        
        # Gerar recomendações
        recommendations = []
        
        # Recomendações baseadas em idade e sexo
        age_sex_recs = generate_age_sex_recommendations(age, sex)
        recommendations.extend(age_sex_recs)
        
        # Recomendações de biomarcadores se necessário
        if risk_level in ['borderline', 'intermediario', 'alto']:
            biomarker_recs = generate_biomarker_recommendations(risk_level, age, sex)
            recommendations.extend(biomarker_recs)
        
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
