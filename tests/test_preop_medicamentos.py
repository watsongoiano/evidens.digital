"""Conduta perioperatória dos medicamentos (src/utils/preop_medicamentos.py), conferida contra as fontes:
AHA/ACC 2026 (Tabelas 12–14 e caixas de recomendação), SBC 2024 (Quadros 8–26 e Tabela 11), orientação
multissocietária de aGLP-1 2024, SPAQI, ACR/AAHKS 2022 e ESE/Endocrine Society 2024. Dados fictícios."""
import pytest

from src.utils import preop_medicamentos as pm
from src.utils.medicamentos import MEDICAMENTOS

CONDUTAS = {'manter', 'suspender', 'ajustar', 'individualizar'}


def item(chave, **ctx):
    r = pm.condutas([chave], ctx)
    assert len(r['itens']) == 1, r
    return r['itens'][0]


def avisos(meds, **ctx):
    return pm.condutas(meds, ctx)['avisos']


def titulos(meds, **ctx):
    return [a['titulo'] for a in avisos(meds, **ctx)]


CTX_COMPLETO = dict(idade=70, sexo='feminino', peso=70.0, clcr=60.0, sangramento='baixo_moderado',
                    cirurgia_risco_elevado=True, urgencia='eletiva', neuraxial=False, pa_controlada=True,
                    condicoes={'fa', 'hipertensao', 'diabetes', 'dac'}, aas_indicacao='secundaria')


# --- Estrutura e referências --------------------------------------------------------------------------------------
def test_cada_item_coberto_tem_campos_e_referencia_https():
    chaves = sorted(pm.CHAVES_COBERTAS)
    r = pm.condutas(chaves, CTX_COMPLETO)
    assert [i['chave'] for i in r['itens']] == chaves
    for i in r['itens']:
        assert i['conduta'] in CONDUTAS, i
        assert i['medicamento'] == MEDICAMENTOS[i['chave']]['rotulo']
        assert i['resumo'] and i['texto'] and i['classe']
        assert isinstance(i['divergencia'], str)
        assert i['referencias'] and all(ref['url'].startswith('https://') and ref['label'] for ref in i['referencias'])
    for a in r['avisos']:
        assert a['titulo'] and a['texto']
        assert a['referencias'] and all(ref['url'].startswith('https://') for ref in a['referencias'])


@pytest.mark.parametrize('ctx', [{}, {'condicoes': {'ic'}}, {'sangramento': 'minimo'},
                                 {'sangramento': 'alto', 'neuraxial': True, 'clcr': 20},
                                 {'urgencia': 'emergencia', 'sangramento': 'alto'}])
def test_referencias_https_em_qualquer_contexto(ctx):
    r = pm.condutas(sorted(pm.CHAVES_COBERTAS | pm.CHAVES_SO_NA_IC), ctx)
    for x in r['itens'] + r['avisos']:
        assert x['referencias'] and all(ref['url'].startswith('https://') for ref in x['referencias']), x


def test_chave_desconhecida_ignorada_e_sem_regra_nao_gera_item():
    r = pm.condutas(['nao_existe', 'omeprazol', 'ezetimiba', 'ticlopidina', 'insulina_bifasica', 'zolpidem'], {})
    assert r['itens'] == []
    assert 'omeprazol' not in pm.CHAVES_COBERTAS


def test_um_item_por_chave_na_ordem_da_entrada():
    r = pm.condutas(['sinvastatina', 'atenolol', 'sinvastatina'], {})
    assert [i['chave'] for i in r['itens']] == ['sinvastatina', 'atenolol']


def test_contexto_ausente_nao_quebra():
    r = pm.condutas(['apixabana', 'varfarina', 'aas_acido_acetilsalicilico', 'clopidogrel', 'losartana'], None)
    assert {i['conduta'] for i in r['itens']} == {'individualizar'}


