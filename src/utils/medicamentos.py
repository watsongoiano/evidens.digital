"""Medicamentos de uso contínuo, por princípio ativo, e a classe a que pertencem.

A tela oferece o princípio ativo (busca por nome); o motor trabalha com a classe
(``condicoes.MEDICACOES``), que é o que define exame, vacina e coerência. A lista
de princípios ativos foi conferida com o bulário do Whitebook
(https://whitebook.pebmed.com.br/medicamentos/), restrita ao que se usa de forma
contínua; antibióticos, analgésicos e outros de uso agudo ficam de fora.

Cada item é ``'Rótulo'`` ou ``'Rótulo|sinônimos de busca'``; uma tupla
``(item, [classes])`` troca as classes do grupo (associações em dose fixa).
"""
from __future__ import annotations

import re
import unicodedata

# (grupo, classes do grupo, palavras de busca do grupo, itens)
GRUPOS = [
    ('Estatinas', ['estatina'], 'estatina colesterol', [
        'Sinvastatina', 'Atorvastatina', 'Rosuvastatina', 'Pravastatina', 'Pitavastatina', 'Fluvastatina', 'Lovastatina',
        ('Ezetimiba + sinvastatina', ['estatina', 'outro_hipolipemiante']),
        ('Rosuvastatina + ezetimiba', ['estatina', 'outro_hipolipemiante']),
    ]),
    ('Outros hipolipemiantes', ['outro_hipolipemiante'], 'colesterol triglicerideos fibrato', [
        'Ezetimiba', 'Fenofibrato', 'Ciprofibrato', 'Bezafibrato', 'Genfibrozila', 'Ácido bempedoico', 'Evolocumabe',
        'Alirocumabe', 'Inclisirana', 'Colestiramina', 'Ômega-3 (ésteres etílicos)',
    ]),
    ('IECA', ['ieca_bra'], 'ieca pressao anti-hipertensivo', [
        'Captopril', 'Enalapril', 'Ramipril', 'Lisinopril', 'Perindopril', 'Benazepril',
    ]),
    ('BRA', ['ieca_bra'], 'bra sartana pressao anti-hipertensivo', [
        'Losartana', 'Valsartana', 'Olmesartana', 'Candesartana', 'Telmisartana', 'Irbesartana',
    ]),
    ('Bloqueadores de canal de cálcio', ['bcc'], 'bcc pressao anti-hipertensivo', [
        'Anlodipino|amlodipina anlodipina', 'Levanlodipino', 'Nifedipino', 'Felodipino', 'Lercanidipino', 'Lacidipino',
        'Manidipino', 'Nitrendipino', 'Diltiazem', 'Verapamil',
    ]),
    ('Diuréticos', ['tiazidico'], 'diuretico pressao', [
        'Hidroclorotiazida', 'Clortalidona', 'Indapamida',
        ('Furosemida', ['diuretico_alca']), ('Bumetanida', ['diuretico_alca']),
        ('Espironolactona', ['espironolactona']), ('Eplerenona', ['espironolactona']),
        ('Amilorida', ['espironolactona']),
    ]),
    ('Betabloqueadores', ['betabloqueador'], 'betabloqueador', [
        ('Atenolol', ['betabloqueador', 'betabloqueador_has']), ('Metoprolol', ['betabloqueador', 'betabloqueador_has']),
        ('Nebivolol', ['betabloqueador', 'betabloqueador_has']), 'Carvedilol', 'Bisoprolol', 'Propranolol',
    ]),
    ('Outros anti-hipertensivos', ['anti_hipertensivo_outro'], 'pressao anti-hipertensivo', [
        'Hidralazina', 'Clonidina', 'Metildopa', 'Minoxidil (oral)', 'Alisquireno',
    ]),
    ('Associações anti-hipertensivas', ['ieca_bra', 'tiazidico'], 'pressao anti-hipertensivo associacao', [
        'Losartana + hidroclorotiazida', 'Valsartana + hidroclorotiazida', 'Olmesartana + hidroclorotiazida',
        'Candesartana + hidroclorotiazida', 'Telmisartana + hidroclorotiazida', 'Irbesartana + hidroclorotiazida',
        'Enalapril + hidroclorotiazida', 'Perindopril + indapamida',
        ('Valsartana + anlodipino', ['ieca_bra', 'bcc']), ('Olmesartana + anlodipino', ['ieca_bra', 'bcc']),
        ('Losartana + anlodipino', ['ieca_bra', 'bcc']), ('Perindopril + anlodipino', ['ieca_bra', 'bcc']),
        ('Perindopril + indapamida + anlodipino', ['ieca_bra', 'tiazidico', 'bcc']),
        ('Atenolol + clortalidona', ['betabloqueador', 'tiazidico']),
    ]),
    ('Insuficiência cardíaca, arritmia e angina', ['cardio_outro'], 'coracao', [
        ('Sacubitril + valsartana|entresto', ['arni']), ('Amiodarona', ['amiodarona']),
        ('Digoxina', ['cardio_outro', 'digoxina']), 'Ivabradina', 'Propafenona', ('Sotalol', ['cardio_outro', 'sotalol']), 'Mononitrato de isossorbida', 'Dinitrato de isossorbida',
        'Trimetazidina', 'Ranolazina',
    ]),
    ('Antiagregantes', ['antiagregante'], 'antiplaquetario', [
        'AAS (ácido acetilsalicílico)|aspirina', 'Clopidogrel', 'Ticagrelor', 'Prasugrel', 'Ticlopidina', 'Cilostazol',
    ]),
    ('Anticoagulantes', ['doac'], 'anticoagulante', [
        ('Varfarina|marevan', ['varfarina']), 'Rivaroxabana', 'Apixabana', 'Edoxabana', 'Dabigatrana',
        ('Enoxaparina', ['heparina']),
    ]),
    ('Antidiabéticos', ['idpp4_pioglitazona'], 'diabetes', [
        ('Metformina|glifage', ['metformina']),
        ('Glibenclamida', ['sulfonilureia']), ('Gliclazida', ['sulfonilureia']), ('Glimepirida', ['sulfonilureia']),
        'Sitagliptina', 'Vildagliptina', 'Linagliptina', 'Saxagliptina', 'Alogliptina', 'Pioglitazona', 'Acarbose',
        ('Dapagliflozina', ['isglt2']), ('Empagliflozina', ['isglt2']), ('Canagliflozina', ['isglt2']),
        ('Semaglutida', ['aglp1']), ('Liraglutida', ['aglp1']), ('Dulaglutida', ['aglp1']), ('Tirzepatida', ['aglp1']),
        ('Sitagliptina + metformina', ['idpp4_pioglitazona', 'metformina']),
        ('Vildagliptina + metformina', ['idpp4_pioglitazona', 'metformina']),
        ('Linagliptina + metformina', ['idpp4_pioglitazona', 'metformina']),
        ('Dapagliflozina + metformina', ['isglt2', 'metformina']),
        ('Empagliflozina + linagliptina', ['isglt2', 'idpp4_pioglitazona']),
    ]),
    ('Insulinas', ['insulina'], 'diabetes insulina', [
        'Insulina NPH', 'Insulina regular', 'Insulina glargina', 'Insulina degludeca', 'Insulina detemir',
        'Insulina icodeca', 'Insulina asparte', 'Insulina lispro', 'Insulina glulisina', 'Insulina bifásica',
        ('Insulina glargina + lixisenatida', ['insulina', 'aglp1']),
        ('Insulina degludeca + liraglutida', ['insulina', 'aglp1']),
    ]),
    ('Tireoide', ['antitireoidiano'], 'tireoide', [
        ('Levotiroxina|puran synthroid euthyrox', ['levotiroxina']), 'Metimazol (tiamazol)|tapazol', 'Propiltiouracila',
    ]),
    ('Asma e DPOC', ['inalatorio'], 'bombinha inalatorio broncodilatador asma dpoc', [
        'Salbutamol', 'Fenoterol', 'Terbutalina', 'Ipratrópio', 'Formoterol', 'Tiotrópio', 'Umeclidínio',
        'Budesonida inalatória', 'Beclometasona inalatória', 'Fluticasona inalatória', 'Mometasona inalatória',
        'Formoterol + budesonida', 'Formoterol + beclometasona', 'Salmeterol + fluticasona', 'Vilanterol + fluticasona',
        'Umeclidínio + vilanterol', 'Indacaterol + glicopirrônio', 'Tiotrópio + olodaterol',
        'Fluticasona + umeclidínio + vilanterol', 'Beclometasona + formoterol + glicopirrônio',
        'Montelucaste', 'Teofilina', 'Omalizumabe', 'Mepolizumabe',
    ]),
    ('Protetores gástricos', ['ibp'], 'estomago ibp prazol', [
        'Omeprazol', 'Pantoprazol', 'Esomeprazol', 'Lansoprazol', 'Dexlansoprazol', 'Rabeprazol', 'Vonoprazana',
    ]),
    ('Antidepressivos', ['antidepressivo'], 'depressao ansiedade', [
        'Sertralina', 'Fluoxetina', 'Escitalopram', 'Citalopram', 'Paroxetina', 'Fluvoxamina', 'Venlafaxina',
        'Desvenlafaxina', 'Duloxetina', 'Vortioxetina', 'Vilazodona', 'Bupropiona', 'Mirtazapina', 'Trazodona',
        'Agomelatina', 'Amitriptilina', 'Nortriptilina', 'Clomipramina', 'Imipramina',
    ]),
    ('Ansiolíticos e hipnóticos', ['sedativo'], 'ansiedade insonia benzodiazepinico', [
        'Clonazepam|rivotril', 'Alprazolam', 'Bromazepam', 'Diazepam', 'Lorazepam', 'Zolpidem', 'Eszopiclona', 'Zopiclona',
    ]),
    ('Antipsicóticos e estabilizadores de humor', ['antipsicotico_atipico'], 'antipsicotico', [
        'Quetiapina', 'Olanzapina', 'Risperidona', 'Aripiprazol', ('Clozapina', ['antipsicotico_atipico', 'clozapina']),
        'Paliperidona', 'Ziprasidona',
        'Lurasidona', 'Brexpiprazol', 'Amissulprida',
        ('Haloperidol', ['antipsicotico_tipico']), ('Clorpromazina', ['antipsicotico_tipico']),
        ('Levomepromazina', ['antipsicotico_tipico']), ('Lítio|carbolitium', ['litio']),
    ]),
    ('Anticonvulsivantes', ['anticonvulsivante'], 'epilepsia convulsao', [
        ('Ácido valproico / divalproato', ['anticonvulsivante', 'valproato']),
        ('Carbamazepina', ['anticonvulsivante', 'carbamazepina']), 'Oxcarbazepina', 'Lamotrigina', 'Levetiracetam',
        ('Fenitoína', ['anticonvulsivante', 'fenitoina']), ('Fenobarbital', ['anticonvulsivante', 'fenobarbital']), 'Topiramato', 'Lacosamida', 'Clobazam', 'Gabapentina', 'Pregabalina',
    ]),
    ('Parkinson, demência e TDAH', ['neuro_outro'], 'parkinson alzheimer demencia tdah', [
        'Levodopa + benserazida', 'Levodopa + carbidopa', 'Pramipexol', 'Rasagilina', 'Amantadina', 'Biperideno',
        'Donepezila', 'Rivastigmina', 'Galantamina', 'Memantina', 'Metilfenidato', 'Lisdexanfetamina',
    ]),
    ('Corticoides sistêmicos', ['corticoide_sistemico', 'corticoide_cronico'], 'corticoide', [
        'Prednisona', 'Prednisolona', 'Metilprednisolona', 'Deflazacorte', 'Dexametasona', 'Hidrocortisona',
    ]),
    ('Imunossupressores e imunobiológicos', ['imunossupressor'], 'imunossupressor imunobiologico biologico', [
        ('Metotrexato', ['imunossupressor', 'metotrexato']), ('Azatioprina', ['imunossupressor', 'azatioprina']),
        ('Leflunomida', ['imunossupressor', 'leflunomida']),
        ('Micofenolato', ['imunossupressor', 'micofenolato']), ('Ciclosporina', ['imunossupressor', 'inibidor_calcineurina', 'ciclosporina']),
        ('Tacrolimo', ['imunossupressor', 'inibidor_calcineurina', 'tacrolimo']),
        ('Sirolimo', ['imunossupressor', 'inibidor_mtor']), ('Everolimo', ['imunossupressor', 'inibidor_mtor']),
        ('Tofacitinibe|inibidor de jak', ['imunossupressor', 'biologico', 'inibidor_jak']),
        ('Upadacitinibe|inibidor de jak', ['imunossupressor', 'biologico', 'inibidor_jak']),
        ('Baricitinibe|inibidor de jak', ['imunossupressor', 'biologico', 'inibidor_jak']),
        ('Adalimumabe|anti-tnf', ['imunossupressor', 'biologico']), ('Etanercepte|anti-tnf', ['imunossupressor', 'biologico']),
        ('Infliximabe|anti-tnf', ['imunossupressor', 'biologico']), ('Golimumabe|anti-tnf', ['imunossupressor', 'biologico']),
        ('Certolizumabe pegol|anti-tnf', ['imunossupressor', 'biologico']),
        ('Tocilizumabe|anti-il-6', ['imunossupressor', 'biologico', 'tocilizumabe']),
        ('Rituximabe|anti-cd20', ['imunossupressor', 'biologico', 'rituximabe']),
        ('Abatacepte', ['imunossupressor', 'biologico']), ('Secuquinumabe|anti-il-17', ['imunossupressor', 'biologico']),
        ('Ixequizumabe|anti-il-17', ['imunossupressor', 'biologico']), ('Vedolizumabe', ['imunossupressor', 'biologico']),
        ('Ustequinumabe', ['imunossupressor', 'biologico']), ('Risanquizumabe', ['imunossupressor', 'biologico']),
        ('Guselcumabe', ['imunossupressor', 'biologico']),
        ('Natalizumabe', ['imunossupressor', 'biologico', 'natalizumabe']),
        ('Ocrelizumabe|anti-cd20', ['imunossupressor', 'biologico', 'ocrelizumabe']),
        ('Fingolimode', ['imunossupressor', 'fingolimode']),
    ]),
    ('Reumatologia e gota', ['reumato_outro'], 'reumatismo gota', [
        ('Hidroxicloroquina', ['hidroxicloroquina']), ('Sulfassalazina', ['reumato_outro', 'sulfassalazina']),
        ('Mesalazina', ['reumato_outro', 'aminossalicilato']), ('Alopurinol', ['reumato_outro', 'alopurinol']), 'Colchicina',
        'Benzbromarona',
    ]),
    ('Osteoporose', ['antiosteoporose'], 'osso osteoporose', [
        'Alendronato', 'Risedronato', 'Ibandronato', ('Ácido zoledrônico', ['antiosteoporose', 'zoledronico']),
        ('Denosumabe', ['antiosteoporose', 'denosumabe']), 'Teriparatida',
        'Cálcio + vitamina D', 'Colecalciferol (vitamina D)',
    ]),
    ('Urologia', ['urologico'], 'prostata bexiga', [
        'Tansulosina', 'Doxazosina', 'Silodosina', 'Finasterida', 'Dutasterida', 'Dutasterida + tansulosina',
        'Solifenacina', 'Mirabegrona', 'Oxibutinina',
    ]),
    ('Hormônios e oncologia hormonal', ['hormonio'], 'hormonio anticoncepcional reposicao', [
        'Anticoncepcional combinado', 'Anticoncepcional só com progestagênio', 'Terapia hormonal da menopausa',
        'Tibolona', ('Testosterona', ['hormonio', 'testosterona']), ('Tamoxifeno', ['hormonio', 'tamoxifeno']), 'Fludrocortisona',
        ('Anastrozol', ['inibidor_aromatase']), ('Letrozol', ['inibidor_aromatase']),
        ('Exemestano', ['inibidor_aromatase']),
    ]),
    # Tratamento sistêmico do câncer com acompanhamento próprio (ESC 2022, ASCO 2021, EMA 2020, AHA/ACS/AUA 2010).
    ('Oncologia (tratamento sistêmico)', ['oncologico'], 'cancer quimioterapia oncologia', [
        ('Doxorrubicina|antraciclina adriamicina', ['oncologico', 'antraciclina']),
        ('Epirrubicina|antraciclina', ['oncologico', 'antraciclina']),
        ('Trastuzumabe|anti-her2 herceptin', ['oncologico', 'anti_her2']),
        ('Pertuzumabe|anti-her2', ['oncologico', 'anti_her2']),
        ('Trastuzumabe entansina|anti-her2 t-dm1', ['oncologico', 'anti_her2']),
        ('Pembrolizumabe|imunoterapia anti-pd-1', ['oncologico', 'inibidor_checkpoint']),
        ('Nivolumabe|imunoterapia anti-pd-1', ['oncologico', 'inibidor_checkpoint']),
        ('Cemiplimabe|imunoterapia anti-pd-1', ['oncologico', 'inibidor_checkpoint']),
        ('Atezolizumabe|imunoterapia anti-pd-l1', ['oncologico', 'inibidor_checkpoint']),
        ('Durvalumabe|imunoterapia anti-pd-l1', ['oncologico', 'inibidor_checkpoint']),
        ('Ipilimumabe|imunoterapia anti-ctla-4', ['oncologico', 'inibidor_checkpoint']),
        ('Fluoruracila (5-FU)|fluoropirimidina', ['oncologico', 'fluoropirimidina']),
        ('Capecitabina|fluoropirimidina', ['oncologico', 'fluoropirimidina']),
        ('Leuprorrelina|agonista gnrh bloqueio androgenico', ['bloqueio_hormonal']),
        ('Gosserrelina|agonista gnrh bloqueio androgenico', ['bloqueio_hormonal']),
        ('Triptorrelina|agonista gnrh bloqueio androgenico', ['bloqueio_hormonal']),
        ('Degarelix|antagonista gnrh bloqueio androgenico', ['oncologico', 'bloqueio_hormonal']),
    ]),
    ('Antirretrovirais', ['tarv'], 'hiv tarv prep', [
        # tenofovir (TDF e TAF): creatinina e EAS a cada 3-6 meses na PVHA (MS 2024, Quadro 10). Tenofovir +
        # entricitabina e cabotegravir sem HIV marcado são PrEP (PCDT PrEP, Portaria SECTICS/MS nº 55/2024).
        ('Tenofovir + lamivudina + dolutegravir', ['tarv', 'tenofovir']), 'Dolutegravir',
        ('Tenofovir + entricitabina', ['tarv', 'tenofovir', 'prep']),
        ('Bictegravir + entricitabina + tenofovir alafenamida', ['tarv', 'tenofovir', 'tenofovir_alafenamida']),
        'Darunavir + ritonavir', ('Cabotegravir', ['tarv', 'prep']),
    ]),
]

