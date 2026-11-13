"""Catálogo de itens que o médico pode acrescentar a um pedido ou receita.

Duas fontes, unidas na resposta de `/api/catalogo`:

- os títulos que o próprio motor recomenda (para algum perfil), gerados por
  `scripts/gerar_catalogo.py` em `src/data/catalogo_motor.json` e conferidos
  por teste, para não divergirem do motor;
- a lista `EXTRAS` abaixo, com pedidos frequentes no check-up que o motor não
  recomenda sozinho. Qualquer item pode ainda ser digitado em texto livre.
"""
import json
from pathlib import Path

ARQUIVO_DO_MOTOR = Path(__file__).resolve().parents[1] / 'data' / 'catalogo_motor.json'

EXTRAS = {
    'laboratorio': [
        'Hemograma completo',
        'TSH, soro',
        'T4 livre, soro',
        '25-hidroxivitamina D, soro',
        'Vitamina B12, soro',
        'Ácido fólico, soro',
        'Ferritina, soro',
        'Ferro sérico e saturação de transferrina',
        'Ureia, soro',
        'Ácido úrico, soro',
        'Sódio e potássio, soro',
        'Cálcio total, soro',
        'Magnésio, soro',
        'TGO (AST) e TGP (ALT), soro',
        'Gama-GT, soro',
        'Fosfatase alcalina, soro',
        'Bilirrubinas totais e frações, soro',
        'Proteína C reativa ultrassensível, soro',
        'VHS',
        'Insulina de jejum, soro',
        'Apolipoproteína B, soro',
        'Homocisteína, soro',
        'Urina tipo I (EAS)',
        'Urocultura com antibiograma',
        'Parasitológico de fezes (3 amostras)',
        'Sangue oculto nas fezes (FIT)',
        'PSA total e livre, soro',
        'Testosterona total, soro',
        'FSH e LH, soro',
        'Estradiol, soro',
        'Prolactina, soro',
        'Beta-hCG, soro',
        'Anti-HIV 1 e 2 (4ª geração)',
        'HBsAg, anti-HBc total e anti-HBs',
        'Anti-HCV',
        'VDRL / teste treponêmico',
        'Tipagem sanguínea ABO e fator Rh',
        'Coagulograma (TP/INR e TTPa)',
        'Toxoplasmose IgG e IgM',
        'Rubéola IgG',
        'Citomegalovírus IgG e IgM',
        'Eletroforese de proteínas, soro',
        'Fator reumatoide e anti-CCP',
        'FAN (fator antinuclear)',
    ],
    'imagem': [
        'Radiografia de tórax (PA e perfil)',
        'Ultrassonografia de abdome total',
        'Ultrassonografia de tireoide',
        'Ultrassonografia de mamas',
        'Ultrassonografia pélvica transvaginal',
        'Ultrassonografia de próstata (via abdominal)',
        'Ultrassonografia de vias urinárias',
        'Ultrassonografia obstétrica',
        'Ultrassonografia morfológica (20–24 semanas)',
        'Doppler de carótidas e vertebrais',
        'Doppler arterial de membros inferiores',
        'Mamografia bilateral',
        'Densitometria óssea (coluna lombar e fêmur)',
        'Eletrocardiograma de repouso',
        'Ecocardiograma transtorácico',
        'Teste ergométrico',
        'MAPA de 24 horas',
        'Holter de 24 horas',
        'Escore de cálcio coronariano (TC)',
        'Angiotomografia de coronárias',
        'Tomografia de tórax de baixa dose',
        'Espirometria com prova broncodilatadora',
        'Endoscopia digestiva alta',
        'Colonoscopia',
        'Ressonância magnética de crânio',
        'Avaliação oftalmológica (fundo de olho)',
        'Audiometria tonal',
    ],
    'vacina': [
        # Só o que o motor não recomenda para perfil nenhum; o resto vem do motor.
        'dT (dupla adulto)',
        'Raiva (pré-exposição)',
        'Poliomielite inativada (VIP)',
        'Hepatite B dose dobrada (imunossuprimidos e renais crônicos)',
    ],
}

CATEGORIAS = tuple(EXTRAS)


def _do_motor():
    try:
        return json.loads(ARQUIVO_DO_MOTOR.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def catalogo():
    """{categoria: [títulos em ordem alfabética, sem repetição]}"""
    motor = _do_motor()
    saida = {}
    for categoria in CATEGORIAS:
        vistos, lista = set(), []
        for titulo in list(motor.get(categoria, [])) + EXTRAS[categoria]:
            chave = titulo.strip().lower()
            if chave and chave not in vistos:
                vistos.add(chave)
                lista.append(titulo.strip())
        saida[categoria] = sorted(lista, key=lambda t: t.lower())
    return saida


def titulos_do_motor(app):
    """Varre perfis pelo motor e devolve {categoria: [títulos]} (usado pelo script e pelo teste)."""
    import itertools
    cliente = app.test_client()
    encontrados = {c: set() for c in CATEGORIAS}
    grade = itertools.product(
        (18, 25, 35, 45, 50, 55, 60, 65, 70, 80), ('masculino', 'feminino'), ('nunca', 'atual', 'ex'),
        ([], ['diabetes'], ['hipertensao'], ['hiv'], ['doenca_renal', 'cardiopatia'], ['dpoc'],
         ['obesidade', 'dislipidemia'], ['has_resistente']),
        ([], ['cancer_mama', 'cancer_colorretal', 'cancer_ovario', 'diabetes', 'cardiopatia']),
        ('nao', 'sim'), ('nao', 'sim_menor_6m'))
    for idade, sexo, tab, com, fam, gest, lact in grade:
        if sexo != 'feminino' and (gest == 'sim' or lact != 'nao'):
            continue
        if gest == 'sim' and (idade > 50 or lact != 'nao'):
            continue
        dados = dict(idade=idade, sexo=sexo, tabagismo=tab, comorbidades=com, historia_familiar=fam,
                     imunossupressao='nao', gestante=gest, lactante=lact,
                     macos_ano='30' if tab != 'nunca' else '', anos_parou_fumar='5' if tab == 'ex' else '',
                     cd4='500' if 'hiv' in com else '', alcoolismo='pesado', doses_semana='20')
        resposta = cliente.post('/api/checkup-intelligent', json=dados)
        for rec in resposta.get_json()['recommendations']:
            if rec.get('categoria') in encontrados:
                encontrados[rec['categoria']].add(rec['titulo'])
    return {c: sorted(v, key=lambda t: t.lower()) for c, v in encontrados.items()}
