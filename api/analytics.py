from flask import Flask, jsonify
import datetime
from src.utils.cors import sanitize_private_network_header

app = Flask(__name__)

@app.route('/api/analytics/stats', methods=['GET', 'OPTIONS'])
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    try:
        # Mock data for analytics
        stats = {
            "total_visits": 127,
            "unique_visitors": 89,
            "today_visits": 23,
            "bounce_rate": 0.34,
            "avg_session_duration": 240,
            "top_pages": [
                {"page": "/", "visits": 67},
                {"page": "/analytics.html", "visits": 34},
                {"page": "/api/checkup", "visits": 26}
            ],
            "devices": {
                "desktop": 0.65,
                "mobile": 0.28,
                "tablet": 0.07
            },
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        response = jsonify(stats)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return sanitize_private_network_header(response)
    except Exception as e:
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return sanitize_private_network_header(error_response), 500

@app.route('/api/analytics/full', methods=['GET', 'OPTIONS'])
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas (admin)"""
    try:
        full_stats = {
            "summary": {
                "total_visits": 127,
                "unique_visitors": 89,
                "conversion_rate": 0.12
            },
            "detailed_stats": [
                {"date": "2024-09-11", "visits": 45, "users": 32},
                {"date": "2024-09-10", "visits": 38, "users": 28},
                {"date": "2024-09-09", "visits": 44, "users": 29}
            ],
            "generated_at": datetime.datetime.now().isoformat()
        }
        
        response = jsonify(full_stats)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return sanitize_private_network_header(response)
    except Exception as e:
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return sanitize_private_network_header(error_response), 500

def handler(req):
    with app.test_request_context(path=req.path, method=req.method, 
                                   data=req.get_data(), headers=req.headers):
        return app.full_dispatch_request()