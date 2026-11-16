"""Coerência entre campos do formulário.

Um dado implica outro: estatina implica dislipidemia, anti-hipertensivo implica
hipertensão, IMC ≥ 30 implica obesidade etc. Um exame isolado não confirma doença: PA de
consultório, TFG < 60 e HbA1c ≥ 6,5% pedem confirmação, sem marcar a caixa. Sem
isso, o médico marca "sinvastatina" no texto e o motor (e o PREVENT) tratam o
paciente como se não usasse estatina.

As mesmas regras rodam na tela (static/coerencia.js, que lê TERMOS por
/api/coerencia) e no servidor (aqui), para que o resultado não dependa de o
navegador ter marcado as caixas.
"""
from __future__ import annotations

import re
import unicodedata

# Termos procurados no campo "Outras medicações", sem acento e por palavra inteira.
TERMOS = {
    'estatinas': [
        'estatina', 'estatinas', 'sinvastatina', 'simvastatina', 'atorvastatina', 'rosuvastatina',
        'pravastatina', 'pitavastatina', 'lovastatina', 'fluvastatina',
    ],
    'outros_hipolipemiantes': [
        'ezetimiba', 'ezetimibe', 'fenofibrato', 'ciprofibrato', 'bezafibrato', 'genfibrozila',
        'evolocumabe', 'alirocumabe', 'inclisirana', 'acido bempedoico',
    ],
    'anti_hipertensivos': [
        'anti-hipertensivo', 'anti-hipertensivos', 'antihipertensivo', 'antihipertensivos',
        'losartana', 'losartan', 'valsartana', 'valsartan', 'olmesartana', 'candesartana', 'irbesartana',
        'telmisartana', 'enalapril', 'captopril', 'ramipril', 'lisinopril', 'perindopril',
        'anlodipino', 'amlodipina', 'nifedipino', 'lercanidipino', 'hidroclorotiazida', 'clortalidona',
        'indapamida', 'espironolactona', 'atenolol', 'metoprolol', 'bisoprolol', 'carvedilol',
        'nebivolol', 'metildopa', 'hidralazina', 'clonidina',
    ],
    # Metformina, iSGLT2 e aGLP-1 ficam de fora: também são usados em pré-diabetes,
    # SOP, IC, DRC e obesidade, então não provam diabetes.
    'antidiabeticos': [
        'insulina', 'glibenclamida', 'gliclazida', 'glimepirida', 'glipizida', 'sitagliptina',
        'vildagliptina', 'linagliptina', 'saxagliptina', 'alogliptina', 'pioglitazona', 'acarbose',
        'repaglinida', 'nateglinida',
    ],
}

METFORMINA_NO_TEXTO = ('metformina', 'metformin', 'glifage')

ROTULOS = {
    'dislipidemia': 'Dislipidemia', 'hipertensao': 'Hipertensão', 'diabetes': 'Diabetes tipo 2',
    'obesidade': 'Obesidade', 'doenca_renal': 'Doença renal crônica',
    'estatinas': 'Estatinas', 'anti_hipertensivos': 'Anti-hipertensivos',
    'insuficiencia_cardiaca': 'Insuficiência cardíaca', 'dcv_aterosclerotica': 'Doença cardiovascular aterosclerótica',
    'dpoc': 'DPOC', 'hiv': 'HIV', 'diabetes_tipo_1': 'Diabetes tipo 1', 'has_resistente': 'HAS resistente',
}
from src.utils.condicoes import TIPOS_DE_DIABETES as DIABETES  # noqa: E402  (tipo 1, tipo 2 e tipos específicos)


def rotulo_de(valor):
    """Nome da caixa: as fixas da tela estão em ROTULOS; as da lista com busca, em condicoes.COMORBIDADES."""
    from src.utils.condicoes import COMORBIDADES
    return ROTULOS.get(valor) or COMORBIDADES[valor]['rotulo']


