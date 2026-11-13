"""Rotina de exames do pré-natal de baixo risco, conforme a idade gestacional.

Fontes
- Hospital Israelita Albert Einstein. Guia do Episódio de Cuidado — Pré-Natal de Baixo
  Risco, v.3 (CPTW53.3, revisão 01/08/2024).
- Ministério da Saúde. Atenção ao pré-natal de baixo risco (Cadernos de Atenção Básica 32),
  2012; Protocolos da Atenção Básica — Saúde das Mulheres, 2016.
- Williams Obstetrics, 26ª ed., Tabela 10-1 (componentes da rotina de pré-natal).
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
    rh = str(entrada.get('fator_rh') or 'desconhecido').lower()
    if rh not in ('positivo', 'negativo', 'desconhecido'):
        erros.append({'campo': 'fator_rh', 'mensagem': 'Fator Rh: valor inválido.'})
        rh = 'desconhecido'
    toxo = str(entrada.get('toxoplasmose') or 'desconhecido').lower()
    if toxo not in ('suscetivel', 'imune', 'desconhecido'):
        erros.append({'campo': 'toxoplasmose', 'mensagem': 'Toxoplasmose: valor inválido.'})
        toxo = 'desconhecido'
    condicoes = entrada.get('gestacao_condicoes') or []
    if isinstance(condicoes, str):
        condicoes = [condicoes]
    desconhecidas = [c for c in condicoes if c not in CONDICOES]
    if desconhecidas:
        erros.append({'campo': 'gestacao_condicoes', 'mensagem': 'Condição da gestação inválida.'})
    if erros:
        raise GestacaoInvalida(erros)
    return {'ig': ig, 'primeira_consulta': primeira, 'rh': rh, 'toxo': toxo, 'condicoes': sorted(set(condicoes))}


def _rec(titulo, categoria, descricao, subtitulo, prioridade='alta', grau='A', referencia=REF):
    return {'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'prioridade': prioridade, 'referencia': referencia, 'grau_evidencia': grau, 'gestacao': True}


# Janelas (semana inicial, semana final EXCLUSIVA, nome): 20-24 semanas vale até 24+6 → (20, 25).
def _janelas(g, idade, hipertensa, diabetica):
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
        (colo_inicio, 25, f'{colo_inicio}-24 semanas', [
            _rec('Ultrassonografia morfológica de 2º trimestre', 'imagem',
                 'Rastreamento de anomalias fetais.', 'Pré-natal | 20-24 semanas'),
            _rec('Ultrassonografia transvaginal para medida do colo uterino', 'imagem',
                 'Rastreio de colo curto (≤ 25 mm). Com parto prematuro anterior, medir a partir de 16 semanas.',
                 f'Pré-natal | {colo_inicio}-24 semanas', prioridade='media', grau='B'),
        ] + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
                   'Repetir a cada trimestre enquanto suscetível (IgG negativa).', 'Pré-natal | Suscetível: a cada trimestre')]
             if toxo_repetir else [])),
        (24, 29, '24-28 semanas', ([] if diabetica else [
            _rec('TOTG-75g gestacional (jejum, 1 h e 2 h), soro', 'laboratorio',
                 'Rastreio de diabetes gestacional para todas sem diagnóstico prévio. Critérios IADPSG/OMS: jejum ≥ 92, 1 h ≥ 180 ou 2 h ≥ 153 mg/dL (um valor basta).',
                 'Pré-natal | 24-28 semanas'),
        ]) + ([_rec('Coombs indireto, soro', 'laboratorio',
                    'Gestante Rh negativo: repetir com 28 semanas; se negativo, imunoglobulina anti-D com 28 semanas e até 72 h após o parto (se RN Rh positivo).',
                    'Pré-natal | Rh negativo: 28 semanas')] if rh_neg else [])),
        (28, 37, '28-36 semanas', [
            _rec('Hemograma completo', 'laboratorio', 'Rastreio de anemia no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
            _rec('Urocultura com antibiograma', 'laboratorio', 'Bacteriúria assintomática.', 'Pré-natal | 28-36 semanas'),
            _rec('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
            _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Repetir no 3º trimestre.', 'Pré-natal | 28-36 semanas'),
            _rec('HBsAg, soro', 'laboratorio', 'Repetir no 3º trimestre (Einstein/MS).', 'Pré-natal | 28-36 semanas', prioridade='media'),
            _rec('Ultrassonografia obstétrica com Doppler', 'imagem', 'Crescimento e vitalidade fetal (protocolo Einstein).',
                 'Pré-natal | 28-36 semanas', prioridade='media', grau='B'),
        ] + ([_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio',
                   'Repetir a cada trimestre enquanto suscetível (IgG negativa).', 'Pré-natal | Suscetível: a cada trimestre')]
             if toxo_repetir else [])),
        (35, 38, '35-37 semanas', [
            _rec('Cultura para estreptococo do grupo B (swab vaginal e retal)', 'laboratorio',
                 'Define antibioticoprofilaxia intraparto. Einstein: 35-37 semanas; ACOG: 36+0 a 37+6 semanas.',
                 'Pré-natal | 35-37 semanas'),
        ]),
    ]
    return janelas


def _primeira_consulta(g, idade, hipertensa, diabetica):
    recs = [
        _rec('Hemograma completo', 'laboratorio', 'Rastreio de anemia.', 'Pré-natal | 1ª consulta'),
        _rec('Glicemia de jejum, soro', 'laboratorio',
             'Diabetes prévio se ≥ 126 mg/dL; diabetes gestacional se 92-125 mg/dL (IADPSG).', 'Pré-natal | 1ª consulta'),
        _rec('EAS - Elementos Anormais e Sedimentoscopia', 'laboratorio', 'Urina tipo I.', 'Pré-natal | 1ª consulta'),
        _rec('Urocultura com antibiograma', 'laboratorio', 'Bacteriúria assintomática.', 'Pré-natal | 1ª consulta'),
        _rec('HIV 1/2 (anticorpos e antígeno p24), soro', 'laboratorio', 'Transmissão vertical.', 'Pré-natal | 1ª consulta'),
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
    if g['rh'] == 'negativo':
        recs.append(_rec('Coombs indireto, soro', 'laboratorio', 'Gestante Rh negativo.', 'Pré-natal | 1ª consulta'))
    if g['toxo'] != 'imune':
        recs.append(_rec('Toxoplasmose IgG e IgM, soro', 'laboratorio', 'Suscetível: repetir a cada trimestre.', 'Pré-natal | 1ª consulta'))
    if idade < 25:
        recs.append(_rec('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
                         'Rastreio para menores de 25 anos ou com fator de risco; repetir no 3º trimestre se risco.',
                         'Pré-natal | 1ª consulta | < 25 anos', grau='B',
                         referencia='USPSTF 2021 / Williams 26e'))
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


def exames(g, idade, hipertensa=False, diabetica=False):
    """Exames do pré-natal para a gestação ``g`` (saída de :func:`normalizar`)."""
    recs = []
    ig = g['ig']
    if g['primeira_consulta'] or ig is None:
        recs += _primeira_consulta(g, idade, hipertensa, diabetica)
    if ig is not None:
        janelas = _janelas(g, idade, hipertensa, diabetica)
        proxima_marcada = False
        for inicio, fim, nome, itens in janelas:
            atual = inicio <= ig < fim
            proxima = not proxima_marcada and ig < inicio
            if proxima:
                proxima_marcada = True
                itens = [{**r, 'subtitulo': r['subtitulo'] + f' | Deixar pedido para {nome}', 'prioridade': 'media'} for r in itens]
            if atual or proxima:
                recs += itens
    recs += _risco_pre_eclampsia(g, hipertensa, diabetica)
    vistos, unicos = set(), []
    for r in recs:
        if r['titulo'] in vistos:
            continue
        vistos.add(r['titulo'])
        unicos.append(r)
    return unicos


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
