"""Rastreamento do câncer do colo do útero: teste de DNA-HPV oncogênico, citologia e colposcopia.

Fontes (lidas na íntegra para estas regras)
- MS 2025: Diretrizes Brasileiras para o Rastreamento do Câncer do Colo do Útero, Parte I (Portaria
  Conjunta SAES/SECTICS nº 13, de 29/07/2025), recomendações 9-14, 18-25 e 34-40 e Figuras 1 e 2.
- SBOC 2026: Diretrizes de tratamentos oncológicos, Colo do útero (mesmos fluxogramas do MS).
- ACOG 2026: Committee Statement nº 28, Screening for Cervical Cancer (risco habitual).

Resumo aplicado
- 21 a 24 anos, risco habitual: citologia a cada 3 anos (ACOG). MS e SBOC não rastreiam antes dos 25;
  a divergência aparece nas orientações (decisão do responsável técnico, 14/11/2026).
- 25 a 65 anos, risco habitual: teste de DNA-HPV a cada 5 anos (MS e SBOC a partir dos 25; ACOG a
  partir dos 30, com citologia dos 25 aos 29: também vai para as orientações). O limite de 65 anos é o
  da ACOG; o MS convida até os 64 e encerra com teste negativo depois dos 60.
- HIV ou imunossupressão: a cada 3 anos, desde o início da atividade sexual, sem idade para encerrar.
- Histerectomia total por doença benigna (comorbidade marcada): rastreamento dispensado. Sem a
  marcação, a paciente é tratada como não histerectomizada.
- Resultado do último teste (campo opcional do formulário) decide o passo seguinte:
    HPV 16/18 ..................................... colposcopia
    outros tipos + citologia reflexa ASC-US ou mais  colposcopia
    outros tipos + citologia reflexa negativa ...... repetir o teste em 12 meses
    colposcopia sem doença ......................... repetir o teste em 12 meses
    imunossuprimida com qualquer tipo detectado .... colposcopia (não depende da citologia)
- Dos 61 aos 65 com o último teste negativo: não se pede (o negativo depois dos 60 encerra, MS 2025, rec. 12),
  com orientação para o caso de o teste ter sido feito antes dos 60.
- Depois dos 65 anos (risco habitual, sem resultado positivo a seguir): para só com rastreio anterior adequado e
  negativo (pergunta do formulário; ACOG 2026) ou com teste negativo depois dos 60 (MS). Sem rastreio adequado, ou
  sem resposta, o teste continua sendo pedido (MS rec. 13: quem passou dos 60 sem teste faz um). NIC 2+ tratada:
  rastreio por 25 anos após o tratamento (MS rec. 14; ACOG). A orientação mostra a divergência MS x ACOG.
- Aos 65 anos o teste cita só a ACOG (o MS convida até os 64).
- Método (MS: DNA-HPV, sem coteste; ACOG 2026: HPV primário preferido, coteste aceitável, autocoleta a cada 3 anos
  com sistema de seguimento): texto em METODOS.
"""

HPV = 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular'
COLPOSCOPIA = 'Colposcopia (cérvice uterina e vagina)'
CITOLOGIA = 'Citologia cervicovaginal (Papanicolaou)'

NAO_DETECTADO = 'nao_detectado'
HPV_16_18 = 'hpv_16_18'
OUTROS_CITOLOGIA_NEGATIVA = 'outros_citologia_negativa'
OUTROS_CITOLOGIA_ALTERADA = 'outros_citologia_alterada'
COLPOSCOPIA_NEGATIVA = 'colposcopia_negativa'
RESULTADOS = (NAO_DETECTADO, HPV_16_18, OUTROS_CITOLOGIA_NEGATIVA, OUTROS_CITOLOGIA_ALTERADA, COLPOSCOPIA_NEGATIVA)

MS = 'MS 2025 (DNA-HPV)'
SBOC = 'SBOC 2026'
ACOG = 'ACOG 2026'
USPSTF_COLO = 'USPSTF 2018 (colo do útero)'
BRASIL = f'{MS} / {SBOC}'

IDADE_CITOLOGIA = 21   # ACOG: citologia dos 21 aos 29; aqui, até o teste de HPV começar
IDADE_INICIO = 25      # MS e SBOC: teste de DNA-HPV
IDADE_FIM = 65         # ACOG; o MS convida até os 64
IDADE_FIM_MS = 64
IDADE_ENCERRA = 60     # MS: teste negativo depois dos 60 anos encerra
HISTERECTOMIA = 'histerectomia_total'
SIM, NAO = 'sim', 'nao'

