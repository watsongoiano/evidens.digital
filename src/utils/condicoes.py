"""Listas de comorbidades, medicações e história familiar e o que cada item dispara.

Substituem os campos de texto livre: cada item escolhido na lista suspensa tem
efeito definido (exame, vacina, orientação, agravante de risco ou resposta da
triagem de vacinas), com a fonte ao lado. As chaves vão nos mesmos campos de
lista do formulário (``comorbidades``, ``medicacoes``, ``historia_familiar``).

``marca`` diz quais caixas o item implica (as mesmas regras de coerência da tela).
``talvez`` diz quais caixas o item NÃO marca sozinho, porque tem outras indicações frequentes
(betabloqueador na IC, iSGLT2 na IC e na DRC, agonista de GLP-1 na obesidade): a tela avisa e o
médico marca se for o caso.
"""
from __future__ import annotations

ORDEM_PRIORIDADE = {'baixa': 0, 'media': 1, 'alta': 2}

# Tipos de diabetes pela classificação da ADA (Standards of Care 2026, seção 2): tipo 1, tipo 2,
# tipos específicos por outras causas (monogênico, doença do pâncreas exócrino, induzido por
# medicamento ou pós-transplante) e gestacional. O tipo 2 é caixa fixa na tela (valor "diabetes");
# o tipo 1 também; os demais ficam na lista. O gestacional não é diabetes fora da gestação: o
# histórico entra como fator de risco e o da gestação atual, nos dados do pré-natal.
TIPOS_DE_DIABETES = ('diabetes', 'diabetes_tipo_2', 'diabetes_tipo_1', 'diabetes_monogenico', 'diabetes_pancreatico',
                     'diabetes_medicamentoso')

COMORBIDADES = {
    'diabetes_monogenico': {'rotulo': 'Diabetes monogênico (MODY, neonatal)', 'busca': 'mody tipo de diabetes'},
    'diabetes_pancreatico': {'rotulo': 'Diabetes por doença do pâncreas (pancreatite, fibrose cística)',
                             'busca': 'tipo 3c pancreatogenico pancreatectomia tipo de diabetes'},
    'diabetes_medicamentoso': {'rotulo': 'Diabetes induzido por medicamento ou pós-transplante',
                               'busca': 'corticoide antirretroviral nodat ptdm tipo de diabetes'},
    'diabetes_gestacional_previo': {'rotulo': 'Diabetes gestacional em gestação anterior', 'busca': 'dmg previo historia'},
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
    'arni': {'rotulo': 'sacubitril/valsartana', 'reduz_pa': True, 'talvez': ['hipertensao']},
    'tiazidico': {'rotulo': 'Diurético tiazídico', 'marca': ['anti_hipertensivos']},
    'bcc': {'rotulo': 'Bloqueador de canal de cálcio', 'marca': ['anti_hipertensivos']},
    'anti_hipertensivo_outro': {'rotulo': 'Outro anti-hipertensivo', 'marca': ['anti_hipertensivos']},
    'betabloqueador': {'rotulo': 'Betabloqueador', 'reduz_pa': True, 'talvez': ['hipertensao']},
    # atenolol, metoprolol e nebivolol: uso principal é hipertensão
    'betabloqueador_has': {'rotulo': 'Betabloqueador', 'marca': ['anti_hipertensivos']},
    'espironolactona': {'rotulo': 'Espironolactona / eplerenona', 'reduz_pa': True, 'talvez': ['hipertensao']},
    'diuretico_alca': {'rotulo': 'Diurético de alça', 'reduz_pa': True, 'talvez': ['hipertensao']},
    'estatina': {'rotulo': 'Estatina', 'marca': ['estatinas']},
    'outro_hipolipemiante': {'rotulo': 'Ezetimiba, fibrato ou iPCSK9', 'marca': ['dislipidemia']},
    'metformina': {'rotulo': 'Metformina', 'marca': ['diabetes']},
    # Insulina se usa no tipo 1, no tipo 2, no gestacional e nos outros tipos: indica diabetes, mas não marca um tipo.
    'insulina': {'rotulo': 'Insulina'},
    'sulfonilureia': {'rotulo': 'Sulfonilureia', 'marca': ['diabetes']},
    'idpp4_pioglitazona': {'rotulo': 'iDPP-4, pioglitazona ou acarbose', 'marca': ['diabetes']},
    'isglt2': {'rotulo': 'iSGLT2', 'talvez': ['diabetes']},
    'aglp1': {'rotulo': 'Agonista de GLP-1', 'talvez': ['diabetes']},
    'levotiroxina': {'rotulo': 'Levotiroxina'},
    'antitireoidiano': {'rotulo': 'Antitireoidiano'},
    'corticoide_sistemico': {'rotulo': 'Corticoide sistêmico'},
    'corticoide_cronico': {'rotulo': 'Corticoide sistêmico ≥ 3 meses'},
    'imunossupressor': {'rotulo': 'Imunossupressor ou imunobiológico', 'imunossupressao': True},
    # Definidas pela dose e pela duração (src/utils/doses.py)
    'corticoide_imunossupressor': {'rotulo': 'Corticoide em dose imunossupressora', 'imunossupressao': True},
    'rastreio_tb_latente': {'rotulo': 'Corticoide ≥ 15 mg/dia por ≥ 1 mês'},
    'metotrexato': {'rotulo': 'Metotrexato'},
    'azatioprina': {'rotulo': 'Azatioprina'},
    'leflunomida': {'rotulo': 'Leflunomida'},
    'inibidor_calcineurina': {'rotulo': 'Ciclosporina ou tacrolimo'},
    'biologico': {'rotulo': 'Imunobiológico ou inibidor de JAK'},
    'bisfosfonato_longo': {'rotulo': 'Bisfosfonato por 5 anos ou mais'},
    'litio': {'rotulo': 'Lítio'},
    'amiodarona': {'rotulo': 'Amiodarona'},
    'varfarina': {'rotulo': 'Varfarina'},
    'doac': {'rotulo': 'Anticoagulante oral direto'},
    'antipsicotico_atipico': {'rotulo': 'Antipsicótico de 2ª geração'},
    'inibidor_aromatase': {'rotulo': 'Inibidor de aromatase'},
    'hidroxicloroquina': {'rotulo': 'Hidroxicloroquina'},
}

