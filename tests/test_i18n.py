"""Versão em inglês: nenhum texto das páginas ou do motor pode ficar sem tradução.

As páginas são escritas em português; static/i18n/en.json guarda o par em inglês de cada texto.
Estes testes falham quando alguém acrescenta ou muda um texto e esquece o par.
"""
from datetime import date, timedelta
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


CAMPO_DA_VARIAVEL = {'fam': 'historia_familiar', 'familia': 'historia_familiar', 'com': 'comorbidades', 'comorbidades': 'comorbidades',
                     'med': 'medicacoes', 'medicacoes': 'medicacoes'}


def _chaves_do_motor():
    """Toda chave de comorbidade, medicação e história familiar que o motor consulta, lida do próprio código
    (``'x' in fam``, ``{'a', 'b'} & com``), das listas de condicoes.py e das caixas do formulário."""
    from src.utils import condicoes, medicamentos

    chaves = {'historia_familiar': set(condicoes.FAMILIA) | set(condicoes.FAMILIA_CHIPS), 'comorbidades': set(condicoes.COMORBIDADES),
              'medicacoes': set(condicoes.MEDICACOES)}
    fonte = '\n'.join(c.read_text(encoding='utf-8') for c in sorted((RAIZ / 'src').rglob('*.py')))
    for chave, variavel in re.findall(r"'([a-z_0-9]+)' in (\w+)\b", fonte):
        if variavel in CAMPO_DA_VARIAVEL:
            chaves[CAMPO_DA_VARIAVEL[variavel]].add(chave)
    for grupo, variavel in re.findall(r"\{([^{}]*)\} & (\w+)\b", fonte):
        if variavel in CAMPO_DA_VARIAVEL:
            chaves[CAMPO_DA_VARIAVEL[variavel]].update(re.findall(r"'([a-z_0-9]+)'", grupo))
    formulario = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    for campo, valor in re.findall(r'name="(comorbidades|historia_familiar|medicacoes)"[^>]*value="([^"]+)"', formulario):
        chaves[campo].add(valor)
    return {campo: sorted(v) for campo, v in chaves.items()}, sorted(set(medicamentos.MEDICAMENTOS) - chaves['medicacoes'])


