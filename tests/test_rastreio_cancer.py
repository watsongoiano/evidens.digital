"""Rastreamento de câncer: idades de início e de parada, divergências entre diretrizes e dado ausente.

PSA (USPSTF 2018: decisão compartilhada 55-69, D a partir de 70), mamografia (USPSTF 2024 bienal 40-74), colorretal
(USPSTF 2021 / USMSTF 2022: colonoscopia ou FIT 45-75, individualizar 76-85), TC de baixa dose (USPSTF 2021 /
SBCT-SBPT-CBR 2024), vigilância por história familiar e síndrome hereditária até 75 anos, e o que se adia na gestação.
Perfis fictícios.
"""
import pytest

from src.utils import rastreio_cancer as RC
from src.utils.reference_links import build_reference_links

PSA, MAMO, COLONO, FIT, LDCT = RC.PSA, RC.MAMOGRAFIA, RC.COLONOSCOPIA, RC.FIT, RC.LDCT
DIV_PSA = 'Câncer de próstata: as diretrizes divergem'
DIV_MAMO = 'Mamografia: as diretrizes divergem no intervalo e na idade de início'
MAMO_75 = 'Mamografia a partir de 75 anos: decisão individual'
DIV_CCR = 'Câncer colorretal: as diretrizes divergem na idade de início e no método'
CCR_76 = 'Rastreio colorretal de 76 a 85 anos: decisão individual'
CCR_86 = 'Rastreio colorretal depois dos 85 anos: não recomendado'
SINDROME_75 = 'Síndrome hereditária de câncer depois dos 75 anos: decisão individual'
DIV_PULMAO = 'Câncer de pulmão: as diretrizes divergem para quem parou de fumar há 15 anos ou mais'


