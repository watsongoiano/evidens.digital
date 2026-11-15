"""Leitura de laudos laboratoriais em PDF: quais exames foram feitos e em que data foi a coleta.

Serve só para preencher "Exames já realizados". Quem decide se o exame volta a ser pedido continua
sendo src/utils/periodicidade.py, pela periodicidade da diretriz de cada recomendação.

Como lê (por código, sem IA)
- Texto do PDF com pypdf. PDF escaneado (sem texto) não é lido: o médico digita.
- Título de exame: linha em maiúsculas, sem dois-pontos, com o nome de um exame conhecido; ou, se o
  nome não é conhecido, imediatamente acima de "Método", "Material" ou "[Data da coleta" (é assim que os laudos
  separam um exame do outro).
- Data: a "Data da coleta" logo abaixo do título (antes do exame seguinte); sem ela, a "Coleta" do
  cabeçalho da página (antes do primeiro exame). Data própria inválida não herda a do cabeçalho.
- Nome: sinônimos usados pelos laboratórios (abaixo) e, depois, os nomes do catálogo do motor. Partes
  entre parênteses ou depois de " - " só valem se todas forem nomes do mesmo exame.
  Título que não bate com nenhum fica em `nao_reconhecidos` (o médico vê e decide).

O arquivo é lido em memória e descartado: nada do laudo é gravado.
"""
import io
import logging
import re
from datetime import date

from src.utils import tuss
from src.utils.periodicidade import TITULO_HBA1C, hoje

logging.getLogger('pypdf').setLevel(logging.ERROR)   # avisos de layout do pypdf não interessam no log

TAMANHO_MAXIMO = 4 * 1024 * 1024     # a função da Vercel recebe até 4,5 MB por pedido
PAGINAS_MAXIMAS = 60


# Mensagens fixas mostradas ao médico (a resposta nunca carrega o texto de uma exceção).
MENSAGENS = {
    'nao_pdf': 'O arquivo não é um PDF.',
    'grande': 'O arquivo passa de 4 MB. Envie um laudo por vez.',
    'senha': 'O PDF está protegido por senha.',
    'paginas': f'O PDF tem mais de {PAGINAS_MAXIMAS} páginas.',
    'invalido': 'Não foi possível abrir o PDF.',
    'sem_texto': 'O PDF não tem texto (parece escaneado). Digite os exames e as datas.',
}


class LaudoIlegivel(Exception):
    """PDF inválido, protegido ou sem texto (escaneado). `codigo` é uma chave de MENSAGENS."""

    def __init__(self, codigo):
        super().__init__(codigo)
        self.codigo = codigo

    def __str__(self):
        return MENSAGENS.get(self.codigo, MENSAGENS['invalido'])


