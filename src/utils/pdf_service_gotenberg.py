"""
Serviço de geração de PDFs usando Gotenberg (Chromium)
"""

import os
import urllib.request
import urllib.error
from datetime import datetime
from jinja2 import Template

# URL do microserviço Gotenberg no Railway
# Será definida via variável de ambiente
GOTENBERG_URL = os.getenv('GOTENBERG_URL', 'http://localhost:3000')

def gerar_justificativa_clinica(dados_paciente):
    """Gera justificativa clínica automática baseada nos dados do paciente"""
    
    idade = dados_paciente.get('idade', 0)
    # Garantir que idade seja um inteiro
    try:
        idade = int(idade) if idade else 0
    except (ValueError, TypeError):
        idade = 0
    
    sexo = dados_paciente.get('sexo', 'Não informado')
    sexo_texto = 'Paciente feminina' if sexo == 'F' else 'Paciente masculino'
    
    # Coletar comorbidades
    comorbidades = []
    if dados_paciente.get('hipertensao'):
        comorbidades.append('hipertensa' if sexo == 'F' else 'hipertenso')
    if dados_paciente.get('diabetes'):
        comorbidades.append('diabética' if sexo == 'F' else 'diabético')
    if dados_paciente.get('dislipidemia'):
        comorbidades.append('dislipidêmica' if sexo == 'F' else 'dislipidêmico')
    if dados_paciente.get('has_resistente'):
        comorbidades.append('com HAS resistente')
    if dados_paciente.get('cardiopatia'):
        comorbidades.append('cardiopata')
    
    # Coletar medicações
    medicacoes = dados_paciente.get('medicacoes', [])
    if isinstance(medicacoes, str):
        medicacoes = [medicacoes] if medicacoes else []
    
    # Coletar história familiar
    historia_familiar = []
    if dados_paciente.get('hf_cancer_mama'):
        historia_familiar.append('câncer de mama')
    if dados_paciente.get('hf_cancer_colorretal'):
        historia_familiar.append('câncer colorretal')
    if dados_paciente.get('hf_diabetes'):
        historia_familiar.append('diabetes')
    if dados_paciente.get('hf_cardiopatia'):
        historia_familiar.append('cardiopatia')
    
    # Construir justificativa
    justificativa = f"{sexo_texto}, {idade} anos"
    
    if comorbidades:
        justificativa += f", {', '.join(comorbidades)}"
    
    if medicacoes:
        justificativa += f", em uso de {', '.join(medicacoes)}"
    
    if historia_familiar:
        justificativa += f", com história familiar de {', '.join(historia_familiar)}"
    
    # Adicionar motivo do screening
    if idade >= 65:
        justificativa += ", com necessidade de realização de screening geriátrico anual."
    elif idade >= 50:
        justificativa += ", com necessidade de realização de screening preventivo anual."
    elif idade >= 40:
        justificativa += ", com necessidade de realização de check-up preventivo."
    else:
        justificativa += ", com necessidade de avaliação clínica e exames de rotina."
    
    return justificativa


