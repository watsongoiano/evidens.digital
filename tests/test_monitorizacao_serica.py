"""Monitorização sérica de fármacos: lítio (NICE CG185), digoxina, anticonvulsivantes (NICE NG217) e
inibidores de calcineurina em transplantados (KDIGO 2009)."""
import pytest

LITIO = 'Lítio, soro'


def _resposta(client, **dados):
    base = dict(idade=45, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], medicacoes=[], historia_familiar=[])
    r = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    return {x['titulo']: x for x in d['recommendations']}, {o['titulo']: o for o in d.get('orientacoes', [])}


def test_litio_pede_litemia_e_o_painel_da_nice_a_cada_6_meses(client):
    recs, orient = _resposta(client, medicacoes=['litio'])
    assert recs[LITIO]['subtitulo'].endswith('A cada 6 meses')
    assert '12 horas após a última dose' in recs[LITIO]['descricao'] and 'NICE CG185' in recs[LITIO]['referencia']
    for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Creatinina, soro', 'Ureia, soro', 'Sódio, soro',
                   'Cálcio iônico, soro'):
        assert titulo in recs, titulo
        assert 'Em uso de lítio | A cada 6 meses' in recs[titulo]['subtitulo'], titulo
    assert 'Lítio: frequência da litemia' in orient


@pytest.mark.parametrize('dados', [dict(idade=70), dict(medicacoes=['litio', 'enalapril']),
                                   dict(medicacoes=['litio', 'losartana_hidroclorotiazida'])],
                         ids=['idoso', 'ieca', 'diuretico'])
def test_litio_a_cada_3_meses_em_idoso_ou_com_farmaco_que_interage(client, dados):
    dados.setdefault('medicacoes', ['litio'])
    recs, _ = _resposta(client, **dados)
    assert recs[LITIO]['subtitulo'].endswith('A cada 3 meses')
    assert recs['Creatinina, soro']['subtitulo'].count('A cada 6 meses') >= 1


def test_digoxina_e_anticonvulsivantes_orientam_sem_pedir_nivel_de_rotina(client):
    recs, orient = _resposta(client, medicacoes=['digoxina', 'acido_valproico_divalproato', 'carbamazepina', 'fenitoina'])
    assert 'Digoxina: nível sérico não é rotineiro' in orient
    assert '0,5-0,9 ng/mL' in orient['Digoxina: nível sérico não é rotineiro']['descricao']
    assert 'Anticonvulsivantes: nível sérico só com indicação' in orient
    for nivel in ('Digitoxina ou digoxina', 'Ácido valpróico', 'Carbamazepina', 'Fenitoína'):
        assert nivel not in recs


@pytest.mark.parametrize('remedio, nivel', [('tacrolimo', 'Tacrolimo, sangue total (nível de vale)'),
                                            ('ciclosporina', 'Ciclosporina, sangue total (nível de vale)')])
def test_inibidor_de_calcineurina_no_transplantado_pede_nivel_de_vale(client, remedio, nivel):
    recs, _ = _resposta(client, medicacoes=[remedio], comorbidades=['transplante'], imunossupressao='sim')
    assert nivel in recs and 'KDIGO 2009' in recs[nivel]['referencia']
    # Fora do transplante (psoríase, por exemplo) o nível não é pedido.
    recs, _ = _resposta(client, medicacoes=[remedio])
    assert nivel not in recs


def test_niveis_novos_tem_codigo_tuss():
    from src.utils import tuss
    assert tuss.CODIGOS['Tacrolimo, sangue total (nível de vale)'] == ['40302458']
    assert tuss.CODIGOS['Ciclosporina, sangue total (nível de vale)'] == ['40301486']
    assert tuss.CODIGOS[LITIO] == ['40302229']
