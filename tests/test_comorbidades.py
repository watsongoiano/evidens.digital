"""Outras comorbidades: cada doença com o acompanhamento da sua diretriz (src/utils/condicoes.py)."""
import pytest

from src.utils import condicoes, medicamentos

IMUNOMEDIADAS = ('artrite_reumatoide', 'lupus', 'psoriase', 'artrite_psoriasica', 'espondiloartrite', 'doenca_crohn',
                 'retocolite', 'esclerose_sistemica')


def _rodar(comorbidades, idade=45, sexo='feminino', **extra):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, comorbidades, [], [], **extra)
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


def test_doencas_imunomediadas_sao_itens_separados():
    assert 'doenca_autoimune' not in condicoes.COMORBIDADES
    for chave in IMUNOMEDIADAS:
        assert chave in condicoes.COMORBIDADES
    # cada uma gera o seu acompanhamento (as três artrites dividem a avaliação de risco cardiovascular)
    assinaturas = {chave: frozenset(_rodar([chave])[0]) | frozenset(_rodar([chave])[1]) for chave in IMUNOMEDIADAS}
    assert len(set(assinaturas.values())) >= 6


def test_antirreumatico_nao_marca_doenca_sozinho():
    for nome in ('adalimumabe', 'hidroxicloroquina', 'mesalazina', 'tofacitinibe'):
        assert not medicamentos.MARCA.get(nome), nome


def test_agravante_cardiovascular_das_inflamatorias():
    for chave in ('artrite_reumatoide', 'lupus', 'psoriase', 'doenca_crohn', 'retocolite'):
        assert condicoes.agravantes_de_risco([chave], []) == ['doença inflamatória crônica']
    assert condicoes.agravantes_de_risco(['esclerose_sistemica'], []) == []
    assert condicoes.agravantes_de_risco(['doenca_autoimune'], []) == ['doença inflamatória crônica']   # formulário antigo


def test_artrites_avaliam_risco_cv_a_cada_5_anos():
    recs, orient = _rodar(['artrite_reumatoide'])
    assert recs['Colesterol total e frações, soro']['subtitulo'] == 'Artrite reumatoide | A cada 5 anos'
    assert 'EULAR 2016' in recs['Colesterol total e frações, soro']['referencia']
    assert 'Artrite reumatoide: pulmão e osso' in orient


def test_lupus_monitorizacao_e_nefrite():
    recs, orient = _rodar(['lupus'])
    for titulo in ('Hemograma completo com plaquetas', 'VHS', 'Albumina, soro', 'Creatinina, soro', 'Urina tipo I (EAS)'):
        assert recs[titulo]['subtitulo'].endswith('A cada 6-12 meses'), titulo
    assert recs['Relação proteína/creatinina, urina']['referencia'] == condicoes.ACR_NEFRITE
    assert {'Complemento C3', 'Complemento C4', 'Anti-DNA', 'Anticoagulante lúpico, pesquisa'} <= set(recs)
    assert 'Antes do tratamento' in recs['HBsAg, anti-HBc total e anti-HBs']['subtitulo']
    assert 'Lúpus: pressão arterial e olhos' in orient
    com_nefrite, _ = _rodar(['lupus', 'les_nefrite'])
    assert 'Nefrite lúpica | A cada 3 meses' in com_nefrite['Relação proteína/creatinina, urina']['subtitulo']
    # detalhe sozinho (sem o lúpus) não faz nada
    assert _rodar(['les_nefrite'])[0] == {}


def test_psoriase_extensa_antecipa_rastreio_metabolico():
    simples, orient = _rodar(['psoriase'])
    assert 'Colesterol total e frações, soro' in simples and 'Glicose, soro' not in simples
    assert 'Psoríase: comorbidades' in orient
    extensa, _ = _rodar(['psoriase', 'psoriase_extensa'])
    assert {'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'} <= set(extensa)


@pytest.mark.parametrize('detalhes, esperado', [
    ([], None),
    (['crohn_colon'], None),
    (['crohn_colon', 'crohn_8_anos'], 'A cada 1-5 anos'),
    (['crohn_cep'], 'Anual'),
])
def test_crohn_colonoscopia_de_vigilancia(detalhes, esperado):
    recs, orient = _rodar(['doenca_crohn', *detalhes])
    colono = recs.get('Colonoscopia de Rastreio com ou sem biópsia')
    if esperado is None:
        assert colono is None and 'Doença de Crohn: colonoscopia de vigilância' in orient
    else:
        assert colono['subtitulo'].endswith(esperado) and colono['referencia'] == condicoes.BSG_DII
    assert recs['Ferritina, soro']['subtitulo'] == 'Doença de Crohn | A cada 6-12 meses'


