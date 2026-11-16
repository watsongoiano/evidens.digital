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
                'tenofovir_lamivudina_dolutegravir': 'hiv'}
    for medicamento, doenca in esperado.items():
        com, _, inf = coerencia.inferir({}, escolhidas=[medicamento])
        assert com == [doenca], medicamento
        assert inf[0]['motivo'].startswith('uso de ') and inf[0]['rotulo'] == coerencia.rotulo_de(doenca)
    # todo alvo é uma comorbidade que a tela conhece (caixa fixa ou item da lista)
    for alvos in medicamentos.MARCA.values():
        for alvo in alvos:
            assert coerencia.rotulo_de(alvo)
    # os que têm outra indicação comum não marcam nada sozinhos
    # antirreumáticos e imunobiológicos servem a várias doenças imunomediadas, com acompanhamentos diferentes
    for medicamento in ('metotrexato', 'pramipexol', 'alopurinol', 'clopidogrel', 'tenofovir_entricitabina', 'pregabalina',
                        'adalimumabe', 'hidroxicloroquina', 'mesalazina', 'sulfassalazina', 'tofacitinibe'):
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


# Uma PA de consultório isolada não rotula HAS (decisão do responsável clínico; SBC 2025 e AHA/ACC 2025 pedem
# confirmação em 2 ou mais consultas ou com MRPA/MAPA). A categoria AHA/ACC 2025 continua sendo a da medida;
# fora da gestação, só PA ≥ 180/110 (HAS estágio 3 da SBC 2025) marca a caixa.
@pytest.mark.parametrize('pas, pad, categoria, sbc, has', [
    (118, 76, 'normal', 'normal', False), (125, 78, 'elevada', 'pre_hipertensao', False),
    (128, 82, 'estagio1', 'pre_hipertensao', False), (134, 70, 'estagio1', 'pre_hipertensao', False),
    (138, 92, 'estagio2', 'estagio1', False), (150, 85, 'estagio2', 'estagio1', False),
    (165, 102, 'estagio2', 'estagio2', False), (179, 109, 'estagio2', 'estagio2', False),
    (180, 95, 'estagio2', 'estagio3', True), (150, 110, 'estagio2', 'estagio3', True),
])
def test_pa_isolada_so_marca_has_a_partir_de_180_110(pas, pad, categoria, sbc, has):
    c = coerencia.classificar_pa(pas, pad)
    assert c['categoria'] == categoria and c['sbc']['categoria'] == sbc
    com, _, inf = coerencia.inferir({'pas': pas, 'pad': pad})
    assert ('hipertensao' in com) is has
    if has:
        assert 'MRPA ou MAPA' in inf[0]['motivo'] and '180/110' in inf[0]['motivo']


@pytest.mark.parametrize('pas, pad, a_confirmar', [
    (129, 79, False), (130, 79, True), (129, 80, True), (150, 95, True), (179, 109, True), (180, 109, False),
    (125, 78, False),
])
def test_pa_alterada_sem_has_fica_a_confirmar(pas, pad, a_confirmar):
    c = coerencia.classificar_pa(pas, pad)
    com, _, _ = coerencia.inferir({'pas': pas, 'pad': pad})
    assert coerencia.pa_a_confirmar(c, com) is a_confirmar
    # HAS marcada pelo médico ou anti-hipertensivo em uso: não é "a confirmar"; na gestação também não
    assert coerencia.pa_a_confirmar(c, ['hipertensao']) is False
    assert coerencia.pa_a_confirmar(c, coerencia.inferir({'pas': pas, 'pad': pad, 'medicacoes': ['anti_hipertensivos']})[0]) is False
    assert coerencia.pa_a_confirmar(c, com, gestante=True) is False


def test_pa_na_gestacao_usa_140_90():
    assert 'hipertensao' not in coerencia.inferir({'pas': 134, 'pad': 84}, gestante=True)[0]
    assert 'hipertensao' in coerencia.inferir({'pas': 142, 'pad': 84}, gestante=True)[0]


def test_api_pa_alterada_pede_so_mrpa_ou_mapa(client):
    corpo = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao', 'pas': '132', 'pad': '78'}
    r = client.post('/api/checkup-intelligent', json=corpo).get_json()
    assert r['pa_classificacao']['categoria'] == 'estagio1'
    assert r['pa_classificacao']['sbc']['categoria'] == 'pre_hipertensao'
    assert not any(i['valor'] == 'hipertensao' for i in r['inferencias'])
    recs = {t['titulo']: t for t in r['recommendations']}
    mapa = recs['MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)']
    assert 'Para confirmar o diagnóstico' in mapa['subtitulo'] and 'MRPA' in mapa['descricao']
    for exame in ('Potássio, soro', 'Ácido úrico, soro', 'EAS - Elementos Anormais e Sedimentoscopia',
                  'Relação albumina/creatinina urinária (uACR)', 'Eletrocardiograma de repouso', 'Ecocardiograma transtorácico'):
        assert exame not in recs, exame
    titulos = [o['titulo'] for o in r['orientacoes']]
    assert 'PA alterada: confirmar antes de rotular HAS' in titulos
    assert 'Divergência entre diretrizes: classificação da PA' in titulos   # 130-139/80-89: SBC chama de pré-hipertensão
    # 150/95: HAS estágio 1 nas duas diretrizes; só a confirmação, sem aviso de divergência
    r = client.post('/api/checkup-intelligent', json={**corpo, 'pas': '150', 'pad': '95'}).get_json()
    titulos = [o['titulo'] for o in r['orientacoes']]
    assert 'PA alterada: confirmar antes de rotular HAS' in titulos and 'Divergência entre diretrizes: classificação da PA' not in titulos
    assert 'Potássio, soro' not in {t['titulo'] for t in r['recommendations']}
    # 129/79: nada
    r = client.post('/api/checkup-intelligent', json={**corpo, 'pas': '129', 'pad': '79'}).get_json()
    assert not any(t['titulo'].startswith('MAPA') for t in r['recommendations'])


