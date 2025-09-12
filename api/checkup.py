from flask import Flask, request, jsonify
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the checkup route
from routes.checkup import gerar_recomendacoes

# Create Flask app instance
app = Flask(__name__)

@app.route('/api/checkup', methods=['POST', 'OPTIONS'])
def handle_checkup():
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        # Add CORS headers
        response = gerar_recomendacoes()
        if hasattr(response, 'headers'):
            response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

# Vercel handler
def handler(req):
    with app.test_request_context(path=req.path, method=req.method, 
                                   data=req.get_data(), headers=req.headers):
        return app.full_dispatch_request()