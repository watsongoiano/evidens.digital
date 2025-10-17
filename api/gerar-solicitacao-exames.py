from http.server import BaseHTTPRequestHandler
import json
import io
import base64
from datetime import datetime
from fpdf import FPDF

class SolicitacaoExamePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Título principal com borda
        self.set_font('Arial', 'B', 16)
        self.cell(0, 15, 'SOLICITAÇÃO DE EXAME', 1, 1, 'C')
        self.ln(5)
        
    def add_clinic_info(self):
        # Nome da clínica
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'Órion Business and Health', 0, 1, 'L')
        
        # Data de emissão (lado direito)
        data_atual = datetime.now().strftime('%d/%m/%Y')
        self.set_xy(150, self.get_y() - 8)
        self.cell(0, 8, f'Data de emissão: {data_atual}', 0, 1, 'L')
        
        # Endereço
        self.set_font('Arial', '', 10)
        self.cell(30, 6, 'Endereço:', 0, 0, 'L')
        self.cell(0, 6, 'Avenida Portugal, 1148, Setor Marista, Goiânia - GO', 0, 1, 'L')
        
        # Telefone
        self.cell(30, 6, 'Telefone:', 0, 0, 'L')
        self.cell(0, 6, '(11 )', 0, 1, 'L')
        self.ln(5)
        
    def add_doctor_info(self, medico_nome="", medico_crm=""):
        # Dados do médico
        self.set_font('Arial', '', 10)
        self.cell(30, 6, 'Dr(a).', 0, 0, 'L')
        self.cell(100, 6, medico_nome, 0, 0, 'L')
        self.cell(20, 6, 'CRM:', 0, 0, 'L')
        self.cell(0, 6, medico_crm, 0, 1, 'L')
        self.ln(5)
        
        # Linha separadora
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
    def add_patient_info(self, paciente_nome="", paciente_cpf="", paciente_sexo="", paciente_idade=""):
        # Dados do paciente
        self.set_font('Arial', '', 10)
        self.cell(20, 6, 'Paciente:', 0, 0, 'L')
        self.cell(80, 6, paciente_nome, 0, 0, 'L')
        self.cell(15, 6, 'Sexo:', 0, 0, 'L')
        self.cell(30, 6, paciente_sexo, 0, 0, 'L')
        self.cell(15, 6, 'Idade:', 0, 0, 'L')
        self.cell(0, 6, str(paciente_idade), 0, 1, 'L')
        self.ln(5)
        
        # Linha separadora
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
    def add_exams_list(self, exames):
        # Título da seção
        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, 'Solicito:', 0, 1, 'L')
        self.ln(2)
        
        # Lista de exames
        self.set_font('Arial', '', 10)
        for exame in exames:
            # Bullet point (usando asterisco em vez de bullet unicode)
            self.cell(5, 6, '*', 0, 0, 'L')
            self.cell(0, 6, exame, 0, 1, 'L')
            self.ln(1)

def categorizar_exames(recommendations):
    """Categoriza exames em Laboratoriais e de Imagem"""
    exames_laboratoriais = []
    exames_imagem = []
    
    for rec in recommendations:
        categoria = rec.get('categoria', '').lower()
        titulo = rec.get('titulo', '')
        
        if 'laboratorial' in categoria or 'exames laboratoriais' in categoria:
            exames_laboratoriais.append(titulo)
        elif 'imagem' in categoria or 'exames de imagem' in categoria:
            exames_imagem.append(titulo)
        elif any(keyword in titulo.lower() for keyword in ['tomografia', 'ressonância', 'ultrassom', 'raio-x', 'mamografia', 'densitometria']):
            exames_imagem.append(titulo)
        else:
            # Por padrão, considera como laboratorial
            exames_laboratoriais.append(titulo)
    
    return exames_laboratoriais, exames_imagem