# --- Cardiovasculares ---------------------------------------------------------------------------------------------
def test_betabloqueador_e_estatina_mantidos():
    bb = item('metoprolol')
    assert bb['conduta'] == 'manter' and bb['classe'] == 'AHA 1 (B-NR) · SBC I-B'
    est = item('atorvastatina')
    assert est['conduta'] == 'manter' and est['classe'] == 'AHA 1 (B-NR) · SBC I-B'
    assert 'ezetimiba' in item('ezetimiba_sinvastatina')['texto']
    assert 'diurético' in item('atenolol_clortalidona')['texto']


def test_bcc_diuretico_clonidina_mantidos():
    assert item('anlodipino')['classe'] == 'SBC I-C'
    assert item('hidroclorotiazida')['conduta'] == 'manter'
    assert item('furosemida', condicoes={'ic'})['classe'] == 'SBC I-C'
    clon = item('clonidina')
    assert clon['conduta'] == 'manter' and clon['classe'] == 'SBC I-B' and 'rebote' in clon['texto']
    assert item('hidralazina')['classe'] == 'AHA 2a (C-EO)'


def test_cautela_de_hipotensao_em_idosos():
    assert 'nota da AHA' in item('anlodipino', idade=72)['texto']
    assert 'nota da AHA' not in item('anlodipino', idade=50)['texto']


def test_espironolactona_na_ic_e_como_diuretico():
    assert item('espironolactona', condicoes={'ic'})['classe'] == 'AHA 2a (C-LD) · SBC I-C'
    assert item('espironolactona')['classe'] == 'AHA 2a (C-EO) · SBC I-C'


def test_losartana_hipertensao_perfil_aha_omite_24h_com_divergencia():
    i = item('losartana', cirurgia_risco_elevado=True, pa_controlada=True, condicoes={'hipertensao'})
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Omitir nas 24 h antes'
    assert i['classe'] == 'AHA 2b (B-R) · SBC I-C'
    assert '2b, B-R' in i['divergencia'] and 'I-C' in i['divergencia']
    assert 'Nós optamos por seguir a AHA' in i['divergencia']


def test_losartana_fora_do_perfil_mantem_e_falta_de_dado_e_dita():
    i = item('losartana', cirurgia_risco_elevado=False, pa_controlada=True)
    assert i['conduta'] == 'manter' and i['divergencia']
    j = item('losartana', pa_controlada=True)
    assert j['conduta'] == 'individualizar' and 'risco elevado' in j['texto'] and j['divergencia']


def test_ieca_na_icfer_mantido_sem_divergencia():
    i = item('enalapril', condicoes={'ic_fe_reduzida'}, cirurgia_risco_elevado=True, pa_controlada=True)
    assert i['conduta'] == 'manter' and i['classe'] == 'AHA 2a (C-EO) · SBC I-C' and i['divergencia'] == ''


def test_associacao_bra_diuretico_segue_o_bra():
    i = item('losartana_hidroclorotiazida', cirurgia_risco_elevado=True, pa_controlada=True)
    assert i['resumo'] == 'Omitir nas 24 h antes' and 'diurético' in i['texto']
    j = item('perindopril_indapamida_anlodipino', cirurgia_risco_elevado=False)
    assert 'acompanham' in j['texto']


def test_arni_mantido():
    i = item('sacubitril_valsartana')
    assert i['conduta'] == 'manter' and 'SBC I-C' in i['classe']


def test_cardio_outro_so_com_ic():
    assert pm.condutas(['digoxina'], {})['itens'] == []
    assert item('digoxina', condicoes={'ic'})['classe'] == 'SBC I-C'
    assert 'digoxina' in pm.CHAVES_SO_NA_IC and 'digoxina' not in pm.CHAVES_COBERTAS


# --- iSGLT2, metformina, outros antidiabéticos, aGLP-1, insulina ---------------------------------------------------
@pytest.mark.parametrize('chave', ['empagliflozina', 'dapagliflozina', 'canagliflozina'])
def test_isglt2_suspende_3_dias_com_divergencia_sbc(chave):
    i = item(chave, condicoes={'ic'})
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 3 dias antes'
    assert i['classe'] == 'AHA 1 (C-LD)' and 'D-4' in i['texto']
    assert 'SBC' in i['divergencia'] and 'Nós optamos por seguir a AHA' in i['divergencia']


