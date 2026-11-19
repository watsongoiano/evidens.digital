"""Pacientes simulados ("testes em modelos de computador"): anticoagulantes no pré-operatório de cirurgia não cardíaca.

Cada caso é um paciente fictício. A conduta que ``src.utils.preop_medicamentos.condutas`` devolve para o
anticoagulante dele é conferida contra um ORÁCULO INDEPENDENTE, montado aqui direto das fontes primárias (sem
reaproveitar a lógica do módulo, que só é chamado pela API pública):

- AHA/ACC 2026 (= texto de 2024, Thompson et al., Circulation 2024;150:e351–e442,
  https://doi.org/10.1161/CIR.0000000000001285): Tabela 13 transcrita célula a célula (D-6 … D+4), Tabela 14
  (risco tromboembólico), recomendações do §7.6 (interrupção por tempo 1 B-NR; ponte no alto risco com AVK 2a C-LD;
  ponte de rotina 3: Dano C-LD; reinício após hemostasia 2a C-LD) e texto do §7.6 (neuroaxial: ≥3 dias para anti-Xa,
  ≥4 dias para dabigatrana, 5–6 se ClCr <50; reversão com andexanet/complexo protrombínico ou idarucizumabe).
- SBC 2024 (Gualandro et al., Arq Bras Cardiol 2024;121(9):e20240590, https://doi.org/10.36660/abc.20240590):
  Quadros 24 (varfarina na urgência), 25 (varfarina e ponte), 26 (DOAC em horas, por ClCr e sangramento), Tabela 11
  (risco tromboembólico por CHADS₂) e texto do 4.3 (edoxabana 24 h / 48–72 h; neuroaxial = sangramento alto;
  DOAC contraindicado em prótese mecânica).
- PAUSE (Douketis et al., JAMA Intern Med 2019;179:1469–78, https://doi.org/10.1001/jamainternmed.2019.2431):
  apixabana/rivaroxabana omitidas 1 dia (baixo) ou 2 dias (alto); dabigatrana com ClCr 30–49 omitida 2 ou 4 dias;
  reinício D+1 (baixo) ou D+2–3 (alto). Excluídos: apixabana com ClCr <25; dabigatrana e rivaroxabana com ClCr <30.
- ACCP/CHEST 2022 (Douketis et al., Chest 2022;162:e207–e243, https://doi.org/10.1016/j.chest.2022.07.025): DOAC
  suspenso 1–2 dias antes (1–4 para dabigatrana), reinício ~24 h (baixo/moderado) ou 48–72 h (alto); contra ponte
  com heparina na interrupção de DOAC (condicional); contra ponte na FA (forte) e na prótese mecânica (condicional).
- ACCP 2022 conforme a revisão de Douketis e Spyropoulos (NEJM Evidence 2023;2(6),
  https://doi.org/10.1056/EVIDra2200322), Figuras 1 e 2 e texto: HBPM em dose plena (enoxaparina 1 mg/kg de 12/12 h
  ou 1,5 mg/kg/dia) com a última dose na manhã da véspera (D-1), metade da dose diária total; retorno da dose plena
  cerca de 24 h depois (sangramento baixo ou moderado) ou 48 a 72 h (alto); dose baixa (enoxaparina 40 mg/dia) nas
  primeiras 24 a 72 h após sangramento alto. Tudo isso está na nota da Figura 1, sobre a HBPM usada como PONTE na
  interrupção da varfarina; a Figura 2 fala em anticoagulante em dose baixa nas primeiras 48 a 72 h após o
  procedimento, depois da interrupção de DOAC, no alto risco de TEV. O módulo estende os intervalos ao uso contínuo de
  enoxaparina e tem de dizer isso. A SBC 2024 (Quadro 25 e texto do 4.3.2.6) fala em última dose 24 h antes (IIa-C,
  também na ponte) e, no texto do 4.3.2.6 (seção dos DOAC), em HBPM profilática 12 h após o procedimento, se adequada
  hemostasia, no alto risco de TEV, suspensa ao reintroduzir o anticoagulante oral. Nenhuma delas, nem a AHA/ACC
  (Tabela 13), fixa o intervalo entre a última dose profilática e a cirurgia. Da mesma revisão: procedimento de
  sangramento mínimo pode ser feito sob anticoagulação plena (Tabela 1, nota §) e a Figura 1 não tem HBPM nessa linha,
  de modo que o esquema da ponte não vale ali; ponte pós-operatória evitada com hemostasia cirúrgica inadequada; em
  cirurgias selecionadas de sangramento alto (cardíaca, intracraniana) a dose plena pode ficar impedida e a dose baixa
  pode ser dada por 3 a 5 dias; na Figura 2 a dose baixa é para pacientes selecionados ("selected patients").
- ASRA 2025, 5ª edição (Kopp et al., Reg Anesth Pain Med, https://doi.org/10.1136/rapm-2024-105766): neuroaxial
  com DOAC em dose plena ≥72 h; dabigatrana ≥72 h (ClCr ≥50), ≥120 h (ClCr 30–49), bloqueio neuroaxial não
  sugerido com ClCr <30; primeira dose ≥24 h depois; varfarina 5 dias com INR normal; HBPM em dose plena 24 h.
- Outras: AHA/ACC 2020 valvopatias (Otto et al., https://doi.org/10.1161/CIR.0000000000000923; DOAC contraindicado
  em prótese mecânica, 3: Dano) e ACCP 9ª ed., anticoagulantes parenterais (Garcia et al.,
  https://doi.org/10.1378/chest.11-2291; protamina neutraliza parcialmente a HBPM).

Convenções do oráculo (D0 = dia da cirurgia; x = "última dose no D-x"; y = "reinício no D+y"):
- AHA, Tabela 13: x = dia do último '*' antes do primeiro '†'; y = primeiro '*' depois do D0.
- SBC (Quadro 26): horas convertidas pela equivalência do próprio texto da SBC (4.3.2.6), que descreve o PAUSE:
  "24 h antes" = "suspenso 1 dia antes" = 1 dia inteiro sem dose → x = h/24 + 1; reinício y = h/24.
- PAUSE/CHEST: "omitir n dias" → x = n + 1.
- ASRA: horas entre a última dose e a punção (mesmo horário do dia) → x = h/24.
Regra de aceitação por paciente: o valor do módulo passa se couber no intervalo de ALGUMA fonte aplicável; se for
mais curto que TODAS, falha; se for mais longo que todas, só passa com texto de divergência.
Discordâncias reais ficam como ``xfail(strict=True)`` com o motivo e a fonte. Dados 100% fictícios.

Pontos documentados no relatório (/tmp/validacao/casos-anticoagulantes.md) e não testados aqui, por não serem de
intervalo de suspensão:
- TEV há <3 meses (AHA, texto do §7.6): adiar a cirurgia eletiva pode permitir uma interrupção mais segura; nem
  ``condutas`` nem os adiamentos de ``preoperatorio`` dizem isso.
- Ponte na prótese mecânica: a CHEST 2022 sugere CONTRA a ponte (condicional), a AHA a indica só na prótese de alto
  risco (mitral, bola-gaiola/disco, AVC recente) e a SBC em toda prótese. O módulo segue a AHA e cita a SBC na
  divergência, mas não cita a CHEST.
"""
import itertools
import math
import re

import pytest

from src.utils import preop_medicamentos as pm

INF = math.inf
ANTI_XA = ('apixabana', 'rivaroxabana', 'edoxabana')
DOAC = ANTI_XA + ('dabigatrana',)
ORDEM = {'baixo': 0, 'moderado': 1, 'alto': 2}

# ---------------------------------------------------------------------------------------------------------------
# Oráculo 1 — AHA/ACC, Tabela 13 (transcrição célula a célula; colunas D-6 … D+4)
# '*' administrar; '†' suspender; '‡' ponte com heparina; '#' HBPM pós-operatória até o INR voltar à faixa.
# ---------------------------------------------------------------------------------------------------------------
DIAS_T13 = (-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4)
T13 = {
    ('anti_xa', 'normal', 'alto'): '* * * * † † † † † * *',
    ('anti_xa', 'normal', 'baixo_moderado'): '* * * * * † † * * * *',
    ('anti_xa', 'normal', 'minimo'): '* * * * * * * * * * *',
    ('anti_xa', 'renal', 'alto'): '* * * † † † † † † * *',
    ('anti_xa', 'renal', 'baixo_moderado'): '* * * * † † † * * * *',
    ('anti_xa', 'renal', 'minimo'): '* * * * * * * * * * *',
    ('dabigatrana', 'normal', 'alto'): '* * * * † † † † † * *',
    ('dabigatrana', 'normal', 'baixo_moderado'): '* * * * * † † * * * *',
    ('dabigatrana', 'normal', 'minimo'): '* * * * * * * * * * *',
    ('dabigatrana', 'renal', 'alto'): '* * † † † † † † † * *',
    ('dabigatrana', 'renal', 'baixo_moderado'): '* * * * † † † * * * *',
    ('dabigatrana', 'renal', 'minimo'): '* * * * * * * * * * *',
    ('varfarina', 'te_baixo_moderado', 'alto'): '* † † † † † † * * * *',
    ('varfarina', 'te_baixo_moderado', 'baixo_moderado'): '* † † † † † † * * * *',
    ('varfarina', 'te_baixo_moderado', 'minimo'): '* * * * * * * * * * *',
    ('varfarina', 'te_alto', 'alto'): '* † † ‡ ‡ ‡ † * * *# *#',
    ('varfarina', 'te_alto', 'baixo_moderado'): '* † † ‡ ‡ ‡ † * *# *# *#',
    ('varfarina', 'te_alto', 'minimo'): '* * * * * * * * * * *',
}


