"""Modo sombra da conta de operadora: classifica pedidos de exame laboratorial sem barrar nada.

O que faz
---------
Lê os pedidos que a operadora já recebeu (um exame por linha) e diz, para cada um, o que o Evidēns faria:
liberaria (verde), pediria esclarecimento (amarelo) ou barraria, mandando ao médico auditor (vermelho). Nada é
decidido aqui: o resultado mede o tamanho de cada grupo antes de qualquer fila ser ligada.

De onde vêm as regras
---------------------
Das regras do check-up e de pareceres de sociedades médicas. Para a idade e o sexo do beneficiário, sem
comorbidade (a guia não traz), o motor diz o que recomenda como rastreio, com o grau, a periodicidade e a referência, e o que recomenda
não fazer (`nao_incluidas`). O intervalo é lido da periodicidade da própria recomendação
(`src/utils/periodicidade.py`). O exame é reconhecido pelo código TUSS (`src/utils/tuss.py`).

Regra de classificação (decisão do Dr. Rodolfo, 17/11/2026)
- fora do intervalo, recomendação contrária ou sem recomendação para o perfil: vermelho;
- decisão individual (grau C): amarelo;
- recomendado e dentro do intervalo: verde.
"Pelo menos uma vez na vida" já feito fica no amarelo: repetir depende de risco, que o pedido não informa. O
intervalo que depende do resultado anterior ("a cada 3 anos se normal") também: o pedido não informa o resultado.
O exame que as mesmas diretrizes aceitam no lugar do recomendado (ALTERNATIVAS: glicemia de jejum pela HbA1c,
citologia pelo teste de DNA-HPV) é tratado como recomendado.
O último exame vem da coluna data_ultimo_exame ou, na falta dela, do pedido anterior do mesmo beneficiário e código
no próprio arquivo.

Entrada por laudo em PDF
- `pedidos_do_laudo` lê o laudo com o mesmo leitor do check-up (src/utils/laudos.py) e devolve uma linha de pedido
  por exame identificado, com o código TUSS e a data da coleta. Sexo e idade saem do cabeçalho do laudo quando não
  são informados. Nada do laudo é gravado.

Pareceres de sociedades médicas (PARECERES_CONTRARIOS)
- Contra o pedido de rotina em assintomático (vitamina D, testosterona, VHS, FAN e outros): vermelho quando a
  finalidade é rastreio, com o parecer e o link.
- Contra o exame em qualquer finalidade (escopo "sempre": tempo de sangramento, sorologia de H. pylori, folato
  eritrocitário): vermelho também no pedido diagnóstico.
- Evidência insuficiente (USPSTF grau I: TSH) e divergência que muda a conduta (vitamina D acima de 60 anos,
  urocultura em mulher em idade reprodutiva): amarelo.
- Divergência entre diretrizes: sai na coluna "aviso".
- Só entra o exame cujo código TUSS está na tabela conferida do repositório; os demais ficam listados em
  docs/operadoras-modo-sombra.md até o código ser conferido.

Intervalo mínimo fora do rastreio (INTERVALOS_MINIMOS)
- HbA1c repetida em menos de 3 meses: vermelho, com a próxima data elegível, em qualquer finalidade.

O que a regra de rastreio não julga
- Urgência, emergência, pronto-socorro e paciente internado: fora do escopo. Exame que não é de laboratório
  (imagem, endoscopia, métodos gráficos) também, nesta versão.
- Pedido com finalidade diagnóstica ou de seguimento (informada, ou com CID que não é de exame de rotina):
  liberado. A regra de rastreio vale para assintomático. CID de rotina: Z00, Z01 (menos Z01.8, usado no
  pré-operatório), Z02 e Z10 a Z13. Z03, Z04, Z08 e Z09 são observação por suspeita e seguimento.
- Finalidade não informada e sem CID: tratado como rastreio, com a origem marcada "presumida", para o resumo
  mostrar quanto do resultado depende dessa presunção.
- Exame sem regra no Evidēns: liberado, marcado "sem regra".

Ainda não entra: a situação do exame no Rol da ANS (Anexo I e DUT). Depende da correlação oficial entre os códigos
TUSS e os itens do Rol, a conferir exame por exame.
"""
import contextlib
import csv
import io
import math
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from functools import lru_cache

from src.utils import periodicidade, tuss

VERSAO = '0.2'

# Limites do envio pela tela (/operadoras).
TAMANHO_MAXIMO_DO_ENVIO = 4 * 1024 * 1024
MAXIMO_DE_ARQUIVOS_NA_TELA = 8

OBRIGATORIAS = ('id_pedido', 'id_beneficiario', 'idade', 'sexo', 'data_pedido', 'codigo_tuss', 'carater', 'regime')
OPCIONAIS = ('segmentacao', 'finalidade', 'cid', 'indicacao_clinica', 'data_ultimo_exame', 'valor', 'comorbidades',
             'medicacoes')
SAIDA = ('cor', 'acao', 'codigo_do_motivo', 'motivo', 'exame', 'grau', 'referencia', 'link', 'aviso', 'finalidade_usada',
         'origem_da_finalidade', 'ultimo_exame_usado', 'origem_do_ultimo_exame', 'proxima_data_elegivel', 'versao',
         'erro')

ACAO = {'verde': 'liberaria', 'amarelo': 'pediria esclarecimento', 'vermelho': 'barraria',
        'fora_do_escopo': 'passaria direto'}
_SEXOS = {'f': 'feminino', 'feminino': 'feminino', 'm': 'masculino', 'masculino': 'masculino'}
_CARATER = {'eletivo': 'eletivo', 'eletiva': 'eletivo', '1': 'eletivo', 'urgencia': 'urgencia', 'emergencia': 'urgencia',
            'urgencia/emergencia': 'urgencia', 'urgencia e emergencia': 'urgencia', '2': 'urgencia'}
_REGIMES = {'ambulatorial': 'ambulatorial', 'domiciliar': 'ambulatorial', 'telessaude': 'ambulatorial',
            'internado': 'internado', 'internacao': 'internado', 'hospitalar': 'internado',
            'pronto-socorro': 'pronto_socorro', 'pronto socorro': 'pronto_socorro'}
_FINALIDADES = {'': None, 'nao_informada': None, 'nao informada': None, 'rastreio': 'rastreio',
                'rastreamento': 'rastreio', 'rotina': 'rastreio', 'check-up': 'rastreio', 'checkup': 'rastreio',
                'diagnostico': 'diagnostico', 'seguimento': 'seguimento', 'acompanhamento': 'seguimento'}
