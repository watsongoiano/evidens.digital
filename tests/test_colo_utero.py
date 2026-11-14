"""Rastreamento do colo do útero: teste de DNA-HPV e colposcopia (MS 2025, SBOC 2026, ACOG 2026).

Cada caso reproduz um ramo dos fluxogramas (risco habitual e HIV/imunossupressão).
"""
from datetime import date, timedelta

import pytest

from src.utils import colo_utero as C

HPV, COLPO = C.HPV, C.COLPOSCOPIA


def _resposta(client, **dados):
    base = dict(idade=40, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], medicacoes=[], historia_familiar=[])
    r = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _colo(client, **dados):
    d = _resposta(client, **dados)
    recs = {x['titulo']: x for x in d['recommendations'] if x['titulo'] in (HPV, COLPO)}
    return recs, {o['titulo']: o for o in d.get('orientacoes', [])}


# --- Risco habitual -----------------------------------------------------------------------------

@pytest.mark.parametrize('idade', [25, 29, 30, 45, 64])
def test_risco_habitual_teste_de_hpv_a_cada_5_anos_dos_25_aos_64(client, idade):
    recs, _ = _colo(client, idade=idade)
    assert list(recs) == [HPV] and recs[HPV]['subtitulo'] == 'Mulheres 25-64 anos | A cada 5 anos'
    assert 'MS 2025' in recs[HPV]['referencia'] and 'SBOC 2026' in recs[HPV]['referencia']
    # A ACOG só apoia o teste primário a partir dos 30 anos.
    assert ('ACOG 2026' in recs[HPV]['referencia']) == (idade >= 30)


@pytest.mark.parametrize('idade', [18, 21, 24])
def test_antes_dos_25_nao_se_pede_nada_nem_com_teste_positivo(client, idade):
    for resultado in (None, 'hpv_16_18'):
        recs, orient = _colo(client, idade=idade, **({'hpv_resultado': resultado} if resultado else {}))
        assert recs == {}
        assert ('Colo do útero: rastreamento a partir dos 25 anos' in orient) == (idade >= 21)


def test_depois_dos_64_orienta_quando_encerrar(client):
    recs, orient = _colo(client, idade=66)
    assert recs == {} and 'Colo do útero: quando encerrar o rastreamento' in orient
    recs, _ = _colo(client, idade=62)
    assert 'Depois dos 60 anos, um teste negativo encerra' in recs[HPV]['descricao']


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


def test_resultado_positivo_vale_tambem_depois_dos_64(client):
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
    for item in d['orientacoes'] + _resposta(client, hpv_resultado='hpv_16_18')['recommendations'] + _resposta(client)['recommendations']:
        if item['titulo'] in (HPV, COLPO) or item['titulo'].startswith('Colo do útero'):
            assert item['referencia_html'].count('<a href="https://') == len(item['referencias']) >= 2, item['titulo']
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
    assert "getElementById('hpv-item').style.display = feminino ? 'block' : 'none'" in html
