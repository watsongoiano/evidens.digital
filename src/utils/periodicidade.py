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
- Recomendação com mais de uma indicação ("Anual | Também: Em uso de lítio | A cada 6 meses"):
  vale o menor intervalo; se alguma indicação não tem intervalo, não se adia.
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
JUNTO_DA_HBA1C = 'junto_da_hba1c'
TITULO_HBA1C = 'Hemoglobina glicada (HbA1c), soro'

# Trechos que dizem "uma única vez".
_UMA_VEZ = {'dose única', 'dose única na vida', 'pelo menos 1x na vida', 'uma vez'}

# Trechos que qualificam a indicação mas não trazem intervalo. Com um deles (e sem intervalo
# em outro trecho da mesma indicação), o exame não é adiado.
SEM_INTERVALO = {
    # momento único ligado a um tratamento ou a um diagnóstico: a data sozinha não diz se serve
    'basal', 'basal e periódico', 'periódico', 'durante o uso', 'antes do tratamento',
    'antes ou no início do tratamento', 'até 6 meses do início', 'avaliação inicial',
    'avaliação inicial ou falha virológica', 'avaliação de fratura', 'reavaliação',
    'para confirmar o diagnóstico', 'rastreio em cascata', 'conforme uso de medicações',
    # a critério clínico
    'conforme necessidade', 'conforme indicação clínica', 'fator de risco', 'adulto em risco',
    'alvo < 6 mg/dl', 'não solicitar se >500 em 2 exames consecutivos com intervalo de 6 meses',
    # quem e a partir de quando, sem dizer de quanto em quanto tempo
    'portador ou parente de 1º grau não testado', 'a partir de 40 anos', 'a partir de 45 anos', '65-75 anos',
    'alto risco de pré-eclâmpsia',
    # pré-natal: o que manda é a idade gestacional, não o tempo desde o último exame
    '1ª consulta', '1ª consulta após 14 semanas', '7-9 semanas', '11-13+6 semanas', '20-24 semanas',
    '24-28 semanas', '28-36 semanas', '35-37 semanas', 'rh negativo: 28 semanas',
    'suscetível: a cada trimestre', 'não realizado com 24-28 semanas: fazer agora',
}

_UNIDADES = {'semana': 'semanas', 'semanas': 'semanas', 'mês': 'meses', 'meses': 'meses', 'ano': 'anos', 'anos': 'anos'}
_A_CADA = re.compile(r'^(?:fib-4 |inicial e |pelo menos )?a cada (\d+)(?:-\d+)? (semanas?|mês|meses|anos?)(?: se normal)?$')
_ANUAL = re.compile(r'^anual(?: ou conforme (?:indicação|sintomas)| a partir de \d+ anos)?$')
_SEMESTRAL = re.compile(r'^semestral(?: ou conforme indicação)?$')


def intervalo_do_trecho(trecho):
    """O que um trecho do subtítulo diz sobre periodicidade.

    Devolve ('semanas'|'meses'|'anos', n), UMA_VEZ, JUNTO_DA_HBA1C, ou None (o trecho não traz intervalo).
    """
    t = ' '.join(str(trecho or '').lower().split())
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
    unidade, n = intervalo
    return n * {'semanas': 7, 'meses': 30.44, 'anos': 365.25}[unidade]


def intervalo(subtitulo):
    """Intervalo que vale para a recomendação inteira.

    Devolve {'tipo': 'intervalo', 'unidade', 'n', 'texto'}, {'tipo': UMA_VEZ, 'texto'},
    {'tipo': JUNTO_DA_HBA1C, 'texto'} ou None (alguma indicação não tem intervalo: não adiar).
    """
    achados = []
    for _grupo, trechos in indicacoes(subtitulo):
        da_indicacao = [(intervalo_do_trecho(t), t) for t in trechos]
        da_indicacao = [(i, t) for i, t in da_indicacao if i is not None]
        if not da_indicacao:
            return None
        achados.extend(da_indicacao)
    if not achados:
        return None
    com_prazo = [(i, t) for i, t in achados if isinstance(i, tuple)]
    if com_prazo:      # o menor intervalo manda, mesmo que outra indicação seja "uma vez na vida"
        (unidade, n), texto = min(com_prazo, key=lambda par: _em_dias(par[0]))
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
    """Valida `exames_anteriores` do pedido: [{'exame': título, 'data': 'AAAA-MM-DD'}].

    Devolve (lista normalizada, erros). Linha em branco é ignorada; data futura ou impossível é erro.
    """
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
        if not exame and not quando:
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
            lidos.append({'exame': exame, 'data': data})
    return lidos, erros


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
    feitos = [(chaves(e['exame'], sexo), e['data']) for e in exames_anteriores]
    mantidas, em_dia, junto = [], [], []
    hba1c_em_dia = False

    def adiar(rec, feito, motivo):
        em_dia.append({'titulo': rec.get('titulo'), 'categoria': rec.get('categoria'), 'estado': 'em_dia',
                       'motivo': motivo, 'referencia': re.sub(r'<[^>]+>', '', rec.get('referencia') or ''),
                       'feito_em': feito.isoformat()})

    for rec in recomendacoes:
        if rec.get('categoria') not in ('laboratorio', 'imagem'):
            mantidas.append(rec)
            continue
        feito = _ultima_data(rec.get('titulo'), sexo, feitos)
        if feito is None:
            mantidas.append(rec)
            continue
        regra = intervalo(rec.get('subtitulo'))
        if regra is None:
            mantidas.append(dict(rec, ultimo_exame=f'Feito em {_br(feito)}. Esta indicação não tem intervalo definido '
                                                   'na referência: avalie se o resultado ainda serve.'))
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
                         'Escolha o nome do exame na lista de sugestões para que ele entre na conferência.',
            'referencia': ''}
