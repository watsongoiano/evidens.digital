"""Coerência entre campos do formulário.

Um dado implica outro: estatina implica dislipidemia, anti-hipertensivo implica
hipertensão, HbA1c ≥ 6,5% implica diabetes, IMC ≥ 30 implica obesidade etc. Sem
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

ROTULOS = {
    'dislipidemia': 'Dislipidemia', 'hipertensao': 'Hipertensão', 'diabetes': 'Diabetes tipo 2',
    'obesidade': 'Obesidade', 'doenca_renal': 'Doença renal crônica',
    'estatinas': 'Estatinas', 'anti_hipertensivos': 'Anti-hipertensivos',
}


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
    """Categoria da PA de consultório pela diretriz AHA/ACC 2025 (mesmas faixas de 2017)."""
    if not pas and not pad:
        return None
    pas, pad = float(pas or 0), float(pad or 0)
    if pas >= 140 or pad >= 90:
        return {'categoria': 'estagio2', 'rotulo': 'HAS estágio 2'}
    if pas >= 130 or pad >= 80:
        return {'categoria': 'estagio1', 'rotulo': 'HAS estágio 1'}
    if pas >= 120:
        return {'categoria': 'elevada', 'rotulo': 'PA elevada'}
    return {'categoria': 'normal', 'rotulo': 'PA normal'}


def inferir(data, egfr=None, gestante=False):
    """Completa comorbidades e medicações a partir dos outros campos.

    Devolve ``(comorbidades, medicacoes, inferencias)``; cada inferência tem
    ``campo``, ``valor``, ``rotulo`` e ``motivo``. Nunca desmarca nada.
    """
    comorbidades = list(data.get('comorbidades') or [])
    medicacoes = list(data.get('medicacoes') or [])
    inferencias = []

    def marcar(lista, campo, valor, motivo):
        if valor not in lista:
            lista.append(valor)
            inferencias.append({'campo': campo, 'valor': valor, 'rotulo': ROTULOS[valor], 'motivo': motivo})

    texto = achados_no_texto(data.get('medicacoes_continuo') or '')
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
        limiar = pa['categoria'] == 'estagio2' or (pa['categoria'] == 'estagio1' and not gestante)
        if limiar:
            marcar(comorbidades, 'comorbidades', 'hipertensao',
                   f"PA {_pa_texto(data)} = {pa['rotulo']} (AHA/ACC 2025); confirmar com MRPA ou MAPA")
    if 'has_resistente' in comorbidades:
        marcar(comorbidades, 'comorbidades', 'hipertensao', 'HAS resistente marcada')
    if 'antidiabeticos' in texto:
        marcar(comorbidades, 'comorbidades', 'diabetes', 'antidiabético citado em "Outras medicações"')
    hba1c = data.get('hba1c')
    if hba1c is not None and float(hba1c) >= 6.5 and 'diabetes_tipo_2' not in comorbidades:
        marcar(comorbidades, 'comorbidades', 'diabetes', 'HbA1c ≥ 6,5% (ADA; confirmar com 2º exame)')
    peso, altura = data.get('peso'), data.get('altura')
    if peso and altura and float(peso) / (float(altura) / 100) ** 2 >= 30:
        marcar(comorbidades, 'comorbidades', 'obesidade', 'IMC ≥ 30 kg/m²')
    if egfr is not None and egfr < 60:
        marcar(comorbidades, 'comorbidades', 'doenca_renal',
               f'TFG estimada {egfr} mL/min/1,73 m² (< 60; confirmar cronicidade > 3 meses)')
    return comorbidades, medicacoes, inferencias