# Nomes que os laboratórios usam → título do motor. Chaves já normalizadas (minúsculas, sem acento).
_SINONIMOS = {
    'Glicose, soro': ['glicemia', 'glicose', 'glicemia de jejum', 'glicose de jejum', 'glicose em jejum',
                      'glicose jejum', 'glicemia jejum'],
    'Hemograma completo com plaquetas': ['hemograma', 'hemograma completo', 'hemograma com plaquetas',
                                         'hemograma completo com plaquetas'],
    TITULO_HBA1C: ['hemoglobina glicada', 'hemoglobina glicada (hba1c)', 'hemoglobina glicada hba1c',
                   'hemoglobina glicada - hba1c', 'hemoglobina glicosilada', 'hba1c', 'hemoglobina a1c'],
    'Alanina aminotransferase, soro': ['transaminase glutamico piruvica', 'transaminase piruvica', 'tgp', 'alt',
                                       'tgp - alt', 'tgp (alt)', 'alanina aminotransferase',
                                       'alanina aminotransferase (alt)', 'alanina aminotransferase - alt'],
    'Aspartato aminotransferase, soro': ['transaminase glutamico oxalacetica', 'transaminase oxalacetica', 'tgo',
                                         'ast', 'tgo - ast', 'tgo (ast)', 'aspartato aminotransferase',
                                         'aspartato aminotransferase (ast)', 'aspartato aminotransferase - ast'],
    'Bilirrubinas totais e frações, soro': ['bilirrubinas', 'bilirrubinas totais e fracoes', 'bilirrubina total e fracoes',
                                            'bilirrubina total e fracoes', 'bilirrubinas total e fracoes'],
    'Fosfatase alcalina, soro': ['fosfatase alcalina'],
    'Gama-GT, soro': ['gama gt', 'gama-gt', 'ggt', 'gama glutamil transferase', 'gama glutamiltransferase',
                      'gama glutamil transferase - gama gt', 'gama glutamil transpeptidase'],
    'Ureia, soro': ['ureia', 'ureia serica', 'dosagem de ureia'],
    'Creatinina, soro': ['creatinina', 'creatinina serica', 'dosagem de creatinina'],
    'Sódio, soro': ['sodio', 'sodio serico'],
    'Potássio, soro': ['potassio', 'potassio serico'],
    'Cálcio iônico, soro': ['calcio ionico', 'calcio ionizado'],
    'Magnésio, soro': ['magnesio'],
    'Fósforo, soro': ['fosforo', 'fosforo serico'],
    'Ácido úrico, soro': ['acido urico'],
    'Colesterol total e frações, soro': ['colesterol total e fracoes', 'perfil lipidico', 'lipidograma',
                                         'colesterol total, hdl, ldl e triglicerides'],
    'Triglicerídeos': ['triglicerides', 'triglicerideos', 'triglicerides sericos'],
    'Hormônio Tireoestimulante (TSH), soro': ['tsh', 'tsh ultrassensivel', 'hormonio tireoestimulante',
                                              'hormonio tireoestimulante (tsh)', 'tsh - hormonio tireoestimulante',
                                              'hormonio tireoestimulante - tsh'],
    'T4 livre, soro': ['t4 livre', 'tiroxina livre', 't4 livre (tiroxina livre)'],
    '25-hidroxivitamina D, soro': ['vitamina d', '25-hidroxivitamina d', '25 hidroxivitamina d', '25-oh vitamina d',
                                   'vitamina d - 25 hidroxi', 'vitamina d 25 hidroxi', 'vitamina d (25-oh)'],
    'Vitamina B12, soro': ['vitamina b12', 'vitamina b 12', 'cianocobalamina'],
    'Ferritina, soro': ['ferritina'],
    'Ácido fólico, soro': ['acido folico', 'folato'],
    'EAS - Elementos Anormais e Sedimentoscopia, urina': ['eas', 'urina tipo i', 'urina tipo 1', 'urina rotina',
                                                          'sumario de urina', 'elementos anormais e sedimentoscopia',
                                                          'exame de urina', 'urinalise'],
    'Urocultura com antibiograma': ['urocultura', 'urocultura com antibiograma', 'cultura de urina'],
    'PSA total, soro': ['psa total', 'psa', 'antigeno prostatico especifico', 'antigeno prostatico especifico total'],
    'PSA total e livre, soro': ['psa total e livre', 'psa livre e total'],
    'Tempo de protrombina (TP/INR), plasma': ['tempo de protrombina', 'tp', 'tap', 'tempo de protrombina (tp)',
                                              'tempo de atividade da protrombina'],
    'Ácido láctico (lactato)': ['lactato', 'acido latico', 'acido lactico'],
    'Anticorpos anti-HCV, soro': ['anti-hcv', 'anti hcv', 'hepatite c - anti-hcv', 'hepatite c anti-hcv',
                                  'hepatite c - anti hcv', 'sorologia para hepatite c'],
    'Antígeno HBs, soro': ['hbsag', 'antigeno hbs', 'hepatite b - hbsag', 'antigeno de superficie da hepatite b'],
    'Anticorpos anti-HBs, soro': ['anti-hbs', 'anti hbs', 'hepatite b - anti-hbs'],
    'Anticorpos anti-HBc total, soro': ['anti-hbc total', 'anti hbc total', 'hepatite b - anti-hbc total'],
    'Anticorpos anti-HAV IgG, soro': ['hepatite a - igg', 'anti-hav igg', 'hepatite a igg'],
    'HIV 1/2 (anticorpos e antígeno p24), soro': ['hiv 1 e 2', 'anti-hiv 1 e 2', 'hiv 1/2', 'hiv - anticorpos e antigeno',
                                                  'hiv 1 e 2 - anticorpos e antigeno p24', 'anti hiv 1 e 2'],
    'Sífilis: teste treponêmico ou VDRL, soro': ['vdrl', 'sifilis', 'teste treponemico', 'sifilis - vdrl'],
    'Relação albumina/creatinina urinária (uACR)': ['microalbuminuria', 'relacao albumina/creatinina',
                                                    'relacao albumina creatinina', 'albuminuria'],
    'Paratormônio (PTH), soro': ['pth', 'paratormonio', 'pth intacto', 'paratormonio pth intacto',
                                 'paratormonio pth intacto (molecula inteira)', 'paratormonio (pth)'],
    'Prolactina, soro': ['prolactina'],
    'Lítio, soro': ['litio', 'litemia'],
    'Insulina de jejum, soro': ['insulina', 'insulina de jejum', 'insulina basal'],
    'Homocisteína, soro': ['homocisteina'],
    'Proteína C reativa ultrassensível, soro': ['proteina c reativa ultrassensivel', 'pcr ultrassensivel', 'pcr-us'],
    'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular': [
        'hpv', 'pesquisa de hpv', 'hpv dna', 'hpv alto risco', 'captura hibrida para hpv', 'hpv - captura hibrida',
        'papilomavirus humano (hpv)', 'hpv - pcr', 'hpv por pcr'],
    'Citologia cervicovaginal (Papanicolaou)': ['citologia oncotica', 'colpocitologia oncotica', 'papanicolau',
                                                'papanicolaou', 'citopatologico cervico-vaginal',
                                                'citologia cervico-vaginal'],
    'Sangue oculto nas fezes (FIT)': ['sangue oculto nas fezes', 'pesquisa de sangue oculto nas fezes'],
    'Complemento C3': ['complemento serico c3', 'complemento c3', 'c3'],
    'Complemento C4': ['complemento serico c4', 'complemento c4', 'c4'],
    'Amilase': ['amilase'],
    'Lipase': ['lipase'],
}

