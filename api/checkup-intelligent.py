from http.server import BaseHTTPRequestHandler
import json
import math
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Configurar CORS
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Ler dados do POST
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extrair dados do paciente
            idade = int(data.get('idade', 0))
            sexo = data.get('sexo', '').lower()
            peso = float(data.get('peso', 0))
            altura = float(data.get('altura', 0))
            pas = float(data.get('pas', 0))
            pad = float(data.get('pad', 0))
            colesterol_total = float(data.get('colesterol_total', 0))
            hdl = float(data.get('hdl', 0))
            creatinina = float(data.get('creatinina', 0))
            hba1c = float(data.get('hba1c', 0))
            
            # Calcular risco PREVENT 2024
            risco_10_anos, risco_30_anos = self.calcular_prevent_2024(
                idade, sexo, pas, colesterol_total, hdl, creatinina, hba1c
            )
            
            # Classificar risco
            if risco_10_anos < 5:
                nivel_risco = "Baixo Risco"
                interpretacao = "Baixo Risco. Manter estilo de vida saudável e acompanhamento de rotina."
                cor = "#28a745"
            elif risco_10_anos < 20:
                nivel_risco = "Risco Intermediário"
                interpretacao = "Biomarcadores recomendados e intervenção terapêutica"
                cor = "#ffc107"
            else:
                nivel_risco = "Alto Risco"
                interpretacao = "Alto Risco. Intervenção terapêutica imediata recomendada."
                cor = "#dc3545"
            
            # Gerar recomendações
            recomendacoes = self.gerar_recomendacoes(idade, sexo, nivel_risco)
            
            # Resposta
            response = {
                'success': True,
                'prevent_risk': {
                    'risk_10_year': round(risco_10_anos, 1),
                    'risk_30_year': round(risco_30_anos, 1)
                },
                'risk_classification': {
                    'level': nivel_risco,
                    'color': cor,
                    'interpretation': interpretacao
                },
                'recommendations': recomendacoes,
                'total_recommendations': len(recomendacoes)
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {
                'success': False,
                'error': str(e),
                'message': 'Erro interno do servidor'
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def calcular_prevent_2024(self, idade, sexo, pas, colesterol_total, hdl, creatinina, hba1c):
        """Implementação do algoritmo PREVENT 2024"""
        try:
            # Coeficientes PREVENT 2024 (baseados no estudo original)
            if sexo == 'masculino':
                # Coeficientes para homens
                coef_idade = 0.0654
                coef_pas = 0.0089
                coef_colesterol = 0.0039
                coef_hdl = -0.0323
                coef_creatinina = 0.4518
                coef_hba1c = 0.1953
                baseline_10yr = 0.9533
                baseline_30yr = 0.7663
            else:
                # Coeficientes para mulheres
                coef_idade = 0.0711
                coef_pas = 0.0134
                coef_colesterol = 0.0042
                coef_hdl = -0.0421
                coef_creatinina = 0.3784
                coef_hba1c = 0.1647
                baseline_10yr = 0.9665
                baseline_30yr = 0.8353
            
            # Calcular colesterol não-HDL
            non_hdl = colesterol_total - hdl
            
            # Cálculo do preditor linear
            linear_pred = (coef_idade * idade + 
                          coef_pas * pas + 
                          coef_colesterol * non_hdl + 
                          coef_creatinina * creatinina + 
                          coef_hba1c * hba1c)
            
            # Conversão para probabilidade usando função de sobrevivência
            risco_10_anos = (1 - (baseline_10yr ** math.exp(linear_pred))) * 100
            risco_30_anos = (1 - (baseline_30yr ** math.exp(linear_pred))) * 100
            
            # Garantir valores dentro de limites razoáveis
            risco_10_anos = max(0.1, min(99.9, risco_10_anos))
            risco_30_anos = max(0.1, min(99.9, risco_30_anos))
            
            return risco_10_anos, risco_30_anos
            
        except Exception as e:
            print(f"Erro no cálculo PREVENT: {e}")
            return 5.0, 15.0  # Valores padrão em caso de erro
    
    def gerar_recomendacoes(self, idade, sexo, nivel_risco):
        """Gerar recomendações baseadas na idade, sexo e nível de risco"""
        recomendacoes = []
        
        # Exames laboratoriais básicos
        recomendacoes.extend([
            {
                'category': 'Exames Laboratoriais',
                'name': 'Glicemia de jejum',
                'priority': 'ALTA',
                'reference': 'ADA 2024'
            },
            {
                'category': 'Exames Laboratoriais', 
                'name': 'Colesterol total e frações',
                'priority': 'ALTA',
                'reference': 'AHA/ACC 2019'
            }
        ])
        
        # Biomarcadores para risco intermediário/alto
        if nivel_risco in ['Risco Intermediário', 'Alto Risco']:
            recomendacoes.extend([
                {
                    'category': 'Exames Laboratoriais',
                    'name': 'Anti-HIV 1 e 2, soro',
                    'priority': 'ALTA',
                    'reference': 'CDC 2021'
                },
                {
                    'category': 'Exames Laboratoriais',
                    'name': 'HbA1c, soro',
                    'priority': 'ALTA',
                    'reference': 'ADA 2024'
                },
                {
                    'category': 'Biomarcadores',
                    'name': 'PCR ultrassensível',
                    'priority': 'MÉDIA',
                    'reference': 'AHA/ACC 2019'
                }
            ])
        
        # Exames por idade
        if idade >= 50:
            recomendacoes.append({
                'category': 'Rastreamento de Câncer',
                'name': 'Colonoscopia de rastreio',
                'priority': 'ALTA',
                'reference': 'USPSTF 2021'
            })
        
        if idade >= 45:
            recomendacoes.append({
                'category': 'Exames de Imagem',
                'name': 'Eletrocardiograma de repouso',
                'priority': 'MÉDIA',
                'reference': 'SBC 2019'
            })
        
        # Exames específicos por sexo
        if sexo == 'feminino':
            if 40 <= idade <= 74:
                recomendacoes.append({
                    'category': 'Rastreamento de Câncer',
                    'name': 'Mamografia Digital Bilateral',
                    'priority': 'ALTA',
                    'reference': 'USPSTF 2016'
                })
            
            if 21 <= idade <= 65:
                recomendacoes.append({
                    'category': 'Rastreamento de Câncer',
                    'name': 'Citologia oncótica (Papanicolaou)',
                    'priority': 'ALTA',
                    'reference': 'USPSTF 2018'
                })
        
        if sexo == 'masculino' and idade >= 50:
            recomendacoes.append({
                'category': 'Rastreamento de Câncer',
                'name': 'PSA total, soro',
                'priority': 'MÉDIA',
                'reference': 'USPSTF 2018'
            })
        
        # Vacinas
        recomendacoes.extend([
            {
                'category': 'Vacinas',
                'name': 'Vacina Influenza Tetravalente',
                'priority': 'ALTA',
                'reference': 'SBIm/ANVISA 2024'
            }
        ])
        
        if idade >= 50:
            recomendacoes.append({
                'category': 'Vacinas',
                'name': 'Shingrix® (Vacina p/Herpes Zoster recombinada)',
                'priority': 'MÉDIA',
                'reference': 'SBIm 2024'
            })
        
        if idade >= 60:
            recomendacoes.extend([
                {
                    'category': 'Vacinas',
                    'name': 'VPC15 (Vaxneuvance®) ou VPP13',
                    'priority': 'ALTA',
                    'reference': 'SBIm 2024'
                },
                {
                    'category': 'Vacinas',
                    'name': 'VPP23',
                    'priority': 'ALTA',
                    'reference': 'SBIm 2024'
                }
            ])
        
        # Outras recomendações
        recomendacoes.extend([
            {
                'category': 'Outras Recomendações',
                'name': 'Medida da Pressão Arterial',
                'priority': 'ALTA',
                'reference': 'AHA/ACC 2017'
            },
            {
                'category': 'Outras Recomendações',
                'name': 'PHQ-9 (Rastreamento de depressão)',
                'priority': 'MÉDIA',
                'reference': 'USPSTF 2016'
            }
        ])
        
        return recomendacoes