def _casos_do_motor():
    from src.utils import doses

    base = dict(imunossupressao='nao', lactante='nao', primeira_consulta='sim', gestante='nao', comorbidades=[], historia_familiar=[])
    chaves, medicamentos = _chaves_do_motor()
    # cada medicamento da lista (o motor os reduz a classes: uma idade por sexo basta)
    casos = [dict(base, idade=58, sexo=sexo, tabagismo='nunca', medicacoes=[m]) for sexo in ('masculino', 'feminino') for m in medicamentos]
    # cada chave sozinha, nas idades em que os cortes das diretrizes mudam (25, 30, 35, 40, 45, 50, 60, 65, 70, 75)
    for idade, sexo in itertools.product((19, 27, 33, 38, 42, 47, 52, 58, 63, 68, 73, 78), ('masculino', 'feminino')):
        casos += [dict(base, idade=idade, sexo=sexo, tabagismo='nunca', **{campo: [chave]}) for campo, lista in chaves.items() for chave in lista]
        exames = [dict(peso=p, altura=a, pas=s, pad=d, colesterol=c, hdl=h, creatinina=cr, hba1c=hb) for p, a, s, d, c, h, cr, hb in (
            ('70', '170', '118', '76', '180', '55', '0.9', '5.2'), ('82', '170', '126', '78', '210', '45', '1.0', '5.9'),
            ('95', '168', '134', '86', '240', '38', '1.3', '6.6'), ('110', '165', '165', '100', '280', '30', '1.8', '8.5'),
            ('48', '170', '185', '125', '330', '25', '3.5', '11'), ('70', '170', '125', '', '', '', '', ''))]
        extras = exames + [dict(e, comorbidades=['diabetes']) for e in exames[:4]] + [
            dict(comorbidades=['hiv'], cd4='150', carga_viral='5000', em_tarv='nao', supressao_viral='nao'),
            dict(comorbidades=['hiv'], cd4='650', carga_viral='0', em_tarv='sim', supressao_viral='sim'), dict(comorbidades=['hiv']),
            dict(imunossupressao='sim'), dict(imunossupressao='nao_informado'), dict(lactante='menos_6m'), dict(lactante='6m_ou_mais'),
            dict(lactante='nao_informado'), dict(alcoolismo='sim', doses_semana='30', anos_consumo_alcool='15'), dict(alcoolismo='sim', doses_semana='4'),
            dict(comorbidades=['diabetes', 'hipertensao', 'doenca_renal', 'dcv_aterosclerotica', 'dpoc', 'obesidade', 'dislipidemia', 'has_resistente']),
            dict(comorbidades=['insuficiencia_cardiaca', 'doenca_renal'], medicacoes=['losartana', 'metformina', 'sinvastatina'])]
        for tab, extra in itertools.product(('nunca', 'atual', 'ex'), [dict()] + extras):
            fumo = dict(tabagismo=tab, macos_ano='30' if tab != 'nunca' else '', anos_parou_fumar='5' if tab == 'ex' else '')
            casos.append(dict(base, idade=idade, sexo=sexo, **fumo, **extra))
    for ig, primeira, rh, toxo in itertools.product((6, 10, 13, 16, 20, 24, 27, 30, 34, 36, 39), ('sim', 'nao'), ('negativo', 'positivo', 'nao_sabido'),
                                                    ('suscetivel', 'imune', 'nao_sabida')):
        casos.append(dict(base, idade=30, sexo='feminino', tabagismo='nunca', gestante='sim', idade_gestacional=ig, primeira_consulta=primeira,
                          fator_rh=rh, toxoplasmose=toxo, totg_feito='nao' if ig % 2 else 'sim',
                          gestacao_condicoes=['pe_previa', 'dmg_previo', 'prematuro_previo', 'gemelar'] if ig % 2 else [],
                          comorbidades=['hipertensao'] if ig > 30 else (['diabetes'] if ig < 10 else (['hiv'] if ig == 20 else []))))
    for med, (dose, duracao) in itertools.product(doses.POR_MEDICAMENTO, (('5', '2'), ('20', '4'), ('40', '30'), ('', ''))):
        casos.append(dict(base, idade=55, sexo='feminino', tabagismo='nunca', medicacoes=[med], peso='70', **{f'dose__{med}': dose, f'duracao__{med}': duracao}))
    casos += [dict(), dict(idade='abc'), dict(idade=5, sexo='x', tabagismo='y'), dict(idade=30, sexo='masculino', tabagismo='nunca', gestante='sim'),
              dict(idade=200, sexo='feminino', tabagismo='nunca', pas='20', pad='300', peso='1', altura='10', hba1c='40', colesterol='5', hdl='500', creatinina='40'),
              dict(idade=30, sexo='feminino', tabagismo='nunca', gestante='sim'), dict(idade=30, sexo='feminino', tabagismo='atual'),
              dict(idade=30, sexo='feminino', tabagismo='ex', macos_ano='-3'), dict(idade=30, sexo='feminino', tabagismo='nunca', gestante='sim', idade_gestacional='60')]
    # exames já realizados: em dia, vencido, uma vez na vida, sem intervalo e "junto da HbA1c"
    hoje = date.today()
    recente, antigo = (hoje - timedelta(days=20)).isoformat(), (hoje - timedelta(days=4000)).isoformat()
    anteriores = [{'exame': e, 'data': d} for e, d in (
        ('Hemoglobina glicada (HbA1c), soro', recente), ('Glicose, soro', recente), ('Creatinina, soro', antigo),
        ('Lipoproteína(a) - Lp(a), soro', antigo), ('MAPA de 24 horas', recente), ('Exame fora da lista', recente))]
    casos.append(dict(base, idade=65, sexo='feminino', tabagismo='nunca', comorbidades=['diabetes', 'hipertensao'],
                      exames_anteriores=anteriores))
    casos.append(dict(base, idade=65, sexo='feminino', tabagismo='nunca',
                      exames_anteriores=[{'exame': 'Hemograma completo', 'data': '2999-01-01'}, {'exame': '', 'data': recente},
                                         {'exame': 'Creatinina, soro', 'data': 'ontem'}]))
    casos.append(dict(base, idade=65, sexo='feminino', tabagismo='nunca', exames_anteriores='x'))
    return casos


def test_tudo_o_que_o_motor_devolve_tem_traducao(client):
    """Varre o motor (cada comorbidade, medicação e história familiar em cada faixa de idade; exames em
    todas as faixas; gestação; HIV; doses; erros) e confere que cada frase devolvida tem par em inglês."""
    faltando = set()
    for dados in _casos_do_motor():
        resposta = client.post('/api/checkup-intelligent', json=dados).get_json()
        faltando.update(t for t in _frases(resposta) if not i18n.coberto(t))
    assert not faltando, f'{len(faltando)} frases do motor sem par em inglês, por exemplo: {sorted(faltando)[:8]}'


def test_todo_item_do_catalogo_de_acrescimo_tem_traducao():
    from src.utils.catalogo import catalogo

    faltando = [t for itens in catalogo().values() for t in itens if not i18n.coberto(t)]
    assert not faltando, f'itens do catálogo sem par em inglês: {faltando[:8]}'
    # dois itens não podem virar o mesmo nome: a tela precisa voltar do inglês para o título original
    for categoria, itens in catalogo().items():
        em_ingles = [i18n.traduzir(t).lower() for t in itens]
        repetidos = sorted({t for t in em_ingles if em_ingles.count(t) > 1})
        assert not repetidos, f'{categoria}: itens diferentes com o mesmo nome em inglês: {repetidos}'


# --- PDFs ---------------------------------------------------------------------------------------