def test_ertugliflozina_4_dias(monkeypatch):
    monkeypatch.setitem(MEDICAMENTOS, 'ertugliflozina', {'rotulo': 'Ertugliflozina', 'grupo': 'Antidiabéticos',
                                                         'classes': ['isglt2'], 'busca': 'ertugliflozina'})
    i = item('ertugliflozina')
    assert i['resumo'] == 'Suspender 4 dias antes' and 'D-5' in i['texto']


def test_associacoes_com_isglt2_seguem_o_isglt2():
    i = item('dapagliflozina_metformina')
    assert i['resumo'] == 'Suspender 3 dias antes' and 'metformina' in i['texto']
    assert item('empagliflozina_linagliptina')['resumo'] == 'Suspender 3 dias antes'


def test_metformina_mantida_com_divergencia_spaqi():
    i = item('metformina')
    assert i['conduta'] == 'manter' and i['classe'] == 'AHA 2a (C-LD)'
    assert 'SPAQI' in i['divergencia'] and 'Nós optamos por seguir a AHA' in i['divergencia']


@pytest.mark.parametrize('chave', ['glibenclamida', 'gliclazida', 'sitagliptina', 'pioglitazona', 'acarbose'])
def test_orais_nao_tomados_na_manha_da_cirurgia(chave):
    i = item(chave)
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender no dia da cirurgia'
    assert 'consenso' in i['classe']


def test_idpp4_mais_metformina_segue_a_spaqi_com_divergencia():
    i = item('sitagliptina_metformina')
    assert i['resumo'] == 'Suspender no dia da cirurgia' and 'AHA' in i['divergencia']


@pytest.mark.parametrize('chave', ['semaglutida', 'dulaglutida', 'tirzepatida'])
def test_aglp1_semanal(chave):
    i = item(chave)
    assert i['conduta'] == 'individualizar' and '1 semana antes' in i['resumo']
    assert '≥1 semana antes' in i['texto'] and 'dieta líquida nas 24 h' in i['texto']
    assert '>1 semana' in i['divergencia'] and 'multissocietária' in i['divergencia']


def test_aglp1_diario():
    i = item('liraglutida')
    assert 'suspender no dia' in i['resumo'] and 'não aplicar no dia da cirurgia' in i['texto']
    assert 'véspera' in i['divergencia']


def test_insulina_basal_nph_prandial_e_associacao_com_aglp1():
    basal = item('insulina_glargina')
    assert basal['conduta'] == 'ajustar' and '60–80%' in basal['resumo']
    nph = item('insulina_nph')
    assert nph['conduta'] == 'ajustar' and '50%' in nph['resumo']
    for chave in ('insulina_lispro', 'insulina_regular'):
        assert item(chave)['conduta'] == 'suspender'
    combo = item('insulina_degludeca_liraglutida')
    assert combo['conduta'] == 'individualizar' and '60–80%' in combo['texto'] and 'aGLP-1' in combo['texto']
    assert pm.condutas(['insulina_icodeca'], {})['itens'] == []


def test_aviso_de_hba1c_com_antidiabetico():
    assert 'HbA1c pré-operatória' in titulos(['metformina'])
    assert 'HbA1c pré-operatória' not in titulos(['atenolol'])


