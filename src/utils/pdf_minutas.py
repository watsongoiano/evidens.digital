"""Minutas em PDF (pedidos de exames e receita de vacinas), geradas na própria função.

Não há serviço externo: o PDF é montado com a biblioteca fpdf2 e as fontes
DejaVu que acompanham o repositório (assets/fonts). O texto vindo do navegador
(nome do paciente, títulos) é desenhado como texto, nunca interpretado.
"""
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

FONTES = Path(__file__).resolve().parents[2] / 'assets' / 'fonts'

AVISO = 'Documento sem assinatura digital. Válido somente com assinatura e carimbo do médico.'
LINHA_ASSINATURA = 'Assinatura e Carimbo do Médico'

# Posologia impressa na receita, por termo encontrado no título da vacina.
VACINAS_ADMINISTRACAO = {
    "efluelda": "Aplicar uma dose (0,7 ml), INTRAMUSCULAR, anualmente.",
    "influenza": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, anualmente.",
    "gardasil": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR. Até 19 anos: 2 doses (0 e 6 meses); a partir de 20 anos: 3 doses (0, 2 e 6 meses).",
    "hpv": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR. Até 19 anos: 2 doses (0 e 6 meses); a partir de 20 anos: 3 doses (0, 2 e 6 meses).",
    "twinrix": "Aplicar uma dose (1,0 ml), INTRAMUSCULAR, no intervalo 0, 1 e 6 meses.",
    "hepatite b": "Aplicar uma dose (1,0 ml), INTRAMUSCULAR, no intervalo 0, 1 e 6 meses.",
    "hepatite a": "Aplicar uma dose (1,0 ml), INTRAMUSCULAR, no intervalo 0 e 6 meses.",
    "dtpa": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, com reforço a cada 10 anos.",
    "triplice viral": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, no intervalo 0 e 1 mês.",
    "tríplice viral": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, no intervalo 0 e 1 mês.",
    "scr": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, no intervalo 0 e 1 mês.",
    "febre amarela": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, dose única.",
    # Meningocócicas: cada tipo com seu esquema; outra meningocócica (C, por exemplo) cai na
    # posologia padrão em vez de herdar o esquema de outro tipo.
    "acwy": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR. Reforço a cada 5 anos para grupos de risco.",
    "meningocócica b": "Aplicar duas doses (0,5 ml), INTRAMUSCULAR. Bexsero®: intervalo de 1 mês. Trumenba®: intervalo de 6 meses. Sem reforço de rotina.",
    "meningococica b": "Aplicar duas doses (0,5 ml), INTRAMUSCULAR. Bexsero®: intervalo de 1 mês. Trumenba®: intervalo de 6 meses. Sem reforço de rotina.",
    "bexsero": "Aplicar duas doses (0,5 ml), INTRAMUSCULAR, com intervalo de 1 mês. Sem reforço de rotina.",
    "trumenba": "Aplicar duas doses (0,5 ml), INTRAMUSCULAR, com intervalo de 6 meses. Sem reforço de rotina.",
    "dengue": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, no intervalo 0 e 3 meses.",
    "covid": "Aplicar conforme esquema vacinal vigente e orientação do Ministério da Saúde.",
    "varicela": "Aplicar uma dose (0,5 ml), SUBCUTÂNEA, no intervalo 0 e 1-2 meses.",
    "pneumoc": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, dose única (VPC20).",
    "herpes z": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, no intervalo 0 e 2 meses.",
    "zóster": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, no intervalo 0 e 2 meses.",
    "rsv": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, dose única.",
    "vsr": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, dose única.",
    " dt": "Aplicar uma dose (0,5 ml), INTRAMUSCULAR, com reforço a cada 10 anos.",
}
POSOLOGIA_PADRAO = 'Aplicar conforme orientação médica e bula do fabricante.'


def posologia_da_vacina(titulo):
    t = f' {titulo.lower()}'
    for termo, texto in VACINAS_ADMINISTRACAO.items():
        if termo in t:
            return texto
    return POSOLOGIA_PADRAO


def _rotulo_sexo(sexo):
    """Sexo ausente não é impresso como masculino."""
    if sexo in ('F', 'feminino'):
        return 'Feminino'
    if sexo in ('M', 'masculino'):
        return 'Masculino'
    return 'Não informado'


def _texto(valor, maximo=300):
    """Garante texto simples e de tamanho limitado, sem quebras de linha de controle."""
    s = str(valor if valor is not None else '')
    s = ''.join(c if c.isprintable() or c == '\n' else ' ' for c in s)
    return s[:maximo]


