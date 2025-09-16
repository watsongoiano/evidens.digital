from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # Resposta para GET requests (para testes)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'message': 'API funcionando. Use POST para enviar dados.', 'status': 'ok'}
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_POST(self):
        try:
            # Ler dados do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
            
            # Dados básicos do paciente
            idade = int(data.get('idade', 0))
            sexo = data.get('sexo', '')
            
            # Condições médicas
            hipertensao = data.get('hipertensao') == 'on'
            diabetes = data.get('diabetes_tipo2') == 'on'
            cardiopatia = data.get('cardiopatia') == 'on'
            uso_diureticos = data.get('diureticos') == 'on'
            
            # Sistema limpo - aguardando novas diretrizes baseadas em evidências científicas
            recommendations = []
            
            # Função auxiliar para adicionar recomendação
            def add_recommendation(rec_data):
                recommendations.append(rec_data)
            
            # ÁREA PARA NOVAS RECOMENDAÇÕES BASEADAS EM GUIDELINES
            # Todas as recomendações foram removidas para reconstrução baseada em evidências científicas
            
            # Placeholder: Sistema aguardando implementação de novas diretrizes
            # As recomendações serão adicionadas conforme as guidelines fornecidas
            
            response_data = {
                'recommendations': recommendations,
                'patient_data': data,
                'total_recommendations': len(recommendations)
            }
            
            # Enviar resposta
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            # Enviar erro
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {'error': f'Erro interno: {str(e)}'}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
