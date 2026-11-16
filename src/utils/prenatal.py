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
- USPSTF: clamídia/gonorreia (2021), ácido acetilsalicílico para pré-eclâmpsia (2021; fatores de alto e de
  risco moderado), ácido fólico (2023).
- ACOG Practice Bulletin 222 (2020; hipertensão gestacional e pré-eclâmpsia: PA ≥ 140/90 em 2 medidas com 4 h
  de intervalo depois de 20 semanas; faixa grave ≥ 160/110 confirmada em minutos; investigação com hemograma e
  plaquetas, creatinina, LDH, TGO/TGP e proteinúria; AAS de 12 a 28 semanas, até o parto), Committee Opinion 767
  (2019; tratar a hipertensão grave em 30-60 minutos) e Committee Opinion 797 (2020; estreptococo do grupo B com
  36+0 a 37+6 semanas).
- FEBRASGO Position Statement nº 1/2023 (pré-eclâmpsia: AAS ≥ 100 mg, idealmente 150 mg, antes de 16 semanas e até
  36 semanas; rastreio combinado de 11-14 semanas com corte de 1:100) e nº 10/2022 (FEBRASGO/SBEM: TSH universal
  no início do pré-natal; sem referência local, TSH ≤ 4,0 mUI/L normal; acima disso, T4 livre).
- FEBRASGO Position Statement nº 10/2025 (HIV na gestação: carga viral na 1ª consulta, 2-4 semanas após iniciar ou
  trocar a TARV e a partir de 34 semanas; CD4 na 1ª consulta e com 34 semanas em quem já está em TARV com carga
  viral indetectável).
- ADA, Standards of Care 2026, seção 15 (TOTG 75 g com 4-12 semanas pós-parto após DMG; fundo de olho no DM
  pré-gestacional no 1º trimestre, a cada trimestre e até 1 ano pós-parto).
- MS, Manual de Gestação de Alto Risco (2022), e PCDT de Transmissão Vertical de HIV, Sífilis e Hepatites (2022).