@pytest.mark.parametrize('extra', [dict(pas='182', pad='100'), dict(comorbidades=['hipertensao']),
                                   dict(medicacoes_continuo='losartana 50 mg')], ids=['pa_grave', 'marcada', 'anti_hipertensivo'])
def test_api_bloco_de_has_so_com_has_confirmada(client, extra):
    corpo = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao', **extra}
    r = client.post('/api/checkup-intelligent', json=corpo).get_json()
    recs = {t['titulo']: t for t in r['recommendations']}
    for exame in ('Potássio, soro', 'Ácido úrico, soro', 'Creatinina, soro', 'Relação albumina/creatinina urinária (uACR)',
                  'Eletrocardiograma de repouso'):
        assert exame in recs, exame
    mapa = recs['MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)']
    assert 'avaliar controle' in mapa['subtitulo'] and 'suspeita' not in mapa['subtitulo']
    # ecocardiograma só com indicação (AHA/ACC 2025), com o aviso da divergência com a SBC 2025
    assert 'Ecocardiograma transtorácico' not in recs
    assert 'Divergência entre diretrizes: ecocardiograma na HAS' in [o['titulo'] for o in r['orientacoes']]


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


# ── HAS resistente (AHA 2018, Carey et al.; AHA/ACC 2025) ────────────────────
# PA acima da meta (< 130/80) com 3 classes anti-hipertensivas, ou 4 ou mais classes mesmo com a PA na meta.
TRIPLA = ['losartana', 'hidroclorotiazida', 'anlodipino']


def _resistente(escolhidas, pas=None, pad=None, gestante=False, comorbidades=()):
    from src.utils import medicamentos
    com, _, inf = coerencia.inferir({'pas': pas, 'pad': pad, 'comorbidades': list(comorbidades),
                                     'medicacoes': medicamentos.classes_de(escolhidas)},
                                    gestante=gestante, escolhidas=escolhidas)
    return 'has_resistente' in com, {i['valor']: i['motivo'] for i in inf}.get('has_resistente', '')


def test_tres_classes_com_pa_acima_da_meta_marca_has_resistente():
    marcou, motivo = _resistente(TRIPLA, 138, 84)
    assert marcou and '3 classes' in motivo and 'MRPA ou MAPA' in motivo and 'adesão' in motivo


def test_tres_classes_com_pa_na_meta_ou_sem_pa_nao_marca():
    assert not _resistente(TRIPLA, 124, 76)[0]
    assert not _resistente(TRIPLA)[0]


def test_quatro_classes_marcam_mesmo_com_pa_na_meta():
    marcou, motivo = _resistente(TRIPLA + ['espironolactona'], 122, 74)
    assert marcou and '4 classes' in motivo


def test_associacao_em_comprimido_unico_conta_cada_classe():
    assert _resistente(['losartana_hidroclorotiazida', 'anlodipino'], 150, 95)[0]


def test_mesma_classe_repetida_conta_uma_vez():
    # IECA + BRA bloqueiam o mesmo sistema; tiazídico + alça são diuréticos
    assert not _resistente(['losartana', 'enalapril', 'anlodipino'], 150, 95)[0]
    assert not _resistente(['hidroclorotiazida', 'furosemida', 'anlodipino'], 150, 95)[0]


def test_esquema_de_insuficiencia_cardiaca_sem_hipertensao_nao_e_has_resistente():
    # betabloqueador, espironolactona, alça e sacubitril/valsartana também tratam IC
    assert not _resistente(['carvedilol', 'espironolactona', 'furosemida', 'sacubitril_valsartana'])[0]
    assert _resistente(['carvedilol', 'espironolactona', 'furosemida', 'sacubitril_valsartana'],
                       comorbidades=['hipertensao'])[0]


def test_na_gestacao_o_corte_e_140_90():
    gestante = ['metildopa', 'nifedipino', 'hidralazina']
    assert not _resistente(gestante, 135, 85, gestante=True)[0]
    assert _resistente(gestante, 145, 85, gestante=True)[0]


def test_has_resistente_recusada_pelo_medico_nao_volta():
    from src.utils import medicamentos
    com, _, _ = coerencia.inferir({'pas': 150, 'pad': 95, 'medicacoes': medicamentos.classes_de(TRIPLA)},
                                  recusados=('has_resistente',), escolhidas=TRIPLA)
    assert 'has_resistente' not in com
