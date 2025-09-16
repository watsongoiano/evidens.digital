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
            
            # Gerar recomendações básicas baseadas na idade e sexo
            recommendations = []
            
            # Recomendações básicas para adultos
            if idade >= 18:
                recommendations.append({
                    'titulo': 'Hemograma Completo',
                    'categoria': 'exame',
                    'subtitulo': 'Hemograma completo, soro',
                    'indicacao': 'Avaliação hematológica geral - Recomendado anualmente para adultos',
                    'grau_evidencia': 'A',
                    'referencia': 'SBC/SBD 2024'
                })
                
                recommendations.append({
                    'titulo': 'Glicemia de Jejum',
                    'categoria': 'exame',
                    'subtitulo': 'Glicose, soro',
                    'indicacao': 'Rastreamento de diabetes - Recomendado a cada 3 anos para adultos',
                    'grau_evidencia': 'A',
                    'referencia': 'ADA/SBD 2024'
                })
                
                recommendations.append({
                    'titulo': 'Perfil Lipídico',
                    'categoria': 'exame',
                    'subtitulo': 'Colesterol total, HDL, LDL, triglicérides, soro',
                    'indicacao': 'Avaliação do risco cardiovascular - Recomendado a cada 5 anos para adultos',
                    'grau_evidencia': 'A',
                    'referencia': 'SBC/ACC 2024'
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
