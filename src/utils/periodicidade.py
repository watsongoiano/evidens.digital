"""Periodicidade dos exames: o exame que o paciente já fez e ainda está em dia não é pedido de novo.

De onde vem o intervalo
-----------------------
Cada recomendação do motor já traz a periodicidade no subtítulo, junto do grupo a que se
aplica e ao lado da diretriz que a sustenta ("Diabéticos | A cada 3-6 meses", "Adultos com HAS |
Anual"). Este módulo NÃO cria intervalo novo: lê o que a regra já diz e o transforma em número.

Regras de leitura (todas conservadoras: na dúvida, o exame continua sendo pedido)

- Faixa ("a cada 3-6 meses", "a cada 4-6 anos"): vale o limite inferior. O exame só é adiado
  se foi feito há menos tempo do que o menor intervalo que a referência admite.
- "Uma vez na vida" ("dose única", "pelo menos 1x na vida"): feito uma vez, não se repete.
- Indicação sem intervalo ("basal", "conforme necessidade", "1ª consulta" do pré-natal, "antes do
  tratamento"): não se adia. A data informada aparece como aviso, e o médico decide.
- "Avaliação inicial": as diretrizes não dizem por quanto tempo o resultado vale. Por decisão do responsável
  clínico do Evidēns (não é prazo de diretriz, e o aviso ao prescritor diz isso), o exame feito há menos de
  90 dias não é repetido, salvo se o resultado informado estiver fora da faixa de referência: nesse caso
  o exame continua no pedido, como nova amostra. A faixa é a da tabela do ABIM (`FAIXAS`); resultado sem
  faixa na tabela, ou não informado, não é julgado, e o aviso pede ao médico que confira.
- Recomendação com mais de uma indicação ("Anual | Também: Em uso de lítio | A cada 6 meses"):
  vale o menor intervalo (a avaliação inicial conta como 90 dias); se alguma indicação não tem intervalo,
  não se adia.
- "Junto da HbA1c": acompanha a HbA1c do mesmo atendimento.

Como se sabe que é o mesmo exame
--------------------------------
Pelo código TUSS (`src/utils/tuss.py`): "Hemograma completo" e "Hemograma completo com plaquetas"
são o mesmo código. Um exame combinado cobre as partes ("TGO e TGP" cobre a ALT pedida sozinha), e
uma recomendação combinada só está em dia se todas as partes foram feitas (vale a data mais antiga).
Exame sem código é comparado pelo nome.

A frase de cada trecho do subtítulo tem de estar classificada aqui: um teste percorre o motor e
falha se aparecer periodicidade nova sem classificação.
"""
import calendar
import re
from datetime import date, datetime, timedelta, timezone

from src.utils import tuss

MAX_EXAMES_ANTERIORES = 80
FUSO_BRASILIA = timezone(timedelta(hours=-3))

UMA_VEZ = 'uma_vez'
AVALIACAO_INICIAL = 'avaliacao_inicial'
VALIDADE_DA_AVALIACAO_INICIAL = 90      # dias; critério do Evidēns (ver o texto no alto do módulo)

# Faixas de referência do adulto para julgar "alterado" na avaliação inicial. Fonte única: ABIM Laboratory Test
# Reference Ranges, revisão de janeiro de 2026. Campo (src/utils/exames_comuns.py) → (mínimo, máximo), ou por sexo.
ABIM = {'rotulo': 'Faixas de referência: ABIM 2026',
        'url': 'https://www.abim.org/Media/bfijryql/laboratory-reference-ranges.pdf'}
FAIXAS = {
    'sodio': (136, 145),                 # mEq/L
    'potassio': (3.5, 5.0),              # mEq/L
    'calcio_ionico': (1.16, 1.31),       # mmol/L
    'hemoglobina': {'feminino': (12, 16), 'masculino': (14, 18)},   # g/dL
    'leucocitos': (4000, 11000),         # /µL
    'plaquetas': (150000, 450000),       # /µL
    'tsh': (0.5, 4.0),                   # mUI/L
    'acido_urico': (3.0, 7.0),           # mg/dL
    'pth': (10, 65),                     # pg/mL (PTH intacto)
}
JUNTO_DA_HBA1C = 'junto_da_hba1c'
TITULO_HBA1C = 'Hemoglobina glicada (HbA1c), soro'