class _Minuta(FPDF):
    def __init__(self, titulo):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.titulo = titulo
        self.set_margins(20, 18, 20)
        self.set_auto_page_break(auto=True, margin=42)   # espaço para assinatura e rodapé
        self.add_font('DejaVu', '', str(FONTES / 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', str(FONTES / 'DejaVuSans-Bold.ttf'))
        self.set_title(titulo)
        self.set_author('Evidēns')

    def header(self):
        self.set_font('DejaVu', 'B', 11)
        self.set_text_color(14, 151, 181)
        self.cell(0, 6, 'evidēns', new_x='LMARGIN', new_y='NEXT')
        self.set_font('DejaVu', 'B', 15)
        self.set_text_color(20, 41, 47)
        self.cell(0, 10, self.titulo, align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(20, 41, 47)
        self.line(20, self.get_y() + 1, 190, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_font('DejaVu', '', 7.5)
        self.set_text_color(90, 100, 103)
        self.cell(0, 5, f'Página {self.page_no()}/{{nb}}', align='R')

    def dados_do_paciente(self, dados):
        idade = dados.get('idade')
        self.set_font('DejaVu', '', 10.5)
        self.set_text_color(20, 41, 47)
        self.cell(0, 6, f'Data de emissão: {datetime.now().strftime("%d/%m/%Y")}', new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 6, f'Paciente: {_texto(dados.get("nome") or "Não informado", 150)}', new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 6, f'Sexo: {_rotulo_sexo(dados.get("sexo"))}     Idade: {f"{_texto(idade, 10)} anos" if idade else "Não informada"}',
                  new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

    def assinatura(self):
        """Linha de assinatura no fim da última página (nova página se não couber)."""
        if self.get_y() > 232:
            self.add_page()
        # A assinatura fica dentro da margem reservada à quebra automática: desligá-la aqui.
        self.set_auto_page_break(auto=False)
        self.set_y(-44)
        self.set_draw_color(20, 41, 47)
        self.line(60, self.get_y(), 150, self.get_y())
        self.set_font('DejaVu', '', 9.5)
        self.set_text_color(20, 41, 47)
        self.cell(0, 6, LINHA_ASSINATURA, align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('DejaVu', '', 8)
        self.set_text_color(90, 100, 103)
        self.multi_cell(0, 4.5, AVISO, align='C')

    def bytes(self):
        return bytes(self.output())


def _pdf_de_exames(dados_paciente, exames, tipo):
    pdf = _Minuta(f'SOLICITAÇÃO DE EXAMES {tipo}')
    pdf.add_page()
    pdf.dados_do_paciente(dados_paciente)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(0, 7, 'Solicito:', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('DejaVu', '', 10.5)
    for n, exame in enumerate(exames, 1):
        pdf.set_x(24)
        pdf.set_font('DejaVu', '', 10.5)
        pdf.multi_cell(0, 6.2, f'{n}. {_texto(exame.get("titulo"))}')
        quando = exame.get('quando_pdf')
        if isinstance(quando, str) and quando.strip():
            # Pré-natal: a janela gestacional vai no pedido, para exame antecipado não parecer imediato.
            pdf.set_font('DejaVu', '', 9)
            pdf.set_text_color(90, 100, 103)
            pdf.set_x(30)
            pdf.multi_cell(0, 5, _texto(quando[:160]))
            pdf.set_text_color(20, 41, 47)
    pdf.assinatura()
    return pdf.bytes()


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    return _pdf_de_exames(dados_paciente, exames, 'LABORATORIAIS')


def gerar_pdf_exames_imagem(dados_paciente, exames):
    return _pdf_de_exames(dados_paciente, exames, 'DE IMAGEM')


def gerar_pdf_vacinas(dados_paciente, vacinas):
    pdf = _Minuta('RECEITA DE VACINAS')
    pdf.add_page()
    pdf.dados_do_paciente(dados_paciente)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(0, 7, 'Prescrevo:', new_x='LMARGIN', new_y='NEXT')
    for n, vacina in enumerate(vacinas, 1):
        titulo = _texto(vacina.get('titulo') or 'Vacina')
        pdf.set_font('DejaVu', 'B', 10.5)
        pdf.set_x(24)
        pdf.multi_cell(0, 6.2, f'{n}. {titulo.upper()}')
        pdf.set_font('DejaVu', '', 9.5)
        pdf.set_x(30)
        pdf.multi_cell(0, 5.5, posologia_da_vacina(titulo))
        pdf.ln(2)
    pdf.assinatura()
    return pdf.bytes()
