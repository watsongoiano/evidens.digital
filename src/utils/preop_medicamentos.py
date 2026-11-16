"""Pré-operatório de cirurgia não cardíaca: conduta perioperatória para cada medicamento de uso contínuo.

Entrada: chaves de ``src.utils.medicamentos.MEDICAMENTOS`` e um contexto clínico (ver ``condutas``). Saída: um item
por medicamento que tem recomendação nas fontes, mais avisos transversais (ponte na varfarina, janela após ICP,
ClCr que falta, anestesia neuroaxial...). Texto para o médico, não para o paciente.

Fontes (só entra o que tem fonte citável; o que não tem não gera item):
- AHA/ACC 2026: reafirmação, com texto idêntico, da diretriz de 2024 (Thompson et al., Circulation
  2024;150:e351–e442). §6.2, §6.3, §7.1–7.8 e Tabelas 12–14. As classes vêm das caixas de recomendação.
- SBC 2024, Diretriz de Avaliação Cardiovascular Perioperatória (Gualandro et al., Arq Bras Cardiol
  2024;121(9):e20240590): Quadros 8–26, Tabelas 11–12 e texto.
- Orientação multissocietária sobre agonistas do receptor de GLP-1 (Kindel et al., Clin Gastroenterol Hepatol 2024):
  "guidance", sem gradação.
- SPAQI (consenso Delphi, sem gradação): medicações endócrinas, hormonais e urológicas (Pfeifer et al., Mayo Clin
  Proc 2021) e psiquiátricas (Oprea et al., Mayo Clin Proc 2022).
- ACR/AAHKS 2022 (Goodman et al., Arthritis Rheumatol 2022): antirreumáticos na artroplastia eletiva de quadril ou
  joelho; fora dela, evidência indireta.
- ESE/Endocrine Society 2024 (Beuschlein et al., J Clin Endocrinol Metab 2024): insuficiência adrenal induzida por
  glicocorticoide.
- SBD/SBA/ABESO 2026 (Diabetol Metab Syndr 2026;18:91; versão em inglês da Diretriz SBD 2025): antidiabéticos e
  insulinas (R4–R15, Tabela 2); aGLP-1 pela nota da SBA de 15/05/2026 (C.SBA-01744/2026).

Convenções:
- D0 = dia da cirurgia. "Dias sem dose" são dias inteiros antes do D0 em que o fármaco não é tomado.
- Risco de sangramento nos 3 níveis da AHA (Tabela 13): mínimo (~0% de sangramento maior em 30 dias: catarata,
  odontologia ou dermatologia menores), baixo/moderado (<2%) e alto (≥2%). Na SBC (Tabela 12: baixo 0–2%,
  alto 2–4%), mínimo e baixo/moderado contam como "baixo" e alto como "alto". Anestesia neuroaxial conta como
  sangramento alto (SBC, texto do 4.3.2.6; AHA, texto do §7.6).
- Quando AHA e SBC divergem, ``divergencia`` traz as duas posições e, quando escolhemos uma, "Nós optamos por
  seguir …".
- Associações em dose fixa geram um item só, com a regra do componente que mais restringe (o comprimido não se
  divide), e o texto cita o outro componente: IECA/BRA + diurético/BCC seguem o IECA/BRA; betabloqueador +
  diurético segue o betabloqueador; estatina + ezetimiba segue a estatina; iSGLT2 + metformina/iDPP-4 seguem o
  iSGLT2; iDPP-4 + metformina seguem a metformina (não tomar no dia); insulina + aGLP-1 seguem o aGLP-1.
- Medicamento sem recomendação perioperatória nas fontes não gera item (não se presume "manter"). Entre eles:
  ezetimiba e outros hipolipemiantes isolados, nitratos, ticlopidina, cilostazol, insulinas bifásica e icodeca,
  hipnóticos não benzodiazepínicos, metilfenidato, anticonvulsivantes, inalatórios, IBP, imunossupressores fora do
  escopo do ACR/AAHKS (sirolimo, everolimo, natalizumabe, ocrelizumabe, vedolizumabe, fingolimode).
"""
from __future__ import annotations

from src.utils.medicamentos import MEDICAMENTOS

# ---------------------------------------------------------------------------------------------------------------
# Referências
# ---------------------------------------------------------------------------------------------------------------
_URL_AHA = ('https://professional.heart.org/en/science-news/'
            '2026-guideline-for-perioperative-cardiovascular-management-for-noncardiac-surgery')
_URL_AHA_2024 = 'https://doi.org/10.1161/CIR.0000000000001285'
_URL_SBC = 'https://doi.org/10.36660/abc.20240590'
_URL_GLP1 = 'https://doi.org/10.1016/j.cgh.2024.10.003'
_URL_SPAQI_ENDO = 'https://doi.org/10.1016/j.mayocp.2020.10.002'
_URL_SPAQI_PSIQ = 'https://doi.org/10.1016/j.mayocp.2021.11.011'
_URL_ACR = 'https://doi.org/10.1002/art.42140'
_URL_ESE = 'https://doi.org/10.1210/clinem/dgae250'
_URL_SBD = 'https://doi.org/10.1186/s13098-025-02060-5'
_URL_SBD_PT = 'https://diretriz.diabetes.org.br/rastreamento-e-controle-da-hiperglicemia-no-perioperatorio-2/'
_URL_SBA_GLP1 = ('https://www.sbahq.org/nota-da-sba-de-atualizacao-sobre-as-recomendacoes-do-manejo-perioperatorio-'
                 'dos-agonistas-do-receptor-glp-1-e-coagonistas-glp-1-gip/')
_URL_KDIGO_DM = 'https://doi.org/10.1016/j.kint.2022.06.008'
_URL_ASRA = 'https://doi.org/10.1097/AAP.0000000000000763'
_URL_VALVAS = 'https://doi.org/10.1161/CIR.0000000000000923'
_URL_MEC = 'https://doi.org/10.15585/mmwr.rr7304a1'

REFERENCIAS = {
    'aha': {'label': 'AHA/ACC 2026, Manejo cardiovascular perioperatório em cirurgia não cardíaca', 'url': _URL_AHA},
    'aha_2024': {'label': 'AHA/ACC 2024, texto integral (Circulation 2024;150:e351–e442)', 'url': _URL_AHA_2024},
    'sbc': {'label': 'SBC 2024, Diretriz de Avaliação Cardiovascular Perioperatória', 'url': _URL_SBC},
    'glp1': {'label': 'Orientação multissocietária sobre aGLP-1 no perioperatório (Clin Gastroenterol Hepatol 2024)',
             'url': _URL_GLP1},
    'spaqi_endo': {'label': 'SPAQI 2021, medicações endócrinas, hormonais e urológicas (Mayo Clin Proc)',
                   'url': _URL_SPAQI_ENDO},
    'spaqi_psiq': {'label': 'SPAQI 2022, medicações psiquiátricas (Mayo Clin Proc)', 'url': _URL_SPAQI_PSIQ},
    'acr': {'label': 'ACR/AAHKS 2022, antirreumáticos na artroplastia de quadril e joelho', 'url': _URL_ACR},
    'ese': {'label': 'ESE/Endocrine Society 2024, insuficiência adrenal induzida por glicocorticoide', 'url': _URL_ESE},
    'sbd': {'label': 'SBD/SBA/ABESO 2026, hiperglicemia no perioperatório (Diabetol Metab Syndr 2026;18:91)',
            'url': _URL_SBD},
    'sbd_pt': {'label': 'Diretriz SBD 2025, Rastreamento e controle da hiperglicemia no perioperatório', 'url': _URL_SBD_PT},
    'sba_glp1': {'label': 'SBA 2026, nota C.SBA-01744/2026 sobre aGLP-1 e coagonistas GLP-1/GIP no perioperatório',
                 'url': _URL_SBA_GLP1},
    'kdigo_dm': {'label': 'KDIGO 2022, diabetes na doença renal crônica', 'url': _URL_KDIGO_DM},
    'asra': {'label': 'ASRA 2018 (4ª ed.), anestesia regional e antitrombóticos', 'url': _URL_ASRA},
    'valvas': {'label': 'ACC/AHA 2020, valvopatias (Circulation 2021;143:e72–e227)', 'url': _URL_VALVAS},
    'mec': {'label': 'CDC US MEC 2024, critérios de elegibilidade para contraceptivos (MMWR 2024;73(4))',
            'url': _URL_MEC},
}


def _aha(onde):
    return [{'label': f'AHA/ACC 2026, {onde}', 'url': _URL_AHA}, dict(REFERENCIAS['aha_2024'])]


def _sbc(onde):
    return [{'label': f'SBC 2024, {onde}', 'url': _URL_SBC}]


def _ref(nome):
    return [dict(REFERENCIAS[nome])]


def _refs(*listas):
    saida, vistos = [], set()
    for lista in listas:
        for r in lista:
            if (r['label'], r['url']) not in vistos:
                vistos.add((r['label'], r['url']))
                saida.append(r)
    return saida


# ---------------------------------------------------------------------------------------------------------------
# Grupos de medicamentos com regra própria
# ---------------------------------------------------------------------------------------------------------------
_AAS = 'aas_acido_acetilsalicilico'
_P2Y12 = {'clopidogrel': ('clopidogrel', 5, '5–7'), 'ticagrelor': ('ticagrelor', 5, '3–5'),
          'prasugrel': ('prasugrel', 7, '7–10')}
_ANTI_XA = {'apixabana', 'rivaroxabana', 'edoxabana'}
_DOAC = _ANTI_XA | {'dabigatrana'}
_ANTICOAGULANTES = _DOAC | {'varfarina', 'enoxaparina'}

_GLP1_SEMANAL = {'semaglutida', 'dulaglutida', 'tirzepatida'}
_GLP1_DIARIO = {'liraglutida'}
_INSULINA_BASAL = {'insulina_glargina', 'insulina_degludeca', 'insulina_detemir'}
_INSULINA_NPH = {'insulina_nph'}
_INSULINA_PRANDIAL = {'insulina_regular', 'insulina_asparte', 'insulina_lispro', 'insulina_glulisina'}
_INSULINA_GLP1 = {'insulina_glargina_lixisenatida': ('insulina_glargina', 'lixisenatida'),
                  'insulina_degludeca_liraglutida': ('insulina_degludeca', 'liraglutida')}

_OUTROS_ANTI_HAS = {'hidralazina', 'metildopa', 'minoxidil_oral'}
_CARDIO_IC = {'cardio_outro', 'amiodarona', 'digoxina', 'sotalol'}

_DMARD_MANTER = {'metotrexato', 'leflunomida', 'hidroxicloroquina', 'sulfassalazina'}
_BIOLOGICOS = {'adalimumabe', 'etanercepte', 'infliximabe', 'golimumabe', 'certolizumabe_pegol', 'tocilizumabe',
               'abatacepte', 'secuquinumabe', 'ixequizumabe', 'ustequinumabe', 'risanquizumabe', 'guselcumabe',
               'rituximabe'}
_JAK = {'tofacitinibe', 'upadacitinibe', 'baricitinibe'}
_LES = {'micofenolato', 'azatioprina', 'ciclosporina', 'tacrolimo'}

_BENZODIAZEPINICOS = {'clonazepam', 'alprazolam', 'bromazepam', 'diazepam', 'lorazepam'}
_ANFETAMINAS = {'lisdexanfetamina'}
_ESTROGENIOS = {'anticoncepcional_combinado', 'terapia_hormonal_da_menopausa'}
_TIREOIDE = {'levotiroxina', 'metimazol_tiamazol', 'propiltiouracila'}

_ANTIDIABETICOS = {'metformina', 'sulfonilureia', 'idpp4_pioglitazona', 'isglt2', 'aglp1', 'insulina'}

# Condições que marcam prevenção secundária (AAS) e doença vascular (CHA₂DS₂-VASc)
_SECUNDARIA = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'avc_ait', 'avc_ait_recente',
               'doenca_arterial_periferica'}
_VASCULAR = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'doenca_arterial_periferica'}
_DAC = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica'}

_ORDEM_RISCO = {'baixo': 0, 'moderado': 1, 'alto': 2}


# ---------------------------------------------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------------------------------------------
def _cond(ctx):
    return set(ctx.get('condicoes') or ())


def _ic(cond):
    return bool(cond & {'ic', 'ic_fe_reduzida'})


def _dias(n):
    return f'{n} dia' if n == 1 else f'{n} dias'


def _num(x):
    return f'{x:g}'.replace('.', ',')


def _item(chave, conduta, resumo, texto, classe, referencias, divergencia=''):
    return {'chave': chave, 'medicamento': MEDICAMENTOS[chave]['rotulo'], 'conduta': conduta, 'resumo': resumo,
            'texto': texto, 'classe': classe, 'referencias': referencias, 'divergencia': divergencia}


