"""Rastreamento de câncer no risco habitual: mama, próstata, colorretal e pulmão.

As regras de idade e sexo saem daqui para o check-up (`src/routes/checkup_intelligent.py`); a história familiar e as
síndromes hereditárias ficam em `src/utils/condicoes.py`. Este módulo também monta, no fim, as orientações de
divergência entre diretrizes e o que acontece depois da idade de parada, olhando a lista já pronta.

Fontes (links em src/utils/reference_links.py)
- Mama: USPSTF 2024 (bienal 40-74, B; I a partir de 75). CBR/SBM/FEBRASGO 2023 (Radiol Bras 56:207): anual 40-74 e,
  a partir de 75, se a expectativa de vida for de 7 anos ou mais. MS, Nota Técnica 626/2025-CGCAN/DECAN/SAES/MS:
  rastreamento bienal de 50 a 74 anos; de 40 a 49 e acima de 74, por demanda, após orientação sobre riscos e benefícios.
- Próstata: USPSTF 2018 (JAMA 319:1901): decisão individual de 55 a 69 anos (C), não rastrear a partir de 70 (D).
  MS, Nota Técnica 9/2023-COSAH/CGACI/DGCI/SAPS/MS: não recomenda o rastreamento populacional; decisão compartilhada
  com quem pede o exame. SBU/SBOC/SBRT (posicionamento conjunto): discussão individual a partir de 50 anos com
  expectativa de vida acima de 10 anos; 40-50 anos com história familiar, etnia negra ou BRCA. AUA/SUO 2023: intervalo
  de 2 a 4 anos.
- Colorretal: USPSTF 2021 (A 50-75, B 45-49, C 76-85; vários métodos, entre eles colonoscopia a cada 10 anos e FIT
  anual). USMSTF 2022 (Gastroenterology 162:285): início aos 45, 76-85 individualizar, não rastrear depois dos 85.
  MS/INCA, 21/05/2026: FIT como exame de referência do SUS para assintomáticos de 50 a 75 anos.
- Pulmão: USPSTF 2021 (B) e consenso SBCT/SBPT/CBR 2024 (J Bras Pneumol 50:e20230233), idênticos: 50-80 anos, 20
  maços-ano ou mais, fumante atual ou que parou há menos de 15 anos. ACS 2023 (CA Cancer J Clin 74:50): os anos desde
  a cessação não são critério.
"""
from __future__ import annotations

MAMOGRAFIA = 'Mamografia Digital - Bilateral'
PSA = 'PSA total, soro'
COLONOSCOPIA = 'Colonoscopia de Rastreio com ou sem biópsia'
FIT = 'Sangue oculto nas fezes (FIT)'
LDCT = 'Tomografia computadorizada de tórax de baixa dose (LDCT)'

USPSTF_MAMA = 'USPSTF 2024'
CBR_MAMA = 'CBR/SBM/FEBRASGO 2023'
MS_MAMA = 'MS NT 626/2025'
USPSTF_PROSTATA = 'USPSTF 2018'
MS_PROSTATA = 'MS/INCA NT 9/2023'
SBU = 'SBU/SBOC/SBRT'
AUA = 'AUA/SUO 2023'
USPSTF_CCR = 'USPSTF 2021'
USMSTF_2022 = 'USMSTF 2022'
INCA_FIT = 'MS/INCA 2026'
USPSTF_PULMAO = 'USPSTF 2021'
CONSENSO_PULMAO = 'SBCT-SBPT-CBR 2024'
ACS_PULMAO = 'ACS 2023'

NAO_RECOMENDADO = 'nao_recomendado'
DADOS_INSUFICIENTES = 'dados_insuficientes'

SUBTITULO_MAMOGRAFIA = 'Mulheres 40-74 anos | Bienal'
SUBTITULO_COLONOSCOPIA = 'Adultos 45-75 anos | A cada 10 anos'


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau, prioridade='alta'):
    return {'titulo': titulo, 'descricao': descricao, 'subtitulo': subtitulo, 'categoria': categoria,
            'prioridade': prioridade, 'referencia': referencia, 'grau_evidencia': grau}


def mama_e_prostata(idade, sexo):
    """Mamografia (40-74, bienal) e PSA (55-69, decisão compartilhada)."""
    recs = []
    if sexo == 'feminino' and 40 <= idade <= 74:
        recs.append(_rec(MAMOGRAFIA, 'imagem', 'Mamografia bienal (40-74 anos)', SUBTITULO_MAMOGRAFIA, USPSTF_MAMA, 'B'))
    if sexo == 'masculino' and 55 <= idade <= 69:
        recs.append(_rec(
            PSA, 'laboratorio',
            'Decisão compartilhada: pedir só depois de conversar sobre benefícios (pequena redução da mortalidade por câncer '
            'de próstata) e danos (falso-positivo, biópsia, sobrediagnóstico, incontinência e disfunção erétil do tratamento). '
            'Não pedir para quem, depois da conversa, não manifestar preferência pelo rastreamento. Intervalo de 2 a 4 anos.',
            'Homens 55-69 anos, decisão compartilhada | A cada 2-4 anos', USPSTF_PROSTATA + ' / ' + AUA, 'C', 'media'))
    return recs


