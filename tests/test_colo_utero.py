"""Rastreamento do colo do útero: teste de DNA-HPV e colposcopia (MS 2025, SBOC 2026, ACOG 2026).

Cada caso reproduz um ramo dos fluxogramas (risco habitual e HIV/imunossupressão).
"""
from datetime import date, timedelta

import pytest

from src.utils import colo_utero as C

HPV, COLPO, CITO = C.HPV, C.COLPOSCOPIA, C.CITOLOGIA
DIVERGENCIA = 'Colo do útero: as diretrizes divergem antes dos 30 anos'


def _resposta(client, **dados):
    base = dict(idade=40, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], medicacoes=[], historia_familiar=[], exames_hiv_previos='nao')
    r = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _colo(client, **dados):
    d = _resposta(client, **dados)
    recs = {x['titulo']: x for x in d['recommendations'] if x['titulo'] in (HPV, COLPO, CITO)}
    return recs, {o['titulo']: o for o in d.get('orientacoes', [])}


# --- Risco habitual -----------------------------------------------------------------------------

@pytest.mark.parametrize('idade', [25, 29, 30, 45, 64, 65])
def test_risco_habitual_teste_de_hpv_a_cada_5_anos_dos_25_aos_65(client, idade):
    recs, orient = _colo(client, idade=idade)
    assert list(recs) == [HPV] and recs[HPV]['subtitulo'] == 'Mulheres 25-64 anos (ACOG: até 65) | A cada 5 anos'
    # O MS convida até os 64; aos 65 a fonte é só a ACOG.
    assert ('MS 2025' in recs[HPV]['referencia'] and 'SBOC 2026' in recs[HPV]['referencia']) == (idade <= 64)
    if idade == 65:
        assert recs[HPV]['referencia'] == 'ACOG 2026'
    # A ACOG só apoia o teste primário a partir dos 30 anos; dos 25 aos 29 a divergência vai para as orientações.
    assert ('ACOG 2026' in recs[HPV]['referencia']) == (idade >= 30)
    assert (DIVERGENCIA in orient) == (idade < 30)
    if idade < 30:
        assert 'Foi pedido o teste de DNA-HPV (MS e SBOC)' in orient[DIVERGENCIA]['descricao']


@pytest.mark.parametrize('idade', [21, 24])
def test_dos_21_aos_24_citologia_a_cada_3_anos_pela_acog_com_a_divergencia_explicada(client, idade):
    for resultado in (None, 'hpv_16_18'):   # teste de HPV feito antes dos 25 não é considerado (MS, rec. 11)
        recs, orient = _colo(client, idade=idade, **({'hpv_resultado': resultado} if resultado else {}))
        assert list(recs) == [CITO] and recs[CITO]['subtitulo'] == 'Mulheres 21-24 anos | A cada 3 anos'
        assert recs[CITO]['referencia'] == 'ACOG 2026'
        texto = orient[DIVERGENCIA]['descricao']
        for trecho in ('MS 2025 e SBOC 2026: não rastrear antes dos 25 anos', 'ACOG 2026: citologia isolada a cada 3 anos',
                       'Foi mantida a citologia a cada 3 anos (ACOG)'):
            assert trecho in texto, trecho
        assert all(f in orient[DIVERGENCIA]['referencia'] for f in ('MS 2025', 'SBOC 2026', 'ACOG 2026'))


@pytest.mark.parametrize('idade', [18, 20])
def test_antes_dos_21_nao_se_pede_nada(client, idade):
    recs, orient = _colo(client, idade=idade)
    assert recs == {} and not any(t.startswith('Colo do útero') for t in orient)


@pytest.mark.parametrize('idade, encerra', [(60, False), (61, True), (65, True)])
def test_negativo_depois_dos_60_encerra_o_rastreamento(client, idade, encerra):
    recs, orient = _colo(client, idade=idade, hpv_resultado='nao_detectado')
    assert (HPV in recs) == (not encerra)
    assert ('Colo do útero: rastreamento encerrado' in orient) == encerra
    if encerra:
        assert 'antes dos 60 anos, ainda falta um' in orient['Colo do útero: rastreamento encerrado']['descricao']
    # sem resultado informado, o teste continua sendo pedido
    recs, _ = _colo(client, idade=idade)
    assert HPV in recs