def _aviso(titulo, texto, referencias, divergencia=''):
    return {'titulo': titulo, 'texto': texto, 'referencias': referencias, 'divergencia': divergencia}


def _cautela_hipotensao(ctx):
    idade = ctx.get('idade')
    if idade is not None and idade >= 65:
        return (' Cautela ao manter anti-hipertensivo em ≥65 anos, com PA baixa ou limítrofe ou alto risco de '
                'hipotensão (nota da AHA ao §6.2).')
    return ''


def _sangramento(ctx):
    """Risco de sangramento efetivo: anestesia neuroaxial conta como alto (SBC 4.3.2.6; AHA §7.6)."""
    if ctx.get('neuraxial'):
        return 'alto'
    return ctx.get('sangramento')


_ROTULO_SANGRAMENTO = {'minimo': 'mínimo', 'baixo_moderado': 'baixo/moderado', 'alto': 'alto'}


# ---------------------------------------------------------------------------------------------------------------
# Escores e risco tromboembólico
# ---------------------------------------------------------------------------------------------------------------
def _componentes_cha2ds2vasc(ctx):
    cond = _cond(ctx)
    idade, sexo = ctx.get('idade'), ctx.get('sexo')
    comp = []
    if _ic(cond):
        comp.append(('IC', 1))
    if 'hipertensao' in cond:
        comp.append(('hipertensão', 1))
    if idade is not None and idade >= 75:
        comp.append(('idade ≥75 anos', 2))
    elif idade is not None and idade >= 65:
        comp.append(('idade 65–74 anos', 1))
    if cond & {'diabetes', 'diabetes_insulina'}:
        comp.append(('diabetes', 1))
    if cond & {'avc_ait', 'avc_ait_recente'}:
        comp.append(('AVC/AIT prévio', 2))
    if cond & _VASCULAR or ctx.get('stent'):
        comp.append(('doença vascular', 1))
    if sexo == 'feminino':
        comp.append(('sexo feminino', 1))
    faltas = [nome for nome, valor in (('idade', idade), ('sexo', sexo)) if valor is None]
    return comp, faltas


def cha2ds2vasc(ctx) -> int:
    """CHA₂DS₂-VASc (o escore da AHA, Tabela 14) a partir de idade, sexo e condições do contexto.

    Doença vascular = DAC (inclui stent e revascularização) ou doença arterial periférica. Idade ou sexo ausentes
    não pontuam (os avisos dizem o que falta).
    """
    comp, _ = _componentes_cha2ds2vasc(ctx or {})
    return sum(v for _, v in comp)


def chads2(ctx) -> int:
    """CHADS₂ (o escore da SBC, Tabela 11): IC 1, HAS 1, idade ≥75 1, DM 1, AVC/AIT 2."""
    ctx = ctx or {}
    cond = _cond(ctx)
    idade = ctx.get('idade')
    return (_ic(cond) + ('hipertensao' in cond) + (idade is not None and idade >= 75)
            + bool(cond & {'diabetes', 'diabetes_insulina'}) + 2 * bool(cond & {'avc_ait', 'avc_ait_recente'}))


def _descreve_escore(nome, valor, comp):
    if not comp:
        return f'{nome} = {valor}'
    partes = ', '.join(f'{c} ({v})' if v > 1 else c for c, v in comp)
    return f'{nome} = {valor} ({partes})'


def _risco_te_aha(ctx):
    """Categoria de risco tromboembólico pela AHA (Tabela 14, adaptada de Douketis/CHEST 2022).

    Devolve (categoria ou None, motivos, faltas). 'tev' sem 'tev_recente_3m'/'tev_3_12m' é lido como TEV há
    >12 meses; prótese mecânica não mitral é lida como aórtica de duplo folheto.
    """
    cond = _cond(ctx)
    motivos, faltas = [], []
    escore = cha2ds2vasc(ctx)
    recente = 'avc_ait_recente' in cond

    def marca(cat, motivo):
        motivos.append((cat, motivo))

    if 'fa' in cond:
        if escore >= 7:
            marca('alto', f'FA com CHA₂DS₂-VASc {escore}')
        elif escore >= 5 and recente:
            marca('alto', f'FA com CHA₂DS₂-VASc {escore} e AVC/AIT recente')
        elif escore >= 5:
            marca('moderado', f'FA com CHA₂DS₂-VASc {escore}')
        elif cond & {'avc_ait', 'avc_ait_recente'}:
            if not recente:
                marca('moderado', f'FA com CHA₂DS₂-VASc {escore} e AVC/AIT prévio (fora das faixas explícitas da '
                                  'Tabela 14: o baixo risco exige ausência de AVC prévio)')
        else:
            marca('baixo', f'FA com CHA₂DS₂-VASc {escore}, sem AVC prévio')
        if 'valvopatia' in cond:
            faltas.append('se a valvopatia é reumática (FA com valvopatia reumática é alto risco)')
    if recente:
        marca('alto', 'AVC/AIT há <3 meses')
    if 'tev_recente_3m' in cond:
        marca('alto', 'TEV há <3 meses')
    elif 'tev_3_12m' in cond:
        marca('moderado', 'TEV há 3–12 meses')
    elif 'tev' in cond:
        marca('baixo', 'TEV há >12 meses')
    if 'trombofilia_grave' in cond:
        marca('alto', 'trombofilia grave')
    if 'cancer_ativo' in cond:
        marca('moderado', 'câncer ativo')
        faltas.append('se o câncer tem alto risco de TEV (alto risco na Tabela 14)')
    if 'protese_mecanica_mitral' in cond:
        marca('alto', 'prótese mecânica mitral')
    elif 'protese_mecanica' in cond:
        # Fatores maiores (Tabela 14): FA, AVC/AIT múltiplos, AVC perioperatório prévio ou trombose de prótese. Um
        # AVC/AIT isolado não basta; o recente (< 3 meses) já é alto risco por si.
        fatores = [f for f, c in (('FA', 'fa'),) if c in cond]
        if fatores:
            marca('moderado', 'prótese aórtica mecânica de duplo folheto com fator maior: ' + ', '.join(fatores))
        else:
            marca('baixo', 'prótese aórtica mecânica de duplo folheto sem fator maior')
        faltas.append('o modelo da prótese (bola-gaiola ou disco basculante são alto risco)')
    if not motivos:
        return None, [], ['a indicação da anticoagulação (FA, TEV ou prótese mecânica)']
    cat = max((c for c, _ in motivos), key=_ORDEM_RISCO.get)
    return cat, [m for c, m in motivos if c == cat], faltas


def _risco_te_sbc(ctx):
    """Categoria de risco tromboembólico pela SBC (Tabela 11, CHADS₂; toda prótese mecânica = alto, texto 4.3)."""
    cond = _cond(ctx)
    motivos, notas = [], []
    escore = chads2(ctx)

    def marca(cat, motivo):
        motivos.append((cat, motivo))

    if 'fa' in cond:
        if escore >= 5:
            marca('alto', f'FA com CHADS₂ {escore}')
        elif escore >= 3:
            marca('moderado', f'FA com CHADS₂ {escore}')
        elif cond & {'avc_ait', 'avc_ait_recente'}:
            marca('moderado', f'FA com CHADS₂ {escore} e AVC/AIT prévio (o baixo risco exige ausência de AVC/AIT)')
        else:
            marca('baixo', f'FA com CHADS₂ {escore}, sem AVC/AIT')
        if cond & {'avc_ait'} and 'avc_ait_recente' not in cond and escore < 5:
            notas.append('AVC/AIT há >3 meses com CHADS₂ <5 também pode ser considerado alto risco (nota da Tabela 11)')
    if 'avc_ait_recente' in cond:
        marca('alto', 'AVC/AIT há <3 meses')
    if 'tev_recente_3m' in cond:
        marca('alto', 'TEV há <3 meses')
    elif 'tev_3_12m' in cond:
        marca('moderado', 'TEV há 3–12 meses')
    elif 'tev' in cond:
        marca('baixo', 'TEV há >12 meses')
    if 'trombofilia_grave' in cond:
        marca('alto', 'trombofilia grave')
    if 'cancer_ativo' in cond:
        marca('moderado', 'neoplasia ativa')
    if cond & {'protese_mecanica', 'protese_mecanica_mitral'}:
        marca('alto', 'prótese valvar mecânica, que a SBC considera de alto risco em qualquer posição')
    if not motivos:
        return None, [], notas
    cat = max((c for c, _ in motivos), key=_ORDEM_RISCO.get)
    return cat, [m for c, m in motivos if c == cat], notas


# ---------------------------------------------------------------------------------------------------------------
# Janela após ICP
# ---------------------------------------------------------------------------------------------------------------
def _sbc_classe_janela(indicacao, meses):
    """(classe, quadro, faixa) da SBC para o intervalo ICP → cirurgia (Quadro 22: ICP eletiva; Quadro 23: SCA)."""
    if indicacao == 'sca':
        faixas = ((12, 'I-A', '≥12 meses'), (6, 'IIa-B', '6–12 meses'), (1, 'IIb-B', '30 dias a 6 meses'))
        quadro = 'Quadro 23'
    else:
        faixas = ((6, 'I-A', '≥6 meses'), (3, 'IIa-B', '3–6 meses'), (1, 'IIb-B', '30 dias a 3 meses'))
        quadro = 'Quadro 22'
    for limite, classe, rotulo in faixas:
        if meses >= limite:
            return classe, quadro, rotulo
    return 'III-B', quadro, '<30 dias'


def _sbc_janela(indicacao, meses):
    classe, quadro, rotulo = _sbc_classe_janela(indicacao, meses)
    texto = f'SBC ({quadro}): intervalo de {rotulo}, {classe}.'
    if 1 <= meses < 3:
        texto += ' Cirurgia de baixo risco de sangramento pode ser feita na vigência da DAPT (IIa-C, Quadro 21).'
    return texto


