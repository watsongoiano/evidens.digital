"""Modo sombra da conta de operadora: classifica pedidos de exame laboratorial sem barrar nada.

O que faz
---------
Lê os pedidos que a operadora já recebeu (um exame por linha) e diz, para cada um, o que o Evidēns faria:
liberaria (verde), pediria esclarecimento (amarelo) ou barraria, mandando ao médico auditor (vermelho). Nada é
decidido aqui: o resultado mede o tamanho de cada grupo antes de qualquer fila ser ligada.

De onde vêm as regras
---------------------
Das mesmas regras do check-up, sem regra nova. Para a idade e o sexo do beneficiário, sem comorbidade (a guia não
traz), o motor diz o que recomenda como rastreio, com o grau, a periodicidade e a referência, e o que recomenda
não fazer (`nao_incluidas`). O intervalo é lido da periodicidade da própria recomendação
(`src/utils/periodicidade.py`). O exame é reconhecido pelo código TUSS (`src/utils/tuss.py`).

Regra de classificação (decisão do Dr. Rodolfo, 17/11/2026)
- fora do intervalo, recomendação contrária ou sem recomendação para o perfil: vermelho;
- decisão individual (grau C): amarelo;
- recomendado e dentro do intervalo: verde.
"Pelo menos uma vez na vida" já feito fica no amarelo: repetir depende de risco, que o pedido não informa.

Pareceres contra o pedido de rotina
- Exame com parecer de sociedade médica contra a dosagem de rotina em assintomático (vitamina D, testosterona
  e outros em PARECERES_CONTRARIOS): vermelho, com o parecer e o link. Só entra o exame cujo código TUSS está na
  tabela conferida do repositório; os demais ficam listados em docs/operadoras-modo-sombra.md até o código ser
  conferido.

O que a regra de rastreio não julga
- Urgência, emergência e paciente internado: fora do escopo.
- Pedido com finalidade diagnóstica ou de seguimento (informada, ou com CID que não é de exame de rotina,
  Z00 a Z13): liberado. A regra de rastreio vale para assintomático.
- Finalidade não informada e sem CID: tratado como rastreio, com a origem marcada "presumida", para o resumo
  mostrar quanto do resultado depende dessa presunção.
- Exame sem regra no Evidēns: liberado, marcado "sem regra".

Ainda não entra: a situação do exame no Rol da ANS (Anexo I e DUT). Depende da correlação oficial entre os códigos
TUSS e os itens do Rol, a conferir exame por exame.
"""
import contextlib
import csv
import io
import re
import unicodedata
from collections import Counter
from datetime import date
from functools import lru_cache

from src.utils import periodicidade, tuss

VERSAO = '0.1'

OBRIGATORIAS = ('id_pedido', 'id_beneficiario', 'idade', 'sexo', 'data_pedido', 'codigo_tuss', 'carater', 'regime')
OPCIONAIS = ('segmentacao', 'finalidade', 'cid', 'indicacao_clinica', 'data_ultimo_exame', 'valor')
SAIDA = ('cor', 'acao', 'codigo_do_motivo', 'motivo', 'exame', 'grau', 'referencia', 'link', 'finalidade_usada',
         'origem_da_finalidade', 'proxima_data_elegivel', 'versao', 'erro')

ACAO = {'verde': 'liberaria', 'amarelo': 'pediria esclarecimento', 'vermelho': 'barraria',
        'fora_do_escopo': 'passaria direto'}
_SEXOS = {'f': 'feminino', 'feminino': 'feminino', 'm': 'masculino', 'masculino': 'masculino'}
_CARATER = {'eletivo': 'eletivo', 'eletiva': 'eletivo', 'urgencia': 'urgencia', 'emergencia': 'urgencia'}
_REGIMES = {'ambulatorial': 'ambulatorial', 'internado': 'internado', 'internacao': 'internado',
            'hospitalar': 'internado'}
_FINALIDADES = {'': None, 'nao_informada': None, 'nao informada': None, 'rastreio': 'rastreio',
                'rastreamento': 'rastreio', 'diagnostico': 'diagnostico', 'seguimento': 'seguimento'}