# Medicamento de uso contínuo que, na prática, só se prescreve para uma doença: escolher o medicamento
# marca a comorbidade (a tela e src/utils/coerencia.py usam a mesma tabela). Ficam de fora os que têm
# outra indicação comum: metotrexato e azatioprina (oncologia, transplante), rituximabe (linfoma),
# pramipexol (pernas inquietas), amantadina, valproato, carbamazepina, lamotrigina e topiramato (humor,
# enxaqueca, dor), gabapentina e pregabalina (dor), alopurinol e colchicina (não só gota), clopidogrel e
# AAS (prevenção primária e outras), anticoagulantes, amiodarona e digoxina (várias indicações),
# doxazosina (hipertensão), finasterida (alopecia), denosumabe e ácido zoledrônico (oncologia),
# tenofovir + entricitabina e cabotegravir (PrEP), inalatórios usados em asma e em DPOC. Antirreumáticos,
# imunobiológicos, inibidores de JAK e aminossalicilatos também: cada um serve a várias doenças imunomediadas
# (artrite reumatoide, lúpus, psoríase, espondiloartrite, Crohn, retocolite), e a doença muda o acompanhamento.
IMPLICA = {
    'insuficiencia_cardiaca': ['Sacubitril + valsartana'],
    'hipotireoidismo': ['Levotiroxina'],
    'hipertireoidismo': ['Metimazol (tiamazol)', 'Propiltiouracila'],
    'parkinson': ['Levodopa + benserazida', 'Levodopa + carbidopa', 'Rasagilina'],
    'demencia': ['Donepezila', 'Rivastigmina', 'Galantamina', 'Memantina'],
    'epilepsia': ['Levetiracetam', 'Fenitoína', 'Fenobarbital', 'Lacosamida'],
    'osteoporose': ['Alendronato', 'Risedronato', 'Ibandronato', 'Teriparatida'],
    'hpb': ['Tansulosina', 'Silodosina', 'Dutasterida', 'Dutasterida + tansulosina'],
    'dpoc': ['Umeclidínio + vilanterol', 'Indacaterol + glicopirrônio', 'Tiotrópio + olodaterol'],
    'dcv_aterosclerotica': ['Ticagrelor', 'Prasugrel'],
    # quimioterapia citotóxica: só se usa no câncer
    'neoplasia_ativa': ['Doxorrubicina', 'Epirrubicina', 'Fluoruracila (5-FU)', 'Capecitabina'],
    'hiv': ['Tenofovir + lamivudina + dolutegravir', 'Dolutegravir', 'Bictegravir + entricitabina + tenofovir alafenamida',
            'Darunavir + ritonavir'],
}