def _janela_icp(ctx):
    """Situação da cirurgia em relação à ICP prévia (AHA §7.5 recs. 2–10; SBC Quadros 21–23), com os mesmos prazos
    da tela de adiamentos (src/utils/preoperatorio.py).

    fase: 'proibitiva' (stent ≤ 30 dias), 'urgente' (urgência ou emergência até 1 ano da ICP), 'manter_dapt' (DES
    < 3 meses e cirurgia tempo-sensível), 'adiar' (eletiva dentro do prazo da indicação), 'indefinida' (faltam dados)
    ou 'liberada'. Sem a indicação da ICP, vale o prazo mais longo (SCA).
    """
    st = ctx.get('stent')
    cond = _cond(ctx)
    if not st:
        if 'stent' in cond:
            return {'fase': 'indefinida', 'faltas': ['tipo do stent, indicação da ICP e data da ICP'],
                    'aha': '', 'sbc': '', 'div': '', 'tempo_sensivel': False}
        return None
    tipo, indicacao = st.get('tipo'), st.get('indicacao')
    dias = st.get('dias')
    if dias is None and st.get('meses') is not None:
        dias = float(st['meses']) * 30.44
    urg = ctx.get('urgencia')
    tempo_sensivel = urg in ('tempo_sensivel', 'urgencia', 'emergencia')
    faltas = [n for n, v in (('tipo do stent', tipo), ('data da ICP', dias)) if v is None]
    r = {'faltas': faltas, 'aha': '', 'sbc': '', 'div': '', 'classe': '', 'dias': dias, 'tipo': tipo,
         'indicacao': indicacao, 'tempo_sensivel': tempo_sensivel, 'urgencia': urg}
    if tipo is None or dias is None:
        r['fase'] = 'indefinida'
        return r
    m = dias / 30.44
    if urg in ('urgencia', 'emergencia'):
        if dias < 365:
            r['fase'] = 'urgente'
            r['sbc'] = ('SBC (Quadro 21, I-C): na cirurgia que não pode esperar, manter o AAS e, se o risco de '
                        'sangramento permitir, o inibidor de P2Y12; operar em centro com suporte multidisciplinar e '
                        'hemodinâmica.')
        else:
            r['fase'] = 'liberada'
        return r
    if tipo == 'balao':
        if dias < 14:
            r['fase'] = 'adiar'
            r['classe'] = 'AHA 1 (C-LD)'
            r['aha'] = 'AHA: após angioplastia só com balão, adiar a cirurgia eletiva por no mínimo 14 dias (1, C-LD).'
        else:
            r['fase'] = 'liberada'
            r['aha'] = 'AHA: angioplastia só com balão há ≥14 dias; cirurgia eletiva liberada pelo intervalo (1, C-LD).'
        r['sbc'] = 'SBC 2022 (ICP): o mesmo prazo de 14 dias após angioplastia com balão.'
        return r
    if dias <= 30:
        r['fase'] = 'proibitiva'
        r['aha'] = ('AHA: stent há ≤30 dias; cirurgia eletiva com interrupção de antiplaquetário é potencialmente '
                    'danosa (3: Dano, B-NR). Se a cirurgia for tempo-sensível, manter a DAPT, salvo se o risco de '
                    'sangramento superar o de trombose do stent (1, B-NR).')
        r['sbc'] = ('SBC: <30 dias, III-B (Quadros 22–23). Cirurgia de baixo risco de sangramento pode ser feita na '
                    'vigência da DAPT (IIa-C); se a DAPT for interrompida antes do tempo mínimo, operar em centro com '
                    'retaguarda hemodinâmica (I-C). Ponte com tirofiban: IIb-B; ponte com HBPM: III-B (Quadro 21).')
        return r
    ind = indicacao or 'sca'
    nota_ind = '' if indicacao else ' Sem a indicação da ICP informada, valeu o prazo mais longo (SCA).'
    if tempo_sensivel:
        if tipo == 'farmacologico' and m < 3:
            r['fase'] = 'manter_dapt'
            r['aha'] = ('AHA: cirurgia tempo-sensível <3 meses após DES: manter a DAPT, salvo se o risco de '
                        'sangramento superar o de trombose do stent (1, B-NR). Em selecionados de alto risco '
                        'trombótico, ponte com antiplaquetário venoso pode ser considerada se a cirurgia não puder '
                        'esperar (<6 meses do DES; 2b, B-NR).')
            r['sbc'] = _sbc_janela(ind, m) + nota_ind
            r['div'] = ('Ponte venosa: a AHA admite até 6 meses após DES (2b, B-NR); a SBC reserva o tirofiban para '
                        '<1 mês de ICP (IIb-B) e contraindica ponte com HBPM (III-B).')
        else:
            r['fase'] = 'liberada'
            r['aha'] = ('AHA: cirurgia tempo-sensível ≥3 meses após DES pode ser considerada se o risco de adiar '
                        'superar o de eventos (2b, B-NR).' if tipo == 'farmacologico' else
                        'AHA: stent convencional após ≥30 dias de DAPT; a cirurgia pode prosseguir.')
            r['sbc'] = _sbc_janela(ind, m) + nota_ind
        return r
    ideal = 12 if ind == 'sca' else 6
    r['sbc'] = _sbc_janela(ind, m) + nota_ind
    classe_sbc = _sbc_classe_janela(ind, m)[0]
    if m >= ideal:
        r['fase'] = 'liberada'
        r['aha'] = ('AHA: DES por SCA há ≥12 meses; intervalo cumprido (1, B-NR).' if tipo == 'farmacologico' and
                    ind == 'sca' else 'AHA: DES por DAC crônica há ≥6 meses; intervalo cumprido (2a, B-NR).'
                    if tipo == 'farmacologico' else 'AHA: stent convencional após ≥30 dias; intervalo cumprido.')
        if tipo == 'farmacologico' and ind != 'sca':
            r['div'] = 'Força diferente para o mesmo intervalo de ≥6 meses: SBC I-A × AHA 2a.'
        return r
    r['fase'] = 'adiar'
    if tipo == 'farmacologico':
        if ind == 'sca':
            r['classe'] = f'AHA 1 (B-NR) · SBC {classe_sbc}'
            r['aha'] = 'AHA: DES por SCA; idealmente adiar a cirurgia eletiva até ≥12 meses (1, B-NR).'
            if m >= 6:
                r['div'] = ('Entre 6 e 12 meses após DES por SCA, a SBC aceita operar (IIa-B) e a AHA prefere adiar '
                            'até 12 meses (1, B-NR). Nós optamos por seguir a AHA: adiar, se a cirurgia puder esperar.')
        else:
            r['classe'] = f'AHA 2a (B-NR) · SBC {classe_sbc}'
            r['aha'] = 'AHA: DES por DAC crônica; é razoável adiar a cirurgia eletiva até ≥6 meses (2a, B-NR).'
            if m >= 3:
                r['div'] = ('Entre 3 e 6 meses após DES por DAC crônica, a SBC aceita operar (IIa-B) e a AHA considera '
                            'razoável adiar até 6 meses (2a, B-NR). Nós optamos por seguir a AHA: adiar, se a '
                            'cirurgia puder esperar.')
    else:
        r['classe'] = f'SBC {classe_sbc}'
        r['aha'] = 'AHA: stent convencional após ≥30 dias de DAPT; a AHA não define prazo maior.'
        r['div'] = (f'A AHA não define intervalo além de 30 dias para o stent convencional; a SBC gradua pela indicação '
                    f'(ideal ≥{ideal} meses, I-A). Nós optamos por seguir a SBC, como na tela de adiamentos.')
    return r


# ---------------------------------------------------------------------------------------------------------------
# Regras por medicamento
# ---------------------------------------------------------------------------------------------------------------
def _betabloqueador(chave, ctx):
    texto = ('Manter no perioperatório conforme a situação clínica; sem via oral, considerar sonda enteral ou via '
             'venosa (SBC, Quadro 8, na IC).')
    if 'tiazidico' in MEDICAMENTOS[chave]['classes']:
        texto += ' O diurético da associação acompanha a conduta (SBC I-C, Quadro 10).'
    return _item(chave, 'manter', 'Manter, inclusive no dia', texto, 'AHA 1 (B-NR) · SBC I-B',
                 _refs(_aha('§7.7, rec. 1'), _sbc('Quadros 8 e 18')))


def _estatina(chave, ctx):
    texto = 'Manter no perioperatório para reduzir eventos cardiovasculares maiores.'
    if 'outro_hipolipemiante' in MEDICAMENTOS[chave]['classes']:
        texto += ' A ezetimiba da associação acompanha a conduta.'
    return _item(chave, 'manter', 'Manter', texto, 'AHA 1 (B-NR) · SBC I-B',
                 _refs(_aha('§7.1, rec. 1'), _sbc('Quadro 19')))


def _nota_associacao_has(chave):
    classes = MEDICAMENTOS[chave]['classes']
    partes = []
    if 'tiazidico' in classes:
        partes.append('o diurético')
    if 'bcc' in classes:
        partes.append('o bloqueador de canal de cálcio')
    if not partes:
        return ''
    verbo = 'acompanham' if len(partes) > 1 else 'acompanha'
    return f' Na associação, {" e ".join(partes)} {verbo} a conduta.'


def _ieca_bra(chave, ctx):
    cond = _cond(ctx)
    nota = _nota_associacao_has(chave)
    if 'ic_fe_reduzida' in cond:
        return _item(chave, 'manter', 'Manter',
                     'ICFEr: manter no perioperatório e retomar o mais cedo possível; a omissão de 24 h sugerida '
                     'pela AHA vale só para o uso na hipertensão.' + nota,
                     'AHA 2a (C-EO) · SBC I-C', _refs(_aha('§7.2, rec. 2'), _sbc('Quadro 8')))
    if 'ic' in cond:
        div_ic = ''
        if 'hipertensao' in cond:
            div_ic = ('Na IC sem FE reduzida com hipertensão, duas recomendações da AHA se cruzam: manter a terapia da IC '
                      '(§6.3, 2a) e omitir o IECA/BRA nas 24 h antes em selecionados com PA controlada e cirurgia de '
                      'risco elevado (§7.2, 2b). A SBC manda manter todas as medicações da IC (I-C). Nós optamos por '
                      'manter, pela IC.')
        return _item(chave, 'manter', 'Manter',
                     'IC compensada: manter a terapia da IC no perioperatório e retomar o mais cedo possível.' + nota
                     + _cautela_hipotensao(ctx),
                     'AHA 2a (C-LD) · SBC I-C', _refs(_aha('§6.3, rec. 2, e §7.2, rec. 1'), _sbc('Quadro 8')), div_ic)
    div = ('AHA 2026: em selecionados (PA controlada e cirurgia de risco elevado), omitir o IECA/BRA nas 24 h antes '
           'para limitar a hipotensão intraoperatória (2b, B-R). SBC 2024: manter no perioperatório, com suspensão '
           'permitida em casos selecionados (I-C).')
    refs = _refs(_aha('§7.2, rec. 1, e §6.2, recs. 1 e 5'), _sbc('Quadros 9 e 10'))
    retomar = ('retomar assim que clinicamente possível (AHA 1, C-EO; SBC I-C); no texto da SBC, BRA não '
               'reintroduzido em até 2 dias associou-se a maior mortalidade')
    elevado, pa = ctx.get('cirurgia_risco_elevado'), ctx.get('pa_controlada')
    if elevado is True and pa is True:
        return _item(chave, 'suspender', 'Omitir nas 24 h antes',
                     f'PA controlada e cirurgia de risco elevado: omitir a dose das 24 h anteriores à cirurgia e '
                     f'{retomar}.' + nota,
                     'AHA 2b (B-R) · SBC I-C', refs,
                     div + ' Nós optamos por seguir a AHA neste perfil, o que cabe na suspensão em casos selecionados '
                           'prevista pela SBC.')
    if elevado is False or pa is False:
        return _item(chave, 'manter', 'Manter',
                     'Fora do perfil em que a AHA sugere omitir (PA controlada e cirurgia de risco elevado): manter, '
                     'inclusive no dia, e retomar o quanto antes no pós-operatório.' + nota + _cautela_hipotensao(ctx),
                     'AHA 2a (C-EO) · SBC I-C', refs, div + ' Neste paciente, as duas levam a manter.')
    faltas = [n for n, v in (('se a cirurgia é de risco elevado', elevado), ('se a PA está controlada', pa))
              if v is None]
    return _item(chave, 'individualizar', 'Manter ou omitir 24 h antes',
                 f'Falta informar {" e ".join(faltas)}: com PA controlada e cirurgia de risco elevado, a AHA sugere '
                 f'omitir nas 24 h antes; nos demais casos, manter. Se omitido, {retomar}.' + nota
                 + _cautela_hipotensao(ctx),
                 'AHA 2b (B-R) · SBC I-C', refs, div)


def _arni(chave, ctx):
    return _item(chave, 'manter', 'Manter',
                 'Terapia da ICFEr: manter no perioperatório (o ARNI contém um BRA e entra na recomendação para '
                 'inibidores do SRAA na ICFEr) e retomar o mais cedo possível.',
                 'AHA 2a (C-EO) · SBC I-C', _refs(_aha('§7.2, rec. 2'), _sbc('Quadro 8')))


def _bcc(chave, ctx):
    return _item(chave, 'manter', 'Manter',
                 'Manter; a suspensão é permitida em casos selecionados (SBC). A AHA não tem recomendação formal: o '
                 'texto considera a continuação razoável, atento a hipotensão com di-hidropiridínicos e a bradicardia '
                 'com diltiazem e verapamil.' + _cautela_hipotensao(ctx),
                 'SBC I-C', _refs(_sbc('Quadro 10'), _aha('§7.3 (texto)')))


def _diuretico(chave, ctx):
    if _ic(_cond(ctx)):
        return _item(chave, 'manter', 'Manter',
                     'IC: manter, como as demais medicações de uso crônico, e retomar o mais cedo possível; '
                     'otimizar a volemia, evitando desidratação (SBC I-C, Quadro 9).',
                     'SBC I-C', _refs(_sbc('Quadros 8, 9 e 10')))
    return _item(chave, 'manter', 'Manter',
                 'Manter, com suspensão permitida em casos selecionados (SBC); na hipertensão, a AHA considera '
                 'razoável manter e recomenda retomar o quanto antes (1, C-EO). Otimizar a volemia, evitando '
                 'desidratação (SBC I-C).' + _cautela_hipotensao(ctx),
                 'AHA 2a (C-EO) · SBC I-C', _refs(_aha('§6.2, recs. 1 e 5'), _sbc('Quadros 9 e 10')))


def _antagonista_mineralocorticoide(chave, ctx):
    if _ic(_cond(ctx)) and chave != 'amilorida':
        return _item(chave, 'manter', 'Manter',
                     'IC compensada: manter a terapia da IC (exceto iSGLT2) no perioperatório e retomar o mais cedo '
                     'possível.',
                     'AHA 2a (C-LD) · SBC I-C', _refs(_aha('§6.3, rec. 2'), _sbc('Quadro 8')))
    return _diuretico(chave, ctx)


