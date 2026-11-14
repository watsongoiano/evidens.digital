"""Rastreamento do câncer do colo do útero: teste de DNA-HPV oncogênico e colposcopia.

Fontes (lidas na íntegra para estas regras)
- MS 2025: Diretrizes Brasileiras para o Rastreamento do Câncer do Colo do Útero, Parte I (Portaria
  Conjunta SAES/SECTICS nº 13, de 29/07/2025), recomendações 9-14, 18-25 e 34-40 e Figuras 1 e 2.
- SBOC 2026: Diretrizes de tratamentos oncológicos, Colo do útero (mesmos fluxogramas do MS).
- ACOG 2026: Committee Statement nº 28, Screening for Cervical Cancer (risco habitual).

Resumo aplicado
- Risco habitual: teste de DNA-HPV a cada 5 anos dos 25 aos 64 anos (MS, SBOC; ACOG: 30-65). Antes
  dos 25 não se rastreia (MS e SBOC, recomendação forte); a ACOG mantém citologia trienal dos 21 aos
  29, e isso aparece como orientação, sem pedido automático.
- HIV ou imunossupressão: a cada 3 anos, desde o início da atividade sexual, sem idade para encerrar.
- Resultado do último teste (campo opcional do formulário) decide o passo seguinte:
    HPV 16/18 ..................................... colposcopia
    outros tipos + citologia reflexa ASC-US ou mais  colposcopia
    outros tipos + citologia reflexa negativa ...... repetir o teste em 12 meses
    colposcopia sem doença ......................... repetir o teste em 12 meses
    imunossuprimida com qualquer tipo detectado .... colposcopia (não depende da citologia)
- A partir dos 65 anos (risco habitual, sem resultado positivo a seguir): não se pede; a orientação
  diz quando encerrar.
"""

HPV = 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular'
COLPOSCOPIA = 'Colposcopia (cérvice uterina e vagina)'

NAO_DETECTADO = 'nao_detectado'
HPV_16_18 = 'hpv_16_18'
OUTROS_CITOLOGIA_NEGATIVA = 'outros_citologia_negativa'
OUTROS_CITOLOGIA_ALTERADA = 'outros_citologia_alterada'
COLPOSCOPIA_NEGATIVA = 'colposcopia_negativa'
RESULTADOS = (NAO_DETECTADO, HPV_16_18, OUTROS_CITOLOGIA_NEGATIVA, OUTROS_CITOLOGIA_ALTERADA, COLPOSCOPIA_NEGATIVA)

MS = 'MS 2025 (DNA-HPV)'
SBOC = 'SBOC 2026'
ACOG = 'ACOG 2026'
BRASIL = f'{MS} / {SBOC}'

IDADE_INICIO = 25
IDADE_FIM = 64


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau='A'):
    return {'titulo': titulo, 'descricao': descricao, 'subtitulo': subtitulo, 'categoria': categoria,
            'prioridade': 'alta', 'referencia': referencia, 'grau_evidencia': grau}


def _colposcopia(motivo, descricao):
    return _rec(COLPOSCOPIA, 'imagem', descricao + ' Sem doença na colposcopia: repetir o teste de DNA-HPV em 12 meses.',
                f'{motivo} | Após teste de HPV positivo', BRASIL)


def recomendar(idade, imunossuprimida=False, resultado=None):
    """Devolve (recomendações, orientações) para uma mulher adulta. `resultado`: um de RESULTADOS ou None."""
    resultado = resultado if resultado in RESULTADOS else None
    recs, orient = [], []

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

    # Risco habitual. Teste feito antes dos 25 anos não é considerado (MS, recomendação 11).
    if idade < IDADE_INICIO:
        if idade >= 21:
            orient.append({
                'titulo': 'Colo do útero: rastreamento a partir dos 25 anos',
                'descricao': 'MS e SBOC não recomendam rastrear antes dos 25 anos, com teste de HPV ou citologia: nessa idade a '
                             'infecção costuma ser transitória, e um teste feito por engano não deve ser considerado. A ACOG mantém '
                             'citologia a cada 3 anos dos 21 aos 29 anos; se optar por ela, acrescente o exame pelo catálogo. Com '
                             'HIV ou imunossupressão, o rastreamento começa com o início da atividade sexual.',
                'referencia': f'{BRASIL} / {ACOG}'})
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
    elif idade <= IDADE_FIM:
        com_acog = idade >= 30
        descricao = ('Teste de DNA-HPV oncogênico com genotipagem a cada 5 anos, dos 25 aos 64 anos, sem citologia junto '
                     '(coteste não é recomendado). HPV 16/18: colposcopia. Outros tipos: citologia reflexa na mesma amostra. '
                     'Onde o teste não estiver disponível: citologia a cada 3 anos, após dois exames anuais negativos.')
        if idade > 60:
            descricao += ' Depois dos 60 anos, um teste negativo encerra o rastreamento.'
        recs.append(_rec(HPV, 'laboratorio', descricao, 'Mulheres 25-64 anos | A cada 5 anos',
                         f'{BRASIL} / {ACOG}' if com_acog else BRASIL, 'A' if com_acog else 'B'))
    else:
        orient.append({
            'titulo': 'Colo do útero: quando encerrar o rastreamento',
            'descricao': 'Encerrar se o último teste de DNA-HPV, feito depois dos 60 anos, foi negativo (ACOG: depois dos 65 anos, '
                         'com rastreamento prévio adequado). Quem nunca fez o teste faz um; negativo, encerra. Com NIC2, NIC3 ou '
                         'adenocarcinoma in situ tratados, manter o rastreamento por 25 anos após o tratamento. Não se aplica após '
                         'histerectomia total por doença benigna.',
            'referencia': f'{MS} / {ACOG}'})
    return recs, orient
