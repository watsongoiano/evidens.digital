"""Dose e duração das medicações: imunossupressão, densitometria e rastreio de complicações."""
import pytest

from src.utils import doses

BASE = dict(idade=50, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
            imunossupressao='desconhecido', gestante='nao', lactante='nao')


def _pedir(client, **extra):
    r = client.post('/api/checkup-intelligent', json=dict(BASE, **extra))
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _titulos(r):
    return [x['titulo'] for x in r['recommendations']]


def _orientacoes(r):
    return ' | '.join(o['titulo'] for o in r['orientacoes'])


def test_corticoide_sem_dose_segue_como_cronico_e_pede_o_dado(client):
    r = _pedir(client, medicacoes=['prednisona'])
    assert 'Densitometria óssea (DEXA)' in _titulos(r)
    assert 'informe dose e duração' in _orientacoes(r)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'


def test_prednisona_20mg_por_2_semanas_e_imunossupressora(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=20, duracao__prednisona=2)
    assert r['triagem_vacinas']['imunossupressao'] == 'sim'
    assert 'dose imunossupressora' in _orientacoes(r)
    assert 'Densitometria óssea (DEXA)' not in _titulos(r)          # ainda não chegou a 3 meses
    assert 'Prova tuberculínica (PPD) ou IGRA' not in _titulos(r)   # ainda não chegou a 1 mês


def test_prednisona_5mg_por_6_meses_indica_densitometria_sem_imunossupressao(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=5, duracao__prednisona=26)
    t = _titulos(r)
    assert 'Densitometria óssea (DEXA)' in t and 'Hemoglobina glicada (HbA1c), soro' in t
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    assert 'Prova tuberculínica (PPD) ou IGRA' not in t


def test_prednisona_20mg_por_2_meses_rastreia_tuberculose_latente(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=20, duracao__prednisona=8)
    assert 'Prova tuberculínica (PPD) ou IGRA' in _titulos(r)
    assert 'dose alta por 4 semanas' in _orientacoes(r)


def test_curso_curto_em_dose_baixa_nao_muda_nada(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=10, duracao__prednisona=1)
    assert 'Densitometria óssea (DEXA)' not in _titulos(r)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    assert 'dose ou tempo baixos' in _orientacoes(r)


@pytest.mark.parametrize('remedio, dose, equivalente', [
    ('dexametasona', 4, 26.7), ('hidrocortisona', 100, 25), ('metilprednisolona', 16, 20), ('deflazacorte', 30, 25)])
def test_equivalencia_de_corticoides(remedio, dose, equivalente):
    mais, menos, orient = doses.avaliar([remedio], {remedio: {'dose': dose, 'duracao': 3}})
    assert 'corticoide_imunossupressor' in mais
    assert f'{equivalente:g}'.replace('.', ',') in orient[0]['descricao']


def test_metotrexato_baixa_dose_nao_forca_imunossupressao_mas_monitora(client):
    r = _pedir(client, medicacoes=['metotrexato'], dose__metotrexato=15)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    t = _titulos(r)
    assert 'Aspartato aminotransferase, soro' in t and 'Hemograma completo com plaquetas' in t
    assert 'baixo grau' in _orientacoes(r)


def test_metotrexato_sem_dose_ou_em_dose_alta_e_imunossupressor(client):
    assert _pedir(client, medicacoes=['metotrexato'])['triagem_vacinas']['imunossupressao'] == 'sim'
    assert _pedir(client, medicacoes=['metotrexato'], dose__metotrexato=25)['triagem_vacinas']['imunossupressao'] == 'sim'
    # com o peso, o limite é 0,4 mg/kg/semana: 25 mg em 80 kg é baixo grau
    r = _pedir(client, medicacoes=['metotrexato'], dose__metotrexato=25, peso=80, altura=170)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'


def test_azatioprina_depende_do_peso(client):
    assert _pedir(client, medicacoes=['azatioprina'], dose__azatioprina=100)['triagem_vacinas']['imunossupressao'] == 'sim'
    r = _pedir(client, medicacoes=['azatioprina'], dose__azatioprina=100, peso=70, altura=170)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    assert _pedir(client, medicacoes=['azatioprina'], dose__azatioprina=250, peso=70, altura=170)['triagem_vacinas']['imunossupressao'] == 'sim'


def test_imunobiologico_rastreia_tuberculose_e_hepatite_b(client):
    t = _titulos(_pedir(client, medicacoes=['adalimumabe']))
    for esperado in ('Prova tuberculínica (PPD) ou IGRA', 'Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro'):
        assert esperado in t


def test_hidroxicloroquina_por_5_anos_ou_dose_alta(client):
    assert 'rastreamento anual de retinopatia' in _orientacoes(
        _pedir(client, medicacoes=['hidroxicloroquina'], dose__hidroxicloroquina=400, duracao__hidroxicloroquina=6))
    assert 'rastreamento anual de retinopatia' in _orientacoes(
        _pedir(client, medicacoes=['hidroxicloroquina'], dose__hidroxicloroquina=400, duracao__hidroxicloroquina=1, peso=60, altura=160))
    r = _pedir(client, medicacoes=['hidroxicloroquina'], dose__hidroxicloroquina=200, duracao__hidroxicloroquina=1, peso=60, altura=160)
    assert 'rastreamento anual de retinopatia' not in _orientacoes(r) and 'Hidroxicloroquina' in _orientacoes(r)


def test_bisfosfonato_por_5_anos_pede_reavaliacao(client):
    r = _pedir(client, medicacoes=['alendronato'], duracao__alendronato=6)
    assert 'Densitometria óssea (DEXA)' in _titulos(r) and 'reavaliar a continuidade' in _orientacoes(r)
    assert 'reavaliar a continuidade' not in _orientacoes(_pedir(client, medicacoes=['alendronato'], duracao__alendronato=2))
    assert 'reavaliar a continuidade' in _orientacoes(_pedir(client, medicacoes=['acido_zoledronico'], duracao__acido_zoledronico=3))


def test_dose_invalida_e_recusada(client):
    r = client.post('/api/checkup-intelligent', json=dict(BASE, medicacoes=['prednisona'], dose__prednisona='abc'))
    assert r.status_code == 400 and r.get_json()['erros'][0]['campo'] == 'dose__prednisona'
    r = client.post('/api/checkup-intelligent', json=dict(BASE, medicacoes=['prednisona'], dose__prednisona=-5))
    assert r.status_code == 400


def test_dose_de_medicacao_nao_escolhida_e_ignorada(client):
    r = _pedir(client, medicacoes=[], dose__prednisona=60, duracao__prednisona=20)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim' and 'Densitometria óssea (DEXA)' not in _titulos(r)


def test_tela_pergunta_dose_e_duracao(client):
    pagina = client.get('/intelligent-tools').get_data(as_text=True)
    for chave, (tipo, _) in doses.POR_MEDICAMENTO.items():
        assert f'data-valor="{chave}"' in pagina and f'data-detalhe="{tipo}"' in pagina, chave
    assert 'id="medicacoes-detalhes"' in pagina and 'id="detalhes-medicacao"' in pagina
    assert 'function imunossuprime(item)' in pagina