# Método: preferido e alternativas aceitas por fonte (a ACOG não proíbe o coteste).
METODOS = ('Métodos: MS 2025, teste de DNA-HPV sem citologia junto (não recomenda o coteste) e, onde o teste não estiver '
           'disponível, citologia a cada 3 anos após dois exames anuais negativos. ACOG 2026: teste de HPV primário a cada 5 '
           'anos é o preferido; o coteste (HPV com citologia) a cada 5 anos é aceitável quando o HPV primário não estiver '
           'disponível ou por escolha após aconselhamento; a autocoleta a cada 3 anos pode ser considerada se houver sistema '
           'de aviso e seguimento.')
NIC2_TEXTO = ('NIC 2, NIC 3 ou adenocarcinoma in situ tratados: manter o rastreamento por 25 anos após o tratamento, mesmo '
              'depois dos 60-65 anos (MS 2025, rec. 14; ACOG 2026).')


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau='A'):
    return {'titulo': titulo, 'descricao': descricao, 'subtitulo': subtitulo, 'categoria': categoria,
            'prioridade': 'alta', 'referencia': referencia, 'grau_evidencia': grau}


def _colposcopia(motivo, descricao):
    return _rec(COLPOSCOPIA, 'imagem', descricao + ' Sem doença na colposcopia: repetir o teste de DNA-HPV em 12 meses.',
                f'{motivo} | Após teste de HPV positivo', BRASIL)


def _divergencia(idade):
    """Antes dos 30 anos as diretrizes brasileiras e a ACOG recomendam condutas diferentes."""
    if idade < IDADE_INICIO:
        feito = ('Foi mantida a citologia a cada 3 anos (ACOG). Pelo MS e pela SBOC o rastreamento começaria aos 25 anos, '
                 'com teste de DNA-HPV: retire o item se preferir segui-los.')
    else:
        feito = ('Foi pedido o teste de DNA-HPV (MS e SBOC). Pela ACOG seria citologia a cada 3 anos até os 29: para '
                 'segui-la, troque o item pela citologia no catálogo.')
    return {
        'titulo': 'Colo do útero: as diretrizes divergem antes dos 30 anos',
        'descricao': 'MS 2025 e SBOC 2026: não rastrear antes dos 25 anos, com teste de HPV ou com citologia (a infecção '
                     'costuma ser transitória e o rastreamento traz mais colposcopias e tratamentos do que benefício); a partir '
                     'dos 25, teste de DNA-HPV a cada 5 anos, sem citologia junto. ACOG 2026: citologia isolada a cada 3 anos '
                     'dos 21 aos 29 anos e teste de HPV a cada 5 anos só a partir dos 30. ' + feito,
        'referencia': f'{BRASIL} / {ACOG}'}


def _quando_encerrar():
    return {
        'titulo': 'Colo do útero: quando encerrar o rastreamento',
        'descricao': 'As diretrizes divergem. MS 2025: encerrar quando o último teste de DNA-HPV, feito depois dos 60 anos, for '
                     'negativo; quem passou dos 60 sem nenhum teste faz um, e negativo encerra. ACOG 2026: depois dos 65 anos, '
                     'parar só com rastreio anterior adequado (3 citologias negativas seguidas ou 2 cotestes negativos em 10 '
                     'anos, o último há até 3 anos para citologia ou até 5 para coteste); sem rastreio adequado ou com alto '
                     'risco, continuar. Com NIC 2, NIC 3 ou adenocarcinoma in situ tratados, manter o rastreamento por 25 anos '
                     'após o tratamento (MS e ACOG).',
        'referencia': f'{MS} / {ACOG}'}


