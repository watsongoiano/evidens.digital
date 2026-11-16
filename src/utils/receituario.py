"""Receituário do médico: o fundo e as margens dos pedidos (exames e vacinas) gerados pelo Evidēns.

Quatro modos, escolhidos no painel da conta:
- ``padrao``: modelo do Evidēns (sem fundo).
- ``modelo``: o médico envia o receituário que já usa (PDF, PNG ou JPG; ver src/utils/timbrado.py).
- ``montado``: o médico monta o cabeçalho e o rodapé na tela (logo, nome, CRM, RQE, especialidade,
  endereço e contato), num de três temas; o fundo é gerado aqui.
- ``papel``: o pedido sai sem fundo, só com o texto entre as margens, para imprimir em papel já timbrado.

Como fazem os sistemas de prescrição: a Memed importa cabeçalho/rodapé de um PDF e também tem um editor
(logo, nome, registro, especialidade, alinhamento, temas, margens); Feegow e iClinic ajustam margens para
imprimir sobre papel timbrado. Os três modos aqui seguem essas ideias.
"""
import io

from src.utils import timbrado

MODOS = ('padrao', 'modelo', 'montado', 'papel')
TEMAS = ('linha', 'faixa', 'simples')
ALINHAMENTOS = ('esquerda', 'centro', 'direita')
CORES = {
    'teal': (14, 151, 181), 'grafite': (20, 41, 47), 'azul': (29, 78, 137),
    'verde': (31, 110, 74), 'vinho': (122, 31, 52),
}
CAMPOS = {   # campo -> tamanho máximo
    'nome': 80, 'registro': 60, 'especialidade': 80, 'endereco': 140, 'contato': 120,
}
PAPEL_PADRAO = (40.0, 30.0)     # mm: cabeçalho e rodapé típicos de um receituário impresso
LOGO_MAXIMO = 1024 * 1024

MENSAGENS = {
    'modo': 'Escolha como o receituário deve sair.',
    'tema': 'Escolha um dos temas.',
    'alinhamento': 'Escolha o alinhamento do cabeçalho.',
    'cor': 'Escolha uma das cores.',
    'nome': 'Informe o nome que vai no cabeçalho.',
    'logo': 'O logo precisa ser uma imagem PNG ou JPG de até 1 MB.',
    'sem_modelo': 'Envie o seu modelo antes de escolher esta opção.',
}


class ReceituarioInvalido(Exception):
    def __init__(self, codigo):
        super().__init__(codigo)
        self.codigo = codigo

    def __str__(self):
        return MENSAGENS.get(self.codigo) or timbrado.MENSAGENS.get(self.codigo, MENSAGENS['modo'])


def _limpo(valor, maximo):
    texto = ' '.join(str(valor or '').split())
    return ''.join(c for c in texto if c.isprintable())[:maximo]


def validar_montado(dados, logo=None):
    """Dados do receituário montado, limpos; levanta ReceituarioInvalido."""
    saida = {campo: _limpo(dados.get(campo), maximo) for campo, maximo in CAMPOS.items()}
    if not saida['nome']:
        raise ReceituarioInvalido('nome')
    for campo, opcoes in (('tema', TEMAS), ('alinhamento', ALINHAMENTOS), ('cor', tuple(CORES))):
        valor = dados.get(campo) or opcoes[0]
        if valor not in opcoes:
            raise ReceituarioInvalido(campo)
        saida[campo] = valor
    if logo is not None:
        conferir_logo(logo)
    return saida


def conferir_logo(logo):
    if not logo or len(logo) > LOGO_MAXIMO or not timbrado.eh_imagem(logo):
        raise ReceituarioInvalido('logo')
    try:
        from PIL import Image
        imagem = Image.open(io.BytesIO(logo))
        imagem.load()
    except Exception:
        raise ReceituarioInvalido('logo')
    if not (16 <= imagem.size[0] <= 6000 and 16 <= imagem.size[1] <= 6000):
        raise ReceituarioInvalido('logo')


def _logo_rgb(logo):
    """Logo com transparência sobre fundo branco (o PDF não precisa de canal alfa)."""
    from PIL import Image
    imagem = Image.open(io.BytesIO(logo))
    if imagem.mode in ('RGBA', 'LA', 'P'):
        rgba = imagem.convert('RGBA')
        fundo = Image.new('RGB', rgba.size, 'white')
        fundo.paste(rgba, mask=rgba.split()[-1])
        return fundo
    return imagem.convert('RGB')


