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
    'nodulo_tireoide': {'rotulo': 'Nódulo de tireoide', 'busca': 'tireoidiano bocio nodular cisto tirads paaf'},
    'hiperparatireoidismo_primario': {'rotulo': 'Hiperparatireoidismo primário', 'busca': 'paratireoide pth calcio hipercalcemia hptp'},
    'incidentaloma_adrenal': {'rotulo': 'Incidentaloma adrenal', 'busca': 'nodulo de suprarrenal adenoma adrenal massa adrenal'},
    'hipogonadismo_masculino': {'rotulo': 'Hipogonadismo masculino', 'busca': 'testosterona baixa deficiencia androgenica'},
    'hiperprolactinemia': {'rotulo': 'Hiperprolactinemia ou prolactinoma',
                           'busca': 'prolactina alta galactorreia adenoma de hipofise cabergolina'},
    'masld': {'rotulo': 'Esteatose hepática (MASLD)', 'agravante': 'esteatose hepática (MASLD)',
              'busca': 'gordura no figado nafld'},
    'cirrose': {'rotulo': 'Cirrose / hepatopatia crônica', 'busca': 'figado'},
    'hepatite_b_cronica': {'rotulo': 'Hepatite B crônica', 'busca': 'figado hbv'},
    'hepatite_c': {'rotulo': 'Hepatite C', 'busca': 'figado hcv'},
    # Doenças inflamatórias imunomediadas: cada uma com o seu acompanhamento (antes eram um item só).
    'artrite_reumatoide': {'rotulo': 'Artrite reumatoide', 'agravante': 'doença inflamatória crônica',
                           'busca': 'ar autoimune doenca inflamatoria reumatismo'},
    'lupus': {'rotulo': 'Lúpus eritematoso sistêmico', 'agravante': 'doença inflamatória crônica',
              'busca': 'les autoimune doenca inflamatoria colagenose'},
    # Fator de alto risco de pré-eclâmpsia (USPSTF 2021; src/utils/prenatal.py); sem exame próprio fora da gestação.
    'saf': {'rotulo': 'Síndrome antifosfolípide', 'busca': 'saf sindrome do anticorpo antifosfolipide trombofilia autoimune'},
    'psoriase': {'rotulo': 'Psoríase', 'agravante': 'doença inflamatória crônica', 'busca': 'pele autoimune doenca inflamatoria'},
    'artrite_psoriasica': {'rotulo': 'Artrite psoriásica', 'agravante': 'doença inflamatória crônica',
                           'busca': 'aps psoriase espondiloartrite autoimune doenca inflamatoria'},
    'espondiloartrite': {'rotulo': 'Espondiloartrite axial (espondilite anquilosante)', 'agravante': 'doença inflamatória crônica',
                         'busca': 'ea espondilite anquilosante autoimune doenca inflamatoria'},
    'doenca_crohn': {'rotulo': 'Doença de Crohn', 'agravante': 'doença inflamatória crônica',
                     'busca': 'dii doenca inflamatoria intestinal autoimune'},
    'retocolite': {'rotulo': 'Retocolite ulcerativa', 'agravante': 'doença inflamatória crônica',
                   'busca': 'rcu colite ulcerativa dii doenca inflamatoria intestinal autoimune'},
    'esclerose_sistemica': {'rotulo': 'Esclerose sistêmica (esclerodermia)', 'busca': 'autoimune colagenose'},
    'asma_grave': {'rotulo': 'Asma moderada ou grave'},
    'bronquiectasias': {'rotulo': 'Bronquiectasias (adulto, sem fibrose cística)',
                        'busca': 'bronquiectasia escarro pseudomonas abpa'},
    'hipertensao_arterial_pulmonar': {'rotulo': 'Hipertensão arterial pulmonar (grupo 1)',
                                      'busca': 'hipertensao pulmonar hap pah bosentana ambrisentana sildenafila'},
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
    # Muda o rastreio do colo do útero (src/utils/colo_utero.py). Sem ela na lista, a paciente é tratada como não histerectomizada.
    'histerectomia_total': {'rotulo': 'Histerectomia total por doença benigna', 'busca': 'utero retirada histerectomizada'},
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
    # Metformina também se usa em pré-diabetes, resistência insulínica e SOP: sugere diabetes, mas não marca.
    'metformina': {'rotulo': 'Metformina', 'talvez': ['diabetes']},
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
    # Sem marca de imunossupressão: só mudam a triagem das vacinas de vírus vivo (src/utils/seguranca_vacinas.py)
    'corticoide_dose_desconhecida': {'rotulo': 'Corticoide sistêmico sem dose ou duração informadas'},
    'imunossupressao_baixo_grau': {'rotulo': 'Metotrexato ou azatioprina em dose de baixo grau'},
    'metotrexato': {'rotulo': 'Metotrexato'},
    'azatioprina': {'rotulo': 'Azatioprina'},
    'leflunomida': {'rotulo': 'Leflunomida'},
    'inibidor_calcineurina': {'rotulo': 'Ciclosporina ou tacrolimo'},
    'tacrolimo': {'rotulo': 'Tacrolimo'},
    'ciclosporina': {'rotulo': 'Ciclosporina'},
    'biologico': {'rotulo': 'Imunobiológico ou inibidor de JAK'},
    'bisfosfonato_longo': {'rotulo': 'Bisfosfonato por 5 anos ou mais'},
    'litio': {'rotulo': 'Lítio'},
    'amiodarona': {'rotulo': 'Amiodarona'},
    'digoxina': {'rotulo': 'Digoxina'},
    'valproato': {'rotulo': 'Ácido valproico / divalproato'},
    'carbamazepina': {'rotulo': 'Carbamazepina'},
    'fenitoina': {'rotulo': 'Fenitoína'},
    'fenobarbital': {'rotulo': 'Fenobarbital'},
    'varfarina': {'rotulo': 'Varfarina'},
    'doac': {'rotulo': 'Anticoagulante oral direto'},
    'antipsicotico_atipico': {'rotulo': 'Antipsicótico de 2ª geração'},
    'inibidor_aromatase': {'rotulo': 'Inibidor de aromatase'},
    'hidroxicloroquina': {'rotulo': 'Hidroxicloroquina'},
    'inibidor_jak': {'rotulo': 'Inibidor de JAK'},
    'tocilizumabe': {'rotulo': 'Tocilizumabe'},
    'rituximabe': {'rotulo': 'Rituximabe'},
    'oncologico': {'rotulo': 'Tratamento sistêmico do câncer'},
    'antraciclina': {'rotulo': 'Antraciclina', 'imunossupressao': True},
    'anti_her2': {'rotulo': 'Terapia anti-HER2'},
    'inibidor_checkpoint': {'rotulo': 'Inibidor de checkpoint imunológico'},
    'fluoropirimidina': {'rotulo': 'Fluoropirimidina', 'imunossupressao': True},
    'bloqueio_hormonal': {'rotulo': 'Agonista ou antagonista de GnRH'},
    # Monitorização própria (auditoria clínica de 15/11/2026, relatório D)
    'clozapina': {'rotulo': 'Clozapina'},
    'prep': {'rotulo': 'Tenofovir + entricitabina ou cabotegravir (PrEP, sem HIV)'},
    'tenofovir': {'rotulo': 'Tenofovir (TDF ou TAF)'},
    'tenofovir_alafenamida': {'rotulo': 'Tenofovir alafenamida (TAF)'},
    'ocrelizumabe': {'rotulo': 'Ocrelizumabe'},
    'natalizumabe': {'rotulo': 'Natalizumabe'},
    'fingolimode': {'rotulo': 'Fingolimode'},
    'micofenolato': {'rotulo': 'Micofenolato'},
    'inibidor_mtor': {'rotulo': 'Sirolimo ou everolimo'},
    'testosterona': {'rotulo': 'Testosterona'},
    'sulfassalazina': {'rotulo': 'Sulfassalazina'},
    'aminossalicilato': {'rotulo': 'Mesalazina'},
    'alopurinol': {'rotulo': 'Alopurinol'},
    'zoledronico': {'rotulo': 'Ácido zoledrônico'},
    'denosumabe': {'rotulo': 'Denosumabe'},
    'sotalol': {'rotulo': 'Sotalol'},
    'tamoxifeno': {'rotulo': 'Tamoxifeno'},
    # Corticoide sem dose ou duração informadas (src/utils/doses.py): conduta conservadora, com aviso
    'corticoide_sem_dose': {'rotulo': 'Corticoide sistêmico sem dose informada'},
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
    'barrett_esofago': {'rotulo': 'Esôfago de Barrett ou adenocarcinoma de esôfago', 'busca': 'refluxo esofago'},
}
# Marcadas por chip na tela (e "cardiopatia" é o valor antigo de DAC precoce).
FAMILIA_CHIPS = ('cancer_mama', 'cancer_colorretal', 'cancer_ovario', 'diabetes', 'dac_precoce', 'cardiopatia')

# Detalhes dos casos de câncer na família (caixas que aparecem quando há câncer na família). Decidem a
# indicação de teste genético (NCCN) e o rastreio colorretal (USMSTF); vão na mesma lista historia_familiar.
FAMILIA_DETALHES = {
    'mama_ate_50': 'Câncer de mama diagnosticado aos 50 anos ou antes',
    'mama_bilateral': 'Câncer de mama bilateral, ou mama e ovário na mesma pessoa',
    'mama_masculino': 'Câncer de mama em homem',
    'mama_triplo_negativo': 'Câncer de mama triplo-negativo',
    'mama_prostata_3_casos': '3 ou mais casos de câncer de mama e/ou de próstata no mesmo ramo da família (materno ou paterno)',
    'prostata_alto_risco': 'Câncer de próstata metastático ou de alto risco',
    'ccr_antes_60': 'Câncer colorretal antes dos 60 anos, ou em 2 ou mais parentes de 1º grau',
    'ascendencia_asquenaze': 'Ascendência judaica asquenaze (do paciente)',
}
NCCN_GENETICA = 'NCCN 2026 (risco genético mama/ovário/pâncreas/próstata)'
USPSTF_BRCA = 'USPSTF 2019 (BRCA)'
USMSTF = 'USMSTF 2017'
USMSTF_2022 = 'USMSTF 2022'
# Vigilância por história familiar e por síndrome hereditária de câncer: até 75 anos (USMSTF 2017/2022 para o
# colorretal; NCCN, que não fixa idade de parada para o portador e manda individualizar pela expectativa de vida).
# Depois disso, só orientação. A mamografia por história familiar segue a do risco habitual: até 74 anos.
FIM_VIGILANCIA = 75
FIM_MAMOGRAFIA_FAMILIAR = 74
FIM_PSA = 69  # USPSTF 2018: grau D a partir de 70 anos
SINDROMES_DE_CANCER = {'brca': 'BRCA1/2', 'li_fraumeni': 'Li-Fraumeni', 'lynch': 'Lynch', 'paf': 'PAF', 'cdh1': 'CDH1',
                       'cowden': 'Cowden', 'nem1': 'NEM1', 'nem2': 'NEM2'}


def criterios_teste_genetico(familia):
    """Critérios do NCCN (pessoa sem câncer, com parente próximo) para teste germinativo de BRCA1/2 e painel."""
    fam = set(familia)
    criterios = []
    if 'mama_ate_50' in fam:
        criterios.append('câncer de mama aos 50 anos ou antes em parente próximo')
    if 'mama_triplo_negativo' in fam:
        criterios.append('câncer de mama triplo-negativo em parente próximo, em qualquer idade')
    if 'mama_masculino' in fam:
        criterios.append('câncer de mama em homem da família')
    if 'cancer_ovario' in fam:
        criterios.append('câncer de ovário (epitelial) em parente próximo, em qualquer idade')
    if 'cancer_pancreas' in fam:
        criterios.append('câncer de pâncreas em parente de 1º grau, em qualquer idade')
    if 'prostata_alto_risco' in fam:
        criterios.append('câncer de próstata metastático ou de alto risco em parente de 1º grau')
    if 'mama_prostata_3_casos' in fam:
        criterios.append('3 ou mais casos de câncer de mama e/ou de próstata no mesmo ramo da família (materno ou paterno)')
    if 'mama_bilateral' in fam:
        criterios.append('câncer de mama bilateral, ou mama e ovário, na mesma pessoa da família')
    return criterios

PNEUMO = 'Pneumocócica conjugada 20-valente (Prevenar 20®)'
ZOSTER = 'Herpes Zóster (Shingrix®)'
VSR = 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'
SBIM = 'SBIm 2026/2027'
SBIM_ESPECIAIS = 'SBIm Pacientes Especiais 2026/2027'
IN_CNV = 'IN CNV 2026 (MS)'
CRIE = 'Manual dos CRIE (MS, 2023)'
ACIP = 'CDC/ACIP 2025'
MENB_ACIP = 'CDC/ACIP 2024 (MenB-4C)'
MENB_ACIP_REFORCO = 'CDC/ACIP 2020 (meningocócicas)'
HEPATITE_B_60 = 'Hepatite B (Engerix-B® ou Euvax B®)'
HEPATITES_A_B = 'Hepatites A e B (Twinrix® ou vacinas isoladas)'
HPV9 = 'Gardasil 9® (Vacina HPV 9-Valente)'
MENACWY = 'Meningocócica ACWY (Menactra® ou Menveo®)'
HIB = 'Haemophilus influenzae tipo b (Hib)'
COVID = 'COVID-19 (Comirnaty®, Spikevax® ou outras)'
INFLUENZA = 'Influenza (trivalente ou quadrivalente)'
HEPATOPATIAS = ('cirrose', 'hepatite_b_cronica', 'hepatite_c')
CGH_CORTICOIDE = 'CGH 2025 (Feuerstein)'
SPARLING = 'Drugs Aging 2024 (Sparling)'
# Fontes das comorbidades (links em src/utils/reference_links.py)
EULAR_CV_ARTRITES = 'EULAR 2016 (risco CV nas artrites inflamatórias)'
EULAR_CV_DRM = 'EULAR 2022 (risco CV no LES e outras DRM)'
EULAR_LES = 'EULAR 2010 (monitorização do LES)'
ACR_NEFRITE = 'ACR 2024 (nefrite lúpica)'
EULAR_INFECCOES = 'EULAR 2022 (infecções em DRAI)'
EULAR_VACINAS = 'EULAR 2019 (vacinação em DRAI)'
AAD_PSORIASE = 'AAD-NPF 2019 (comorbidades da psoríase)'
ACR_CHEST_DPI = 'ACR/CHEST 2023 (doença pulmonar intersticial)'
ESC_ERS_HP = 'ESC/ERS 2022 (hipertensão pulmonar)'
# Diretriz ERS 2025 (Chalmers et al., Eur Respir J 2025;66:2501126), lida no resumo dos próprios autores para a
# atenção primária (Mosgrove et al., npj Prim Care Respir Med 2026, doi 10.1038/s41533-026-00528-z).
ERS_BRONQUIECTASIAS = 'ERS 2025 (bronquiectasias) / Mosgrove 2026 (resumo da ERS 2025)'
ECCO_ANEMIA = 'ECCO 2015 (anemia na DII)'
BSG_DII = 'BSG 2025 (vigilância colorretal na DII)'
ACG_DII = 'ACG 2017 (cuidados preventivos na DII)'
AASLD_HBV = 'AASLD 2018 (hepatite B)'
AASLD_HCV = 'AASLD/IDSA (hepatite C)'
ASCO_HBV = 'ASCO 2020 (hepatite B no câncer)'
NHLBI_FALCIFORME = 'NHLBI 2014 (doença falciforme)'
GINA = 'GINA 2025'
ESC_FA = 'ESC 2024 (fibrilação atrial)'
AGA_CELIACA = 'AGA 2019 (doença celíaca)'
BSG_CELIACA = 'BSG 2014 (doença celíaca)'
ACG_BARRETT = 'ACG 2022 (esôfago de Barrett)'
PCOS = 'Diretriz internacional de SOP 2023'
FDA_TOFACITINIBE = 'FDA (bula do tofacitinibe)'
EMA_JAK = 'EMA 2023 (inibidores de JAK)'
FDA_TOCILIZUMABE = 'FDA (bula do tocilizumabe)'
BUCH_RITUXIMABE = 'Buch 2011 (consenso do rituximabe)'
ESC_ONCO = 'ESC 2022 (cardio-oncologia)'
ASCO_IRAE = 'ASCO 2021 (eventos imunomediados)'
EMA_DPD = 'EMA 2020 (teste de DPD)'
AHA_ADT = 'AHA/ACS/AUA 2010 (bloqueio androgênico)'
NCCN_OSSO = 'NCCN (saúde óssea no câncer)'
# Auditoria clínica de 15/11/2026 (relatório D): comorbidades e monitorização de medicações
KDIGO_DRC = 'KDIGO 2024 (DRC)'
KDIGO_DMO = 'KDIGO 2017 (DMO-DRC)'
KDIGO_ANEMIA = 'KDIGO 2012 (anemia na DRC)'
ESC_IC = 'ESC 2021 (insuficiência cardíaca)'
ESC_IC_2023 = 'ESC 2023 (insuficiência cardíaca)'
ACC_AHA_COLESTEROL = 'ACC/AHA 2018 (colesterol)'
SBC_DISLIPIDEMIA = 'SBC 2025 (dislipidemia)'
ADA_FIGADO = 'ADA 2026 (seção 4)'
ADA_LIPIDIOS = 'ADA 2026 (seção 10)'
ADA_PES = 'ADA 2026 (seção 12)'
ADA_METFORMINA = 'ADA 2026 (seção 9)'
AASLD_MASLD = 'AASLD 2023'
FDA_CLOZAPINA = 'FDA 2025 (clozapina)'
ANVISA_CLOZAPINA = 'ANVISA (bula do Leponex)'
RONALDSON = 'Ronaldson 2011 (miocardite por clozapina)'
PCDT_PREP = 'MS 2024 (PCDT PrEP)'
FDA_OCRELIZUMABE = 'FDA (bula do ocrelizumabe)'
EMA_NATALIZUMABE = 'EMA (bula do natalizumabe)'
EMA_FINGOLIMODE = 'EMA (bula do fingolimode)'
EMA_MICOFENOLATO = 'EMA (bula do micofenolato)'
EMA_SIROLIMO = 'EMA (bula do sirolimo)'
EMA_ZOLEDRONICO = 'EMA (bula do ácido zoledrônico)'
EMA_DENOSUMABE = 'EMA (bula do denosumabe)'
EMA_VALPROATO = 'EMA 2018 (valproato)'
ENDO_TESTOSTERONA = 'Endocrine Society 2018 (hipogonadismo)'
ATA_NODULO = 'ATA 2015 (nódulo de tireoide)'
HPTP_2022 = 'Workshop Internacional 2022 (hiperparatireoidismo primário)'
ESE_INCIDENTALOMA = 'ESE/ENSAT 2023 (incidentaloma adrenal)'
ENDO_PROLACTINA = 'Endocrine Society 2011 (hiperprolactinemia)'
PITUITARY_PROLACTINOMA = 'Pituitary Society 2023 (prolactinoma)'
ENDO_VITAMINA_D = 'Endocrine Society 2024 (vitamina D)'
ENDO_PA_2016 = 'Endocrine Society 2016 (hiperaldosteronismo)'
ENDO_PA_2025 = 'Endocrine Society 2025 (hiperaldosteronismo)'
ACC_AHA_HAS_2017 = 'ACC/AHA 2017 (hipertensão)'
ACR_GIOP = 'ACR 2022 (osteoporose por corticoide)'
BSR = 'BSR 2017'
CPIC_TIOPURINA = 'CPIC 2018 (TPMT/NUDT15)'
BSG_2019 = 'BSG 2019 (DII)'
AHA_FA_2023 = 'AHA/ACC/ACCP/HRS 2023 (FA)'
ATA_HIPERTIREOIDISMO = 'ATA 2016'
# Revisão externa (16/11/2026)
AASLD_HBV_2025 = 'AASLD/IDSA 2025 (hepatite B)'
OMS_HBV = 'OMS 2024 (hepatite B)'
AAO_HCQ = 'AAO 2025 (hidroxicloroquina)'