HEREDITARIAS = 'Síndromes e doenças hereditárias'
FAMILIA = {
    # Com rastreamento próprio para o parente de 1º grau (portador confirmado ou ainda não testado)
    'brca': {'rotulo': 'Mutação BRCA1 / BRCA2', 'grupo': HEREDITARIAS, 'busca': 'mama ovario hboc hereditario'},
    'li_fraumeni': {'rotulo': 'Síndrome de Li-Fraumeni (TP53)', 'grupo': HEREDITARIAS, 'busca': 'sarcoma'},
    'lynch': {'rotulo': 'Síndrome de Lynch (MLH1, MSH2, MSH6, PMS2)', 'grupo': HEREDITARIAS,
              'busca': 'hnpcc colorretal endometrio hereditario'},
    'paf': {'rotulo': 'Polipose adenomatosa familiar (APC)', 'grupo': HEREDITARIAS, 'busca': 'paf polipos colorretal'},
    'cdh1': {'rotulo': 'Câncer gástrico difuso hereditário (CDH1)', 'grupo': HEREDITARIAS, 'busca': 'estomago'},
    'cowden': {'rotulo': 'Síndrome de Cowden (PTEN)', 'grupo': HEREDITARIAS, 'busca': 'hamartoma'},
    'nem1': {'rotulo': 'Neoplasia endócrina múltipla tipo 1 (MEN1)', 'grupo': HEREDITARIAS,
             'busca': 'nem1 paratireoide hipofise'},
    'nem2': {'rotulo': 'Neoplasia endócrina múltipla tipo 2 / carcinoma medular de tireoide (RET)',
             'grupo': HEREDITARIAS, 'busca': 'nem2 men2 feocromocitoma'},
    'hipercolesterolemia_familiar': {'rotulo': 'Hipercolesterolemia familiar', 'grupo': HEREDITARIAS,
                                     'busca': 'colesterol ldl'},
    'cardiomiopatia_hipertrofica': {'rotulo': 'Cardiomiopatia hipertrófica', 'grupo': HEREDITARIAS, 'busca': 'cmh coracao'},
    'cardiomiopatia_dilatada': {'rotulo': 'Cardiomiopatia dilatada familiar', 'grupo': HEREDITARIAS, 'busca': 'coracao'},
    'canalopatia': {'rotulo': 'Síndrome do QT longo, Brugada ou outra canalopatia', 'grupo': HEREDITARIAS,
                    'busca': 'arritmia hereditaria'},
    'aorta_toracica': {'rotulo': 'Aneurisma ou dissecção de aorta torácica / síndrome de Marfan', 'grupo': HEREDITARIAS},
    'aneurisma_cerebral': {'rotulo': 'Aneurisma cerebral (2 ou mais parentes de 1º grau)', 'grupo': HEREDITARIAS,
                           'busca': 'hemorragia subaracnoide'},
    'hemocromatose': {'rotulo': 'Hemocromatose hereditária', 'grupo': HEREDITARIAS, 'busca': 'ferro ferritina hfe'},
    'rim_policistico': {'rotulo': 'Doença renal policística', 'grupo': HEREDITARIAS, 'busca': 'rins cistos drpad'},
    'alfa1': {'rotulo': 'Deficiência de alfa-1 antitripsina', 'grupo': HEREDITARIAS, 'busca': 'enfisema'},
    'doenca_celiaca_familiar': {'rotulo': 'Doença celíaca', 'grupo': HEREDITARIAS, 'busca': 'gluten'},
    # Outras condições que mudam idade de início ou indicação
    'avc_precoce': {'rotulo': 'AVC precoce (H < 55, M < 65)', 'busca': 'derrame'},
    'morte_subita': {'rotulo': 'Morte súbita antes dos 50 anos'},
    'aneurisma_aorta': {'rotulo': 'Aneurisma de aorta abdominal'},
    'cancer_prostata': {'rotulo': 'Câncer de próstata (pai ou irmão)'},
    'cancer_endometrio': {'rotulo': 'Câncer de endométrio', 'busca': 'utero'},
    'cancer_pancreas': {'rotulo': 'Câncer de pâncreas'},
    'cancer_gastrico': {'rotulo': 'Câncer gástrico', 'busca': 'estomago'},
    'melanoma': {'rotulo': 'Melanoma', 'busca': 'pele'},
    'osteoporose_fratura': {'rotulo': 'Fratura de quadril em pai ou mãe', 'busca': 'osteoporose'},
    'trombose': {'rotulo': 'Trombose venosa ou trombofilia', 'busca': 'tvp tep embolia'},
    'glaucoma': {'rotulo': 'Glaucoma', 'busca': 'olho'},
}
# Marcadas por chip na tela (e "cardiopatia" é o valor antigo de DAC precoce).
FAMILIA_CHIPS = ('cancer_mama', 'cancer_colorretal', 'cancer_ovario', 'diabetes', 'dac_precoce', 'cardiopatia')

