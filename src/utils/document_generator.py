"""
Gerador de Documentos Médicos (Solicitações de Exames e Vacinas)
Evidens Digital - Sistema de Check-up Inteligente
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO


def gerar_justificativa_clinica(dados_paciente):
    """
    Gera justificativa clínica automática baseada nos dados do paciente.
    
    Args:
        dados_paciente (dict): Dicionário com dados do paciente
            - idade (int)
            - sexo (str): 'masculino' ou 'feminino'
            - comorbidades (list): Lista de comorbidades
            - medicacoes (list): Lista de medicações
            - tabagismo (str): Status de tabagismo
            - historico_familiar (list): História familiar
    
    Returns:
        str: Justificativa clínica formatada
    """
    idade = dados_paciente.get('idade', 0)
    sexo = dados_paciente.get('sexo', '').lower()
    comorbidades = dados_paciente.get('comorbidades', [])
    medicacoes = dados_paciente.get('medicacoes', [])
    tabagismo = dados_paciente.get('tabagismo', 'nunca_fumou')
    historico_familiar = dados_paciente.get('historico_familiar', [])
    
    # Determinar artigo e gênero
    artigo = "Paciente" if sexo == 'masculino' else "Paciente"
    genero_adj = "o" if sexo == 'masculino' else "a"
    
    # Construir descrição de comorbidades
    comorbidades_texto = []
    if 'diabetes' in comorbidades or 'Diabetes Tipo 2' in comorbidades:
        comorbidades_texto.append('diabétic' + genero_adj)
    if 'hipertensao' in comorbidades or 'Hipertensão' in comorbidades:
        comorbidades_texto.append('hipertens' + genero_adj)
    if 'dislipidemia' in comorbidades or 'Dislipidemia' in comorbidades:
        comorbidades_texto.append('dislipidêmic' + genero_adj)
    if 'obesidade' in comorbidades or 'Obesidade' in comorbidades:
        comorbidades_texto.append('obeso' if sexo == 'masculino' else 'obesa')
    if 'doenca_renal' in comorbidades or 'Doença Renal Crônica' in comorbidades:
        comorbidades_texto.append('com doença renal crônica')
    if 'cardiopatia' in comorbidades or 'Cardiopatia' in comorbidades:
        comorbidades_texto.append('cardiopata')
    
    # Adicionar tabagismo se relevante
    if tabagismo == 'fumante_atual':
        comorbidades_texto.append('tabagista')
    elif tabagismo == 'ex_fumante':
        comorbidades_texto.append('ex-tabagista')
    
    # Construir frase de comorbidades
    if comorbidades_texto:
        if len(comorbidades_texto) == 1:
            comorbidades_frase = comorbidades_texto[0]
        elif len(comorbidades_texto) == 2:
            comorbidades_frase = f"{comorbidades_texto[0]} e {comorbidades_texto[1]}"
        else:
            comorbidades_frase = ', '.join(comorbidades_texto[:-1]) + f' e {comorbidades_texto[-1]}'
    else:
        comorbidades_frase = "sem comorbidades conhecidas"
    
    # Determinar tipo de screening
    screening_tipo = []
    
    # Screening por idade
    if idade >= 65:
        screening_tipo.append('screening geriátrico anual')
    elif idade >= 50:
        screening_tipo.append('screening preventivo anual')
    elif idade >= 40:
        screening_tipo.append('avaliação de risco cardiovascular')
    elif idade >= 35:
        screening_tipo.append('rastreamento metabólico')
    
    # Screening por comorbidades
    if 'diabetes' in comorbidades or 'Diabetes Tipo 2' in comorbidades:
        screening_tipo.append('monitoramento de diabetes')
    if 'hipertensao' in comorbidades or 'Hipertensão' in comorbidades:
        screening_tipo.append('controle de hipertensão arterial')
    if 'dislipidemia' in comorbidades or 'Dislipidemia' in comorbidades:
        screening_tipo.append('controle lipídico')
    
    # Screening por história familiar
    if historico_familiar:
        screening_tipo.append('rastreamento por história familiar positiva')
    
    # Construir frase de screening
    if screening_tipo:
        if len(screening_tipo) == 1:
            screening_frase = screening_tipo[0]
        else:
            screening_frase = ', '.join(screening_tipo[:-1]) + f' e {screening_tipo[-1]}'
    else:
        screening_frase = 'avaliação de saúde preventiva'
    
    # Construir justificativa final
    justificativa = (
        f"{artigo} {sexo}, {idade} anos, {comorbidades_frase}, "
        f"com necessidade de realização de {screening_frase}."
    )
    
    return justificativa


def gerar_pdf_exames_laboratoriais(dados_paciente, exames, nome_arquivo=None):
    """
    Gera PDF de solicitação de exames laboratoriais.
    
    Args:
        dados_paciente (dict): Dados do paciente
        exames (list): Lista de exames laboratoriais
        nome_arquivo (str): Nome do arquivo (opcional)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    buffer = BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para título
    titulo_style = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.black,
        borderPadding=8
    )
    
    # Estilo para cabeçalho
    cabecalho_style = ParagraphStyle(
        'Cabecalho',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Estilo para dados do paciente
    paciente_style = ParagraphStyle(
        'Paciente',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    # Estilo para justificativa
    justificativa_style = ParagraphStyle(
        'Justificativa',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_JUSTIFY
    )
    
    # Estilo para lista de exames
    exame_style = ParagraphStyle(
        'Exame',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=4,
        alignment=TA_LEFT,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Estilo para rodapé
    rodape_style = ParagraphStyle(
        'Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    
    # Construir elementos do documento
    elementos = []
    
    # Título
    titulo = Paragraph("SOLICITAÇÃO DE EXAMES LABORATORIAIS", titulo_style)
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Cabeçalho (Evidens Digital)
    cabecalho = Paragraph(
        "<b>Evidens Digital</b><br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências",
        cabecalho_style
    )
    elementos.append(cabecalho)
    
    # Data de emissão
    data_emissao = datetime.now().strftime("%d/%m/%Y")
    data_texto = Paragraph(
        f"<b>Data de emissão:</b> {data_emissao}",
        cabecalho_style
    )
    elementos.append(data_texto)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Dados do paciente
    nome_paciente = dados_paciente.get('nome', 'Paciente')
    sexo_paciente = dados_paciente.get('sexo', '').capitalize()
    idade_paciente = dados_paciente.get('idade', '')
    
    paciente_info = Paragraph(
        f"<b>Paciente:</b> {nome_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Sexo:</b> {sexo_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Idade:</b> {idade_paciente} anos",
        paciente_style
    )
    elementos.append(paciente_info)
    elementos.append(Spacer(1, 0.3*cm))
    
    # Justificativa clínica
    justificativa_texto = gerar_justificativa_clinica(dados_paciente)
    justificativa = Paragraph(
        f"<b>Justificativa Clínica:</b> {justificativa_texto}",
        justificativa_style
    )
    elementos.append(justificativa)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Lista de exames
    solicito_titulo = Paragraph("<b>Solicito:</b>", paciente_style)
    elementos.append(solicito_titulo)
    elementos.append(Spacer(1, 0.2*cm))
    
    for exame in exames:
        exame_titulo = exame.get('titulo', '')
        exame_item = Paragraph(f"• {exame_titulo}", exame_style)
        elementos.append(exame_item)
    
    elementos.append(Spacer(1, 1*cm))
    
    # Rodapé
    rodape = Paragraph(
        f"Documento gerado por Evidens Digital em {data_emissao}<br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências Científicas",
        rodape_style
    )
    elementos.append(rodape)
    
    # Gerar PDF
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer


def gerar_pdf_exames_imagem(dados_paciente, exames, nome_arquivo=None):
    """
    Gera PDF de solicitação de exames de imagem.
    
    Args:
        dados_paciente (dict): Dados do paciente
        exames (list): Lista de exames de imagem
        nome_arquivo (str): Nome do arquivo (opcional)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    buffer = BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos (mesmos do documento de exames laboratoriais)
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.black,
        borderPadding=8
    )
    
    cabecalho_style = ParagraphStyle(
        'Cabecalho',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    paciente_style = ParagraphStyle(
        'Paciente',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    justificativa_style = ParagraphStyle(
        'Justificativa',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_JUSTIFY
    )
    
    exame_style = ParagraphStyle(
        'Exame',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=4,
        alignment=TA_LEFT,
        leftIndent=20,
        bulletIndent=10
    )
    
    rodape_style = ParagraphStyle(
        'Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    
    # Construir elementos do documento
    elementos = []
    
    # Título
    titulo = Paragraph("SOLICITAÇÃO DE EXAMES DE IMAGEM", titulo_style)
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Cabeçalho
    cabecalho = Paragraph(
        "<b>Evidens Digital</b><br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências",
        cabecalho_style
    )
    elementos.append(cabecalho)
    
    # Data de emissão
    data_emissao = datetime.now().strftime("%d/%m/%Y")
    data_texto = Paragraph(
        f"<b>Data de emissão:</b> {data_emissao}",
        cabecalho_style
    )
    elementos.append(data_texto)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Dados do paciente
    nome_paciente = dados_paciente.get('nome', 'Paciente')
    sexo_paciente = dados_paciente.get('sexo', '').capitalize()
    idade_paciente = dados_paciente.get('idade', '')
    
    paciente_info = Paragraph(
        f"<b>Paciente:</b> {nome_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Sexo:</b> {sexo_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Idade:</b> {idade_paciente} anos",
        paciente_style
    )
    elementos.append(paciente_info)
    elementos.append(Spacer(1, 0.3*cm))
    
    # Justificativa clínica
    justificativa_texto = gerar_justificativa_clinica(dados_paciente)
    justificativa = Paragraph(
        f"<b>Justificativa Clínica:</b> {justificativa_texto}",
        justificativa_style
    )
    elementos.append(justificativa)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Lista de exames
    solicito_titulo = Paragraph("<b>Solicito:</b>", paciente_style)
    elementos.append(solicito_titulo)
    elementos.append(Spacer(1, 0.2*cm))
    
    for exame in exames:
        exame_titulo = exame.get('titulo', '')
        exame_item = Paragraph(f"• {exame_titulo}", exame_style)
        elementos.append(exame_item)
    
    elementos.append(Spacer(1, 1*cm))
    
    # Rodapé
    rodape = Paragraph(
        f"Documento gerado por Evidens Digital em {data_emissao}<br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências Científicas",
        rodape_style
    )
    elementos.append(rodape)
    
    # Gerar PDF
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer


def gerar_pdf_vacinas(dados_paciente, vacinas, nome_arquivo=None):
    """
    Gera PDF de prescrição de vacinas.
    
    Args:
        dados_paciente (dict): Dados do paciente
        vacinas (list): Lista de vacinas
        nome_arquivo (str): Nome do arquivo (opcional)
    
    Returns:
        BytesIO: Buffer com o PDF gerado
    """
    buffer = BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.black,
        borderPadding=8
    )
    
    cabecalho_style = ParagraphStyle(
        'Cabecalho',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    paciente_style = ParagraphStyle(
        'Paciente',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    justificativa_style = ParagraphStyle(
        'Justificativa',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_JUSTIFY
    )
    
    vacina_numero_style = ParagraphStyle(
        'VacinaNumero',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=2,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    vacina_instrucao_style = ParagraphStyle(
        'VacinaInstrucao',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=8,
        alignment=TA_LEFT,
        leftIndent=20
    )
    
    rodape_style = ParagraphStyle(
        'Rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    
    # Construir elementos do documento
    elementos = []
    
    # Título
    titulo = Paragraph("PRESCRIÇÃO DE VACINAS", titulo_style)
    elementos.append(titulo)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Cabeçalho
    cabecalho = Paragraph(
        "<b>Evidens Digital</b><br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências",
        cabecalho_style
    )
    elementos.append(cabecalho)
    
    # Data de emissão
    data_emissao = datetime.now().strftime("%d/%m/%Y")
    data_texto = Paragraph(
        f"<b>Data de emissão:</b> {data_emissao}",
        cabecalho_style
    )
    elementos.append(data_texto)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Dados do paciente
    nome_paciente = dados_paciente.get('nome', 'Paciente')
    sexo_paciente = dados_paciente.get('sexo', '').capitalize()
    idade_paciente = dados_paciente.get('idade', '')
    
    paciente_info = Paragraph(
        f"<b>Paciente:</b> {nome_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Sexo:</b> {sexo_paciente} &nbsp;&nbsp;&nbsp; "
        f"<b>Idade:</b> {idade_paciente} anos",
        paciente_style
    )
    elementos.append(paciente_info)
    elementos.append(Spacer(1, 0.3*cm))
    
    # Justificativa clínica
    justificativa_texto = gerar_justificativa_clinica(dados_paciente)
    justificativa = Paragraph(
        f"<b>Justificativa Clínica:</b> {justificativa_texto}",
        justificativa_style
    )
    elementos.append(justificativa)
    elementos.append(Spacer(1, 0.5*cm))
    
    # Lista de vacinas (formato numerado)
    for idx, vacina in enumerate(vacinas, start=1):
        vacina_titulo = vacina.get('titulo', '')
        vacina_subtitulo = vacina.get('subtitulo', '')
        
        # Extrair número de doses do subtítulo
        doses_info = ""
        if '|' in vacina_subtitulo:
            doses_info = vacina_subtitulo.split('|')[-1].strip()
        
        # Número e nome da vacina
        vacina_numero = Paragraph(
            f"{idx}  {vacina_titulo} {'.'*50} {doses_info}",
            vacina_numero_style
        )
        elementos.append(vacina_numero)
        elementos.append(Spacer(1, 0.1*cm))
        
        # Instrução de aplicação (genérica)
        instrucao = f"Aplicar conforme esquema vacinal recomendado, via intramuscular."
        vacina_instrucao = Paragraph(instrucao, vacina_instrucao_style)
        elementos.append(vacina_instrucao)
        elementos.append(Spacer(1, 0.3*cm))
    
    # Observação sobre contraindicações
    obs_texto = (
        "<b>Obs:</b> Verificar contraindicações antes da administração. "
        "Paciente deve informar uso de medicações imunossupressoras, "
        "alergias prévias a vacinas ou componentes, e outras condições relevantes."
    )
    obs = Paragraph(obs_texto, vacina_instrucao_style)
    elementos.append(obs)
    elementos.append(Spacer(1, 1*cm))
    
    # Rodapé
    rodape = Paragraph(
        f"Documento gerado por Evidens Digital em {data_emissao}<br/>"
        "Sistema de Check-up Inteligente Baseado em Evidências Científicas",
        rodape_style
    )
    elementos.append(rodape)
    
    # Gerar PDF
    doc.build(elementos)
    buffer.seek(0)
    
    return buffer

