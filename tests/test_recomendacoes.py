"""Formato das recomendações devolvidas pela API.

Substitui o antigo `test_corrections.py`, que imprimia os mesmos campos sem
verificar nada.
"""
import pytest

CATEGORIAS = {'laboratorio', 'imagem', 'vacina'}
PRIORIDADES = {'alta', 'media', 'baixa'}

PERFIS = [
    {'idade': 25, 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao'},
    {'idade': 45, 'sexo': 'masculino', 'tabagismo': 'ex', 'macos_ano': 25, 'anos_parou_fumar': 3, 'imunossupressao': 'nao'},
    {'idade': 50, 'sexo': 'feminino', 'tabagismo': 'nunca', 'gestante': 'nao', 'lactante': 'nao', 'imunossupressao': 'nao'},
    {'idade': 62, 'sexo': 'feminino', 'tabagismo': 'nunca', 'comorbidades': ['diabetes', 'hipertensao'],
     'medicacoes_continuo': 'metformina, losartana', 'imunossupressao': 'nao'},
    {'idade': 35, 'sexo': 'masculino', 'tabagismo': 'nunca', 'comorbidades': ['hiv'], 'cd4': 420, 'carga_viral': 0,
     'em_tarv': 'sim', 'supressao_viral': 'sim'},
    {'idade': 68, 'sexo': 'masculino', 'tabagismo': 'atual', 'macos_ano': 40, 'comorbidades': ['dpoc'], 'imunossupressao': 'nao'},
    {'idade': 88, 'sexo': 'masculino', 'tabagismo': 'nunca'},
]


@pytest.mark.parametrize('perfil', PERFIS, ids=lambda p: f"{p['sexo'][0]}{p['idade']}")
def test_cada_recomendacao_tem_os_campos_que_a_tela_e_os_pdfs_usam(client, perfil):
    resposta = client.post('/api/checkup-intelligent', json=perfil)
    assert resposta.status_code == 200
    dados = resposta.get_json()

    assert dados['recommendations'], 'perfil sem nenhuma recomendação'
    assert dados['total_recommendations'] == len(dados['recommendations'])
    for rec in dados['recommendations']:
        assert rec['titulo'].strip()
        assert rec['categoria'] in CATEGORIAS, rec['titulo']
        assert rec['prioridade'] in PRIORIDADES, rec['titulo']
        assert rec['referencia'], rec['titulo']
        assert rec['subtitulo'] is not None, rec['titulo']
        assert rec['grau_evidencia'] is not None, rec['titulo']

    titulos = [rec['titulo'] for rec in dados['recommendations']]
    assert len(titulos) == len(set(titulos)), 'título repetido na mesma resposta'
