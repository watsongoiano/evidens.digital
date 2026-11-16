"""Pacientes simulados (fictícios): antiagregantes, DAPT e momento da cirurgia após ICP no módulo pré-operatório.

Confere ``preop_medicamentos.condutas`` (AAS, clopidogrel, ticagrelor, prasugrel e combinações) e
``preoperatorio.adiamentos``/``avaliar`` (prazos após angioplastia) contra um ORÁCULO INDEPENDENTE, escrito a partir das
fontes primárias, e não da lógica do módulo:

- AHA/ACC 2024 (reafirmada em 2026), §7.5 recs. 1–12 e Tabela 12. https://doi.org/10.1161/CIR.0000000000001285
    rec. 2 balão ≥14 d (1, C-LD); rec. 3 DES por SCA ≥12 m (1, B-NR); rec. 4 DES por DAC crônica ≥6 m (2a, B-NR);
    rec. 5 tempo-sensível ≥3 m após DES (2b, B-NR); rec. 6 BMS/DES ≤30 d com interrupção = dano (3: Dano, B-NR);
    rec. 7 manter AAS após ICP (1, B-R); rec. 8 tempo-sensível ≤30 d de BMS ou <3 m de DES: manter DAPT (1, B-NR);
    rec. 11 DAC crônica sem ICP: AAS em selecionados (2b, B-R). Tabela 12: AAS 4 d; clopidogrel 5–7 d;
    prasugrel 7–10 d; ticagrelor 3–5 d.
- SBC 2024 (Gualandro et al.), Quadros 11, 12, 14 e 20–23. https://doi.org/10.36660/abc.20240590
    Q20: AAS primária suspender 7 d (I-A); secundária manter 100 mg (I-A), exceto neurocirurgia/risco proibitivo;
    monoterapia: clopidogrel manter no baixo risco e suspender 5 d no moderado/alto (IIb-C), ticagrelor 5 d (IIb-C),
    prasugrel 7 d (IIb-C). Q21 (DAP): AAS mantido (I-A); clopidogrel/ticagrelor 5 d (I-B); prasugrel 7 d (I-B); baixo
    sangramento na vigência da DAP se ICP <3 m (IIa-C). Q22 ICP eletiva: ≥6 m I-A, 3–6 m IIa-B, 30 d–3 m IIb-B,
    <30 d III-B. Q23 SCA: ≥12 m I-A, 6–12 m IIa-B, 30 d–6 m IIb-B, <30 d III-B. Q11 odontologia e Q14 catarata: manter
    a antiagregação (IIa-B).
- ESC 2022 (Halvorsen et al.). https://doi.org/10.1093/eurheartj/ehac270 — ticagrelor 3–5 d, clopidogrel 5 d,
    prasugrel 7 d (I-B); adiar a eletiva até 6 m após ICP eletiva e 12 m após SCA (I-A), qualquer stent.
- ASRA 2018 (4ª ed.). https://doi.org/10.1097/AAP.0000000000000763 — antes de bloqueio neuroaxial: clopidogrel 5–7 d,
    ticagrelor 5–7 d, prasugrel 7–10 d.
- Contexto de duração da DAPT: ACC/AHA 2025 SCA https://doi.org/10.1161/CIR.0000000000001309 e AHA/ACC 2023 DAC
    crônica https://doi.org/10.1161/CIR.0000000000001168.

Discordância do módulo com o oráculo = ``xfail(strict=True)`` com a fonte, para a suíte ficar verde e o xfail virar
falha quando o módulo for corrigido. Relatório: /tmp/validacao/casos-antiplaquetarios.md. Pacientes fictícios.
"""
import re
from datetime import date, timedelta

import pytest

from src.utils import preop_medicamentos as pm
from src.utils import preoperatorio as po

HOJE = date(2026, 11, 16)
AAS, CLOPI, TICA, PRASU = 'aas_acido_acetilsalicilico', 'clopidogrel', 'ticagrelor', 'prasugrel'
P2Y12 = (CLOPI, TICA, PRASU)

# ── Oráculo (fontes primárias) ──────────────────────────────────────────────────────────────────────────────────
DIAS_SBC = {CLOPI: 5, TICA: 5, PRASU: 7}                          # SBC Quadros 20–21
FAIXA_AHA = {CLOPI: (5, 7), TICA: (3, 5), PRASU: (7, 10)}          # AHA Tabela 12
FAIXA_ESC = {CLOPI: (5, 5), TICA: (3, 5), PRASU: (7, 7)}           # ESC 2022
FAIXA_ASRA = {CLOPI: (5, 7), TICA: (5, 7), PRASU: (7, 10)}         # ASRA 2018, neuroaxial
TEXTO_FAIXA_AHA = {CLOPI: '5–7', TICA: '3–5', PRASU: '7–10'}
AAS_PRIMARIA_DIAS, AAS_AHA_DIAS = 7, 4                             # SBC Quadro 20 · AHA Tabela 12
DIAS_POR_MES = 30.44
SECUNDARIA = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'avc_ait', 'avc_ait_recente',
              'doenca_arterial_periferica'}
DAC_SEM_ICP = {'dac', 'iam_previo', 'revascularizacao_cirurgica'}

REF = {
    'aha': 'AHA/ACC 2024 §7.5 (https://doi.org/10.1161/CIR.0000000000001285)',
    'sbc': 'SBC 2024 (https://doi.org/10.36660/abc.20240590)',
    'esc': 'ESC 2022 (https://doi.org/10.1093/eurheartj/ehac270)',
    'asra': 'ASRA 2018 (https://doi.org/10.1097/AAP.0000000000000763)',
}


def sbc_classe(indicacao, meses):
    """SBC Quadro 22 (ICP eletiva / DAC crônica) e Quadro 23 (SCA)."""
    faixas = ((12, 'I-A'), (6, 'IIa-B'), (1, 'IIb-B')) if indicacao == 'sca' else ((6, 'I-A'), (3, 'IIa-B'),
                                                                                   (1, 'IIb-B'))
    for limite, classe in faixas:
        if meses >= limite:
            return classe
    return 'III-B'


def _dias_icp(st):
    """Dias desde a ICP: 'dias' (tela, data exata) ou 'meses' × 30,44."""
    if st.get('dias') is not None:
        return float(st['dias'])
    return None if st.get('meses') is None else st['meses'] * DIAS_POR_MES