def recomendar(idade, imunossuprimida=False, resultado=None, histerectomizada=False, rastreio_adequado=None,
               nic2_previa=False):
    """Devolve (recomendações, orientações) para uma mulher adulta. `resultado`: um de RESULTADOS ou None.

    `rastreio_adequado`: 'sim', 'nao' ou None (não sabe): rastreio anterior adequado e negativo, que decide se o
    rastreamento pode parar depois dos 65 anos (ACOG 2026). `nic2_previa`: NIC 2, NIC 3 ou AIS já tratados.
    """
    resultado = resultado if resultado in RESULTADOS else None
    recs, orient = [], []

    # Histerectomia total por doença benigna: sem colo, sem rastreamento (um resultado positivo informado segue o fluxo).
    if histerectomizada and resultado in (None, NAO_DETECTADO):
        if idade >= (0 if imunossuprimida else IDADE_CITOLOGIA):
            orient.append({
                'titulo': 'Colo do útero: rastreamento dispensado após histerectomia total',
                'descricao': 'Histerectomia total por doença benigna, sem lesão de alto grau prévia e com exames anteriores '
                             'normais: o rastreamento pode ser encerrado. Se a histerectomia foi por lesão precursora ou câncer '
                             'do colo, manter o rastreamento (coleta vaginal) por pelo menos 25 anos; na dúvida sobre o motivo, '
                             'manter.',
                'referencia': MS if imunossuprimida else f'{MS} / {ACOG}'})
        return recs, orient

    if imunossuprimida:
        if resultado in (HPV_16_18, OUTROS_CITOLOGIA_NEGATIVA, OUTROS_CITOLOGIA_ALTERADA):
            recs.append(_colposcopia('HPV oncogênico detectado com HIV ou imunossupressão',
                                     'HIV ou imunossupressão: qualquer tipo oncogênico detectado indica colposcopia, '
                                     'sem depender da citologia reflexa.'))
        elif resultado == COLPOSCOPIA_NEGATIVA:
            recs.append(_rec(HPV, 'laboratorio',
                             'Colposcopia sem doença após HPV detectado: repetir o teste de DNA-HPV em 12 meses. Negativo: volta a '
                             'cada 3 anos. Detectado de novo: nova colposcopia.',
                             'Colposcopia sem doença após HPV detectado | A cada 1 ano', BRASIL, 'B'))
        else:
            recs.append(_rec(HPV, 'laboratorio',
                             'HIV ou imunossupressão: teste de DNA-HPV oncogênico a cada 3 anos, a partir do início da atividade '
                             'sexual e sem idade para encerrar. Qualquer tipo oncogênico detectado indica colposcopia.',
                             'Mulheres com HIV ou imunossupressão | A cada 3 anos', BRASIL, 'B'))
        return recs, orient

    # Risco habitual. Teste de HPV feito antes dos 25 anos não é considerado (MS, recomendação 11).
    if idade < IDADE_INICIO:
        if idade >= IDADE_CITOLOGIA:
            recs.append(_rec(CITOLOGIA, 'laboratorio',
                             'Citologia isolada a cada 3 anos dos 21 aos 29 anos (ACOG). MS e SBOC não recomendam rastrear antes '
                             'dos 25 anos: veja a orientação sobre a divergência.',
                             'Mulheres 21-24 anos | A cada 3 anos', ACOG, 'B'))
            orient.append(_divergencia(idade))
        return recs, orient

    if resultado == HPV_16_18:
        recs.append(_colposcopia('HPV 16 e/ou 18 detectado',
                                 'HPV 16 ou 18 detectado: colposcopia direta, sem depender de citologia.'))
    elif resultado == OUTROS_CITOLOGIA_ALTERADA:
        recs.append(_colposcopia('HPV oncogênico não 16-18 com citologia reflexa ASC-US ou mais',
                                 'Outro tipo oncogênico (não 16-18) com citologia reflexa alterada (ASC-US ou mais) ou '
                                 'insatisfatória: colposcopia.'))
    elif resultado == OUTROS_CITOLOGIA_NEGATIVA:
        recs.append(_rec(HPV, 'laboratorio',
                         'Outro tipo oncogênico (não 16-18) com citologia reflexa negativa: repetir o teste de DNA-HPV em 12 meses. '
                         'Negativo: volta a cada 5 anos. HPV 16/18 ou citologia alterada no novo teste: colposcopia. Qualquer tipo '
                         'oncogênico persistente por 24 meses: colposcopia, mesmo com citologia negativa.',
                         'HPV oncogênico não 16-18 com citologia reflexa negativa | A cada 1 ano', BRASIL, 'B'))
    elif resultado == COLPOSCOPIA_NEGATIVA:
        recs.append(_rec(HPV, 'laboratorio',
                         'Colposcopia sem doença após HPV detectado: repetir o teste de DNA-HPV em 12 meses. Negativo: volta a cada '
                         '5 anos. HPV 16/18 de novo, ou outro tipo persistente por 24 meses: nova colposcopia.',
                         'Colposcopia sem doença após HPV detectado | A cada 1 ano', BRASIL, 'B'))
    elif idade <= IDADE_FIM and not (resultado == NAO_DETECTADO and idade > IDADE_ENCERRA and not nic2_previa):
        com_acog = idade >= 30
        so_acog = idade > IDADE_FIM_MS
        descricao = ('Teste de DNA-HPV oncogênico com genotipagem a cada 5 anos. HPV 16/18: colposcopia. Outros tipos: citologia '
                     'reflexa na mesma amostra. ' + METODOS)
        if nic2_previa and idade > IDADE_ENCERRA:
            descricao += ' ' + NIC2_TEXTO
        elif idade > IDADE_ENCERRA:
            descricao += ' Depois dos 60 anos, um teste negativo encerra o rastreamento (MS 2025).'
        recs.append(_rec(HPV, 'laboratorio', descricao, 'Mulheres 25-64 anos (ACOG: até 65) | A cada 5 anos',
                         ACOG if so_acog else f'{BRASIL} / {ACOG}' if com_acog else BRASIL, 'A' if com_acog else 'B'))
        if not com_acog:
            orient.append(_divergencia(idade))
    elif idade <= IDADE_FIM:
        # MS 2025 (rec. 12): teste negativo depois dos 60 anos encerra o rastreamento. O campo não traz a data do teste.
        orient.append({
            'titulo': 'Colo do útero: rastreamento encerrado',
            'descricao': 'MS 2025: teste de DNA-HPV negativo depois dos 60 anos encerra o rastreamento. Se o teste negativo foi '
                         'feito antes dos 60 anos, ainda falta um: repetir 5 anos depois dele (acrescente o teste pelo catálogo). '
                         'Pela ACOG 2026, o rastreio vai até os 65 anos e só para com rastreio anterior adequado.',
            'referencia': f'{MS} / {ACOG}'})
    elif nic2_previa:
        # Depois dos 65 com NIC 2+ tratada: MS 2025 (rec. 14) e ACOG 2026 (alto risco) mantêm o rastreamento.
        recs.append(_rec(HPV, 'laboratorio',
                         'Teste de DNA-HPV oncogênico a cada 5 anos. ' + NIC2_TEXTO + ' ' + METODOS,
                         'Mulheres acima de 65 anos com NIC 2 ou mais tratada | A cada 5 anos', f'{BRASIL} / {ACOG}', 'C'))
        orient.append(_quando_encerrar())
    elif rastreio_adequado == SIM or (resultado == NAO_DETECTADO and rastreio_adequado != NAO):
        orient.append(_quando_encerrar())
    elif rastreio_adequado == NAO:
        # Rastreio anterior declarado inadequado: MS 2025 (rec. 13) e ACOG 2026 não presumem que ela possa parar.
        recs.append(_rec(HPV, 'laboratorio',
                         'Rastreio anterior inadequado. MS 2025 (rec. 13): mulher com mais de 60 anos sem teste prévio faz um '
                         'teste de DNA-HPV; negativo, encerra. ACOG 2026: depois dos 65 anos, continuar até completar o rastreio '
                         'adequado. A decisão de rastrear é individual, pela saúde e pela expectativa de vida.',
                         'Mulheres acima de 65 anos sem rastreio anterior adequado | A cada 5 anos', f'{BRASIL} / {ACOG}', 'C'))
        orient.append(_quando_encerrar())
    else:
        # Depois dos 65 anos, sem NIC 2+ e sem rastreio declarado inadequado: não se rastreia (USPSTF 2018, D, com
        # rastreio anterior adequado; ACOG 2026). O teste só volta se o rastreio anterior não foi adequado.
        orient.append({
            'titulo': 'Colo do útero: sem rastreio depois dos 65 anos',
            'descricao': 'Depois dos 65 anos não sugerimos o teste de DNA-HPV. A exceção é o rastreio anterior inadequado '
                         '(resposta "Não" no formulário) ou NIC 2, NIC 3 ou adenocarcinoma in situ tratados nos últimos 25 '
                         'anos: nesses casos o rastreio continua.',
            'referencia': f'{USPSTF_COLO} / {ACOG} / {MS}'})
        orient.append(_quando_encerrar())
    return recs, orient
