"""Equações PREVENT (AHA, 2024) — risco cardiovascular em 10 e 30 anos.

Implementação única, usada pelo servidor, dos modelos *base*, *HbA1c*, *UACR* e
*completo* (HbA1c + UACR, sem o índice de privação social, que é dos EUA).
Os coeficientes vêm de ``src/data/prevent_coeficientes.json`` e os resultados
são conferidos nos testes contra os vetores de referência do pacote R
``preventr`` (que por sua vez bate com a calculadora oficial da AHA), já com
o erratum de 2026 dos termos de HbA1c.

Referências
- Khan SS et al. Development and Validation of the AHA PREVENT Equations.
  Circulation 2024;149:430-449.
- Erratum: Circulation 2026 (doi:10.1161/CIR.0000000000001491).
- Diretriz Brasileira de Dislipidemias e Prevenção da Aterosclerose 2025 (SBC):
  risco de DCVA em 10 anos < 5 % baixo, 5 a < 20 % intermediário, ≥ 20 % alto.
- 2026 ACC/AHA Guideline on the Management of Dyslipidemia: PREVENT-ASCVD em
  10 anos < 3 % baixo, 3 a < 5 % limítrofe, 5 a < 10 % intermediário, ≥ 10 % alto.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_ARQUIVO = Path(__file__).resolve().parent.parent / 'data' / 'prevent_coeficientes.json'
_COEFICIENTES = json.loads(_ARQUIVO.read_text(encoding='utf-8'))

DESFECHOS = ('total_cvd', 'ascvd', 'heart_failure', 'chd', 'stroke')
NOMES = {
    'total_cvd': 'dcv_total',
    'ascvd': 'dcva',
    'heart_failure': 'ic',
    'chd': 'dac',
    'stroke': 'avc',
}

# Faixas em que as equações foram derivadas (as mesmas da calculadora da AHA).
FAIXAS = {
    'idade': (30, 79),
    'colesterol_total': (130, 320),   # mg/dL
    'hdl': (20, 100),                 # mg/dL
    'pas': (90, 180),                 # mmHg
    'imc': (18.5, 39.9),
    'egfr': (15, 140),
    'hba1c': (4.5, 15),
    'uacr': (0.1, 25000),
}

MG_DL_PARA_MMOL_L = 0.02586


class EntradaForaDaFaixa(ValueError):
    def __init__(self, problemas):
        super().__init__('; '.join(problemas))
        self.problemas = problemas


def _arredondar_meio_para_cima(valor, casas):
    """Arredondamento usado pela calculadora oficial (0,0005 → 0,001)."""
    fator = 10 ** casas
    return math.floor(abs(valor) * fator + 0.5 + 1e-12) / fator * (1 if valor >= 0 else -1)


def egfr_ckd_epi_2021(creatinina_mg_dl, idade, sexo):
    """TFG estimada (CKD-EPI 2021, sem raça), em mL/min/1,73 m², inteira."""
    feminino = sexo == 'feminino'
    k = 0.7 if feminino else 0.9
    a1 = -0.241 if feminino else -0.302
    razao = creatinina_mg_dl / k
    valor = 142 * min(razao, 1) ** a1 * max(razao, 1) ** -1.2 * 0.9938 ** idade * (1.012 if feminino else 1)
    return int(_arredondar_meio_para_cima(valor, 0))


def imc(peso_kg, altura_cm):
    return peso_kg / (altura_cm / 100) ** 2


def _preditores(idade, colesterol_total, hdl, pas, diabetes, fumante, imc_valor, egfr,
                anti_hipertensivo, estatina, hba1c, uacr):
    idade_c = (idade - 55) / 10
    nao_hdl = (colesterol_total - hdl) * MG_DL_PARA_MMOL_L - 3.5
    hdl_c = (hdl * MG_DL_PARA_MMOL_L - 1.3) / 0.3
    pas_menor_110 = (min(pas, 110) - 110) / 20
    pas_maior_110 = (max(pas, 110) - 130) / 20
    dm = 1 if diabetes else 0
    fumo = 1 if fumante else 0
    imc_menor_30 = (min(imc_valor, 30) - 25) / 5
    imc_maior_30 = (max(imc_valor, 30) - 30) / 5
    egfr_menor_60 = (min(egfr, 60) - 60) / -15
    egfr_maior_60 = (max(egfr, 60) - 90) / -15
    tx = 1 if anti_hipertensivo else 0
    est = 1 if estatina else 0
    p = {
        'Age per 10 years': idade_c,
        'Age per 10 years squared': idade_c ** 2,
        'non-HDL-C per 1 mmol/L': nao_hdl,
        'HDL-C per 0.3 mmol/L': hdl_c,
        'SBP <110 per 20 mmHg': pas_menor_110,
        'SBP ≥110 per 20 mmHg': pas_maior_110,
        'Diabetes': dm,
        'Current smoking': fumo,
        'BMI <30, per 5 kg/m2': imc_menor_30,
        'BMI 30+, per 5 kg/m2': imc_maior_30,
        'eGFR <60, per -15 ml': egfr_menor_60,
        'eGFR 60+, per -15 ml': egfr_maior_60,
        'Anti-hypertensive use': tx,
        'Statin use': est,
        'Treated SBP ≥110 mm Hg per 20 mm Hg': tx * pas_maior_110,
        'Treated non-HDL-C': est * nao_hdl,
        'Age per 10yr * non-HDL-C per 1 mmol/L': idade_c * nao_hdl,
        'Age per 10yr * HDL-C per 0.3 mmol/L': idade_c * hdl_c,
        'Age per 10yr * SBP ≥110 mm Hg per 20 mmHg': idade_c * pas_maior_110,
        'Age per 10yr * diabetes': idade_c * dm,
        'Age per 10yr * current smoking': idade_c * fumo,
        'Age per 10yr * BMI 30+ per 5 kg/m2': idade_c * imc_maior_30,
        'Age per 10yr * eGFR <60, per -15 ml': idade_c * egfr_menor_60,
        # Índice de privação social: só existe para CEPs dos EUA; aqui é sempre "ausente".
        'SDI decile categories 4-6 vs. 1-3': 0,
        'SDI decile categories 7-10 vs. 1-3': 0,
        'Missing SDI': 1,
        'ln-UACR, mg/g, per 1 ln unit': math.log(uacr) if uacr is not None else 0,
        'Missing UACR/PCR/Dipstick': 0 if uacr is not None else 1,
        # Ordem conforme o erratum de 2026: "no DM" antes de "in DM".
        'HbA1c no DM, per 1%': (hba1c - 5.3) if (hba1c is not None and not dm) else 0,
        'HbA1c in DM, per 1%': (hba1c - 5.3) if (hba1c is not None and dm) else 0,
        'Missing HbA1c': 0 if hba1c is not None else 1,
        'Constant': 1,
    }
    return p


def _escolher_modelo(hba1c, uacr):
    if hba1c is None and uacr is None:
        return 'base'
    if hba1c is not None and uacr is None:
        return 'hba1c'
    if hba1c is None and uacr is not None:
        return 'uacr'
    return 'full'


def _rodar(modelo, horizonte, sexo, preditores, sdi_decil=None):
    tabela = _COEFICIENTES[f'{modelo}_{horizonte}']
    prefixo = 'female_' if sexo == 'feminino' else 'male_'
    if sdi_decil is not None:  # só para a validação contra os vetores do preventr
        preditores = dict(preditores)
        preditores['SDI decile categories 4-6 vs. 1-3'] = 1 if 4 <= sdi_decil <= 6 else 0
        preditores['SDI decile categories 7-10 vs. 1-3'] = 1 if 7 <= sdi_decil <= 10 else 0
        preditores['Missing SDI'] = 0
    resultado = {}
    for desfecho in DESFECHOS:
        betas = tabela[prefixo + desfecho]
        logito = sum(beta * preditores[nome] for beta, nome in zip(betas, tabela['rows']))
        resultado[desfecho] = _arredondar_meio_para_cima(math.exp(logito) / (1 + math.exp(logito)), 3)
    return resultado


def validar(idade, colesterol_total, hdl, pas, imc_valor, egfr, hba1c=None, uacr=None):
    problemas = []
    for nome, valor in (('idade', idade), ('colesterol_total', colesterol_total), ('hdl', hdl),
                        ('pas', pas), ('imc', imc_valor), ('egfr', egfr), ('hba1c', hba1c), ('uacr', uacr)):
        if valor is None:
            continue
        minimo, maximo = FAIXAS[nome]
        if not (minimo <= valor <= maximo):
            problemas.append(f'{nome} = {valor} fora da faixa {minimo}–{maximo}')
    return problemas


def estimar(idade, sexo, colesterol_total, hdl, pas, diabetes, fumante, imc_valor, egfr,
            anti_hipertensivo, estatina, hba1c=None, uacr=None, _sdi_decil=None, _modelo=None):
    """Risco PREVENT em 10 anos (e em 30 anos quando a idade é de 30 a 59).

    Devolve ``{'modelo', 'dez_anos': {...}, 'trinta_anos': {...} | None}`` com as
    probabilidades (0–1, 3 casas) de DCV total, DCVA, IC, DAC e AVC.
    Levanta ``EntradaForaDaFaixa`` quando alguma entrada está fora da faixa de derivação.
    """
    if sexo not in ('feminino', 'masculino'):
        raise ValueError('sexo deve ser "feminino" ou "masculino"')
    problemas = validar(idade, colesterol_total, hdl, pas, imc_valor, egfr, hba1c, uacr)
    if problemas:
        raise EntradaForaDaFaixa(problemas)
    modelo = _modelo or _escolher_modelo(hba1c, uacr)
    p = _preditores(idade, colesterol_total, hdl, pas, diabetes, fumante, imc_valor, egfr,
                    anti_hipertensivo, estatina, hba1c, uacr)
    dez = _rodar(modelo, '10yr', sexo, p, _sdi_decil)
    trinta = _rodar(modelo, '30yr', sexo, p, _sdi_decil) if idade <= 59 else None
    traduzir = lambda r: {NOMES[k]: v for k, v in r.items()}
    return {'modelo': modelo, 'dez_anos': traduzir(dez), 'trinta_anos': traduzir(trinta) if trinta else None}


def categoria_sbc_2025(dcva_10_anos, diabetes=False, idade=None, sexo=None, agravantes=()):
    """Categoria pelo risco de DCVA em 10 anos (Diretriz Brasileira de Dislipidemias 2025).

    Aplica a regra do DM2 da própria diretriz: homem ≥ 50 ou mulher ≥ 56 anos com DM2 é
    alto risco; DM2 mais jovem é no mínimo intermediário. Outros agravantes, LDL ≥ 190,
    estratificadores do diabetes e aterosclerose subclínica ficam a cargo do médico.
    """
    pct = dcva_10_anos * 100
    nivel = 0 if pct < 5 else (1 if pct < 20 else 2)
    motivo = None
    if diabetes and idade is not None and sexo in ('feminino', 'masculino'):
        limite = 56 if sexo == 'feminino' else 50
        minimo = 2 if idade >= limite else 1
        if minimo > nivel:
            nivel = minimo
            motivo = (f'DM2 em {"mulher ≥ 56" if sexo == "feminino" else "homem ≥ 50"} anos'
                      if minimo == 2 else 'DM2 abaixo da idade de alto risco')
    # Agravante de risco: baixo vira intermediário e intermediário vira alto (SBC 2025).
    if agravantes and nivel < 2:
        nivel += 1
        motivo = '; '.join(filter(None, [motivo, 'agravante: ' + ', '.join(agravantes)]))
    categoria = [
        {'categoria': 'baixo', 'rotulo': 'Baixo', 'meta_ldl': '< 115 mg/dL'},
        {'categoria': 'intermediario', 'rotulo': 'Intermediário', 'meta_ldl': '< 100 mg/dL'},
        {'categoria': 'alto', 'rotulo': 'Alto', 'meta_ldl': '< 70 mg/dL'},
    ][nivel]
    return {**categoria, 'reclassificado_por': motivo}


def categoria_acc_aha_2026(dcva_10_anos):
    """Categoria pelo PREVENT-ASCVD em 10 anos (2026 ACC/AHA Dyslipidemia Guideline)."""
    pct = dcva_10_anos * 100
    if pct < 3:
        return {'categoria': 'baixo', 'rotulo': 'Baixo'}
    if pct < 5:
        return {'categoria': 'limitrofe', 'rotulo': 'Limítrofe'}
    if pct < 10:
        return {'categoria': 'intermediario', 'rotulo': 'Intermediário'}
    return {'categoria': 'alto', 'rotulo': 'Alto'}
