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

    def _add_recommendation(self, recommendations, titulo, descricao, prioridade, referencia, categoria, grau_evidencia='A'):
        """Adiciona uma recomendação à lista, evitando duplicatas"""
        # Verificar se já existe
        for rec in recommendations:
            if rec['titulo'] == titulo:
                return
        
        rec = {
            'titulo': titulo,
            'categoria': categoria,
            'subtitulo': titulo,  # Nome científico do exame
            'indicacao': descricao,
            'grau_evidencia': grau_evidencia,
            'referencia': referencia,
            'prioridade': prioridade
        }
        recommendations.append(rec)

    def _add_laboratorial_exams(self, recommendations, idade, sexo, comorbidades, status='alta'):
        """Adiciona exames laboratoriais baseados na idade, sexo e comorbidades"""
        
        # Exames básicos para adultos
        if idade >= 18:
            # Hemograma completo
            self._add_recommendation(
                recommendations,
                'Hemograma completo, soro',
                'Avaliação hematológica geral - Recomendado anualmente para adultos',
                status,
                'SBC/SBD 2024',
                'laboratorial',
                'A'
            )
            
            # Glicemia de jejum
            self._add_recommendation(
                recommendations,
                'Glicose, soro',
                'Rastreamento de diabetes - Recomendado a cada 3 anos para adultos',
                status,
                'ADA/SBD 2024',
                'laboratorial',
                'A'
            )
            
            # Perfil lipídico completo
            self._add_recommendation(
                recommendations,
                'Colesterol total, soro',
                'Avaliação do risco cardiovascular - Recomendado a cada 5 anos',
                status,
                'SBC/ACC 2024',
                'laboratorial',
                'A'
            )
            
            self._add_recommendation(
                recommendations,
                'HDL colesterol, soro',
                'Avaliação do risco cardiovascular - Componente do perfil lipídico',
                status,
                'SBC/ACC 2024',
                'laboratorial',
                'A'
            )
            
            self._add_recommendation(
                recommendations,
                'LDL colesterol, soro',
                'Avaliação do risco cardiovascular - Principal alvo terapêutico',
                status,
                'SBC/ACC 2024',
                'laboratorial',
                'A'
            )
            
            self._add_recommendation(
                recommendations,
                'Triglicérides, soro',
                'Avaliação do risco cardiovascular - Componente do perfil lipídico',
                status,
                'SBC/ACC 2024',
                'laboratorial',
                'A'
            )

        # Exames para hipertensão, diabetes, cardiopatia ou ≥60 anos
        if 'hipertensao' in comorbidades or 'diabetes_tipo_2' in comorbidades or 'cardiopatia' in comorbidades or idade >= 60:
            # Função renal
            self._add_recommendation(
                recommendations,
                'Creatinina (c/eGFR), soro',
                'Avaliação da função renal - Indicado para hipertensão, diabetes, cardiopatia ou ≥60 anos',
                status,
                'KDIGO 2024 / SBN 2023',
                'laboratorial',
                'A'
            )
            
            # Adicionar Ureia separadamente
            self._add_recommendation(
                recommendations,
                'Ureia, soro',
                'Avaliação da função renal complementar',
                status,
                'KDIGO 2024 / SBN 2023',
                'laboratorial',
                'A'
            )
            
            # Eletrólitos
            self._add_recommendation(
                recommendations,
                'Sódio, soro',
                'Dosagem de eletrólitos - Indicado para hipertensão, diabetes, cardiopatia ou uso de diuréticos',
                status,
                'SBC 2020 / KDIGO 2024',
                'laboratorial',
                'A'
            )
            
            # Adicionar Potássio separadamente
            self._add_recommendation(
                recommendations,
                'Potássio, soro',
                'Dosagem de eletrólitos complementar',
                status,
                'SBC 2020 / KDIGO 2024',
                'laboratorial',
                'A'
            )
            
            # Adicionar Cloro separadamente
            self._add_recommendation(
                recommendations,
                'Cloro, soro',
                'Dosagem de eletrólitos complementar',
                status,
                'SBC 2020 / KDIGO 2024',
                'laboratorial',
                'A'
            )

        # Exames específicos para diabetes
        if 'diabetes_tipo_2' in comorbidades:
            self._add_recommendation(
                recommendations,
                'HbA1c (%)',
                'Controle glicêmico - Recomendado a cada 3-6 meses para diabéticos',
                status,
                'ADA/SBD 2024',
                'laboratorial',
                'A'
            )
            
            self._add_recommendation(
                recommendations,
                'Microalbuminúria, urina',
                'Rastreamento de nefropatia diabética - Anual para diabéticos',
                status,
                'ADA/KDIGO 2024',
                'laboratorial',
                'A'
            )

    def _add_imaging_exams(self, recommendations, idade, sexo, comorbidades, historia_familiar, tabagismo, status='alta'):
        """Adiciona exames de imagem baseados nos critérios clínicos"""
        
        # Rastreamento de câncer de mama (mulheres 40-74 anos)
        if sexo == 'feminino' and 40 <= idade <= 74:
            self._add_recommendation(
                recommendations,
                'Mamografia bilateral',
                'Rastreamento de câncer de mama - Recomendado a cada 2 anos entre 40-74 anos',
                status,
                'USPSTF 2024 / INCA 2024',
                'imagem',
                'B'
            )

        # Rastreamento de câncer colorretal (45-75 anos)
        if 45 <= idade <= 75:
            grau = 'A' if idade >= 50 else 'B'
            self._add_recommendation(
                recommendations,
                'Colonoscopia',
                f'Rastreamento de câncer colorretal - Recomendado a cada 10 anos entre 45-75 anos',
                status,
                'USPSTF 2024 / SBC 2024',
                'imagem',
                grau
            )

        # Rastreamento de câncer de pulmão (fumantes/ex-fumantes)
        if 50 <= idade <= 80 and tabagismo.get('status') in ['fumante', 'ex-fumante']:
            macos_ano = tabagismo.get('macos_ano', 0)
            anos_parou = tabagismo.get('anos_desde_parou', 0)
            
            if macos_ano >= 20 and (tabagismo.get('status') == 'fumante' or anos_parou <= 15):
                self._add_recommendation(
                    recommendations,
                    'Tomografia de tórax (baixa dose)',
                    'Rastreamento de câncer de pulmão - Para fumantes/ex-fumantes com ≥20 maços-ano',
                    status,
                    'USPSTF 2024 / INCA 2024',
                    'imagem',
                    'B'
                )

        # Aneurisma de aorta abdominal (homens 65-75 anos que já fumaram)
        if sexo == 'masculino' and 65 <= idade <= 75 and tabagismo.get('status') in ['fumante', 'ex-fumante']:
            self._add_recommendation(
                recommendations,
                'Ultrassom de aorta abdominal',
                'Rastreamento de aneurisma de aorta abdominal - Para homens 65-75 anos que já fumaram',
                status,
                'USPSTF 2024 / SBC 2024',
                'imagem',
                'B'
            )

        # Densitometria óssea (mulheres ≥65 anos)
        if sexo == 'feminino' and idade >= 65:
            self._add_recommendation(
                recommendations,
                'Densitometria óssea',
                'Rastreamento de osteoporose - Recomendado para mulheres ≥65 anos',
                status,
                'USPSTF 2024 / ABRASSO 2024',
                'imagem',
                'B'
            )

    def _add_vaccines(self, recommendations, idade, sexo, comorbidades, status='alta'):
        """Adiciona recomendações de vacinas baseadas na idade e comorbidades"""
        
        # Vacina da gripe (anual para todos)
        self._add_recommendation(
            recommendations,
            'Vacina Influenza (anual)',
            'Prevenção de influenza - Recomendado anualmente para todos os adultos',
            status,
            'SBIm 2024 / CDC 2024',
            'vacina',
            'A'
        )

        # Vacina pneumocócica (≥65 anos ou comorbidades)
        if idade >= 65 or any(comorb in comorbidades for comorb in ['diabetes_tipo_2', 'cardiopatia', 'doenca_pulmonar']):
            self._add_recommendation(
                recommendations,
                'Vacina Pneumocócica',
                'Prevenção de pneumonia - Recomendado para ≥65 anos ou comorbidades',
                status,
                'SBIm 2024 / CDC 2024',
                'vacina',
                'A'
            )

        # Vacina Herpes Zóster (≥50 anos)
        if idade >= 50:
            self._add_recommendation(
                recommendations,
                'Vacina Herpes Zóster',
                'Prevenção de herpes zóster - Recomendado para ≥50 anos',
                status,
                'SBIm 2024 / CDC 2024',
                'vacina',
                'B'
            )

    def do_POST(self):
        try:
            # Ler dados do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
            
            # Extrair dados do paciente
            idade = int(data.get('idade', 0))
            sexo = data.get('sexo', '').lower()
            comorbidades = data.get('comorbidades', [])
            historia_familiar = data.get('historia_familiar', [])
            tabagismo = data.get('tabagismo', {'status': 'nunca_fumou', 'macos_ano': 0, 'anos_desde_parou': 0})
            
            # Inicializar lista de recomendações
            recommendations = []
            
            # Adicionar exames laboratoriais
            self._add_laboratorial_exams(recommendations, idade, sexo, comorbidades)
            
            # Adicionar exames de imagem
            self._add_imaging_exams(recommendations, idade, sexo, comorbidades, historia_familiar, tabagismo)
            
            # Adicionar vacinas
            self._add_vaccines(recommendations, idade, sexo, comorbidades)
            
            # Ordenar por prioridade (alta primeiro)
            recommendations.sort(key=lambda x: (x['prioridade'] != 'alta', x['categoria'], x['titulo']))
            
            response_data = {
                'recommendations': recommendations,
                'patient_data': data,
                'total_recommendations': len(recommendations),
                'algorithm_version': '2.0_evidens_enhanced'
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
            error_response = {'error': f'Erro interno: {str(e)}', 'details': str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
