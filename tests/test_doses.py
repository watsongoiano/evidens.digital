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
    assert 'Radiografia de coluna torácica e lombar (perfil)' not in _titulos(r)
    # Avaliação basal da dose imunossupressora (Sparling & Butler 2024) e monitorização durante o uso (Feuerstein 2025)
    basal = {'Prova tuberculínica (PPD) ou IGRA', 'Hemograma completo com plaquetas', 'Albumina, soro', 'Creatinina, soro',
             'Ureia, soro', 'Sódio, soro', 'Potássio, soro', 'Cálcio iônico, soro', 'Aspartato aminotransferase, soro',
             'Alanina aminotransferase, soro', 'Fosfatase alcalina, soro', 'Bilirrubinas totais e frações, soro',
             'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro', 'Colesterol total e frações, soro', '25-hidroxivitamina D, soro',
             'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)', 'Avaliação oftalmológica com tonometria e fundoscopia',
             'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'}
    assert basal <= set(_titulos(r)), basal - set(_titulos(r))
    for viva in ('Tríplice Viral', 'Varicela', 'Febre Amarela', 'Dengue'):
        assert not any(viva in t for t in _titulos(r)), viva
    assert 'influenza, COVID-19, pneumocócica' in ' '.join(o['descricao'] for o in r['orientacoes'])


PAINEL_DO_CORTICOIDE = {
    'Prova tuberculínica (PPD) ou IGRA', 'Hemograma completo com plaquetas', 'Albumina, soro', 'Creatinina, soro', 'Ureia, soro',
    'Sódio, soro', 'Potássio, soro', 'Cálcio iônico, soro', 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro',
    'Fosfatase alcalina, soro', 'Bilirrubinas totais e frações, soro', 'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro',
    'Colesterol total e frações, soro', '25-hidroxivitamina D, soro', 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)',
    'Avaliação oftalmológica com tonometria e fundoscopia'}


@pytest.mark.parametrize('dose, semanas', [(5, 2), (5, 26), (2, 52), (40, 16), (None, None)],
                         ids=['baixa-curta', 'baixa-cronica', 'muito-baixa', 'imunossupressora', 'sem-dose'])
def test_work_up_do_corticoide_vale_a_partir_da_dose_baixa(client, dose, semanas):
    """Qualquer corticoide sistêmico em uso recebe a avaliação basal e a monitorização inteiras."""
    extra = {} if dose is None else dict(dose__prednisona=dose, duracao__prednisona=semanas)
    r = _pedir(client, idade=32, medicacoes=['prednisona'], **extra)
    assert PAINEL_DO_CORTICOIDE <= set(_titulos(r)), PAINEL_DO_CORTICOIDE - set(_titulos(r))


def test_dose_e_duracao_so_mudam_osso_e_vacinas(client):
    # dose baixa por pouco tempo: sem densitometria, sem VSR e sem marcar imunossupressão
    r = _pedir(client, idade=52, imunossupressao='nao', medicacoes=['prednisona'], dose__prednisona=5, duracao__prednisona=2)
    assert not {'Densitometria óssea (DEXA)', 'Radiografia de coluna torácica e lombar (perfil)',
                'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'} & set(_titulos(r))
    assert r['triagem_vacinas']['imunossupressao'] == 'nao' and any('Febre Amarela' in t for t in _titulos(r))
    tb = next(x for x in r['recommendations'] if x['titulo'] == 'Prova tuberculínica (PPD) ou IGRA')
    assert tb['subtitulo'].startswith('Corticoide sistêmico') and 'corticoide sistêmico' in tb['descricao']
    # 3 meses ou mais: densitometria em qualquer idade adulta; imagem da coluna a partir dos 40
    jovem = _pedir(client, idade=32, medicacoes=['prednisona'], dose__prednisona=5, duracao__prednisona=26)
    assert 'Densitometria óssea (DEXA)' in _titulos(jovem) and 'Radiografia de coluna torácica e lombar (perfil)' not in _titulos(jovem)
    assert 'Radiografia de coluna torácica e lombar (perfil)' in _titulos(
        _pedir(client, idade=52, medicacoes=['prednisona'], dose__prednisona=5, duracao__prednisona=26))


def test_prednisona_5mg_por_6_meses_indica_densitometria_sem_imunossupressao(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=5, duracao__prednisona=26)
    t = _titulos(r)
    assert 'Densitometria óssea (DEXA)' in t and 'Hemoglobina glicada (HbA1c), soro' in t
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    assert 'Prova tuberculínica (PPD) ou IGRA' in t   # avaliação basal vale em qualquer dose


def test_prednisona_20mg_por_2_meses_rastreia_tuberculose_latente(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=20, duracao__prednisona=8)
    assert 'Prova tuberculínica (PPD) ou IGRA' in _titulos(r)
    assert 'dose alta por 4 semanas' in _orientacoes(r)


def test_curso_curto_em_dose_baixa_nao_muda_vacinas_nem_osso(client):
    r = _pedir(client, medicacoes=['prednisona'], dose__prednisona=10, duracao__prednisona=1)
    assert 'Densitometria óssea (DEXA)' not in _titulos(r)
    assert r['triagem_vacinas']['imunossupressao'] != 'sim'
    assert 'dose ou tempo baixos' in _orientacoes(r)


@pytest.mark.parametrize('remedio, dose, equivalente', [
    ('dexametasona', 4, 26.7), ('hidrocortisona', 100, 25), ('metilprednisolona', 16, 20), ('deflazacorte', 30, 25)])
def test_equivalencia_de_corticoides(remedio, dose, equivalente):
    mais, _, orient = doses.avaliar([remedio], {remedio: {'dose': dose, 'duracao': 3}})
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
    assert 'linha.innerHTML' not in pagina   # campos montados sem interpretar texto como HTML


def test_metotrexato_baixo_com_imunobiologico_continua_imunossupressao(client):
    """A exclusão vale para o metotrexato, não para o adalimumabe que traz a mesma classe."""
    r = _pedir(client, medicacoes=['metotrexato', 'adalimumabe'], dose__metotrexato=15)
    assert r['triagem_vacinas']['imunossupressao'] == 'sim'
    r = _pedir(client, medicacoes=['metotrexato', 'azatioprina'], dose__metotrexato=15)   # azatioprina sem dose
    assert r['triagem_vacinas']['imunossupressao'] == 'sim'


def test_dois_corticoides_com_duracoes_diferentes_nao_somam_a_exposicao():
    """Prednisona 5 mg há 1 ano + dexametasona 4 mg há 1 semana: a dose alta só existe há 1 semana."""
    mais, excluir, orient = doses.avaliar(['prednisona', 'dexametasona'], {
        'prednisona': {'dose': 5, 'duracao': 52}, 'dexametasona': {'dose': 4, 'duracao': 1}})
    assert 'corticoide_imunossupressor' not in mais and 'rastreio_tb_latente' not in mais
    assert not excluir                                    # 5 mg por 52 semanas segue sendo uso crônico
    assert any('3 meses ou mais' in o['titulo'] for o in orient)
    # as duas em dose alta por tempo suficiente somam
    mais, _, _ = doses.avaliar(['prednisona', 'dexametasona'], {
        'prednisona': {'dose': 10, 'duracao': 6}, 'dexametasona': {'dose': 2, 'duracao': 6}})
    assert {'corticoide_imunossupressor', 'rastreio_tb_latente'} <= mais