def colorretal(idade):
    """Colonoscopia a cada 10 anos ou FIT anual, dos 45 aos 75 anos: o médico escolhe um dos dois."""
    if not 45 <= idade <= 75:
        return []
    return [
        _rec(COLONOSCOPIA, 'imagem',
             'Colonoscopia a cada 10 anos (45-75 anos). Alternativa: pesquisa de sangue oculto nas fezes por método '
             'imunoquímico (FIT) anual. Escolha um dos dois métodos com o paciente e retire o outro.',
             SUBTITULO_COLONOSCOPIA, USPSTF_CCR, 'B'),
        _rec(FIT, 'laboratorio',
             'Pesquisa de sangue oculto nas fezes por método imunoquímico (FIT), anual, como alternativa à colonoscopia: '
             'escolha um dos dois métodos e retire o outro. Positivo: colonoscopia. É o exame de rastreio do SUS para '
             'assintomáticos de 50 a 75 anos.',
             'Adultos 45-75 anos, alternativa à colonoscopia | Anual', USPSTF_CCR + ' / ' + INCA_FIT, 'B'),
    ]


def pulmao(idade, tabagismo, macos_ano, anos_parou_fumar, gestante=False):
    """TC de baixa dose. Devolve `(recs, nao_incluidas, orientacoes)`.

    Dado ausente não vira valor: sem maços-ano (ou, no ex-fumante, sem os anos desde que parou) o item aparece como
    dados insuficientes, em vez de sumir ou de entrar.
    """
    recs, nao_incluidas, orient = [], [], []
    if tabagismo not in ('atual', 'ex') or not 50 <= idade <= 80:
        return recs, nao_incluidas, orient
    ref = USPSTF_PULMAO + ' / ' + CONSENSO_PULMAO
    criterio = '50-80 anos, 20 maços-ano ou mais, fumante atual ou que parou há menos de 15 anos'
    if macos_ano is None:
        if not gestante:
            nao_incluidas.append({'titulo': LDCT, 'categoria': 'imagem', 'estado': DADOS_INSUFICIENTES, 'referencia': ref,
                                  'motivo': f'Câncer de pulmão: informe os maços-ano para avaliar a TC de baixa dose ({criterio}).'})
        return recs, nao_incluidas, orient
    if macos_ano < 20:
        return recs, nao_incluidas, orient
    if tabagismo == 'ex' and anos_parou_fumar is None:
        if not gestante:
            nao_incluidas.append({'titulo': LDCT, 'categoria': 'imagem', 'estado': DADOS_INSUFICIENTES, 'referencia': ref,
                                  'motivo': 'Câncer de pulmão: informe há quantos anos parou de fumar para avaliar a TC de '
                                            f'baixa dose ({criterio}).'})
        return recs, nao_incluidas, orient
    if tabagismo == 'atual' or anos_parou_fumar < 15:
        rec = _rec(LDCT, 'imagem',
                   'Rastreamento anual de câncer de pulmão. Indicado para adultos 50-80 anos com história de tabagismo de 20 '
                   'maços-ano e que atualmente fumam ou pararam nos últimos 15 anos. Descontinuar se não fumou por 15 anos ou '
                   'desenvolveu problema de saúde que limita substancialmente expectativa de vida.',
                   'Adultos 50-80 anos com ≥20 maços-ano | Anual', ref, 'B')
        rec['link'] = 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/lung-cancer-screening'
        recs.append(rec)
    else:
        orient.append({
            'titulo': 'Câncer de pulmão: as diretrizes divergem para quem parou de fumar há 15 anos ou mais',
            'descricao': 'O motor seguiu o USPSTF 2021 e o consenso brasileiro (SBCT/SBPT/CBR 2024), que não indicam a TC de '
                         'baixa dose depois de 15 anos sem fumar. A ACS 2023 não usa o tempo desde a cessação e incluiria este '
                         'paciente (50-80 anos, 20 maços-ano ou mais), com decisão compartilhada.',
            'referencia': ref + ' / ' + ACS_PULMAO})
    return recs, nao_incluidas, orient


def _achar(recs, titulo):
    return next((r for r in recs if (r.get('titulo') or '').strip().lower() == titulo.lower()), None)


