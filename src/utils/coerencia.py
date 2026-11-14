"""Coerência entre campos do formulário.

Um dado implica outro: estatina implica dislipidemia, anti-hipertensivo implica
hipertensão, IMC ≥ 30 implica obesidade etc. (HbA1c ≥ 6,5% indica diabetes sem dizer o tipo) Sem
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
    'dpoc': 'DPOC', 'hiv': 'HIV', 'diabetes_tipo_1': 'Diabetes tipo 1',
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
    """Categoria da PA de consultório pela diretriz AHA/ACC 2025 (mesmas faixas de 2017).

    Com só um dos componentes, a categoria vale apenas se aquele valor já a define
    (ex.: PAS 145 é estágio 2 qualquer que seja a PAD); senão volta "incompleta".
    """
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
    pa = classificar_pa(data.get('pas'), data.get('pad'))
    if pa:
        # Fora da gestação, corte AHA/ACC 2025 (≥ 130/80). Na gestação, ≥ 140/90.
        # (estágio 1 com um componente faltando pode ser 2 na gestação; só marca o que é certo)
        limiar = pa['categoria'] == 'estagio2' or (pa['categoria'] == 'estagio1' and not gestante)
        if limiar:
            marcar(comorbidades, 'comorbidades', 'hipertensao',
                   f"PA {_pa_texto(data)} = {pa['rotulo']} (AHA/ACC 2025); confirmar com MRPA ou MAPA")
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
    # HbA1c ≥ 6,5% é critério de diabetes, mas não diz o tipo: não marca caixa nenhuma (o motor trata o
    # paciente como diabético e pede o tipo; ver a rota do check-up).
    # 5,7 a 6,4% em quem não tem diabetes é pré-diabetes (no diabético tratado, é só bom controle)
    if hba1c is not None and 5.7 <= float(hba1c) < 6.5 and not set(DIABETES) & set(comorbidades) and 'insulina' not in medicacoes:
        marcar(comorbidades, 'comorbidades', 'pre_diabetes', 'HbA1c de 5,7 a 6,4% (ADA)')
    peso, altura = data.get('peso'), data.get('altura')
    if peso and altura and float(peso) / (float(altura) / 100) ** 2 >= 30:
        marcar(comorbidades, 'comorbidades', 'obesidade', 'IMC ≥ 30 kg/m²')
    if egfr is not None and egfr < 60:
        marcar(comorbidades, 'comorbidades', 'doenca_renal',
               f'TFG estimada {egfr} mL/min/1,73 m² (< 60; confirmar cronicidade > 3 meses)')
    return comorbidades, medicacoes, inferencias