def montar(dados, logo=None):
    """PDF A4 de uma página com o cabeçalho e o rodapé do receituário montado (fundo dos pedidos)."""
    from fpdf import FPDF
    from src.utils.pdf_minutas import FONTES
    cor = CORES.get(dados.get('cor'), CORES['teal'])
    tema, alinhar = dados.get('tema', 'linha'), dados.get('alinhamento', 'esquerda')
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_auto_page_break(False)
    pdf.set_margins(0, 0, 0)
    pdf.add_font('DejaVu', '', str(FONTES / 'DejaVuSans.ttf'))
    pdf.add_font('DejaVu', 'B', str(FONTES / 'DejaVuSans-Bold.ttf'))
    pdf.add_page()
    esquerda, direita, largura = 20.0, 190.0, 170.0
    topo = 14.0
    if tema == 'faixa':
        pdf.set_fill_color(*cor)
        pdf.rect(0, 0, 210, 7, 'F')
        topo = 15.0

    # Logo: até 22 mm de altura e 55 mm de largura.
    texto_x, texto_w, alinhamento_texto = esquerda, largura, {'esquerda': 'L', 'centro': 'C', 'direita': 'R'}[alinhar]
    y_texto = topo
    if logo:
        imagem = _logo_rgb(logo)
        lw_px, lh_px = imagem.size
        escala = min(55.0 / lw_px, 22.0 / lh_px)
        lw, lh = lw_px * escala, lh_px * escala
        if alinhar == 'centro':
            pdf.image(imagem, x=105 - lw / 2, y=topo, w=lw, h=lh)
            y_texto = topo + lh + 3
        elif alinhar == 'esquerda':
            pdf.image(imagem, x=esquerda, y=topo, w=lw, h=lh)
            texto_x, texto_w = esquerda + lw + 6, largura - lw - 6
        else:
            pdf.image(imagem, x=direita - lw, y=topo, w=lw, h=lh)
            texto_w = largura - lw - 6

    pdf.set_xy(texto_x, y_texto)
    pdf.set_text_color(*cor)
    pdf.set_font('DejaVu', 'B', 14)
    pdf.multi_cell(texto_w, 6.5, dados['nome'], align=alinhamento_texto, new_x='LEFT', new_y='NEXT')
    pdf.set_text_color(60, 72, 76)
    pdf.set_font('DejaVu', '', 9.5)
    for linha in (dados.get('registro'), dados.get('especialidade')):
        if linha:
            pdf.set_x(texto_x)
            pdf.multi_cell(texto_w, 4.8, linha, align=alinhamento_texto, new_x='LEFT', new_y='NEXT')
    fim_cabecalho = max(pdf.get_y(), topo + (22 if logo and alinhar != 'centro' else 0))
    if tema == 'linha':
        pdf.set_draw_color(*cor)
        pdf.set_line_width(0.5)
        pdf.line(esquerda, fim_cabecalho + 3, direita, fim_cabecalho + 3)

    # Endereço e contato quebram dentro da largura da página (um texto longo não pode sair pelas bordas);
    # a altura do rodapé sai do número de linhas resultante.
    pdf.set_font('DejaVu', '', 8.5)
    rodape = [parte for linha in (dados.get('endereco'), dados.get('contato')) if linha
              for parte in pdf.multi_cell(largura, 4.5, linha, align='C', dry_run=True, output='LINES')]
    if rodape or tema == 'faixa':
        y = 297 - 12 - 4.5 * len(rodape)
        if tema == 'linha' and rodape:
            pdf.set_draw_color(*cor)
            pdf.set_line_width(0.3)
            pdf.line(esquerda, y - 3, direita, y - 3)
        pdf.set_text_color(90, 100, 103)
        pdf.set_font('DejaVu', '', 8.5)
        for linha in rodape:
            pdf.set_xy(esquerda, y)
            pdf.cell(largura, 4.5, linha, align='C')
            y += 4.5
        if tema == 'faixa':
            pdf.set_fill_color(*cor)
            pdf.rect(0, 293, 210, 4, 'F')
    return bytes(pdf.output())


def _margens_do_montado(dados, logo):
    pdf = montar(dados, logo)
    return pdf, timbrado.margens_sugeridas(pdf)


