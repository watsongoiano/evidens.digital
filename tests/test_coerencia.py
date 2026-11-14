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
    ('metformina 850 2x/dia', False),      # pré-diabetes, resistência insulínica, SOP
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
    assert {'obesidade', 'doenca_renal', 'hipertensao'} <= set(com)
    assert not {'diabetes', 'diabetes_tipo_1'} & set(com)   # HbA1c ≥ 6,5% não diz o tipo: nenhuma caixa de diabetes
    com, _, inf = coerencia.inferir({'hba1c': 5.6, 'peso': 80, 'altura': 170}, egfr=75)
    assert com == [] and inf == []


def test_hba1c_na_faixa_de_pre_diabetes_marca_pre_diabetes():
    for valor in (5.7, 6.0, 6.4):
        com, _, inf = coerencia.inferir({'hba1c': valor})
        assert com == ['pre_diabetes'] and inf[0]['rotulo'] == 'Pré-diabetes' and '5,7 a 6,4%' in inf[0]['motivo']
    # no diabético (marcado, ou reconhecido pela medicação), 6,0% é bom controle, não pré-diabetes
    assert coerencia.inferir({'hba1c': 6.0, 'comorbidades': ['diabetes']})[0] == ['diabetes']
    com, _, _ = coerencia.inferir({'hba1c': 6.0, 'medicacoes': ['sulfonilureia']})
    assert 'diabetes' in com and 'pre_diabetes' not in com
    # insulina indica diabetes, mas não o tipo: nem tipo 2, nem pré-diabetes
    assert coerencia.inferir({'hba1c': 6.0, 'medicacoes': ['insulina']})[0] == []
    # quem desmarcou a caixa na tela fica com a decisão
    assert coerencia.inferir({'hba1c': 6.0}, recusados=['pre_diabetes'])[0] == []


def test_medicamento_que_so_se_usa_numa_doenca_marca_a_doenca():
    from src.utils import medicamentos
    esperado = {'sacubitril_valsartana': 'insuficiencia_cardiaca', 'levotiroxina': 'hipotireoidismo',
                'metimazol_tiamazol': 'hipertireoidismo', 'propiltiouracila': 'hipertireoidismo',
                'levodopa_benserazida': 'parkinson', 'levodopa_carbidopa': 'parkinson', 'donepezila': 'demencia',
                'levetiracetam': 'epilepsia', 'alendronato': 'osteoporose', 'tansulosina': 'hpb',
                'umeclidinio_vilanterol': 'dpoc', 'ticagrelor': 'dcv_aterosclerotica',
                'tenofovir_lamivudina_dolutegravir': 'hiv', 'adalimumabe': 'doenca_autoimune'}
    for medicamento, doenca in esperado.items():
        com, _, inf = coerencia.inferir({}, escolhidas=[medicamento])
        assert com == [doenca], medicamento
        assert inf[0]['motivo'].startswith('uso de ') and inf[0]['rotulo'] == coerencia.rotulo_de(doenca)
    # todo alvo é uma comorbidade que a tela conhece (caixa fixa ou item da lista)
    for alvos in medicamentos.MARCA.values():
        for alvo in alvos:
            assert coerencia.rotulo_de(alvo)
    # os que têm outra indicação comum não marcam nada sozinhos
    for medicamento in ('metotrexato', 'pramipexol', 'alopurinol', 'clopidogrel', 'tenofovir_entricitabina', 'pregabalina'):
        assert coerencia.inferir({}, escolhidas=[medicamento])[0] == [], medicamento
    # desmarcar na tela vale
    assert coerencia.inferir({}, escolhidas=['levotiroxina'], recusados=['hipotireoidismo'])[0] == []


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


def test_betabloqueador_de_ic_conta_como_tratamento_so_com_hipertensao():
    """Carvedilol isolado não marca hipertensão (IC, FA); com hipertensão, vale como anti-hipertensivo no PREVENT."""
    from src.utils import coerencia, medicamentos
    classes = medicamentos.classes_de(['carvedilol'])
    com, med, _ = coerencia.inferir({'comorbidades': [], 'medicacoes': list(classes)})
    assert 'hipertensao' not in com and 'anti_hipertensivos' not in med
    com, med, inf = coerencia.inferir({'comorbidades': ['hipertensao'], 'medicacoes': list(classes)})
    assert 'anti_hipertensivos' in med
    assert any(i['valor'] == 'anti_hipertensivos' for i in inf)