def _clonidina(chave, ctx):
    return _item(chave, 'manter', 'Manter',
                 'Manter: a suspensão abrupta pode causar hipertensão de rebote (texto da AHA). Iniciar clonidina para '
                 'reduzir risco cardiovascular não traz benefício (AHA 3: Sem benefício, B-R).',
                 'SBC I-B', _refs(_sbc('Quadro 10'), _aha('§7.4')))


def _outro_anti_has(chave, ctx):
    return _item(chave, 'manter', 'Manter',
                 'Na hipertensão, é razoável manter a terapia anti-hipertensiva no perioperatório e retomá-la o quanto '
                 'antes no pós-operatório (AHA 1, C-EO).' + _cautela_hipotensao(ctx),
                 'AHA 2a (C-EO)', _refs(_aha('§6.2, recs. 1 e 5')))


def _cardio_ic(chave, ctx):
    if not _ic(_cond(ctx)):
        return None
    return _item(chave, 'manter', 'Manter',
                 'IC: manter todas as medicações de uso crônico no perioperatório e retomá-las o mais cedo possível; '
                 'sem via oral, considerar sonda enteral ou via venosa.',
                 'SBC I-C', _refs(_sbc('Quadro 8')))


# --- Diabetes -----------------------------------------------------------------------------------------------------
# Fonte principal: posicionamento conjunto SBD/SBA/ABESO (Diabetol Metab Syndr 2026, versão em inglês da Diretriz SBD
# 2025), recomendações R4–R15 e Tabela 2; aGLP-1 atualizados pela nota da SBA de 15/05/2026 (C.SBA-01744/2026).
# Classes da SBD: I (> 90% de concordância), IIa (70–90%), IIb (50–70%); níveis A, B e C.
def _sbd(onde):
    return [{'label': f'SBD/SBA/ABESO 2026, {onde}', 'url': _URL_SBD}, dict(REFERENCIAS['sbd_pt'])]


_DIV_METFORMINA = ('AHA 2026: é razoável manter a metformina no perioperatório (2a, C-LD), sem citar o dia da cirurgia. '
                   'SBD/SBA/ABESO 2026 (IIa-B) e SPAQI: manter até a véspera e não tomar no dia. Nós optamos por seguir '
                   'a SBD/SBA/ABESO.')


def _isglt2(chave, ctx):
    dias = 4 if 'ertugliflozina' in chave else 3
    classes = MEDICAMENTOS[chave]['classes']
    refs = [_aha('§7.8, rec. 2, e §6.3, rec. 1'), _sbd('R6 e Tabela 2'), _sbc('Quadro 8')]
    if ctx.get('urgencia') in ('urgencia', 'emergencia'):
        texto = ('Sem tempo para suspender antes: não tomar mais e, pelo risco de cetoacidose euglicêmica, dosar a '
                 'cetonemia capilar (beta-hidroxibutirato) e fazer gasometria com ânion gap; a cetoacidose pode vir com '
                 'glicemia normal. Retomar só com dieta normal e paciente estável.')
        return _item(chave, 'suspender', 'Não tomar mais; dosar a cetonemia', texto,
                     'SBD/SBA/ABESO: notas 3 e 4 · AHA 1 (C-LD) na eletiva', _refs(*refs))
    texto = (f'Suspender ≥{dias} dias antes (última dose no D-{dias + 1}) para reduzir o risco de cetoacidose '
             'euglicêmica, também na IC; retomar com o paciente estável e em dieta normal. Mal-estar, náusea ou dor '
             'abdominal no perioperatório: dosar a cetonemia mesmo com glicemia normal.')
    if 'metformina' in classes:
        texto += ' A metformina da associação fica suspensa junto.'
    elif 'idpp4_pioglitazona' in classes:
        texto += ' O iDPP-4 da associação fica suspenso junto.'
    return _item(chave, 'suspender', f'Suspender {dias} dias antes', texto, 'AHA 1 (C-LD) · SBD/SBA/ABESO I-B',
                 _refs(*refs),
                 'SBD/SBA/ABESO 2026 (R6, I-B): suspender 3–4 dias antes de cirurgia maior ou de procedimento com '
                 'restrição calórica; nos demais, decidir caso a caso. A SBC 2024 manda manter as medicações da IC '
                 '(Quadro 8, I-C), sem citar o iSGLT2. Nós optamos por seguir a AHA (3 dias antes em toda cirurgia '
                 'eletiva), mais protetora contra a cetoacidose.')


def _metformina(chave, ctx):
    clcr = ctx.get('clcr')
    refs = [_sbd('R5 e Tabela 2'), _aha('§7.8, rec. 3'), _ref('spaqi_endo')]
    if clcr is not None and clcr < 30:
        return _item(chave, 'suspender', 'Suspender (ClCr < 30 mL/min)',
                     f'ClCr {clcr:.0f} mL/min: a metformina é contraindicada com filtração abaixo de 30 mL/min/1,73 m². '
                     'Suspender e rever o tratamento com o médico assistente; no pós-operatório, não reintroduzir sem '
                     'função renal estável.',
                     'KDIGO 2022: ponto de prática (sem gradação)', _refs(_ref('kdigo_dm'), *refs))
    return _item(chave, 'suspender', 'Tomar até a véspera; não tomar no dia',
                 'Manter até a véspera e não tomar no dia da cirurgia. Reintroduzir com o paciente estável, com função '
                 'renal preservada e sem complicação que leve a hipóxia tecidual.',
                 'SBD/SBA/ABESO IIa-B · AHA 2a (C-LD)', _refs(*refs), _DIV_METFORMINA)


def _sulfonilureia(chave, ctx):
    return _item(chave, 'suspender', 'Suspender 24 h antes',
                 'Última dose pelo menos 24 h antes da cirurgia (na prática, não tomar na véspera à noite nem no dia): '
                 'em jejum, o secretagogo causa hipoglicemia, que a anestesia mascara.',
                 'SBD/SBA/ABESO I-C', _refs(_sbd('R4 e Tabela 2'), _ref('spaqi_endo')),
                 'A SPAQI orienta só não tomar na manhã da cirurgia. Nós optamos por seguir a SBD/SBA/ABESO, mais '
                 'protetora contra a hipoglicemia.')


def _idpp4(chave, ctx):
    classes = MEDICAMENTOS[chave]['classes']
    div_spaqi = ('A SPAQI (consenso) orienta não tomar o iDPP-4 na manhã da cirurgia; a SBD/SBA/ABESO (R11, I-A, com '
                 'ensaios randomizados) mantém. Nós optamos por seguir a SBD/SBA/ABESO.')
    if 'metformina' in classes:
        return _item(chave, 'suspender', 'Tomar até a véspera; não tomar no dia',
                     'O iDPP-4 pode ser mantido no perioperatório (SBD/SBA/ABESO I-A), mas o comprimido leva metformina, '
                     'que não se toma no dia da cirurgia (IIa-B).',
                     'SBD/SBA/ABESO IIa-B (metformina) · I-A (iDPP-4)',
                     _refs(_sbd('R5, R11 e Tabela 2'), _aha('§7.8, rec. 3'), _ref('spaqi_endo')), _DIV_METFORMINA)
    if chave == 'saxagliptina':
        ic = _ic(_cond(ctx))
        texto = ('Os iDPP-4 são mantidos no perioperatório, mas a SBD/SBA/ABESO evita a saxagliptina, sobretudo com IC '
                 'ou risco de IC (mais internação por IC no SAVOR-TIMI 53).')
        if ic:
            texto += ' Com IC: discutir a troca com o médico assistente.'
        return _item(chave, 'individualizar' if ic else 'manter',
                     'Discutir a troca (IC)' if ic else 'Manter (evitar se IC ou risco de IC)', texto,
                     'SBD/SBA/ABESO I-A', _refs(_sbd('R11 e Tabela 2'), _ref('spaqi_endo')), div_spaqi)
    return _item(chave, 'manter', 'Manter, inclusive no dia',
                 'Manter no perioperatório: controle glicêmico semelhante ao da insulina basal-bolus, com menos '
                 'hipoglicemia.',
                 'SBD/SBA/ABESO I-A', _refs(_sbd('R11 e Tabela 2'), _ref('spaqi_endo')), div_spaqi)


def _pioglitazona(chave, ctx):
    if _ic(_cond(ctx)):
        return _item(chave, 'individualizar', 'Discutir a suspensão (IC)',
                     'A pioglitazona retém líquido e pode descompensar a IC, com efeito que dura dias a semanas: com IC, '
                     'discutir a suspensão com o médico assistente.',
                     'SBD/SBA/ABESO IIb-C', _refs(_sbd('R12 e Tabela 2'), _ref('spaqi_endo')))
    return _item(chave, 'manter', 'Pode manter',
                 'Pode ser mantida em cirurgia eletiva não cardíaca, com o paciente estável e sem internação longa '
                 'prevista; cautela na IC conhecida ou suspeita.',
                 'SBD/SBA/ABESO IIb-C', _refs(_sbd('R12 e Tabela 2'), _ref('spaqi_endo')),
                 'A SPAQI orienta não tomar na manhã da cirurgia. Nós optamos por seguir a SBD/SBA/ABESO.')


def _acarbose(chave, ctx):
    return _item(chave, 'suspender', 'Suspender no dia da cirurgia', 'Não tomar no dia da cirurgia (age só com refeição).',
                 'SBD/SBA/ABESO: Tabela 2 · SPAQI: consenso', _refs(_sbd('Tabela 2'), _ref('spaqi_endo')))


_FATORES_GLP1 = ('Fatores de risco de aspiração: início há menos de 12 semanas ou aumento de dose nos últimos 3 meses; '
                 'sintomas gastrointestinais; HbA1c > 8% ou diabetes há mais de 8 anos; gastroparesia; cirurgia '
                 'gastrointestinal prévia, inclusive bariátrica; resíduo gástrico em endoscopia anterior; obstrução ou '
                 'acalasia; IMC ≥ 40; opioide crônico, tricíclico, anticolinérgico ou bloqueador dos canais de cálcio; '
                 'disfagia ou doença neurológica; sedação moderada ou profunda sem via aérea protegida, posição prona, '
                 'sedação > 30 min ou via aérea difícil prevista.')


def _texto_glp1(longa, chave):
    nome = {'liraglutida': 'liraglutida (curta ação)', 'semaglutida': 'semaglutida, oral ou subcutânea (longa ação)',
            'dulaglutida': 'dulaglutida (longa ação)', 'tirzepatida': 'tirzepatida, coagonista GIP/GLP-1 (longa ação)'}
    dias = 7 if longa else 1
    rotulo = nome.get(chave, chave)
    return (f'{rotulo[0].upper() + rotulo[1:]}: suspender {dias} dia{"s" if dias > 1 else ""} antes. Para todos: '
            'dieta líquida sem resíduos nas 24 h antes e jejum de 8 a 12 h. Manter a dose só se estiver estável há mais '
            'de 12 semanas, sem fatores de risco de aspiração, e se o serviço fizer ultrassonografia gástrica (POCUS) '
            'sistemática no dia, pelo menos 1 h antes da anestesia; sem POCUS, suspender. ' + _FATORES_GLP1 +
            ' Com suspensão longa no DM2, o médico assistente ajusta o tratamento para evitar hiperglicemia. Termo de '
            'consentimento específico da SBA.')


def _div_glp1(longa):
    return ('AHA 2026 (texto, sem classe, citando a ASA 2023): suspender ' +
            ('a formulação semanal mais de 1 semana antes' if longa else 'a formulação diária na véspera') +
            '. A orientação multissocietária de 2024 e o consenso britânico de 2025 mantêm na maioria. A SBD/SBA/ABESO '
            '2026 manteria quem está estável há mais de 12 semanas e sem fatores de risco (R9, I-C); a nota da SBA de '
            'maio de 2026 passou a exigir POCUS sistemático para manter. Nós optamos por seguir a nota da SBA de 2026, '
            'a posição brasileira mais recente.')


def _glp1(chave, ctx):
    longa = chave not in _GLP1_DIARIO
    resumo = ('Suspender 7 dias antes; dieta líquida nas 24 h antes' if longa else
              'Suspender 1 dia antes; dieta líquida nas 24 h antes')
    return _item(chave, 'suspender', resumo, _texto_glp1(longa, chave),
                 'SBD/SBA/ABESO I-C · SBA 2026 (nota)',
                 _refs(_ref('sba_glp1'), _sbd('R7–R10 e Tabela 2'), _aha('§7.8 (texto)'), _ref('glp1')),
                 _div_glp1(longa))