# --- DOAC: fármaco × ClCr × sangramento (AHA Tabela 13; SBC Quadro 26) --------------------------------------------
@pytest.mark.parametrize('chave, clcr, sangramento, resumo, sbc', [
    ('apixabana', 80, 'baixo_moderado', 'Última dose no D-2 (1 dia sem dose); reiniciar no D+1',
     'suspender 24 h antes e reintroduzir 24 h depois'),
    ('apixabana', 80, 'alto', 'Última dose no D-3 (2 dias sem dose); reiniciar no D+3',
     'suspender pelo menos 48 h antes e reintroduzir 48 h depois'),
    ('rivaroxabana', 25, 'baixo_moderado', 'Última dose no D-3 (2 dias sem dose); reiniciar no D+1',
     'suspender pelo menos 48 h antes'),
    ('rivaroxabana', 25, 'alto', 'Última dose no D-4 (3 dias sem dose); reiniciar no D+3',
     'suspender pelo menos 48 h antes'),
    ('rivaroxabana', 90, 'baixo_moderado', 'Última dose no D-2 (1 dia sem dose); reiniciar no D+1',
     'suspender 24 h antes'),
    ('edoxabana', 60, 'alto', 'Última dose no D-3 (2 dias sem dose); reiniciar no D+3', 'suspender 48–72 h antes'),
    ('dabigatrana', 60, 'baixo_moderado', 'Última dose no D-2 (1 dia sem dose); reiniciar no D+1',
     'suspender 24 h antes e reintroduzir 24 h depois'),
    ('dabigatrana', 60, 'alto', 'Última dose no D-3 (2 dias sem dose); reiniciar no D+3',
     'suspender 48 h antes e reintroduzir 48 h depois'),
    ('dabigatrana', 45, 'baixo_moderado', 'Última dose no D-3 (2 dias sem dose); reiniciar no D+1',
     'suspender 48 h antes e reintroduzir 24 h depois'),
    ('dabigatrana', 40, 'alto', 'Última dose no D-5 (4 dias sem dose); reiniciar no D+3',
     'suspender 96 h antes e reintroduzir 48 h depois'),
])
def test_matriz_doac(chave, clcr, sangramento, resumo, sbc):
    i = item(chave, clcr=clcr, sangramento=sangramento)
    assert i['conduta'] == 'suspender'
    assert i['resumo'] == resumo
    assert sbc in i['texto']
    assert 'Sem ponte' in i['texto']


def test_apixabana_clcr_30_50_baixo_segue_a_sbc():
    i = item('apixabana', clcr=40, sangramento='baixo_moderado')
    assert i['resumo'] == 'Última dose ≥48 h antes; reiniciar 48 h depois'
    assert 'Nós optamos por seguir a SBC' in i['divergencia']


def test_anti_xa_clcr_menor_30_alto_tem_divergencia():
    assert 'D-4' in item('apixabana', clcr=20, sangramento='alto')['divergencia']


def test_edoxabana_sem_classe_na_sbc():
    i = item('edoxabana', clcr=60, sangramento='baixo_moderado')
    assert i['classe'] == 'AHA 1 (B-NR) · SBC: texto, sem classe' and i['divergencia']


def test_doac_sangramento_minimo_nao_interrompe_mesmo_sem_clcr():
    r = pm.condutas(['rivaroxabana'], {'sangramento': 'minimo'})
    assert r['itens'][0]['conduta'] == 'manter' and r['itens'][0]['resumo'] == 'Não interromper'
    assert 'Falta o clearance de creatinina' not in [a['titulo'] for a in r['avisos']]


def test_doac_sem_clcr_pede_o_dado():
    r = pm.condutas(['apixabana'], {'sangramento': 'baixo_moderado'})
    i = r['itens'][0]
    assert i['conduta'] == 'individualizar' and i['resumo'] == 'Depende do ClCr' and 'Falta o ClCr' in i['texto']
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Falta o clearance de creatinina')
    assert 'Cockcroft-Gault' in aviso['texto'] and 'apixabana' in aviso['texto']


def test_falta_risco_de_sangramento():
    r = pm.condutas(['dabigatrana'], {'clcr': 70})
    assert r['itens'][0]['resumo'] == 'Depende do risco de sangramento'
    assert 'Falta o risco de sangramento da cirurgia' in [a['titulo'] for a in r['avisos']]