@pytest.mark.parametrize('remedio, caixa', [
    ('atenolol', 'hipertensao'), ('metoprolol', 'hipertensao'), ('nebivolol', 'hipertensao'), ('losartana', 'hipertensao'),
    ('hidroclorotiazida', 'hipertensao'), ('anlodipino', 'hipertensao'), ('clonidina', 'hipertensao'),
    ('glibenclamida', 'diabetes'), ('sitagliptina', 'diabetes'), ('sitagliptina_metformina', 'diabetes'),
    ('sinvastatina', 'dislipidemia'), ('ezetimiba', 'dislipidemia'),
])
def test_medicacao_marca_a_comorbidade_que_implica(remedio, caixa):
    from src.utils import coerencia, medicamentos
    com, _, inf = coerencia.inferir({'comorbidades': [], 'medicacoes': medicamentos.classes_de([remedio])})
    assert caixa in com, (remedio, com)


@pytest.mark.parametrize('remedio, caixa', [
    ('carvedilol', 'hipertensao'), ('bisoprolol', 'hipertensao'), ('propranolol', 'hipertensao'),
    ('espironolactona', 'hipertensao'), ('furosemida', 'hipertensao'), ('sacubitril_valsartana', 'hipertensao'),
    ('empagliflozina', 'diabetes'), ('dapagliflozina', 'diabetes'), ('semaglutida', 'diabetes'), ('tirzepatida', 'diabetes'),
])
def test_medicacao_com_outras_indicacoes_nao_marca_sozinha_mas_a_tela_avisa(remedio, caixa, client):
    from src.utils import coerencia, medicamentos
    com, _, _ = coerencia.inferir({'comorbidades': [], 'medicacoes': medicamentos.classes_de([remedio])})
    assert caixa not in com
    pagina = client.get('/intelligent-tools').get_data(as_text=True)
    import re
    item = re.search(r'data-valor="%s"[^>]*>' % remedio, pagina).group(0)
    assert f'data-talvez="{caixa}"' in item, item


# --- Tipos de diabetes (classificação da ADA 2026) -----------------------------------------------

def test_insulina_nao_marca_tipo_de_diabetes():
    from src.utils import medicamentos
    for remedio in ('insulina_nph', 'insulina_glargina', 'insulina_asparte'):
        com, _, inf = coerencia.inferir({'comorbidades': [], 'medicacoes': medicamentos.classes_de([remedio])})
        assert com == [] and inf == [], remedio


@pytest.mark.parametrize('tipo', ['diabetes_tipo_1', 'diabetes_monogenico', 'diabetes_pancreatico', 'diabetes_medicamentoso'])
def test_com_outro_tipo_marcado_nada_marca_o_tipo_2(tipo):
    """Antidiabético e HbA1c ≥ 6,5% não dizem o tipo: não acrescentam "tipo 2" a quem já tem outro tipo."""
    com, _, inf = coerencia.inferir({'comorbidades': [tipo], 'medicacoes': ['metformina', 'sulfonilureia'], 'hba1c': 8.2})
    assert com == [tipo] and inf == []
    assert coerencia.inferir({'comorbidades': [tipo], 'hba1c': 6.0})[0] == [tipo]   # e não é pré-diabetes
    assert coerencia.rotulo_de(tipo)


@pytest.mark.parametrize('remedio', ['metformina', 'dapagliflozina_metformina'])
def test_metformina_nao_marca_diabetes(remedio):
    """Metformina também se usa em pré-diabetes e resistência insulínica: não marca "Diabetes tipo 2"."""
    from src.utils import coerencia, medicamentos
    com, _, _ = coerencia.inferir({'comorbidades': [], 'medicacoes': medicamentos.classes_de([remedio])})
    assert not {'diabetes', 'diabetes_tipo_1'} & set(com), (remedio, com)
    com, _, _ = coerencia.inferir({'comorbidades': ['pre_diabetes'], 'medicacoes': medicamentos.classes_de([remedio])})
    assert 'pre_diabetes' in com and 'diabetes' not in com


@pytest.mark.parametrize('texto', ['metformina 850 2x/dia', 'Glifage XR 500', 'metformin 1 g'])
def test_metformina_no_texto_livre_entra_como_medicacao_sem_marcar_diabetes(texto):
    com, med, inf = _inf(medicacoes_continuo=texto)
    assert 'metformina' in med and 'diabetes' not in com
    assert not any(i['valor'] == 'metformina' for i in inf)      # não aparece como caixa marcada na tela


def test_metformina_no_texto_livre_mantem_a_vitamina_b12_sem_diabetes(client):
    """Tirar a marcação automática de diabetes não pode tirar a monitorização de B12 de quem usa metformina."""
    base = dict(idade=45, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], historia_familiar=[], medicacoes=[])
    for corpo in (dict(base, medicacoes_continuo='metformina 850 2x/dia'), dict(base, medicacoes=['metformina']),
                  dict(base, comorbidades=['pre_diabetes'], medicacoes_continuo='glifage 500')):
        dados = client.post('/api/checkup-intelligent', json=corpo).get_json()
        titulos = [r['titulo'] for r in dados['recommendations']]
        assert titulos.count('Vitamina B12, soro') == 1, corpo
        assert 'diabetes' not in (dados.get('comorbidades_consideradas') or [])