def oraculo_p2y12(droga, meds, ctx):
    """Conduta esperada para o inibidor de P2Y12, a partir das recomendações (ver o cabeçalho)."""
    d = DIAS_SBC[droga]
    dapt = AAS in meds
    urg = ctx.get('urgencia') or 'eletiva'
    sang = 'alto' if ctx.get('neuroaxial') else ctx.get('sangramento')     # neuroaxial = sangramento alto (SBC/AHA)
    st, cond = ctx.get('stent'), set(ctx.get('condicoes') or ())
    nao_espera = urg in ('urgencia', 'emergencia')

    def e(acao, classe=(), proibidas=(), divergencia=False):
        return {'acao': acao, 'dias': d, 'classe': list(classe), 'proibidas': list(proibidas),
                'divergencia': divergencia}

    janela, classe_j, proib_j, div_j = None, [], [], False      # dentro do período de risco após a ICP?
    if st is None and 'stent' in cond:
        return e('individualizar')
    if st:
        tipo, ind = st.get('tipo'), st.get('indicacao')
        dias_icp = _dias_icp(st)
        if tipo is None or dias_icp is None:
            return e('individualizar')
        m = dias_icp / DIAS_POR_MES
        if nao_espera and dias_icp < 365:
            # Cirurgia que não espera: manter o AAS e, se o sangramento permitir, o P2Y12; centro com hemodinâmica
            # (SBC Q21 I-C). Stent ≤30 d ou DES <3 m: manter a DAPT (AHA rec. 8, 1 B-NR).
            classe = ['SBC I-C']
            if (tipo != 'balao' and dias_icp <= 30) or (tipo == 'farmacologico' and m < 3):
                classe.append('AHA 1 (B-NR)')
            return e('sem_suspensao_programada', classe)
        if tipo == 'balao':
            if dias_icp < 14 and not nao_espera:                                 # AHA rec. 2
                janela, classe_j = 'adiar', ['AHA 1 (C-LD)']
        elif dias_icp <= 30:                                                     # AHA recs. 6 e 8; SBC III-B
            if urg == 'eletiva':
                janela, classe_j = 'dano', ['3: Dano', 'III-B']
            elif not nao_espera:
                janela, classe_j = 'manter_dapt', ['AHA 1 (B-NR)']
        elif urg == 'tempo_sensivel':
            if tipo == 'farmacologico' and m < 3:                                # AHA rec. 8
                janela, classe_j = 'manter_dapt', ['AHA 1 (B-NR)']
        elif urg == 'eletiva':
            ind_ef = ind or 'sca'                       # sem indicação, a janela mais longa (SCA)
            if m < (12 if ind_ef == 'sca' else 6):      # AHA recs. 3–4 (DES); SBC Q22–23 e ESC (qualquer stent)
                janela = 'adiar'
                if tipo == 'farmacologico':
                    classe_j = ['AHA 1 (B-NR)' if ind_ef == 'sca' else 'AHA 2a (B-NR)', 'SBC ' + sbc_classe(ind_ef, m)]
                else:                                   # a AHA não dá classe ao BMS após 30 dias
                    classe_j, proib_j, div_j = ['SBC ' + sbc_classe(ind_ef, m)], ['AHA 1', 'AHA 2a'], True
    # Sangramento mínimo (catarata, odontologia): não se interrompe a antiagregação (SBC Q11/Q14 IIa-B; Q21 IIa-C);
    # os prazos pós-ICP da AHA (recs. 3–6) valem para cirurgia "com interrupção de ≥1 antiagregante".
    if sang == 'minimo':
        if janela:
            return e('manter_min', ['SBC IIa'])
        return e('manter_min') if (dapt or droga == CLOPI) else e('individualizar')
    if janela:
        return e(janela, classe_j, proib_j, div_j)
    if nao_espera:                                                               # sem tempo para 5–7 dias; SBC Q21 I-C
        return e('sem_suspensao_programada')
    if sang is None:
        return e('individualizar')
    if droga == CLOPI and not dapt and sang == 'baixo_moderado':                 # SBC Q20 IIb-C
        return e('individualizar')
    return e('suspender', ['SBC I-B' if dapt else 'SBC IIb-C'])


def oraculo_aas(meds, ctx):
    """Conduta esperada para o AAS: SBC Q20/Q21 e texto 4.1.3.1; AHA §7.5 recs. 7 e 11; ESC 2022."""
    cond = set(ctx.get('condicoes') or ())
    icp = bool(ctx.get('stent')) or 'stent' in cond
    dapt = any(m in meds for m in P2Y12)
    secundaria = icp or bool(cond & SECUNDARIA) or ctx.get('aas_indicacao') == 'secundaria' or dapt
    cirurgia = ctx.get('cirurgia')
    if secundaria and cirurgia == 'neurocirurgia':      # SBC Q20/Q21 (exceção) e texto; ESC 2022: 7 dias
        return {'acao': 'suspender', 'classe': [], 'dias': AAS_PRIMARIA_DIAS,
                'texto': ['stent recente'] if icp else []}
    if secundaria and cirurgia == 'rtu':                # SBC texto 4.1.3.1: RTU de próstata 7 d; bexiga: manter
        return {'acao': 'individualizar', 'classe': [], 'texto': ['próstata', '7 dias', 'bexiga']}
    if icp:
        return {'acao': 'manter', 'classe': ['AHA 1 (B-R)', 'SBC I-A']}
    if cond & DAC_SEM_ICP:
        return {'acao': 'manter', 'classe': ['AHA 2b (B-R)', 'SBC I-A'], 'divergencia': True}
    if secundaria:                                      # inclui DAPT, que nunca é prevenção primária
        return {'acao': 'manter', 'classe': ['SBC I-A']}
    if ctx.get('aas_indicacao') == 'primaria':
        return {'acao': 'suspender', 'classe': ['SBC I-A'], 'dias': AAS_PRIMARIA_DIAS, 'primaria': True}
    return {'acao': 'individualizar', 'classe': []}


# ── Leitura da saída ───────────────────────────────────────────────────────────────────────────────────────────
_RE_SUSP = re.compile(r'suspender (?:o \w+ )?(\d+) dias', re.I)
TEXTO_FAIXA_ASRA = {CLOPI: '5–7', TICA: '5–7', PRASU: '7–10'}


def dias_em(texto):
    m = _RE_SUSP.search(texto or '')
    return int(m.group(1)) if m else None