def gerar_html_solicitacao_exames(dados_paciente, exames, tipo='laboratoriais'):
    """Gera HTML para solicitação de exames"""
    
    titulo = "SOLICITAÇÃO DE EXAMES LABORATORIAIS" if tipo == 'laboratoriais' else "SOLICITAÇÃO DE EXAMES DE IMAGEM"
    
    justificativa = gerar_justificativa_clinica(dados_paciente)
    
    # Template HTML
    template_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ titulo }}</title>
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.4;
                color: #333;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #4A90E2;
                padding-bottom: 15px;
            }
            .logo {
                font-size: 24pt;
                font-weight: bold;
                color: #4A90E2;
                margin-bottom: 5px;
            }
            .subtitle {
                font-size: 10pt;
                color: #666;
            }
            h1 {
                font-size: 16pt;
                text-align: center;
                margin: 20px 0;
                color: #333;
            }
            .patient-info {
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .patient-info p {
                margin: 5px 0;
            }
            .justification {
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin-bottom: 20px;
            }
            .justification strong {
                display: block;
                margin-bottom: 10px;
                color: #856404;
            }
            .exams-list {
                margin-bottom: 30px;
            }
            .exam-item {
                margin-bottom: 15px;
                padding: 10px;
                border-left: 3px solid #4A90E2;
                background-color: #f8f9fa;
            }
            .exam-title {
                font-weight: bold;
                color: #4A90E2;
                margin-bottom: 5px;
            }
            .exam-subtitle {
                font-size: 9pt;
                color: #666;
                margin-bottom: 5px;
            }
            .exam-description {
                font-size: 10pt;
                color: #555;
            }
            .signature {
                margin-top: 50px;
                text-align: center;
            }
            .signature-line {
                border-top: 1px solid #333;
                width: 300px;
                margin: 0 auto;
                padding-top: 10px;
            }
            .footer {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                text-align: center;
                font-size: 8pt;
                color: #999;
                padding: 10px;
                border-top: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">evidēns digital</div>
            <div class="subtitle">Sistema Inteligente de Recomendações Clínicas</div>
        </div>
        
        <h1>{{ titulo }}</h1>
        
        <div class="patient-info">
            <p><strong>Paciente:</strong> {{ paciente_nome }}</p>
            <p><strong>Idade:</strong> {{ paciente_idade }} anos</p>
            <p><strong>Sexo:</strong> {{ paciente_sexo }}</p>
            <p><strong>Data:</strong> {{ data_emissao }}</p>
        </div>
        
        <div class="justification">
            <strong>JUSTIFICATIVA CLÍNICA:</strong>
            {{ justificativa }}
        </div>
        
        <div class="exams-list">
            <h3>Exames Solicitados:</h3>
            {% for exam in exames %}
            <div class="exam-item">
                <div class="exam-title">{{ loop.index }}. {{ exam.titulo }}</div>
                {% if exam.subtitulo %}
                <div class="exam-subtitle">{{ exam.subtitulo }}</div>
                {% endif %}
                {% if exam.descricao %}
                <div class="exam-description">{{ exam.descricao }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <div class="signature">
            <div class="signature-line">
                Assinatura e Carimbo do Médico
            </div>
        </div>
        
        <div class="footer">
            Documento gerado em {{ data_hora_completa }} | evidens.digital
        </div>
    </body>
    </html>
    """
    
    template = Template(template_html)
    
    html = template.render(
        titulo=titulo,
        paciente_nome=dados_paciente.get('nome', 'Não informado'),
        paciente_idade=dados_paciente.get('idade', 'Não informada'),
        paciente_sexo='Feminino' if dados_paciente.get('sexo') == 'F' else 'Masculino',
        data_emissao=datetime.now().strftime('%d/%m/%Y'),
        data_hora_completa=datetime.now().strftime('%d/%m/%Y às %H:%M'),
        justificativa=justificativa,
        exames=exames
    )
    
    return html


def gerar_html_prescricao_vacinas(dados_paciente, vacinas):
    """Gera HTML para prescrição de vacinas"""
    
    justificativa = gerar_justificativa_clinica(dados_paciente)
    
    # Template HTML
    template_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PRESCRIÇÃO DE VACINAS</title>
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.4;
                color: #333;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #28a745;
                padding-bottom: 15px;
            }
            .logo {
                font-size: 24pt;
                font-weight: bold;
                color: #28a745;
                margin-bottom: 5px;
            }
            .subtitle {
                font-size: 10pt;
                color: #666;
            }
            h1 {
                font-size: 16pt;
                text-align: center;
                margin: 20px 0;
                color: #333;
            }
            .patient-info {
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .patient-info p {
                margin: 5px 0;
            }
            .justification {
                background-color: #d4edda;
                border-left: 4px solid #28a745;
                padding: 15px;
                margin-bottom: 20px;
            }
            .justification strong {
                display: block;
                margin-bottom: 10px;
                color: #155724;
            }
            .vaccines-list {
                margin-bottom: 30px;
            }
            .vaccine-item {
                margin-bottom: 15px;
                padding: 10px;
                border-left: 3px solid #28a745;
                background-color: #f8f9fa;
            }
            .vaccine-title {
                font-weight: bold;
                color: #28a745;
                margin-bottom: 5px;
            }
            .vaccine-subtitle {
                font-size: 9pt;
                color: #666;
                margin-bottom: 5px;
            }
            .vaccine-priority {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 8pt;
                font-weight: bold;
                margin-left: 10px;
            }
            .priority-alta {
                background-color: #dc3545;
                color: white;
            }
            .priority-media {
                background-color: #ffc107;
                color: #333;
            }
            .signature {
                margin-top: 50px;
                text-align: center;
            }
            .signature-line {
                border-top: 1px solid #333;
                width: 300px;
                margin: 0 auto;
                padding-top: 10px;
            }
            .footer {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                text-align: center;
                font-size: 8pt;
                color: #999;
                padding: 10px;
                border-top: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">evidēns digital</div>
            <div class="subtitle">Sistema Inteligente de Recomendações Clínicas</div>
        </div>
        
        <h1>PRESCRIÇÃO DE VACINAS</h1>
        
        <div class="patient-info">
            <p><strong>Paciente:</strong> {{ paciente_nome }}</p>
            <p><strong>Idade:</strong> {{ paciente_idade }} anos</p>
            <p><strong>Sexo:</strong> {{ paciente_sexo }}</p>
            <p><strong>Data:</strong> {{ data_emissao }}</p>
        </div>
        
        <div class="justification">
            <strong>JUSTIFICATIVA CLÍNICA:</strong>
            {{ justificativa }}
        </div>
        
        <div class="vaccines-list">
            <h3>Vacinas Recomendadas:</h3>
            {% for vaccine in vacinas %}
            <div class="vaccine-item">
                <div class="vaccine-title">
                    {{ loop.index }}. {{ vaccine.titulo }}
                    {% if vaccine.prioridade %}
                    <span class="vaccine-priority priority-{{ vaccine.prioridade|lower }}">{{ vaccine.prioridade }}</span>
                    {% endif %}
                </div>
                {% if vaccine.subtitulo %}
                <div class="vaccine-subtitle">{{ vaccine.subtitulo }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        <div class="signature">
            <div class="signature-line">
                Assinatura e Carimbo do Médico
            </div>
        </div>
        
        <div class="footer">
            Documento gerado em {{ data_hora_completa }} | evidens.digital
        </div>
    </body>
    </html>
    """
    
    template = Template(template_html)
    
    html = template.render(
        paciente_nome=dados_paciente.get('nome', 'Não informado'),
        paciente_idade=dados_paciente.get('idade', 'Não informada'),
        paciente_sexo='Feminino' if dados_paciente.get('sexo') == 'F' else 'Masculino',
        data_emissao=datetime.now().strftime('%d/%m/%Y'),
        data_hora_completa=datetime.now().strftime('%d/%m/%Y às %H:%M'),
        justificativa=justificativa,
        vacinas=vacinas
    )
    
    return html


def gerar_pdf_via_gotenberg(html_content):
    """Gera PDF usando Gotenberg (Chromium)"""
    
    try:
        import io
        from urllib.parse import urlencode
        
        # Endpoint do Gotenberg para conversão HTML -> PDF
        url = f"{GOTENBERG_URL}/forms/chromium/convert/html"
        
        # Criar boundary para multipart/form-data
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        
        # Construir corpo da requisição multipart/form-data
        body = io.BytesIO()
        body.write(f'--{boundary}\r\n'.encode())
        body.write(b'Content-Disposition: form-data; name="files"; filename="index.html"\r\n')
        body.write(b'Content-Type: text/html\r\n\r\n')
        body.write(html_content.encode('utf-8'))
        body.write(f'\r\n--{boundary}--\r\n'.encode())
        
        # Criar requisição
        req = urllib.request.Request(
            url,
            data=body.getvalue(),
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            },
            method='POST'
        )
        
        # Fazer requisição
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
        
    except urllib.error.HTTPError as e:
        raise Exception(f"Erro HTTP ao gerar PDF via Gotenberg: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Erro de conexão ao gerar PDF via Gotenberg: {str(e.reason)}")
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF via Gotenberg: {str(e)}")


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    """Gera PDF de solicitação de exames laboratoriais"""
    html = gerar_html_solicitacao_exames(dados_paciente, exames, tipo='laboratoriais')
    return gerar_pdf_via_gotenberg(html)


def gerar_pdf_exames_imagem(dados_paciente, exames):
    """Gera PDF de solicitação de exames de imagem"""
    html = gerar_html_solicitacao_exames(dados_paciente, exames, tipo='imagem')
    return gerar_pdf_via_gotenberg(html)


def gerar_pdf_vacinas(dados_paciente, vacinas):
    """Gera PDF de prescrição de vacinas"""
    html = gerar_html_prescricao_vacinas(dados_paciente, vacinas)
    return gerar_pdf_via_gotenberg(html)

