"""
Gerador de Documentos Médicos (Solicitações de Exames e Vacinas)
Evidens Digital - Sistema de Check-up Inteligente
"""

from datetime import datetime
from fpdf import FPDF
from io import BytesIO


class PDF_Solicitacao(FPDF):
    """Classe personalizada para geração de PDFs de solicitação médica"""
    
    def header(self):
        """Cabeçalho do documento"""
        self.set_font('Arial', 'B', 16)
        self.set_text_color(52, 152, 219)
        self.cell(0, 10, 'evidens digital', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Sistema de Check-up Inteligente Baseado em Evidencias', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        """Rodapé do documento"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 10, f'Gerado em {data_hora} - Pagina {self.page_no()}', 0, 0, 'C')


def gerar_justificativa_clinica(dados_paciente):
    idade = dados_paciente.get('idade', 0)
    sexo = dados_paciente.get('sexo', 'nao informado')
    comorbidades = dados_paciente.get('comorbidades', [])
    medicacoes = dados_paciente.get('medicacoes', [])
    tabagismo = dados_paciente.get('tabagismo', 'nunca_fumou')
    
    justificativa_partes = []
    sexo_texto = "feminino" if sexo == "feminino" else "masculino"
    justificativa_partes.append(f"Paciente do sexo {sexo_texto}, {idade} anos")
    
    if comorbidades and len(comorbidades) > 0:
        comorbidades_texto = ", ".join(comorbidades)
        justificativa_partes.append(f"com diagnostico de {comorbidades_texto}")
    
    if medicacoes and len(medicacoes) > 0:
        justificativa_partes.append(f"em uso de {len(medicacoes)} medicacao(oes) continua(s)")
    
    if tabagismo == "fumante_atual":
        justificativa_partes.append("tabagista ativo")
    elif tabagismo == "ex_fumante":
        justificativa_partes.append("ex-tabagista")
    
    if len(justificativa_partes) == 1:
        justificativa = f"{justificativa_partes[0]}, com necessidade de realizacao de screening preventivo conforme diretrizes baseadas em evidencias."
    else:
        justificativa = f"{justificativa_partes[0]}, {', '.join(justificativa_partes[1:])}, com necessidade de realizacao de screening preventivo e monitoramento de fatores de risco conforme diretrizes baseadas em evidencias."
    
    return justificativa


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    pdf = PDF_Solicitacao()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, 'SOLICITACAO DE EXAMES LABORATORIAIS', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'DADOS DO PACIENTE', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Nome: {dados_paciente.get('nome', '______________________________')}", 0, 1)
    pdf.cell(0, 6, f"Idade: {dados_paciente.get('idade', '__')} anos     Sexo: {dados_paciente.get('sexo', '______').capitalize()}", 0, 1)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'JUSTIFICATIVA CLINICA', 0, 1)
    pdf.set_font('Arial', '', 10)
    justificativa = gerar_justificativa_clinica(dados_paciente)
    pdf.multi_cell(0, 5, justificativa)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'EXAMES SOLICITADOS', 0, 1)
    pdf.ln(2)
    
    exames_lab = [e for e in exames if e.get('categoria') == 'laboratorio' or e.get('categoria') == 'Exames Laboratoriais']
    
    if not exames_lab:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, 'Nenhum exame laboratorial recomendado.', 0, 1)
    else:
        for i, exame in enumerate(exames_lab, 1):
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(10, 6, f"{i}.", 0, 0)
            pdf.multi_cell(0, 6, exame.get('titulo', 'Exame nao especificado'))
            
            if exame.get('descricao'):
                pdf.set_font('Arial', '', 9)
                pdf.set_x(15)
                pdf.multi_cell(0, 5, f"   {exame.get('descricao')}")
            
            pdf.ln(2)
    
    pdf.ln(15)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, '_' * 50, 0, 1, 'C')
    pdf.cell(0, 6, 'Assinatura e Carimbo do Medico Solicitante', 0, 1, 'C')
    
    pdf_buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def gerar_pdf_exames_imagem(dados_paciente, exames):
    pdf = PDF_Solicitacao()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, 'SOLICITACAO DE EXAMES DE IMAGEM', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'DADOS DO PACIENTE', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Nome: {dados_paciente.get('nome', '______________________________')}", 0, 1)
    pdf.cell(0, 6, f"Idade: {dados_paciente.get('idade', '__')} anos     Sexo: {dados_paciente.get('sexo', '______').capitalize()}", 0, 1)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'JUSTIFICATIVA CLINICA', 0, 1)
    pdf.set_font('Arial', '', 10)
    justificativa = gerar_justificativa_clinica(dados_paciente)
    pdf.multi_cell(0, 5, justificativa)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'EXAMES SOLICITADOS', 0, 1)
    pdf.ln(2)
    
    exames_img = [e for e in exames if e.get('categoria') == 'imagem' or e.get('categoria') == 'Exames de Imagem']
    
    if not exames_img:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, 'Nenhum exame de imagem recomendado.', 0, 1)
    else:
        for i, exame in enumerate(exames_img, 1):
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(10, 6, f"{i}.", 0, 0)
            pdf.multi_cell(0, 6, exame.get('titulo', 'Exame nao especificado'))
            
            if exame.get('descricao'):
                pdf.set_font('Arial', '', 9)
                pdf.set_x(15)
                pdf.multi_cell(0, 5, f"   {exame.get('descricao')}")
            
            pdf.ln(2)
    
    pdf.ln(15)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, '_' * 50, 0, 1, 'C')
    pdf.cell(0, 6, 'Assinatura e Carimbo do Medico Solicitante', 0, 1, 'C')
    
    pdf_buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def gerar_pdf_vacinas(dados_paciente, vacinas):
    pdf = PDF_Solicitacao()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, 'PRESCRICAO DE VACINAS', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'DADOS DO PACIENTE', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"Nome: {dados_paciente.get('nome', '______________________________')}", 0, 1)
    pdf.cell(0, 6, f"Idade: {dados_paciente.get('idade', '__')} anos     Sexo: {dados_paciente.get('sexo', '______').capitalize()}", 0, 1)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'JUSTIFICATIVA CLINICA', 0, 1)
    pdf.set_font('Arial', '', 10)
    justificativa = gerar_justificativa_clinica(dados_paciente)
    pdf.multi_cell(0, 5, justificativa)
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 7, 'VACINAS PRESCRITAS', 0, 1)
    pdf.ln(2)
    
    vacinas_list = [v for v in vacinas if v.get('categoria') == 'vacina']
    
    if not vacinas_list:
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 6, 'Nenhuma vacina recomendada.', 0, 1)
    else:
        for i, vacina in enumerate(vacinas_list, 1):
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(10, 6, f"{i}.", 0, 0)
            pdf.multi_cell(0, 6, vacina.get('titulo', 'Vacina nao especificada'))
            
            if vacina.get('subtitulo'):
                pdf.set_font('Arial', 'I', 9)
                pdf.set_text_color(52, 152, 219)
                pdf.set_x(15)
                pdf.multi_cell(0, 5, f"   {vacina.get('subtitulo')}")
                pdf.set_text_color(0, 0, 0)
            
            if vacina.get('descricao'):
                pdf.set_font('Arial', '', 9)
                pdf.set_x(15)
                pdf.multi_cell(0, 5, f"   {vacina.get('descricao')}")
            
            pdf.ln(2)
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'OBSERVACOES:', 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, '- Verificar contraindicacoes antes da aplicacao\n- Respeitar intervalos minimos entre doses\n- Registrar no cartao de vacinacao')
    
    pdf.ln(10)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, '_' * 50, 0, 1, 'C')
    pdf.cell(0, 6, 'Assinatura e Carimbo do Medico Prescritor', 0, 1, 'C')
    
    pdf_buffer = BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    
    return pdf_buffer
