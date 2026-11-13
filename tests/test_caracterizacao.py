"""Caracterização do motor de recomendações.

Este teste NÃO afirma que as saídas estão clinicamente corretas. Ele registra o
que o motor devolve hoje para um conjunto fixo de vinhetas, inclusive o que
está sabidamente errado (ver "Abertos" em docs/registro-de-perigos.md), para
que toda mudança de comportamento apareça no pull request e seja revisada.

Quando a mudança for intencional, atualize o registro e confira o diff do
arquivo `tests/caracterizacao/vinhetas.json` antes de mesclar:

    ATUALIZAR_CARACTERIZACAO=1 python -m pytest tests/test_caracterizacao.py
"""
import json
import os
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).resolve().parent / 'caracterizacao' / 'vinhetas.json'

LIBERADA_H = {'imunossupressao': 'nao'}
LIBERADA_M = {'gestante': 'nao', 'lactante': 'nao', 'imunossupressao': 'nao'}

VINHETAS = {
    'h25_higido': {'idade': 25, 'sexo': 'masculino', 'tabagismo': 'nunca', **LIBERADA_H},
    'm30_higida': {'idade': 30, 'sexo': 'feminino', 'tabagismo': 'nunca', **LIBERADA_M},
    'm30_sem_triagem': {'idade': 30, 'sexo': 'feminino', 'tabagismo': 'nunca'},
    'm30_gestante': {'idade': 30, 'sexo': 'feminino', 'tabagismo': 'nunca', **LIBERADA_M, 'gestante': 'sim',
                     'idade_gestacional': '20', 'primeira_consulta': 'sim'},
    'h45_ex_tabagista': {'idade': 45, 'sexo': 'masculino', 'tabagismo': 'ex', 'macos_ano': 25,
                         'anos_parou_fumar': 3, **LIBERADA_H},
    'm50_higida': {'idade': 50, 'sexo': 'feminino', 'tabagismo': 'nunca', **LIBERADA_M},
    'h55_pa_limitrofe_fumante': {'idade': 55, 'sexo': 'masculino', 'tabagismo': 'atual', 'macos_ano': 30,
                                 'pas': 132, 'pad': 80, 'colesterol': 200, 'hdl': 45, 'creatinina': 1.0,
                                 **LIBERADA_H},
    'h60_dm_has': {'idade': 60, 'sexo': 'masculino', 'tabagismo': 'ex', 'macos_ano': 25, 'anos_parou_fumar': 3,
                   'comorbidades': ['diabetes', 'hipertensao'], 'medicacoes_continuo': 'metformina, losartana',
                   **LIBERADA_H},
    'h58_has_resistente': {'idade': 58, 'sexo': 'masculino', 'tabagismo': 'nunca', 'comorbidades': ['hipertensao'],
                           'pas': 162, 'pad': 98,
                           'medicacoes_continuo': 'losartana, anlodipino, hidroclorotiazida, espironolactona',
                           **LIBERADA_H},
    'm62_dm': {'idade': 62, 'sexo': 'feminino', 'tabagismo': 'nunca', 'comorbidades': ['diabetes'],
               'pas': 120, 'pad': 70, 'hba1c': 7.4, 'imunossupressao': 'nao'},
    'h68_ex_fumante_leve': {'idade': 68, 'sexo': 'masculino', 'tabagismo': 'ex', 'macos_ano': 5,
                            'anos_parou_fumar': 20, **LIBERADA_H},
    'h68_dpoc_fumante': {'idade': 68, 'sexo': 'masculino', 'tabagismo': 'atual', 'macos_ano': 40,
                         'comorbidades': ['dpoc'], **LIBERADA_H},
    'm70_higida': {'idade': 70, 'sexo': 'feminino', 'tabagismo': 'nunca', 'imunossupressao': 'nao'},
    'h88_higido': {'idade': 88, 'sexo': 'masculino', 'tabagismo': 'nunca', **LIBERADA_H},
    'h35_hiv_cd4_150': {'idade': 35, 'sexo': 'masculino', 'tabagismo': 'nunca', 'comorbidades': ['hiv'],
                        'cd4': 150, 'carga_viral': 80000, 'em_tarv': 'nao'},
    'h35_hiv_controlado': {'idade': 35, 'sexo': 'masculino', 'tabagismo': 'nunca', 'comorbidades': ['hiv'],
                           'cd4': 600, 'carga_viral': 0, 'em_tarv': 'sim', 'supressao_viral': 'sim'},
    'h40_imunossuprimido': {'idade': 40, 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'sim'},
}


def _resumir(dados):
    por_categoria = {}
    for rec in dados['recommendations']:
        por_categoria.setdefault(rec['categoria'], []).append(rec['titulo'])
    return {
        'recomendacoes': por_categoria,
        'nao_incluidas': [[item['titulo'], item['estado']] for item in dados['nao_incluidas']],
        'outras_recomendacoes': [item.get('titulo') for item in dados.get('outras_recomendacoes', [])],
    }


def _observar(client):
    observado = {}
    for nome, entrada in VINHETAS.items():
        resposta = client.post('/api/checkup-intelligent', json=entrada)
        assert resposta.status_code == 200, (nome, resposta.get_json())
        observado[nome] = {'entrada': entrada, **_resumir(resposta.get_json())}
    return observado


def test_saida_do_motor_para_as_vinhetas_nao_mudou(client):
    observado = _observar(client)

    if os.environ.get('ATUALIZAR_CARACTERIZACAO'):
        ARQUIVO.parent.mkdir(exist_ok=True)
        ARQUIVO.write_text(json.dumps(observado, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        pytest.skip('registro de caracterização atualizado; confira o diff antes de mesclar')

    registrado = json.loads(ARQUIVO.read_text(encoding='utf-8'))
    assert set(observado) == set(registrado), 'conjunto de vinhetas diferente do registro'

    diferencas = []
    for nome in VINHETAS:
        if observado[nome] != registrado[nome]:
            diferencas.append(nome)
            antes = json.dumps(registrado[nome], ensure_ascii=False, indent=2, sort_keys=True).splitlines()
            depois = json.dumps(observado[nome], ensure_ascii=False, indent=2, sort_keys=True).splitlines()
            import difflib
            print(f'\n--- {nome}')
            print('\n'.join(difflib.unified_diff(antes, depois, 'registrado', 'observado', lineterm='', n=1)))

    assert not diferencas, (
        f'O motor mudou de comportamento em: {", ".join(diferencas)}. '
        'Se a mudança for intencional, atualize o registro (ver o cabeçalho deste arquivo) '
        'e revise o diff no pull request.'
    )
