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
    conduta = {i['chave']: i['conduta'] for i in r['itens']}
    assert conduta.pop('aas_acido_acetilsalicilico') == 'manter'      # AAS com P2Y12 (DAPT) é prevenção secundária
    assert set(conduta.values()) == {'individualizar'}


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
# --- Antidiabéticos: SBD/SBA/ABESO 2026 (R4–R15, Tabela 2), nota da SBA 2026 (aGLP-1) e AHA §7.8 ---------------
SBD = 'https://doi.org/10.1186/s13098-025-02060-5'


def _urls(i):
    return {r['url'] for r in i['referencias']}


@pytest.mark.parametrize('chave', ['empagliflozina', 'dapagliflozina', 'canagliflozina'])
def test_isglt2_suspende_3_dias_com_divergencia_sbd(chave):
    i = item(chave, condicoes={'ic'})
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 3 dias antes'
    assert i['classe'] == 'AHA 1 (C-LD) · SBD/SBA/ABESO I-B' and 'D-4' in i['texto']
    assert 'SBD' in i['divergencia'] and 'SBC' in i['divergencia'] and 'Nós optamos por seguir a AHA' in i['divergencia']
    assert SBD in _urls(i)


def test_isglt2_na_emergencia_pede_cetonemia():
    i = item('empagliflozina', urgencia='emergencia')
    assert 'cetonemia' in i['resumo'] and 'ânion gap' in i['texto']


def test_ertugliflozina_4_dias(monkeypatch):
    monkeypatch.setitem(MEDICAMENTOS, 'ertugliflozina', {'rotulo': 'Ertugliflozina', 'grupo': 'Antidiabéticos',
                                                         'classes': ['isglt2'], 'busca': 'ertugliflozina'})
    i = item('ertugliflozina')
    assert i['resumo'] == 'Suspender 4 dias antes' and 'D-5' in i['texto']


def test_associacoes_com_isglt2_seguem_o_isglt2():
    i = item('dapagliflozina_metformina')
    assert i['resumo'] == 'Suspender 3 dias antes' and 'metformina' in i['texto']
    assert item('empagliflozina_linagliptina')['resumo'] == 'Suspender 3 dias antes'


def test_metformina_nao_tomada_no_dia_com_divergencia_aha():
    i = item('metformina')
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Tomar até a véspera; não tomar no dia'
    assert 'IIa-B' in i['classe'] and 'AHA' in i['divergencia'] and 'Nós optamos por seguir a SBD/SBA/ABESO' in i['divergencia']
    assert SBD in _urls(i)


def test_metformina_usa_a_tfg_e_nao_o_clcr():
    # O limite é de TFG (CKD-EPI, mL/min/1,73 m²); ClCr baixo com TFG ≥ 30 não suspende.
    i = item('metformina', clcr=22.0, tfg=25)
    assert i['conduta'] == 'suspender' and 'TFG < 30' in i['resumo'] and 'KDIGO' in i['classe']
    assert 'TFG < 30' not in item('metformina', clcr=22.0, tfg=38)['resumo']
    assert '1.000 mg/dia' in item('metformina', tfg=38)['texto']
    assert 'confira a TFG' in item('metformina')['texto']


@pytest.mark.parametrize('chave', ['glibenclamida', 'gliclazida', 'glimepirida'])
def test_sulfonilureia_suspensa_24_h_antes(chave):
    i = item(chave)
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 24 h antes'
    assert i['classe'] == 'SBD/SBA/ABESO I-C' and 'hipoglicemia' in i['texto'] and 'SPAQI' in i['divergencia']


@pytest.mark.parametrize('chave', ['sitagliptina', 'vildagliptina', 'linagliptina', 'alogliptina'])
def test_idpp4_mantido(chave):
    i = item(chave)
    assert i['conduta'] == 'manter' and i['classe'] == 'SBD/SBA/ABESO I-A' and 'SPAQI' in i['divergencia']


def test_saxagliptina_com_ic_discute_troca():
    assert item('saxagliptina')['conduta'] == 'manter'
    i = item('saxagliptina', condicoes={'ic'})
    assert i['conduta'] == 'individualizar' and 'IC' in i['texto']


