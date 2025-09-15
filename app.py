import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.checkup import checkup_bp
from src.routes.checkup_intelligent import checkup_intelligent_bp
from src.routes.database_api import database_api_bp
from src.utils.analytics import analytics, track_visit

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'src', 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Habilitar CORS para todas as rotas
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(checkup_bp, url_prefix='/api')
app.register_blueprint(checkup_intelligent_bp, url_prefix='/api')
app.register_blueprint(database_api_bp)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/analytics/stats')
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    return jsonify(analytics.get_summary())

@app.route('/analytics/full')
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas (admin)"""
    return jsonify(analytics.get_stats())

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@track_visit()
def serve(path):
    # Não interceptar rotas da API
    if path.startswith('api/'):
        return "API route not found", 404
    
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return 'Static folder not configured', 404
    
    if path != '' and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return 'index.html not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
