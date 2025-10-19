"""
Gerador de documentos PDF para solicitações de exames e vacinas
Usa ReportLab para geração de PDFs
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO


def gerar_justificativa_clinica(dados_paciente):
    """Gera justificativa clínica automática"""
    idade = dados_paciente.get('idade', '')
    sexo = dados_paciente.get('sexo', '').capitalize()
    
    condicoes = []
    comorbidades = dados_paciente.get('comorbidades', [])
    if isinstance(comorbidades, list):
        condicoes.extend(comorbidades)
    
    medicacoes = dados_paciente.get('medicacoes', [])
    if isinstance(medicacoes, list):
        if 'Medicamentos Anti-hipertensivos' in medicacoes:
            if 'Hipertensão' not in condicoes and 'HAS Resistente' not in condicoes:
                condicoes.append('em uso de anti-hipertensivos')
    
    tabagismo = dados_paciente.get('tabagismo', '')
    if tabagismo and tabagismo != 'Nunca fumou':
        condicoes.append(tabagismo.lower())
    
    if condicoes:
        condicoes_texto = ', '.join(condicoes)
        return f"Paciente {sexo.lower()}, {idade} anos, com {condicoes_texto}, necessitando de screening preventivo e acompanhamento conforme diretrizes clínicas."
    else:
        return f"Paciente {sexo.lower()}, {idade} anos, necessitando de screening preventivo conforme diretrizes clínicas."


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    """Gera PDF de solicitação de exames laboratoriais"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo customizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Cabeçalho
    story.append(Paragraph("evidens digital", title_style))
    story.append(Paragraph("SOLICITAÇÃO DE EXAMES LABORATORIAIS", styles['Heading2']))
    story.append(Spacer(1, 0.5*cm))
    
    # Dados do paciente
    nome = dados_paciente.get('nome', '________________________________')
    idade = dados_paciente.get('idade', '__')
    sexo = dados_paciente.get('sexo', '________').capitalize()
    
    story.append(Paragraph(f"<b>Paciente:</b> {nome}", styles['Normal']))
    story.append(Paragraph(f"<b>Idade:</b> {idade} anos | <b>Sexo:</b> {sexo}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Justificativa
    justificativa = gerar_justificativa_clinica(dados_paciente)
    story.append(Paragraph("<b>Justificativa Clínica:</b>", styles['Normal']))
    story.append(Paragraph(justificativa, styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Exames
    story.append(Paragraph("<b>Exames Solicitados:</b>", styles['Normal']))
    story.append(Spacer(1, 0.3*cm))
    
    for i, exame in enumerate(exames, 1):
        titulo = exame.get('titulo', '')
        story.append(Paragraph(f"{i}. {titulo}", styles['Normal']))
    
    story.append(Spacer(1, 2*cm))
    
    # Assinatura
    story.append(Paragraph("_" * 50, styles['Normal']))
    story.append(Paragraph("Assinatura e Carimbo do Médico", styles['Normal']))
    
    # Rodapé
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Documento gerado em {data_hora} | evidens digital", styles['Normal']))
    
    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_exames_imagem(dados_paciente, exames):
    """Gera PDF de solicitação de exames de imagem"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph("evidens digital", title_style))
    story.append(Paragraph("SOLICITAÇÃO DE EXAMES DE IMAGEM", styles['Heading2']))
    story.append(Spacer(1, 0.5*cm))
    
    nome = dados_paciente.get('nome', '________________________________')
    idade = dados_paciente.get('idade', '__')
    sexo = dados_paciente.get('sexo', '________').capitalize()
    
    story.append(Paragraph(f"<b>Paciente:</b> {nome}", styles['Normal']))
    story.append(Paragraph(f"<b>Idade:</b> {idade} anos | <b>Sexo:</b> {sexo}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    justificativa = gerar_justificativa_clinica(dados_paciente)
    story.append(Paragraph("<b>Justificativa Clínica:</b>", styles['Normal']))
    story.append(Paragraph(justificativa, styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>Exames Solicitados:</b>", styles['Normal']))
    story.append(Spacer(1, 0.3*cm))
    
    for i, exame in enumerate(exames, 1):
        titulo = exame.get('titulo', '')
        story.append(Paragraph(f"{i}. {titulo}", styles['Normal']))
    
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("_" * 50, styles['Normal']))
    story.append(Paragraph("Assinatura e Carimbo do Médico", styles['Normal']))
    
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Documento gerado em {data_hora} | evidens digital", styles['Normal']))
    
    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_vacinas(dados_paciente, vacinas):
    """Gera PDF de prescrição de vacinas"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph("evidens digital", title_style))
    story.append(Paragraph("PRESCRIÇÃO DE VACINAS", styles['Heading2']))
    story.append(Spacer(1, 0.5*cm))
    
    nome = dados_paciente.get('nome', '________________________________')
    idade = dados_paciente.get('idade', '__')
    sexo = dados_paciente.get('sexo', '________').capitalize()
    
    story.append(Paragraph(f"<b>Paciente:</b> {nome}", styles['Normal']))
    story.append(Paragraph(f"<b>Idade:</b> {idade} anos | <b>Sexo:</b> {sexo}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>Vacinas Recomendadas:</b>", styles['Normal']))
    story.append(Spacer(1, 0.3*cm))
    
    for i, vacina in enumerate(vacinas, 1):
        titulo = vacina.get('titulo', '')
        subtitulo = vacina.get('subtitulo', '')
        story.append(Paragraph(f"<b>{i}. {titulo}</b>", styles['Normal']))
        if subtitulo:
            story.append(Paragraph(f"   <i>{subtitulo}</i>", styles['Normal']))
        story.append(Spacer(1, 0.2*cm))
    
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("_" * 50, styles['Normal']))
    story.append(Paragraph("Assinatura e Carimbo do Médico", styles['Normal']))
    
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Documento gerado em {data_hora} | evidens digital", styles['Normal']))
    
    doc.build(story)
    return buffer.getvalue()