# Grupos da TUSS que esta versão julga: medicina laboratorial (403) e anatomia patológica e citopatologia (406)
_LABORATORIO = ('403', '406')

# Comorbidades que o check-up traz como caixa fixa (as demais vêm de condicoes.COMORBIDADES).
CONDICOES_FIXAS = {
    'hipertensao': 'Hipertensão', 'has_resistente': 'HAS resistente', 'diabetes': 'Diabetes tipo 2',
    'diabetes_tipo_1': 'Diabetes tipo 1', 'dislipidemia': 'Dislipidemia', 'doenca_renal': 'Doença renal crônica',
    'dcv_aterosclerotica': 'DCV aterosclerótica (IAM, AVC, DAP)', 'insuficiencia_cardiaca': 'Insuficiência cardíaca',
    'obesidade': 'Obesidade', 'hiv': 'HIV', 'dpoc': 'DPOC',
}

# Exame que vale por outro nas regras: o cálcio total é tratado como o cálcio iônico (decisão do responsável clínico).
EQUIVALENTES = periodicidade.EQUIVALENTES

# Exames que chegaram nos laudos das operadoras e não são de rastreio: o que a literatura diz de cada um. Entram aqui à
# medida que aparecem, para não voltarem como "sem regra". Com finalidade diagnóstica ou de seguimento, são liberados.
_SSC_2021 = 'https://doi.org/10.1007/s00134-021-06506-y'
_ACC_AHA_2018 = 'https://doi.org/10.1161/CIR.0000000000000625'
NAO_SAO_DE_RASTREIO = {
    '40301109': {'referencia': 'Surviving Sepsis Campaign 2021', 'link': _SSC_2021,
                 'motivo': 'Lactato não é exame de rastreio. Indicação reconhecida: suspeita de sepse ou de hipoperfusão '
                           '(recomendação fraca, evidência de baixa qualidade).'},
    '40301648': {'referencia': 'AHA/ACC 2018 (colesterol)', 'link': _ACC_AHA_2018,
                 'motivo': 'CK não é exame de rastreio, nem de rotina em quem usa estatina (classe III, sem benefício). '
                           'Indicação reconhecida: sintoma muscular grave ou fraqueza objetiva em uso de estatina.'},
    '40302385': {'referencia': None, 'link': None,
                 'motivo': 'Proteínas totais e frações não fazem parte de nenhum rastreio recomendado.'},
}


def comorbidades_validas():
    """Chave → rótulo de tudo o que o check-up aceita em `comorbidades`: as caixas fixas, a lista e os detalhes de
    cada condição (nefrite lúpica, osteoporose recém-diagnosticada...), com o nome da condição à frente."""
    from src.utils import condicoes
    validas = {**CONDICOES_FIXAS, **{chave: item['rotulo'] for chave, item in condicoes.COMORBIDADES.items()}}
    for condicao, (_titulo, _nota, opcoes) in condicoes.DETALHES_COMORBIDADE.items():
        for chave, rotulo in opcoes:
            validas.setdefault(chave, f'{validas.get(condicao, condicao)}: {rotulo[0].lower()}{rotulo[1:]}')
    return validas


def medicacoes_validas():
    from src.utils import medicamentos
    return {chave: item['rotulo'] for chave, item in medicamentos.MEDICAMENTOS.items()}


def _chaves_do_perfil(texto, validas, coluna, erros):
    """Chaves separadas por "|" (ou espaço) → frozenset; chave fora da lista é erro da linha."""
    chaves = frozenset(parte for parte in re.split(r'[|\s]+', str(texto or '').strip().lower()) if parte)
    fora = sorted(chaves - set(validas))
    if fora:
        erros.append(f'{coluna} fora da lista do check-up: {", ".join(fora)}')
    return chaves

# Listas do Choosing Wisely abertas e conferidas em 17/11/2026
_ENDOCRINE_CW = ('https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/'
                 'endocrine-society--choosing-wisely.pdf?la=en')
_ASCP = 'https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf'
_CAMB = 'https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf'
_CSCC = 'https://choosingwiselycanada.org/download/17612'
_CW_CANADA = ('https://choosingwiselycanada.org/wp-content/uploads/2022/10/'
              'Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf')
_VITAMINA_D = 'https://doi.org/10.1210/clinem/dgae290'
_BACTERIURIA = ('https://www.uspreventiveservicestaskforce.org/uspstf/document/ClinicalSummaryFinal/'
                'asymptomatic-bacteriuria-in-adults-screening')


def _parecer(codigos, referencia, link, motivo, sexo=None, escopo='rastreio', cor='vermelho',
             codigo_do_motivo='parecer_contrario', aviso='', idade_min=18, idade_max=120):
    return {'codigos': tuple(codigos), 'sexo': sexo, 'referencia': referencia, 'link': link, 'motivo': motivo,
            'escopo': escopo, 'cor': cor, 'codigo_do_motivo': codigo_do_motivo, 'aviso': aviso,
            'idade_min': idade_min, 'idade_max': idade_max}