def _insulina(chave, ctx):
    refs_sbd = _sbd('R13–R15 e Tabela 2')
    nunca = (' No DM1, LADA ou pancreatectomia total, nunca omitir a insulina basal (risco de cetoacidose), salvo com '
             'insulina venosa ou bomba funcionando.')
    if chave == 'insulina_degludeca':
        return _item(chave, 'ajustar', 'Reduzir 20–30% a partir de 72 h antes',
                     'Reduzir a dose em 20–30% começando 72 h antes (ação ultralonga); até 50% se a basal passar de '
                     'metade da dose diária total; com basal até metade da dose total e glicemia estável, a redução '
                     'pode ser desnecessária.' + nunca,
                     'SBD/SBA/ABESO IIa-B', _refs(refs_sbd, _ref('spaqi_endo')),
                     'A SPAQI orienta 60–80% da dose na noite anterior para as insulinas basais, sem prazo próprio para '
                     'a degludeca. Nós optamos por seguir a SBD/SBA/ABESO.')
    if chave in _INSULINA_BASAL:
        return _item(chave, 'ajustar', 'Na noite anterior, 70–80% da dose',
                     'Reduzir a dose da noite anterior em 20–30%; até 50% se a basal passar de metade da dose diária '
                     'total; com basal até metade da dose total e glicemia estável, a redução pode ser desnecessária. '
                     'Manter a basal no dia.' + nunca,
                     'SBD/SBA/ABESO IIa-B', _refs(refs_sbd, _ref('spaqi_endo')),
                     'A SPAQI aceita 60–80% da dose na noite anterior. Nós optamos por seguir a SBD/SBA/ABESO (70–80%).')
    if chave in _INSULINA_NPH:
        return _item(chave, 'ajustar', 'Na manhã da cirurgia, 50% da dose',
                     'Dose habitual na noite anterior; na manhã da cirurgia, 50% da dose (sobretudo se a NPH for mais '
                     'da metade da insulina total ou se dois terços ou mais forem aplicados de manhã). No esquema '
                     'basal-bolus com NPH, reduzir cada componente em 50% e dividir a NPH em três doses iguais.' + nunca,
                     'SBD/SBA/ABESO IIa-C', _refs(refs_sbd, _ref('spaqi_endo')),
                     'A SPAQI sugere considerar também reduzir 25% a dose da noite anterior. Nós optamos por seguir a '
                     'SBD/SBA/ABESO (noite anterior sem redução).')
    if chave in _INSULINA_PRANDIAL:
        return _item(chave, 'suspender', 'No jejum, só correção',
                     'Dose habitual até a véspera; em jejum, suspender as doses fixas das refeições e usar só a insulina '
                     'de correção (esquema basal-plus) até voltar a comer.',
                     'SBD/SBA/ABESO I-C', _refs(refs_sbd, _ref('spaqi_endo')))
    if chave in _INSULINA_GLP1:
        return _item(chave, 'individualizar', 'Seguir a regra do aGLP-1 (curta ação)',
                     'A associação em dose fixa segue o componente aGLP-1 (lixisenatida e liraglutida são de curta '
                     'ação): suspender 1 dia antes, salvo se estável há mais de 12 semanas, sem fatores de risco e com '
                     'POCUS gástrico sistemático no serviço; dieta líquida nas 24 h antes e jejum de 8 a 12 h. A '
                     'insulina da caneta não reduz o efeito no esvaziamento gástrico; no dia sem a caneta, o médico '
                     'assistente define a cobertura com insulina basal.',
                     'SBD/SBA/ABESO I-C · SBA 2026 (nota)',
                     _refs(_ref('sba_glp1'), _sbd('Nota 8 e Tabela 2'), _ref('spaqi_endo')), _div_glp1(False))
    return None  # bifásica e icodeca: sem recomendação nas fontes


# --- Anticoagulantes ----------------------------------------------------------------------------------------------
def _esquema_aha_doac(farmaco, clcr, sang, neuraxial):
    """(última dose no D-x, dias sem dose, reinício no D+y) pela AHA (Tabela 13; texto do §7.6 na neuroaxial)."""
    # Neuroaxial: interrupção completa por ≥ 5 meias-vidas (texto do §7.6): ≥ 3 dias sem dose para anti-Xa (72 h) e
    # ≥ 4 dias para dabigatrana (5–6 com ClCr < 50; usamos 6, o limite conservador).
    if farmaco == 'dabigatrana':
        reduzida = clcr < 50
        if neuraxial:
            return (7, 6, 3) if reduzida else (5, 4, 3)
        if sang == 'alto':
            return (5, 4, 3) if reduzida else (3, 2, 3)
        return (3, 2, 1) if reduzida else (2, 1, 1)
    reduzida = clcr < 30
    if neuraxial or sang == 'alto':
        return (4, 3, 3) if (reduzida or neuraxial) else (3, 2, 3)
    return (3, 2, 1) if reduzida else (2, 1, 1)


def _esquema_sbc_doac(farmaco, clcr, sang):
    """(antes, depois, classe, nota) pela SBC (Quadro 26; edoxabana pelo texto do 4.3.2.6)."""
    alto = sang == 'alto'
    nota = ''
    if clcr < 15:
        nota = ' ClCr <15 mL/min fica fora das faixas do Quadro 26.'
    if farmaco == 'dabigatrana':
        if clcr < 50:
            antes, depois = ('96 h', '48 h') if alto else ('48 h', '24 h')
        else:
            antes, depois = ('48 h', '48 h') if alto else ('24 h', '24 h')
        return antes, depois, 'I-B', nota
    if farmaco == 'apixabana':
        if alto or clcr < 50:
            return 'pelo menos 48 h', '48 h', 'I-B', nota
        return '24 h', '24 h', 'I-B', nota
    if farmaco == 'rivaroxabana':
        if alto or clcr < 30:
            return 'pelo menos 48 h', '48 h', 'I-B', nota
        if clcr < 50:
            nota += ' O Quadro 26 não traz linha própria para ClCr 30–50; aplicada a de função renal normal.'
        return '24 h', '24 h', 'I-B', nota
    # edoxabana: sem quadro; texto da SBC
    return ('48–72 h' if alto else '24 h'), None, None, nota


def _doac(chave, ctx):
    farmaco = chave
    nome = MEDICAMENTOS[chave]['rotulo'].lower()
    sang = _sangramento(ctx)
    clcr = ctx.get('clcr')
    neuraxial = bool(ctx.get('neuraxial'))
    refs = _refs(_aha('§7.6, rec. 1, e Tabela 13'), _sbc('Quadros 12–14 e 26'))
    if _cond(ctx) & {'protese_mecanica', 'protese_mecanica_mitral'}:
        texto = (f'Prótese valvar mecânica: a {nome} é contraindicada (mais trombose e sangramento que a varfarina). '
                 'Rever a anticoagulação com o cardiologista antes da cirurgia; o manejo perioperatório passa a ser o '
                 'da varfarina.')
        if ctx.get('urgencia') in ('urgencia', 'emergencia'):
            reversor = 'idarucizumabe' if farmaco == 'dabigatrana' else 'andexanet alfa ou complexo protrombínico'
            texto += (' Na urgência: medir o efeito residual (testes de coagulação ou nível do fármaco) e, se presente '
                      f'com sangramento relevante, reverter com {reversor} (AHA, texto do §7.6 e Tabela 15).')
        return _item(chave, 'individualizar', 'Contraindicado com prótese mecânica', texto,
                     'ACC/AHA 2020 (valvopatias) 3: Dano (B-R) · SBC: texto',
                     _refs(_ref('valvas'), _sbc('4.3.2 (texto)'), _aha('§7.6 (texto) e Tabela 15')))
    if neuraxial and farmaco == 'dabigatrana' and clcr is not None and clcr < 30:
        return _item(chave, 'individualizar', 'ClCr < 30: evitar anestesia neuroaxial',
                     f'Dabigatrana com ClCr {_num(clcr)} mL/min: a ASRA não recomenda bloqueio neuroaxial; preferir '
                     'outra técnica anestésica, em decisão com a anestesia. Se a neuroaxial for indispensável, '
                     'suspender por mais tempo (pela AHA, ≥6 dias sem dose) e conferir o efeito residual.',
                     'ASRA 2018 · AHA 1 (B-NR)', _refs(_ref('asra'), refs))
    if sang == 'minimo':
        return _item(chave, 'manter', 'Não interromper',
                     'Sangramento mínimo: manter (AHA, Tabela 13). SBC: catarata, I-B; endoscopia de baixo risco e '
                     'dermatologia, IIa-C (marcar o procedimento algumas horas antes da próxima dose).',
                     'AHA 1 (B-NR) · SBC I-B', refs)
    if ctx.get('urgencia') in ('urgencia', 'emergencia'):
        reversor = 'idarucizumabe' if farmaco == 'dabigatrana' else 'andexanet alfa ou complexo protrombínico'
        return _item(chave, 'individualizar', 'Urgência: avaliar efeito residual e reversão',
                     'Na urgência, a interrupção por tempo pode não ser viável: testes de coagulação ou nível do '
                     f'fármaco identificam efeito residual; se presente e com sangramento relevante, reverter com '
                     f'{reversor} (AHA, texto do §7.6 e Tabela 15).',
                     'AHA: texto, sem classe', _refs(_aha('§7.6 (texto) e Tabela 15'), _sbc('4.3.2 (texto)')))
    if sang is None:
        return _item(chave, 'individualizar', 'Depende do risco de sangramento',
                     'Falta o risco de sangramento da cirurgia (mínimo, baixo/moderado ou alto) para escolher o '
                     'esquema de suspensão e reinício (AHA, Tabela 13; SBC, Quadro 26).',
                     'AHA 1 (B-NR) · SBC I-B', refs)
    corte = 50 if farmaco == 'dabigatrana' else 30
    if clcr is None:
        a = _esquema_aha_doac(farmaco, corte, sang, neuraxial)
        b = _esquema_aha_doac(farmaco, corte - 1, sang, neuraxial)
        return _item(chave, 'individualizar', 'Depende do ClCr',
                     f'Falta o ClCr (Cockcroft-Gault). Pela AHA (sangramento {_ROTULO_SANGRAMENTO[sang]}): com ClCr '
                     f'≥{corte}, última dose no D-{a[0]} e reinício no D+{a[2]}; com ClCr <{corte}, última dose no '
                     f'D-{b[0]} e reinício no D+{b[2]}.',
                     'AHA 1 (B-NR) · SBC I-B', refs)
    ultima, sem, reinicio = _esquema_aha_doac(farmaco, clcr, sang, neuraxial)
    antes, depois, classe_sbc, nota = _esquema_sbc_doac(farmaco, clcr, sang)
    if depois:
        sbc_txt = f'SBC (Quadro 26): suspender {antes} antes e reintroduzir {depois} depois.'
    else:
        sbc_txt = (f'SBC (texto, sem quadro): suspender {antes} antes, a conduta "mais aceita" para a edoxabana.')
    resumo = f'Última dose no D-{ultima} ({_dias(sem)} sem dose); reiniciar no D+{reinicio}'
    texto = (f'AHA (Tabela 13, ClCr {_num(clcr)} mL/min, sangramento {_ROTULO_SANGRAMENTO[sang]}): última dose no '
             f'D-{ultima}, {_dias(sem)} sem dose e reinício no D+{reinicio}, após hemostasia. {sbc_txt} Sem ponte com '
             f'heparina.{nota}')
    if neuraxial:
        texto += (' Neuroaxial: interrupção completa por ≥5 meias-vidas (≥3 dias para anti-Xa; ≥4 dias para '
                  'dabigatrana, 5–6 se ClCr <50) e próxima dose ≥6 h após retirar o cateter peridural (SBC I-B).')
    div = ''
    if farmaco == 'apixabana' and 15 <= clcr < 50 and sang == 'baixo_moderado':
        resumo = 'Última dose ≥48 h antes; reiniciar 48 h depois'
        div = ('Apixabana com ClCr 15–50: a SBC pede ≥48 h antes mesmo no sangramento baixo (I-B); a AHA usa o '
               f'esquema de função normal (última dose no D-{ultima}). Nós optamos por seguir a SBC, mais '
               'conservadora.')
    elif farmaco in {'apixabana', 'rivaroxabana'} and clcr < 30 and sang == 'alto':
        div = ('Anti-Xa com ClCr <30 e sangramento alto: a AHA deixa 3 dias sem dose (última no D-4); a SBC pede "pelo '
               'menos 48 h". Nós optamos por seguir a AHA, mais conservadora.')
    elif farmaco == 'edoxabana' and clcr < 30 and sang == 'alto':
        div = ('Edoxabana com ClCr <30 e sangramento alto: a AHA deixa 3 dias sem dose (última no D-4); a SBC (texto, '
               'sem quadro) fala em 48–72 h. Nós optamos por seguir a AHA, mais conservadora.')
    elif farmaco == 'edoxabana':
        div = ('A SBC não tem quadro para a edoxabana (só texto, sem classe); a AHA a agrupa com apixabana e '
               'rivaroxabana. Nós optamos por seguir a AHA.')
    classe = f'AHA 1 (B-NR) · SBC {classe_sbc}' if classe_sbc else 'AHA 1 (B-NR) · SBC: texto, sem classe'
    return _item(chave, 'suspender', resumo, texto, classe, refs, div)


