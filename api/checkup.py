import json
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def handler(request):
    try:
        if request.method != 'POST':
            return json.dumps({'error': 'Method not allowed'}), 405
        
        # Get request data
        if hasattr(request, 'get_json'):
            data = request.get_json()
        else:
            body = request.get_data(as_text=True) if hasattr(request, 'get_data') else request.data
            data = json.loads(body) if body else {}
        
        # Mock Flask request context
        class MockRequest:
            def __init__(self, data):
                self._json = data
                self.method = 'POST'
            
            def get_json(self):
                return self._json
        
        # Import and execute
        import routes.checkup as checkup_module
        
        # Temporarily replace Flask's request
        original_request = None
        try:
            import flask
            original_request = getattr(flask, 'request', None)
            flask.request = MockRequest(data)
        except:
            pass
        
        # Generate recommendations
        result = checkup_module.gerar_recomendacoes()
        
        # Restore original request
        if original_request:
            flask.request = original_request
        
        return result
        
    except Exception as e:
        return json.dumps({'error': str(e)}), 500