PNEUMO = 'Pneumocócica conjugada 20-valente (Prevenar 20®)'
ZOSTER = 'Herpes Zóster (Shingrix®)'
VSR = 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'
SBIM = 'SBIm 2026/2027'
CGH_CORTICOIDE = 'CGH 2025 (Feuerstein)'
SPARLING = 'Drugs Aging 2024 (Sparling)'


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
        orientar('Hipercolesterolemia familiar na família',
                 'Aplicar os critérios da Dutch Lipid Clinic Network; teste genético em cascata quando a variante familiar é '
                 'conhecida. Na HF confirmada, o risco não se estima por escore: tratar como alto risco.', 'SBC 2025')
    if 'aneurisma_aorta' in fam and 65 <= idade <= 75:
        add('Ultrassonografia com Doppler de Aorta Abdominal', 'imagem',
            'Parente de 1º grau com aneurisma de aorta abdominal: ultrassonografia uma vez entre 65 e 75 anos, '
            'em homens e mulheres.', 'História familiar de AAA | 65-75 anos | Uma vez', 'SVS 2018', 'B')
    if 'morte_subita' in fam:
        add('Eletrocardiograma de repouso', 'imagem',
            'Morte súbita antes dos 50 anos em parente de 1º grau: ECG e avaliação clínica dirigida '
            '(canalopatias, cardiomiopatias).', 'Morte súbita precoce na família', 'AHA/ACC/HRS 2017', 'B')

    # ---- Síndromes hereditárias: parente de 1º grau portador (paciente portador ou ainda não testado) ----
    CASCATA = ('Oferecer aconselhamento e teste genético em cascata; os exames listados valem para o portador '
               'confirmado e para o parente de 1º grau ainda não testado.')
    QUEM = 'Portador ou parente de 1º grau não testado'
    mulher, homem = sexo == 'feminino', sexo == 'masculino'

    def rm_mamas(inicio, ref, motivo):
        if mulher and inicio <= idade <= 75:
            add('Ressonância magnética de mamas', 'imagem',
                f'{motivo}: ressonância magnética de mamas anual a partir de {inicio} anos, alternada ou associada à mamografia.',
                f'{motivo} | {QUEM} | Anual a partir de {inicio} anos', ref, 'A', 'alta')

    def mamografia_anual(inicio, ref, motivo):
        if mulher and inicio <= idade <= 75:
            add('Mamografia Digital - Bilateral', 'imagem', f'{motivo}: mamografia anual a partir de {inicio} anos.',
                f'{motivo} | {QUEM} | Anual a partir de {inicio} anos', ref, 'A', 'alta', substituir=True)

    def colonoscopia(inicio, intervalo, ref, motivo, grau='A'):
        if idade >= inicio:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                f'{motivo}: colonoscopia {intervalo}, a partir de {inicio} anos.',
                f'{motivo} | {QUEM} | {intervalo.capitalize()}', ref, grau, 'alta', substituir=True)

    if 'brca' in fam:
        rm_mamas(25, 'NCCN 2025 / ACS 2007', 'BRCA1/2 na família')
        mamografia_anual(30, 'NCCN 2025', 'BRCA1/2 na família')
        if homem and idade >= 40:
            add('PSA total, soro', 'laboratorio',
                'BRCA1/2 na família: rastreamento de câncer de próstata a partir dos 40 anos no portador de BRCA2 '
                '(considerar em BRCA1).', f'BRCA1/2 na família | {QUEM} | A partir de 40 anos', 'NCCN 2025', 'B')
        orientar('Mutação BRCA1/2 na família',
                 CASCATA + ' Portadoras: discutir salpingo-ooforectomia redutora de risco (35-40 anos em BRCA1, 40-45 em '
                 'BRCA2) e mastectomia redutora. Homens portadores: exame clínico das mamas a partir de 35 anos. '
                 'Pâncreas: rastrear o portador que também tem caso de câncer de pâncreas na família.', 'NCCN 2025')
    if 'li_fraumeni' in fam:
        rm_mamas(20, 'NCCN 2025 / Kratz 2017', 'Li-Fraumeni na família')
        for titulo in ('Ressonância magnética de corpo inteiro', 'Ressonância magnética de crânio'):
            add(titulo, 'imagem', 'Li-Fraumeni (protocolo de Toronto): ressonância de corpo inteiro e de crânio anuais, '
                'sem contraste quando possível.', f'Li-Fraumeni na família | {QUEM} | Anual', 'NCCN 2025 / Kratz 2017', 'B', 'alta')
        colonoscopia(25, 'a cada 2-5 anos', 'NCCN 2025 / Kratz 2017', 'Li-Fraumeni na família', 'B')
        orientar('Síndrome de Li-Fraumeni na família',
                 CASCATA + ' Exame físico completo e neurológico a cada 6-12 meses, exame dermatológico anual e '
                 'endoscopia digestiva alta junto com a colonoscopia. Evitar radiação ionizante sempre que houver alternativa.',
                 'NCCN 2025 / Kratz 2017')
    if 'lynch' in fam:
        colonoscopia(20, 'a cada 1-2 anos', 'NCCN 2025 / ACG 2015', 'Síndrome de Lynch na família')
        if idade >= 30:
            add('Endoscopia digestiva alta', 'imagem',
                'Síndrome de Lynch: endoscopia digestiva alta com biópsias e pesquisa de H. pylori a cada 2-4 anos, a partir de 30-40 anos.',
                f'Síndrome de Lynch na família | {QUEM} | A cada 2-4 anos', 'NCCN 2025', 'B')
        orientar('Síndrome de Lynch na família',
                 CASCATA + ' Início da colonoscopia aos 20-25 anos em MLH1/MSH2 e aos 30-35 em MSH6/PMS2. Mulheres: '
                 'orientar sobre sangramento uterino anormal, considerar biópsia de endométrio a cada 1-2 anos a partir de '
                 '30-35 anos e discutir histerectomia com salpingo-ooforectomia após prole constituída.', 'NCCN 2025 / ACG 2015')
    if 'paf' in fam:
        colonoscopia(18, 'anual', 'NCCN 2025 / ACG 2015', 'Polipose adenomatosa familiar')
        if idade >= 20:
            add('Endoscopia digestiva alta', 'imagem',
                'Polipose adenomatosa familiar: endoscopia digestiva alta com avaliação da papila a partir de 20-25 anos; '
                'intervalo conforme o estágio de Spigelman.', f'PAF na família | {QUEM}', 'NCCN 2025 / ACG 2015', 'B')
        orientar('Polipose adenomatosa familiar na família',
                 CASCATA + ' No portador, a colonoscopia começa aos 10-15 anos; discutir colectomia conforme a carga de pólipos. '
                 'Considerar ultrassonografia de tireoide.', 'NCCN 2025 / ACG 2015')
    if 'cdh1' in fam:
        add('Endoscopia digestiva alta', 'imagem',
            'CDH1: endoscopia digestiva alta anual com múltiplas biópsias (protocolo de Cambridge) para quem adia a gastrectomia.',
            f'CDH1 na família | {QUEM} | Anual', 'IGCLC 2020 / NCCN 2025', 'B', 'alta')
        rm_mamas(30, 'IGCLC 2020 / NCCN 2025', 'CDH1 na família')
        orientar('Câncer gástrico difuso hereditário na família',
                 CASCATA + ' No portador de variante patogênica de CDH1, discutir gastrectomia total profilática entre 18 e 40 anos.',
                 'IGCLC 2020 / NCCN 2025')
    if 'cowden' in fam:
        rm_mamas(30, 'NCCN 2025', 'Síndrome de Cowden na família')
        mamografia_anual(30, 'NCCN 2025', 'Síndrome de Cowden na família')
        add('Ultrassonografia de tireoide', 'imagem', 'Síndrome de Cowden (PTEN): ultrassonografia de tireoide anual.',
            f'Síndrome de Cowden na família | {QUEM} | Anual', 'NCCN 2025', 'B')
        colonoscopia(35, 'a cada 5 anos', 'NCCN 2025', 'Síndrome de Cowden na família', 'B')
        if idade >= 40:
            add('Ultrassonografia de rins e vias urinárias', 'imagem',
                'Síndrome de Cowden (PTEN): ultrassonografia renal a cada 1-2 anos a partir dos 40 anos.',
                f'Síndrome de Cowden na família | {QUEM} | A cada 1-2 anos', 'NCCN 2025', 'C')
        orientar('Síndrome de Cowden na família',
                 CASCATA + ' Mulheres: orientar sobre sangramento uterino anormal e considerar rastreamento de endométrio a partir de 35 anos.',
                 'NCCN 2025')
    if 'nem1' in fam:
        for titulo in ('Cálcio iônico, soro', 'Paratormônio (PTH), soro', 'Prolactina, soro'):
            add(titulo, 'laboratorio', 'NEM1: cálcio, PTH e prolactina anuais.', f'NEM1 na família | {QUEM} | Anual',
                'Endocrine Society 2012', 'B')
        orientar('Neoplasia endócrina múltipla tipo 1 na família',
                 CASCATA + ' No portador: gastrina e imagem pancreática anuais; ressonância de hipófise a cada 3-5 anos.',
                 'Endocrine Society 2012')
    if 'nem2' in fam:
        for titulo in ('Calcitonina, soro', 'Metanefrinas, plasma ou urina de 24h', 'Cálcio iônico, soro'):
            add(titulo, 'laboratorio', 'NEM2 / carcinoma medular de tireoide familiar: calcitonina, metanefrinas e cálcio anuais.',
                f'NEM2 na família | {QUEM} | Anual', 'ATA 2015', 'B', 'alta')
        add('Ultrassonografia de tireoide', 'imagem', 'NEM2 / carcinoma medular de tireoide familiar: ultrassonografia cervical.',
            f'NEM2 na família | {QUEM}', 'ATA 2015', 'B')
        orientar('NEM2 / carcinoma medular de tireoide na família',
                 CASCATA + ' O teste do gene RET define a conduta: no portador, tireoidectomia profilática na idade indicada pelo '
                 'risco da mutação.', 'ATA 2015')
    if 'cardiomiopatia_hipertrofica' in fam or 'cardiomiopatia_dilatada' in fam:
        qual = 'cardiomiopatia hipertrófica' if 'cardiomiopatia_hipertrofica' in fam else 'cardiomiopatia dilatada familiar'
        ref = 'AHA/ACC 2024' if 'cardiomiopatia_hipertrofica' in fam else 'AHA/ACC/HFSA 2022'
        for titulo in ('Eletrocardiograma de repouso', 'Ecocardiograma transtorácico'):
            add(titulo, 'imagem', f'Parente de 1º grau com {qual}: ECG e ecocardiograma a cada 3-5 anos no adulto '
                '(antes, se surgirem sintomas).', f'{qual.capitalize()} na família | A cada 3-5 anos', ref, 'B', 'alta')
        orientar(f'{qual.capitalize()} na família', 'Oferecer aconselhamento e teste genético em cascata quando a variante '
                 'familiar é conhecida; teste negativo para a variante dispensa o seguimento.', ref)
    if 'canalopatia' in fam:
        add('Eletrocardiograma de repouso', 'imagem',
            'Parente de 1º grau com QT longo, Brugada ou outra canalopatia: ECG de 12 derivações e avaliação com cardiologista.',
            'Canalopatia na família', 'HRS/EHRA/APHRS 2013', 'B', 'alta')
        orientar('Canalopatia na família', 'Oferecer teste genético em cascata quando a variante familiar é conhecida; '
                 'conforme a síndrome, teste ergométrico ou Holter. Revisar fármacos que prolongam o QT.', 'HRS/EHRA/APHRS 2013')
    if 'aorta_toracica' in fam:
        add('Ecocardiograma transtorácico', 'imagem',
            'Parente de 1º grau com aneurisma ou dissecção de aorta torácica (ou síndrome de Marfan): imagem da raiz da aorta '
            'e da aorta ascendente.', 'Doença da aorta torácica na família', 'ACC/AHA 2022', 'B', 'alta')
        orientar('Doença da aorta torácica na família', 'Considerar teste genético quando há síndrome ou variante conhecida; '
                 'se a aorta ascendente não for bem vista ao ecocardiograma, angiotomografia ou angiorressonância.', 'ACC/AHA 2022')
    if 'aneurisma_cerebral' in fam:
        add('Angiorressonância de crânio', 'imagem',
            'Dois ou mais parentes de 1º grau com aneurisma cerebral ou hemorragia subaracnoide: rastreamento não invasivo '
            '(angiorressonância ou angiotomografia).', 'Aneurisma cerebral em 2 ou mais parentes de 1º grau', 'AHA/ASA 2015', 'B')
    if 'alfa1' in fam:
        add('Alfa-1 antitripsina, soro', 'laboratorio',
            'Parente de 1º grau com deficiência de alfa-1 antitripsina: dosagem sérica (e genotipagem se baixa).',
            'Deficiência de alfa-1 antitripsina na família', 'ATS/ERS 2003', 'B')
    if 'doenca_celiaca_familiar' in fam:
        for titulo in ('Anticorpo antitransglutaminase tecidual IgA, soro', 'Imunoglobulina A (IgA), soro'):
            add(titulo, 'laboratorio', 'Parente de 1º grau com doença celíaca: sorologia (antitransglutaminase IgA com IgA total), '
                'em dieta com glúten.', 'Doença celíaca na família', 'ACG 2023', 'B')
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
    if 'hidroxicloroquina' in med and 'hidroxicloroquina_rastreio' not in med:
        orientar('Hidroxicloroquina',
                 'Exame oftalmológico basal no primeiro ano e rastreamento anual de retinopatia após 5 anos de uso '
                 '(antes, se dose > 5 mg/kg/dia, doença renal ou uso de tamoxifeno).', 'AAO 2016')
    if 'levotiroxina' in med or 'hipotireoidismo' in com:
        add('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
            'Hipotireoidismo em reposição: TSH anual com dose estável (6-8 semanas após ajuste).',
            'Hipotireoidismo / levotiroxina | Anual', 'ATA 2014', 'B')
    # Corticoide sistêmico em uso, a partir da dose baixa: avaliação basal e monitorização valem para todos.
    # A dose e a duração (src/utils/doses.py) só mudam o que depende delas: densitometria e imagem da coluna
    # a partir de 3 meses de uso (≥ 2,5 mg/dia de prednisona) e, na dose imunossupressora (≥ 20 mg/dia por
    # ≥ 2 semanas), vacinas de vírus vivo fora e VSR indicada.
    # Fontes: Feuerstein et al., Clin Gastroenterol Hepatol 2025;23:2068-82 (monitorização durante o uso);
    # Sparling & Butler, Drugs Aging 2024;41:795-808 (avaliação basal antes do corticoide oral); ACR 2022 (osso).
    cronico, imunossupressor = 'corticoide_cronico' in med, 'corticoide_imunossupressor' in med
    corticoide = cronico or imunossupressor or 'corticoide_sistemico' in med
    if corticoide:
        quem = ('Corticoide em dose imunossupressora' if imunossupressor else
                'Corticoide sistêmico ≥ 3 meses' if cronico else 'Corticoide sistêmico')
        for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
            add(titulo, 'laboratorio',
                'Corticoide sistêmico: glicemia e HbA1c antes de iniciar e de rotina durante o uso (hiperglicemia e diabetes '
                'induzidos por corticoide).', f'{quem} | Basal e periódico', CGH_CORTICOIDE + ' / ' + SPARLING, 'B', 'alta')
        add('Colesterol total e frações, soro', 'laboratorio',
            'Corticoide sistêmico: perfil lipídico basal e de rotina durante o uso.', f'{quem} | Basal e periódico',
            CGH_CORTICOIDE + ' / ' + SPARLING, 'B')
        add('MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)', 'imagem',
            'Corticoide sistêmico: acompanhar a pressão arterial de rotina durante o uso (hipertensão induzida por corticoide).',
            f'{quem} | Durante o uso', CGH_CORTICOIDE, 'B')
        add('Avaliação oftalmológica com tonometria e fundoscopia', 'imagem',
            'Corticoide sistêmico: exame oftalmológico periódico para catarata e glaucoma.', f'{quem} | Periódico',
            CGH_CORTICOIDE + ' / ' + SPARLING, 'B')
        add('25-hidroxivitamina D, soro', 'laboratorio',
            'Corticoide sistêmico: manter vitamina D adequada (prevenção de osteoporose induzida por corticoide).',
            f'{quem} | Basal', 'ACR 2022 / ' + SPARLING, 'B')
        painel = ('Hemograma completo com plaquetas', 'Albumina, soro', 'Creatinina, soro', 'Ureia, soro', 'Sódio, soro',
                  'Potássio, soro', 'Cálcio iônico, soro', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro',
                  'Fosfatase alcalina, soro', 'Bilirrubinas totais e frações, soro')
        for titulo in painel:
            add(titulo, 'laboratorio',
                'Corticoide sistêmico: avaliação laboratorial basal (hemograma, albumina e painel metabólico: função renal, '
                'eletrólitos, cálcio e perfil hepático).', f'{quem} | Basal', SPARLING, 'C')
    if cronico:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Corticoide ≥ 2,5 mg/dia de prednisona por mais de 3 meses: densitometria nos primeiros 6 meses de uso, em qualquer '
            'idade adulta, repetida a cada 2-3 anos (a cada 1-3 anos a partir dos 40 anos sem tratamento para osteoporose). '
            'Calcular o FRAX a partir dos 40 anos.', 'Corticoide sistêmico ≥ 3 meses | Até 6 meses do início',
            'ACR 2022 / ' + CGH_CORTICOIDE, 'B', 'alta')
        if idade >= 40:
            add('Radiografia de coluna torácica e lombar (perfil)', 'imagem',
                'Corticoide por mais de 3 meses a partir dos 40 anos: imagem da coluna para fratura vertebral, que muda a '
                'classificação de risco mesmo com densitometria normal.', 'Corticoide sistêmico ≥ 3 meses | Avaliação de fratura',
                'ACR 2022 / ' + SPARLING, 'B')
    if imunossupressor and 18 <= idade < 60 and not gestante:
        add(VSR, 'vacina', 'Dose única para adultos imunossuprimidos, incluído o uso de corticoide em dose imunossupressora.',
            'Corticoide em dose imunossupressora | Dose única', SBIM + ' / ' + CGH_CORTICOIDE, 'B')
    if corticoide or 'biologico' in med:
        motivo = ' e '.join(x for x, sim in (('corticoide sistêmico', corticoide),
                                             (MEDICACOES['biologico']['rotulo'].lower(), 'biologico' in med)) if sim)
        imunossuprime = imunossupressor or 'rastreio_tb_latente' in med or 'biologico' in med
        add('Prova tuberculínica (PPD) ou IGRA', 'laboratorio',
            f'Rastreamento de tuberculose latente em uso de {motivo}; com resultado positivo e doença ativa afastada, tratar.',
            ('Imunossupressão' if imunossuprime else 'Corticoide sistêmico') + ' | Antes ou no início do tratamento', 'MS 2019 (Manual de Tuberculose) / ACR 2022' + (' / ' + SPARLING if corticoide else ''), 'A', 'alta')
    if 'biologico' in med:
        for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro'):
            add(titulo, 'laboratorio', 'Imunobiológico ou inibidor de JAK: rastrear hepatite B antes do tratamento '
                '(risco de reativação, sobretudo com rituximabe).', 'Imunobiológico | Antes do tratamento', 'ACR 2022 / AASLD 2018', 'A', 'alta')
    for classe, exames, quando, ref in (
            ('metotrexato', ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro',
                             'Alanina aminotransferase, soro', 'Creatinina, soro'), 'A cada 8-12 semanas', 'ACR 2021'),
            ('azatioprina', ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro',
                             'Alanina aminotransferase, soro'), 'A cada 12 semanas', 'BSR 2017'),
            ('leflunomida', ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro',
                             'Alanina aminotransferase, soro'), 'A cada 8-12 semanas', 'ACR 2021'),
            ('inibidor_calcineurina', ('Creatinina, soro', 'Potássio, soro', 'Magnésio, soro'), 'A cada 1-3 meses', 'KDIGO 2009 (transplante)')):
        if classe in med:
            for titulo in exames:
                add(titulo, 'laboratorio', f'Monitorização de toxicidade em uso de {MEDICACOES[classe]["rotulo"].lower()}.',
                    f'Em uso de {MEDICACOES[classe]["rotulo"].lower()} | {quando}', ref, 'B')
    if 'bisfosfonato_longo' in med:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Bisfosfonato por 5 anos (oral) ou 3 anos (ácido zoledrônico): densitometria para decidir entre pausa e continuidade.',
            'Bisfosfonato por tempo prolongado | Reavaliação', 'ASBMR 2016', 'B')
    if 'litio' in med:
        for titulo, texto in (('Lítio, soro', 'Litemia'), ('Hormônio Tireoestimulante (TSH), soro', 'Função tireoidiana'),
                              ('Creatinina, soro', 'Função renal'), ('Cálcio iônico, soro', 'Hiperparatireoidismo associado ao lítio')):
            add(titulo, 'laboratorio', f'{texto} em uso de lítio.', 'Em uso de lítio | A cada 6 meses', 'NICE CG185', 'B')
    if 'amiodarona' in med:
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Toxicidade tireoidiana e hepática da amiodarona.', 'Em uso de amiodarona | A cada 6 meses',
                'HRS 2007 (Goldschlager)', 'B')

    # ---------------- Comorbidades ----------------
    diabetico = bool(set(TIPOS_DE_DIABETES) & com)
    if 'insulina' in med and not diabetico:
        orientar('Insulina em uso: informe o tipo de diabetes',
                 'A insulina é usada no diabetes tipo 1, no tipo 2, no gestacional e em outros tipos; por isso não marca um tipo '
                 'sozinha. As recomendações foram montadas como para uma pessoa com diabetes. Marque o tipo para refinar '
                 '(por exemplo, TSH no tipo 1).', 'ADA 2026')
    if 'diabetes_gestacional_previo' in com and sexo == 'feminino' and not gestante and not diabetico and 'insulina' not in med:
        for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
            add(titulo, 'laboratorio',
                'Diabetes gestacional em gestação anterior: rastrear pré-diabetes e diabetes por toda a vida, pelo menos a cada 3 anos.',
                'Diabetes gestacional prévio | Pelo menos a cada 3 anos', 'ADA 2026', 'B', 'alta')
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
                    'doenca_autoimune', 'hepatite_b_cronica', 'hepatite_c'} & com or {'imunossupressor', 'corticoide_cronico', 'corticoide_imunossupressor'} & med
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