# Pareceres de sociedades médicas contra o pedido de rotina (rastreio em adulto assintomático). Valem quando a
# finalidade é rastreio e o check-up não recomenda o exame para o perfil. 'sexo' None: os dois.
PARECERES_CONTRARIOS = (
    {'codigos': ('40302830',), 'sexo': None, 'referencia': 'Endocrine Society 2024',
     'link': 'https://doi.org/10.1210/clinem/dgae290',
     'motivo': 'Endocrine Society 2024: contra a dosagem de rotina de 25-hidroxivitamina D em adultos saudáveis.'},
    {'codigos': ('40305015',), 'sexo': None, 'referencia': 'Endocrine Society e AACE (Choosing Wisely 2013)',
     'link': 'https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/'
             'endocrine-society--choosing-wisely.pdf?la=en',
     'motivo': 'Endocrine Society e AACE (Choosing Wisely 2013): não dosar 1,25-di-hidroxivitamina D de rotina; só com '
               'hipercalcemia ou função renal reduzida.'},
    {'codigos': ('40316513',), 'sexo': 'feminino', 'referencia': 'Consenso Global sobre testosterona em mulheres 2019',
     'link': 'https://doi.org/10.1080/13697137.2019.1637079',
     'motivo': 'Consenso Global 2019 (IMS, Endocrine Society e outras): a testosterona no sangue não diagnostica o '
               'transtorno do desejo sexual hipoativo, e nenhum ponto de corte separa mulheres com e sem disfunção '
               'sexual.'},
    {'codigos': ('40316513',), 'sexo': 'masculino', 'referencia': 'Endocrine Society 2018',
     'link': 'https://doi.org/10.1210/jc.2018-00229',
     'motivo': 'Endocrine Society 2018: contra o rastreio de hipogonadismo em homens da população geral.'},
    {'codigos': ('40307085', '40307093'), 'sexo': None, 'referencia': 'USPSTF 2023',
     'link': 'https://pubmed.ncbi.nlm.nih.gov/36786784/',
     'motivo': 'USPSTF 2023 (grau D): contra o rastreio sorológico de herpes genital em adolescentes e adultos '
               'assintomáticos.'},
    # Em mulheres o rastreio é recomendado na gestação, que o pedido não informa: a regra só vale para homens.
    {'codigos': ('40310213',), 'sexo': 'masculino', 'referencia': 'USPSTF 2019',
     'link': 'https://www.uspreventiveservicestaskforce.org/uspstf/document/ClinicalSummaryFinal/'
             'asymptomatic-bacteriuria-in-adults-screening',
     'motivo': 'USPSTF 2019 (grau D): contra o rastreio de bacteriúria assintomática em adultos fora da gestação.'},
)


def parecer_contrario(codigo, sexo):
    return next((p for p in PARECERES_CONTRARIOS if codigo in p['codigos'] and p['sexo'] in (None, sexo)), None)


# CID-10 de quem procura o serviço para exame de rotina ou de rastreamento, sem queixa: Z00 a Z13
_CID_DE_ROTINA = re.compile(r'^Z(0\d|1[0-3])')
_CID = re.compile(r'^[A-Z]\d{2}[0-9A-Z]?$')


def _sem_acento(texto):
    s = unicodedata.normalize('NFD', str(texto or '').strip().lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def _data(texto):
    """AAAA-MM-DD ou DD/MM/AAAA; None se vazio. ValueError se não for data."""
    texto = str(texto or '').strip()
    if not texto:
        return None
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', texto) or re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', texto)
    if not m:
        raise ValueError(texto)
    a, b, c = (int(x) for x in m.groups())
    return date(a, b, c) if len(m.group(1)) == 4 else date(c, b, a)