def _normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.split(r'[^a-z0-9-]+', texto))


def _pa_texto(data):
    def n(v):
        return f'{float(v):g}' if v not in (None, '') else '–'
    return f"{n(data.get('pas'))}/{n(data.get('pad'))} mmHg"


def achados_no_texto(texto):
    """Classes de medicação citadas no texto livre (palavra inteira, sem acento)."""
    t = f' {_normalizar(texto)} '
    return {classe for classe, termos in TERMOS.items()
            if any(f' {termo} ' in t for termo in termos)}


def classificar_pa(pas, pad):
    """Categoria da PA de consultório pela diretriz AHA/ACC 2025 (mesmas faixas de 2017), com a da SBC 2025 em ``sbc``.

    Com só um dos componentes, a categoria vale apenas se aquele valor já a define
    (ex.: PAS 145 é estágio 2 qualquer que seja a PAD); senão volta "incompleta".
    A categoria é da medida, não um diagnóstico: uma PA isolada não confirma HAS (ver ``inferir``).
    """
    c = _classificar_pa_aha(pas, pad)
    if c is not None:
        sbc = classificar_pa_sbc(pas, pad)
        if sbc:
            c['sbc'] = sbc
    return c


# SBC 2025 (Diretriz Brasileira de HAS, Arq Bras Cardiol 2025;122(9):e20250624): normal < 120/80;
# pré-hipertensão 120-139 e/ou 80-89; HAS estágio 1 140-159/90-99, estágio 2 160-179/100-109, estágio 3 ≥ 180/110.
ROTULOS_SBC = {'normal': 'PA normal', 'pre_hipertensao': 'pré-hipertensão', 'estagio1': 'HAS estágio 1',
               'estagio2': 'HAS estágio 2', 'estagio3': 'HAS estágio 3'}


def classificar_pa_sbc(pas, pad):
    """Categoria da PA de consultório pela SBC 2025, ou None se faltar o componente que a define."""
    tem_pas, tem_pad = pas not in (None, ''), pad not in (None, '')
    if not tem_pas and not tem_pad:
        return None
    s_ = float(pas) if tem_pas else None
    d_ = float(pad) if tem_pad else None
    for categoria, corte_s, corte_d in (('estagio3', 180, 110), ('estagio2', 160, 100), ('estagio1', 140, 90),
                                         ('pre_hipertensao', 120, 80)):
        if (s_ is not None and s_ >= corte_s) or (d_ is not None and d_ >= corte_d):
            # com um componente só, a categoria vale se ele já a define (o outro só poderia subir a faixa)
            c = {'categoria': categoria, 'rotulo': ROTULOS_SBC[categoria]}
            if not (tem_pas and tem_pad):
                c['incompleta'] = True
            return c
    if not (tem_pas and tem_pad):
        return None
    return {'categoria': 'normal', 'rotulo': ROTULOS_SBC['normal']}


# PA a partir da qual uma medida de consultório basta para tratar como HAS (decisão do responsável clínico:
# HAS estágio 3 da SBC 2025). Abaixo disso, sem HAS conhecida, a PA alterada só pede confirmação (MRPA ou MAPA).
PA_GRAVE = (180, 110)


def pa_grave(pas, pad):
    s_ = float(pas) if pas not in (None, '') else None
    d_ = float(pad) if pad not in (None, '') else None
    return (s_ is not None and s_ >= PA_GRAVE[0]) or (d_ is not None and d_ >= PA_GRAVE[1])


def pa_a_confirmar(classificacao, comorbidades, gestante=False):
    """PA de consultório ≥ 130/80 (AHA/ACC 2025) sem HAS conhecida: estado "PA alterada, HAS a confirmar".

    Fora da gestação. HAS marcada pelo médico, anti-hipertensivo em uso (que marca HAS) ou PA ≥ 180/110 já
    chegam aqui como 'hipertensao' nas comorbidades e não ficam neste estado.
    """
    if gestante or not classificacao or 'hipertensao' in comorbidades:
        return False
    return classificacao['categoria'] in ('estagio1', 'estagio2')


