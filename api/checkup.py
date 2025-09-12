import sys
import os
import json

# Add the src directory to the path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def handler(request):
    if request.method == 'POST':
        try:
            # Import here to avoid issues
            from src.routes.checkup import gerar_recomendacoes
            from flask import Flask
            
            app = Flask(__name__)
            with app.app_context():
                with app.test_request_context(
                    path='/api/checkup', 
                    method='POST',
                    data=request.get_data(),
                    content_type='application/json'
                ):
                    return gerar_recomendacoes()
        except Exception as e:
            return {
                'error': str(e)
            }, 500
    
    return {'error': 'Method not allowed'}, 405