def test_neuroaxial_conta_como_sangramento_alto_e_gera_aviso():
    r = pm.condutas(['dabigatrana'], {'clcr': 70, 'sangramento': 'baixo_moderado', 'neuraxial': True})
    i = r['itens'][0]
    # Neuroaxial: ≥ 5 meias-vidas (AHA §7.6, texto): ≥ 4 dias sem dabigatrana com ClCr ≥ 50; 6 com ClCr < 50
    assert i['resumo'] == 'Última dose no D-5 (4 dias sem dose); reiniciar no D+3'
    assert '≥6 h após retirar o cateter' in i['texto']
    r = pm.condutas(['dabigatrana'], {'clcr': 40, 'sangramento': 'alto', 'neuraxial': True})
    assert r['itens'][0]['resumo'] == 'Última dose no D-7 (6 dias sem dose); reiniciar no D+3'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Anestesia neuroaxial e anticoagulantes')
    assert '≥5 meias-vidas' in aviso['texto']
    assert item('apixabana', clcr=70, sangramento='minimo', neuraxial=True)['resumo'].startswith('Última dose no D-4')


def test_aceita_a_grafia_neuroaxial():
    r = pm.condutas(['apixabana'], {'clcr': 70, 'sangramento': 'baixo_moderado', 'neuroaxial': True})
    # Anti-Xa com neuroaxial: ≥ 3 dias sem dose (72 h)
    assert r['itens'][0]['resumo'] == 'Última dose no D-4 (3 dias sem dose); reiniciar no D+3'
    assert 'Anestesia neuroaxial e anticoagulantes' in [a['titulo'] for a in r['avisos']]


def test_correcoes_da_revisao_clinica():
    # AAS marcado como "primária" em quem tem stent: continua prevenção secundária (nunca suspender por erro de marcação)
    r = pm.condutas(['aas_acido_acetilsalicilico'], {'aas_indicacao': 'primaria', 'condicoes': {'stent'},
                                                     'stent': {'tipo': 'farmacologico', 'indicacao': 'sca', 'meses': 3}})
    assert r['itens'][0]['conduta'] == 'manter'
    # Alisquireno segue a regra dos IECA/BRA
    r = pm.condutas(['alisquireno'], {'condicoes': {'hipertensao'}, 'pa_controlada': True, 'cirurgia_risco_elevado': True})
    assert r['itens'][0]['resumo'].startswith('Omitir')
    # Edoxabana com ClCr < 30 e sangramento alto: divergência própria (SBC 48–72 h)
    r = pm.condutas(['edoxabana'], {'clcr': 25, 'sangramento': 'alto'})
    assert '48–72 h' in r['itens'][0]['divergencia']


def test_stent_com_campos_vazios_pede_os_dados():
    ctx = {'sangramento': 'alto', 'condicoes': {'stent', 'dac'},
           'stent': {'tipo': None, 'indicacao': None, 'meses': None}}
    r = pm.condutas(['aas_acido_acetilsalicilico', 'ticagrelor'], ctx)
    assert r['itens'][0]['resumo'] == 'Manter (75–100 mg)'
    assert r['itens'][1]['conduta'] == 'individualizar' and 'Falta tipo do stent' in r['itens'][1]['texto']


def test_doac_na_urgencia():
    i = item('dabigatrana', clcr=70, sangramento='alto', urgencia='emergencia')
    assert i['conduta'] == 'individualizar' and 'idarucizumabe' in i['texto']


# --- Varfarina: ponte conforme risco tromboembólico (AHA Tabela 14 × SBC Tabela 11) -----------------------------
def test_cha2ds2vasc_e_chads2():
    ctx = dict(idade=78, sexo='feminino', condicoes={'ic', 'hipertensao', 'diabetes', 'avc_ait', 'dac'})
    assert pm.cha2ds2vasc(ctx) == 1 + 1 + 2 + 1 + 2 + 1 + 1
    assert pm.chads2(ctx) == 1 + 1 + 1 + 1 + 2
    assert pm.cha2ds2vasc(dict(idade=70, sexo='masculino', condicoes=set())) == 1
    assert pm.cha2ds2vasc({}) == 0
    assert pm.cha2ds2vasc(dict(idade=60, condicoes={'doenca_arterial_periferica'})) == 1
    assert pm.cha2ds2vasc(dict(idade=60, condicoes={'iam_previo'})) == 1