# Os mais usados de forma contínua no Brasil ficam como botões na tela (PNAUM 2014; PróGenéricos/IQVIA 2025).
MAIS_USADOS = ('losartana', 'hidroclorotiazida', 'enalapril', 'anlodipino', 'atenolol', 'sinvastatina',
               'atorvastatina', 'metformina', 'glibenclamida', 'aas_acido_acetilsalicilico', 'levotiroxina', 'omeprazol')


def sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')


def chave_de(rotulo):
    return re.sub(r'[^a-z0-9]+', '_', sem_acento(rotulo)).strip('_')


def _montar():
    itens = {}
    for grupo, classes_do_grupo, busca_do_grupo, lista in GRUPOS:
        for item in lista:
            classes = classes_do_grupo
            if isinstance(item, tuple):
                item, classes = item
            rotulo, _, sinonimos = item.partition('|')
            chave = chave_de(rotulo)
            assert chave not in itens, chave
            itens[chave] = {'rotulo': rotulo, 'grupo': grupo, 'classes': list(classes),
                            'busca': sem_acento(f'{rotulo} {grupo} {busca_do_grupo} {sinonimos}')}
    return itens


MEDICAMENTOS = _montar()
assert all(k in MEDICAMENTOS for k in MAIS_USADOS)
# medicamento (chave) -> comorbidades que ele marca
MARCA = {}
for _comorbidade, _rotulos in IMPLICA.items():
    for _rotulo in _rotulos:
        assert chave_de(_rotulo) in MEDICAMENTOS, _rotulo
        MARCA.setdefault(chave_de(_rotulo), []).append(_comorbidade)