def test_pioglitazona_e_acarbose():
    assert item('pioglitazona')['conduta'] == 'manter'
    assert item('pioglitazona', condicoes={'ic'})['conduta'] == 'individualizar'
    i = item('acarbose')
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender no dia da cirurgia'


def test_idpp4_mais_metformina_segue_a_metformina():
    i = item('sitagliptina_metformina')
    assert i['resumo'] == 'Tomar até a véspera; não tomar no dia' and 'AHA' in i['divergencia']


@pytest.mark.parametrize('chave', ['semaglutida', 'dulaglutida', 'tirzepatida'])
def test_aglp1_de_longa_acao(chave):
    i = item(chave)
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Suspender 7 dias antes; dieta líquida nas 24 h antes'
    assert 'jejum de 8 a 12 h' in i['texto'] and 'POCUS' in i['texto'] and '12 semanas' in i['texto']
    assert 'multissocietária' in i['divergencia'] and 'SBA de 2026' in i['divergencia']
    assert any('C.SBA-01744/2026' in r['label'] for r in i['referencias'])


def test_aglp1_de_curta_acao():
    i = item('liraglutida')
    assert i['resumo'] == 'Suspender 1 dia antes; dieta líquida nas 24 h antes' and 'véspera' in i['divergencia']


def test_insulinas():
    basal = item('insulina_glargina')
    assert basal['conduta'] == 'ajustar' and '70–80%' in basal['resumo'] and 'nunca omitir' in basal['texto']
    deg = item('insulina_degludeca')
    assert deg['conduta'] == 'ajustar' and '72 h' in deg['resumo']
    nph = item('insulina_nph')
    assert nph['conduta'] == 'ajustar' and '50%' in nph['resumo']
    for chave in ('insulina_lispro', 'insulina_regular'):
        assert item(chave)['conduta'] == 'suspender'
    combo = item('insulina_degludeca_liraglutida')
    assert combo['conduta'] == 'individualizar' and 'aGLP-1' in combo['texto'] and '1 dia' in combo['texto']
    assert pm.condutas(['insulina_icodeca'], {})['itens'] == []


def test_aviso_de_hba1c_com_antidiabetico():
    assert 'HbA1c e glicemia pré-operatórias' in titulos(['metformina'])
    assert 'HbA1c e glicemia pré-operatórias' not in titulos(['atenolol'])
    a = [x for x in avisos(['metformina']) if x['titulo'] == 'HbA1c e glicemia pré-operatórias'][0]
    assert '8%' in a['texto'] and '250 mg/dL' in a['texto'] and SBD in {r['url'] for r in a['referencias']}


