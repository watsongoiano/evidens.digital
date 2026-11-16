"""Recomendações A e B do USPSTF sem exame: cada orientação só aparece para quem está no quadro informado no
formulário (fumante, consumo pesado de álcool, obesidade, fator de risco cardiovascular, PrEP, história familiar
de câncer de mama, gestação, aleitamento)."""
from src.utils import aconselhamento as A
from src.utils.reference_links import build_reference_links
from tests.test_periodicidade import BASE


def _titulos(*a, **k):
    return [o['titulo'] for o in A.orientacoes(*a, **k)]


def test_adulto_fora_de_qualquer_quadro_nao_recebe_nada():
    assert _titulos(40, 'masculino', tabagismo='nunca', imc=24) == []
    assert _titulos(70, 'feminino', alcool='social') == []
    assert _titulos(30, 'feminino') == []          # sem rastreio universal (violência, depressão)
    assert _titulos(17, 'feminino', tabagismo='atual') == []


def test_cada_orientacao_no_seu_quadro():
    alcool = 'Consumo pesado de álcool: aconselhamento breve'
    assert alcool in _titulos(40, 'masculino', alcool='pesado')
    assert alcool not in _titulos(40, 'masculino', alcool='moderado')
    fuma = A.orientacoes(50, 'masculino', tabagismo='atual')
    assert any('farmacoterapia aprovada' in o['descricao'] for o in fuma)
    assert not any('Tabagismo' in t for t in _titulos(50, 'masculino', tabagismo='ex'))
    assert 'Obesidade: intervenção comportamental intensiva' in _titulos(40, 'masculino', imc=30)
    assert 'Obesidade: intervenção comportamental intensiva' not in _titulos(40, 'masculino', imc=29.9)
    assert 'Aconselhamento de dieta e atividade física' in _titulos(40, 'masculino', comorbidades=['hipertensao'])
    assert 'Aconselhamento para prevenção de IST' in _titulos(30, 'masculino', prep=True)


def test_questionario_citado_tem_link_no_nome():
    item = A.orientacoes(40, 'masculino', alcool='pesado')[0]
    assert 'AUDIT' in item['descricao']
    assert item['links'] == [{'texto': 'AUDIT', 'url': A.AUDIT[1]}] and A.AUDIT[1].startswith('https://www.who.int/')


def test_medicacao_para_mama_so_com_historia_familiar_a_partir_dos_35():
    titulo = 'Câncer de mama: avaliar medicação para reduzir o risco'
    assert titulo in _titulos(40, 'feminino', historia_familiar=['cancer_mama'])
    assert titulo not in _titulos(34, 'feminino', historia_familiar=['cancer_mama'])
    assert titulo not in _titulos(40, 'feminino') + _titulos(40, 'masculino', historia_familiar=['cancer_mama'])
    assert titulo not in _titulos(40, 'feminino', historia_familiar=['cancer_mama'], medicacoes=['tamoxifeno'])


def test_gestante():
    orient = A.orientacoes(28, 'feminino', gestante=True, tabagismo='atual', comorbidades=['hipertensao'])
    titulos = [o['titulo'] for o in orient]
    assert 'Gestação: aleitamento, ganho de peso e saúde mental' in titulos
    assert 'Aconselhamento de dieta e atividade física' not in titulos
    assert any('a evidência sobre farmacoterapia é insuficiente' in o['descricao'] for o in orient)


def test_toda_orientacao_tem_link_clicavel():
    for o in A.orientacoes(66, 'feminino', tabagismo='atual', imc=32, prep=True, alcool='pesado',
                           comorbidades=['hipertensao'], historia_familiar=['cancer_mama']):
        links = build_reference_links(o['titulo'], o['referencia'])
        assert len(links) == 1 and links[0]['url'].endswith('uspstf-a-and-b-recommendations'), o


def test_rota_inclui_as_orientacoes_do_quadro(client):
    r = client.post('/api/checkup-intelligent', json=dict(BASE, tabagismo='atual', macos_ano=10, alcoolismo='pesado'))
    orient = r.get_json()['orientacoes']
    titulos = [o['titulo'] for o in orient]
    assert 'Tabagismo: oferecer tratamento para parar de fumar' in titulos
    assert 'Consumo pesado de álcool: aconselhamento breve' in titulos
    assert next(o for o in orient if o['titulo'].startswith('Consumo pesado'))['links'][0]['texto'] == 'AUDIT'


def test_rota_nao_trata_como_lactante_quem_nao_amamenta(client):
    for extra in (dict(sexo='masculino', idade=40), dict(sexo='feminino', idade=65), dict(sexo='feminino', idade=30)):
        dados = dict(BASE, **extra)
        dados.pop('lactante', None)
        titulos = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=dados).get_json()['orientacoes']]
        assert 'Puerpério: apoio ao aleitamento e saúde mental' not in titulos, extra


def test_rota_quimioterapico_exclui_medicacao_para_mama(client):
    titulo = 'Câncer de mama: avaliar medicação para reduzir o risco'
    base = dict(BASE, idade=50, historia_familiar=['cancer_mama'])
    sem = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=base).get_json()['orientacoes']]
    com = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=dict(base, medicacoes=['doxorrubicina'])).get_json()['orientacoes']]
    assert titulo in sem and titulo not in com


def test_tela_poe_o_link_no_nome_do_questionario():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert 'function comLinks(o)' in html and '${comLinks(o)}' in html