# Pareceres de sociedades médicas sobre exames laboratoriais em adultos. 'sexo' None: os dois.
# escopo 'rastreio': vale quando a finalidade é rastreio e o check-up não recomenda o exame para o perfil.
# escopo 'sempre': o parecer é contra o exame em si, e vale também no pedido diagnóstico ou de seguimento.
PARECERES_CONTRARIOS = (
    _parecer(['40302830'], 'Endocrine Society 2024', _VITAMINA_D,
             'Endocrine Society 2024 (sugestão condicional): contra a dosagem de rotina de 25-hidroxivitamina D em '
             'adultos sem indicação estabelecida. No mesmo sentido: SBPC/ML e SBEM 2017, ASCP 2014, CFPC e SBMFC 2018.',
             aviso='Divergência: para o USPSTF 2021 a evidência é insuficiente (grau I); SBPC/ML e SBEM 2017 indicam '
                   'a dosagem em grupos de risco, como gestantes e lactantes.', idade_max=60),
    _parecer(['40302830'], 'Endocrine Society 2024; SBPC/ML e SBEM 2017', _VITAMINA_D,
             'Diretrizes divergem sobre a dosagem de 25-hidroxivitamina D acima de 60 anos; o pedido não informa a '
             'indicação.', cor='amarelo', codigo_do_motivo='divergencia_entre_diretrizes',
             aviso='Divergência: SBPC/ML e SBEM 2017 indicam a dosagem em idosos acima de 60 anos; a Endocrine '
                   'Society 2024 sugere não dosar de rotina, inclusive a partir de 75 anos.', idade_min=61),
    _parecer(['40305015'], 'Endocrine Society (Choosing Wisely 2013, atualizado em 2017)', _ENDOCRINE_CW,
             'Endocrine Society (Choosing Wisely 2013, atualizado em 2017): não dosar 1,25-di-hidroxivitamina D de '
             'rotina; só com hipercalcemia ou função renal reduzida.'),
    _parecer(['40316513'], 'Endocrine Society 2014 e Consenso Global 2019', 'https://doi.org/10.1210/jc.2014-2260',
             'Endocrine Society 2014: contra o diagnóstico de deficiência androgênica em mulheres saudáveis. Consenso '
             'Global 2019: a testosterona total não diagnostica o transtorno do desejo sexual hipoativo. Não vale '
             'para investigação de hiperandrogenismo nem para controle de terapia com testosterona.', sexo='feminino'),
    _parecer(['40316513'], 'Endocrine Society 2018', 'https://doi.org/10.1210/jc.2018-00229',
             'Endocrine Society 2018 (recomendação forte, evidência de baixa qualidade): contra o rastreio de '
             'hipogonadismo em homens da população geral. No mesmo sentido: CUA (Choosing Wisely Canada). Não vale '
             'para busca de casos em doença hipofisária, uso crônico de opioide ou glicocorticoide, infertilidade e '
             'osteoporose.', sexo='masculino'),
    _parecer(['40307085', '40307093'], 'USPSTF 2023 e SBI 2019', 'https://pubmed.ncbi.nlm.nih.gov/36786784/',
             'USPSTF 2023 (grau D): contra o rastreio sorológico de herpes genital em adolescentes e adultos '
             'assintomáticos, gestantes incluídas. SBI 2019 (Choosing Wisely Brasil): não usar sorologia de herpes '
             'simples para diagnóstico ou rastreio na população geral. Não vale para pessoas com HIV ou '
             'imunossupressão.'),
    # Urocultura de rastreio: recomendada na gestação (grau B) e contraindicada fora dela (grau D). O pedido não
    # informa gestação: mulher em idade reprodutiva (15 a 49 anos, OMS) fica no amarelo.
    _parecer(['40310213'], 'USPSTF 2019', _BACTERIURIA,
             'USPSTF 2019: a urocultura de rastreio é recomendada na gestação (grau B) e contraindicada fora dela '
             '(grau D); o pedido não informa gestação.', sexo='feminino', cor='amarelo',
             codigo_do_motivo='depende_de_gestacao', idade_max=49),
    _parecer(['40310213'], 'USPSTF 2019 e SBI 2019', _BACTERIURIA,
             'USPSTF 2019 (grau D) e SBI 2019 (Choosing Wisely Brasil): contra a urocultura de rastreio em adulto '
             'assintomático fora da gestação e sem doença urológica crônica. Não vale antes de procedimento '
             'urológico (IDSA 2019).'),
    _parecer(['40304370'], 'CAMB 2020 e ASCP 2015 (Choosing Wisely)', _CAMB,
             'CAMB 2020 e ASCP 2015 (Choosing Wisely): não usar a VHS para rastrear assintomáticos nem como teste '
             'geral de inflamação; a proteína C reativa é preferível.'),
    _parecer(['40301150'], 'CAMB 2020 (Choosing Wisely Canada)', _CAMB,
             'CAMB 2020 (Choosing Wisely Canada): não pedir ácido úrico na avaliação de rotina de risco '
             'cardiovascular, obesidade ou diabetes.'),
    _parecer(['40301761', '40302717'], 'CAMB 2020 (Choosing Wisely Canada)', _CAMB,
             'CAMB 2020 (Choosing Wisely Canada): não pedir eletroforese de proteínas séricas em assintomáticos; cabe '
             'com hipercalcemia, insuficiência renal, anemia ou lesão óssea lítica sem explicação.'),
    _parecer(['40306852'], 'CRA (Choosing Wisely Canada)', _CW_CANADA,
             'CRA (Choosing Wisely Canada): não pedir FAN como rastreio sem sinais ou sintomas específicos de lúpus '
             'ou de outra doença do tecido conjuntivo.'),
    _parecer(['40312127'], 'CAMB 2020 e CRA (Choosing Wisely Canada)', _CAMB,
             'CAMB 2020 e CRA (Choosing Wisely Canada): ácido úrico, eletroforese de proteínas, FAN e VHS, que '
             'compõem este painel, não devem ser pedidos como rastreio em assintomáticos.'),
    _parecer(['40306437'], 'CSEM (Choosing Wisely Canada)', _CW_CANADA,
             'CSEM (Choosing Wisely Canada): não pedir anti-TPO de rotina.'),
    _parecer(['40316491', '40305627'], 'CSEM (Choosing Wisely Canada), ASCP 2015 e SBPC/ML 2019', _CW_CANADA,
             'CSEM (Choosing Wisely Canada), ASCP 2015 e SBPC/ML 2019: não usar T4 livre ou T3 para rastrear '
             'hipotireoidismo; o exame inicial é o TSH.'),
    _parecer(['40316521'], 'USPSTF 2015',
             'https://www.uspreventiveservicestaskforce.org/uspstf/document/clinical-summary142/'
             'thyroid-dysfunction-screening',
             'USPSTF 2015 (grau I): evidência insuficiente para o rastreio de disfunção tireoidiana em adultos '
             'assintomáticos fora da gestação.', cor='amarelo', codigo_do_motivo='evidencia_insuficiente',
             aviso='Divergência: SBMFC 2018 e CFPC (Choosing Wisely) são contra pedir função tireoidiana de rotina '
                   'em assintomáticos.'),
    _parecer(['40304612', '40304914'], 'ASCP 2014 e SBPC/ML 2023 (Choosing Wisely)', _ASCP,
             'ASCP 2014 e SBPC/ML 2023 (Choosing Wisely): não usar o tempo de sangramento para orientar a conduta.',
             escopo='sempre'),
    _parecer(['40306909', '40306917', '40306925'], 'ASCP 2016 e SBPC/ML 2023 (Choosing Wisely)', _ASCP,
             'ASCP 2016 e SBPC/ML 2023 (Choosing Wisely): não pedir sorologia para Helicobacter pylori; usar o '
             'antígeno fecal ou o teste respiratório.', escopo='sempre'),
    _parecer(['40301087'], 'ASCP 2017 (Choosing Wisely)', _ASCP,
             'ASCP 2017 (Choosing Wisely): não pedir folato eritrocitário; na anemia macrocítica, considerar a '
             'suplementação de ácido fólico.', escopo='sempre'),
)

