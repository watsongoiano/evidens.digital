"""
Template simplificado para PDFs de solicitação de exames e prescrição de vacinas
"""

from datetime import datetime
from jinja2 import Template

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
                <p><strong>{{ loop.index }}. {{ vaccine.titulo }}</strong></p>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    template = Template(template_html)
    
    html = template.render(
        paciente_nome=dados_paciente.get('nome', 'Não informado'),
        paciente_idade=f"{dados_paciente.get('idade', 'Não informada')} anos" if dados_paciente.get('idade') else 'Não informada',
        paciente_sexo='Feminino' if dados_paciente.get('sexo') in ['F', 'feminino'] else 'Masculino',
        data_emissao=datetime.now().strftime('%d/%m/%Y'),
        vacinas=vacinas
    )
    
    return html