def finalizar(recs, idade, sexo, familia):
    """Depois das listas (história familiar, síndromes, comorbidades): tira o FIT quando a colonoscopia passou a ser de
    risco aumentado e devolve `(orientacoes, nao_incluidas)` com as divergências entre diretrizes e o que vale depois
    da idade de parada. Altera `recs` no lugar."""
    fam = set(familia)
    orient, nao_incluidas = [], []

    # ---- Colorretal ----
    colono = _achar(recs, COLONOSCOPIA)
    fit = _achar(recs, FIT)
    risco_aumentado = colono is not None and (colono.get('subtitulo') or '') != SUBTITULO_COLONOSCOPIA
    if fit is not None and risco_aumentado:
        # História familiar, síndrome ou doença inflamatória intestinal: só a colonoscopia (USMSTF).
        recs.remove(fit)
        fit = None
    if fit is not None:
        orient.append({
            'titulo': 'Câncer colorretal: as diretrizes divergem na idade de início e no método',
            'descricao': 'O motor seguiu o USPSTF 2021 e a USMSTF 2022: rastreio a partir dos 45 anos, com colonoscopia a cada '
                         '10 anos ou FIT anual (o médico escolhe um dos dois). O MS/INCA (2026) adotou o FIT como exame do SUS '
                         'para assintomáticos de 50 a 75 anos, com colonoscopia se positivo, e não rastreia antes dos 50.',
            'referencia': f'{USPSTF_CCR} / {USMSTF_2022} / {INCA_FIT}'})
    if 76 <= idade <= 85:
        orient.append({
            'titulo': 'Rastreio colorretal de 76 a 85 anos: decisão individual',
            'descricao': 'O rastreio de rotina vai até os 75 anos, também na história familiar. De 76 a 85 anos, decidir pela '
                         'saúde, pela expectativa de vida e pelos rastreios anteriores: quem nunca rastreou ou tem expectativa de '
                         'vida de 10 anos ou mais pode se beneficiar; quem está em dia, com exames negativos, pode encerrar.',
            'referencia': f'{USPSTF_CCR} / {USMSTF_2022}'})
    elif idade >= 86:
        orient.append({
            'titulo': 'Rastreio colorretal depois dos 85 anos: não recomendado',
            'descricao': 'Depois dos 85 anos o rastreio não é recomendado; colonoscopia só para investigar sintomas.',
            'referencia': f'{USPSTF_CCR} / {USMSTF_2022}'})

    # ---- Mama ----
    if sexo == 'feminino':
        mamo = _achar(recs, MAMOGRAFIA)
        if mamo is not None and (mamo.get('subtitulo') or '') == SUBTITULO_MAMOGRAFIA:
            orient.append({
                'titulo': 'Mamografia: as diretrizes divergem no intervalo e na idade de início',
                'descricao': 'O motor seguiu o USPSTF 2024: mamografia bienal dos 40 aos 74 anos. CBR/SBM/FEBRASGO 2023: anual '
                             'dos 40 aos 74. MS (Nota Técnica 626/2025): rastreamento bienal dos 50 aos 74; dos 40 aos 49, por '
                             'demanda, após conversa sobre riscos e benefícios.',
                'referencia': f'{USPSTF_MAMA} / {CBR_MAMA} / {MS_MAMA}'})
        if idade >= 75:
            orient.append({
                'titulo': 'Mamografia a partir de 75 anos: decisão individual',
                'descricao': 'O rastreio de rotina vai até os 74 anos, também na história familiar. A partir de 75: o USPSTF '
                             'considera a evidência insuficiente; CBR/SBM/FEBRASGO mantêm a mamografia se a mulher tiver boa saúde '
                             'e expectativa de vida de 7 anos ou mais; o MS faz por demanda, após conversa sobre riscos e benefícios.',
                'referencia': f'{USPSTF_MAMA} / {CBR_MAMA} / {MS_MAMA}'})

    # ---- Próstata ----
    if sexo == 'masculino':
        risco_prostata = bool({'cancer_prostata', 'brca'} & fam)
        if 50 <= idade <= 69 or (40 <= idade < 50 and risco_prostata):
            orient.append({
                'titulo': 'Câncer de próstata: as diretrizes divergem',
                'descricao': 'O motor seguiu o USPSTF 2018: PSA por decisão compartilhada dos 55 aos 69 anos e nenhum rastreio a '
                             'partir de 70. O MS/INCA (Nota Técnica 9/2023) não recomenda o rastreamento populacional: só decisão '
                             'compartilhada com quem pede o exame. SBU, SBOC e SBRT propõem discussão individual a partir de 50 '
                             'anos com expectativa de vida acima de 10 anos, e de 40 a 50 anos com história familiar, etnia negra '
                             'ou mutação de BRCA.',
                'referencia': f'{USPSTF_PROSTATA} / {MS_PROSTATA} / {SBU}'})
        if idade >= 70 and _achar(recs, PSA) is None:
            motivo = ('USPSTF 2018 (grau D): não rastrear câncer de próstata a partir de 70 anos; os danos do rastreio superam '
                      'os benefícios. PSA só para investigar sintomas.')
            if risco_prostata:
                motivo += (' Com BRCA ou câncer de próstata na família, a decisão pode ser individualizada pela expectativa de '
                           'vida e pela saúde (NCCN).')
            nao_incluidas.append({'titulo': PSA, 'categoria': 'laboratorio', 'estado': NAO_RECOMENDADO, 'motivo': motivo,
                                  'referencia': USPSTF_PROSTATA + (' / NCCN 2025' if risco_prostata else '')})
    return orient, nao_incluidas
