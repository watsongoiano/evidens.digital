"""Acompanhamento laboratorial da PVHA (MS 2024 PCDT HIV, Quadros 2, 8, 9 e 10; HIVMA/IDSA 2024, Tabelas 4 e 5)."""
import pytest

from src.utils import hiv as H
from src.utils import periodicidade, tuss
from src.utils.reference_links import build_reference_links

CD4, CV, GENO = 'Contagem de linfócitos T CD4+', 'Carga Viral do HIV (HIV RNA)', 'Genotipagem do HIV (Teste de Resistência)'
PPD, CRAG, HCG = 'Prova tuberculínica (PPD) ou IGRA', 'Antígeno criptocócico (LF-CrAg), soro', 'Beta-hCG, soro'


def _recs(**k):
    base = dict(idade=40, sexo='masculino')
    recs, orient = H.recomendar(**dict(base, **k))
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


def _freq(rec):
    return rec['subtitulo'].split(' | ')[-1]


@pytest.mark.parametrize('cd4, em_tarv, supressao, esperado', [
    (250, True, True, 'A cada 6 meses'), (400, True, True, 'Anual'),
    (650, True, True, 'Não solicitar se >500 em 2 exames consecutivos com intervalo de 6 meses'),
    (650, False, False, 'A cada 6 meses'), (650, True, False, 'A cada 6 meses'), (None, True, True, 'Avaliação inicial')])
def test_cd4_segue_o_quadro_8_do_pcdt(cd4, em_tarv, supressao, esperado):
    recs, _ = _recs(cd4=cd4, em_tarv=em_tarv, supressao_viral=supressao)
    assert _freq(recs[CD4]) == esperado


@pytest.mark.parametrize('em_tarv, supressao, esperado', [
    (True, True, 'A cada 6 meses'), (True, False, 'Após 8 semanas do início ou mudança de TARV'),
    (False, False, 'Antes de iniciar a TARV')])
def test_carga_viral_segue_o_quadro_9_do_pcdt(em_tarv, supressao, esperado):
    recs, _ = _recs(em_tarv=em_tarv, supressao_viral=supressao, carga_viral=0 if supressao else 4000)
    assert _freq(recs[CV]) == esperado


def test_genotipagem_so_na_falha_acima_de_500_ou_nas_indicacoes_pre_tratamento():
    assert GENO in _recs(em_tarv=True, carga_viral=800)[0]
    assert GENO not in _recs(em_tarv=True, carga_viral=300)[0]
    sem_tarv, orient = _recs(em_tarv=False, carga_viral=80000)
    assert GENO not in sem_tarv and 'HIV: genotipagem antes da TARV' in orient
    assert GENO in _recs(idade=30, sexo='feminino', em_tarv=False, gestante=True)[0]


def test_tenofovir_ou_risco_renal_encurtam_creatinina_e_eas():
    for k in (dict(tenofovir=True), dict(risco_renal=True)):
        recs, _ = _recs(**k)
        assert _freq(recs['Creatinina, soro']) == 'A cada 3-6 meses'
        assert _freq(recs['EAS - Elementos Anormais e Sedimentoscopia, urina']) == 'A cada 3-6 meses'
    recs, _ = _recs()
    assert _freq(recs['Creatinina, soro']) == 'Anual'


def test_prova_tuberculinica_so_com_cd4_acima_de_350():
    assert PPD in _recs(cd4=500)[0]
    recs, orient = _recs(cd4=300)
    assert PPD not in recs and 'HIV com CD4 até 350: infecção latente por tuberculose' in orient
    assert 'Radiografia de tórax' in recs


def test_sem_cd4_nem_carga_viral_anteriores_pede_os_dois_e_explica_o_que_depende_do_resultado():
    recs, orient = _recs(em_tarv=True, supressao_viral=True)
    assert _freq(recs[CD4]) == _freq(recs[CV]) == 'Avaliação inicial'
    assert recs[CD4]['descricao'].startswith('Sem CD4 anterior: pedir agora.')
    assert PPD not in recs and CRAG not in recs
    assert 'LF-CrAg' in orient['HIV sem CD4 anterior: o que depende do resultado']['descricao']
    assert 'HIV sem CD4 anterior: o que depende do resultado' not in _recs(cd4=400)[1]


def test_antigeno_criptococico_com_cd4_abaixo_de_200():
    assert CRAG in _recs(cd4=150)[0]
    assert CRAG not in _recs(cd4=200)[0] and CRAG not in _recs()[0]


def test_teste_de_gravidez_antes_da_tarv_em_quem_pode_engravidar():
    assert HCG in _recs(idade=30, sexo='feminino', em_tarv=False)[0]
    assert HCG not in _recs(idade=30, sexo='feminino', em_tarv=True)[0]
    assert HCG not in _recs(idade=30, sexo='feminino', em_tarv=False, gestante=True)[0]
    assert HCG not in _recs(idade=55, sexo='feminino', em_tarv=False)[0]
    assert HCG not in _recs(idade=30, sexo='masculino', em_tarv=False)[0]


def test_coinfeccoes_e_ist_da_avaliacao():
    recs, orient = _recs(sexo='feminino', idade=30)
    for titulo in ('Anticorpos anti-HAV IgG, soro', 'Anticorpos anti-HCV, soro', 'Antígeno HBs, soro',
                   'Anticorpos anti-HBc total, soro', 'Anticorpos anti-HBs, soro', 'Sífilis: teste treponêmico ou VDRL, soro',
                   'Clamídia e gonococo, PCR (urina ou swab)', 'Trichomonas vaginalis, PCR (swab vaginal)',
                   'Toxoplasmose IgG, soro', 'Sorologia para HTLV 1 e 2, soro', 'Sódio, soro', 'Potássio, soro'):
        assert titulo in recs, titulo
    assert 'Trichomonas vaginalis, PCR (swab vaginal)' not in _recs()[0]
    assert 'HIV: rastreio de câncer anal' in orient


def test_toda_periodicidade_classificada_codigo_tuss_e_referencia_com_link():
    for k in (dict(), dict(cd4=150, em_tarv=False), dict(cd4=650, em_tarv=True, supressao_viral=True),
              dict(sexo='feminino', idade=25, em_tarv=False, gestante=True), dict(em_tarv=True, carga_viral=900)):
        recs, orient = H.recomendar(**dict(dict(idade=40, sexo='masculino'), **k))
        for r in recs:
            for _grupo, trechos in periodicidade.indicacoes(r['subtitulo']):
                for t in trechos:
                    assert periodicidade.intervalo_do_trecho(t) is not None or t.lower() in periodicidade.SEM_INTERVALO, t
            assert r['titulo'] in tuss.SEM_CODIGO or tuss.linhas_da_guia(r['titulo'])[0]['codigo'], r['titulo']
        for item in recs + orient:
            links = build_reference_links(item['titulo'], item['referencia'])
            assert links and all(l.get('url') for l in links), item
