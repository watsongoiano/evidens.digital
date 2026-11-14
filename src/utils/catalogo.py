"""Catálogo de itens que o médico pode acrescentar a um pedido ou receita.

Duas fontes, unidas na resposta de `/api/catalogo`:

- os títulos que o próprio motor recomenda (para algum perfil), gerados por
  `scripts/gerar_catalogo.py` em `src/data/catalogo_motor.json` e conferidos
  por teste, para não divergirem do motor;
- a lista `EXTRAS` abaixo, com pedidos frequentes no check-up que o motor não
  recomenda sozinho;
- a tabela TUSS de laboratório (`src/data/tuss_laboratorio.json`), com o nome
  da própria TUSS. O exame que já está no catálogo com outro nome não entra
  duas vezes: "Creatinina" (TUSS) é a "Creatinina, soro" que já existe.

Qualquer item pode ainda ser digitado em texto livre.
"""
import functools
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


# Código da tabela que não entra no catálogo. O cálcio total fica de fora por decisão clínica do
# projeto: o cálcio dos pedidos é sempre o iônico.
FORA_DO_CATALOGO = {'40301400'}


@functools.lru_cache(maxsize=4)
def _da_tabela_tuss(ja_no_catalogo):
    """Nomes da tabela TUSS de laboratório cujo exame ainda não está no catálogo.

    `ja_no_catalogo` é uma tupla (a conta é a mesma a cada pedido, e fica guardada).
    """
    from src.utils import tuss
    cobertos, nomes_vistos = set(), set()
    for titulo in ja_no_catalogo:
        nomes_vistos.add(tuss._chave(titulo))
        linhas = tuss.linhas_da_guia(titulo)
        if len(linhas) == 1 and linhas[0]['codigo']:       # exame simples: o código já está representado
            cobertos.add(linhas[0]['codigo'])
    novos = []
    for codigo, nome in tuss.TABELA_DE_LABORATORIO:
        if codigo in cobertos or codigo in FORA_DO_CATALOGO or tuss._chave(nome) in nomes_vistos:
            continue
        nomes_vistos.add(tuss._chave(nome))
        novos.append(nome)
    return tuple(novos)


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
        if categoria == 'laboratorio':
            lista += _da_tabela_tuss(tuple(lista))
        saida[categoria] = sorted(lista, key=lambda t: t.lower())
    return saida


def titulos_do_motor(app):
    """Varre perfis pelo motor e devolve {categoria: [títulos]} (usado pelo script e pelo teste)."""
    import itertools
    cliente = app.test_client()
    encontrados = {c: set() for c in CATEGORIAS}
    grade = itertools.product(
        (18, 25, 35, 45, 50, 55, 60, 65, 70, 80), ('masculino', 'feminino'), ('nunca', 'atual', 'ex'),
        ([], ['diabetes'], ['hipertensao'], ['hiv'], ['doenca_renal', 'dcv_aterosclerotica'], ['insuficiencia_cardiaca'], ['dpoc'],
         ['obesidade', 'dislipidemia'], ['has_resistente']),
        ([], ['cancer_mama', 'cancer_colorretal', 'cancer_ovario', 'diabetes', 'dac_precoce']),
        ('nao', 'sim'), ('nao', 'sim_menor_6m'))
    for idade, sexo, tab, com, fam, gest, lact in grade:
        if sexo != 'feminino' and (gest == 'sim' or lact != 'nao'):
            continue
        if gest == 'sim' and (idade > 50 or lact != 'nao'):
            continue
        dados = dict(idade=idade, sexo=sexo, tabagismo=tab, comorbidades=com, historia_familiar=fam,
                     imunossupressao='nao', gestante=gest, lactante=lact,
                     idade_gestacional='20' if gest == 'sim' else '', primeira_consulta='sim',
                     macos_ano='30' if tab != 'nunca' else '', anos_parou_fumar='5' if tab == 'ex' else '',
                     cd4='500' if 'hiv' in com else '', alcoolismo='pesado', doses_semana='20')
        resposta = cliente.post('/api/checkup-intelligent', json=dados)
        for rec in resposta.get_json()['recommendations']:
            if rec.get('categoria') in encontrados:
                encontrados[rec['categoria']].add(rec['titulo'])
    # Gestação: todas as janelas do pré-natal, com Rh negativo, toxoplasmose suscetível e risco
    for idade, ig in itertools.product((22, 35), (8, 12, 15, 22, 26, 32, 36)):
        dados = dict(idade=idade, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
                     imunossupressao='nao', gestante='sim', lactante='nao', idade_gestacional=ig,
                     primeira_consulta='sim', fator_rh='negativo', toxoplasmose='suscetivel',
                     gestacao_condicoes=['pe_previa', 'dmg_previo', 'prematuro_previo'])
        for rec in cliente.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']:
            if rec.get('categoria') in encontrados:
                encontrados[rec['categoria']].add(rec['titulo'])
    # Listas suspensas (comorbidades, medicações e família): cada item sozinho, em idades e sexos distintos
    from src.utils import condicoes
    for idade, sexo in itertools.product((30, 47, 68), ('masculino', 'feminino')):
        casos = ([dict(comorbidades=[k]) for k in condicoes.COMORBIDADES]
                 + [dict(medicacoes=[k]) for k in condicoes.MEDICACOES]
                 + [dict(historia_familiar=[k]) for k in list(condicoes.FAMILIA) + ['cancer_colorretal', 'cancer_mama', 'dac_precoce']])
        for caso in casos:
            dados = dict(dict(idade=idade, sexo=sexo, tabagismo='nunca', comorbidades=[], medicacoes=[],
                              historia_familiar=[], imunossupressao='nao', gestante='nao', lactante='nao'), **caso)
            for rec in cliente.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']:
                if rec.get('categoria') in encontrados:
                    encontrados[rec['categoria']].add(rec['titulo'])
    return {c: sorted(v, key=lambda t: t.lower()) for c, v in encontrados.items()}