# Trechos que dizem "uma única vez".
_UMA_VEZ = {'dose única', 'dose única na vida', 'pelo menos 1x na vida', 'uma vez'}

# Trechos que qualificam a indicação mas não trazem intervalo. Com um deles (e sem intervalo
# em outro trecho da mesma indicação), o exame não é adiado.
SEM_INTERVALO = {
    # momento único ligado a um tratamento ou a um diagnóstico: a data sozinha não diz se serve
    'basal', 'basal e periódico', 'periódico', 'durante o uso', 'antes do tratamento',
    'antes ou no início do tratamento', 'até 6 meses do início',
    'avaliação inicial ou falha virológica', 'avaliação de fratura', 'reavaliação',
    'para confirmar o diagnóstico', 'rastreio em cascata', 'conforme uso de medicações', 'após teste de hpv positivo',
    'antes de iniciar a tarv', 'após 8 semanas do início ou mudança de tarv', 'após 4-8 semanas do início',
    'antes de cada ciclo', 'antes de cada dose', 'no início e a cada ajuste de dose', '3-4 meses após o início',
    '3-12 meses após o início', 'se spo2 ≤ 92% ou dpoc grave', 'após 4 semanas da primeira carga viral detectável', 'em cada consulta, no máximo mensal',
    'conforme protocolo de prep',
    'repetir em 3 meses',  # confirmação de DRC: a data do exame alterado não adia a repetição
    # a critério clínico
    'conforme necessidade', 'conforme indicação clínica', 'fator de risco', 'adulto em risco',
    'repetir conforme o resultado (t-score)', 'decisão individual (expectativa de vida, prevenção secundária)',
    'alvo < 6 mg/dl', 'não solicitar se >500 em 2 exames consecutivos com intervalo de 6 meses',
    # quem e a partir de quando, sem dizer de quanto em quanto tempo
    'portador ou parente de 1º grau não testado', 'a partir de 40 anos', 'a partir de 45 anos', '65-75 anos',
    'alto risco de pré-eclâmpsia',
    # pré-natal: o que manda é a idade gestacional, não o tempo desde o último exame
    '1ª consulta', '1ª consulta após 14 semanas', '7-9 semanas', '11-13+6 semanas', '20-24 semanas',
    '24-28 semanas', '28-36 semanas', '35-37 semanas', 'rh negativo: 28 semanas',
    'suscetível: a cada trimestre', 'não realizado com 24-28 semanas: fazer agora',
    '36-37+6 semanas', 'investigação de pré-eclâmpsia', 'agora', 'alto risco', 'protocolo institucional',
    'dm pré-gestacional', 'gemelar monocoriônica', 'a cada 2 semanas a partir de 16 semanas',
    '1ª consulta e com 34 semanas', '1ª consulta e pelo menos a cada 3 meses',
    '1ª consulta, 2-4 semanas após iniciar ou trocar a tarv e a partir de 34 semanas',
    '1º trimestre, a cada trimestre e até 1 ano pós-parto', 'medida secundária na gestação',
    '4-12 semanas após o parto',
}

_UNIDADES = {'semana': 'semanas', 'semanas': 'semanas', 'mês': 'meses', 'meses': 'meses', 'ano': 'anos', 'anos': 'anos'}
_A_CADA = re.compile(r'^(?:fib-4 |inicial e |pelo menos )?a cada (\d+)(?:-\d+)? (semanas?|mês|meses|anos?)(?: se normal)?$')
_ANUAL = re.compile(r'^anual(?: ou conforme (?:indicação|sintomas)| a partir de \d+ anos)?$')
_SEMESTRAL = re.compile(r'^semestral(?: ou conforme indicação)?$')