# Classe anti-hipertensiva (para contar classes na hipertensão resistente). IECA, BRA, alisquireno e
# sacubitril/valsartana bloqueiam o mesmo sistema; tiazídico e diurético de alça contam como diurético.
CLASSE_ANTI_HIPERTENSIVA = {
    'ieca_bra': 'bloqueio do SRAA', 'arni': 'bloqueio do SRAA', 'tiazidico': 'diurético', 'diuretico_alca': 'diurético',
    'bcc': 'bloqueador de canal de cálcio', 'betabloqueador': 'betabloqueador', 'betabloqueador_has': 'betabloqueador',
    'espironolactona': 'antagonista mineralocorticoide',
}
_OUTROS_ANTI_HIPERTENSIVOS = {
    'hidralazina': 'vasodilatador direto', 'minoxidil_oral': 'vasodilatador direto',
    'clonidina': 'simpatolítico central', 'metildopa': 'simpatolítico central', 'alisquireno': 'bloqueio do SRAA',
}


def classes_anti_hipertensivas(chave):
    """(classes anti-hipertensivas do medicamento, só_com_hipertensao).

    Betabloqueador, espironolactona, diurético de alça e sacubitril/valsartana também se usam em IC, FA e
    edema: só contam como anti-hipertensivo quando há hipertensão (mesma regra de coerencia.inferir).
    """
    from src.utils.condicoes import MEDICACOES
    m = MEDICAMENTOS.get(chave)
    if not m:
        return set(), False
    classes = {_OUTROS_ANTI_HIPERTENSIVOS[chave] if c == 'anti_hipertensivo_outro' else CLASSE_ANTI_HIPERTENSIVA.get(c)
               for c in m['classes']} - {None}
    sempre = any('anti_hipertensivos' in MEDICACOES.get(c, {}).get('marca', []) for c in m['classes'])
    return classes, bool(classes) and not sempre


def classes_de(medicacoes, excluir=None):
    """Troca cada princípio ativo pelas suas classes; chaves de classe (e as antigas) passam direto.

    ``excluir`` (``{medicamento: {classes}}``) tira uma classe só da contribuição daquele medicamento.
    """
    excluir = excluir or {}
    saida = []
    for chave in medicacoes:
        for c in (MEDICAMENTOS[chave]['classes'] if chave in MEDICAMENTOS else [chave]):
            if c not in saida and c not in excluir.get(chave, ()):
                saida.append(c)
    return saida