def confere_p2y12(item, esp, droga, ctx):
    acao, d = esp['acao'], esp['dias']
    resumo, texto, classe = item['resumo'], item['texto'], item['classe']
    tudo = ' '.join((resumo, texto, item['divergencia']))
    if acao == 'suspender':
        assert item['conduta'] == 'suspender', (resumo, texto)
        achado = dias_em(resumo)
        assert achado == d, resumo
        lo, hi = FAIXA_AHA[droga]
        assert lo <= achado <= hi and FAIXA_ESC[droga][0] <= achado <= FAIXA_ESC[droga][1]
        assert TEXTO_FAIXA_AHA[droga] in tudo, 'a faixa da AHA (Tabela 12) deve aparecer'
        if ctx.get('neuroaxial'):
            assert FAIXA_ASRA[droga][0] <= achado <= FAIXA_ASRA[droga][1]
            assert 'ASRA' in tudo and TEXTO_FAIXA_ASRA[droga] in tudo, 'neuroaxial: o intervalo da ASRA deve aparecer'
        assert 'AAS' in texto if AAS in ctx.get('_meds', ()) else True
    elif acao == 'adiar':
        assert item['conduta'] == 'individualizar', resumo
        assert 'adiar' in resumo.lower(), resumo
        assert dias_em(resumo) == d, resumo
    elif acao == 'dano':
        assert item['conduta'] != 'suspender', resumo
        assert dias_em(resumo) is None, f'≤30 dias: não pode orientar suspensão ({resumo})'
        assert '3: Dano' in classe or 'danosa' in texto, (classe, texto)
    elif acao == 'manter_dapt':
        assert item['conduta'] == 'manter' and 'DAPT' in resumo, resumo
        assert dias_em(resumo) is None
    elif acao == 'manter_min':
        assert item['conduta'] in ('manter', 'individualizar'), resumo
        assert dias_em(resumo) is None, f'sangramento mínimo: não suspender ({resumo})'
        assert 'manter' in (resumo + ' ' + texto).lower()
    elif acao == 'sem_suspensao_programada':
        assert item['conduta'] != 'suspender', resumo
        assert dias_em(resumo) is None, f'urgência/emergência: sem suspensão programada de dias ({resumo})'
        assert 'adiar' not in resumo.lower(), resumo
    elif acao == 'individualizar':
        assert item['conduta'] == 'individualizar', resumo
        achado = dias_em(resumo) or dias_em(texto)
        assert achado in (None, d), (resumo, texto)
    else:  # pragma: no cover
        raise AssertionError(acao)
    for parte in esp['classe']:
        assert parte in classe, (parte, classe)
    for parte in esp['proibidas']:
        assert parte not in classe, (parte, classe)
    if esp['divergencia']:
        assert item['divergencia'], 'a divergência entre as fontes deve aparecer'


def confere_aas(item, esp):
    assert item['conduta'] == esp['acao'], (item['conduta'], item['resumo'], esp)
    for parte in esp['classe']:
        assert parte in item['classe'], (parte, item['classe'])
    for parte in esp.get('texto', ()):
        assert parte in item['texto'], (parte, item['texto'])
    if esp['acao'] == 'manter':
        assert 'neurocirurgia' in item['texto'], 'exceção da SBC (Q20/Q21) deve aparecer'
        if esp.get('divergencia'):
            assert item['divergencia'], 'AHA 2b × SBC I-A deve aparecer como divergência'
    if esp['acao'] == 'suspender':
        assert dias_em(item['resumo']) == esp['dias'], item['resumo']
        if esp.get('primaria'):
            assert f'{AAS_AHA_DIAS} dias' in item['divergencia'], 'divergência com a AHA (Tabela 12: 4 d) deve aparecer'


def confere_avisos(avisos, meds, ctx, esperados):
    st, cond = ctx.get('stent'), set(ctx.get('condicoes') or ())
    if ctx.get('neuroaxial') and any(m in P2Y12 for m in meds):
        neuro = [a for a in avisos if a['titulo'].startswith('Anestesia neuroaxial')]
        assert neuro, 'neuroaxial com P2Y12: o aviso neuroaxial deve aparecer'
        assert 'ASRA' in neuro[0]['texto'] and 'não definem' not in neuro[0]['texto'], neuro[0]['texto']
    if not (st or 'stent' in cond):
        assert not any(a['titulo'] == 'Momento da cirurgia após ICP' for a in avisos)
        return
    icp = [a for a in avisos if a['titulo'] == 'Momento da cirurgia após ICP']
    assert icp, 'com ICP prévia, o aviso sobre o momento da cirurgia deve aparecer'
    texto = icp[0]['texto'] + ' ' + icp[0]['divergencia']
    for parte in esperados:
        assert parte in texto, (parte, texto)


def oraculo_aviso_icp(ctx):
    """O que o aviso "Momento da cirurgia após ICP" tem de citar (AHA §7.5 recs. 2–8; SBC Q21–23)."""
    st = ctx.get('stent')
    if not st:
        return []
    tipo, ind = st.get('tipo'), st.get('indicacao')
    dias_icp = _dias_icp(st)
    urg = ctx.get('urgencia') or 'eletiva'
    if tipo is None or dias_icp is None:
        return ['Falta']
    if urg in ('urgencia', 'emergencia'):
        return ['Quadro 21', 'I-C'] if dias_icp < 365 else []
    if tipo == 'balao':
        return ['14 dias']
    if dias_icp <= 30:
        return ['3: Dano', 'III-B']                                 # AHA rec. 6; SBC Q22–23 (<30 d)
    m, ind_ef = dias_icp / DIAS_POR_MES, ind or 'sca'
    saida = [sbc_classe(ind_ef, m), 'Quadro 23' if ind_ef == 'sca' else 'Quadro 22']
    if ind is None:
        saida.append('SCA')
    if tipo == 'farmacologico':
        if urg == 'tempo_sensivel':
            saida.append('(2b, B-NR)' if m >= 3 else '(1, B-NR)')
        else:
            saida.append('(1, B-NR)' if ind_ef == 'sca' else '(2a, B-NR)')
    return saida