_RUIDO = re.compile(r'^(resultado|valor(es)? de referencia|material|metodo|nota|notas|observ|paciente|nome|medico|'
                    r'solicitante|liberado|assinado|pagina|data|unidade|atendimento|identidade|cnes|laudo|amostra|'
                    r'interpreta|referencia)')
_MARCA = re.compile(r'^(m[ée]todo|material|\[?\s*data\s+d[ae]\s+coleta|amostra)\b', re.IGNORECASE)
_DATA_DO_EXAME = re.compile(r'data\s+d[ae]\s+coleta\s*:?\s*(\d{2})/(\d{2})/(\d{4})', re.IGNORECASE)
_DATA_DA_PAGINA = re.compile(r'(?:data\s+d[ae]\s+coleta|coletad[oa]\s+em|\bcoleta)\s*:?\s+(\d{2})/(\d{2})/(\d{4})',
                             re.IGNORECASE)


def _normalizar(texto):
    return tuss._chave(re.sub(r'\s+', ' ', texto or '')).strip(' .:-')


def _indice():
    """Nome normalizado → título do motor (sinônimos primeiro; depois o catálogo)."""
    from src.utils.catalogo import catalogo
    indice = {}
    cat = catalogo()
    for titulo in list(cat.get('laboratorio', [])) + list(cat.get('imagem', [])):
        chave = _normalizar(titulo)
        indice.setdefault(chave, titulo)
        sem_material = re.sub(r', (soro|plasma|urina|sangue total|sangue)$', '', chave)
        indice.setdefault(sem_material, titulo)
    for titulo, nomes in _SINONIMOS.items():
        for nome in nomes:
            indice[_normalizar(nome)] = titulo
    return indice


_INDICE = None


def reconhecer(nome_no_laudo):
    """Título do motor para o nome que o laboratório usou, ou None."""
    global _INDICE
    if _INDICE is None:
        _INDICE = _indice()
    chave = _normalizar(nome_no_laudo)
    if chave in _INDICE:
        return _INDICE[chave]
    # "NOME (OUTRO NOME)" ou "NOME - OUTRO NOME": só vale se TODAS as partes forem nomes do MESMO exame.
    # Um qualificador desconhecido ("GLICOSE (URINA)", "PSA (LIVRE)") deixa o título sem reconhecer.
    partes = [p.strip() for p in re.split(r'\s+-\s+|\(|\)', chave) if p.strip()]
    if len(partes) < 2:
        return None
    titulos = {_INDICE.get(parte) for parte in partes}
    return titulos.pop() if len(titulos) == 1 and None not in titulos else None


def textos_do_pdf(conteudo):
    """Texto de cada página. Levanta LaudoIlegivel se não houver o que ler."""
    if not conteudo or not conteudo.lstrip().startswith(b'%PDF'):
        raise LaudoIlegivel('nao_pdf')
    if len(conteudo) > TAMANHO_MAXIMO:
        raise LaudoIlegivel('grande')
    try:
        from pypdf import PdfReader
        leitor = PdfReader(io.BytesIO(conteudo))
        if leitor.is_encrypted:
            # Muitos laboratórios protegem só contra edição (senha de abertura vazia).
            try:
                aberto = leitor.decrypt('')
            except Exception:
                aberto = 0
            if not aberto:
                raise LaudoIlegivel('senha')
        if len(leitor.pages) > PAGINAS_MAXIMAS:
            raise LaudoIlegivel('paginas')
        textos = [(pagina.extract_text(extraction_mode='layout') or '') for pagina in leitor.pages]
    except LaudoIlegivel:
        raise
    except Exception:
        raise LaudoIlegivel('invalido')
    if not any(re.search(r'[A-Za-zÀ-ú]{3}', t) for t in textos):
        raise LaudoIlegivel('sem_texto')
    return textos


