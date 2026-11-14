"""Rotina de exames do pré-natal de baixo risco, conforme a idade gestacional.

Fontes
- Hospital Israelita Albert Einstein. Guia do Episódio de Cuidado — Pré-Natal de Baixo
  Risco, v.3 (CPTW53.3, revisão 01/08/2024).
- Ministério da Saúde. Atenção ao pré-natal de baixo risco (Cadernos de Atenção Básica 32),
  2012; Protocolos da Atenção Básica — Saúde das Mulheres, 2016.
- Williams Obstetrics, 26ª ed., Tabela 10-1 (componentes da rotina de pré-natal). É o guia da rotina
  laboratorial: todo item marcado com ponto na tabela é pedido na coluna correspondente.
    1ª consulta: hemoglobina/hematócrito, tipagem ABO e Rh, pesquisa de anticorpos (Coombs indireto),
                 Papanicolaou, proteína urinária (urina tipo I), urocultura, rubéola, sífilis, clamídia,
                 hepatite B e HIV.
    24-28 semanas: hemoglobina/hematócrito, teste de tolerância à glicose e, na Rh negativo, nova
                 pesquisa de anticorpos com 28 semanas (A).
    29-41 semanas: reteste de sífilis, clamídia, gonococo, hepatite B e HIV (C, D) e cultura de
                 estreptococo do grupo B com 35-37 semanas (E).
  As letras B (oferecer rastreio de aneuploidias, tubo neural e fibrose cística) e F (tuberculose em
  alto risco) não geram pedido automático.
- USPSTF: clamídia/gonorreia (2021), ácido acetilsalicílico para pré-eclâmpsia (2021).
- ACOG Practice Bulletin 222 (2020) e Committee Opinion 797 (2020, estreptococo do grupo B).

O módulo devolve, para a idade gestacional informada, os exames da janela atual e os da
próxima janela (para já deixar pedido), mais os da primeira consulta quando for o caso.
Também diz quais itens do check-up geral se adiam na gestação.
"""
from __future__ import annotations

REF = 'Einstein Pré-Natal v.3 (2024) / MS 2012-2016 / Williams 26e'
SIM_NAO = {'sim': True, 'nao': False, 'não': False}
CONDICOES = {
    'gemelar': 'Gestação gemelar',
    'pe_previa': 'Pré-eclâmpsia em gestação anterior',
    'dmg_previo': 'Diabetes gestacional em gestação anterior',
    'dmg_atual': 'Diabetes gestacional já diagnosticado nesta gestação',
    'prematuro_previo': 'Parto prematuro anterior',
}

# Itens do check-up geral que não se aplicam ou se adiam durante a gestação.
ADIAR_NA_GESTACAO = {
    'Colesterol total e frações, soro': 'Lípides sobem fisiologicamente na gestação; rastrear após o puerpério.',
    'Lipoproteína(a) - Lp(a), soro': 'Dosagem única na vida; pode ser feita após a gestação.',
    'TOTG-75g (Teste Oral de Tolerância à Glicose), soro': 'Substituído pelo TOTG-75g gestacional de 24-28 semanas.',
    'Hemoglobina glicada (HbA1c), soro': 'Menos confiável na gestação; usar glicemia de jejum e TOTG (HbA1c só em diabética ou com fator de risco antes de 15 semanas).',
    'PSA total, soro': 'Não se aplica.',
    'Glicose, soro': 'Substituída pela glicemia de jejum da primeira consulta do pré-natal.',
    'Mamografia Digital - Bilateral': 'Mamografia de rastreio adiada para após a gestação e a lactação (investigar se houver achado clínico).',
    'Densitometria óssea (DEXA)': 'Rastreio de osteoporose não se faz na gestação.',
    'Colonoscopia de Rastreio com ou sem biópsia': 'Colonoscopia de rastreio adiada para após a gestação (fazer na gestação só se houver indicação diagnóstica).',
    'Tomografia computadorizada de tórax de baixa dose (LDCT)': 'Rastreio com radiação ionizante adiado para após a gestação.',
}


class GestacaoInvalida(ValueError):
    def __init__(self, erros):
        super().__init__('; '.join(e['mensagem'] for e in erros))
        self.erros = erros


