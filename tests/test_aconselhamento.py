"""Recomendações A e B do USPSTF sem exame (rastreio por questionário, aconselhamento, medicação preventiva):
cada orientação só aparece para o perfil a que se aplica."""
from src.utils import aconselhamento as A
from src.utils.reference_links import build_reference_links
from tests.test_periodicidade import BASE


def _titulos(*a, **k):
    return [o['titulo'] for o in A.orientacoes(*a, **k)]


def test_adulto_sem_fator_so_recebe_saude_mental_e_alcool():
    assert _titulos(40, 'masculino', tabagismo='nunca', imc=24) == [
        'Rastrear depressão e ansiedade', 'Perguntar sobre álcool e outras drogas']


def test_menor_de_18_nao_recebe_nada():
    assert _titulos(17, 'feminino') == []


def test_ansiedade_so_ate_64_e_so_sem_diagnostico():
    assert 'Rastrear depressão' in _titulos(70, 'masculino')
    assert 'Rastrear ansiedade' in _titulos(40, 'masculino', comorbidades=['depressao'])
    assert not [t for t in _titulos(40, 'masculino', comorbidades=['depressao', 'ansiedade']) if t.startswith('Rastrear dep')]


def test_cada_orientacao_no_seu_perfil():
    fuma = A.orientacoes(50, 'masculino', tabagismo='atual')
    assert any('farmacoterapia aprovada' in o['descricao'] for o in fuma)
    assert not any('Tabagismo' in t for t in _titulos(50, 'masculino', tabagismo='ex'))
    assert 'Rastrear violência por parceiro íntimo' in _titulos(30, 'feminino')
    assert 'Rastrear violência por parceiro íntimo' not in _titulos(30, 'masculino') + _titulos(60, 'feminino')
    assert 'Prevenção de quedas a partir dos 65 anos' in _titulos(65, 'feminino')
    assert 'Prevenção de quedas a partir dos 65 anos' not in _titulos(64, 'feminino')
    assert 'Obesidade: intervenção comportamental intensiva' in _titulos(40, 'masculino', imc=30)
    assert 'Obesidade: intervenção comportamental intensiva' not in _titulos(40, 'masculino', imc=29.9)
    assert 'Aconselhamento de dieta e atividade física' in _titulos(40, 'masculino', comorbidades=['hipertensao'])
    assert 'Aconselhamento para prevenção de IST' in _titulos(30, 'masculino', prep=True)
    assert 'Aconselhamento para prevenção de IST' not in _titulos(30, 'masculino')


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
    for o in A.orientacoes(66, 'feminino', gestante=False, tabagismo='atual', imc=32, prep=True,
                           comorbidades=['hipertensao'], historia_familiar=['cancer_mama']):
        links = build_reference_links(o['titulo'], o['referencia'])
        assert len(links) == 1 and links[0]['url'].endswith('uspstf-a-and-b-recommendations'), o


def test_rota_inclui_as_orientacoes(client):
    r = client.post('/api/checkup-intelligent', json=dict(BASE, tabagismo='atual', macos_ano=10))
    titulos = [o['titulo'] for o in r.get_json()['orientacoes']]
    assert 'Tabagismo: oferecer tratamento para parar de fumar' in titulos
    assert 'Prevenção de quedas a partir dos 65 anos' in titulos


def test_rota_nao_trata_como_lactante_quem_nao_amamenta(client):
    """Homem, mulher idosa sem resposta e mulher jovem sem resposta não recebem orientação de puerpério."""
    for extra in (dict(sexo='masculino', idade=40), dict(sexo='feminino', idade=65), dict(sexo='feminino', idade=30, lactante=None)):
        dados = dict(BASE, **extra)
        if dados.get('lactante') is None:
            dados.pop('lactante')
        titulos = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=dados).get_json()['orientacoes']]
        assert 'Puerpério: apoio ao aleitamento e saúde mental' not in titulos, extra
        if extra['idade'] > 45:
            assert 'Rastrear violência por parceiro íntimo' not in titulos, extra


def test_rota_quimioterapico_exclui_medicacao_para_mama(client):
    titulo = 'Câncer de mama: avaliar medicação para reduzir o risco'
    base = dict(BASE, idade=50, historia_familiar=['cancer_mama'])
    sem = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=base).get_json()['orientacoes']]
    com = [o['titulo'] for o in client.post('/api/checkup-intelligent', json=dict(base, medicacoes=['doxorrubicina'])).get_json()['orientacoes']]
    assert titulo in sem and titulo not in com
