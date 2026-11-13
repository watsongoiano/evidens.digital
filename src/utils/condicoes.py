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
    'pre_diabetes': {'rotulo': 'Pré-diabetes', 'busca': 'glicemia de jejum alterada intolerancia'},
    'hipotireoidismo': {'rotulo': 'Hipotireoidismo', 'busca': 'tireoide hashimoto'},
    'hipertireoidismo': {'rotulo': 'Hipertireoidismo', 'busca': 'tireoide graves'},
    'masld': {'rotulo': 'Esteatose hepática (MASLD)', 'agravante': 'esteatose hepática (MASLD)',
              'busca': 'gordura no figado nafld'},
    'cirrose': {'rotulo': 'Cirrose / hepatopatia crônica', 'busca': 'figado'},
    'hepatite_b_cronica': {'rotulo': 'Hepatite B crônica', 'busca': 'figado hbv'},
    'hepatite_c': {'rotulo': 'Hepatite C', 'busca': 'figado hcv'},
    'doenca_autoimune': {'rotulo': 'Doença inflamatória autoimune (AR, lúpus, psoríase, DII)',
                         'agravante': 'doença inflamatória crônica',
                         'busca': 'artrite reumatoide les crohn retocolite espondilite'},
    'asma_grave': {'rotulo': 'Asma moderada ou grave'},
    'asplenia': {'rotulo': 'Asplenia / esplenectomia', 'busca': 'baco'},
    'anemia_falciforme': {'rotulo': 'Doença falciforme', 'busca': 'anemia falciforme hemoglobinopatia'},
    'transplante': {'rotulo': 'Transplante de órgão sólido ou de medula', 'imunossupressao': True},
    'neoplasia_ativa': {'rotulo': 'Câncer em quimio ou radioterapia', 'imunossupressao': True,
                        'busca': 'neoplasia tumor quimioterapia'},
    'cirurgia_bariatrica': {'rotulo': 'Cirurgia bariátrica prévia', 'busca': 'bypass sleeve gastroplastia'},
    'osteoporose': {'rotulo': 'Osteoporose', 'busca': 'osso fratura'},
    'gota': {'rotulo': 'Gota', 'busca': 'acido urico'},
    # Sem exame ou vacina própria no check-up: ficam registradas para a consulta.
    'fibrilacao_atrial': {'rotulo': 'Fibrilação atrial', 'busca': 'arritmia fa'},
    'apneia_sono': {'rotulo': 'Apneia obstrutiva do sono', 'busca': 'saos ronco'},
    'depressao': {'rotulo': 'Depressão'},
    'ansiedade': {'rotulo': 'Transtorno de ansiedade'},
    'epilepsia': {'rotulo': 'Epilepsia', 'busca': 'convulsao'},
    'enxaqueca': {'rotulo': 'Enxaqueca', 'busca': 'migranea cefaleia'},
    'demencia': {'rotulo': 'Demência', 'busca': 'alzheimer'},
    'parkinson': {'rotulo': 'Doença de Parkinson'},
    'hpb': {'rotulo': 'Hiperplasia prostática benigna', 'busca': 'prostata'},
    'sop': {'rotulo': 'Síndrome dos ovários policísticos', 'busca': 'sop'},
    'endometriose': {'rotulo': 'Endometriose'},
    'drge': {'rotulo': 'Doença do refluxo gastroesofágico', 'busca': 'refluxo drge'},
    'doenca_celiaca': {'rotulo': 'Doença celíaca', 'busca': 'gluten'},
    'osteoartrite': {'rotulo': 'Osteoartrite', 'busca': 'artrose'},
    'fibromialgia': {'rotulo': 'Fibromialgia'},
}