def normalizar(entrada):
    """Lê os subcampos da gestação. Ausente fica ``None`` (não é presumido)."""
    erros = []
    ig = entrada.get('idade_gestacional')
    if ig in (None, ''):
        erros.append({'campo': 'idade_gestacional',
                      'mensagem': 'Gestante: informe a idade gestacional em semanas (define quais exames são para agora).'})
        ig = None
    else:
        try:
            ig = float(str(ig).replace(',', '.'))
        except ValueError:
            ig = -1
        if not 0 <= ig <= 42:
            erros.append({'campo': 'idade_gestacional', 'mensagem': 'Idade gestacional deve estar entre 0 e 42 semanas.'})
            ig = None
    primeira = SIM_NAO.get(str(entrada.get('primeira_consulta') or '').lower())
    if primeira is None:
        erros.append({'campo': 'primeira_consulta', 'mensagem': 'Gestante: diga se é a primeira consulta de pré-natal.'})
    rh = str(entrada.get('fator_rh') or 'desconhecido').lower()
    if rh not in ('positivo', 'negativo', 'desconhecido'):
        erros.append({'campo': 'fator_rh', 'mensagem': 'Fator Rh: valor inválido.'})
        rh = 'desconhecido'
    toxo = str(entrada.get('toxoplasmose') or 'desconhecido').lower()
    if toxo not in ('suscetivel', 'imune', 'desconhecido'):
        erros.append({'campo': 'toxoplasmose', 'mensagem': 'Toxoplasmose: valor inválido.'})
        toxo = 'desconhecido'
    totg = str(entrada.get('totg_feito') or 'desconhecido').lower()
    if totg not in ('sim', 'nao', 'não', 'desconhecido'):
        erros.append({'campo': 'totg_feito', 'mensagem': 'TOTG-75g já realizado: valor inválido.'})
    condicoes = entrada.get('gestacao_condicoes') or []
    if isinstance(condicoes, str):
        condicoes = [condicoes]
    desconhecidas = [c for c in condicoes if c not in CONDICOES]
    if desconhecidas:
        erros.append({'campo': 'gestacao_condicoes', 'mensagem': 'Condição da gestação inválida.'})
    if erros:
        raise GestacaoInvalida(erros)
    return {'ig': ig, 'primeira_consulta': primeira, 'rh': rh, 'toxo': toxo, 'totg_feito': totg == 'sim',
            'condicoes': sorted(set(condicoes))}