def _data(dia, mes, ano, hoje_):
    try:
        d = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    return d if date(1990, 1, 1) <= d <= hoje_ else None


def _titulo_provavel(linha):
    letras = [c for c in linha if c.isalpha()]
    if len(letras) < 2 or len(linha) > 90 or ':' in linha or '[' in linha or re.search(r'\d{2}/\d{2}/\d{4}', linha):
        return False
    if sum(c.isupper() for c in letras) / len(letras) < 0.8:
        return False
    return not _RUIDO.match(_normalizar(linha))


def _eh_titulo(linhas, i):
    """Título reconhecido vale sozinho (o hemograma, por exemplo, vem sem "Método"); o que não é
    reconhecido só conta como exame se vier logo acima de "Método", "Material" ou "Data da coleta"."""
    if not _titulo_provavel(linhas[i]):
        return False
    return reconhecer(linhas[i]) is not None or any(_MARCA.match(l) for l in linhas[i + 1:i + 2])


def extrair(textos, hoje_=None):
    """Exames do laudo: {'exames': [{'exame', 'data', 'nome_no_laudo'}], 'nao_reconhecidos': [...], 'sem_data': [...]}.

    'data' em AAAA-MM-DD. Exame repetido fica com a coleta mais recente.
    """
    hoje_ = hoje_ or hoje()
    achados, nao_reconhecidos, sem_data = {}, [], []
    for texto in textos:
        linhas = [re.sub(r'\s+', ' ', l).strip() for l in texto.splitlines()]
        linhas = [l for l in linhas if l]
        titulos = [i for i in range(len(linhas)) if _eh_titulo(linhas, i)]
        # Data da página: só a do cabeçalho (antes do primeiro exame), nunca a de um exame da página.
        cabecalho = ' '.join(linhas[:titulos[0]] if titulos else linhas)
        m = _DATA_DA_PAGINA.search(cabecalho)
        da_pagina = _data(*m.groups(), hoje_) if m else None
        for n, i in enumerate(titulos):
            linha = linhas[i]
            titulo = reconhecer(linha)
            fim = titulos[n + 1] if n + 1 < len(titulos) else len(linhas)
            data_exame, explicita = None, False
            for seguinte in linhas[i + 1:min(i + 5, fim)]:   # só até o próximo exame
                m = _DATA_DO_EXAME.search(seguinte)
                if m:
                    data_exame, explicita = _data(*m.groups(), hoje_), True
                    break
            if not explicita:   # data própria inválida (futura, impossível) não herda a da página
                data_exame = da_pagina
            if titulo is None:
                if linha not in nao_reconhecidos:
                    nao_reconhecidos.append(linha)
                continue
            if data_exame is None:
                if linha not in sem_data:
                    sem_data.append(linha)
                continue
            anterior = achados.get(titulo)
            if anterior is None or data_exame > anterior['data']:
                achados[titulo] = {'exame': titulo, 'data': data_exame, 'nome_no_laudo': linha}
    exames = sorted(achados.values(), key=lambda e: tuss._chave(e['exame']))
    return {'exames': [dict(e, data=e['data'].isoformat()) for e in exames],
            'nao_reconhecidos': nao_reconhecidos, 'sem_data': sem_data}


def _como_na_lista(titulo):
    """Nome com que o exame aparece em "Exames já realizados" (um nome por exame, ver periodicidade)."""
    from src.utils import periodicidade
    global _LISTA
    if _LISTA is None:
        _LISTA = {periodicidade.chaves(t): t for t in periodicidade.exames_conhecidos()}
    return _LISTA.get(periodicidade.chaves(titulo), titulo)


_LISTA = None


def ler(conteudo, hoje_=None):
    lido = extrair(textos_do_pdf(conteudo), hoje_)
    vistos, exames = {}, []
    for exame in lido['exames']:
        nome = _como_na_lista(exame['exame'])
        if nome in vistos:  # dois nomes do laudo para o mesmo exame: fica a coleta mais recente
            vistos[nome]['data'] = max(vistos[nome]['data'], exame['data'])
            continue
        vistos[nome] = dict(exame, exame=nome)
        exames.append(vistos[nome])
    return dict(lido, exames=exames)