def ler_linha(bruta):
    """Normaliza uma linha do arquivo. Devolve (linha, erros); com erro, a linha não é classificada."""
    bruta = {str(k or '').strip().lower(): str(v or '').strip() for k, v in (bruta or {}).items()}
    erros = [f'falta {coluna}' for coluna in OBRIGATORIAS if not bruta.get(coluna)]
    if erros:
        return None, erros
    linha = {'id_pedido': bruta['id_pedido'], 'id_beneficiario': bruta['id_beneficiario']}
    if not re.fullmatch(r'\d{1,3}', bruta['idade']) or int(bruta['idade']) > 120:
        erros.append('idade inválida')
    else:
        linha['idade'] = int(bruta['idade'])
    linha['sexo'] = _SEXOS.get(_sem_acento(bruta['sexo']))
    if not linha['sexo']:
        erros.append('sexo inválido (F ou M)')
    linha['codigo_tuss'] = re.sub(r'\D', '', bruta['codigo_tuss'])
    if len(linha['codigo_tuss']) != 8:
        erros.append('codigo_tuss inválido (8 dígitos)')
    linha['carater'] = _CARATER.get(_sem_acento(bruta['carater']))
    if not linha['carater']:
        erros.append('carater inválido (eletivo ou urgencia)')
    linha['regime'] = _REGIMES.get(_sem_acento(bruta['regime']))
    if not linha['regime']:
        erros.append('regime inválido (ambulatorial ou internado)')
    for coluna in ('data_pedido', 'data_ultimo_exame'):
        try:
            linha[coluna] = _data(bruta.get(coluna))
        except ValueError:
            erros.append(f'{coluna} inválida (AAAA-MM-DD)')
    if linha.get('data_pedido') and linha.get('data_ultimo_exame') and linha['data_ultimo_exame'] > linha['data_pedido']:
        erros.append('data_ultimo_exame depois da data_pedido')
    finalidade = _sem_acento(bruta.get('finalidade'))
    if finalidade not in _FINALIDADES:
        erros.append('finalidade inválida (rastreio, diagnostico, seguimento ou nao_informada)')
    linha['finalidade'] = _FINALIDADES.get(finalidade)
    cid = re.sub(r'[.\s]', '', bruta.get('cid', '')).upper()
    if cid and not _CID.match(cid):
        erros.append('cid inválido')
    linha['cid'] = cid
    valor = bruta.get('valor', '').replace('R$', '').strip()
    if valor:
        try:
            linha['valor'] = float(valor.replace('.', '').replace(',', '.') if ',' in valor else valor)
        except ValueError:
            erros.append('valor inválido')
    return (None, erros) if erros else (linha, [])


def finalidade_usada(linha):
    """(finalidade, origem). A informada vale; sem ela, o CID decide; sem os dois, presume-se rastreio."""
    if linha['finalidade']:
        return linha['finalidade'], 'informada'
    if linha['cid']:
        return ('rastreio' if _CID_DE_ROTINA.match(linha['cid']) else 'diagnostico'), 'cid'
    return 'rastreio', 'presumida'


@lru_cache(maxsize=1)
def _conhecidos():
    """Código TUSS → nome do exame, para todo exame que o motor do check-up sabe pedir."""
    nomes = {}
    for titulo in tuss.CODIGOS:
        for sexo in ('feminino', 'masculino'):
            for item in tuss.linhas_da_guia(titulo, sexo):
                if item['codigo']:
                    nomes.setdefault(item['codigo'], titulo)
    return nomes


@lru_cache(maxsize=None)
def _perfil(idade, sexo):
    """O que o check-up recomenda e o que recomenda não fazer, como rastreio, para a idade e o sexo.

    Sem comorbidade e com tabagismo "nunca fumou": a guia não traz esses dados. O tabagismo só muda rastreios de
    fumante, que não são laboratoriais. None se a idade está fora do que o motor atende (18 a 120 anos)."""
    from src.routes.checkup_intelligent import recomendar
    with contextlib.redirect_stdout(io.StringIO()):       # o motor imprime cada recomendação que acrescenta
        resposta, status = recomendar({'idade': idade, 'sexo': sexo, 'tabagismo': 'nunca_fumou'})
    if status != 200:
        return None
    recomendados, contrarios = {}, {}
    for rec in resposta.get('recommendations') or []:
        if rec.get('categoria') == 'laboratorio':
            for chave in periodicidade.chaves(rec['titulo'], sexo):
                recomendados.setdefault(chave, rec)
    for item in resposta.get('nao_incluidas') or []:
        if item.get('categoria') == 'laboratorio' and item.get('estado') == 'nao_recomendado':
            for chave in periodicidade.chaves(item['titulo'], sexo):
                contrarios.setdefault(chave, item)
    return recomendados, contrarios