def _decisao_ponte(ctx):
    cat_aha, mot_aha, faltas = _risco_te_aha(ctx)
    cat_sbc, mot_sbc, notas = _risco_te_sbc(ctx)
    return {'aha': cat_aha, 'aha_motivos': mot_aha, 'faltas': faltas, 'sbc': cat_sbc, 'sbc_motivos': mot_sbc,
            'notas': notas, 'ponte_aha': cat_aha == 'alto', 'ponte_sbc': cat_sbc == 'alto'}


def _div_ponte(d):
    if d['aha'] is None or d['ponte_aha'] == d['ponte_sbc']:
        return ''
    if d['ponte_sbc']:
        return (f'SBC: risco tromboembólico alto ({"; ".join(d["sbc_motivos"])}) e ponte com heparina (IIa-C). AHA: '
                f'risco {d["aha"]} ({"; ".join(d["aha_motivos"])}), sem ponte, pois a ponte de rotina aumenta o '
                'sangramento (3: Dano, C-LD). Nós optamos por seguir a AHA (Tabela 14).')
    sbc = ('sem ponte (IIa-C)' if d['sbc'] == 'baixo' else
           'conduta individualizada, sem classe (texto do 4.3.1.1)' if d['sbc'] == 'moderado' else 'sem ponte')
    return (f'AHA: risco alto ({"; ".join(d["aha_motivos"])}) e ponte com heparina (2a, C-LD). SBC: risco '
            f'{d["sbc"] or "não classificado"}, {sbc}. Nós optamos por seguir a AHA (Tabela 14).')


def _varfarina(chave, ctx):
    sang = _sangramento(ctx)
    refs = _refs(_aha('§7.6, recs. 1–4, e Tabelas 13 e 14'), _sbc('Quadros 11–14, 24 e 25; Tabela 11'))
    if sang == 'minimo':
        return _item(chave, 'manter', 'Manter, com INR na faixa',
                     'Sangramento mínimo: manter (AHA, Tabela 13). SBC: catarata com INR na faixa terapêutica (I-B), '
                     'dermatologia com INR ≤3,5 (IIa-C), odontologia (IIa-B); vitrectomia e trabeculectomia são '
                     'exceção e pedem suspensão (I-B).',
                     'AHA 1 (B-NR) · SBC I-B', refs)
    if ctx.get('urgencia') in ('urgencia', 'emergencia'):
        return _item(chave, 'suspender', 'Suspender e reverter',
                     'Urgência ou emergência: suspender, vitamina K por via venosa e reposição de fatores com complexo '
                     'protrombínico ou plasma fresco congelado, conforme a disponibilidade.',
                     'SBC I-C', _refs(_sbc('Quadro 24'), _aha('§7.6 (texto) e Tabela 15')))
    if sang is None:
        return _item(chave, 'individualizar', 'Suspender 5 dias antes; ponte conforme o risco',
                     'Falta o risco de sangramento da cirurgia: em sangramento mínimo (catarata, odontologia ou '
                     'dermatologia menores) a varfarina é mantida; nos demais, suspensa 5 dias antes, com ponte só no '
                     'alto risco tromboembólico.',
                     'AHA 1 (B-NR) · SBC I-C', refs)
    d = _decisao_ponte(ctx)
    base = ('Última dose no D-6 (5 dias sem dose) e operar com INR <1,5 (SBC I-C); INR na véspera e, se ≥1,5, '
            'vitamina K oral 1–2 mg e nova medida (texto da SBC).')
    if d['aha'] is None:
        return _item(chave, 'individualizar', 'Suspender 5 dias antes; ponte conforme o risco',
                     base + ' Falta a indicação da anticoagulação (FA, TEV ou prótese mecânica) para classificar o '
                            'risco tromboembólico e decidir a ponte.',
                     'AHA 1 (B-NR) · SBC I-C', refs)
    if d['ponte_aha']:
        heparina = 'D+3' if sang == 'alto' else 'D+2'
        texto = (base + ' Ponte com HBPM ou HNF em dose plena quando o INR ficar abaixo da faixa (SBC: INR <2), em '
                        'geral do D-3 ao D-1; última HBPM 24 h antes e HNF 4–6 h antes. Varfarina de volta no D+1 '
                        f'(≥24 h), na dose habitual; heparina retomada no {heparina} (SBC: 48–72 h se sangramento '
                        'alto), em dose plena ou profilática por decisão de equipe, até o INR voltar à faixa.')
        return _item(chave, 'suspender', 'Suspender 5 dias antes, com ponte de heparina', texto,
                     'AHA 2a (C-LD) · SBC IIa-C', refs, _div_ponte(d))
    texto = (base + ' Sem ponte. Retomar 12–24 h após, na dose habitual, quando houver hemostasia; heparina '
                    'profilática antes e depois se houver indicação de profilaxia de TEV (SBC IIa-C).')
    return _item(chave, 'suspender', 'Suspender 5 dias antes, sem ponte', texto,
                 'AHA 1 (B-NR); ponte de rotina 3: Dano (C-LD) · SBC IIa-C', refs, _div_ponte(d))


def _enoxaparina(chave, ctx):
    if ctx.get('urgencia') in ('urgencia', 'emergencia'):
        return _item(chave, 'individualizar', 'Urgência: informar a hora da última dose',
                     'Sem tempo para o intervalo de 24 h: informar à anestesia a hora da última aplicação. Anestesia '
                     'neuroaxial só ≥24 h após dose plena e ≥12 h após dose profilática (ASRA); com dose recente, '
                     'preferir outra técnica.',
                     'ASRA 2018 · SBC IIa-C', _refs(_ref('asra'), _sbc('Quadro 25')))
    return _item(chave, 'suspender', 'Dose plena: última dose 24 h antes',
                 'Em dose plena, última aplicação 24 h antes e retorno ≥24 h depois (48–72 h se sangramento alto), com '
                 'hemostasia: intervalos que a SBC define para a HBPM na ponte, aqui estendidos ao uso contínuo. Na '
                 'anestesia neuroaxial (ASRA): punção ≥24 h após dose plena e ≥12 h após dose profilática.',
                 'SBC IIa-C (extrapolado da ponte) · ASRA 2018', _refs(_sbc('Quadro 25'), _ref('asra')))


# --- Antiagregantes -----------------------------------------------------------------------------------------------
def _indicacao_aas(ctx):
    # Doença vascular ou stent é prevenção secundária, mesmo que a tela tenha marcado "primária": nunca suspender o
    # AAS de quem tem stent ou DAC por um erro de marcação.
    if _cond(ctx) & _SECUNDARIA or ctx.get('stent'):
        return 'secundaria'
    if set(ctx.get('medicacoes') or ()) & set(_P2Y12):   # DAPT: houve SCA ou ICP
        return 'secundaria'
    return ctx.get('aas_indicacao')


def _aas(chave, ctx):
    indicacao = _indicacao_aas(ctx)
    cond = _cond(ctx)
    excecao = (' Exceções da SBC: neurocirurgia e procedimentos de risco hemorrágico proibitivo, em que se suspende 7 '
               'dias antes.')
    if indicacao == 'primaria':
        return _item(chave, 'suspender', 'Suspender 7 dias antes',
                     'Prevenção primária: suspender 7 dias antes e não reintroduzir no pós-operatório (texto da SBC, '
                     'com base no POISE-2).',
                     'SBC I-A', _refs(_sbc('Quadro 20'), _aha('§7.5 (texto) e Tabela 12')),
                     'AHA 2026: sem recomendação formal; a interrupção do AAS de prevenção primária dispensa decisão '
                     'multiprofissional e a função plaquetária se recupera em 4 dias (Tabela 12). Nós optamos por '
                     'seguir a SBC (7 dias).')
    if indicacao == 'secundaria' and ctx.get('cirurgia') == 'neurocirurgia':
        return _item(chave, 'suspender', 'Suspender 7 dias antes (neurocirurgia)',
                     'Neurocirurgia: mesmo na prevenção secundária, suspender o AAS 7 dias antes, porque qualquer '
                     'sangramento pode ser catastrófico; retomar assim que a hemostasia permitir. Com stent recente, '
                     'decisão multiprofissional.',
                     'SBC: texto do 4.1.3 (exceção do Quadro 20)', _refs(_sbc('Quadros 20 e 21 e texto do 4.1.3'), _aha('§7.5')))
    if indicacao == 'secundaria' and ctx.get('cirurgia') == 'rtu':
        return _item(chave, 'individualizar', 'RTU de próstata: suspender 7 dias antes; de bexiga: manter',
                     'Na ressecção transuretral de próstata, sem hemostasia direta, a SBC suspende o AAS 7 dias antes, '
                     'mesmo na prevenção secundária (algumas técnicas permitem manter: decidir com o urologista). Na '
                     'RTU de bexiga, manter. Com stent recente, decisão multiprofissional.',
                     'SBC: texto do 4.1.3', _refs(_sbc('texto do 4.1.3 e Quadro 20')))
    if indicacao == 'secundaria':
        if ctx.get('stent') or 'stent' in cond:
            return _item(chave, 'manter', 'Manter (75–100 mg)',
                         'ICP prévia: manter o AAS em dose baixa (75–100 mg; SBC: 100 mg/dia) durante todo o '
                         'perioperatório; se não tolerado, P2Y12 em monoterapia pode ser considerado (AHA).' + excecao,
                         'AHA 1 (B-R) · SBC I-A', _refs(_aha('§7.5, rec. 7'), _sbc('Quadros 20 e 21')))
        texto = 'Prevenção secundária: manter 100 mg/dia durante todo o perioperatório.' + excecao
        if cond & _DAC:
            return _item(chave, 'manter', 'Manter', texto, 'AHA 2b (B-R) · SBC I-A',
                         _refs(_aha('§7.5, rec. 11'), _sbc('Quadro 20')),
                         'AHA 2026: na DAC crônica sem ICP, manter o AAS só em selecionados, quando o risco cardíaco '
                         'superar o de sangramento (2b, B-R). SBC 2024: manter em toda prevenção secundária (I-A). '
                         'Nós optamos por seguir a SBC.')
        return _item(chave, 'manter', 'Manter', texto, 'SBC I-A', _refs(_sbc('Quadro 20')))
    return _item(chave, 'individualizar', 'Depende da indicação',
                 'Falta a indicação do AAS: em prevenção primária, a SBC suspende 7 dias antes (I-A); em prevenção '
                 'secundária, mantém durante todo o perioperatório (I-A).',
                 'SBC I-A', _refs(_sbc('Quadro 20'), _aha('§7.5')))


def _p2y12(chave, ctx, medicacoes):
    item = _p2y12_regra(chave, ctx, medicacoes)
    if ctx.get('neuraxial') and item['conduta'] in ('manter', 'individualizar'):
        nome, _, _ = _P2Y12[chave]
        asra = {'clopidogrel': '5–7', 'ticagrelor': '5–7', 'prasugrel': '7–10'}[chave]
        item['texto'] += (f' Anestesia neuroaxial: com o {nome} mantido, o bloqueio fica contraindicado (a ASRA pede '
                          f'{asra} dias sem ele); preferir outra técnica, em decisão com a anestesia.')
        item['referencias'] = _refs(item['referencias'], _ref('asra'))
    return item


