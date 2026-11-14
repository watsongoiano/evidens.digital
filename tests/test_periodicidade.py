"""Periodicidade: exame já feito e dentro do intervalo da própria regra não é pedido de novo."""
from datetime import date

import pytest

from src.utils import periodicidade as P
from test_i18n import _casos_do_motor

HOJE = date(2026, 11, 14)
BASE = dict(idade=65, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
            comorbidades=['diabetes', 'hipertensao'], historia_familiar=[], medicacoes=[])


@pytest.fixture(autouse=True)
def _hoje_fixo(monkeypatch):
    monkeypatch.setattr(P, 'hoje', lambda: HOJE)


def _pedir(client, exames, **mudancas):
    resposta = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames, **mudancas))
    assert resposta.status_code == 200, resposta.get_json()
    dados = resposta.get_json()
    pedidos = {r['titulo']: r for r in dados['recommendations']}
    em_dia = {i['titulo']: i for i in dados['nao_incluidas'] if i['estado'] == 'em_dia'}
    return pedidos, em_dia


def _feito(exame, data):
    return {'exame': exame, 'data': data}


# --- Leitura da periodicidade que a regra já traz ------------------------------

@pytest.mark.parametrize('trecho, esperado', [
    ('Anual', ('anos', 1)), ('Anual ou conforme indicação', ('anos', 1)), ('Anual a partir de 30 anos', ('anos', 1)),
    ('Bienal', ('anos', 2)), ('Semestral ou conforme indicação', ('meses', 6)),
    ('A cada 6 meses', ('meses', 6)), ('A cada 3-6 meses', ('meses', 3)), ('A cada 4-6 anos', ('anos', 4)),
    ('A cada 8-12 semanas', ('semanas', 8)), ('A cada 3 anos se normal', ('anos', 3)),
    ('Inicial e a cada 1-2 anos', ('anos', 1)), ('FIB-4 a cada 1-2 anos', ('anos', 1)),
    ('Pelo menos a cada 3 anos', ('anos', 3)),
    ('Dose única na vida', P.UMA_VEZ), ('Pelo menos 1x na vida', P.UMA_VEZ), ('Uma vez', P.UMA_VEZ),
    ('Junto da HbA1c', P.JUNTO_DA_HBA1C),
    ('Basal', None), ('Conforme necessidade', None), ('1ª consulta', None), ('A partir de 40 anos', None),
    ('Adultos ≥40 anos', None), ('', None),
])
def test_intervalo_do_trecho(trecho, esperado):
    assert P.intervalo_do_trecho(trecho) == esperado


def test_faixa_usa_o_limite_inferior_e_varias_indicacoes_usam_o_menor_intervalo():
    assert P.intervalo('Diabéticos | A cada 3-6 meses')['n'] == 3
    regra = P.intervalo('Adultos | Anual | Também: Em uso de lítio | A cada 6 meses')
    assert (regra['unidade'], regra['n'], regra['texto']) == ('meses', 6, 'A cada 6 meses')
    regra = P.intervalo('Adultos ≥40 anos | A cada 4-6 anos | Também: Em uso de antipsicótico de 2ª geração | Anual')
    assert (regra['unidade'], regra['n']) == ('anos', 1)
    assert P.intervalo('Homens | 65-75 anos | Uma vez')['tipo'] == P.UMA_VEZ
    assert P.intervalo('BRCA | Portador ou parente de 1º grau não testado | Anual a partir de 30 anos')['n'] == 1


@pytest.mark.parametrize('subtitulo', [
    'Osteoporose', '', None, 'Gestantes | 1ª consulta', 'Adultos com suspeita de HAS | Conforme necessidade',
    'Diabéticos | Anual | Também: Corticoide sistêmico | Basal',          # uma indicação sem intervalo: não adia
    'Mulheres | Anual | Também: BRCA1/2 na família | Portador ou parente de 1º grau não testado | A partir de 40 anos',
])
def test_sem_intervalo_em_alguma_indicacao_nao_ha_intervalo(subtitulo):
    assert P.intervalo(subtitulo) is None


def test_soma_de_datas_no_calendario():
    assert P.somar(date(2026, 1, 31), 'meses', 1) == date(2026, 2, 28)
    assert P.somar(date(2024, 2, 29), 'anos', 1) == date(2025, 2, 28)
    assert P.somar(date(2026, 10, 1), 'meses', 3) == date(2027, 1, 1)
    assert P.somar(date(2026, 10, 1), 'semanas', 8) == date(2026, 11, 26)