# Detalhes que abrem embaixo do item escolhido (como o bloco do HIV): vão no mesmo campo `comorbidades`.
DETALHES_COMORBIDADE = {
    'lupus': ('Lúpus: o que se aplica', 'Muda a frequência da proteinúria (ACR 2024).', [
        ('les_nefrite', 'Nefrite lúpica (atual ou prévia)')]),
    'psoriase': ('Psoríase: o que se aplica', 'Muda a frequência do rastreio cardiometabólico (AAD-NPF 2019).', [
        ('psoriase_extensa', 'Mais de 10% da superfície corporal, ou candidata a tratamento sistêmico ou fototerapia')]),
    'doenca_crohn': ('Doença de Crohn: o que se aplica', 'Define a colonoscopia de vigilância (BSG 2025) e B12/folato (ECCO 2015).', [
        ('crohn_colon', 'Acomete o cólon (1/3 ou mais do cólon)'),
        ('crohn_8_anos', '8 anos ou mais desde o início dos sintomas'),
        ('crohn_cep', 'Colangite esclerosante primária'),
        ('crohn_delgado', 'Acomete o intestino delgado ou já teve ressecção ileal')]),
    'retocolite': ('Retocolite: o que se aplica', 'Define a colonoscopia de vigilância (BSG 2025).', [
        ('rcu_alem_reto', 'Colite além do reto (não só proctite)'),
        ('rcu_8_anos', '8 anos ou mais desde o início dos sintomas'),
        ('rcu_cep', 'Colangite esclerosante primária')]),
    # Sem opções na tela: o estágio vem da creatinina e da uACR informadas em "Exames já realizados" (um só lugar).
    # Os valores drc_g*/drc_a* continuam aceitos pela API (estagio_drc).
    'doenca_renal': ('Doença renal crônica: estágio', 'Define a frequência de TFG, albuminúria e dos exames de G3a em diante '
                     '(KDIGO 2024). O estágio é calculado com a creatinina e a relação albumina/creatinina informadas em '
                     '"Exames já realizados".', []),
    'osteoporose': ('Osteoporose: o que se aplica', 'Define a investigação de causas secundárias (BHOF 2022).', [
        ('osteoporose_diagnostico', 'Diagnóstico recente, causas secundárias ainda não investigadas')]),
    'hepatite_b_cronica': ('Hepatite B: o que se aplica', 'Define o rastreio de carcinoma hepatocelular sem cirrose (AASLD 2018).', [
        ('hbv_risco_chc', 'História familiar de carcinoma hepatocelular, coinfecção por HIV ou hepatite D, homem asiático ≥ 40 anos, '
                          'mulher asiática ≥ 50 anos ou origem africana subsaariana')]),
}
# Diagnóstico antigo "doença inflamatória autoimune" (um item só): ainda aceito vindo de formulários salvos.
LEGADO_AUTOIMUNE = 'doenca_autoimune'


def _clcr(idade, sexo, peso, creatinina):
    """Clearance de creatinina estimado (Cockcroft-Gault), em mL/min; None sem peso ou creatinina."""
    try:
        peso, creatinina = float(peso), float(creatinina)
    except (TypeError, ValueError):
        return None
    if peso <= 0 or creatinina <= 0:
        return None
    valor = (140 - idade) * peso / (72 * creatinina)
    return valor * 0.85 if sexo == 'feminino' else valor


# Doença renal crônica (KDIGO 2024): estágio G pela TFG e categoria A pela albuminúria. Detalhes do item
# "Doença renal crônica" (a TFG calculada pela creatinina, quando informada, também define o G).
ESTAGIOS_G = ('G1-G2', 'G3a', 'G3b', 'G4', 'G5')
CATEGORIAS_A = ('A1', 'A2', 'A3')
# Vezes por ano que a TFG e a albuminúria são medidas, pelo mapa G x A (KDIGO 2024, Fig. 13; igual ao de 2012).
VEZES_POR_ANO = {'G1-G2': (1, 1, 2), 'G3a': (1, 2, 3), 'G3b': (2, 3, 3), 'G4': (3, 3, 4), 'G5': (4, 4, 4)}
_FREQUENCIA = {1: 'Anual', 2: 'A cada 6 meses', 3: 'A cada 4 meses', 4: 'A cada 3 meses'}


def texto_fib4(idade):
    """Interpretação do FIB-4 pela idade (AASLD 2023): corte baixo 2,0 a partir de 65 anos; pouco confiável abaixo de 35."""
    base = 'Rastreio de fibrose hepática pelo FIB-4 (idade, AST, ALT e plaquetas), mesmo com enzimas normais: '
    if idade >= 65:
        return base + ('com 65 anos ou mais, abaixo de 2,0 afasta fibrose avançada e repete em 1-2 anos; de 2,0 a 2,67, '
                       'elastografia; acima de 2,67, encaminhar ao hepatologista.')
    if idade < 35:
        return base + ('abaixo de 35 anos o FIB-4 é pouco confiável: interpretar junto com a elastografia. Abaixo de 1,3, repetir '
                       'em 1-2 anos; de 1,3 em diante, elastografia; acima de 2,67, encaminhar ao hepatologista.')
    return base + ('abaixo de 1,3, repetir em 1-2 anos; de 1,3 em diante, elastografia; acima de 2,67, encaminhar ao '
                   'hepatologista.')


def _detalhe_drc(chave):
    return 'drc_' + chave.lower().replace('-', '_')


def estagio_drc(com, tfg=None, uacr=None):
    """(estágio G, categoria A) da DRC; o pior entre o calculado (TFG, uACR em mg/g) e o detalhe marcado.
    None se não se sabe."""
    marcados = [g for g in ESTAGIOS_G if _detalhe_drc(g) in com]
    if tfg is not None:
        marcados.append('G1-G2' if tfg >= 60 else 'G3a' if tfg >= 45 else 'G3b' if tfg >= 30 else 'G4' if tfg >= 15 else 'G5')
    g = max(marcados, key=ESTAGIOS_G.index) if marcados else None
    categorias = [a for a in CATEGORIAS_A if _detalhe_drc(a) in com]
    if uacr is not None:
        categorias.append('A1' if uacr < 30 else 'A2' if uacr <= 300 else 'A3')   # KDIGO 2024, Tabela 3
    return g, (max(categorias, key=CATEGORIAS_A.index) if categorias else None)


def imunossupressao_implicada(comorbidades, medicacoes):
    return any(COMORBIDADES.get(c, {}).get('imunossupressao') for c in comorbidades) or \
        any(MEDICACOES.get(m, {}).get('imunossupressao') for m in medicacoes)


def agravantes_de_risco(comorbidades, familia, hiv=False):
    """Agravantes de risco cardiovascular (SBC 2025) que o formulário consegue saber."""
    lista = []
    for c in comorbidades:
        agravante = COMORBIDADES.get(c, {}).get('agravante') or ('doença inflamatória crônica' if c == LEGADO_AUTOIMUNE else None)
        if agravante and agravante not in lista:
            lista.append(agravante)
    if 'obesidade' in comorbidades:
        lista.append('obesidade')
    if hiv:
        lista.append('HIV')
    if {'dac_precoce', 'cardiopatia', 'avc_precoce'} & set(familia):
        lista.append('história familiar de DCV prematura')
    return lista


def _rec(titulo, categoria, descricao, subtitulo, referencia, grau, prioridade='media', substituir=False, esquema=None,
         obs=None):
    """``obs``: instrução que precisa chegar a quem faz o exame; sai impressa no pedido, abaixo do exame."""
    extra = {'esquema_pdf': esquema} if esquema else {}
    if obs:
        extra['quando_pdf'] = obs
    return {**extra, 'titulo': titulo, 'categoria': categoria, 'descricao': descricao, 'subtitulo': subtitulo,
            'referencia': referencia, 'grau_evidencia': grau, 'prioridade': prioridade, '_substituir': substituir}


def eh_rastreio_populacional(subtitulo):
    """Subtítulo de rastreio por idade ("Adultos 15-65 anos", "Adultos ≥40 anos"), não de grupo de risco
    ("Adultos com DPOC", "PrEP", "Em uso de ...")."""
    return (subtitulo or '').startswith('Adultos') and not subtitulo.startswith('Adultos com')


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
                atual = r.get('subtitulo') or ''
                if nova['subtitulo'] not in atual:
                    # O motivo de grupo de risco vem antes do rastreio populacional ("Adultos ..."), que passa a "Também".
                    if eh_rastreio_populacional(atual) and not eh_rastreio_populacional(nova['subtitulo']):
                        r['subtitulo'] = f"{nova['subtitulo']} | Também: {atual}"
                        r['descricao'] = nova.get('descricao') or r.get('descricao')
                    else:
                        r['subtitulo'] = f"{atual} | Também: {nova['subtitulo']}".strip(' |')
                if nova['referencia'] not in (r.get('referencia') or ''):
                    r['referencia'] = f"{r.get('referencia') or ''} | {nova['referencia']}".strip(' |')
            # A instrução do pedido vale também quando o exame já estava recomendado por outro motivo
            if nova.get('quando_pdf') and not r.get('quando_pdf'):
                r['quando_pdf'] = nova['quando_pdf']
            return
    recs.append(nova)