def avalia(meds, ctx):
    r = pm.condutas(meds, ctx)
    itens = {i['chave']: i for i in r['itens']}
    for droga in meds:
        if droga == AAS:
            confere_aas(itens[AAS], oraculo_aas(meds, ctx))
        elif droga in P2Y12:
            confere_p2y12(itens[droga], oraculo_p2y12(droga, meds, ctx), droga, dict(ctx, _meds=meds))
    confere_avisos(r['avisos'], meds, ctx, oraculo_aviso_icp(ctx))
    # Após ICP, o paciente não pode ficar sem antiagregante sem que isso seja dito (AHA rec. 7, 1 B-R, e nota: P2Y12
    # em monoterapia no lugar do AAS; rec. 9: AAS no lugar do anticoagulante suspenso).
    mono = [d for d in meds if d in P2Y12] if AAS not in meds else []
    if ctx.get('stent') and mono:
        suspende = [itens[d] for d in mono if dias_em(itens[d]['resumo']) or dias_em(itens[d]['texto'])]
        if suspende:
            textos = ' '.join([i['texto'] + ' ' + i['divergencia'] for i in suspende]
                              + [a['texto'] for a in r['avisos']])
            assert 'AAS' in textos, 'P2Y12 em monoterapia após ICP: suspender sem citar o AAS deixa o stent sem proteção'
    return r


# ── Pacientes (condutas) ───────────────────────────────────────────────────────────────────────────────────────
def xf(motivo):
    return pytest.mark.xfail(strict=True, reason=motivo)


def stent(tipo, indicacao, meses):
    return {'tipo': tipo, 'indicacao': indicacao, 'meses': meses}


_ROT = {'farmacologico': 'DES', 'convencional': 'BMS', 'balao': 'balao', None: 'tipo?'}
_ROT_IND = {'sca': 'SCA', 'dac_cronica': 'DACcr', None: 'ind?'}
_ROT_MED = {AAS: 'AAS', CLOPI: 'clopi', TICA: 'tica', PRASU: 'prasu'}


def _rot_meses(m):
    return 'mes?' if m is None else f'{m:g}m'


CASOS = []


def caso(meds, marca=None, rotulo='', **ctx):
    n = len(CASOS) + 1
    partes = [f'P{n:03d}']
    st = ctx.get('stent')
    if st:
        partes.append(f'{_ROT[st.get("tipo")]}-{_ROT_IND[st.get("indicacao")]}-{_rot_meses(st.get("meses"))}')
    if rotulo:
        partes.append(rotulo)
    partes.append(ctx.get('urgencia') or 'eletiva')
    partes.append('sang-' + (ctx.get('sangramento') or 'nd'))
    if ctx.get('neuroaxial'):
        partes.append('neuroaxial')
    if ctx.get('cirurgia'):
        partes.append(ctx['cirurgia'])
    partes.append('+'.join(_ROT_MED[m] for m in meds))
    ctx['condicoes'] = set(ctx.get('condicoes') or ()) | ({'stent', 'dac'} if st else set())
    CASOS.append(pytest.param(list(meds), ctx, id='-'.join(partes), marks=[marca] if marca else []))


MESES = (0, 0.5, 1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 24, None)

# A. DES por SCA, eletiva, sangramento alto, AAS + ticagrelor: todos os intervalos (AHA rec. 3; SBC Q23)
for m in MESES:
    caso([AAS, TICA], stent=stent('farmacologico', 'sca', m), urgencia='eletiva', sangramento='alto')
# B. DES por DAC crônica, eletiva, sangramento baixo/moderado, AAS + clopidogrel (AHA rec. 4; SBC Q22)
for m in MESES:
    caso([AAS, CLOPI], stent=stent('farmacologico', 'dac_cronica', m), urgencia='eletiva',
         sangramento='baixo_moderado')
# C. DES por SCA, cirurgia tempo-sensível, AAS + prasugrel (AHA recs. 5 e 8)
for m in (0, 0.5, 1, 2, 3, 4, 7, 13):
    caso([AAS, PRASU], stent=stent('farmacologico', 'sca', m), urgencia='tempo_sensivel', sangramento='alto')
# D. DES, urgência e emergência (sem tempo para suspensão programada; SBC Q21 I-C; AHA rec. 8)
for m in (0.5, 2, 4, 13):
    caso([AAS, CLOPI], stent=stent('farmacologico', 'dac_cronica', m), urgencia='urgencia', sangramento='alto')
for m in (0, 2, 8):
    caso([AAS, TICA], stent=stent('farmacologico', 'sca', m), urgencia='emergencia', sangramento='alto')

# E. Stent convencional (BMS): janela pela indicação (SBC Q22–23; ESC 2022), sem classe da AHA após 30 dias
for m in (0, 0.5, 7, 24, None):
    caso([AAS, CLOPI], stent=stent('convencional', 'dac_cronica', m), urgencia='eletiva', sangramento='alto')
for m in (1, 2):
    caso([AAS, CLOPI], stent=stent('convencional', 'dac_cronica', m), urgencia='eletiva', sangramento='alto')
caso([AAS, CLOPI], stent=stent('convencional', 'sca', 0.5), urgencia='eletiva', sangramento='baixo_moderado')
caso([AAS, CLOPI], stent=stent('convencional', 'sca', 8), urgencia='eletiva', sangramento='baixo_moderado')
caso([AAS, CLOPI], stent=stent('convencional', 'sca', 13), urgencia='eletiva', sangramento='baixo_moderado')
caso([AAS, CLOPI], stent=stent('convencional', 'dac_cronica', 0.5), urgencia='tempo_sensivel', sangramento='alto')
caso([AAS, CLOPI], stent=stent('convencional', 'dac_cronica', 2), urgencia='tempo_sensivel', sangramento='alto')

# F. Angioplastia só com balão (AHA rec. 2: ≥14 dias)
for m in (0.2, 0.4, 0.5, 1, 6):
    caso([AAS, CLOPI], stent=stent('balao', 'dac_cronica', m), urgencia='eletiva', sangramento='alto')
caso([AAS, CLOPI], stent=stent('balao', 'sca', 0.3), urgencia='tempo_sensivel', sangramento='alto')
caso([AAS, CLOPI], stent=stent('balao', 'sca', 0.3), urgencia='emergencia', sangramento='alto')
caso([AAS, TICA], stent=stent('balao', 'dac_cronica', 0.2), urgencia='urgencia', sangramento='alto')