def _rec(titulo, categoria, descricao, subtitulo, prioridade='alta', grau='A', referencia=REF):
    return {'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'prioridade': prioridade, 'referencia': referencia, 'grau_evidencia': grau, 'gestacao': True}


# Janelas (semana inicial, semana final EXCLUSIVA, nome): 20-24 semanas vale até 24+6 → (20, 25).
def _janelas(g, idade, hipertensa, diabetica, hiv=False):
    toxo_repetir = g['toxo'] != 'imune'
    rh_neg = g['rh'] == 'negativo'
    colo_inicio = 16 if 'prematuro_previo' in g['condicoes'] else 20
    janelas = [
        (5, 11, '7-9 semanas', [
            _rec('Ultrassonografia obstétrica transvaginal', 'imagem',
                 'Datação da gestação, número e localização dos embriões, viabilidade.', 'Pré-natal | 7-9 semanas'),
        ]),
        (11, 14, '11-13+6 semanas', [
            _rec('Ultrassonografia morfológica de 1º trimestre (translucência nucal)', 'imagem',
                 'Datação, número de fetos, rastreamento de aneuploidias e anomalias; avaliação de risco de pré-eclâmpsia (Doppler de artérias uterinas). Rastreio bioquímico ou DNA fetal livre opcionais.',
                 'Pré-natal | 11-13+6 semanas'),
        ]),
        (20, 25, '20-24 semanas', [
            _rec('Ultrassonografia morfológica de 2º trimestre', 'imagem',
                 'Rastreamento de anomalias fetais.', 'Pré-natal | 20-24 semanas'),
        ] + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
                   'Repetir a cada trimestre enquanto suscetível (IgG negativa).', 'Pré-natal | Suscetível: a cada trimestre')]
             if toxo_repetir else [])),
        # Colo uterino tem janela própria: com parto prematuro anterior começa em 16 semanas.
        (colo_inicio, 25, f'{colo_inicio}-24 semanas', [
            _rec('Ultrassonografia transvaginal para medida do colo uterino', 'imagem',
                 'Rastreio de colo curto (≤ 25 mm). Com parto prematuro anterior, medir a partir de 16 semanas.',
                 f'Pré-natal | {colo_inicio}-24 semanas', prioridade='media', grau='B'),
        ]),
        (24, 29, '24-28 semanas', [
            _rec('Hemograma completo', 'laboratorio', 'Hemoglobina/hematócrito de 24-28 semanas (rastreio de anemia).',
                 'Pré-natal | 24-28 semanas'),
        ] + ([_rec('Coombs indireto, soro', 'laboratorio',
                                         'Gestante Rh negativo: repetir com 28 semanas; se negativo, imunoglobulina anti-D com 28 semanas e até 72 h após o parto (se RN Rh positivo).',
                                         'Pré-natal | Rh negativo: 28 semanas')] if rh_neg else [])),
        (28, 37, '28-36 semanas', [
            _rec('Hemograma completo', 'laboratorio', 'Rastreio de anemia no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
            _rec('Urocultura com antibiograma', 'laboratorio', 'Bacteriúria assintomática.', 'Pré-natal | 28-36 semanas'),
            _rec('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
        ] + ([] if hiv else [
            _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
        ]) + [
            _rec('HBsAg, soro', 'laboratorio', 'Repetir no 3º trimestre (Einstein/MS).', 'Pré-natal | 28-36 semanas', prioridade='media'),
            _rec('Ultrassonografia obstétrica com Doppler', 'imagem', 'Crescimento e vitalidade fetal (protocolo Einstein).',
                 'Pré-natal | 28-36 semanas', prioridade='media', grau='B'),
        ] + ([_rec('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
                   'Reteste no 3º trimestre para menores de 25 anos ou com fator de risco.',
                   'Pré-natal | 28-36 semanas | < 25 anos', grau='B', referencia='Williams 26e / USPSTF 2021')]
             if idade < 25 else []) + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
                   'Repetir a cada trimestre enquanto suscetível (IgG negativa).', 'Pré-natal | Suscetível: a cada trimestre')]
             if toxo_repetir else [])),
        (35, 38, '35-37 semanas', [
            _rec('Cultura para estreptococo do grupo B (swab vaginal e retal)', 'laboratorio',
                 'Define antibioticoprofilaxia intraparto. Einstein: 35-37 semanas; ACOG: 36+0 a 37+6 semanas.',
                 'Pré-natal | 35-37 semanas'),
        ]),
    ]
    return janelas


REF_DMG = 'Consenso brasileiro de DMG 2017 / ' + REF


def _totg(g, diabetica):
    """TOTG-75g: de 24 a 28 semanas; depois disso, pedido enquanto não constar como já realizado.

    Devolve ``(inicio, item)`` ou ``None``. Quem começa o pré-natal depois de 28 semanas, ou não fez o
    exame na janela, faz o TOTG de imediato (OPAS/MS/FEBRASGO/SBD 2017).
    """
    if diabetica or g.get('totg_feito') or 'dmg_atual' in g['condicoes']:  # já diagnosticada: não se repete o TOTG
        return None
    atrasado = g['ig'] is not None and g['ig'] >= 29
    item = _rec('TOTG-75g gestacional (jejum, 1 h e 2 h), soro', 'laboratorio',
                'Rastreio de diabetes gestacional para todas sem diagnóstico prévio. Critérios IADPSG/OMS: jejum ≥ 92, '
                '1 h ≥ 180 ou 2 h ≥ 153 mg/dL (um valor basta).'
                + (' Fora da janela de 24-28 semanas: se ainda não foi feito, fazer de imediato.' if atrasado else ''),
                'Pré-natal | Não realizado com 24-28 semanas: fazer agora' if atrasado else 'Pré-natal | 24-28 semanas',
                referencia=REF_DMG if atrasado else REF)
    item['quando_pdf'] = ('TOTG-75g ainda não realizado nesta gestação: fazer agora.' if atrasado
                          else 'Realizar com 24-28 semanas de gestação.')
    return 24, item


