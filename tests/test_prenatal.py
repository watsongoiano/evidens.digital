"""Rotina de pré-natal pela idade gestacional (Einstein v.3, MS 2012/2016, Williams 26e)."""
import pytest

from src.utils import prenatal


def _g(**kw):
    base = {'idade_gestacional': '', 'primeira_consulta': 'nao', 'fator_rh': 'desconhecido',
            'toxoplasmose': 'desconhecido', 'gestacao_condicoes': []}
    base.update(kw)
    return prenatal.normalizar(base)


def _titulos(g, idade=30, **kw):
    return [r['titulo'] for r in prenatal.exames(g, idade, **kw)]


def test_primeira_consulta_tem_a_rotina_inicial():
    t = _titulos(_g(idade_gestacional='8', primeira_consulta='sim'))
    for item in ('Hemograma completo', 'Glicemia de jejum, soro', 'Urocultura com antibiograma',
                 'HIV 1/2 (anticorpos e antígeno p24), soro', 'Sífilis: teste treponêmico ou VDRL, soro',
                 'HBsAg, soro', 'Anti-HCV IgG, soro', 'Toxoplasmose IgG e IgM, soro',
                 'Tipagem sanguínea ABO e fator Rh', 'Ultrassonografia obstétrica transvaginal'):
        assert item in t, item
    # próxima janela já sai para deixar pedida
    assert 'Ultrassonografia morfológica de 1º trimestre (translucência nucal)' in t


def test_janela_de_24_semanas():
    t = _titulos(_g(idade_gestacional='24'))
    assert 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro' in t
    assert 'Hemograma completo' in t          # próxima janela (28-36)
    assert 'Ultrassonografia morfológica de 2º trimestre' in t   # 20-24+6
    assert 'Ultrassonografia morfológica de 2º trimestre' not in _titulos(_g(idade_gestacional='25'))


def test_diabetica_nao_faz_totg_e_rh_negativo_faz_coombs():
    t = _titulos(_g(idade_gestacional='25', fator_rh='negativo'), diabetica=True)
    assert not any(x.startswith('TOTG') for x in t)
    assert 'Coombs indireto, soro' in t


def test_toxo_imune_nao_repete():
    assert 'Toxoplasmose IgG e IgM, soro' not in _titulos(_g(idade_gestacional='21', toxoplasmose='imune'))
    assert 'Toxoplasmose IgG e IgM, soro' in _titulos(_g(idade_gestacional='21', toxoplasmose='suscetivel'))


def test_estreptococo_b_no_fim():
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in _titulos(_g(idade_gestacional='36'))
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in _titulos(_g(idade_gestacional='30'))  # próxima
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' not in _titulos(_g(idade_gestacional='22'))


def test_hipertensa_tem_exames_basais_de_pre_eclampsia_e_aas():
    recs = prenatal.exames(_g(idade_gestacional='14'), 42, hipertensa=True)
    upcr = next(r for r in recs if r['titulo'] == 'Relação proteína/creatinina, urina')
    assert 'AAS' in upcr['descricao']


def test_parto_prematuro_previo_antecipa_colo():
    t = _titulos(_g(idade_gestacional='15', gestacao_condicoes=['prematuro_previo']))
    assert 'Ultrassonografia transvaginal para medida do colo uterino' in t


def test_menor_de_25_rastreia_clamidia():
    assert any('Clamídia' in x for x in _titulos(_g(primeira_consulta='sim'), idade=22))
    assert not any('Clamídia' in x for x in _titulos(_g(primeira_consulta='sim'), idade=30))


@pytest.mark.parametrize('campo, valor', [('idade_gestacional', '50'), ('fator_rh', 'x'),
                                          ('toxoplasmose', 'x'), ('gestacao_condicoes', ['outra'])])
def test_entrada_invalida(campo, valor):
    with pytest.raises(prenatal.GestacaoInvalida):
        _g(**{campo: valor})


def test_adiados_na_gestacao():
    recs = [{'titulo': 'Mamografia Digital - Bilateral', 'categoria': 'imagem'},
            {'titulo': 'Colesterol total e frações, soro', 'categoria': 'laboratorio'},
            {'titulo': 'Hemoglobina glicada (HbA1c), soro', 'categoria': 'laboratorio'},
            {'titulo': 'Creatinina, soro', 'categoria': 'laboratorio'}]
    mantidas, adiadas = prenatal.adiar(recs)
    assert [r['titulo'] for r in mantidas] == ['Creatinina, soro']
    assert {a['estado'] for a in adiadas} == {'adiado_gestacao'}
    mantidas, _ = prenatal.adiar(recs, diabetica=True)
    assert 'Hemoglobina glicada (HbA1c), soro' in [r['titulo'] for r in mantidas]


CASO_DA_HOME = {   # gestante 42 a, 24 semanas, hipertensa, ex-tabagista 25 maços-ano, mãe com CCR
    'idade': '42', 'sexo': 'feminino', 'tabagismo': 'ex', 'macos_ano': '25', 'anos_parou_fumar': '3',
    'comorbidades': ['hipertensao'], 'historia_familiar': ['cancer_colorretal'],
    'gestante': 'sim', 'lactante': 'nao', 'imunossupressao': 'nao',
    'idade_gestacional': '24', 'primeira_consulta': 'sim', 'fator_rh': 'desconhecido',
    'toxoplasmose': 'desconhecido',
}


def test_api_gestante_de_24_semanas(client):
    r = client.post('/api/checkup-intelligent', json=CASO_DA_HOME).get_json()
    titulos = [x['titulo'] for x in r['recommendations']]
    assert 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro' in titulos
    assert 'Relação proteína/creatinina, urina' in titulos
    assert 'Mamografia Digital - Bilateral' not in titulos
    assert not any(t.startswith('Colesterol total') for t in titulos)
    adiados = {x['titulo'] for x in r['adiados_gestacao']}
    assert all(x['categoria'] == 'vacina' for x in r['nao_incluidas'])
    assert 'Mamografia Digital - Bilateral' in adiados
    # vacinas de vírus vivo continuam barradas pela triagem
    assert not any('Febre Amarela' in t or 'Tríplice Viral' in t for t in titulos)
    assert r['gestacao']['ig'] == 24


def test_api_recusa_ig_impossivel(client):
    r = client.post('/api/checkup-intelligent', json={**CASO_DA_HOME, 'idade_gestacional': '60'})
    assert r.status_code == 400
    assert r.get_json()['erros'][0]['campo'] == 'idade_gestacional'


def test_nao_gestante_ignora_subcampos(client):
    r = client.post('/api/checkup-intelligent', json={**CASO_DA_HOME, 'gestante': 'nao', 'idade_gestacional': '60'})
    assert r.status_code == 200
    assert r.get_json()['gestacao'] is None
