"""Papel timbrado do médico: o PDF do consultório vira o fundo dos pedidos gerados pelo Evidēns.

- O médico envia o timbrado uma vez, no painel da conta; ele fica guardado só para a conta dele.
- Usa-se a 1ª página do PDF. A área livre (entre o cabeçalho e o rodapé) é medida pelo que está
  desenhado na página (texto e imagens); o médico confere na prévia e pode ajustar as margens.
- Ao gerar o pedido, cada página do pedido é escrita nessa área e posta sobre uma cópia do timbrado
  (pypdf). A guia SP/SADT continua no formato padrão (formulário da ANS), sem timbrado.
"""
import io
import logging

logging.getLogger('pypdf').setLevel(logging.ERROR)

TAMANHO_MAXIMO = 3 * 1024 * 1024
PT_EM_MM = 25.4 / 72
FOLGA = 4.0              # mm entre o que está desenhado no timbrado e o texto do pedido
MARGEM_PADRAO = 20.0     # mm, quando o timbrado não tem nada naquela borda
AREA_MINIMA = 120.0       # mm livres para o pedido entre o cabeçalho e o rodapé (assinatura incluída)
MARGEM_MINIMA, FRACAO_MAXIMA = 10.0, 0.4   # cada margem: de 10 mm até 40% da altura da página

MENSAGENS = {
    'nao_pdf': 'Envie o timbrado em PDF.',
    'grande': 'O timbrado passa de 3 MB.',
    'senha': 'O PDF do timbrado está protegido por senha.',
    'invalido': 'Não foi possível abrir o PDF do timbrado.',
    'tamanho': 'A página do timbrado precisa ter entre 10 e 50 cm de lado.',
    'area': 'O timbrado deixa menos de 12 cm livres entre o cabeçalho e o rodapé: use um modelo com mais espaço para o pedido.',
    'margens': 'Margens inválidas: cada uma entre 10 mm e 40% da altura da página, deixando espaço para o pedido.',
}


class TimbradoInvalido(Exception):
    def __init__(self, codigo):
        super().__init__(codigo)
        self.codigo = codigo

    def __str__(self):
        return MENSAGENS.get(self.codigo, MENSAGENS['invalido'])


def _pagina(conteudo):
    if not conteudo or not conteudo.lstrip().startswith(b'%PDF'):
        raise TimbradoInvalido('nao_pdf')
    if len(conteudo) > TAMANHO_MAXIMO:
        raise TimbradoInvalido('grande')
    try:
        from pypdf import PdfReader
        leitor = PdfReader(io.BytesIO(conteudo))
        if leitor.is_encrypted:
            try:
                aberto = leitor.decrypt('')
            except Exception:
                aberto = 0
            if not aberto:
                raise TimbradoInvalido('senha')
        pagina = leitor.pages[0]
        if pagina.get('/Rotate', 0):
            pagina.transfer_rotation_to_content()   # página girada vira conteúdo girado (tamanho já final)
    except TimbradoInvalido:
        raise
    except Exception:
        raise TimbradoInvalido('invalido')
    return pagina


def dimensoes(conteudo):
    """(largura, altura) da 1ª página em mm."""
    pagina = _pagina(conteudo)
    caixa = pagina.mediabox
    largura, altura = float(caixa.width) * PT_EM_MM, float(caixa.height) * PT_EM_MM
    if not (100 <= largura <= 500 and 100 <= altura <= 500):
        raise TimbradoInvalido('tamanho')
    return round(largura, 1), round(altura, 1)


