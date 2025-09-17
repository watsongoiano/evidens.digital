from http.server import BaseHTTPRequestHandler
import json
import io
import base64
from datetime import datetime
from fpdf import FPDF


def _normalize_text(value: object, *, default: str = "") -> str:
    """Return a safe string representation, ignoring ``None`` values."""

    if value is None:
        return default

    text = str(value)
    return text if text is not None else default


def _ensure_dict(value: object) -> dict:
    """Return ``value`` if it is a dict, otherwise an empty dict."""

    return value if isinstance(value, dict) else {}


def _ensure_list(value: object) -> list:
    """Return ``value`` if it is a list, otherwise an empty list."""

    return value if isinstance(value, list) else []


def _sanitize_name_for_filename(value: object) -> str:
    """Convert a name into a safe fragment for filenames."""

    base_name = _normalize_text(value).strip() or "Paciente"
    return base_name.replace(" ", "_")

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
            exame_texto = _normalize_text(exame).strip()
            if not exame_texto:
                continue
            # Bullet point (usando asterisco em vez de bullet unicode)
            self.cell(5, 6, '*', 0, 0, 'L')
            self.cell(0, 6, exame_texto, 0, 1, 'L')
            self.ln(1)

def categorizar_exames(recommendations):
    """Categoriza exames em Laboratoriais e de Imagem"""

    exames_laboratoriais = []
    exames_imagem = []

    for rec in _ensure_list(recommendations):
        if not isinstance(rec, dict):
            continue

        categoria = _normalize_text(rec.get('categoria')).lower()
        titulo = _normalize_text(rec.get('titulo'))

        if not titulo:
            continue

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
    medico_nome = _normalize_text(dados_medico.get('nome'))
    medico_crm = _normalize_text(dados_medico.get('crm'))
    pdf.add_doctor_info(medico_nome, medico_crm)

    # Adicionar dados do paciente
    paciente_nome = _normalize_text(dados_paciente.get('nome'))
    paciente_cpf = _normalize_text(dados_paciente.get('cpf'))
    paciente_sexo = _normalize_text(dados_paciente.get('sexo'))
    idade_valor = dados_paciente.get('idade')
    paciente_idade = _normalize_text(idade_valor) if idade_valor not in (None, '') else ''
    pdf.add_patient_info(paciente_nome, paciente_cpf, paciente_sexo, paciente_idade)

    # Adicionar lista de exames
    pdf.add_exams_list(_ensure_list(exames))

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
            if not isinstance(data, dict):
                data = {}

            # Extrair dados
            recommendations = _ensure_list(data.get('recommendations'))
            patient_data = _ensure_dict(data.get('patient_data'))
            medico_data = _ensure_dict(data.get('medico'))
            raw_tipo_exame = data.get('tipo_exame', 'todos')
            tipo_exame = _normalize_text(raw_tipo_exame, default='todos').lower() or 'todos'

            # Dados do médico (podem vir dos dados do paciente ou serem padrão)
            dados_medico = {
                'nome': _normalize_text(medico_data.get('nome')),
                'crm': _normalize_text(medico_data.get('crm'))
            }

            # Dados do paciente
            dados_paciente = {
                'nome': _normalize_text(patient_data.get('nome')),
                'cpf': _normalize_text(patient_data.get('cpf')),
                'sexo': _normalize_text(patient_data.get('sexo')),
                'idade': patient_data.get('idade')
            }
            
            pdfs_gerados = []
            exames_laboratoriais = []
            exames_imagem = []

            # Processar baseado no tipo solicitado
            if tipo_exame == 'laboratorial':
                # Gerar apenas PDF de exames laboratoriais
                exames = [
                    titulo
                    for rec in recommendations
                    if isinstance(rec, dict)
                    for titulo in [_normalize_text(rec.get('titulo')).strip()]
                    if titulo
                ]
                exames_laboratoriais = exames
                if exames:
                    pdf_lab = gerar_pdf_solicitacao(
                        exames,
                        'Laboratorial',
                        dados_medico,
                        dados_paciente
                    )
                    pdfs_gerados.append({
                        'tipo': 'Laboratorial',
                        'filename': f'Solicitacao_Laboratorial_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
                        'content': base64.b64encode(pdf_lab).decode('utf-8'),
                        'exames_count': len(exames)
                    })

            elif tipo_exame == 'imagem':
                # Gerar apenas PDF de exames de imagem
                exames = [
                    titulo
                    for rec in recommendations
                    if isinstance(rec, dict)
                    for titulo in [_normalize_text(rec.get('titulo')).strip()]
                    if titulo
                ]
                exames_imagem = exames
                if exames:
                    pdf_img = gerar_pdf_solicitacao(
                        exames,
                        'Imagem',
                        dados_medico,
                        dados_paciente
                    )
                    pdfs_gerados.append({
                        'tipo': 'Imagem',
                        'filename': f'Solicitacao_Imagem_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
                        'content': base64.b64encode(pdf_img).decode('utf-8'),
                        'exames_count': len(exames)
                    })

            else:
                # Comportamento original - categorizar e gerar ambos
                exames_laboratoriais, exames_imagem = categorizar_exames(recommendations)

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
                        'filename': f'Solicitacao_Laboratorial_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
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
                        'filename': f'Solicitacao_Imagem_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
                        'content': base64.b64encode(pdf_img).decode('utf-8'),
                        'exames_count': len(exames_imagem)
                    })
            
            # Se não há exames categorizados, gerar um PDF geral
            if not pdfs_gerados:
                todos_exames = [
                    titulo
                    for rec in recommendations
                    if isinstance(rec, dict)
                    for titulo in [_normalize_text(rec.get('titulo')).strip()]
                    if titulo
                ]
                if todos_exames:
                    pdf_geral = gerar_pdf_solicitacao(
                        todos_exames, 
                        'Geral', 
                        dados_medico, 
                        dados_paciente
                    )
                    pdfs_gerados.append({
                        'tipo': 'Geral',
                        'filename': f'Solicitacao_Exames_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
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