def _r(client, **dados):
    base = dict(sexo='masculino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], historia_familiar=[])
    resposta = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert resposta.status_code == 200, resposta.get_json()
    r = resposta.get_json()
    return ({x['titulo']: x for x in r['recommendations']}, {o['titulo']: o for o in r['orientacoes']},
            {x['titulo']: x for x in r['nao_incluidas']}, {x['titulo']: x for x in r.get('adiados_gestacao') or []})


# --- PSA ----------------------------------------------------------------------------------------

@pytest.mark.parametrize('idade, pede', [(50, False), (54, False), (55, True), (69, True), (70, False), (88, False)])
def test_psa_por_decisao_compartilhada_dos_55_aos_69(client, idade, pede):
    recs, orient, nao, _ = _r(client, idade=idade)
    assert (PSA in recs) == pede
    if pede:
        rec = recs[PSA]
        assert rec['subtitulo'] == 'Homens 55-69 anos, decisão compartilhada | A cada 2-4 anos'
        assert rec['grau_evidencia'] == 'C' and 'USPSTF 2018' in rec['referencia']
        assert 'Não pedir para quem' in rec['descricao']
    # A partir de 70 anos: não se pede e aparece como não recomendado (USPSTF D).
    assert (PSA in nao) == (idade >= 70)
    if idade >= 70:
        assert nao[PSA]['estado'] == 'nao_recomendado' and 'grau D' in nao[PSA]['motivo']
    # Divergência com MS/INCA e SBU só na faixa em que importa (50-69).
    assert (DIV_PSA in orient) == (50 <= idade <= 69)


def test_psa_nunca_para_mulher(client):
    recs, orient, nao, _ = _r(client, idade=60, sexo='feminino')
    assert PSA not in recs and PSA not in nao and DIV_PSA not in orient


def test_divergencia_do_psa_cita_ms_inca_e_sbu_com_links(client):
    _, orient, _, _ = _r(client, idade=60)
    o = orient[DIV_PSA]
    assert 'Nota Técnica 9/2023' in o['descricao'] and 'SBU' in o['descricao']
    assert all(link['url'] for link in o['referencias']) and len(o['referencias']) == 3


@pytest.mark.parametrize('familia, idade, pede', [
    (['cancer_prostata'], 44, False), (['cancer_prostata'], 45, True), (['cancer_prostata'], 69, True),
    (['cancer_prostata'], 70, False), (['brca'], 39, False), (['brca'], 40, True), (['brca'], 69, True), (['brca'], 76, False),
])
def test_psa_por_historia_familiar_ou_brca_para_aos_69(client, familia, idade, pede):
    recs, orient, nao, _ = _r(client, idade=idade, historia_familiar=familia)
    assert (PSA in recs) == pede
    assert (DIV_PSA in orient) == (40 <= idade <= 69)
    if idade >= 70:
        assert 'NCCN' in nao[PSA]['motivo']


# --- Mama ---------------------------------------------------------------------------------------

@pytest.mark.parametrize('idade', [39, 40, 74, 75, 88])
def test_mamografia_bienal_40_74_com_divergencia(client, idade):
    recs, orient, _, _ = _r(client, idade=idade, sexo='feminino')
    assert (MAMO in recs) == (40 <= idade <= 74)
    assert (DIV_MAMO in orient) == (40 <= idade <= 74)
    assert (MAMO_75 in orient) == (idade >= 75)
    if MAMO in recs:
        assert recs[MAMO]['subtitulo'] == 'Mulheres 40-74 anos | Bienal'
        refs = orient[DIV_MAMO]['referencias']
        assert [r['label'] for r in refs] == ['USPSTF 2024', 'CBR/SBM/FEBRASGO 2023', 'MS NT 626/2025'] and all(r['url'] for r in refs)


@pytest.mark.parametrize('idade', [74, 75, 76, 88])
def test_mamografia_anual_por_historia_familiar_para_aos_74(client, idade):
    recs, orient, _, _ = _r(client, idade=idade, sexo='feminino', historia_familiar=['cancer_mama'])
    assert (MAMO in recs) == (idade <= 74)
    if MAMO in recs:
        assert recs[MAMO]['subtitulo'] == 'Câncer de mama na família | Anual'
        assert DIV_MAMO not in orient  # a divergência é do risco habitual
    else:
        assert MAMO_75 in orient


def test_so_o_detalhe_de_2o_grau_nao_torna_a_mamografia_anual(client):
    recs, _, _, _ = _r(client, idade=45, sexo='feminino', historia_familiar=['mama_ate_50'])
    assert recs[MAMO]['subtitulo'] == 'Mulheres 40-74 anos | Bienal'
    recs, _, _, _ = _r(client, idade=45, sexo='feminino', historia_familiar=['cancer_mama', 'mama_ate_50'])
    assert recs[MAMO]['subtitulo'].endswith('Anual')


@pytest.mark.parametrize('sindrome, idade, pede', [('brca', 75, True), ('brca', 76, False), ('li_fraumeni', 76, False)])
def test_rm_de_mamas_da_sindrome_para_aos_75(client, sindrome, idade, pede):
    recs, orient, _, _ = _r(client, idade=idade, sexo='feminino', historia_familiar=[sindrome])
    assert ('Ressonância magnética de mamas' in recs) == pede
    assert (SINDROME_75 in orient) == (not pede)


# --- Colorretal ---------------------------------------------------------------------------------

@pytest.mark.parametrize('idade', [44, 45, 75, 76, 85, 86, 88])
def test_colorretal_colonoscopia_ou_fit_dos_45_aos_75(client, idade):
    recs, orient, _, _ = _r(client, idade=idade)
    dentro = 45 <= idade <= 75
    assert (COLONO in recs) == dentro and (FIT in recs) == dentro
    assert (DIV_CCR in orient) == dentro
    assert (CCR_76 in orient) == (76 <= idade <= 85)
    assert (CCR_86 in orient) == (idade >= 86)
    if dentro:
        assert recs[FIT]['subtitulo'] == 'Adultos 45-75 anos, alternativa à colonoscopia | Anual'
        assert 'retirar o outro' in recs[FIT]['descricao'] and 'retirar o outro' in recs[COLONO]['descricao']
        assert [l['label'] for l in recs[FIT]['referencias']] == ['USPSTF 2021', 'MS/INCA 2026']
        assert all(l['url'] for l in recs[FIT]['referencias'])
        assert 'USMSTF 2022' in orient[DIV_CCR]['referencia']


@pytest.mark.parametrize('familia', [['cancer_colorretal'], ['cancer_colorretal', 'ccr_antes_60'], ['lynch']])
def test_no_risco_aumentado_so_a_colonoscopia(client, familia):
    recs, orient, _, _ = _r(client, idade=50, historia_familiar=familia)
    assert COLONO in recs and FIT not in recs and DIV_CCR not in orient


@pytest.mark.parametrize('familia', [['cancer_colorretal'], ['cancer_colorretal', 'ccr_antes_60']])
@pytest.mark.parametrize('idade', [75, 76, 88])
def test_colonoscopia_por_historia_familiar_para_aos_75(client, familia, idade):
    recs, orient, _, _ = _r(client, idade=idade, historia_familiar=familia)
    assert (COLONO in recs) == (idade <= 75)
    assert (CCR_76 in orient or CCR_86 in orient) == (idade > 75)


@pytest.mark.parametrize('idade, pede', [(31, False), (32, True), (40, True)])
def test_inicio_10_anos_antes_do_familiar_mais_jovem(client, idade, pede):
    recs, orient, _, _ = _r(client, idade=idade, historia_familiar=['cancer_colorretal', 'ccr_antes_60'], idade_ccr_familiar=42)
    assert (COLONO in recs) == pede
    if pede:
        assert 'a partir dos 32 anos' in recs[COLONO]['descricao'] and recs[COLONO]['subtitulo'].endswith('A cada 5 anos')
    else:
        assert 'Colonoscopia por história familiar de câncer colorretal' in orient


def test_idade_do_familiar_antes_dos_60_vale_como_o_detalhe(client):
    recs, _, _, _ = _r(client, idade=41, historia_familiar=['cancer_colorretal'], idade_ccr_familiar=55)
    assert recs[COLONO]['subtitulo'] == 'História familiar de CCR antes dos 60 anos | A partir de 40 anos | A cada 5 anos'
    recs, _, _, _ = _r(client, idade=41, historia_familiar=['cancer_colorretal'], idade_ccr_familiar=60)
    assert recs[COLONO]['subtitulo'].endswith('A cada 10 anos')


@pytest.mark.parametrize('valor', [5, 200, 'abc'])
def test_idade_do_familiar_fora_da_faixa_e_recusada(client, valor):
    resposta = client.post('/api/checkup-intelligent', json=dict(idade=40, sexo='masculino', tabagismo='nunca',
                                                                 historia_familiar=['cancer_colorretal'], idade_ccr_familiar=valor))
    assert resposta.status_code == 400


# --- Síndromes hereditárias ---------------------------------------------------------------------

@pytest.mark.parametrize('sindrome, exames', [
    ('lynch', [COLONO, 'Endoscopia digestiva alta']),
    ('paf', [COLONO, 'Endoscopia digestiva alta']),
    ('li_fraumeni', ['Ressonância magnética de corpo inteiro', 'Ressonância magnética de crânio', COLONO]),
    ('cdh1', ['Endoscopia digestiva alta']),
    ('cowden', ['Ultrassonografia de tireoide', COLONO, 'Ultrassonografia de rins e vias urinárias']),
    ('nem2', ['Calcitonina, soro', 'Ultrassonografia de tireoide']),
])
@pytest.mark.parametrize('idade', [75, 76, 88])
def test_vigilancia_por_sindrome_para_aos_75_e_vira_orientacao(client, sindrome, exames, idade):
    recs, orient, _, _ = _r(client, idade=idade, historia_familiar=[sindrome])
    for exame in exames:
        assert (exame in recs) == (idade <= 75), exame
    assert (SINDROME_75 in orient) == (idade > 75)
    if idade > 75:
        assert 'teste em cascata' in orient[SINDROME_75]['descricao']
        assert all(l['url'] for l in orient[SINDROME_75]['referencias'])


@pytest.mark.parametrize('idade, aviso', [(50, False), (51, True)])
def test_paf_no_parente_acima_dos_50_orienta_o_teste_em_cascata(client, idade, aviso):
    recs, orient, _, _ = _r(client, idade=idade, historia_familiar=['paf'])
    assert COLONO in recs  # o formulário não distingue portador confirmado de parente não testado
    assert ('Parente não testado com mais de 50 anos' in orient['Polipose adenomatosa familiar na família']['descricao']) == aviso


def test_lynch_diferencia_os_genes_no_texto(client):
    recs, _, _, _ = _r(client, idade=30, historia_familiar=['lynch'])
    assert 'MSH6 e PMS2: a partir de 30-35 anos' in recs[COLONO]['descricao']


# --- Gestação -----------------------------------------------------------------------------------

def test_gestante_adia_rm_de_mamas_e_endoscopia_eletiva(client):
    gestante = dict(sexo='feminino', gestante='sim', idade_gestacional=20, primeira_consulta='nao')
    recs, _, _, adiados = _r(client, idade=36, historia_familiar=['brca', 'lynch'], **gestante)
    for titulo, ref in (('Ressonância magnética de mamas', 'ACOG CO 723'), ('Endoscopia digestiva alta', 'ASGE 2012')):
        assert titulo not in recs and adiados[titulo]['referencia'] == ref
    assert 'gadolínio' in adiados['Ressonância magnética de mamas']['motivo']
    # fora da gestação, as duas continuam
    recs, _, _, _ = _r(client, idade=36, sexo='feminino', historia_familiar=['brca', 'lynch'])
    assert 'Ressonância magnética de mamas' in recs and 'Endoscopia digestiva alta' in recs


def test_gestante_adia_o_fit_junto_com_a_colonoscopia(client):
    recs, _, _, adiados = _r(client, idade=46, sexo='feminino', gestante='sim', idade_gestacional=20, primeira_consulta='nao')
    assert FIT not in recs and COLONO not in recs and FIT in adiados and COLONO in adiados


# --- Pulmão -------------------------------------------------------------------------------------

@pytest.mark.parametrize('dados, esperado', [
    (dict(idade=60, tabagismo='atual'), 'dados'),
    (dict(idade=60, tabagismo='atual', macos_ano=20), 'tc'),
    (dict(idade=60, tabagismo='atual', macos_ano=19.9), 'nada'),
    (dict(idade=49, tabagismo='atual'), 'nada'),
    (dict(idade=81, tabagismo='atual'), 'nada'),
    (dict(idade=60, tabagismo='ex', macos_ano=30), 'dados'),
    (dict(idade=60, tabagismo='ex', macos_ano=30, anos_parou_fumar=0), 'tc'),
    (dict(idade=60, tabagismo='ex', macos_ano=30, anos_parou_fumar=14), 'tc'),
    (dict(idade=60, tabagismo='ex', macos_ano=30, anos_parou_fumar=15), 'acs'),
    (dict(idade=60, tabagismo='ex', macos_ano=10, anos_parou_fumar=20), 'nada'),
    (dict(idade=60, tabagismo='nunca'), 'nada'),
])
def test_tc_de_baixa_dose_e_dado_ausente(client, dados, esperado):
    recs, orient, nao, _ = _r(client, **dados)
    assert (LDCT in recs) == (esperado == 'tc')
    assert (LDCT in nao) == (esperado == 'dados')
    assert (DIV_PULMAO in orient) == (esperado == 'acs')
    if esperado == 'dados':
        assert nao[LDCT]['estado'] == 'dados_insuficientes'
        falta = 'maços-ano' if 'macos_ano' not in dados else 'parou de fumar'
        assert falta in nao[LDCT]['motivo']
    if esperado == 'tc':
        assert [l['label'] for l in recs[LDCT]['referencias']] == ['USPSTF 2021', 'SBCT-SBPT-CBR 2024']
        assert all(l['url'] for l in recs[LDCT]['referencias'])
    if esperado == 'acs':
        assert 'ACS 2023' in orient[DIV_PULMAO]['referencia'] and all(l['url'] for l in orient[DIV_PULMAO]['referencias'])


def test_gestante_sem_macos_ano_nao_recebe_aviso_de_tc(client):
    _, _, nao, _ = _r(client, idade=50, sexo='feminino', tabagismo='atual', gestante='sim', idade_gestacional=20,
                      primeira_consulta='nao')
    assert LDCT not in nao


# --- Textos e referências -----------------------------------------------------------------------

def test_referencias_somadas_por_regras_diferentes_tem_um_link_cada():
    links = build_reference_links('Mamografia Digital - Bilateral', 'USPSTF 2024 | NCCN 2025 / ACS 2007')
    assert [l['label'] for l in links] == ['USPSTF 2024', 'NCCN 2025', 'ACS 2007']
    from urllib.parse import urlsplit
    assert 'breast-cancer-screening' in links[0]['url'] and 'canjclin' in links[2]['url']
    assert urlsplit(links[1]['url']).hostname in ('nccn.org', 'www.nccn.org')


def test_textos_da_historia_familiar(client):
    from src.utils import condicoes
    assert 'triplo-negativo em parente próximo, em qualquer idade' in ' '.join(condicoes.criterios_teste_genetico(['mama_triplo_negativo']))
    recs = []
    orient = {o['titulo']: o for o in condicoes.aplicar(recs, 40, 'feminino', [], [], ['cancer_pancreas', 'melanoma'])}
    assert 'mesmo ramo da família, com pelo menos um de 1º grau' in orient['Câncer de pâncreas na família']['descricao']
    melanoma = orient['Melanoma na família']
    assert melanoma['referencia'] == 'USPSTF 2023' and 'grau I' in melanoma['descricao']
    assert 'skin-cancer-screening' in build_reference_links(melanoma['titulo'], melanoma['referencia'])[0]['url']