def test_retocolite_e_crohn_de_delgado():
    recs, _ = _rodar(['retocolite', 'rcu_alem_reto', 'rcu_8_anos'])
    assert recs['Colonoscopia de Rastreio com ou sem biópsia']['subtitulo'].endswith('A cada 1-5 anos')
    assert 'Vitamina B12, soro' not in recs
    delgado, _ = _rodar(['doenca_crohn', 'crohn_delgado'])
    assert delgado['Vitamina B12, soro']['subtitulo'] == 'Crohn de delgado ou ressecção ileal | Anual'


def test_esclerose_sistemica_rastreia_hipertensao_pulmonar_e_pulmao():
    recs, _ = _rodar(['esclerose_sistemica'])
    for titulo in ('Ecocardiograma transtorácico', 'Peptídeo natriurético BNP/PROBNP',
                   'Prova de função pulmonar completa com difusão (DLCO)'):
        assert recs[titulo]['subtitulo'] == 'Esclerose sistêmica | Anual'
    assert 'Tomografia computadorizada de tórax de alta resolução' in recs


def test_hepatite_b_monitorizacao_e_carcinoma():
    recs, orient = _rodar(['hepatite_b_cronica'])
    assert recs['Carga viral da hepatite B (HBV-DNA quantitativo), plasma']['subtitulo'].endswith('A cada 6-12 meses')
    assert 'Ultrassonografia de abdome superior' not in recs
    assert 'Hepatite B: estadiamento e carcinoma hepatocelular' in orient
    risco, _ = _rodar(['hepatite_b_cronica', 'hbv_risco_chc'])
    assert risco['Ultrassonografia de abdome superior']['subtitulo'] == 'Hepatite B de alto risco | A cada 6 meses'


def test_hepatite_c_avaliacao_antes_do_tratamento():
    recs, _ = _rodar(['hepatite_c'])
    assert 'Carga viral da hepatite C (HCV-RNA quantitativo), plasma' in recs
    assert 'Antes do tratamento' in recs['HBsAg, anti-HBc total e anti-HBs']['subtitulo']


def test_barrett_so_com_tres_fatores():
    sem, orient = _rodar(['drge'], idade=55, sexo='masculino', tabagismo='nunca', imc=24)
    assert 'Endoscopia digestiva alta' not in sem and 'Refluxo: rastreio de esôfago de Barrett' in orient
    com, _ = _rodar(['drge'], idade=55, sexo='masculino', tabagismo='atual', imc=24)
    assert com['Endoscopia digestiva alta']['subtitulo'].endswith('Uma vez')


def test_sop_rastreia_glicemia_independente_do_imc():
    recs, _ = _rodar(['sop'], idade=25)
    assert recs['TOTG-75g (Teste Oral de Tolerância à Glicose), soro']['subtitulo'].endswith('A cada 1-3 anos')
    assert _rodar(['sop'], sexo='masculino')[0] == {}


@pytest.mark.parametrize('chave, titulo', [
    ('anemia_falciforme', 'Relação albumina/creatinina urinária (uACR)'),
    ('asma_grave', 'Espirometria, com broncodilatador'),
    ('fibrilacao_atrial', 'Ecocardiograma transtorácico'),
    ('doenca_celiaca', 'Anticorpo antitransglutaminase tecidual IgA, soro'),
    ('neoplasia_ativa', 'HBsAg, anti-HBc total e anti-HBs'),
    ('osteoporose', 'Paratormônio (PTH), soro'),
    ('cirurgia_bariatrica', 'Ácido fólico, soro'),
    ('gota', 'Creatinina, soro'),
])
def test_comorbidade_pede_o_exame_da_sua_diretriz(chave, titulo):
    assert titulo in _rodar([chave])[0]


def test_detalhes_estao_na_tela(client):
    pagina = client.get('/intelligent-tools').get_data(as_text=True)
    for chave, (_titulo, _dica, itens) in condicoes.DETALHES_COMORBIDADE.items():
        assert f'data-comorbidade="{chave}"' in pagina
        for valor, _rotulo in itens:
            assert f'name="comorbidades" value="{valor}"' in pagina