def _referencia(rotulo, links):
    primeiro = next((r for r in links or [] if r.get('url')), None)
    return {'referencia': rotulo or '', 'link': primeiro['url'] if primeiro else ''}


def classificar(linha):
    """Classifica uma linha já normalizada (ler_linha). Devolve as colunas de SAIDA, menos 'erro'."""
    codigo = linha['codigo_tuss']
    nome = _conhecidos().get(codigo) or tuss.DESCRICOES.get(codigo) or tuss.DA_TABELA.get(codigo) or ''

    def saida(cor, codigo_do_motivo, motivo, **extra):
        return {'cor': cor, 'acao': ACAO[cor], 'codigo_do_motivo': codigo_do_motivo, 'motivo': motivo, 'exame': nome,
                'grau': '', 'referencia': '', 'link': '', 'finalidade_usada': '', 'origem_da_finalidade': '',
                'proxima_data_elegivel': '', 'versao': VERSAO, **extra}

    if linha['carater'] == 'urgencia' or linha['regime'] == 'internado':
        return saida('fora_do_escopo', 'urgencia_ou_internado', 'Urgência, emergência ou paciente internado: fora do escopo.')
    finalidade, origem = finalidade_usada(linha)
    comum = {'finalidade_usada': finalidade, 'origem_da_finalidade': origem}
    perfil = _perfil(linha['idade'], linha['sexo']) if finalidade == 'rastreio' else None
    parecer = parecer_contrario(codigo, linha['sexo']) if finalidade == 'rastreio' and linha['idade'] >= 18 else None
    if parecer and not (perfil and codigo in perfil[0]):
        return saida('vermelho', 'parecer_contrario', parecer['motivo'], referencia=parecer['referencia'],
                     link=parecer['link'], **comum)
    if codigo not in _conhecidos():
        if codigo in tuss.DA_TABELA:
            return saida('verde', 'sem_regra', 'Exame sem regra no Evidēns.', **comum)
        return saida('verde', 'codigo_desconhecido', 'Código fora da tabela de laboratório conferida.', **comum)
    if finalidade != 'rastreio':
        motivo = ('Finalidade diagnóstica ou de seguimento informada no pedido.' if origem == 'informada'
                  else f'CID {_cid(linha["cid"])} informado: indicação diagnóstica ou de seguimento.')
        return saida('verde', 'indicacao_informada' if origem == 'informada' else 'indicacao_pelo_cid', motivo, **comum)
    if perfil is None:
        return saida('verde', 'idade_fora_do_motor', 'O motor do check-up atende de 18 a 120 anos.', **comum)
    recomendados, contrarios = perfil
    rec = recomendados.get(codigo)
    if rec:
        grau = rec.get('grau_evidencia') or ''
        comum.update(grau=grau, **_referencia(rec.get('referencia'), rec.get('referencias')))
        grupo = (rec.get('subtitulo') or '').split(' | ')[0]
        regra = periodicidade.intervalo(rec.get('subtitulo') or '')
        ultimo = linha.get('data_ultimo_exame')
        if ultimo and regra:
            if regra['tipo'] == periodicidade.UMA_VEZ:
                if 'pelo menos' in regra['texto'].lower():
                    return saida('amarelo', 'repeticao_depende_de_risco',
                                 f'Rastreio indicado {regra["texto"].lower()}, já feito em {_br(ultimo)}; '
                                 'repetir depende de risco, que o pedido não informa.', **comum)
                return saida('vermelho', 'ja_realizado', f'Indicado {regra["texto"].lower()}; já feito em {_br(ultimo)}.',
                             **comum)
            if regra['tipo'] == 'intervalo':
                proxima = periodicidade.somar(ultimo, regra['unidade'], regra['n'])
                if linha['data_pedido'] < proxima:
                    return saida('vermelho', 'antes_do_intervalo',
                                 f'Antes do intervalo: {regra["texto"].lower()}; último em {_br(ultimo)}, '
                                 f'próximo a partir de {_br(proxima)}.', proxima_data_elegivel=proxima.isoformat(), **comum)
        if grau == 'C':
            return saida('amarelo', 'decisao_individual', f'{grupo}: decisão individual (grau C).', **comum)
        return saida('verde', 'recomendado', f'{grupo}: rastreio recomendado (grau {grau}).' if grau else
                     f'{grupo}: rastreio recomendado.', **comum)
    contra = contrarios.get(codigo)
    if contra:
        from src.utils.reference_links import build_reference_links
        links = build_reference_links(contra.get('titulo') or '', contra.get('referencia') or '')
        return saida('vermelho', 'recomendacao_contraria', contra.get('motivo') or 'Recomendação contrária ao rastreio.',
                     **comum, **_referencia(contra.get('referencia'), links))
    return saida('vermelho', 'sem_recomendacao_para_o_perfil',
                 'O check-up não recomenda este exame como rastreio para a idade e o sexo informados, sem comorbidade '
                 'nem gestação informadas.',
                 **comum)


