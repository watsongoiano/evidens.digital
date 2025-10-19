"""
Serviço de geração de PDFs usando WeasyPrint com templates HTML/CSS
"""

from datetime import datetime
import uuid
import base64
import io
import qrcode
from jinja2 import Template
import os

# Importar WeasyPrint
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("⚠️ WeasyPrint não disponível - usando fallback para reportlab")

def generate_qr_code(data):
    """Gera QR Code e retorna como base64"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()

def generate_document_code():
    """Gera código único para o documento"""
    return f"EVD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def gerar_justificativa_clinica(dados_paciente, comorbidades=None):
    """
    Gera justificativa clínica automática baseada nos dados do paciente
    """
    idade = dados_paciente.get('idade', 0)
    sexo = dados_paciente.get('sexo', 'não informado')
    sexo_texto = 'masculino' if sexo.lower() == 'masculino' else 'feminino'
    
    # Construir lista de condições
    condicoes = []
    
    if comorbidades:
        if isinstance(comorbidades, list):
            condicoes.extend(comorbidades)
        elif isinstance(comorbidades, str):
            condicoes.append(comorbidades)
    
    # Adicionar informações de idade
    if idade >= 65:
        condicoes.append("idade avançada")
    
    # Construir justificativa
    if condicoes:
        condicoes_texto = ", ".join(condicoes)
        justificativa = f"Paciente {sexo_texto}, {idade} anos, com {condicoes_texto}, necessitando de avaliação laboratorial/complementar para screening preventivo e monitoramento de saúde conforme diretrizes clínicas vigentes."
    else:
        justificativa = f"Paciente {sexo_texto}, {idade} anos, necessitando de avaliação laboratorial/complementar para screening preventivo conforme diretrizes clínicas vigentes."
    
    return justificativa

def render_pdf_from_template(template_path, context):
    """
    Renderiza PDF a partir de template HTML usando WeasyPrint
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("WeasyPrint não está disponível")
    
    # Ler template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Renderizar template com Jinja2
    template = Template(template_content)
    html_content = template.render(**context)
    
    # Gerar PDF com WeasyPrint
    pdf_bytes = HTML(string=html_content).write_pdf()
    
    return pdf_bytes

def gerar_pdf_exames(dados_paciente, exames, tipo_exame="LABORATORIAIS"):
    """
    Gera PDF de solicitação de exames
    
    Args:
        dados_paciente: dict com idade, sexo, nome
        exames: lista de dicts com titulo, subtitulo, referencia
        tipo_exame: str - "LABORATORIAIS" ou "DE IMAGEM"
    
    Returns:
        bytes do PDF gerado
    """
    # Gerar código e QR code
    document_code = generate_document_code()
    qr_code_data = f"https://evidens.digital/verify/{document_code}"
    qr_code_base64 = generate_qr_code(qr_code_data)
    
    # Gerar justificativa clínica
    comorbidades = dados_paciente.get('comorbidades', [])
    justificativa = gerar_justificativa_clinica(dados_paciente, comorbidades)
    
    # Preparar contexto
    context = {
        'patient_name': dados_paciente.get('nome', 'Paciente'),
        'patient_age': dados_paciente.get('idade', ''),
        'patient_sex': dados_paciente.get('sexo', '').capitalize(),
        'date': datetime.now().strftime('%d/%m/%Y'),
        'generation_datetime': datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'tipo_exame': tipo_exame,
        'justification': justificativa,
        'exams': exames,
        'qr_code': qr_code_base64,
        'document_code': document_code
    }
    
    # Caminho do template
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    template_path = os.path.join(template_dir, 'solicitacao_exames_template.html')
    
    # Gerar PDF
    pdf_bytes = render_pdf_from_template(template_path, context)
    
    return pdf_bytes

def gerar_pdf_vacinas(dados_paciente, vacinas):
    """
    Gera PDF de prescrição de vacinas
    
    Args:
        dados_paciente: dict com idade, sexo, nome
        vacinas: lista de dicts com titulo, subtitulo, referencia
    
    Returns:
        bytes do PDF gerado
    """
    # Gerar código e QR code
    document_code = generate_document_code()
    qr_code_data = f"https://evidens.digital/verify/{document_code}"
    qr_code_base64 = generate_qr_code(qr_code_data)
    
    # Preparar contexto
    context = {
        'patient_name': dados_paciente.get('nome', 'Paciente'),
        'patient_age': dados_paciente.get('idade', ''),
        'patient_sex': dados_paciente.get('sexo', '').capitalize(),
        'date': datetime.now().strftime('%d/%m/%Y'),
        'generation_datetime': datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'vaccines': vacinas,
        'qr_code': qr_code_base64,
        'document_code': document_code
    }
    
    # Caminho do template
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    template_path = os.path.join(template_dir, 'prescricao_vacinas_template.html')
    
    # Gerar PDF
    pdf_bytes = render_pdf_from_template(template_path, context)
    
    return pdf_bytes

