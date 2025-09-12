from flask import Flask, request, jsonify
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from routes.checkup_intelligent import generate_intelligent_recommendations

app = Flask(__name__)

@app.route('/checkup-intelligent', methods=['POST', 'OPTIONS'])
def handle_intelligent_checkup():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        response = generate_intelligent_recommendations()
        if hasattr(response, 'headers'):
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