# G. Dados do stent incompletos
caso([AAS, TICA], stent=stent(None, None, None), urgencia='eletiva', sangramento='alto', rotulo='stent-vazio')
caso([AAS, CLOPI], condicoes={'stent', 'dac'}, urgencia='eletiva', sangramento='alto', rotulo='stent-sem-dados')
caso([AAS, CLOPI], stent=stent(None, 'dac_cronica', 4), urgencia='eletiva', sangramento='alto')
for m in (0.5, 4, 13):
    caso([AAS, PRASU], stent=stent('farmacologico', None, m), urgencia='eletiva', sangramento='alto')

# H. Sangramento mínimo (catarata, odontologia): manter a antiagregação (SBC Q11, Q14, Q21)
caso([AAS, TICA], stent=stent('farmacologico', 'sca', 2), urgencia='eletiva', sangramento='minimo',
     rotulo='catarata')
caso([AAS, CLOPI], stent=stent('farmacologico', 'dac_cronica', 4), urgencia='eletiva',
     sangramento='minimo', rotulo='odonto')
caso([AAS, CLOPI], stent=stent('convencional', 'dac_cronica', 0.5), urgencia='eletiva', sangramento='minimo',
     rotulo='odonto')
caso([AAS, PRASU], stent=stent('farmacologico', 'sca', 24), urgencia='eletiva', sangramento='minimo',
     rotulo='catarata')

# I. Sem ICP: DAPT e monoterapia de P2Y12 por risco de sangramento
for s in ('minimo', 'baixo_moderado', 'alto', None):
    caso([AAS, CLOPI], condicoes={'dac', 'iam_previo'}, urgencia='eletiva', sangramento=s, rotulo='IAM-sem-ICP')
for s in ('minimo', 'alto'):
    caso([AAS, TICA], condicoes={'iam_previo'}, urgencia='eletiva', sangramento=s, rotulo='IAM-sem-ICP')
for s in ('baixo_moderado', 'alto'):
    caso([AAS, PRASU], condicoes={'iam_previo'}, urgencia='eletiva', sangramento=s, rotulo='IAM-sem-ICP')
for s in ('minimo', 'baixo_moderado', 'alto', None):
    caso([CLOPI], condicoes={'avc_ait'}, urgencia='eletiva', sangramento=s, rotulo='AVC-mono')
for s in ('minimo', 'baixo_moderado', 'alto'):
    caso([TICA], condicoes={'iam_previo'}, urgencia='eletiva', sangramento=s, rotulo='intolerante-AAS')
for s in ('minimo', 'alto'):
    caso([PRASU], condicoes={'dac'}, urgencia='eletiva', sangramento=s, rotulo='intolerante-AAS')
_XF_MONO = xf('P2Y12 em monoterapia após ICP (estratégia prevista na ACC/AHA 2025 de SCA — ticagrelor isolado ≥1 mês '
              'após a ICP — e na AHA/ACC 2023 de DAC crônica — P2Y12 isolado após 1–3 meses de DAPT): o módulo manda '
              'suspender o único antiagregante sem dizer que o paciente com stent fica sem proteção nem considerar o '
              'AAS no período. AHA §7.5 rec. 7 (manter antiagregante após ICP, 1 B-R; nota: P2Y12 isolado no lugar do '
              'AAS) e, por analogia, rec. 9 (AAS no lugar do anticoagulante suspenso). ' + REF['aha']
              + '; https://doi.org/10.1161/CIR.0000000000001309; https://doi.org/10.1161/CIR.0000000000001168')
caso([CLOPI], _XF_MONO, stent=stent('farmacologico', 'dac_cronica', 24), urgencia='eletiva',
     sangramento='baixo_moderado', rotulo='mono-P2Y12')
caso([TICA], _XF_MONO, stent=stent('farmacologico', 'sca', 4), urgencia='eletiva', sangramento='alto',
     rotulo='mono-tica-pos-1m')
caso([PRASU], _XF_MONO, stent=stent('farmacologico', 'sca', 13), urgencia='eletiva', sangramento='alto',
     rotulo='mono-P2Y12')
caso([TICA], stent=stent('farmacologico', 'sca', 0.5), urgencia='eletiva', sangramento='baixo_moderado',
     rotulo='mono-P2Y12')
caso([AAS, CLOPI], condicoes={'doenca_arterial_periferica'}, urgencia='urgencia', sangramento='alto', rotulo='DAP')
caso([TICA], condicoes={'iam_previo'}, urgencia='emergencia', sangramento='alto', rotulo='mono')
caso([AAS, TICA], condicoes={'iam_previo'}, urgencia='tempo_sensivel', sangramento='baixo_moderado',
     rotulo='IAM-sem-ICP')

# J. Anestesia neuroaxial (= sangramento alto; ASRA: clopidogrel 5–7 d, ticagrelor 5–7 d, prasugrel 7–10 d)
caso([CLOPI], condicoes={'avc_ait'}, urgencia='eletiva', sangramento='baixo_moderado', neuroaxial=True,
     rotulo='raqui-hernia')
caso([AAS, TICA], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='baixo_moderado', neuroaxial=True,
     rotulo='raqui-joelho')
caso([AAS, PRASU], stent=stent('farmacologico', 'sca', 14), urgencia='eletiva', sangramento='baixo_moderado',
     neuroaxial=True)
caso([CLOPI], condicoes={'avc_ait'}, urgencia='eletiva', sangramento='minimo', neuroaxial=True,
     rotulo='raqui-com-sang-minimo')

# K. AAS isolado
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='minimo', rotulo='primaria-catarata')
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='baixo_moderado', rotulo='primaria')
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='alto', rotulo='primaria')
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='baixo_moderado', neuroaxial=True,
     rotulo='primaria')
caso([AAS], aas_indicacao='secundaria', urgencia='eletiva', sangramento='alto', rotulo='secundaria-declarada')
caso([AAS], condicoes={'dac'}, urgencia='eletiva', sangramento='alto', rotulo='DAC-sem-ICP')
caso([AAS], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='baixo_moderado', rotulo='IAM-sem-ICP')
caso([AAS], condicoes={'revascularizacao_cirurgica'}, urgencia='eletiva', sangramento='alto', rotulo='pos-CRM')
caso([AAS], condicoes={'avc_ait'}, urgencia='eletiva', sangramento='alto', rotulo='AVC')
caso([AAS], condicoes={'doenca_arterial_periferica'}, urgencia='eletiva', sangramento='alto', rotulo='DAP')
caso([AAS], stent=stent('farmacologico', 'dac_cronica', 24), urgencia='eletiva', sangramento='alto')
caso([AAS], stent=stent('convencional', 'dac_cronica', 0.5), urgencia='eletiva', sangramento='alto')
caso([AAS], condicoes={'dac'}, urgencia='eletiva', sangramento='minimo', rotulo='odonto')
caso([AAS], stent=stent('farmacologico', 'sca', 13), urgencia='eletiva', sangramento='minimo', rotulo='catarata')
caso([AAS], condicoes={'avc_ait'}, urgencia='emergencia', sangramento='alto', rotulo='AVC')
caso([AAS], urgencia='eletiva', sangramento='alto', rotulo='sem-indicacao')
caso([AAS], aas_indicacao='primaria', stent=stent('farmacologico', 'dac_cronica', 24),
     urgencia='eletiva', sangramento='alto', rotulo='rotulo-primaria')
