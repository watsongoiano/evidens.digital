"""Validação e normalização da entrada do check-up.

Princípios:

* dado ausente não vira dado normal: nenhum campo recebe valor padrão clínico;
* valor impossível é recusado com mensagem, em vez de seguir adiante;
* as perguntas de triagem de segurança têm três respostas (sim, não,
  desconhecido), e "desconhecido" nunca é tratado como "não".

A função devolve um dicionário normalizado com as mesmas chaves que o motor de
recomendações já lê (incluindo os nomes alternativos de cada campo), para que o
motor não precise conhecer os formatos aceitos na entrada.
"""
from __future__ import annotations

import math

IDADE_MINIMA = 18
IDADE_MAXIMA = 120

# Acima desta idade, gestação e amamentação deixam de ser perguntadas: a
# ausência de resposta passa a valer como "não se aplica". Uma resposta
# explícita ("sim") continua sendo respeitada em qualquer idade.
IDADE_MAXIMA_TRIAGEM_GESTACAO = 55

SEXOS = ('masculino', 'feminino')

TABAGISMO = {
    'nunca': 'nunca',
    'nunca_fumou': 'nunca',
    'atual': 'atual',
    'fumante_atual': 'atual',
    'ex': 'ex',
    'ex_fumante': 'ex',
    'ex-fumante': 'ex',
}

SIM = 'sim'
NAO = 'nao'
DESCONHECIDO = 'desconhecido'
NAO_APLICAVEL = 'nao_aplicavel'

LACTANTE_MENOR_6M = 'sim_menor_6m'
LACTANTE_6M_OU_MAIS = 'sim_6m_ou_mais'

_SIM_NAO = {
    True: SIM, 'true': SIM, 'on': SIM, 'sim': SIM, '1': SIM,
    False: NAO, 'false': NAO, 'nao': NAO, 'não': NAO, '0': NAO,
    None: DESCONHECIDO, '': DESCONHECIDO, 'desconhecido': DESCONHECIDO,
    'nao_informado': DESCONHECIDO, 'não informado': DESCONHECIDO,
}

_LACTANTE = {
    False: NAO, 'false': NAO, 'nao': NAO, 'não': NAO,
    # "Sim" sem a idade da criança vale como a situação mais restritiva.
    True: LACTANTE_MENOR_6M, 'true': LACTANTE_MENOR_6M, 'sim': LACTANTE_MENOR_6M,
    LACTANTE_MENOR_6M: LACTANTE_MENOR_6M,
    LACTANTE_6M_OU_MAIS: LACTANTE_6M_OU_MAIS,
    None: DESCONHECIDO, '': DESCONHECIDO, 'desconhecido': DESCONHECIDO,
    'nao_informado': DESCONHECIDO, 'não informado': DESCONHECIDO,
}

# nome canônico: (nomes aceitos, mínimo, máximo, rótulo para a mensagem)
CAMPOS_NUMERICOS = {
    'peso': (('peso',), 20, 400, 'Peso (kg)'),
    'altura': (('altura',), 100, 250, 'Altura (cm)'),
    'pas': (('pas', 'pressao_sistolica'), 50, 300, 'Pressão arterial sistólica (mmHg)'),
    'pad': (('pad', 'pressao_diastolica'), 20, 200, 'Pressão arterial diastólica (mmHg)'),
    'colesterol': (('colesterol', 'colesterol_total'), 50, 1000, 'Colesterol total (mg/dL)'),
    'hdl': (('hdl', 'hdl_colesterol'), 5, 200, 'HDL colesterol (mg/dL)'),
    'creatinina': (('creatinina',), 0.1, 25, 'Creatinina sérica (mg/dL)'),
    'hba1c': (('hba1c',), 3, 20, 'HbA1c (%)'),
    'macos_ano': (('macos_ano',), 0, 300, 'Maços-ano'),
    'anos_parou_fumar': (('anos_parou_fumar',), 0, 100, 'Anos desde que parou de fumar'),
    'cd4': (('cd4',), 0, 5000, 'CD4 (células/mm³)'),
    'carga_viral': (('carga_viral',), 0, 100_000_000, 'Carga viral (cópias/mL)'),
}

CAMPOS_LISTA = ('comorbidades', 'medicacoes')
CAMPOS_SIM_NAO_OPCIONAIS = ('em_tarv', 'supressao_viral')
TAMANHO_MAXIMO_TEXTO = 2000
ITENS_MAXIMOS_LISTA = 50


class EntradaInvalida(Exception):
    """A entrada não pode ser usada; `erros` lista campo e mensagem."""

    def __init__(self, erros):
        super().__init__('entrada inválida')
        self.erros = erros


