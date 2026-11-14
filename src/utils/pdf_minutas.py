"""Minutas em PDF (pedidos de exames e receita de vacinas), geradas na própria função.

Não há serviço externo: o PDF é montado com a biblioteca fpdf2 e as fontes
DejaVu que acompanham o repositório (assets/fonts). O texto vindo do navegador
(nome do paciente, títulos) é desenhado como texto, nunca interpretado.

Idioma: os textos são escritos aqui em português e a versão em inglês sai do mesmo
dicionário das páginas (static/i18n/en.json), na hora de desenhar. O pedido chega
sempre com os títulos em português, porque a posologia e a triagem de segurança
são decididas por eles.
"""
import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from src.utils import i18n

FONTES = Path(__file__).resolve().parents[2] / 'assets' / 'fonts'

AVISO = 'Documento sem assinatura digital. Válido somente com assinatura e carimbo do médico.'
LINHA_ASSINATURA = 'Assinatura e Carimbo do Médico'
TITULOS = {'laboratorio': 'SOLICITAÇÃO DE EXAMES LABORATORIAIS', 'imagem': 'SOLICITAÇÃO DE EXAMES DE IMAGEM',
           'vacina': 'RECEITA DE VACINAS'}
# Textos fixos das minutas (os testes conferem que cada um tem par em inglês).
FIXOS = ('Solicito:', 'Prescrevo:', 'Data de emissão', 'Paciente', 'Sexo', 'Idade', 'anos', 'Página', 'Feminino', 'Masculino',
         'Não informado', 'Não informada', 'Minuta preparada por', 'estudante de medicina', 'Vacina')
MESES_EN = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def data_de_emissao(idioma='pt', agora=None):
    agora = agora or datetime.now()
    if idioma == 'en':
        return f'{MESES_EN[agora.month - 1]} {agora.day}, {agora.year}'
    return agora.strftime('%d/%m/%Y')

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


# Esquemas de grupo de risco: substituem a posologia de rotina quando a recomendação traz 'esquema_pdf'.
ESQUEMAS_DE_RISCO = {
    'asplenia': {
        'acwy': 'Asplenia: aplicar duas doses (0,5 ml), INTRAMUSCULAR, com 8 semanas de intervalo. Reforço a cada 5 anos.',
        'meningocócica b': 'Asplenia: aplicar duas doses (0,5 ml), INTRAMUSCULAR, com 1 mês de intervalo (Bexsero®). '
                           'Reforço 1 ano após o esquema e, depois, a cada 2-3 anos.',
        'hib': 'Asplenia: aplicar uma dose (0,5 ml), INTRAMUSCULAR, dose única se não vacinado previamente.',
    },
}


def posologia_da_vacina(titulo, esquema=None):
    t = f' {titulo.lower()}'
    for termo, texto in ESQUEMAS_DE_RISCO.get(esquema, {}).items():
        if termo in t:
            return texto
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


def responsavel_de(usuario):
    """Quem responde pelo documento, a partir da conta logada.

    Médico e residente assinam: nome sob a linha, com o CRM quando o registro é reconhecido
    (conta antiga com registro fora do padrão sai só com o nome). Estudante não assina:
    o nome aparece como quem preparou a minuta.
    """
    if not usuario or not (usuario.get('nome') or '').strip():
        return None
    from src.utils import contas
    # O perfil da conta decide quem assina; o texto do registro só fornece o CRM.
    estudante = usuario.get('perfil') == 'estudante'
    return {'nome': usuario['nome'].strip(), 'estudante': estudante,
            'crm': None if estudante else contas.crm_de(usuario)}


