"""Coerência entre campos: um dado marca o que ele implica (tela e servidor com as mesmas regras)."""
import pytest

from src.utils import coerencia


def _inf(**data):
    return coerencia.inferir(data)


@pytest.mark.parametrize('texto, medicacao, comorbidade', [
    ('Sinvastatina 20 mg à noite', 'estatinas', 'dislipidemia'),
    ('simvastatina 40mg', 'estatinas', 'dislipidemia'),
    ('ROSUVASTATINA 10', 'estatinas', 'dislipidemia'),
    ('Losartana 50 mg 12/12h', 'anti_hipertensivos', 'hipertensao'),
    ('anlodipino 5mg; hidroclorotiazida 25', 'anti_hipertensivos', 'hipertensao'),
])
def test_texto_livre_marca_medicacao_e_comorbidade(texto, medicacao, comorbidade):
    com, med, inf = _inf(medicacoes_continuo=texto)
    assert medicacao in med and comorbidade in com
    assert {i['valor'] for i in inf} == {medicacao, comorbidade}


def test_caixas_de_medicacao_implicam_comorbidade():
    com, _, _ = _inf(medicacoes=['estatinas', 'anti_hipertensivos'])
    assert {'dislipidemia', 'hipertensao'} <= set(com)


@pytest.mark.parametrize('texto', ['ezetimiba 10 mg', 'fenofibrato 200'])
def test_outros_hipolipemiantes_marcam_dislipidemia_sem_marcar_estatina(texto):
    com, med, _ = _inf(medicacoes_continuo=texto)
    assert 'dislipidemia' in com and 'estatinas' not in med


@pytest.mark.parametrize('texto, diabetes', [
    ('insulina NPH 20 UI', True), ('gliclazida MR 60', True), ('sitagliptina 100', True),
    ('metformina 850 2x/dia', False),      # pré-diabetes/SOP: não prova DM
    ('dapagliflozina 10', False),          # IC/DRC
    ('semaglutida 1 mg', False),           # obesidade
])
def test_antidiabeticos(texto, diabetes):
    com, _, _ = _inf(medicacoes_continuo=texto)
    assert ('diabetes' in com) is diabetes


def test_sem_falso_positivo_por_pedaco_de_palavra():
    com, med, inf = _inf(medicacoes_continuo='mora no Brasil; usa cobra-d\'água? não; levotiroxina 50')
    assert inf == [] and med == [] and com == []


def test_hba1c_imc_tfg_e_has_resistente():
    com, _, _ = coerencia.inferir({'hba1c': 6.5, 'peso': 95, 'altura': 170,
                                   'comorbidades': ['has_resistente']}, egfr=52)
    assert {'diabetes', 'obesidade', 'doenca_renal', 'hipertensao'} <= set(com)
    com, _, inf = coerencia.inferir({'hba1c': 6.4, 'peso': 80, 'altura': 170}, egfr=75)
    assert com == [] and inf == []


def test_nao_duplica_o_que_ja_esta_marcado():
    com, med, inf = _inf(comorbidades=['dislipidemia'], medicacoes=['estatinas'], medicacoes_continuo='atorvastatina 40')
    assert com.count('dislipidemia') == 1 and med.count('estatinas') == 1 and inf == []


def test_api_estatina_no_texto_entra_no_prevent_e_volta_nas_inferencias(client):
    base = {'idade': '55', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao',
            'pas': '128', 'colesterol': '200', 'hdl': '45', 'creatinina': '1.0', 'peso': '80', 'altura': '175'}
    sem = client.post('/api/checkup-intelligent', json=base).get_json()
    com = client.post('/api/checkup-intelligent', json={**base, 'medicacoes_continuo': 'Sinvastatina 20 mg'}).get_json()
    assert {i['valor'] for i in com['inferencias']} == {'estatinas', 'dislipidemia'}
    # estatina muda o PREVENT (termo de tratamento)
    assert com['risco_cardiovascular']['dez_anos'] != sem['risco_cardiovascular']['dez_anos']


def test_api_termos_para_a_tela(client):
    termos = client.get('/api/coerencia').get_json()['termos']
    assert termos == coerencia.TERMOS


@pytest.mark.parametrize('pas, pad, categoria, has', [
    (118, 76, 'normal', False), (125, 78, 'elevada', False), (128, 82, 'estagio1', True),
    (134, 70, 'estagio1', True), (138, 92, 'estagio2', True), (150, 85, 'estagio2', True),
])
def test_pa_pela_aha_2025(pas, pad, categoria, has):
    assert coerencia.classificar_pa(pas, pad)['categoria'] == categoria
    com, _, inf = coerencia.inferir({'pas': pas, 'pad': pad})
    assert ('hipertensao' in com) is has
    if has:
        assert 'MRPA ou MAPA' in inf[0]['motivo']


def test_pa_na_gestacao_usa_140_90():
    assert 'hipertensao' not in coerencia.inferir({'pas': 134, 'pad': 84}, gestante=True)[0]
    assert 'hipertensao' in coerencia.inferir({'pas': 142, 'pad': 84}, gestante=True)[0]


def test_api_devolve_classificacao_da_pa_e_pede_mapa(client):
    corpo = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao', 'pas': '132', 'pad': '78'}
    r = client.post('/api/checkup-intelligent', json=corpo).get_json()
    assert r['pa_classificacao']['categoria'] == 'estagio1'
    assert any(t['titulo'].startswith('MAPA') for t in r['recommendations'])


@pytest.mark.parametrize('pas, pad, categoria', [
    (118, None, 'incompleta'), (None, 76, 'incompleta'),
    (134, None, 'estagio1'), (None, 84, 'estagio1'),
    (145, None, 'estagio2'), (None, 95, 'estagio2'),
])
def test_pa_com_um_componente_so_classifica_o_que_e_certo(pas, pad, categoria):
    c = coerencia.classificar_pa(pas, pad)
    assert c['categoria'] == categoria
    if categoria != 'estagio2':
        assert c.get('incompleta') is True