def test_toda_periodicidade_do_motor_esta_classificada(client):
    """Trecho novo de subtítulo tem de ser classificado: intervalo, uma vez, ou sem intervalo (de propósito)."""
    soltos = {}
    for dados in _casos_do_motor():
        resposta = client.post('/api/checkup-intelligent', json=dados).get_json() or {}
        for rec in resposta.get('recommendations') or []:
            if rec.get('categoria') not in ('laboratorio', 'imagem'):
                continue
            for _grupo, trechos in P.indicacoes(rec.get('subtitulo')):
                for trecho in trechos:
                    if P.intervalo_do_trecho(trecho) is None and trecho.lower() not in P.SEM_INTERVALO:
                        soltos.setdefault(trecho, rec['titulo'])
    assert not soltos, f'periodicidade sem classificação em src/utils/periodicidade.py: {soltos}'


# --- No motor -----------------------------------------------------------------

def test_sem_exames_informados_nada_muda(client):
    resposta = client.post('/api/checkup-intelligent', json=BASE).get_json()
    pedidos, em_dia = _pedir(client, [])
    assert not em_dia and list(pedidos) == [r['titulo'] for r in resposta['recommendations']]
    assert all('ultimo_exame' not in r for r in pedidos.values())


def test_exame_dentro_do_intervalo_sai_do_pedido_com_a_data_do_proximo(client):
    pedidos, em_dia = _pedir(client, [_feito('Hemoglobina glicada (HbA1c), soro', '2026-10-01'),
                                      _feito('Densitometria óssea (DEXA)', '2025-06-10')])
    assert 'Hemoglobina glicada (HbA1c), soro' not in pedidos and 'Densitometria óssea (DEXA)' not in pedidos
    hba1c = em_dia['Hemoglobina glicada (HbA1c), soro']
    assert hba1c['motivo'] == 'Feito em 01/10/2026. Periodicidade: A cada 3-6 meses. Próximo a partir de 01/01/2027.'
    assert hba1c['categoria'] == 'laboratorio' and hba1c['referencia'].startswith('ADA')
    assert em_dia['Densitometria óssea (DEXA)']['motivo'].endswith('Próximo a partir de 10/06/2027.')


def test_intervalo_vencido_continua_no_pedido_e_avisa(client):
    pedidos, em_dia = _pedir(client, [_feito('Hemoglobina glicada (HbA1c), soro', '2026-08-14'),
                                      _feito('Creatinina, soro', '2025-01-10')])
    assert not em_dia
    assert pedidos['Hemoglobina glicada (HbA1c), soro']['ultimo_exame'] == (
        'Feito em 14/08/2026. Periodicidade: A cada 3-6 meses. Intervalo vencido desde 14/11/2026.')
    assert 'Intervalo vencido desde 10/01/2026' in pedidos['Creatinina, soro']['ultimo_exame']


def test_exame_de_uma_vez_na_vida_nao_se_repete(client):
    pedidos, em_dia = _pedir(client, [_feito('Lipoproteína(a) - Lp(a), soro', '2009-03-02'), _feito('Anti-HCV', '2015-01-01')])
    assert 'Lipoproteína(a) - Lp(a), soro' not in pedidos and 'Anti-HCV IgG, soro' not in pedidos
    assert 'uma única vez (Dose única na vida)' in em_dia['Lipoproteína(a) - Lp(a), soro']['motivo']
    assert 'Anti-HCV IgG, soro' in em_dia          # o nome informado era outro: vale o código do exame


def test_indicacao_sem_intervalo_nao_e_adiada_mas_mostra_a_data(client):
    pedidos, em_dia = _pedir(client, [_feito('MAPA de 24 horas', '2026-11-01')])
    assert not em_dia
    assert pedidos['MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)']['ultimo_exame'].startswith(
        'Feito em 01/11/2026. Esta indicação não tem intervalo definido')


def test_glicemia_do_diabetico_acompanha_a_hba1c(client):
    glicose, hba1c = 'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro'
    pedidos, em_dia = _pedir(client, [_feito(glicose, '2026-10-01'), _feito(hba1c, '2026-10-01')])
    assert glicose in em_dia and em_dia[glicose]['motivo'].endswith('Acompanha a HbA1c, que está em dia.')
    pedidos, em_dia = _pedir(client, [_feito(glicose, '2026-10-01')])          # sem a HbA1c em dia, a glicemia fica
    assert glicose in pedidos and hba1c in pedidos and not em_dia
    pedidos, em_dia = _pedir(client, [_feito(glicose, '2026-10-01'), _feito(hba1c, '2026-06-01')])
    assert glicose in pedidos and not em_dia


