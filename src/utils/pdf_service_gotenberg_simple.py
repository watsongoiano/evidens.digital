"""
Template simplificado para PDFs de solicitação de exames e prescrição de vacinas
"""

from datetime import datetime
from jinja2 import Template
import re

# Dicionário com informações de administração de vacinas
VACINAS_ADMINISTRACAO = {
    "influenza": {"doses": "1 dose anual", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "Anualmente", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, anualmente."},
    "gardasil": {"doses": "3 doses", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "0, 2 e 6 meses", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, no intervalo 0, 2 e 6 meses."},
    "hpv": {"doses": "3 doses", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "0, 2 e 6 meses", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, no intervalo 0, 2 e 6 meses."},
    "hepatite b": {"doses": "3 doses", "via": "INTRAMUSCULAR", "volume": "1,0ml", "intervalo": "0, 1 e 6 meses", "detalhes": "Aplicar uma dose (1,0ml), INTRAMUSCULAR, no intervalo 0, 1 e 6 meses."},
    "dtpa": {"doses": "1 dose", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "A cada 10 anos", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, com reforço a cada 10 anos."},
    "triplice viral": {"doses": "2 doses", "via": "SUBCUTÂNEA", "volume": "0,5ml", "intervalo": "0 e 1 mês", "detalhes": "Aplicar uma dose (0,5ml), SUBCUTÂNEA, no intervalo 0 e 1 mês."},
    "scr": {"doses": "2 doses", "via": "SUBCUTÂNEA", "volume": "0,5ml", "intervalo": "0 e 1 mês", "detalhes": "Aplicar uma dose (0,5ml), SUBCUTÂNEA, no intervalo 0 e 1 mês."},
    "hepatite a": {"doses": "2 doses", "via": "INTRAMUSCULAR", "volume": "1,0ml", "intervalo": "0 e 6 meses", "detalhes": "Aplicar uma dose (1,0ml), INTRAMUSCULAR, no intervalo 0 e 6 meses."},
    "febre amarela": {"doses": "1 dose", "via": "SUBCUTÂNEA", "volume": "0,5ml", "intervalo": "Dose única", "detalhes": "Aplicar uma dose (0,5ml), SUBCUTÂNEA, dose única."},
    "meningococica": {"doses": "1 dose", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "Dose única ou reforço conforme indicação", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, dose única ou reforço conforme indicação médica."},
    "dengue": {"doses": "2 doses", "via": "SUBCUTÂNEA", "volume": "0,5ml", "intervalo": "0 e 3 meses", "detalhes": "Aplicar uma dose (0,5ml), SUBCUTÂNEA, no intervalo 0 e 3 meses."},
    "covid": {"doses": "Conforme esquema vigente", "via": "INTRAMUSCULAR", "volume": "Conforme fabricante", "intervalo": "Conforme esquema vigente", "detalhes": "Aplicar conforme esquema vacinal vigente e orientação do Ministério da Saúde."},
    "varicela": {"doses": "2 doses", "via": "SUBCUTÂNEA", "volume": "0,5ml", "intervalo": "0 e 1-2 meses", "detalhes": "Aplicar uma dose (0,5ml), SUBCUTÂNEA, no intervalo 0 e 1-2 meses."},
    "pneumococica": {"doses": "1-2 doses", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "Conforme esquema", "detalhes": "Aplicar conforme esquema vacinal (VPC13 seguida de VPP23 após 2 meses)."},
    "herpes zoster": {"doses": "2 doses", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "0 e 2-6 meses", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, no intervalo 0 e 2-6 meses."},
    "twinrix": {"doses": "3 doses", "via": "INTRAMUSCULAR", "volume": "1,0ml", "intervalo": "0, 1 e 6 meses", "detalhes": "Aplicar uma dose (1,0ml), INTRAMUSCULAR, no intervalo 0, 1 e 6 meses."},
    "rsv": {"doses": "1 dose", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "Dose única", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, dose única."},
    "dt": {"doses": "1 dose", "via": "INTRAMUSCULAR", "volume": "0,5ml", "intervalo": "A cada 10 anos", "detalhes": "Aplicar uma dose (0,5ml), INTRAMUSCULAR, com reforço a cada 10 anos."}
}

def get_detalhes_administracao_vacina(titulo_vacina):
    """Retorna detalhes de administração da vacina baseado no título"""
    titulo_lower = titulo_vacina.lower()
    
    # Tentar match direto
    for key, info in VACINAS_ADMINISTRACAO.items():
        if key in titulo_lower:
            return info
    
    # Fallback
    return {"doses": "Conforme orientação médica", "via": "Conforme bula", "volume": "Conforme bula", "intervalo": "Conforme orientação médica", "detalhes": "Aplicar conforme orientação médica e bula do fabricante."}

def gerar_html_exames_simples(dados_paciente, exames, tipo_exame="LABORATORIAIS"):
    """Gera HTML simplificado para solicitação de exames"""
    
    # Determinar título baseado no tipo
    if tipo_exame == "LABORATORIAIS":
        titulo = "SOLICITAÇÃO DE EXAME"
    elif tipo_exame == "IMAGEM":
        titulo = "SOLICITAÇÃO DE EXAME"
    else:
        titulo = "SOLICITAÇÃO DE EXAME"
    
    template_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #000;
            }
            .header-box {
                border: 2px solid #000;
                padding: 10px;
                text-align: center;
                margin-bottom: 20px;
            }
            .header-box h1 {
                margin: 0;
                font-size: 14pt;
                font-weight: bold;
            }
            .clinic-info {
                margin-bottom: 20px;
            }
            .clinic-info p {
                margin: 3px 0;
            }
            .doctor-name {
                color: #2E7D32;
                font-weight: bold;
                margin-top: 10px;
            }
            .crm {
                text-align: right;
                font-weight: bold;
            }
            .patient-info {
                border-top: 1px solid #000;
                border-bottom: 1px solid #000;
                padding: 10px 0;
                margin: 20px 0;
            }
            .patient-info p {
                margin: 5px 0;
            }
            .exam-list {
                margin: 20px 0;
            }
            .exam-list h3 {
                font-size: 11pt;
                margin-bottom: 10px;
            }
            .exam-list ul {
                list-style-type: disc;
                margin-left: 20px;
            }
            .exam-list li {
                margin: 5px 0;
            }
            .signature-section {
                margin-top: 80px;
                text-align: center;
            }
            .signature-line {
                border-top: 1px solid #000;
                width: 300px;
                margin: 0 auto;
                padding-top: 5px;
                font-size: 10pt;
            }
        </style>
    </head>
    <body>
        <div class="header-box">
            <h1>{{ titulo }}</h1>
        </div>
        
        <div class="clinic-info">
            <p><strong>evidēns digital</strong></p>
            <p><strong>Data de emissão:</strong> {{ data_emissao }}</p>
        </div>
        
        <div class="patient-info">
            <p><strong>Paciente:</strong> {{ paciente_nome }}</p>
            <p><strong>Sexo:</strong> {{ paciente_sexo }} <strong>Idade:</strong> {{ paciente_idade }}</p>
        </div>
        
        <div class="exam-list">
            <p><strong>Solicito:</strong></p>
            <ul>
                {% for exam in exames %}
                <li>{{ exam.titulo }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="signature-section">
            <div class="signature-line">
                Assinatura e Carimbo do Médico
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(template_html)
    
    html = template.render(
        titulo=titulo,
        paciente_nome=dados_paciente.get('nome', 'Não informado'),
        paciente_idade=f"{dados_paciente.get('idade', 'Não informada')} anos" if dados_paciente.get('idade') else 'Não informada',
        paciente_sexo='Feminino' if dados_paciente.get('sexo') in ['F', 'feminino'] else 'Masculino',
        data_emissao=datetime.now().strftime('%d/%m/%Y'),
        exames=exames
    )
    
    return html


def gerar_html_prescricao_vacinas_simples(dados_paciente, vacinas):
    """Gera HTML simplificado para prescrição de vacinas (Receita Simples)"""
    
    template_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #000;
            }
            .header-box {
                border: 2px solid #000;
                padding: 10px;
                text-align: center;
                margin-bottom: 20px;
            }
            .header-box h1 {
                margin: 0;
                font-size: 14pt;
                font-weight: bold;
            }
            .clinic-info {
                margin-bottom: 20px;
            }
            .clinic-info p {
                margin: 3px 0;
            }
            .doctor-name {
                color: #2E7D32;
                font-weight: bold;
                margin-top: 10px;
            }
            .crm {
                text-align: right;
                font-weight: bold;
            }
            .patient-info {
                border-top: 1px solid #000;
                border-bottom: 1px solid #000;
                padding: 10px 0;
                margin: 20px 0;
            }
            .patient-info p {
                margin: 5px 0;
            }
            .vaccine-list {
                margin: 20px 0;
            }
            .vaccine-item {
                margin: 15px 0;
                padding-left: 20px;
            }
            .signature-section {
                margin-top: 80px;
                text-align: center;
            }
            .signature-line {
                border-top: 1px solid #000;
                width: 300px;
                margin: 0 auto;
                padding-top: 5px;
                font-size: 10pt;
            }
        </style>
    </head>
    <body>
        <div class="header-box">
            <h1>Receita Simples</h1>
        </div>
        
        <div class="clinic-info">
            <p><strong>evidēns digital</strong></p>
            <p><strong>Data de emissão:</strong> {{ data_emissao }}</p>
        </div>
        
        <div class="patient-info">
            <p><strong>Paciente:</strong> {{ paciente_nome }}</p>
            <p><strong>Sexo:</strong> {{ paciente_sexo }} <strong>Idade:</strong> {{ paciente_idade }}</p>
        </div>
        
        <div class="vaccine-list">
            {% for vaccine in vacinas %}
            <div class="vaccine-item">
                <p><strong>{{ loop.index }}. {{ vaccine.titulo|upper }}</strong> {{ vaccine.pontos }} {{ vaccine.doses }}</p>
                <p style="margin-left: 20px; font-size: 0.9em;">{{ vaccine.detalhes }}</p>
            </div>
            {% endfor %}
        </div>
        
        <div class="signature-section">
            <div class="signature-line">
                Assinatura e Carimbo do Médico
            </div>
        </div>
    </body>
    </html>
    """
    
    # Adicionar detalhes de administração a cada vacina
    vacinas_com_detalhes = []
    max_titulo_length = 0
    
    # Primeira passagem: encontrar o título mais longo
    for vacina in vacinas:
        titulo = vacina.get('titulo', 'Vacina')
        titulo_length = len(titulo)
        if titulo_length > max_titulo_length:
            max_titulo_length = titulo_length
    
    # Segunda passagem: criar vacinas com pontos alinhados
    for vacina in vacinas:
        titulo = vacina.get('titulo', 'Vacina')
        detalhes_admin = get_detalhes_administracao_vacina(titulo)
        
        # Calcular quantidade de pontos necessária para alinhamento
        # Fórmula: pontos base (50) + diferença de comprimento
        titulo_length = len(titulo)
        pontos_necessarios = 50 + (max_titulo_length - titulo_length)
        pontos = '.' * pontos_necessarios
        
        vacina_completa = {
            'titulo': titulo,
            'pontos': pontos,
            'doses': detalhes_admin['doses'],
            'detalhes': detalhes_admin['detalhes']
        }
        vacinas_com_detalhes.append(vacina_completa)
    
    template = Template(template_html)
    
    html = template.render(
        paciente_nome=dados_paciente.get('nome', 'Não informado'),
        paciente_idade=f"{dados_paciente.get('idade', 'Não informada')} anos" if dados_paciente.get('idade') else 'Não informada',
        paciente_sexo='Feminino' if dados_paciente.get('sexo') in ['F', 'feminino'] else 'Masculino',
        data_emissao=datetime.now().strftime('%d/%m/%Y'),
        vacinas=vacinas_com_detalhes
    )
    
    return html