caso([AAS], aas_indicacao='primaria', condicoes={'iam_previo'}, urgencia='eletiva', sangramento='alto',
     rotulo='rotulo-primaria-IAM')
caso([AAS, CLOPI], aas_indicacao='primaria', urgencia='eletiva', sangramento='alto',
     rotulo='rotulo-primaria-DAPT')
caso([AAS, CLOPI],
     urgencia='eletiva', sangramento='alto', rotulo='DAPT-sem-indicacao')

# L. Combinações de três antiagregantes / P2Y12 duplicado (entrada atípica: cada fármaco recebe sua conduta)
caso([AAS, CLOPI, TICA], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='alto', rotulo='troca-P2Y12')
caso([CLOPI, PRASU], condicoes={'dac'}, urgencia='eletiva', sangramento='alto', rotulo='troca-P2Y12')

# M. Cirurgias com regra própria para o AAS (SBC Q20/Q21 e texto 4.1.3.1; ESC 2022)
caso([AAS], condicoes={'avc_ait'}, aas_indicacao='secundaria', urgencia='eletiva', sangramento='alto',
     cirurgia='neurocirurgia', rotulo='AVC')
caso([AAS, CLOPI], stent=stent('farmacologico', 'dac_cronica', 24), urgencia='eletiva', sangramento='alto',
     cirurgia='neurocirurgia')
caso([AAS, PRASU], stent=stent('farmacologico', 'sca', 2), urgencia='eletiva', sangramento='alto',
     cirurgia='neurocirurgia')
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='alto', cirurgia='neurocirurgia',
     rotulo='primaria')
caso([AAS], condicoes={'dac'}, urgencia='eletiva', sangramento='baixo_moderado', cirurgia='rtu', rotulo='DAC')
caso([AAS, TICA], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='baixo_moderado', cirurgia='rtu',
     rotulo='IAM-sem-ICP')
caso([AAS], aas_indicacao='primaria', urgencia='eletiva', sangramento='baixo_moderado', cirurgia='rtu',
     rotulo='primaria')
caso([AAS], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='alto', cirurgia='coluna', rotulo='IAM')

# N. Mais combinações de janela, urgência e neuroaxial
caso([AAS, PRASU], condicoes={'iam_previo'}, urgencia='eletiva', sangramento='baixo_moderado', neuroaxial=True,
     rotulo='raqui')
caso([AAS, CLOPI], stent=stent('convencional', None, 4), urgencia='eletiva', sangramento='alto')
caso([AAS, TICA], stent=stent('convencional', 'sca', 0.5), urgencia='urgencia', sangramento='alto')
caso([AAS, CLOPI], stent=stent('balao', 'dac_cronica', 2), urgencia='emergencia', sangramento='alto')
caso([AAS, TICA], stent=stent('farmacologico', 'sca', 1), urgencia='eletiva', sangramento='minimo',
     rotulo='injecao-intravitrea')
caso([AAS, CLOPI], stent=stent('farmacologico', 'dac_cronica', 0), urgencia='eletiva', sangramento='minimo',
     rotulo='odonto')


@pytest.mark.parametrize('meds, ctx', CASOS)
def test_conduta_antiagregante_contra_o_oraculo(meds, ctx):
    avalia(meds, ctx)


# ── Exceção da neurocirurgia (SBC Q20/Q21; ESC 2022) ──────────────────────────────────────────────────────────────
def test_P900_aas_secundario_texto_cita_excecao_da_neurocirurgia():
    i = pm.condutas([AAS], {'condicoes': {'stent', 'dac'}, 'sangramento': 'alto',
                            'stent': stent('farmacologico', 'dac_cronica', 24)})['itens'][0]
    assert i['conduta'] == 'manter' and 'neurocirurgia' in i['texto'] and '7 dias' in i['texto']


def test_P901_aas_secundario_em_neurocirurgia_suspende_7_dias():
    """SBC Q20/Q21 (exceção) e texto 4.1.3.1; ESC 2022: AAS suspenso 7 dias na neurocirurgia."""
    i = pm.condutas([AAS], {'condicoes': {'avc_ait'}, 'aas_indicacao': 'secundaria', 'sangramento': 'alto',
                            'cirurgia': 'neurocirurgia'})['itens'][0]
    assert i['conduta'] == 'suspender' and dias_em(i['resumo']) == 7


def test_P902_dapt_mantida_com_neuroaxial_mostra_os_intervalos_da_asra():
    r = pm.condutas([AAS, TICA], {'condicoes': {'stent', 'dac'}, 'urgencia': 'tempo_sensivel', 'neuroaxial': True,
                                  'sangramento': 'baixo_moderado', 'stent': stent('farmacologico', 'sca', 2)})
    assert r['itens'][1]['resumo'] == 'Manter a DAPT'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Anestesia neuroaxial e antiagregantes')
    assert 'ASRA' in aviso['texto'] and '5–7 dias' in aviso['texto'] and '7–10 dias' in aviso['texto']


def test_P903_p2y12_mantido_com_neuroaxial_avisa_no_proprio_item():
    r = pm.condutas([AAS, TICA], {'condicoes': {'stent', 'dac'}, 'urgencia': 'tempo_sensivel', 'neuroaxial': True,
                                  'sangramento': 'baixo_moderado', 'stent': stent('farmacologico', 'sca', 2)})
    tica = r['itens'][1]
    assert tica['conduta'] == 'manter'
    assert 'neuroaxial' in (tica['texto'] + ' ' + tica['divergencia']).lower()