def gerar_pdf_solicitacao(exames, tipo_exame, dados_medico, dados_paciente):
    """Gera PDF de solicitação de exames"""
    pdf = SolicitacaoExamePDF()
    pdf.add_page()
    
    # Adicionar informações da clínica
    pdf.add_clinic_info()
    
    # Adicionar dados do médico
    medico_nome = dados_medico.get('nome', '')
    medico_crm = dados_medico.get('crm', '')
    pdf.add_doctor_info(medico_nome, medico_crm)
    
    # Adicionar dados do paciente
    paciente_nome = dados_paciente.get('nome', '')
    paciente_cpf = dados_paciente.get('cpf', '')
    paciente_sexo = dados_paciente.get('sexo', '')
    paciente_idade = dados_paciente.get('idade', '')
    pdf.add_patient_info(paciente_nome, paciente_cpf, paciente_sexo, paciente_idade)
    
    # Adicionar lista de exames
    pdf.add_exams_list(exames)
    
    return pdf.output()

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            # Ler dados do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
            
            # Extrair dados
            recommendations = data.get('recommendations', [])
            patient_data = data.get('patient_data', {})
            
            # Dados do médico (podem vir dos dados do paciente ou serem padrão)
            dados_medico = {
                'nome': data.get('medico', {}).get('nome', ''),
                'crm': data.get('medico', {}).get('crm', '')
            }
            
            # Dados do paciente
            dados_paciente = {
                'nome': patient_data.get('nome', ''),
                'cpf': patient_data.get('cpf', ''),
                'sexo': patient_data.get('sexo', ''),
                'idade': patient_data.get('idade', '')
            }
            
            # Categorizar exames
            exames_laboratoriais, exames_imagem = categorizar_exames(recommendations)
            
            pdfs_gerados = []
            
            # Gerar PDF para exames laboratoriais
            if exames_laboratoriais:
                pdf_lab = gerar_pdf_solicitacao(
                    exames_laboratoriais, 
                    'Laboratorial', 
                    dados_medico, 
                    dados_paciente
                )
                pdfs_gerados.append({
                    'tipo': 'Laboratorial',
                    'filename': f'Solicitacao_Laboratorial_{dados_paciente.get("nome", "Paciente").replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf',
                    'content': base64.b64encode(pdf_lab).decode('utf-8'),
                    'exames_count': len(exames_laboratoriais)
                })
            
            # Gerar PDF para exames de imagem
            if exames_imagem:
                pdf_img = gerar_pdf_solicitacao(
                    exames_imagem, 
                    'Imagem', 
                    dados_medico, 
                    dados_paciente
                )
                pdfs_gerados.append({
                    'tipo': 'Imagem',
                    'filename': f'Solicitacao_Imagem_{dados_paciente.get("nome", "Paciente").replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf',
                    'content': base64.b64encode(pdf_img).decode('utf-8'),
                    'exames_count': len(exames_imagem)
                })
            
            # Se não há exames categorizados, gerar um PDF geral
            if not pdfs_gerados:
                todos_exames = [rec.get('titulo', '') for rec in recommendations]
                if todos_exames:
                    pdf_geral = gerar_pdf_solicitacao(
                        todos_exames, 
                        'Geral', 
                        dados_medico, 
                        dados_paciente
                    )
                    pdfs_gerados.append({
                        'tipo': 'Geral',
                        'filename': f'Solicitacao_Exames_{dados_paciente.get("nome", "Paciente").replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf',
                        'content': base64.b64encode(pdf_geral).decode('utf-8'),
                        'exames_count': len(todos_exames)
                    })
            
            # Resposta JSON com os PDFs gerados
            response = {
                'success': True,
                'pdfs': pdfs_gerados,
                'total_pdfs': len(pdfs_gerados),
                'exames_laboratoriais': len(exames_laboratoriais),
                'exames_imagem': len(exames_imagem)
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            # Enviar erro
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {
                'success': False,
                'error': str(e),
                'details': repr(e)
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