ENCERRAR = 'Colo do útero: quando encerrar o rastreamento'


@pytest.mark.parametrize('idade', [66, 75, 88])
@pytest.mark.parametrize('adequado, nic2, resultado, pede', [
    ('sim', None, None, False),          # rastreio anterior adequado e negativo: para (ACOG)
    (None, None, 'nao_detectado', False),  # negativo depois dos 60 (MS) sem resposta sobre o rastreio anterior
    (None, None, None, False),           # sem rastreio declarado inadequado: não se rastreia depois dos 65 (USPSTF D)
    ('nao', None, None, True),           # rastreio inadequado: continua (ACOG; MS rec. 13)
    ('nao', None, 'nao_detectado', True),
    ('sim', 'sim', None, True),          # NIC 2+ tratada: 25 anos após o tratamento
])
def test_depois_dos_65_para_so_com_rastreio_adequado(client, idade, adequado, nic2, resultado, pede):
    extra = {k: v for k, v in (('colo_rastreio_adequado', adequado), ('colo_nic2_previa', nic2), ('hpv_resultado', resultado)) if v}
    recs, orient = _colo(client, idade=idade, **extra)
    assert (HPV in recs) == pede
    assert ENCERRAR in orient
    o = orient[ENCERRAR]
    assert 'As diretrizes divergem' in o['descricao'] and '3 citologias negativas seguidas' in o['descricao']
    assert 'MS 2025' in o['referencia'] and 'ACOG 2026' in o['referencia']
    if pede:
        assert recs[HPV]['subtitulo'].startswith('Mulheres acima de 65 anos')
        assert ('25 anos após o tratamento' in recs[HPV]['descricao']) == (nic2 == 'sim')


def test_nic2_tratada_depois_dos_60_negativo_nao_encerra(client):
    recs, orient = _colo(client, idade=62, hpv_resultado='nao_detectado', colo_nic2_previa='sim')
    assert HPV in recs and '25 anos após o tratamento' in recs[HPV]['descricao']
    assert 'Colo do útero: rastreamento encerrado' not in orient


def test_texto_dos_metodos_nao_diz_que_a_acog_proibe_o_coteste(client):
    recs, _ = _colo(client, idade=40)
    texto = recs[HPV]['descricao']
    assert 'coteste não é recomendado' not in texto
    for trecho in ('MS 2025, teste de DNA-HPV sem citologia junto', 'HPV primário a cada 5 anos é o preferido',
                   'coteste (HPV com citologia) a cada 5 anos é aceitável', 'autocoleta a cada 3 anos'):
        assert trecho in texto, trecho


@pytest.mark.parametrize('valor', ['talvez', 3])
def test_resposta_invalida_do_historico_do_colo_e_recusada(client, valor):
    r = client.post('/api/checkup-intelligent', json=dict(idade=70, sexo='feminino', tabagismo='nunca',
                                                          colo_rastreio_adequado=valor))
    assert r.status_code == 400


def test_depois_dos_65_orienta_quando_encerrar(client):
    recs, orient = _colo(client, idade=66, colo_rastreio_adequado='sim')
    assert recs == {} and ENCERRAR in orient
    recs, _ = _colo(client, idade=62)
    assert 'Depois dos 60 anos, um teste negativo encerra' in recs[HPV]['descricao']


# --- Histerectomia ------------------------------------------------------------------------------

@pytest.mark.parametrize('dados', [dict(idade=23), dict(idade=40), dict(idade=70), dict(idade=40, comorbidades_extra=['hiv']),
                                   dict(idade=40, hpv_resultado='nao_detectado')])
