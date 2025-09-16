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
            
            # 3. RASTREAMENTO DE HIV - USPSTF 2019 (Grau A)
            # Critérios: Adolescentes e adultos de 15 a 65 anos
            if 15 <= idade <= 65:
                add_recommendation({
                    'titulo': 'Rastreamento da Infecção pelo HIV (Adolescentes e Adultos)',
                    'descricao': 'Rastrear adolescentes e adultos de 15 a 65 anos com imunoensaio de antígeno/anticorpo para HIV. Pessoas mais jovens ou mais velhas com risco aumentado de infecção também devem ser rastreadas.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2019',
                    'site_referencia': 'https://doi.org/10.1001/jama.2019.6587',
                    'categoria': 'laboratorial'
                })
            
            # 4. RASTREAMENTO DE HIV EM GESTANTES - USPSTF 2019 (Grau A)
            # Critérios: Todas as gestantes
            gestante = data.get('gestante') == 'on'
            if gestante:
                add_recommendation({
                    'titulo': 'Rastreamento da Infecção pelo HIV (Gestantes)',
                    'descricao': 'Rastrear todas as gestantes para infecção pelo HIV, incluindo aquelas que se apresentam em trabalho de parto com estado sorológico desconhecido. Nesses casos, utilizar um teste rápido de HIV.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2019',
                    'site_referencia': 'https://doi.org/10.1001/jama.2019.6587',
                    'categoria': 'laboratorial'
                })
            
            # 5. RASTREAMENTO DE ANEURISMA DE AORTA ABDOMINAL (AAA) - USPSTF 2019 (Grau B)
            # Critérios: Homens de 65-75 anos que já fumaram alguma vez (≥100 cigarros)
            historico_tabagismo = data.get('historico_tabagismo') == 'on'
            if (sexo == 'masculino' and 
                65 <= idade <= 75 and 
                historico_tabagismo):
                
                add_recommendation({
                    'titulo': 'Doppler Arterial de Aorta Abdominal',
                    'descricao': 'Realizar rastreamento único com ultrassonografia para aneurisma de aorta abdominal em homens de 65 a 75 anos que já fumaram alguma vez na vida (100 ou mais cigarros).',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2019',
                    'site_referencia': 'https://doi.org/10.1001/jama.2019.18928',
                    'categoria': 'imagem'
                })
            
            # 6. RASTREAMENTO DE OSTEOPOROSE - MULHERES ≥65 ANOS - USPSTF 2025 (Grau B)
            # Critérios: Mulheres com 65 anos ou mais
            if sexo == 'feminino' and idade >= 65:
                add_recommendation({
                    'titulo': 'Rastreamento de Osteoporose (Mulheres ≥ 65 anos)',
                    'descricao': 'Rastrear mulheres com 65 anos ou mais para osteoporose, a fim de prevenir fraturas osteoporóticas. O rastreamento é feito com densitometria óssea (DXA) da coluna ou quadril.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2025',
                    'site_referencia': 'https://doi.org/10.1001/jama.2024.27154',
                    'categoria': 'imagem'
                })
            
            # 7. RASTREAMENTO DE OSTEOPOROSE - MULHERES PÓS-MENOPAUSA <65 ANOS - USPSTF 2025 (Grau B)
            # Critérios: Mulheres pós-menopausa <65 anos com risco aumentado
            pos_menopausa = data.get('pos_menopausa') == 'on'
            risco_osteoporose = data.get('risco_osteoporose') == 'on'
            if (sexo == 'feminino' and 
                idade < 65 and 
                pos_menopausa and 
                risco_osteoporose):
                
                add_recommendation({
                    'titulo': 'Rastreamento de Osteoporose (Mulheres Pós-Menopausa < 65 anos)',
                    'descricao': 'Rastrear mulheres na pós-menopausa com menos de 65 anos que tenham risco aumentado de fratura osteoporótica. O risco deve ser estimado por uma ferramenta de avaliação de risco clínico antes do exame.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2025',
                    'site_referencia': 'https://doi.org/10.1001/jama.2024.27154',
                    'categoria': 'imagem'
                })
            
            # 8. RASTREAMENTO DE SÍFILIS - USPSTF 2022 (Grau A)
            # Critérios: Adolescentes e adultos não gestantes com risco aumentado
            risco_sifilis = data.get('risco_sifilis') == 'on'
            if (idade >= 15 and 
                not gestante and 
                risco_sifilis):
                
                add_recommendation({
                    'titulo': 'Rastreamento de Infecção por Sífilis (Não gestantes)',
                    'descricao': 'Rastrear adolescentes e adultos não gestantes com risco aumentado de infecção, como homens que fazem sexo com homens, pessoas com HIV, histórico de encarceramento ou trabalho sexual. Pelo menos anual para homens que fazem sexo com homens e pessoas com HIV.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2022',
                    'site_referencia': 'https://doi.org/10.1001/jama.2022.15322',
                    'categoria': 'laboratorial'
                })
            
            # 9. RASTREAMENTO DE TUBERCULOSE LATENTE - USPSTF 2023 (Grau B)
            # Critérios: Adultos assintomáticos ≥18 anos com risco aumentado
            risco_tuberculose = data.get('risco_tuberculose') == 'on'
            if (idade >= 18 and 
                risco_tuberculose):
                
                add_recommendation({
                    'titulo': 'Rastreamento de Tuberculose Latente (Adultos de Risco)',
                    'descricao': 'Rastrear adultos assintomáticos com risco aumentado de infecção, como pessoas que nasceram ou viveram em países de alta prevalência ou em ambientes de alto risco (ex: abrigos, presídios). Teste cutâneo de tuberculina (PPD/TST) ou Ensaio de liberação de interferon-gama (IGRA).',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2023',
                    'site_referencia': 'https://doi.org/10.1001/jama.2023.4899',
                    'categoria': 'laboratorial'
                })
            
            # 10. RASTREAMENTO DE CLAMÍDIA E GONORREIA - USPSTF 2021 (Grau B)
            # Critérios: Mulheres sexualmente ativas ≤24 anos OU ≥25 anos com risco aumentado
            sexualmente_ativa = data.get('sexualmente_ativa') == 'on'
            risco_ist = data.get('risco_ist') == 'on'
            
            if (sexo == 'feminino' and 
                sexualmente_ativa and 
                (idade <= 24 or (idade >= 25 and risco_ist))):
                
                add_recommendation({
                    'titulo': 'Rastreamento de Clamídia e Gonorreia (Mulheres)',
                    'descricao': 'Rastrear todas as mulheres (incluindo gestantes) sexualmente ativas com 24 anos ou menos, e mulheres com 25 anos ou mais que apresentem risco aumentado de infecção. Teste de Amplificação de Ácidos Nucleicos (NAAT) para Gonorreia e Clamídia.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021',
                    'site_referencia': 'https://doi.org/10.1001/jama.2021.14081',
                    'categoria': 'laboratorial'
                })
            
            # 11. RASTREAMENTO DE CÂNCER COLORRETAL (45-75 anos) - USPSTF 2021 (Grau A/B)
            # Critérios: Adultos 45-75 anos com risco médio
            if 45 <= idade <= 75:
                add_recommendation({
                    'titulo': 'Rastreamento de Câncer Colorretal (45 a 75 anos)',
                    'descricao': 'Rastrear todos os adultos com risco médio para câncer colorretal. Testes de fezes (FIT, gFOBT de alta sensibilidade, sDNA-FIT) ou Colonoscopia ou Colonografia por TC ou Sigmoidoscopia flexível (isolada ou com FIT). A escolha do teste deve considerar as preferências do paciente e a disponibilidade do método.',
                    'prioridade': 'alta',
                    'referencia': 'USPSTF 2021',
                    'site_referencia': 'https://doi.org/10.1001/jama.2021.6238',
                    'categoria': 'rastreamento'
                })
            
            # 12. RASTREAMENTO SELETIVO DE CÂNCER COLORRETAL (76-85 anos) - USPSTF 2021 (Grau C)
            # Critérios: Adultos 76-85 anos com decisão individualizada
            if 76 <= idade <= 85:
                add_recommendation({
                    'titulo': 'Rastreamento Seletivo de Câncer Colorretal (76 a 85 anos)',
                    'descricao': 'Oferecer seletivamente o rastreamento, com decisão individualizada baseada na saúde geral, histórico de rastreamento prévio e preferências do paciente. Testes de fezes (FIT, gFOBT de alta sensibilidade, sDNA-FIT) ou Colonoscopia ou Colonografia por TC ou Sigmoidoscopia flexível (isolada ou com FIT).',
                    'prioridade': 'media',
                    'referencia': 'USPSTF 2021',
                    'site_referencia': 'https://doi.org/10.1001/jama.2021.6238',
                    'categoria': 'rastreamento'
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