def test_P904_classe_da_excecao_da_neurocirurgia_e_a_da_fonte():
    i = pm.condutas([AAS], {'condicoes': {'avc_ait'}, 'aas_indicacao': 'secundaria', 'sangramento': 'alto',
                            'cirurgia': 'neurocirurgia'})['itens'][0]
    assert 'SBC I-C' not in i['classe'], i['classe']


def test_P905_coluna_sem_regra_propria_mantem_o_aas_e_cita_a_excecao():
    """Coluna: a SBC só excetua a neurocirurgia; a ESC 2022 inclui o canal medular (conflito de fontes, no relatório)."""
    i = pm.condutas([AAS], {'condicoes': {'iam_previo'}, 'sangramento': 'alto', 'cirurgia': 'coluna'})['itens'][0]
    assert i['conduta'] == 'manter' and 'neurocirurgia' in i['texto']


def test_oraculo_fontes_concordam_nos_dias_de_suspensao():
    """Sanidade do oráculo: os dias da SBC caem dentro das faixas da AHA (Tabela 12), da ESC e, na neuroaxial, ASRA."""
    for droga, d in DIAS_SBC.items():
        assert FAIXA_AHA[droga][0] <= d <= FAIXA_AHA[droga][1]
        assert FAIXA_ESC[droga][0] <= d <= FAIXA_ESC[droga][1]
        assert FAIXA_ASRA[droga][0] <= d <= FAIXA_ASRA[droga][1]


# ── Pacientes pela tela (preoperatorio.ler → adiamentos/avaliar → condutas) ─────────────────────────────────────
def data_ha(dias):
    return (HOJE - timedelta(days=dias)).isoformat()


def ler(stent_dados=None, urgencia='eletiva', cirurgia='hernia', **extra):
    dados = dict(idade=66, sexo='masculino', peso=80, cirurgia=cirurgia, urgencia=urgencia, **extra)
    if stent_dados is not None:
        dados.setdefault('condicoes', [])
        dados['condicoes'] = list(dados['condicoes']) + ['stent']
        dados['stent'] = stent_dados
    return po.ler(dados, hoje=HOJE)


def oraculo_adiamento(tipo, indicacao, dias, urgencia):
    """Prazos após angioplastia: AHA §7.5 recs. 2–6 e 8; SBC Q21–23; ESC 2022."""
    if urgencia in ('urgencia', 'emergencia'):
        return {'acao': 'sem_adiamento', 'retaguarda': dias is not None and dias < 365}
    if tipo is None:
        return {'acao': 'falta', 'termo': 'tipo'}
    if dias is None:
        return {'acao': 'falta', 'termo': 'data'}
    if tipo == 'balao':
        return {'acao': 'adiar', 'classe': ['AHA 1']} if dias < 14 else {'acao': 'ok'}
    if dias <= 30:
        return {'acao': 'dano', 'classe': ['AHA 3', 'SBC III']}
    ind = indicacao or 'sca'                                    # sem indicação: a janela mais longa (SCA)
    meses = dias / DIAS_POR_MES
    ideal = 12 if ind == 'sca' else 6
    if meses >= ideal:
        return {'acao': 'ok'}
    classe = ['SBC ' + sbc_classe(ind, meses).split('-')[0]]
    proibidas = []
    if tipo == 'farmacologico':
        classe.append('AHA 1' if ind == 'sca' else 'AHA 2a')
    else:
        proibidas = ['AHA 1', 'AHA 2a']                         # a AHA não dá classe ao BMS após 30 dias
    esp = {'acao': 'adiar', 'classe': classe, 'proibidas': proibidas}
    if indicacao is None:
        esp['texto'] = 'SCA'
    if urgencia == 'tempo_sensivel' and tipo == 'farmacologico':
        esp['texto'] = '3 meses'                                # AHA rec. 5 (2b)
    return esp


def confere_adiamento(saida, esp):
    pendentes = [a for a in saida if not a.get('ok')]
    acao = esp['acao']
    if acao == 'ok':
        assert not pendentes and saida and all(a.get('ok') for a in saida), saida
        return
    if acao == 'sem_adiamento':
        for a in pendentes:
            assert not re.search(r'\badiar\b|esperar', a['texto'].lower()), a
        if esp['retaguarda']:
            assert any('hemodin' in a['texto'].lower() and 'I-C' in a['classe'] for a in saida), saida
        return
    assert len(pendentes) == 1, saida
    a = pendentes[0]
    if acao == 'falta':
        assert 'não informad' in a['titulo'] and esp['termo'] in a['titulo'].lower(), a
        return
    for parte in esp.get('classe', ()):
        assert re.search(re.escape(parte) + r'(?![a-zI])', a['classe']), (parte, a['classe'])
    for parte in esp.get('proibidas', ()):
        assert parte not in a['classe'], (parte, a['classe'])
    if acao == 'dano':
        assert 'danosa' in a['texto'] or 'dano' in a['classe'].lower()
    if acao == 'adiar' and 'texto' in esp:
        assert esp['texto'] in a['texto'], (esp['texto'], a['texto'])


CASOS_TELA = []


def caso_tela(tipo, indicacao, dias, urgencia='eletiva', marca=None):
    n = 200 + len(CASOS_TELA) + 1
    rot = f'P{n:03d}-{_ROT[tipo]}-{_ROT_IND[indicacao]}-{"data?" if dias is None else f"{dias}d"}-{urgencia}'
    CASOS_TELA.append(pytest.param(tipo, indicacao, dias, urgencia, id=rot, marks=[marca] if marca else []))


for d in (5, 30, 31, 60, 150, 200, 340, 370, 800, None):
    caso_tela('farmacologico', 'sca', d)
for d in (10, 45, 80, 100, 170, 190, 400):
    caso_tela('farmacologico', 'dac_cronica', d)
for d in (20, 31, 60, 150, 200):
    caso_tela('convencional', 'dac_cronica', d)
for d in (90, 300, 400):
    caso_tela('convencional', 'sca', d)
for d in (5, 13, 14, 20, 60):
    caso_tela('balao', 'dac_cronica', d)
caso_tela('farmacologico', None, 100)
caso_tela('farmacologico', None, 400)
caso_tela('convencional', None, 200)
caso_tela(None, 'sca', 100)
caso_tela('farmacologico', 'sca', 20, 'urgencia')
caso_tela('farmacologico', 'dac_cronica', 60, 'emergencia')
caso_tela('convencional', 'sca', 10, 'emergencia')
caso_tela('balao', 'sca', 5, 'urgencia')
caso_tela('farmacologico', 'dac_cronica', 100, 'tempo_sensivel')
caso_tela('farmacologico', 'sca', 120, 'tempo_sensivel')
caso_tela('farmacologico', 'sca', 20, 'tempo_sensivel')


