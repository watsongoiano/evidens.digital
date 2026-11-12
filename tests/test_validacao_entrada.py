"""Perigos P-05 e P-07: entrada inválida aceita e ausência tratada como normalidade."""
import pytest

from src.utils.validacao import (
    DESCONHECIDO,
    LACTANTE_MENOR_6M,
    NAO,
    NAO_APLICAVEL,
    SIM,
    EntradaInvalida,
    validar_entrada,
)

MINIMO = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca'}


def _post(client, **campos):
    return client.post('/api/checkup-intelligent', json={**MINIMO, **campos})


def test_entrada_minima_valida(client):
    resposta = _post(client)
    assert resposta.status_code == 200
    assert resposta.get_json()['success'] is True


@pytest.mark.parametrize('corpo, campo', [
    ({'sexo': 'masculino', 'tabagismo': 'nunca'}, 'idade'),                    # ausente
    ({**MINIMO, 'idade': ''}, 'idade'),                                         # vazia: antes era erro 500
    ({**MINIMO, 'idade': '-5'}, 'idade'),
    ({**MINIMO, 'idade': '0'}, 'idade'),
    ({**MINIMO, 'idade': '17'}, 'idade'),
    ({**MINIMO, 'idade': '150'}, 'idade'),
    ({**MINIMO, 'idade': '45,5'}, 'idade'),
    ({**MINIMO, 'idade': 'quarenta'}, 'idade'),
    ({**MINIMO, 'idade': ['45']}, 'idade'),
    ({**MINIMO, 'sexo': 'outro'}, 'sexo'),
    ({**MINIMO, 'sexo': ''}, 'sexo'),
    ({'idade': '45', 'sexo': 'masculino'}, 'tabagismo'),                        # não presumir "nunca fumou"
    ({**MINIMO, 'tabagismo': 'às vezes'}, 'tabagismo'),
    ({**MINIMO, 'pas': '900'}, 'pas'),
    ({**MINIMO, 'pas': '120', 'pad': '130'}, 'pad'),
    ({**MINIMO, 'creatinina': 'abc'}, 'creatinina'),
    ({**MINIMO, 'creatinina': '0'}, 'creatinina'),
    ({**MINIMO, 'peso': '-70'}, 'peso'),
    ({**MINIMO, 'altura': '1.70'}, 'altura'),                                   # metros no lugar de cm
    ({**MINIMO, 'hba1c': '70'}, 'hba1c'),
    ({**MINIMO, 'cd4': '-1'}, 'cd4'),
    ({**MINIMO, 'macos_ano': 'muitos'}, 'macos_ano'),
    ({**MINIMO, 'comorbidades': 7}, 'comorbidades'),
    ({**MINIMO, 'comorbidades': [1, 2]}, 'comorbidades'),
    ({**MINIMO, 'gestante': 'sim'}, 'gestante'),                                # homem gestante
    ({**MINIMO, 'lactante': 'sim_menor_6m'}, 'lactante'),
    ({**MINIMO, 'imunossupressao': 'talvez'}, 'imunossupressao'),
    ({**MINIMO, 'medicacoes_continuo': 'x' * 5000}, 'medicacoes_continuo'),
])
def test_entrada_invalida_e_recusada_com_mensagem(client, corpo, campo):
    resposta = client.post('/api/checkup-intelligent', json=corpo)

    assert resposta.status_code == 400
    dados = resposta.get_json()
    assert dados['codigo'] == 'entrada_invalida'
    assert campo in [erro['campo'] for erro in dados['erros']]
    assert all(erro['mensagem'] for erro in dados['erros'])
    assert 'recommendations' not in dados


@pytest.mark.parametrize('corpo', [None, {}, [], 'texto', 42])
def test_corpo_que_nao_e_objeto_json_e_recusado(client, corpo):
    resposta = client.post('/api/checkup-intelligent', json=corpo)
    assert resposta.status_code == 400


def test_corpo_que_nao_e_json_e_recusado(client):
    resposta = client.post('/api/checkup-intelligent', data='idade=45', content_type='text/plain')
    assert resposta.status_code == 400


def test_varios_erros_sao_informados_de_uma_vez(client):
    resposta = client.post('/api/checkup-intelligent', json={'idade': '', 'sexo': 'x', 'pas': 'alta'})
    campos = {erro['campo'] for erro in resposta.get_json()['erros']}
    assert {'idade', 'sexo', 'tabagismo', 'pas'} <= campos


def test_virgula_decimal_e_aceita():
    dados, _ = validar_entrada({**MINIMO, 'creatinina': '1,2', 'hba1c': '6,5'})
    assert dados['creatinina'] == pytest.approx(1.2)
    assert dados['hba1c'] == pytest.approx(6.5)