def _classificar_pa_aha(pas, pad):
    tem_pas, tem_pad = pas not in (None, ''), pad not in (None, '')
    if not tem_pas and not tem_pad:
        return None
    s_ = float(pas) if tem_pas else None
    d_ = float(pad) if tem_pad else None
    if (s_ is not None and s_ >= 140) or (d_ is not None and d_ >= 90):
        return {'categoria': 'estagio2', 'rotulo': 'HAS estágio 2'}
    if (s_ is not None and s_ >= 130) or (d_ is not None and d_ >= 80):
        if tem_pas and tem_pad:
            return {'categoria': 'estagio1', 'rotulo': 'HAS estágio 1'}
        return {'categoria': 'estagio1', 'rotulo': 'HAS estágio 1 ou 2 (falta um componente)', 'incompleta': True}
    if not (tem_pas and tem_pad):
        return {'categoria': 'incompleta', 'rotulo': 'Informe PAS e PAD para classificar', 'incompleta': True}
    if s_ >= 120:
        return {'categoria': 'elevada', 'rotulo': 'PA elevada'}
    return {'categoria': 'normal', 'rotulo': 'PA normal'}


RESISTENTE_REFERENCIA = 'AHA 2018; AHA/ACC 2025'
RESISTENTE_CONFIRMAR = 'confirmar adesão, doses máximas toleradas e PA fora do consultório (MRPA ou MAPA)'


def classes_em_uso(escolhidas, hipertensao):
    """Classes anti-hipertensivas distintas em uso (betabloqueador, espironolactona etc. só com hipertensão)."""
    from src.utils.medicamentos import classes_anti_hipertensivas
    classes = set()
    for chave in escolhidas or ():
        delas, so_com_has = classes_anti_hipertensivas(chave)
        if delas and (hipertensao or not so_com_has):
            classes |= delas
    return classes


def hipertensao_resistente(escolhidas, hipertensao, pas, pad, gestante=False):
    """Motivo para marcar HAS resistente, ou None.

    AHA 2018 (Carey et al., Hypertension 2018;72:e53) e AHA/ACC 2025: PA acima da meta com 3 classes
    anti-hipertensivas em dose máxima tolerada, ou PA na meta com 4 ou mais. Meta < 130/80 (na gestação,
    hipertensão a partir de 140/90). Com 3 classes e PA não informada, não marca: a dica da tela pede a PA.
    """
    classes = classes_em_uso(escolhidas, hipertensao)
    if len(classes) >= 4:
        return f'{len(classes)} classes de anti-hipertensivos ({RESISTENTE_REFERENCIA}); {RESISTENTE_CONFIRMAR}'
    if len(classes) == 3:
        corte_s, corte_d = (140, 90) if gestante else (130, 80)
        s_ = float(pas) if pas not in (None, '') else None
        d_ = float(pad) if pad not in (None, '') else None
        if (s_ is not None and s_ >= corte_s) or (d_ is not None and d_ >= corte_d):
            pa = f"{s_:g}" if s_ is not None else '–'
            pa += '/' + (f"{d_:g}" if d_ is not None else '–')
            return (f'3 classes de anti-hipertensivos com PA {pa} mmHg acima da meta ({RESISTENTE_REFERENCIA}); '
                    f'{RESISTENTE_CONFIRMAR}')
    return None


