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
# Com assinatura digital (src/utils/assinatura.py): no lugar da linha de assinatura e do aviso de minuta.
ASSINADO_POR = 'Assinado digitalmente por'
CERTIFICADO = 'Certificado digital ICP-Brasil'
CONFIRA = 'Confira a assinatura em validar.iti.gov.br'
TITULOS = {'laboratorio': 'SOLICITAÇÃO DE EXAMES LABORATORIAIS', 'imagem': 'SOLICITAÇÃO DE EXAMES DE IMAGEM',
           'vacina': 'RECEITA DE VACINAS'}
# Textos fixos das minutas (os testes conferem que cada um tem par em inglês).
FIXOS = ('Solicito:', 'Prescrevo:', 'Data de emissão', 'Paciente', 'Sexo', 'Idade', 'anos', 'Página', 'Feminino', 'Masculino',
         'Não informado', 'Não informada', 'Minuta preparada por', 'estudante de medicina', 'Vacina', 'Obs.:',
         ASSINADO_POR, CERTIFICADO, CONFIRA)
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
        'meningocócica b': 'Asplenia: aplicar três doses (0,5 ml), INTRAMUSCULAR, a 0, 1-2 e 6 meses (Bexsero®). '
                           'Reforço 1 ano após o esquema e, depois, a cada 2-3 anos (ACIP) ou 3 anos (SBIm).',
        'hib': 'Asplenia: aplicar duas doses (0,5 ml), INTRAMUSCULAR, com 2 meses de intervalo, se não vacinado '
               'previamente (SBIm/CRIE; o ACIP indica dose única).',
    },
    # Pessoa vivendo com HIV (SBIm Pacientes Especiais 2026/2027; Manual dos CRIE)
    'hiv': {
        'acwy': 'HIV: aplicar duas doses (0,5 ml), INTRAMUSCULAR, com 8 semanas de intervalo. Reforço a cada 5 anos.',
        'hib': 'HIV: aplicar duas doses (0,5 ml), INTRAMUSCULAR, com 2 meses de intervalo, se não vacinado previamente.',
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


MARGEM_INFERIOR = 42      # mm reservados à assinatura e ao rodapé de cada folha
PISO_DA_PAGINA = 8        # mm da borda de baixo (ou do rodapé do timbrado) até o número da página
FOLGA_DO_RODAPE = 2       # mm entre o fim da assinatura e o número da página


class _Minuta(FPDF):
    def __init__(self, titulo, idioma='pt', timbrado=None, assinatura=None):
        # Com papel timbrado (src/utils/timbrado.py): página do tamanho do timbrado, texto só entre o cabeçalho
        # e o rodapé dele, sem a marca do Evidēns; o timbrado entra como fundo depois (timbrado.aplicar).
        self.timbrado = timbrado
        # {'titular': nome no certificado} quando o PDF vai ser assinado digitalmente logo depois de gerado.
        self.assinante = assinatura
        formato = (timbrado['largura'], timbrado['altura']) if timbrado else 'A4'
        super().__init__(orientation='P', unit='mm', format=formato)
        self.idioma = idioma
        titulo = self.t(titulo)
        self.titulo = titulo
        self.base = (timbrado['margem_base'] if timbrado else 0)
        self.margem_inferior = MARGEM_INFERIOR + self.base
        self.set_margins(20, timbrado['margem_topo'] if timbrado else 18, 20)
        self.set_auto_page_break(auto=True, margin=self.margem_inferior)   # espaço para assinatura e rodapé
        self.add_font('DejaVu', '', str(FONTES / 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', str(FONTES / 'DejaVuSans-Bold.ttf'))
        self.add_font('DejaVu', 'I', str(FONTES / 'DejaVuSans-Oblique.ttf'))
        self.set_title(titulo)
        self.set_author('Evidēns')

    def t(self, texto):
        """O texto no idioma do documento (o que não tem par, como um item digitado, sai como veio)."""
        return i18n.traduzir(texto, self.idioma)

    def header(self):
        if getattr(self, 'em_guia', False):
            return
        if not self.timbrado:
            self.set_font('DejaVu', 'B', 11)
            self.set_text_color(14, 151, 181)
            self.cell(0, 6, 'evidēns', new_x='LMARGIN', new_y='NEXT')
        self.set_font('DejaVu', 'B', 15)
        self.set_text_color(20, 41, 47)
        self.cell(0, 10, self.titulo, align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(20, 41, 47)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        if getattr(self, 'em_guia', False):
            return
        # Número da página no canto inferior direito da folha (com timbrado, logo acima do rodapé dele).
        self.set_y(-(PISO_DA_PAGINA + self.base))
        self.set_font('DejaVu', '', 7.5)
        self.set_text_color(90, 100, 103)
        texto = f'{self.t("Página")} {self.page_no()}/{{nb}}'
        self.set_x(self.w - 8 - 40)
        self.cell(40, 4, texto, align='R')

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
        """Assinatura no fim da última página (nova página se não couber), encostada no rodapé: o bloco é medido
        e termina logo acima do número da página, sem faixa em branco entre os dois."""
        if self.get_y() > self.h - self.margem_inferior - 31:
            self.add_page()
        # A assinatura fica dentro da margem reservada à quebra automática: desligá-la aqui.
        self.set_auto_page_break(auto=False)
        resp = getattr(self, 'responsavel', None)
        linhas = self._linhas_da_assinatura(resp)   # (estilo, tamanho, altura, texto, cinza)
        largura = self.w - self.l_margin - self.r_margin
        altura = 0
        for estilo, tamanho, h, texto, _ in linhas:
            self.set_font('DejaVu', estilo, tamanho)
            altura += len(self.multi_cell(largura, h, texto, align='C', dry_run=True, output='LINES')) * h
        fim = self.h - self.base - PISO_DA_PAGINA - FOLGA_DO_RODAPE
        self.set_y(fim - altura - (0 if self.assinante else 1))
        if not self.assinante:
            self.set_draw_color(20, 41, 47)
            self.line(self.w / 2 - 45, self.get_y(), self.w / 2 + 45, self.get_y())
            self.ln(1)
        for estilo, tamanho, h, texto, cinza in linhas:
            self.set_font('DejaVu', estilo, tamanho)
            self.set_text_color(*((90, 100, 103) if cinza else (20, 41, 47)))
            self.multi_cell(largura, h, texto, align='C', new_x='LMARGIN', new_y='NEXT')

    def _linhas_da_assinatura(self, resp):
        t, linhas = self.t, []
        if self.assinante:
            # No lugar da linha para caneta e carimbo: quem assinou, com que certificado e onde conferir.
            if resp:
                linhas.append(('B', 9.5, 5, resp['nome'], False))
                if resp.get('crm'):
                    linhas.append(('', 9.5, 5, resp['crm'], False))
            linhas.append(('', 8.5, 4.5, f"{t(ASSINADO_POR)} {_texto(self.assinante['titular'], 150)}", False))
            linhas.append(('', 8, 4.5, f'{t(CERTIFICADO)} · {t(CONFIRA)}', True))
            return linhas
        medico = resp and not resp.get('estudante')
        if medico:
            linhas.append(('B', 9.5, 5, resp['nome'], False))
            if resp.get('crm'):
                linhas.append(('', 9.5, 5, resp['crm'], False))
        linhas.append(('', 8.5 if medico else 9.5, 5, t(LINHA_ASSINATURA), False))
        if resp and resp.get('estudante'):
            linhas.append(('', 8, 4.5, f"{t('Minuta preparada por')} {resp['nome']} ({t('estudante de medicina')}).", True))
        linhas.append(('', 8, 4.5, t(AVISO), True))
        return linhas

    def bytes(self):
        return bytes(self.output())


# ── Guia SP/SADT (padrão TISS) ──────────────────────────────────────────────
# A guia é um formulário brasileiro padronizado pela ANS: sai sempre em português,
# com os números de campo do padrão. O Evidēns preenche a parte da SOLICITAÇÃO
# (campos 1, 8 a 19 e 21 a 27); senha, validade, autorização e execução são da
# operadora e do prestador executante, e ficam em branco.

LINHAS_POR_GUIA = 5      # a guia impressa do padrão tem 5 linhas de procedimentos solicitados
CARATER_ELETIVO = '1'   # Caráter do atendimento, tabela TISS: 1 = eletivo


def indicacao_clinica(texto):
    """Indicação clínica da guia (campo 23): o que o médico escreveu, ou "Check-up"."""
    return _texto(' '.join(str(texto or '').split()), 150) or 'Check-up'


def _numero_do_crm(crm):
    """('GO', '26815') a partir de 'CRM-GO 26815'; ('', '') se não reconhecer."""
    partes = re.match(r'^CRM-([A-Z]{2}) (\d+)$', crm or '')
    return (partes.group(1), partes.group(2)) if partes else ('', '')


def _encaixar(pdf, x, y, largura, altura, valor, tamanho=9, estilo=''):
    """Escreve o valor INTEIRO dentro da caixa: diminui a letra e, se preciso, quebra em linhas.

    Nada é cortado em silêncio (um número de carteira sem os últimos dígitos seria outro número).
    Só um valor que não cabe nem na menor letra legível é abreviado, e aí termina em "…".
    """
    valor = _texto(valor, 300).strip()
    pdf.set_text_color(20, 41, 47)
    linhas, altura_da_linha = [valor], altura
    while True:
        pdf.set_font('DejaVu', estilo, tamanho)
        altura_da_linha = tamanho * 0.3528 * 1.15
        cabem = max(1, int(altura / altura_da_linha))
        if pdf.get_string_width(valor) <= largura:
            linhas = [valor]
            break
        linhas = pdf.multi_cell(largura, altura_da_linha, valor, dry_run=True, output='LINES')
        if len(linhas) <= cabem:
            break
        if tamanho <= 4:
            linhas = linhas[:cabem]
            linhas[-1] = linhas[-1][:-1].rstrip() + '…'
            break
        tamanho -= 0.5
    topo = y + max(0, (altura - altura_da_linha * len(linhas)) / 2)
    for n, linha in enumerate(linhas):
        pdf.set_xy(x, topo + n * altura_da_linha)
        pdf.cell(largura, altura_da_linha, linha)


def _rotulo(pdf, x, y, largura, rotulo):
    """Rótulo do campo dentro da largura: diminui a letra até 4,6 e, se ainda não couber, quebra em duas linhas.
    Devolve a altura ocupada."""
    pdf.set_text_color(70, 80, 84)
    tamanho = 5.6
    pdf.set_font('DejaVu', '', tamanho)
    while pdf.get_string_width(rotulo) > largura and tamanho > 4.2:
        tamanho -= 0.2
        pdf.set_font('DejaVu', '', tamanho)
    pdf.set_xy(x, y)
    if pdf.get_string_width(rotulo) <= largura:
        pdf.cell(largura, 2.6, rotulo)
        return 2.6
    pdf.multi_cell(largura, 1.6, rotulo, align='L')
    return 3.2


def _campo(pdf, x, y, largura, altura, rotulo, valor='', tamanho=9):
    pdf.set_draw_color(20, 41, 47)
    pdf.rect(x, y, largura, altura)
    ocupado = _rotulo(pdf, x + 0.8, y + 0.5, largura - 1.6, rotulo)
    if valor:
        livre = max(altura - 1.0 - ocupado, 2.6)   # rótulo em duas linhas: o valor encolhe, mas fica dentro da caixa
        _encaixar(pdf, x + 1.2, y + altura - 0.4 - livre, largura - 2.4, livre, valor, tamanho)


def _faixa(pdf, y, texto):
    pdf.set_fill_color(225, 232, 234)
    pdf.set_xy(10, y)
    pdf.set_font('DejaVu', 'B', 6.5)
    pdf.set_text_color(20, 41, 47)
    pdf.cell(277, 4, texto, fill=True)
    return y + 4


# Posições copiadas da guia SP/SADT impressa do padrão TISS 4 (modelo 2023, com os campos 89 a 92): a medida
# está em unidades do modelo (1 unidade = 0,1715 mm em A4 paisagem) para a guia sair com a mesma geometria.
_ESCALA_GUIA = 0.168
_X0_GUIA, _Y0_GUIA = 18.3, 4.0
# O quadro dos procedimentos solicitados ganha 25 unidades de altura (descrições longas cabem inteiras);
# tudo o que vem abaixo dele desce o mesmo tanto.
_FIM_SOLICITADOS, _ACRESCIMO = 566, 25


def _g(x, y=None):
    """Converte posições do modelo para milímetros na página."""
    if y is None:
        return x * _ESCALA_GUIA
    if y >= _FIM_SOLICITADOS:
        y += _ACRESCIMO
    return _X0_GUIA + (x - 30) * _ESCALA_GUIA, _Y0_GUIA + (y - 15) * _ESCALA_GUIA


def _campo_guia(pdf, x1, y1, x2, y2, rotulo, valor='', tamanho=8.5):
    x, y = _g(x1, y1)
    _campo(pdf, x, y, _g(x2 - x1), _g(y2 - y1), rotulo, valor, tamanho)


def _faixa_guia(pdf, y1, texto):
    x, y = _g(30, y1)
    pdf.set_fill_color(225, 232, 234)
    pdf.set_xy(x, y)
    pdf.set_font('DejaVu', 'B', 6.2)
    pdf.set_text_color(20, 41, 47)
    pdf.cell(_g(1550), _g(14), texto, fill=True)


def _tabela_guia(pdf, y1, y2, colunas, linhas, valores=None, numerar=True):
    """Quadro com cabeçalho de colunas (x1, x2, rótulo) e ``linhas`` linhas; ``valores``: lista de tuplas."""
    x, y = _g(30, y1)
    altura = _g(y2 - y1)
    pdf.set_draw_color(20, 41, 47)
    pdf.rect(x, y, _g(1550), altura)
    cabecalho = max(_rotulo(pdf, _g(c1, y1)[0] + 0.4, y + 0.5, _g(c2 - c1) - 0.6, rotulo) for c1, c2, rotulo in colunas)
    topo = y + cabecalho + 0.8
    passo = (altura - cabecalho - 1.2) / linhas
    for n in range(linhas):
        base = topo + passo * (n + 1) - 0.8
        if numerar:
            pdf.set_font('DejaVu', '', 5.4)
            pdf.set_text_color(70, 80, 84)
            pdf.set_xy(x + 0.4, base - 2.6)
            pdf.cell(3, 2.6, f'{n + 1}-')
        pdf.set_draw_color(160, 170, 172)
        for c1, c2, _ in colunas:
            pdf.line(_g(c1, 0)[0] + (2.4 if numerar and c1 == colunas[0][0] else 0), base, _g(c2, 0)[0], base)
        if valores and n < len(valores):
            for (c1, c2, _), valor in zip(colunas, valores[n]):
                if valor:
                    inicio = _g(c1, 0)[0] + (2.6 if numerar and c1 == colunas[0][0] else 0.4)
                    _encaixar(pdf, inicio, base - passo + 0.3, _g(c2, 0)[0] - inicio - 0.4, passo - 0.5, valor, 7.5)
    pdf.set_draw_color(20, 41, 47)


def _pagina_da_guia(pdf, dados_paciente, guia, linhas, parte, partes):
    pdf.add_page(orientation='L', format='A4')   # a guia é sempre A4, com ou sem papel timbrado
    cred, resp = guia['credenciamento'], guia.get('responsavel') or {}
    uf, numero = _numero_do_crm(resp.get('crm'))
    # Cabeçalho: o título do padrão e o nº da guia no prestador. O canto do logotipo leva o nome da operadora só
    # nas guias Unimed (pedido do médico responsável); nas demais operadoras fica em branco.
    if re.search(r'\bunimed\b', cred['operadora'] or '', re.IGNORECASE):
        x, y = _g(30, 20)
        _encaixar(pdf, x, y, _g(230), _g(70), cred['operadora'], 12, estilo='B')
    pdf.set_text_color(20, 41, 47)
    pdf.set_font('DejaVu', 'B', 9.5)
    x, y = _g(470, 28)
    pdf.set_xy(x, y)
    pdf.multi_cell(_g(660), 4.4, 'GUIA DE SERVIÇO PROFISSIONAL / SERVIÇO AUXILIAR DE\nDIAGNÓSTICO E TERAPIA - SP/SADT', align='C')
    _campo_guia(pdf, 1240, 32, 1580, 62, '2 - Nº Guia no Prestador')
    # Operadora e autorização
    _campo_guia(pdf, 30, 102, 168, 140, '1 - Registro ANS', cred.get('registro_ans'))
    _campo_guia(pdf, 175, 102, 594, 140, '3 - Número da Guia Principal')
    _campo_guia(pdf, 30, 144, 228, 182, '4 - Data da Autorização')
    _campo_guia(pdf, 243, 144, 655, 182, '5 - Senha')
    _campo_guia(pdf, 673, 144, 865, 182, '6 - Data de Validade da Senha')
    _campo_guia(pdf, 878, 144, 1288, 182, '7 - Número da Guia Atribuído pela Operadora')
    # Beneficiário
    _faixa_guia(pdf, 185, 'Dados do Beneficiário')
    nome = dados_paciente.get('nome') or ''
    _campo_guia(pdf, 30, 201, 403, 239, '8 - Número da Carteira', guia.get('carteira'))
    _campo_guia(pdf, 412, 201, 607, 239, '9 - Validade da Carteira')
    _campo_guia(pdf, 614, 201, 1430, 239, '89 - Nome Social')
    _campo_guia(pdf, 1437, 201, 1580, 239, '12 - Atendimento a RN', 'N')
    _campo_guia(pdf, 30, 242, 1580, 280, '10 - Nome', '' if nome in ('Paciente', 'Não informado') else nome)
    # Solicitante
    _faixa_guia(pdf, 284, 'Dados do Solicitante')
    _campo_guia(pdf, 30, 299, 327, 338, '13 - Código na Operadora', cred['codigo_prestador'])
    _campo_guia(pdf, 336, 299, 1580, 338, '14 - Nome do Contratado', cred['nome_contratado'])
    _campo_guia(pdf, 30, 342, 466, 381, '15 - Nome do Profissional Solicitante', resp.get('nome'))
    _campo_guia(pdf, 472, 342, 583, 381, '16 - Conselho Profissional', 'CRM' if numero else '')
    _campo_guia(pdf, 590, 342, 897, 381, '17 - Número no Conselho', numero)
    _campo_guia(pdf, 904, 342, 956, 381, '18 - UF', uf)
    _campo_guia(pdf, 962, 342, 1090, 381, '19 - Código CBO', cred.get('cbo'))
    _campo_guia(pdf, 1097, 342, 1580, 381, '20 - Assinatura do Profissional Solicitante',
                'Assinado digitalmente (ICP-Brasil)' if pdf.assinante else '')
    # Solicitação
    _faixa_guia(pdf, 386, 'Dados da Solicitação / Procedimentos ou Itens Assistenciais Solicitados')
    _campo_guia(pdf, 30, 402, 140, 440, '21 - Caráter do Atendimento', CARATER_ELETIVO)
    _campo_guia(pdf, 146, 402, 315, 440, '22 - Data da Solicitação', data_de_emissao('pt'))
    _campo_guia(pdf, 322, 402, 1246, 440, '23 - Indicação Clínica', guia['indicacao'])
    _campo_guia(pdf, 1252, 402, 1453, 440, '90 - Indicador de Cobertura Especial')
    valores = [(TABELA_TUSS if l['codigo'] else '', l['codigo'], l['descricao'], str(l['quantidade']), '') for l in linhas]
    _tabela_guia(pdf, 445, 565 + _ACRESCIMO, ((30, 95, '24 - Tabela'), (97, 300, '25 - Código do Procedimento ou Item Assistencial'),
                                 (303, 1335, '26 - Descrição'), (1345, 1412, '27 - Qtde. Solic.'),
                                 (1430, 1497, '28 - Qtde. Aut.')), LINHAS_POR_GUIA, valores)
    # Executante e atendimento (preenchidos por quem executa)
    _faixa_guia(pdf, 567, 'Dados do Contratado Executante')
    _campo_guia(pdf, 30, 583, 341, 622, '29 - Código na Operadora')
    _campo_guia(pdf, 348, 583, 1400, 622, '30 - Nome do Contratado')
    _campo_guia(pdf, 1407, 583, 1578, 622, '31 - Código CNES')
    _faixa_guia(pdf, 625, 'Dados do Atendimento')
    for x1, x2, rotulo in ((30, 158, '32 - Tipo de Atendimento'), (163, 473, '33 - Indicação de Acidente'),
                           (482, 597, '34 - Tipo de Consulta'), (604, 835, '35 - Motivo de Encerramento'),
                           (842, 1002, '91 - Regime de Atendimento'), (1009, 1139, '92 - Saúde Ocupacional')):
        _campo_guia(pdf, x1, 641, x2, 681, rotulo)
    _faixa_guia(pdf, 684, 'Dados da Execução / Procedimentos e Exames Realizados')
    _tabela_guia(pdf, 701, 835, ((30, 215, '36 - Data'), (220, 300, '37 - Hora Inicial'), (300, 368, '38 - Hora Final'),
                                 (372, 418, '39 - Tabela'), (422, 567, '40 - Código do Procedimento'),
                                 (572, 930, '41 - Descrição'), (936, 997, '42 - Qtde.'), (1000, 1032, '43 - Via'),
                                 (1035, 1068, '44 - Téc.'), (1075, 1180, '45 - Fator Red./Acresc.'),
                                 (1195, 1360, '46 - Valor Unitário (R$)'), (1368, 1538, '47 - Valor Total (R$)')), 5)
    _faixa_guia(pdf, 838, 'Identificação do(s) Profissional(is) Executante(s)')
    _tabela_guia(pdf, 854, 962, ((30, 88, '48 - Seq. Ref.'), (92, 155, '49 - Grau Part.'),
                                 (160, 445, '50 - Código na Operadora/CPF'), (452, 1000, '51 - Nome do Profissional'),
                                 (1000, 1062, '52 - Conselho'), (1066, 1365, '53 - Número no Conselho'),
                                 (1370, 1415, '54 - UF'), (1420, 1540, '55 - Código CBO')), 4, numerar=False)
    # Procedimentos em série (datas e assinaturas do beneficiário)
    x, y = _g(30, 966)
    pdf.rect(x, y, _g(1550), _g(62))
    pdf.set_font('DejaVu', '', 5.4)
    pdf.set_text_color(70, 80, 84)
    pdf.set_xy(x + 0.6, y + 0.6)
    pdf.cell(_g(1500), 2.4, '56 - Data de Realização de Procedimentos em Série     57 - Assinatura do Beneficiário ou Responsável')
    pdf.set_draw_color(160, 170, 172)
    for n in range(10):
        coluna, linha_ = divmod(n, 2)
        cx, cy = _g(30 + coluna * 303, 0)[0] + 0.8, y + 5.6 + linha_ * 4.6
        pdf.set_xy(cx, cy - 2.4)
        pdf.cell(3, 2.4, f'{n + 1} -')
        pdf.line(cx + 3.6, cy, cx + 16, cy)
        pdf.line(cx + 18, cy, cx + _g(290) - 1.6, cy)
    pdf.set_draw_color(20, 41, 47)
    _campo_guia(pdf, 30, 1032, 1580, 1095, '58 - Observação / Justificativa',
                f'Guia {parte} de {partes} deste pedido.' if partes > 1 else '', tamanho=7.5)
    for x1, x2, rotulo in ((30, 245, '59 - Total de Procedimentos (R$)'), (252, 468, '60 - Total de Taxas e Aluguéis (R$)'),
                           (475, 690, '61 - Total de Materiais (R$)'), (697, 912, '62 - Total de OPME (R$)'),
                           (919, 1128, '63 - Total de Medicamentos (R$)'), (1135, 1352, '64 - Total de Gases Medicinais (R$)'),
                           (1359, 1580, '65 - Total Geral (R$)')):
        _campo_guia(pdf, x1, 1100, x2, 1138, rotulo)
    _campo_guia(pdf, 30, 1142, 558, 1185, '66 - Assinatura do Responsável pela Autorização')
    _campo_guia(pdf, 566, 1142, 1083, 1185, '67 - Assinatura do Beneficiário ou Responsável')
    _campo_guia(pdf, 1090, 1142, 1580, 1185, '68 - Assinatura do Contratado')


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


def _folha_de_pedido(pdf, dados_paciente, exames, numerar=True):
    """Uma folha de pedido: dados do paciente, "Solicito:", os exames e a assinatura."""
    pdf.set_auto_page_break(auto=True, margin=pdf.margem_inferior)    # a assinatura da folha anterior desliga
    pdf.add_page()
    pdf.dados_do_paciente(dados_paciente)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(0, 7, pdf.t('Solicito:'), new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('DejaVu', '', 10.5)
    for n, exame in enumerate(exames, 1):
        pdf.set_x(24)
        pdf.set_font('DejaVu', '', 10.5)
        titulo = _texto(pdf.t(exame.get('titulo')))
        pdf.multi_cell(0, 6.2, f'{n}. {titulo}' if numerar else titulo)
        quando = exame.get('quando_pdf')
        if isinstance(quando, str) and quando.strip():
            # Pré-natal: só a orientação de quando fazer o exame vai no pedido ("Realizar com 35-37 semanas"),
            # em itálico e precedida de "Obs.:". O motor não manda mais o motivo do pedido ("Primeira consulta").
            pdf.set_font('DejaVu', 'I', 9)
            pdf.set_text_color(90, 100, 103)
            pdf.set_x(30)
            pdf.multi_cell(0, 5, _texto(pdf.t('Obs.:') + ' ' + pdf.t(quando.strip()[:160])))
            pdf.set_text_color(20, 41, 47)
    pdf.assinatura()


def _com_timbrado(pdf, timbrado, paginas=None):
    """Bytes do PDF; com timbrado, as `paginas` primeiras (o pedido) ganham o fundo do médico."""
    conteudo = pdf.bytes()
    if not timbrado or not timbrado.get('arquivo'):   # papel já timbrado: só as margens, sem fundo
        return conteudo
    from src.utils import timbrado as papel
    return papel.aplicar(conteudo, timbrado['arquivo'], paginas)


def _pdf_de_exames(dados_paciente, exames, categoria, responsavel=None, idioma='pt', guia=None, timbrado=None,
                   assinatura=None):
    pdf = _Minuta(TITULOS[categoria], idioma, timbrado, assinatura)
    pdf.responsavel = responsavel
    if categoria == 'imagem':
        # Exames de imagem: um pedido por folha (cada serviço de imagem fica com o seu), no mesmo PDF.
        for exame in exames:
            _folha_de_pedido(pdf, dados_paciente, [exame], numerar=False)
    else:
        _folha_de_pedido(pdf, dados_paciente, exames)
    paginas_do_pedido = pdf.page_no()
    if guia:
        _anexar_guias(pdf, dados_paciente, exames, dict(guia, responsavel=responsavel))
    return _com_timbrado(pdf, timbrado, paginas_do_pedido)


def gerar_pdf_exames_laboratoriais(dados_paciente, exames, responsavel=None, idioma='pt', guia=None, timbrado=None,
                                   assinatura=None):
    return _pdf_de_exames(dados_paciente, exames, 'laboratorio', responsavel, idioma, guia, timbrado, assinatura)


def gerar_pdf_exames_imagem(dados_paciente, exames, responsavel=None, idioma='pt', guia=None, timbrado=None,
                            assinatura=None):
    return _pdf_de_exames(dados_paciente, exames, 'imagem', responsavel, idioma, guia, timbrado, assinatura)


def gerar_pdf_vacinas(dados_paciente, vacinas, responsavel=None, idioma='pt', timbrado=None, assinatura=None):
    pdf = _Minuta(TITULOS['vacina'], idioma, timbrado, assinatura)
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
    return _com_timbrado(pdf, timbrado)