def le_t13(chave):
    """{'interrompe', 'x', 'y', 'ponte', 'hbpm_pos'} lidos da linha da Tabela 13."""
    cel = dict(zip(DIAS_T13, T13[chave].split()))
    assert len(cel) == 11, chave
    suspensos = [d for d in DIAS_T13 if d < 0 and cel[d][0] in '†‡']
    if not suspensos:
        return {'interrompe': False, 'x': 0, 'y': 0, 'ponte': False, 'hbpm_pos': None}
    pos = [d for d in DIAS_T13 if d > 0]
    hbpm = [d for d in pos if '#' in cel[d]]
    return {'interrompe': True, 'x': 1 - min(suspensos), 'y': min(d for d in pos if cel[d].startswith('*')),
            'ponte': any('‡' in c for c in cel.values()), 'hbpm_pos': min(hbpm) if hbpm else None}


def faixa_renal_aha(farmaco, clcr):
    corte = 50 if farmaco == 'dabigatrana' else 30          # "CrCl <30" (anti-Xa); "CrCl ≥50 / <50" (dabigatrana)
    return 'renal' if clcr < corte else 'normal'


# ---------------------------------------------------------------------------------------------------------------
# Oráculo 2 — fontes para DOAC: intervalos (fonte, mínimo, máximo) para x e y
# ---------------------------------------------------------------------------------------------------------------
def fontes_doac(farmaco, clcr, sang, neuro):
    """sang = risco efetivo (neuroaxial já promovido a 'alto'). Devolve {'x': [...], 'y': [...], 'evitar_neuro': [...]}."""
    xs, ys, evitar = [], [], []
    grupo = 'dabigatrana' if farmaco == 'dabigatrana' else 'anti_xa'
    t = le_t13((grupo, faixa_renal_aha(farmaco, clcr), sang))
    xs.append(('AHA Tabela 13', t['x'], t['x']))
    ys.append(('AHA Tabela 13', t['y'], t['y']))
    if neuro:  # AHA, texto do §7.6: "held for ≥3 days (anti-Xa), ≥4 days (dabigatran; 5–6 days if CrCl <50)".
        # "Held for n days" admite duas leituras: n dias desde a última dose (x = n, coerente com ≥5 meias-vidas) ou
        # n dias inteiros sem dose (x = n + 1). O oráculo aceita as duas: 5–6 dias → x de 5 a 7.
        if farmaco == 'dabigatrana':
            xs.append(('AHA §7.6 (texto)', 5, 7) if clcr < 50 else ('AHA §7.6 (texto)', 4, INF))
        else:
            xs.append(('AHA §7.6 (texto)', 3, INF))
    # SBC, Quadro 26 (h → dias: x = h/24 + 1; y = h/24); edoxabana pelo texto do 4.3.2.6; <15 fora das faixas
    alto = sang == 'alto'
    if clcr >= 15:
        if farmaco == 'dabigatrana':
            antes, depois = ((96, 48) if alto else (48, 24)) if clcr < 50 else ((48, 48) if alto else (24, 24))
            xs.append(('SBC Quadro 26', antes // 24 + 1, antes // 24 + 1))
            ys.append(('SBC Quadro 26', depois // 24, depois // 24))
        elif farmaco == 'rivaroxabana':
            if alto or 15 <= clcr <= 30:                   # "pelo menos 48 h"; "15 a 30 mL/min"
                xs.append(('SBC Quadro 26', 3, INF))
                ys.append(('SBC Quadro 26', 2, 2))
            elif clcr >= 50:                               # "função renal normal"; 31–49 sem linha própria
                xs.append(('SBC Quadro 26', 2, 2))
                ys.append(('SBC Quadro 26', 1, 1))
        elif farmaco == 'apixabana':
            if alto or 15 <= clcr <= 50:                   # "pelo menos 48 h"; "15 a 50 mL/min"
                xs.append(('SBC Quadro 26', 3, INF))
                ys.append(('SBC Quadro 26', 2, 2))
            else:
                xs.append(('SBC Quadro 26', 2, 2))
                ys.append(('SBC Quadro 26', 1, 1))
        else:                                              # edoxabana: 24 h (baixo) / 48–72 h (alto), sem reinício
            xs.append(('SBC 4.3.2.6 (texto)', 3, 4) if alto else ('SBC 4.3.2.6 (texto)', 2, 2))
    # PAUSE 2019 (apixabana ≥25; rivaroxabana e dabigatrana ≥30) e CHEST 2022 (inclui edoxabana)
    minimo_pause = {'apixabana': 25, 'rivaroxabana': 30, 'dabigatrana': 30, 'edoxabana': 30}[farmaco]
    if clcr >= minimo_pause and sang in ('baixo_moderado', 'alto'):
        omitidos = {'baixo_moderado': 1, 'alto': 2}[sang]
        if farmaco == 'dabigatrana' and clcr < 50:
            omitidos *= 2
        nome = 'CHEST 2022' if farmaco == 'edoxabana' else 'PAUSE/CHEST 2022'
        xs.append((nome, omitidos + 1, omitidos + 1))
        ys.append((nome, 1, 1) if sang == 'baixo_moderado' else (nome, 2, 3))
    if neuro:  # ASRA 2025, 5ª ed. (dose plena)
        if farmaco == 'dabigatrana':
            if clcr < 30:
                evitar.append('ASRA 2025: bloqueio neuroaxial não sugerido com dabigatrana e ClCr <30')
            else:
                xs.append(('ASRA 2025', 3 if clcr >= 50 else 5, INF))
                ys.append(('ASRA 2025', 1, INF))
        else:
            xs.append(('ASRA 2025', 3, INF))
            ys.append(('ASRA 2025', 1, INF))
    return {'x': xs, 'y': ys, 'evitar_neuro': evitar}


def avalia(valor, intervalos):
    if not intervalos:
        return 'sem_fonte'
    if any(lo <= valor <= hi for _, lo, hi in intervalos):
        return 'ok'
    return 'curto' if valor < min(lo for _, lo, _ in intervalos) else 'longo'


# ---------------------------------------------------------------------------------------------------------------
# Oráculo 3 — risco tromboembólico (AHA Tabela 14; SBC Tabela 11 + Quadro 25) e ponte na varfarina
# ---------------------------------------------------------------------------------------------------------------
def cha2ds2vasc(p):
    """Lip 2010: IC 1, HAS 1, idade ≥75 2, DM 1, AVC/AIT/TE 2, doença vascular (IAM, DAP) 1, 65–74 1, sexo fem. 1."""
    idade = p['idade']
    return (p['ic'] + p['has'] + (2 if idade >= 75 else 1 if idade >= 65 else 0) + p['dm']
            + (2 if p['avc'] else 0) + bool(p['vasc']) + (p['sexo'] == 'feminino'))


def chads2(p):
    """Gage 2001 (SBC, Tabela 11): IC 1, HAS 1, idade ≥75 1, DM 1, AVC/AIT 2."""
    return p['ic'] + p['has'] + (p['idade'] >= 75) + p['dm'] + (2 if p['avc'] else 0)


def _combina(opcoes):
    if not opcoes:
        return None
    return {max(combo, key=ORDEM.get) for combo in itertools.product(*opcoes)}


def aha_t14(p):
    """Categorias aceitas pela Tabela 14 da AHA (adaptada de Douketis/CHEST 2022). None = sem indicação informada."""
    op = []
    if p['fa']:
        s = cha2ds2vasc(p)
        if s >= 7 or (s >= 5 and p['avc'] == 'recente'):
            op.append({'alto'})
        elif s >= 5:
            op.append({'moderado'})
        elif p['avc'] is None:
            op.append({'baixo'})
        elif p['avc'] == 'antigo':
            op.append({'baixo', 'moderado'})            # fora das faixas: "baixo" exige ausência de AVC; não é alto
        if p['valvopatia']:
            op.append({'baixo', 'alto'})                # "FA com valvopatia reumática" = alto, se reumática
    if p['avc'] == 'recente' and (p['fa'] or p['protese']):
        op.append({'alto'})                             # AVC cardioembólico <3 m; prótese com AVC/AIT <3 m
    if p['tev'] in ('<1m', '1-3m'):
        op.append({'alto'})
    elif p['tev'] == '3-12m':
        op.append({'moderado'})
    elif p['tev'] == '>12m':
        op.append({'baixo'})
    if p['tromb_grave']:
        op.append({'alto'})
    if p['cancer']:
        op.append({'moderado', 'alto'})                 # alto se câncer de alto risco de TEV (não informado)
    if p['protese'] == 'mitral':
        op.append({'alto'})
    elif p['protese'] == 'aortica':                     # duplo folheto (descrito no caso)
        if p['fa']:
            op.append({'moderado'})                     # FA é fator maior (nota da Tabela 14)
        elif p['avc'] == 'antigo':
            op.append({'baixo', 'moderado'})            # fator maior = AVC/AIT múltiplos ou perioperatório
        else:
            op.append({'baixo'})
    return _combina(op)


def sbc_t11(p):
    """Categorias aceitas pela SBC (Tabela 11 por CHADS₂; prótese mecânica entra na ponte do Quadro 25)."""
    op = []
    if p['fa']:
        c = chads2(p)
        if c >= 5 or p['avc'] == 'recente':
            op.append({'alto'})
        elif p['avc'] == 'antigo':
            op.append({'moderado', 'alto'})             # nota da Tabela 11: AVC >3 m com CHADS₂ <5 pode ser alto
        elif c >= 3:
            op.append({'moderado'})
        else:
            op.append({'baixo'})
        if p['valvopatia']:
            op.append({'baixo', 'alto'})
    elif p['avc'] == 'recente':
        op.append({'alto'})
    if p['tev'] in ('<1m', '1-3m'):
        op.append({'alto'})
    elif p['tev'] == '3-12m':
        op.append({'moderado'})
    elif p['tev'] == '>12m':
        op.append({'baixo'})
    if p['tromb_grave']:
        op.append({'alto'})
    if p['cancer']:
        op.append({'moderado'})
    if p['protese']:
        op.append({'alto'})                             # Quadro 25: "alto risco ... e próteses valvares mecânicas"
    return _combina(op)


def decide_ponte(categorias):
    if categorias is None:
        return None
    if categorias == {'alto'}:
        return True
    return False if 'alto' not in categorias else None


# ---------------------------------------------------------------------------------------------------------------
# Leitura da saída do módulo
# ---------------------------------------------------------------------------------------------------------------
# O resumo segue a Tabela 13: os dias sem dose (da interrupção à véspera do reinício), a última dose e o reinício.
RE_DIAS = re.compile(r'Sem dose do D-(\d+) ao (D0|D\+\d+) \(última no D-(\d+)\); reiniciar no D\+(\d+)')
RE_HORAS = re.compile(r'Última dose ≥(\d+) h antes; reiniciar (\d+) h depois')
RE_SEM_CLCR = re.compile(r'Com ClCr ≥(\d+): sem dose do D-\d+ ao (?:D0|D\+\d+) \(última no D-(\d+)\) e reinício no '
                         r'D\+(\d+)\. Com ClCr <(\d+): sem dose do D-\d+ ao (?:D0|D\+\d+) \(última no D-(\d+)\) e '
                         r'reinício no D\+(\d+)')
RE_CAT_AHA = re.compile(r'pela AHA \(Tabela 14\): (baixo|moderado|alto)')
RE_ULTIMA_VARF = re.compile(r'Sem dose do D-(\d+) ao D0 \(AHA, Tabela 13\): última dose no D-(\d+)')
RE_HEPARINA_POS = re.compile(r'heparina retomada no D\+(\d+)')
RE_VARF_VOLTA = re.compile(r'Varfarina de volta no D\+(\d+)')
RE_ENOXA_ANTES = re.compile(r'última dose (\d+) h antes')
RE_ENOXA_DEPOIS = re.compile(r'retorno ≥(\d+) h depois \((\d+)–(\d+) h se sangramento alto\)')
# Enoxaparina com a dose informada (campo "Dose da enoxaparina")
RE_ENOXA_PLENA_ACCP = re.compile(r'ACCP 2022, dose plena \(enoxaparina 1 mg/kg de 12/12 h ou 1,5 mg/kg/dia\): última '
                                 r'dose na manhã da véspera \(D-(\d+)\), com metade da dose diária total')
RE_ENOXA_PLENA_SBC = re.compile(r'SBC 2024 \(Quadro 25, IIa-C\): última dose (\d+) h antes')
RE_ENOXA_RETORNO = re.compile(r'Retorno da dose plena \(ACCP 2022\), com hemostasia adequada: cerca de (\d+) h após cirurgia de sangramento '
                              r'baixo ou moderado; (\d+) a (\d+) h após sangramento alto')
RE_ENOXA_BAIXA = re.compile(r'a ACCP 2022 a descreve na ponte da varfarina \(enoxaparina 40 mg/dia nas primeiras (\d+) a '
                            r'(\d+) h após cirurgia de sangramento alto, até voltar a dose plena\)')
RE_ENOXA_BAIXA_DOAC = re.compile(r'após a interrupção de DOAC, em pacientes selecionados de alto risco de tromboembolismo venoso '
                                 r'\(anticoagulante em dose baixa nas primeiras (\d+) a (\d+) h após o procedimento\)')
RE_ENOXA_PONTE_ACCP = re.compile(r'intervalos que a ACCP 2022 define para a HBPM na ponte da varfarina, aqui estendidos '
                                 r'ao uso contínuo')
RE_ENOXA_PONTE_SBC = re.compile(r'intervalo que a SBC define para a HBPM na ponte, aqui estendido ao uso contínuo')
RE_ENOXA_PROFILATICA_SBC = re.compile(r'SBC 2024 \(texto do 4\.3\.2\.6, na seção dos anticoagulantes orais diretos\) aconselha '
                                      r'iniciar a HBPM profilática (\d+) h após o procedimento, se adequada hemostasia, em '
                                      r'pacientes ou procedimentos de alto risco de tromboembolismo venoso, e suspendê-la ao '
                                      r'reintroduzir o anticoagulante oral')
RE_ENOXA_HEMOSTASIA = re.compile(r'Com hemostasia cirúrgica inadequada, a ACCP 2022 aconselha evitar a ponte pós-operatória')
RE_ENOXA_EXCECAO_ALTO = re.compile(r'Exceção no sangramento alto \(ACCP 2022\): em cirurgias selecionadas \(por exemplo, '
                                   r'cardíaca ou intracraniana\), os riscos e as consequências do sangramento podem impedir '
                                   r'a dose plena depois da cirurgia; nesses pacientes, a HBPM em dose profilática \(baixa\) '
                                   r'pode ser dada por (\d+) a (\d+) dias, enquanto a varfarina é retomada')
URL_ACCP_NEJM = 'https://doi.org/10.1056/EVIDra2200322'
RE_REVERSAO_DOAC = {'dabigatrana': re.compile(r'idarucizumab', re.I),
                    'anti_xa': re.compile(r'andexanet|complexo protrombínico', re.I)}


def esquema_doac(resumo):
    """(x, y) do resumo do módulo; horas pela mesma equivalência usada para a SBC."""
    m = RE_DIAS.search(resumo)
    if m:
        sem, fim, x, y = m.groups()
        sem, x, y = int(sem), int(x), int(y)
        assert sem == x - 1, f'dias sem dose incoerentes com a última dose: {resumo}'
        assert fim == ('D0' if y == 1 else f'D+{y - 1}'), f'os dias sem dose não vão até a véspera do reinício: {resumo}'
        return x, y
    m = RE_HORAS.search(resumo)
    if m:
        antes, depois = map(int, m.groups())
        return antes // 24 + 1, depois // 24
    return None


# ---------------------------------------------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------------------------------------------
BASE = dict(idade=60, sexo='masculino', peso=75.0, clcr=80.0, sang='baixo_moderado', neuro=False, urg='eletiva',
            fa=False, has=False, dm=False, ic=False, vasc=None, avc=None, tev=None, protese=None, cancer=False,
            tromb_grave=False, valvopatia=False, dose=None)   # dose: a da enoxaparina ('plena' | 'profilatica')
PERFIS = [  # (idade, sexo, peso, indicação) — rodízio para variar os pacientes da grade de DOAC
    (34, 'feminino', 58.0, dict(tev='>12m')), (47, 'masculino', 82.0, dict(fa=True, has=True)),
    (58, 'feminino', 64.0, dict(tev='3-12m')), (66, 'masculino', 90.0, dict(fa=True, dm=True)),
    (72, 'feminino', 55.0, dict(fa=True, has=True, ic=True)), (79, 'masculino', 70.0, dict(tev='>12m')),
    (85, 'feminino', 48.0, dict(fa=True, has=True)), (91, 'masculino', 61.0, dict(fa=True, vasc='dap')),
]
_ROT_SANG = {'baixo_moderado': 'baixo', 'alto': 'alto', 'minimo': 'minimo', None: 'sangNA'}


def paciente(id_, **campos):
    p = dict(BASE)
    p.update(campos)
    p['id'] = id_
    return p


def _grade():
    casos, n = [], 0
    clcrs = {f: [120, 80, 50, 49, 35, 30, 29, 25, 15] for f in ANTI_XA}
    clcrs['dabigatrana'] = [120, 80, 55, 50, 49, 45, 30, 29, 25, 15]
    for farmaco in DOAC:
        for clcr in clcrs[farmaco]:
            for sang in ('baixo_moderado', 'alto'):
                idade, sexo, peso, ind = PERFIS[n % len(PERFIS)]
                n += 1
                casos.append(paciente(f'{farmaco}-clcr{clcr}-{_ROT_SANG[sang]}', med=farmaco, clcr=float(clcr),
                                      sang=sang, idade=idade, sexo=sexo, peso=peso, **ind))
    casos.append(paciente('apixabana-clcr10-alto', med='apixabana', clcr=10.0, sang='alto', idade=77,
                          sexo='feminino', peso=52.0, fa=True, has=True))
    return casos


P = paciente
CASOS = _grade() + [
    # --- Sangramento mínimo: não interromper (AHA Tabela 13; SBC Quadros 12–14) -----------------------------------
    P('apixabana-clcr80-minimo', med='apixabana', sang='minimo', idade=74, sexo='feminino', fa=True, has=True),
    P('rivaroxabana-clcr25-minimo', med='rivaroxabana', clcr=25.0, sang='minimo', idade=83, tev='>12m'),
    P('edoxabana-clcr55-minimo', med='edoxabana', clcr=55.0, sang='minimo', idade=69, sexo='feminino', fa=True),
    P('dabigatrana-clcr40-minimo', med='dabigatrana', clcr=40.0, sang='minimo', idade=81, fa=True, has=True),
    P('varfarina-minimo-fa', med='varfarina', sang='minimo', idade=76, sexo='feminino', fa=True, has=True),
    P('varfarina-minimo-protese-mitral', med='varfarina', sang='minimo', idade=52, sexo='feminino',
      protese='mitral'),
    # --- ClCr ausente: pedir o ClCr, sem chutar um esquema único -------------------------------------------------
    P('apixabana-clcrNA-baixo', med='apixabana', clcr=None, idade=68, sexo='feminino', fa=True, has=True),
    P('apixabana-clcrNA-alto', med='apixabana', clcr=None, sang='alto', idade=73, fa=True, dm=True),
    P('rivaroxabana-clcrNA-baixo', med='rivaroxabana', clcr=None, idade=45, sexo='feminino', tev='3-12m'),
    P('rivaroxabana-clcrNA-alto', med='rivaroxabana', clcr=None, sang='alto', idade=62, tev='>12m'),
    P('edoxabana-clcrNA-baixo', med='edoxabana', clcr=None, idade=71, fa=True, has=True, ic=True),
    P('edoxabana-clcrNA-alto', med='edoxabana', clcr=None, sang='alto', idade=80, sexo='feminino', fa=True),
    P('dabigatrana-clcrNA-baixo', med='dabigatrana', clcr=None, idade=77, fa=True, has=True),
    P('dabigatrana-clcrNA-alto', med='dabigatrana', clcr=None, sang='alto', idade=64, sexo='feminino', fa=True),
    P('rivaroxabana-clcrNA-minimo', med='rivaroxabana', clcr=None, sang='minimo', idade=70, fa=True),
    P('dabigatrana-clcrNA-neuroaxial', med='dabigatrana', clcr=None, neuro=True, idade=75, fa=True, has=True),
    P('apixabana-clcrNA-neuroaxial', med='apixabana', clcr=None, neuro=True, sang=None, idade=59,
      sexo='feminino', tev='>12m'),
    # --- Risco de sangramento ausente --------------------------------------------------------------------------
    P('apixabana-clcr70-sangNA', med='apixabana', clcr=70.0, sang=None, idade=61, fa=True, has=True),
    P('rivaroxabana-clcr40-sangNA', med='rivaroxabana', clcr=40.0, sang=None, idade=78, sexo='feminino', fa=True),
    P('edoxabana-clcr28-sangNA', med='edoxabana', clcr=28.0, sang=None, idade=84, fa=True, ic=True),
    P('dabigatrana-clcr45-sangNA', med='dabigatrana', clcr=45.0, sang=None, idade=73, sexo='feminino', fa=True),
    P('dabigatrana-clcrNA-sangNA', med='dabigatrana', clcr=None, sang=None, idade=66, fa=True, has=True),
    P('varfarina-sangNA-fa', med='varfarina', sang=None, idade=70, fa=True, has=True, dm=True),
    # --- Anestesia neuroaxial: pelo menos o esquema de sangramento alto ----------------------------------------
    P('apixabana-clcr80-neuroaxial', med='apixabana', neuro=True, idade=67, fa=True, has=True),
    P('apixabana-clcr25-neuroaxial-sangNA', med='apixabana', clcr=25.0, neuro=True, sang=None, idade=86,
      sexo='feminino', fa=True),
    P('rivaroxabana-clcr90-neuroaxial-minimo', med='rivaroxabana', clcr=90.0, neuro=True, sang='minimo', idade=55,
      tev='>12m'),
    P('rivaroxabana-clcr28-neuroaxial', med='rivaroxabana', clcr=28.0, neuro=True, idade=82, fa=True),
    P('edoxabana-clcr60-neuroaxial', med='edoxabana', clcr=60.0, neuro=True, idade=63, sexo='feminino',
      tev='3-12m'),
    P('edoxabana-clcr20-neuroaxial', med='edoxabana', clcr=20.0, neuro=True, sang='alto', idade=88, fa=True),
    P('dabigatrana-clcr120-neuroaxial', med='dabigatrana', clcr=120.0, neuro=True, idade=44, fa=True),
    P('dabigatrana-clcr60-neuroaxial', med='dabigatrana', clcr=60.0, neuro=True, idade=70, fa=True, has=True),
    P('dabigatrana-clcr45-neuroaxial', med='dabigatrana', clcr=45.0, neuro=True, idade=79, sexo='feminino',
      fa=True),
    P('dabigatrana-clcr30-neuroaxial', med='dabigatrana', clcr=30.0, neuro=True, sang='alto', idade=83, fa=True),
    P('dabigatrana-clcr20-neuroaxial', med='dabigatrana', clcr=20.0, neuro=True, idade=87, sexo='feminino',
      fa=True, has=True),
    P('varfarina-neuroaxial-fa-cha2ds2vasc3', med='varfarina', neuro=True, idade=68, sexo='feminino', fa=True,
      has=True),
    P('varfarina-neuroaxial-protese-mitral', med='varfarina', neuro=True, idade=57, protese='mitral'),
    P('enoxaparina-neuroaxial', med='enoxaparina', neuro=True, idade=49, sexo='feminino', tev='1-3m'),
    # --- Urgência e emergência: reversão, não esquema eletivo --------------------------------------------------
    P('apixabana-clcr60-alto-emergencia', med='apixabana', clcr=60.0, sang='alto', urg='emergencia', idade=81,
      fa=True),
    P('rivaroxabana-clcr35-baixo-urgencia', med='rivaroxabana', clcr=35.0, urg='urgencia', idade=72,
      sexo='feminino', tev='3-12m'),
    P('edoxabana-clcr50-alto-emergencia', med='edoxabana', clcr=50.0, sang='alto', urg='emergencia', idade=65,
      fa=True, has=True),
    P('dabigatrana-clcr70-alto-emergencia', med='dabigatrana', clcr=70.0, sang='alto', urg='emergencia',
      idade=58, fa=True),
    P('dabigatrana-clcr40-baixo-urgencia', med='dabigatrana', clcr=40.0, urg='urgencia', idade=80,
      sexo='feminino', fa=True),
    P('rivaroxabana-clcrNA-alto-emergencia', med='rivaroxabana', clcr=None, sang='alto', urg='emergencia',
      idade=39, tev='<1m'),
    P('dabigatrana-clcr55-neuroaxial-emergencia', med='dabigatrana', clcr=55.0, neuro=True, urg='emergencia',
      idade=71, fa=True),
    P('apixabana-clcr80-minimo-emergencia', med='apixabana', sang='minimo', urg='emergencia', idade=76,
      fa=True, has=True),
    P('apixabana-clcr80-alto-tempo-sensivel', med='apixabana', sang='alto', urg='tempo_sensivel', idade=64,
      sexo='feminino', fa=True),
    P('varfarina-emergencia-fa', med='varfarina', sang='alto', urg='emergencia', idade=79, fa=True, has=True),
    P('varfarina-emergencia-protese-mitral', med='varfarina', urg='emergencia', idade=50, sexo='feminino',
      protese='mitral'),
    P('varfarina-urgencia-tev', med='varfarina', sang='alto', urg='urgencia', idade=42, tev='3-12m'),
    P('enoxaparina-emergencia', med='enoxaparina', sang='alto', urg='emergencia', idade=67, tev='<1m'),
    P('enoxaparina-urgencia', med='enoxaparina', urg='urgencia', idade=53, sexo='feminino', cancer=True,
      tev='1-3m'),
    # --- Varfarina: risco tromboembólico e ponte (AHA Tabela 14 × SBC Tabela 11/Quadro 25) ---------------------
    P('varfarina-fa-cha2ds2vasc1', med='varfarina', idade=52, fa=True, has=True),
    P('varfarina-fa-cha2ds2vasc2', med='varfarina', idade=67, sexo='feminino', fa=True, sang='alto'),
    P('varfarina-fa-cha2ds2vasc3', med='varfarina', idade=77, fa=True, has=True),
    P('varfarina-fa-cha2ds2vasc4', med='varfarina', idade=70, sexo='feminino', fa=True, has=True, dm=True,
      sang='alto'),
    P('varfarina-fa-cha2ds2vasc5', med='varfarina', idade=78, sexo='feminino', fa=True, has=True, dm=True),
    P('varfarina-fa-cha2ds2vasc6', med='varfarina', idade=78, sexo='feminino', fa=True, has=True, dm=True,
      ic=True, sang='alto'),
    P('varfarina-fa-cha2ds2vasc7', med='varfarina', idade=80, sexo='feminino', fa=True, has=True, dm=True,
      ic=True, vasc='dap'),
    P('varfarina-fa-cha2ds2vasc7-alto', med='varfarina', idade=76, sexo='feminino', fa=True, has=True, dm=True,
      ic=True, vasc='iam', sang='alto'),
    P('varfarina-fa-cha2ds2vasc8', med='varfarina', idade=80, sexo='feminino', fa=True, has=True, dm=True,
      ic=True, avc='antigo'),
    P('varfarina-fa-cha2ds2vasc9', med='varfarina', idade=82, sexo='feminino', fa=True, has=True, dm=True,
      ic=True, vasc='dap', avc='antigo', sang='alto'),
    P('varfarina-fa-cha2ds2vasc3-avc-recente', med='varfarina', idade=60, fa=True, has=True, avc='recente'),
    P('varfarina-fa-cha2ds2vasc5-avc-recente', med='varfarina', idade=66, fa=True, has=True, dm=True,
      avc='recente'),
    P('varfarina-fa-cha2ds2vasc6-avc-recente', med='varfarina', idade=70, sexo='feminino', fa=True, has=True,
      dm=True, avc='recente', sang='alto'),
    P('varfarina-fa-cha2ds2vasc4-avc-antigo', med='varfarina', idade=60, fa=True, has=True, dm=True,
      avc='antigo'),
    P('varfarina-fa-cha2ds2vasc6-avc-antigo-chads2-5', med='varfarina', idade=78, fa=True, has=True, dm=True,
      avc='antigo'),
    P('varfarina-fa-cha2ds2vasc2-valvopatia', med='varfarina', idade=67, sexo='feminino', fa=True,
      valvopatia=True),
    P('varfarina-protese-aortica-sem-fator', med='varfarina', idade=45, protese='aortica'),
    P('varfarina-protese-aortica-com-fa', med='varfarina', idade=60, protese='aortica', fa=True, has=True,
      sang='alto'),
    P('varfarina-protese-aortica-avc-antigo', med='varfarina', idade=55, sexo='feminino', protese='aortica',
      avc='antigo'),
    P('varfarina-protese-aortica-avc-recente', med='varfarina', idade=63, protese='aortica', avc='recente'),
    P('varfarina-protese-mitral-baixo', med='varfarina', idade=48, sexo='feminino', protese='mitral'),
    P('varfarina-protese-mitral-alto', med='varfarina', idade=59, protese='mitral', sang='alto'),
    P('varfarina-protese-mitral-fa-cha2ds2vasc3', med='varfarina', idade=71, sexo='feminino', protese='mitral',
      fa=True, has=True),
    P('varfarina-tev-menos-1-mes', med='varfarina', idade=38, sexo='feminino', tev='<1m'),
    P('varfarina-tev-1-3-meses', med='varfarina', idade=51, tev='1-3m', sang='alto'),
    P('varfarina-tev-3-12-meses', med='varfarina', idade=46, sexo='feminino', tev='3-12m'),
    P('varfarina-tev-mais-12-meses', med='varfarina', idade=63, tev='>12m', sang='alto'),
    P('varfarina-tev-mais-12m-cancer-ativo', med='varfarina', idade=69, sexo='feminino', tev='>12m', cancer=True),
    P('varfarina-tev-mais-12m-trombofilia-grave', med='varfarina', idade=33, sexo='feminino', tev='>12m',
      tromb_grave=True),
    P('varfarina-trombofilia-grave-alto', med='varfarina', idade=41, tromb_grave=True, sang='alto'),
    P('varfarina-fa-cha2ds2vasc2-tev-3-12m', med='varfarina', idade=68, fa=True, has=True, tev='3-12m'),
    P('varfarina-sem-indicacao', med='varfarina', idade=57),
    # --- DOAC com alto risco tromboembólico: nunca ponte -------------------------------------------------------
    P('apixabana-clcr85-tev-menos-1-mes-alto', med='apixabana', clcr=85.0, sang='alto', idade=36, sexo='feminino',
      tev='<1m'),
    P('rivaroxabana-clcr95-trombofilia-grave', med='rivaroxabana', clcr=95.0, idade=29, sexo='feminino',
      tev='>12m', tromb_grave=True),
    P('edoxabana-clcr65-fa-cha2ds2vasc8-alto', med='edoxabana', clcr=65.0, sang='alto', idade=79,
      sexo='feminino', fa=True, has=True, dm=True, ic=True, avc='antigo'),
    P('dabigatrana-clcr60-tev-1-3m-cancer', med='dabigatrana', clcr=60.0, idade=61, tev='1-3m', cancer=True),
    # --- DOAC em portador de prótese mecânica (contraindicado) ------------------------------------------------
    P('apixabana-clcr80-protese-aortica', med='apixabana', idade=56, protese='aortica'),
    P('rivaroxabana-clcr70-protese-mitral', med='rivaroxabana', clcr=70.0, idade=49, sexo='feminino',
      protese='mitral', sang='alto'),
    P('dabigatrana-clcr75-protese-mitral', med='dabigatrana', clcr=75.0, idade=62, protese='mitral'),
    P('rivaroxabana-clcr60-protese-mitral-emergencia', med='rivaroxabana', clcr=60.0, sang='alto', urg='emergencia',
      idade=66, sexo='feminino', protese='mitral'),
    # --- Enoxaparina em dose plena --------------------------------------------------------------------------
    P('enoxaparina-baixo', med='enoxaparina', idade=58, tev='1-3m'),
    P('enoxaparina-alto', med='enoxaparina', sang='alto', idade=64, sexo='feminino', cancer=True, tev='3-12m'),
    P('enoxaparina-minimo', med='enoxaparina', sang='minimo', idade=71, tev='<1m'),
    P('enoxaparina-clcr20-alto', med='enoxaparina', clcr=20.0, sang='alto', idade=84, sexo='feminino',
      tev='1-3m'),
    P('enoxaparina-sangNA', med='enoxaparina', sang=None, idade=46, tev='<1m'),
    # --- Enoxaparina com a dose informada: plena (ACCP 2022 e SBC) e profilática (sem intervalo nas fontes) --------
    P('enoxaparina-plena-baixo', med='enoxaparina', dose='plena', idade=57, sexo='feminino', tev='1-3m'),
    P('enoxaparina-plena-alto', med='enoxaparina', dose='plena', sang='alto', idade=69, cancer=True, tev='3-12m'),
    P('enoxaparina-plena-sangNA', med='enoxaparina', dose='plena', sang=None, idade=43, sexo='feminino', tev='<1m'),
    P('enoxaparina-plena-minimo', med='enoxaparina', dose='plena', sang='minimo', idade=61, tev='3-12m'),
    P('enoxaparina-plena-neuroaxial', med='enoxaparina', dose='plena', neuro=True, idade=51, tev='1-3m'),
    P('enoxaparina-plena-tempo-sensivel', med='enoxaparina', dose='plena', sang='alto', urg='tempo_sensivel', idade=74,
      sexo='feminino', cancer=True, tev='<1m'),
    P('enoxaparina-profilatica-baixo', med='enoxaparina', dose='profilatica', idade=62, sexo='feminino', cancer=True),
    P('enoxaparina-profilatica-alto', med='enoxaparina', dose='profilatica', sang='alto', idade=78, tev='>12m'),
    P('enoxaparina-profilatica-sangNA', med='enoxaparina', dose='profilatica', sang=None, idade=39, sexo='feminino',
      tev='>12m'),
    P('enoxaparina-profilatica-neuroaxial', med='enoxaparina', dose='profilatica', neuro=True, idade=66,
      cancer=True),
]


def contexto(p):
    """Contexto que o módulo recebe, normalizado como em preoperatorio.ler (AVC recente ⊂ AVC; mitral ⊂ prótese)."""
    c = set()
    for chave, cond in (('fa', 'fa'), ('has', 'hipertensao'), ('dm', 'diabetes'), ('ic', 'ic'),
                        ('cancer', 'cancer_ativo'), ('tromb_grave', 'trombofilia_grave'),
                        ('valvopatia', 'valvopatia')):
        if p[chave]:
            c.add(cond)
    if p['vasc'] == 'dap':
        c.add('doenca_arterial_periferica')
    elif p['vasc'] == 'iam':
        c |= {'iam_previo', 'dac'}
    if p['avc']:
        c.add('avc_ait')
        if p['avc'] == 'recente':
            c.add('avc_ait_recente')
    if p['tev']:
        c.add('tev')
        c.add({'<1m': 'tev_recente_3m', '1-3m': 'tev_recente_3m', '3-12m': 'tev_3_12m', '>12m': None}[p['tev']]
              or 'tev')
    if p['protese']:
        c.add('protese_mecanica')
        if p['protese'] == 'mitral':
            c.add('protese_mecanica_mitral')
    return {'idade': p['idade'], 'sexo': p['sexo'], 'peso': p['peso'], 'clcr': p['clcr'],
            'sangramento': p['sang'], 'neuroaxial': p['neuro'], 'urgencia': p['urg'], 'condicoes': c,
            'dose_heparina': p['dose'] or ''}


# ---------------------------------------------------------------------------------------------------------------
# Discordâncias encontradas (módulo × oráculo) — continuam visíveis como xfail estrito
# ---------------------------------------------------------------------------------------------------------------
# Histórico (versão sha256 6d86d6e4…, 16/11/2026): DOAC em prótese mecânica sem alerta (3 casos), dabigatrana com
# ClCr <30 e neuroaxial sem alerta (1) e enoxaparina na urgência com esquema eletivo (2). Corrigidos na versão
# e8e27c88…: os casos passam e as verificações abaixo guardam a correção. Continua pendente só a protamina
# (ver test_enoxaparina_urgencia_orienta_protamina).
DISCREPANCIAS = {}   # DOAC + prótese mecânica na emergência: reversão incluída na rodada 3.
_MOTIVO_PROTAMINA = ('Enoxaparina na urgência/emergência: o módulo pede a hora da última dose e dá os intervalos '
                     'neuroaxiais da ASRA, mas não cita a protamina (neutraliza parcialmente a HBPM; ACCP 9ª ed., '
                     'Garcia 2012, doi:10.1378/chest.11-2291)')
RE_EVITAR_NEURO = re.compile(r'(evitar|não (?:fazer|recomend\w*|sugerid\w*)|contraindicad\w*)[^.]{0,40}'
                             r'(neuroaxial|bloqueio)|(neuroaxial|bloqueio)[^.]{0,40}(não (?:é )?(?:sugerid|recomendad)|'
                             r'contraindicad)', re.I)
URL_VHD = 'https://doi.org/10.1161/CIR.0000000000000923'


# ---------------------------------------------------------------------------------------------------------------
# Verificações
# ---------------------------------------------------------------------------------------------------------------
def _item(r, med):
    itens = [i for i in r['itens'] if i['chave'] == med]
    assert len(itens) == 1, r
    return itens[0]


def _titulos(r):
    return [a['titulo'] for a in r['avisos']]


def _tudo(it, r):
    partes = [it['resumo'], it['texto'], it['divergencia']]
    for a in r['avisos']:
        partes += [a['titulo'], a['texto'], a['divergencia']]
    return ' '.join(partes)


def _confere(valor, intervalos, rotulo, it):
    veredito = avalia(valor, intervalos)
    fontes = '; '.join(f'{n}: {lo}–{hi}' for n, lo, hi in intervalos)
    assert veredito != 'curto', f'{rotulo} = {valor} é MAIS CURTO que todas as fontes ({fontes})'
    if veredito == 'longo':
        assert it['divergencia'], f'{rotulo} = {valor} é mais longo que todas as fontes ({fontes}) sem divergência'


def verifica_urgencia(p, it, r):
    med = p['med']
    texto = it['resumo'] + ' ' + it['texto']
    assert not RE_DIAS.search(it['resumo']) and not RE_HORAS.search(it['resumo']), \
        f'urgência com esquema eletivo: {it["resumo"]}'
    if med in DOAC:
        grupo = 'dabigatrana' if med == 'dabigatrana' else 'anti_xa'
        assert RE_REVERSAO_DOAC[grupo].search(texto), f'sem o reversor esperado (AHA Tabela 15): {texto}'
        assert re.search(r'coagulação|nível', texto), 'sem orientação de medir efeito residual (AHA §7.6)'
        if p['protese']:
            assert re.search(r'[Cc]ontraindicad', _tudo(it, r)), 'DOAC em prótese mecânica sem alerta'
    elif med == 'varfarina':
        assert 'vitamina K' in texto and re.search(r'complexo protrombínico|plasma', texto), texto  # SBC Quadro 24
    else:  # enoxaparina (a protamina é conferida à parte, em test_enoxaparina_urgencia_orienta_protamina)
        assert it['conduta'] != 'suspender' and not RE_ENOXA_ANTES.search(it['resumo']), \
            f'HBPM na urgência com o esquema eletivo: {it["resumo"]}'
        assert re.search(r'hora da última (?:dose|aplicação)', texto), 'urgência sem pedir a hora da última dose'
        verifica_intervalos_hbpm_asra(texto, it)


def verifica_intervalos_hbpm_asra(texto, it):
    """ASRA 2025 (e 2018): neuroaxial ≥24 h após HBPM em dose alta e ≥12 h após dose baixa."""
    mp = re.search(r'≥(\d+) h após dose plena', texto)
    mf = re.search(r'≥(\d+) h após dose profilática', texto)
    assert mp and mf, f'sem os intervalos neuroaxiais da HBPM: {texto}'
    _confere(int(mp.group(1)), [('ASRA 2025', 24, INF)], 'HBPM plena → neuroaxial (h)', it)
    _confere(int(mf.group(1)), [('ASRA 2025', 12, INF)], 'HBPM profilática → neuroaxial (h)', it)


def verifica_aviso_neuro(r):
    """Aviso neuroaxial: presente e, se citar a ASRA, com intervalos não mais curtos que os da ASRA 2025."""
    avisos = [a for a in r['avisos'] if a['titulo'] == 'Anestesia neuroaxial e anticoagulantes']
    assert len(avisos) == 1, _titulos(r)
    texto = avisos[0]['texto']
    assert 'ASRA' in texto, 'aviso neuroaxial sem a ASRA'
    m = re.search(r'anti-Xa ≥(\d+) h', texto)
    assert m and int(m.group(1)) >= 72, f'anti-Xa: ASRA pede ≥72 h: {texto}'
    m = re.search(r'dabigatrana (\d+)–(\d+) h', texto)
    assert m and int(m.group(1)) >= 72 and int(m.group(2)) >= 120, f'dabigatrana: ASRA 72–120 h: {texto}'
    assert RE_EVITAR_NEURO.search(texto) and 'ClCr <30' in texto, 'aviso sem "não fazer o bloqueio com ClCr <30"'
    verifica_intervalos_hbpm_asra(texto, {'divergencia': ''})


def verifica_doac(p, it, r):
    med, clcr = p['med'], p['clcr']
    sang = 'alto' if p['neuro'] else p['sang']
    tudo = _tudo(it, r)
    if p['protese']:  # SBC 2024 (4.3.2) e ACC/AHA 2020 valvopatias (3: Dano): DOAC contraindicado
        assert it['conduta'] == 'individualizar' and not esquema_doac(it['resumo']), \
            f'DOAC em prótese mecânica com esquema de suspensão: {it["resumo"]}'
        assert re.search(r'[Cc]ontraindicad', it['resumo'] + it['texto']) and 'prótese' in tudo.lower(), \
            'DOAC em prótese mecânica sem alerta de contraindicação'
        assert URL_VHD in [ref['url'] for ref in it['referencias']], 'sem a referência ACC/AHA 2020 (valvopatias)'
        assert re.search(r'varfarina', it['texto']), 'sem orientar a troca para varfarina'
        return
    if sang == 'minimo':
        assert it['conduta'] == 'manter' and not RE_DIAS.search(it['resumo']), it['resumo']
        return
    if sang is None:
        assert it['conduta'] == 'individualizar' and not esquema_doac(it['resumo']), it['resumo']
        assert 'Falta o risco de sangramento da cirurgia' in _titulos(r)
        if clcr is None:
            assert 'Falta o clearance de creatinina' in _titulos(r)
        return
    if clcr is None:
        assert it['conduta'] == 'individualizar' and not esquema_doac(it['resumo']), \
            f'ClCr ausente, mas o módulo escolheu um esquema: {it["resumo"]}'
        assert 'ClCr' in it['resumo'] and 'Falta o clearance de creatinina' in _titulos(r)
        m = RE_SEM_CLCR.search(it['texto'])
        assert m, f'as duas alternativas por faixa de ClCr não aparecem: {it["texto"]}'
        corte, xa, ya, corte2, xb, yb = map(int, m.groups())
        assert corte == corte2 and corte in ((50,) if med == 'dabigatrana' else (30, 50))
        for clcr_rep, x, y in ((float(corte), xa, ya), (corte - 1.0, xb, yb)):
            f = fontes_doac(med, clcr_rep, sang, p['neuro'])
            _confere(x, f['x'], f'ClCr ausente, alternativa ClCr {clcr_rep:g}: última dose D-', it)
            _confere(y, f['y'], f'ClCr ausente, alternativa ClCr {clcr_rep:g}: reinício D+', it)
        if p['neuro']:
            verifica_aviso_neuro(r)                        # inclui "sem bloqueio com ClCr <30" (dabigatrana)
        return
    f = fontes_doac(med, clcr, sang, p['neuro'])
    if f['evitar_neuro']:  # ASRA (2018 e 2025): dabigatrana com ClCr <30 → bloqueio neuroaxial não sugerido
        assert it['conduta'] == 'individualizar' and not esquema_doac(it['resumo']), \
            f'neuroaxial a evitar, mas o resumo dá um esquema: {it["resumo"]}'
        assert RE_EVITAR_NEURO.search(it['resumo'] + ' ' + it['texto']), '; '.join(f['evitar_neuro'])
        m = re.search(r'≥(\d+) dias sem dose', it['texto'])   # plano B, se a neuroaxial for indispensável
        if m:
            _confere(int(m.group(1)) + 1, f['x'], 'neuroaxial indispensável: última dose D-', it)
        verifica_aviso_neuro(r)
        return
    esquema = esquema_doac(it['resumo'])
    assert it['conduta'] == 'suspender' and esquema, f'esquema não encontrado no resumo: {it["resumo"]}'
    x, y = esquema
    _confere(x, f['x'], 'última dose D-', it)
    _confere(y, f['y'], 'reinício D+', it)
    # Nunca ponte com DOAC (AHA rec. 3: Dano; SBC 4.3.2; PAUSE; CHEST 2022)
    assert 'Sem ponte' in it['texto'] and 'Ponte com HBPM' not in it['texto']
    assert not any(t.startswith('Varfarina') for t in _titulos(r))
    if p['neuro']:
        # ASRA 2025: dose terapêutica só ≥24 h após a punção ou a retirada do cateter (6 h só na profilática); a SBC
        # (I-B) fala em 6 h sem distinguir a dose, e a diferença tem de aparecer como divergência.
        assert re.search(r'≥24 h após a punção ou a retirada do cateter', it['texto']), 'neuroaxial sem o reinício da ASRA'
        assert 'SBC' in it['divergencia'] and '≥24 h' in it['divergencia'], 'falta a divergência SBC × ASRA no reinício'
        verifica_aviso_neuro(r)


def verifica_varfarina(p, it, r):
    sang = 'alto' if p['neuro'] else p['sang']
    if sang == 'minimo':
        assert it['conduta'] == 'manter' and 'INR' in it['resumo'] + it['texto'], it['resumo']
        return
    if sang is None:
        assert it['conduta'] == 'individualizar' and 'Falta o risco de sangramento da cirurgia' in _titulos(r)
        return
    aviso = [a for a in r['avisos'] if a['titulo'].startswith('Varfarina')]
    assert len(aviso) == 1, _titulos(r)
    aviso = aviso[0]
    cat_aha, cat_sbc = aha_t14(p), sbc_t11(p)
    m = RE_ULTIMA_VARF.search(it['texto'])
    if cat_aha is None:
        assert it['conduta'] == 'individualizar' and 'indicação' in it['texto'], it['texto']
        return
    assert m, it['texto']
    assert int(m.group(1)) == int(m.group(2)) - 1, it['texto']
    x = int(m.group(2))
    # Última dose: AHA Tabela 13 (D-6), SBC Quadro 25 (5 dias), CHEST 2022 (≥5 dias), ASRA 2025 (5 dias)
    t = le_t13(('varfarina', 'te_alto' if cat_aha == {'alto'} else 'te_baixo_moderado', sang))
    fontes_x = [('AHA Tabela 13', t['x'], t['x']), ('SBC Quadro 25', 6, 6), ('CHEST 2022', 6, INF)]
    if p['neuro']:
        fontes_x.append(('ASRA 2025', 6, INF))
    _confere(x, fontes_x, 'varfarina: última dose D-', it)
    assert re.search(r'INR <1,5', it['texto']), 'sem a meta de INR <1,5 (SBC I-C; ASRA: INR normal)'
    # Categoria AHA
    mc = RE_CAT_AHA.search(aviso['texto'])
    assert mc and mc.group(1) in cat_aha, f'categoria AHA {mc and mc.group(1)} ∉ {cat_aha}: {aviso["texto"]}'
    if p['protese'] == 'aortica':
        assert 'modelo da prótese' in aviso['texto']     # bola-gaiola/disco basculante = alto (Tabela 14)
    if p['valvopatia']:
        assert 'reumática' in aviso['texto']
    if p['cancer']:
        assert 'alto risco de TEV' in aviso['texto']
    # Ponte
    ponte_aha, ponte_sbc = decide_ponte(cat_aha), decide_ponte(cat_sbc)
    resumo = it['resumo']
    ponte_mod = True if 'com ponte' in resumo else False if 'sem ponte' in resumo else None
    assert ponte_mod is not None, resumo
    divergencia = it['divergencia'] or aviso['divergencia']
    if ponte_aha is not None:
        assert ponte_mod == ponte_aha or (ponte_mod == ponte_sbc and divergencia), \
            f'ponte do módulo = {ponte_mod}; AHA (Tabela 14 {cat_aha}) = {ponte_aha}; SBC = {ponte_sbc}'
    if ponte_aha is not None and ponte_sbc is not None and ponte_aha != ponte_sbc:
        assert 'AHA' in divergencia and 'SBC' in divergencia, 'AHA e SBC divergem sobre a ponte sem texto'
    if ponte_mod:
        assert re.search(r'última HBPM 24 h antes', it['texto'])          # SBC Quadro 25; CHEST 2022
        mh, mv = RE_HEPARINA_POS.search(it['texto']), RE_VARF_VOLTA.search(it['texto'])
        assert mh and mv, it['texto']
        t_alto = le_t13(('varfarina', 'te_alto', sang))
        fontes_hep = [('AHA Tabela 13 (#)', t_alto['hbpm_pos'], t_alto['hbpm_pos']),
                      ('SBC Quadro 25', 2, 3) if sang == 'alto' else ('SBC Quadro 25', 1, INF),
                      ('CHEST 2022', 2, 3) if sang == 'alto' else ('CHEST 2022', 1, 1)]
        _confere(int(mh.group(1)), fontes_hep, 'heparina pós-operatória D+', it)
        _confere(int(mv.group(1)), [('AHA Tabela 13', t_alto['y'], t_alto['y']), ('SBC Quadro 25', 1, INF)],
                 'varfarina de volta D+', it)
    else:
        assert re.search(r'Retomar 12–24 h após', it['texto']), it['texto']   # SBC Quadro 25; AHA D+1; CHEST ≤24 h
    if p['neuro']:
        verifica_aviso_neuro(r)


def verifica_enoxaparina_depois(texto, it):
    """Dose baixa depois da cirurgia: a ACCP 2022 só a descreve na ponte da varfarina (primeiras 24 a 72 h após
    sangramento alto, até voltar a dose plena) e, após a interrupção de DOAC, no alto risco de TEV (primeiras 48 a
    72 h); a SBC 2024 fala em HBPM profilática 12 h após o procedimento no alto risco de TEV."""
    mb, md, ms = RE_ENOXA_BAIXA.search(texto), RE_ENOXA_BAIXA_DOAC.search(texto), RE_ENOXA_PROFILATICA_SBC.search(texto)
    assert mb and md and ms, texto
    assert tuple(map(int, mb.groups())) == (24, 72), mb.group(0)
    assert tuple(map(int, md.groups())) == (48, 72), md.group(0)
    assert 'pode ser usada' not in texto, 'o texto não pode recomendar a dose baixa fora dos contextos da ACCP'
    _confere(int(ms.group(1)), [('SBC 2024', 12, INF)], 'HBPM profilática: horas depois', it)
    verifica_intervalos_hbpm_asra(texto, it)


def verifica_enoxaparina_plena(p, it, r):
    """ACCP 2022 (revisão em NEJM Evidence): manhã da véspera, com metade da dose diária; SBC: 24 h antes (IIa-C)."""
    texto = it['texto']
    if not p['neuro'] and p['sang'] == 'minimo':
        # Revisão de Douketis, Tabela 1 (nota §) e Figura 1: sem esquema de HBPM no sangramento mínimo. O item não aplica
        # a ponte, não manda suspender nem manter, e diz que a fonte não descreve o manejo.
        tudo = it['resumo'] + ' ' + texto + ' ' + it['divergencia']
        assert it['conduta'] == 'individualizar', it['conduta']
        assert not RE_ENOXA_PLENA_ACCP.search(tudo) and not RE_ENOXA_ANTES.search(tudo) and not RE_ENOXA_RETORNO.search(tudo), tudo
        assert not re.search(r'véspera|metade da dose|D-\d|[Ss]uspender|[Mm]anter', tudo), tudo
        assert 'não descreve o manejo da HBPM em dose plena nesse cenário' in texto and 'individualizada' in texto, texto
        assert URL_ACCP_NEJM in [ref['url'] for ref in it['referencias']], 'sem a referência da ACCP 2022'
        return
    assert it['conduta'] == 'suspender' and 'manhã da véspera' in it['resumo'] and 'metade da dose' in it['resumo']
    ma, ms, mr = RE_ENOXA_PLENA_ACCP.search(texto), RE_ENOXA_PLENA_SBC.search(texto), RE_ENOXA_RETORNO.search(texto)
    assert ma and ms and mr, texto
    assert int(ma.group(1)) == 1, 'ACCP 2022: a última dose plena é na manhã da véspera (D-1)'
    _confere(int(ms.group(1)), [('SBC Quadro 25', 24, INF)], 'HBPM plena pela SBC: horas antes', it)
    depois, lo, hi = map(int, mr.groups())
    _confere(depois, [('ACCP 2022', 24, INF)], 'HBPM plena: horas depois (sangramento baixo ou moderado)', it)
    assert (lo, hi) == (48, 72), 'ACCP 2022: 48 a 72 h após sangramento alto'
    # Hemostasia e exceção do sangramento alto (p. 4 da revisão)
    me = RE_ENOXA_EXCECAO_ALTO.search(texto)
    assert RE_ENOXA_HEMOSTASIA.search(texto) and me, texto
    assert tuple(map(int, me.groups())) == (3, 5), 'ACCP 2022: dose baixa por 3 a 5 dias'
    # ACCP e SBC definem esses intervalos para a HBPM na ponte: o texto e a classe dizem que o uso contínuo é extensão
    assert RE_ENOXA_PONTE_ACCP.search(texto) and RE_ENOXA_PONTE_SBC.search(texto), texto
    assert it['classe'].count('(extrapolado da ponte)') == 2 and 'ACCP 2022 (extrapolado da ponte)' in it['classe']
    # A redação da última dose difere entre ACCP e SBC: aparece no aviso, sem escolha entre as sociedades
    assert 'ACCP 2022' in it['divergencia'] and 'SBC 2024' in it['divergencia'], it['divergencia']
    assert 'manhã da véspera' in it['divergencia'] and '24 h antes' in it['divergencia']
    assert 'compatíveis no horário' in it['divergencia'] and 'meia dose da véspera' in it['divergencia']
    assert not re.search(r'optamos|seguir', it['divergencia']), it['divergencia']
    assert URL_ACCP_NEJM in [ref['url'] for ref in it['referencias']], 'sem a referência da ACCP 2022'
    verifica_enoxaparina_depois(texto, it)


def verifica_enoxaparina_profilatica(p, it, r):
    """Dose profilática antes da cirurgia: nenhuma das fontes fixa o intervalo, e o item não pode inventar um."""
    texto = it['texto']
    assert it['conduta'] == 'individualizar', it['conduta']
    assert not RE_ENOXA_ANTES.search(it['resumo'] + ' ' + texto) and 'manhã da véspera' not in it['resumo'] + texto, \
        f'dose profilática com o esquema da dose plena: {it["resumo"]} {texto}'
    assert not re.search(r'D-\d', it['resumo'] + texto), 'dose profilática com dia de suspensão que as fontes não dão'
    assert re.search(r'não fixam o intervalo entre a última dose e a cirurgia', texto), texto
    assert it['divergencia'] == ''
    assert URL_ACCP_NEJM in [ref['url'] for ref in it['referencias']], 'sem a referência da ACCP 2022'
    verifica_enoxaparina_depois(texto, it)


def verifica_enoxaparina(p, it, r):
    sang = 'alto' if p['neuro'] else p['sang']
    if p['dose']:
        {'plena': verifica_enoxaparina_plena, 'profilatica': verifica_enoxaparina_profilatica}[p['dose']](p, it, r)
        if p['neuro']:
            verifica_aviso_neuro(r)
        return
    assert it['texto'].startswith('Informe se a dose é plena ou profilática.'), it['texto']
    m = RE_ENOXA_ANTES.search(it['resumo'])
    assert m, it['resumo']
    # Última dose plena 24 h antes: SBC Quadro 25 (IIa-C), CHEST 2022 (~24 h), ASRA 2025 (dose alta, 24 h)
    _confere(int(m.group(1)), [('SBC Quadro 25', 24, INF), ('CHEST 2022', 24, INF)] +
             ([('ASRA 2025', 24, INF)] if p['neuro'] else []), 'HBPM: horas antes', it)
    md = RE_ENOXA_DEPOIS.search(it['texto'])
    assert md, it['texto']
    depois, lo, hi = map(int, md.groups())
    _confere(depois, [('SBC Quadro 25', 24, INF), ('CHEST 2022', 24, INF)], 'HBPM: horas depois', it)
    if sang in ('alto', None):
        _confere(lo, [('SBC Quadro 25', 48, 72), ('CHEST 2022', 48, 72)], 'HBPM, sangramento alto: horas depois', it)
        _confere(hi, [('SBC Quadro 25', 48, 72), ('CHEST 2022', 48, 72)], 'HBPM, sangramento alto: horas depois', it)
    if p['neuro']:
        verifica_aviso_neuro(r)


def _param(p):
    marcas = ()
    if p['id'] in DISCREPANCIAS:
        marcas = (pytest.mark.xfail(strict=True, reason=DISCREPANCIAS[p['id']]),)
    return pytest.param(p, id=p['id'], marks=marcas)


@pytest.mark.parametrize('p', [_param(p) for p in CASOS])
def test_paciente_anticoagulante(p):
    r = pm.condutas([p['med']], contexto(p))
    it = _item(r, p['med'])
    sang = 'alto' if p['neuro'] else p['sang']
    if p['urg'] in ('urgencia', 'emergencia') and sang != 'minimo':
        verifica_urgencia(p, it, r)
    elif p['med'] in DOAC:
        verifica_doac(p, it, r)
    elif p['med'] == 'varfarina':
        verifica_varfarina(p, it, r)
    else:
        verifica_enoxaparina(p, it, r)


# ---------------------------------------------------------------------------------------------------------------
# Propriedades transversais
# ---------------------------------------------------------------------------------------------------------------
def test_pacientes_distintos_e_suficientes():
    assert len(CASOS) >= 130
    assert len({p['id'] for p in CASOS}) == len(CASOS)
    chaves = {tuple(sorted((k, str(v)) for k, v in p.items() if k != 'id')) for p in CASOS}
    assert len(chaves) == len(CASOS), 'há pacientes com dados idênticos'


def test_rotulos_cha2ds2vasc_dos_ids_conferem():
    for p in CASOS:
        m = re.search(r'cha2ds2vasc(\d)', p['id'])
        if m:
            assert cha2ds2vasc(p) == int(m.group(1)), p['id']


@pytest.mark.parametrize('farmaco,sang', [(f, s) for f in DOAC for s in ('baixo_moderado', 'alto')],
                         ids=lambda v: v)
def test_monotonia_clcr(farmaco, sang):
    """ClCr menor nunca encurta a interrupção (AHA Tabela 13; SBC Quadro 26; PAUSE)."""
    anterior = 0
    for clcr in (120, 90, 80, 60, 55, 50, 49, 45, 40, 35, 30, 29, 25, 20, 15):
        r = pm.condutas([farmaco], {'clcr': float(clcr), 'sangramento': sang, 'condicoes': {'fa'}})
        x, _ = esquema_doac(r['itens'][0]['resumo'])
        assert x >= anterior, f'{farmaco}: ClCr {clcr} deu D-{x}, mais curto que D-{anterior} com ClCr maior'
        anterior = x


@pytest.mark.parametrize('farmaco,sang', [(f, s) for f in DOAC for s in ('baixo_moderado', 'alto')],
                         ids=lambda v: v)
def test_insuficiencia_renal_alonga_interrupcao(farmaco, sang):
    """AHA Tabela 13: linha "renal impairment" (anti-Xa ClCr <30; dabigatrana <50) com mais dias sem dose que a de
    função normal, nos dois níveis de sangramento (a SBC também alonga no sangramento baixo)."""
    clcr_reduzido = 45.0 if farmaco == 'dabigatrana' else 25.0
    x = {}
    for clcr in (80.0, clcr_reduzido):
        r = pm.condutas([farmaco], {'clcr': clcr, 'sangramento': sang, 'condicoes': {'fa'}})
        x[clcr] = esquema_doac(r['itens'][0]['resumo'])[0]
    grupo = 'dabigatrana' if farmaco == 'dabigatrana' else 'anti_xa'
    assert le_t13((grupo, 'renal', sang))['x'] > le_t13((grupo, 'normal', sang))['x']
    assert x[clcr_reduzido] > x[80.0], x


@pytest.mark.parametrize('farmaco', DOAC)
def test_neuroaxial_nunca_mais_curto_que_sangramento_alto(farmaco):
    """Neuroaxial = pelo menos o esquema de sangramento alto. Exceção: dabigatrana com ClCr <30, em que a ASRA não
    sugere o bloqueio — aí o esperado é o alerta, não um esquema de dias."""
    for clcr in (100.0, 45.0, 25.0):
        alto = pm.condutas([farmaco], {'clcr': clcr, 'sangramento': 'alto'})['itens'][0]
        for sang in ('minimo', 'baixo_moderado', None):
            neuro = pm.condutas([farmaco], {'clcr': clcr, 'sangramento': sang, 'neuroaxial': True})['itens'][0]
            if fontes_doac(farmaco, clcr, 'alto', True)['evitar_neuro']:
                assert neuro['conduta'] == 'individualizar' and esquema_doac(neuro['resumo']) is None, neuro['resumo']
                assert RE_EVITAR_NEURO.search(neuro['resumo'] + ' ' + neuro['texto']), (clcr, sang)
                continue
            assert esquema_doac(neuro['resumo'])[0] >= esquema_doac(alto['resumo'])[0], (clcr, sang)


def _casos_enoxaparina_urgente():
    return [pytest.param(p, id=p['id'] + '-protamina',
                         marks=pytest.mark.xfail(strict=True, reason=_MOTIVO_PROTAMINA))
            for p in CASOS if p['med'] == 'enoxaparina' and p['urg'] in ('urgencia', 'emergencia')]


@pytest.mark.parametrize('p', _casos_enoxaparina_urgente())
def test_enoxaparina_urgencia_orienta_protamina(p):
    """HBPM na urgência com sangramento relevante: protamina neutraliza parcialmente o efeito (ACCP 9ª ed.)."""
    it = _item(pm.condutas([p['med']], contexto(p)), p['med'])
    assert re.search(r'protamina', it['resumo'] + ' ' + it['texto'], re.I), it['texto']


def test_oraculo_tabela13_concorda_com_pause_nas_linhas_comuns():
    """Autoverificação da transcrição: linhas de função normal da Tabela 13 = protocolo PAUSE (1 ou 2 dias sem dose;
    dabigatrana com ClCr <50: 2 ou 4 dias)."""
    for grupo in ('anti_xa', 'dabigatrana'):
        assert le_t13((grupo, 'normal', 'baixo_moderado'))['x'] == 2
        assert le_t13((grupo, 'normal', 'alto'))['x'] == 3
        assert le_t13((grupo, 'normal', 'minimo'))['interrompe'] is False
    assert le_t13(('dabigatrana', 'renal', 'baixo_moderado'))['x'] == 3
    assert le_t13(('dabigatrana', 'renal', 'alto'))['x'] == 5
    assert le_t13(('varfarina', 'te_baixo_moderado', 'alto'))['x'] == 6          # 5 dias sem dose (SBC/CHEST)
    assert le_t13(('varfarina', 'te_alto', 'alto'))['ponte'] is True
    assert le_t13(('varfarina', 'te_baixo_moderado', 'alto'))['ponte'] is False
    assert le_t13(('varfarina', 'te_alto', 'alto'))['hbpm_pos'] == 3
    assert le_t13(('varfarina', 'te_alto', 'baixo_moderado'))['hbpm_pos'] == 2


def test_oraculo_escores():
    fem80 = dict(BASE, idade=80, sexo='feminino', fa=True, has=True, dm=True, ic=True, vasc='dap', avc='antigo')
    assert cha2ds2vasc(fem80) == 9 and chads2(fem80) == 6
    assert cha2ds2vasc(dict(BASE, idade=52, has=True)) == 1
    assert aha_t14(dict(BASE, protese='mitral')) == {'alto'}
    assert aha_t14(dict(BASE, protese='aortica')) == {'baixo'} and sbc_t11(dict(BASE, protese='aortica')) == {'alto'}