def intervalo_do_trecho(trecho):
    """O que um trecho do subtítulo diz sobre periodicidade.

    Devolve ('semanas'|'meses'|'anos', n), UMA_VEZ, JUNTO_DA_HBA1C, AVALIACAO_INICIAL, ou None (o trecho não
    traz intervalo).
    """
    t = ' '.join(str(trecho or '').lower().split())
    if t == 'avaliação inicial':
        return AVALIACAO_INICIAL
    if t in _UMA_VEZ:
        return UMA_VEZ
    if t == 'junto da hba1c':
        return JUNTO_DA_HBA1C
    if _ANUAL.match(t):
        return ('anos', 1)
    if t == 'bienal':
        return ('anos', 2)
    if _SEMESTRAL.match(t):
        return ('meses', 6)
    m = _A_CADA.match(t)
    if m:
        return (_UNIDADES[m.group(2)], int(m.group(1)))
    return None


def indicacoes(subtitulo):
    """Separa o subtítulo em indicações: [(grupo, [trechos seguintes])].

    "Adultos | Anual | Também: Em uso de lítio | A cada 6 meses" →
    [('Adultos', ['Anual']), ('Em uso de lítio', ['A cada 6 meses'])]
    """
    lista = []
    for trecho in (t.strip() for t in str(subtitulo or '').split('|')):
        if not trecho:
            continue
        if trecho.startswith('Também:'):
            lista.append((trecho[len('Também:'):].strip(), []))
        elif not lista:
            lista.append((trecho, []))
        else:
            lista[-1][1].append(trecho)
    return lista


def _em_dias(intervalo):
    if intervalo == AVALIACAO_INICIAL:
        return VALIDADE_DA_AVALIACAO_INICIAL
    unidade, n = intervalo
    return n * {'semanas': 7, 'meses': 30.44, 'anos': 365.25}[unidade]


def intervalo(subtitulo, outros=()):
    """Intervalo que vale para a recomendação inteira.

    `outros` são os subtítulos das demais regras que pediram o mesmo exame e foram unidas a esta
    na resposta (o diabético que também vive com HIV): todas as indicações contam.

    Devolve {'tipo': 'intervalo', 'unidade', 'n', 'texto'}, {'tipo': AVALIACAO_INICIAL, 'texto'},
    {'tipo': UMA_VEZ, 'texto'}, {'tipo': JUNTO_DA_HBA1C, 'texto'} ou None (alguma indicação não tem intervalo:
    não adiar).
    """
    achados = []
    for texto in [subtitulo, *outros]:
        da_regra = indicacoes(texto)
        if not da_regra:          # regra sem subtítulo: não se sabe o intervalo dela
            return None
        for _grupo, trechos in da_regra:
            da_indicacao = [(intervalo_do_trecho(t), t) for t in trechos]
            da_indicacao = [(i, t) for i, t in da_indicacao if i is not None]
            if not da_indicacao:
                return None
            achados.extend(da_indicacao)
    if not achados:
        return None
    com_prazo = [(i, t) for i, t in achados if isinstance(i, tuple) or i == AVALIACAO_INICIAL]
    if com_prazo:      # o menor intervalo manda, mesmo que outra indicação seja "uma vez na vida"
        menor, texto = min(com_prazo, key=lambda par: _em_dias(par[0]))
        if menor == AVALIACAO_INICIAL:
            return {'tipo': AVALIACAO_INICIAL, 'texto': texto}
        unidade, n = menor
        return {'tipo': 'intervalo', 'unidade': unidade, 'n': n, 'texto': texto}
    if any(i == JUNTO_DA_HBA1C for i, _ in achados):
        return {'tipo': JUNTO_DA_HBA1C, 'texto': next(t for i, t in achados if i == JUNTO_DA_HBA1C)}
    return {'tipo': UMA_VEZ, 'texto': achados[0][1]}


def somar(data, unidade, n):
    """`data` mais n semanas, meses ou anos (mês e ano de calendário; 31/01 + 1 mês = último dia de fevereiro)."""
    if unidade == 'semanas':
        return data + timedelta(weeks=n)
    meses = data.month - 1 + (n * 12 if unidade == 'anos' else n)
    ano, mes = data.year + meses // 12, meses % 12 + 1
    return date(ano, mes, min(data.day, calendar.monthrange(ano, mes)[1]))


def hoje():
    return datetime.now(FUSO_BRASILIA).date()


def _br(data):
    return data.strftime('%d/%m/%Y')


