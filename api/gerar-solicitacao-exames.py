from http.server import BaseHTTPRequestHandler
import json
import base64
import unicodedata
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


def _normalize_for_matching(value: object) -> str:
    """Return a normalized representation for keyword matching."""

    text = _normalize_text(value)
    if not text:
        return ""

    decomposed = unicodedata.normalize('NFD', text)
    stripped = ''.join(ch for ch in decomposed if unicodedata.category(ch) != 'Mn')
    return stripped.casefold()


LAB_CATEGORY_KEYWORDS = (
    'laboratorio',
    'laboratorial',
    'laboratoriais',
    'lab',
)

IMAGING_CATEGORY_KEYWORDS = (
    'imagem',
    'radiologia',
)

LAB_TITLE_KEYWORDS = (
    'soro',
    'sangue',
    'serum',
    'plasma',
    'urina',
    'fezes',
    'hemograma',
    'hemoglob',
    'glic',
    'colesterol',
    'lipoproteina',
    'lp(a',
    'lpa',
    'apolipoprote',
    'hscrp',
    'proteina c reativa',
    'proteina c',
    'pcr',
    'reativa',
    'ultrassensivel',
    'psa',
    'totg',
    'tsh',
    'creatinina',
    'ureia',
    'microalbumin',
    'ferritina',
    'transferrina',
    'vitamina d',
    'homocisteina',
    'd-dimero',
    'dimero',
    'hiv',
    'hepatite',
)

IMAGING_TITLE_KEYWORDS = (
    'tomograf',
    'resson',
    'ultrassom',
    'ultrasonograf',
    'ecografia',
    'ecocardio',
    'eletrocardiograma',
    'mamograf',
    'colonoscop',
    'densitometr',
    'raio x',
    'raiox',
    'radiograf',
    'mapa',
    'mrpa',
    'holter',
    'strain',
    'score de calcio',
    'calcio coron',
    'tcbd',
    'doppler',
    'angiotom',
    'angiograf',
    'cintilograf',
    'pet',
    'dexa',
)


SPECIAL_EXAM_TITLE_REPLACEMENTS = {
    _normalize_for_matching('Citologia Cervical + Teste de HPV'): [
        {
            'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular, autocoleta',
            'tipo': 'laboratorial',
        },
        {
            'titulo': 'Citologia cérvico-vaginal, em base líqüida, material vaginal e colo uterino',
            'tipo': 'laboratorial',
        },
    ],
}


