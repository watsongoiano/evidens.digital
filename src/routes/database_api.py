from flask import Blueprint, request, jsonify
from datetime import datetime
import json
from src.models.user import db
from src.models.medical import Patient, Checkup, Recomendacao, ExameRealizado, Analytics

database_api_bp = Blueprint('database_api', __name__)

@database_api_bp.route('/api/patients', methods=['GET'])
def get_patients():
    """Listar todos os pacientes"""
    try:
        patients = Patient.query.all()
        return jsonify({
            'success': True,
            'data': [patient.to_dict() for patient in patients],
            'count': len(patients)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/patients', methods=['POST'])
def create_patient():
    """Criar novo paciente"""
    try:
        data = request.json
        
        patient = Patient(
            nome=data.get('nome'),
            idade=data.get('idade'),
            sexo=data.get('sexo'),
            peso=data.get('peso'),
            altura=data.get('altura')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': patient.to_dict(),
            'message': 'Paciente criado com sucesso'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Obter dados de um paciente específico"""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Incluir checkups do paciente
        checkups = [checkup.to_dict() for checkup in patient.checkups]
        
        patient_data = patient.to_dict()
        patient_data['checkups'] = checkups
        
        return jsonify({
            'success': True,
            'data': patient_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/checkups', methods=['POST'])
def create_checkup():
    """Criar novo checkup"""
    try:
        data = request.json
        
        checkup = Checkup(
            patient_id=data.get('patient_id'),
            pressao_sistolica=data.get('pressao_sistolica'),
            pressao_diastolica=data.get('pressao_diastolica'),
            colesterol_total=data.get('colesterol_total'),
            hdl_colesterol=data.get('hdl_colesterol'),
            creatinina=data.get('creatinina'),
            hba1c=data.get('hba1c'),
            risco_10_anos=data.get('risco_10_anos'),
            risco_30_anos=data.get('risco_30_anos'),
            classificacao_risco=data.get('classificacao_risco'),
            comorbidades=json.dumps(data.get('comorbidades', [])),
            historia_familiar=json.dumps(data.get('historia_familiar', [])),
            tabagismo=data.get('tabagismo'),
            macos_ano=data.get('macos_ano'),
            medicacoes=data.get('medicacoes'),
            pais_guideline=data.get('pais_guideline', 'BR')
        )
        
        db.session.add(checkup)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': checkup.to_dict(),
            'message': 'Checkup criado com sucesso'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/checkups/<int:checkup_id>/recomendacoes', methods=['POST'])
def create_recomendacao():
    """Criar nova recomendação para um checkup"""
    try:
        data = request.json
        checkup_id = request.view_args['checkup_id']
        
        # Verificar se o checkup existe
        checkup = Checkup.query.get_or_404(checkup_id)
        
        recomendacao = Recomendacao(
            checkup_id=checkup_id,
            titulo=data.get('titulo'),
            descricao=data.get('descricao'),
            categoria=data.get('categoria'),
            prioridade=data.get('prioridade'),
            referencia=data.get('referencia'),
            status=data.get('status', 'pendente')
        )
        
        db.session.add(recomendacao)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': recomendacao.to_dict(),
            'message': 'Recomendação criada com sucesso'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/recomendacoes/<int:recomendacao_id>', methods=['PUT'])
def update_recomendacao(recomendacao_id):
    """Atualizar status de uma recomendação"""
    try:
        recomendacao = Recomendacao.query.get_or_404(recomendacao_id)
        data = request.json
        
        if 'status' in data:
            recomendacao.status = data['status']
        
        if 'data_realizacao' in data and data['data_realizacao']:
            recomendacao.data_realizacao = datetime.fromisoformat(data['data_realizacao'])
        
        if 'observacoes' in data:
            recomendacao.observacoes = data['observacoes']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': recomendacao.to_dict(),
            'message': 'Recomendação atualizada com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/exames', methods=['POST'])
def create_exame():
    """Registrar um exame realizado"""
    try:
        data = request.json
        
        exame = ExameRealizado(
            checkup_id=data.get('checkup_id'),
            nome_exame=data.get('nome_exame'),
            data_realizacao=datetime.fromisoformat(data.get('data_realizacao')),
            resultado=data.get('resultado'),
            valores_referencia=data.get('valores_referencia'),
            observacoes=data.get('observacoes'),
            arquivo_path=data.get('arquivo_path'),
            arquivo_nome=data.get('arquivo_nome')
        )
        
        db.session.add(exame)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': exame.to_dict(),
            'message': 'Exame registrado com sucesso'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/analytics', methods=['POST'])
def track_event():
    """Registrar evento de analytics"""
    try:
        data = request.json
        
        analytics = Analytics(
            evento=data.get('evento'),
            dados=json.dumps(data.get('dados', {})),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(analytics)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Evento registrado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/analytics/stats', methods=['GET'])
def get_analytics_stats():
    """Obter estatísticas de analytics"""
    try:
        # Contar eventos por tipo
        eventos = db.session.query(
            Analytics.evento,
            db.func.count(Analytics.id).label('count')
        ).group_by(Analytics.evento).all()
        
        # Total de eventos
        total_eventos = Analytics.query.count()
        
        # Eventos por dia (últimos 30 dias)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        eventos_recentes = db.session.query(
            db.func.date(Analytics.timestamp).label('data'),
            db.func.count(Analytics.id).label('count')
        ).filter(
            Analytics.timestamp >= thirty_days_ago
        ).group_by(
            db.func.date(Analytics.timestamp)
        ).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_eventos': total_eventos,
                'eventos_por_tipo': [{'evento': e.evento, 'count': e.count} for e in eventos],
                'eventos_recentes': [{'data': str(e.data), 'count': e.count} for e in eventos_recentes]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@database_api_bp.route('/api/database/stats', methods=['GET'])
def get_database_stats():
    """Obter estatísticas gerais do banco de dados"""
    try:
        from src.models.user import User
        
        stats = {
            'usuarios': User.query.count(),
            'pacientes': Patient.query.count(),
            'checkups': Checkup.query.count(),
            'recomendacoes': Recomendacao.query.count(),
            'exames_realizados': ExameRealizado.query.count(),
            'eventos_analytics': Analytics.query.count()
        }
        
        # Estatísticas por categoria de recomendação
        recomendacoes_por_categoria = db.session.query(
            Recomendacao.categoria,
            db.func.count(Recomendacao.id).label('count')
        ).group_by(Recomendacao.categoria).all()
        
        # Distribuição de risco
        distribuicao_risco = db.session.query(
            Checkup.classificacao_risco,
            db.func.count(Checkup.id).label('count')
        ).group_by(Checkup.classificacao_risco).all()
        
        return jsonify({
            'success': True,
            'data': {
                'totais': stats,
                'recomendacoes_por_categoria': [
                    {'categoria': r.categoria, 'count': r.count} 
                    for r in recomendacoes_por_categoria
                ],
                'distribuicao_risco': [
                    {'risco': r.classificacao_risco, 'count': r.count} 
                    for r in distribuicao_risco
                ]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
