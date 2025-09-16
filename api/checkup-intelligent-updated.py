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
            
            # Gerar recomendações baseadas na idade, sexo e condições
            recommendations = []
            
            # Função auxiliar para adicionar recomendação com status
            def add_recommendation(rec_data, status=None):
                if status:
                    rec_data['status'] = status
                recommendations.append(rec_data)
            
            # Recomendações básicas para adultos
            if idade >= 18:
                # Hemograma completo
                add_recommendation({
                    'titulo': 'Hemograma completo, soro',
                    'descricao': 'Avaliação hematológica geral - Recomendado anualmente para adultos',
                    'prioridade': 'alta',
                    'referencia': 'SBC/SBD 2024',
                    'categoria': 'laboratorial'
                })
                
                # Glicemia de jejum
                add_recommendation({
                    'titulo': 'Glicose, soro',
                    'descricao': 'Rastreamento de diabetes - Recomendado a cada 3 anos para adultos',
                    'prioridade': 'alta',
                    'referencia': 'ADA/SBD 2024',
                    'categoria': 'laboratorial'
                })
                
                # Perfil lipídico separado em cards individuais
                add_recommendation({
                    'titulo': 'Colesterol total, soro',
                    'descricao': 'Avaliação do risco cardiovascular - Recomendado a cada 5 anos para adultos',
                    'prioridade': 'alta',
                    'referencia': 'SBC/ACC 2024',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'HDL colesterol, soro',
                    'descricao': 'Avaliação do risco cardiovascular complementar',
                    'prioridade': 'alta',
                    'referencia': 'SBC/ACC 2024',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'LDL colesterol, soro',
                    'descricao': 'Avaliação do risco cardiovascular complementar',
                    'prioridade': 'alta',
                    'referencia': 'SBC/ACC 2024',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'Triglicérides, soro',
                    'descricao': 'Avaliação do risco cardiovascular complementar',
                    'prioridade': 'alta',
                    'referencia': 'SBC/ACC 2024',
                    'categoria': 'laboratorial'
                })
            
            # Recomendações para condições específicas ou idade avançada
            if idade >= 60 or hipertensao or diabetes or cardiopatia:
                # Função renal - Creatinina e Ureia separadas
                add_recommendation({
                    'titulo': 'Creatinina (c/eGFR), soro',
                    'descricao': 'Avaliação da função renal - Indicado para hipertensão, diabetes, cardiopatia ou ≥60 anos',
                    'prioridade': 'alta',
                    'referencia': 'KDIGO 2024 / SBN 2023',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'Ureia, soro',
                    'descricao': 'Avaliação da função renal complementar',
                    'prioridade': 'alta',
                    'referencia': 'KDIGO 2024 / SBN 2023',
                    'categoria': 'laboratorial'
                })
            
            # Eletrólitos para hipertensão, diabetes, cardiopatia ou uso de diuréticos
            if hipertensao or diabetes or cardiopatia or uso_diureticos:
                # Eletrólitos separados em cards individuais
                add_recommendation({
                    'titulo': 'Sódio, soro',
                    'descricao': 'Dosagem de eletrólitos - Indicado para hipertensão, diabetes, cardiopatia ou uso de diuréticos',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2020 / KDIGO 2024',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'Potássio, soro',
                    'descricao': 'Dosagem de eletrólitos complementar',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2020 / KDIGO 2024',
                    'categoria': 'laboratorial'
                })
                
                add_recommendation({
                    'titulo': 'Cloro, soro',
                    'descricao': 'Dosagem de eletrólitos complementar',
                    'prioridade': 'alta',
                    'referencia': 'SBC 2020 / KDIGO 2024',
                    'categoria': 'laboratorial'
                })
            
            # HbA1c para diabetes ou pré-diabetes
            if diabetes or idade >= 45:
                add_recommendation({
                    'titulo': 'Hemoglobina glicada (HbA1c), soro',
                    'descricao': 'Controle glicêmico - Indicado para diabetes ou rastreamento em ≥45 anos',
                    'prioridade': 'alta',
                    'referencia': 'ADA/SBD 2024',
                    'categoria': 'laboratorial'
                })
            
            # Recomendações específicas por sexo
            if sexo == 'feminino' and idade >= 25:
                add_recommendation({
                    'titulo': 'Papanicolau',
                    'descricao': 'Rastreamento de câncer cervical - Recomendado a cada 3 anos',
                    'prioridade': 'alta',
                    'referencia': 'INCA/MS 2024',
                    'categoria': 'rastreamento'
                })
                
            if sexo == 'feminino' and idade >= 50:
                add_recommendation({
                    'titulo': 'Mamografia',
                    'descricao': 'Rastreamento de câncer de mama - Recomendado anualmente após os 50 anos',
                    'prioridade': 'alta',
                    'referencia': 'INCA/MS 2024',
                    'categoria': 'imagem'
                })
                
            if sexo == 'masculino' and idade >= 50:
                add_recommendation({
                    'titulo': 'PSA, soro',
                    'descricao': 'Rastreamento de câncer de próstata - Discutir com médico após os 50 anos',
                    'prioridade': 'media',
                    'referencia': 'SBU 2024',
                    'categoria': 'laboratorial'
                })
            
            # Exames de imagem para hipertensão resistente
            if hipertensao:
                add_recommendation({
                    'titulo': 'Ecocardiograma transtorácico',
                    'descricao': 'Avaliação de hipertrofia ventricular esquerda e função cardíaca em HAS resistente',
                    'prioridade': 'alta',
                    'referencia': 'AHA/ACC 2025',
                    'categoria': 'imagem'
                })
            
            # Vacinas para idosos
            if idade >= 60:
                add_recommendation({
                    'titulo': 'HD4V (Vacina p/Influenza de Alta dose - Efluelda®)',
                    'descricao': 'Dose anual Aplicar em dose única, INTRAMUSCULAR, anualmente. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Arexvy® e Shingrix®; de preferência, aguardar 15 dias de intervalo para vacinação com a QDenga®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                })
                
                add_recommendation({
                    'titulo': 'Hexavalente (HEXAXIM® ou Infanrix®)',
                    'descricao': '1 dose Aplicar dose única e reforço após 5 anos. * Não tem na rede pública',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
                })
                
                add_recommendation({
                    'titulo': 'Shingrix® (Vacina p/Herpes Zoster recombinada)',
                    'descricao': '2 doses Aplicar uma dose de 0,5ml, INTRAMUSCULAR e repetir segunda dose após 2 meses. Obs: Pode ser coadministrada com VPC13 ou VPC15®, Efluelda® e Arexvy®',
                    'prioridade': 'alta',
                    'referencia': 'SBIm/ANVISA 2024',
                    'categoria': 'vacina'
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