# Classes de medicação: é nelas que o motor decide exame, vacina e coerência. A tela oferece o
# princípio ativo (src/utils/medicamentos.py), que é trocado pela classe antes das regras.
MEDICACOES = {
    'ieca_bra': {'rotulo': 'IECA ou BRA', 'marca': ['anti_hipertensivos']},
    'arni': {'rotulo': 'sacubitril/valsartana', 'reduz_pa': True},
    'tiazidico': {'rotulo': 'Diurético tiazídico', 'marca': ['anti_hipertensivos']},
    'bcc': {'rotulo': 'Bloqueador de canal de cálcio', 'marca': ['anti_hipertensivos']},
    'anti_hipertensivo_outro': {'rotulo': 'Outro anti-hipertensivo', 'marca': ['anti_hipertensivos']},
    'betabloqueador': {'rotulo': 'Betabloqueador', 'reduz_pa': True},
    'espironolactona': {'rotulo': 'Espironolactona / eplerenona', 'reduz_pa': True},
    'diuretico_alca': {'rotulo': 'Diurético de alça', 'reduz_pa': True},
    'estatina': {'rotulo': 'Estatina', 'marca': ['estatinas']},
    'outro_hipolipemiante': {'rotulo': 'Ezetimiba, fibrato ou iPCSK9', 'marca': ['dislipidemia']},
    'metformina': {'rotulo': 'Metformina'},
    'insulina': {'rotulo': 'Insulina', 'marca': ['diabetes']},
    'sulfonilureia': {'rotulo': 'Sulfonilureia', 'marca': ['diabetes']},
    'idpp4_pioglitazona': {'rotulo': 'iDPP-4, pioglitazona ou acarbose', 'marca': ['diabetes']},
    'isglt2': {'rotulo': 'iSGLT2'},
    'aglp1': {'rotulo': 'Agonista de GLP-1'},
    'levotiroxina': {'rotulo': 'Levotiroxina'},
    'antitireoidiano': {'rotulo': 'Antitireoidiano'},
    'corticoide_cronico': {'rotulo': 'Corticoide sistêmico ≥ 3 meses'},
    'imunossupressor': {'rotulo': 'Imunossupressor ou imunobiológico', 'imunossupressao': True},
    'litio': {'rotulo': 'Lítio'},
    'amiodarona': {'rotulo': 'Amiodarona'},
    'varfarina': {'rotulo': 'Varfarina'},
    'doac': {'rotulo': 'Anticoagulante oral direto'},
    'antipsicotico_atipico': {'rotulo': 'Antipsicótico de 2ª geração'},
    'inibidor_aromatase': {'rotulo': 'Inibidor de aromatase'},
    'hidroxicloroquina': {'rotulo': 'Hidroxicloroquina'},
}