def test_histerectomia_total_por_doenca_benigna_dispensa_o_rastreamento(client, dados):
    com = ['histerectomia_total'] + dados.pop('comorbidades_extra', [])
    recs, orient = _colo(client, comorbidades=com, **dados)
    assert recs == {}
    o = orient['Colo do útero: rastreamento dispensado após histerectomia total']
    assert 'lesão precursora ou câncer' in o['descricao'] and 'MS 2025' in o['referencia']
    assert ('ACOG' in o['referencia']) == ('hiv' not in com)


def test_sem_histerectomia_marcada_a_paciente_e_rastreada(client):
    recs, orient = _colo(client, idade=40)
    assert list(recs) == [HPV] and not any('histerectomia' in t for t in orient)


def test_resultado_positivo_segue_o_fluxo_mesmo_com_histerectomia(client):
    recs, _ = _colo(client, comorbidades=['histerectomia_total'], hpv_resultado='hpv_16_18')
    assert list(recs) == [COLPO]


@pytest.mark.parametrize('resultado, exame, trecho', [
    ('nao_detectado', HPV, 'A cada 5 anos'),
    ('hpv_16_18', COLPO, 'HPV 16 e/ou 18 detectado'),
    ('outros_citologia_alterada', COLPO, 'ASC-US ou mais'),
    ('outros_citologia_negativa', HPV, 'A cada 1 ano'),
    ('colposcopia_negativa', HPV, 'A cada 1 ano'),
])
def test_fluxograma_de_risco_habitual(client, resultado, exame, trecho):
    recs, _ = _colo(client, hpv_resultado=resultado)
    assert list(recs) == [exame] and trecho in recs[exame]['subtitulo']
    if exame == COLPO:
        assert recs[COLPO]['categoria'] == 'imagem' and 'repetir o teste de DNA-HPV em 12 meses' in recs[COLPO]['descricao']


def test_persistencia_por_24_meses_esta_descrita(client):
    recs, _ = _colo(client, hpv_resultado='outros_citologia_negativa')
    assert 'persistente por 24 meses: colposcopia' in recs[HPV]['descricao']


def test_resultado_positivo_vale_tambem_depois_dos_65(client):
    recs, _ = _colo(client, idade=70, hpv_resultado='hpv_16_18')
    assert list(recs) == [COLPO]


# --- HIV e imunossupressão ----------------------------------------------------------------------

@pytest.mark.parametrize('dados', [dict(comorbidades=['hiv']), dict(imunossupressao='sim'), dict(comorbidades=['transplante']),
                                   dict(medicacoes=['tacrolimo'])], ids=['hiv', 'triagem', 'transplante', 'imunossupressor'])
@pytest.mark.parametrize('idade', [19, 40, 75])
def test_imunossuprimida_a_cada_3_anos_em_qualquer_idade(client, dados, idade):
    recs, orient = _colo(client, idade=idade, **dados)
    assert list(recs) == [HPV] and recs[HPV]['subtitulo'] == 'Mulheres com HIV ou imunossupressão | A cada 3 anos'
    assert 'ACOG' not in recs[HPV]['referencia']
    assert not any(t.startswith('Colo do útero') for t in orient)


@pytest.mark.parametrize('resultado', ['hpv_16_18', 'outros_citologia_negativa', 'outros_citologia_alterada'])
def test_imunossuprimida_com_qualquer_tipo_vai_para_colposcopia(client, resultado):
    recs, _ = _colo(client, comorbidades=['hiv'], hpv_resultado=resultado)
    assert list(recs) == [COLPO] and 'sem depender da citologia reflexa' in recs[COLPO]['descricao']


def test_imunossuprimida_apos_colposcopia_sem_doenca_repete_em_1_ano(client):
    recs, _ = _colo(client, imunossupressao='sim', hpv_resultado='colposcopia_negativa')
    assert list(recs) == [HPV] and recs[HPV]['subtitulo'].endswith('A cada 1 ano') and 'cada 3 anos' in recs[HPV]['descricao']


# --- Periodicidade, entrada, códigos e links ---------------------------------------------------

def _feito_ha(dias):
    return [{'exame': HPV, 'data': (date.today() - timedelta(days=dias)).isoformat()}]