@pytest.mark.parametrize('tipo, indicacao, dias, urgencia', CASOS_TELA)
def test_adiamento_apos_angioplastia_contra_o_oraculo(tipo, indicacao, dias, urgencia):
    st = {'tipo': tipo, 'indicacao': indicacao}
    if dias is not None:
        st['data'] = data_ha(dias)
    p = ler(st, urgencia=urgencia)
    confere_adiamento(po.adiamentos(p), oraculo_adiamento(tipo, indicacao, dias, urgencia))


@pytest.mark.parametrize('data, esperado', [
    pytest.param('2026-10', 'dano', id='P250-DES-DACcr-mes-2026-10-menor-intervalo-16d-dano'),
    pytest.param('2026-11', 'dano', id='P254-DES-DACcr-mes-corrente-dano'),
    pytest.param('2026-05', 'adiar', id='P255-DES-DACcr-mes-2026-05-menor-intervalo-169d-adiar'),
    pytest.param('2025-11', 'ok', id='P256-DES-DACcr-mes-2025-11-ok'),
])
def test_data_so_com_mes_usa_o_menor_intervalo_possivel(data, esperado):
    """Data só com mês e ano: o lado seguro é o menor intervalo possível (último dia do mês, ou hoje no mês corrente)
    — AHA rec. 6 (≤30 d) e rec. 4 (≥6 m na DAC crônica)."""
    pend = [a for a in po.adiamentos(ler({'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': data}))
            if not a.get('ok')]
    if esperado == 'ok':
        assert not pend
    elif esperado == 'dano':
        assert len(pend) == 1 and 'AHA 3' in pend[0]['classe'], pend
    else:
        assert len(pend) == 1 and 'AHA 2a' in pend[0]['classe'] and 'SBC IIa' in pend[0]['classe'], pend


@pytest.mark.parametrize('dias, conclusao_com_adiamento', [
    pytest.param(60, True, id='P251-DES-DACcr-60d-hernia-conclusao-aponta-adiamento'),
    pytest.param(800, False, id='P252-DES-DACcr-800d-hernia-conclusao-sem-adiamento'),
])
def test_avaliar_aponta_o_adiamento_na_conclusao(dias, conclusao_com_adiamento):
    r = po.avaliar(ler({'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': data_ha(dias)}))
    assert ('adiamento' in r['indicacao']['conclusao']) is conclusao_com_adiamento
    assert any(not a.get('ok') for a in r['adiar']) is conclusao_com_adiamento


def test_P253_emergencia_com_stent_recente_nao_manda_adiar():
    r = po.avaliar(ler({'tipo': 'farmacologico', 'indicacao': 'sca', 'data': data_ha(15)}, urgencia='emergencia',
                       cirurgia='perfuracao_intestinal'))
    assert r['indicacao']['tipo'] == 'emergencia'
    assert not any(re.search(r'\badiar\b', a['texto'].lower()) for a in r['adiar'] if not a.get('ok'))


# Ponta a ponta: a rota passa p['stent'] (de ler) direto para condutas(); a janela tem de bater com adiamentos().
def ctx_da_tela(p):
    return {'sangramento': p['sangramento'], 'urgencia': p['urgencia'], 'neuroaxial': p['neuroaxial'],
            'condicoes': set(p['condicoes']), 'stent': p['stent'], 'aas_indicacao': p['aas_indicacao'],
            'cirurgia': p['cirurgia']}


@pytest.mark.parametrize('tipo, indicacao, dados_data, esperado', [
    pytest.param('balao', 'dac_cronica', data_ha(20), 'suspender',
                 id='P260-balao-20d-condutas-libera'),
    pytest.param('farmacologico', 'dac_cronica', data_ha(30), 'dano',
                 id='P261-DES-30d-condutas-marca-dano'),
    pytest.param('convencional', 'dac_cronica', '2026-10', 'dano',
                 id='P262-BMS-mes-2026-10-condutas-alerta-dano'),
    pytest.param('farmacologico', 'sca', data_ha(200), 'adiar', id='P263-DES-SCA-200d-condutas-adiar'),
    pytest.param('farmacologico', 'dac_cronica', data_ha(100), 'adiar', id='P264-DES-DACcr-100d-condutas-adiar'),
    pytest.param('farmacologico', 'dac_cronica', data_ha(10), 'dano', id='P265-DES-DACcr-10d-condutas-dano'),
])
def test_tela_e_condutas_concordam_na_janela(tipo, indicacao, dados_data, esperado):
    p = ler({'tipo': tipo, 'indicacao': indicacao, 'data': dados_data}, sangramento='alto',
            medicacoes=[AAS, CLOPI])
    i = {x['chave']: x for x in pm.condutas([AAS, CLOPI], ctx_da_tela(p))['itens']}[CLOPI]
    if esperado == 'suspender':
        assert i['conduta'] == 'suspender' and dias_em(i['resumo']) == 5, i['resumo']
    elif esperado == 'dano':
        assert i['conduta'] != 'suspender' and dias_em(i['resumo']) is None, i['resumo']
        assert '3: Dano' in i['classe'], i['classe']
    else:
        assert 'adiar' in i['resumo'].lower() and dias_em(i['resumo']) == 5, i['resumo']


@pytest.mark.parametrize('cirurgia, conduta', [
    pytest.param('neurocirurgia', 'suspender', id='P266-AVC-AAS-secundario-neurocirurgia-pela-tela'),
    pytest.param('rtu', 'individualizar', id='P267-AVC-AAS-secundario-RTU-pela-tela'),
    pytest.param('quadril', 'manter', id='P268-AVC-AAS-secundario-artroplastia-pela-tela'),
])
def test_aas_secundario_pela_tela_segue_a_cirurgia(cirurgia, conduta):
    p = ler(None, cirurgia=cirurgia, condicoes=['avc_ait'], aas_indicacao='secundaria', sangramento='alto',
            medicacoes=[AAS])
    i = pm.condutas([AAS], ctx_da_tela(p))['itens'][0]
    assert i['conduta'] == conduta, i['resumo']
    if conduta == 'suspender':
        assert dias_em(i['resumo']) == AAS_PRIMARIA_DIAS