def _desenhado(pagina):
    """Faixas verticais (y0, y1, em pt, origem embaixo) do que está desenhado: texto e imagens."""
    faixas = []

    def texto(conteudo, cm, tm, fonte, tamanho):
        if conteudo and conteudo.strip():
            y = tm[5] * cm[3] + cm[5]
            altura = abs((tamanho or 10) * tm[3] * cm[3]) or 10
            faixas.append((y - altura * 0.25, y + altura))

    pilha, ctm = [], [1, 0, 0, 1, 0, 0]

    def antes(operador, operandos, cm, tm):
        nonlocal ctm
        if operador == b'q':
            pilha.append(list(ctm))
        elif operador == b'Q' and pilha:
            ctm = pilha.pop()
        elif operador == b'cm' and len(operandos) == 6:
            a, b, c, d, e, f = (float(x) for x in operandos)
            A, B, C, D, E, F = ctm
            ctm = [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F]
        elif operador in (b're', b'm', b'l', b'c', b'v', b'y') and operandos:
            # traço ou retângulo (linhas e faixas do cabeçalho/rodapé): os pontos transformados pela matriz atual
            numeros = [float(x) for x in operandos]
            pontos = [(numeros[0], numeros[1]), (numeros[0] + numeros[2], numeros[1] + numeros[3])] if operador == b're' \
                else list(zip(numeros[0::2], numeros[1::2]))
            ys = [ctm[1] * x + ctm[3] * y + ctm[5] for x, y in pontos]
            if ys:
                faixas.append((min(ys), max(ys)))
        elif operador == b'Do':
            # imagem ou formulário: o quadrado unitário transformado pela matriz atual
            ys = [ctm[5], ctm[3] + ctm[5], ctm[1] + ctm[5], ctm[1] + ctm[3] + ctm[5]]
            faixas.append((min(ys), max(ys)))

    try:
        pagina.extract_text(visitor_text=texto, visitor_operand_before=antes)
    except Exception:
        pass
    return faixas


def margens_sugeridas(conteudo):
    """(topo, base) em mm: abaixo do cabeçalho e acima do rodapé desenhados no timbrado."""
    pagina = _pagina(conteudo)
    _, altura_mm = dimensoes(conteudo)
    altura = altura_mm / PT_EM_MM
    topo = base = None
    for y0, y1 in _desenhado(pagina):
        if y1 > altura * 0.55:          # metade de cima: cabeçalho
            topo = max(topo or 0, (altura - y0) * PT_EM_MM)
        elif y0 < altura * 0.45:        # metade de baixo: rodapé
            base = max(base or 0, y1 * PT_EM_MM)
    limite = altura_mm * FRACAO_MAXIMA

    def ajustar(valor):
        if valor is None:
            return MARGEM_PADRAO
        return round(min(max(valor + FOLGA, MARGEM_MINIMA), limite), 1)

    topo, base = ajustar(topo), ajustar(base)
    if altura_mm - topo - base < AREA_MINIMA:
        raise TimbradoInvalido('area')
    return topo, base


def conferir_margens(conteudo, topo, base):
    """Margens dentro dos limites e com espaço para o pedido (assinatura incluída)."""
    _, altura = dimensoes(conteudo)
    try:
        topo, base = float(topo), float(base)
    except (TypeError, ValueError):
        raise TimbradoInvalido('margens')
    limite = altura * FRACAO_MAXIMA
    if not (MARGEM_MINIMA <= topo <= limite and MARGEM_MINIMA <= base <= limite) or altura - topo - base < AREA_MINIMA:
        raise TimbradoInvalido('margens')
    return round(topo, 1), round(base, 1)


def para_o_pdf(registro):
    """O que o gerador de PDF precisa: tamanho da página, margens e o arquivo."""
    largura, altura = dimensoes(registro['arquivo'])
    return {'arquivo': registro['arquivo'], 'largura': largura, 'altura': altura,
            'margem_topo': registro['margem_topo'], 'margem_base': registro['margem_base']}


def aplicar(conteudo_pdf, timbrado_pdf, paginas=None):
    """Põe cada uma das `paginas` primeiras do PDF gerado sobre uma cópia da 1ª página do timbrado."""
    from pypdf import PageObject, PdfReader, PdfWriter
    gerado = PdfReader(io.BytesIO(conteudo_pdf))
    fundo = _pagina(timbrado_pdf)
    saida = PdfWriter()
    total = len(gerado.pages) if paginas is None else min(paginas, len(gerado.pages))
    for i, pagina in enumerate(gerado.pages):
        if i < total:
            nova = PageObject.create_blank_page(width=pagina.mediabox.width, height=pagina.mediabox.height)
            nova.merge_page(fundo)   # fundo já sem rotação (ver _pagina)
            nova.merge_page(pagina)
            saida.add_page(nova)
        else:
            saida.add_page(pagina)
    saida.add_metadata({'/Title': (gerado.metadata or {}).get('/Title', ''), '/Author': 'Evidēns'})
    resultado = io.BytesIO()
    saida.write(resultado)
    return resultado.getvalue()
