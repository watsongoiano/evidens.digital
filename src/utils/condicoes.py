"""Listas de comorbidades, medicações e história familiar e o que cada item dispara.

Substituem os campos de texto livre: cada item escolhido na lista suspensa tem
efeito definido (exame, vacina, orientação, agravante de risco ou resposta da
triagem de vacinas), com a fonte ao lado. As chaves vão nos mesmos campos de
lista do formulário (``comorbidades``, ``medicacoes``, ``historia_familiar``).

``marca`` diz quais caixas o item implica (as mesmas regras de coerência da tela).
"""
from __future__ import annotations

ORDEM_PRIORIDADE = {'baixa': 0, 'media': 1, 'alta': 2}

COMORBIDADES = {
    'hipotireoidismo': {'rotulo': 'Hipotireoidismo'},
    'masld': {'rotulo': 'Esteatose hepática (MASLD)', 'agravante': 'esteatose hepática (MASLD)'},
    'cirrose': {'rotulo': 'Cirrose / hepatopatia crônica'},
    'doenca_autoimune': {'rotulo': 'Doença inflamatória autoimune (AR, lúpus, psoríase, DII)',
                         'agravante': 'doença inflamatória crônica'},
    'asma_grave': {'rotulo': 'Asma moderada ou grave'},
    'asplenia': {'rotulo': 'Asplenia / esplenectomia'},
    'osteoporose': {'rotulo': 'Osteoporose'},
    'gota': {'rotulo': 'Gota'},
    'neoplasia_ativa': {'rotulo': 'Câncer em quimio ou radioterapia', 'imunossupressao': True},
}

MEDICACOES = {
    'ieca_bra': {'rotulo': 'IECA ou BRA', 'marca': ['anti_hipertensivos']},
    'tiazidico': {'rotulo': 'Diurético tiazídico', 'marca': ['anti_hipertensivos']},
    'bcc': {'rotulo': 'Bloqueador de canal de cálcio', 'marca': ['anti_hipertensivos']},
    'betabloqueador': {'rotulo': 'Betabloqueador'},
    'espironolactona': {'rotulo': 'Espironolactona / eplerenona'},
    'diuretico_alca': {'rotulo': 'Diurético de alça'},
    'outro_hipolipemiante': {'rotulo': 'Ezetimiba, fibrato ou iPCSK9', 'marca': ['dislipidemia']},
    'metformina': {'rotulo': 'Metformina'},
    'insulina': {'rotulo': 'Insulina', 'marca': ['diabetes']},
    'sulfonilureia': {'rotulo': 'Sulfonilureia', 'marca': ['diabetes']},
    'idpp4_pioglitazona': {'rotulo': 'iDPP-4 ou pioglitazona', 'marca': ['diabetes']},
    'isglt2': {'rotulo': 'iSGLT2'},
    'aglp1': {'rotulo': 'Agonista de GLP-1'},
    'levotiroxina': {'rotulo': 'Levotiroxina'},
    'corticoide_cronico': {'rotulo': 'Corticoide sistêmico ≥ 3 meses'},
    'imunossupressor': {'rotulo': 'Imunossupressor ou imunobiológico', 'imunossupressao': True},
    'litio': {'rotulo': 'Lítio'},
    'amiodarona': {'rotulo': 'Amiodarona'},
}

FAMILIA = {
    'cancer_prostata': {'rotulo': 'Câncer de próstata (pai ou irmão)'},
    'osteoporose_fratura': {'rotulo': 'Fratura de quadril em pai ou mãe'},
    'hipercolesterolemia_familiar': {'rotulo': 'Hipercolesterolemia familiar'},
    'aneurisma_aorta': {'rotulo': 'Aneurisma de aorta abdominal'},
    'morte_subita': {'rotulo': 'Morte súbita antes dos 50 anos'},
}
# Marcadas por chip na tela (e "cardiopatia" é o valor antigo de DAC precoce).
FAMILIA_CHIPS = ('cancer_mama', 'cancer_colorretal', 'cancer_ovario', 'diabetes', 'dac_precoce', 'cardiopatia')

PNEUMO = 'Pneumocócica conjugada 20-valente (Prevenar 20®)'
ZOSTER = 'Herpes Zóster (Shingrix®)'
VSR = 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'
SBIM = 'SBIm 2026/2027'


def imunossupressao_implicada(comorbidades, medicacoes):
    return any(COMORBIDADES.get(c, {}).get('imunossupressao') for c in comorbidades) or \
        any(MEDICACOES.get(m, {}).get('imunossupressao') for m in medicacoes)


