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
ECCO_ANEMIA = 'ECCO 2015 (anemia na DII)'
BSG_DII = 'BSG 2025 (vigilância colorretal na DII)'
ACG_DII = 'ACG 2017 (cuidados preventivos na DII)'
AASLD_HBV = 'AASLD 2018 (hepatite B)'
AASLD_HCV = 'AASLD/IDSA (hepatite C)'
ASCO_HBV = 'ASCO 2020 (hepatite B no câncer)'
NHLBI_FALCIFORME = 'NHLBI 2014 (doença falciforme)'
GINA = 'GINA 2024'
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
    'hepatite_b_cronica': ('Hepatite B: o que se aplica', 'Define o rastreio de carcinoma hepatocelular sem cirrose (AASLD 2018).', [
        ('hbv_risco_chc', 'História familiar de carcinoma hepatocelular, coinfecção por HIV ou hepatite D, homem asiático ≥ 40 anos, '
                          'mulher asiática ≥ 50 anos ou origem africana subsaariana')]),
}
# Diagnóstico antigo "doença inflamatória autoimune" (um item só): ainda aceito vindo de formulários salvos.
LEGADO_AUTOIMUNE = 'doenca_autoimune'


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


def aplicar(recs, idade, sexo, comorbidades, medicacoes, familia, gestante=False, tabagismo=None, imc=None,
            imunossuprimido=None, cd4=None, idade_ccr_familiar=None):
    """Soma às recomendações o que as listas disparam. Devolve as orientações (sem pedido/receita).

    ``imunossuprimido``: resposta "Sim" da triagem de imunossupressão (inclui a implicada pelas listas); sem ela,
    vale só o que as listas implicam. ``cd4``: LT-CD4+ da pessoa vivendo com HIV (imunodeficiência grave < 200).
    ``idade_ccr_familiar``: idade do diagnóstico do familiar mais jovem com câncer colorretal (opcional).
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
                     'vier primeiro). Informe a idade do familiar na história familiar para o motor calcular o início.', USMSTF)
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

    # ---------------- Comorbidades ----------------
    com_tipo = bool(set(TIPOS_DE_DIABETES) & com)
    diabetico = com_tipo or 'diabetes_sem_tipo' in com or 'insulina' in med
    if 'diabetes_sem_tipo' in com:
        orientar('HbA1c ≥ 6,5%: informe o tipo de diabetes',
                 'HbA1c ≥ 6,5% é critério de diabetes (confirmar com um segundo exame se não houver hiperglicemia inequívoca), '
                 'mas não define o tipo. As recomendações foram montadas como para uma pessoa com diabetes. Marque o tipo '
                 'para refinar (por exemplo, TSH no tipo 1).', 'ADA 2026')
    if 'insulina' in med and not com_tipo:
        orientar('Insulina em uso: informe o tipo de diabetes',
                 'A insulina é usada no diabetes tipo 1, no tipo 2, no gestacional e em outros tipos; por isso não marca um tipo '
                 'sozinha. As recomendações foram montadas como para uma pessoa com diabetes. Marque o tipo para refinar '
                 '(por exemplo, TSH no tipo 1).', 'ADA 2026')
    if 'diabetes_gestacional_previo' in com and sexo == 'feminino' and not gestante and not diabetico:
        for titulo in ('Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'):
            add(titulo, 'laboratorio',
                'Diabetes gestacional em gestação anterior: rastrear pré-diabetes e diabetes por toda a vida, pelo menos a cada 3 anos.',
                'Diabetes gestacional prévio | Pelo menos a cada 3 anos', 'ADA 2026', 'B', 'alta')
    if 'pre_diabetes' in com:
        add('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'Pré-diabetes: reavaliar a glicemia ao menos uma vez por ano.',
            'Pré-diabetes | Anual', 'ADA 2025', 'B')
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
            add(titulo, 'laboratorio', 'Para o cálculo do FIB-4 (idade, AST, ALT, plaquetas): estratifica risco de fibrose '
                'avançada; FIB-4 ≥ 1,3 pede elastografia.', 'MASLD | FIB-4 a cada 1-2 anos', 'AASLD 2023 / ADA 2025', 'B')
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
        for titulo in ('Cálcio iônico, soro', 'Fósforo, soro', 'Creatinina, soro', 'Fosfatase alcalina, soro',
                       'Paratormônio (PTH), soro'):
            add(titulo, 'laboratorio', 'Osteoporose: investigar causas secundárias no diagnóstico (cálcio, fósforo, função '
                'renal, fosfatase alcalina e PTH) antes de iniciar o tratamento.', 'Osteoporose | Avaliação inicial', 'BHOF 2022', 'B')
    if 'gota' in com:
        add('Ácido úrico, soro', 'laboratorio', 'Tratamento por alvo: ácido úrico < 6 mg/dL.', 'Gota | Alvo < 6 mg/dL',
            'ACR 2020', 'A')
    if 'gota' in com:
        add('Creatinina, soro', 'laboratorio', 'Gota: função renal para a dose do hipouricemiante e para a escolha do '
            'anti-inflamatório da crise.', 'Gota | Periódico', 'ACR 2020', 'B')
        orientar('Gota: comorbidades', 'Rastrear e tratar hipertensão, diabetes, dislipidemia, obesidade e doença renal, '
                 'frequentes na gota. Evitar diurético para tratar a hipertensão quando houver alternativa.', 'ACR 2020 / ' + EULAR_CV_DRM)

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
                     'Marque os detalhes do item para o sistema calcular.', BSG_DII)
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
                 'O item antigo reunia doenças com acompanhamento diferente. Escolha na lista a doença (artrite reumatoide, '
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
                '(vacinar se suscetível). Anti-HDV se houver fator de risco.', 'Hepatite B crônica | Avaliação inicial',
                AASLD_HBV, 'B')
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
        fatores = [nome for nome, sim in (('sexo masculino', sexo == 'masculino'), ('mais de 50 anos', idade > 50),
                                          ('tabagismo', fumante), ('obesidade', obeso)) if sim]
        if len(fatores) >= 3:
            add('Endoscopia digestiva alta', 'imagem',
                'Doença do refluxo crônica com 3 ou mais fatores de risco de esôfago de Barrett (sexo masculino, mais de 50 '
                'anos, tabagismo, obesidade): endoscopia única de rastreio.', 'Refluxo crônico com fatores de risco | Uma vez', ACG_BARRETT, 'C')
        else:
            orientar('Refluxo: rastreio de esôfago de Barrett',
                     'Endoscopia única de rastreio se refluxo crônico e 3 ou mais fatores: sexo masculino, mais de 50 anos, '
                     'raça branca, tabagismo, obesidade, esôfago de Barrett ou adenocarcinoma de esôfago em parente de 1º grau.',
                     ACG_BARRETT)
    if 'sop' in com and sexo == 'feminino' and not gestante:
        add('TOTG-75g (Teste Oral de Tolerância à Glicose), soro', 'laboratorio',
            'Síndrome dos ovários policísticos: avaliar a glicemia no diagnóstico e a cada 1-3 anos, qualquer que seja o IMC '
            '(TOTG preferido; glicemia de jejum ou HbA1c como alternativa).', 'Síndrome dos ovários policísticos | A cada 1-3 anos',
            PCOS, 'B')
        add('Colesterol total e frações, soro', 'laboratorio',
            'Síndrome dos ovários policísticos: perfil lipídico no diagnóstico; depois, conforme o risco cardiovascular.',
            'Síndrome dos ovários policísticos | Avaliação inicial', PCOS, 'B')

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
                 'O motor seguiu a SBIm e os CRIE, que não listam o tabagismo como risco, e não incluiu a VPC20. O ACIP indica '
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
        risco_vsr = bool({'dpoc', 'asma_grave', 'dcv_aterosclerotica', 'cardiopatia', 'insuficiencia_cardiaca'} & com) \
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
                 'O motor seguiu a SBIm (a partir de 18 anos na doença cardiopulmonar crônica e na imunodeficiência moderada '
                 'ou grave; rotina a partir de 70 anos). O ACIP indica a vacina a partir de 75 anos e, de 50 a 74, só com risco '
                 'aumentado.', SBIM + ' / CDC/ACIP 2025 (VSR)')
    if gestante and sexo == 'feminino':
        orientar('VSR na gestação (Abrysvo®): diretrizes divergem',
                 'O motor seguiu a SBIm e o PNI: a partir de 28 semanas, sem limite superior, 1 dose a cada gestação. O ACIP e o '
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
                 'reforços seguintes: a cada 2-3 anos pelo ACIP e a cada 3 anos pela SBIm. O motor mostra os dois intervalos.',
                 MENB_ACIP_REFORCO + ' / ' + SBIM_ESPECIAIS)
    elif 'meningocócica b (bexsero®)' in titulos():
        # Cartão de rotina (SBIm): 2 doses com intervalo mínimo de 1 mês. O ACIP difere no esquema e na indicação.
        orientar('Meningocócica B de rotina: diretrizes divergem',
                 'O motor seguiu a SBIm: 2 doses com intervalo mínimo de 1 mês. O ACIP indica a MenB-4C (Bexsero®) de 16 a 23 '
                 'anos por decisão compartilhada, em 2 doses a 0 e 6 meses, e fora dessa faixa só com risco aumentado.',
                 SBIM + ' / ' + MENB_ACIP)
    if hiv or {'asplenia', 'anemia_falciforme'} & com:
        orientar('Hib no adulto: diretrizes divergem',
                 'O motor seguiu a SBIm: 2 doses com 2 meses de intervalo no adulto não vacinado com asplenia ou HIV. O ACIP indica '
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
