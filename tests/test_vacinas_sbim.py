"""Vacinas conforme os calendários SBIm 2026/2027 (adolescente, adulto, idoso), sem duplicatas."""
import pytest

from src.routes.checkup_intelligent import generate_age_sex_recommendations


def _vacinas(idade, sexo='feminino', **kw):
    return [r['titulo'] for r in generate_age_sex_recommendations(idade, sexo, **kw) if r['categoria'] == 'vacina']


@pytest.mark.parametrize('idade', [18, 19, 25, 40, 52, 59, 60, 65, 72, 88])
@pytest.mark.parametrize('sexo', ['feminino', 'masculino'])
def test_sem_vacinas_redundantes(idade, sexo):
    v = ' | '.join(_vacinas(idade, sexo))
    # Hepatites: uma recomendação só
    assert sum(t in v for t in ('Twinrix', 'Havrix', 'Hepatite A (')) <= 1
    assert not ('Twinrix' in v and 'Hepatite B (' in v)
    # Pneumocócica: VPC20 em dose única, sem VPP23 em paralelo
    assert 'Pneumovax' not in v and '23V' not in v
    assert v.count('Pneumocócica') <= 1
    assert v.count('Influenza') == 1
    assert v.count('Sincicial') <= 1


def test_idoso_hd3v_hepatite_b_sem_scr_nem_varicela():
    v = _vacinas(65)
    assert any('alta concentração' in t for t in v)
    assert any(t.startswith('Hepatite B') for t in v)
    assert not any('Tríplice Viral' in t or 'Varicela' in t or 'Twinrix' in t for t in v)


def test_vsr_rotina_a_partir_de_70_e_por_risco_antes():
    recs = {r['titulo']: r for r in generate_age_sex_recommendations(72, 'masculino')}
    vsr = next(r for t, r in recs.items() if 'Sincicial' in t)
    assert vsr['prioridade'] == 'alta'
    recs = {r['titulo']: r for r in generate_age_sex_recommendations(64, 'masculino')}
    assert next(r for t, r in recs.items() if 'Sincicial' in t)['prioridade'] == 'media'
    assert not any('Sincicial' in t for t in _vacinas(45))
    assert any('Sincicial' in t for t in _vacinas(45, has_dpoc=True))


def test_hpv_duas_doses_ate_19_e_tres_a_partir_de_20():
    hpv = lambda i: next(r for r in generate_age_sex_recommendations(i, 'feminino') if 'HPV' in r['titulo'])
    assert '2 doses (0-6 meses)' in hpv(19)['descricao']
    assert '3 doses' in hpv(20)['descricao']


def test_meningococicas_rotina_no_adolescente_e_situacional_no_adulto():
    pri = lambda i: {r['titulo']: r['prioridade'] for r in generate_age_sex_recommendations(i, 'masculino')
                     if 'Meningocócica' in r['titulo']}
    assert set(pri(18).values()) == {'media'} and len(pri(18)) == 2
    assert set(pri(35).values()) == {'baixa'}
    assert len(pri(55)) == 1          # B licenciada até 50 anos
    assert pri(62) == {}               # 60+: só surtos/viagem


def test_gestante_vsr_com_as_duas_janelas():
    rec = next(r for r in generate_age_sex_recommendations(30, 'feminino', is_pregnant=True) if 'Abrysvo' in r['titulo'])
    assert '28 semanas' in rec['descricao'] and '32 a 36' in rec['descricao']
