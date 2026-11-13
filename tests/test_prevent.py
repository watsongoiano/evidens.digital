"""Equações PREVENT conferidas contra os vetores de referência do pacote R preventr
(Mayer, github.com/martingmayer/preventr, tests/testthat/test-estimate_risk.R, já com o
erratum de 2026 dos termos de HbA1c). O caso de referência é: 50 anos, PAS 160 em uso de
anti-hipertensivo, CT 200, HDL 45, sem estatina, diabetes, não fumante, TFG 90, IMC 35."""
import pytest

from src.utils import prevent

CASO = dict(idade=50, colesterol_total=200, hdl=45, pas=160, diabetes=True, fumante=False,
            imc_valor=35, egfr=90, anti_hipertensivo=True, estatina=False)

# (sexo, extras, modelo esperado, 10 anos, 30 anos) — valores: dcv_total, dcva, ic, dac, avc
REFERENCIA = [
    ('feminino', {}, 'base', (0.147, 0.092, 0.081, 0.044, 0.054), (0.53, 0.354, 0.39, 0.198, 0.221)),
    ('masculino', {}, 'base', (0.163, 0.102, 0.106, 0.056, 0.052), (0.514, 0.349, 0.424, 0.216, 0.197)),
    ('feminino', {'hba1c': 9.2}, 'hba1c', (0.181, 0.112, 0.106, 0.054, 0.067), (0.557, 0.378, 0.433, 0.214, 0.241)),
    ('masculino', {'hba1c': 9.2}, 'hba1c', (0.185, 0.117, 0.124, 0.061, 0.063), (0.525, 0.36, 0.442, 0.212, 0.214)),
    ('feminino', {'uacr': 92}, 'uacr', (0.181, 0.111, 0.105, 0.055, 0.065), (0.565, 0.381, 0.437, 0.22, 0.241)),
    ('masculino', {'uacr': 92}, 'uacr', (0.195, 0.123, 0.13, 0.066, 0.063), (0.535, 0.368, 0.448, 0.227, 0.213)),
    # Modelo completo com SDI do CEP 14738 (decil 3): só para validar os coeficientes;
    # em produção o SDI é sempre "ausente".
    ('feminino', {'hba1c': 9.2, 'uacr': 92, '_sdi_decil': 3}, 'full', (0.181, 0.112, 0.108, 0.054, 0.067), (0.539, 0.367, 0.42, 0.21, 0.235)),
    ('masculino', {'hba1c': 9.2, 'uacr': 92, '_sdi_decil': 3}, 'full', (0.185, 0.115, 0.12, 0.063, 0.058), (0.509, 0.345, 0.42, 0.214, 0.193)),
]


@pytest.mark.parametrize('sexo, extras, modelo, dez, trinta', REFERENCIA)
def test_bate_com_os_vetores_do_preventr(sexo, extras, modelo, dez, trinta):
    r = prevent.estimar(sexo=sexo, **CASO, **extras)
    assert r['modelo'] == modelo
    assert tuple(r['dez_anos'][k] for k in ('dcv_total', 'dcva', 'ic', 'dac', 'avc')) == dez
    assert tuple(r['trinta_anos'][k] for k in ('dcv_total', 'dcva', 'ic', 'dac', 'avc')) == trinta


def test_modelo_completo_sem_sdi_usa_termo_de_ausencia():
    r = prevent.estimar(sexo='feminino', hba1c=9.2, uacr=92, **CASO)
    assert r['modelo'] == 'full'
    # Sem o SDI o risco difere do caso com decil 3, mas continua na mesma ordem.
    assert 0.15 < r['dez_anos']['dcv_total'] < 0.22


def test_sem_trinta_anos_acima_de_59():
    r = prevent.estimar(sexo='masculino', **{**CASO, 'idade': 60})
    assert r['trinta_anos'] is None
    assert prevent.estimar(sexo='masculino', **{**CASO, 'idade': 59})['trinta_anos'] is not None


@pytest.mark.parametrize('campo, valor', [('idade', 29), ('idade', 80), ('colesterol_total', 129),
                                          ('hdl', 101), ('pas', 85), ('imc_valor', 40), ('egfr', 14)])
def test_recusa_entrada_fora_da_faixa(campo, valor):
    with pytest.raises(prevent.EntradaForaDaFaixa) as exc:
        prevent.estimar(sexo='feminino', **{**CASO, campo: valor})
    assert exc.value.problemas


def test_hba1c_fora_da_faixa_tambem_e_recusada():
    with pytest.raises(prevent.EntradaForaDaFaixa):
        prevent.estimar(sexo='feminino', hba1c=16, **CASO)


def test_egfr_ckd_epi_2021_confere_com_o_preventr():
    # calc_egfr(1) para 50 anos, mulher → 69 (exemplo da documentação do preventr)
    assert prevent.egfr_ckd_epi_2021(1.0, 50, 'feminino') == 69
    assert prevent.egfr_ckd_epi_2021(1.0, 50, 'masculino') == 92


def test_categorias():
    assert prevent.categoria_sbc_2025(0.049)['categoria'] == 'baixo'
    assert prevent.categoria_sbc_2025(0.05)['categoria'] == 'intermediario'
    assert prevent.categoria_sbc_2025(0.199)['categoria'] == 'intermediario'
    assert prevent.categoria_sbc_2025(0.20)['categoria'] == 'alto'
    assert [prevent.categoria_acc_aha_2026(x)['categoria'] for x in (0.029, 0.03, 0.049, 0.05, 0.099, 0.10)] == \
        ['baixo', 'limitrofe', 'limitrofe', 'intermediario', 'intermediario', 'alto']


def test_regra_do_dm2_da_sbc_2025():
    assert prevent.categoria_sbc_2025(0.03, True, 52, 'masculino')['categoria'] == 'alto'
    assert prevent.categoria_sbc_2025(0.03, True, 52, 'feminino')['categoria'] == 'intermediario'
    assert prevent.categoria_sbc_2025(0.03, True, 56, 'feminino')['categoria'] == 'alto'
    r = prevent.categoria_sbc_2025(0.03, True, 40, 'masculino')
    assert r['categoria'] == 'intermediario' and r['reclassificado_por']
    assert prevent.categoria_sbc_2025(0.25, False)['reclassificado_por'] is None