def test_varfarina_baixo_risco_sem_ponte():
    ctx = dict(idade=60, sexo='masculino', condicoes={'fa', 'hipertensao'}, sangramento='baixo_moderado')
    r = pm.condutas(['varfarina'], ctx)
    i = r['itens'][0]
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 5 dias antes, sem ponte'
    assert 'D-6' in i['texto'] and 'INR <1,5' in i['texto'] and i['divergencia'] == ''
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Varfarina: risco tromboembólico e ponte')
    assert 'CHA₂DS₂-VASc = 1' in aviso['texto'] and 'AHA (Tabela 14): baixo' in aviso['texto']
    assert 'Sem ponte' in aviso['texto']


def test_varfarina_alto_risco_com_ponte():
    i = item('varfarina', condicoes={'protese_mecanica_mitral'}, sangramento='alto', idade=50, sexo='masculino')
    assert i['resumo'] == 'Suspender 5 dias antes, com ponte de heparina'
    assert i['classe'] == 'AHA 2a (C-LD) · SBC IIa-C'
    assert 'D+3' in i['texto'] and '24 h antes' in i['texto'] and i['divergencia'] == ''
    j = item('varfarina', condicoes={'tev_recente_3m'}, sangramento='baixo_moderado')
    assert 'com ponte' in j['resumo'] and 'D+2' in j['texto']


def test_varfarina_fa_cha2ds2vasc_7_e_alto_risco():
    ctx = dict(idade=80, sexo='feminino', condicoes={'fa', 'ic', 'hipertensao', 'diabetes', 'dac'},
               sangramento='baixo_moderado')
    assert pm.cha2ds2vasc(ctx) == 7
    i = item('varfarina', **ctx)
    assert 'com ponte' in i['resumo']
    # CHADS₂ 4 = moderado na SBC: a divergência explica e registra a escolha
    assert 'SBC: risco moderado' in i['divergencia'] and 'Nós optamos por seguir a AHA' in i['divergencia']


def test_varfarina_protese_aortica_divergencia_aha_sbc():
    i = item('varfarina', condicoes={'protese_mecanica'}, sangramento='alto', idade=55, sexo='masculino')
    assert i['resumo'] == 'Suspender 5 dias antes, sem ponte'
    assert 'SBC: risco tromboembólico alto' in i['divergencia']
    assert 'Nós optamos por seguir a AHA' in i['divergencia']


def test_varfarina_sangramento_minimo_urgencia_e_indicacao_ausente():
    assert item('varfarina', sangramento='minimo')['conduta'] == 'manter'
    urg = item('varfarina', sangramento='alto', urgencia='urgencia')
    assert urg['classe'] == 'SBC I-C' and 'vitamina K' in urg['texto']
    sem = pm.condutas(['varfarina'], {'sangramento': 'alto'})
    assert sem['itens'][0]['conduta'] == 'individualizar' and 'Falta a indicação' in sem['itens'][0]['texto']
    aviso = next(a for a in sem['avisos'] if a['titulo'].startswith('Varfarina'))
    assert 'Falta a indicação' in aviso['texto']


def test_aviso_da_varfarina_diz_o_que_falta_no_escore():
    r = pm.condutas(['varfarina'], {'condicoes': {'fa'}, 'sangramento': 'alto'})
    aviso = next(a for a in r['avisos'] if a['titulo'].startswith('Varfarina'))
    assert 'idade' in aviso['texto'] and 'sexo' in aviso['texto']


def test_enoxaparina_extrapolada_e_rotulada():
    i = item('enoxaparina')
    assert i['resumo'] == 'Dose plena: última dose 24 h antes' and 'extrapolado' in i['classe']


