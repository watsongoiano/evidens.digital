"""
Evidens Digital - API Principal
Sistema de Check-up Médico Inteligente
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importar módulos do sistema
from src.routes.checkup_intelligent import checkup_intelligent_bp
from src.utils.analytics import analytics

# Criar aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configurar CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Registrar blueprints
app.register_blueprint(checkup_intelligent_bp, url_prefix='/api')

@app.route('/')
def index():
    """Rota raiz - redireciona para index.html"""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/intelligent-tools')
def intelligent_tools():
    """Rota para ferramentas inteligentes"""
    return send_from_directory(BASE_DIR, 'intelligent-tools.html')

@app.route('/analytics')
def analytics_page():
    """Rota para página de analytics"""
    return send_from_directory(BASE_DIR, 'analytics.html')

@app.route('/api/analytics/stats')
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    return jsonify(analytics.get_summary())

@app.route('/api/analytics/full')
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas"""
    return jsonify(analytics.get_stats())

@app.route('/<path:filename>')
def serve_static(filename):
    """Servir arquivos estáticos"""
    # Lista de extensões permitidas
    allowed_extensions = {'.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.json', '.pdf'}
    
    file_path = BASE_DIR / filename
    
    # Verificar se o arquivo existe e tem extensão permitida
    if file_path.exists() and file_path.suffix.lower() in allowed_extensions:
        return send_from_directory(BASE_DIR, filename)
    
    # Se não encontrar, retornar 404
    return jsonify({'error': 'File not found'}), 404

@app.errorhandler(404)
def not_found(e):
    """Handler para erros 404"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handler para erros 500"""
    return jsonify({'error': 'Internal server error'}), 500

# Para execução local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