def inferir(data, egfr=None, gestante=False, recusados=(), escolhidas=()):
    """Completa comorbidades e medicações a partir dos outros campos.

    ``escolhidas`` são os medicamentos como vieram da tela (princípio ativo), antes de virarem classe:
    o que só se usa numa doença marca a doença (``medicamentos.MARCA``).

    Devolve ``(comorbidades, medicacoes, inferencias)``; cada inferência tem
    ``campo``, ``valor``, ``rotulo`` e ``motivo``. Nunca desmarca nada.
    """
    comorbidades = list(data.get('comorbidades') or [])
    medicacoes = list(data.get('medicacoes') or [])
    inferencias = []

    def marcar(lista, campo, valor, motivo):
        # "recusados": caixas automáticas que o médico desmarcou na tela.
        # Antidiabético ou HbA1c ≥ 6,5% não dizem o tipo: se outro tipo de diabetes já está marcado, o tipo 2 não entra.
        if valor == 'diabetes' and set(DIABETES) & set(comorbidades):
            return
        if valor not in lista and valor not in recusados:
            lista.append(valor)
            inferencias.append({'campo': campo, 'valor': valor, 'rotulo': rotulo_de(valor), 'motivo': motivo})

    texto = achados_no_texto(data.get('medicacoes_continuo') or '')
    # Metformina citada no texto livre entra como medicação (vitamina B12 em uso de metformina), sem marcar
    # diabetes: também se usa em pré-diabetes e resistência insulínica.
    livre = f" {_normalizar(data.get('medicacoes_continuo') or '')} "
    if 'metformina' not in medicacoes and any(f' {termo} ' in livre for termo in METFORMINA_NO_TEXTO):
        medicacoes.append('metformina')
    # Itens da lista suspensa de medicações (src/utils/condicoes.py)
    from src.utils.condicoes import MEDICACOES
    for chave in list(medicacoes):
        for alvo in MEDICACOES.get(chave, {}).get('marca', []):
            destino = medicacoes if alvo in ('estatinas', 'anti_hipertensivos') else comorbidades
            marcar(destino, 'medicacoes' if destino is medicacoes else 'comorbidades', alvo,
                   f"uso de {MEDICACOES[chave]['rotulo']}")
    from src.utils.medicamentos import MARCA, MEDICAMENTOS
    for chave in escolhidas:
        for alvo in MARCA.get(chave, []):
            marcar(comorbidades, 'comorbidades', alvo, f"uso de {MEDICAMENTOS[chave]['rotulo'].split(' (')[0]}")
    if 'estatinas' in texto:
        marcar(medicacoes, 'medicacoes', 'estatinas', 'estatina citada em "Outras medicações"')
    if 'anti_hipertensivos' in texto:
        marcar(medicacoes, 'medicacoes', 'anti_hipertensivos', 'anti-hipertensivo citado em "Outras medicações"')
    if 'estatinas' in medicacoes:
        marcar(comorbidades, 'comorbidades', 'dislipidemia', 'uso de estatina')
    if 'outros_hipolipemiantes' in texto:
        marcar(comorbidades, 'comorbidades', 'dislipidemia', 'uso de hipolipemiante')
    if 'anti_hipertensivos' in medicacoes:
        marcar(comorbidades, 'comorbidades', 'hipertensao', 'uso de anti-hipertensivo')
    # Na gestação a PA não marca hipertensão: antes de 20 semanas é provável HAS crônica a confirmar; depois,
    # hipertensão gestacional ou pré-eclâmpsia (ACOG PB 222). As orientações vêm de src/utils/prenatal.py.
    pa = None if gestante else classificar_pa(data.get('pas'), data.get('pad'))
    if pa:
        # Uma PA de consultório isolada não rotula HAS (SBC 2025 e AHA/ACC 2025: confirmar em 2 ou mais consultas
        # ou com MRPA/MAPA). Fora da gestação, só a PA ≥ 180/110 marca a caixa; de 130/80 a 179/109 a rota pede
        # MRPA ou MAPA (estado "PA alterada, HAS a confirmar", ver pa_a_confirmar).
        if pa_grave(data.get('pas'), data.get('pad')):
            marcar(comorbidades, 'comorbidades', 'hipertensao',
                   f"PA {_pa_texto(data)} ≥ 180/110 mmHg = HAS estágio 3 (SBC 2025); confirmar com MRPA ou MAPA")
    resistente = hipertensao_resistente(escolhidas, 'hipertensao' in comorbidades, data.get('pas'), data.get('pad'), gestante)
    if resistente:
        marcar(comorbidades, 'comorbidades', 'has_resistente', resistente)
    if 'has_resistente' in comorbidades:
        marcar(comorbidades, 'comorbidades', 'hipertensao', 'HAS resistente marcada')
    # Betabloqueador, espironolactona, diurético de alça e sacubitril/valsartana têm outras indicações
    # (IC, FA, edema) e por isso não marcam hipertensão. Com hipertensão presente, contam como
    # tratamento anti-hipertensivo (é o que o PREVENT pergunta).
    if 'hipertensao' in comorbidades and 'anti_hipertensivos' not in medicacoes:
        for chave in medicacoes:
            if MEDICACOES.get(chave, {}).get('reduz_pa'):
                marcar(medicacoes, 'medicacoes', 'anti_hipertensivos',
                       f"hipertensão em uso de {MEDICACOES[chave]['rotulo'].lower()}")
                break
    if 'antidiabeticos' in texto:
        marcar(comorbidades, 'comorbidades', 'diabetes', 'antidiabético citado em "Outras medicações"')
    hba1c = data.get('hba1c')
    # HbA1c ≥ 6,5% isolada não marca caixa nenhuma: sem diabetes marcado, pede confirmação (diabetes_a_confirmar).
    # 5,7 a 6,4% em quem não tem diabetes é pré-diabetes (no diabético tratado, é só bom controle)
    if hba1c is not None and 5.7 <= float(hba1c) < 6.5 and not set(DIABETES) & set(comorbidades) and 'insulina' not in medicacoes:
        marcar(comorbidades, 'comorbidades', 'pre_diabetes', 'HbA1c de 5,7 a 6,4% (ADA)')
    peso, altura = data.get('peso'), data.get('altura')
    if peso and altura and float(peso) / (float(altura) / 100) ** 2 >= 30:
        marcar(comorbidades, 'comorbidades', 'obesidade', 'IMC ≥ 30 kg/m²')
    # TFG < 60 e HbA1c ≥ 6,5% isoladas não marcam DRC nem diabetes: a rota pede a confirmação
    # (drc_a_confirmar, diabetes_a_confirmar).
    return comorbidades, medicacoes, inferencias