def _texto_do_pdf(dados):
    import io

    from pypdf import PdfReader
    assert dados.startswith(b'%PDF')
    return ' '.join('\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(dados)).pages).split())


def test_todo_texto_fixo_das_minutas_tem_traducao():
    from src.utils import pdf_minutas as P

    textos = (list(P.VACINAS_ADMINISTRACAO.values()) + [t for esquema in P.ESQUEMAS_DE_RISCO.values() for t in esquema.values()]
              + [P.POSOLOGIA_PADRAO, P.AVISO, P.LINHA_ASSINATURA, 'Paciente'] + list(P.TITULOS.values()) + list(P.FIXOS))
    faltando = [t for t in textos if not i18n.coberto(t)]
    assert not faltando, f'textos das minutas sem par em inglês: {faltando[:5]}'


def test_pdf_sai_em_ingles_quando_o_idioma_e_ingles(client):
    paciente = {'nome': 'Maria de Souza', 'idade': '30', 'sexo': 'feminino', 'gestante': 'nao', 'lactante': 'nao', 'imunossupressao': 'nao'}
    itens = [{'titulo': 'Creatinina, soro', 'categoria': 'laboratorio', 'quando_pdf': 'Realizar com 24-28 semanas de gestação.'},
             {'titulo': 'Exame digitado pelo médico', 'categoria': 'laboratorio'},
             {'titulo': 'Influenza Tetravalente (Fluarix®, Vaxigrip® ou similar)', 'categoria': 'vacina'}]
    corpo = {'dados_paciente': paciente, 'recomendacoes': itens}

    client.set_cookie(i18n.COOKIE, 'en')
    exames = _texto_do_pdf(client.post('/api/gerar-pdf-exames-laboratoriais', json=corpo).data)
    vacinas = _texto_do_pdf(client.post('/api/gerar-pdf-vacinas', json=corpo).data)
    assert 'LABORATORY TEST REQUEST' in exames and 'I request:' in exames and 'Creatinine, serum' in exames
    assert 'Perform at 24-28 weeks of pregnancy.' in exames and 'Sex: Female' in exames and 'Age: 30 years' in exames
    # nome de gente e item digitado não passam pelo dicionário
    assert 'Patient: Maria de Souza' in exames and 'Exame digitado pelo médico' in exames
    assert "Physician's Signature and Stamp" in exames and 'Page 1/1' in exames
    assert 'VACCINE PRESCRIPTION' in vacinas and 'I prescribe:' in vacinas
    # a posologia é a da vacina certa (escolhida pelo título em português), impressa em inglês
    assert 'Give one dose (0.5 mL), INTRAMUSCULAR, yearly.' in vacinas
    for texto in (exames, vacinas):
        assert not re.search(r'Solicito|Prescrevo|Paciente:|Assinatura|Página|Aplicar', texto), texto

    # o endereço também decide (?lang=), e sem escolha o documento sai em português
    client.set_cookie(i18n.COOKIE, 'pt')
    assert 'SOLICITAÇÃO DE EXAMES LABORATORIAIS' in _texto_do_pdf(client.post('/api/gerar-pdf-exames-laboratoriais', json=corpo).data)
    assert 'LABORATORY TEST REQUEST' in _texto_do_pdf(client.post('/api/gerar-pdf-exames-laboratoriais?lang=en', json=corpo).data)


def test_recusa_do_pdf_vem_em_ingles(client):
    client.set_cookie(i18n.COOKIE, 'en')
    gestante = {'nome': 'Teste', 'idade': '30', 'sexo': 'feminino', 'gestante': 'sim', 'lactante': 'nao', 'imunossupressao': 'nao'}
    resposta = client.post('/api/gerar-pdf-vacinas', json={'dados_paciente': gestante, 'recomendacoes': [
        {'titulo': 'Febre Amarela (Stamaril®)', 'categoria': 'vacina'}]})
    assert resposta.status_code == 400 and resposta.get_json()['codigo'] == 'triagem_vacinas'
    assert resposta.get_json()['error'] == ('The list contains vaccines that the safety screening does not clear for this patient '
                                            '(Yellow fever (Stamaril®)). Generate the recommendations again.')
    vazio = client.post('/api/gerar-pdf-exames-imagem', json={'dados_paciente': gestante, 'recomendacoes': [{'titulo': 'x', 'categoria': 'vacina'}]})
    assert vazio.get_json()['error'] == 'No imaging test found'


def test_erros_de_validacao_vem_em_ingles(client):
    client.set_cookie(i18n.COOKIE, 'en')
    resposta = client.post('/api/checkup-intelligent', json={'idade': 200, 'sexo': 'feminino', 'tabagismo': 'nunca', 'peso': '1'}).get_json()
    assert resposta['error'].startswith('Invalid data: ') and not re.search(r'fora da faixa|Informe|inválid', resposta['error']), resposta['error']
    mensagens = [e['mensagem'] for e in resposta['erros']]
    assert 'Age outside the range covered (18 to 120 years).' in mensagens, mensagens
    assert 'Weight (kg): value outside the accepted range (20 to 400).' in mensagens, mensagens