def aplicar(recs, idade, sexo, comorbidades, medicacoes, familia, gestante=False, tabagismo=None, imc=None,
            tfg=None, creatinina=None, peso=None, hipertensao=False, imunossuprimido=None, cd4=None,
            idade_ccr_familiar=None, uacr=None):
    """Soma às recomendações o que as listas disparam. Devolve as orientações (sem pedido/receita).

    ``tfg`` (CKD-EPI 2021), ``creatinina`` e ``peso`` vêm dos exames informados; ``hipertensao`` é a HAS que
    a rota considera estabelecida (marcada, em tratamento ou pela PA, conforme a regra da rota).
    ``imunossuprimido``: resposta "Sim" da triagem de imunossupressão (inclui a implicada pelas listas); sem ela,
    vale só o que as listas implicam. ``cd4``: LT-CD4+ da pessoa vivendo com HIV (imunodeficiência grave < 200).
    ``idade_ccr_familiar``: idade do diagnóstico do familiar mais jovem com câncer colorretal (opcional).
    ``uacr``: relação albumina/creatinina urinária (mg/g), que define a categoria A da DRC.
    """
    com, med, fam = set(comorbidades), set(medicacoes), set(familia)
    orient = []

    def add(*a, **k):
        _garantir(recs, _rec(*a, **k))

    def orientar(titulo, descricao, referencia):
        orient.append({'titulo': titulo, 'descricao': descricao, 'referencia': referencia})

    def vacina_hepatopatia_60():
        # 60+: um cartão só de hepatite (o de rotina, hepatite B), com a hepatite A para os suscetíveis (SBIm Idoso).
        add(HEPATITE_B_60, 'vacina',
            'Hepatopatia crônica: vacinar os suscetíveis contra hepatite A (2 doses, 0-6 meses) e contra hepatite B '
            '(3 doses, 0-1-6 meses; não se aplica a quem já tem hepatite B crônica). A combinada A+B (3 doses, 0-1-6 meses) '
            'pode substituir as isoladas.', 'Hepatopatia crônica | Suscetíveis | Hepatite A: rede privada', SBIM, 'A', 'alta',
            substituir=True)

    diabetico = bool(set(TIPOS_DE_DIABETES) & com) or 'diabetes_sem_tipo' in com or 'insulina' in med
    ic = 'insuficiencia_cardiaca' in com
    dcv = bool({'dcv_aterosclerotica', 'cardiopatia'} & com)
    hipolipemiante = bool({'estatina', 'outro_hipolipemiante'} & med)
    obeso = 'obesidade' in com or (imc or 0) >= 30
    hipertenso = hipertensao  # decidida pela rota (HAS confirmada), não por uma PA isolada

    # ---------------- Perfil lipídico (relatório D, D-11) ----------------
    # Em tratamento hipolipemiante, com dislipidemia ou com DCV aterosclerótica o perfil lipídico deixa de ser
    # rastreio (a cada 4-6 anos): 4-12 semanas após iniciar ou ajustar e depois a cada 3-12 meses (ACC/AHA 2018,
    # I-A). No diabetes sem estatina: anual a partir de 40 anos; antes, a cada 5 anos (ADA 2026, seção 10).
    # Só a regra de rastreio por idade ("Adultos ...") é trocada; as de outras indicações (HIV) ficam somadas.
    lipidios = None
    if hipolipemiante or dcv or 'dislipidemia' in com:
        quem = 'DCV aterosclerótica' if dcv else 'Dislipidemia ou tratamento hipolipemiante'
        lipidios = _rec('Colesterol total e frações, soro', 'laboratorio',
                        'Em tratamento hipolipemiante: perfil lipídico 4-12 semanas após iniciar ou ajustar a dose (adesão e '
                        'resposta) e depois a cada 3-12 meses. Sem tratamento, dosar para decidir o início.'
                        + (' DCV aterosclerótica: risco muito alto pela SBC 2025, meta de LDL-c < 50 mg/dL (< 40 mg/dL no '
                           'risco extremo).' if dcv else ''),
                        f'{quem} | A cada 3-12 meses', ACC_AHA_COLESTEROL + (' / ' + SBC_DISLIPIDEMIA if dcv else ''), 'A', 'alta')
        if diabetico and hipolipemiante:
            orientar('Perfil lipídico no diabetes em uso de estatina: diretrizes divergem',
                     'Nós optamos por seguir a referência da ACC/AHA 2018 (4-12 semanas após iniciar ou ajustar e depois a cada 3-12 meses). A ADA '
                     '2026 aceita, depois do controle de 4-12 semanas, um perfil lipídico por ano.',
                     ACC_AHA_COLESTEROL + ' / ' + ADA_LIPIDIOS)
    elif diabetico:
        lipidios = _rec('Colesterol total e frações, soro', 'laboratorio',
                        'Diabetes sem estatina: perfil lipídico no diagnóstico e na avaliação inicial; depois anual a partir '
                        'de 40 anos (idade em que a estatina passa a ser indicada) e a cada 5 anos antes disso.',
                        'Diabéticos | Anual' if idade >= 40 else 'Diabéticos sem estatina, menos de 40 anos | A cada 5 anos',
                        ADA_LIPIDIOS, 'B', 'alta')
    if lipidios:
        rastreio = next((r for r in recs if (r.get('titulo') or '').lower() == lipidios['titulo'].lower()
                         and (r.get('subtitulo') or '').startswith('Adultos ')), None)
        lipidios['_substituir'] = rastreio is not None
        _garantir(recs, lipidios)

    # ---------------- História familiar ----------------
    # Colorretal (USMSTF 2017): parente de 1º grau antes dos 60 anos, ou 2 ou mais parentes → colonoscopia a cada
    # 5 anos a partir dos 40 (ou 10 anos antes do caso mais jovem, o que vier primeiro); 1 parente com 60 anos ou mais
    # → rastreio de risco habitual, mas começando aos 40. Até 75 anos (USMSTF 2017/2022); depois, decisão individual
    # (orientação em src/utils/rastreio_cancer.py).
    antes_60 = 'ccr_antes_60' in fam or (idade_ccr_familiar is not None and idade_ccr_familiar < 60)
    if antes_60:
        inicio = 40 if idade_ccr_familiar is None else int(min(40, idade_ccr_familiar - 10))
        if inicio <= idade <= FIM_VIGILANCIA:
            quando = ('a partir dos 40 anos, ou 10 anos antes da idade do diagnóstico do familiar mais jovem (o que vier '
                      'primeiro)' if idade_ccr_familiar is None else
                      f'a partir dos {inicio} anos (familiar mais jovem diagnosticado aos {int(idade_ccr_familiar)}; início aos '
                      '40 anos ou 10 anos antes dessa idade, o que vier primeiro)')
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                'Parente de 1º grau com câncer colorretal antes dos 60 anos (ou 2 ou mais parentes de 1º grau): '
                f'colonoscopia a cada 5 anos, {quando}, até os 75 anos.',
                'História familiar de CCR antes dos 60 anos | ' + ('A partir de 40 anos | ' if inicio == 40 else '') + 'A cada 5 anos',
                USMSTF, 'B', 'alta', substituir=True)
        elif idade < inicio:
            orientar('Colonoscopia por história familiar de câncer colorretal',
                     'Parente de 1º grau com câncer colorretal antes dos 60 anos (ou 2 ou mais parentes): colonoscopia a cada '
                     '5 anos, começando aos 40 anos ou 10 anos antes da idade do diagnóstico do familiar mais jovem (o que '
                     'vier primeiro). Com a idade do familiar informada na história familiar, calculamos o início.', USMSTF)
    elif 'cancer_colorretal' in fam:
        if 40 <= idade <= FIM_VIGILANCIA:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                'Um parente de 1º grau com câncer colorretal diagnosticado aos 60 anos ou mais: rastreio de risco habitual '
                '(colonoscopia a cada 10 anos ou pesquisa de sangue oculto anual), começando aos 40 anos.',
                'História familiar de CCR aos 60 anos ou mais | A partir de 40 anos | A cada 10 anos',
                USMSTF, 'B', 'alta', substituir=True)
        if idade <= FIM_VIGILANCIA:
            orientar('Câncer colorretal na família: idade do familiar',
                     'Se o diagnóstico do familiar foi antes dos 60 anos, ou se há 2 ou mais parentes de 1º grau, marque o detalhe '
                     'na história familiar: a colonoscopia passa a cada 5 anos, a partir dos 40 anos ou 10 anos antes do caso mais '
                     'jovem.', USMSTF)
    tem_mama = bool({'cancer_mama', 'mama_ate_50', 'mama_bilateral', 'mama_masculino', 'mama_triplo_negativo'} & fam)
    # Anual só com parente de 1º grau (a caixa "Câncer de mama"); os detalhes aceitam também o 2º grau, que muda o risco
    # calculado, não o intervalo. Até 74 anos, como no risco habitual; depois, decisão individual (rastreio_cancer.py).
    if tem_mama and sexo == 'feminino':
        if 'cancer_mama' in fam and 40 <= idade <= FIM_MAMOGRAFIA_FAMILIAR:
            add('Mamografia Digital - Bilateral', 'imagem',
                'Câncer de mama em parente de 1º grau: risco acima do habitual; mamografia anual dos 40 aos 74 anos. '
                'Calcular o risco de câncer de mama ao longo da vida (Tyrer-Cuzick/IBIS): 20% ou mais indica ressonância '
                'anual associada.', 'Câncer de mama na família | Anual', 'ACR 2023', 'B', 'alta', substituir=True)
        elif 25 <= idade < 40:
            orientar('Rastreio de câncer de mama por história familiar',
                     'Calcular o risco de câncer de mama ao longo da vida (Tyrer-Cuzick/IBIS) até os 25 anos. Com risco de '
                     '20% ou mais: ressonância anual a partir de 25-30 anos e mamografia anual a partir de 30. Abaixo disso: '
                     'mamografia anual a partir dos 40.', 'ACR 2023')
    # Teste genético (BRCA1/2 e painel): só com os critérios do NCCN, não para toda história de câncer de mama.
    criterios = criterios_teste_genetico(fam)
    if criterios and 'brca' not in fam:
        orientar('Teste genético indicado: aconselhamento e painel germinativo (BRCA1/2)',
                 'A história familiar preenche critério para teste genético. ' +
                 ' '.join(c[0].upper() + c[1:] + '.' for c in criterios) +
                 ' Encaminhar para aconselhamento genético. O ideal é testar primeiro o familiar com câncer; se não for '
                 'possível, testar o paciente com painel que inclua BRCA1, BRCA2 e PALB2.', NCCN_GENETICA + ' / ' + USPSTF_BRCA)
    elif tem_mama and 'brca' not in fam:
        orientar('Câncer de mama na família sem critério para teste genético',
                 'Câncer de mama na família, por si só, não indica teste de BRCA1/2. Pelo NCCN, o teste é indicado quando há '
                 'em parente próximo: câncer de mama aos 50 anos ou antes, triplo-negativo, em homem, bilateral; câncer de '
                 'ovário ou de pâncreas; câncer de próstata metastático ou de alto risco; ou 3 ou mais casos de câncer de mama e/ou de '
                 'próstata no mesmo ramo da família (materno ou paterno). Se algum desses se aplicar, marque o detalhe na história familiar. '
                 'Sem eles, não testar de rotina; rever a história familiar a cada consulta.',
                 NCCN_GENETICA + ' / ' + USPSTF_BRCA)
    if 'ascendencia_asquenaze' in fam and not criterios and 'brca' not in fam:
        orientar('Ascendência judaica asquenaze',
                 'Ascendência associada a variantes fundadoras de BRCA1/2: aplicar ferramenta de risco familiar e oferecer '
                 'aconselhamento genético; o teste pode ser considerado mesmo sem câncer na família.',
                 NCCN_GENETICA + ' / ' + USPSTF_BRCA)
    if {'dac_precoce', 'cardiopatia', 'avc_precoce'} & fam:
        orientar('História familiar de DCV prematura',
                 'Agravante de risco cardiovascular (já considerado na categoria SBC). Em risco intermediário, o escore '
                 'de cálcio coronário pode reclassificar.', 'SBC 2025')
    if 'cancer_prostata' in fam and sexo == 'masculino' and 45 <= idade <= FIM_PSA:
        add('PSA total, soro', 'laboratorio',
            'Pai ou irmão com câncer de próstata: oferecer rastreamento a partir dos 45 anos, com decisão compartilhada '
            '(conversa sobre benefícios e danos), até os 69 anos.',
            'História familiar de câncer de próstata | A partir de 45 anos', 'AUA/SUO 2023 / EAU 2024', 'B')
    # Mulher pós-menopausa < 65 anos com fator de risco: USPSTF 2025 (B). Homem: a USPSTF 2025 é I (evidência
    # insuficiente); o apoio vem só da BHOF 2022 (50 a 69 anos com fator de risco), em decisão compartilhada.
    if 'osteoporose_fratura' in fam and sexo == 'feminino' and 50 <= idade < 65:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Fratura de quadril em pai ou mãe é fator de risco maior para fratura: rastrear antes dos 65 anos '
            '(mulher pós-menopausa).',
            'Fratura de quadril em pai ou mãe | Fator de risco', 'USPSTF 2025 / BHOF 2022', 'B')
    if 'osteoporose_fratura' in fam and sexo == 'masculino' and 50 <= idade < 70:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Fratura de quadril em pai ou mãe é fator de risco maior para fratura: a BHOF indica densitometria em homens '
            'de 50 a 69 anos com fator de risco. Decisão compartilhada: para homens, a USPSTF considera a evidência '
            'insuficiente.',
            'Fratura de quadril em pai ou mãe | Fator de risco', 'BHOF 2022', 'C')
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

    vigilancia = idade <= FIM_VIGILANCIA

    def colonoscopia(inicio, intervalo, ref, motivo, grau='A', detalhe=''):
        if inicio <= idade <= FIM_VIGILANCIA:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                f'{motivo}: colonoscopia {intervalo}, a partir de {inicio} anos{detalhe}.',
                f'{motivo} | {QUEM} | {intervalo.capitalize()}', ref, grau, 'alta', substituir=True)

    if 'brca' in fam:
        rm_mamas(25, 'NCCN 2025 / ACS 2007', 'BRCA1/2 na família')
        mamografia_anual(30, 'NCCN 2025', 'BRCA1/2 na família')
        if homem and 40 <= idade <= FIM_PSA:
            add('PSA total, soro', 'laboratorio',
                'BRCA1/2 na família: rastreamento de câncer de próstata a partir dos 40 anos no portador de BRCA2 '
                '(considerar em BRCA1), com decisão compartilhada, até os 69 anos.', f'BRCA1/2 na família | {QUEM} | A partir de 40 anos', 'NCCN 2025', 'B')
        orientar('Mutação BRCA1/2 na família',
                 CASCATA + ' Portadoras: discutir salpingo-ooforectomia redutora de risco (35-40 anos em BRCA1, 40-45 em '
                 'BRCA2) e mastectomia redutora. Homens portadores: exame clínico das mamas a partir de 35 anos. '
                 'Pâncreas: rastrear o portador que também tem caso de câncer de pâncreas na família.', 'NCCN 2025')
    if 'li_fraumeni' in fam:
        rm_mamas(20, 'NCCN 2025 / Kratz 2017', 'Li-Fraumeni na família')
        for titulo in ('Ressonância magnética de corpo inteiro', 'Ressonância magnética de crânio') if vigilancia else ():
            add(titulo, 'imagem', 'Li-Fraumeni (protocolo de Toronto): ressonância de corpo inteiro e de crânio anuais, '
                'sem contraste quando possível.', f'Li-Fraumeni na família | {QUEM} | Anual', 'NCCN 2025 / Kratz 2017', 'B', 'alta')
        colonoscopia(25, 'a cada 2-5 anos', 'NCCN 2025 / Kratz 2017', 'Li-Fraumeni na família', 'B')
        orientar('Síndrome de Li-Fraumeni na família',
                 CASCATA + ' Exame físico completo e neurológico a cada 6-12 meses, exame dermatológico anual e '
                 'endoscopia digestiva alta junto com a colonoscopia. Evitar radiação ionizante sempre que houver alternativa.',
                 'NCCN 2025 / Kratz 2017')
    if 'lynch' in fam:
        colonoscopia(20, 'a cada 1-2 anos', 'NCCN 2025 / ACG 2015', 'Síndrome de Lynch na família',
                     detalhe=' (MLH1, MSH2 e EPCAM: a partir de 20-25 anos, a cada 1-2 anos; MSH6 e PMS2: a partir de 30-35 '
                             'anos, a cada 1-3 anos)')
        if 30 <= idade <= FIM_VIGILANCIA:
            add('Endoscopia digestiva alta', 'imagem',
                'Síndrome de Lynch: endoscopia digestiva alta com biópsias e pesquisa de H. pylori a cada 2-4 anos, a partir de 30-40 anos.',
                f'Síndrome de Lynch na família | {QUEM} | A cada 2-4 anos', 'NCCN 2025', 'B')
        orientar('Síndrome de Lynch na família',
                 CASCATA + ' Início da colonoscopia aos 20-25 anos em MLH1/MSH2 e aos 30-35 em MSH6/PMS2. Mulheres: '
                 'orientar sobre sangramento uterino anormal, considerar biópsia de endométrio a cada 1-2 anos a partir de '
                 '30-35 anos e discutir histerectomia com salpingo-ooforectomia após prole constituída.', 'NCCN 2025 / ACG 2015')
    if 'paf' in fam:
        colonoscopia(18, 'anual', 'NCCN 2025 / ACG 2015', 'Polipose adenomatosa familiar')
        if 20 <= idade <= FIM_VIGILANCIA:
            add('Endoscopia digestiva alta', 'imagem',
                'Polipose adenomatosa familiar: endoscopia digestiva alta com avaliação da papila a partir de 20-25 anos; '
                'intervalo conforme o estágio de Spigelman.', f'PAF na família | {QUEM}', 'NCCN 2025 / ACG 2015', 'B')
        orientar('Polipose adenomatosa familiar na família',
                 CASCATA + ' No portador, a colonoscopia começa aos 10-15 anos; discutir colectomia conforme a carga de pólipos. '
                 'Considerar ultrassonografia de tireoide.' + (
                     ' Parente não testado com mais de 50 anos: a penetrância da PAF chega a quase 100% antes dos 40-50 anos; '
                     'sem polipose nas colonoscopias anteriores, a chance de ser portador é baixa. Fazer o teste em cascata '
                     'antes de continuar a vigilância anual.' if idade > 50 else ''), 'NCCN 2025 / ACG 2015')
    if 'cdh1' in fam and vigilancia:
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
        if vigilancia:
            add('Ultrassonografia de tireoide', 'imagem', 'Síndrome de Cowden (PTEN): ultrassonografia de tireoide anual.',
                f'Síndrome de Cowden na família | {QUEM} | Anual', 'NCCN 2025', 'B')
        colonoscopia(35, 'a cada 5 anos', 'NCCN 2025', 'Síndrome de Cowden na família', 'B')
        if 40 <= idade <= FIM_VIGILANCIA:
            add('Ultrassonografia de rins e vias urinárias', 'imagem',
                'Síndrome de Cowden (PTEN): ultrassonografia renal a cada 1-2 anos a partir dos 40 anos.',
                f'Síndrome de Cowden na família | {QUEM} | A cada 1-2 anos', 'NCCN 2025', 'C')
        orientar('Síndrome de Cowden na família',
                 CASCATA + ' Mulheres: orientar sobre sangramento uterino anormal e considerar rastreamento de endométrio a partir de 35 anos.',
                 'NCCN 2025')
    if 'nem1' in fam:
        for titulo in ('Cálcio iônico, soro', 'Paratormônio (PTH), soro', 'Prolactina, soro') if vigilancia else ():
            add(titulo, 'laboratorio', 'NEM1: cálcio, PTH e prolactina anuais.', f'NEM1 na família | {QUEM} | Anual',
                'Endocrine Society 2012', 'B')
        orientar('Neoplasia endócrina múltipla tipo 1 na família',
                 CASCATA + ' No portador: gastrina e imagem pancreática anuais; ressonância de hipófise a cada 3-5 anos.',
                 'Endocrine Society 2012')
    if 'nem2' in fam:
        for titulo in ('Calcitonina, soro', 'Metanefrinas, plasma ou urina de 24h', 'Cálcio iônico, soro') if vigilancia else ():
            add(titulo, 'laboratorio', 'NEM2 / carcinoma medular de tireoide familiar: calcitonina, metanefrinas e cálcio anuais.',
                f'NEM2 na família | {QUEM} | Anual', 'ATA 2015', 'B', 'alta')
        if vigilancia:
            add('Ultrassonografia de tireoide', 'imagem', 'NEM2 / carcinoma medular de tireoide familiar: ultrassonografia cervical.',
                f'NEM2 na família | {QUEM}', 'ATA 2015', 'B')
        orientar('NEM2 / carcinoma medular de tireoide na família',
                 CASCATA + ' O teste do gene RET define a conduta: no portador, tireoidectomia profilática na idade indicada pelo '
                 'risco da mutação.', 'ATA 2015')
    sindromes = [nome for chave, nome in SINDROMES_DE_CANCER.items() if chave in fam]
    if sindromes and not vigilancia:
        orientar('Síndrome hereditária de câncer depois dos 75 anos: decisão individual',
                 f'A vigilância por {", ".join(sindromes)} na família vai até os 75 anos. Depois disso, individualizar pela '
                 'expectativa de vida e pelas comorbidades: o NCCN não fixa idade de parada para o portador confirmado. No parente '
                 'ainda não testado, fazer primeiro o teste em cascata: teste negativo para a variante da família dispensa a '
                 'vigilância.', 'NCCN 2025 / ' + USMSTF_2022)
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
                 'Indicam avaliação em centro de referência (ressonância ou ecoendoscopia): dois ou mais parentes acometidos do '
                 'mesmo ramo da família, com pelo menos um de 1º grau; ou variante patogênica de risco (BRCA1, BRCA2, PALB2, ATM, '
                 'síndrome de Lynch) com parente acometido; ou síndrome de alto risco (Peutz-Jeghers, CDKN2A). Um parente '
                 'isolado, sem variante conhecida, não indica rastreamento.',
                 'AGA 2020 / CAPS 2020')
    if 'cancer_gastrico' in fam:
        orientar('Câncer gástrico na família',
                 'Pesquisar e tratar Helicobacter pylori; endoscopia conforme sintomas e risco individual.',
                 'Maastricht VI 2022 / ACG 2024')
    if 'melanoma' in fam:
        orientar('Melanoma na família',
                 'Parente com melanoma aumenta o risco, mas a evidência para o exame da pele em pessoa assintomática é '
                 'insuficiente (USPSTF, grau I): individualizar o exame dermatológico de corpo inteiro periódico e orientar '
                 'fotoproteção.', 'USPSTF 2023')
    if 'trombose' in fam:
        orientar('Trombose venosa na família',
                 'Pesar o risco antes de prescrever estrogênio (anticoncepcional combinado, terapia hormonal). Pesquisa de '
                 'trombofilia não é rotina em assintomáticos.', 'ASH 2023')
    if 'glaucoma' in fam and idade >= 40:
        orientar('Glaucoma na família', 'Avaliação oftalmológica com tonometria e fundoscopia a cada 1-2 anos a partir dos 40 anos.',
                 'AAO 2020')

    # ---------------- Medicações ----------------
    # Antagonista mineralocorticoide, e sacubitril/valsartana na IC: K e creatinina em 1 e 4 semanas e depois a
    # cada 3-4 meses (ESC 2021; AHA/ACC/HFSA 2022). IECA/BRA e diuréticos: 2-4 semanas após iniciar ou ajustar
    # e depois anual (KDIGO 2024, PP 3.6.2; AHA 2025).
    renais = ('ieca_bra', 'arni', 'espironolactona', 'tiazidico', 'diuretico_alca')
    frequentes = [k for k in renais if k in med and (k == 'espironolactona' or (k == 'arni' and ic))]
    anuais = [k for k in renais if k in med and k not in frequentes]
    if anuais:
        quais = ', '.join(MEDICACOES[k]['rotulo'] for k in anuais)
        add('Potássio, soro', 'laboratorio', f'Potássio em uso de {quais}: 2-4 semanas após iniciar ou ajustar a dose e '
            'depois pelo menos uma vez por ano.', f'Em uso de {quais} | Anual', 'KDIGO 2024 / AHA 2025', 'B')
        add('Creatinina, soro', 'laboratorio', f'Função renal em uso de {quais}: 2-4 semanas após iniciar ou ajustar a dose '
            'e depois pelo menos uma vez por ano.', f'Em uso de {quais} | Anual', 'KDIGO 2024 / AHA 2025', 'B')
    if frequentes:
        quais = ', '.join(MEDICACOES[k]['rotulo'] for k in frequentes)
        grupo = ('Insuficiência cardíaca em uso de ' if ic else 'Em uso de ') + quais
        for titulo in ('Potássio, soro', 'Creatinina, soro'):
            add(titulo, 'laboratorio',
                'Antagonista mineralocorticoide (e sacubitril/valsartana na insuficiência cardíaca): potássio e creatinina 1 e '
                '4 semanas após iniciar ou ajustar a dose, depois mensalmente até 3 meses e então a cada 3-4 meses.',
                f'{grupo} | A cada 3-4 meses', ESC_IC + ' / AHA/ACC/HFSA 2022', 'C', 'alta')
    if {'tiazidico', 'diuretico_alca'} & med:
        add('Sódio, soro', 'laboratorio', 'Hiponatremia por diurético, sobretudo em idosos.', 'Em uso de diurético | Anual',
            'AHA 2025', 'C', 'baixa')
    if 'metformina' in med:
        add('Vitamina B12, soro', 'laboratorio',
            'Uso prolongado de metformina associa-se a deficiência de B12; dosar periodicamente, sobretudo com anemia '
            'ou neuropatia.', 'Em uso de metformina | Periódico', ADA_METFORMINA, 'B')
    if 'antitireoidiano' in med or 'hipertireoidismo' in com:
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'T4 livre, soro'):
            add(titulo, 'laboratorio',
                'Hipertireoidismo: T4 livre e T3 total (com o TSH, que pode seguir suprimido por meses) 4-6 semanas após iniciar '
                'o antitireoidiano, depois a cada 4-8 semanas até o eutireoidismo e então a cada 2-3 meses.',
                'Hipertireoidismo / antitireoidiano | A cada 4-8 semanas', ATA_HIPERTIREOIDISMO, 'B')
        if 'antitireoidiano' in med:
            orientar('Antitireoidiano: agranulocitose e hepatotoxicidade',
                     'Hemograma com diferencial se houver febre ou dor de garganta, e função hepática se houver sintomas de '
                     'hepatotoxicidade; suspender o antitireoidiano até o resultado. Hemograma e função hepática basais antes '
                     'de iniciar.', ATA_HIPERTIREOIDISMO)
        else:
            for titulo in ('Hemograma completo com plaquetas', 'Alanina aminotransferase, soro'):
                add(titulo, 'laboratorio', 'Hipertireoidismo: hemograma com diferencial e função hepática basais antes de '
                    'iniciar o antitireoidiano (neutropenia e hepatopatia prévias mudam a escolha).',
                    'Hipertireoidismo | Antes do tratamento', ATA_HIPERTIREOIDISMO, 'B')
    if 'varfarina' in med:
        add('Tempo de protrombina (TP/INR), plasma', 'laboratorio',
            'Varfarina: INR a cada 4 semanas com dose estável (até 12 semanas se INR consistentemente no alvo).',
            'Em uso de varfarina | A cada 4-12 semanas', 'CHEST 2012', 'B', 'alta')
    if 'doac' in med:
        # EHRA 2021: função renal, hemoglobina e função hepática anuais; a cada 6 meses com 75 anos ou mais (ou
        # fragilidade); com ClCr ≤ 60 mL/min, a função renal a cada ClCr/10 meses.
        meses = 6 if idade >= 75 else 12
        clcr = _clcr(idade, sexo, peso, creatinina)
        renal = min(meses, max(1, int(clcr // 10))) if clcr is not None and clcr <= 60 else meses
        texto = {12: 'Anual', 1: 'A cada 1 mês'}.get(renal, f'A cada {renal} meses')
        add('Creatinina, soro', 'laboratorio',
            'Anticoagulante oral direto: função renal (ClCr por Cockcroft-Gault) para ajustar a dose: anual; a cada 6 meses '
            'com 75 anos ou mais ou fragilidade; com ClCr ≤ 60 mL/min, a cada "ClCr/10" meses (ClCr de 40: a cada 4 meses).',
            f'Em uso de anticoagulante oral direto | {texto}', 'EHRA 2021', 'B')
        for titulo in ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Anticoagulante oral direto: hemoglobina e função hepática anuais (a cada 6 meses com '
                '75 anos ou mais ou fragilidade).',
                'Em uso de anticoagulante oral direto | ' + ('A cada 6 meses' if idade >= 75 else 'Anual'), 'EHRA 2021', 'B')
    if 'antipsicotico_atipico' in med:
        for titulo in ('Glicose, soro', 'Colesterol total e frações, soro'):
            add(titulo, 'laboratorio', 'Antipsicótico de 2ª geração: monitorização metabólica (peso, glicemia e lipídios) '
                'em 12 semanas e depois anualmente.', 'Em uso de antipsicótico de 2ª geração | Anual', 'ADA/APA 2004', 'B')
    if 'clozapina' in med:
        add('Hemograma completo com plaquetas', 'laboratorio',
            'Clozapina: contagem absoluta de neutrófilos antes de iniciar, semanal nos 6 primeiros meses, quinzenal do 6º ao 12º '
            'mês e mensal depois (bula FDA; a FDA retirou o REMS em 2025, mas manteve a recomendação). A bula brasileira pede '
            'semanal nas 18 primeiras semanas e mensal depois.', 'Em uso de clozapina | A cada 1-4 semanas',
            FDA_CLOZAPINA + ' / ' + ANVISA_CLOZAPINA, 'B', 'alta')
        orientar('Clozapina: neutrófilos e miocardite',
                 'Nós optamos por seguir a referência da bula americana para os neutrófilos (semanal até 6 meses, quinzenal até 12 meses e mensal '
                 'depois); a bula brasileira pede semanal até 18 semanas e mensal depois. Miocardite: troponina e PCR antes de '
                 'iniciar e nos dias 7, 14, 21 e 28; troponina acima de 2 vezes o limite ou PCR acima de 100 mg/L indicam '
                 'suspender.', FDA_CLOZAPINA + ' / ' + ANVISA_CLOZAPINA + ' / ' + RONALDSON)
    if 'inibidor_aromatase' in med:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Inibidor de aromatase: densitometria no início do tratamento e a cada 1-2 anos.',
            'Em uso de inibidor de aromatase', 'ASCO 2019', 'B')
    if 'hidroxicloroquina' in med and 'hidroxicloroquina_rastreio' not in med:
        # AAO 2025 (revisão da de 2016): OCT e autofluorescência de padrão amplo são o rastreio principal (revisão externa, FARM-02)
        risco = 'doenca_renal' in com or 'tamoxifeno' in med
        orientar('Hidroxicloroquina',
                 'Dose até 5 mg/kg/dia de peso real (menos de 400 mg/dia na obesidade grave). Exame basal logo após o início, '
                 'com fundo de olho, OCT e autofluorescência de padrão amplo. Rastreio anual com OCT e autofluorescência; pode '
                 'ser adiado nos 5 primeiros anos sem fator de risco (doença renal, tamoxifeno, início em idade mais avançada).'
                 + (' Com doença renal crônica ou tamoxifeno: rastreio anual desde o início.' if risco else ''), AAO_HCQ)
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
        # A PA se acompanha no consultório: o uso de corticoide, sozinho, não indica MAPA (relatório D, D-14).
        orientar('Corticoide sistêmico: pressão arterial',
                 'Aferir a pressão arterial em cada consulta durante o uso (hipertensão induzida por corticoide).', CGH_CORTICOIDE)
        add('Avaliação oftalmológica com tonometria e fundoscopia', 'imagem',
            'Corticoide sistêmico: exame oftalmológico periódico para catarata e glaucoma.', f'{quem} | Periódico',
            CGH_CORTICOIDE + ' / ' + SPARLING, 'B')
    # 25(OH)D e painel basal: só no uso por 3 meses ou mais (ou sem dose informada, tratado como crônico) e na
    # dose imunossupressora. Dose baixa e curta não pede painel (relatório D, D-14).
    if cronico:
        add('25-hidroxivitamina D, soro', 'laboratorio',
            'Corticoide sistêmico por 3 meses ou mais: manter vitamina D adequada (prevenção de osteoporose induzida por corticoide).',
            f'{quem} | Basal', ACR_GIOP + ' / ' + SPARLING, 'B')
        orientar('Vitamina D no corticoide crônico: diretrizes divergem',
                 'Sugerimos a 25(OH)D basal no uso de corticoide por 3 meses ou mais (Sparling 2024). A ACR 2022 recomenda '
                 'otimizar cálcio e vitamina D sem exigir a dosagem, e a Endocrine Society 2024 sugere não dosar de rotina em '
                 'adultos sem indicação. Se a opção for suplementar empiricamente, o exame pode ser retirado.',
                 SPARLING + ' / ' + ACR_GIOP + ' / ' + ENDO_VITAMINA_D)
    if cronico or imunossupressor:
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
    # Tuberculose latente: corticoide ≥ 15 mg/dia de prednisona por ≥ 1 mês (MS 2019), dose imunossupressora ou
    # imunobiológico. Sem a dose informada, conservador: entra, com o aviso de doses.py (relatório D, D-14).
    tb_corticoide = imunossupressor or 'rastreio_tb_latente' in med or 'corticoide_sem_dose' in med
    if tb_corticoide or 'biologico' in med:
        motivo = ' e '.join(x for x, sim in (('corticoide sistêmico', tb_corticoide),
                                             (MEDICACOES['biologico']['rotulo'].lower(), 'biologico' in med)) if sim)
        imunossuprime = imunossupressor or 'rastreio_tb_latente' in med or 'biologico' in med
        add('Prova tuberculínica (PPD) ou IGRA', 'laboratorio',
            f'Rastreamento de tuberculose latente em uso de {motivo}; com resultado positivo e doença ativa afastada, tratar.',
            ('Imunossupressão' if imunossuprime else 'Corticoide sistêmico sem dose informada') + ' | Antes ou no início do tratamento',
            'MS 2019 (Manual de Tuberculose) / ACR 2022' + (' / ' + SPARLING if tb_corticoide else ''), 'A', 'alta')
    if 'biologico' in med:
        for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro'):
            add(titulo, 'laboratorio', 'Imunobiológico ou inibidor de JAK: rastrear hepatite B antes do tratamento '
                '(risco de reativação, sobretudo com rituximabe).', 'Imunobiológico | Antes do tratamento', 'ACR 2022 / AASLD 2018', 'A', 'alta')
    if 'biologico' in med:
        add('Anticorpos anti-HCV, soro', 'laboratorio', 'Imunobiológico ou inibidor de JAK: rastrear hepatite C antes do '
            'tratamento; HCV-RNA positivo, encaminhar para tratamento antiviral.', 'Imunobiológico | Antes do tratamento',
            EULAR_INFECCOES, 'B', 'alta')
    if 'inibidor_jak' in med:
        add('Hemograma completo com plaquetas', 'laboratorio',
            'Inibidor de JAK: neutrófilos, linfócitos e hemoglobina no início, após 4-8 semanas e depois a cada 3 meses.',
            'Em uso de inibidor de JAK | A cada 4-12 semanas', FDA_TOFACITINIBE, 'B', 'alta')
        add('Colesterol total e frações, soro', 'laboratorio',
            'Inibidor de JAK: perfil lipídico 4-8 semanas após o início (elevação de LDL e HDL) e depois conforme o risco '
            'cardiovascular.', 'Em uso de inibidor de JAK | Após 4-8 semanas do início', FDA_TOFACITINIBE, 'B')
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Inibidor de JAK: enzimas hepáticas de rotina durante o uso.',
                'Em uso de inibidor de JAK | Periódico', FDA_TOFACITINIBE, 'B')
        orientar('Inibidor de JAK: quem tem mais risco',
                 'Com 65 anos ou mais, tabagismo atual ou prévio de longa duração, outros fatores de risco cardiovascular ou de '
                 'câncer, usar só se não houver alternativa adequada; cautela com risco de trombose venosa. Vacina inativada '
                 'contra herpes-zóster antes ou durante o uso.', EMA_JAK)
    if 'tocilizumabe' in med:
        for titulo in ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Tocilizumabe: neutrófilos, plaquetas e transaminases no início, 4-8 semanas após (as '
                'transaminases a cada 4-8 semanas nos primeiros 6 meses) e depois a cada 3 meses.',
                'Em uso de tocilizumabe | A cada 4-12 semanas', FDA_TOCILIZUMABE, 'B', 'alta')
        add('Colesterol total e frações, soro', 'laboratorio', 'Tocilizumabe: perfil lipídico 4-8 semanas após o início.',
            'Em uso de tocilizumabe | Após 4-8 semanas do início', FDA_TOCILIZUMABE, 'B')
    if 'rituximabe' in med:
        add('Imunoglobulina G (IgG), soro', 'laboratorio',
            'Rituximabe: IgG antes do primeiro ciclo e antes de cada novo ciclo (hipogamaglobulinemia aumenta o risco de '
            'infecção grave).', 'Em uso de rituximabe | Antes de cada ciclo', BUCH_RITUXIMABE, 'C', 'alta')
    if 'ocrelizumabe' in med:
        add('Imunoglobulina G (IgG), soro', 'laboratorio',
            'Ocrelizumabe: imunoglobulinas antes de iniciar e antes de cada nova dose (hipogamaglobulinemia aumenta o risco de '
            'infecção grave). Hepatite B ativa contraindica o uso: HBsAg e anti-HBc antes da primeira dose.',
            'Em uso de ocrelizumabe | Antes de cada ciclo', FDA_OCRELIZUMABE, 'B', 'alta')
    if 'natalizumabe' in med:
        add('Anticorpo anti-JCV (vírus JC), soro', 'laboratorio',
            'Natalizumabe: anticorpo anti-JCV (com índice) antes de iniciar para estratificar o risco de leucoencefalopatia '
            'multifocal progressiva (LEMP), e a cada 6 meses enquanto negativo ou com índice baixo.',
            'Em uso de natalizumabe | A cada 6 meses', EMA_NATALIZUMABE, 'B', 'alta')
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Natalizumabe: função hepática periódica (lesão hepática descrita na bula).',
                'Em uso de natalizumabe | A cada 6 meses', EMA_NATALIZUMABE, 'C')
    if 'fingolimode' in med:
        add('Eletrocardiograma de repouso', 'imagem',
            'Fingolimode: ECG antes da primeira dose e monitorização de 6 horas na primeira dose (bradicardia e bloqueio '
            'atrioventricular).', 'Em uso de fingolimode | Antes do tratamento', EMA_FINGOLIMODE, 'B', 'alta')
        add('Avaliação oftalmológica (fundo de olho)', 'imagem',
            'Fingolimode: exame oftalmológico 3-4 meses após o início (edema macular); antes de iniciar no diabetes ou com uveíte.',
            'Em uso de fingolimode | 3-4 meses após o início', EMA_FINGOLIMODE, 'B')
        add('Varicela, IgG', 'laboratorio', 'Fingolimode: sorologia para varicela-zóster antes de iniciar; não imune, vacinar '
            'e só iniciar o fingolimode 1 mês depois.', 'Em uso de fingolimode | Antes do tratamento', EMA_FINGOLIMODE, 'B')
        add('Hemograma completo com plaquetas', 'laboratorio',
            'Fingolimode: hemograma (linfócitos) antes de iniciar, no 3º mês e pelo menos anual.',
            'Em uso de fingolimode | Anual', EMA_FINGOLIMODE, 'B')
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Fingolimode: transaminases antes de iniciar, nos meses 1, 3, 6, 9 e 12 e depois periodicamente.',
                'Em uso de fingolimode | A cada 3 meses', EMA_FINGOLIMODE, 'B')
    if 'micofenolato' in med:
        add('Hemograma completo com plaquetas', 'laboratorio',
            'Micofenolato: hemograma semanal no 1º mês, quinzenal no 2º e no 3º mês e mensal até completar 1 ano (neutropenia).',
            'Em uso de micofenolato | A cada 1-4 semanas', EMA_MICOFENOLATO, 'B', 'alta')
    if 'inibidor_mtor' in med:
        for titulo in ('Colesterol total e frações, soro', 'Glicose, soro', 'Relação proteína/creatinina, urina'):
            add(titulo, 'laboratorio', 'Sirolimo ou everolimo: lipídios, glicemia e proteinúria periódicos (dislipidemia, '
                'hiperglicemia e proteinúria induzidas pelo inibidor de mTOR).', 'Em uso de sirolimo ou everolimo | Periódico',
                EMA_SIROLIMO, 'B')
        if 'transplante' in com:
            add('Sirolimo ou everolimo, sangue total (nível de vale)', 'laboratorio',
                'Transplantado em uso de sirolimo ou everolimo: nível de vale, com alvo definido pela equipe de transplante; '
                'repetir após mudança de medicação que interage.', 'Transplante em uso de sirolimo ou everolimo | A cada 1-3 meses',
                'KDIGO 2009 (transplante renal) / ' + EMA_SIROLIMO, 'B', 'alta')
    if 'testosterona' in med and sexo == 'masculino':
        add('Hemograma completo com plaquetas', 'laboratorio',
            'Testosterona: hematócrito antes de iniciar, 3-6 meses após o início e depois anual; acima de 54%, suspender até '
            'normalizar e investigar.', 'Em uso de testosterona | Anual', ENDO_TESTOSTERONA, 'B', 'alta')
        risco_prostata = bool({'cancer_prostata', 'prostata_alto_risco', 'brca'} & fam)
        if 55 <= idade <= 69 or (risco_prostata and 40 <= idade <= 69):
            add('PSA total, soro', 'laboratorio',
                'Testosterona: PSA 3-12 meses após o início (homens de 55 a 69 anos, ou de 40 a 69 com risco aumentado de '
                'câncer de próstata) e depois conforme o rastreio habitual.',
                'Em uso de testosterona | 3-12 meses após o início', ENDO_TESTOSTERONA, 'B')
    if 'aminossalicilato' in med:
        add('Creatinina, soro', 'laboratorio', 'Mesalazina: função renal antes de iniciar e pelo menos uma vez por ano '
            '(nefrite intersticial).', 'Em uso de mesalazina | Anual', BSG_2019, 'C')
    if 'alopurinol' in med:
        orientar('Alopurinol: HLA-B*58:01',
                 'Antes de iniciar, testar o HLA-B*58:01 em pessoas de ascendência do Sudeste Asiático ou afrodescendentes '
                 '(risco maior de reação cutânea grave); recomendação condicional. Começar com dose baixa (até 100 mg/dia; '
                 'menos na doença renal) e aumentar até o alvo de ácido úrico.', 'ACR 2020')
    if 'zoledronico' in med:
        for titulo in ('Creatinina, soro', 'Cálcio iônico, soro'):
            add(titulo, 'laboratorio', 'Ácido zoledrônico: creatinina (clearance) e cálcio antes de cada infusão; hipocalcemia '
                'deve ser corrigida antes, e ClCr < 35 mL/min contraindica.', 'Em uso de ácido zoledrônico | Antes de cada dose',
                EMA_ZOLEDRONICO, 'B', 'alta')
    if 'denosumabe' in med:
        add('Cálcio iônico, soro', 'laboratorio', 'Denosumabe: cálcio antes de cada dose e, com risco de hipocalcemia (doença '
            'renal crônica avançada), também nas 2 semanas seguintes à primeira dose.', 'Em uso de denosumabe | Antes de cada dose',
            EMA_DENOSUMABE, 'B', 'alta')
    if 'sotalol' in med:
        add('Eletrocardiograma de repouso', 'imagem', 'Sotalol: ECG com QTc no início e a cada ajuste de dose (pró-arrítmico).',
            'Em uso de sotalol | No início e a cada ajuste de dose', AHA_FA_2023, 'B', 'alta')
        add('Creatinina, soro', 'laboratorio', 'Sotalol: função renal (ClCr) para definir a dose e o intervalo; eliminação renal.',
            'Em uso de sotalol | No início e a cada ajuste de dose', AHA_FA_2023, 'B', 'alta')
    if 'prep' in med and 'hiv' not in com:
        # PCDT PrEP oral (Portaria SECTICS/MS nº 55/2024), Quadro 5: consultas a cada 120 dias.
        add('Anti-HIV 1 e 2, soro', 'laboratorio',
            'PrEP: teste de HIV (de preferência teste rápido) 30 dias após o início e em toda consulta, a cada 120 dias; '
            'obrigatório para dispensar a medicação.', 'PrEP | A cada 4 meses', PCDT_PREP, 'A', 'alta')
        add('Sífilis: teste treponêmico ou VDRL, soro', 'laboratorio', 'PrEP: teste para sífilis a cada 120 dias.',
            'PrEP | A cada 4 meses', PCDT_PREP, 'A', 'alta')
        add('Anticorpos anti-HCV, soro', 'laboratorio', 'PrEP: anti-HCV a cada 120 dias se o anterior foi não reagente '
            '(o texto do PCDT fala em a cada 3 meses).', 'PrEP | A cada 4 meses', PCDT_PREP, 'B')
        for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBs, soro'):
            add(titulo, 'laboratorio', 'PrEP: HBsAg e anti-HBs anuais, conforme a avaliação inicial; vacinar quem não é imune.',
                'PrEP | Anual', PCDT_PREP, 'B')
        add('Clamídia e gonococo, PCR (urina ou swab)', 'laboratorio',
            'PrEP: teste molecular para clamídia e gonococo a cada 6 meses (antes, se houver sintomas).',
            'PrEP | A cada 6 meses', PCDT_PREP, 'B')
        clcr = _clcr(idade, sexo, peso, creatinina)
        risco_renal = idade >= 50 or diabetico or hipertenso or 'doenca_renal' in com or clcr is None or clcr < 90
        add('Creatinina, soro', 'laboratorio',
            'PrEP: creatinina com clearance a cada 12 meses abaixo de 50 anos, sem comorbidade e com ClCr ≥ 90 mL/min; a cada '
            '6 meses a partir de 50 anos, com hipertensão, diabetes ou ClCr < 90 (ou sem ClCr calculado).',
            'PrEP | ' + ('A cada 6 meses' if risco_renal else 'Anual'), PCDT_PREP, 'B')
        if sexo == 'feminino' and idade <= 50 and not gestante:
            add('Beta-hCG, soro', 'laboratorio', 'PrEP em quem pode engravidar: teste de gravidez a cada 120 dias ou quando necessário.',
                'PrEP | A cada 4 meses', PCDT_PREP, 'B')
    if {'oncologico', 'antraciclina', 'anti_her2', 'inibidor_checkpoint', 'fluoropirimidina'} & med:
        add('HBsAg, anti-HBc total e anti-HBs', 'laboratorio',
            'Tratamento sistêmico do câncer: HBsAg, anti-HBc total e anti-HBs antes de iniciar (risco de reativação da '
            'hepatite B).', 'Câncer em tratamento | Antes do tratamento', ASCO_HBV, 'B', 'alta')
    if {'antraciclina', 'anti_her2'} & med:
        for titulo in ('Ecocardiograma transtorácico', 'Eletrocardiograma de repouso'):
            add(titulo, 'imagem', 'Antraciclina ou terapia anti-HER2: ecocardiograma (com strain, se disponível) e ECG antes '
                'de iniciar; na terapia anti-HER2, ecocardiograma a cada 3 meses durante o tratamento e 12 meses após o fim.',
                'Antraciclina ou anti-HER2 | Antes do tratamento', ESC_ONCO, 'A', 'alta')
        for titulo in ('Troponina, soro', 'Peptídeo natriurético BNP/PROBNP'):
            add(titulo, 'laboratorio', 'Antraciclina ou terapia anti-HER2: troponina e peptídeo natriurético basais para '
                'estratificar o risco de cardiotoxicidade e comparar no seguimento.',
                'Antraciclina ou anti-HER2 | Antes do tratamento', ESC_ONCO, 'B', 'alta')
    if 'anti_her2' in med:
        add('Ecocardiograma transtorácico', 'imagem', 'Terapia anti-HER2: ecocardiograma a cada 3 meses durante o tratamento.',
            'Em terapia anti-HER2 | A cada 3 meses', ESC_ONCO, 'A', 'alta')
    if 'inibidor_checkpoint' in med:
        for titulo, categoria in (('Eletrocardiograma de repouso', 'imagem'), ('Troponina, soro', 'laboratorio'),
                                  ('Peptídeo natriurético BNP/PROBNP', 'laboratorio')):
            add(titulo, categoria, 'Inibidor de checkpoint: ECG, troponina e peptídeo natriurético antes de iniciar '
                '(miocardite imunomediada).', 'Inibidor de checkpoint | Antes do tratamento', ESC_ONCO, 'A', 'alta')
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'T4 livre, soro', 'Glicose, soro'):
            add(titulo, 'laboratorio', 'Inibidor de checkpoint: TSH, T4 livre e glicemia no início e a cada 4-6 semanas '
                'durante o tratamento (tireoidite, hipofisite, diabetes imunomediado).',
                'Inibidor de checkpoint | A cada 4-6 semanas', ASCO_IRAE, 'B', 'alta')
    if 'fluoropirimidina' in med:
        add('Genotipagem do gene DPYD (deficiência de DPD)', 'laboratorio',
            'Fluoruracila ou capecitabina: testar deficiência de DPD (genotipagem do DPYD ou uracilemia) antes de iniciar; '
            'deficiência completa contraindica, parcial pede dose inicial menor.', 'Fluoropirimidina | Antes do tratamento',
            EMA_DPD, 'A', 'alta')
    if 'bloqueio_hormonal' in med:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Bloqueio hormonal com agonista ou antagonista de GnRH: densitometria no início e periodicamente (perda óssea '
            'acelerada pela queda dos hormônios sexuais).', 'Agonista ou antagonista de GnRH | Antes do tratamento', NCCN_OSSO, 'B')
        if sexo == 'masculino':
            for titulo in ('Glicose, soro', 'Colesterol total e frações, soro'):
                add(titulo, 'laboratorio', 'Bloqueio androgênico: pressão arterial, perfil lipídico e glicemia antes de '
                    'iniciar (resistência insulínica, dislipidemia e risco cardiovascular).',
                    'Bloqueio androgênico | Antes do tratamento', AHA_ADT, 'B')
    # Antirreumáticos sintéticos (BSR 2017): hemograma, TGO/TGP, creatinina e albumina a cada 2 semanas até 6 semanas de
    # dose estável, depois mensal por 3 meses e então pelo menos a cada 12 semanas (relatório D, D-16, D-17, D-21).
    painel_dmard = ('Hemograma completo com plaquetas', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro',
                    'Creatinina, soro', 'Albumina, soro')
    for classe in ('metotrexato', 'leflunomida', 'azatioprina', 'sulfassalazina'):
        if classe not in med:
            continue
        nome = MEDICACOES[classe]['rotulo'].lower()
        for titulo in painel_dmard:
            add(titulo, 'laboratorio', f'Monitorização de toxicidade em uso de {nome}: a cada 2 semanas até completar 6 semanas '
                'com dose estável, depois mensal por 3 meses e então pelo menos a cada 12 semanas; repetir o ciclo a cada '
                'aumento de dose.', f'Em uso de {nome} | A cada 2-12 semanas', BSR, 'B')
        if classe in ('metotrexato', 'leflunomida'):
            for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro', 'Anticorpos anti-HCV, soro'):
                add(titulo, 'laboratorio', f'Antes de iniciar {nome}: rastrear hepatites B e C (HIV conforme o risco).',
                    f'Em uso de {nome} | Avaliação inicial', BSR, 'B')
        if classe == 'metotrexato':
            add('Radiografia de tórax', 'imagem', 'Metotrexato: radiografia de tórax antes de iniciar, se não houver uma dos '
                'últimos 6 meses (referência para pneumonite).', 'Em uso de metotrexato | Avaliação inicial', BSR, 'C')
        if classe == 'azatioprina':
            add('Atividade da TPMT ou genotipagem TPMT/NUDT15', 'laboratorio',
                'Azatioprina: atividade da TPMT (ou genotipagem de TPMT e NUDT15) antes de iniciar; atividade baixa pede dose '
                'reduzida e ausente contraindica.', 'Em uso de azatioprina | Antes do tratamento', BSR + ' / ' + CPIC_TIOPURINA,
                'A', 'alta')
    if 'inibidor_calcineurina' in med:
        for titulo in ('Creatinina, soro', 'Potássio, soro', 'Magnésio, soro'):
            add(titulo, 'laboratorio', 'Monitorização de toxicidade em uso de ciclosporina ou tacrolimo.',
                'Em uso de ciclosporina ou tacrolimo | A cada 1-3 meses', 'KDIGO 2009 (transplante)', 'B')
    if 'bisfosfonato_longo' in med:
        add('Densitometria óssea (DEXA)', 'imagem',
            'Bisfosfonato por 5 anos (oral) ou 3 anos (ácido zoledrônico): densitometria para decidir entre pausa e continuidade.',
            'Bisfosfonato por tempo prolongado | Reavaliação', 'ASBMR 2016', 'B')
    if 'litio' in med:
        # NICE CG185 (2014, atualizada em 2023), 1.10: litemia a cada 3 meses no 1º ano e depois a cada 6 meses;
        # a cada 3 meses em idosos, com fármaco que interage (IECA/BRA, diuréticos, AINE), com última litemia
        # ≥ 0,8 mmol/L, má adesão ou mau controle. Peso, ureia e eletrólitos com cálcio, TFG e TSH a cada 6 meses.
        # IECA/BRA (inclui sacubitril/valsartana) e diuréticos (tiazídico, de alça, poupador de potássio).
        frequente = idade >= 65 or bool({'ieca_bra', 'arni', 'tiazidico', 'diuretico_alca', 'espironolactona'} & med)
        add('Lítio, soro', 'laboratorio',
            'Litemia com coleta 12 horas após a última dose (aceitável de 10 a 14 h, sempre no mesmo intervalo). Alvo de '
            'manutenção em geral de 0,6 a 0,8 mmol/L. ' + (
                'A cada 3 meses: 65 anos ou mais, ou uso de IECA/BRA ou diurético (risco maior de intoxicação). ' if frequente
                else 'A cada 6 meses após o primeiro ano; a cada 3 meses no primeiro ano de uso. ') +
            'Antecipar se houver sinais de toxicidade, desidratação, piora da função renal, início de fármaco que '
            'interage ou última litemia ≥ 0,8 mmol/L.',
            'Em uso de lítio | ' + ('A cada 3 meses' if frequente else 'A cada 6 meses'), 'NICE CG185 (2023)', 'B', 'alta')
        for titulo, texto in (
                ('Hormônio Tireoestimulante (TSH), soro', 'Lítio: TSH a cada 6 meses (hipotireoidismo induzido pelo lítio).'),
                ('Creatinina, soro', 'Lítio: creatinina com TFG estimada a cada 6 meses; mais vezes se a TFG cair.'),
                ('Ureia, soro', 'Lítio: ureia e eletrólitos a cada 6 meses.'),
                ('Sódio, soro', 'Lítio: sódio a cada 6 meses (hiponatremia eleva a litemia).'),
                ('Cálcio iônico, soro', 'Lítio: cálcio a cada 6 meses (hiperparatireoidismo e hipercalcemia associados ao lítio).')):
            add(titulo, 'laboratorio', texto, 'Em uso de lítio | A cada 6 meses', 'NICE CG185 (2023)', 'B')
        orientar('Lítio: frequência da litemia',
                 'Primeiro ano de uso: litemia a cada 3 meses (antes disso, 1 semana após o início e após cada ajuste de '
                 'dose até estabilizar). Depois, a cada 6 meses, ou a cada 3 meses em idosos, com IECA/BRA, diuréticos ou '
                 'AINE, com última litemia ≥ 0,8 mmol/L, má adesão ou mau controle. Peso ou IMC a cada 6 meses. ECG no '
                 'início se houver doença ou risco cardiovascular.', 'NICE CG185 (2023)')
    if 'digoxina' in med:
        orientar('Digoxina: nível sérico não é rotineiro',
                 'Dosar a digoxinemia (no vale, pelo menos 6 h após a dose) se houver suspeita de toxicidade, piora da função '
                 'renal, início de fármaco que interage (amiodarona, verapamil, diltiazem, claritromicina) ou ajuste de dose. '
                 'Na insuficiência cardíaca, manter 0,5-0,9 ng/mL: concentrações ≥ 1,0 ng/mL associaram-se a maior '
                 'mortalidade. Conferir potássio e função renal, que alteram o risco de toxicidade.',
                 'AHA/ACC/HFSA 2022 / DIG (Rathore, JAMA 2003)')
    if {'valproato', 'carbamazepina', 'fenitoina', 'fenobarbital'} & med:
        orientar('Anticonvulsivantes: nível sérico só com indicação',
                 'Valproato, carbamazepina, fenitoína e fenobarbital: a dosagem sérica de rotina não é recomendada. Dosar se houver suspeita '
                 'de má adesão ou de toxicidade, ajuste de dose de fenitoína, interação farmacocinética ou situações '
                 'especiais (gestação, insuficiência renal ou hepática). Indicar na requisição o horário da última dose.',
                 'NICE NG217 (2022)')
    if sexo == 'feminino' and idade <= 55 and not gestante:
        if 'valproato' in med:
            orientar('Valproato em mulher que pode engravidar',
                     'Programa de prevenção da gravidez: teste de gravidez antes de iniciar e quando necessário, contracepção '
                     'eficaz durante todo o uso e revisão anual da indicação por especialista (risco de malformação e de '
                     'alteração do neurodesenvolvimento).', EMA_VALPROATO + ' / NICE NG217 (2022)')
        if {'carbamazepina', 'fenitoina', 'fenobarbital'} & med:
            orientar('Anticonvulsivante indutor enzimático e contracepção',
                     'Carbamazepina, fenitoína e fenobarbital reduzem a eficácia de contraceptivos hormonais orais, do adesivo, '
                     'do anel e do implante: preferir DIU (cobre ou levonorgestrel) ou injetável trimestral.', 'NICE NG217 (2022)')
    if 'transplante' in com:
        for classe, titulo in (('tacrolimo', 'Tacrolimo, sangue total (nível de vale)'),
                               ('ciclosporina', 'Ciclosporina, sangue total (nível de vale)')):
            if classe in med:
                add(titulo, 'laboratorio',
                    f'Transplantado em uso de {MEDICACOES[classe]["rotulo"].lower()}: nível de vale (C0, antes da dose), com '
                    'alvo definido pela equipe de transplante. Repetir também após mudança de medicação que interage e '
                    'na piora da função renal.', f'Transplante em uso de {MEDICACOES[classe]["rotulo"].lower()} | '
                    'A cada 1-3 meses', 'KDIGO 2009 (transplante renal)', 'B', 'alta')
    if 'amiodarona' in med:
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'):
            add(titulo, 'laboratorio', 'Toxicidade tireoidiana e hepática da amiodarona.', 'Em uso de amiodarona | A cada 6 meses',
                'HRS 2007 (Goldschlager)', 'B')
        add('T4 livre, soro', 'laboratorio', 'Amiodarona: TSH e T4 livre antes de iniciar e a cada 6 meses (hipo e '
            'hipertireoidismo).', 'Em uso de amiodarona | A cada 6 meses', 'HRS 2007 (Goldschlager)', 'B')
        add('Radiografia de tórax', 'imagem', 'Amiodarona: radiografia de tórax antes de iniciar e anual (toxicidade pulmonar).',
            'Em uso de amiodarona | Anual', 'HRS 2007 (Goldschlager)', 'B')
        add('Prova de função pulmonar completa com difusão (DLCO)', 'imagem',
            'Amiodarona: prova de função pulmonar com DLCO antes de iniciar (referência para tosse ou dispneia novas).',
            'Em uso de amiodarona | Basal', 'HRS 2007 (Goldschlager)', 'B')
        if 'varfarina' in med:
            orientar('Amiodarona com varfarina',
                     'A amiodarona potencializa a varfarina: reduzir empiricamente a dose da varfarina ao iniciar a amiodarona e '
                     'medir o INR semanalmente nas primeiras 6-8 semanas.', 'HRS 2007 (Goldschlager)')

    # ---------------- Comorbidades ----------------
    com_tipo = bool(set(TIPOS_DE_DIABETES) & com)
    if 'diabetes_sem_tipo' in com:
        orientar('HbA1c ≥ 6,5%: informe o tipo de diabetes',
                 'HbA1c ≥ 6,5% é critério de diabetes (confirmar com um segundo exame se não houver hiperglicemia inequívoca), '
                 'mas não define o tipo. As recomendações foram montadas como para uma pessoa com diabetes. Com o tipo marcado, '
                 'elas ficam mais precisas (por exemplo, TSH no tipo 1).', 'ADA 2026')
    if 'insulina' in med and not com_tipo:
        orientar('Insulina em uso: informe o tipo de diabetes',
                 'A insulina é usada no diabetes tipo 1, no tipo 2, no gestacional e em outros tipos; por isso não marca um tipo '
                 'sozinha. As recomendações foram montadas como para uma pessoa com diabetes. Com o tipo marcado, elas ficam '
                 'mais precisas (por exemplo, TSH no tipo 1).', 'ADA 2026')
    if 'diabetes_gestacional_previo' in com and sexo == 'feminino' and not gestante and not diabetico:
        for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
            add(titulo, 'laboratorio',
                'Diabetes gestacional em gestação anterior: rastrear pré-diabetes e diabetes por toda a vida, pelo menos a cada 3 anos.',
                'Diabetes gestacional prévio | Pelo menos a cada 3 anos', 'ADA 2026', 'B', 'alta')
    if 'pre_diabetes' in com:
        add('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'Pré-diabetes: reavaliar a glicemia ao menos uma vez por ano.',
            'Pré-diabetes | Anual', 'ADA 2026', 'B')
    if 'cirurgia_bariatrica' in com:
        for titulo in ('Hemograma completo com plaquetas', 'Ferritina, soro', 'Vitamina B12, soro', 'Ácido fólico, soro',
                       '25-hidroxivitamina D, soro', 'Cálcio iônico, soro', 'Paratormônio (PTH), soro'):
            add(titulo, 'laboratorio', 'Após cirurgia bariátrica: rastreamento anual de deficiências nutricionais '
                '(ferro, B12, folato, vitamina D, cálcio e PTH).', 'Cirurgia bariátrica prévia | Anual', 'ASMBS 2019', 'B')
    if 'hepatite_c' in com or 'hepatite_b_cronica' in com:
        if idade >= 60:
            vacina_hepatopatia_60()
        else:
            add('Hepatites A e B (Twinrix® ou vacinas isoladas)', 'vacina',
                'Hepatite viral crônica: vacinar os suscetíveis contra hepatite A (e contra hepatite B, na hepatite C).',
                'Hepatopatia crônica | Suscetíveis', SBIM, 'A', 'alta')
    if 'masld' in com:
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Hemograma completo com plaquetas'):
            add(titulo, 'laboratorio', texto_fib4(idade), 'MASLD | FIB-4 a cada 1-2 anos', AASLD_MASLD + ' / ' + ADA_FIGADO, 'B')
    # Fibrose hepática pelo FIB-4 mesmo com enzimas normais (relatório D, D-22 e D-24): diabetes tipo 2 e outros tipos
    # e pré-diabetes (ADA 2026, seção 4); diabetes tipo 1 só com obesidade ou MASLD; obesidade com mais um fator
    # metabólico (AASLD 2023: 2 ou mais fatores de risco metabólico).
    so_dm1 = 'diabetes_tipo_1' in com and not (set(TIPOS_DE_DIABETES) - {'diabetes_tipo_1'}) & com
    metabolicos = hipertenso or 'dislipidemia' in com or hipolipemiante or 'pre_diabetes' in com or diabetico
    fib4 = None
    if (diabetico and not so_dm1) or 'pre_diabetes' in com:
        fib4 = ('Diabetes tipo 2 ou pré-diabetes', ADA_FIGADO + ' / ' + AASLD_MASLD)
    elif diabetico and (obeso or 'masld' in com):
        fib4 = ('Diabetes tipo 1 com obesidade ou MASLD', ADA_FIGADO + ' / ' + AASLD_MASLD)
    elif obeso and metabolicos:
        fib4 = ('Obesidade com fator de risco metabólico', AASLD_MASLD)
    if fib4:
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Hemograma completo com plaquetas'):
            add(titulo, 'laboratorio', texto_fib4(idade), f'{fib4[0]} | FIB-4 a cada 1-2 anos', fib4[1], 'B')
    if diabetico:
        orientar('Diabetes: exame dos pés',
                 'Avaliação completa dos pés pelo menos uma vez por ano: inspeção, pulsos pediosos, monofilamento de 10 g e mais um '
                 'teste de sensibilidade (vibração com diapasão de 128 Hz, pinprick ou reflexo aquileu); a cada consulta se houver '
                 'perda de sensibilidade, deformidade ou úlcera prévia.', ADA_PES)
    if so_dm1:
        orientar('Diabetes tipo 1: quando começar a uACR',
                 'No tipo 1, a uACR e a TFG anuais começam 5 anos após o diagnóstico (no tipo 2, desde o diagnóstico). Não temos '
                 'como saber a duração do diabetes: a uACR pode ser retirada se o diagnóstico tiver menos de 5 anos e não houver outra indicação.',
                 'ADA 2026 (seção 11)')
    if 'diabetes_tipo_1' in com:
        for titulo in ('Anticorpo antitransglutaminase tecidual IgA, soro', 'Imunoglobulina A (IgA), soro'):
            add(titulo, 'laboratorio', 'Diabetes tipo 1: rastrear doença celíaca (antitransglutaminase IgA com IgA total) logo após o '
                'diagnóstico; repetir se houver sintomas, crescimento ou glicemia instáveis ou parente de 1º grau com doença celíaca.',
                'Diabetes tipo 1 | Avaliação inicial', ADA_FIGADO, 'B')
    if 'cirrose' in com:
        add('Ultrassonografia de abdome superior', 'imagem',
            'Cirrose: rastreamento de carcinoma hepatocelular com ultrassonografia a cada 6 meses (com ou sem alfafetoproteína).',
            'Cirrose | A cada 6 meses', 'AASLD 2023', 'A', 'alta')
        if idade >= 60:
            vacina_hepatopatia_60()
        else:
            add('Hepatites A e B (Twinrix® ou vacinas isoladas)', 'vacina',
                'Hepatopatia crônica: vacinar contra hepatites A e B os suscetíveis, em qualquer idade.',
                'Hepatopatia crônica | Suscetíveis', SBIM, 'A', 'alta')
    if 'osteoporose' in com:
        add('Densitometria óssea (DEXA)', 'imagem', 'Seguimento de osteoporose em tratamento.', 'Osteoporose | A cada 1-2 anos',
            'BHOF 2022', 'B')
        add('25-hidroxivitamina D, soro', 'laboratorio', 'Manter 25(OH)D ≥ 30 ng/mL em osteoporose.', 'Osteoporose',
            'BHOF 2022', 'B')
        # Causas secundárias só no diagnóstico (relatório D, D-37): detalhe "diagnóstico recente" do item.
        if 'osteoporose_diagnostico' in com:
            for titulo in ('Cálcio iônico, soro', 'Fósforo, soro', 'Creatinina, soro', 'Fosfatase alcalina, soro',
                           'Paratormônio (PTH), soro'):
                add(titulo, 'laboratorio', 'Osteoporose: investigar causas secundárias no diagnóstico (cálcio, fósforo, função '
                    'renal, fosfatase alcalina e PTH) antes de iniciar o tratamento.', 'Osteoporose | Avaliação inicial', 'BHOF 2022', 'B')
        else:
            orientar('Osteoporose: causas secundárias',
                     'As causas secundárias (cálcio, fósforo, função renal, fosfatase alcalina e PTH) se investigam no diagnóstico, '
                     'antes de iniciar o tratamento. Se ainda não foram investigadas, marque o detalhe "diagnóstico recente" do item.',
                     'BHOF 2022')
    if 'gota' in com:
        add('Ácido úrico, soro', 'laboratorio', 'Tratamento por alvo: ácido úrico < 6 mg/dL.', 'Gota | Alvo < 6 mg/dL',
            'ACR 2020', 'A')
    if 'gota' in com:
        add('Creatinina, soro', 'laboratorio', 'Gota: função renal para a dose do hipouricemiante e para a escolha do '
            'anti-inflamatório da crise.', 'Gota | Periódico', 'ACR 2020', 'B')
        orientar('Gota: comorbidades', 'Sugerimos rastrear e tratar hipertensão, diabetes, dislipidemia, obesidade e doença renal, '
                 'frequentes na gota, e evitar diurético para tratar a hipertensão quando houver alternativa.', 'ACR 2020 / ' + EULAR_CV_DRM)

    # ---------------- Doenças inflamatórias imunomediadas: cada uma com o seu acompanhamento ----------------
    articulares = [c for c in ('artrite_reumatoide', 'artrite_psoriasica', 'espondiloartrite') if c in com]
    if articulares:
        nomes = ', '.join(COMORBIDADES[c]['rotulo'] for c in articulares)
        add('Colesterol total e frações, soro', 'laboratorio',
            'Artrite inflamatória: risco cardiovascular aumentado. Avaliar o risco (lipídios, pressão arterial, glicemia e '
            'tabagismo) pelo menos a cada 5 anos e após mudança importante do tratamento, com os lipídios dosados com a '
            'doença estável ou em remissão.', f'{nomes} | A cada 5 anos', EULAR_CV_ARTRITES, 'B')
    if 'artrite_reumatoide' in com:
        orientar('Artrite reumatoide: pulmão e osso',
                 'Com fator de risco para doença pulmonar intersticial (tabagismo, sexo masculino, idade mais avançada, fator '
                 'reumatoide ou anti-CCP em título alto, doença ativa), rastrear com prova de função pulmonar com difusão (DLCO) '
                 'e tomografia de tórax de alta resolução. A artrite reumatoide entra no cálculo do FRAX.', ACR_CHEST_DPI)
    if 'lupus' in com:
        for titulo in ('Hemograma completo com plaquetas', 'VHS', 'Proteína C reativa, soro', 'Albumina, soro',
                       'Creatinina, soro', 'Urina tipo I (EAS)'):
            add(titulo, 'laboratorio', 'Lúpus sem atividade: hemograma, VHS, PCR, albumina, creatinina e urina tipo I a cada '
                '6-12 meses; mais vezes com atividade, dano ou conforme o tratamento.',
                'Lúpus eritematoso sistêmico | A cada 6-12 meses', EULAR_LES, 'C', 'alta')
        if 'les_nefrite' not in com:
            add('Relação proteína/creatinina, urina', 'laboratorio',
                'Lúpus sem nefrite conhecida: rastrear proteinúria pelo menos a cada 6-12 meses e em toda reativação fora do rim.',
                'Lúpus eritematoso sistêmico | A cada 6-12 meses', ACR_NEFRITE, 'A', 'alta')
        else:
            add('Relação proteína/creatinina, urina', 'laboratorio',
                'Nefrite lúpica: quantificar a proteinúria pelo menos a cada 3 meses até a remissão completa e a cada 3-6 meses '
                'na remissão mantida.', 'Nefrite lúpica | A cada 3 meses', ACR_NEFRITE, 'A', 'alta')
        for titulo in ('Complemento C3', 'Complemento C4', 'Anti-DNA'):
            if 'les_nefrite' in com:
                # ACR 2024, boa prática: complemento e anti-dsDNA em cada consulta, não mais que mensalmente (REUM-01)
                add(titulo, 'laboratorio', 'Nefrite lúpica: complemento (C3, C4) e anti-dsDNA em cada consulta de acompanhamento, '
                    'não mais que uma vez por mês.', 'Nefrite lúpica | Em cada consulta, no máximo mensal', ACR_NEFRITE, 'C')
            else:
                add(titulo, 'laboratorio', 'Lúpus: complemento (C3, C4) e anti-DNA ajudam a confirmar atividade ou remissão.',
                    'Lúpus eritematoso sistêmico | Conforme indicação clínica', EULAR_LES, 'C')
        for titulo in ('Anticardiolipina - IgG', 'Anticardiolipina - IgM', 'Anticorpos Beta 2 glicoproteina I - IgG/IgM/IgA',
                       'Anticoagulante lúpico, pesquisa'):
            add(titulo, 'laboratorio', 'Lúpus: anticorpos antifosfolípides na avaliação inicial e de novo antes de gestação, '
                'cirurgia, estrogênio ou após evento vascular, se antes negativos.',
                'Lúpus eritematoso sistêmico | Avaliação inicial', EULAR_LES, 'C')
        for titulo in ('Colesterol total e frações, soro', 'Glicose, soro'):
            add(titulo, 'laboratorio', 'Lúpus: lipídios e glicemia anuais, com pressão arterial e IMC (risco cardiovascular).',
                'Lúpus eritematoso sistêmico | Anual', EULAR_LES + ' / ' + EULAR_CV_DRM, 'C')
        for titulo in ('Anti-HIV 1 e 2, soro', 'Anticorpos anti-HCV, soro', 'HBsAg, anti-HBc total e anti-HBs'):
            add(titulo, 'laboratorio', 'Lúpus: rastrear HIV e hepatites B e C (e tuberculose latente) antes de imunossupressor.',
                'Lúpus eritematoso sistêmico | Antes do tratamento', EULAR_LES + ' / ' + EULAR_INFECCOES, 'B')
        orientar('Lúpus: pressão arterial e olhos',
                 'Considerar alvo de pressão arterial < 130/80 mmHg. Hidroxicloroquina para todos, salvo contraindicação, também '
                 'pela proteção cardiovascular; exame oftalmológico conforme o uso de antimalárico e de corticoide.',
                 EULAR_CV_DRM + ' / ' + EULAR_LES)
    if {'psoriase', 'artrite_psoriasica'} & com:
        extensa = 'psoriase_extensa' in com
        add('Colesterol total e frações, soro', 'laboratorio',
            'Psoríase: dosar os lipídios e rastrear hipertensão e diabetes como na população geral'
            + ('; mais cedo e com mais frequência na psoríase extensa (> 10% da superfície corporal) ou com indicação de '
               'tratamento sistêmico ou fototerapia.' if extensa else '.'),
            ('Psoríase extensa ou com tratamento sistêmico' if extensa else 'Psoríase') + ' | Fator de risco', AAD_PSORIASE, 'B')
        if extensa:
            for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
                add(titulo, 'laboratorio', 'Psoríase extensa (> 10% da superfície corporal) ou com indicação de tratamento '
                    'sistêmico ou fototerapia: rastreio de diabetes mais cedo e com mais frequência.',
                    'Psoríase extensa ou com tratamento sistêmico | Fator de risco', AAD_PSORIASE, 'B')
        if 'psoriase' in com:
            orientar('Psoríase: comorbidades',
                     'Perguntar por dor ou rigidez articular em toda consulta (artrite psoriásica), rastrear depressão e '
                     'ansiedade e orientar sobre tabagismo e álcool.', AAD_PSORIASE)
    for chave, nome, alem_reto, oito_anos, cep in (
            ('doenca_crohn', 'Doença de Crohn', 'crohn_colon', 'crohn_8_anos', 'crohn_cep'),
            ('retocolite', 'Retocolite ulcerativa', 'rcu_alem_reto', 'rcu_8_anos', 'rcu_cep')):
        if chave not in com:
            continue
        for titulo in ('Hemograma completo com plaquetas', 'Ferritina, soro', 'Proteína C reativa, soro'):
            add(titulo, 'laboratorio', 'Doença inflamatória intestinal em remissão ou leve: hemograma, ferritina e PCR a cada '
                '6-12 meses para anemia e ferropenia (a cada 3 meses com doença ativa).', f'{nome} | A cada 6-12 meses',
                ECCO_ANEMIA, 'C')
        extensao = 'Crohn com 1/3 ou mais do cólon' if chave == 'doenca_crohn' else 'colite além do reto'
        if cep in com:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                f'{nome} com colangite esclerosante primária: colonoscopia de vigilância anual desde o diagnóstico da colangite, '
                'com cromoscopia.', f'{nome} com colangite esclerosante | Anual', BSG_DII, 'A', 'alta', substituir=True)
        elif alem_reto in com and oito_anos in com:
            add('Colonoscopia de Rastreio com ou sem biópsia', 'imagem',
                f'{nome} ({extensao}) há 8 anos ou mais: colonoscopia de vigilância com cromoscopia; a seguinte em 1, 3 '
                'ou 5 anos conforme o risco (inflamação, displasia prévia, estenose, pseudopólipos, câncer colorretal em '
                'parente de 1º grau).', f'{nome} há 8 anos ou mais | A cada 1-5 anos', BSG_DII, 'A', 'alta', substituir=True)
        else:
            orientar(f'{nome}: colonoscopia de vigilância',
                     'Primeira colonoscopia de vigilância 8 anos após o início dos sintomas (logo no diagnóstico, se houver '
                     f'colangite esclerosante primária) quando houver {extensao}; o intervalo seguinte depende do risco. '
                     'Com os detalhes do item marcados, calculamos o intervalo.', BSG_DII)
        if chave == 'doenca_crohn' and 'crohn_delgado' in com:
            for titulo in ('Vitamina B12, soro', 'Ácido fólico, soro'):
                add(titulo, 'laboratorio', 'Crohn de intestino delgado ou ressecção ileal: vitamina B12 e ácido fólico pelo '
                    'menos uma vez por ano.', 'Crohn de delgado ou ressecção ileal | Anual', ECCO_ANEMIA, 'C')
    if {'doenca_crohn', 'retocolite'} & com:
        orientar('Doença inflamatória intestinal: prevenção',
                 'Exame da pele para melanoma em todos (e para câncer de pele não melanoma em uso de tiopurina); densitometria '
                 'com fator de risco (corticoide por 3 meses ou mais, pós-menopausa, baixo peso); rastrear depressão e '
                 'ansiedade; parar de fumar; vacinas antes de imunossupressor.', ACG_DII)
    if 'esclerose_sistemica' in com:
        for titulo in ('Ecocardiograma transtorácico', 'Peptídeo natriurético BNP/PROBNP',
                       'Prova de função pulmonar completa com difusão (DLCO)'):
            add(titulo, 'laboratorio' if 'Peptídeo' in titulo else 'imagem',
                'Esclerose sistêmica: avaliação anual do risco de hipertensão arterial pulmonar (ecocardiograma, prova de função '
                'pulmonar com difusão e NT-proBNP; algoritmo DETECT se mais de 3 anos de doença, CVF ≥ 40% e DLCO < 60%).',
                'Esclerose sistêmica | Anual', ESC_ERS_HP, 'A', 'alta')
        add('Tomografia computadorizada de tórax de alta resolução', 'imagem',
            'Esclerose sistêmica: rastrear doença pulmonar intersticial com tomografia de alta resolução e prova de função '
            'pulmonar; com doença intersticial, prova de função a cada 3-6 meses no primeiro ano.',
            'Esclerose sistêmica | Avaliação inicial', ACR_CHEST_DPI, 'B', 'alta')
    if LEGADO_AUTOIMUNE in com:
        orientar('Doença inflamatória autoimune: especifique',
                 'O item antigo reunia doenças com acompanhamento diferente. Sugerimos escolher na lista a doença (artrite reumatoide, '
                 'lúpus, psoríase, artrite psoriásica, espondiloartrite, Crohn, retocolite ou esclerose sistêmica).', EULAR_CV_ARTRITES)

    # ---------------- Hepatites virais crônicas ----------------
    if 'hepatite_b_cronica' in com:
        for titulo in ('Alanina aminotransferase, soro', 'Carga viral da hepatite B (HBV-DNA quantitativo), plasma'):
            add(titulo, 'laboratorio', 'Hepatite B crônica: ALT e HBV-DNA a cada 6-12 meses fora de tratamento (a cada 3 meses no '
                'primeiro ano de acompanhamento ou com ALT alterada) e a cada 3-6 meses em tratamento.',
                'Hepatite B crônica | A cada 6-12 meses', AASLD_HBV, 'B', 'alta')
        for titulo in ('Hepatite B - HBeAG (antígeno "E")', 'Hepatite B - HBeAC (anti HBE)'):
            add(titulo, 'laboratorio', 'Hepatite B crônica: HBeAg e anti-HBe definem a fase da infecção.',
                'Hepatite B crônica | Avaliação inicial', AASLD_HBV, 'B')
        for titulo in ('Anticorpos anti-HCV, soro', 'Anti-HIV 1 e 2, soro', 'Anticorpos anti-HAV IgG, soro'):
            add(titulo, 'laboratorio', 'Hepatite B crônica: testar coinfecção por HCV e HIV e imunidade contra hepatite A '
                '(vacinar se suscetível).', 'Hepatite B crônica | Avaliação inicial', AASLD_HBV, 'B')
        # OMS 2024: anti-HDV para toda pessoa com HBsAg reagente (revisão externa, HEP-02)
        add('Hepatite delta, anticorpo IgG', 'laboratorio', 'Hepatite B crônica: anti-HDV em toda pessoa com HBsAg reagente; '
            'reagente, pedir o HDV-RNA (hepatite delta acelera a fibrose e o carcinoma hepatocelular).',
            'Hepatite B crônica | Avaliação inicial', OMS_HBV, 'B')
        # AASLD/IDSA 2025, rec. 8 (condicional): HBV com HIV, vigilância de CHC em homens ≥ 18 e mulheres ≥ 40 (HEP-01)
        if 'hiv' in com and 'cirrose' not in com and 'hbv_risco_chc' not in com and (
                (sexo == 'masculino' and idade >= 18) or (sexo == 'feminino' and idade >= 40)):
            add('Ultrassonografia de abdome superior', 'imagem',
                'Hepatite B com HIV: vigilância de carcinoma hepatocelular com ultrassonografia a cada 6 meses (com ou sem '
                'alfafetoproteína) em homens a partir de 18 anos e mulheres a partir de 40, mesmo sem cirrose; recomendação '
                'condicional.', 'Hepatite B com HIV | A cada 6 meses', AASLD_HBV_2025, 'C', 'alta')
        if 'hbv_risco_chc' in com and 'cirrose' not in com:
            add('Ultrassonografia de abdome superior', 'imagem',
                'Hepatite B com alto risco de carcinoma hepatocelular, mesmo sem cirrose: ultrassonografia a cada 6 meses, com '
                'ou sem alfafetoproteína.', 'Hepatite B de alto risco | A cada 6 meses', AASLD_HBV, 'B', 'alta')
        orientar('Hepatite B: estadiamento e carcinoma hepatocelular',
                 'Estadiar a fibrose (FIB-4 ou elastografia). Rastreio de carcinoma hepatocelular com ultrassonografia a cada '
                 '6 meses na cirrose e, sem cirrose, com história familiar de CHC, coinfecção por HIV ou hepatite D, homem '
                 'asiático ≥ 40 anos, mulher asiática ≥ 50 anos ou origem africana subsaariana.', AASLD_HBV)
    if 'hepatite_c' in com:
        add('Carga viral da hepatite C (HCV-RNA quantitativo), plasma', 'laboratorio',
            'Hepatite C: HCV-RNA confirma a viremia antes do tratamento e, 12 semanas após o fim, a resposta virológica '
            'sustentada (cura).', 'Hepatite C | Avaliação inicial', AASLD_HCV, 'A', 'alta')
        add('HBsAg, anti-HBc total e anti-HBs', 'laboratorio',
            'Hepatite C: HBsAg, anti-HBc e anti-HBs antes do antiviral de ação direta (risco de reativação da hepatite B); '
            'vacinar contra hepatite B se suscetível.', 'Hepatite C | Antes do tratamento', AASLD_HCV, 'A', 'alta')
        for titulo in ('Anti-HIV 1 e 2, soro', 'Anticorpos anti-HAV IgG, soro'):
            add(titulo, 'laboratorio', 'Hepatite C: testar HIV e imunidade contra hepatite A (vacinar se suscetível).',
                'Hepatite C | Avaliação inicial', AASLD_HCV, 'B')
        for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Hemograma completo com plaquetas',
                       'Creatinina, soro'):
            add(titulo, 'laboratorio', 'Hepatite C: FIB-4 (idade, AST, ALT e plaquetas) para estadiar a fibrose; FIB-4 > 3,25 '
                'indica fibrose avançada ou cirrose. Hemograma, função hepática e creatinina antes do tratamento.',
                'Hepatite C | Avaliação inicial', AASLD_HCV, 'B')
        orientar('Hepatite C: depois da cura',
                 'Com fibrose avançada ou cirrose, a ultrassonografia a cada 6 meses continua mesmo após a cura. Sem ela, '
                 'não há acompanhamento hepático de rotina; repetir o HCV-RNA se houver nova exposição.', AASLD_HCV)

    # ---------------- Doença renal crônica (relatório D, D-01; relatório A, M-03) ----------------
    if 'doenca_renal' in com:
        g, a = estagio_drc(com, tfg, uacr)
        if g:
            vezes = VEZES_POR_ANO[g][CATEGORIAS_A.index(a) if a else 0]
        else:
            vezes = {'A3': 2}.get(a, 1)
        grupo = ' '.join(['Doença renal crônica'] + [x for x in (g, a) if x])
        freq = _FREQUENCIA[vezes]
        for titulo in ('Creatinina, soro', 'Relação albumina/creatinina urinária (uACR)'):
            add(titulo, 'laboratorio',
                'Doença renal crônica: TFG estimada (CKD-EPI 2021) e albuminúria (uACR) pelo menos uma vez por ano e mais vezes '
                'com maior risco de progressão, pelo mapa G x A do KDIGO 2024 (de 1 vez por ano em G1-G2/A1 a 4 ou mais em G4-G5). '
                'A uACR também define a categoria A e a indicação de iSGLT2 e de IECA ou BRA.',
                f'{grupo} | {freq}', KDIGO_DRC, 'E', 'alta')
        if not g or not a:
            orientar('Doença renal crônica: estágio incompleto',
                     'A frequência de TFG e albuminúria depende do estágio G (TFG) e da categoria A (albuminúria). Com a '
                     'creatinina e a relação albumina/creatinina informadas, ou com os detalhes do item marcados, ajustamos a '
                     'frequência; sem eles, o mínimo é uma vez por ano.', KDIGO_DRC)
        if g in ('G3a', 'G3b', 'G4', 'G5'):
            g3 = g in ('G3a', 'G3b')
            add('Hemograma completo com plaquetas', 'laboratorio',
                'DRC: rastrear anemia (hemoglobina) pelo menos uma vez por ano em G3 e duas vezes por ano em G4-G5.',
                f'{grupo} | ' + ('Anual' if g3 else 'A cada 6 meses'), KDIGO_ANEMIA, 'E')
            ca_p = {'G3a': 'A cada 6-12 meses', 'G3b': 'A cada 6-12 meses', 'G4': 'A cada 3-6 meses', 'G5': 'A cada 1-3 meses'}[g]
            for titulo in ('Cálcio iônico, soro', 'Fósforo, soro'):
                add(titulo, 'laboratorio', 'Distúrbio mineral e ósseo da DRC: cálcio e fósforo a cada 6-12 meses em G3, a cada 3-6 '
                    'meses em G4 e a cada 1-3 meses em G5.', f'{grupo} | {ca_p}', KDIGO_DMO, 'E')
            pth = {'G4': 'A cada 6-12 meses', 'G5': 'A cada 3-6 meses'}.get(g, 'Avaliação inicial')
            add('Paratormônio (PTH), soro', 'laboratorio', 'Distúrbio mineral e ósseo da DRC: PTH basal em G3 (repetir conforme o '
                'valor e a progressão), a cada 6-12 meses em G4 e a cada 3-6 meses em G5.', f'{grupo} | {pth}', KDIGO_DMO, 'E')
            add('Fosfatase alcalina, soro', 'laboratorio', 'Distúrbio mineral e ósseo da DRC: fosfatase alcalina basal em G3 e anual '
                'a partir de G4 (mais vezes com PTH elevado).', f'{grupo} | ' + ('Avaliação inicial' if g3 else 'Anual'), KDIGO_DMO, 'E')
            add('25-hidroxivitamina D, soro', 'laboratorio', 'Distúrbio mineral e ósseo da DRC: 25(OH)D basal a partir de G3a; '
                'repetir conforme o valor e o tratamento.', f'{grupo} | Avaliação inicial', KDIGO_DMO, 'C')
            for titulo in ('Potássio, soro', 'Reserva alcalina (bicarbonato)'):
                add(titulo, 'laboratorio', 'DRC G3a ou mais: potássio e bicarbonato junto da TFG (hipercalemia e acidose metabólica, '
                    'que mudam o tratamento).', f'{grupo} | {freq}', KDIGO_DRC, 'E')
        if g in ('G4', 'G5') or a == 'A3':
            orientar('Doença renal crônica: encaminhar ao nefrologista',
                     'TFG abaixo de 30 mL/min/1,73 m² ou albuminúria A3 (uACR ≥ 300 mg/g): acompanhamento conjunto com nefrologia.',
                     KDIGO_DRC)

    # ---------------- Insuficiência cardíaca (relatório D, D-02) ----------------
    if ic:
        for titulo in ('Hemograma completo com plaquetas', 'Ferritina, soro', 'Índice de saturação de transferrina, soro'):
            add(titulo, 'laboratorio',
                'Insuficiência cardíaca: rastrear anemia e deficiência de ferro periodicamente em todos, com hemograma, ferritina e '
                'saturação de transferrina (classe I). Ferropenia: ferritina < 100 ng/mL, ou 100-299 com saturação < 20%; com '
                'sintomas e fração de ejeção reduzida ou levemente reduzida, ferro intravenoso (classe I).',
                'Insuficiência cardíaca | Anual', ESC_IC + ' / ' + ESC_IC_2023, 'C', 'alta')
        add('Peptídeo natriurético BNP/PROBNP', 'laboratorio',
            'Insuficiência cardíaca: peptídeo natriurético na avaliação inicial (prognóstico e referência) e de novo na mudança do '
            'quadro clínico.', 'Insuficiência cardíaca | Avaliação inicial', ESC_IC, 'B')
        add('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
            'Insuficiência cardíaca: TSH na avaliação inicial (hipo e hipertireoidismo causam ou agravam a IC).',
            'Insuficiência cardíaca | Avaliação inicial', ESC_IC, 'C')

    # ---------------- Hipertensão (relatório D, D-13, D-30 e Dúvida 1) ----------------
    if hipertenso and idade >= 18:
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Cálcio iônico, soro', 'Sódio, soro',
                       'Hemograma completo com plaquetas'):
            add(titulo, 'laboratorio', 'Hipertensão: exames básicos da avaliação inicial (glicemia, hemograma, lipídios, creatinina '
                'com TFG, sódio, potássio, cálcio, TSH, urina e ECG).', 'Adultos com HAS | Avaliação inicial',
                ACC_AHA_HAS_2017 + ' / AHA 2025', 'B')
        orientar('Ácido úrico na hipertensão: diretrizes divergem',
                 'A SBC 2025 inclui o ácido úrico nos exames de rotina do hipertenso; a AHA/ACC o trata como exame opcional, sem '
                 'repetição seriada. Sugerimos uma dosagem na avaliação inicial.', 'SBC 2025 / AHA 2025')
        resistente = 'has_resistente' in com
        if 'apneia_sono' in com and not resistente:
            add('Relação Aldosterona/Renina (A/R)', 'laboratorio',
                'Hipertensão com apneia obstrutiva do sono: rastrear hiperaldosteronismo primário (aldosterona e renina com potássio, '
                'pela manhã e sentado; corrigir a hipocalemia; interpretar pelos cortes do método do laboratório).',
                'HAS com apneia do sono | Avaliação inicial', ENDO_PA_2016 + ' / ' + ENDO_PA_2025, 'C')
        orientar('Hiperaldosteronismo primário: diretrizes divergem',
                 'Sugerimos a relação aldosterona/renina na HAS resistente (AHA/ACC 2025, classe 1, com qualquer potássio) e na '
                 'HAS com apneia do sono (Endocrine Society 2016). Sugerimos rastrear também com hipocalemia espontânea ou por diurético, '
                 'incidentaloma adrenal, PA ≥ 150/100 persistente ou história familiar de HAS ou AVC antes dos 40 anos. A '
                 'Endocrine Society 2025 sugere rastrear todos os hipertensos (recomendação condicional, certeza baixa).',
                 'AHA 2025 / ' + ENDO_PA_2016 + ' / ' + ENDO_PA_2025)
    if 'apneia_sono' in com:
        # A apneia já diagnosticada não se investiga de novo na HAS resistente (relatório D, D-30).
        recs[:] = [r for r in recs if r.get('titulo') != 'Polissonografia']

    # ---------------- Outras comorbidades ----------------
    if 'neoplasia_ativa' in com:
        add('HBsAg, anti-HBc total e anti-HBs', 'laboratorio',
            'Câncer com tratamento sistêmico: HBsAg, anti-HBc total e anti-HBs antes de iniciar (risco de reativação da '
            'hepatite B); positivo, profilaxia antiviral ou monitorização conforme o caso.', 'Câncer em tratamento | Antes do tratamento',
            ASCO_HBV, 'B', 'alta')
    if 'transplante' in com:
        orientar('Transplante: câncer de pele e rastreios',
                 'Exame de toda a pele anual por profissional treinado (risco muito aumentado de câncer de pele) e os rastreios '
                 'de câncer da população geral.', 'KDIGO 2009 (transplante renal)')
    if 'anemia_falciforme' in com:
        add('Relação albumina/creatinina urinária (uACR)', 'laboratorio',
            'Doença falciforme: rastrear albuminúria e proteinúria anualmente (nefropatia falciforme).',
            'Doença falciforme | Anual', NHLBI_FALCIFORME, 'B')
        add('Avaliação oftalmológica (fundo de olho)', 'imagem',
            'Doença falciforme: exame de fundo de olho sob midríase a cada 1-2 anos (retinopatia falciforme).',
            'Doença falciforme | A cada 1-2 anos', NHLBI_FALCIFORME, 'B')
    if 'asma_grave' in com:
        add('Espirometria, com broncodilatador', 'imagem',
            'Asma: função pulmonar no diagnóstico, 3-6 meses após iniciar o controlador e depois periodicamente, pelo menos a '
            'cada 1-2 anos.', 'Asma moderada ou grave | A cada 1-2 anos', GINA, 'C')
    if 'bronquiectasias' in com:
        # ERS 2025, recomendação 1 (forte; certeza moderada, de revisão narrativa): testagem padronizada para a causa, a
        # gravidade, o risco, as comorbidades e os traços tratáveis. O painel abaixo é o que o resumo dos autores manda
        # fazer em todo paciente com bronquiectasias confirmadas (Mosgrove 2026, p. 2 e Tabela 1). A força é a da
        # recomendação 1; não há força por exame. O resumo não fixa intervalo de consulta, de cultura nem de espirometria
        # no paciente estável e não trata de vacinas: nada disso vira pedido.
        painel = ('Bronquiectasias: painel de exames para investigar a causa, indicado a todo paciente com o '
                  'diagnóstico confirmado: hemograma, imunoglobulinas (IgG, IgA e IgM), eletroforese de proteínas, '
                  'pesquisa de aspergilose broncopulmonar alérgica (IgE total, IgE e IgG para Aspergillus) e escarro '
                  'para bactérias e micobactérias.')
        for titulo in ('Hemograma completo com plaquetas', 'Imunoglobulina G (IgG), soro', 'Imunoglobulina A (IgA), soro',
                       'Imunoglobulina M (IgM), soro', 'Eletroforese de proteínas, soro',
                       'Imunoglobulina E (IgE) total, soro', 'IgE específica para Aspergillus, soro',
                       'IgG específica para Aspergillus, soro', 'Cultura de escarro (bactérias)',
                       'Cultura para micobactérias, escarro'):
            add(titulo, 'laboratorio', painel, 'Bronquiectasias | Avaliação inicial', ERS_BRONQUIECTASIAS, 'A')
        orientar('Bronquiectasias: escarro no seguimento',
                 'Colher cultura de escarro no início de cada exacerbação, de preferência antes do antibiótico, e repetir '
                 'se não houver resposta. Pesquisar micobactérias também nos sintomas persistentes que não melhoram com '
                 'antibiótico e antes de iniciar macrolídeo prolongado. Isolamento novo de Pseudomonas aeruginosa: repetir '
                 'a cultura e discutir de imediato com o especialista; a diretriz sugere o tratamento de erradicação '
                 '(recomendação condicional). No paciente estável, a cultura positiva isolada não é motivo para '
                 'antibiótico.',
                 ERS_BRONQUIECTASIAS)
        orientar('Bronquiectasias: o que não vira pedido automático',
                 'A espirometria entra na avaliação da gravidade (VEF1), não na investigação da causa. O resumo da diretriz '
                 'não fixa intervalo de consulta, de cultura de escarro nem de espirometria no paciente estável, e não '
                 'trata de vacinas. Causas raras (discinesia ciliar, fibrose cística) são investigadas quando os exames '
                 'iniciais são negativos e a história as sugere. Na avaliação inicial, rever comorbidades: risco '
                 'cardiovascular, osteoporose, rinossinusite, refluxo e humor, e otimizar o tratamento da doença de via '
                 'aérea associada. A diretriz trata das bronquiectasias do adulto não relacionadas à fibrose cística.',
                 ERS_BRONQUIECTASIAS)
    if 'hipertensao_arterial_pulmonar' in com:
        # ESC/ERS 2022, texto integral lido em 18/11/2026: Tabela 17 (avaliações e momentos do seguimento, com as notas:
        # exames básicos = hemograma, INR em uso de antagonista da vitamina K, creatinina, sódio, potássio, TGO/TGP,
        # bilirrubina e BNP/NT-proBNP; estendidos = TSH, troponina, ácido úrico e ferro, conforme o quadro),
        # Recommendation Table 4 (gravidade por painel de dados e risco em quatro estratos no seguimento: classe I,
        # nível B), seção 6.3.1.6 (ferro) e Recommendation Table 5 (ferro e vacinas: classe I, nível C).
        hap = 'Hipertensão arterial pulmonar'
        for titulo, categoria in (('Peptídeo natriurético BNP/PROBNP', 'laboratorio'),
                                  ('Teste de caminhada de 6 minutos', 'imagem')):
            add(titulo, categoria,
                'Hipertensão arterial pulmonar: no seguimento, o risco é estratificado em quatro níveis pela classe funcional '
                '(OMS), pela distância no teste de caminhada de 6 minutos e pelo BNP ou NT-proBNP. Reavaliar 3-6 meses após '
                'mudança do tratamento e a cada 3-6 meses no paciente estável, com o intervalo ajustado ao caso.',
                hap + ' | A cada 3-6 meses', ESC_ERS_HP, 'A', 'alta')
        add('Ecocardiograma transtorácico', 'imagem',
            'Hipertensão arterial pulmonar: a gravidade é avaliada por um painel de dados (avaliação clínica, teste de '
            'exercício, biomarcadores, ecocardiograma e hemodinâmica). O ecocardiograma, ou a ressonância cardíaca, entra na '
            'avaliação inicial e no seguimento.', hap + ' | Conforme a evolução', ESC_ERS_HP, 'A')
        for titulo in ('Hemograma completo com plaquetas', 'Creatinina, soro', 'Sódio e potássio, soro',
                       'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro',
                       'Bilirrubinas totais e frações, soro'):
            add(titulo, 'laboratorio',
                'Hipertensão arterial pulmonar: exames básicos sugeridos na avaliação inicial e em cada reavaliação '
                '(hemograma, creatinina, sódio, potássio, TGO, TGP e bilirrubinas, além do BNP ou NT-proBNP).',
                hap + ' | A cada 3-6 meses', ESC_ERS_HP, 'E')
        for titulo in ('Ferritina, soro', 'Ferro sérico e saturação de transferrina'):
            add(titulo, 'laboratorio',
                'Hipertensão arterial pulmonar: monitorar o estado do ferro com regularidade (ferro sérico, ferritina e '
                'saturação de transferrina). Deficiência de ferro: ferritina abaixo de 100 µg/L, ou de 100 a 299 µg/L com '
                'saturação de transferrina abaixo de 20%. Com anemia ferropriva, corrigir o ferro.',
                hap + ' | Periódico', ESC_ERS_HP, 'E')
        if idade < 50:
            add(PNEUMO, 'vacina',
                'Dose única. Hipertensão arterial pulmonar: vacinar contra pneumococo, influenza e COVID-19. Já recebeu '
                'VPP23: aguardar 1 ano.', hap + ' | Dose única', ESC_ERS_HP, 'A', 'alta')
        orientar('Hipertensão arterial pulmonar: seguimento e vacinas',
                 'O seguimento é feito em centro de referência. Além dos exames pedidos, a diretriz lista: gasometria '
                 'arterial na avaliação inicial (a oximetria de pulso pode substituí-la no paciente estável), '
                 'eletrocardiograma, qualidade de vida, teste cardiopulmonar de exercício e cateterismo direito, conforme o '
                 'caso. Exames estendidos (TSH, troponina, ácido úrico) conforme o quadro clínico; INR em uso de antagonista '
                 'da vitamina K. Vacinas recomendadas: influenza, pneumocócica e COVID-19. Na deficiência de ferro sem '
                 'anemia, a reposição pode ser considerada.', ESC_ERS_HP)
    if 'fibrilacao_atrial' in com:
        add('Ecocardiograma transtorácico', 'imagem',
            'Fibrilação atrial: ecocardiograma transtorácico para orientar o tratamento (cardiopatia estrutural, função '
            'ventricular, átrio esquerdo).', 'Fibrilação atrial | Avaliação inicial', ESC_FA, 'B')
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Hemograma completo com plaquetas', 'Creatinina, soro',
                       'Sódio e potássio, soro'):
            add(titulo, 'laboratorio', 'Fibrilação atrial: função tireoidiana, hemograma, função renal e eletrólitos na avaliação '
                'inicial e na reavaliação periódica (anticoagulação, controle de ritmo e de frequência).',
                'Fibrilação atrial | Avaliação inicial', ESC_FA, 'B')
    if 'doenca_celiaca' in com:
        add('Anticorpo antitransglutaminase tecidual IgA, soro', 'laboratorio',
            'Doença celíaca: antitransglutaminase IgA aos 6 e 12 meses do diagnóstico e depois anualmente (adesão à dieta sem '
            'glúten).', 'Doença celíaca | Anual', AGA_CELIACA, 'B')
        for titulo in ('Hemograma completo com plaquetas', 'Ferritina, soro', 'Ácido fólico, soro', 'Vitamina B12, soro',
                       '25-hidroxivitamina D, soro', 'Hormônio Tireoestimulante (TSH), soro'):
            add(titulo, 'laboratorio', 'Doença celíaca: revisão anual com hemograma, ferritina, folato, B12, vitamina D e '
                'função tireoidiana (deficiências e tireoidite autoimune associadas).', 'Doença celíaca | Anual',
                BSG_CELIACA, 'C')
    if 'drge' in com:
        fumante = tabagismo in ('atual', 'ex')
        obeso = 'obesidade' in com or (imc or 0) >= 30
        # ACG 2022: sexo masculino, mais de 50 anos, raça branca, tabagismo, obesidade e Barrett ou adenocarcinoma de esôfago em
        # parente de 1º grau. A raça não é coletada: fica na orientação (revisão externa, GASTRO-01).
        fatores = [nome for nome, sim in (('sexo masculino', sexo == 'masculino'), ('mais de 50 anos', idade > 50),
                                          ('tabagismo', fumante), ('obesidade', obeso),
                                          ('familiar', 'barrett_esofago' in fam)) if sim]
        if len(fatores) >= 3:
            add('Endoscopia digestiva alta', 'imagem',
                'Doença do refluxo crônica com 3 ou mais fatores de risco de esôfago de Barrett (sexo masculino, mais de 50 '
                'anos, raça branca, tabagismo, obesidade, Barrett ou adenocarcinoma de esôfago em parente de 1º grau): endoscopia '
                'única de rastreio.', 'Refluxo crônico com fatores de risco | Uma vez', ACG_BARRETT, 'C')
        else:
            orientar('Refluxo: rastreio de esôfago de Barrett',
                     'Endoscopia única de rastreio se refluxo crônico e 3 ou mais fatores: sexo masculino, mais de 50 anos, '
                     'raça branca, tabagismo, obesidade, esôfago de Barrett ou adenocarcinoma de esôfago em parente de 1º grau. A raça '
                     'não é coletada: com 2 fatores e raça branca, a endoscopia está indicada.',
                     ACG_BARRETT)
    if 'sop' in com and sexo == 'feminino' and not gestante:
        add('TOTG-75g (Teste Oral de Tolerância à Glicose), soro', 'laboratorio',
            'Síndrome dos ovários policísticos: avaliar a glicemia no diagnóstico e a cada 1-3 anos, qualquer que seja o IMC '
            '(TOTG preferido; glicemia de jejum ou HbA1c como alternativa).', 'Síndrome dos ovários policísticos | A cada 1-3 anos',
            PCOS, 'B')
        add('Colesterol total e frações, soro', 'laboratorio',
            'Síndrome dos ovários policísticos: perfil lipídico no diagnóstico; depois, conforme o risco cardiovascular.',
            'Síndrome dos ovários policísticos | Avaliação inicial', PCOS, 'B')

    # ---------------- Endocrinologia: nódulo de tireoide, hiperparatireoidismo, adrenal, hipogonadismo ----------------
    if 'nodulo_tireoide' in com:
        # ATA 2015: recomendações 2 (TSH), 6 (ultrassonografia com linfonodos cervicais), 23 e 24 (seguimento).
        add('Hormônio Tireoestimulante (TSH), soro', 'laboratorio',
            'Nódulo de tireoide: TSH na avaliação inicial. Com TSH baixo, cintilografia para saber se o nódulo é '
            'hiperfuncionante (nesse caso não precisa de punção).', 'Nódulo de tireoide | Avaliação inicial', ATA_NODULO, 'B')
        add('Ultrassonografia de tireoide', 'imagem',
            'Nódulo de tireoide: ultrassonografia com avaliação dos linfonodos cervicais em todo paciente com nódulo. O '
            'seguimento do nódulo com citologia benigna depende do padrão ultrassonográfico: alta suspeita, repetir a '
            'ultrassonografia e a punção em até 12 meses; suspeita baixa ou intermediária, repetir em 12-24 meses; suspeita '
            'muito baixa, se repetir, depois de 24 meses.', 'Nódulo de tireoide | Conforme o padrão ultrassonográfico',
            ATA_NODULO, 'B')
        orientar('Nódulo de tireoide: o que a ATA não recomenda de rotina',
                 'A tireoglobulina sérica não é recomendada na avaliação inicial do nódulo. Sobre a calcitonina de '
                 'rotina, a ATA não se posiciona a favor nem contra. A indicação de punção depende do tamanho e do padrão '
                 'ultrassonográfico do nódulo.', ATA_NODULO)
    if 'hiperparatireoidismo_primario' in com:
        # 5º Workshop Internacional (2022): itens 3 (avaliação) e 9 (seguimento de quem não opera) do resumo.
        inicial = 'Hiperparatireoidismo primário | Avaliação inicial'
        for titulo in ('Paratormônio (PTH), soro', 'Fósforo, soro', 'Calciúria de 24 horas'):
            add(titulo, 'laboratorio', 'Hiperparatireoidismo primário: avaliação inicial com cálcio, fósforo, PTH, '
                '25-hidroxivitamina D, creatinina e calciúria de 24 horas.', inicial, HPTP_2022, 'E')
        for titulo in ('Cálcio iônico, soro', '25-hidroxivitamina D, soro', 'Creatinina, soro'):
            add(titulo, 'laboratorio', 'Hiperparatireoidismo primário: na avaliação inicial e, em quem não foi operado, '
                'cálcio, 25-hidroxivitamina D e função renal uma vez por ano. A diretriz cita o cálcio total corrigido pela '
                'albumina; pedimos o iônico, que ela indica na suspeita da forma normocalcêmica.',
                'Hiperparatireoidismo primário | Anual',
                HPTP_2022, 'E')
        add('Densitometria óssea (DEXA)', 'imagem',
            'Hiperparatireoidismo primário: densitometria em três sítios (coluna lombar, fêmur e terço distal do rádio) na '
            'avaliação inicial e a cada 1-2 anos em quem não foi operado.', 'Hiperparatireoidismo primário | A cada 1-2 anos',
            HPTP_2022, 'E', obs='Incluir o terço distal do rádio (antebraço), além da coluna lombar e do fêmur.')
        add('Radiografia de coluna torácica e lombar (perfil)', 'imagem',
            'Hiperparatireoidismo primário: imagem da coluna (radiografia ou avaliação de fratura vertebral pela '
            'densitometria) na avaliação inicial, para fratura vertebral.', inicial, HPTP_2022, 'E')
        add('Ultrassonografia de rins e vias urinárias', 'imagem',
            'Hiperparatireoidismo primário: imagem dos rins na avaliação inicial, para nefrolitíase e nefrocalcinose.',
            inicial, HPTP_2022, 'E')
    if 'incidentaloma_adrenal' in com:
        # ESE/ENSAT 2023: R.3.2 (dexametasona), R.3.9 (metanefrinas), R.3.10 (aldosterona/renina), R.2.3, R.5.1-R.5.4.
        add('Cortisol após 1 mg de dexametasona, soro', 'laboratorio',
            'Incidentaloma adrenal: teste de supressão com 1 mg de dexametasona à noite em todos os pacientes; cortisol de '
            'até 1,8 µg/dL (50 nmol/L) afasta secreção autônoma de cortisol.', 'Incidentaloma adrenal | Avaliação inicial',
            ESE_INCIDENTALOMA, 'B')
        if hipertenso:
            add('Relação Aldosterona/Renina (A/R)', 'laboratorio',
                'Incidentaloma adrenal com hipertensão ou hipocalemia sem explicação: relação aldosterona/renina.',
                'Incidentaloma adrenal com HAS | Avaliação inicial', ESE_INCIDENTALOMA, 'C')
        orientar('Incidentaloma adrenal: metanefrinas, imagem e seguimento',
                 'Sugerimos metanefrinas (plasma ou urina) quando a lesão não tem aspecto de adenoma benigno na '
                 'tomografia sem contraste. Lesão homogênea com até 10 UH é benigna e não precisa de nova imagem, qualquer que '
                 'seja o tamanho. Lesão indeterminada não operada: repetir a tomografia sem contraste ou a ressonância uma '
                 'vez, em 6-12 meses. Com avaliação hormonal inicial normal, não repetir os exames, salvo sinal clínico novo ou '
                 'piora de hipertensão ou diabetes. Na secreção autônoma leve de cortisol: rastrear hipertensão, diabetes '
                 'tipo 2 e fratura vertebral, e reavaliar essas comorbidades uma vez por ano.' + ('' if hipertenso else
                 ' Com hipertensão ou hipocalemia sem explicação, pedir a relação aldosterona/renina.'), ESE_INCIDENTALOMA)
    if 'hipogonadismo_masculino' in com and sexo == 'masculino':
        # Endocrine Society 2018: 1.1 (duas dosagens matinais em jejum), 1.3 (LH e FSH), 3.x (seguimento do tratamento).
        add('FSH e LH, soro', 'laboratorio',
            'Hipogonadismo masculino: LH e FSH para separar a causa testicular (primária) da hipotálamo-hipofisária '
            '(secundária).', 'Hipogonadismo masculino | Avaliação inicial', ENDO_TESTOSTERONA, 'B')
        if 'testosterona' not in med:
            add('Testosterona total, soro', 'laboratorio',
                'Hipogonadismo masculino: o diagnóstico pede testosterona total baixa em duas dosagens, pela manhã e em '
                'jejum, junto de sintomas ou sinais de deficiência.', 'Hipogonadismo masculino | Para confirmar o diagnóstico',
                ENDO_TESTOSTERONA, 'B')
        orientar('Hipogonadismo masculino: seguimento da reposição de testosterona',
                 'Em quem repõe testosterona: testosterona 3-6 meses após o início; hematócrito antes, aos 3-6 meses e depois '
                 'uma vez por ano; PSA e toque retal antes e 3-12 meses após o início nos homens de 55 a 69 anos (ou de 40 a 69 '
                 'com risco aumentado) que optam pelo rastreio. Marque a testosterona na lista de medicações para o sistema '
                 'pedir esses exames. A diretriz não recomenda rastrear hipogonadismo na população geral.', ENDO_TESTOSTERONA)

    if 'hiperprolactinemia' in com:
        # Endocrine Society 2011: 1.1-1.3 (diagnóstico), 2.1 (excluir medicação, insuficiência renal, hipotireoidismo e
        # tumor parasselar: forte, evidência alta) e o seguimento do tratamento. Pituitary Society 2023 (consenso):
        # repetir a prolactina abaixo de 5x o limite, gravidez, ressonância, IGF-1, densitometria e ecocardiograma.
        inicial = 'Hiperprolactinemia | Avaliação inicial'
        for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Creatinina, soro'):
            add(titulo, 'laboratorio',
                'Hiperprolactinemia: antes de investigar a hipófise, excluir medicação, insuficiência renal e '
                'hipotireoidismo como causa.', inicial, ENDO_PROLACTINA, 'A')
        if sexo == 'feminino' and idade <= 50 and not gestante:
            add('Beta-hCG, soro', 'laboratorio',
                'Hiperprolactinemia em quem pode engravidar: afastar gravidez, causa fisiológica de prolactina alta.',
                inicial, PITUITARY_PROLACTINOMA, 'E')
        add('Ressonância magnética de sela túrcica', 'imagem',
            'Hiperprolactinemia sem causa medicamentosa, renal ou tireoidiana: ressonância da região selar, para tumor de '
            'hipófise ou lesão parasselar.', inicial, ENDO_PROLACTINA + ' / ' + PITUITARY_PROLACTINOMA, 'A')
        add('Prolactina, soro', 'laboratorio',
            'Hiperprolactinemia em tratamento com agonista dopaminérgico: prolactina a partir de 1 mês do início, para '
            'ajustar a dose. Depois de suspender o tratamento: a cada 3 meses no primeiro ano e, depois, uma vez por ano.',
            'Hiperprolactinemia | Conforme o tratamento', ENDO_PROLACTINA + ' / ' + PITUITARY_PROLACTINOMA, 'E')
        orientar('Hiperprolactinemia: confirmar a prolactina alta',
                 'Aviso de divergência: a Endocrine Society (2011) aceita uma única dosagem acima do limite, colhida sem '
                 'estresse de punção, e não recomenda testes dinâmicos; a Pituitary Society (2023) pede repetir a dosagem '
                 'quando a prolactina está abaixo de 5 vezes o limite superior. Macroprolactina: pesquisar na '
                 'hiperprolactinemia assintomática (Endocrine Society) ou com prolactina abaixo de 200 ng/mL e clínica ou '
                 'imagem discordantes (Pituitary Society). Tumor grande com prolactina pouco elevada: pedir a dosagem com '
                 'diluição, por causa do efeito gancho.', ENDO_PROLACTINA + ' / ' + PITUITARY_PROLACTINOMA)
        orientar('Hiperprolactinemia: hipófise, osso e seguimento',
                 'A Pituitary Society (2023) recomenda dosar o IGF-1 na avaliação inicial e avaliar a densidade óssea '
                 'conforme a idade, a duração da hiperprolactinemia e do hipogonadismo e outros fatores de risco. No '
                 'macroadenoma com risco para o quiasma óptico, campo visual (Endocrine Society). Ressonância de controle: '
                 'em 1 ano de tratamento, ou em 3 meses no macroprolactinoma se a prolactina continua a subir ou surge '
                 'sintoma novo (Endocrine Society); a Pituitary Society pede a imagem 3-6 meses após o início no '
                 'macroprolactinoma. Aviso de divergência sobre o ecocardiograma em uso de cabergolina: para a Endocrine '
                 'Society, a dose habitual (1-2 mg por semana) provavelmente não exige ecocardiograma periódico; a Pituitary '
                 'Society sugere ecocardiograma inicial se a dose prevista passa de 2 mg por semana, a cada 2-3 anos acima '
                 'dessa dose e depois de 5-6 anos com até 2 mg por semana (recomendação fraca).',
                 ENDO_PROLACTINA + ' / ' + PITUITARY_PROLACTINOMA)

    # ---------------- Vacinas por condição de risco ----------------
    # SBIm 2026/2027 (adulto, idoso, gestante) e SBIm Pacientes Especiais 2026/2027; esquemas do PNI pela IN CNV 2026.
    imuno_listas = imunossupressao_implicada(com, med)
    imuno = imuno_listas or bool(imunossuprimido)
    hiv = 'hiv' in com
    cd4_baixo = hiv and cd4 is not None and cd4 < 200
    onco = 'oncologico' in med                       # tratamento sistêmico do câncer (inclui imunoterapia e anti-HER2)
    imunocomprometido = imuno or hiv or onco
    tem_diabetes = bool(set(TIPOS_DE_DIABETES) & com) or 'diabetes_sem_tipo' in com
    drc = 'doenca_renal' in com
    hepatopatia = bool(set(HEPATOPATIAS) & com)
    obeso = 'obesidade' in com or (imc or 0) >= 30
    titulos = lambda: {(r.get('titulo') or '').strip().lower() for r in recs}

    # Pneumocócica (VPC20) em qualquer idade com comorbidade de risco para doença pneumocócica invasiva:
    # HIV, DRC, diabetes, imunossupressão e câncer em tratamento entram (SBIm Pacientes Especiais; CRIE).
    risco_pneumo = {'cirrose', 'asma_grave', 'asplenia', 'anemia_falciforme', 'transplante', 'neoplasia_ativa',
                    'artrite_reumatoide', 'lupus', 'artrite_psoriasica', 'espondiloartrite', 'esclerose_sistemica',
                    LEGADO_AUTOIMUNE, 'hepatite_b_cronica', 'hepatite_c', 'hiv', 'doenca_renal'} & com or \
        {'imunossupressor', 'corticoide_cronico', 'corticoide_imunossupressor', 'oncologico'} & med or tem_diabetes or imuno
    if risco_pneumo and idade < 50:
        add(PNEUMO, 'vacina', 'Dose única. Indicada em qualquer idade com comorbidade de risco para doença pneumocócica invasiva '
            '(inclusive HIV, doença renal crônica, diabetes e imunossupressão). Já recebeu VPP23: aguardar 1 ano.',
            'Comorbidade de risco | Dose única | PNI: CRIE', SBIM + ' / ' + SBIM_ESPECIAIS, 'A', 'alta')
    elif tabagismo == 'atual' and 19 <= idade < 50:
        orientar('Pneumocócica no tabagismo antes dos 50 anos: diretrizes divergem',
                 'Nós optamos por seguir a referência da SBIm e dos CRIE, que não listam o tabagismo como risco, e não incluímos a VPC20. O ACIP indica '
                 'a VPC20 de 19 a 49 anos em fumantes de cigarro (e no etilismo).',
                 SBIM_ESPECIAIS + ' / CDC/ACIP 2025 (pneumocócica)')

    # Herpes-zóster recombinante a partir de 18 anos: imunocomprometidos e toda pessoa vivendo com HIV, qualquer que
    # seja o CD4 (o HIV não marca "imunossupressão": as vivas seguem pela faixa de CD4 em seguranca_vacinas.py).
    if imunocomprometido and 18 <= idade < 50 and not gestante:
        add(ZOSTER, 'vacina', 'Vacina inativada: 2 doses (0-2 meses; intervalo mínimo de 1 mês), mesmo após herpes-zóster. '
            'Indicada a partir de 18 anos em imunocomprometidos, no câncer (de preferência antes do tratamento) e em toda '
            'pessoa vivendo com HIV, qualquer que seja o LT-CD4+.', 'HIV ou imunocomprometidos ≥ 18 anos | 2 doses (0-2m)',
            'CDC/ACIP 2022 / ' + SBIM_ESPECIAIS, 'A', 'alta')

    # HPV: 3 doses em qualquer idade no imunossuprimido e no HIV (o PNI oferece HPV4 de 9 a 45 anos).
    if (imuno or hiv) and idade <= 45:
        add(HPV9, 'vacina', '3 doses (0-2-6 meses) em qualquer idade para imunossuprimidos e pessoas vivendo com HIV. Preferir '
            'HPV9 e revacinar quem recebeu HPV2/HPV4. Contraindicada na gestação. PNI: HPV4 em 3 doses de 9 a 45 anos para '
            'imunocomprometidos.', 'Imunossuprimido ou HIV | 3 doses (0-2-6m) em qualquer idade | PNI: HPV4 9-45 anos (CRIE)',
            SBIM_ESPECIAIS + ' / ' + IN_CNV, 'A', 'alta', substituir=True)

    # Hepatite B: esquema especial na DRC/diálise, no HIV e na imunossupressão (4 doses com o dobro do volume e sorologia).
    if drc or hiv or imuno:
        add(HEPATITE_B_60 if idade >= 60 else HEPATITES_A_B, 'vacina',
            'DRC, diálise, HIV ou imunossupressão: hepatite B em 4 doses (0-1-2-6 meses) com o dobro do volume da dose para a '
            'idade, com a vacina isolada. Anti-HBs 1 a 2 meses depois da última dose; abaixo de 10 mUI/mL, repetir o esquema '
            'uma vez. Em hemodiálise, anti-HBs anual e reforço se abaixo de 10 mUI/mL.'
            + (' Hepatite A, se suscetível: 2 doses (0-6 meses).' if idade < 60 or hepatopatia else ''),
            'DRC/HIV/imunossupressão | 4 doses dobradas + sorologia | PNI: CRIE',
            SBIM_ESPECIAIS + ' / ' + CRIE + ' / ' + IN_CNV, 'A', 'alta', substituir=True)

    # Influenza: na imunossupressão grave abaixo de 60 anos, a SBIm sugere a HD3V (off-label), sem dose extra.
    grave = bool({'transplante', 'neoplasia_ativa'} & com or {'antraciclina', 'fluoropirimidina'} & med or cd4_baixo)
    if grave and idade < 60:
        add(INFLUENZA, 'vacina', 'Dose única anual. Imunossupressão grave (transplante, quimioterapia, HIV com LT-CD4+ abaixo de '
            '200): a SBIm sugere considerar a HD3V (alta concentração, off-label abaixo de 60 anos), sem dose adicional.',
            'Imunossupressão grave | Dose anual | Considerar HD3V (off-label)', SBIM_ESPECIAIS, 'A', 'alta', substituir=True)

    # COVID-19 (IN CNV 2026): gestante > imunocomprometido > 60+ (já no calendário por idade) > comorbidade > demais.
    comorbidade_covid = bool({'dcv_aterosclerotica', 'cardiopatia', 'insuficiencia_cardiaca', 'dpoc', 'doenca_renal'} & com) \
        or tem_diabetes or obeso
    if gestante:
        add(COVID, 'vacina', '1 dose a cada gestação, em qualquer idade gestacional (mínimo de 6 meses desde a última dose). '
            'Conferir vacinas disponíveis no PNI (gov.br/saude).', 'Gestante | 1 dose a cada gestação',
            IN_CNV + ' / ' + SBIM, 'A', 'alta', substituir=True)
    elif imuno or hiv:
        add(COVID, 'vacina', '1 dose a cada 6 meses. Conferir vacinas disponíveis no PNI (gov.br/saude).',
            'Imunocomprometido | 1 dose a cada 6 meses', IN_CNV + ' / ' + SBIM, 'A', 'alta', substituir=True)
    elif idade < 60 and comorbidade_covid:
        add(COVID, 'vacina', '1 dose por ano. Conferir vacinas disponíveis no PNI (gov.br/saude).', 'Comorbidade | 1 dose/ano',
            IN_CNV + ' / ' + SBIM, 'A', 'alta', substituir=True)

    # VSR (SBIm 2026/2027 e SBIm Pacientes Especiais 2026/2027)
    if 'asma_grave' in com and 18 <= idade < 60 and not gestante:
        add(VSR, 'vacina', 'Dose única para adultos com asma moderada ou grave.', 'Asma moderada/grave | Dose única', SBIM, 'B')
    so_corticoide = 'corticoide_imunossupressor' in med and not imunossupressao_implicada(com, med - {'corticoide_imunossupressor'}) \
        and not cd4_baixo
    if (imuno or cd4_baixo) and not so_corticoide and 18 <= idade < 60 and not gestante:
        add(VSR, 'vacina', 'Dose única a partir de 18 anos na imunodeficiência moderada ou grave (transplante, quimioterapia, '
            'imunobiológico ou imunossupressor, HIV com LT-CD4+ abaixo de 200).',
            'Imunodeficiência moderada/grave | Dose única | Rede privada', SBIM_ESPECIAIS, 'B')
    if (tem_diabetes or drc or hepatopatia) and 50 <= idade < 60:
        add(VSR, 'vacina', 'Dose única a partir de 50 anos em diabetes, nefropatia ou hepatopatia crônica, pelo risco de evolução '
            'grave ou descompensação.', 'Diabetes, nefropatia ou hepatopatia ≥ 50 anos | Dose única | Rede privada',
            SBIM_ESPECIAIS, 'B')
    if 60 <= idade < 70:
        # A hipertensão arterial pulmonar é doença cardiopulmonar crônica: entra como as demais pneumopatias e cardiopatias.
        risco_vsr = bool({'dpoc', 'asma_grave', 'dcv_aterosclerotica', 'cardiopatia', 'insuficiencia_cardiaca',
                          'hipertensao_arterial_pulmonar'} & com) \
            or tem_diabetes or drc or hepatopatia or obeso or imuno or hiv
        if risco_vsr:
            add(VSR, 'vacina', 'Dose única para 60-69 anos com maior risco: cardiopatia, pneumopatia, diabetes, obesidade, '
                'nefropatia, hepatopatia, imunossupressão, fragilidade ou institucionalização.',
                '60-69 anos com fator de risco | Dose única | Rede privada', SBIM, 'A')
        else:
            orientar('VSR de 60 a 69 anos: só com fator de risco',
                     'Sem fator de risco nas listas, a vacina VSR não entrou na receita. De 60 a 69 anos, a SBIm a indica com '
                     'cardiopatia, pneumopatia, diabetes, obesidade, nefropatia, hepatopatia, imunossupressão, fragilidade ou '
                     'institucionalização; a rotina começa aos 70 anos.', SBIM)
    tem_vsr = VSR.lower() in titulos()
    if not tem_vsr and not gestante and ((tem_diabetes or drc or hepatopatia) and 18 <= idade < 50 or obeso and 18 <= idade < 60):
        orientar('VSR a critério médico',
                 'Diabetes, nefropatia ou hepatopatia crônica de 18 a 49 anos e obesidade de 18 a 59 anos: a SBIm deixa a vacina '
                 'VSR (dose única) a critério médico. Não entrou na receita automática.', SBIM + ' / ' + SBIM_ESPECIAIS)
    if tem_vsr and not gestante and (18 <= idade < 50 or 70 <= idade < 75):
        orientar('VSR: diretrizes divergem',
                 'Nós optamos por seguir a referência da SBIm (a partir de 18 anos na doença cardiopulmonar crônica e na imunodeficiência moderada '
                 'ou grave; rotina a partir de 70 anos). O ACIP indica a vacina a partir de 75 anos e, de 50 a 74, só com risco '
                 'aumentado.', SBIM + ' / CDC/ACIP 2025 (VSR)')
    if gestante and sexo == 'feminino':
        orientar('VSR na gestação (Abrysvo®): diretrizes divergem',
                 'Nós optamos por seguir a referência da SBIm e do PNI: a partir de 28 semanas, sem limite superior, 1 dose a cada gestação. O ACIP e o '
                 'ACOG indicam de 32 a 36 semanas, na sazonalidade, e não repetem a dose em gestação seguinte.',
                 SBIM + ' / CVE-SP/PNI 2025 (VSR na gestante) / CDC/ACIP 2025 (esquema adulto) / ACOG 2023')

    # Meningocócica ACWY no HIV: 2 doses com 8 semanas de intervalo e reforço a cada 5 anos (CRIE)
    if hiv:
        add(MENACWY, 'vacina', 'Pessoa vivendo com HIV: 2 doses de ACWY conjugada com 8 semanas de intervalo e reforço a cada '
            '5 anos.', 'HIV | 2 doses (8 sem) + reforço 5/5 anos | PNI: CRIE', SBIM_ESPECIAIS + ' / ' + CRIE + ' / ' + ACIP,
            'A', 'alta', substituir=True, esquema='hiv')
        add(HIB, 'vacina', 'Pessoa vivendo com HIV não vacinada: 2 doses com 2 meses de intervalo.',
            'HIV, não vacinado | 2 doses (0-2m)', SBIM_ESPECIAIS, 'B', esquema='hiv')
    if {'asplenia', 'anemia_falciforme'} & com:
        # Asplenia anatômica ou funcional (doença falciforme). Esquema de risco substitui o de rotina na tela e no PDF (esquema_pdf)
        add(MENACWY, 'vacina',
            'Asplenia: 2 doses com 8 semanas de intervalo e reforço a cada 5 anos.', 'Asplenia | 2 doses + reforço 5/5 anos',
            'CDC/ACIP 2025 / ' + SBIM, 'A', 'alta', substituir=True, esquema='asplenia')
        # MenB-4C no alto risco: 3 doses (0, 1-2, 6 meses) pelo ACIP (out/2024, após a bula da FDA de ago/2024) e pela SBIm.
        add('Meningocócica B (Bexsero®)', 'vacina', 'Asplenia: 3 doses (0, 1-2 e 6 meses); reforço 1 ano depois do esquema e, '
            'depois, a cada 2-3 anos (ACIP) ou a cada 3 anos (SBIm). Todas as doses do mesmo fabricante. Licenciada até 50 anos.',
            'Asplenia | 3 doses (0, 1-2, 6m) + reforços', MENB_ACIP + ' / ' + MENB_ACIP_REFORCO + ' / ' + SBIM_ESPECIAIS,
            'A', 'alta', substituir=True, esquema='asplenia')
        add(HIB, 'vacina', 'Asplenia, não vacinado: SBIm e CRIE indicam 2 doses com 2 meses de intervalo; o ACIP, dose única.',
            'Asplenia | SBIm/CRIE: 2 doses (0-2m); ACIP: 1 dose', SBIM_ESPECIAIS + ' / ' + ACIP, 'B', 'alta', substituir=True,
            esquema='asplenia')
        orientar('Meningocócica B na asplenia: diretrizes divergem',
                 'ACIP e SBIm concordam no esquema de 3 doses (0, 1-2 e 6 meses) e no primeiro reforço 1 ano depois. Divergem nos '
                 'reforços seguintes: a cada 2-3 anos pelo ACIP e a cada 3 anos pela SBIm. Mostramos os dois intervalos.',
                 MENB_ACIP_REFORCO + ' / ' + SBIM_ESPECIAIS)
    elif 'meningocócica b (bexsero®)' in titulos():
        # Cartão de rotina (SBIm): 2 doses com intervalo mínimo de 1 mês. O ACIP difere no esquema e na indicação.
        orientar('Meningocócica B de rotina: diretrizes divergem',
                 'Nós optamos por seguir a referência da SBIm: 2 doses com intervalo mínimo de 1 mês. O ACIP indica a MenB-4C (Bexsero®) de 16 a 23 '
                 'anos por decisão compartilhada, em 2 doses a 0 e 6 meses, e fora dessa faixa só com risco aumentado.',
                 SBIM + ' / ' + MENB_ACIP)
    if hiv or {'asplenia', 'anemia_falciforme'} & com:
        orientar('Hib no adulto: diretrizes divergem',
                 'Nós optamos por seguir a referência da SBIm: 2 doses com 2 meses de intervalo no adulto não vacinado com asplenia ou HIV. O ACIP indica '
                 'dose única na asplenia e não indica Hib no adulto com HIV.', SBIM_ESPECIAIS + ' / ' + ACIP)

    if 'transplante' in com:
        orientar('Transplante de medula óssea (TCTH): revacinação',
                 'Se o transplante foi de células-tronco hematopoéticas, todas as vacinas feitas antes devem ser repetidas: '
                 'inativadas a partir de 3 a 6 meses, influenza a partir de 3 a 4 meses e vacinas de vírus vivo só depois de '
                 '24 meses, sem doença do enxerto contra o hospedeiro e com reconstituição imune. Seguir o protocolo da equipe de '
                 'transplante.', SBIM_ESPECIAIS)
    if idade >= 60:
        orientar('Vacinas em situações especiais (60+)',
                 'Hepatite A depois de sorologia negativa, exposição ou surto; meningocócica ACWY (ou C) em surto ou viagem a área '
                 'de risco; tríplice viral em situação de risco aumentado (contraindicada no imunodeprimido).', SBIM)
    if imuno_listas:
        orientar('Imunossupressão',
                 'Item marcado implica imunossupressão: a triagem de vacinas foi tratada como "Sim" e as vacinas de vírus '
                 'vivo atenuado não entram.', SBIM)
    elif imuno:
        orientar('Imunossupressão informada na triagem',
                 'Imunossupressão informada na triagem: indicadas as vacinas inativadas do imunocomprometido. Defina a causa na '
                 'lista de comorbidades ou de medicações.', SBIM_ESPECIAIS)
    return orient