def drc_a_confirmar(egfr, comorbidades):
    """TFG estimada < 60 sem DRC marcada pelo médico: estado "DRC a confirmar".

    KDIGO 2024, Practice Points 1.1.3.1 e 1.1.3.2: a cronicidade (≥ 3 meses) tem de ser provada, e não se presume
    a partir de um único resultado de TFG ou de albuminúria (pode ser lesão renal aguda). A comorbidade não é
    marcada; a rota pede creatinina/TFG e uACR em 3 meses (PP 1.1.1.2: repetir o exame para confirmar).
    """
    return egfr is not None and egfr < 60 and 'doenca_renal' not in comorbidades


def diabetes_a_confirmar(hba1c, comorbidades, medicacoes):
    """HbA1c ≥ 6,5% sem diabetes marcado pelo médico e sem antidiabético: estado "diabetes a confirmar".

    ADA 2026 (seção 2): sem hiperglicemia inequívoca, o diagnóstico exige dois resultados alterados (do mesmo
    exame repetido ou de dois exames diferentes). O formulário não registra sintomas nem glicemia casual, então
    não há como saber se a hiperglicemia é inequívoca: o motor só pede a confirmação e o médico marca o diabetes.
    Antidiabético que só se usa no diabetes já marca a caixa (``inferir``); insulina em uso também conta.
    """
    if hba1c in (None, '') or float(hba1c) < 6.5:
        return False
    return not (set(DIABETES) & set(comorbidades)) and 'insulina' not in medicacoes