# ── Entrada: exames que o paciente já fez ────────────────────────────────────

def ler_exames_anteriores(bruto, hoje_=None):
    """Valida `exames_anteriores` do pedido: [{'exame': título, 'data': 'AAAA-MM-DD', 'resultados': {...}}].

    Devolve (lista normalizada, erros). Linha em branco é ignorada; data futura ou impossível é erro.
    'resultados' (opcional) vira a lista de itens para mostrar (exames_comuns.ler_resultados).
    """
    from src.utils import exames_comuns
    hoje_ = hoje_ or hoje()
    if bruto in (None, '', []):
        return [], []
    campo = 'exames_anteriores'
    if not isinstance(bruto, list):
        return [], [{'campo': campo, 'mensagem': 'Exames já realizados em formato inválido.'}]
    if len(bruto) > MAX_EXAMES_ANTERIORES:
        return [], [{'campo': campo, 'mensagem': f'Informe no máximo {MAX_EXAMES_ANTERIORES} exames já realizados.'}]
    lidos, erros = [], []
    for item in bruto:
        if not isinstance(item, dict):
            return [], [{'campo': campo, 'mensagem': 'Exames já realizados em formato inválido.'}]
        exame, quando = item.get('exame'), item.get('data')
        exame = ' '.join(exame.split()) if isinstance(exame, str) else ''
        quando = quando.strip() if isinstance(quando, str) else ''
        resultados = item.get('resultados')
        if not exame and not quando and not resultados:
            continue
        if not exame or len(exame) > 300:
            erros.append({'campo': campo, 'mensagem': 'Informe o nome de cada exame já realizado.'})
            continue
        try:
            data = datetime.strptime(quando, '%Y-%m-%d').date()
        except ValueError:
            erros.append({'campo': campo, 'mensagem': f'Informe a data em que o exame foi feito: {exame}.'})
            continue
        if data > hoje_:
            erros.append({'campo': campo, 'mensagem': f'A data do exame não pode estar no futuro: {exame}.'})
        elif data.year < 1900:
            erros.append({'campo': campo, 'mensagem': f'Confira a data do exame: {exame}.'})
        else:
            itens, erros_resultado = exames_comuns.ler_resultados(exame, resultados)
            erros.extend({'campo': campo, 'mensagem': m} for m in erros_resultado)
            lido = {'exame': exame, 'data': data}
            if itens:
                lido['resultados'] = itens
            lidos.append(lido)
    return lidos, erros


def resultados_informados(exames_anteriores):
    """Exames com resultado digitado ou lido do laudo, para o cartão "Resultados informados"."""
    return [{'exame': e['exame'], 'data': _br(e['data']), 'itens': e['resultados']}
            for e in sorted(exames_anteriores or [], key=lambda e: e['data'], reverse=True) if e.get('resultados')]


# ── Identidade do exame ──────────────────────────────────────────────────────

def chaves(titulo, sexo=None):
    """Conjunto que identifica o exame: os códigos TUSS, ou o nome quando não há código."""
    linhas = tuss.linhas_da_guia(titulo, sexo)
    codigos = {linha['codigo'] for linha in linhas if linha['codigo']}
    return frozenset(codigos) if codigos and all(linha['codigo'] for linha in linhas) else frozenset({'nome:' + tuss._chave(titulo)})


def _ultima_data(titulo, sexo, feitos):
    """Data em que a recomendação inteira foi coberta pela última vez (None se alguma parte falta)."""
    datas = []
    for chave in chaves(titulo, sexo):
        do_componente = [data for chaves_feitas, data in feitos if chave in chaves_feitas]
        if not do_componente:
            return None
        datas.append(max(do_componente))
    return min(datas)


# ── Resultado da avaliação inicial: dentro ou fora da faixa ──────────────────

def _numero(valor):
    try:
        return float(str(valor).replace('.', '').replace(',', '.')) if ',' in str(valor) else float(valor)
    except (TypeError, ValueError):
        return None