class _Minuta(FPDF):
    def __init__(self, titulo, idioma='pt'):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.idioma = idioma
        titulo = self.t(titulo)
        self.titulo = titulo
        self.set_margins(20, 18, 20)
        self.set_auto_page_break(auto=True, margin=42)   # espaço para assinatura e rodapé
        self.add_font('DejaVu', '', str(FONTES / 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', str(FONTES / 'DejaVuSans-Bold.ttf'))
        self.set_title(titulo)
        self.set_author('Evidēns')

    def t(self, texto):
        """O texto no idioma do documento (o que não tem par, como um item digitado, sai como veio)."""
        return i18n.traduzir(texto, self.idioma)

    def header(self):
        if getattr(self, 'em_guia', False):
            return
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
        if getattr(self, 'em_guia', False):
            return
        self.set_y(-14)
        self.set_font('DejaVu', '', 7.5)
        self.set_text_color(90, 100, 103)
        self.cell(0, 5, f'{self.t("Página")} {self.page_no()}/{{nb}}', align='R')

    def dados_do_paciente(self, dados):
        idade = dados.get('idade')
        self.set_font('DejaVu', '', 10.5)
        self.set_text_color(20, 41, 47)
        t = self.t
        self.cell(0, 6, f'{t("Data de emissão")}: {data_de_emissao(self.idioma)}', new_x='LMARGIN', new_y='NEXT')
        nome = dados.get('nome') or 'Não informado'
        if nome in ('Paciente', 'Não informado'):  # só o nome genérico muda de idioma; nome de gente nunca
            nome = t(nome)
        self.cell(0, 6, f'{t("Paciente")}: {_texto(nome, 150)}', new_x='LMARGIN', new_y='NEXT')
        anos = f'{_texto(idade, 10)} {t("anos")}' if idade else t('Não informada')
        self.cell(0, 6, f'{t("Sexo")}: {t(_rotulo_sexo(dados.get("sexo")))}     {t("Idade")}: {anos}', new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

    def assinatura(self):
        """Linha de assinatura no fim da última página (nova página se não couber)."""
        if self.get_y() > 224:
            self.add_page()
        # A assinatura fica dentro da margem reservada à quebra automática: desligá-la aqui.
        self.set_auto_page_break(auto=False)
        self.set_y(-52)
        self.set_draw_color(20, 41, 47)
        self.line(60, self.get_y(), 150, self.get_y())
        self.set_font('DejaVu', '', 9.5)
        self.set_text_color(20, 41, 47)
        resp = getattr(self, 'responsavel', None)
        if resp and not resp.get('estudante'):
            self.set_font('DejaVu', 'B', 9.5)
            self.cell(0, 5, resp['nome'], align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('DejaVu', '', 9.5)
            if resp.get('crm'):
                self.cell(0, 5, resp['crm'], align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('DejaVu', '', 8.5)
        self.cell(0, 5, self.t(LINHA_ASSINATURA), align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('DejaVu', '', 8)
        self.set_text_color(90, 100, 103)
        if resp and resp.get('estudante'):
            self.multi_cell(0, 4.5, f"{self.t('Minuta preparada por')} {resp['nome']} ({self.t('estudante de medicina')}).",
                            align='C', new_x='LMARGIN', new_y='NEXT')
        self.multi_cell(0, 4.5, self.t(AVISO), align='C')

    def bytes(self):
        return bytes(self.output())


# ── Guia SP/SADT (padrão TISS) ──────────────────────────────────────────────
# A guia é um formulário brasileiro padronizado pela ANS: sai sempre em português,
# com os números de campo do padrão. O Evidēns preenche a parte da SOLICITAÇÃO
# (campos 1, 8 a 19 e 21 a 27); senha, validade, autorização e execução são da
# operadora e do prestador executante, e ficam em branco.

LINHAS_POR_GUIA = 5      # a guia impressa do padrão tem 5 linhas de procedimentos solicitados
CARATER_ELETIVO = '1 - Eletivo'


def indicacao_clinica(texto):
    """Indicação clínica da guia (campo 23): o que o médico escreveu, ou "Check-up"."""
    return _texto(' '.join(str(texto or '').split()), 150) or 'Check-up'


def _numero_do_crm(crm):
    """('GO', '26815') a partir de 'CRM-GO 26815'; ('', '') se não reconhecer."""
    partes = re.match(r'^CRM-([A-Z]{2}) (\d+)$', crm or '')
    return (partes.group(1), partes.group(2)) if partes else ('', '')


def _campo(pdf, x, y, largura, altura, rotulo, valor='', tamanho=9):
    pdf.set_draw_color(20, 41, 47)
    pdf.rect(x, y, largura, altura)
    pdf.set_xy(x + 0.8, y + 0.5)
    pdf.set_font('DejaVu', '', 5.6)
    pdf.set_text_color(70, 80, 84)
    pdf.cell(largura - 1.6, 2.6, rotulo)
    if valor:
        pdf.set_font('DejaVu', '', tamanho)
        pdf.set_text_color(20, 41, 47)
        valor = _texto(valor, 200)
        while pdf.get_string_width(valor) > largura - 2.4 and len(valor) > 4:
            valor = valor[:-2]
        pdf.set_xy(x + 1.2, y + 3.4)
        pdf.cell(largura - 2.4, altura - 4.2, valor)


def _faixa(pdf, y, texto):
    pdf.set_fill_color(225, 232, 234)
    pdf.set_xy(10, y)
    pdf.set_font('DejaVu', 'B', 6.5)
    pdf.set_text_color(20, 41, 47)
    pdf.cell(277, 4, texto, fill=True)
    return y + 4


def _pagina_da_guia(pdf, dados_paciente, guia, linhas, parte, partes):
    pdf.add_page(orientation='L')
    cred, resp = guia['credenciamento'], guia.get('responsavel') or {}
    uf, numero = _numero_do_crm(resp.get('crm'))
    pdf.set_xy(10, 9)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.set_text_color(20, 41, 47)
    pdf.cell(60, 7, _texto(cred['operadora'], 40))
    pdf.set_font('DejaVu', 'B', 8.5)
    pdf.set_xy(70, 9)
    pdf.cell(160, 7, 'GUIA DE SERVIÇO PROFISSIONAL / SERVIÇO AUXILIAR DE DIAGNÓSTICO E TERAPIA - SP/SADT', align='C')
    _campo(pdf, 232, 8, 55, 9, '2 - Nº Guia no Prestador')
    y = 19
    _campo(pdf, 10, y, 30, 9, '1 - Registro ANS', cred.get('registro_ans'))
    _campo(pdf, 40, y, 52, 9, '3 - Nº Guia Principal')
    _campo(pdf, 92, y, 35, 9, '4 - Data da Autorização')
    _campo(pdf, 127, y, 55, 9, '5 - Senha')
    _campo(pdf, 182, y, 40, 9, '6 - Data de Validade da Senha')
    _campo(pdf, 222, y, 65, 9, '7 - Nº da Guia Atribuído pela Operadora')
    y = _faixa(pdf, y + 10, 'Dados do Beneficiário')
    nome = dados_paciente.get('nome') or ''
    _campo(pdf, 10, y, 62, 9, '8 - Número da Carteira', guia.get('carteira'))
    _campo(pdf, 72, y, 30, 9, '9 - Validade da Carteira')
    _campo(pdf, 102, y, 120, 9, '10 - Nome', '' if nome in ('Paciente', 'Não informado') else nome)
    _campo(pdf, 222, y, 45, 9, '11 - Cartão Nacional de Saúde')
    _campo(pdf, 267, y, 20, 9, '12 - Atend. a RN', 'N')
    y = _faixa(pdf, y + 10, 'Dados do Solicitante')
    _campo(pdf, 10, y, 62, 9, '13 - Código na Operadora', cred['codigo_prestador'])
    _campo(pdf, 72, y, 215, 9, '14 - Nome do Contratado', cred['nome_contratado'])
    y += 9
    _campo(pdf, 10, y, 92, 9, '15 - Nome do Profissional Solicitante', resp.get('nome'))
    _campo(pdf, 102, y, 32, 9, '16 - Conselho Profissional', 'CRM' if numero else '')
    _campo(pdf, 134, y, 34, 9, '17 - Número no Conselho', numero)
    _campo(pdf, 168, y, 14, 9, '18 - UF', uf)
    _campo(pdf, 182, y, 30, 9, '19 - Código CBO', cred.get('cbo'))
    _campo(pdf, 212, y, 75, 9, '20 - Assinatura do Profissional Solicitante')
    y = _faixa(pdf, y + 10, 'Dados da Solicitação / Procedimentos ou Itens Assistenciais Solicitados')
    _campo(pdf, 10, y, 40, 9, '21 - Caráter do Atendimento', CARATER_ELETIVO)
    _campo(pdf, 50, y, 40, 9, '22 - Data da Solicitação', data_de_emissao('pt'))
    _campo(pdf, 90, y, 197, 9, '23 - Indicação Clínica', guia['indicacao'])
    y += 9
    colunas = ((10, 18, '24 - Tabela'), (28, 34, '25 - Código do Procedimento'), (62, 177, '26 - Descrição'),
               (239, 24, '27 - Qtde. Solic.'), (263, 24, '28 - Qtde. Aut.'))
    pdf.set_font('DejaVu', '', 5.6)
    pdf.set_text_color(70, 80, 84)
    for x, largura, rotulo in colunas:
        pdf.rect(x, y, largura, 4.5)
        pdf.set_xy(x + 0.8, y + 0.9)
        pdf.cell(largura - 1.6, 2.6, rotulo)
    y += 4.5
    pdf.set_text_color(20, 41, 47)
    for n in range(LINHAS_POR_GUIA):
        linha = linhas[n] if n < len(linhas) else None
        valores = ((TABELA_TUSS if linha['codigo'] else '', linha['codigo'], linha['descricao'], str(linha['quantidade']), '')
                   if linha else ('', '', '', '', ''))
        for (x, largura, _), valor in zip(colunas, valores):
            pdf.rect(x, y, largura, 7)
            if valor:
                pdf.set_font('DejaVu', '', 8)
                valor = _texto(valor, 200)
                while pdf.get_string_width(valor) > largura - 2.4 and len(valor) > 4:
                    valor = valor[:-2]
                pdf.set_xy(x + 1.2, y + 1.2)
                pdf.cell(largura - 2.4, 4.6, valor)
        y += 7
    y = _faixa(pdf, y + 1, 'Dados do Contratado Executante')
    _campo(pdf, 10, y, 62, 9, '29 - Código na Operadora')
    _campo(pdf, 72, y, 170, 9, '30 - Nome do Contratado')
    _campo(pdf, 242, y, 45, 9, '31 - Código CNES')
    y += 11
    _campo(pdf, 10, y, 277, 18, 'Observação / Justificativa')
    pdf.set_xy(10, y + 20)
    pdf.set_font('DejaVu', '', 6.5)
    pdf.set_text_color(90, 100, 103)
    pdf.multi_cell(277, 3.4,
                   f'Guia {parte} de {partes} deste pedido. Solicitação preenchida pelo Evidēns no padrão TISS (ANS), com os códigos da '
                   'TUSS (tabela 22); linha sem código deve ser completada conforme a tabela da operadora. '
                   'Senha, validade e autorização são emitidas pela operadora. '
                   'Válida somente com assinatura e carimbo do médico solicitante.')


TABELA_TUSS = '22'


def _anexar_guias(pdf, dados_paciente, exames, guia):
    """Acrescenta ao pedido as guias SP/SADT (5 procedimentos por guia)."""
    from src.utils import tuss
    sexo = dados_paciente.get('sexo')
    sexo = {'F': 'feminino', 'M': 'masculino'}.get(sexo, sexo)
    linhas = []
    for exame in exames:
        for linha in tuss.linhas_da_guia(exame.get('titulo'), sexo):
            repetida = next((l for l in linhas if linha['codigo'] and l['codigo'] == linha['codigo']), None)
            if repetida:   # dois pedidos com o mesmo código (ex.: TGO pedido sozinho e no par TGO/TGP)
                repetida['quantidade'] = max(repetida['quantidade'], linha['quantidade'])
            else:
                linhas.append(linha)
    partes = max(1, -(-len(linhas) // LINHAS_POR_GUIA))
    pdf.em_guia = True
    pdf.set_auto_page_break(auto=False)
    for parte in range(partes):
        _pagina_da_guia(pdf, dados_paciente, guia, linhas[parte * LINHAS_POR_GUIA:(parte + 1) * LINHAS_POR_GUIA],
                        parte + 1, partes)


def _pdf_de_exames(dados_paciente, exames, categoria, responsavel=None, idioma='pt', guia=None):
    pdf = _Minuta(TITULOS[categoria], idioma)
    pdf.responsavel = responsavel
    pdf.add_page()
    pdf.dados_do_paciente(dados_paciente)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(0, 7, pdf.t('Solicito:'), new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('DejaVu', '', 10.5)
    for n, exame in enumerate(exames, 1):
        pdf.set_x(24)
        pdf.set_font('DejaVu', '', 10.5)
        pdf.multi_cell(0, 6.2, f'{n}. {_texto(pdf.t(exame.get("titulo")))}')
        quando = exame.get('quando_pdf')
        if isinstance(quando, str) and quando.strip():
            # Pré-natal: a janela gestacional vai no pedido, para exame antecipado não parecer imediato.
            pdf.set_font('DejaVu', '', 9)
            pdf.set_text_color(90, 100, 103)
            pdf.set_x(30)
            pdf.multi_cell(0, 5, _texto(pdf.t(quando[:160])))
            pdf.set_text_color(20, 41, 47)
    pdf.assinatura()
    if guia:
        _anexar_guias(pdf, dados_paciente, exames, dict(guia, responsavel=responsavel))
    return pdf.bytes()


def gerar_pdf_exames_laboratoriais(dados_paciente, exames, responsavel=None, idioma='pt', guia=None):
    return _pdf_de_exames(dados_paciente, exames, 'laboratorio', responsavel, idioma, guia)


def gerar_pdf_exames_imagem(dados_paciente, exames, responsavel=None, idioma='pt', guia=None):
    return _pdf_de_exames(dados_paciente, exames, 'imagem', responsavel, idioma, guia)


def gerar_pdf_vacinas(dados_paciente, vacinas, responsavel=None, idioma='pt'):
    pdf = _Minuta(TITULOS['vacina'], idioma)
    pdf.responsavel = responsavel
    pdf.add_page()
    pdf.dados_do_paciente(dados_paciente)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(0, 7, pdf.t('Prescrevo:'), new_x='LMARGIN', new_y='NEXT')
    for n, vacina in enumerate(vacinas, 1):
        titulo = _texto(vacina.get('titulo') or 'Vacina')
        pdf.set_font('DejaVu', 'B', 10.5)
        pdf.set_x(24)
        pdf.multi_cell(0, 6.2, f'{n}. {_texto(pdf.t(titulo)).upper()}')
        pdf.set_font('DejaVu', '', 9.5)
        pdf.set_x(30)
        # a posologia é escolhida pelo título em português; só o texto impresso muda de idioma
        pdf.multi_cell(0, 5.5, pdf.t(posologia_da_vacina(titulo, vacina.get('esquema_pdf'))))
        pdf.ln(2)
    pdf.assinatura()
    return pdf.bytes()