def salvar_montado(contas, uid, dados, logo=None, remover_logo=False):
    """Valida, gera o fundo e grava; as margens são medidas de novo a cada alteração."""
    atual = contas.receituario_de(uid) or {'dados': {}, 'logo': None}
    limpos = validar_montado(dados, logo)
    novo_logo = None if remover_logo else (logo if logo is not None else atual['logo'])
    _, (topo, base) = _margens_do_montado(limpos, novo_logo)
    limpos.update(margem_topo=topo, margem_base=base)
    papel = atual['dados'].get('papel')
    if papel:
        limpos['papel'] = papel
    contas.salvar_receituario(uid, 'montado', {**atual['dados'], **limpos}, novo_logo)


def escolher_modo(contas, uid, modo):
    if modo not in MODOS:
        raise ReceituarioInvalido('modo')
    if modo == 'modelo' and not contas.timbrado_de(uid, com_arquivo=False):
        raise ReceituarioInvalido('sem_modelo')
    atual = contas.receituario_de(uid)
    if modo == 'montado' and not (atual and atual['dados'].get('nome')):
        raise ReceituarioInvalido('nome')
    contas.salvar_receituario(uid, modo)


def modo_de(contas, uid):
    r = contas.receituario_de(uid)
    if r and r['modo'] in MODOS:
        return r['modo']
    # contas de antes dos modos: quem enviou o timbrado usa o modelo
    return 'modelo' if contas.timbrado_de(uid, com_arquivo=False) else 'padrao'


def margens_do_papel(dados):
    papel = dados.get('papel') or {}
    return float(papel.get('margem_topo', PAPEL_PADRAO[0])), float(papel.get('margem_base', PAPEL_PADRAO[1]))


def para_o_pdf(contas, uid):
    """O que o gerador de PDF precisa ({arquivo, largura, altura, margem_topo, margem_base}) ou None."""
    modo = modo_de(contas, uid)
    if modo == 'modelo':
        registro = contas.timbrado_de(uid)
        return timbrado.para_o_pdf(registro) if registro else None
    r = contas.receituario_de(uid)
    if not r:
        return None
    if modo == 'montado':
        d = r['dados']
        return {'arquivo': montar(d, r['logo']), 'largura': timbrado.A4[0], 'altura': timbrado.A4[1],
                'margem_topo': float(d['margem_topo']), 'margem_base': float(d['margem_base'])}
    if modo == 'papel':
        topo, base = margens_do_papel(r['dados'])
        return {'arquivo': None, 'largura': timbrado.A4[0], 'altura': timbrado.A4[1],
                'margem_topo': topo, 'margem_base': base}
    return None


def ajustar_margens(contas, uid, topo, base):
    """Grava as margens do modo atual (conferidas pela altura da página)."""
    modo = modo_de(contas, uid)
    if modo == 'modelo':
        registro = contas.timbrado_de(uid)
        topo, base = timbrado.conferir_margens(registro['arquivo'], topo, base)
        contas.ajustar_margens_do_timbrado(uid, topo, base)
        return topo, base
    if modo not in ('montado', 'papel'):
        raise ReceituarioInvalido('modo')
    topo, base = timbrado.conferir_margens_na_altura(timbrado.A4[1], topo, base)
    r = contas.receituario_de(uid) or {'dados': {}}
    dados = dict(r['dados'])
    if modo == 'papel':
        dados['papel'] = {'margem_topo': topo, 'margem_base': base}
    else:
        dados.update(margem_topo=topo, margem_base=base)
    contas.salvar_receituario(uid, modo, dados)
    return topo, base


def imagem(config, largura_px=620):
    """PNG da página de fundo (página em branco no papel já timbrado), para ajustar as margens na tela."""
    if config and config.get('arquivo'):
        import pypdfium2
        documento = pypdfium2.PdfDocument(config['arquivo'])
        try:
            pagina = documento[0]
            figura = pagina.render(scale=largura_px / pagina.get_width()).to_pil().convert('RGB')
        finally:
            documento.close()
    else:
        from PIL import Image
        largura_mm, altura_mm = (config['largura'], config['altura']) if config else timbrado.A4
        figura = Image.new('RGB', (largura_px, round(largura_px * altura_mm / largura_mm)), 'white')
    saida = io.BytesIO()
    figura.save(saida, format='PNG', optimize=True)
    return saida.getvalue()