def test_valores_antigos_de_tabagismo_sao_normalizados():
    for enviado, esperado in [('fumante_atual', 'atual'), ('ex_fumante', 'ex'), ('nunca_fumou', 'nunca'), ('ATUAL', 'atual')]:
        dados, _ = validar_entrada({**MINIMO, 'tabagismo': enviado})
        assert dados['tabagismo'] == esperado


def test_dado_ausente_nao_recebe_valor_padrao():
    dados, _ = validar_entrada(MINIMO)
    for campo in ('peso', 'altura', 'pas', 'pad', 'colesterol', 'hdl', 'creatinina', 'hba1c', 'cd4', 'macos_ano'):
        assert campo not in dados


def test_nomes_alternativos_dos_campos_sao_aceitos():
    dados, _ = validar_entrada({**MINIMO, 'pressao_sistolica': 130, 'pressao_diastolica': 80, 'colesterol_total': 190})
    assert dados['pas'] == dados['pressao_sistolica'] == 130
    assert dados['pad'] == 80
    assert dados['colesterol'] == dados['colesterol_total'] == 190


def test_dados_de_hiv_agrupados_sao_aceitos():
    dados, _ = validar_entrada({**MINIMO, 'comorbidades': ['hiv'], 'hiv_data': {'cd4': '350', 'em_tarv': 'sim'}})
    assert dados['cd4'] == 350
    assert dados['em_tarv'] == 'sim'
    assert 'hiv_data' not in dados


class TestTriagemDeTresValores:
    """Resposta ausente é "desconhecido"; nunca é lida como "não"."""

    def test_mulher_em_idade_fertil_sem_resposta(self):
        _, triagem = validar_entrada({**MINIMO, 'sexo': 'feminino', 'idade': '30'})
        assert triagem == {'gestante': DESCONHECIDO, 'lactante': DESCONHECIDO, 'imunossupressao': DESCONHECIDO}

    def test_respostas_explicitas(self):
        _, triagem = validar_entrada({
            **MINIMO, 'sexo': 'feminino', 'idade': '30',
            'gestante': 'nao', 'lactante': 'nao', 'imunossupressao': 'sim',
        })
        assert triagem == {'gestante': NAO, 'lactante': NAO, 'imunossupressao': SIM}

    def test_homem_gestacao_e_amamentacao_nao_se_aplicam(self):
        _, triagem = validar_entrada(MINIMO)
        assert triagem['gestante'] == NAO_APLICAVEL
        assert triagem['lactante'] == NAO_APLICAVEL
        assert triagem['imunossupressao'] == DESCONHECIDO

    def test_mulher_acima_da_idade_de_triagem(self):
        _, triagem = validar_entrada({**MINIMO, 'sexo': 'feminino', 'idade': '62'})
        assert triagem['gestante'] == NAO_APLICAVEL
        assert triagem['lactante'] == NAO_APLICAVEL

    def test_resposta_explicita_vale_em_qualquer_idade(self):
        _, triagem = validar_entrada({**MINIMO, 'sexo': 'feminino', 'idade': '57', 'gestante': 'sim'})
        assert triagem['gestante'] == SIM

    def test_caixa_de_selecao_da_pagina_antiga(self):
        _, triagem = validar_entrada({**MINIMO, 'sexo': 'feminino', 'idade': '30', 'gestante': 'true'})
        assert triagem['gestante'] == SIM

    def test_amamentando_sem_idade_da_crianca_vale_como_mais_restritivo(self):
        _, triagem = validar_entrada({**MINIMO, 'sexo': 'feminino', 'idade': '30', 'lactante': 'sim'})
        assert triagem['lactante'] == LACTANTE_MENOR_6M

    def test_resposta_invalida_e_erro(self):
        with pytest.raises(EntradaInvalida):
            validar_entrada({**MINIMO, 'imunossupressao': 3})


def test_nome_do_paciente_nao_altera_as_recomendacoes(client):
    """O servidor não precisa do nome para recomendar, e a página deixou de enviá-lo."""
    perfil = {**MINIMO, 'idade': '58', 'pas': '128', 'pad': '82', 'imunossupressao': 'nao'}
    sem_nome = client.post('/api/checkup-intelligent', json=perfil).get_json()
    com_nome = client.post('/api/checkup-intelligent', json={**perfil, 'nome_paciente': 'Maria da Silva'}).get_json()
    assert sem_nome == com_nome


def test_resposta_nao_expoe_cabecalho_de_rede_privada(client):
    """Herdado do teste de fumaça anterior (Flask-CORS 4.0.1)."""
    resposta = _post(client)
    assert 'Access-Control-Allow-Private-Network' not in resposta.headers
