# -*- coding: utf-8 -*-
from typing import List, Dict

def _split_refs(ref: str) -> List[str]:
    if not ref:
        return []
    parts = []
    for sep in ['/', ';', ',']:
        if sep in ref:
            parts = [p.strip() for p in ref.split(sep)]
            break
    if not parts:
        parts = [ref.strip()]
    return [p for p in parts if p]

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
    if _contains_any(title_lc, ['aorta']):
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

def _resolve_url_by_org(token_lc: str, title_lc: str) -> str:
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
    if token_lc.startswith('kdigo'):
        return 'https://kdigo.org/guidelines/ckd-evaluation-and-management/'
    if token_lc.startswith('sbc'):
        if '2019' in token_lc:
            return 'http://publicacoes.cardiol.br/portal/abc/portugues/2019/v11303/pdf/11303022.pdf'
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