def _p2y12_regra(chave, ctx, medicacoes):
    nome, dias, faixa = _P2Y12[chave]
    dapt = _AAS in medicacoes
    sang = _sangramento(ctx)
    janela = _janela_icp(ctx)
    refs = _refs(_aha('§7.5, recs. 1, 6, 8 e 10, e Tabela 12'), _sbc('Quadros 20–23'))
    reinicio = ' Se interrompido, retomar no pós-operatório o mais rápido possível (texto da SBC).'
    mantendo = ', mantendo o AAS' if dapt else ''
    div_dias = (f'AHA (Tabela 12): {faixa} dias até recuperar a função plaquetária; SBC: {dias} dias. Nós optamos por '
                f'seguir a SBC ({dias} dias), dentro da faixa da AHA.')
    if janela and sang == 'minimo' and janela['fase'] in ('proibitiva', 'manter_dapt', 'adiar'):
        return _item(chave, 'manter', 'Manter a DAPT',
                     'Procedimento de sangramento mínimo dentro do prazo após a ICP: fazer na vigência da DAPT, sem '
                     'suspender (SBC: odontologia, IIa-B; catarata com stent recente, IIa-B; baixo risco de '
                     'sangramento < 3 meses da ICP, IIa-C).',
                     'SBC IIa-B', _refs(_sbc('Quadros 11, 14 e 21')), janela['div'])
    if janela:
        fase = janela['fase']
        if fase == 'urgente':
            recente = (janela['dias'] or 0) <= 30 or (janela['tipo'] == 'farmacologico' and janela['dias'] < 91)
            return _item(chave, 'manter', 'Manter a DAPT, se o sangramento permitir',
                         janela['sbc'] + ' Se a DAPT for interrompida antes do tempo mínimo, operar em centro com '
                         'retaguarda hemodinâmica.', ('AHA 1 (B-NR) · SBC I-C' if recente else 'SBC I-C'), refs,
                         janela['div'])
        if fase == 'proibitiva':
            if janela['tempo_sensivel']:
                return _item(chave, 'manter', 'Manter a DAPT',
                             'Stent há ≤30 dias e cirurgia tempo-sensível: manter a DAPT, salvo se o risco de '
                             'sangramento superar o de trombose do stent; decisão multiprofissional.',
                             'AHA 1 (B-NR) · SBC IIa-C', refs, janela['div'])
            return _item(chave, 'individualizar', 'Não suspender: adiar a cirurgia eletiva',
                         'Stent há ≤30 dias: cirurgia eletiva que exija interromper antiplaquetário é potencialmente '
                         'danosa; adiar e manter a DAPT. Ver o aviso sobre o momento da cirurgia após ICP.',
                         'AHA 3: Dano (B-NR) · SBC III-B', refs, janela['div'])
        if fase == 'manter_dapt':
            return _item(chave, 'manter', 'Manter a DAPT',
                         'DES há <3 meses e cirurgia tempo-sensível: manter a DAPT, salvo se o risco de sangramento '
                         'superar o de trombose do stent; decisão multiprofissional.',
                         'AHA 1 (B-NR) · SBC IIa-C', refs, janela['div'])
        if fase == 'adiar':
            partes = [janela['aha'], janela['sbc'],
                      f'Não suspender agora. Se a equipe decidir operar antes do prazo, suspender o {nome} {dias} dias '
                      f'antes{mantendo}, com decisão multiprofissional.']
            return _item(chave, 'individualizar', f'Adiar a eletiva; se operar antes, suspender {dias} dias antes',
                         ' '.join(p for p in partes if p), janela['classe'], refs, janela['div'] or div_dias)
        if fase == 'indefinida':
            return _item(chave, 'individualizar', f'Suspender {dias} dias antes, se fora da janela do stent',
                         f'Falta {", ".join(janela["faltas"])} para verificar a janela após ICP; fora dela, '
                         f'suspender o {nome} {dias} dias antes{mantendo}.',
                         'AHA 1 (B-NR) · SBC I-B', refs, div_dias)
    if ctx.get('urgencia') in ('urgencia', 'emergencia'):
        return _item(chave, 'individualizar', 'Urgência: sem janela para suspensão eletiva',
                     'Na urgência não há tempo para a suspensão programada: decisão multiprofissional pesando '
                     'sangramento e trombose; se a DAPT for interrompida antes do tempo mínimo, operar em centro com '
                     'retaguarda hemodinâmica (SBC I-C).',
                     'AHA 1 (B-NR) · SBC I-C', refs)
    if sang is None:
        return _item(chave, 'individualizar', f'Suspender {dias} dias antes, conforme o sangramento',
                     'Falta o risco de sangramento da cirurgia: em procedimentos de sangramento mínimo a SBC admite '
                     f'manter o antiagregante; nos demais, suspender o {nome} {dias} dias antes.',
                     'SBC I-B' if dapt else 'SBC IIb-C', refs, div_dias)
    if sang == 'minimo':
        if dapt:
            return _item(chave, 'individualizar', 'Sangramento mínimo: em geral manter',
                         'SBC: na odontologia, manter a antiagregação (IIa-B); na catarata e injeções intravitreais '
                         'com stent recente ou SCA <1 ano, manter a DAPT (IIa-B); na dermatologia, fora do período de '
                         f'maior risco trombótico, manter o AAS e suspender o {nome} (I-C).',
                         'SBC IIa-B', _refs(_sbc('Quadros 11, 12 e 14')))
        if chave == 'clopidogrel':
            return _item(chave, 'manter', 'Manter',
                         'Sangramento mínimo: manter o clopidogrel em monoterapia (SBC: baixo risco de sangramento, '
                         'IIb-C; catarata, IIa-B; dermatologia, IIa-C).',
                         'SBC IIb-C', _refs(_sbc('Quadros 12, 14 e 20')))
        return _item(chave, 'individualizar', 'Sangramento mínimo: decisão individual',
                     f'Para o {nome} em monoterapia em procedimento de baixo risco de sangramento, a SBC não encontra '
                     f'evidência suficiente e sugere decisão multiprofissional caso a caso; se suspenso, {dias} dias '
                     'antes.',
                     'SBC: texto, sem classe', _refs(_sbc('4.1.3.2 (texto) e Quadro 20')))
    if chave == 'clopidogrel' and not dapt and sang == 'baixo_moderado':
        return _item(chave, 'individualizar', 'Manter se baixo risco; suspender 5 dias antes se moderado',
                     'Clopidogrel em monoterapia: a SBC mantém em procedimentos de baixo risco de sangramento (ex.: '
                     'dermatológicos) e suspende 5 dias antes no risco moderado ou alto; a categoria baixo/moderado da '
                     'AHA (<2%) abrange os dois cenários.' + reinicio,
                     'SBC IIb-C', refs, div_dias)
    classe = 'AHA: sem classe (Tabela 12) · SBC I-B' if dapt else 'AHA: sem classe (Tabela 12) · SBC IIb-C'
    texto = f'Suspender o {nome} {dias} dias antes{mantendo}.' + reinicio
    if ctx.get('neuraxial'):
        asra = {'clopidogrel': '5–7', 'ticagrelor': '5–7', 'prasugrel': '7–10'}[chave]
        texto += (f' Anestesia neuroaxial: a ASRA pede {asra} dias sem o {nome} antes da punção; o AAS isolado não '
                  'impede o bloqueio.')
        refs = _refs(refs, _ref('asra'))
    return _item(chave, 'suspender', f'Suspender {dias} dias antes', texto, classe, refs, div_dias)


# --- Outros (endócrino, reumatologia, psiquiatria, hormônios) -----------------------------------------------------
def _corticoide(chave, ctx):
    return _item(chave, 'manter', 'Manter a dose habitual, inclusive no dia',
                 'Manter a dose diária habitual. Com uso ≥3–4 semanas em dose acima do equivalente a hidrocortisona '
                 '15–25 mg/dia (≈ prednisona 4–6 mg/dia) e sem teste do eixo, indicar cobertura de estresse, por via '
                 'parenteral em anestesia geral ou regional (ESE/Endocrine Society 2024, boa prática clínica).',
                 'ESE/ES 2024: boa prática clínica · SPAQI: consenso',
                 _refs(_ref('ese'), _ref('spaqi_endo'), _ref('acr')),
                 'ACR/AAHKS 2022 (artroplastia de quadril ou joelho em AR, EpA ou LES): manter a dose diária habitual, '
                 'sem dose suprafisiológica (condicional, evidência baixa). Nós optamos por seguir a ESE/Endocrine '
                 'Society 2024 fora desse cenário.')


_ESCOPO_ACR = (' Recomendação feita para artroplastia eletiva de quadril ou joelho em doença reumática; em outras '
               'cirurgias, evidência indireta.')
_REINICIO_ACR = ('retomar após a cicatrização (~14 dias): ferida fechada, pontos retirados, sem edema, eritema ou '
                 'drenagem e sem infecção ativa')
_CLASSE_ACR = 'ACR/AAHKS 2022: condicional, evidência baixa a muito baixa'


def _antirreumatico(chave, ctx):
    if chave in _DMARD_MANTER:
        return _item(chave, 'manter', 'Manter', 'Manter a dose habitual no perioperatório.' + _ESCOPO_ACR,
                     _CLASSE_ACR, _refs(_ref('acr')))
    if chave in _BIOLOGICOS:
        return _item(chave, 'suspender', 'Suspender um ciclo: operar quando venceria a próxima dose',
                     'Omitir a dose prevista antes da cirurgia e operar no fim do intervalo (ex.: a cada 4 semanas → '
                     f'operar na 5ª semana); {_REINICIO_ACR}.' + _ESCOPO_ACR,
                     _CLASSE_ACR, _refs(_ref('acr')))
    if chave in _JAK:
        return _item(chave, 'suspender', 'Suspender 3 dias antes',
                     f'Última dose 3 dias antes (operar no 4º dia); {_REINICIO_ACR}. O intervalo considerou o risco de '
                     'infecção, não o de TEV.' + _ESCOPO_ACR,
                     _CLASSE_ACR, _refs(_ref('acr')))
    if chave in _LES:
        return _item(chave, 'individualizar', 'LES grave: manter; LES não grave: suspender 1 semana antes',
                     f'No LES grave, manter; no LES não grave, suspender 1 semana antes e {_REINICIO_ACR}. Não cobre '
                     'outras indicações (ex.: transplante).' + _ESCOPO_ACR,
                     _CLASSE_ACR, _refs(_ref('acr')))
    return None


def _psicotropico(chave, ctx):
    refs = _refs(_ref('spaqi_psiq'))
    classe = 'SPAQI: consenso de especialistas'
    if chave == 'litio':
        return _item(chave, 'individualizar', 'Procedimento menor: manter; maior: suspender 72 h antes',
                     'Procedimento menor: manter, inclusive no dia. Procedimento maior: suspender 72 h antes.',
                     classe, refs)
    if chave in _ANFETAMINAS:
        return _item(chave, 'suspender', 'Suspender no dia da cirurgia',
                     'Manter até a véspera; não tomar no dia da cirurgia.', classe, refs)
    return _item(chave, 'manter', 'Manter, inclusive no dia', 'Manter, inclusive no dia da cirurgia.', classe, refs)


def _hormonio(chave, ctx):
    refs = _refs(_ref('spaqi_endo'))
    classe = 'SPAQI: consenso de especialistas'
    if chave in _ESTROGENIOS:
        texto = 'Manter antes e no dia da cirurgia, pesando o risco de TEV.'
        div = ''
        if chave == 'anticoncepcional_combinado':
            texto += ' Se suspenso, considerar o risco de gestação.'
            refs = _refs(refs, _ref('mec'))
            div = ('CDC US MEC 2024: cirurgia de grande porte com imobilização prolongada é categoria 4 (risco '
                   'inaceitável) para o contraceptivo combinado; a SPAQI mantém, pesando o TEV. Nós optamos por seguir '
                   'a SPAQI na cirurgia sem imobilização prolongada; com imobilização prolongada prevista, trocar por '
                   'método só com progestagênio ou não hormonal, com antecedência.')
        return _item(chave, 'manter', 'Manter, pesando o risco de TEV', texto, classe, refs, div)
    if chave == 'anticoncepcional_so_com_progestagenio':
        return _item(chave, 'manter', 'Manter', 'Manter antes e no dia da cirurgia.', classe, refs)
    if chave == 'testosterona':
        return _item(chave, 'manter', 'Manter, pesando o risco de TEV',
                     'Manter antes e no dia da cirurgia, considerando o risco de TEV pós-operatório.', classe, refs)
    if chave == 'tamoxifeno':
        return _item(chave, 'manter', 'Manter (câncer de mama)',
                     'Manter antes e no dia da cirurgia na prevenção ou no tratamento do câncer de mama; em outras '
                     'indicações, com fator de risco de TEV, suspender ≥7 dias antes.', classe, refs)
    if chave in _TIREOIDE:
        return _item(chave, 'manter', 'Manter', 'Manter sem ajuste de dose, inclusive no dia da cirurgia.', classe,
                     refs)
    return None