# Exames gerais que medem o mesmo que um exame do pré-natal: na gestação fica só o do pré-natal.
EQUIVALENTES = {
    'hiv 1/2 (anticorpos e antígeno p24), soro': ['anti-hiv 1 e 2, soro'],
    'anti-hcv igg, soro': ['anticorpos anti-hcv, soro'],
    'hbsag, soro': ['antígeno hbs, soro'],
    'sífilis: teste treponêmico ou vdrl, soro': ['vdrl, soro'],
    'hemograma completo': ['hemograma completo com plaquetas', 'hemograma completo, sangue total'],
    'eas - elementos anormais e sedimentoscopia': ['eas - elementos anormais e sedimentoscopia, urina'],
    'tgo e tgp, soro': ['aspartato aminotransferase, soro', 'alanina aminotransferase, soro'],
}


def sem_equivalentes(recomendacoes, exames_pn):
    """Tira do check-up geral o exame que o pré-natal já pede com outro nome."""
    fora = {t for r in exames_pn for t in EQUIVALENTES.get(r['titulo'].lower(), [])}
    return [r for r in recomendacoes if (r.get('titulo') or '').strip().lower() not in fora]


def _primeira_consulta(g, idade, hipertensa, diabetica, hiv=False):
    recs = [
        _rec('Hemograma completo', 'laboratorio', 'Rastreio de anemia.', 'Pré-natal | 1ª consulta'),
        _rec('Glicemia de jejum, soro', 'laboratorio',
             'Diabetes prévio se ≥ 126 mg/dL; diabetes gestacional se 92-125 mg/dL (IADPSG).', 'Pré-natal | 1ª consulta'),
        _rec('EAS - Elementos Anormais e Sedimentoscopia', 'laboratorio', 'Urina tipo I.', 'Pré-natal | 1ª consulta'),
        _rec('Urocultura com antibiograma', 'laboratorio', 'Bacteriúria assintomática.', 'Pré-natal | 1ª consulta'),
    ] + ([] if hiv else [
        _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta'),
    ]) + [
        _rec('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta'),
        _rec('HBsAg, soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta'),
        _rec('Anti-HCV IgG, soro', 'laboratorio', 'Rastreio universal na gestação.', 'Pré-natal | 1ª consulta'),
        _rec('Rubéola IgG, soro', 'laboratorio', 'Suscetível: vacinar no puerpério (vacina de vírus vivo).',
             'Pré-natal | 1ª consulta', prioridade='media', grau='B'),
        _rec('Citomegalovírus IgG e IgM, soro', 'laboratorio',
             'Protocolo Einstein; não é rastreio universal no MS nem na ACOG.', 'Pré-natal | 1ª consulta',
             prioridade='baixa', grau='C'),
        _rec('Parasitológico de fezes', 'laboratorio', 'Protocolo Einstein/MS.', 'Pré-natal | 1ª consulta',
             prioridade='baixa', grau='C'),
    ]
    if g['rh'] != 'positivo':
        recs.append(_rec('Tipagem sanguínea ABO e fator Rh', 'laboratorio', 'Risco de aloimunização Rh.', 'Pré-natal | 1ª consulta'))
    # Williams, Tab. 10-1: pesquisa de anticorpos irregulares na 1ª consulta para todas (não só Rh negativo)
    recs.append(_rec('Coombs indireto, soro', 'laboratorio',
                     'Pesquisa de anticorpos irregulares na primeira consulta, para todas as gestantes. Na Rh negativo, '
                     'repetir com 28 semanas.', 'Pré-natal | 1ª consulta'))
    if g['toxo'] != 'imune':
        recs.append(_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio', 'Suscetível: repetir a cada trimestre.', 'Pré-natal | 1ª consulta'))
    recs.append(_rec('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
                     'Clamídia: rastreio na primeira consulta para todas. Gonococo: para menores de 25 anos ou com fator de '
                     'risco. Repetir no 3º trimestre se menor de 25 anos ou com risco.',
                     'Pré-natal | 1ª consulta', grau='B', referencia='Williams 26e / USPSTF 2021'))
    # Papanicolaou (ponto da 1ª consulta na Tab. 10-1): vem do rastreio de colo do check-up geral, que na
    # gestação segue na lista (citologia de 21 a 29 anos; teste de HPV a partir de 30).
    if not diabetica and ('dmg_previo' in g['condicoes']):
        recs.append(_rec('Hemoglobina glicada (HbA1c), soro', 'laboratorio',
                         'Fator de risco para diabetes: rastrear diabetes não diagnosticado antes de 15 semanas.',
                         'Pré-natal | 1ª consulta | Fator de risco', grau='B', referencia='ADA 2024'))
    return recs


def _risco_pre_eclampsia(g, hipertensa, diabetica):
    alto = hipertensa or diabetica or 'pe_previa' in g['condicoes'] or 'gemelar' in g['condicoes']
    if not alto:
        return []
    texto = ('Alto risco de pré-eclâmpsia: AAS 100-150 mg à noite de 12-16 até 36 semanas '
             '(USPSTF 2021; ACOG). Exames basais para comparação futura.')
    return [
        _rec('Relação proteína/creatinina, urina', 'laboratorio', texto, 'Pré-natal | Alto risco de pré-eclâmpsia | Basal',
             grau='B', referencia='ACOG PB 222 (2020) / USPSTF 2021'),
        _rec('TGO e TGP, soro', 'laboratorio', 'Basal para pré-eclâmpsia/HELLP.', 'Pré-natal | Alto risco de pré-eclâmpsia | Basal',
             prioridade='media', grau='B', referencia='ACOG PB 222 (2020)'),
        _rec('Creatinina, soro', 'laboratorio', 'Basal para pré-eclâmpsia.', 'Pré-natal | Alto risco de pré-eclâmpsia | Basal',
             prioridade='media', grau='B', referencia='ACOG PB 222 (2020)'),
    ]


def exames(g, idade, hipertensa=False, diabetica=False, hiv=False):
    """Exames do pré-natal para fazer AGORA (1ª consulta + janela atual + basais de risco)."""
    return programacao(g, idade, hipertensa, diabetica, hiv)[0]


INICIAIS = ('tipagem ABO/Rh, Coombs indireto, hemograma, glicemia de jejum, urina tipo I e urocultura, HIV, '
            'sífilis, HBsAg, anti-HCV, clamídia, toxoplasmose, rubéola e citomegalovírus')


def programacao(g, idade, hipertensa=False, diabetica=False, hiv=False):
    """Devolve ``(agora, proximas)``.

    ``agora`` vai para a lista e para os PDFs. ``proximas`` são os exames das janelas
    seguintes e os avisos de etapas anteriores: aparecem só como informação, nunca no PDF.
    """
    agora, proximas = [], []
    ig = g['ig']
    if g['primeira_consulta']:
        agora += [{**r, 'quando_pdf': 'Primeira consulta de pré-natal.'}
                  for r in _primeira_consulta(g, idade, hipertensa, diabetica, hiv)]
    else:
        proximas.append({'titulo': 'Exames iniciais do pré-natal (1ª consulta)', 'categoria': 'laboratorio',
                         'estado': 'etapa_anterior', 'referencia': REF, 'semana': -1,
                         'motivo': f'Considerados já feitos: {INICIAIS}. Se algum ficou faltando, responda "Sim" em '
                                   '"Primeira consulta de pré-natal?" ou acrescente o exame ao gerar o PDF.'})
    janelas = _janelas(g, idade, hipertensa, diabetica, hiv)
    com_imagem = False
    if ig is not None:
        for inicio, fim, nome, itens in janelas:
            if inicio <= ig < fim:
                agora += [{**r, 'quando_pdf': f'Realizar com {nome} de gestação.'} for r in itens]
                com_imagem = com_imagem or any(r['categoria'] == 'imagem' and 'colo' not in r['titulo'] for r in itens)
            elif inicio > ig:
                proximas += [{'titulo': r['titulo'], 'categoria': r['categoria'], 'estado': 'proxima_janela',
                              'motivo': f'Pedir com {nome} de gestação. {r["descricao"]}',
                              'referencia': r['referencia'], 'semana': inicio} for r in itens]
    totg = _totg(g, diabetica)
    if totg and ig is not None:
        inicio, item = totg
        if ig >= inicio:
            agora.append(item)
        else:
            proximas.append({'titulo': item['titulo'], 'categoria': item['categoria'], 'estado': 'proxima_janela',
                             'motivo': f'Pedir com 24-28 semanas de gestação. {item["descricao"]}',
                             'referencia': item['referencia'], 'semana': inicio})
    elif g.get('totg_feito') and ig is not None and ig >= 24:
        proximas.append({'titulo': 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro', 'categoria': 'laboratorio',
                         'estado': 'etapa_anterior', 'referencia': REF, 'semana': -1,
                         'motivo': 'Informado como já realizado nesta gestação.'})
    # Início tardio do pré-natal fora das janelas de ultrassonografia: uma ultrassonografia obstétrica agora.
    if g['primeira_consulta'] and ig is not None and ig >= 14 and not com_imagem:
        agora.append({**_rec('Ultrassonografia obstétrica', 'imagem',
                             'Início do pré-natal fora das janelas de ultrassonografia: datação, vitalidade e avaliação fetal.',
                             'Pré-natal | 1ª consulta após 14 semanas', grau='B'),
                      'quando_pdf': 'Primeira consulta de pré-natal.'})
    agora += [{**r, 'quando_pdf': 'Basal: alto risco de pré-eclâmpsia.'}
              for r in _risco_pre_eclampsia(g, hipertensa, diabetica)]
    vistos, unicos = set(), []
    for r in agora:
        if r['titulo'] not in vistos:
            vistos.add(r['titulo'])
            unicos.append(r)
    ja = set(vistos)
    prox_unicas = []
    for r in sorted(proximas, key=lambda x: x['semana']):
        chave = (r['titulo'], r['semana'])
        if chave not in ja:
            ja.add(chave)
            prox_unicas.append(r)
    return unicos, prox_unicas


_ADIAR = {k.lower(): v for k, v in ADIAR_NA_GESTACAO.items()}


def adiar(recomendacoes, diabetica=False):
    """Separa os itens do check-up geral que se adiam na gestação."""
    mantidas, adiadas = [], []
    for r in recomendacoes:
        titulo = (r.get('titulo') or '').strip().lower()
        motivo = _ADIAR.get(titulo)
        if diabetica and titulo.startswith('hemoglobina glicada'):
            motivo = None
        if motivo and not r.get('gestacao'):
            adiadas.append({'titulo': r['titulo'], 'categoria': r.get('categoria'), 'estado': 'adiado_gestacao',
                            'motivo': motivo, 'referencia': REF})
        else:
            mantidas.append(r)
    return mantidas, adiadas


# Vacinas da gestação que têm idade gestacional mínima (MS/PNI e SBIm 2026/2027).
VACINAS_COM_JANELA = [
    ('dtpa', 20, 'dTpa a cada gestação a partir de 20 semanas (MS/PNI; SBIm).'),
    ('abrysvo', 28, 'VSR (Abrysvo®) a partir de 28 semanas (SBIm/PNI; ACOG: 32-36 semanas).'),
]


def vacinas_fora_da_janela(recomendacoes, ig):
    """Tira da lista (e dos PDFs) as vacinas da gestante cuja janela ainda não abriu."""
    if ig is None:
        return recomendacoes, []
    mantidas, proximas = [], []
    for r in recomendacoes:
        titulo = (r.get('titulo') or '').lower()
        regra = next(((sem, texto) for termo, sem, texto in VACINAS_COM_JANELA
                      if r.get('categoria') == 'vacina' and termo in titulo and ig < sem), None)
        if regra:
            proximas.append({'titulo': r['titulo'], 'categoria': 'vacina', 'estado': 'proxima_janela',
                             'motivo': regra[1], 'referencia': r.get('referencia', ''), 'semana': regra[0]})
        else:
            mantidas.append(r)
    return mantidas, proximas
