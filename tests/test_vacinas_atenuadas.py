"""Perigos P-02 a P-05: vacina de vírus vivo atenuado em quem não pode recebê-la.

Os testes de invariantes usam um oráculo independente da implementação: as
vacinas são reconhecidas aqui pelo título, por expressões próprias deste
arquivo, e não pelo atributo nem pelas funções do módulo de triagem.
"""
import itertools
import re

import pytest

from src.utils import seguranca_vacinas as sv
from src.utils.validacao import (
    DESCONHECIDO,
    LACTANTE_6M_OU_MAIS,
    LACTANTE_MENOR_6M,
    NAO,
    NAO_APLICAVEL,
    SIM,
)

# --- Oráculo independente -------------------------------------------------
ATENUADA = re.compile(r'tr[ií]plice viral|varicela|febre amarela|dengue', re.I)
FEBRE_AMARELA = re.compile(r'febre amarela', re.I)
DENGUE = re.compile(r'dengue', re.I)
HPV = re.compile(r'gardasil|\bhpv\b', re.I)

ESTADOS = {'contraindicada', 'precaucao', 'dados_insuficientes'}
IDADE_MAXIMA_TRIAGEM_GESTACAO = 55


def _vacinas(resposta):
    return [r['titulo'] for r in resposta['recommendations'] if r.get('categoria') == 'vacina']


def _consultar(client, **campos):
    corpo = {'tabagismo': 'nunca', **campos}
    if corpo.get('gestante') == 'sim':   # gestante exige IG e 1ª consulta
        corpo.setdefault('idade_gestacional', '20')
        corpo.setdefault('primeira_consulta', 'sim')
    resposta = client.post('/api/checkup-intelligent', json=corpo)
    assert resposta.status_code == 200, resposta.get_json()
    return resposta.get_json()


# --- Casos clínicos que motivaram a contenção -----------------------------

def test_gestante_nao_recebe_atenuadas_nem_hpv(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='sim', lactante='nao', imunossupressao='nao')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t) or HPV.search(t)]
    retiradas = {item['titulo']: item for item in dados['nao_incluidas']}
    assert len(retiradas) == 5
    assert all(item['estado'] == 'contraindicada' for item in retiradas.values())


def test_febre_amarela_na_gestacao_menciona_a_excecao_epidemiologica(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='sim', lactante='nao', imunossupressao='nao')
    febre_amarela = next(i for i in dados['nao_incluidas'] if FEBRE_AMARELA.search(i['titulo']))
    assert 'surto' in febre_amarela['motivo']
    assert 'risco-benefício' in febre_amarela['motivo']


def test_hiv_com_cd4_abaixo_de_200_nao_recebe_atenuadas(client):
    dados = _consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], cd4=150, imunossupressao='nao')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t)]
    assert {i['estado'] for i in dados['nao_incluidas']} == {'contraindicada'}


def test_hiv_sem_cd4_informado_e_dado_insuficiente(client):
    dados = _consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], imunossupressao='nao')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t)]
    assert {i['estado'] for i in dados['nao_incluidas']} == {'dados_insuficientes'}
    assert all('CD4' in i['motivo'] for i in dados['nao_incluidas'])


def test_hiv_com_cd4_alto_fica_como_precaucao(client):
    dados = _consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], cd4=600, imunossupressao='nao')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t)]
    assert {i['estado'] for i in dados['nao_incluidas']} == {'precaucao'}


def test_imunossupressao_bloqueia_atenuadas(client):
    dados = _consultar(client, idade=40, sexo='masculino', imunossupressao='sim')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t)]
    assert {i['estado'] for i in dados['nao_incluidas']} == {'contraindicada'}


def test_triagem_nao_respondida_nao_vale_como_nao(client):
    """O defeito original: ausência de informação era lida como ausência de risco."""
    dados = _consultar(client, idade=30, sexo='feminino')

    assert not [t for t in _vacinas(dados) if ATENUADA.search(t) or HPV.search(t)]
    assert {i['estado'] for i in dados['nao_incluidas']} == {'dados_insuficientes'}
    assert dados['triagem_vacinas'] == {
        'gestante': DESCONHECIDO, 'lactante': DESCONHECIDO, 'imunossupressao': DESCONHECIDO,
    }


def test_triagem_respondida_libera_as_atenuadas(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='nao', lactante='nao', imunossupressao='nao')

    assert len([t for t in _vacinas(dados) if ATENUADA.search(t)]) == 4
    assert dados['nao_incluidas'] == []


def test_nutriz_de_lactente_pequeno_nao_recebe_febre_amarela_nem_dengue(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='nao', lactante='sim_menor_6m', imunossupressao='nao')

    vacinas = _vacinas(dados)
    assert not [t for t in vacinas if FEBRE_AMARELA.search(t) or DENGUE.search(t)]
    assert [t for t in vacinas if re.search('tr[ií]plice viral', t, re.I)]  # permitida na amamentação
    assert {i['estado'] for i in dados['nao_incluidas']} == {'contraindicada'}