# Intervalo mínimo entre dois exames iguais, em qualquer finalidade.
INTERVALOS_MINIMOS = (
    {'codigos': ('40302733',), 'unidade': 'meses', 'n': 3, 'referencia': 'CSCC 2024 e SBPC/ML 2023 (Choosing Wisely)',
     'link': _CSCC, 'texto': 'não repetir a HbA1c em menos de 3 meses em paciente estável'},
)

# Exame que as diretrizes do check-up aceitam no lugar do recomendado. 'periodicidade' None: a do recomendado.
# 'condicao': quando a periodicidade depende do resultado anterior, o texto da condição.
ALTERNATIVAS = (
    {'codigo': '40302040', 'no_lugar_de': '40302733', 'periodicidade': None, 'condicao': '',
     'nota': 'O check-up aceita a glicemia de jejum no lugar da HbA1c no rastreio de diabetes; um exame basta.'},
    {'codigo': '40601137', 'no_lugar_de': '40314154', 'periodicidade': 'A cada 3 anos',
     'condicao': 'após dois exames anuais normais',
     'nota': 'O check-up prefere o teste de DNA-HPV; onde ele não está disponível, o MS 2025 aceita a citologia.'},
)

# Divergência entre diretrizes num exame que o check-up recomenda: sai na coluna "aviso".
AVISOS_DE_DIVERGENCIA = {
    '40316149': 'Divergência: a SBMFC 2018 (Choosing Wisely Brasil) é contra o rastreio de rotina com PSA.',
}

# Sem recomendação de rastreio para o perfil: a fonte da regra geral.


def parecer_contrario(codigo, sexo, finalidade='rastreio', idade=40):
    return next((p for p in PARECERES_CONTRARIOS
                 if codigo in p['codigos'] and p['sexo'] in (None, sexo)
                 and p['idade_min'] <= idade <= p['idade_max']
                 and (p['escopo'] == 'sempre' or finalidade == 'rastreio')), None)


# CID-10 de quem procura o serviço para exame de rotina ou de rastreamento, sem queixa: Z00, Z01 (menos Z01.8,
# usado na avaliação pré-operatória), Z02 e Z10 a Z13. Z03 e Z04 são observação por suspeita; Z08 e Z09, seguimento.
_CID_DE_ROTINA = re.compile(r'^Z(00|01(?!8)|02|1[0-3])')
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
    data = date(a, b, c) if len(m.group(1)) == 4 else date(c, b, a)
    if data.year < 1900:
        raise ValueError(texto)
    return data


def _valor(texto):
    """Valor em reais: 1234,56, 1.234,56, 1234.56 ou 1,234.56. ValueError se for ambíguo (1.234), negativo ou texto."""
    t = texto.replace('R$', '').replace(' ', '')
    if re.fullmatch(r'\d{1,3}(\.\d{3})+,\d{1,2}|\d+,\d{1,2}', t):
        return float(t.replace('.', '').replace(',', '.'))
    if re.fullmatch(r'\d+(\.\d{1,2})?', t):
        return float(t)
    if re.fullmatch(r'\d{1,3}(,\d{3})+\.\d{1,2}', t):
        return float(t.replace(',', ''))
    raise ValueError(texto)


def ler_linha(bruta):
    """Normaliza uma linha do arquivo. Devolve (linha, erros); com erro, a linha não é classificada."""
    if None in (bruta or {}):
        return None, ['colunas a mais na linha (confira o separador e as aspas)']
    bruta = {str(k or '').strip().lower(): str(v or '').strip() for k, v in (bruta or {}).items()}
    erros = [f'falta {coluna}' for coluna in OBRIGATORIAS if not bruta.get(coluna)]
    if erros:
        return None, erros
    linha = {'id_pedido': bruta['id_pedido'], 'id_beneficiario': bruta['id_beneficiario']}
    idade = re.fullmatch(r'(\d{1,3})([.,]0+)?', bruta['idade'])
    if not idade or int(idade.group(1)) > 120:
        erros.append('idade inválida')
    else:
        linha['idade'] = int(idade.group(1))
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
        erros.append('regime inválido (ambulatorial, internado ou pronto-socorro)')
    for coluna in ('data_pedido', 'data_ultimo_exame'):
        try:
            linha[coluna] = _data(bruta.get(coluna))
        except ValueError:
            erros.append(f'{coluna} inválida (AAAA-MM-DD ou DD/MM/AAAA)')
    if linha.get('data_pedido') and linha['data_pedido'] > periodicidade.hoje() + timedelta(days=1):
        erros.append('data_pedido no futuro')
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
    linha['comorbidades'] = _chaves_do_perfil(bruta.get('comorbidades'), comorbidades_validas(), 'comorbidades', erros)
    linha['medicacoes'] = _chaves_do_perfil(bruta.get('medicacoes'), medicacoes_validas(), 'medicacoes', erros)
    if bruta.get('valor'):
        try:
            linha['valor'] = _valor(bruta['valor'])
        except ValueError:
            erros.append('valor inválido (use 1234,56 ou 1234.56)')
    return (None, erros) if erros else (linha, [])


def finalidade_usada(linha):
    """(finalidade, origem). A informada vale; sem ela, o CID decide; sem os dois, presume-se rastreio."""
    if linha['finalidade']:
        return linha['finalidade'], 'informada'
    if linha['cid']:
        return ('rastreio' if _CID_DE_ROTINA.match(linha['cid']) else 'diagnostico'), 'cid'
    return 'rastreio', 'presumida'


def _codigos_do_titulo(titulo):
    return {item['codigo'] for sexo in ('feminino', 'masculino') for item in tuss.linhas_da_guia(titulo, sexo)
            if item['codigo']}


@lru_cache(maxsize=1)
def _conhecidos():
    """Código TUSS de laboratório → nome, para todo exame de laboratório que o motor do check-up sabe pedir.

    O nome é o título do check-up quando o título é só daquele código; no exame combinado (ferro e saturação de
    transferrina, por exemplo), cada código fica com a descrição da TUSS."""
    from src.utils import exames_comuns
    do_titulo, da_tuss = {}, {}
    # Com dois títulos para o mesmo código (PCR e PCR ultrassensível), vale o da lista de exames comuns.
    for titulo in sorted(tuss.CODIGOS, key=lambda t: t not in exames_comuns.POR_TITULO):
        codigos = _codigos_do_titulo(titulo)
        for codigo in codigos:
            if codigo[:3] not in _LABORATORIO:
                continue
            if len(codigos) == 1:
                do_titulo.setdefault(codigo, titulo)
            else:
                da_tuss.setdefault(codigo, tuss.DESCRICOES.get(codigo) or tuss.DA_TABELA.get(codigo) or titulo)
    return {**da_tuss, **do_titulo}