# --- DOAC: fármaco × ClCr × sangramento (AHA Tabela 13; SBC Quadro 26) --------------------------------------------
@pytest.mark.parametrize('chave, clcr, sangramento, resumo, sbc', [
    ('apixabana', 80, 'baixo_moderado', 'Sem dose do D-1 ao D0 (última no D-2); reiniciar no D+1',
     'suspender 24 h antes e reintroduzir 24 h depois'),
    ('apixabana', 80, 'alto', 'Sem dose do D-2 ao D+2 (última no D-3); reiniciar no D+3',
     'suspender pelo menos 48 h antes e reintroduzir 48 h depois'),
    ('rivaroxabana', 25, 'baixo_moderado', 'Sem dose do D-2 ao D0 (última no D-3); reiniciar no D+1',
     'suspender pelo menos 48 h antes'),
    ('rivaroxabana', 25, 'alto', 'Sem dose do D-3 ao D+2 (última no D-4); reiniciar no D+3',
     'suspender pelo menos 48 h antes'),
    ('rivaroxabana', 90, 'baixo_moderado', 'Sem dose do D-1 ao D0 (última no D-2); reiniciar no D+1',
     'suspender 24 h antes'),
    ('edoxabana', 60, 'alto', 'Sem dose do D-2 ao D+2 (última no D-3); reiniciar no D+3', 'suspender 48–72 h antes'),
    ('dabigatrana', 60, 'baixo_moderado', 'Sem dose do D-1 ao D0 (última no D-2); reiniciar no D+1',
     'suspender 24 h antes e reintroduzir 24 h depois'),
    ('dabigatrana', 60, 'alto', 'Sem dose do D-2 ao D+2 (última no D-3); reiniciar no D+3',
     'suspender 48 h antes e reintroduzir 48 h depois'),
    ('dabigatrana', 45, 'baixo_moderado', 'Sem dose do D-2 ao D0 (última no D-3); reiniciar no D+1',
     'suspender 48 h antes e reintroduzir 24 h depois'),
    ('dabigatrana', 40, 'alto', 'Sem dose do D-4 ao D+2 (última no D-5); reiniciar no D+3',
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
    assert i['resumo'] == 'Sem dose do D-4 ao D+2 (última no D-5); reiniciar no D+3'
    assert '≥24 h após a punção ou a retirada do cateter' in i['texto'] and 'ASRA' in i['divergencia']
    r = pm.condutas(['dabigatrana'], {'clcr': 40, 'sangramento': 'alto', 'neuraxial': True})
    assert r['itens'][0]['resumo'] == 'Sem dose do D-6 ao D+2 (última no D-7); reiniciar no D+3'
    aviso = next(a for a in r['avisos'] if a['titulo'] == 'Anestesia neuroaxial e anticoagulantes')
    assert '≥5 meias-vidas' in aviso['texto']
    assert item('apixabana', clcr=70, sangramento='minimo', neuraxial=True)['resumo'].startswith('Sem dose do D-3 ao D+2 (última no D-4)')


def test_aceita_a_grafia_neuroaxial():
    r = pm.condutas(['apixabana'], {'clcr': 70, 'sangramento': 'baixo_moderado', 'neuroaxial': True})
    # Anti-Xa com neuroaxial: ≥ 3 dias sem dose (72 h)
    assert r['itens'][0]['resumo'] == 'Sem dose do D-3 ao D+2 (última no D-4); reiniciar no D+3'
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


# --- Enoxaparina pela dose e DOAC (pedido do responsável clínico: dose plena ou profilática) --------------------------
# Fontes: ACCP 2022 conforme a revisão de Douketis e Spyropoulos (NEJM Evidence 2023;2(6), doi 10.1056/EVIDra2200322,
# Figuras 1 e 2 e texto), SBC 2024 (Quadro 25 e texto do 4.3.2.6) e AHA/ACC (Tabela 13). Os intervalos da dose plena
# estão na nota da Figura 1, sobre a HBPM usada como ponte na interrupção da varfarina: o uso contínuo é uma extensão,
# e o item tem de dizer isso. A dose baixa depois do procedimento vem da mesma nota (ponte) e da Figura 2 (após a
# interrupção de DOAC, no alto risco de tromboembolismo venoso, nas primeiras 48 a 72 h).
NEUROAXIAL_DA_HBPM = 'Na anestesia neuroaxial (ASRA): punção ≥24 h após dose plena e ≥12 h após dose profilática.'
DOSE_DO_DOAC = 'AHA/ACC e SBC não diferenciam o intervalo pela dose (plena ou reduzida) do DOAC.'
URL_ACCP = 'https://doi.org/10.1056/EVIDra2200322'
DIVERGENCIA_NEUTRA = ('As duas redações são compatíveis no horário (a manhã da véspera fica a cerca de 24 h da cirurgia); a '
                      'diferença é a meia dose da véspera, descrita só pela ACCP.')
DOACS = ('apixabana', 'rivaroxabana', 'edoxabana', 'dabigatrana')
DOSE_BAIXA_DEPOIS = ('Dose baixa depois da cirurgia: a ACCP 2022 a descreve na ponte da varfarina (enoxaparina 40 mg/dia nas '
                     'primeiras 24 a 72 h após cirurgia de sangramento alto, até voltar a dose plena) e, após a interrupção '
                     'de DOAC, em pacientes selecionados de alto risco de tromboembolismo venoso (anticoagulante em dose '
                     'baixa nas primeiras 48 a 72 h após o procedimento). A SBC 2024 (texto do 4.3.2.6, na seção dos '
                     'anticoagulantes orais diretos) aconselha iniciar a HBPM profilática 12 h após o procedimento, se '
                     'adequada hemostasia, em pacientes ou procedimentos de alto risco de tromboembolismo venoso, e '
                     'suspendê-la ao reintroduzir o anticoagulante oral.')
# Revisão de Douketis, p. 4: sem ponte pós-operatória com hemostasia cirúrgica inadequada; em cirurgias selecionadas de
# sangramento alto (cardíaca, intracraniana) a dose plena pode ficar impedida, e a dose baixa pode ser dada por 3 a 5 dias
HEMOSTASIA_INADEQUADA = 'Com hemostasia cirúrgica inadequada, a ACCP 2022 aconselha evitar a ponte pós-operatória.'
EXCECAO_SANGRAMENTO_ALTO = ('Exceção no sangramento alto (ACCP 2022): em cirurgias selecionadas (por exemplo, cardíaca ou '
                            'intracraniana), os riscos e as consequências do sangramento podem impedir a dose plena depois '
                            'da cirurgia; nesses pacientes, a HBPM em dose profilática (baixa) pode ser dada por 3 a 5 '
                            'dias, enquanto a varfarina é retomada.')


def _referencias_com_link(i):
    assert i['referencias'] and all(r['label'] and r['url'].startswith('https://') for r in i['referencias']), i
    return {r['label']: r['url'] for r in i['referencias']}


def test_enoxaparina_dose_plena_mostra_a_accp_e_a_sbc_como_extrapolacao_da_ponte():
    i = item('enoxaparina', dose_heparina='plena', urgencia='eletiva', sangramento='alto')
    assert i['conduta'] == 'suspender'
    assert i['resumo'] == 'Dose plena: última dose na manhã da véspera, com metade da dose diária'
    t = i['texto']
    # antes: ACCP 2022 (manhã da véspera, meia dose) e SBC (24 h antes, IIa-C), cada uma com o seu nome
    assert ('ACCP 2022, dose plena (enoxaparina 1 mg/kg de 12/12 h ou 1,5 mg/kg/dia): última dose na manhã da véspera '
            '(D-1), com metade da dose diária total.') in t
    # depois: retorno da dose plena
    assert ('Retorno da dose plena (ACCP 2022), com hemostasia adequada: cerca de 24 h após cirurgia de sangramento baixo '
            'ou moderado; 48 a 72 h após sangramento alto.') in t
    # condição de hemostasia e exceção do sangramento alto (p. 4 da revisão), antes da frase da extrapolação
    assert HEMOSTASIA_INADEQUADA in t and EXCECAO_SANGRAMENTO_ALTO in t
    assert (t.index('Retorno da dose plena') < t.index(HEMOSTASIA_INADEQUADA) < t.index(EXCECAO_SANGRAMENTO_ALTO)
            < t.index('São os intervalos que a ACCP 2022 define'))
    # honestidade com a fonte: ACCP e SBC definem esses intervalos para a HBPM na ponte; o uso contínuo é extensão
    assert ('São os intervalos que a ACCP 2022 define para a HBPM na ponte da varfarina, aqui estendidos ao uso '
            'contínuo.') in t
    assert ('SBC 2024 (Quadro 25, IIa-C): última dose 24 h antes, intervalo que a SBC define para a HBPM na ponte, aqui '
            'estendido ao uso contínuo.') in t
    assert t.index('Retorno da dose plena') < t.index('São os intervalos que a ACCP 2022 define') < t.index('SBC 2024 (Quadro 25')
    # dose baixa depois da cirurgia: só os dois contextos em que a ACCP a descreve, e o que a SBC diz
    assert DOSE_BAIXA_DEPOIS in t and 'pode ser usada' not in t
    assert t.endswith(DOSE_BAIXA_DEPOIS + ' ' + NEUROAXIAL_DA_HBPM)   # a frase do neuroeixo fica como estava
    assert 'Informe se a dose' not in t
    assert i['classe'] == 'ACCP 2022 (extrapolado da ponte) · SBC IIa-C (extrapolado da ponte) · ASRA 2025'
    refs = _referencias_com_link(i)
    assert refs['ACCP 2022, antitrombóticos no perioperatório (resumo em NEJM Evidence 2023;2(6))'] == URL_ACCP
    assert 'SBC 2024, Quadro 25 e texto do 4.3.2.6' in refs and any(r.startswith('ASRA 2025') for r in refs)
    # ACCP e SBC escrevem a última dose de modo diferente: o aviso mostra as duas, diz que o horário é compatível e
    # que a diferença é a meia dose da véspera; não declara escolha entre as sociedades
    assert i['divergencia'] == ('ACCP 2022: última dose plena na manhã da véspera (D-1), com metade da dose diária total. '
                                'SBC 2024 (IIa-C): última dose 24 h antes. ' + DIVERGENCIA_NEUTRA)
    assert 'optamos' not in i['divergencia'] and 'seguir' not in i['divergencia']


def test_enoxaparina_dose_profilatica_diz_que_as_fontes_nao_fixam_o_intervalo():
    i = item('enoxaparina', dose_heparina='profilatica', urgencia='eletiva', sangramento='alto')
    assert i['conduta'] == 'individualizar'
    assert i['resumo'] == 'Dose profilática: horário da última dose combinado com a equipe'
    t = i['texto']
    assert 'ACCP 2022, SBC 2024 e AHA/ACC não fixam o intervalo entre a última dose e a cirurgia' in t
    # depois da cirurgia: a mesma ressalva da dose plena (ponte; após DOAC, alto risco de TEV nas primeiras 48 a 72 h)
    assert DOSE_BAIXA_DEPOIS in t and 'pode ser usada' not in t
    assert '≥12 h após dose profilática' in t and t.endswith(DOSE_BAIXA_DEPOIS + ' ' + NEUROAXIAL_DA_HBPM)
    # nada do esquema da dose plena: nem "manhã da véspera", nem "24 h antes", nem divergência
    assert 'manhã da véspera' not in t and '24 h antes' not in t and 'metade da dose' not in t
    assert i['divergencia'] == '' and i['classe'] == 'Intervalo não fixado nas fontes · ASRA 2025'
    refs = _referencias_com_link(i)
    assert refs['ACCP 2022, antitrombóticos no perioperatório (resumo em NEJM Evidence 2023;2(6))'] == URL_ACCP
    assert 'SBC 2024, Quadro 25 e texto do 4.3.2.6' in refs and 'AHA/ACC 2026, Tabela 13' in refs
    assert any(r.startswith('ASRA 2025') for r in refs)


def test_enoxaparina_dose_plena_no_sangramento_minimo_nao_aplica_o_esquema_da_ponte():
    # Tabela 1 da revisão, nota §: procedimento de sangramento mínimo pode ser feito sob anticoagulação plena; a Figura 1
    # não tem HBPM na linha de sangramento mínimo. O item não manda suspender nem manter: diz o que a fonte não descreve.
    for urgencia in (None, 'eletiva', 'tempo_sensivel'):
        ctx = dict(dose_heparina='plena', sangramento='minimo')
        if urgencia:
            ctx['urgencia'] = urgencia
        i = item('enoxaparina', **ctx)
        assert i['conduta'] == 'individualizar'
        assert i['resumo'] == 'Dose plena e sangramento mínimo: conduta individualizada'
        assert i['texto'] == ('Sangramento mínimo: a ACCP 2022 (Tabela 1 da revisão) diz que o procedimento pode ser feito '
                              'com segurança sob anticoagulação em dose plena, mas não descreve o manejo da HBPM em dose '
                              'plena nesse cenário: a Figura 1 traz só a varfarina na linha de sangramento mínimo. O esquema '
                              'da ponte não se aplica a este cenário. A conduta é individualizada.')
        tudo = i['resumo'] + ' ' + i['texto'] + ' ' + i['divergencia']
        for proibido in ('véspera', 'metade da dose', '24 h', 'D-1', 'Retorno', 'suspender', 'Suspender', 'manter',
                         'Manter', 'SBC'):
            assert proibido not in tudo, proibido
        assert i['classe'] == 'ACCP 2022: manejo não descrito' and i['divergencia'] == ''
        assert list(_referencias_com_link(i).values()) == [URL_ACCP]
    # a anestesia neuroaxial conta como sangramento alto: volta o esquema da dose plena
    neuro = item('enoxaparina', dose_heparina='plena', sangramento='minimo', neuraxial=True)
    assert neuro['conduta'] == 'suspender' and 'manhã da véspera' in neuro['resumo']
    # os demais riscos de sangramento seguem com o esquema da ponte
    for sangramento in (None, 'baixo_moderado', 'alto'):
        assert item('enoxaparina', dose_heparina='plena', sangramento=sangramento)['conduta'] == 'suspender'
    # a dose profilática não muda com o sangramento mínimo
    assert (item('enoxaparina', dose_heparina='profilatica', sangramento='minimo')
            == item('enoxaparina', dose_heparina='profilatica', sangramento='alto'))


@pytest.mark.parametrize('dose', [None, '', 'x', 'PLENA', 'terapeutica', ['plena'], 1, True],
                         ids=['ausente', 'vazia', 'x', 'maiusculas', 'terapeutica', 'lista', 'numero', 'booleano'])
def test_enoxaparina_dose_nao_informada_ou_invalida_pede_a_dose(dose):
    ctx = {} if dose is None else {'dose_heparina': dose}
    i = pm.condutas(['enoxaparina'], ctx)['itens'][0]
    assert i == item('enoxaparina')                           # valor inválido conta como dose não informada
    assert i['conduta'] == 'suspender' and i['resumo'] == 'Dose plena: última dose 24 h antes'
    assert i['texto'] == ('Informe se a dose é plena ou profilática. Em dose plena, última aplicação 24 h antes e '
                          'retorno ≥24 h depois (48–72 h se sangramento alto), com hemostasia: intervalos que a SBC '
                          'define para a HBPM na ponte, aqui estendidos ao uso contínuo. ' + NEUROAXIAL_DA_HBPM)
    assert i['classe'] == 'SBC IIa-C (extrapolado da ponte) · ASRA 2025' and i['divergencia'] == ''
    assert list(_referencias_com_link(i)) == ['SBC 2024, Quadro 25',
                                              'ASRA 2025 (5ª ed.), anestesia regional e antitrombóticos (Reg Anesth Pain Med)']


@pytest.mark.parametrize('urgencia', ['urgencia', 'emergencia'])
def test_enoxaparina_na_urgencia_nao_muda_com_a_dose(urgencia):
    sem = item('enoxaparina', urgencia=urgencia)
    assert sem['resumo'] == 'Urgência: informar a hora da última dose' and 'Informe se a dose' not in sem['texto']
    for dose in ('plena', 'profilatica', 'x'):
        assert item('enoxaparina', urgencia=urgencia, dose_heparina=dose) == sem


def test_referencia_da_accp_esta_no_dicionario_do_modulo():
    assert pm.REFERENCIAS['accp'] == {
        'label': 'ACCP 2022, antitrombóticos no perioperatório (resumo em NEJM Evidence 2023;2(6))', 'url': URL_ACCP}
    assert [k for k, r in pm.REFERENCIAS.items() if 'ACCP' in r['label'] or 'CHEST' in r['label']] == ['accp']


@pytest.mark.parametrize('chave', DOACS)
@pytest.mark.parametrize('urgencia', [None, 'eletiva', 'tempo_sensivel'])
def test_doac_na_cirurgia_eletiva_diz_que_a_dose_nao_muda_o_intervalo(chave, urgencia):
    ctx = dict(clcr=60.0, sangramento='alto', condicoes={'fa'})
    if urgencia:
        ctx['urgencia'] = urgencia
    i = item(chave, **ctx)
    assert i['conduta'] == 'suspender' and i['texto'].endswith(' ' + DOSE_DO_DOAC) and i['texto'].count(DOSE_DO_DOAC) == 1
    # só o texto muda: resumo e dias são os da Tabela 13 (os mesmos de test_matriz_doac)
    assert i['resumo'] == 'Sem dose do D-2 ao D+2 (última no D-3); reiniciar no D+3'
    assert 'com a última dose no D-3 e o reinício no D+3' in i['texto']
    # a dose da enoxaparina não interfere no item do DOAC
    assert item(chave, dose_heparina='profilatica', **ctx) == i
    assert 'não muda este intervalo' not in i['texto'] and 'diretrizes usadas aqui' not in i['texto']
    # sem o ClCr o item ainda mostra os intervalos, e a frase vem junto
    j = item(chave, **{k: v for k, v in ctx.items() if k != 'clcr'})
    assert j['resumo'] == 'Depende do ClCr' and j['texto'].endswith(' ' + DOSE_DO_DOAC)
    # sem o risco de sangramento o item não mostra intervalo nenhum: a frase não aparece
    j = item(chave, **{k: v for k, v in ctx.items() if k != 'sangramento'})
    assert j['resumo'] == 'Depende do risco de sangramento' and 'D-' not in j['texto']
    assert 'DOAC' not in j['texto'] and 'intervalo' not in j['texto']


@pytest.mark.parametrize('chave', DOACS)
def test_doac_sem_a_frase_da_dose_onde_ela_nao_se_aplica(chave):
    base = dict(clcr=60.0, sangramento='alto', condicoes={'fa'})
    fora = [dict(base, urgencia='urgencia'), dict(base, urgencia='emergencia'),      # reversão, não intervalo
            dict(base, sangramento='minimo'),                                        # não interrompe
            dict(base, condicoes={'protese_mecanica'}),                              # DOAC contraindicado
            dict(base, condicoes={'fa', 'protese_mecanica_mitral'}),
            dict(base, neuraxial=True), dict(base, neuroaxial=True, clcr=25.0)]      # o item cita a ASRA, que separa as doses
    for ctx in fora:
        assert 'do DOAC' not in item(chave, **ctx)['texto'], ctx


@pytest.mark.parametrize('chave', ['varfarina', 'enoxaparina'])
def test_varfarina_e_enoxaparina_nao_levam_a_frase_do_doac(chave):
    for dose in ('', 'plena', 'profilatica'):
        for urgencia in ('eletiva', 'tempo_sensivel', 'urgencia'):
            for sangramento in (None, 'minimo', 'baixo_moderado', 'alto'):
                i = item(chave, dose_heparina=dose, urgencia=urgencia, sangramento=sangramento, clcr=60.0,
                         condicoes={'fa'}, idade=70, sexo='feminino')
                assert 'do DOAC.' not in i['texto'] + i['divergencia'], (dose, urgencia, sangramento)


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
    assert tica['conduta'] == 'individualizar' and tica['resumo'].startswith('Adiar a eletiva')
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


def test_referencia_da_aha_abre_o_texto_integral_na_tabela_13():
    """Pedido do responsável clínico (18/11/2026): a referência leva ao ponto exato da diretriz, não ao endereço
    geral. A Tabela 13 abre pelo título dela, copiado da diretriz (fragmento de texto)."""
    from urllib.parse import unquote
    for med in ('rivaroxabana', 'dabigatrana', 'varfarina'):
        refs = item(med, clcr=80, sangramento="alto", condicoes={"fa"}, urgencia="eletiva", idade=70)["referencias"]
        da_tabela = [r for r in refs if 'Tabela' in r['label'] and '13' in r['label']]
        assert da_tabela, (med, [r['label'] for r in refs])
        url = da_tabela[0]['url']
        assert url.startswith('https://www.ahajournals.org/doi/10.1161/CIR.0000000000001285#:~:text='), url
        assert unquote(url.split('#:~:text=')[1]) == ('Perioperative Management of Direct Oral Anticoagulants and '
                                                      'Vitamin K Antagonists')
        assert ' ' not in url
    # Lugar sem título conhecido continua no endereço geral da diretriz.
    assert pm._aha('§7.6 (texto) e Tabela 15')[0]['url'] == pm._URL_AHA


def test_enoxaparina_sem_dose_no_sangramento_minimo_nao_aplica_o_esquema_da_ponte():
    # Mesmo motivo da dose plena: sem a dose informada, o item não pode mandar suspender 24 h antes no sangramento mínimo.
    i = item('enoxaparina', sangramento='minimo')
    assert i['conduta'] == 'individualizar' and i['resumo'].startswith('Informe a dose')
    assert '24 h antes' not in i['texto'] and 'não se aplica' in i['texto']
    assert item('enoxaparina', sangramento='alto')['conduta'] == 'suspender'      # fora do mínimo, nada muda