def test_nutriz_de_crianca_maior_pode_receber_febre_amarela_mas_nao_dengue(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='nao', lactante='sim_6m_ou_mais', imunossupressao='nao')

    vacinas = _vacinas(dados)
    assert [t for t in vacinas if FEBRE_AMARELA.search(t)]
    assert not [t for t in vacinas if DENGUE.search(t)]


def test_febre_amarela_a_partir_dos_60_anos_e_precaucao(client):
    dados = _consultar(client, idade=70, sexo='masculino', imunossupressao='nao')

    assert not [t for t in _vacinas(dados) if FEBRE_AMARELA.search(t)]
    febre_amarela = next(i for i in dados['nao_incluidas'] if FEBRE_AMARELA.search(i['titulo']))
    assert febre_amarela['estado'] == 'precaucao'


def test_item_retirado_traz_motivo_e_fonte(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='sim')
    for item in dados['nao_incluidas']:
        assert set(item) == {'titulo', 'categoria', 'estado', 'motivo', 'referencia'}
        assert item['estado'] in ESTADOS
        assert len(item['motivo']) > 20
        assert item['referencia']


# --- Invariantes sobre uma grade de pacientes ------------------------------

IDADES = [18, 26, 30, 45, 49, 55, 56, 59, 60, 68, 75, 90]
GESTANTE = [None, 'nao', 'sim']
LACTANTE = [None, 'nao', 'sim_menor_6m', 'sim_6m_ou_mais']
IMUNOSSUPRESSAO = [None, 'nao', 'sim']
HIV = [None, ('hiv', None), ('hiv', 100), ('hiv', 250), ('hiv', 600)]


def _grade():
    for idade, imuno, hiv in itertools.product(IDADES, IMUNOSSUPRESSAO, HIV):
        yield 'masculino', idade, None, None, imuno, hiv
        for gestante, lactante in itertools.product(GESTANTE, LACTANTE):
            yield 'feminino', idade, gestante, lactante, imuno, hiv


def test_invariantes_de_seguranca_em_toda_a_grade(client):
    """Nenhuma combinação pode sugerir vacina atenuada a quem não foi liberado pela triagem."""
    verificados = 0
    for sexo, idade, gestante, lactante, imuno, hiv in _grade():
        corpo = {'idade': idade, 'sexo': sexo}
        if gestante is not None:
            corpo['gestante'] = gestante
        if lactante is not None:
            corpo['lactante'] = lactante
        if imuno is not None:
            corpo['imunossupressao'] = imuno
        if hiv:
            corpo['comorbidades'] = ['hiv']
            if hiv[1] is not None:
                corpo['cd4'] = hiv[1]

        dados = _consultar(client, **corpo)
        vacinas = _vacinas(dados)
        atenuadas = [t for t in vacinas if ATENUADA.search(t)]
        caso = f'{corpo} -> {atenuadas}'

        triagem_gestacao = sexo == 'feminino' and idade <= IDADE_MAXIMA_TRIAGEM_GESTACAO

        # Imunossupressão: precisa estar explicitamente negada
        if imuno != 'nao':
            assert not atenuadas, caso
        # Pessoa vivendo com HIV: nunca entra automaticamente, qualquer que seja o CD4
        if hiv:
            assert not atenuadas, caso
        # Gestação: "sim" bloqueia sempre; ausência de resposta bloqueia em idade fértil
        if gestante == 'sim' or (triagem_gestacao and gestante is None):
            assert not atenuadas, caso
            assert not [t for t in vacinas if HPV.search(t)], caso
        # Amamentação
        if lactante == 'sim_menor_6m' or (triagem_gestacao and lactante is None):
            assert not [t for t in vacinas if FEBRE_AMARELA.search(t)], caso
        if lactante in ('sim_menor_6m', 'sim_6m_ou_mais') or (triagem_gestacao and lactante is None):
            assert not [t for t in vacinas if DENGUE.search(t)], caso
        # Febre amarela a partir dos 60 anos
        if idade >= 60:
            assert not [t for t in vacinas if FEBRE_AMARELA.search(t)], caso

        # O que sai da lista aparece em `nao_incluidas`, com estado e motivo, e só vacinas sujeitas à triagem saem
        titulos_retirados = [i['titulo'] for i in dados['nao_incluidas']]
        assert len(titulos_retirados) == len(set(titulos_retirados)), caso
        assert not set(titulos_retirados) & set(r['titulo'] for r in dados['recommendations']), caso
        for item in dados['nao_incluidas']:
            assert item['estado'] in ESTADOS and item['motivo'], caso
            assert ATENUADA.search(item['titulo']) or HPV.search(item['titulo']), caso
        assert dados['total_recommendations'] == len(dados['recommendations']), caso
        verificados += 1

    assert verificados == len(IDADES) * len(IMUNOSSUPRESSAO) * len(HIV) * (1 + len(GESTANTE) * len(LACTANTE))


