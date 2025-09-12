from flask import Flask, request, jsonify
import json

app = Flask(__name__)

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

@app.route('/api/checkup', methods=['POST', 'OPTIONS'])
def handle_checkup():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        data = request.get_json()
        
        if not data:
            error_response = jsonify({'error': 'Dados não fornecidos'})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 400
        
        # Validar dados obrigatórios
        if 'idade' not in data or 'sexo' not in data:
            error_response = jsonify({'error': 'Idade e sexo são obrigatórios'})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 400
        
        idade = data['idade']
        sexo = data['sexo']
        comorbidades = data.get('comorbidades', [])
        tabagismo = data.get('tabagismo', {})
        
        # Gerar recomendações
        recomendacoes = []
        recomendacoes.extend(get_age_sex_recommendations(idade, sexo, tabagismo))
        recomendacoes.extend(get_comorbidity_recommendations(comorbidades))
        
        # Adicionar vacinas básicas
        recomendacoes.extend([
            {
                'titulo': 'Vacina Influenza',
                'descricao': 'Vacina anual (alta dose se ≥65 anos)',
                'prioridade': 'alta',
                'categoria': 'vacinacao',
                'referencia': 'CDC 2024'
            },
            {
                'titulo': 'Vacina COVID-19',
                'descricao': 'Vacina 2024-2025 conforme CDC',
                'prioridade': 'alta',
                'categoria': 'vacinacao',
                'referencia': 'CDC 2024'
            }
        ])
        
        response = jsonify(recomendacoes)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

def handler(req):
    with app.test_request_context(path=req.path, method=req.method, 
                                   data=req.get_data(), headers=req.headers):
        return app.full_dispatch_request()