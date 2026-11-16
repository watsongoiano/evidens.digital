# -*- coding: utf-8 -*-
from typing import List, Dict

def _split_refs(ref: str) -> List[str]:
    """Separa referências múltiplas preservando referências compostas como ACC/AHA.
    
    Usa ' / ' (com espaços) como separador principal para não quebrar 'ACC/AHA'.
    Fallback para ';' e ',' se ' / ' não estiver presente.
    """
    if not ref:
        return []

    # Referências somadas por regras diferentes vêm unidas por ' | ' (src/utils/condicoes.py): cada uma tem o seu link.
    if ' | ' in ref:
        return [p for parte in ref.split(' | ') for p in _split_refs(parte)]

    # Tentar separar por ' / ' primeiro (preserva ACC/AHA, ESC/EAS, etc)
    if ' / ' in ref:
        parts = [p.strip() for p in ref.split(' / ')]
        return [p for p in parts if p]
    
    # Fallback para outros separadores
    for sep in [';', ',']:
        if sep in ref:
            parts = [p.strip() for p in ref.split(sep)]
            return [p for p in parts if p]
    
    # Sem separador, retornar como está
    return [ref.strip()]

def _norm(s: str) -> str:
    return (s or '').strip().lower()

def _contains_any(haystack: str, needles: List[str]) -> bool:
    return any(n in haystack for n in needles)