_ORDEM_DO_GRAU = {'A': 0, 'B': 1, 'C': 2}


def _dias(regra):
    if not regra or regra['tipo'] != 'intervalo':
        return math.inf
    return regra['n'] * {'semanas': 7, 'meses': 30, 'anos': 365}[regra['unidade']]


def _mais_permissiva(a, b):
    """Entre duas recomendações para o mesmo código, a de melhor grau; no empate, a de menor intervalo."""
    def peso(rec):
        return (_ORDEM_DO_GRAU.get(rec.get('grau_evidencia'), 3), _dias(periodicidade.intervalo(rec.get('subtitulo') or '')))
    return b if peso(b) < peso(a) else a


@lru_cache(maxsize=4096)
def _perfil(idade, sexo, comorbidades=frozenset(), medicacoes=frozenset()):
    """O que o check-up recomenda e o que recomenda não fazer para a idade, o sexo e, quando o pedido informa, as
    comorbidades e as medicações de uso contínuo (as mesmas entradas do check-up).

    Tabagismo "nunca fumou": a guia não traz esse dado, e ele só muda rastreios de fumante, que não são laboratoriais. None se a idade está fora do que o motor atende (18 a 120 anos); falha do
    motor levanta RuntimeError, para não virar liberação."""
    from src.routes.checkup_intelligent import recomendar
    with contextlib.redirect_stdout(io.StringIO()):       # o motor imprime cada recomendação que acrescenta
        resposta, status = recomendar({'idade': idade, 'sexo': sexo, 'tabagismo': 'nunca_fumou',
                                       'comorbidades': sorted(comorbidades), 'medicacoes': sorted(medicacoes)})
    if status == 400:
        return None
    if status != 200:
        raise RuntimeError(f'o motor do check-up falhou (status {status})')
    return _da_resposta(resposta, sexo)


def _da_resposta(resposta, sexo):
    """(recomendados, contrários) por código TUSS, a partir da resposta do motor do check-up."""
    recomendados, contrarios = {}, {}
    for rec in resposta.get('recommendations') or []:
        if rec.get('categoria') == 'laboratorio':
            for chave in periodicidade.chaves(rec['titulo'], sexo):
                recomendados[chave] = _mais_permissiva(recomendados[chave], rec) if chave in recomendados else rec
    for alternativa in ALTERNATIVAS:
        base = recomendados.get(alternativa['no_lugar_de'])
        if base and alternativa['codigo'] not in recomendados:
            grupo, _, vigente = (base.get('subtitulo') or '').partition(' | ')
            recomendados[alternativa['codigo']] = dict(
                base, subtitulo=f'{grupo} | {alternativa["periodicidade"] or vigente}', _alternativa=alternativa['nota'],
                _condicao=alternativa['condicao'])
    for item in resposta.get('nao_incluidas') or []:
        if item.get('categoria') == 'laboratorio' and item.get('estado') == 'nao_recomendado':
            for chave in periodicidade.chaves(item['titulo'], sexo):
                contrarios.setdefault(chave, item)
    return recomendados, contrarios


def _referencia(rotulo, links):
    primeiro = next((r for r in links or [] if r.get('url')), None)
    return {'referencia': rotulo or '', 'link': primeiro['url'] if primeiro else ''}


def _condicional(texto):
    """A periodicidade depende do resultado anterior ("a cada 3 anos se normal")?"""
    return 'se normal' in texto.lower()


