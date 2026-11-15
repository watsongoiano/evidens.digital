"""História familiar de câncer: teste genético só com os critérios do NCCN (não para toda história de
câncer de mama) e colonoscopia pela idade do familiar (USMSTF 2017)."""
import pytest

from src.utils import condicoes

TESTE = 'Teste genético indicado: aconselhamento e painel germinativo (BRCA1/2)'
SEM_CRITERIO = 'Câncer de mama na família sem critério para teste genético'
COLONO = 'Colonoscopia de Rastreio com ou sem biópsia'


def _rodar(familia, idade=35, sexo='feminino'):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, [], [], familia)
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


def test_cancer_de_mama_na_familia_sozinho_nao_indica_teste_genetico():
    _, orient = _rodar(['cancer_mama'])
    assert TESTE not in orient
    assert SEM_CRITERIO in orient and 'não indica teste de BRCA1/2' in orient[SEM_CRITERIO]['descricao']


@pytest.mark.parametrize('detalhe, trecho', [
    ('mama_ate_50', 'aos 50 anos ou antes'),
    ('mama_triplo_negativo', 'triplo-negativo'),
    ('mama_masculino', 'em homem'),
    ('mama_bilateral', 'bilateral'),
    ('mama_prostata_3_casos', '3 ou mais casos'),
    ('prostata_alto_risco', 'metastático ou de alto risco'),
    ('cancer_ovario', 'ovário'),
    ('cancer_pancreas', 'pâncreas'),
])
def test_criterios_do_nccn_indicam_teste_genetico(detalhe, trecho):
    _, orient = _rodar(['cancer_mama', detalhe] if detalhe.startswith('mama') else [detalhe])
    assert TESTE in orient and trecho in orient[TESTE]['descricao']
    assert SEM_CRITERIO not in orient


def test_criterio_vale_para_homem_tambem():
    _, orient = _rodar(['cancer_ovario'], sexo='masculino')
    assert TESTE in orient


def test_variante_conhecida_na_familia_vai_para_o_teste_em_cascata():
    _, orient = _rodar(['brca', 'cancer_mama', 'mama_ate_50'])
    assert TESTE not in orient and 'Mutação BRCA1/2 na família' in orient


def test_referencias_tem_link():
    from src.utils.reference_links import build_reference_links
    _, orient = _rodar(['cancer_mama', 'mama_ate_50'])
    links = build_reference_links(TESTE, orient[TESTE]['referencia'])
    assert len(links) == 2 and all(l['url'] for l in links)
    assert 'brca-related' in links[1]['url']


def test_colonoscopia_a_cada_5_anos_com_familiar_antes_dos_60():
    recs, _ = _rodar(['cancer_colorretal', 'ccr_antes_60'], idade=42)
    assert recs[COLONO]['subtitulo'].endswith('A cada 5 anos')


def test_um_familiar_aos_60_ou_mais_rastreio_habitual_a_partir_dos_40():
    recs, orient = _rodar(['cancer_colorretal'], idade=42)
    assert recs[COLONO]['subtitulo'].endswith('A cada 10 anos')
    assert 'Câncer colorretal na família: idade do familiar' in orient


def test_colonoscopia_antes_dos_40_vira_orientacao():
    recs, orient = _rodar(['cancer_colorretal', 'ccr_antes_60'], idade=35)
    assert COLONO not in recs and 'Colonoscopia por história familiar de câncer colorretal' in orient


def test_mamografia_por_historia_familiar_com_calculo_de_risco():
    recs, _ = _rodar(['cancer_mama'], idade=42)
    assert 'Tyrer-Cuzick' in recs['Mamografia Digital - Bilateral']['descricao']
    _, orient = _rodar(['cancer_mama'], idade=30)
    assert 'Rastreio de câncer de mama por história familiar' in orient
