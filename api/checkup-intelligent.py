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
            
            # RECOMENDAÇÕES BASEADAS EM GUIDELINES E EVIDÊNCIAS CIENTÍFICAS
            
            # 1. RASTREAMENTO DE CÂNCER DE PULMÃO - USPSTF 2021 (Grau B)
            # Critérios: 50-80 anos + 20 maços-ano + fumante atual ou parou ≤15 anos
            tabagismo_atual = data.get('tabagismo_atual') == 'on'
            ex_fumante = data.get('ex_fumante') == 'on'
            anos_parou_fumar = int(data.get('anos_parou_fumar', 999)) if data.get('anos_parou_fumar') else 999
            macos_ano = int(data.get('macos_ano', 0)) if data.get('macos_ano') else 0
            
            # Aplicar critérios USPSTF para TCBD
            if (50 <= idade <= 80 and 
                macos_ano >= 20 and 
                (tabagismo_atual or (ex_fumante and anos_parou_fumar <= 15))):
                
                add_recommendation({
                    'titulo': 'Tomografia Computadorizada de Tórax de Baixa Dose (TCBD)',
                    'descricao': 'Recomenda-se o rastreamento anual com TCBD em adultos de 50 a 80 anos com histórico de tabagismo de 20 maços-ano que fumam ou pararam nos últimos 15 anos. O rastreamento deve ser interrompido se a pessoa parar de fumar por 15 anos ou desenvolver problemas de saúde que limitem a expectativa de vida ou a cirurgia curativa.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021',
                    'site_referencia': 'https://doi.org/10.1001/jama.2021.1117',
                    'categoria': 'imagem'
                })
            
            # 2. RASTREAMENTO DE HEPATITE C - USPSTF 2020 (Grau B)
            # Critérios: Adultos de 18 a 79 anos - rastreamento universal
            if 18 <= idade <= 79:
                add_recommendation({
                    'titulo': 'Rastreamento da Infecção pelo Vírus da Hepatite C (HCV)',
                    'descricao': 'Rastrear adultos de 18 a 79 anos com teste de anticorpos anti-HCV. A maioria dos adultos necessita de um único rastreamento, com testes periódicos para pessoas com risco contínuo de infecção',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2020',
                    'site_referencia': 'https://doi.org/10.1001/jama.2020.1123',
                    'categoria': 'laboratorial'
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