def _vazio(valor) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def ler_numero(valor):
    """Converte para float; aceita vírgula decimal. Devolve None se não for número."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str):
        try:
            numero = float(valor.strip().replace(',', '.'))
        except ValueError:
            return None
    else:
        return None
    if math.isnan(numero) or math.isinf(numero):
        return None
    return numero


def _formatar(numero) -> str:
    if float(numero).is_integer():
        return str(int(numero))
    return str(numero).replace('.', ',')


def _lista_de_textos(valor):
    """Normaliza lista, texto único ou dicionário {chave: verdadeiro} em lista de textos."""
    if _vazio(valor):
        return []
    if isinstance(valor, str):
        return [valor.strip().lower()]
    if isinstance(valor, dict):
        return [str(chave).strip().lower() for chave, marcado in valor.items() if marcado]
    if isinstance(valor, (list, tuple)):
        if not all(isinstance(item, str) for item in valor):
            return None
        return [item.strip().lower() for item in valor if item.strip()]
    return None


def validar_entrada(bruto):
    """Valida o corpo da requisição e devolve `(dados, triagem)`.

    `dados` é o dicionário normalizado lido pelo motor de recomendações.
    `triagem` traz as respostas de segurança para vacinas atenuadas:
    `gestante`, `lactante` e `imunossupressao`.

    Levanta `EntradaInvalida` com a lista de problemas encontrados.
    """
    if not isinstance(bruto, dict) or not bruto:
        raise EntradaInvalida([{'campo': None, 'mensagem': 'Envie os dados do paciente em JSON.'}])

    erros = []
    dados = {}

    def erro(campo, mensagem):
        erros.append({'campo': campo, 'mensagem': mensagem})

    # Dados de HIV podem chegar agrupados em `hiv_data`; passam a valer como campos diretos.
    entrada = dict(bruto)
    agrupado = entrada.pop('hiv_data', None)
    if isinstance(agrupado, dict):
        for chave in ('cd4', 'carga_viral', 'em_tarv', 'supressao_viral'):
            if _vazio(entrada.get(chave)) and not _vazio(agrupado.get(chave)):
                entrada[chave] = agrupado[chave]
    elif agrupado is not None:
        erro('hiv_data', 'Dados de HIV em formato inválido.')

    # Idade: obrigatória, inteira, adulto.
    idade = None
    if _vazio(entrada.get('idade')):
        erro('idade', f'Informe a idade ({IDADE_MINIMA} a {IDADE_MAXIMA} anos).')
    else:
        numero = ler_numero(entrada.get('idade'))
        if numero is None or numero != int(numero):
            erro('idade', 'Idade deve ser um número inteiro de anos.')
        elif not IDADE_MINIMA <= numero <= IDADE_MAXIMA:
            erro('idade', f'Idade fora da faixa atendida ({IDADE_MINIMA} a {IDADE_MAXIMA} anos).')
        else:
            idade = int(numero)
            dados['idade'] = idade

    # Sexo: obrigatório.
    sexo = entrada.get('sexo')
    sexo = sexo.strip().lower() if isinstance(sexo, str) else sexo
    if sexo in SEXOS:
        dados['sexo'] = sexo
    else:
        sexo = None
        erro('sexo', 'Informe o sexo (masculino ou feminino).')

    # Tabagismo: obrigatório e explícito. "Nunca fumou" não é presumido.
    tabagismo = entrada.get('tabagismo')
    tabagismo = tabagismo.strip().lower() if isinstance(tabagismo, str) else tabagismo
    if isinstance(tabagismo, str) and tabagismo in TABAGISMO:
        dados['tabagismo'] = TABAGISMO[tabagismo]
    else:
        erro('tabagismo', 'Informe o tabagismo (nunca fumou, fumante atual ou ex-fumante).')

    # Medidas e exames: opcionais; quando informados, precisam ser plausíveis.
    for canonico, (nomes, minimo, maximo, rotulo) in CAMPOS_NUMERICOS.items():
        informado = next((entrada[nome] for nome in nomes if not _vazio(entrada.get(nome))), None)
        if informado is None:
            continue
        numero = ler_numero(informado)
        if numero is None:
            erro(canonico, f'{rotulo}: valor não numérico.')
        elif not minimo <= numero <= maximo:
            erro(canonico, f'{rotulo}: valor fora da faixa aceita ({_formatar(minimo)} a {_formatar(maximo)}).')
        else:
            for nome in nomes:
                dados[nome] = numero

    if 'pas' in dados and 'pad' in dados and dados['pad'] >= dados['pas']:
        erro('pad', 'Pressão diastólica deve ser menor que a sistólica.')

    # Listas marcadas no formulário.
    for campo in CAMPOS_LISTA:
        lista = _lista_de_textos(entrada.get(campo))
        if lista is None or len(lista) > ITENS_MAXIMOS_LISTA:
            erro(campo, f'{campo}: formato inválido.')
        else:
            dados[campo] = lista

    # História familiar: o motor aceita lista ou dicionário; o tipo é preservado.
    historia = entrada.get('historia_familiar')
    if _vazio(historia):
        dados['historia_familiar'] = []
    elif isinstance(historia, dict):
        dados['historia_familiar'] = historia
    else:
        lista = _lista_de_textos(historia)
        if lista is None or len(lista) > ITENS_MAXIMOS_LISTA:
            erro('historia_familiar', 'historia_familiar: formato inválido.')
        else:
            dados['historia_familiar'] = lista

    # Texto livre de medicações (usado para detectar classes de fármacos).
    medicacoes_continuo = entrada.get('medicacoes_continuo')
    if _vazio(medicacoes_continuo):
        dados['medicacoes_continuo'] = ''
    elif isinstance(medicacoes_continuo, str) and len(medicacoes_continuo) <= TAMANHO_MAXIMO_TEXTO:
        dados['medicacoes_continuo'] = medicacoes_continuo
    else:
        erro('medicacoes_continuo', 'Medicações de uso contínuo: texto inválido ou longo demais.')

    atividade = entrada.get('atividade_fisica')
    if isinstance(atividade, str) and len(atividade) <= 40:
        dados['atividade_fisica'] = atividade.strip().lower()

    for campo in CAMPOS_SIM_NAO_OPCIONAIS:
        valor = entrada.get(campo)
        valor = valor.strip().lower() if isinstance(valor, str) else valor
        resposta = _SIM_NAO.get(valor) if isinstance(valor, (str, bool, type(None))) else None
        if resposta is None:
            erro(campo, f'{campo}: resposta inválida.')
        elif resposta != DESCONHECIDO:
            dados[campo] = resposta

    # Triagem de segurança para vacinas atenuadas: três valores.
    triagem, erros_triagem = normalizar_triagem(entrada, sexo, idade)
    erros.extend(erros_triagem)

    if erros:
        raise EntradaInvalida(erros)

    return dados, triagem


def normalizar_triagem(entrada, sexo, idade):
    """Normaliza as respostas de triagem (gestante, lactante, imunossupressao).

    Devolve `(triagem, erros)`. Resposta ausente ou em branco vale como
    "desconhecido". Para o sexo masculino, gestação e amamentação não se
    aplicam; para mulheres acima de `IDADE_MAXIMA_TRIAGEM_GESTACAO`, a ausência
    de resposta também passa a valer como "não se aplica".

    É usada tanto na geração das recomendações quanto nos pedidos de PDF, para
    que a mesma leitura das respostas valha nos dois momentos.
    """
    erros = []
    entrada = entrada if isinstance(entrada, dict) else {}

    def responder(campo, tabela, rotulo):
        valor = entrada.get(campo)
        valor = valor.strip().lower() if isinstance(valor, str) else valor
        resposta = tabela.get(valor) if isinstance(valor, (str, bool, type(None))) else None
        if resposta is None:
            erros.append({'campo': campo, 'mensagem': f'{rotulo}: resposta inválida.'})
            return DESCONHECIDO
        return resposta

    gestante = responder('gestante', _SIM_NAO, 'Gestante')
    lactante = responder('lactante', _LACTANTE, 'Amamentando')
    imunossupressao = responder('imunossupressao', _SIM_NAO, 'Imunossupressão')

    if sexo == 'masculino':
        if gestante == SIM:
            erros.append({'campo': 'gestante', 'mensagem': 'Gestante: não se aplica ao sexo masculino.'})
        if lactante in (LACTANTE_MENOR_6M, LACTANTE_6M_OU_MAIS):
            erros.append({'campo': 'lactante', 'mensagem': 'Amamentando: não se aplica ao sexo masculino.'})
        gestante = NAO_APLICAVEL
        lactante = NAO_APLICAVEL
    elif sexo == 'feminino' and isinstance(idade, (int, float)) and idade > IDADE_MAXIMA_TRIAGEM_GESTACAO:
        if gestante == DESCONHECIDO:
            gestante = NAO_APLICAVEL
        if lactante == DESCONHECIDO:
            lactante = NAO_APLICAVEL

    triagem = {
        'gestante': gestante,
        'lactante': lactante,
        'imunossupressao': imunossupressao,
    }
    return triagem, erros
