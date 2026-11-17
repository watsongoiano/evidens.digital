"""Os exames mais pedidos, com campo de resultado e data em "Exames já realizados".

Cada exame tem o título do catálogo (é o que vai para a conferência da periodicidade) e um ou mais campos de
resultado. Os campos ``colesterol``, ``hdl``, ``creatinina``, ``uacr``, ``hba1c`` e ``hpv_resultado`` têm o
mesmo nome que o motor já usa (PREVENT, TFG, KFRE, diabetes, colo do útero); os demais acompanham o pedido para
o médico conferir e para regras futuras.

O leitor de laudos (src/utils/laudos.py) usa ``valores_do_bloco`` para tirar do texto do laudo o resultado de
cada campo, quando ele está escrito de forma reconhecível ("Resultado: 0,9 mg/dL", "HDL: 45 mg/dL",
"NÃO REAGENTE"). Valor de referência nunca é lido como resultado: vale o primeiro número depois do nome do
analito ou de "Resultado"; depois da linha "Valores de referência", o limite ("BILIRRUBINA TOTAL: Até 1,2",
"RNI: Até 1,20") e a faixa ("INR: 2,0 a 3,0") não contam, e a primeira linha que começa por número também não.
Exame fora da lista, com um resultado só ("RESULTADO: 70 U/L"), fica com o texto do resultado.
"""
import re

SOROLOGIA = [('', 'Não informado'), ('nao_reagente', 'Não reagente'), ('reagente', 'Reagente'),
             ('indeterminado', 'Indeterminado')]
HPV = [('', 'Não sabe'), ('nao_detectado', 'Não detectado'), ('hpv_16_18', 'HPV 16 ou 18'),
       ('outros_citologia_negativa', 'Outros tipos, citologia negativa'),
       ('outros_citologia_alterada', 'Outros tipos, citologia ASC-US ou mais'),
       ('colposcopia_negativa', 'Colposcopia sem doença')]


FIT = [('', 'Não informado'), ('negativo', 'Negativo'), ('positivo', 'Positivo')]


def _n(nome, rotulo, unidade, minimo, maximo, no_laudo=None):
    return {'nome': nome, 'rotulo': rotulo, 'unidade': unidade, 'min': minimo, 'max': maximo,
            'no_laudo': no_laudo}


def _s(nome, rotulo, opcoes, no_laudo=None):
    return {'nome': nome, 'rotulo': rotulo, 'opcoes': opcoes, 'no_laudo': no_laudo}