# --- Unidade: classificação e avaliação ------------------------------------

@pytest.mark.parametrize('titulo, esperado', [
    ('Tríplice Viral - SCR (Priorix® ou M-M-R® II)', sv.TRIPLICE_VIRAL),
    ('Vacina SCRV (tetraviral)', sv.TRIPLICE_VIRAL),
    ('Varicela (Varilrix® ou Varivax®)', sv.VARICELA),
    ('Febre Amarela (Stamaril®)', sv.FEBRE_AMARELA),
    ('Dengue (Qdenga®)', sv.DENGUE),
    ('Vacina dengue Butantan-DV', sv.DENGUE),
    ('Gardasil 9® (Vacina HPV 9-Valente)', sv.HPV),
    ('Influenza Tetravalente (Fluarix®, Vaxigrip® ou similar)', None),
    ('Hepatites A e B Combinada (Twinrix®)', None),
    ('dTpa (Adacel® ou Boostrix®)', None),
    ('Herpes Zóster (Shingrix®)', None),
    ('RSV - Vírus Sincicial Respiratório (Abrysvo®)', None),
    ('', None),
    (None, None),
])
def test_classificacao_pelo_titulo(titulo, esperado):
    assert sv.classificar_vacina(titulo) == esperado


def test_vacina_marcada_como_atenuada_e_tratada_como_tal_mesmo_sem_titulo_conhecido():
    assert sv.classificar_vacina('Vacina nova qualquer', viva_atenuada=True) == sv.ATENUADA_NAO_CLASSIFICADA
    resultado = sv.avaliar_vacina(
        sv.ATENUADA_NAO_CLASSIFICADA,
        {'gestante': SIM, 'lactante': NAO, 'imunossupressao': NAO},
        {'idade': 30, 'hiv': False, 'cd4': None},
    )
    assert resultado['estado'] == sv.CONTRAINDICADA


def test_triagem_ausente_vale_como_desconhecido():
    resultado = sv.avaliar_vacina(sv.TRIPLICE_VIRAL, {}, {'idade': 30, 'hiv': False, 'cd4': None})
    assert resultado['estado'] == sv.DADOS_INSUFICIENTES


def test_liberada_quando_tudo_esta_respondido():
    triagem = {'gestante': NAO, 'lactante': NAO, 'imunossupressao': NAO}
    contexto = {'idade': 30, 'hiv': False, 'cd4': None}
    for tipo in (sv.TRIPLICE_VIRAL, sv.VARICELA, sv.FEBRE_AMARELA, sv.DENGUE, sv.HPV):
        assert sv.avaliar_vacina(tipo, triagem, contexto) is None


def test_homem_so_precisa_responder_imunossupressao():
    contexto = {'idade': 30, 'hiv': False, 'cd4': None}
    triagem = {'gestante': NAO_APLICAVEL, 'lactante': NAO_APLICAVEL, 'imunossupressao': NAO}
    assert sv.avaliar_vacina(sv.FEBRE_AMARELA, triagem, contexto) is None
    assert sv.avaliar_vacina(sv.HPV, {**triagem, 'imunossupressao': DESCONHECIDO}, contexto) is None


def test_cd4_zero_e_tratado_como_valor_e_nao_como_ausencia():
    resultado = sv.avaliar_vacina(
        sv.VARICELA,
        {'gestante': NAO_APLICAVEL, 'lactante': NAO_APLICAVEL, 'imunossupressao': NAO},
        {'idade': 30, 'hiv': True, 'cd4': 0},
    )
    assert resultado['estado'] == sv.CONTRAINDICADA


def test_itens_que_nao_sao_vacina_nao_passam_pela_triagem():
    recomendacoes = [
        {'titulo': 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular', 'categoria': 'laboratorio'},
        {'titulo': 'Sorologia para dengue', 'categoria': 'laboratorio'},
    ]
    mantidas, retiradas = sv.aplicar_triagem_vacinas(recomendacoes, {}, {'idade': 30, 'hiv': False, 'cd4': None})
    assert mantidas == recomendacoes
    assert retiradas == []


def test_lactante_de_crianca_maior_nao_bloqueia_febre_amarela():
    triagem = {'gestante': NAO, 'lactante': LACTANTE_6M_OU_MAIS, 'imunossupressao': NAO}
    contexto = {'idade': 30, 'hiv': False, 'cd4': None}
    assert sv.avaliar_vacina(sv.FEBRE_AMARELA, triagem, contexto) is None
    assert sv.avaliar_vacina(sv.DENGUE, triagem, contexto)['estado'] == sv.CONTRAINDICADA
    assert sv.avaliar_vacina(sv.FEBRE_AMARELA, {**triagem, 'lactante': LACTANTE_MENOR_6M}, contexto)['estado'] == sv.CONTRAINDICADA
