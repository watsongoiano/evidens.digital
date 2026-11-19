"""Função renal: TFG estimada (CKD-EPI 2021), categorias G e A e risco de falência renal (KFRE).

- TFG: CKD-EPI 2021 com creatinina, sem raça (Inker, NEJM 2021), a equação que a KDIGO 2024 recomenda para a
  estimativa inicial. Mesma função usada pelo PREVENT (src/utils/prevent.py).
- Categorias: G1-G5 pela TFG e A1-A3 pela relação albumina/creatinina urinária (KDIGO 2024, Tabelas 2 e 3).
- KFRE de 4 variáveis (idade, sexo, TFG e uACR), calibração para fora da América do Norte (Tangri, JAMA 2016,
  eAppendix 2): risco de falência renal tratada (diálise ou transplante) em 2 e 5 anos. A KDIGO 2024 recomenda uma
  equação validada na DRC G3-G5 (1A); 5 anos com 3-5% ajuda a decidir o encaminhamento ao nefrologista (PP 2.2.1) e
  2 anos acima de 40% marca o preparo para a terapia renal substitutiva (PP 2.2.3).

O cálculo só vale para DRC já estabelecida: uma TFG < 60 isolada pede confirmação em 3 meses (KDIGO 2024,
PP 1.1.3.1), e o KFRE só sai com DRC marcada pelo médico, TFG < 60 e uACR informada.
"""
import math

from src.utils import prevent

CKD_EPI = {'rotulo': 'CKD-EPI 2021 (NEJM 2021)', 'link': 'https://doi.org/10.1056/NEJMoa2102953'}
KDIGO = {'rotulo': 'KDIGO 2024 (DRC)', 'link': 'https://doi.org/10.1016/j.kint.2023.10.018'}
KFRE = {'rotulo': 'KFRE (Tangri, JAMA 2016)', 'link': 'https://doi.org/10.1001/jama.2015.18202'}

# KFRE de 4 variáveis (Tangri 2016, eAppendix 2): coeficientes centrados na média da coorte de derivação.
_KFRE_COEF = {'idade': -0.2201, 'idade_media': 7.036, 'masculino': 0.2467, 'masculino_medio': 0.5642,
              'tfg': -0.5567, 'tfg_media': 7.222, 'ln_uacr': 0.4510, 'ln_uacr_medio': 5.137}
# Sobrevida basal fora da América do Norte (o Brasil entra aqui)
_KFRE_S0 = {2: 0.9832, 5: 0.9365}

# Limiares de decisão: TFG (categorias G da KDIGO 2024; 30 e 45 são também os da metformina) e ClCr dos
# anticoagulantes (AHA/ACC, Tabela 13; SBC 2024, Quadro 26).
LIMIARES_TFG = (15, 30, 45, 60, 90)
LIMIARES_CLCR = (15, 30, 50)


def para_exibir(valor, limiares, casas=0):
    """Número para mostrar: arredondado para ``casas``; se o arredondamento o levar para o outro lado de um limiar de
    decisão, sai com mais uma casa, truncada. Uma TFG de 29,6 aparece como 29,6, e não como 30 ao lado de
    "contraindicada abaixo de 30".

    Só para exibir: as comparações com os limiares usam sempre o valor exato, nunca o que esta função devolve.
    """
    def do_mesmo_lado(mostrado):
        return all((mostrado < limite) == (valor < limite) for limite in limiares)

    arredondado = prevent._arredondar_meio_para_cima(valor, casas)
    if do_mesmo_lado(arredondado):
        return int(arredondado) if casas == 0 else arredondado
    for mais in range(casas + 1, casas + 6):
        fator = 10 ** mais
        for folga in (1e-9, 0):          # a folga desfaz o erro de ponto flutuante (29,7 × 10 = 296,99999999999997)
            truncado = math.floor(valor * fator + folga) / fator
            if do_mesmo_lado(truncado):
                return truncado
    return valor


def categoria_g(tfg):
    for limite, cat, rotulo in ((90, 'G1', 'normal ou alta'), (60, 'G2', 'levemente diminuída'),
                                (45, 'G3a', 'leve a moderadamente diminuída'),
                                (30, 'G3b', 'moderada a gravemente diminuída'), (15, 'G4', 'gravemente diminuída')):
        if tfg >= limite:
            return {'categoria': cat, 'rotulo': rotulo}
    return {'categoria': 'G5', 'rotulo': 'falência renal'}


def categoria_a(uacr):
    if uacr < 30:
        return {'categoria': 'A1', 'rotulo': 'normal a levemente aumentada'}
    if uacr <= 300:
        return {'categoria': 'A2', 'rotulo': 'moderadamente aumentada'}
    return {'categoria': 'A3', 'rotulo': 'gravemente aumentada'}