def julgar(itens, sexo=None):
    """Julga os resultados informados de um exame pelas `FAIXAS`.

    Devolve ('alterado', [textos dos resultados fora da faixa]), ('normal', []) ou (None, []) quando nenhum
    resultado pôde ser julgado (não informado, sem faixa na tabela ou faixa que depende do sexo não informado).
    """
    fora, julgados = [], 0
    for item in itens or []:
        faixa = FAIXAS.get(item.get('campo'))
        if isinstance(faixa, dict):
            faixa = faixa.get(sexo)
        numero = _numero(item.get('valor'))
        if not faixa or numero is None:
            continue
        julgados += 1
        if not faixa[0] <= numero <= faixa[1]:
            fora.append(' '.join(str(p) for p in (item.get('rotulo'), item.get('valor'), item.get('unidade')) if p))
    if fora:
        return 'alterado', fora
    return ('normal', []) if julgados else (None, [])


def _resultados_mais_recentes(titulo, sexo, exames_anteriores):
    """Resultados informados que cobrem a recomendação: de cada parte dela, os da coleta mais recente.

    A validade conta da parte mais antiga (`_ultima_data`), mas o julgamento olha o último resultado de cada
    parte: o potássio alterado de ontem não pode sumir porque o sódio é de anteontem.
    """
    escolhidos = {}
    for chave in chaves(titulo, sexo):
        da_parte = [e for e in exames_anteriores if chave in cobertos(e['exame'], sexo)]
        if da_parte:
            ultima = max(e['data'] for e in da_parte)
            escolhidos.update({id(e): e for e in da_parte if e['data'] == ultima})
    return [item for e in escolhidos.values() for item in e.get('resultados') or []]


# Exame feito que vale por outro: o cálcio total conta como o cálcio iônico (decisão do responsável clínico).
EQUIVALENTES = {'40301400': '40301419'}


def cobertos(titulo, sexo=None):
    """Códigos que o exame feito cobre: os dele e os dos exames a que equivale."""
    proprios = chaves(titulo, sexo)
    return proprios | {EQUIVALENTES[c] for c in proprios if c in EQUIVALENTES}


# ── Aplicação ────────────────────────────────────────────────────────────────