def classificar(linha):
    """Classifica uma linha já normalizada (ler_linha). Devolve as colunas de SAIDA, menos 'erro'."""
    pedido = linha['codigo_tuss']
    codigo = EQUIVALENTES.get(pedido, pedido)          # as regras valem para o exame equivalente
    nome = _conhecidos().get(pedido) or (f'{tuss.DA_TABELA.get(pedido) or pedido} (tratado como {_conhecidos().get(codigo)})'
                                          if pedido != codigo else None) or _conhecidos().get(codigo) or tuss.DESCRICOES.get(codigo) or tuss.DA_TABELA.get(codigo) or ''
    ultimo = linha.get('data_ultimo_exame')
    feito = f'{_br(ultimo)} (pedido anterior no arquivo)' if linha.get('origem_do_ultimo_exame') == 'arquivo' else (
        _br(ultimo) if ultimo else '')

    def saida(cor, codigo_do_motivo, motivo, **extra):
        return {'cor': cor, 'acao': ACAO[cor], 'codigo_do_motivo': codigo_do_motivo, 'motivo': motivo, 'exame': nome,
                'grau': '', 'referencia': '', 'link': '', 'aviso': '', 'finalidade_usada': '',
                'origem_da_finalidade': '', 'ultimo_exame_usado': ultimo.isoformat() if ultimo else '',
                'origem_do_ultimo_exame': linha.get('origem_do_ultimo_exame') or ('informada' if ultimo else ''),
                'proxima_data_elegivel': '', 'versao': VERSAO, **extra}

    if linha['carater'] == 'urgencia' or linha['regime'] != 'ambulatorial':
        return saida('fora_do_escopo', 'urgencia_ou_internado',
                     'Urgência, emergência, pronto-socorro ou paciente internado: fora do escopo.')
    if codigo[:3] not in _LABORATORIO:
        return saida('fora_do_escopo', 'nao_laboratorial', 'Exame que não é de laboratório: fora do escopo desta versão.')
    finalidade, origem = finalidade_usada(linha)
    comum = {'finalidade_usada': finalidade, 'origem_da_finalidade': origem}
    comorbidades, medicacoes = linha.get('comorbidades') or frozenset(), linha.get('medicacoes') or frozenset()
    perfil = _perfil(linha['idade'], linha['sexo'], comorbidades, medicacoes) if finalidade == 'rastreio' else None
    parecer = parecer_contrario(codigo, linha['sexo'], finalidade, linha['idade'])
    if parecer and not (perfil and codigo in perfil[0]):
        return saida(parecer['cor'], parecer['codigo_do_motivo'], parecer['motivo'], referencia=parecer['referencia'],
                     link=parecer['link'], aviso=parecer['aviso'], **comum)
    minimo = next((m for m in INTERVALOS_MINIMOS if codigo in m['codigos']), None)
    if minimo and ultimo:
        proxima = periodicidade.somar(ultimo, minimo['unidade'], minimo['n'])
        if linha['data_pedido'] < proxima:
            return saida('vermelho', 'antes_do_intervalo',
                         f'{minimo["referencia"]}: {minimo["texto"]}; último em {feito}, próximo a partir de '
                         f'{_br(proxima)}.', referencia=minimo['referencia'], link=minimo['link'],
                         proxima_data_elegivel=proxima.isoformat(), **comum)
    fora = NAO_SAO_DE_RASTREIO.get(codigo)
    if fora and finalidade == 'rastreio' and not (perfil and codigo in perfil[0]):
        fonte = {'referencia': fora['referencia'], 'link': fora['link']} if fora['link'] else {}
        return saida('vermelho' if fora['link'] else 'amarelo', 'nao_e_de_rastreio', fora['motivo'], **fonte, **comum)
    if fora:
        return saida('verde', 'indicacao_informada' if origem == 'informada' else 'indicacao_pelo_cid',
                     'Finalidade diagnóstica ou de seguimento informada no pedido.' if origem == 'informada'
                     else f'CID {_cid(linha["cid"])} informado: indicação diagnóstica ou de seguimento.', **comum)
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
        comum.update(grau=grau, aviso=AVISOS_DE_DIVERGENCIA.get(codigo, ''),
                     **_referencia(rec.get('referencia'), rec.get('referencias')))
        grupo = (rec.get('subtitulo') or '').split(' | ')[0]
        regra = periodicidade.intervalo(rec.get('subtitulo') or '')
        if ultimo and regra:
            if regra['tipo'] == periodicidade.UMA_VEZ:
                if 'pelo menos' in regra['texto'].lower():
                    return saida('amarelo', 'repeticao_depende_de_risco',
                                 f'Rastreio indicado {regra["texto"].lower()}, já feito em {feito}; '
                                 'repetir depende de risco, que o pedido não informa.', **comum)
                return saida('vermelho', 'ja_realizado',
                             f'Indicação de uma única vez ({regra["texto"].lower()}); já feito em {feito}.', **comum)
            if regra['tipo'] == 'intervalo':
                proxima = periodicidade.somar(ultimo, regra['unidade'], regra['n'])
                if linha['data_pedido'] < proxima and (rec.get('_condicao') or _condicional(regra['texto'])):
                    texto = f'{regra["texto"]} {rec.get("_condicao") or ""}'.strip().lower()
                    return saida('amarelo', 'intervalo_depende_do_resultado',
                                 f'Repetição antes do intervalo ({texto}); último em {feito}. O intervalo depende '
                                 'do resultado anterior, que o pedido não informa.',
                                 proxima_data_elegivel=proxima.isoformat(), **comum)
                if linha['data_pedido'] < proxima:
                    return saida('vermelho', 'antes_do_intervalo',
                                 f'Antes do intervalo: {regra["texto"].lower()}; último em {feito}, '
                                 f'próximo a partir de {_br(proxima)}.', proxima_data_elegivel=proxima.isoformat(), **comum)
        if grau == 'C':
            return saida('amarelo', 'decisao_individual', f'{grupo}: decisão individual (grau C).', **comum)
        if rec.get('_alternativa'):
            return saida('verde', 'alternativa_aceita', f'{grupo}: alternativa aceita. {rec["_alternativa"]}', **comum)
        tipo = 'exame recomendado' if comorbidades or medicacoes else 'rastreio recomendado'
        return saida('verde', 'recomendado', f'{grupo}: {tipo} (grau {grau}).' if grau else f'{grupo}: {tipo}.', **comum)
    contra = contrarios.get(codigo)
    if contra:
        from src.utils.reference_links import build_reference_links
        links = build_reference_links(contra.get('titulo') or '', contra.get('referencia') or '')
        return saida('vermelho', 'recomendacao_contraria', contra.get('motivo') or 'Recomendação contrária ao rastreio.',
                     **comum, **_referencia(contra.get('referencia'), links))
    # Sem recomendação do check-up e sem parecer contrário de sociedade: não se barra, pede-se a indicação clínica.
    return saida('amarelo', 'sem_recomendacao_para_o_perfil',
                 ('O check-up não indica este exame para a idade, o sexo, as comorbidades e as medicações informadas. '
                  if comorbidades or medicacoes else
                  'O check-up não indica este exame como rastreio para a idade e o sexo informados, sem comorbidade nem '
                  'gestação informadas. ') + 'Pedir a indicação clínica.', **comum)


def _br(data):
    return data.strftime('%d/%m/%Y')


def _cid(cid):
    return cid[:3] + ('.' + cid[3:] if len(cid) > 3 else '')


def _com_o_ultimo_do_arquivo(linhas):
    """Acrescenta a cada linha o último exame igual do mesmo beneficiário pedido antes, no próprio arquivo.

    Vale o mais recente entre o informado na coluna e o achado no arquivo; a origem fica registrada."""
    datas = {}
    for linha in linhas:
        if linha:
            datas.setdefault((linha['id_beneficiario'], linha['codigo_tuss']), set()).add(linha['data_pedido'])
    for linha in linhas:
        if not linha:
            continue
        anteriores = [d for d in datas[(linha['id_beneficiario'], linha['codigo_tuss'])] if d < linha['data_pedido']]
        informado = linha.get('data_ultimo_exame')
        if anteriores and (not informado or max(anteriores) > informado):
            linha['data_ultimo_exame'], linha['origem_do_ultimo_exame'] = max(anteriores), 'arquivo'
        elif informado:
            linha['origem_do_ultimo_exame'] = 'informada'


def classificar_lote(brutas):
    """Classifica as linhas do arquivo. Devolve (resultados, resumo); cada resultado traz as colunas de SAIDA."""
    lidas = [ler_linha(bruta) for bruta in brutas]
    _com_o_ultimo_do_arquivo([linha for linha, _ in lidas])
    resultados, valores = [], []
    for linha, erros in lidas:
        if not erros:
            try:
                resultados.append({**classificar(linha), 'erro': ''})
                valores.append(linha.get('valor') or 0.0)
                continue
            except RuntimeError as falha:
                erros = [str(falha)]
        resultados.append({**{c: '' for c in SAIDA}, 'versao': VERSAO, 'erro': '; '.join(erros)})
        valores.append(0.0)
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
    barrados = Counter(r['exame'] for r in validos if r['cor'] == 'vermelho')
    return {
        'versao': VERSAO, 'linhas': len(resultados), 'invalidas': len(resultados) - len(validos),
        'por_cor': dict(Counter(r['cor'] for r in validos)),
        'por_motivo': dict(Counter(r['codigo_do_motivo'] for r in validos)),
        'origem_da_finalidade': origem,
        'valor_por_cor': {cor: round(total, 2) for cor, total in valor_por_cor.items() if total},
        'mais_barrados': sorted(barrados.items(), key=lambda par: (-par[1], par[0]))[:10],
    }