# Estágio pela categoria G (KDIGO 2024: G1-G5; o G3 se divide em 3a e 3b)
ESTAGIO = {'G1': '1', 'G2': '2', 'G3a': '3a', 'G3b': '3b', 'G4': '4', 'G5': '5'}

# Mapa de calor da KDIGO 2024 (Figura 1): risco de desfechos adversos por G x A.
_MAPA = {'G1': ('baixo', 'moderado', 'alto'), 'G2': ('baixo', 'moderado', 'alto'),
         'G3a': ('moderado', 'alto', 'muito alto'), 'G3b': ('alto', 'muito alto', 'muito alto'),
         'G4': ('muito alto', 'muito alto', 'muito alto'), 'G5': ('muito alto', 'muito alto', 'muito alto')}


def risco_kdigo(g, a):
    """Risco de progressão e de eventos pelo mapa G x A da KDIGO 2024 ('baixo' a 'muito alto')."""
    return _MAPA[g][('A1', 'A2', 'A3').index(a)]


def kfre(idade, sexo, tfg, uacr):
    """Risco (0-1) de falência renal tratada em 2 e 5 anos, KFRE de 4 variáveis (fora da América do Norte)."""
    c = _KFRE_COEF
    soma = (c['idade'] * (idade / 10 - c['idade_media'])
            + c['masculino'] * ((1 if sexo == 'masculino' else 0) - c['masculino_medio'])
            + c['tfg'] * (tfg / 5 - c['tfg_media'])
            + c['ln_uacr'] * (math.log(uacr) - c['ln_uacr_medio']))
    return {anos: 1 - s0 ** math.exp(soma) for anos, s0 in _KFRE_S0.items()}


def avaliar(creatinina, idade, sexo, uacr=None, drc=False):
    """Cartão de função renal para a tela, ou None sem creatinina.

    ``drc``: doença renal crônica marcada pelo médico. Sem ela, a TFG sai com a categoria G, mas sem estágio de
    DRC nem KFRE (uma TFG isolada não confirma a doença).
    """
    if not creatinina or sexo not in ('feminino', 'masculino'):
        return None
    # TFG exata: é a que define a categoria G, o corte de 60 e o KFRE. A tela recebe o número de ``para_exibir``.
    tfg = prevent.tfg_ckd_epi_2021(float(creatinina), idade, sexo)
    g = categoria_g(tfg)
    a = categoria_a(float(uacr)) if uacr else None
    cartao = {'tfg': para_exibir(tfg, LIMIARES_TFG), 'g': g, 'a': a, 'drc': bool(drc), 'kfre': None, 'observacoes': [],
              'fontes': [CKD_EPI, KDIGO],
              'estagio': f"Estágio {ESTAGIO[g['categoria']]}" if drc else None,
              'risco_kdigo': risco_kdigo(g['categoria'], a['categoria']) if drc and a else None}
    obs = cartao['observacoes']
    if not drc:
        if tfg < 60:
            obs.append('TFG < 60 sem doença renal crônica marcada: um resultado isolado não confirma a doença. '
                       'Sugerimos repetir a creatinina e a uACR em 3 meses. Com a DRC confirmada e marcada no formulário, '
                       'mostramos o estágio e o risco de falência renal.')
        return cartao
    if tfg >= 60:
        obs.append('O risco de falência renal (KFRE) foi validado na DRC G3 a G5 (TFG < 60).')
        return cartao
    if not uacr:
        obs.append('Com a relação albumina/creatinina urinária (uACR) informada, calculamos o risco de falência '
                   'renal (KFRE) e completamos o estadiamento (categoria A).')
        return cartao
    risco = kfre(idade, sexo, tfg, float(uacr))
    cartao['kfre'] = {'dois_anos': round(risco[2], 3), 'cinco_anos': round(risco[5], 3)}
    cartao['fontes'].append(KFRE)
    if risco[2] > 0.40:
        obs.append('Risco em 2 anos acima de 40%: pela KDIGO 2024 (PP 2.2.3), é o momento de discutir as modalidades '
                   'de terapia renal substitutiva, planejar o acesso vascular e avaliar o transplante.')
    elif risco[5] >= 0.03:
        obs.append('Risco em 5 anos de 3% ou mais: pela KDIGO 2024 (PP 2.2.1), sugerimos considerar o encaminhamento '
                   'ao nefrologista (o limiar fica entre 3% e 5%, junto com os critérios de TFG e uACR).')
    obs.append('KFRE com a calibração para fora da América do Norte; a equação foi derivada com a TFG pela CKD-EPI '
               '2009 e não tem validação em coorte brasileira.')
    return cartao