def _classify_exam_type(rec: dict) -> str:
    """Return ``imagem`` or ``laboratorial`` based on exam metadata."""

    categoria = _normalize_for_matching(rec.get('categoria'))
    titulo = _normalize_for_matching(rec.get('titulo'))
    subtitulo = _normalize_for_matching(rec.get('subtitulo'))
    descricao = _normalize_for_matching(rec.get('descricao'))

    if not titulo:
        return ''

    if any(keyword in categoria for keyword in IMAGING_CATEGORY_KEYWORDS):
        return 'imagem'
    if any(keyword in categoria for keyword in LAB_CATEGORY_KEYWORDS):
        return 'laboratorial'

    combined = ' '.join(filter(None, (titulo, subtitulo, descricao)))

    if any(keyword in combined for keyword in IMAGING_TITLE_KEYWORDS):
        return 'imagem'
    if any(keyword in combined for keyword in LAB_TITLE_KEYWORDS):
        return 'laboratorial'

    return 'laboratorial'

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
        
    def add_doctor_info(self, nome, crm):
        # Dr(a).
        self.set_font('Arial', '', 10)
        self.cell(30, 6, 'Dr(a).', 0, 0, 'L')
        
        # CRM (lado direito)
        self.set_xy(150, self.get_y())
        self.cell(0, 6, f'CRM: {crm}', 0, 1, 'L')
        self.ln(10)
        
    def add_patient_info(self, nome, cpf, sexo, idade):
        # Linha separadora
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
        # Informações do paciente em uma linha
        self.set_font('Arial', '', 10)
        
        # Paciente
        self.cell(20, 6, 'Paciente:', 0, 0, 'L')
        self.cell(60, 6, nome, 0, 0, 'L')
        
        # Sexo
        self.cell(15, 6, 'Sexo:', 0, 0, 'L')
        self.cell(30, 6, sexo.capitalize() if sexo else '', 0, 0, 'L')
        
        # Idade
        self.cell(15, 6, 'Idade:', 0, 0, 'L')
        self.cell(0, 6, str(idade), 0, 1, 'L')
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
    """Categoriza exames em laboratoriais e de imagem de forma resiliente."""

    exames_laboratoriais = []
    exames_imagem = []
    vistos_laboratoriais = set()
    vistos_imagem = set()

    def _append_exam(rec, *, force_tipo=None):
        if not isinstance(rec, dict):
            return

        titulo_texto = _normalize_text(rec.get('titulo')).strip()
        if not titulo_texto:
            return

        rec_normalizado = dict(rec)
        rec_normalizado['titulo'] = titulo_texto

        tipo_forcado = ''
        if isinstance(force_tipo, str):
            tipo_forcado = force_tipo.strip().lower()

        tipo = tipo_forcado or _classify_exam_type(rec_normalizado)
        if tipo not in ('imagem', 'laboratorial'):
            tipo = 'laboratorial'

        if tipo == 'imagem':
            if titulo_texto not in vistos_imagem:
                exames_imagem.append(titulo_texto)
                vistos_imagem.add(titulo_texto)
        else:
            if titulo_texto not in vistos_laboratoriais:
                exames_laboratoriais.append(titulo_texto)
                vistos_laboratoriais.add(titulo_texto)

    for rec in _ensure_list(recommendations):
        if not isinstance(rec, dict):
            continue

        titulo = _normalize_text(rec.get('titulo')).strip()
        if not titulo:
            continue

        titulo_normalizado = _normalize_for_matching(titulo)
        substituicoes = SPECIAL_EXAM_TITLE_REPLACEMENTS.get(titulo_normalizado)

        if substituicoes:
            for substituicao in substituicoes:
                novo_titulo = substituicao.get('titulo')
                if not novo_titulo:
                    continue

                rec_substituido = dict(rec)
                rec_substituido['titulo'] = novo_titulo

                for chave, valor in substituicao.items():
                    if chave in {'titulo', 'tipo'}:
                        continue
                    rec_substituido[chave] = valor

                _append_exam(rec_substituido, force_tipo=substituicao.get('tipo'))
            continue

        _append_exam(rec)

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
            
            todos_os_exames = [
                titulo
                for rec in recommendations
                if isinstance(rec, dict)
                for titulo in [_normalize_text(rec.get('titulo')).strip()]
                if titulo
            ]

            categorizados_laboratoriais, categorizados_imagem = categorizar_exames(recommendations)

            pdfs_gerados = []
            exames_laboratoriais = []
            exames_imagem = []

            # Processar baseado no tipo solicitado
            if tipo_exame == 'laboratorial':
                exames = categorizados_laboratoriais or todos_os_exames
                exames_laboratoriais = exames
                exames_imagem = categorizados_imagem
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
                exames = categorizados_imagem or todos_os_exames
                exames_imagem = exames
                exames_laboratoriais = categorizados_laboratoriais
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
                exames_laboratoriais = categorizados_laboratoriais
                exames_imagem = categorizados_imagem

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
            if not pdfs_gerados and todos_os_exames:
                pdf_geral = gerar_pdf_solicitacao(
                    todos_os_exames, 
                    'Geral', 
                    dados_medico, 
                    dados_paciente
                )
                pdfs_gerados.append({
                    'tipo': 'Geral',
                    'filename': f'Solicitacao_Exames_{_sanitize_name_for_filename(dados_paciente.get("nome"))}_{datetime.now().strftime("%Y%m%d")}.pdf',
                    'content': base64.b64encode(pdf_geral).decode('utf-8'),
                    'exames_count': len(todos_os_exames)
                })

            # Resposta de sucesso
            response_data = {
                'success': True,
                'message': f'{len(pdfs_gerados)} PDF(s) gerado(s) com sucesso',
                'pdfs': pdfs_gerados,
                'categorization': {
                    'laboratoriais': exames_laboratoriais,
                    'imagem': exames_imagem,
                    'total_exames': len(todos_os_exames)
                }
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            # Resposta de erro
            error_response = {
                'success': False,
                'error': str(e),
                'message': 'Erro interno do servidor ao gerar solicitação de exames'
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