# Setor do cabeçalho do laudo que indica paciente internado ou em pronto atendimento
_SETOR_INTERNADO = re.compile(r'\bu\.?\s?i\b|\buti\b|\bcti\b|enfermaria|interna', re.IGNORECASE)
_SETOR_DE_URGENCIA = re.compile(r'pronto|emerg|urg[eê]ncia|\bupa\b', re.IGNORECASE)


def regime_do_setor(setor):
    """'internado' ou 'pronto-socorro' quando o setor do laudo diz isso ("U.I CLÍNICA MÉDICA", "UTI"); senão None."""
    if _SETOR_DE_URGENCIA.search(setor or ''):
        return 'pronto-socorro'
    return 'internado' if _SETOR_INTERNADO.search(setor or '') else None


def pedidos_do_laudo(conteudo, id_beneficiario, idade=None, sexo=None, carater='eletivo', regime=None,
                     finalidade='', cid='', comorbidades=(), medicacoes=()):
    """Linhas de pedido, no formato do arquivo do modo sombra, para os exames de um laudo em PDF.

    Devolve (linhas, nao_identificados). Cada exame identificado vira uma linha por código TUSS, com a data da coleta
    como data do pedido. `sexo` (F ou M) e `idade` vêm do cabeçalho do laudo ("Sexo:", "Nasc.:") quando não são
    informados; sem eles, levanta ValueError. Sem `regime`, vale o que o setor do laudo indicar (unidade de
    internação, UTI, pronto-socorro) e, se ele não indicar nada, ambulatorial. `nao_identificados` traz os títulos
    que o leitor não reconheceu, os que ficaram sem data e os exames sem código TUSS conferido."""
    from src.utils import laudos
    textos = laudos.textos_do_pdf(conteudo)
    lido, dados = laudos.dos_textos(textos), laudos.cabecalho(textos)
    sexo = _SEXOS.get(_sem_acento(sexo)) if sexo else dados['sexo']
    if not sexo:
        raise ValueError('o laudo não traz o sexo: informe o sexo')
    if idade is None and not dados['nascimento']:
        raise ValueError('o laudo não traz a data de nascimento: informe a idade')
    regime = regime or regime_do_setor(dados['setor']) or 'ambulatorial'
    linhas, nao_identificados = [], list(lido['nao_reconhecidos']) + list(lido['sem_data'])
    for exame in lido['exames']:
        coleta = date.fromisoformat(exame['data'])
        codigos = [item['codigo'] for item in tuss.linhas_da_guia(exame['exame'], sexo) if item['codigo']]
        if not codigos:
            nao_identificados.append(exame['nome_no_laudo'])
            continue
        nascimento = dados['nascimento']
        anos = idade if idade is not None else (
            coleta.year - nascimento.year - ((coleta.month, coleta.day) < (nascimento.month, nascimento.day)))
        for codigo in codigos:
            linhas.append({'id_pedido': f'{id_beneficiario}-{len(linhas) + 1:02d}', 'id_beneficiario': id_beneficiario,
                           'idade': str(anos), 'sexo': sexo[0].upper(), 'data_pedido': coleta.isoformat(),
                           'codigo_tuss': codigo, 'carater': carater, 'regime': regime, 'finalidade': finalidade,
                           'cid': cid, 'comorbidades': '|'.join(sorted(comorbidades)),
                           'medicacoes': '|'.join(sorted(medicacoes))})
    return linhas, nao_identificados


def ler_csv(texto):
    """Linhas do arquivo (lista de dicionários). Aceita vírgula ou ponto e vírgula como separador."""
    texto = texto.lstrip('﻿')
    cabecalho = texto.split('\n', 1)[0]
    separador = ';' if cabecalho.count(';') > cabecalho.count(',') else ','
    return list(csv.DictReader(io.StringIO(texto), delimiter=separador))


def escrever_csv(brutas, resultados):
    """O arquivo de entrada com as colunas de SAIDA acrescentadas.

    Coluna da entrada com nome igual ao de uma coluna de saída sai com o sufixo "_entrada"."""
    entrada = [c for c in (brutas[0].keys() if brutas else OBRIGATORIAS) if c is not None]
    nome = {c: f'{c}_entrada' if c.strip().lower() in SAIDA else c for c in entrada}
    destino = io.StringIO()
    escritor = csv.DictWriter(destino, fieldnames=[nome[c] for c in entrada] + list(SAIDA), lineterminator='\n',
                              extrasaction='ignore')
    escritor.writeheader()
    for bruta, resultado in zip(brutas, resultados):
        escritor.writerow({**{nome[c]: bruta.get(c, '') for c in entrada}, **resultado})
    return destino.getvalue()


# ── Conferência do pedido pelo check-up (tela /operadoras) ───────────────────────────────────────────────────────────
# A operadora informa os dados do paciente, os mesmos do check-up, e envia o PDF com os exames que o médico pediu. O
# motor do check-up roda como está, sem nenhuma regra a mais, e cada exame pedido é só comparado com o que ele devolve:
# está entre os recomendados para o paciente (indicado) ou não está (não indicado). Os pareceres, as cores e a
# finalidade do modo em lote (acima) não entram aqui.

_DE_EXAME = ('laboratorio', 'imagem')
_NAO_INDICADO_AGORA = {
    'em_dia': 'Já feito e ainda em dia',
    'nao_recomendado': 'O check-up recomenda não fazer',
    'adiado_gestacao': 'Adiado na gestação',
    'proxima_janela': 'Fora da etapa atual da gestação',
    'etapa_anterior': 'Etapa da gestação já passada',
    'dados_insuficientes': 'Faltam dados para o check-up indicar',
}
_MARCADOR_DE_LISTA = re.compile(r'^\s*(?:[-•*·–]+|\d{1,2}\s*[.)-])\s*')
_CODIGO_TUSS = re.compile(r'(?<!\d)(4\d{7})(?!\d)')