def _uspstf_url_by_title(title_lc: str) -> str:
    if _contains_any(title_lc, ['hiv']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/human-immunodeficiency-virus-hiv-infection-screening'
    if _contains_any(title_lc, ['hepatite c', 'hcv']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/hepatitis-c-screening'
    if _contains_any(title_lc, ['tuberculose']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/latent-tuberculosis-infection-screening'
    if _contains_any(title_lc, ['sífilis', 'sifilis', 'vdrl', 'rpr']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/syphilis-infection-in-nonpregnant-adults-and-adolescents-screening'
    if _contains_any(title_lc, ['hepatite b', 'hbsag']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/hepatitis-b-virus-infection-in-adults-screening'
    if _contains_any(title_lc, ['gonorreia', 'gonorréia', 'gonorrhoeae', 'clamídia', 'clamidia', 'chlamydia']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/chlamydia-and-gonorrhea-screening'
    if _contains_any(title_lc, ['mamografia']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/breast-cancer-screening'
    if _contains_any(title_lc, ['brca']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/brca-related-cancer-risk-assessment-genetic-counseling-and-genetic-testing'
    if _contains_any(title_lc, ['colonoscopia', 'colorretal', 'sangue oculto']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening'
    if _contains_any(title_lc, ['melanoma', 'pele']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/skin-cancer-screening'
    if _contains_any(title_lc, ['cervical', 'papanicolaou', 'pap', 'hpv']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/cervical-cancer-screening'
    if _contains_any(title_lc, ['psa', 'próstata', 'prostata']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/prostate-cancer-screening'
    if _contains_any(title_lc, ['aorta', 'aneurisma']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/abdominal-aortic-aneurysm-screening'
    if _contains_any(title_lc, ['pulm', 'tomografia', 'tc tórax', 'tc torax', 'ldct']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/lung-cancer-screening'
    if _contains_any(title_lc, ['densitometria', 'osteoporose', 'dexa']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/osteoporosis-screening'
    if _contains_any(title_lc, ['pré-diabetes', 'prediabetes', 'diabetes tipo 2']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/screening-for-prediabetes-and-type-2-diabetes'
    if _contains_any(title_lc, ['carótida', 'carotida']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/carotid-artery-stenosis-screening'
    if _contains_any(title_lc, ['vitamina d']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/vitamin-d-deficiency-screening'
    if _contains_any(title_lc, ['depress', 'phq-9']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/depression-in-adults-screening'
    if _contains_any(title_lc, ['ovário', 'ovario']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/ovarian-cancer-screening'
    return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics'

# Fontes citadas pelo pré-natal, pelas listas e pelas síndromes hereditárias: (trecho do rótulo, URL).
# A ordem importa: o primeiro trecho contido no rótulo vence.
_FONTES_DIRETAS = [
    # Comorbidades (src/utils/condicoes.py): as específicas antes das genéricas ("acg", "aasld")
    ('eular 2016 (risco cv', 'https://doi.org/10.1136/annrheumdis-2016-209775'),
    ('eular 2022 (risco cv', 'https://doi.org/10.1136/annrheumdis-2021-221733'),
    ('eular 2010 (monitorização do les)', 'https://doi.org/10.1136/ard.2009.117200'),
    ('acr 2024 (nefrite lúpica)', 'https://doi.org/10.1002/art.43212'),
    ('eular 2022 (infecções', 'https://doi.org/10.1136/ard-2022-223335'),
    ('eular 2019 (vacinação', 'https://doi.org/10.1136/annrheumdis-2019-215882'),
    ('aad-npf 2019', 'https://doi.org/10.1016/j.jaad.2018.11.058'),
    ('acr/chest 2023', 'https://doi.org/10.1002/art.42860'),
    ('esc/ers 2022', 'https://doi.org/10.1093/eurheartj/ehac237'),
    ('ecco 2015', 'https://doi.org/10.1093/ecco-jcc/jju009'),
    ('bsg 2025', 'https://doi.org/10.1136/gutjnl-2025-335023'),
    ('acg 2017 (cuidados preventivos', 'https://doi.org/10.1038/ajg.2016.537'),
    ('aasld 2018 (hepatite b)', 'https://doi.org/10.1002/hep.29800'),
    ('aasld/idsa (hepatite c)', 'https://www.hcvguidelines.org/'),
    ('asco 2020 (hepatite b', 'https://doi.org/10.1200/JCO.20.01757'),
    ('nhlbi 2014', 'https://doi.org/10.1001/jama.2014.10517'),
    ('gina 2024', 'https://ginasthma.org/reports/'),
    ('esc 2024 (fibrilação atrial)', 'https://doi.org/10.1093/eurheartj/ehae176'),
    ('aga 2019 (doença celíaca)', 'https://doi.org/10.1053/j.gastro.2018.12.010'),
    ('bsg 2014 (doença celíaca)', 'https://doi.org/10.1136/gutjnl-2013-306578'),
    ('acg 2022 (esôfago de barrett)', 'https://doi.org/10.14309/ajg.0000000000001680'),
    ('diretriz internacional de sop 2023', 'https://doi.org/10.1210/clinem/dgad463'),
    ('acr 2020', 'https://doi.org/10.1002/acr.24180'),
    ('uspstf 2019 (brca)', 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/brca-related-cancer-risk-assessment-genetic-counseling-and-genetic-testing'),
    ('fda (bula do tofacitinibe)', 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/203214s038,208246s025,213082s010lbl.pdf'),
    ('ema 2023 (inibidores de jak)', 'https://www.ema.europa.eu/en/medicines/human/referrals/janus-kinase-inhibitors-jaki'),
    ('fda (bula do tocilizumabe)', 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2017/125276s114lbl.pdf'),
    ('buch 2011', 'https://doi.org/10.1136/ard.2010.144998'),
    ('esc 2022 (cardio-oncologia)', 'https://doi.org/10.1093/eurheartj/ehac244'),
    ('asco 2021 (eventos imunomediados)', 'https://doi.org/10.1200/JCO.21.01440'),
    ('ema 2020 (teste de dpd)', 'https://www.ema.europa.eu/en/medicines/human/referrals/fluorouracil-fluorouracil-related-substances-capecitabine-tegafur-flucytosine-containing-medicinal-products'),
    ('aha/acs/aua 2010', 'https://doi.org/10.1161/CIRCULATIONAHA.109.192695'),
    ('nccn (saúde óssea', 'https://www.nccn.org/guidelines/category_3'),
    ('ms 2024 (pcdt hiv)', 'https://portal.saude.sp.gov.br/resources/crt/assistencia/pcdt/pcdt_hiv_modulo_1_2024_1.pdf'),
    ('hivma/idsa 2024', 'https://doi.org/10.1093/cid/ciae479'),
    # Gestação (src/utils/prenatal.py): as específicas antes das genéricas ("acog pb 222", "ada 2026", "ata")
    ('acog co 767', 'https://doi.org/10.1097/AOG.0000000000003075'),
    ('acog co 797', 'https://doi.org/10.1097/AOG.0000000000003668'),
    ('acog co 495', 'https://doi.org/10.1097/AOG.0b013e318227f06b'),
    ('acog pb 201', 'https://doi.org/10.1097/AOG.0000000000002961'),
    ('acog pb 234', 'https://doi.org/10.1097/AOG.0000000000004479'),
    ('aha 2014 (ecocardiograma fetal)', 'https://doi.org/10.1161/01.cir.0000437597.44550.5d'),
    ('febrasgo 2023 (pré-eclâmpsia)', 'https://www.febrasgo.org.br/images/pec/FPS---N1---Janeiro-2023---portugues-1.pdf'),
    ('febrasgo/sbem 2022', 'https://www.febrasgo.org.br/images/pec/posicionamentos-febrasgo/FPS-N10-Outubro-2022-portugues.pdf'),
    ('febrasgo 2025 (hiv na gestação)', 'https://www.febrasgo.org.br/images/pec/posicionamentos-febrasgo/2025/novo/FPS---2025---N10---portugues.pdf'),
    ('conitec 2026 (aas', 'https://www.gov.br/conitec/pt-br/midias/consultas/relatorios/2026/relatorio-preliminar-acido-acetilsalicilico-pre-eclampsia-cp-53/@@display-file/file'),
    ('uspstf 2021 (aas', 'https://www.uspreventiveservicestaskforce.org/uspstf/document/RecommendationStatementFinal/low-dose-aspirin-use-for-the-prevention-of-morbidity-and-mortality-from-preeclampsia-preventive-medication'),
    ('uspstf 2021 (clamídia', 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/chlamydia-and-gonorrhea-screening'),
    ('uspstf 2023 (ácido fólico', 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/folic-acid-for-the-prevention-of-neural-tube-defects-preventive-medication'),
    ('ms nt 8/2025', 'https://www.gov.br/aids/pt-br/central-de-conteudo/notas-tecnicas/2025/nota-tecnica-no-8-2025-cgist-dathi-svsa-ms.pdf/@@download/file'),
    ('ms 2022 (gestação de alto risco)', 'https://bvsms.saude.gov.br/bvs/publicacoes/manual_gestacao_alto_risco.pdf'),
    ('pcdt tv ms 2022', 'https://portaldeboaspraticas.iff.fiocruz.br/biblioteca/pcdt-2022-transmissao-vertical-do-hiv-sifilis-e-hepatites-virais'),
    ('ms 2013 (suplementação de ferro)', 'https://portaldeboaspraticas.iff.fiocruz.br/biblioteca/programa-nacional-de-suplementacao-de-ferro-manual-de-condutas-gerais/'),
    ('cochrane 2015 (doppler', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6464774'),
    ('ata 2017 (tireoide na gestação)', 'https://doi.org/10.1089/thy.2016.0457'),
    ('isuog 2025 (gemelar)', 'https://doi.org/10.1002/uog.29166'),
    ('ada 2026 (seção 15)', 'https://doi.org/10.2337/dc26-S015'),  # gestação
    ('einstein pré-natal', 'https://medicalsuite.einstein.br/pratica-medica/Pathways/Pr%C3%A9%20Natal%20de%20Baixo%20Risco%20v.3.pdf'),
    ('ms 2012-2016', 'https://bvsms.saude.gov.br/bvs/publicacoes/cadernos_atencao_basica_32_prenatal.pdf'),
    ('williams 26e', 'https://www.mheducation.com/highered/mhp/product/williams-obstetrics-26e.html'),
    ('sbd 2024', 'https://doi.org/10.29327/5412848.2024-1'),
    ('ada 2026 (seção 4)', 'https://doi.org/10.2337/dc26-S004'),  # avaliação médica e comorbidades
    ('ada 2026', 'https://doi.org/10.2337/dc26-S002'),  # diagnóstico e classificação
    ('cgh 2025 (feuerstein)', 'https://doi.org/10.1016/j.cgh.2025.05.019'),
    ('drugs aging 2024 (sparling)', 'https://doi.org/10.1007/s40266-024-01143-8'),
    ('consenso brasileiro de dmg', 'https://iris.paho.org/handle/10665.2/34278'),
    ('acog pb 222', 'https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2020/06/gestational-hypertension-and-preeclampsia'),
    ('acog 2023', 'https://www.acog.org/clinical/clinical-guidance/practice-advisory/articles/2023/09/maternal-respiratory-syncytial-virus-vaccination'),
    # Vacinação (calendários, PNI e divergências entre diretrizes)
    ('sbim pacientes especiais', 'https://sbim.org.br/images/calend-vacinacao-pacientes-especiais-2026-27-260626.pdf_2026-06-29.pdf'),
    ('in cnv 2026', 'https://www.prefeitura.poa.br/sites/default/files/usu_doc/hotsites/sms/vigilancia-em-saude/INSTRU%C3%87%C3%83O%20NORMATIVA%20CNV%204a%20versao%20site%20TIMBRADO%2008102026%20(1).pdf'),
    ('manual dos crie', 'https://goias.gov.br/saude/wp-content/uploads/sites/34/2019/12/manual-crie-6-edicao-f97.pdf'),
    ('cve-sp/pni 2025 (vsr na gestante)', 'https://www.saude.sp.gov.br/resources/cve-centro-de-vigilancia-epidemiologica/areas-de-vigilancia/imunizacao/2025/vsr_gestante_esp_031225.pdf'),
    ('cdc/acip 2024 (menb-4c)', 'https://www.cdc.gov/mmwr/volumes/73/wr/mm7349a3.htm'),
    ('cdc/acip 2020 (meningocócicas)', 'https://www.cdc.gov/mmwr/volumes/69/rr/pdfs/rr6909a1-H.pdf'),
    ('cdc/acip 2025 (vsr)', 'https://www.cdc.gov/rsv/hcp/vaccine-clinical-guidance/adults.html'),
    ('cdc/acip 2025 (pneumocócica)', 'https://www.cdc.gov/pneumococcal/hcp/vaccine-recommendations/risk-indications.html'),
    ('cdc/acip 2025 (esquema adulto)', 'https://www.cdc.gov/vaccines/hcp/imz-schedules/downloads/adult/adult-combined-schedule.pdf'),
    ('anvisa 2025 (butantan-dv)', 'https://site.cff.org.br/noticia/Noticias-gerais/01/12/2025/brasil-aprova-a-primeira-vacina-de-dose-unica-do-mundo-contra-a-dengue'),
    ('pcdt-ist', 'https://www.gov.br/aids/pt-br/central-de-conteudo/pcdts'),
    ('nccn', 'https://www.nccn.org/guidelines/category_2'),
    # Rastreio de câncer (src/utils/rastreio_cancer.py)
    ('cbr/sbm/febrasgo 2023', 'https://doi.org/10.1590/0100-3984.2023.0064-en'),
    ('ms nt 626/2025', 'https://ninho.inca.gov.br/jspui/bitstream/123456789/17713/1/SEI_0050548355_Nota_Tecnica_626.pdf'),
    ('ms/inca nt 9/2023', 'https://antigo.inca.gov.br/sites/ufu.sti.inca.local/files//media/document//notatecnica_rastreio_cancer_de_prostata_2023.pdf'),
    ('sbu/sboc/sbrt', 'https://portaldaurologia.org.br/files/arquivos/filee4e2d7e8d48f92bae5f8f445d4e71e43.pdf'),
    ('ms/inca 2026', 'https://www.gov.br/inca/pt-br/assuntos/noticias/2026/sus-adota-novo-exame-para-detectar-cancer-de-intestino-antes-dos-sintomas'),
    ('usmstf 2022', 'https://doi.org/10.1053/j.gastro.2021.10.007'),
    ('sbct-sbpt-cbr 2024', 'https://dx.doi.org/10.36416/1806-3756/e20230233'),
    ('acs 2023', 'https://doi.org/10.3322/caac.21811'),
    ('acog co 723', 'https://pubmed.ncbi.nlm.nih.gov/28937575/'),
    ('asge 2012', 'https://pubmed.ncbi.nlm.nih.gov/22579258/'),
    ('acs 2007', 'https://doi.org/10.3322/canjclin.57.2.75'),
    ('kratz 2017', 'https://doi.org/10.1158/1078-0432.CCR-17-0408'),
    ('igclc 2020', 'https://doi.org/10.1016/S1470-2045(20)30219-9'),
    ('usmstf 2017', 'https://doi.org/10.1038/ajg.2017.174'),
    ('acg', 'https://gi.org/clinical-guidelines/'),
    ('easl 2022', 'https://doi.org/10.1016/j.jhep.2022.03.033'),
    ('endocrine society 2012', 'https://doi.org/10.1210/jc.2012-1230'),
    ('aha/acc 2024', 'https://doi.org/10.1161/CIR.0000000000001250'),
    ('aha/acc/hfsa 2022', 'https://doi.org/10.1161/CIR.0000000000001063'),
    ('acc/aha 2022', 'https://doi.org/10.1161/CIR.0000000000001106'),
    ('aha/asa 2015', 'https://doi.org/10.1161/STR.0000000000000070'),
    ('hrs/ehra/aphrs 2013', 'https://doi.org/10.1016/j.hrthm.2013.05.014'),
    ('hrs 2007', 'https://doi.org/10.1016/j.hrthm.2007.07.020'),
    ('ats/ers 2003', 'https://doi.org/10.1164/rccm.168.7.818'),
    ('ehra 2021', 'https://doi.org/10.1093/europace/euab065'),
    ('chest 2012', 'https://doi.org/10.1378/chest.11-2292'),
    ('asco 2019', 'https://doi.org/10.1200/JCO.19.01696'),
    ('asmbs 2019', 'https://doi.org/10.1016/j.soard.2019.10.025'),
    ('kdigo 2025', 'https://kdigo.org/guidelines/adpkd/'),
    ('nice cg185', 'https://www.nice.org.uk/guidance/cg185'),
    ('nice ng217', 'https://www.nice.org.uk/guidance/ng217'),
    ('ms 2025 (dna-hpv)', 'https://www.gov.br/conitec/pt-br/midias/relatorios/portaria/2025/portaria-conjunta-saes-sectics-no-13-de-29-de-julho-de-2025'),
    ('sboc 2026', 'https://sboc.org.br/wp-content/uploads/2026/04/Diretrizes-SBOC-2026-Colo-do-%E2%94%9C%E2%95%91tero-v5-VERS%E2%94%9CaO-FINAL.pdf'),
    ('acog 2026', 'https://doi.org/10.1097/AOG.0000000000006257'),
    ('rathore', 'https://doi.org/10.1001/jama.289.7.871'),
    ('aad 2019', 'https://doi.org/10.1016/j.jaad.2018.08.055'),
    ('aao 2016', 'https://doi.org/10.1016/j.ophtha.2016.01.058'),
    ('aao 2020', 'https://doi.org/10.1016/j.ophtha.2020.10.022'),
    ('aga 2020', 'https://doi.org/10.1053/j.gastro.2020.03.088'),
    ('ash 2023', 'https://doi.org/10.1182/bloodadvances.2023010177'),
    ('ats 2011', 'https://doi.org/10.1164/rccm.2008-740ST'),
    ('caps 2020', 'https://doi.org/10.1136/gutjnl-2019-319352'),
    ('idsa 2013', 'https://doi.org/10.1093/cid/cit684'),
    ('maastricht vi', 'https://doi.org/10.1136/gutjnl-2022-327745'),
    ('bhof 2022', 'https://doi.org/10.1007/s00198-021-05900-y'),
    ('aua/suo 2023', 'https://www.auanet.org/guidelines-and-quality/guidelines/early-detection-of-prostate-cancer-guidelines'),
    ('eau 2024', 'https://uroweb.org/guidelines/prostate-cancer'),
    ('svs 2018', 'https://doi.org/10.1016/j.jvs.2017.10.044'),
    ('ada/apa 2004', 'https://doi.org/10.2337/diacare.27.2.596'),
    ('ms 2019', 'https://bvsms.saude.gov.br/bvs/publicacoes/manual_recomendacoes_controle_tuberculose_brasil_2_ed.pdf'),
    ('asbmr 2016', 'https://doi.org/10.1002/jbmr.2708'),
    ('bsr 2017', 'https://doi.org/10.1093/rheumatology/kew479'),
    ('kdigo 2009', 'https://kdigo.org/guidelines/transplant-recipient/'),
    ('aasld 2018', 'https://doi.org/10.1002/hep.29800'),
]


def _fonte_direta(token_lc: str, title_lc: str) -> str:
    if token_lc.startswith('aasld') and '(' not in token_lc:
        # carcinoma hepatocelular (ultrassonografia na cirrose) ou esteatose (FIB-4)
        return ('https://doi.org/10.1097/HEP.0000000000000466' if 'ultrassonografia' in title_lc
                else 'https://doi.org/10.1097/HEP.0000000000000323')
    if token_lc.startswith('acr') and _contains_any(title_lc, ['mamografia', 'mama']):
        return 'https://doi.org/10.1016/j.jacr.2023.04.002'  # American College of Radiology, não o de Reumatologia
    if token_lc.startswith('uspstf') and _contains_any(title_lc, ['proteína/creatinina']):
        return ('https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/'
                'low-dose-aspirin-use-for-the-prevention-of-morbidity-and-mortality-from-preeclampsia-preventive-medication')
    for trecho, url in _FONTES_DIRETAS:
        if trecho in token_lc:
            return url
    return ''


def _resolve_url_by_org(token_lc: str, title_lc: str) -> str:
    direta = _fonte_direta(token_lc, title_lc)
    if direta:
        return direta
    # Tratar ACC/AHA como um caso especial
    if 'acc' in token_lc and 'aha' in token_lc:
        if '2019' in token_lc:
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000000625'
        if '2025' in token_lc:
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000001309'
        return 'https://www.ahajournals.org/journal/circ'
    
    # Tratar ESC/EAS como um caso especial
    if 'esc' in token_lc and 'eas' in token_lc:
        if '2019' in token_lc:
            return 'https://academic.oup.com/eurheartj/article/41/1/111/5556353'
        return 'https://academic.oup.com/eurheartj'
    
    if token_lc.startswith('uspstf'):
        url = _uspstf_url_by_title(title_lc)
        # Adicionar ano específico se disponível
        if '2024' in token_lc and _contains_any(title_lc, ['mamografia', 'mama']):
            return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/breast-cancer-screening'
        if '2021' in token_lc and _contains_any(title_lc, ['colonoscopia', 'colorretal']):
            return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening'
        if '2018' in token_lc and _contains_any(title_lc, ['pulm', 'tomografia']):
            return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/lung-cancer-screening'
        return url
    if token_lc.startswith('ada'):
        if _contains_any(title_lc, ['glicemia', 'glicose', 'diabetes']):
            return 'https://diabetesjournals.org/care/article/47/Supplement_1/S20/153954/2-Diagnosis-and-Classification-of-Diabetes'
        return 'https://diabetesjournals.org/care/issue/47/Supplement_1'
    if 'aha/acc' in token_lc:
        if '2025' in token_lc or _contains_any(title_lc, ['colesterol', 'lipid', 'ldl', 'hdl', 'triglicerid']):
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000001309'
        if '2019' in token_lc or _contains_any(title_lc, ['ecg', 'eletrocardiograma', 'cardiovascular']):
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000000625'
        return 'https://www.ahajournals.org/journal/circ'
    if token_lc.startswith('aha'):
        if '2025' in token_lc:
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000001356'
        if '2022' in token_lc:
            return 'https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063'
        return 'https://www.ahajournals.org/journal/circ'
    if token_lc.startswith('kdigo'):
        return 'https://kdigo.org/guidelines/ckd-evaluation-and-management/'
    if token_lc.startswith('sbc'):
        if '2025' in token_lc:
            return 'https://abccardiol.org/wp-content/uploads/articles_xml/0066-782X-abc-122-09-e20250624/0066-782X-abc-122-09-e20250624.x66747.pdf'
        if '2019' in token_lc:
            return 'http://publicacoes.cardiol.br/portal/abc/portugues/2019/v11303/pdf/11303022.pdf'
        if '2018' in token_lc:
            return 'https://abccardiol.org/wp-content/uploads/articles_xml/0066-782X-abc-111-03-0436/0066-782X-abc-111-03-0436.x66747.pdf'
        return 'https://abccardiol.org/diretrizes/'
    if token_lc.startswith('ase'):
        return 'https://www.asecho.org/clinical-guidelines/'
    if 'sbim' in token_lc and 'cdc' in token_lc:
        # Referência combinada SBIm/CDC
        return 'https://sbim.org.br/calendarios-de-vacinacao'
    if 'sbim' in token_lc:
        return 'https://sbim.org.br/calendarios-de-vacinacao'
    if 'cdc' in token_lc:
        if _contains_any(title_lc, ['covid']):
            return 'https://www.cdc.gov/vaccines/hcp/imz-schedules/adult-age.html'
        return 'https://www.cdc.gov/vaccines/hcp/imz-schedules/index.html'
    if token_lc.startswith('cdc') and _contains_any(title_lc, ['rsv']):
        return 'https://www.cdc.gov/rsv/hcp/vaccine-clinical-guidance/adults.html'
    if token_lc.startswith('ms') and '2024' in token_lc:
        return 'https://www.gov.br/saude/pt-br'
    if 'acc' in token_lc and 'aha' in token_lc and '2019' in token_lc:
        return 'https://pmc.ncbi.nlm.nih.gov/articles/PMC8351755/'
    if 'esc' in token_lc and 'eas' in token_lc and '2019' in token_lc:
        return 'https://academic.oup.com/eurheartj/article/41/1/111/5556353'
    if 'eas' in token_lc and '2022' in token_lc:
        return 'https://academic.oup.com/eurheartj/article/43/39/3925/6670929'
    if token_lc.startswith('gold'):
        return 'https://goldcopd.org/'
    if token_lc.startswith('ata'):
        return 'https://www.thyroid.org/professionals/ata-professional-guidelines/'
    if token_lc.startswith('acr'):
        return 'https://www.rheumatology.org/Practice-Quality/Clinical-Support/Clinical-Practice-Guidelines'
    if token_lc.startswith('sbn'):
        return 'https://sbn.org.br/diretrizes/'
    return ''

def build_reference_links(title: str, referencia: str) -> List[Dict[str, str]]:
    title_lc = _norm(title)
    tokens = _split_refs(referencia)
    links: List[Dict[str, str]] = []
    for tok in tokens:
        tok_lc = _norm(tok)
        url = _resolve_url_by_org(tok_lc, title_lc)
        links.append({'label': tok, 'url': url})
    return links

def build_reference_html(links: List[Dict[str, str]]) -> str:
    parts = []
    for item in links or []:
        label = item.get('label') or ''
        url = item.get('url') or ''
        if url:
            parts.append(f"<a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{label}</a>")
        else:
            parts.append(label)
    return ' | '.join(parts)