def aplicar(recomendacoes, exames_anteriores, sexo=None, hoje_=None):
    """Separa o que está em dia. Devolve (mantidas, em_dia).

    `em_dia` segue o formato de `nao_incluidas` da resposta do motor. A recomendação mantida que tem
    exame anterior informado ganha `ultimo_exame` com a data e o porquê de continuar no pedido.
    """
    if not exames_anteriores:
        return recomendacoes, []
    hoje_ = hoje_ or hoje()
    sexo = {'F': 'feminino', 'M': 'masculino'}.get(sexo, sexo)
    feitos = [(cobertos(e['exame'], sexo), e['data']) for e in exames_anteriores]
    mantidas, em_dia, junto = [], [], []
    hba1c_em_dia = False

    def adiar(rec, feito, motivo, link=None):
        item = {'titulo': rec.get('titulo'), 'categoria': rec.get('categoria'), 'estado': 'em_dia',
                'motivo': motivo, 'referencia': re.sub(r'<[^>]+>', '', rec.get('referencia') or ''),
                'feito_em': feito.isoformat()}
        if link:
            item['link'] = link
        em_dia.append(item)

    for rec in recomendacoes:
        if rec.get('categoria') not in ('laboratorio', 'imagem'):
            mantidas.append(rec)
            continue
        feito = _ultima_data(rec.get('titulo'), sexo, feitos)
        if feito is None:
            mantidas.append(rec)
            continue
        regra = intervalo(rec.get('subtitulo'), rec.get('_subtitulos') or ())
        if regra is None:
            mantidas.append(dict(rec, ultimo_exame=f'Feito em {_br(feito)}. Esta indicação não tem intervalo definido '
                                                   'na referência: avalie se o resultado ainda serve.'))
        elif regra['tipo'] == AVALIACAO_INICIAL:
            validade = feito + timedelta(days=VALIDADE_DA_AVALIACAO_INICIAL)
            estado, fora = julgar(_resultados_mais_recentes(rec.get('titulo'), sexo, exames_anteriores), sexo)
            if hoje_ >= validade:
                mantidas.append(dict(rec, ultimo_exame=f'Feito em {_br(feito)}. Avaliação inicial: validade de '
                                                       f'{VALIDADE_DA_AVALIACAO_INICIAL} dias vencida em {_br(validade)}.'))
            elif estado == 'alterado':
                mantidas.append(dict(rec, ultimo_exame=f'Feito em {_br(feito)}, com alteração ({"; ".join(fora)}): '
                                                       'sugerimos nova amostra.', ultimo_exame_link=ABIM))
            elif estado == 'normal':
                adiar(rec, feito, f'Feito em {_br(feito)}, sem alteração. Avaliação inicial: resultado válido por '
                                  f'{VALIDADE_DA_AVALIACAO_INICIAL} dias (critério do Evidēns), até {_br(validade)}.', ABIM)
            else:
                adiar(rec, feito, f'Feito em {_br(feito)}. Avaliação inicial: resultado válido por '
                                  f'{VALIDADE_DA_AVALIACAO_INICIAL} dias (critério do Evidēns), até {_br(validade)}. '
                                  'O sistema não conferiu o resultado: se estiver alterado, peça nova amostra.')
        elif regra['tipo'] == UMA_VEZ:
            adiar(rec, feito, f'Feito em {_br(feito)}. Indicação de uma única vez ({regra["texto"]}): não precisa repetir.')
        elif regra['tipo'] == JUNTO_DA_HBA1C:
            junto.append((len(mantidas), rec, feito))
            mantidas.append(rec)
        else:
            proximo = somar(feito, regra['unidade'], regra['n'])
            if hoje_ < proximo:
                adiar(rec, feito, f'Feito em {_br(feito)}. Periodicidade: {regra["texto"]}. Próximo a partir de {_br(proximo)}.')
                hba1c_em_dia = hba1c_em_dia or tuss._chave(rec.get('titulo')) == tuss._chave(TITULO_HBA1C)
            else:
                mantidas.append(dict(rec, ultimo_exame=f'Feito em {_br(feito)}. Periodicidade: {regra["texto"]}. '
                                                       f'Intervalo vencido desde {_br(proximo)}.'))
    # O exame pedido "junto da HbA1c" segue a HbA1c: só é adiado se ela também foi.
    for posicao, rec, feito in reversed(junto):
        if hba1c_em_dia:
            del mantidas[posicao]
            adiar(rec, feito, f'Feito em {_br(feito)}. Acompanha a HbA1c, que está em dia.')
    return mantidas, em_dia


def exames_conhecidos():
    """Nomes de exame oferecidos em "Exames já realizados": um por exame (sem os sinônimos), em ordem alfabética."""
    from src.utils.catalogo import catalogo
    cat, vistos, nomes = catalogo(), set(), []
    for titulo in list(cat.get('laboratorio', [])) + list(cat.get('imagem', [])):
        chave = chaves(titulo)
        if chave not in vistos:
            vistos.add(chave)
            nomes.append(titulo)
    return sorted(nomes, key=tuss._chave)


def nao_reconhecidos(exames_anteriores):
    """Nomes informados que não correspondem a nenhum exame conhecido (não têm como ser conferidos)."""
    if not exames_anteriores:
        return []
    from src.utils.catalogo import catalogo
    cat = catalogo()
    conhecidos = set(tuss._POR_CHAVE) | {tuss._chave(t) for c in ('laboratorio', 'imagem') for t in cat.get(c, [])}
    vistos, soltos = set(), []
    for exame in exames_anteriores:
        chave = tuss._chave(exame['exame'])
        if chave not in conhecidos and chave not in vistos:
            vistos.add(chave)
            soltos.append(exame['exame'])
    return soltos


def orientacao_dos_nao_reconhecidos(exames_anteriores):
    """Aviso para a tela: exame informado com nome fora da lista não entra na conferência."""
    soltos = nao_reconhecidos(exames_anteriores)
    if not soltos:
        return None
    return {'titulo': 'Exame já realizado não reconhecido',
            'descricao': 'A periodicidade não foi conferida para: ' + '; '.join(soltos) + '. '
                         'Para entrar na conferência, o nome do exame precisa ser escolhido na lista do catálogo.',
            'referencia': ''}
