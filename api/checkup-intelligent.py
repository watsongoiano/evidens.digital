from flask import Flask, request, jsonify
import json

app = Flask(__name__)

def _corsify(resp):
    """Add basic CORS headers to a Flask response object."""
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp

@app.route('/', methods=['POST', 'OPTIONS'])
def handle_intelligent_checkup():
    if request.method == 'OPTIONS':
        return _corsify(jsonify({}))
    
    try:
        data = request.get_json() or {}
        
        # Dados básicos do paciente
        idade = int(data.get('idade', 0))
        sexo = data.get('sexo', '')
        
        # Gerar recomendações básicas baseadas na idade e sexo
        recommendations = []
        
        # Recomendações básicas para adultos
        if idade >= 18:
            recommendations.append({
                'titulo': 'Hemograma Completo',
                'categoria': 'exame',
                'subtitulo': 'Avaliação hematológica geral',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado anualmente para adultos'
            })
            
            recommendations.append({
                'titulo': 'Glicemia de Jejum',
                'categoria': 'exame',
                'subtitulo': 'Rastreamento de diabetes',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado a cada 3 anos para adultos'
            })
            
            recommendations.append({
                'titulo': 'Perfil Lipídico',
                'categoria': 'exame',
                'subtitulo': 'Avaliação do risco cardiovascular',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado a cada 5 anos para adultos'
            })
        
        # Recomendações específicas por sexo
        if sexo == 'feminino' and idade >= 25:
            recommendations.append({
                'titulo': 'Papanicolau',
                'categoria': 'exame',
                'subtitulo': 'Rastreamento de câncer cervical',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado a cada 3 anos'
            })
            
        if sexo == 'feminino' and idade >= 50:
            recommendations.append({
                'titulo': 'Mamografia',
                'categoria': 'exame',
                'subtitulo': 'Rastreamento de câncer de mama',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado anualmente após os 50 anos'
            })
            
        if sexo == 'masculino' and idade >= 50:
            recommendations.append({
                'titulo': 'PSA',
                'categoria': 'exame',
                'subtitulo': 'Rastreamento de câncer de próstata',
                'grau_evidencia': 'B',
                'referencia_html': 'Discutir com médico após os 50 anos'
            })
        
        # Vacinas
        if idade >= 60:
            recommendations.append({
                'titulo': 'Vacina da Gripe',
                'categoria': 'vacina',
                'subtitulo': 'Prevenção de influenza',
                'grau_evidencia': 'A',
                'referencia_html': 'Recomendado anualmente para idosos'
            })
        
        response_data = {
            'recommendations': recommendations,
            'patient_data': data,
            'total_recommendations': len(recommendations)
        }
        
        return _corsify(jsonify(response_data))
        
    except Exception as e:
        error_response = jsonify({'error': f'Erro interno: {str(e)}'})
        return _corsify(error_response), 500

# For Vercel
def handler(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    app.run(debug=True)