# (grupo, título do catálogo, campos)
EXAMES = [
    ('Metabolismo', 'Glicose, soro', [_n('glicose', 'Glicose de jejum', 'mg/dL', 20, 1000)]),
    ('Metabolismo', 'Hemoglobina glicada (HbA1c), soro', [_n('hba1c', 'HbA1c', '%', 3, 20)]),
    ('Metabolismo', 'Insulina de jejum, soro', [_n('insulina', 'Insulina de jejum', 'µUI/mL', 0.5, 500)]),
    ('Metabolismo', 'Colesterol total e frações, soro', [
        _n('colesterol', 'Colesterol total', 'mg/dL', 50, 1000, r'colesterol\s+total'),
        _n('hdl', 'HDL', 'mg/dL', 5, 200, r'(?<!n[ãa]o[\s-])\bhdl\b'),
        _n('ldl', 'LDL', 'mg/dL', 5, 800, r'\bldl\b'),
        _n('triglicerideos', 'Triglicerídeos', 'mg/dL', 10, 10000, r'triglic')]),
    ('Metabolismo', 'Lipoproteína(a) - Lp(a), soro', [_n('lpa', 'Lp(a)', 'mg/dL', 0, 500)]),
    ('Metabolismo', 'Apolipoproteína B, soro', [_n('apob', 'ApoB', 'mg/dL', 10, 400)]),
    ('Metabolismo', 'Ácido úrico, soro', [_n('acido_urico', 'Ácido úrico', 'mg/dL', 0.5, 30)]),
    ('Rim e eletrólitos', 'Creatinina, soro', [_n('creatinina', 'Creatinina', 'mg/dL', 0.1, 25)]),
    ('Rim e eletrólitos', 'Relação albumina/creatinina urinária (uACR)', [_n('uacr', 'Relação albumina/creatinina', 'mg/g', 0.1, 25000)]),
    ('Rim e eletrólitos', 'Ureia, soro', [_n('ureia', 'Ureia', 'mg/dL', 2, 500)]),
    ('Rim e eletrólitos', 'EAS - Elementos Anormais e Sedimentoscopia', []),
    ('Rim e eletrólitos', 'Sódio, soro', [_n('sodio', 'Sódio', 'mEq/L', 100, 180)]),
    ('Rim e eletrólitos', 'Potássio, soro', [_n('potassio', 'Potássio', 'mEq/L', 1.5, 9)]),
    ('Rim e eletrólitos', 'Cálcio iônico, soro', [_n('calcio_ionico', 'Cálcio iônico', 'mmol/L', 0.5, 2.5)]),
    ('Rim e eletrólitos', 'Fósforo, soro', [_n('fosforo', 'Fósforo', 'mg/dL', 0.5, 15)]),
    ('Rim e eletrólitos', 'Magnésio, soro', [_n('magnesio', 'Magnésio', 'mg/dL', 0.5, 8)]),
    ('Rim e eletrólitos', 'Paratormônio (PTH), soro', [_n('pth', 'PTH', 'pg/mL', 1, 3000)]),
    ('Fígado', 'Aspartato aminotransferase, soro', [_n('tgo', 'TGO (AST)', 'U/L', 1, 10000)]),
    ('Fígado', 'Alanina aminotransferase, soro', [_n('tgp', 'TGP (ALT)', 'U/L', 1, 10000)]),
    ('Fígado', 'Gama-GT, soro', [_n('ggt', 'Gama-GT', 'U/L', 1, 5000)]),
    ('Fígado', 'Fosfatase alcalina, soro', [_n('fosfatase_alcalina', 'Fosfatase alcalina', 'U/L', 5, 5000)]),
    ('Fígado', 'Bilirrubinas totais e frações, soro', [
        _n('bilirrubina_total', 'Bilirrubina total', 'mg/dL', 0.1, 50,
           r'bilirrubinas?\s+tota(?:l|is)\b(?!\s+e\s+fra)|(?:^|resultado\s*:)\s*total\b')]),
    ('Fígado', 'Albumina, soro', [_n('albumina', 'Albumina', 'g/dL', 0.5, 7)]),
    ('Fígado', 'Tempo de protrombina (TP/INR), plasma', [
        _n('inr', 'INR', '', 0.5, 15, r'\binr\b|\brni\b|\br\.\s*n\.\s*i\b|\bi\.\s*n\.\s*r\b')]),
    ('Sangue, ferro e vitaminas', 'Hemograma completo com plaquetas', [
        _n('hemoglobina', 'Hemoglobina', 'g/dL', 2, 25, r'hemoglobina(?!\s+(glicada|corpuscular))'),
        _n('leucocitos', 'Leucócitos', '/mm³', 100, 500000, r'leuc[oó]citos'),
        _n('plaquetas', 'Plaquetas', '/mm³', 1000, 2000000, r'plaquetas')]),
    ('Sangue, ferro e vitaminas', 'Ferritina, soro', [_n('ferritina', 'Ferritina', 'ng/mL', 1, 100000)]),
    ('Sangue, ferro e vitaminas', 'Ferro sérico', [_n('ferro', 'Ferro sérico', 'µg/dL', 5, 1000)]),
    ('Sangue, ferro e vitaminas', 'Vitamina B12, soro', [_n('b12', 'Vitamina B12', 'pg/mL', 20, 5000)]),
    ('Sangue, ferro e vitaminas', '25-hidroxivitamina D, soro', [_n('vitamina_d', '25(OH) vitamina D', 'ng/mL', 1, 300)]),
    ('Sangue, ferro e vitaminas', 'Ácido fólico, soro', [_n('folato', 'Ácido fólico', 'ng/mL', 0.5, 100)]),
    ('Hormônios e inflamação', 'Hormônio Tireoestimulante (TSH), soro', [_n('tsh', 'TSH', 'mUI/L', 0.001, 500)]),
    ('Hormônios e inflamação', 'T4 livre, soro', [_n('t4_livre', 'T4 livre', 'ng/dL', 0.05, 10)]),
    ('Hormônios e inflamação', 'Testosterona total, soro', [_n('testosterona', 'Testosterona total', 'ng/dL', 1, 3000)]),
    ('Hormônios e inflamação', 'PSA total, soro', [_n('psa', 'PSA total', 'ng/mL', 0, 10000)]),
    ('Hormônios e inflamação', 'Proteína C reativa, soro', [_n('pcr', 'PCR', 'mg/L', 0, 1000)]),
    ('Hormônios e inflamação', 'VHS', [_n('vhs', 'VHS', 'mm/h', 0, 200)]),
    ('Sorologias e rastreio', 'Anti-HIV 1 e 2, soro', [_s('anti_hiv', 'Anti-HIV 1 e 2', SOROLOGIA)]),
    ('Sorologias e rastreio', 'Anti-HCV IgG, soro', [_s('anti_hcv', 'Anti-HCV', SOROLOGIA)]),
    ('Sorologias e rastreio', 'HBsAg, anti-HBc total e anti-HBs', [
        _s('hbsag', 'HBsAg', SOROLOGIA, r'hbsag'), _s('anti_hbc', 'Anti-HBc total', SOROLOGIA, r'anti[\s-]*hbc'),
        _s('anti_hbs', 'Anti-HBs', SOROLOGIA, r'anti[\s-]*hbs')]),
    ('Sorologias e rastreio', 'Sífilis: teste treponêmico ou VDRL, soro', [_s('sifilis', 'Sífilis', SOROLOGIA)]),
    ('Sorologias e rastreio', 'Sangue oculto nas fezes (FIT)', [_s('fit', 'Resultado', FIT)]),
    ('Sorologias e rastreio', 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular', [_s('hpv_resultado', 'Resultado', HPV)]),
]

# Aba Pré-operatório: só o que o motor de lá lê (src/utils/preoperatorio.py). Creatinina, hemoglobina e HbA1c entram
# nos escores; glicemia, ECG e ecocardiograma contam pela data. Os de imagem não têm campo de resultado.
PREOP = {'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro', 'Creatinina, soro', 'Hemograma completo com plaquetas'}
PREOP_IMAGEM = [('Eletrocardiograma de repouso', 'ECG'), ('Ecocardiograma transtorácico', 'Ecocardiograma')]

# Nome curto do botão em "Exames mais comuns".
CURTO = {
    'Glicose, soro': 'Glicemia', 'Hemoglobina glicada (HbA1c), soro': 'HbA1c', 'Insulina de jejum, soro': 'Insulina',
    'Colesterol total e frações, soro': 'Perfil lipídico', 'Lipoproteína(a) - Lp(a), soro': 'Lp(a)',
    'Apolipoproteína B, soro': 'ApoB', 'Creatinina, soro': 'Creatinina',
    'Relação albumina/creatinina urinária (uACR)': 'Albumina/creatinina (urina)', 'Ureia, soro': 'Ureia',
    'Ácido úrico, soro': 'Ácido úrico', 'EAS - Elementos Anormais e Sedimentoscopia': 'EAS (urina tipo 1)',
    'Sódio, soro': 'Sódio', 'Potássio, soro': 'Potássio', 'Cálcio iônico, soro': 'Cálcio iônico', 'Fósforo, soro': 'Fósforo',
    'Magnésio, soro': 'Magnésio', 'Paratormônio (PTH), soro': 'PTH', 'Aspartato aminotransferase, soro': 'TGO (AST)',
    'Alanina aminotransferase, soro': 'TGP (ALT)', 'Gama-GT, soro': 'Gama-GT', 'Fosfatase alcalina, soro': 'Fosfatase alcalina',
    'Bilirrubinas totais e frações, soro': 'Bilirrubinas', 'Albumina, soro': 'Albumina sérica',
    'Tempo de protrombina (TP/INR), plasma': 'TP/INR', 'Hemograma completo com plaquetas': 'Hemograma',
    'Ferritina, soro': 'Ferritina', 'Ferro sérico': 'Ferro sérico', 'Vitamina B12, soro': 'Vitamina B12',
    '25-hidroxivitamina D, soro': 'Vitamina D', 'Ácido fólico, soro': 'Ácido fólico',
    'Hormônio Tireoestimulante (TSH), soro': 'TSH', 'T4 livre, soro': 'T4 livre', 'Proteína C reativa, soro': 'PCR',
    'VHS': 'VHS', 'PSA total, soro': 'PSA', 'Testosterona total, soro': 'Testosterona', 'Anti-HIV 1 e 2, soro': 'Anti-HIV',
    'Anti-HCV IgG, soro': 'Anti-HCV', 'HBsAg, anti-HBc total e anti-HBs': 'Hepatite B',
    'Sífilis: teste treponêmico ou VDRL, soro': 'Sífilis', 'Sangue oculto nas fezes (FIT)': 'Sangue oculto (FIT)',
    'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular': 'DNA-HPV',
}

# Exames que o laudo e o catálogo trazem separados, mas que são um campo de um exame da lista (ex.: o HDL dosado
# sozinho). Os demais nomes do mesmo exame (ex.: "Glicemia de jejum, soro") são achados pelo código TUSS.
COMPONENTES = {
    'Colesterol total': ('Colesterol total e frações, soro', 'colesterol'),
    'Colesterol (HDL)': ('Colesterol total e frações, soro', 'hdl'),
    'Colesterol (LDL)': ('Colesterol total e frações, soro', 'ldl'),
    'Triglicerídeos': ('Colesterol total e frações, soro', 'triglicerideos'),
    'HBsAg, soro': ('HBsAg, anti-HBc total e anti-HBs', 'hbsag'),
    'Anticorpos anti-HBc total, soro': ('HBsAg, anti-HBc total e anti-HBs', 'anti_hbc'),
    'Anticorpos anti-HBs, soro': ('HBsAg, anti-HBc total e anti-HBs', 'anti_hbs'),
}

POR_TITULO = {titulo: campos for _, titulo, campos in EXAMES}
CAMPOS = {c['nome']: c for _, _, campos in EXAMES for c in campos}
# Resultado em texto livre: exames fora da lista (ou sem número, como o EAS).
LIVRE = {'nome': 'resultado', 'rotulo': 'Resultado', 'texto': True, 'max': 80, 'no_laudo': None}
# Campos que o motor usa nos cálculos: o formulário os envia também soltos (name="colesterol" etc.).
DO_MOTOR = ('colesterol', 'hdl', 'creatinina', 'uacr', 'hba1c', 'hpv_resultado')

_APELIDOS = None


def apelidos():
    """Título do catálogo (ou da lista de "Exames já realizados") → (título da lista, nomes dos campos)."""
    global _APELIDOS
    if _APELIDOS is not None:
        return _APELIDOS
    from src.utils import periodicidade
    from src.utils.catalogo import catalogo
    por_chave = {periodicidade.chaves(t): t for t in POR_TITULO}
    mapa = {t: (t, [c['nome'] for c in campos]) for t, campos in POR_TITULO.items()}
    for titulo, (base, campo) in COMPONENTES.items():
        mapa[titulo] = (base, [campo])
    from src.utils import tuss
    # Os títulos do motor entram também: "Fósforo, soro" é o mesmo exame da lista "Fósforo" (mesmo código TUSS).
    for titulo in (list(catalogo().get('laboratorio', [])) + list(periodicidade.exames_conhecidos())
                   + list(tuss.CODIGOS)):
        if titulo in mapa:
            continue
        base = por_chave.get(periodicidade.chaves(titulo))
        if base:
            mapa[titulo] = (base, [c['nome'] for c in POR_TITULO[base]])
    _APELIDOS = mapa
    return mapa


def campos_do_exame(titulo):
    """Campos de resultado do exame (lista de dicionários). Fora da lista ou sem número: resultado livre."""
    achado = apelidos().get(titulo)
    if not achado or not achado[1]:
        return [LIVRE]
    return [CAMPOS[n] for n in achado[1]]


# ── Leitura do laudo ─────────────────────────────────────────────────────────

# "9.200/mm³" vale (a unidade vem colada); "0/100" e "16/11/2026" não (fração e data).
_NUMERO = re.compile(r'(?<![\w/])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?!\w|/\d)')
_RESULTADO = re.compile(r'resultado\s*:?', re.IGNORECASE)
_REFERENCIA = re.compile(r'valor(es)?\s+de\s+refer|refer[eê]ncia|desej[aá]vel|ideal\b|limite', re.IGNORECASE)
_NAO_E_RESULTADO = re.compile(r'^\s*(m[ée]todo|material|coletad|liberad|data|hash|nota|obs|amostra)', re.IGNORECASE)
# Seção de referência do exame: a linha que começa por "Valor(es) de referência" (o cabeçalho de coluna
# "Valores Obtidos   Valores de Referência" não começa por ele e não abre a seção).
_SECAO_DE_REFERENCIA = re.compile(r'^\s*valor(es)?\s+de\s+refer[eê]ncia', re.IGNORECASE)
_LIMITE = re.compile(r'\bat[ée]\b|\binferior\b|\bsuperior\b|\bmaior\b|\bmenor\b|\bacima\b|\babaixo\b|\bentre\b',
                     re.IGNORECASE)
_FAIXA = re.compile(r'^[\s:.]*\d+(?:[.,]\d+)?\s*(?:a|at[ée]|-|–)\s*\d', re.IGNORECASE)
_RESULTADO_UNICO = re.compile(r'^\s*resultado\s*:\s*(\d+(?:[.,]\d+)?)\s*([^\s\d:][^\s:]{0,14})?\s*$', re.IGNORECASE)
_QUALITATIVO = re.compile(r'n[ãa]o\s+reagente|n[ãa]o\s+detectad[oa]|negativ[oa]|indetermin|inconclusiv|reagente|'
                          r'detectad[oa]|positiv[oa]', re.IGNORECASE)


def _numero(texto, campo):
    m = _NUMERO.search(texto)
    if not m:
        return None
    bruto = m.group(1)
    milhar = campo['nome'] in ('leucocitos', 'plaquetas')
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', bruto):
        if not milhar:
            return None                              # "1.234" fora do hemograma é ambíguo
        valor = float(bruto.replace('.', ''))        # 250.000 plaquetas
    elif ',' in bruto:
        valor = float(bruto.replace('.', '').replace(',', '.'))
    else:
        valor = float(bruto)
    if milhar and re.match(r'\s*(mil\b|x\s*10\s*(³|\^?3)|10\s*(³|\^?3)|k/)', texto[m.end():], re.IGNORECASE):
        valor *= 1000                                # "7,5 mil/mm³" ou "250 x10³/µL"; "500 /mm³" fica 500
    if not campo['min'] <= valor <= campo['max']:
        return None
    return int(valor) if valor.is_integer() else round(valor, 3)


def _qualitativo(texto, campo):
    """Primeira palavra de resultado do trecho (a da referência vem depois e não conta)."""
    m = _QUALITATIVO.search(texto)
    if not m:
        return None
    palavra = m.group(0).lower()
    negativo = bool(re.match(r'n[ãa]o|negativ', palavra))
    if campo['nome'] == 'hpv_resultado':
        # Só o negativo é lido: o tipo detectado e a citologia definem as outras opções, e ficam com o médico.
        return 'nao_detectado' if negativo else None
    if re.match(r'indetermin|inconclusiv', palavra):
        return None if campo['nome'] == 'fit' else 'indeterminado'
    if campo['nome'] == 'fit':
        return 'negativo' if negativo else 'positivo'
    return 'nao_reagente' if negativo else 'reagente'


def _ler(campo, trecho):
    return _qualitativo(trecho, campo) if 'opcoes' in campo else _numero(trecho, campo)


def _e_referencia(trecho):
    """O número do trecho é um limite ("Até 1,2", "Inferior a 40") ou uma faixa ("2,0 a 3,0") de referência?"""
    m = _NUMERO.search(trecho)
    return bool(_LIMITE.search(trecho[:m.start()] if m else trecho) or _FAIXA.match(trecho))


def _limpar(linha):
    """Linha sem o que vem depois de "Valores de referência" (a referência nunca é o resultado)."""
    m = _REFERENCIA.search(linha)
    return linha[:m.start()] if m else linha


def valores_do_bloco(titulo, linhas, campos=None):
    """Resultados reconhecíveis no bloco do exame ``titulo`` (linhas depois do título, até o próximo exame).

    ``campos``: nomes dos campos a procurar (padrão: os do exame). Devolve {nome_do_campo: valor}.
    Um campo só é lido pelo nome do analito ("HDL: 45"), por "Resultado: ..." ou pela primeira linha que começa
    pelo resultado; com vários campos (perfil lipídico, hemograma), só pelo nome do analito."""
    nomes = campos or [c['nome'] for c in POR_TITULO.get(titulo, [])]
    linhas = [l for l in linhas if not _NAO_E_RESULTADO.match(l)]
    # Da linha "Valores de referência" em diante, o que vem escrito como limite ou faixa não é resultado.
    referencia = next((i for i, l in enumerate(linhas) if _SECAO_DE_REFERENCIA.match(l)), len(linhas))
    linhas = [_limpar(l) for l in linhas]
    if 'hpv_resultado' in nomes and any(re.search(r'(?<!n[ãa]o )(?<!n[ãa]o\s)\b(detectad|positiv)', l, re.IGNORECASE)
                                        for l in linhas):
        nomes = [n for n in nomes if n != 'hpv_resultado']   # algum tipo detectado: o médico escolhe a opção
    achados = {}
    for nome in nomes:
        campo = CAMPOS[nome]
        valor, rotulo = None, campo.get('no_laudo')
        if rotulo:
            for i, linha in enumerate(linhas):
                m = re.search(rotulo, linha, re.IGNORECASE)
                if not m or (i > referencia and 'opcoes' not in campo and _e_referencia(linha[m.end():])):
                    continue
                if (valor := _ler(campo, linha[m.end():])) is not None:
                    break
        if valor is None and len(nomes) == 1:
            for linha in linhas:
                m = _RESULTADO.search(linha)
                if m:
                    resto = linha[m.end():]
                    # "RESULTADO: DIRETA : 0,20": o número é de outro analito, não do campo procurado
                    if rotulo and re.search(r'[^\W\d_]{3,}\s*:', resto) and not re.search(rotulo, linha, re.IGNORECASE):
                        continue
                    valor = _ler(campo, resto.rsplit(':', 1)[-1])
                    if valor is not None:
                        break
            if valor is None:
                for linha in linhas[:referencia]:
                    if re.match(r'^[\s:.]*\d', linha) or ('opcoes' in campo and _QUALITATIVO.match(linha.strip())):
                        if (valor := _ler(campo, linha)) is not None:
                            break
        if valor is not None:
            achados[nome] = valor
    return achados


def do_laudo(titulo, linhas):
    """Resultados do exame lido no laudo, pelos campos do exame da lista a que o título corresponde."""
    achado = apelidos().get(titulo)
    if not achado or not achado[1]:
        return _resultado_livre(linhas)
    return valores_do_bloco(achado[0], linhas, achado[1])


def _resultado_livre(linhas):
    """Exame fora da lista: o texto do resultado, quando o laudo traz um só ("RESULTADO: 70 U/L")."""
    for linha in linhas:
        if _SECAO_DE_REFERENCIA.match(linha):
            break
        m = _RESULTADO_UNICO.match(linha)
        if m:
            return {'resultado': ' '.join(parte for parte in m.groups() if parte)}
    return {}


# ── Entrada do formulário e saída para a tela ───────────────────────────────

def ler_resultados(exame, bruto):
    """Valida {'campo': valor} de um exame já realizado. Devolve (itens para mostrar, erros)."""
    if not bruto:
        return [], []
    if not isinstance(bruto, dict):
        return [], [f'Resultado em formato inválido: {exame}.']
    itens, erros = [], []
    for campo in campos_do_exame(exame):
        valor = bruto.get(campo['nome'])
        if valor in (None, ''):
            continue
        if campo.get('texto'):
            texto = ' '.join(str(valor).split())[:campo['max']]
            if texto:
                itens.append({'campo': campo['nome'], 'rotulo': campo['rotulo'], 'valor': texto, 'unidade': ''})
        elif 'opcoes' in campo:
            rotulos = dict(campo['opcoes'])
            if valor not in rotulos:
                erros.append(f'Resultado inválido em {exame}: {campo["rotulo"]}.')
            else:
                itens.append({'campo': campo['nome'], 'rotulo': campo['rotulo'], 'valor': rotulos[valor], 'unidade': ''})
        else:
            try:
                numero = float(str(valor).replace(',', '.'))
            except ValueError:
                numero = None
            if numero is None or not campo['min'] <= numero <= campo['max']:
                erros.append(f'Confira o resultado de {campo["rotulo"]} ({exame}): aceito de '
                             f'{_br(campo["min"])} a {_br(campo["max"])} {campo["unidade"]}.'.replace(' .', '.'))
                continue
            itens.append({'campo': campo['nome'], 'rotulo': campo['rotulo'], 'valor': _br(numero), 'unidade': campo['unidade']})
    return itens, erros


def _br(numero):
    numero = float(numero)
    texto = str(int(numero)) if numero.is_integer() else f'{numero:.3f}'.rstrip('0').rstrip('.')
    return texto.replace('.', ',')


def para_a_tela():
    """Definição usada pela tela: grupos, títulos, nomes curtos, campos e os outros nomes de cada exame."""
    tirar = ('no_laudo',)
    return {
        'exames': [{'grupo': g, 'titulo': t, 'curto': CURTO.get(t, t), 'preop': t in PREOP,
                    'campos': [{k: v for k, v in c.items() if k not in tirar} for c in campos]}
                   for g, t, campos in EXAMES],
        'preop_imagem': [{'titulo': t, 'curto': curto} for t, curto in PREOP_IMAGEM],
        'apelidos': {t: {'titulo': base, 'campos': campos} for t, (base, campos) in apelidos().items()},
        'livre': {k: v for k, v in LIVRE.items() if k not in tirar},
    }