def test_exame_combinado_cobre_as_partes_e_a_parte_nao_cobre_o_combinado(client):
    ast, alt = 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro'
    pedidos, em_dia = _pedir(client, [_feito('TGO e TGP, soro', '2026-05-02')])
    assert ast in em_dia and alt in em_dia
    pedidos, em_dia = _pedir(client, [_feito(ast, '2026-05-02')])
    assert ast in em_dia and alt in pedidos
    # perfil lipídico: só está em dia se todas as partes foram feitas, e vale a mais antiga
    lipidios = 'Colesterol total e frações, soro'
    assert P._ultima_data(lipidios, None, [(P.chaves('Colesterol total e frações, soro'), date(2025, 1, 1))]) == date(2025, 1, 1)
    assert P._ultima_data(lipidios, None, [(frozenset({'40301605'}), date(2025, 1, 1))]) is None


def test_a_data_mais_recente_e_a_que_vale(client):
    exames = [_feito('Hemoglobina glicada (HbA1c), soro', '2025-01-01'), _feito('Hemoglobina glicada (HbA1c), soro', '2026-10-20')]
    _, em_dia = _pedir(client, exames)
    assert em_dia['Hemoglobina glicada (HbA1c), soro']['feito_em'] == '2026-10-20'


def test_ultrassom_de_vias_urinarias_segue_o_sexo():
    assert P.chaves('Ultrassonografia de vias urinárias', 'feminino') == frozenset({'40901157'})
    assert P.chaves('Ultrassonografia de vias urinárias', 'masculino') == frozenset({'40901165'})
    assert P.chaves('Exame digitado à mão') == frozenset({'nome:exame digitado a mao'})


def test_vacinas_e_exame_desconhecido_nao_sao_afetados(client):
    sem, _ = _pedir(client, [])
    pedidos, em_dia = _pedir(client, [_feito('Influenza', '2026-10-01'), _feito('Exame que não existe', '2026-10-01')])
    assert not em_dia and list(pedidos) == list(sem)


def test_nome_fora_da_lista_e_avisado_em_vez_de_ignorado_em_silencio(client):
    exames = [_feito('Densitometria óssea', '2026-10-01'), _feito('densitometria óssea', '2026-10-02'),
              _feito('Hemograma completo', '2026-10-01')]
    dados = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames)).get_json()
    avisos = [o for o in dados['orientacoes'] if o['titulo'] == 'Exame já realizado não reconhecido']
    assert len(avisos) == 1
    assert avisos[0]['descricao'].startswith('A periodicidade não foi conferida para: Densitometria óssea. ')
    assert 'Hemograma' not in avisos[0]['descricao']
    sem_aviso = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames[2:])).get_json()
    assert all(o['titulo'] != 'Exame já realizado não reconhecido' for o in sem_aviso['orientacoes'])


def test_linha_em_branco_e_ignorada(client):
    pedidos, em_dia = _pedir(client, [_feito('', ''), _feito('  ', '')])
    assert not em_dia


@pytest.mark.parametrize('exames', [
    'hemograma', [{'exame': 'Hemograma completo', 'data': '2026-12-01'}], [{'exame': 'Hemograma completo', 'data': '01/10/2026'}],
    [{'exame': 'Hemograma completo', 'data': ''}], [{'exame': '', 'data': '2026-10-01'}], ['x'],
    [{'exame': 'Hemograma completo', 'data': '1800-01-01'}], [{'exame': 'x' * 301, 'data': '2026-10-01'}],
    [{'exame': 'Hemograma completo', 'data': '2026-10-01'}] * (P.MAX_EXAMES_ANTERIORES + 1),
])
def test_exames_anteriores_invalidos_sao_recusados(client, exames):
    resposta = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames))
    assert resposta.status_code == 400
    assert resposta.get_json()['codigo'] == 'entrada_invalida'
    assert all(e['campo'] == 'exames_anteriores' for e in resposta.get_json()['erros'])


def test_data_de_hoje_e_aceita(client):
    _, em_dia = _pedir(client, [_feito('Creatinina, soro', HOJE.isoformat())])
    assert 'Creatinina, soro' in em_dia


def test_lista_de_exames_conhecidos_nao_repete_o_mesmo_exame(client, anonimo):
    assert anonimo.get('/api/exames-conhecidos').status_code == 401
    exames = client.get('/api/exames-conhecidos').get_json()['exames']
    assert len(exames) > 100 and len({P.chaves(t) for t in exames}) == len(exames)
    assert sum('hemograma' in t.lower() for t in exames) == 1
    conhecidos = {P.chaves(t) for t in exames}
    assert P.chaves('Hemoglobina glicada (HbA1c), soro') in conhecidos and P.chaves('Densitometria óssea (DEXA)') in conhecidos
