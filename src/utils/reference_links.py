# -*- coding: utf-8 -*-
from typing import List, Dict

def _split_refs(ref: str) -> List[str]:
    """Separa referências múltiplas preservando referências compostas como ACC/AHA.
    
    Usa ' / ' (com espaços) como separador principal para não quebrar 'ACC/AHA'.
    Fallback para ';' e ',' se ' / ' não estiver presente.
    """
    if not ref:
        return []
    
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
    if _contains_any(title_lc, ['colonoscopia', 'colorretal']):
        return 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening'
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
    ('einstein pré-natal', 'https://medicalsuite.einstein.br/pratica-medica/Pathways/Pr%C3%A9%20Natal%20de%20Baixo%20Risco%20v.3.pdf'),
    ('ms 2012-2016', 'https://bvsms.saude.gov.br/bvs/publicacoes/cadernos_atencao_basica_32_prenatal.pdf'),
    ('williams 26e', 'https://www.mhprofessional.com/williams-obstetrics-26e-9781260462746-usa'),
    ('consenso brasileiro de dmg', 'https://iris.paho.org/handle/10665.2/34278'),
    ('acog pb 222', 'https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2020/06/gestational-hypertension-and-preeclampsia'),
    ('acog 2025', 'https://www.acog.org/clinical/clinical-guidance/practice-advisory/articles/2023/09/maternal-respiratory-syncytial-virus-vaccination'),
    ('pcdt-ist', 'https://www.gov.br/aids/pt-br/central-de-conteudo/pcdts'),
    ('nccn', 'https://www.nccn.org/guidelines/category_2'),
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
    ('bhof 2022', 'https://doi.org/10.1007/s00198-021-05900-y'),
    ('aua/suo 2023', 'https://www.auanet.org/guidelines-and-quality/guidelines/early-detection-of-prostate-cancer-guidelines'),
    ('eau 2024', 'https://uroweb.org/guidelines/prostate-cancer'),
    ('svs 2018', 'https://doi.org/10.1016/j.jvs.2017.10.044'),
    ('ada/apa 2004', 'https://doi.org/10.2337/diacare.27.2.596'),
]


def _fonte_direta(token_lc: str, title_lc: str) -> str:
    if token_lc.startswith('aasld'):
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