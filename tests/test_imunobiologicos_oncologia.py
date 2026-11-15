"""Work-up de imunobiológicos, inibidores de JAK e tratamento sistêmico do câncer (src/utils/condicoes.py)."""
import pytest

from src.utils import condicoes, medicamentos


def _rodar(medicamentos_escolhidos, sexo='feminino', idade=60):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, [], medicamentos.classes_de(medicamentos_escolhidos), [])
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


@pytest.mark.parametrize('nome', ['adalimumabe', 'certolizumabe_pegol', 'tofacitinibe', 'rituximabe', 'secuquinumabe'])
def test_todo_imunobiologico_rastreia_tb_e_hepatites(nome):
    recs, _ = _rodar([nome])
    for titulo in ('Prova tuberculínica (PPD) ou IGRA', 'Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro',
                   'Anticorpos anti-HCV, soro'):
        assert titulo in recs, (nome, titulo)


def test_inibidor_de_jak():
    recs, orient = _rodar(['baricitinibe'])
    assert recs['Hemograma completo com plaquetas']['subtitulo'] == 'Em uso de inibidor de JAK | A cada 3 meses'
    assert recs['Colesterol total e frações, soro']['subtitulo'].endswith('Após 4-8 semanas do início')
    assert 'Inibidor de JAK: quem tem mais risco' in orient
    assert 'Hemograma completo com plaquetas' not in _rodar(['adalimumabe'])[0]


def test_tocilizumabe_e_rituximabe():
    toci, _ = _rodar(['tocilizumabe'])
    assert toci['Alanina aminotransferase, soro']['subtitulo'] == 'Em uso de tocilizumabe | A cada 3 meses'
    rtx, _ = _rodar(['rituximabe'])
    assert rtx['Imunoglobulina G (IgG), soro']['subtitulo'] == 'Em uso de rituximabe | Antes de cada ciclo'


def test_cardio_oncologia():
    recs, _ = _rodar(['doxorrubicina'])
    assert {'Ecocardiograma transtorácico', 'Eletrocardiograma de repouso', 'Troponina, soro',
            'Peptídeo natriurético BNP/PROBNP', 'HBsAg, anti-HBc total e anti-HBs'} <= set(recs)
    her2, _ = _rodar(['trastuzumabe'])
    assert 'A cada 3 meses' in her2['Ecocardiograma transtorácico']['subtitulo']


def test_inibidor_de_checkpoint():
    recs, _ = _rodar(['pembrolizumabe'])
    for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'T4 livre, soro', 'Glicose, soro'):
        assert recs[titulo]['subtitulo'] == 'Inibidor de checkpoint | A cada 4-6 semanas'
    assert recs['Troponina, soro']['referencia'] == condicoes.ESC_ONCO


def test_fluoropirimidina_testa_dpd_e_quimio_implica_imunossupressao():
    recs, orient = _rodar(['capecitabina'])
    assert recs['Genotipagem do gene DPYD (deficiência de DPD)']['subtitulo'] == 'Fluoropirimidina | Antes do tratamento'
    assert 'Imunossupressão' in orient
    assert medicamentos.MARCA['capecitabina'] == ['neoplasia_ativa']
    assert not medicamentos.MARCA.get('leuprorrelina')   # também se usa na endometriose


def test_bloqueio_hormonal():
    homem, _ = _rodar(['leuprorrelina'], sexo='masculino')
    assert {'Densitometria óssea (DEXA)', 'Glicose, soro', 'Colesterol total e frações, soro'} <= set(homem)
    mulher, _ = _rodar(['leuprorrelina'], sexo='feminino')
    assert 'Densitometria óssea (DEXA)' in mulher and 'Glicose, soro' not in mulher
