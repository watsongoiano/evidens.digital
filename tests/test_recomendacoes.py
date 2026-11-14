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


# --- Correções de novembro de 2026 ---------------------------------------------------------------

def _recs(client, **dados):
    base = dict(idade=52, sexo='masculino', tabagismo='nunca', imunossupressao='nao', comorbidades=[], medicacoes=[],
                historia_familiar=[])
    resposta = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert resposta.status_code == 200, resposta.get_json()
    return {r['titulo']: r for r in resposta.get_json()['recommendations']}


@pytest.mark.parametrize('dados', [
    dict(comorbidades=['diabetes']), dict(hba1c='7.4'), dict(medicacoes=['insulina_nph']),
    dict(medicacoes=['glibenclamida']), dict(medicacoes_continuo='gliclazida 30 mg'),
], ids=['caixa', 'hba1c', 'insulina', 'sulfonilureia', 'texto'])
def test_diabetico_nao_recebe_totg_e_a_glicemia_vira_acompanhamento(client, dados):
    recs = _recs(client, **dados)
    assert not any(t.startswith('TOTG') for t in recs), 'TOTG pedido a quem já é diabético'
    assert recs['Hemoglobina glicada (HbA1c), soro']['subtitulo'].startswith('Diabéticos | A cada 3-6 meses')
    assert 'Rastreamento' not in recs['Hemoglobina glicada (HbA1c), soro']['descricao']
    assert recs['Glicose, soro']['subtitulo'].startswith('Diabéticos')


def test_totg_so_com_indicacao(client):
    """TOTG confirma o diagnóstico quando glicemia ou HbA1c estão limítrofes; não é exame de rotina."""
    tem_totg = lambda **dados: any(t.startswith('TOTG-75g') for t in _recs(client, **dados))  # noqa: E731
    # check-up de rotina, em qualquer idade e sexo, com ou sem fator de risco: sem TOTG
    for dados in (dict(), dict(idade=25), dict(idade=70, sexo='feminino', gestante='nao', lactante='nao'), dict(hba1c='5.2'),
                  dict(comorbidades=['hipertensao', 'obesidade']), dict(historia_familiar=['diabetes']), dict(comorbidades=['sop'])):
        assert not tem_totg(**dados), dados
    # indicação: pré-diabetes marcado ou HbA1c de 5,7 a 6,4%
    assert tem_totg(comorbidades=['pre_diabetes']) and tem_totg(hba1c='5.7') and tem_totg(hba1c='6.4')
    totg = next(r for t, r in _recs(client, hba1c='6.0').items() if t.startswith('TOTG-75g'))
    assert 'limítrofes' in totg['subtitulo'] and 'confirma' in totg['descricao']
    # pré-diabetes marcado em quem já é diabético: sem TOTG
    assert not tem_totg(comorbidades=['pre_diabetes', 'diabetes']) and not tem_totg(comorbidades=['pre_diabetes'], hba1c='7.0')


def test_calcio_e_sempre_o_ionico_e_a_espirometria_e_com_broncodilatador(client):
    from src.utils.catalogo import catalogo

    pedidos = {}
    for dados in (dict(comorbidades=['diabetes']), dict(medicacoes=['litio']), dict(historia_familiar=['nem1']),
                  dict(historia_familiar=['nem2']), dict(comorbidades=['dpoc'], tabagismo='ex', macos_ano=30, anos_parou_fumar=2),
                  dict(medicacoes=['prednisona'], dose__prednisona=40, duracao__prednisona=4)):
        pedidos.update(_recs(client, **dados))
    todos = list(pedidos) + [t for itens in catalogo().values() for t in itens]
    assert 'Cálcio iônico, soro' in pedidos and 'Espirometria, com broncodilatador' in pedidos
    assert not [t for t in todos if t.lower().startswith('cálcio') and 'iônico' not in t]
    assert [t for t in todos if 'spirometria' in t] == ['Espirometria, com broncodilatador'] * 2  # motor e catálogo


def test_referencia_do_williams_abre_a_pagina_do_livro(client):
    from src.utils.reference_links import build_reference_links

    links = build_reference_links('Hemograma completo', 'Einstein Pré-Natal v.3 (2024) / MS 2012-2016 / Williams 26e')
    williams = [link for link in links if 'Williams' in link['label']]
    assert williams and williams[0]['url'].startswith('https://www.mheducation.com/highered/mhp/product/williams-obstetrics-')
    novas = build_reference_links('Albumina, soro', 'CGH 2025 (Feuerstein) / Drugs Aging 2024 (Sparling)')
    assert [link['url'] for link in novas] == ['https://doi.org/10.1016/j.cgh.2025.05.019', 'https://doi.org/10.1007/s40266-024-01143-8']
