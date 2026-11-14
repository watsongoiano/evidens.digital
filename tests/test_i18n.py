"""Versão em inglês: nenhum texto das páginas ou do motor pode ficar sem tradução.

As páginas são escritas em português; static/i18n/en.json guarda o par em inglês de cada texto.
Estes testes falham quando alguém acrescenta ou muda um texto e esquece o par.
"""
import itertools
import json
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))

import extrair_textos  # noqa: E402
from src.utils import i18n  # noqa: E402

DICIONARIO = json.loads((RAIZ / 'static' / 'i18n' / 'en.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('pagina', extrair_textos.PAGINAS)
def test_todo_texto_da_pagina_tem_traducao(pagina):
    faltando = [t for t in extrair_textos.textos_da_pagina(pagina) if not i18n.coberto(t)]
    assert not faltando, f'{pagina}: textos sem par em static/i18n/en.json: {faltando[:10]}'


@pytest.mark.parametrize('pagina', extrair_textos.PAGINAS)
def test_pagina_carrega_os_idiomas_e_tem_o_seletor(pagina):
    html = (RAIZ / pagina).read_text(encoding='utf-8')
    assert '<script src="/static/i18n.js"></script>' in html.split('</head>')[0]
    assert 'data-idioma' in html


def test_painel_do_administrador_fica_em_portugues():
    assert 'i18n.js' not in (RAIZ / 'admin.html').read_text(encoding='utf-8')


def test_dicionario_esta_bem_formado():
    assert set(DICIONARIO) == {'textos', 'padroes', 'manter'}
    for pt, en in DICIONARIO['textos'].items():
        assert pt == i18n.normalizar(pt) and en and en == i18n.normalizar(en), pt
    for expressao, saida in DICIONARIO['padroes']:
        grupos = re.compile(expressao).groups
        assert expressao.startswith('^') and expressao.endswith('$'), expressao
        # só o que os dois lados entendem igual: sem grupos nomeados nem olhar para trás
        assert '(?P' not in expressao and '(?<' not in expressao, expressao
        usados = {int(n) for n in re.findall(r'[$%](\d)', saida)}
        assert usados and max(usados) <= grupos, (expressao, saida)
    # os padrões que só repartem a frase (" | ") vêm antes dos que casam com um trecho dela
    assert DICIONARIO['padroes'][0][0] == r'^(.+?) \| (.+)$'


def test_arquivos_de_idioma_sao_servidos(anonimo):
    assert anonimo.get('/static/i18n.js').status_code == 200
    resposta = anonimo.get('/static/i18n/en.json')
    assert resposta.status_code == 200 and 'textos' in resposta.get_json()


def test_traducao_de_frases_compostas_numeros_e_listas():
    t = i18n.traduzir
    assert t('Adultos ≥18 anos | Anual | Também: Em uso de lítio | A cada 6 meses') == 'Adults ≥18 years | Yearly | Also: On lithium | Every 6 months'
    assert t('Para calcular o PREVENT faltam: colesterol total, HDL, peso.') == 'To calculate PREVENT the following are missing: total cholesterol, HDL, weight.'
    assert t('Deflazacorte 16,7 mg/dia de prednisona (equivalente) há 4 semanas').startswith('Deflazacort 16.7 mg/day')
    assert t('7.000') == '7,000' and t('7,4%') == '7.4%' and t('1.0') == '1.0'
    assert t('Altura (cm): valor fora da faixa aceita (100 a 250).') == 'Height (cm): value outside the accepted range (100 to 250).'
    # português fica como está, e texto sem par não é inventado
    assert i18n.traduzir('Hemograma completo', 'pt') == 'Hemograma completo'
    assert t('frase que não existe no dicionário') == 'frase que não existe no dicionário'
    assert not i18n.coberto('frase que não existe no dicionário')


# Campos da resposta do check-up que a pessoa lê. Os demais são identificadores, links ou dados.
CAMPOS_LIDOS = ('titulo', 'descricao', 'subtitulo', 'motivo', 'mensagem', 'rotulo', 'observacao', 'quando_pdf', 'referencia', 'label', 'meta_ldl')


def _frases(valor, chave=None, dentro=False):
    if isinstance(valor, str):
        if dentro and '<a ' not in valor:
            yield valor
    elif isinstance(valor, list):
        for v in valor:
            yield from _frases(v, chave, dentro)
    elif isinstance(valor, dict):
        for k, v in valor.items():
            yield from _frases(v, k, k in CAMPOS_LIDOS or (dentro and k in ('faltando', 'problemas')) or k in ('faltando', 'problemas'))


def test_tudo_o_que_o_motor_devolve_tem_traducao(client):
    """Varre perfis variados (adulto, comorbidades, medicações, família, gestação, HIV, doses, erros)
    e confere que cada frase devolvida tem par em inglês."""
    from src.utils import condicoes, doses

    def chaves(x):
        return list(x.keys()) if isinstance(x, dict) else [i['id'] if isinstance(i, dict) else i[0] for i in x]

    base = dict(imunossupressao='nao', lactante='nao', primeira_consulta='sim', gestante='nao', comorbidades=[], historia_familiar=[])
    casos = []
    for idade, sexo, tab in itertools.product((22, 47, 58, 68, 78), ('masculino', 'feminino'), ('nunca', 'atual', 'ex')):
        fumo = dict(tabagismo=tab, macos_ano='30' if tab != 'nunca' else '', anos_parou_fumar='5' if tab == 'ex' else '')
        extras = [dict(), dict(comorbidades=['hiv'], cd4='150', carga_viral='5000'), dict(imunossupressao='nao_informado'),
                  dict(peso='110', altura='165', pas='165', pad='100', colesterol_total='280', hdl='30', creatinina='1.8', hba1c='8.5'),
                  dict(comorbidades=['diabetes', 'hipertensao', 'doenca_renal', 'dcv_aterosclerotica', 'dpoc', 'obesidade', 'dislipidemia', 'has_resistente'])]
        if (idade, tab) == (58, 'nunca'):  # cada item das listas, sozinho
            extras += ([dict(comorbidades=[k]) for k in chaves(condicoes.COMORBIDADES)] + [dict(historia_familiar=[k]) for k in chaves(condicoes.FAMILIA)]
                       + [dict(medicacoes=[k]) for k in chaves(condicoes.MEDICACOES)])
        casos += [dict(base, idade=idade, sexo=sexo, **fumo, **e) for e in extras]
    for ig, primeira, rh in itertools.product((6, 10, 13, 20, 24, 30, 36, 39), ('sim', 'nao'), ('negativo', 'positivo')):
        casos.append(dict(base, idade=30, sexo='feminino', tabagismo='nunca', gestante='sim', idade_gestacional=ig, primeira_consulta=primeira,
                          fator_rh=rh, toxoplasmose='suscetivel', gestacao_condicoes=['pe_previa', 'dmg_previo', 'prematuro_previo', 'gemelar']))
    for med, (dose, duracao) in itertools.product(doses.POR_MEDICAMENTO, (('5', '2'), ('40', '30'), ('', ''))):
        casos.append(dict(base, idade=55, sexo='feminino', tabagismo='nunca', medicacoes=[med], peso='70', **{f'dose__{med}': dose, f'duracao__{med}': duracao}))
    casos += [dict(idade=200, sexo='feminino', tabagismo='nunca', pas='20', peso='1', hba1c='40'), dict(idade=30, sexo='masculino', tabagismo='nunca', gestante='sim'), dict()]

    faltando = set()
    for dados in casos:
        resposta = client.post('/api/checkup-intelligent', json=dados).get_json()
        faltando.update(t for t in _frases(resposta) if not i18n.coberto(t))
    assert not faltando, f'{len(faltando)} frases do motor sem par em inglês, por exemplo: {sorted(faltando)[:8]}'