# ---------------------------------------------------------------------------------------------------------------
# Despacho
# ---------------------------------------------------------------------------------------------------------------
def _regra(chave, ctx, medicacoes):
    classes = set(MEDICAMENTOS[chave]['classes'])
    if chave == 'varfarina':
        return _varfarina(chave, ctx)
    if chave in _DOAC:
        return _doac(chave, ctx)
    if chave == 'enoxaparina':
        return _enoxaparina(chave, ctx)
    if chave == _AAS:
        return _aas(chave, ctx)
    if chave in _P2Y12:
        return _p2y12(chave, ctx, medicacoes)
    if 'isglt2' in classes:
        return _isglt2(chave, ctx)
    if 'insulina' in classes:
        return _insulina(chave, ctx)
    if 'aglp1' in classes:
        return _glp1(chave, ctx)
    if 'sulfonilureia' in classes:
        return _sulfonilureia(chave, ctx)
    if chave == 'pioglitazona':
        return _pioglitazona(chave, ctx)
    if chave == 'acarbose':
        return _acarbose(chave, ctx)
    if 'idpp4_pioglitazona' in classes:
        return _idpp4(chave, ctx)
    if 'metformina' in classes:
        return _metformina(chave, ctx)
    if 'arni' in classes:
        return _arni(chave, ctx)
    if 'ieca_bra' in classes or chave == 'alisquireno':   # alisquireno: inibidor do SRAA, mesma regra
        return _ieca_bra(chave, ctx)
    if 'betabloqueador' in classes:
        return _betabloqueador(chave, ctx)
    if 'estatina' in classes:
        return _estatina(chave, ctx)
    if chave == 'clonidina':
        return _clonidina(chave, ctx)
    if chave in _OUTROS_ANTI_HAS:
        return _outro_anti_has(chave, ctx)
    if 'bcc' in classes:
        return _bcc(chave, ctx)
    if 'espironolactona' in classes:
        return _antagonista_mineralocorticoide(chave, ctx)
    if classes & {'tiazidico', 'diuretico_alca'}:
        return _diuretico(chave, ctx)
    if classes & _CARDIO_IC:
        return _cardio_ic(chave, ctx)
    if 'corticoide_sistemico' in classes:
        return _corticoide(chave, ctx)
    if chave in _DMARD_MANTER | _BIOLOGICOS | _JAK | _LES:
        return _antirreumatico(chave, ctx)
    if (classes & {'antidepressivo', 'antipsicotico_atipico', 'antipsicotico_tipico', 'litio'}
            or chave in _BENZODIAZEPINICOS | _ANFETAMINAS):
        return _psicotropico(chave, ctx)
    if chave in _ESTROGENIOS | _TIREOIDE | {'anticoncepcional_so_com_progestagenio', 'testosterona', 'tamoxifeno'}:
        return _hormonio(chave, ctx)
    return None


# ---------------------------------------------------------------------------------------------------------------
# Avisos transversais
# ---------------------------------------------------------------------------------------------------------------
def _avisos(meds, ctx):
    avisos = []
    cond = _cond(ctx)
    sang = _sangramento(ctx)
    doacs = [m for m in meds if m in _DOAC]
    anticoag = [m for m in meds if m in _ANTICOAGULANTES]
    antiagregantes = [m for m in meds if m == _AAS or m in _P2Y12]

    if ctx.get('sangramento') is None and not ctx.get('neuraxial') and (doacs or 'varfarina' in meds
                                                                          or any(m in _P2Y12 for m in meds)):
        avisos.append(_aviso(
            'Falta o risco de sangramento da cirurgia',
            'A conduta com anticoagulantes e inibidores de P2Y12 depende do risco de sangramento (AHA, Tabela 13): '
            'mínimo (~0% de sangramento maior em 30 dias: catarata, odontologia ou dermatologia menores), '
            'baixo/moderado (<2%) ou alto (≥2%).',
            _refs(_aha('Tabela 13'), _sbc('Tabela 12'))))

    if doacs and ctx.get('clcr') is None and sang != 'minimo':
        avisos.append(_aviso(
            'Falta o clearance de creatinina',
            'O esquema de ' + ', '.join(MEDICAMENTOS[m]['rotulo'].lower() for m in doacs) + ' depende do ClCr '
            '(Cockcroft-Gault: idade, peso, sexo e creatinina). Pontos de corte: <30 mL/min para anti-Xa (AHA), <50 '
            'para dabigatrana (AHA e SBC), 15–50 para apixabana e 15–30 para rivaroxabana (SBC).',
            _refs(_aha('Tabela 13'), _sbc('Quadro 26'))))

    if 'varfarina' in meds:
        avisos.append(_aviso_ponte(ctx))

    janela = _janela_icp(ctx)
    if janela:
        avisos.append(_aviso_icp(janela))

    if (ctx.get('stent') or 'stent' in cond) and any(m in _DOAC or m == 'varfarina' for m in meds) \
            and not antiagregantes:
        avisos.append(_aviso(
            'Anticoagulante oral e ICP prévia',
            'Com ICP prévia e anticoagulante oral em monoterapia, substituir por AAS durante a suspensão do '
            'anticoagulante, quando viável, até a retomada; depois, o AAS pode ser suspenso.',
            _refs(_aha('§7.5, rec. 9'))))

    if ctx.get('neuraxial') and not anticoag and set(meds) & set(_P2Y12):
        avisos.append(_aviso(
            'Anestesia neuroaxial e antiagregantes',
            'ASRA: suspender o clopidogrel e o ticagrelor 5–7 dias e o prasugrel 7–10 dias antes da punção; o AAS '
            'isolado não impede o bloqueio. Com inibidor de P2Y12 mantido (stent recente), preferir outra técnica.',
            _refs(_ref('asra'), _sbc('Quadro 21'))))
    elif ctx.get('neuraxial') and anticoag:
        avisos.append(_aviso(
            'Anestesia neuroaxial e anticoagulantes',
            'A AHA trata a anestesia neuroaxial como procedimento de maior risco de sangramento: interrupção completa '
            'do anticoagulante (≥5 meias-vidas: ≥3 dias para anti-Xa; ≥4 dias para dabigatrana, 5–6 se ClCr <50) e '
            'decisão de equipe. Com cateter peridural, a próxima dose de DOAC só ≥6 h após a retirada (SBC I-B). '
            'ASRA: anti-Xa ≥72 h; dabigatrana 72–120 h conforme o ClCr, e não fazer o bloqueio com ClCr <30; HBPM '
            '≥24 h após dose plena e ≥12 h após dose profilática; clopidogrel e ticagrelor 5–7 dias, prasugrel 7–10 '
            'dias; AAS isolado não impede o bloqueio.',
            _refs(_aha('§7.6 (texto) e Tabela 13'), _sbc('Quadro 26'), _ref('asra'))))

    diabetico = cond & {'diabetes', 'diabetes_insulina'} or any(
        set(MEDICAMENTOS[m]['classes']) & _ANTIDIABETICOS for m in meds)
    if diabetico:
        avisos.append(_aviso(
            'HbA1c e glicemia pré-operatórias',
            'Dosar a HbA1c se não houver resultado dos últimos 3 meses (AHA 2a, B-NR). Meta antes da cirurgia eletiva: '
            'HbA1c < 8%, sem hipoglicemia (SBD/SBA/ABESO I-B). HbA1c > 8%: encaminhar ao endocrinologista e considerar '
            'adiar a eletiva; HbA1c < 6% em uso de insulina ou sulfonilureia: endocrinologista, pelo risco de '
            'hipoglicemia. Cirurgia tempo-sensível ou de urgência não espera a meta. No dia, glicemia > 250 mg/dL: '
            'considerar adiar; meta perioperatória de 100 a 180 mg/dL (I-A), com glicemia de hora em hora na cirurgia '
            'média ou grande (I-A).',
            _refs(_sbd('R2, R3, R16, R17 e notas 2–3'), _aha('§7.8, rec. 1'))))
    return avisos


def _aviso_ponte(ctx):
    comp, faltas_escore = _componentes_cha2ds2vasc(ctx)
    d = _decisao_ponte(ctx)
    cond = _cond(ctx)
    partes = []
    if 'fa' in cond:
        partes.append(_descreve_escore('CHA₂DS₂-VASc', cha2ds2vasc(ctx), comp) + f'; CHADS₂ = {chads2(ctx)}.')
    if d['aha'] is None:
        partes.append('Falta a indicação da anticoagulação (FA, TEV ou prótese mecânica) para classificar o risco '
                      'tromboembólico.')
    else:
        partes.append(f'Risco tromboembólico pela AHA (Tabela 14): {d["aha"]} ({"; ".join(d["aha_motivos"])}). '
                      f'Pela SBC (Tabela 11): {d["sbc"] or "não classificado"}'
                      + (f' ({"; ".join(d["sbc_motivos"])})' if d['sbc_motivos'] else '') + '.')
        if d['ponte_aha']:
            partes.append('Ponte com heparina indicada no alto risco (AHA 2a, C-LD; SBC IIa-C).')
        else:
            partes.append('Sem ponte: a ponte de rotina aumenta o sangramento sem reduzir eventos (AHA 3: Dano, C-LD; '
                          'SBC IIa-C).')
    faltas = list(d['faltas']) if d['aha'] is not None else []
    if 'fa' in cond:
        faltas = [f for f in faltas_escore] + faltas
    if faltas:
        partes.append('Falta informar: ' + '; '.join(faltas) + '.')
    if d['notas']:
        partes.append(' '.join(n[0].upper() + n[1:] + '.' for n in d['notas']))
    return _aviso('Varfarina: risco tromboembólico e ponte', ' '.join(partes),
                  _refs(_aha('§7.6, recs. 2 e 3, e Tabela 14'), _sbc('Tabela 11 e Quadro 25')), _div_ponte(d))


def _aviso_icp(j):
    if j['fase'] == 'indefinida' and not j['aha']:
        texto = ('Falta ' + ', '.join(j['faltas']) + ' para definir o momento da cirurgia e a conduta com a DAPT. '
                 'Referências: AHA, ≥12 meses após DES por SCA (1), ≥6 meses por DAC crônica (2a), ≥3 meses se '
                 'tempo-sensível (2b), nunca ≤30 dias com interrupção de antiplaquetário (3: Dano); SBC, Quadros '
                 '22–23.')
    else:
        texto = ' '.join(p for p in (j['aha'], j['sbc']) if p)
        if j['faltas']:
            texto += ' Falta informar: ' + ', '.join(j['faltas']) + '.'
    texto += (' Decisão sobre antiplaquetários e momento da cirurgia por equipe multiprofissional, com o paciente '
              '(AHA 1, B-NR).')
    return _aviso('Momento da cirurgia após ICP', texto.strip(),
                  _refs(_aha('§7.5, recs. 1–10'), _sbc('Quadros 21–23')), j['div'])


# ---------------------------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------------------------
def condutas(medicacoes: list[str], ctx: dict) -> dict:
    """Conduta perioperatória para cada medicamento e avisos transversais.

    ``medicacoes``: chaves de ``MEDICAMENTOS`` (chaves desconhecidas são ignoradas; repetidas contam uma vez).
    ``ctx`` (tudo opcional): idade, sexo ('masculino'|'feminino'), peso, clcr (mL/min, Cockcroft-Gault),
    sangramento ('minimo'|'baixo_moderado'|'alto'), cirurgia_risco_elevado, urgencia
    ('eletiva'|'tempo_sensivel'|'urgencia'|'emergencia'), neuraxial (aceita também 'neuroaxial'), condicoes (set), stent
    ({'tipo': 'farmacologico'|'convencional'|'balao', 'indicacao': 'sca'|'dac_cronica', 'dias': int}; 'meses' ainda
    é aceito), aas_indicacao ('primaria'|'secundaria'), pa_controlada, cirurgia (chave de preoperatorio.CIRURGIAS).

    Devolve {'itens': [...], 'avisos': [...]}. Item: chave, medicamento, conduta
    ('manter'|'suspender'|'ajustar'|'individualizar'), resumo, texto, classe, referencias [{label, url}],
    divergencia. Aviso: titulo, texto, referencias, divergencia.
    """
    ctx = dict(ctx or {})
    ctx['condicoes'] = _cond(ctx)
    if ctx.get('neuraxial') is None and 'neuroaxial' in ctx:
        ctx['neuraxial'] = ctx['neuroaxial']
    meds = []
    for chave in medicacoes or ():
        if chave in MEDICAMENTOS and chave not in meds:
            meds.append(chave)
    ctx['medicacoes'] = set(meds)
    itens = [i for i in (_regra(chave, ctx, meds) for chave in meds) if i]
    return {'itens': itens, 'avisos': _avisos(meds, ctx)}


def _cobertas(ctx):
    return frozenset(k for k in MEDICAMENTOS if _regra(k, ctx, [k]) is not None)


# Medicamentos com regra em qualquer contexto; os de CHAVES_SO_NA_IC só têm regra com IC (SBC, Quadro 8).
CHAVES_COBERTAS = _cobertas({'condicoes': set()})
CHAVES_SO_NA_IC = _cobertas({'condicoes': {'ic'}}) - CHAVES_COBERTAS