O módulo devolve, para a idade gestacional informada, os exames da janela atual e os da
próxima janela (para já deixar pedido), mais os da primeira consulta quando for o caso.
Também diz quais itens do check-up geral se adiam na gestação e monta as orientações da gestação
(hipertensão, AAS, alto risco, suplementos e divergências entre diretrizes).
"""
from __future__ import annotations

REF = 'Einstein Pré-Natal v.3 (2024) / MS 2012-2016 / Williams 26e'
REF_SOROLOGIA = REF + ' / PCDT TV MS 2022'
EINSTEIN = 'Einstein Pré-Natal v.3 (2024)'
ACOG_PE = 'ACOG PB 222 (2020)'
FEBRASGO_PE = 'FEBRASGO 2023 (pré-eclâmpsia)'
USPSTF_AAS = 'USPSTF 2021 (AAS na pré-eclâmpsia)'
CONITEC_AAS = 'Conitec 2026 (AAS na pré-eclâmpsia)'
MS_ALTO_RISCO = 'MS 2022 (gestação de alto risco)'
SIM_NAO = {'sim': True, 'nao': False, 'não': False}
CONDICOES = {
    'gemelar': 'Gestação gemelar',
    'pe_previa': 'Pré-eclâmpsia em gestação anterior',
    'dmg_previo': 'Diabetes gestacional em gestação anterior',
    'dmg_atual': 'Diabetes gestacional já diagnosticado nesta gestação',
    'prematuro_previo': 'Parto prematuro anterior',
    'monocorionica': 'Gestação gemelar monocoriônica',
    # Fatores de risco moderado de pré-eclâmpsia (USPSTF 2021): 2 ou mais indicam considerar o AAS.
    'nulipara': 'Nuliparidade (primeira gestação)',
    'pe_familiar': 'Mãe ou irmã com pré-eclâmpsia',
    'fiv': 'Gestação por fertilização in vitro',
    'intervalo_10_anos': 'Mais de 10 anos desde a última gestação',
    'desfecho_adverso_previo': 'Desfecho adverso em gestação anterior (baixo peso ao nascer, PIG, óbito fetal)',
    # Resultado do rastreio combinado de 11-14 semanas (FEBRASGO 2023): ≥ 1:100 é alto risco.
    'rastreio_pe_alto': 'Rastreio combinado de pré-eclâmpsia (11-14 semanas) com risco ≥ 1:100',
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
    'Sangue oculto nas fezes (FIT)': 'Rastreio colorretal adiado para após a gestação, junto com a colonoscopia.',
    # Com fonte própria: (motivo, referência)
    'Ressonância magnética de mamas': ('Ressonância de rastreio, com gadolínio, adiada para após o parto (na gestação, gadolínio '
                                       'só quando essencial; ultrassonografia e exame clínico se houver achado). Na lactação '
                                       'pode ser feita.', 'ACOG CO 723'),
    'Endoscopia digestiva alta': ('Endoscopia eletiva (rastreio ou vigilância) adiada para após o parto; na gestação, só com '
                                  'indicação forte.', 'ASGE 2012'),
    # Não fazem parte do pré-natal de risco habitual (MS, CAB 32). Com HAS, diabetes, doença renal ou risco de
    # pré-eclâmpsia continuam na lista (ver adiar(..., com_indicacao=True)).
    'Eletrocardiograma de repouso': 'Não faz parte do pré-natal de risco habitual (MS, CAB 32); pedir se houver indicação clínica.',
    'Creatinina, soro': 'Não faz parte do pré-natal de risco habitual (MS, CAB 32); com hipertensão, diabetes, doença renal '
                        'ou risco de pré-eclâmpsia, o pré-natal pede.',
}
# Adiados só quando não há indicação (HAS, diabetes, doença renal, risco de pré-eclâmpsia).
ADIAR_SEM_INDICACAO = {'eletrocardiograma de repouso', 'creatinina, soro'}


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
    condicoes = set(condicoes)
    if 'monocorionica' in condicoes:
        condicoes.add('gemelar')          # monocoriônica é gemelar
    return {'ig': ig, 'primeira_consulta': primeira, 'rh': rh, 'toxo': toxo, 'totg_feito': totg == 'sim',
            'condicoes': sorted(condicoes)}


def _rec(titulo, categoria, descricao, subtitulo, prioridade='alta', grau='A', referencia=REF):
    return {'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'prioridade': prioridade, 'referencia': referencia, 'grau_evidencia': grau, 'gestacao': True}


# Janelas (semana inicial, semana final EXCLUSIVA, nome): 20-24 semanas vale até 24+6 → (20, 25).
def _janelas(g, idade, hipertensa, diabetica, hiv=False, alto_risco=()):
    """``alto_risco``: fatores que indicam o Doppler no 3º trimestre (ver fatores_pre_eclampsia)."""
    toxo_repetir = g['toxo'] != 'imune'
    rh_neg = g['rh'] == 'negativo'
    colo_inicio = 16 if 'prematuro_previo' in g['condicoes'] else 20
    # Ultrassonografia do 3º trimestre: o Doppler de rotina na gestação de baixo risco não tem benefício
    # demonstrado (Cochrane 2015, Alfirevic); fica para o alto risco. No risco habitual, a ultrassonografia de
    # crescimento é do protocolo da instituição (Einstein), não evidência de grau B.
    if alto_risco:
        usg_3o = _rec('Ultrassonografia obstétrica com Doppler', 'imagem',
                      'Crescimento e vitalidade fetal na gestação de alto risco (' + ', '.join(alto_risco) + ').',
                      'Pré-natal | 28-36 semanas | Alto risco', prioridade='media', grau='B',
                      referencia=EINSTEIN + ' / ' + ACOG_PE)
    else:
        usg_3o = _rec('Ultrassonografia obstétrica', 'imagem',
                      'Crescimento fetal no 3º trimestre: protocolo institucional (Einstein). Doppler de rotina sem '
                      'benefício demonstrado no baixo risco (Cochrane 2015).',
                      'Pré-natal | 28-36 semanas | Protocolo institucional', prioridade='baixa', grau='C',
                      referencia=EINSTEIN + ' / Cochrane 2015 (Doppler no baixo risco)')
    janelas = [
        (5, 11, '7-9 semanas', [
            _rec('Ultrassonografia obstétrica transvaginal', 'imagem',
                 'Datação da gestação, número e localização dos embriões, viabilidade.', 'Pré-natal | 7-9 semanas'),
        ]),
        (11, 14, '11-13+6 semanas', [
            _rec('Ultrassonografia morfológica de 1º trimestre (translucência nucal)', 'imagem',
                 'Datação, número de fetos, rastreamento de aneuploidias e anomalias; avaliação de risco de pré-eclâmpsia (Doppler de artérias uterinas). Rastreio bioquímico ou DNA fetal livre opcionais.'
                 + (' Gemelar: definir a corionicidade.' if 'gemelar' in g['condicoes'] else ''),
                 'Pré-natal | 11-13+6 semanas'),
        ]),
        (20, 25, '20-24 semanas', [
            _rec('Ultrassonografia morfológica de 2º trimestre', 'imagem',
                 'Rastreamento de anomalias fetais.', 'Pré-natal | 20-24 semanas'),
        ] + ([_rec('Ecocardiograma fetal', 'imagem',
                   'Diabetes pré-gestacional: rastreio de cardiopatia congênita no 2º trimestre.',
                   'Pré-natal | DM pré-gestacional | 20-24 semanas', prioridade='media', grau='B',
                   referencia='ACOG PB 201 / AHA 2014 (ecocardiograma fetal)')]
             if diabetica else []) + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
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
            _rec('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas',
                 referencia=REF_SOROLOGIA),
        ] + ([] if hiv else [
            _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas',
                 referencia=REF_SOROLOGIA),
        ]) + [
            _rec('HBsAg, soro', 'laboratorio', 'Repetir no 3º trimestre (Einstein/MS).', 'Pré-natal | 28-36 semanas', prioridade='media',
                 referencia=REF_SOROLOGIA),
            usg_3o,
        ] + ([_rec('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
                   'Reteste no 3º trimestre para menores de 25 anos ou com fator de risco.',
                   'Pré-natal | 28-36 semanas | < 25 anos', grau='B', referencia='Williams 26e / USPSTF 2021 (clamídia e gonococo)')]
             if idade < 25 else []) + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
                   'Repetir a cada trimestre enquanto suscetível (IgG negativa).', 'Pré-natal | Suscetível: a cada trimestre')]
             if toxo_repetir else [])),
        # ACOG CO 797 (2020): 36+0 a 37+6 semanas; a cultura vale 5 semanas (colhida com 35, venceria antes de 40).
        (36, 38, '36-37+6 semanas', [
            _rec('Cultura para estreptococo do grupo B (swab vaginal e retal)', 'laboratorio',
                 'Define antibioticoprofilaxia intraparto. Dispensada se houve bacteriúria por estreptococo do grupo B nesta '
                 'gestação ou filho anterior com doença por estreptococo do grupo B: nesses casos a profilaxia é feita de '
                 'qualquer forma.',
                 'Pré-natal | 36-37+6 semanas', referencia=REF + ' / ACOG CO 797 (2020)'),
        ]),
    ]
    if 'monocorionica' in g['condicoes']:
        janelas.append((16, 38, '16-37 semanas', [
            _rec('Ultrassonografia obstétrica', 'imagem',
                 'Gemelar monocoriônica: ultrassonografia a cada 2 semanas a partir de 16 semanas (síndrome de transfusão '
                 'feto-fetal, restrição seletiva de crescimento).',
                 'Pré-natal | Gemelar monocoriônica | A cada 2 semanas a partir de 16 semanas', grau='B',
                 referencia='ISUOG 2025 (gemelar) / ' + MS_ALTO_RISCO),
        ]))
    return janelas


REF_DMG = 'Consenso brasileiro de DMG 2017 / ' + REF
TOTG_ATE = 37   # a partir do termo o TOTG atrasado sai do pedido automático e vira lembrete


def _totg(g, diabetica):
    """TOTG-75g: de 24 a 28 semanas; depois disso, pedido enquanto não constar como já realizado.

    Devolve ``(inicio, item)`` ou ``None``. Quem começa o pré-natal depois de 28 semanas, ou não fez o
    exame na janela, faz o TOTG de imediato (OPAS/MS/FEBRASGO/SBD 2017).
    """
    if diabetica or g.get('totg_feito') or 'dmg_atual' in g['condicoes']:  # já diagnosticada: não se repete o TOTG
        return None
    if g['ig'] is not None and g['ig'] >= TOTG_ATE:
        return None                       # perto do termo: lembrete em programacao(), não pedido automático
    atrasado = g['ig'] is not None and g['ig'] >= 29
    item = _rec('TOTG-75g gestacional (jejum, 1 h e 2 h), soro', 'laboratorio',
                'Rastreio de diabetes gestacional para todas sem diagnóstico prévio. Critérios IADPSG/OMS: jejum ≥ 92, '
                '1 h ≥ 180 ou 2 h ≥ 153 mg/dL (um valor basta).'
                + (' Fora da janela de 24-28 semanas: se ainda não foi feito, fazer de imediato.' if atrasado else ''),
                'Pré-natal | Não realizado com 24-28 semanas: fazer agora' if atrasado else 'Pré-natal | 24-28 semanas',
                referencia=REF_DMG if atrasado else REF)
    # No pedido, só a janela (instrução para quem colhe). O atraso é motivo do pedido: fica na tela.
    if not atrasado:
        item['quando_pdf'] = 'Realizar com 24-28 semanas de gestação.'
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
        _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta',
             referencia=REF_SOROLOGIA),
    ]) + [
        _rec('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta',
             referencia=REF_SOROLOGIA),
        _rec('HBsAg, soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta', referencia=REF_SOROLOGIA),
        _rec('Anti-HCV IgG, soro', 'laboratorio', 'Rastreio universal na gestação.', 'Pré-natal | 1ª consulta',
             referencia=REF_SOROLOGIA),
        _rec('Rubéola IgG, soro', 'laboratorio', 'Suscetível: vacinar no puerpério (vacina de vírus vivo).',
             'Pré-natal | 1ª consulta', prioridade='media', grau='B'),
        # TSH universal no início do pré-natal (FEBRASGO/SBEM 2022). ACOG/ATA: rastreio seletivo (ver orientações).
        _rec('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
             'Rastreio universal no início do pré-natal. Sem referência local por trimestre: TSH ≤ 4,0 mUI/L é normal; '
             'acima disso, dosar T4 livre (TSH > 10: hipotireoidismo clínico, tratar).',
             'Pré-natal | 1ª consulta', prioridade='media', grau='B', referencia='FEBRASGO/SBEM 2022 (tireoide na gestação)'),
        _rec('Citomegalovírus IgG e IgM, soro', 'laboratorio',
             'Protocolo Einstein; não é rastreio universal no MS nem na ACOG.', 'Pré-natal | 1ª consulta | Protocolo institucional',
             prioridade='baixa', grau='C', referencia=EINSTEIN),
        _rec('Parasitológico de fezes', 'laboratorio', 'Protocolo Einstein; não é rastreio de rotina na ACOG.',
             'Pré-natal | 1ª consulta | Protocolo institucional', prioridade='baixa', grau='C', referencia=EINSTEIN),
    ]
    if g['rh'] != 'positivo':
        recs.append(_rec('Tipagem sanguínea ABO e fator Rh', 'laboratorio', 'Risco de aloimunização Rh.', 'Pré-natal | 1ª consulta'))
    # Williams, Tab. 10-1: pesquisa de anticorpos irregulares na 1ª consulta para todas (não só Rh negativo)
    recs.append(_rec('Coombs indireto, soro', 'laboratorio',
                     'Pesquisa de anticorpos irregulares na primeira consulta, para todas as gestantes. Na Rh negativo, '
                     'repetir com 28 semanas.', 'Pré-natal | 1ª consulta'))
    if g['toxo'] != 'imune':
        recs.append(_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio', 'Suscetível: repetir a cada trimestre.', 'Pré-natal | 1ª consulta'))
    # Williams, Tab. 10-1: clamídia para todas na 1ª consulta. A USPSTF limita a ≤ 24 anos ou risco (ver orientações).
    recs.append(_rec('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
                     'Clamídia: rastreio na primeira consulta para todas (Williams). Gonococo: para menores de 25 anos ou com '
                     'fator de risco. Repetir no 3º trimestre se menor de 25 anos ou com risco.',
                     'Pré-natal | 1ª consulta', grau='B', referencia='Williams 26e'))
    # Rastreio do colo (ponto da 1ª consulta na Tab. 10-1): vem do check-up geral (src/utils/colo_utero.py), que
    # na gestação segue na lista: teste de DNA-HPV a partir dos 25 anos; a coleta é segura na gestação (MS 2025, rec. 31).
    if not diabetica and ('dmg_previo' in g['condicoes']):
        recs.append(_rec('Hemoglobina glicada (HbA1c), soro', 'laboratorio',
                         'Fator de risco para diabetes: rastrear diabetes não diagnosticado antes de 15 semanas.',
                         'Pré-natal | 1ª consulta | Fator de risco', grau='B', referencia='ADA 2026 (seção 15)'))
    return recs


# Comorbidades (lista do formulário) que são fator de ALTO risco de pré-eclâmpsia (USPSTF 2021; ACOG PB 222):
# doença renal e doença autoimune (lúpus, síndrome antifosfolípide).
ALTO_RISCO_COMORBIDADES = {
    'lupus': 'lúpus', 'les_nefrite': 'nefrite lúpica', 'saf': 'síndrome antifosfolípide',
    'doenca_renal': 'doença renal crônica',
}
MODERADO_CONDICOES = {
    'nulipara': 'nuliparidade', 'pe_familiar': 'mãe ou irmã com pré-eclâmpsia', 'fiv': 'fertilização in vitro',
    'intervalo_10_anos': 'intervalo > 10 anos', 'desfecho_adverso_previo': 'desfecho adverso prévio',
}


def fatores_pre_eclampsia(g, idade, hipertensa=False, diabetica=False, comorbidades=(), imc=None):
    """Fatores de risco de pré-eclâmpsia: ``(altos, moderados)``, com o nome de cada um.

    Alto risco (1 basta para o AAS): pré-eclâmpsia prévia, gemelar, HAS crônica, DM tipo 1 ou 2, doença renal,
    doença autoimune (lúpus, SAF) (USPSTF 2021; ACOG PB 222), ou rastreio combinado de 11-14 semanas ≥ 1:100
    (FEBRASGO 2023). Moderado (2 ou mais: considerar AAS, USPSTF 2021): nuliparidade, IMC > 30, idade ≥ 35,
    mãe ou irmã com pré-eclâmpsia, fertilização in vitro, intervalo > 10 anos, desfecho adverso prévio.
    """
    cond, com = set(g['condicoes']), set(comorbidades or ())
    altos = []
    if 'pe_previa' in cond:
        altos.append('pré-eclâmpsia prévia')
    if 'gemelar' in cond:
        altos.append('gestação gemelar')
    if hipertensa:
        altos.append('hipertensão crônica')
    if diabetica:
        altos.append('diabetes pré-gestacional')
    altos += [nome for chave, nome in ALTO_RISCO_COMORBIDADES.items() if chave in com]
    if 'rastreio_pe_alto' in cond:
        altos.append('rastreio combinado ≥ 1:100')
    moderados = [nome for chave, nome in MODERADO_CONDICOES.items() if chave in cond]
    if idade >= 35:
        moderados.append('idade ≥ 35 anos')
    if imc is not None and imc > 30:
        moderados.append('IMC > 30')
    return altos, moderados


def classificar_pa(pas, pad):
    """PA na gestação: hipertensão a partir de 140/90 e faixa grave a partir de 160/110 (ACOG PB 222; ISSHP).

    Sem os estágios da AHA/ACC, que não se aplicam à gestação.
    """
    tem_s, tem_d = pas not in (None, '', 0), pad not in (None, '', 0)
    if not tem_s and not tem_d:
        return None
    s_ = float(pas) if tem_s else None
    d_ = float(pad) if tem_d else None
    if (s_ is not None and s_ >= 160) or (d_ is not None and d_ >= 110):
        return {'categoria': 'grave', 'rotulo': 'PA em faixa grave na gestação (≥ 160/110)'}
    if (s_ is not None and s_ >= 140) or (d_ is not None and d_ >= 90):
        return {'categoria': 'hipertensao', 'rotulo': 'Hipertensão na gestação (≥ 140/90)'}
    if not (tem_s and tem_d):
        return {'categoria': 'incompleta', 'rotulo': 'Informe PAS e PAD para classificar', 'incompleta': True}
    return {'categoria': 'normal', 'rotulo': 'PA < 140/90'}


def suspeita_de_pre_eclampsia(g, pas, pad):
    """PA ≥ 140/90 a partir de 20 semanas: investigar pré-eclâmpsia no mesmo dia (ACOG PB 222)."""
    pa = classificar_pa(pas, pad)
    return bool(pa and pa['categoria'] in ('grave', 'hipertensao') and g['ig'] is not None and g['ig'] >= 20)


INVESTIGACAO_PE = 'Pré-natal | Investigação de pré-eclâmpsia | Agora'


def _risco_pre_eclampsia(g, altos, suspeita=False):
    """Exames de pré-eclâmpsia: diagnósticos (agora) com PA ≥ 140/90 após 20 semanas; basais no alto risco."""
    if suspeita:
        texto = ('PA ≥ 140/90 com 20 semanas ou mais: investigar pré-eclâmpsia no mesmo dia (proteinúria, plaquetas, '
                 'creatinina, transaminases e LDH).')
        return [
            _rec('Relação proteína/creatinina, urina', 'laboratorio', texto + ' Proteína/creatinina ≥ 0,3 = proteinúria.',
                 INVESTIGACAO_PE, grau='B', referencia=ACOG_PE),
            _rec('Hemograma completo', 'laboratorio', texto + ' Plaquetas < 100.000/µL é sinal de gravidade.',
                 INVESTIGACAO_PE, grau='B', referencia=ACOG_PE),
            _rec('Creatinina, soro', 'laboratorio', texto + ' Creatinina > 1,1 mg/dL (ou o dobro da basal) é sinal de gravidade.',
                 INVESTIGACAO_PE, grau='B', referencia=ACOG_PE),
            _rec('TGO e TGP, soro', 'laboratorio', texto + ' Transaminases no dobro do normal são sinal de gravidade.',
                 INVESTIGACAO_PE, grau='B', referencia=ACOG_PE),
            _rec('Desidrogenase láctica (LDH), soro', 'laboratorio', texto + ' LDH elevada sugere hemólise (HELLP).',
                 INVESTIGACAO_PE, grau='B', referencia=ACOG_PE),
        ]
    if not altos:
        return []
    motivo = 'Alto risco de pré-eclâmpsia: ' + ', '.join(altos)
    sub = 'Pré-natal | Alto risco de pré-eclâmpsia | Basal'     # o fator vai na descrição (subtítulo é lido como periodicidade)
    return [
        _rec('Relação proteína/creatinina, urina', 'laboratorio',
             f'{motivo}. Exame basal, para comparação se surgir hipertensão.', sub, grau='B', referencia=ACOG_PE),
        _rec('TGO e TGP, soro', 'laboratorio', f'{motivo}. Basal para pré-eclâmpsia/HELLP.', sub,
             prioridade='media', grau='B', referencia=ACOG_PE),
        _rec('Creatinina, soro', 'laboratorio', f'{motivo}. Basal para pré-eclâmpsia.', sub,
             prioridade='media', grau='B', referencia=ACOG_PE),
    ]


def _orientar(titulo, descricao, referencia, urgente=False):
    o = {'titulo': titulo, 'descricao': descricao, 'referencia': referencia}
    if urgente:
        o['urgente'] = True
    return o


def orientacao_aas(ig, altos, moderados):
    """AAS para prevenção de pré-eclâmpsia, pelo fator e pela idade gestacional (ou None)."""
    if altos:
        titulo = 'AAS para prevenção de pré-eclâmpsia'
        motivo = 'Alto risco de pré-eclâmpsia (' + ', '.join(altos) + ').'
    elif len(moderados) >= 2:
        titulo = 'Considerar AAS para prevenção de pré-eclâmpsia'
        motivo = ('Risco moderado de pré-eclâmpsia: 2 ou mais fatores (' + ', '.join(moderados) + '); a evidência para os '
                  'fatores moderados é menos certa. Raça negra e baixa renda também contam como fator moderado (USPSTF).')
    else:
        return None
    dose = 'AAS 100-150 mg à noite (idealmente 150 mg) até 36 semanas.'
    if ig is None or ig < 12:
        quando = 'Iniciar a partir de 12 semanas, idealmente antes de 16: ' + dose
    elif ig < 16:
        quando = 'Iniciar agora (idealmente antes de 16 semanas): ' + dose
    elif ig < 28:
        quando = 'Ainda pode ser iniciado até 28 semanas (ACOG), com benefício menor do que antes de 16: ' + dose
    elif ig < 36:
        quando = 'Não iniciar depois de 28 semanas. Se já estiver em uso, manter até 36 semanas.'
    else:
        quando = 'Não iniciar depois de 28 semanas. Se estiver em uso, a FEBRASGO suspende com 36 semanas.'
    return _orientar(titulo, f'{motivo} {quando}', f'{FEBRASGO_PE} / {CONITEC_AAS} / {USPSTF_AAS} / {ACOG_PE}')


DIVERGENCIA = 'Divergência entre diretrizes: '


def orientacoes(g, idade, pas=None, pad=None, hipertensa=False, diabetica=False, hiv=False, comorbidades=(), imc=None,
                agora=()):
    """Orientações da gestação (não entram nos PDFs). As urgentes vêm primeiro.

    ``agora``: exames da lista (para os avisos de divergência só aparecerem quando o exame foi pedido).
    """
    ig = g['ig']
    cond, com = set(g['condicoes']), set(comorbidades or ())
    urgentes, outras = [], []
    pa = classificar_pa(pas, pad)
    pa_txt = '/'.join(f'{float(v):g}' if v not in (None, '', 0) else '–' for v in (pas, pad))
    if pa and pa['categoria'] == 'grave':
        urgentes.append(_orientar(
            f'PA {pa_txt} mmHg em faixa grave na gestação: urgência',
            'PAS ≥ 160 ou PAD ≥ 110: repetir em 15 minutos para confirmar; se persistir, tratar em 30-60 minutos '
            '(labetalol ou hidralazina venosos, ou nifedipino oral de liberação imediata) e encaminhar à maternidade para '
            'avaliar pré-eclâmpsia com sinais de gravidade.', 'ACOG CO 767 (2019) / ' + ACOG_PE, urgente=True))
    if pa and pa['categoria'] in ('grave', 'hipertensao') and ig is not None:
        if ig >= 20 and not hipertensa:
            outras.append(_orientar(
                'Hipertensão na gestação com 20 semanas ou mais',
                f'PA {pa_txt} mmHg em gestante sem hipertensão prévia: repetir em 4 horas; se confirmada, é hipertensão '
                'gestacional ou pré-eclâmpsia, não HAS crônica (MAPA e ecocardiograma do seguimento de HAS não se aplicam). '
                'Investigar pré-eclâmpsia no mesmo dia: relação proteína/creatinina, hemograma com plaquetas, creatinina, '
                'TGO/TGP e LDH (na lista).', f'{ACOG_PE} / {FEBRASGO_PE}'))
        elif ig >= 20:
            outras.append(_orientar(
                'HAS crônica com PA ≥ 140/90 depois de 20 semanas',
                f'PA {pa_txt} mmHg: avaliar pré-eclâmpsia sobreposta (piora da PA, proteinúria nova, plaquetopenia, alteração '
                'renal ou hepática, sintomas). Exames de investigação na lista.', ACOG_PE))
        elif not hipertensa:
            outras.append(_orientar(
                'PA ≥ 140/90 antes de 20 semanas',
                f'PA {pa_txt} mmHg: provável hipertensão crônica (anterior à gestação). Confirmar com nova medida ou MRPA; se '
                'confirmada, marcar hipertensão: é fator de alto risco de pré-eclâmpsia (AAS).', f'{ACOG_PE} / {FEBRASGO_PE}'))

    altos, moderados = fatores_pre_eclampsia(g, idade, hipertensa, diabetica, com, imc)
    aas = orientacao_aas(ig, altos, moderados)
    if aas:
        outras.append(aas)
        outras.append(_orientar(
            DIVERGENCIA + 'dose e duração do AAS',
            'O motor segue a FEBRASGO 2023 e a Conitec 2026 (100-150 mg à noite, até 36 semanas); USPSTF 2021 e ACOG '
            'usam 81 mg/dia, iniciado de 12 a 28 semanas e mantido até o parto.',
            f'{FEBRASGO_PE} / {CONITEC_AAS} / {USPSTF_AAS} / {ACOG_PE}'))

    # Pré-natal de alto risco (MS 2022)
    motivos = []
    if hipertensa:
        motivos.append('hipertensão crônica')
    elif pa and pa['categoria'] in ('grave', 'hipertensao') and ig is not None and ig >= 20:
        motivos.append('hipertensão na gestação')
    if diabetica:
        motivos.append('diabetes pré-gestacional')
    if 'dmg_atual' in cond:
        motivos.append('diabetes gestacional')
    if 'monocorionica' in cond:
        motivos.append('gestação gemelar monocoriônica')
    elif 'gemelar' in cond:
        motivos.append('gestação gemelar')
    motivos += [nome for chave, nome in ALTO_RISCO_COMORBIDADES.items() if chave in com]
    if hiv:
        motivos.append('HIV')
    if 'pe_previa' in cond:
        motivos.append('pré-eclâmpsia prévia')
    if motivos:
        texto = ('O roteiro abaixo é o mínimo do pré-natal de risco habitual: seguir com o pré-natal de alto risco '
                 '(referência).')
        if 'gemelar' in cond and 'monocorionica' not in cond:
            texto += (' Gemelar: definir a corionicidade na ultrassonografia de 11-14 semanas; a monocoriônica pede '
                      'ultrassonografia a cada 2 semanas a partir de 16 semanas (marque "Gemelar monocoriônica").')
        urgentes.append(_orientar('Gestação de alto risco: ' + ', '.join(motivos), texto,
                                  MS_ALTO_RISCO + (' / ISUOG 2025 (gemelar)' if 'gemelar' in cond else '')))

    titulos = {r['titulo'] for r in agora}
    # TSH universal (FEBRASGO/SBEM) × seletivo (ACOG/ATA)
    if 'Hormônio Tireoestimulante (TSH), soro' in titulos:
        outras.append(_orientar(
            DIVERGENCIA + 'TSH na gestação',
            'O motor segue a FEBRASGO/SBEM 2022 (TSH para todas no início do pré-natal); a ATA 2017 e a ACOG fazem rastreio '
            'seletivo (doença tireoidiana, DM1 ou outra autoimune, anti-TPO positivo, idade > 30, IMC ≥ 40, abortamento ou '
            'parto prematuro prévio, irradiação cervical, amiodarona ou lítio).',
            'FEBRASGO/SBEM 2022 (tireoide na gestação) / ATA 2017 (tireoide na gestação)'))
    # Clamídia na 1ª consulta para todas (Williams) × ≤ 24 anos ou risco (USPSTF)
    if idade >= 25 and any(r['titulo'] == 'Clamídia e gonococo, PCR (urina ou swab)' and r.get('gestacao') for r in agora):
        outras.append(_orientar(
            DIVERGENCIA + 'clamídia e gonococo na gestante a partir de 25 anos',
            'O motor segue o Williams (clamídia para todas na 1ª consulta); a USPSTF 2021 rastreia gestantes a partir de 25 '
            'anos só com risco aumentado (parceria nova ou múltipla, parceria com IST, IST prévia).',
            'Williams 26e / USPSTF 2021 (clamídia e gonococo)'))
    # Protocolo institucional (Einstein) sem respaldo de rotina no MS/ACOG
    nomes = [nome for t, nome in (('Citomegalovírus IgG e IgM, soro', 'citomegalovírus'),
                                  ('Parasitológico de fezes', 'parasitológico de fezes')) if t in titulos]
    if any(r['titulo'] == 'Ultrassonografia obstétrica' and 'Protocolo institucional' in r.get('subtitulo', '') for r in agora):
        nomes.append('ultrassonografia de crescimento no 3º trimestre')
    if any(r['titulo'].startswith('Ultrassonografia transvaginal para medida do colo') for r in agora):
        nomes.append('medida do colo uterino para todas')
    if nomes:
        outras.append(_orientar(
            DIVERGENCIA + 'exames do protocolo institucional',
            'Mantidos por seguirem o protocolo Einstein de pré-natal: ' + ', '.join(nomes) + '. O MS (CAB 32) e a ACOG não '
            'pedem citomegalovírus, parasitológico nem ultrassonografia de 3º trimestre de rotina no risco habitual; para o '
            'colo uterino, a ACOG diz que a medida universal pode ser considerada.',
            f'{EINSTEIN} / MS 2012-2016 / ACOG PB 234 / Cochrane 2015 (Doppler no baixo risco)'))
    # Coombs indireto na Rh negativa: 1 repetição com 28 semanas (ACOG/Williams) × mensal a partir de 24 (MS)
    if g['rh'] == 'negativo' and ig is not None and ig < 29:
        outras.append(_orientar(
            DIVERGENCIA + 'Coombs indireto na Rh negativa',
            'O motor segue ACOG/Williams (repetir com 28 semanas e dar imunoglobulina anti-D); o MS (CAB 32) repete o Coombs '
            'indireto a cada 4 semanas a partir de 24 semanas.', 'Williams 26e / MS 2012-2016'))
    elif g['rh'] == 'desconhecido' and not g['primeira_consulta']:
        outras.append(_orientar(
            'Fator Rh não informado',
            'Confirme a tipagem ABO/Rh da 1ª consulta. Se Rh negativo: Coombs indireto com 28 semanas e imunoglobulina anti-D '
            'com 28 semanas e até 72 h após o parto (RN Rh positivo).', REF))

    # Fim da gestação (MS, CAB 32; PCDT TV 2022)
    if ig is not None and ig >= 37:
        outras.append(_orientar(
            'Sífilis e HIV no fim da gestação',
            'Se a sífilis e o HIV do 3º trimestre não foram feitos, testar agora ou na admissão para o parto (testes rápidos).',
            'PCDT TV MS 2022'))
        if _totg_pendente(g, diabetica):
            outras.append(_orientar(
                'TOTG-75g não realizado',
                'Com 37 semanas ou mais o TOTG muda pouco a conduta: decidir caso a caso (glicemia de jejum ou TOTG).',
                REF_DMG))
    if ig is not None and ig >= 40:
        outras.append(_orientar(
            'Gestação com 40 semanas ou mais',
            'Avaliar a vitalidade fetal e encaminhar à maternidade com 41 semanas para programar o parto.', 'MS 2012-2016'))

    # DM pré-gestacional
    if diabetica:
        outras.append(_orientar(
            'Diabetes pré-gestacional na gestação',
            'Fundo de olho antes da gestação ou no 1º trimestre, a cada trimestre e até 1 ano pós-parto. HbA1c é medida '
            'secundária na gestação (a principal é a glicemia capilar). Cálcio, fósforo e vitamina D não se rastreiam na '
            'gestação.', 'ADA 2026 (seção 15) / ACOG CO 495 (vitamina D)'))

    # Suplementos
    outras.append(_orientar(
        'Suplementação na gestação',
        'Ácido fólico 0,4 mg/dia (idealmente desde antes da concepção) e ferro elementar 40 mg/dia durante a gestação, '
        'ferro até o 3º mês pós-parto (MS). Cálcio ≥ 1 g/dia na 2ª metade da gestação reduz pré-eclâmpsia em quem '
        'ingere pouco cálcio (FEBRASGO; evidência conflitante para uso geral).',
        f'MS 2013 (suplementação de ferro) / USPSTF 2023 (ácido fólico) / {FEBRASGO_PE}'))
    return urgentes + outras


def _totg_pendente(g, diabetica):
    return not (diabetica or g.get('totg_feito') or 'dmg_atual' in g['condicoes'])


def exames(g, idade, hipertensa=False, diabetica=False, hiv=False, **kw):
    """Exames do pré-natal para fazer AGORA (1ª consulta + janela atual + basais de risco)."""
    return programacao(g, idade, hipertensa, diabetica, hiv, **kw)[0]


INICIAIS = ('tipagem ABO/Rh, Coombs indireto, hemograma, glicemia de jejum, urina tipo I e urocultura, HIV, '
            'sífilis, HBsAg, anti-HCV, TSH, clamídia, toxoplasmose, rubéola e citomegalovírus')


def _unir(lista):
    """Um exame por título. O de investigação de pré-eclâmpsia (pedido agora) prevalece e leva o motivo do outro."""
    por_titulo, ordem = {}, []
    for r in lista:
        t = r['titulo']
        if t not in por_titulo:
            por_titulo[t] = r
            ordem.append(t)
        elif r.get('subtitulo') == INVESTIGACAO_PE and por_titulo[t].get('subtitulo') != INVESTIGACAO_PE:
            antigo = por_titulo[t]
            por_titulo[t] = {**r, 'descricao': f"{r['descricao']} {antigo['descricao']}"}
    return [por_titulo[t] for t in ordem]


def programacao(g, idade, hipertensa=False, diabetica=False, hiv=False, comorbidades=(), imc=None, pas=None, pad=None):
    """Devolve ``(agora, proximas)``.

    ``agora`` vai para a lista e para os PDFs. ``proximas`` são os exames das janelas
    seguintes e os avisos de etapas anteriores: aparecem só como informação, nunca no PDF.
    """
    agora, proximas = [], []
    ig = g['ig']
    altos, _ = fatores_pre_eclampsia(g, idade, hipertensa, diabetica, comorbidades, imc)
    suspeita = suspeita_de_pre_eclampsia(g, pas, pad)
    # Exames da investigação de pré-eclâmpsia vêm primeiro: prevalecem sobre o mesmo exame de rotina.
    agora += _risco_pre_eclampsia(g, altos, suspeita)
    if g['primeira_consulta']:
        # Sem observação no pedido: ser da primeira consulta é o motivo, não uma instrução para quem faz o exame.
        agora += _primeira_consulta(g, idade, hipertensa, diabetica, hiv)
    else:
        proximas.append({'titulo': 'Exames iniciais do pré-natal (1ª consulta)', 'categoria': 'laboratorio',
                         'estado': 'etapa_anterior', 'referencia': REF, 'semana': -1,
                         'motivo': f'Considerados já feitos: {INICIAIS}. Se algum ficou faltando, responda "Sim" em '
                                   '"Primeira consulta de pré-natal?" ou acrescente o exame ao gerar o PDF.'})
    risco_doppler = altos + (['hipertensão na gestação'] if suspeita and not altos else [])
    janelas = _janelas(g, idade, hipertensa, diabetica, hiv, alto_risco=risco_doppler)
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
                             'Pré-natal | 1ª consulta após 14 semanas', grau='B')})
    # Gestante com HIV: carga viral (e CD4, em TARV com carga viral indetectável) a partir de 34 semanas.
    if hiv and ig is not None and ig < 34:
        for titulo, texto in (('Carga Viral do HIV (HIV RNA)', 'a partir de 34 semanas, define a via de parto.'),
                              ('Contagem de linfócitos T CD4+', 'com 34 semanas, em TARV com carga viral indetectável.')):
            proximas.append({'titulo': titulo, 'categoria': 'laboratorio', 'estado': 'proxima_janela',
                             'motivo': f'Gestante com HIV: {texto}', 'referencia': 'FEBRASGO 2025 (HIV na gestação)',
                             'semana': 34})
    # DM gestacional nesta gestação: TOTG de 4-12 semanas pós-parto (ADA 2026, seção 15). Só lembrete.
    if 'dmg_atual' in g['condicoes']:
        proximas.append({'titulo': 'TOTG-75g pós-parto (jejum e 2 h)', 'categoria': 'laboratorio', 'estado': 'proxima_janela',
                         'motivo': 'Diabetes gestacional: pedir com 4-12 semanas após o parto (mais sensível que a HbA1c); '
                                   'depois, rastreio por toda a vida, pelo menos a cada 3 anos.',
                         'referencia': 'ADA 2026 (seção 15)', 'semana': 43})
    unicos = _unir(agora)
    ja = {r['titulo'] for r in unicos}
    prox_unicas = []
    for r in sorted(proximas, key=lambda x: x['semana']):
        chave = (r['titulo'], r['semana'])
        if chave not in ja:
            ja.add(chave)
            prox_unicas.append(r)
    return unicos, prox_unicas


# Itens do check-up geral de fora da gestação que não se aplicam a ela (pelo subtítulo da regra que os trouxe):
# o seguimento ambulatorial da HAS (MAPA "confirmação", ecocardiograma a cada 1-2 anos, potássio, ácido úrico,
# uACR, EAS) e o metabolismo ósseo do diabético (cálcio, fósforo, vitamina D: ACOG CO 495).
FORA_DA_GESTACAO = (
    ('Adultos com HAS', 'Seguimento de HAS fora da gestação. Na gestação, a avaliação é a do pré-natal (proteína/creatinina, '
                        'plaquetas, creatinina e transaminases).'),
    ('Adultos com suspeita de HAS', 'Na gestação, PA ≥ 140/90 é avaliada pelo pré-natal (hipertensão gestacional ou '
                                    'pré-eclâmpsia), não pela confirmação de HAS ambulatorial.'),
    ('PA de consultório alterada, HAS a confirmar', 'Na gestação, PA ≥ 140/90 é avaliada pelo pré-natal (hipertensão '
                                                    'gestacional ou pré-eclâmpsia), não pela confirmação de HAS ambulatorial.'),
)
OSSEO_DO_DIABETICO = {'cálcio iônico, soro', '25-hidroxivitamina d, soro', 'fósforo, soro'}
# Rastreios gerais que o pré-natal decide (calendário próprio de HIV, hepatites e toxoplasmose na gestação; PCDT TV 2022).
DO_PRE_NATAL = {'anti-hiv 1 e 2, soro', 'anti-hcv igg, soro', 'anticorpos anti-hcv, soro', 'antígeno hbs, soro',
                'toxoplasmose igg, soro'}


def fora_da_gestacao(recomendacoes):
    """Tira os itens do check-up geral que não valem na gestação. Devolve ``(mantidas, adiadas)``."""
    mantidas, adiadas = [], []
    for r in recomendacoes:
        if r.get('gestacao'):
            mantidas.append(r)
            continue
        titulo = (r.get('titulo') or '').strip().lower()
        sub = r.get('subtitulo') or ''
        motivo = next((m for prefixo, m in FORA_DA_GESTACAO if sub.startswith((prefixo + ' |', prefixo + ' ('))), None)
        if motivo and titulo in ADIAR_SEM_INDICACAO:
            motivo = None     # ECG e creatinina na HAS crônica continuam (avaliação basal do pré-natal de alto risco)
        if not motivo and titulo in OSSEO_DO_DIABETICO and sub.startswith('Diabéticos') and 'Também:' not in sub:
            motivo = 'Metabolismo ósseo do diabético não se rastreia na gestação (vitamina D: ACOG CO 495).'
        if not motivo and titulo in DO_PRE_NATAL:
            continue          # o pré-natal decide (sem aviso: o exame do pré-natal já está na lista ou nas etapas)
        if motivo:
            adiadas.append({'titulo': r['titulo'], 'categoria': r.get('categoria'), 'estado': 'adiado_gestacao',
                            'motivo': motivo, 'referencia': REF})
        else:
            mantidas.append(r)
    return mantidas, adiadas


def ajustar_textos(recomendacoes, diabetica=False):
    """Textos próprios da gestação para itens que vêm do check-up geral (vacinas, DM pré-gestacional)."""
    for r in recomendacoes:
        t = r.get('titulo') or ''
        if r.get('categoria') == 'vacina' and t.startswith('dTpa'):
            r.update({'subtitulo': 'Gestante | 1 dose a cada gestação a partir de 20 semanas',
                      'descricao': '1 dose de dTpa em toda gestação a partir de 20 semanas, qualquer que seja o intervalo '
                                   'desde a última dose. Se não for vacinada na gestação, vacinar no puerpério o quanto antes, '
                                   'até 45 dias após o parto (PNI).'})
        elif r.get('categoria') == 'vacina' and t.startswith('COVID-19'):
            # O cartão da gestante já vem de condicoes.aplicar (intervalo mínimo e PNI); aqui só o subtítulo.
            if not (r.get('subtitulo') or '').startswith('Gestante'):
                r['descricao'] = '1 dose em cada gestação, em qualquer idade gestacional (PNI/SBIm).'
            r['subtitulo'] = 'Gestante | 1 dose a cada gestação, em qualquer idade gestacional'
        elif diabetica and t.startswith('Fundoscopia'):
            r.update({'subtitulo': 'DM pré-gestacional | 1º trimestre, a cada trimestre e até 1 ano pós-parto',
                      'descricao': 'Retinopatia pode progredir na gestação: fundo de olho com dilatação no 1º trimestre, a '
                                   'cada trimestre e até 1 ano pós-parto, conforme o grau de retinopatia.',
                      'referencia': 'ADA 2026 (seção 15)'})
        elif diabetica and t == 'Hemoglobina glicada (HbA1c), soro':
            r.update({'subtitulo': 'DM pré-gestacional | Medida secundária na gestação',
                      'descricao': 'Na gestação a HbA1c é medida secundária do controle (a principal é a glicemia capilar).',
                      'referencia': 'ADA 2026 (seção 15)'})
    return recomendacoes


def pos_parto(lactante, comorbidades, gestante=False, diabetica=False):
    """Puerpério recente (amamentando criança com menos de 6 meses): ``(recomendacoes, orientacoes)``.

    Sem a data do parto não dá para saber se passaram 12 semanas: o TOTG pós-DMG é pedido e o resto vira orientação.
    """
    if gestante or lactante != 'sim_menor_6m':
        return [], []
    recs, orient = [], []
    if 'diabetes_gestacional_previo' in set(comorbidades or ()) and not diabetica:
        recs.append(_rec('TOTG-75g (Teste Oral de Tolerância à Glicose), soro', 'laboratorio',
                         'Diabetes gestacional: TOTG 75 g (jejum e 2 h) com 4-12 semanas após o parto, mais sensível que a '
                         'HbA1c. Se já foi feito, segue o rastreio pelo menos a cada 3 anos.',
                         'DMG prévio, puerpério | 4-12 semanas após o parto', grau='B', referencia='ADA 2026 (seção 15)'))
        recs[-1].pop('gestacao')
    orient.append(_orientar(
        'Puerpério recente: lípides e HbA1c',
        'Amamentando criança com menos de 6 meses: os lípides sobem na gestação e se rastreiam depois do puerpério; a HbA1c '
        'nas primeiras semanas após o parto sofre efeito da gestação e da perda sanguínea. Se o parto foi há menos de 12 '
        'semanas, prefira adiar esses exames.', REF + ' / ADA 2026 (seção 15)'))
    return recs, orient


_ADIAR = {k.lower(): v for k, v in ADIAR_NA_GESTACAO.items()}


def adiar(recomendacoes, diabetica=False, com_indicacao=False):
    """Separa os itens do check-up geral que se adiam na gestação (um aviso por título).

    ``com_indicacao``: HAS, diabetes, doença renal ou risco de pré-eclâmpsia mantêm ECG e creatinina.
    """
    mantidas, adiadas, vistos = [], [], set()
    for r in recomendacoes:
        titulo = (r.get('titulo') or '').strip().lower()
        motivo = _ADIAR.get(titulo)
        referencia = REF
        if isinstance(motivo, tuple):
            motivo, referencia = motivo
        if diabetica and titulo.startswith('hemoglobina glicada'):
            motivo = None
        if com_indicacao and titulo in ADIAR_SEM_INDICACAO:
            motivo = None
        if motivo and not r.get('gestacao'):
            if titulo not in vistos:
                vistos.add(titulo)
                adiadas.append({'titulo': r['titulo'], 'categoria': r.get('categoria'), 'estado': 'adiado_gestacao',
                                'motivo': motivo, 'referencia': referencia})
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

USPSTF_IST = 'USPSTF 2021 (clamídia e gonococo)'
MS_IST = 'MS NT 8/2025 (clamídia e gonococo)'
CLAMIDIA = 'Clamídia e gonococo, PCR (urina ou swab)'


def clamidia_fora_da_gestacao(idade, sexualmente_ativa=None):
    """Mulher não gestante: ``(recomendacoes, orientacoes)`` do rastreio de clamídia e gonococo.

    USPSTF 2021 (B): mulheres sexualmente ativas até 24 anos, e a partir de 25 com risco aumentado. Sem resposta
    sobre atividade sexual, o exame entra (dado ausente não vale como "não") com o lembrete na descrição.
    O MS (NT 8/2025) restringe o teste no SUS a populações vulneráveis: vira aviso de divergência.
    """
    ativa = (sexualmente_ativa or 'desconhecido')
    if ativa == 'nao':
        return [], []
    if idade <= 24:
        desc = ('Teste molecular (urina ou swab vaginal) anual em mulheres sexualmente ativas até 24 anos.'
                + (' Atividade sexual não informada: não se aplica a quem não tem vida sexual.' if ativa != 'sim' else ''))
        rec = {'titulo': CLAMIDIA, 'categoria': 'laboratorio', 'descricao': desc,
               'subtitulo': 'Mulheres sexualmente ativas ≤ 24 anos | Anual', 'prioridade': 'alta',
               'referencia': USPSTF_IST, 'grau_evidencia': 'B'}
        aviso = _orientar(
            DIVERGENCIA + 'clamídia e gonococo',
            'O motor segue a USPSTF 2021 (todas as mulheres sexualmente ativas até 24 anos, anual); a nota técnica do MS de '
            '2025 restringe o teste no SUS a populações vulneráveis.', f'{USPSTF_IST} / {MS_IST}')
        return [rec], [aviso]
    if ativa == 'sim':
        return [], [_orientar(
            'Clamídia e gonococo a partir de 25 anos',
            'Rastrear (teste molecular) se houver risco aumentado: parceria nova ou múltipla, parceria com IST, IST prévia, '
            'troca de sexo por dinheiro ou drogas.', USPSTF_IST)]
    return [], []


def acido_folico(idade, sexualmente_ativa=None, histerectomizada=False):
    """Mulher não gestante que pode engravidar: ácido fólico 0,4-0,8 mg/dia (USPSTF 2023, A)."""
    if not 18 <= idade <= 45 or histerectomizada or sexualmente_ativa == 'nao':
        return []
    return [_orientar(
        'Ácido fólico se pode engravidar',
        'Ácido fólico 0,4-0,8 mg/dia para quem planeja ou pode engravidar, desde pelo menos 1 mês antes da concepção até '
        '2-3 meses de gestação (prevenção de defeitos do tubo neural).', 'USPSTF 2023 (ácido fólico)')]
