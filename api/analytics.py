from flask import Flask, jsonify
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.analytics import analytics

app = Flask(__name__)

@app.route('/api/analytics/stats', methods=['GET', 'OPTIONS'])
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    try:
        response = jsonify(analytics.get_summary())
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/api/analytics/full', methods=['GET', 'OPTIONS'])
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas (admin)"""
    try:
        response = jsonify(analytics.get_stats())
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