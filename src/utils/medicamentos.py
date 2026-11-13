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
        'Atenolol', 'Metoprolol', 'Carvedilol', 'Bisoprolol', 'Nebivolol', 'Propranolol',
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
        'Digoxina', 'Ivabradina', 'Propafenona', 'Sotalol', 'Mononitrato de isossorbida', 'Dinitrato de isossorbida',
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
        'Quetiapina', 'Olanzapina', 'Risperidona', 'Aripiprazol', 'Clozapina', 'Paliperidona', 'Ziprasidona',
        'Lurasidona', 'Brexpiprazol', 'Amissulprida',
        ('Haloperidol', ['antipsicotico_tipico']), ('Clorpromazina', ['antipsicotico_tipico']),
        ('Levomepromazina', ['antipsicotico_tipico']), ('Lítio|carbolitium', ['litio']),
    ]),
    ('Anticonvulsivantes', ['anticonvulsivante'], 'epilepsia convulsao', [
        'Ácido valproico / divalproato', 'Carbamazepina', 'Oxcarbazepina', 'Lamotrigina', 'Levetiracetam', 'Fenitoína',
        'Fenobarbital', 'Topiramato', 'Lacosamida', 'Clobazam', 'Gabapentina', 'Pregabalina',
    ]),
    ('Parkinson, demência e TDAH', ['neuro_outro'], 'parkinson alzheimer demencia tdah', [
        'Levodopa + benserazida', 'Levodopa + carbidopa', 'Pramipexol', 'Rasagilina', 'Amantadina', 'Biperideno',
        'Donepezila', 'Rivastigmina', 'Galantamina', 'Memantina', 'Metilfenidato', 'Lisdexanfetamina',
    ]),
    ('Corticoides sistêmicos', ['corticoide_cronico'], 'corticoide', [
        'Prednisona', 'Prednisolona', 'Dexametasona', 'Hidrocortisona', 'Fludrocortisona',
    ]),
    ('Imunossupressores e imunobiológicos', ['imunossupressor'], 'imunossupressor imunobiologico biologico', [
        'Metotrexato', 'Azatioprina', 'Micofenolato', 'Ciclosporina', 'Tacrolimo', 'Sirolimo', 'Everolimo',
        'Leflunomida', 'Tofacitinibe', 'Upadacitinibe', 'Adalimumabe', 'Etanercepte', 'Infliximabe', 'Golimumabe',
        'Tocilizumabe', 'Rituximabe', 'Ustequinumabe', 'Risanquizumabe', 'Guselcumabe', 'Natalizumabe', 'Ocrelizumabe',
        'Fingolimode',
    ]),
    ('Reumatologia e gota', ['reumato_outro'], 'reumatismo gota', [
        ('Hidroxicloroquina', ['hidroxicloroquina']), 'Sulfassalazina', 'Mesalazina', 'Alopurinol', 'Colchicina',
        'Benzbromarona',
    ]),
    ('Osteoporose', ['antiosteoporose'], 'osso osteoporose', [
        'Alendronato', 'Risedronato', 'Ibandronato', 'Ácido zoledrônico', 'Denosumabe', 'Teriparatida',
        'Cálcio + vitamina D', 'Colecalciferol (vitamina D)',
    ]),
    ('Urologia', ['urologico'], 'prostata bexiga', [
        'Tansulosina', 'Doxazosina', 'Silodosina', 'Finasterida', 'Dutasterida', 'Dutasterida + tansulosina',
        'Solifenacina', 'Mirabegrona', 'Oxibutinina',
    ]),
    ('Hormônios e oncologia hormonal', ['hormonio'], 'hormonio anticoncepcional reposicao', [
        'Anticoncepcional combinado', 'Anticoncepcional só com progestagênio', 'Terapia hormonal da menopausa',
        'Tibolona', 'Testosterona', 'Tamoxifeno',
        ('Anastrozol', ['inibidor_aromatase']), ('Letrozol', ['inibidor_aromatase']),
        ('Exemestano', ['inibidor_aromatase']),
    ]),
    ('Antirretrovirais', ['tarv'], 'hiv tarv prep', [
        'Tenofovir + lamivudina + dolutegravir', 'Dolutegravir', 'Tenofovir + entricitabina',
        'Bictegravir + entricitabina + tenofovir alafenamida', 'Darunavir + ritonavir', 'Cabotegravir',
    ]),
]

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


def classes_de(medicacoes):
    """Troca cada princípio ativo pelas suas classes; chaves de classe (e as antigas) passam direto."""
    saida = []
    for chave in medicacoes:
        for c in (MEDICAMENTOS[chave]['classes'] if chave in MEDICAMENTOS else [chave]):
            if c not in saida:
                saida.append(c)
    return saida
