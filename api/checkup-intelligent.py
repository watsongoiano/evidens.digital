from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _safe_int(value):
        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            value_str = str(value).strip()
            if not value_str:
                return None
            return int(float(value_str))
        except (ValueError, TypeError):
            return None

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # Resposta para GET requests (para testes)
        self._send_json({'message': 'API funcionando. Use POST para enviar dados.', 'status': 'ok'})

    def do_POST(self):
        try:
            # Ler dados do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if post_data else {}

            # Dados básicos do paciente
            idade = self._safe_int(data.get('idade'))
            if not idade or idade <= 0:
                self._send_json({'error': 'Idade inválida ou não informada'}, status=400)
                return
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
            
            response_data = {
                'recommendations': recommendations,
                'patient_data': data,
                'total_recommendations': len(recommendations)
            }

            self._send_json(response_data)

        except Exception as e:
            # Enviar erro
            self._send_json({'error': f'Erro interno: {str(e)}'}, status=500)
