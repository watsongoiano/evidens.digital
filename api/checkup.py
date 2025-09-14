from flask import Flask, request, jsonify, make_response
import json

app = Flask(__name__)

def _corsify(resp):
    """Add CORS headers to response"""
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp

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
    if 45 <= idade <= 75:
        recomendacoes.append({
            'titulo': 'Rastreamento Câncer Colorretal',
            'descricao': 'Colonoscopia a cada 10 anos ou sigmoidoscopia a cada 5 anos',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cancer',
            'referencia': 'USPSTF Grau A'
        })
    
    # Câncer de colo de útero (mulheres 21-65 anos)
    if sexo == 'feminino' and 21 <= idade <= 65:
        recomendacoes.append({
            'titulo': 'Citologia Cervical',
            'descricao': 'Papanicolaou a cada 3 anos',
            'prioridade': 'alta',
            'categoria': 'rastreamento_cancer',
            'referencia': 'USPSTF Grau A'
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
            }
        ])
    
    if 'hipertensao' in comorbidades:
        recomendacoes.append({
            'titulo': 'Eletrólitos e Creatinina',
            'descricao': 'Sódio, potássio e creatinina anual',
            'prioridade': 'alta',
            'categoria': 'acompanhamento_hipertensao',
            'referencia': 'AHA/ACC 2017'
        })
    
    return recomendacoes

@app.route('/checkup', methods=['POST', 'OPTIONS'])
def handle_checkup():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))
    
    try:
        data = request.get_json(silent=True) or {}
        
        return _corsify(jsonify({"ok": True, "data": data}))
        
    except Exception as e:
        error_response = {'error': str(e)}
        return _corsify(jsonify(error_response)), 500