@pytest.mark.parametrize('dados, dias, pedido', [
    (dict(), 4 * 365, False), (dict(), 6 * 365, True),                                   # 5 anos
    (dict(comorbidades=['hiv']), 2 * 365, False), (dict(comorbidades=['hiv']), 4 * 365, True),   # 3 anos
    (dict(hpv_resultado='outros_citologia_negativa'), 200, False),                       # 1 ano
    (dict(hpv_resultado='outros_citologia_negativa'), 400, True),
])
def test_data_do_ultimo_teste_adia_pelo_intervalo_do_ramo(client, dados, dias, pedido):
    recs, _ = _colo(client, exames_anteriores=_feito_ha(dias), **dados)
    assert (HPV in recs) == pedido


def test_colposcopia_indicada_nao_e_adiada_pela_data_do_teste(client):
    recs, _ = _colo(client, hpv_resultado='hpv_16_18', exames_anteriores=_feito_ha(30))
    assert list(recs) == [COLPO]


def test_resultado_invalido_ou_em_homem_e_recusado(client):
    base = dict(idade=40, tabagismo='nunca', imunossupressao='nao', comorbidades=[], medicacoes=[], historia_familiar=[])
    r = client.post('/api/checkup-intelligent', json=dict(base, sexo='feminino', gestante='nao', lactante='nao', hpv_resultado='xyz'))
    assert r.status_code == 400
    r = client.post('/api/checkup-intelligent', json=dict(base, sexo='masculino', hpv_resultado='hpv_16_18'))
    assert r.status_code == 400
    r = client.post('/api/checkup-intelligent', json=dict(base, sexo='masculino', hpv_resultado=''))
    assert r.status_code == 200


def test_codigos_tuss_e_fontes_clicaveis(client):
    from src.utils import tuss
    assert tuss.CODIGOS[COLPO] == ['41301102'] and tuss.CODIGOS[HPV] == ['40314154']
    d = _resposta(client, idade=22)
    for item in (d['orientacoes'] + d['recommendations'] + _resposta(client, hpv_resultado='hpv_16_18')['recommendations']
                 + _resposta(client)['recommendations'] + _resposta(client, comorbidades=['histerectomia_total'])['orientacoes']):
        if item['titulo'] in (HPV, COLPO, CITO) or item['titulo'].startswith('Colo do útero'):
            assert item['referencia_html'].count('<a href="https://') == len(item['referencias']) >= 1, item['titulo']
    html = _colo(client)[0][HPV]['referencia_html']
    assert 'portaria-conjunta-saes-sectics-no-13' in html and '10.1097/AOG.0000000000006257' in html and 'sboc.org.br' in html


def test_citologia_continua_no_catalogo_para_acrescentar():
    from src.utils.catalogo import catalogo
    c = catalogo()
    assert 'Citologia cervicovaginal (Papanicolaou)' in c['laboratorio'] and COLPO in c['imagem']


def test_formulario_tem_o_campo_so_para_o_sexo_feminino():
    from conftest import RAIZ
    from src.utils import validacao
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    for valor in C.RESULTADOS:
        assert f'<option value="{valor}">' in html
    assert tuple(validacao.RESULTADOS_HPV) == tuple(C.RESULTADOS)
    # Só para mulheres com colo, a partir dos 25 anos ou com HIV/imunossupressão (MS 2025, rec. 11)
    assert "const hpv = feminino && (imuno || idade >= 25);" in html
    assert "getElementById('hpv-item').style.display = hpv ? 'block' : 'none'" in html
    # O resultado fica na linha do teste de HPV em "Exames já realizados" (um só lugar)
    assert "if (/papilomavirus|dna-hpv/.test(t)) return ['hpv_resultado'];" in html


def test_sem_rastreio_depois_dos_65_sem_indicacao(client):
    recs, orient = _colo(client, idade=70)
    assert HPV not in recs
    o = orient['Colo do útero: sem rastreio depois dos 65 anos']
    assert 'USPSTF 2018' in o['referencia'] and 'rastreio anterior inadequado' in o['descricao']