def agravantes_de_risco(comorbidades, familia, hiv=False):
    """Agravantes de risco cardiovascular (SBC 2025) que o formulário consegue saber."""
    lista = [COMORBIDADES[c]['agravante'] for c in comorbidades if COMORBIDADES.get(c, {}).get('agravante')]
    if 'obesidade' in comorbidades:
        lista.append('obesidade')
    if hiv:
        lista.append('HIV')
    if {'dac_precoce', 'cardiopatia'} & set(familia):
        lista.append('história familiar de DCV prematura')
    return lista


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau, prioridade='media', substituir=False):
    return {'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'referencia': referencia, 'grau_evidencia': grau, 'prioridade': prioridade, '_substituir': substituir}


def _garantir(recs, nova):
    """Acrescenta a recomendação; se o título já existe, soma o motivo e sobe a prioridade."""
    substituir = nova.pop('_substituir', False)
    for r in recs:
        if (r.get('titulo') or '').strip().lower() == nova['titulo'].lower():
            if ORDEM_PRIORIDADE.get(nova['prioridade'], 0) > ORDEM_PRIORIDADE.get(r.get('prioridade'), 0):
                r['prioridade'] = nova['prioridade']
            if substituir:
                r.update({k: nova[k] for k in ('descricao', 'subtitulo', 'referencia', 'grau_evidencia')})
            else:
                if nova['subtitulo'] not in (r.get('subtitulo') or ''):
                    r['subtitulo'] = f"{r.get('subtitulo') or ''} | Também: {nova['subtitulo']}".strip(' |')
                if nova['referencia'] not in (r.get('referencia') or ''):
                    r['referencia'] = f"{r.get('referencia') or ''} | {nova['referencia']}".strip(' |')
            return
    recs.append(nova)


def aplicar(recs, idade, sexo, comorbidades, medicacoes, familia, gestante=False):
    """Soma às recomendações o que as listas disparam. Devolve as orientações (sem pedido/receita)."""
    com, med, fam = set(comorbidades), set(medicacoes), set(familia)
    orient = []

    def add(*a, **k):
        _garantir(recs, _rec(*a, **k))

    def orientar(titulo, descricao, referencia):
        orient.append({'titulo': titulo, 'descricao': descricao, 'referencia': referencia})

    # ---------------- História familiar ----------------
    if 'cancer_colorretal' in fam:
        if idade >= 40:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                'Parente de 1º grau com câncer colorretal: colonoscopia a partir dos 40 anos, ou 10 anos antes da idade '
                'do diagnóstico do familiar mais jovem (o que vier primeiro), repetida a cada 5 anos.',
                'História familiar de CCR | A partir de 40 anos | A cada 5 anos',
                'USMSTF 2017 / ACG 2021', 'B', 'alta', substituir=True)
        else:
            orientar('Colonoscopia por história familiar de câncer colorretal',
                     'Iniciar aos 40 anos ou 10 anos antes da idade do diagnóstico do familiar de 1º grau mais jovem '
                     '(o que vier primeiro); depois, a cada 5 anos.', 'USMSTF 2017 / ACG 2021')
    if 'cancer_mama' in fam and sexo == 'feminino':
        if idade >= 40:
            add('Mamografia Digital - Bilateral', 'imagem',
                'Parente de 1º grau com câncer de mama: mamografia anual a partir dos 40 anos (ou 10 anos antes do '
                'diagnóstico da familiar, não antes dos 30).',
                'História familiar de câncer de mama | Anual', 'ACR 2023 / NCCN 2024', 'B', 'alta', substituir=True)
        elif idade >= 30:
            orientar('Mamografia por história familiar de câncer de mama',
                     'Se a familiar de 1º grau teve o diagnóstico antes dos 50 anos, iniciar a mamografia anual 10 anos '
                     'antes dessa idade (não antes dos 30).', 'ACR 2023 / NCCN 2024')
    if {'cancer_mama', 'cancer_ovario'} & fam and sexo == 'feminino':
        orientar('Avaliação de risco para BRCA1/2',
                 'História familiar de câncer de mama ou ovário: aplicar ferramenta de rastreio de risco familiar; '
                 'se positiva, encaminhar para aconselhamento genético e, se indicado, teste de BRCA.',
                 'USPSTF 2019 (grau B)')
    if {'dac_precoce', 'cardiopatia'} & fam:
        orientar('História familiar de DCV prematura',
                 'Agravante de risco cardiovascular (já considerado na categoria SBC). Em risco intermediário, o escore '
                 'de cálcio coronário pode reclassificar.', 'SBC 2025')
    if 'cancer_prostata' in fam and sexo == 'masculino' and 45 <= idade < 50:
        add('PSA total, soro', 'laboratorio',
            'Pai ou irmão com câncer de próstata: oferecer rastreamento a partir dos 45 anos, com decisão compartilhada.',
            'História familiar de câncer de próstata | A partir de 45 anos', 'AUA/SUO 2023 / EAU 2024', 'B')
    if 'osteoporose_fratura' in fam and ((sexo == 'feminino' and 50 <= idade < 65) or (sexo == 'masculino' and 50 <= idade < 70)):
        add('Densitometria óssea (DEXA)', 'imagem',
            'Fratura de quadril em pai ou mãe é fator de risco maior para fratura: rastrear antes dos 65 anos '
            '(mulher pós-menopausa) e homens de 50 a 69 anos com fator de risco.',
            'Fratura de quadril em pai ou mãe | Fator de risco', 'USPSTF 2025 / BHOF 2022', 'B')
    if 'hipercolesterolemia_familiar' in fam:
        add('Colesterol total e frações, soro', 'laboratorio',
            'Hipercolesterolemia familiar em parente de 1º grau: perfil lipídico em qualquer idade (rastreio em cascata). '
            'LDL-c ≥ 190 mg/dL sugere HF.', 'Hipercolesterolemia familiar na família | Rastreio em cascata',
            'SBC 2025', 'A', 'alta')
    if 'aneurisma_aorta' in fam and 65 <= idade <= 75:
        add('Ultrassonografia com Doppler de Aorta Abdominal', 'imagem',
            'Parente de 1º grau com aneurisma de aorta abdominal: ultrassonografia uma vez entre 65 e 75 anos, '
            'em homens e mulheres.', 'História familiar de AAA | 65-75 anos | Uma vez', 'SVS 2018', 'B')
    if 'morte_subita' in fam:
        add('Eletrocardiograma de repouso', 'imagem',
            'Morte súbita antes dos 50 anos em parente de 1º grau: ECG e avaliação clínica dirigida '
            '(canalopatias, cardiomiopatias).', 'Morte súbita precoce na família', 'AHA/ACC/HRS 2017', 'B')

    # ---------------- Medicações ----------------
    if {'ieca_bra', 'espironolactona', 'tiazidico', 'diuretico_alca'} & med:
        quais = ', '.join(MEDICACOES[k]['rotulo'] for k in ('ieca_bra', 'espironolactona', 'tiazidico', 'diuretico_alca') if k in med)
        add('Potássio, soro', 'laboratorio', f'Monitorização em uso de {quais}.', f'Em uso de {quais} | Anual',
            'KDIGO 2024 / AHA 2025', 'B')
        add('Creatinina, soro', 'laboratorio', f'Função renal em uso de {quais}.', f'Em uso de {quais} | Anual',
            'KDIGO 2024 / AHA 2025', 'B')
    if {'tiazidico', 'diuretico_alca'} & med:
        add('Sódio, soro', 'laboratorio', 'Hiponatremia por diurético, sobretudo em idosos.', 'Em uso de diurético | Anual',
            'AHA 2025', 'C', 'baixa')
    if 'metformina' in med:
        add('Vitamina B12, soro', 'laboratorio',
            'Uso prolongado de metformina associa-se a deficiência de B12; dosar periodicamente, sobretudo com anemia '
            'ou neuropatia.', 'Em uso de metformina | Periódico', 'ADA 2025', 'B')
    if 'levotiroxina' in med or 'hipotireoidismo' in com:
        add('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
            'Hipotireoidismo em reposição: TSH anual com dose estável (6-8 semanas após ajuste).',
            'Hipotireoidismo / levotiroxina | Anual', 'ATA 2014', 'B')
    if 'corticoide_cronico' in med and idade >= 40:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Corticoide ≥ 2,5 mg/dia de prednisona por ≥ 3 meses: avaliar risco de fratura (densitometria e FRAX) '
            'nos primeiros 6 meses e reavaliar a cada 1-2 anos.', 'Corticoide sistêmico ≥ 3 meses', 'ACR 2022', 'B', 'alta')
    if 'litio' in med:
        for titulo, texto in (('Lítio, soro', 'Litemia'), ('Hormônio Tireoestimulante (TSH), soro', 'Função tireoidiana'),
                              ('Creatinina, soro', 'Função renal'), ('Cálcio, soro', 'Hiperparatireoidismo associado ao lítio')):
            add(titulo, 'laboratorio', f'{texto} em uso de lítio.', 'Em uso de lítio | A cada 6 meses', 'NICE CG185', 'B')
    if 'amiodarona' in med:
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Toxicidade tireoidiana e hepática da amiodarona.', 'Em uso de amiodarona | A cada 6 meses',
                'HRS 2007 (Goldschlager)', 'B')

    # ---------------- Comorbidades ----------------
    if 'masld' in com:
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Hemograma completo com plaquetas'):
            add(titulo, 'laboratorio', 'Para o cálculo do FIB-4 (idade, AST, ALT, plaquetas): estratifica risco de fibrose '
                'avançada; FIB-4 ≥ 1,3 pede elastografia.', 'MASLD | FIB-4 a cada 1-2 anos', 'AASLD 2023 / ADA 2025', 'B')
    if 'cirrose' in com:
        add('Ultrassonografia de abdome superior', 'imagem',
            'Cirrose: rastreamento de carcinoma hepatocelular com ultrassonografia a cada 6 meses (com ou sem alfafetoproteína).',
            'Cirrose | A cada 6 meses', 'AASLD 2023', 'A', 'alta')
        add('Hepatites A e B (Twinrix® ou vacinas isoladas)', 'vacina',
            'Hepatopatia crônica: vacinar contra hepatites A e B os suscetíveis, em qualquer idade.',
            'Hepatopatia crônica | Suscetíveis', SBIM, 'A', 'alta')
    if 'osteoporose' in com:
        add('Densitometria óssea (DEXA)', 'imagem', 'Seguimento de osteoporose em tratamento.', 'Osteoporose | A cada 1-2 anos',
            'BHOF 2022', 'B')
        add('25-hidroxivitamina D, soro', 'laboratorio', 'Manter 25(OH)D ≥ 30 ng/mL em osteoporose.', 'Osteoporose',
            'BHOF 2022', 'B')
    if 'gota' in com:
        add('Ácido úrico, soro', 'laboratorio', 'Tratamento por alvo: ácido úrico < 6 mg/dL.', 'Gota | Alvo < 6 mg/dL',
            'ACR 2020', 'A')

    # Vacinas por condição de risco (SBIm: comorbidade de risco em qualquer idade)
    risco_pneumo = {'cirrose', 'asma_grave', 'asplenia', 'neoplasia_ativa', 'doenca_autoimune'} & com or 'imunossupressor' in med \
        or 'corticoide_cronico' in med
    if risco_pneumo and idade < 50:
        add(PNEUMO, 'vacina', 'Dose única. Indicada em qualquer idade com comorbidade de risco para doença pneumocócica invasiva.',
            'Comorbidade de risco | Dose única | PNI: CRIE', SBIM, 'A', 'alta')
    imuno = imunossupressao_implicada(com, med)
    if imuno and 18 <= idade < 50 and not gestante:
        add(ZOSTER, 'vacina', 'Vacina inativada: 2 doses (0-2 meses; 1-2 meses de intervalo se imunossupressão). '
            'Indicada a partir de 18 anos em imunocomprometidos.', 'Imunocomprometidos ≥ 18 anos | 2 doses',
            'CDC/ACIP 2022 / ' + SBIM, 'A', 'alta')
    if 'asma_grave' in com and 18 <= idade < 60 and not gestante:
        add(VSR, 'vacina', 'Dose única para adultos com asma moderada ou grave.', 'Asma moderada/grave | Dose única', SBIM, 'B')
    if 'asplenia' in com:
        add('Meningocócica ACWY (Menactra® ou Menveo®)', 'vacina',
            'Asplenia: 2 doses com 8 semanas de intervalo e reforço a cada 5 anos.', 'Asplenia | 2 doses + reforço 5/5 anos',
            'CDC/ACIP 2025 / ' + SBIM, 'A', 'alta')
        add('Meningocócica B (Bexsero®)', 'vacina', 'Asplenia: 2 doses; reforço 1 ano depois e a cada 2-3 anos.',
            'Asplenia | 2 doses + reforços', 'CDC/ACIP 2025 / ' + SBIM, 'A', 'alta')
        add('Haemophilus influenzae tipo b (Hib)', 'vacina', 'Asplenia: dose única se não vacinado.', 'Asplenia | Dose única',
            'CDC/ACIP 2025 / ' + SBIM, 'B', 'alta')
    if imuno:
        orientar('Imunossupressão',
                 'Item marcado implica imunossupressão: a triagem de vacinas foi tratada como "Sim" e as vacinas de vírus '
                 'vivo atenuado não entram.', SBIM)
    return orient