def _da_lista_de_exames(textos):
    """Exames de um pedido que não tem o formato de laudo: uma lista de nomes ou de códigos TUSS, um por linha (ou
    separados por vírgula ou ponto e vírgula). Devolve [{'exame', 'nome_no_pedido', 'codigos'}]."""
    from src.utils import laudos
    achados = {}
    for texto in textos:
        for linha in texto.splitlines():
            linha = ' '.join(linha.split())
            for codigo in _CODIGO_TUSS.findall(linha):
                nome = _conhecidos().get(codigo) or tuss.DESCRICOES.get(codigo) or tuss.DA_TABELA.get(codigo)
                if nome:
                    achados.setdefault(nome, {'exame': nome, 'nome_no_pedido': linha[:120], 'codigos': {codigo}})
            sem_codigo = _CODIGO_TUSS.sub(' ', linha)
            for trecho in [sem_codigo] + re.split(r'[,;]', sem_codigo):
                trecho = _MARCADOR_DE_LISTA.sub('', trecho).strip(' -–:.')
                titulo = laudos.reconhecer(trecho) if 2 < len(trecho) <= 90 else None
                if titulo:
                    achados.setdefault(titulo, {'exame': titulo, 'nome_no_pedido': trecho, 'codigos': None})
    return list(achados.values())


def exames_do_pedido(conteudo, arquivo):
    """Exames pedidos que estão num PDF. Devolve (pedidos, nao_identificados, regime_do_setor).

    Lê o laudo de laboratório nos formatos conhecidos; se o PDF não tiver esse formato, lê uma lista de nomes de
    exame ou de códigos TUSS. A data é opcional (a conferência não depende dela). PDF escaneado, sem texto, levanta
    laudos.LaudoIlegivel."""
    from src.utils import laudos
    textos = laudos.textos_do_pdf(conteudo)
    lido, dados = laudos.dos_textos(textos), laudos.cabecalho(textos)
    pedidos = [{'exame': e['exame'], 'nome_no_pedido': e['nome_no_laudo'], 'data': e['data'], 'codigos': None}
               for e in lido['exames']]
    vistos = {p['exame'] for p in pedidos}
    for linha in lido['sem_data']:                      # reconhecido, só sem data de coleta: conta do mesmo jeito
        titulo = laudos.reconhecer(linha)
        if titulo and titulo not in vistos:
            vistos.add(titulo)
            pedidos.append({'exame': titulo, 'nome_no_pedido': linha, 'data': '', 'codigos': None})
    if not pedidos:
        pedidos = [dict(p, data='') for p in _da_lista_de_exames(textos)]
    for pedido in pedidos:
        pedido['arquivo'] = arquivo
    return pedidos, list(lido['nao_reconhecidos']), regime_do_setor(dados['setor'])


def conferir_pedido(paciente, pedidos):
    """Compara os exames pedidos com o que o check-up recomenda para o paciente. Devolve (resultado, erro).

    `paciente`: os dados no formato que o formulário do check-up envia (é também o formato previsto para os dados que
    virão do cadastro da operadora). Vão ao motor como estão, menos o nome; "exames já realizados" inclusive, de modo
    que o exame ainda em dia sai como não indicado agora, com a data do próximo. `pedidos`: saída de exames_do_pedido.
    `erro` é a mensagem do motor quando os dados do paciente são inválidos."""
    from src.routes.checkup_intelligent import recomendar
    from src.utils.reference_links import build_reference_links
    dados = {k: v for k, v in (paciente or {}).items() if k != 'nome_paciente'}
    with contextlib.redirect_stdout(io.StringIO()):       # o motor imprime cada recomendação que acrescenta
        resposta, status = recomendar(dados)
    if status == 400:
        return None, resposta.get('error') or 'Dados do paciente inválidos.'
    if status != 200:
        raise RuntimeError(f'o motor do check-up falhou (status {status})')
    sexo = dados.get('sexo')
    do_checkup = [r for r in resposta.get('recommendations') or [] if r.get('categoria') in _DE_EXAME]
    indicados, nao_agora = {}, {}
    for rec in do_checkup:
        for chave in periodicidade.chaves(rec['titulo'], sexo):
            indicados.setdefault(chave, rec)
    for lista in ('nao_incluidas', 'adiados_gestacao', 'proximas_gestacao'):
        for item in resposta.get(lista) or []:
            if item.get('categoria') in _DE_EXAME and item.get('titulo'):
                for chave in periodicidade.chaves(item['titulo'], sexo):
                    nao_agora.setdefault(chave, item)

    linhas, atendidos = [], set()
    for pedido in pedidos:
        chaves = set(pedido.get('codigos') or periodicidade.chaves(pedido['exame'], sexo))
        chaves |= {EQUIVALENTES[c] for c in chaves if c in EQUIVALENTES}
        rec = next((indicados[c] for c in sorted(chaves) if c in indicados), None)
        item = next((nao_agora[c] for c in sorted(chaves) if c in nao_agora), None)
        linha = {'exame': pedido['exame'], 'nome_no_pedido': pedido.get('nome_no_pedido') or '',
                 'data': pedido.get('data') or '', 'arquivo': pedido.get('arquivo') or '', 'no_checkup': '',
                 'grau': '', 'referencias': [], 'aviso': '', 'observacao': '', 'observacao_link': None}
        if rec:
            atendidos.add(rec['titulo'])
            linha.update(veredito='indicado', estado='indicado', motivo=rec.get('subtitulo') or 'Recomendado pelo check-up.',
                         no_checkup=rec['titulo'], grau=rec.get('grau_evidencia') or '',
                         referencias=rec.get('referencias') or [], aviso=rec.get('ultimo_exame') or '')
        elif item:
            estado = item.get('estado') or 'nao_incluido'
            rotulo = _NAO_INDICADO_AGORA.get(estado, 'Não incluído pelo check-up')
            linha.update(veredito='nao_indicado', estado=estado, motivo=f'{rotulo}. {item.get("motivo") or ""}'.strip(),
                         no_checkup=item['titulo'],
                         referencias=build_reference_links(item['titulo'], item.get('referencia') or ''))
        else:
            linha.update(veredito='nao_indicado', estado='sem_indicacao',
                         motivo='O check-up não indica este exame para este paciente.')
            nota = next((NAO_SAO_DE_RASTREIO[c] for c in sorted(chaves) if c in NAO_SAO_DE_RASTREIO), None)
            if nota and nota['link']:
                linha.update(observacao=nota['motivo'], observacao_link={'label': nota['referencia'], 'url': nota['link']})
        linhas.append(linha)
    indicadas = sum(1 for linha in linhas if linha['veredito'] == 'indicado')
    return {
        'resumo': {'pedidos': len(linhas), 'indicados': indicadas, 'nao_indicados': len(linhas) - indicadas,
                   'do_checkup': len(do_checkup)},
        'linhas': linhas,
        'do_checkup': [{'titulo': r['titulo'], 'motivo': r.get('subtitulo') or '', 'grau': r.get('grau_evidencia') or '',
                        'categoria': r['categoria'], 'pedido': r['titulo'] in atendidos} for r in do_checkup],
    }, None