FAMILIA = {
    'avc_precoce': {'rotulo': 'AVC precoce (H < 55, M < 65)', 'busca': 'derrame'},
    'hipercolesterolemia_familiar': {'rotulo': 'Hipercolesterolemia familiar', 'busca': 'colesterol'},
    'morte_subita': {'rotulo': 'Morte súbita antes dos 50 anos'},
    'aneurisma_aorta': {'rotulo': 'Aneurisma de aorta abdominal'},
    'cancer_prostata': {'rotulo': 'Câncer de próstata (pai ou irmão)'},
    'cancer_endometrio': {'rotulo': 'Câncer de endométrio', 'busca': 'utero lynch'},
    'cancer_pancreas': {'rotulo': 'Câncer de pâncreas'},
    'cancer_gastrico': {'rotulo': 'Câncer gástrico', 'busca': 'estomago'},
    'melanoma': {'rotulo': 'Melanoma', 'busca': 'pele'},
    'osteoporose_fratura': {'rotulo': 'Fratura de quadril em pai ou mãe', 'busca': 'osteoporose'},
    'hemocromatose': {'rotulo': 'Hemocromatose hereditária', 'busca': 'ferro ferritina'},
    'rim_policistico': {'rotulo': 'Doença renal policística', 'busca': 'rins cistos'},
    'trombose': {'rotulo': 'Trombose venosa ou trombofilia', 'busca': 'tvp tep embolia'},
    'glaucoma': {'rotulo': 'Glaucoma', 'busca': 'olho'},
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
    if {'dac_precoce', 'cardiopatia', 'avc_precoce'} & set(familia):
        lista.append('história familiar de DCV prematura')
    return lista


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau, prioridade='media', substituir=False, esquema=None):
    extra = {'esquema_pdf': esquema} if esquema else {}
    return {**extra, 'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'referencia': referencia, 'grau_evidencia': grau, 'prioridade': prioridade, '_substituir': substituir}


def _garantir(recs, nova):
    """Acrescenta a recomendação; se o título já existe, soma o motivo e sobe a prioridade."""
    substituir = nova.pop('_substituir', False)
    for r in recs:
        if (r.get('titulo') or '').strip().lower() == nova['titulo'].lower():
            if ORDEM_PRIORIDADE.get(nova['prioridade'], 0) > ORDEM_PRIORIDADE.get(r.get('prioridade'), 0):
                r['prioridade'] = nova['prioridade']
            if substituir:
                r.update({k: nova[k] for k in ('descricao', 'subtitulo', 'referencia', 'grau_evidencia', 'esquema_pdf') if k in nova})
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
    if {'dac_precoce', 'cardiopatia', 'avc_precoce'} & fam:
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

    if 'hemocromatose' in fam:
        for titulo in ('Ferritina, soro', 'Índice de saturação de transferrina, soro'):
            add(titulo, 'laboratorio', 'Parente de 1º grau com hemocromatose hereditária: ferritina e saturação de '
                'transferrina; se alteradas, pesquisar mutações do gene HFE.',
                'Hemocromatose na família | Rastreio em cascata', 'ACG 2019 / EASL 2022', 'B')
    if 'rim_policistico' in fam:
        add('Ultrassonografia de rins e vias urinárias', 'imagem',
            'Parente de 1º grau com doença renal policística autossômica dominante: ultrassonografia renal no adulto em risco, '
            'após aconselhamento sobre as implicações do diagnóstico.', 'DRPAD na família | Adulto em risco',
            'KDIGO 2025 (DRPAD)', 'B')
    if 'cancer_endometrio' in fam:
        orientar('Câncer de endométrio na família',
                 'Com câncer colorretal ou de endométrio em parentes de 1º grau, sobretudo antes dos 50 anos, considerar '
                 'síndrome de Lynch e encaminhar para aconselhamento genético.', 'NCCN 2024 / ACG 2015')
    if 'cancer_pancreas' in fam:
        orientar('Câncer de pâncreas na família',
                 'Dois ou mais parentes de 1º grau acometidos, ou síndrome hereditária conhecida, indicam avaliação em '
                 'centro de referência (ressonância ou ecoendoscopia). Um parente isolado não indica rastreamento.',
                 'AGA 2020 / CAPS 2020')
    if 'cancer_gastrico' in fam:
        orientar('Câncer gástrico na família',
                 'Pesquisar e tratar Helicobacter pylori; endoscopia conforme sintomas e risco individual.',
                 'Maastricht VI 2022 / ACG 2024')
    if 'melanoma' in fam:
        orientar('Melanoma na família', 'Exame dermatológico de corpo inteiro periódico e orientação de fotoproteção.',
                 'AAD 2019')
    if 'trombose' in fam:
        orientar('Trombose venosa na família',
                 'Pesar o risco antes de prescrever estrogênio (anticoncepcional combinado, terapia hormonal). Pesquisa de '
                 'trombofilia não é rotina em assintomáticos.', 'ASH 2023')
    if 'glaucoma' in fam and idade >= 40:
        orientar('Glaucoma na família', 'Avaliação oftalmológica com tonometria e fundoscopia a cada 1-2 anos a partir dos 40 anos.',
                 'AAO 2020')

    # ---------------- Medicações ----------------
    renais = ('ieca_bra', 'arni', 'espironolactona', 'tiazidico', 'diuretico_alca')
    if set(renais) & med:
        quais = ', '.join(MEDICACOES[k]['rotulo'] for k in renais if k in med)
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
    if 'antitireoidiano' in med or 'hipertireoidismo' in com:
        add('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
            'Hipertireoidismo: TSH (com T4 livre) a cada 4-8 semanas até o controle e depois a cada 3-6 meses.',
            'Hipertireoidismo / antitireoidiano', 'ATA 2016', 'B')
    if 'varfarina' in med:
        add('Tempo de protrombina (TP/INR), plasma', 'laboratorio',
            'Varfarina: INR a cada 4 semanas com dose estável (até 12 semanas se INR consistentemente no alvo).',
            'Em uso de varfarina | A cada 4-12 semanas', 'CHEST 2012', 'B', 'alta')
    if 'doac' in med:
        add('Creatinina, soro', 'laboratorio',
            'Anticoagulante oral direto: função renal ao menos anual (mais frequente se ClCr < 60 mL/min ou idade ≥ 75 anos) '
            'para ajuste de dose.', 'Em uso de anticoagulante oral direto | Anual', 'EHRA 2021', 'B')
        add('Hemograma completo com plaquetas', 'laboratorio', 'Anticoagulante oral direto: hemoglobina ao menos anual.',
            'Em uso de anticoagulante oral direto | Anual', 'EHRA 2021', 'B')
    if 'antipsicotico_atipico' in med:
        for titulo in ('Glicose, soro', 'Colesterol total e frações, soro'):
            add(titulo, 'laboratorio', 'Antipsicótico de 2ª geração: monitorização metabólica (peso, glicemia e lipídios) '
                'em 12 semanas e depois anualmente.', 'Em uso de antipsicótico de 2ª geração | Anual', 'ADA/APA 2004', 'B')
    if 'inibidor_aromatase' in med:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Inibidor de aromatase: densitometria no início do tratamento e a cada 1-2 anos.',
            'Em uso de inibidor de aromatase', 'ASCO 2019', 'B')
    if 'hidroxicloroquina' in med:
        orientar('Hidroxicloroquina',
                 'Exame oftalmológico basal no primeiro ano e rastreamento anual de retinopatia após 5 anos de uso '
                 '(antes, se dose > 5 mg/kg/dia, doença renal ou uso de tamoxifeno).', 'AAO 2016')
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
    if 'pre_diabetes' in com:
        add('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'Pré-diabetes: reavaliar a glicemia ao menos uma vez por ano.',
            'Pré-diabetes | Anual', 'ADA 2025', 'B')
    if 'cirurgia_bariatrica' in com:
        for titulo in ('Hemograma completo com plaquetas', 'Ferritina, soro', 'Vitamina B12, soro', '25-hidroxivitamina D, soro'):
            add(titulo, 'laboratorio', 'Após cirurgia bariátrica: rastreamento anual de deficiências nutricionais '
                '(ferro, B12, vitamina D).', 'Cirurgia bariátrica prévia | Anual', 'ASMBS 2019', 'B')
    if 'hepatite_c' in com or 'hepatite_b_cronica' in com:
        add('Hepatites A e B (Twinrix® ou vacinas isoladas)', 'vacina',
            'Hepatite viral crônica: vacinar os suscetíveis contra hepatite A (e contra hepatite B, na hepatite C).',
            'Hepatopatia crônica | Suscetíveis', SBIM, 'A', 'alta')
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
    risco_pneumo = {'cirrose', 'asma_grave', 'asplenia', 'anemia_falciforme', 'transplante', 'neoplasia_ativa',
                    'doenca_autoimune', 'hepatite_b_cronica', 'hepatite_c'} & com or 'imunossupressor' in med \
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
    if {'asplenia', 'anemia_falciforme'} & com:
        # Asplenia anatômica ou funcional (doença falciforme). Esquema de risco substitui o de rotina na tela e no PDF (esquema_pdf)
        add('Meningocócica ACWY (Menactra® ou Menveo®)', 'vacina',
            'Asplenia: 2 doses com 8 semanas de intervalo e reforço a cada 5 anos.', 'Asplenia | 2 doses + reforço 5/5 anos',
            'CDC/ACIP 2025 / ' + SBIM, 'A', 'alta', substituir=True, esquema='asplenia')
        add('Meningocócica B (Bexsero®)', 'vacina', 'Asplenia: 2 doses com 1 mês de intervalo; reforço 1 ano depois e a cada 2-3 anos.',
            'Asplenia | 2 doses + reforços', 'CDC/ACIP 2025 / ' + SBIM, 'A', 'alta', substituir=True, esquema='asplenia')
        add('Haemophilus influenzae tipo b (Hib)', 'vacina', 'Asplenia: dose única se não vacinado.', 'Asplenia | Dose única',
            'CDC/ACIP 2025 / ' + SBIM, 'B', 'alta', substituir=True, esquema='asplenia')
    if imuno:
        orientar('Imunossupressão',
                 'Item marcado implica imunossupressão: a triagem de vacinas foi tratada como "Sim" e as vacinas de vírus '
                 'vivo atenuado não entram.', SBIM)
    return orient