# --- AAS ------------------------------------------------------------------------------------------------------------
def test_aas_prevencao_primaria_suspende_7_dias():
    i = item('aas_acido_acetilsalicilico', aas_indicacao='primaria')
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 7 dias antes' and i['classe'] == 'SBC I-A'
    assert '4 dias' in i['divergencia'] and 'Nós optamos por seguir a SBC' in i['divergencia']


def test_aas_secundaria_inferida_da_dac_sem_icp():
    i = item('aas_acido_acetilsalicilico', condicoes={'dac'})
    assert i['conduta'] == 'manter' and i['classe'] == 'AHA 2b (B-R) · SBC I-A'
    assert 'Nós optamos por seguir a SBC' in i['divergencia']


def test_aas_com_icp_previa():
    i = item('aas_acido_acetilsalicilico', condicoes={'stent'})
    assert i['resumo'] == 'Manter (75–100 mg)' and i['classe'] == 'AHA 1 (B-R) · SBC I-A'


def test_aas_secundaria_sem_dac_e_indicacao_ausente():
    assert item('aas_acido_acetilsalicilico', condicoes={'avc_ait'})['classe'] == 'SBC I-A'
    i = item('aas_acido_acetilsalicilico')
    assert i['conduta'] == 'individualizar' and 'Falta a indicação' in i['texto']


# --- P2Y12 e janela do stent -----------------------------------------------------------------------------------------
@pytest.mark.parametrize('chave, dias, faixa', [('clopidogrel', 5, '5–7'), ('ticagrelor', 5, '3–5'),
                                                ('prasugrel', 7, '7–10')])
def test_p2y12_em_dapt_fora_da_janela(chave, dias, faixa):
    r = pm.condutas(['aas_acido_acetilsalicilico', chave], {'sangramento': 'alto', 'condicoes': {'dac'}})
    i = r['itens'][1]
    assert i['conduta'] == 'suspender' and i['resumo'] == f'Suspender {dias} dias antes'
    assert i['classe'].endswith('SBC I-B') and 'mantendo o AAS' in i['texto']
    assert faixa in i['divergencia'] and 'Nós optamos por seguir a SBC' in i['divergencia']


def test_ticagrelor_monoterapia_classe_sbc_iib():
    i = item('ticagrelor', sangramento='alto')
    assert i['classe'].endswith('SBC IIb-C')


def test_clopidogrel_monoterapia_por_sangramento():
    assert item('clopidogrel', sangramento='minimo')['conduta'] == 'manter'
    assert item('clopidogrel', sangramento='baixo_moderado')['conduta'] == 'individualizar'
    assert item('clopidogrel', sangramento='alto')['resumo'] == 'Suspender 5 dias antes'
    assert item('prasugrel', sangramento='minimo')['conduta'] == 'individualizar'


def test_des_por_sca_recente_cirurgia_eletiva_adiar():
    ctx = dict(sangramento='alto', urgencia='eletiva', condicoes={'dac', 'stent'},
               stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'meses': 2})
    r = pm.condutas(['aas_acido_acetilsalicilico', 'ticagrelor'], ctx)
    aas, tica = r['itens']
    assert aas['conduta'] == 'manter'
    assert tica['conduta'] == 'individualizar' and 'adiar' in tica['resumo']
    assert tica['classe'] == 'AHA 1 (B-NR) · SBC IIb-B'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Momento da cirurgia após ICP')
    assert '≥12 meses' in aviso['texto'] and 'IIb-B' in aviso['texto']


def test_des_dac_cronica_apos_6_meses_libera_suspensao():
    ctx = dict(sangramento='alto', stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'meses': 8})
    r = pm.condutas(['aas_acido_acetilsalicilico', 'clopidogrel'], ctx)
    assert r['itens'][1]['resumo'] == 'Suspender 5 dias antes'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Momento da cirurgia após ICP')
    assert 'SBC I-A × AHA 2a' in aviso['divergencia']