def _br(data):
    return data.strftime('%d/%m/%Y')


def _cid(cid):
    return cid[:3] + ('.' + cid[3:] if len(cid) > 3 else '')


def classificar_lote(brutas):
    """Classifica as linhas do arquivo. Devolve (resultados, resumo); cada resultado traz as colunas de SAIDA."""
    resultados, valores = [], []
    for bruta in brutas:
        linha, erros = ler_linha(bruta)
        if erros:
            resultados.append({**{c: '' for c in SAIDA}, 'versao': VERSAO, 'erro': '; '.join(erros)})
            valores.append(0.0)
        else:
            resultados.append({**classificar(linha), 'erro': ''})
            valores.append(linha.get('valor') or 0.0)
    return resultados, resumir(resultados, valores)


def resumir(resultados, valores=()):
    validos = [r for r in resultados if not r['erro']]
    valores = list(valores) or [0.0] * len(resultados)
    valor_por_cor = Counter()
    for r, valor in zip(resultados, valores):
        if not r['erro']:
            valor_por_cor[r['cor']] += valor
    origem = {cor: dict(Counter(r['origem_da_finalidade'] for r in validos if r['cor'] == cor and r['origem_da_finalidade']))
              for cor in ('amarelo', 'vermelho')}
    return {
        'versao': VERSAO, 'linhas': len(resultados), 'invalidas': len(resultados) - len(validos),
        'por_cor': dict(Counter(r['cor'] for r in validos)),
        'por_motivo': dict(Counter(r['codigo_do_motivo'] for r in validos)),
        'origem_da_finalidade': origem,
        'valor_por_cor': {cor: round(total, 2) for cor, total in valor_por_cor.items() if total},
        'mais_barrados': Counter(r['exame'] for r in validos if r['cor'] == 'vermelho').most_common(10),
    }


def ler_csv(texto):
    """Linhas do arquivo (lista de dicionários). Aceita vírgula ou ponto e vírgula como separador."""
    texto = texto.lstrip('﻿')
    cabecalho = texto.split('\n', 1)[0]
    separador = ';' if cabecalho.count(';') > cabecalho.count(',') else ','
    return list(csv.DictReader(io.StringIO(texto), delimiter=separador))


def escrever_csv(brutas, resultados):
    """O arquivo de entrada com as colunas de SAIDA acrescentadas."""
    entrada = list(brutas[0].keys()) if brutas else list(OBRIGATORIAS)
    destino = io.StringIO()
    escritor = csv.DictWriter(destino, fieldnames=entrada + [c for c in SAIDA if c not in entrada], lineterminator='\n')
    escritor.writeheader()
    for bruta, resultado in zip(brutas, resultados):
        escritor.writerow({**bruta, **resultado})
    return destino.getvalue()
