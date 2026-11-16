"""Pacientes simulados (fictícios) para validar a conduta perioperatória dos medicamentos NÃO antitrombóticos
(src/utils/preop_medicamentos.py) contra as fontes primárias.

O oráculo abaixo foi escrito a partir das fontes, sem copiar a lógica do módulo:
- AHA/ACC 2026 (= texto de 2024, Thompson et al., Circulation 2024;150:e351–e442,
  https://doi.org/10.1161/CIR.0000000000001285): §6.2 recs. 1 e 5 e nota (cautela ≥65 anos), §6.3 recs. 1–2,
  §7.1 rec. 1 (estatina, 1 B-NR), §7.2 recs. 1–2 (SRAA: omitir 24 h, 2b B-R; ICFEr, 2a C-EO), §7.3 (BCC: só texto),
  §7.4 (clonidina: iniciar = 3: Sem benefício; rebote no texto), §7.7 rec. 1 (betabloqueador, 1 B-NR),
  §7.8 recs. 1–3 (HbA1c 2a; iSGLT2 3 dias, ertugliflozina 4, classe 1 C-LD; metformina 2a C-LD; aGLP-1 só texto).
- SBC 2024 (Gualandro et al., https://doi.org/10.36660/abc.20240590): Quadros 8 (IC), 9, 10 (anti-hipertensivos,
  clonidina I-B), 18 (betabloqueador I-B) e 19 (estatina I-B).
- Orientação multissocietária de aGLP-1 (Kindel et al. 2024, https://doi.org/10.1016/j.cgh.2024.10.003).
- SPAQI endócrino/hormonal/urológico 2021 (https://doi.org/10.1016/j.mayocp.2020.10.002), psiquiátrico 2022
  (https://doi.org/10.1016/j.mayocp.2021.11.011) e neurológico 2022 (https://doi.org/10.1016/j.mayocp.2021.11.010).
- ACR/AAHKS 2022 (https://doi.org/10.1002/art.42140): antirreumáticos na artroplastia.
- ESE/Endocrine Society 2024 (https://doi.org/10.1210/clinem/dgae250): R 3.1, 3.1B e definições (cobertura de
  estresse, parenteral em anestesia geral/regional; dose fisiológica = hidrocortisona 15–25 mg, prednisona 4–6 mg).
- Antidiabéticos e insulinas: posicionamento SBD/SBA/ABESO 2026 (Diabetol Metab Syndr 2026;18:91,
  https://doi.org/10.1186/s13098-025-02060-5), R4–R15 e Tabela 2; aGLP-1 pela nota da SBA de 15/05/2026
  (C.SBA-01744/2026): suspender 7 dias (longa ação) ou 1 dia (curta ação), salvo POCUS sistemático e baixo risco;
  dieta líquida 24 h e jejum de 8 a 12 h para todos. Metformina com TFG < 30: KDIGO 2022
  (https://doi.org/10.1016/j.kint.2022.06.008).
- Fontes que o módulo não usa, citadas só nas divergências marcadas como xfail: rótulo/FDA da metformina e KDIGO
  2022 (contraindicada com TFG <30), SPAQI iSGLT2 2026 (https://doi.org/10.1016/j.bja.2026.02.031) e CDC US MEC 2024
  (https://www.cdc.gov/mmwr/volumes/73/rr/rr7304a1.htm).

Antitrombóticos (AAS, P2Y12, anticoagulantes) ficam fora deste arquivo: aparecem em alguns pacientes só para
garantir que não alteram os itens dos demais medicamentos. Discordância módulo × fonte = xfail(strict=True).
Relatório: /tmp/validacao/casos-medicamentos.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

from src.utils import preop_medicamentos as pm
from src.utils.medicamentos import MEDICAMENTOS

# ---------------------------------------------------------------------------------------------------------------
# Fontes (URL esperada nas referências do item)
# ---------------------------------------------------------------------------------------------------------------
AHA = 'https://doi.org/10.1161/CIR.0000000000001285'
SBC = 'https://doi.org/10.36660/abc.20240590'
GLP1 = 'https://doi.org/10.1016/j.cgh.2024.10.003'
SPAQI_ENDO = 'https://doi.org/10.1016/j.mayocp.2020.10.002'
SPAQI_PSIQ = 'https://doi.org/10.1016/j.mayocp.2021.11.011'
SPAQI_NEURO = 'https://doi.org/10.1016/j.mayocp.2021.11.010'
ACR = 'https://doi.org/10.1002/art.42140'
ESE = 'https://doi.org/10.1210/clinem/dgae250'
SBD = 'https://doi.org/10.1186/s13098-025-02060-5'
SBA_GLP1 = ('https://www.sbahq.org/nota-da-sba-de-atualizacao-sobre-as-recomendacoes-do-manejo-perioperatorio-'
            'dos-agonistas-do-receptor-glp-1-e-coagonistas-glp-1-gip/')
KDIGO = 'https://doi.org/10.1016/j.kint.2022.06.008'

# ---------------------------------------------------------------------------------------------------------------
# Grupos farmacológicos, definidos pelas fontes (não importados do módulo)
# ---------------------------------------------------------------------------------------------------------------
ANTITROMBOTICOS = {'aas_acido_acetilsalicilico', 'clopidogrel', 'ticagrelor', 'prasugrel', 'ticlopidina',
                   'cilostazol', 'varfarina', 'rivaroxabana', 'apixabana', 'edoxabana', 'dabigatrana', 'enoxaparina'}

BETABLOQ = {'atenolol', 'metoprolol', 'nebivolol', 'carvedilol', 'bisoprolol', 'propranolol', 'atenolol_clortalidona'}
ESTATINAS = {'sinvastatina', 'atorvastatina', 'rosuvastatina', 'pravastatina', 'pitavastatina', 'fluvastatina',
             'lovastatina', 'ezetimiba_sinvastatina', 'rosuvastatina_ezetimiba'}
IECA_BRA = {'captopril', 'enalapril', 'ramipril', 'lisinopril', 'perindopril', 'benazepril', 'losartana',
            'valsartana', 'olmesartana', 'candesartana', 'telmisartana', 'irbesartana'}
SRAA_COM_DIURETICO = {'losartana_hidroclorotiazida', 'valsartana_hidroclorotiazida', 'olmesartana_hidroclorotiazida',
                      'candesartana_hidroclorotiazida', 'telmisartana_hidroclorotiazida',
                      'irbesartana_hidroclorotiazida', 'enalapril_hidroclorotiazida', 'perindopril_indapamida',
                      'perindopril_indapamida_anlodipino'}
SRAA_COM_BCC = {'valsartana_anlodipino', 'olmesartana_anlodipino', 'losartana_anlodipino', 'perindopril_anlodipino',
                'perindopril_indapamida_anlodipino'}
SRAA = IECA_BRA | SRAA_COM_DIURETICO | SRAA_COM_BCC
ARNI = {'sacubitril_valsartana'}
INIBIDOR_RENINA = {'alisquireno'}       # inibidor direto da renina: bloqueio do SRAA
BCC_DHP = {'anlodipino', 'levanlodipino', 'nifedipino', 'felodipino', 'lercanidipino', 'lacidipino', 'manidipino',
           'nitrendipino'}
BCC_NAO_DHP = {'diltiazem', 'verapamil'}
TIAZIDICOS = {'hidroclorotiazida', 'clortalidona', 'indapamida'}
ALCA = {'furosemida', 'bumetanida'}
ARM = {'espironolactona', 'eplerenona'}
POUPADOR_K = {'amilorida'}
VASODIL_SIMPATOL = {'hidralazina', 'metildopa', 'minoxidil_oral'}
CLONIDINA = {'clonidina'}
OUTROS_CARDIO = {'amiodarona', 'digoxina', 'ivabradina', 'propafenona', 'sotalol', 'mononitrato_de_isossorbida',
                 'dinitrato_de_isossorbida', 'trimetazidina', 'ranolazina'}

# iSGLT2: AHA §7.8, nota da rec. 2: canagliflozina, dapagliflozina e empagliflozina ≥3 dias; ertugliflozina ≥4.
ISGLT2_DIAS = {'dapagliflozina': 3, 'empagliflozina': 3, 'canagliflozina': 3, 'dapagliflozina_metformina': 3,
               'empagliflozina_linagliptina': 3}
SECRETAGOGOS = {'glibenclamida', 'gliclazida', 'glimepirida'}
IDPP4 = {'sitagliptina', 'vildagliptina', 'linagliptina', 'saxagliptina', 'alogliptina'}
TZD_ACARBOSE = {'pioglitazona', 'acarbose'}
IDPP4_METFORMINA = {'sitagliptina_metformina', 'vildagliptina_metformina', 'linagliptina_metformina'}
GLP1_SEMANAL = {'semaglutida', 'dulaglutida', 'tirzepatida'}
GLP1_DIARIO = {'liraglutida'}
INSULINA_BASAL = {'insulina_glargina', 'insulina_degludeca', 'insulina_detemir'}
INSULINA_NPH = {'insulina_nph'}
INSULINA_PRANDIAL = {'insulina_regular', 'insulina_asparte', 'insulina_lispro', 'insulina_glulisina'}
INSULINA_GLP1 = {'insulina_glargina_lixisenatida', 'insulina_degludeca_liraglutida'}

CORTICOIDES = {'prednisona', 'prednisolona', 'metilprednisolona', 'deflazacorte', 'dexametasona', 'hidrocortisona'}
DMARD_SINTETICOS = {'metotrexato', 'leflunomida', 'hidroxicloroquina', 'sulfassalazina'}
BIOLOGICOS_ACR = {'adalimumabe', 'etanercepte', 'infliximabe', 'golimumabe', 'certolizumabe_pegol', 'tocilizumabe',
                  'rituximabe', 'abatacepte', 'secuquinumabe', 'ixequizumabe', 'ustequinumabe', 'risanquizumabe',
                  'guselcumabe'}
JAK = {'tofacitinibe', 'upadacitinibe', 'baricitinibe'}
LES = {'micofenolato', 'azatioprina', 'ciclosporina', 'tacrolimo'}

ANTIDEPRESSIVOS = {'sertralina', 'fluoxetina', 'escitalopram', 'citalopram', 'paroxetina', 'fluvoxamina', 'venlafaxina',
                   'desvenlafaxina', 'duloxetina', 'vortioxetina', 'vilazodona', 'bupropiona', 'mirtazapina',
                   'trazodona', 'agomelatina', 'amitriptilina', 'nortriptilina', 'clomipramina', 'imipramina'}
ANTIPSICOTICOS = {'quetiapina', 'olanzapina', 'risperidona', 'aripiprazol', 'clozapina', 'paliperidona',
                  'ziprasidona', 'lurasidona', 'brexpiprazol', 'amissulprida', 'haloperidol', 'clorpromazina',
                  'levomepromazina'}
BENZODIAZEPINICOS = {'clonazepam', 'alprazolam', 'bromazepam', 'diazepam', 'lorazepam'}
ANFETAMINAS = {'lisdexanfetamina'}

ESTROGENIOS = {'anticoncepcional_combinado', 'terapia_hormonal_da_menopausa'}
TIREOIDE = {'levotiroxina', 'metimazol_tiamazol', 'propiltiouracila'}

# Lacunas: há recomendação nas fontes (SPAQI), mas o módulo não gera item. Casos com elas são xfail.
ALFA1 = {'tansulosina', 'doxazosina', 'silodosina', 'dutasterida_tansulosina'}
INIBIDOR_5ALFA = {'finasterida', 'dutasterida'}
ANTIMUSCARINICOS_BEXIGA = {'solifenacina', 'oxibutinina'}
BISFOSFONATOS_ORAIS = {'alendronato', 'risedronato', 'ibandronato'}
DENOSUMABE_PTH = {'denosumabe', 'teriparatida'}
NEUROLOGICOS = {'acido_valproico_divalproato', 'carbamazepina', 'oxcarbazepina', 'lamotrigina', 'levetiracetam',
                'fenitoina', 'fenobarbital', 'topiramato', 'lacosamida', 'clobazam', 'gabapentina', 'pregabalina',
                'levodopa_benserazida', 'levodopa_carbidopa', 'pramipexol', 'rasagilina', 'amantadina', 'biperideno',
                'donepezila', 'rivastigmina', 'galantamina', 'memantina'}
LACUNAS = ALFA1 | INIBIDOR_5ALFA | ANTIMUSCARINICOS_BEXIGA | BISFOSFONATOS_ORAIS | DENOSUMABE_PTH | NEUROLOGICOS

# Sem recomendação perioperatória em nenhuma das fontes revisadas: não pode gerar item.
SEM_FONTE = {
    'ezetimiba', 'fenofibrato', 'ciprofibrato', 'bezafibrato', 'genfibrozila', 'acido_bempedoico', 'evolocumabe',
    'alirocumabe', 'inclisirana', 'colestiramina', 'omega_3_esteres_etilicos',
    'omeprazol', 'pantoprazol', 'esomeprazol', 'lansoprazol', 'dexlansoprazol', 'rabeprazol', 'vonoprazana',
    'zolpidem', 'eszopiclona', 'zopiclona', 'metilfenidato',
    'insulina_icodeca', 'insulina_bifasica', 'tibolona', 'fludrocortisona', 'anastrozol', 'letrozol', 'exemestano',
    'sirolimo', 'everolimo', 'vedolizumabe', 'natalizumabe', 'ocrelizumabe', 'fingolimode',
    'mesalazina', 'alopurinol', 'colchicina', 'benzbromarona', 'calcio_vitamina_d', 'colecalciferol_vitamina_d',
    'mirabegrona', 'salbutamol', 'fenoterol', 'terbutalina', 'ipratropio', 'formoterol', 'tiotropio', 'umeclidinio',
    'budesonida_inalatoria', 'beclometasona_inalatoria', 'fluticasona_inalatoria', 'mometasona_inalatoria',
    'formoterol_budesonida', 'formoterol_beclometasona', 'salmeterol_fluticasona', 'vilanterol_fluticasona',
    'umeclidinio_vilanterol', 'indacaterol_glicopirronio', 'tiotropio_olodaterol',
    'fluticasona_umeclidinio_vilanterol', 'beclometasona_formoterol_glicopirronio', 'montelucaste', 'teofilina',
    'omalizumabe', 'mepolizumabe', 'tenofovir_lamivudina_dolutegravir', 'dolutegravir', 'tenofovir_entricitabina',
    'bictegravir_entricitabina_tenofovir_alafenamida', 'darunavir_ritonavir', 'cabotegravir', 'doxorrubicina',
    'epirrubicina', 'trastuzumabe', 'pertuzumabe', 'trastuzumabe_entansina', 'pembrolizumabe', 'nivolumabe',
    'cemiplimabe', 'atezolizumabe', 'durvalumabe', 'ipilimumabe', 'fluoruracila_5_fu', 'capecitabina',
    'leuprorrelina', 'gosserrelina', 'triptorrelina', 'degarelix',
}


# ---------------------------------------------------------------------------------------------------------------
# Oráculo
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Esperado:
    conduta: str
    fontes: tuple = ()                 # URLs que precisam estar nas referências
    resumo: tuple = ()                 # regex que o resumo precisa conter
    texto: tuple = ()                  # regex que o texto precisa conter
    texto_ou_div: tuple = ()           # regex que texto + divergência precisam conter
    divergencia: tuple = ()            # regex na divergência (fontes discordam: texto justificado obrigatório)
    classe: tuple = ()                 # regex na classe
    classe_proibida: tuple = ()        # regex que NÃO pode estar na classe
    dias_antes: int | None = None      # extraído do resumo ("Suspender N dias antes")
    ultima_dose: int | None = None     # extraído do texto ("D-N")
    horas: int | None = None           # extraído do resumo/texto ("N h")
    faixa_pct: tuple | None = None     # extraída do texto ("A–B%")
    cautela_65: bool | None = None     # nota da AHA ao §6.2: True = obrigatória, False = proibida, None = indiferente
    fonte_desc: str = ''


def _idade(ctx):
    return ctx.get('idade')


def _ge65(ctx):
    return _idade(ctx) is not None and _idade(ctx) >= 65


def _cond(ctx):
    return set(ctx.get('condicoes') or ())


def _ic(ctx):
    return bool(_cond(ctx) & {'ic', 'ic_fe_reduzida'})


def oraculo(chave, ctx):
    """Conduta esperada pelas fontes; None = nenhuma fonte revisada tem recomendação (não pode haver item)."""
    cond = _cond(ctx)
    urg = ctx.get('urgencia')

    # --- Cardiovasculares -----------------------------------------------------------------------------------
    if chave in BETABLOQ:
        texto = (r'diurético',) if chave == 'atenolol_clortalidona' else ()
        return Esperado('manter', (AHA, SBC), resumo=(r'inclusive no dia',), texto=texto,
                        classe=(r'AHA 1 \(B-NR\)', r'SBC I-B'), fonte_desc='AHA §7.7 rec. 1; SBC Quadro 18')
    if chave in ESTATINAS:
        texto = (r'ezetimiba',) if 'ezetimiba' in chave else ()
        return Esperado('manter', (AHA, SBC), texto=texto, classe=(r'AHA 1 \(B-NR\)', r'SBC I-B'),
                        fonte_desc='AHA §7.1 rec. 1; SBC Quadro 19')
    if chave in SRAA or chave in INIBIDOR_RENINA:
        return _oraculo_sraa(chave, ctx)
    if chave in ARNI:
        return Esperado('manter', (SBC,), classe=(r'SBC I-C',), texto=(r'ICFEr',),
                        fonte_desc='SBC Quadro 8; AHA §7.2 rec. 2 (por extensão: o ARNI contém um BRA)')
    if chave in BCC_DHP | BCC_NAO_DHP:
        texto = (r'bradicardia',) if chave in BCC_NAO_DHP else (r'hipotensão',)
        return Esperado('manter', (SBC, AHA), texto=texto, classe=(r'SBC I-C',), classe_proibida=(r'AHA \d',),
                        cautela_65=_ge65(ctx), fonte_desc='SBC Quadro 10 (I-C); AHA §7.3, só texto')
    if chave in TIAZIDICOS | ALCA | ARM | POUPADOR_K:
        if _ic(ctx):
            classe = (r'AHA 2a \(C-LD\)', r'SBC I-C') if chave in ARM else (r'SBC I-C',)
            return Esperado('manter', (SBC,), classe=classe, fonte_desc='SBC Quadro 8; AHA §6.3 rec. 2 (ARM)')
        return Esperado('manter', (SBC, AHA), texto=(r'volemia',), classe=(r'SBC I-C',), cautela_65=_ge65(ctx),
                        fonte_desc='SBC Quadros 9–10; AHA §6.2 rec. 1 e nota')
    if chave in CLONIDINA:
        return Esperado('manter', (SBC, AHA), texto=(r'rebote', r'3: Sem benefício'), classe=(r'SBC I-B',),
                        fonte_desc='SBC Quadro 10 (I-B); AHA §7.4 (iniciar: 3: Sem benefício; texto: rebote)')
    if chave in VASODIL_SIMPATOL:
        return Esperado('manter', (AHA,), classe=(r'AHA 2a \(C-EO\)',), cautela_65=_ge65(ctx),
                        fonte_desc='AHA §6.2 recs. 1 e 5 e nota')
    if chave in OUTROS_CARDIO:
        if _ic(ctx):
            return Esperado('manter', (SBC,), classe=(r'SBC I-C',), fonte_desc='SBC Quadro 8 (IC: manter todas)')
        return None

    # --- Diabetes (SBD/SBA/ABESO 2026, Tabela 2; nota da SBA 2026 para aGLP-1; AHA §7.8) ----------------------
    if chave in ISGLT2_DIAS:
        d = ISGLT2_DIAS[chave]
        if urg in ('urgencia', 'emergencia'):
            # SBD/SBA/ABESO notas 3 e 4: iSGLT2 e cirurgia de emergência → cetonemia capilar; AHA §6.3: "when feasible".
            return Esperado('suspender', (SBD, AHA), texto=(r'cetonemia', r'ânion gap|gasometria'),
                            fonte_desc='SBD/SBA/ABESO notas 3–4 (emergência)')
        texto = [r'cetoacidose', r'dieta']
        if chave == 'dapagliflozina_metformina':
            texto.append(r'metformina')
        if chave == 'empagliflozina_linagliptina':
            texto.append(r'iDPP-4')
        return Esperado('suspender', (AHA, SBD), texto=tuple(texto), classe=(r'AHA 1 \(C-LD\)', r'I-B'),
                        divergencia=(r'SBD', r'caso a caso'), dias_antes=d, ultima_dose=d + 1,
                        fonte_desc='AHA §7.8 rec. 2 (1, C-LD); SBD R6 (I-B: 3–4 dias em cirurgia maior/restrição)')
    if chave == 'metformina':
        tfg = ctx.get('tfg')   # KDIGO 2022: o limite é de TFG estimada, não de ClCr por Cockcroft-Gault
        if tfg is not None and tfg < 30:
            return Esperado('suspender', (KDIGO,), resumo=(r'TFG < 30',), fonte_desc='KDIGO 2022 (TFG < 30)')
        return Esperado('suspender', (SBD, AHA), resumo=(r'não tomar no dia',), classe=(r'IIa-B',),
                        divergencia=(r'AHA', r'2a'), fonte_desc='SBD R5 (IIa-B) e Tabela 2 × AHA §7.8 rec. 3 (2a)')
    if chave in SECRETAGOGOS:
        return Esperado('suspender', (SBD,), resumo=(r'24 h',), texto=(r'hipoglicemia',), classe=(r'I-C',),
                        divergencia=(r'SPAQI',), fonte_desc='SBD R4 (I-C: 24 h antes) × SPAQI (manhã)')
    if chave in IDPP4_METFORMINA:
        return Esperado('suspender', (SBD,), resumo=(r'não tomar no dia',), texto=(r'metformina',),
                        divergencia=(r'AHA',), fonte_desc='SBD R5/R11: metformina não se toma no dia')
    if chave in IDPP4:
        if chave == 'saxagliptina':
            return Esperado('individualizar' if _ic(ctx) else 'manter', (SBD,), texto=(r'IC',), classe=(r'I-A',),
                            fonte_desc='SBD R11 (I-A); evitar saxagliptina com IC')
        return Esperado('manter', (SBD,), classe=(r'I-A',), divergencia=(r'SPAQI',),
                        fonte_desc='SBD R11 (I-A: manter) × SPAQI (manhã)')
    if chave == 'pioglitazona':
        return Esperado('individualizar' if _ic(ctx) else 'manter', (SBD,), classe=(r'IIb-C',),
                        fonte_desc='SBD R12 (IIb-C; cautela na IC)')
    if chave == 'acarbose':
        return Esperado('suspender', (SBD,), resumo=(r'no dia',), fonte_desc='SBD Tabela 2 (suspender no dia)')
    if chave in GLP1_SEMANAL | GLP1_DIARIO:
        dias = 7 if chave in GLP1_SEMANAL else 1
        texto = [r'dieta líquida', r'24 h', r'8 a 12 h', r'POCUS', r'12 semanas']
        if chave == 'tirzepatida':
            texto.append(r'GIP')
        return Esperado('suspender', (SBA_GLP1, SBD), texto=tuple(texto), dias_antes=dias,
                        divergencia=(r'AHA', r'multissocietária'),
                        fonte_desc='SBA 2026 (C.SBA-01744/2026) e SBD R7–R10 × multissocietária 2024')
    if chave == 'insulina_degludeca':
        return Esperado('ajustar', (SBD,), resumo=(r'72 h',), faixa_pct=(20, 30), classe=(r'IIa-B',),
                        fonte_desc='SBD R13 e Tabela 2 (degludeca: −20–30% a partir de 72 h)')
    if chave in INSULINA_BASAL:
        return Esperado('ajustar', (SBD,), texto=(r'noite anterior',), faixa_pct=(70, 80), classe=(r'IIa-B',),
                        divergencia=(r'SPAQI',), fonte_desc='SBD R13 (IIa-B: −20–30% na noite anterior)')
    if chave in INSULINA_NPH:
        return Esperado('ajustar', (SBD,), resumo=(r'50%',), texto=(r'manhã',), classe=(r'IIa-C',),
                        divergencia=(r'SPAQI', r'25%'), fonte_desc='SBD R14 (IIa-C: 50% na manhã) × SPAQI')
    if chave in INSULINA_PRANDIAL:
        return Esperado('suspender', (SBD,), resumo=(r'correção',), classe=(r'I-C',),
                        fonte_desc='SBD R15 (I-C: sem doses fixas em jejum)')
    if chave in INSULINA_GLP1:
        return Esperado('individualizar', (SBA_GLP1, SBD), texto=(r'aGLP-1', r'1 dia', r'POCUS'),
                        fonte_desc='SBD nota 8 (associação segue o aGLP-1) e SBA 2026')

    # --- Corticoide, antirreumáticos ------------------------------------------------------------------------
    if chave in CORTICOIDES:
        return Esperado('manter', (ESE, SPAQI_ENDO), resumo=(r'inclusive no dia',),
                        texto=(r'estresse', r'parenteral', r'15–25 mg', r'4–6 mg', r'3–4 semanas', r'geral ou regional'),
                        divergencia=(r'ACR',), classe=(r'ESE',),
                        fonte_desc='ESE/ES 2024 R 3.1 e 3.1B (boa prática); SPAQI 2021; ACR/AAHKS 2022')
    if chave in DMARD_SINTETICOS:
        return Esperado('manter', (ACR,), texto=(r'artroplastia',), classe=(r'ACR/AAHKS 2022',),
                        fonte_desc='ACR/AAHKS 2022 (continuar)')
    if chave in BIOLOGICOS_ACR:
        return Esperado('suspender', (ACR,), resumo=(r'ciclo',), texto=(r'14 dias', r'artroplastia'),
                        classe=(r'ACR/AAHKS 2022',), fonte_desc='ACR/AAHKS 2022 (omitir um ciclo; reinício ~14 dias)')
    if chave in JAK:
        return Esperado('suspender', (ACR,), texto=(r'4º dia', r'TEV', r'14 dias'), dias_antes=3,
                        classe=(r'ACR/AAHKS 2022',), fonte_desc='ACR/AAHKS 2022 (3 dias; operar no dia 4)')
    if chave in LES:
        return Esperado('individualizar', (ACR,), resumo=(r'1 semana',), texto=(r'LES grave', r'LES não grave'),
                        classe=(r'ACR/AAHKS 2022',), fonte_desc='ACR/AAHKS 2022 (LES grave × não grave)')

    # --- Psiquiatria ----------------------------------------------------------------------------------------
    if chave in ANTIDEPRESSIVOS | ANTIPSICOTICOS | BENZODIAZEPINICOS:
        return Esperado('manter', (SPAQI_PSIQ,), resumo=(r'inclusive no dia',), classe=(r'SPAQI',),
                        fonte_desc='SPAQI 2022 (tomar inclusive no dia)')
    if chave == 'litio':
        return Esperado('individualizar', (SPAQI_PSIQ,), texto=(r'menor', r'maior'), horas=72, classe=(r'SPAQI',),
                        fonte_desc='SPAQI 2022 (menor: manter; maior: suspender 72 h antes)')
    if chave in ANFETAMINAS:
        return Esperado('suspender', (SPAQI_PSIQ,), resumo=(r'no dia',), classe=(r'SPAQI',),
                        fonte_desc='SPAQI 2022 (não tomar no dia)')

    # --- Hormônios ------------------------------------------------------------------------------------------
    if chave in ESTROGENIOS:
        texto = (r'TEV', r'gestação') if chave == 'anticoncepcional_combinado' else (r'TEV',)
        e = Esperado('manter', (SPAQI_ENDO,), texto=texto, classe=(r'SPAQI',), fonte_desc='SPAQI 2021 (manter, pesar TEV)')
        if chave == 'anticoncepcional_combinado' and (ctx.get('cirurgia_risco_elevado') or ctx.get('sangramento') == 'alto'):
            # CDC US MEC 2024: cirurgia maior com imobilização prolongada = categoria 4 para contraceptivo combinado.
            e.divergencia = (r'MEC|categoria 4|imobiliza',)
            e.fonte_desc += ' × CDC US MEC 2024 (categoria 4)'
        return e
    if chave == 'anticoncepcional_so_com_progestagenio':
        return Esperado('manter', (SPAQI_ENDO,), classe=(r'SPAQI',), fonte_desc='SPAQI 2021 (progestagênio: manter)')
    if chave == 'testosterona':
        return Esperado('manter', (SPAQI_ENDO,), texto=(r'TEV',), classe=(r'SPAQI',), fonte_desc='SPAQI 2021')
    if chave == 'tamoxifeno':
        return Esperado('manter', (SPAQI_ENDO,), texto=(r'câncer de mama', r'≥7 dias'), classe=(r'SPAQI',),
                        fonte_desc='SPAQI 2021 (SERM)')
    if chave in TIREOIDE:
        return Esperado('manter', (SPAQI_ENDO,), texto=(r'sem ajuste',), classe=(r'SPAQI',), fonte_desc='SPAQI 2021')

    # --- Lacunas (fonte existe; o módulo não cobre) --------------------------------------------------------
    if chave in ALFA1 | INIBIDOR_5ALFA | DENOSUMABE_PTH:
        return Esperado('manter', (SPAQI_ENDO,), fonte_desc='SPAQI 2021 (manter inclusive no dia)')
    if chave in ANTIMUSCARINICOS_BEXIGA | BISFOSFONATOS_ORAIS:
        return Esperado('suspender', (SPAQI_ENDO,), resumo=(r'dia',), fonte_desc='SPAQI 2021 (não tomar no dia)')
    if chave in NEUROLOGICOS:
        fontes = (SPAQI_PSIQ,) if chave in {'acido_valproico_divalproato', 'carbamazepina', 'lamotrigina'} else (SPAQI_NEURO,)
        return Esperado('manter', fontes, fonte_desc='SPAQI neurológico/psiquiátrico 2022 (manter)')
    return None


def _oraculo_sraa(chave, ctx):
    """AHA §7.2 (rec. 1: HAS, PA controlada e cirurgia de risco elevado → omitir 24 h, 2b B-R; rec. 2: ICFEr → manter,
    2a C-EO), §6.3 rec. 2 (IC compensada → manter GDMT, 2a C-LD), §6.2 rec. 1 (demais → manter, 2a C-EO) e nota de
    cautela ≥65 anos; SBC Quadros 8 e 10 (I-C)."""
    cond = _cond(ctx)
    elevado, pa = ctx.get('cirurgia_risco_elevado'), ctx.get('pa_controlada')
    perfil_omissao = elevado is True and pa is True
    renina = chave in INIBIDOR_RENINA
    texto = []
    if chave in SRAA_COM_DIURETICO:
        texto.append(r'diurético')
    if chave in SRAA_COM_BCC:
        texto.append(r'canal de cálcio')
    if 'ic_fe_reduzida' in cond:
        return Esperado('manter', (AHA, SBC), texto=tuple(texto), classe=() if renina else (r'AHA 2a \(C-EO\)', r'SBC I-C'),
                        fonte_desc='AHA §7.2 rec. 2; SBC Quadro 8')
    if 'ic' in cond:
        e = Esperado('manter', (AHA, SBC), texto=tuple(texto), classe=() if renina else (r'AHA 2a \(C-LD\)', r'SBC I-C'),
                     fonte_desc='AHA §6.3 rec. 2; SBC Quadro 8')
        if perfil_omissao and 'hipertensao' in cond:
            # IC sem FE reduzida + HAS no perfil da rec. 1 do §7.2: as duas recomendações da AHA se aplicam e
            # apontam em sentidos opostos (omitir 2b × manter 2a); o item precisa registrar a divergência.
            e.divergencia = (r'24 h',)
            e.fonte_desc += ' × AHA §7.2 rec. 1 (omitir 24 h)'
        return e
    if perfil_omissao:
        if renina:
            return Esperado('suspender', (AHA,), texto_ou_div=(r'24 h',), horas=24,
                            fonte_desc='AHA §7.2 rec. 1 (RAASi; alisquireno é inibidor do SRAA)')
        return Esperado('suspender', (AHA, SBC), resumo=(r'24 h',), texto=tuple(texto) + (r'[Rr]etomar',), horas=24,
                        classe=(r'AHA 2b \(B-R\)', r'SBC I-C'), divergencia=(r'SBC', r'AHA'),
                        fonte_desc='AHA §7.2 rec. 1 (2b, B-R) × SBC Quadro 10 (I-C)')
    if elevado is False or pa is False:
        return Esperado('manter', (AHA,) if renina else (AHA, SBC), texto=tuple(texto),
                        classe=() if renina else (r'AHA 2a \(C-EO\)', r'SBC I-C'),
                        divergencia=() if renina else (r'SBC', r'AHA'), cautela_65=_ge65(ctx),
                        fonte_desc='AHA §6.2 rec. 1 e nota (≥65); SBC Quadro 10')
    return Esperado('individualizar', (AHA,), texto=(r'24 h',), cautela_65=_ge65(ctx),
                    fonte_desc='AHA §7.2 rec. 1 depende de PA e risco cirúrgico; nota do §6.2 (≥65)')


# ---------------------------------------------------------------------------------------------------------------
# Extração de números por regex
# ---------------------------------------------------------------------------------------------------------------
def dias_antes(resumo):
    m = re.search(r'[Ss]uspender (\d+) dias? antes', resumo)
    return int(m.group(1)) if m else None


def ultima_dose(texto):
    m = re.search(r'D-(\d+)', texto)
    return int(m.group(1)) if m else None


def horas(texto):
    m = re.search(r'(\d+) h\b', texto)
    return int(m.group(1)) if m else None


def faixa_pct(texto):
    m = re.search(r'(\d+)[–-](\d+)\s*%', texto)
    return (int(m.group(1)), int(m.group(2))) if m else None


def conferir_item(chave, item, ctx):
    esp = oraculo(chave, ctx)
    rot = f'{chave} ({esp.fonte_desc if esp else "sem fonte"})'
    if esp is None:
        assert item is None, f'{rot}: nenhuma fonte revisada tem recomendação, mas o módulo gerou {item["resumo"]!r}'
        return
    assert item is not None, f'{rot}: a fonte tem recomendação ({esp.conduta}), mas o módulo não gerou item'
    assert item['conduta'] == esp.conduta, f'{rot}: conduta {item["conduta"]!r}, esperado {esp.conduta!r}'
    assert item['medicamento'] == MEDICAMENTOS[chave]['rotulo']
    assert item['resumo'] and item['texto'] and item['classe'], rot
    refs = item['referencias']
    assert refs and all(r['url'].startswith('https://') and r['label'] for r in refs), f'{rot}: referência sem https'
    urls = {r['url'] for r in refs}
    for f in esp.fontes:
        assert f in urls, f'{rot}: falta a referência {f}'
    for p in esp.resumo:
        assert re.search(p, item['resumo']), f'{rot}: resumo {item["resumo"]!r} sem /{p}/'
    for p in esp.texto:
        assert re.search(p, item['texto']), f'{rot}: texto sem /{p}/: {item["texto"]!r}'
    for p in esp.texto_ou_div:
        assert re.search(p, item['texto'] + ' ' + item['divergencia']), \
            f'{rot}: texto/divergência sem /{p}/: {item["texto"]!r} | {item["divergencia"]!r}'
    for p in esp.divergencia:
        assert re.search(p, item['divergencia']), f'{rot}: divergência sem /{p}/: {item["divergencia"]!r}'
    for p in esp.classe:
        assert re.search(p, item['classe']), f'{rot}: classe {item["classe"]!r} sem /{p}/'
    for p in esp.classe_proibida:
        assert not re.search(p, item['classe']), f'{rot}: classe {item["classe"]!r} não deveria ter /{p}/'
    if esp.dias_antes is not None:
        assert dias_antes(item['resumo']) == esp.dias_antes, f'{rot}: dias antes {item["resumo"]!r}'
    if esp.ultima_dose is not None:
        assert ultima_dose(item['texto']) == esp.ultima_dose, f'{rot}: última dose {item["texto"]!r}'
    if esp.horas is not None:
        assert horas(item['resumo'] + ' ' + item['texto']) == esp.horas, f'{rot}: horas {item["resumo"]!r}'
    if esp.faixa_pct is not None:
        assert faixa_pct(item['resumo'] + ' ' + item['texto']) == esp.faixa_pct, f'{rot}: % {item["texto"]!r}'
    if esp.cautela_65 is True:
        assert '≥65' in item['texto'], f'{rot}: paciente com {ctx.get("idade")} anos sem a cautela da nota do §6.2'
    if esp.cautela_65 is False:
        assert '≥65' not in item['texto'], f'{rot}: cautela ≥65 em paciente de {ctx.get("idade")} anos'


# ---------------------------------------------------------------------------------------------------------------
# Pacientes fictícios
# ---------------------------------------------------------------------------------------------------------------
def ctx(idade=60, sexo='masculino', peso=75.0, clcr=80.0, sangramento='baixo_moderado', risco=False,
        urgencia='eletiva', pa=None, cond=(), neuroaxial=False):
    return {'idade': idade, 'sexo': sexo, 'peso': peso, 'clcr': clcr, 'sangramento': sangramento,
            'cirurgia_risco_elevado': risco, 'urgencia': urgencia, 'neuroaxial': neuroaxial,
            'condicoes': set(cond), 'pa_controlada': pa}


@dataclass
class Caso:
    id: str
    meds: list
    ctx: dict = field(default_factory=dict)
    xfail: str = ''


HAS = ('hipertensao',)
DM = ('diabetes',)
DMI = ('diabetes', 'diabetes_insulina')
ICFER = ('ic', 'ic_fe_reduzida')

URL_FDA_METF = ('https://www.fda.gov/drugs/drug-safety-and-availability/fda-drug-safety-communication-fda-revises-'
                'warnings-regarding-use-diabetes-medicine-metformin-certain')

CASOS = [
    # --- Hipertensão: IECA/BRA e associações (AHA §7.2 × SBC Q10) -------------------------------------------
    Caso('P001 losartana HAS PA-controlada risco-elevado 58a', ['losartana'], ctx(58, pa=True, risco=True, cond=HAS)),
    Caso('P002 enalapril HAS PA-controlada baixo-risco 52a', ['enalapril'], ctx(52, pa=True, risco=False, cond=HAS)),
    Caso('P003 valsartana HAS PA-descontrolada risco-elevado 61a', ['valsartana'],
         ctx(61, pa=False, risco=True, cond=HAS)),
    Caso('P004 ramipril HAS PA-controlada baixo-risco 72a (cautela)', ['ramipril'],
         ctx(72, sexo='feminino', pa=True, risco=False, cond=HAS)),
    Caso('P005 olmesartana+HCTZ PA-controlada risco-elevado 63a', ['olmesartana_hidroclorotiazida'],
         ctx(63, pa=True, risco=True, cond=HAS)),
    Caso('P006 perindopril+indapamida+anlodipino PA-controlada risco-elevado 81a', ['perindopril_indapamida_anlodipino'],
         ctx(81, sexo='feminino', pa=True, risco=True, cond=HAS)),
    Caso('P007 captopril PA-nao-informada risco-elevado 50a', ['captopril'], ctx(50, pa=None, risco=True, cond=HAS)),
    Caso('P008 lisinopril PA-controlada risco-nao-informado 45a', ['lisinopril'],
         ctx(45, pa=True, risco=None, cond=HAS)),
    Caso('P009 candesartana ICFEr+HAS PA-controlada risco-elevado 67a', ['candesartana'],
         ctx(67, pa=True, risco=True, cond=ICFER + HAS)),
    Caso('P010 telmisartana ICFEp PA-descontrolada risco-elevado 74a', ['telmisartana'],
         ctx(74, sexo='feminino', pa=False, risco=True, cond=('ic',) + HAS)),
    Caso('P011 irbesartana ICFEr baixo-risco 59a', ['irbesartana'], ctx(59, pa=True, risco=False, cond=ICFER)),
    Caso('P012 benazepril PA-descontrolada baixo-risco 66a (cautela)', ['benazepril'],
         ctx(66, pa=False, risco=False, cond=HAS)),
    Caso('P013 losartana+anlodipino PA-controlada baixo-risco 64a (sem cautela)', ['losartana_anlodipino'],
         ctx(64, pa=True, risco=False, cond=HAS)),
    Caso('P014 valsartana+anlodipino PA-controlada baixo-risco 65a (limiar da cautela)', ['valsartana_anlodipino'],
         ctx(65, sexo='feminino', pa=True, risco=False, cond=HAS)),
    Caso('P015 enalapril+HCTZ PA-controlada baixo-risco 70a', ['enalapril_hidroclorotiazida'],
         ctx(70, pa=True, risco=False, cond=HAS)),
    Caso('P016 losartana+HCTZ PA-descontrolada risco-elevado 77a', ['losartana_hidroclorotiazida'],
         ctx(77, sexo='feminino', pa=False, risco=True, cond=HAS)),
    Caso('P017 perindopril PA-controlada risco-elevado 55a', ['perindopril'], ctx(55, pa=True, risco=True, cond=HAS)),
    Caso('P018 valsartana+HCTZ PA-controlada risco-elevado 69a', ['valsartana_hidroclorotiazida'],
         ctx(69, pa=True, risco=True, cond=HAS)),
    Caso('P019 telmisartana+HCTZ PA-descontrolada baixo-risco 48a', ['telmisartana_hidroclorotiazida'],
         ctx(48, sexo='feminino', pa=False, risco=False, cond=HAS)),
    Caso('P020 perindopril+indapamida PA-controlada baixo-risco 83a', ['perindopril_indapamida'],
         ctx(83, sexo='feminino', pa=True, risco=False, cond=HAS)),
    Caso('P021 sacubitril/valsartana ICFEr risco-elevado 71a', ['sacubitril_valsartana'],
         ctx(71, pa=True, risco=True, cond=ICFER + HAS)),
    Caso('P022 sacubitril/valsartana ICFEr baixo-risco 56a', ['sacubitril_valsartana'],
         ctx(56, pa=False, risco=False, cond=ICFER)),
    Caso('P023 alisquireno PA-descontrolada baixo-risco 62a', ['alisquireno'], ctx(62, pa=False, risco=False, cond=HAS)),
    # AHA §7.2 rec. 1 vale para inibidores do SRAA (RAASi); o alisquireno segue a regra do IECA/BRA (commit 9b1e18d).
    Caso('P024 alisquireno PA-controlada risco-elevado 60a', ['alisquireno'], ctx(60, pa=True, risco=True, cond=HAS)),
    Caso('P025 valsartana ICFEp+HAS PA-controlada risco-elevado 73a', ['valsartana'],
         ctx(73, sexo='feminino', pa=True, risco=True, cond=('ic',) + HAS)),
    Caso('P026 losartana risco-e-PA-nao-informados 79a', ['losartana'],
         ctx(79, sexo='feminino', pa=None, risco=None, cond=HAS)),

    # --- BCC, diuréticos, outros anti-hipertensivos, clonidina ---------------------------------------------
    Caso('P027 anlodipino HAS 50a', ['anlodipino'], ctx(50, cond=HAS)),
    Caso('P028 nifedipino HAS 70a (cautela)', ['nifedipino'], ctx(70, sexo='feminino', cond=HAS)),
    Caso('P029 diltiazem angina 68a (bradicardia, cautela)', ['diltiazem'], ctx(68, cond=('dac',) + HAS)),
    Caso('P030 verapamil FA 55a', ['verapamil'], ctx(55, cond=('fa',))),
    Caso('P031 felodipino HAS 66a', ['felodipino'], ctx(66, sexo='feminino', cond=HAS)),
    Caso('P032 lercanidipino HAS 40a', ['lercanidipino'], ctx(40, cond=HAS)),
    Caso('P033 manidipino HAS 80a', ['manidipino'], ctx(80, cond=HAS)),
    Caso('P034 levanlodipino HAS 75a', ['levanlodipino'], ctx(75, sexo='feminino', cond=HAS)),
    Caso('P035 hidroclorotiazida HAS 60a', ['hidroclorotiazida'], ctx(60, sexo='feminino', cond=HAS)),
    Caso('P036 clortalidona HAS 71a (cautela)', ['clortalidona'], ctx(71, cond=HAS)),
    Caso('P037 indapamida HAS 45a', ['indapamida'], ctx(45, sexo='feminino', cond=HAS)),
    Caso('P038 furosemida ICFEr 78a (ramo IC)', ['furosemida'], ctx(78, cond=ICFER)),
    Caso('P039 furosemida edema sem IC 69a (cautela)', ['furosemida'], ctx(69, sexo='feminino', cond=HAS)),
    Caso('P040 bumetanida ICFEp 82a', ['bumetanida'], ctx(82, sexo='feminino', cond=('ic',))),
    Caso('P041 espironolactona ICFEr 63a (GDMT)', ['espironolactona'], ctx(63, cond=ICFER)),
    Caso('P042 espironolactona HAS resistente 66a', ['espironolactona'], ctx(66, cond=HAS)),
    Caso('P043 eplerenona ICFEr pos-IAM 58a', ['eplerenona'], ctx(58, cond=ICFER + ('dac',))),
    Caso('P044 amilorida com IC 72a', ['amilorida'], ctx(72, cond=('ic',))),
    Caso('P045 hidralazina HAS 74a (cautela)', ['hidralazina'], ctx(74, sexo='feminino', cond=HAS)),
    Caso('P046 metildopa HAS 35a', ['metildopa'], ctx(35, sexo='feminino', cond=HAS)),
    Caso('P047 minoxidil oral HAS resistente 67a', ['minoxidil_oral'], ctx(67, cond=HAS)),
    Caso('P048 clonidina HAS 70a', ['clonidina'], ctx(70, cond=HAS)),
    Caso('P049 clonidina HAS urgencia 52a', ['clonidina'], ctx(52, urgencia='urgencia', cond=HAS)),

    # --- Betabloqueadores e estatinas ------------------------------------------------------------------------
    Caso('P050 atenolol HAS 57a', ['atenolol'], ctx(57, cond=HAS)),
    Caso('P051 metoprolol DAC 64a', ['metoprolol'], ctx(64, cond=('dac',))),
    Caso('P052 nebivolol HAS 49a', ['nebivolol'], ctx(49, sexo='feminino', cond=HAS)),
    Caso('P053 carvedilol ICFEr 70a', ['carvedilol'], ctx(70, cond=ICFER)),
    Caso('P054 bisoprolol ICFEr urgencia 76a', ['bisoprolol'], ctx(76, urgencia='urgencia', cond=ICFER)),
    Caso('P055 propranolol tremor 38a', ['propranolol'], ctx(38, sexo='feminino')),
    Caso('P056 atenolol+clortalidona HAS 68a', ['atenolol_clortalidona'], ctx(68, cond=HAS)),
    Caso('P057 sinvastatina 54a', ['sinvastatina'], ctx(54)),
    Caso('P058 atorvastatina DAC 66a', ['atorvastatina'], ctx(66, cond=('dac',))),
    Caso('P059 rosuvastatina DAP 72a', ['rosuvastatina'], ctx(72, cond=('doenca_arterial_periferica',))),
    Caso('P060 pravastatina HIV 47a', ['pravastatina'], ctx(47)),
    Caso('P061 pitavastatina 58a', ['pitavastatina'], ctx(58, sexo='feminino')),
    Caso('P062 fluvastatina 61a', ['fluvastatina'], ctx(61)),
    Caso('P063 lovastatina 65a', ['lovastatina'], ctx(65, sexo='feminino')),
    Caso('P064 ezetimiba+sinvastatina 59a', ['ezetimiba_sinvastatina'], ctx(59)),
    Caso('P065 rosuvastatina+ezetimiba emergencia 63a', ['rosuvastatina_ezetimiba'], ctx(63, urgencia='emergencia')),
    Caso('P066 amiodarona+digoxina com ICFEr 75a', ['amiodarona', 'digoxina'], ctx(75, cond=ICFER)),
    Caso('P067 ivabradina+mononitrato com IC 68a', ['ivabradina', 'mononitrato_de_isossorbida'], ctx(68, cond=('ic',))),
    Caso('P068 amiodarona+propafenona sem IC 66a (sem fonte)', ['amiodarona', 'propafenona'], ctx(66, cond=('fa',))),

    # --- iSGLT2 (AHA §7.8 rec. 2; §6.3 rec. 1) --------------------------------------------------------------
    Caso('P069 dapagliflozina DM2 61a', ['dapagliflozina'], ctx(61, cond=DM)),
    Caso('P070 empagliflozina ICFEr sem DM 70a', ['empagliflozina'], ctx(70, cond=ICFER)),
    Caso('P071 canagliflozina DM2 DRC 66a', ['canagliflozina'], ctx(66, clcr=42.0, cond=DM + ('doenca_renal',))),
    Caso('P072 dapagliflozina+metformina DM2 55a', ['dapagliflozina_metformina'], ctx(55, sexo='feminino', cond=DM)),
    Caso('P073 empagliflozina+linagliptina DM2 62a', ['empagliflozina_linagliptina'], ctx(62, cond=DM)),
    Caso('P074 dapagliflozina ICFEp 79a tempo-sensivel', ['dapagliflozina'],
         ctx(79, sexo='feminino', urgencia='tempo_sensivel', cond=('ic',))),
    Caso('P075 empagliflozina DM2 emergencia 58a', ['empagliflozina'], ctx(58, urgencia='emergencia', cond=DM)),

    # --- Metformina e orais (SBD/SBA/ABESO 2026; AHA §7.8 rec. 3) ---------------------------------------------------
    Caso('P076 metformina ClCr 92 50a', ['metformina'], ctx(50, clcr=92.0, cond=DM)),
    Caso('P077 metformina ClCr 45 70a', ['metformina'], ctx(70, sexo='feminino', clcr=45.0, cond=DM)),
    Caso('P078 metformina ClCr 31 76a', ['metformina'], ctx(76, clcr=31.0, cond=DM)),
    Caso('P079 metformina TFG 24 81a', ['metformina'], dict(ctx(81, sexo='feminino', clcr=22.0, cond=DM), tfg=24)),
    Caso('P079b metformina ClCr 26 com TFG 34 (peso baixo) 84a', ['metformina'],
         dict(ctx(84, sexo='feminino', clcr=26.0, cond=DM), tfg=34)),
    Caso('P080 glibenclamida DM2 67a', ['glibenclamida'], ctx(67, cond=DM)),
    Caso('P081 gliclazida DM2 59a', ['gliclazida'], ctx(59, sexo='feminino', cond=DM)),
    Caso('P082 glimepirida DM2 72a', ['glimepirida'], ctx(72, cond=DM)),
    Caso('P083 sitagliptina DM2 64a', ['sitagliptina'], ctx(64, cond=DM)),
    Caso('P084 vildagliptina DM2 57a', ['vildagliptina'], ctx(57, sexo='feminino', cond=DM)),
    Caso('P085 linagliptina DM2 DRC 77a', ['linagliptina'], ctx(77, clcr=28.0, cond=DM)),
    Caso('P086 saxagliptina+alogliptina DM2 60a', ['saxagliptina', 'alogliptina'], ctx(60, cond=DM)),
    Caso('P087 pioglitazona+acarbose DM2 63a', ['pioglitazona', 'acarbose'], ctx(63, sexo='feminino', cond=DM)),
    Caso('P088 sitagliptina+metformina DM2 54a', ['sitagliptina_metformina'], ctx(54, cond=DM)),
    Caso('P089 vildagliptina+metformina DM2 68a', ['vildagliptina_metformina'], ctx(68, sexo='feminino', cond=DM)),
    Caso('P090 linagliptina+metformina DM2 71a', ['linagliptina_metformina'], ctx(71, cond=DM)),

    # --- aGLP-1 (Kindel 2024 × AHA texto) --------------------------------------------------------------------
    Caso('P091 semaglutida semanal obesidade 44a', ['semaglutida'], ctx(44, sexo='feminino', cond=('obesidade',))),
    Caso('P092 dulaglutida semanal DM2 62a', ['dulaglutida'], ctx(62, cond=DM)),
    Caso('P093 tirzepatida semanal obesidade+DM2 51a', ['tirzepatida'], ctx(51, cond=DM + ('obesidade',))),
    Caso('P094 liraglutida diaria DM2 58a', ['liraglutida'], ctx(58, sexo='feminino', cond=DM)),
    Caso('P095 semaglutida urgencia 39a', ['semaglutida'], ctx(39, urgencia='urgencia', cond=('obesidade',))),

    # --- Insulinas (SPAQI 2021) ------------------------------------------------------------------------------
    Caso('P096 glargina DM2 66a', ['insulina_glargina'], ctx(66, cond=DMI)),
    Caso('P097 degludeca DM1 29a', ['insulina_degludeca'], ctx(29, sexo='feminino', cond=DMI)),
    Caso('P098 detemir DM2 73a', ['insulina_detemir'], ctx(73, cond=DMI)),
    Caso('P099 NPH DM2 69a', ['insulina_nph'], ctx(69, sexo='feminino', cond=DMI)),
    Caso('P100 regular DM2 61a', ['insulina_regular'], ctx(61, cond=DMI)),
    Caso('P101 asparte+glargina DM1 34a', ['insulina_asparte', 'insulina_glargina'], ctx(34, cond=DMI)),
    Caso('P102 lispro+degludeca DM1 22a', ['insulina_lispro', 'insulina_degludeca'], ctx(22, sexo='feminino', cond=DMI)),
    Caso('P103 glulisina+detemir DM2 57a', ['insulina_glulisina', 'insulina_detemir'], ctx(57, cond=DMI)),
    Caso('P104 glargina+lixisenatida DM2 64a', ['insulina_glargina_lixisenatida'], ctx(64, cond=DMI)),
    Caso('P105 degludeca+liraglutida DM2 70a', ['insulina_degludeca_liraglutida'], ctx(70, sexo='feminino', cond=DMI)),
    Caso('P106 icodeca e bifasica sem fonte 68a', ['insulina_icodeca', 'insulina_bifasica'], ctx(68, cond=DMI)),

    # --- Corticoides (ESE/ES 2024; SPAQI; ACR) ---------------------------------------------------------------
    Caso('P107 prednisona eletiva AR 58a', ['prednisona'], ctx(58, sexo='feminino', cond=())),
    Caso('P108 prednisona emergencia DPOC 74a', ['prednisona'], ctx(74, urgencia='emergencia', cond=('dpoc',))),
    Caso('P109 prednisolona polimialgia 71a', ['prednisolona'], ctx(71, sexo='feminino')),
    Caso('P110 metilprednisolona LES 33a', ['metilprednisolona'], ctx(33, sexo='feminino')),
    Caso('P111 dexametasona glioma urgencia 52a', ['dexametasona'], ctx(52, urgencia='urgencia')),
    Caso('P112 hidrocortisona insuficiencia adrenal 45a', ['hidrocortisona'], ctx(45)),
    Caso('P113 deflazacorte distrofia 19a', ['deflazacorte'], ctx(19)),

    # --- Antirreumáticos / imunobiológicos (ACR/AAHKS 2022) --------------------------------------------------
    Caso('P114 metotrexato+hidroxicloroquina AR artroplastia 62a', ['metotrexato', 'hidroxicloroquina'],
         ctx(62, sexo='feminino', sangramento='alto')),
    Caso('P115 leflunomida+sulfassalazina AR 55a', ['leflunomida', 'sulfassalazina'], ctx(55, sexo='feminino')),
    Caso('P116 adalimumabe EA 41a', ['adalimumabe'], ctx(41)),
    Caso('P117 etanercepte+metotrexato AR 60a', ['etanercepte', 'metotrexato'], ctx(60, sexo='feminino')),
    Caso('P118 infliximabe Crohn 36a', ['infliximabe'], ctx(36)),
    Caso('P119 tocilizumabe AR 67a', ['tocilizumabe'], ctx(67, sexo='feminino')),
    Caso('P120 rituximabe AR 59a', ['rituximabe'], ctx(59, sexo='feminino')),
    Caso('P121 abatacepte AR 72a', ['abatacepte'], ctx(72, sexo='feminino')),
    Caso('P122 secuquinumabe psoriase 44a', ['secuquinumabe'], ctx(44)),
    Caso('P123 ustequinumabe+guselcumabe psoriase 50a', ['ustequinumabe', 'guselcumabe'], ctx(50)),
    Caso('P124 risanquizumabe+ixequizumabe 47a', ['risanquizumabe', 'ixequizumabe'], ctx(47, sexo='feminino')),
    Caso('P125 golimumabe+certolizumabe 53a', ['golimumabe', 'certolizumabe_pegol'], ctx(53)),
    Caso('P126 tofacitinibe AR 64a', ['tofacitinibe'], ctx(64, sexo='feminino')),
    Caso('P127 upadacitinibe EA 39a', ['upadacitinibe'], ctx(39)),
    Caso('P128 baricitinibe AR 70a', ['baricitinibe'], ctx(70, sexo='feminino')),
    Caso('P129 micofenolato LES 31a', ['micofenolato'], ctx(31, sexo='feminino')),
    Caso('P130 azatioprina+ciclosporina 46a', ['azatioprina', 'ciclosporina'], ctx(46, sexo='feminino')),
    Caso('P131 tacrolimo transplante renal 52a', ['tacrolimo'], ctx(52, clcr=48.0)),
    Caso('P132 vedolizumabe+fingolimode+natalizumabe sem fonte 38a', ['vedolizumabe', 'fingolimode', 'natalizumabe'],
         ctx(38, sexo='feminino')),

    # --- Psiquiatria (SPAQI 2022) ----------------------------------------------------------------------------
    Caso('P133 sertralina+escitalopram ISRS 42a', ['sertralina', 'escitalopram'], ctx(42, sexo='feminino')),
    Caso('P134 venlafaxina+duloxetina IRSN 55a', ['venlafaxina', 'duloxetina'], ctx(55, sexo='feminino')),
    Caso('P135 bupropiona+mirtazapina+trazodona 61a', ['bupropiona', 'mirtazapina', 'trazodona'], ctx(61)),
    Caso('P136 amitriptilina+nortriptilina triciclicos 67a', ['amitriptilina', 'nortriptilina'],
         ctx(67, sexo='feminino')),
    Caso('P137 paroxetina+vortioxetina+agomelatina 49a', ['paroxetina', 'vortioxetina', 'agomelatina'], ctx(49)),
    Caso('P138 quetiapina+olanzapina 36a', ['quetiapina', 'olanzapina'], ctx(36)),
    Caso('P139 clozapina+haloperidol esquizofrenia 44a', ['clozapina', 'haloperidol'], ctx(44)),
    Caso('P140 risperidona+aripiprazol 28a', ['risperidona', 'aripiprazol'], ctx(28, sexo='feminino')),
    Caso('P141 clonazepam+alprazolam 58a', ['clonazepam', 'alprazolam'], ctx(58, sexo='feminino')),
    Caso('P142 litio cirurgia maior risco-elevado 47a', ['litio'], ctx(47, risco=True, sangramento='alto')),
    Caso('P143 litio procedimento menor 39a', ['litio'], ctx(39, sexo='feminino', sangramento='minimo')),
    Caso('P144 lisdexanfetamina TDAH 26a', ['lisdexanfetamina'], ctx(26)),
    Caso('P145 zolpidem+metilfenidato sem fonte 33a', ['zolpidem', 'metilfenidato'], ctx(33, sexo='feminino')),

    # --- Hormônios (SPAQI 2021) ------------------------------------------------------------------------------
    Caso('P146 anticoncepcional combinado procedimento menor 28a', ['anticoncepcional_combinado'],
         ctx(28, sexo='feminino', sangramento='minimo', risco=False)),
    Caso('P147 THM menopausa 56a', ['terapia_hormonal_da_menopausa'], ctx(56, sexo='feminino')),
    Caso('P148 progestagenio isolado 31a', ['anticoncepcional_so_com_progestagenio'], ctx(31, sexo='feminino')),
    Caso('P149 testosterona hipogonadismo 54a', ['testosterona'], ctx(54)),
    Caso('P150 tamoxifeno cancer de mama 49a', ['tamoxifeno'], ctx(49, sexo='feminino', cond=('cancer_ativo',))),
    Caso('P151 levotiroxina hipotireoidismo 63a', ['levotiroxina'], ctx(63, sexo='feminino')),
    Caso('P152 metimazol+propiltiouracila 37a', ['metimazol_tiamazol', 'propiltiouracila'], ctx(37, sexo='feminino')),
    Caso('P153 anticoncepcional combinado artroplastia quadril 34a', ['anticoncepcional_combinado'],
         ctx(34, sexo='feminino', sangramento='alto', risco=True)),

    # --- Lacunas: fonte existe, módulo não gera item ---------------------------------------------------------
    Caso('P154 tansulosina HPB 71a', ['tansulosina'], ctx(71),
         xfail='SPAQI 2021: manter alfa-1 bloqueador inclusive no dia (https://doi.org/10.1016/j.mayocp.2020.10.002); '
               'o módulo não gera item.'),
    Caso('P155 dutasterida HPB 68a', ['dutasterida'], ctx(68),
         xfail='SPAQI 2021: manter inibidor da 5-alfa-redutase inclusive no dia '
               '(https://doi.org/10.1016/j.mayocp.2020.10.002); o módulo não gera item.'),
    Caso('P156 oxibutinina bexiga hiperativa 74a', ['oxibutinina'], ctx(74, sexo='feminino'),
         xfail='SPAQI 2021: antimuscarínico vesical, não tomar na manhã da cirurgia '
               '(https://doi.org/10.1016/j.mayocp.2020.10.002); o módulo não gera item.'),
    Caso('P157 alendronato osteoporose 69a', ['alendronato'], ctx(69, sexo='feminino'),
         xfail='SPAQI 2021: bisfosfonato oral pode ser mantido, mas não no dia da cirurgia '
               '(https://doi.org/10.1016/j.mayocp.2020.10.002); o módulo não gera item.'),
    Caso('P158 denosumabe osteoporose 77a', ['denosumabe'], ctx(77, sexo='feminino'),
         xfail='SPAQI 2021: manter denosumabe e PTH antes e no dia (https://doi.org/10.1016/j.mayocp.2020.10.002); '
               'o módulo não gera item.'),
    Caso('P159 levetiracetam epilepsia 35a', ['levetiracetam'], ctx(35),
         xfail='SPAQI neurológico 2022: medicações neurológicas devem ser mantidas no pré-operatório '
               '(https://doi.org/10.1016/j.mayocp.2021.11.010); o módulo trata anticonvulsivantes como sem fonte.'),
    Caso('P160 levodopa+carbidopa Parkinson 72a', ['levodopa_carbidopa'], ctx(72),
         xfail='SPAQI neurológico 2022: manter antiparkinsonianos (https://doi.org/10.1016/j.mayocp.2021.11.010); '
               'o módulo não gera item.'),
    Caso('P161 valproato transtorno bipolar 41a', ['acido_valproico_divalproato'], ctx(41, sexo='feminino'),
         xfail='SPAQI psiquiátrico 2022: anticonvulsivante usado como estabilizador de humor, tomar inclusive no dia '
               '(https://doi.org/10.1016/j.mayocp.2021.11.011); o módulo não gera item.'),

    # --- Sem fonte: nada pode aparecer -----------------------------------------------------------------------
    Caso('P162 ezetimiba+fenofibrato+omeprazol sem fonte 57a', ['ezetimiba', 'fenofibrato', 'omeprazol'], ctx(57)),
    Caso('P163 inalatorios DPOC sem fonte 70a', ['formoterol_budesonida', 'tiotropio', 'salbutamol'],
         ctx(70, cond=('dpoc',))),
    Caso('P164 TARV sem fonte 45a', ['tenofovir_lamivudina_dolutegravir'], ctx(45)),
    Caso('P165 anastrozol+colecalciferol sem fonte 62a', ['anastrozol', 'colecalciferol_vitamina_d'],
         ctx(62, sexo='feminino')),

    # --- Polifarmácia ----------------------------------------------------------------------------------------
    Caso('P166 HAS+DM2+DAC 68a PA-controlada risco-elevado', ['losartana', 'atenolol', 'atorvastatina', 'metformina',
                                                            'dapagliflozina', 'anlodipino',
                                                            'aas_acido_acetilsalicilico'],
         ctx(68, pa=True, risco=True, clcr=70.0, cond=HAS + DM + ('dac',))),
    Caso('P167 ICFEr GDMT completa 74a', ['sacubitril_valsartana', 'carvedilol', 'espironolactona', 'empagliflozina',
                                         'furosemida', 'digoxina'],
         ctx(74, sexo='feminino', pa=True, risco=True, cond=ICFER)),
    Caso('P168 AR artroplastia joelho 55a', ['metotrexato', 'adalimumabe', 'prednisona', 'hidroxicloroquina',
                                           'omeprazol', 'sertralina'],
         ctx(55, sexo='feminino', sangramento='alto', risco=False)),
    Caso('P169 DM1 basal-bolus+HAS 62a PA-descontrolada', ['insulina_glargina', 'insulina_lispro', 'atorvastatina',
                                                         'enalapril', 'levotiroxina'],
         ctx(62, pa=False, risco=True, cond=DMI + HAS)),
    Caso('P170 obesidade+DM2 47a', ['tirzepatida', 'metformina', 'escitalopram', 'anticoncepcional_combinado'],
         ctx(47, sexo='feminino', sangramento='minimo', risco=False, clcr=110.0, cond=DM + ('obesidade',))),
    Caso('P171 idoso 80a HAS PA-controlada baixo-risco', ['anlodipino', 'hidroclorotiazida', 'sinvastatina',
                                                         'sertralina', 'omeprazol'],
         ctx(80, pa=True, risco=False, cond=HAS)),
    Caso('P172 bipolar com hipotireoidismo 40a', ['litio', 'quetiapina', 'clonazepam', 'levotiroxina'],
         ctx(40, sexo='feminino')),
    Caso('P173 LES + HAS 50a PA-controlada risco-elevado', ['micofenolato', 'hidroxicloroquina', 'prednisona',
                                                           'losartana'],
         ctx(50, sexo='feminino', pa=True, risco=True, cond=HAS)),
    Caso('P174 DM2 insulinizado 66a', ['insulina_nph', 'insulina_regular', 'metformina', 'gliclazida', 'sitagliptina'],
         ctx(66, clcr=50.0, cond=DMI)),
    Caso('P175 transplante renal 52a', ['tacrolimo', 'micofenolato', 'prednisona', 'anlodipino', 'everolimo'],
         ctx(52, clcr=55.0, cond=HAS)),
    Caso('P176 HAS resistente 58a PA-descontrolada risco-elevado', ['perindopril_indapamida_anlodipino', 'espironolactona',
                                                                   'clonidina', 'hidralazina'],
         ctx(58, pa=False, risco=True, cond=HAS)),
    Caso('P177 cancer de mama + depressao 76a', ['tamoxifeno', 'anastrozol', 'venlafaxina', 'atorvastatina',
                                                'colecalciferol_vitamina_d'],
         ctx(76, sexo='feminino', cond=('cancer_ativo',))),
    Caso('P178 psoriase 35a', ['secuquinumabe', 'metotrexato', 'bupropiona'], ctx(35)),
    Caso('P179 EA 50a', ['upadacitinibe', 'prednisolona', 'omeprazol'], ctx(50)),
    Caso('P180 ICFEp+HAS 72a PA-descontrolada', ['valsartana', 'espironolactona', 'furosemida', 'dapagliflozina',
                                                'rosuvastatina'],
         ctx(72, sexo='feminino', pa=False, risco=True, cond=('ic',) + HAS)),
    Caso('P181 DAC+DM2 com antitromboticos 69a', ['clopidogrel', 'aas_acido_acetilsalicilico', 'metoprolol',
                                                 'rosuvastatina', 'ezetimiba', 'semaglutida', 'empagliflozina'],
         ctx(69, cond=DM + ('dac',), sangramento='baixo_moderado')),
    Caso('P182 transicao de genero 30a', ['testosterona', 'escitalopram'], ctx(30)),
    Caso('P183 hipertireoidismo + FA 45a', ['metimazol_tiamazol', 'propranolol', 'apixabana'],
         ctx(45, sexo='feminino', cond=('fa',), clcr=90.0)),
]

PARAMS = [pytest.param(c, id=c.id, marks=pytest.mark.xfail(strict=True, reason=c.xfail) if c.xfail else ())
          for c in CASOS]


# ---------------------------------------------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize('caso', PARAMS)
def test_paciente(caso):
    r = pm.condutas(caso.meds, caso.ctx)
    por_chave = {}
    for i in r['itens']:
        assert i['chave'] not in por_chave, f'item duplicado: {i["chave"]}'
        por_chave[i['chave']] = i
    # um item por medicamento com regra, na ordem da entrada (associação em dose fixa = um item só)
    ordem = [i['chave'] for i in r['itens']]
    assert ordem == [m for m in caso.meds if m in por_chave]
    for chave in caso.meds:
        if chave in ANTITROMBOTICOS:
            continue
        conferir_item(chave, por_chave.get(chave), caso.ctx)
    # AHA §7.8 rec. 1 (2a, B-NR): HbA1c se diabetes, inclusive quando a doença só aparece pelo antidiabético
    antidiabeticos = ISGLT2_DIAS.keys() | {'metformina'} | SECRETAGOGOS | IDPP4 | TZD_ACARBOSE | IDPP4_METFORMINA | \
        GLP1_SEMANAL | GLP1_DIARIO | INSULINA_BASAL | INSULINA_NPH | INSULINA_PRANDIAL | INSULINA_GLP1 | \
        {'insulina_icodeca', 'insulina_bifasica'}
    diabetico = bool(_cond(caso.ctx) & {'diabetes', 'diabetes_insulina'}) or any(m in antidiabeticos for m in caso.meds)
    hba1c = [a for a in r['avisos'] if 'HbA1c' in a['titulo']]
    assert bool(hba1c) == diabetico
    for a in hba1c:
        assert '2a' in a['texto'] and '3 meses' in a['texto'] and '8%' in a['texto']
        assert {AHA, SBD} <= {ref['url'] for ref in a['referencias']}
    for a in r['avisos']:
        assert a['referencias'] and all(ref['url'].startswith('https://') for ref in a['referencias'])


def test_sem_fonte_nao_gera_item_em_nenhum_contexto():
    """Medicamentos sem recomendação nas fontes revisadas não geram item (o módulo não presume "manter")."""
    contextos = [ctx(), ctx(80, pa=True, risco=True, cond=HAS + DM + ICFER), ctx(30, urgencia='emergencia')]
    for c in contextos:
        r = pm.condutas(sorted(SEM_FONTE), c)
        assert r['itens'] == [], [i['chave'] for i in r['itens']]


def test_catalogo_nao_antitrombotico_coberto_pelo_oraculo():
    """Todo medicamento não antitrombótico do catálogo está classificado no oráculo (regra, lacuna ou sem fonte)."""
    classificados = (BETABLOQ | ESTATINAS | SRAA | ARNI | INIBIDOR_RENINA | BCC_DHP | BCC_NAO_DHP | TIAZIDICOS | ALCA
                     | ARM | POUPADOR_K | VASODIL_SIMPATOL | CLONIDINA | OUTROS_CARDIO | set(ISGLT2_DIAS) | {'metformina'}
                     | SECRETAGOGOS | IDPP4 | TZD_ACARBOSE | IDPP4_METFORMINA | GLP1_SEMANAL | GLP1_DIARIO
                     | INSULINA_BASAL | INSULINA_NPH | INSULINA_PRANDIAL | INSULINA_GLP1 | CORTICOIDES
                     | DMARD_SINTETICOS | BIOLOGICOS_ACR | JAK | LES | ANTIDEPRESSIVOS | ANTIPSICOTICOS
                     | BENZODIAZEPINICOS | {'litio'} | ANFETAMINAS | ESTROGENIOS | TIREOIDE
                     | {'anticoncepcional_so_com_progestagenio', 'testosterona', 'tamoxifeno'} | LACUNAS | SEM_FONTE
                     | {'acido_zoledronico'})
    faltando = set(MEDICAMENTOS) - ANTITROMBOTICOS - classificados
    assert not faltando, sorted(faltando)
    assert not (LACUNAS & SEM_FONTE)


def test_pelo_menos_100_pacientes_distintos():
    assert len(CASOS) >= 100
    assert len({c.id for c in CASOS}) == len(CASOS)
    assert len({(tuple(c.meds), tuple(sorted((k, str(v)) for k, v in c.ctx.items()))) for c in CASOS}) == len(CASOS)