def test_stent_ate_30_dias_nao_suspende():
    ctx = dict(sangramento='alto', urgencia='eletiva',
               stent={'tipo': 'convencional', 'indicacao': 'dac_cronica', 'meses': 0.5})
    i = pm.condutas(['aas_acido_acetilsalicilico', 'clopidogrel'], ctx)['itens'][1]
    assert i['conduta'] == 'individualizar' and i['classe'] == 'AHA 3: Dano (B-NR) · SBC III-B'


def test_des_menos_de_3_meses_cirurgia_tempo_sensivel_mantem_dapt():
    ctx = dict(sangramento='baixo_moderado', urgencia='tempo_sensivel',
               stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'meses': 2})
    r = pm.condutas(['aas_acido_acetilsalicilico', 'prasugrel'], ctx)
    i = r['itens'][1]
    assert i['conduta'] == 'manter' and i['resumo'] == 'Manter a DAPT' and i['classe'] == 'AHA 1 (B-NR) · SBC IIa-C'
    assert 'tirofiban' in i['divergencia']


def test_angioplastia_so_com_balao_14_dias():
    ctx = dict(sangramento='alto', stent={'tipo': 'balao', 'indicacao': 'dac_cronica', 'meses': 0.3})
    i = pm.condutas(['aas_acido_acetilsalicilico', 'clopidogrel'], ctx)['itens'][1]
    assert i['conduta'] == 'individualizar' and i['classe'] == 'AHA 1 (C-LD)'
    assert '14 dias' in i['texto']


def test_stent_sem_detalhes_pede_os_dados():
    r = pm.condutas(['aas_acido_acetilsalicilico', 'clopidogrel'], {'sangramento': 'alto', 'condicoes': {'stent'}})
    assert r['itens'][1]['conduta'] == 'individualizar'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Momento da cirurgia após ICP')
    assert 'Falta tipo do stent' in aviso['texto']


def test_aco_com_icp_previa_sem_antiagregante():
    t = titulos(['apixabana'], clcr=70, sangramento='alto', condicoes={'stent', 'fa'},
                stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'meses': 24})
    assert 'Anticoagulante oral e ICP prévia' in t
    t2 = titulos(['apixabana', 'clopidogrel'], clcr=70, sangramento='alto', condicoes={'stent', 'fa'},
                 stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'meses': 24})
    assert 'Anticoagulante oral e ICP prévia' not in t2


# --- Corticoide, antirreumáticos, psicotrópicos, hormônios -------------------------------------------------------
def test_corticoide_dose_habitual_com_divergencia_acr():
    i = item('prednisona')
    assert i['conduta'] == 'manter' and 'parenteral' in i['texto'] and 'ACR/AAHKS' in i['divergencia']


def test_antirreumaticos_acr():
    assert item('metotrexato')['conduta'] == 'manter'
    bio = item('adalimumabe')
    assert bio['conduta'] == 'suspender' and '14 dias' in bio['texto'] and 'evidência indireta' in bio['texto']
    assert item('tofacitinibe')['resumo'] == 'Suspender 3 dias antes'
    assert item('micofenolato')['conduta'] == 'individualizar'
    assert pm.condutas(['everolimo', 'natalizumabe'], {})['itens'] == []


def test_psicotropicos_spaqi():
    assert item('sertralina')['conduta'] == 'manter'
    assert item('quetiapina')['conduta'] == 'manter'
    assert item('clonazepam')['conduta'] == 'manter'
    assert '72 h' in item('litio')['resumo']
    assert item('lisdexanfetamina')['conduta'] == 'suspender'
    assert pm.condutas(['metilfenidato'], {})['itens'] == []


def test_hormonios_e_tireoide_spaqi():
    assert 'gestação' in item('anticoncepcional_combinado')['texto']
    assert 'TEV' in item('terapia_hormonal_da_menopausa')['texto']
    assert '7 dias' in item('tamoxifeno')['texto']
    assert item('levotiroxina')['conduta'] == 'manter'
    assert pm.condutas(['anastrozol'], {})['itens'] == []
