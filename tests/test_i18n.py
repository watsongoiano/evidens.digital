"""Versão em inglês: nenhum texto das páginas ou do motor pode ficar sem tradução.

As páginas são escritas em português; static/i18n/en.json guarda o par em inglês de cada texto.
Estes testes falham quando alguém acrescenta ou muda um texto e esquece o par.
"""
from datetime import date, timedelta
from html import unescape as html_unescape
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

    chaves = {'historia_familiar': set(condicoes.FAMILIA) | set(condicoes.FAMILIA_CHIPS) | set(condicoes.FAMILIA_DETALHES), 'comorbidades': set(condicoes.COMORBIDADES),
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
            dict(comorbidades=['hiv'], cd4='650', carga_viral='0', em_tarv='sim', supressao_viral='sim'), dict(comorbidades=['hiv'], exames_hiv_previos='nao'), dict(comorbidades=['hiv']),
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
    # gestação: PA por faixa e idade gestacional, fatores de risco de pré-eclâmpsia, HIV, DM e fim da gestação
    for ig, (pas, pad), extra in itertools.product((12, 18, 26, 34, 37, 40), (('', ''), ('145', '95'), ('165', '112')), (
            dict(), dict(comorbidades=['hipertensao']), dict(comorbidades=['lupus', 'saf', 'doenca_renal', 'les_nefrite']),
            dict(gestacao_condicoes=['nulipara', 'pe_familiar', 'fiv', 'intervalo_10_anos', 'desfecho_adverso_previo'], peso='95', altura='160'),
            dict(gestacao_condicoes=['monocorionica', 'rastreio_pe_alto', 'dmg_atual']), dict(comorbidades=['diabetes_tipo_1']),
            dict(comorbidades=['hiv'], cd4='600', carga_viral='0', em_tarv='sim', supressao_viral='sim'), dict(fator_rh='desconhecido'))):
        casos.append(dict(base, idade=36, sexo='feminino', tabagismo='nunca', gestante='sim', idade_gestacional=ig,
                          primeira_consulta='sim' if ig < 20 else 'nao', pas=pas, pad=pad, **{'fator_rh': 'negativo', **extra}))
    for idade, ativa, lactante, com in itertools.product((22, 30, 50), ('sim', 'nao', 'desconhecido'), ('sim_menor_6m', 'nao'),
                                                         ([], ['diabetes_gestacional_previo'])):
        casos.append(dict(base, idade=idade, sexo='feminino', tabagismo='nunca', sexualmente_ativa=ativa, lactante=lactante,
                          comorbidades=com))
    casos += [dict(idade=16, sexo='feminino', tabagismo='nunca', gestante='sim'), dict(base, idade=22, sexo='feminino',
                                                                                       tabagismo='nunca', sexualmente_ativa='x')]
    for med, (dose, duracao) in itertools.product(doses.POR_MEDICAMENTO, (('5', '2'), ('20', '4'), ('40', '30'), ('', ''))):
        casos.append(dict(base, idade=55, sexo='feminino', tabagismo='nunca', medicacoes=[med], peso='70', **{f'dose__{med}': dose, f'duracao__{med}': duracao}))
    casos += [dict(), dict(idade='abc'), dict(idade=5, sexo='x', tabagismo='y'), dict(idade=30, sexo='masculino', tabagismo='nunca', gestante='sim'),
              dict(idade=200, sexo='feminino', tabagismo='nunca', pas='20', pad='300', peso='1', altura='10', hba1c='40', colesterol='5', hdl='500', creatinina='40'),
              dict(idade=30, sexo='feminino', tabagismo='nunca', gestante='sim'), dict(idade=30, sexo='feminino', tabagismo='atual'),
              dict(idade=30, sexo='feminino', tabagismo='ex', macos_ano='-3'), dict(idade=30, sexo='feminino', tabagismo='nunca', gestante='sim', idade_gestacional='60')]
    # colo do útero: cada desfecho do último teste de DNA-HPV, nas idades de corte, com e sem imunossupressão
    from src.utils import colo_utero
    for idade, imuno, resultado in itertools.product((22, 27, 40, 62, 70), ('nao', 'sim'), (None,) + colo_utero.RESULTADOS):
        casos.append(dict(base, idade=idade, sexo='feminino', tabagismo='nunca', imunossupressao=imuno,
                          **({'hpv_resultado': resultado} if resultado else {})))
    for idade, imuno in itertools.product((23, 40, 70), ('nao', 'sim')):
        casos.append(dict(base, idade=idade, sexo='feminino', tabagismo='nunca', imunossupressao=imuno, comorbidades=['histerectomia_total']))
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


# --- Pré-operatório -----------------------------------------------------------------------------

# Campos da resposta de /api/preoperatorio que a tela mostra (ver exibirPreoperatorio em intelligent-tools.html).
# 'classe' e os rótulos das referências também aparecem: a página traduz todo texto que entra no documento.
CAMPOS_LIDOS_PREOP = ('titulo', 'texto', 'resumo', 'motivo', 'nota', 'faixa', 'valor', 'itens', 'conclusao', 'pergunta',
                      'resposta', 'divergencia', 'classe', 'rotulo', 'risco', 'urgencia', 'falta', 'medicamento', 'nome',
                      'ultimo', 'label')
HOJE_PREOP = date(2026, 11, 16)


def _frases_do_preop(valor, dentro=False):
    if isinstance(valor, str):
        if dentro and '<a ' not in valor:
            yield valor
    elif isinstance(valor, list):
        for v in valor:
            yield from _frases_do_preop(v, dentro)
    elif isinstance(valor, dict):
        if 'aha' in valor and 'sbc' in valor and 'outra' in valor:  # exame: as classes viram etiquetas "AHA 2a", "SBC IIa"
            yield from (f'{quem} {valor[quem.lower()]}' for quem in ('AHA', 'SBC') if valor[quem.lower()] not in ('', '—'))
            yield from ([valor['outra']] if valor['outra'] else [])
        for k, v in valor.items():
            yield from _frases_do_preop(v, k in CAMPOS_LIDOS_PREOP)


def _ctx_dos_medicamentos(p, resultado):
    """O mesmo contexto que a rota /api/preoperatorio monta para preop_medicamentos.condutas."""
    pas, pad = p.get('pas'), p.get('pad')
    return {'idade': p['idade'], 'sexo': p['sexo'], 'peso': p['peso'], 'clcr': resultado['clcr'], 'tfg': resultado['tfg'], 'cirurgia': p['cirurgia'],
            'sangramento': p['sangramento'], 'cirurgia_risco_elevado': resultado['contexto']['cir_elev'],
            'urgencia': p['urgencia'], 'neuroaxial': p['neuroaxial'], 'condicoes': set(p['condicoes']),
            'stent': p['stent'], 'aas_indicacao': p['aas_indicacao'],
            'pa_controlada': (pas < 140 and pad < 90) if pas and pad else None}


def _casos_do_preoperatorio():
    """Pedidos fictícios da aba: cada cirurgia em cada urgência, condições instáveis, prazos depois da angioplastia,
    itens do DASI e do STOP-Bang, faixas dos escores, exames já feitos, medicamentos e dados que faltam."""
    from src.utils import preoperatorio as po

    def mes(k):  # 'AAAA-MM' de k meses antes de HOJE_PREOP
        ano, m = divmod(HOJE_PREOP.year * 12 + HOJE_PREOP.month - 1 - k, 12)
        return f'{ano}-{m + 1:02d}'

    pacientes = [
        dict(idade=35, sexo='feminino'),
        dict(idade=58, sexo='masculino', peso=80, creatinina=1.0, hemoglobina=13, asa=2, duracao='menos_2h', spo2=97,
             escadas='sim', condicoes=['hipertensao', 'diabetes'], sangramento='baixo_moderado'),
        dict(idade=82, sexo='masculino', peso=60, creatinina=2.4, hemoglobina=9.5, asa=4, duracao='mais_3h', spo2=89,
             infeccao_respiratoria=True, escadas='nao', cfs=6, sintomas=['angina', 'dispneia'], sangramento='alto',
             condicoes=['dac', 'ic', 'avc_ait', 'diabetes_insulina', 'dpoc', 'tabagismo', 'fa', 'valvopatia', 'doenca_renal',
                        'hepatopatia', 'obesidade', 'hipertensao'], medicacoes=['metoprolol', 'varfarina', 'losartana']),
        dict(idade=70, sexo='feminino', peso=70, hemoglobina=11, asa=3, duracao='2_3h', spo2=93, escadas='sim',
             condicoes=['revascularizacao_cirurgica', 'protese_mecanica', 'marcapasso_cdi'], dasi=['cuidar_de_si', 'andar_em_casa'],
             medicacoes=['apixabana', 'metformina', 'insulina_glargina'], neuroaxial='sim'),
        dict(idade=50, sexo='feminino', peso=95, creatinina=0.8, asa=2, sintomas=['sopro'], dasi=list(po.DASI_ITENS),
             condicoes=['stent'], stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': mes(8)}, pas=185, pad=100,
             medicacoes=['aas_acido_acetilsalicilico', 'clopidogrel']),
    ]
    casos = [dict(paciente, cirurgia=cirurgia, urgencia=urgencia)
             for cirurgia in po.CIRURGIAS for urgencia in po.URGENCIAS for paciente in pacientes]
    base = dict(idade=68, sexo='masculino', peso=75, cirurgia='colectomia', urgencia='eletiva')
    vascular = dict(base, cirurgia='aorta_aberta')
    casos += [dict(base, instaveis=[chave]) for chave in po.INSTAVEIS] + [dict(base, instaveis=list(po.INSTAVEIS))]
    for cirurgia, idade in itertools.product(('colectomia', 'aorta_aberta', 'catarata', 'mama'), (45, 68, 85)):
        casos += [dict(base, cirurgia=cirurgia, idade=idade, condicoes=[chave]) for chave in po.CONDICOES]
        casos += [dict(base, cirurgia=cirurgia, idade=idade, sintomas=[chave]) for chave in po.SINTOMAS]
        casos += [dict(base, cirurgia=cirurgia, idade=idade, condicoes=['dac', 'ic'], escadas=escadas, dasi=dasi, dasi_respondido=True)
                  for escadas in (None, 'sim', 'nao', 'nao_sabe') for dasi in ([], ['correr', 'esporte_extenuante', 'domestico_pesado', 'subir_lance', 'recreacao_moderada'])]
    # DASI e escadas (concordantes e discordantes), STOP-Bang, fragilidade
    casos += [dict(base, condicoes=['dac', 'ic'], dasi=[item], escadas=escadas) for item in po.DASI_ITENS for escadas in (None, 'sim', 'nao')]
    casos += [dict(base, condicoes=['dac', 'ic'], dasi=list(po.DASI_ITENS), escadas=escadas) for escadas in (None, 'sim', 'nao')]
    casos += [dict(base, sexo=sexo, idade=idade, stop_bang=[item], condicoes=com) for item in po.STOP_BANG_ITENS
              for sexo in ('masculino', 'feminino') for idade in (40, 60) for com in ([], ['hipertensao'])]
    casos += [dict(base, sexo=sexo, stop_bang=list(po.STOP_BANG_ITENS), condicoes=['hipertensao']) for sexo in ('masculino', 'feminino')]
    casos += [dict(base, idade=idade, cfs=cfs) for cfs in range(1, 10) for idade in (60, 75)]
    # ARISCAT, AUB-HAS2, VSG-CRI e exames de rotina pelo porte e pela classe ASA
    casos += [dict(base, idade=idade, spo2=spo2, hemoglobina=hb, duracao=duracao, infeccao_respiratoria=infeccao)
              for idade, spo2, hb, duracao, infeccao in itertools.product((40, 60, 85), (None, 88, 93, 98), (None, 9, 13),
                                                                        (None, 'menos_2h', '2_3h', 'mais_3h'), (False, True))]
    casos += [dict(vascular, idade=idade, creatinina=cr, condicoes=com, medicacoes=meds)
              for idade in (55, 65, 75, 85) for cr in (None, 1.0, 2.0, 2.6)
              for com in ([], ['dac', 'ic', 'dpoc', 'tabagismo', 'diabetes_insulina', 'stent'], ['revascularizacao_cirurgica'])
              for meds in ([], ['metoprolol'])]
    casos += [dict(base, cirurgia=cirurgia, asa=asa, condicoes=com, medicacoes=meds, creatinina=cr)
              for cirurgia in ('catarata', 'mama', 'colectomia', 'rtu') for asa in (None, 1, 2, 3, 4, 5)
              for com in ([], ['doenca_renal'], ['dac'], ['hepatopatia']) for meds in ([], ['varfarina'], ['losartana'])
              for cr in (None, 1.1)]
    casos += [dict(base, sexo='feminino', idade=idade, cirurgia=cirurgia) for idade in (30, 55, 56) for cirurgia in ('rtu', 'mama')]
    # Gupta NSQIP MICA: cada cirurgia com estado funcional, classe ASA e creatinina (e sem eles)
    casos += [dict(base, cirurgia=cirurgia, funcional=funcional, asa=asa, creatinina=cr, idade=idade)
              for cirurgia in po.CIRURGIAS for funcional in po.ESTADOS_FUNCIONAIS
              for asa, cr, idade in ((1, None, 40), (3, 1.0, 68), (5, 2.0, 85))]
    casos += [dict(base, cirurgia=cirurgia, funcional=funcional) for cirurgia in ('colectomia', 'catarata') for funcional in po.ESTADOS_FUNCIONAIS]
    # PA e AVC recente adiam a eletiva; diabetes pede HbA1c
    casos += [dict(base, pas=pas, pad=pad, urgencia=urgencia) for pas, pad in ((185, 100), (150, 115), (130, 80), (130, None))
              for urgencia in po.URGENCIAS]
    casos += [dict(base, condicoes=['avc_ait_recente'], urgencia=urgencia) for urgencia in po.URGENCIAS]
    casos += [dict(base, condicoes=['diabetes'], hba1c_dias=dias, urgencia=urgencia) for dias in (None, 0, 20, 45, 92, 200)
              for urgencia in po.URGENCIAS]
    # Angioplastia: tipo, indicação e tempo desde o procedimento (inclusive sem data)
    for tipo, indicacao, meses, urgencia in itertools.product(('farmacologico', 'convencional', 'balao', None), ('sca', 'dac_cronica', None),
                                                             (0, 1, 2, 4, 7, 11, 13, 30, None), ('eletiva', 'tempo_sensivel', 'urgencia')):
        stent = {'tipo': tipo, 'indicacao': indicacao, 'data': mes(meses) if meses is not None else None}
        casos.append(dict(base, condicoes=['stent'], stent=stent, urgencia=urgencia,
                          medicacoes=['aas_acido_acetilsalicilico', 'clopidogrel', 'ticagrelor', 'prasugrel']))
        casos.append(dict(base, condicoes=['stent', 'fa'], stent=stent, urgencia=urgencia, sangramento='alto',
                          medicacoes=['prasugrel', 'apixabana']))
    # data exata (dia, mês e ano): os prazos curtos (14 e 30 dias) sem o aviso de "só mês e ano"
    for tipo, indicacao, dias in itertools.product(('farmacologico', 'convencional', 'balao'), ('sca', 'dac_cronica'), (5, 20, 45, 120, 250, 400)):
        stent = {'tipo': tipo, 'indicacao': indicacao, 'data': (HOJE_PREOP - timedelta(days=dias)).isoformat()}
        casos.append(dict(base, condicoes=['stent'], stent=stent, medicacoes=['aas_acido_acetilsalicilico', 'clopidogrel']))
    casos.append(dict(base, condicoes=['stent']))
    # Glicemia: HbA1c (com valor acima e abaixo de 8%) e glicose já feitas, no diabetes e no rastreio (≥ 35 anos ou fator
    # de risco), em cirurgia eletiva e tempo-sensível
    for dias, a1c, com, idade, urgencia in itertools.product((10, 60, 200), ('7,2', '9,1', None), (['diabetes'], [], ['hipertensao']),
                                                             (30, 50), ('eletiva', 'tempo_sensivel')):
        data = (HOJE_PREOP - timedelta(days=dias)).isoformat()
        anteriores = [dict({'exame': 'Hemoglobina glicada (HbA1c), soro', 'data': data}, **({'resultados': {'hba1c': a1c}} if a1c else {})),
                      {'exame': 'Glicose, soro', 'data': data}]
        casos.append(dict(base, idade=idade, condicoes=com, urgencia=urgencia, exames_anteriores=anteriores))
    # condição instável em cada urgência; AVC ou AIT recente com e sem doença carotídea sintomática
    casos += [dict(base, instaveis=[chave], urgencia=urgencia) for chave in po.INSTAVEIS for urgencia in po.URGENCIAS]
    casos += [dict(base, cirurgia=cirurgia, condicoes=['avc_ait_recente'], urgencia=urgencia)
              for cirurgia in ('endarterectomia_sintomatica', 'stent_carotida_sintomatica', 'carotida_assintomatica', 'catarata')
              for urgencia in po.URGENCIAS]
    # AAS e inibidor de P2Y12 pela indicação, inclusive nas exceções da SBC (neurocirurgia e RTU)
    casos += [dict(base, cirurgia=cirurgia, condicoes=com, aas_indicacao=indicacao, medicacoes=meds)
              for cirurgia in ('neurocirurgia', 'rtu', 'colectomia', 'catarata') for com in ([], ['dac'], ['stent'])
              for indicacao in (None, 'primaria', 'secundaria')
              for meds in (['aas_acido_acetilsalicilico'], ['aas_acido_acetilsalicilico', 'clopidogrel'])]
    # Exames já realizados: ECG, eco e HbA1c recentes ou antigos, e resultados que alimentam os escores
    for meses, sintomas, com in itertools.product((0, 1, 2, 5, 11, 20, 40), ([], ['dispneia'], ['sopro']), (['dac', 'diabetes'], ['valvopatia'])):
        data = (HOJE_PREOP - timedelta(days=30 * meses + 3)).isoformat()
        anteriores = [{'exame': exame, 'data': data} for exame in (
            'Eletrocardiograma de repouso', 'Ecocardiograma transtorácico', 'Hemoglobina glicada (HbA1c), soro',
            'Peptídeo natriurético BNP/PROBNP', 'Troponina, soro', 'Radiografia de tórax', 'Coagulograma (TP/INR e TTPa)')]
        anteriores += [{'exame': 'Creatinina, soro', 'data': data, 'resultados': {'creatinina': '1,9'}},
                       {'exame': 'Hemograma completo com plaquetas', 'data': data, 'resultados': {'hemoglobina': '9,8'}}]
        casos.append(dict(base, idade=72, condicoes=com, sintomas=sintomas, exames_anteriores=anteriores))
        casos.append(dict(base, idade=72, cirurgia='aorta_aberta', condicoes=com, sintomas=sintomas, exames_anteriores=anteriores))
    return casos


def _ctx_extras_dos_medicamentos():
    """Contextos montados à mão para preop_medicamentos.condutas: cada risco de sangramento, ClCr e urgência; anestesia
    neuroaxial; indicações de anticoagulação e de AAS; PA e risco da cirurgia; janelas depois da ICP."""
    base = dict(idade=70, sexo='feminino', peso=70.0, clcr=60.0, sangramento='baixo_moderado', cirurgia_risco_elevado=True,
                urgencia='eletiva', neuraxial=False, pa_controlada=True, condicoes=set(), aas_indicacao=None, stent=None)
    ctxs = [dict(base, sangramento=sang, neuraxial=neuro, clcr=clcr, urgencia=urg, condicoes={'fa'})
            for sang, neuro, clcr, urg in itertools.product((None, 'minimo', 'baixo_moderado', 'alto'), (False, True),
                                                           (None, 10.0, 22.5, 40.0, 60.0), ('eletiva', 'tempo_sensivel', 'urgencia'))]
    condicoes = [set(), {'ic'}, {'ic_fe_reduzida'}, {'hipertensao'}, {'fa'}, {'fa', 'hipertensao', 'diabetes', 'dac'},
                 {'fa', 'avc_ait'}, {'fa', 'avc_ait_recente'}, {'fa', 'avc_ait', 'ic', 'hipertensao', 'diabetes', 'doenca_arterial_periferica'},
                 {'fa', 'avc_ait_recente', 'ic', 'hipertensao', 'diabetes'}, {'fa', 'valvopatia'}, {'tev'}, {'tev_3_12m'},
                 {'tev_recente_3m'}, {'trombofilia_grave'}, {'cancer_ativo'}, {'protese_mecanica'}, {'protese_mecanica', 'fa', 'avc_ait'},
                 {'protese_mecanica_mitral'}, {'avc_ait'}, {'avc_ait_recente'}, {'stent'}, {'dac'}, {'doenca_arterial_periferica'},
                 {'diabetes'}, {'fa', 'ic', 'hipertensao', 'diabetes', 'avc_ait', 'dac'}]
    for com, (idade, sexo) in itertools.product(condicoes, ((None, None), (50, 'masculino'), (68, 'feminino'), (80, 'masculino'), (80, 'feminino'))):
        ctxs.append(dict(base, condicoes=com, idade=idade, sexo=sexo))
    for elevado, pa, com, idade in itertools.product((True, False, None), (True, False, None), (set(), {'ic'}, {'ic_fe_reduzida'}), (50, 70)):
        ctxs.append(dict(base, cirurgia_risco_elevado=elevado, pa_controlada=pa, condicoes=com, idade=idade))
    for indicacao, com, cirurgia in itertools.product((None, 'primaria', 'secundaria'), (set(), {'dac'}, {'stent'}, {'avc_ait'}),
                                                      (None, 'neurocirurgia', 'rtu', 'quadril', 'catarata')):
        ctxs.append(dict(base, aas_indicacao=indicacao, condicoes=com, cirurgia=cirurgia))
    for tipo, indicacao, meses, urg, sang in itertools.product(('farmacologico', 'convencional', 'balao', None), ('sca', 'dac_cronica', None),
                                                              (0, 0.3, 1, 2, 4, 7, 13, None),
                                                              ('eletiva', 'tempo_sensivel', 'urgencia', 'emergencia'),
                                                              (None, 'minimo', 'alto')):
        ctxs.append(dict(base, condicoes={'stent'}, stent={'tipo': tipo, 'indicacao': indicacao, 'meses': meses}, urgencia=urg,
                         sangramento=sang))
    for tipo, dias, neuro in itertools.product(('farmacologico', 'convencional', 'balao'), (5, 20, 45, 100, 200, 300, 400), (False, True)):
        ctxs.append(dict(base, condicoes={'stent', 'fa'}, stent={'tipo': tipo, 'indicacao': None, 'dias': dias}, neuraxial=neuro))
    # prótese mecânica com anticoagulante direto; anestesia neuroaxial com cada ClCr
    for com, clcr, neuro in itertools.product(({'protese_mecanica'}, {'protese_mecanica_mitral', 'fa'}, {'fa'}), (None, 20.0, 45.0, 80.0),
                                              (False, True)):
        ctxs.append(dict(base, condicoes=com, clcr=clcr, neuraxial=neuro, sangramento='alto'))
    return ctxs


def _textos_do_preoperatorio():
    """Todas as frases que a aba "Pré-operatório" pode mostrar para a bateria acima (e as mensagens de erro)."""
    from src.utils import periodicidade, preoperatorio as po, preop_medicamentos as pm

    frases = set()
    todos = sorted(pm.CHAVES_COBERTAS | pm.CHAVES_SO_NA_IC)
    for dados in _casos_do_preoperatorio():
        anteriores, erros = periodicidade.ler_exames_anteriores(dados.pop('exames_anteriores', None), hoje_=HOJE_PREOP)
        assert not erros, erros
        p = po.aplicar_exames_anteriores(po.ler(dados, hoje=HOJE_PREOP), anteriores, hoje=HOJE_PREOP)
        resultado = po.avaliar(p)
        resultado['medicamentos'] = pm.condutas(p['medicacoes'], _ctx_dos_medicamentos(p, resultado))
        frases.update(_frases_do_preop(resultado))
    # cada medicamento com regra, sozinho e junto dos demais (com e sem AAS: a DAPT muda a conduta do inibidor de P2Y12)
    for ctx in _ctx_extras_dos_medicamentos():
        for meds in (todos, [m for m in todos if m != 'aas_acido_acetilsalicilico'], ['varfarina'], ['dabigatrana'],
                     ['apixabana', 'rivaroxabana']):
            frases.update(_frases_do_preop(pm.condutas(meds, ctx)))
    # mensagens de erro da leitura do pedido
    certo = dict(idade=60, sexo='masculino', cirurgia='colectomia', urgencia='eletiva')
    errados = [None, {}, dict(certo, idade='abc'), dict(certo, idade=10), dict(certo, sexo=None), dict(certo, sexo='x'),
               dict(certo, cirurgia=''), dict(certo, cirurgia='x'), dict(certo, urgencia=''), dict(certo, urgencia='x'),
               dict(certo, peso='x'), dict(certo, peso=500), dict(certo, asa=7), dict(certo, duracao='x'), dict(certo, sangramento='x'),
               dict(certo, pas=20), dict(certo, pad=300), dict(certo, spo2=30), dict(certo, escadas='x'), dict(certo, cfs=12),
               dict(certo, aas_indicacao='x'), dict(certo, creatinina=40), dict(certo, hemoglobina=1), dict(certo, hba1c_dias=-1),
               dict(certo, pas=120, pad=130), dict(certo, instaveis={'x': 1}), dict(certo, condicoes={'x': 1}),
               dict(certo, sintomas={'x': 1}), dict(certo, dasi={'x': 1}), dict(certo, stop_bang={'x': 1}),
               dict(certo, condicoes=['stent'], stent={'tipo': 'x'}), dict(certo, condicoes=['stent'], stent={'indicacao': 'x'}),
               dict(certo, condicoes=['stent'], stent={'data': 'ontem'}), dict(certo, condicoes=['stent'], stent={'data': '2999-01'})]
    mensagens = set()
    for dados in errados:
        try:
            po.ler(dados, hoje=HOJE_PREOP)
        except po.EntradaInvalida as erro:
            mensagens.add(str(erro))
    assert len(mensagens) > 20, mensagens  # a bateria precisa mesmo passar pelas mensagens de erro
    return frases | mensagens


def test_tudo_o_que_o_preoperatorio_devolve_tem_traducao():
    """Varre a aba "Pré-operatório" (cada cirurgia e urgência, condições instáveis, angioplastia, DASI, STOP-Bang,
    escores, exames já feitos, cada medicamento com regra e os erros de leitura) e confere que cada frase mostrada tem
    par em inglês."""
    faltando = sorted(t for t in _textos_do_preoperatorio() if not i18n.coberto(t))
    assert not faltando, f'{len(faltando)} frases do pré-operatório sem par em inglês, por exemplo: {faltando[:8]}'


def test_textos_fixos_da_aba_pre_operatorio_tem_traducao():
    """Textos que o script da aba passa por T() e os grupos de risco das cirurgias (atributo label, fora do extrair_textos)."""
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    bloco = html[html.index('// ── Aba "Pré-operatório"'):]
    textos = {t.replace("\\'", "'") for t in re.findall(r"\b(?:T|textoSeguro)\('((?:[^'\\]|\\.)*)'\)", bloco)}
    textos |= {'Indicado', 'Considerar', 'Já realizado'}  # rótulos do estado de cada exame
    textos |= {html_unescape(t) for t in re.findall(r'<optgroup label="([^"]+)"', html)}
    faltando = sorted(t for t in textos if not i18n.coberto(t))
    assert len(textos) > 25 and not faltando, f'textos da aba "Pré-operatório" sem par em inglês: {faltando}'


def test_todo_item_do_catalogo_de_acrescimo_tem_traducao():
    from src.utils import tuss
    from src.utils.catalogo import catalogo

    # Os nomes da tabela TUSS de laboratório ficam em português também no site em inglês: é a
    # terminologia brasileira dos planos de saúde, e é com esse nome que o exame sai na guia.
    da_tuss = set(tuss.DA_TABELA.values())
    faltando = [t for itens in catalogo().values() for t in itens if not i18n.coberto(t) and t not in da_tuss]
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
