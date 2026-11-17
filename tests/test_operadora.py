"""Modo sombra da conta de operadora (src/utils/operadora.py). Todos os dados são fictícios."""
import subprocess
import sys
from pathlib import Path

import pytest

from src.utils import operadora as op, tuss

RAIZ = Path(__file__).resolve().parents[1]
HBA1C = tuss.CODIGOS['Hemoglobina glicada (HbA1c), soro'][0]
PSA = tuss.CODIGOS['PSA total, soro'][0]
LPA = tuss.CODIGOS['Lipoproteína(a) - Lp(a), soro'][0]
HIV = tuss.CODIGOS['Anti-HIV 1 e 2, soro'][0]
CREATININA = tuss.CODIGOS['Creatinina, soro'][0]
VITAMINA_D, VITAMINA_D_ATIVA, TESTOSTERONA, UROCULTURA, HERPES_IGG = '40302830', '40305015', '40316513', '40310213', '40307085'


def _linha(**campos):
    base = dict(id_pedido='p1', id_beneficiario='b1', idade='52', sexo='M', data_pedido='2026-11-10',
                codigo_tuss=HBA1C, carater='eletivo', regime='ambulatorial')
    base.update(campos)
    return base


def _um(**campos):
    resultados, _ = op.classificar_lote([_linha(**campos)])
    assert not resultados[0]['erro'], resultados[0]['erro']
    return resultados[0]


def test_recomendado_e_dentro_do_intervalo_e_liberado():
    r = _um(finalidade='rastreio')
    assert (r['cor'], r['acao'], r['codigo_do_motivo'], r['grau']) == ('verde', 'liberaria', 'recomendado', 'B')
    assert r['exame'] == 'Hemoglobina glicada (HbA1c), soro' and r['link'].startswith('https://')
    assert r['finalidade_usada'] == 'rastreio' and r['origem_da_finalidade'] == 'informada'


def test_antes_do_intervalo_do_check_up_seria_barrado():
    """HbA1c de rastreio: a cada 3 anos se normal (a mesma periodicidade do check-up)."""
    r = _um(finalidade='rastreio', data_ultimo_exame='2025-11-01')
    assert (r['cor'], r['acao'], r['codigo_do_motivo']) == ('vermelho', 'barraria', 'antes_do_intervalo')
    assert r['proxima_data_elegivel'] == '2028-11-01' and '01/11/2028' in r['motivo']
    assert _um(finalidade='rastreio', data_ultimo_exame='2023-11-01')['cor'] == 'verde'
    assert _um(finalidade='rastreio', data_ultimo_exame='01/11/2025')['cor'] == 'vermelho'      # data no formato brasileiro


def test_uma_vez_na_vida():
    r = _um(codigo_tuss=LPA, finalidade='rastreio', data_ultimo_exame='2024-01-01')
    assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'ja_realizado')
    # "Pelo menos uma vez": repetir depende de risco, que o pedido não informa
    r = _um(codigo_tuss=HIV, finalidade='rastreio', data_ultimo_exame='2024-01-01')
    assert (r['cor'], r['acao'], r['codigo_do_motivo']) == ('amarelo', 'pediria esclarecimento', 'repeticao_depende_de_risco')


def test_grau_da_recomendacao():
    r = _um(codigo_tuss=PSA, idade='60', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo'], r['grau']) == ('amarelo', 'decisao_individual', 'C')
    r = _um(codigo_tuss=PSA, idade='72', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'recomendacao_contraria')
    assert 'grau D' in r['motivo'] and r['referencia'] == 'USPSTF 2018' and r['link'].startswith('https://')
    r = _um(codigo_tuss=CREATININA, idade='30', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'sem_recomendacao_para_o_perfil')


def test_pareceres_contra_o_pedido_de_rotina():
    r = _um(codigo_tuss=VITAMINA_D, idade='44', sexo='F')
    assert (r['cor'], r['codigo_do_motivo'], r['referencia']) == ('vermelho', 'parecer_contrario', 'Endocrine Society 2024')
    assert r['link'] == 'https://doi.org/10.1210/clinem/dgae290'
    assert _um(codigo_tuss=VITAMINA_D_ATIVA)['codigo_do_motivo'] == 'parecer_contrario'
    mulher, homem = _um(codigo_tuss=TESTOSTERONA, sexo='F', idade='38'), _um(codigo_tuss=TESTOSTERONA, sexo='M', idade='61')
    assert mulher['codigo_do_motivo'] == homem['codigo_do_motivo'] == 'parecer_contrario'
    assert 'Consenso Global 2019' in mulher['motivo'] and 'Endocrine Society 2018' in homem['motivo']
    herpes = _um(codigo_tuss=HERPES_IGG, sexo='F')
    assert (herpes['codigo_do_motivo'], herpes['referencia']) == ('parecer_contrario', 'USPSTF 2023')
    # Bacteriúria assintomática: só homens; na mulher o rastreio depende de gestação, que o pedido não informa
    urocultura = _um(codigo_tuss=UROCULTURA, sexo='M', idade='33')
    assert (urocultura['codigo_do_motivo'], urocultura['referencia']) == ('parecer_contrario', 'USPSTF 2019')
    assert _um(codigo_tuss=UROCULTURA, sexo='F', idade='33')['codigo_do_motivo'] == 'sem_recomendacao_para_o_perfil'
    # O parecer é sobre rotina: com indicação informada, o exame é liberado
    assert _um(codigo_tuss=TESTOSTERONA, sexo='M', idade='61', cid='E29.1')['cor'] == 'verde'
    assert _um(codigo_tuss=VITAMINA_D, finalidade='seguimento')['cor'] == 'verde'


def test_todo_parecer_tem_codigo_conferido_fonte_e_link():
    tabela = {**tuss.DA_TABELA, **tuss.DESCRICOES}
    for parecer in op.PARECERES_CONTRARIOS:
        assert parecer['codigos'] and all(codigo in tabela for codigo in parecer['codigos']), parecer
        assert parecer['link'].startswith('https://') and parecer['referencia'] and parecer['motivo'].endswith('.')
        assert parecer['sexo'] in (None, 'feminino', 'masculino')


def test_finalidade_informada_pelo_cid_ou_presumida():
    r = _um(cid='E11.9', data_ultimo_exame='2026-08-01')            # diabético em seguimento não é rastreio
    assert (r['cor'], r['codigo_do_motivo'], r['origem_da_finalidade']) == ('verde', 'indicacao_pelo_cid', 'cid')
    assert 'E11.9' in r['motivo']
    r = _um(cid='Z00.0', data_ultimo_exame='2025-11-01')            # CID de exame de rotina: rastreio
    assert (r['cor'], r['finalidade_usada'], r['origem_da_finalidade']) == ('vermelho', 'rastreio', 'cid')
    r = _um(data_ultimo_exame='2025-11-01')                         # sem finalidade nem CID: presume rastreio
    assert (r['cor'], r['origem_da_finalidade']) == ('vermelho', 'presumida')
    r = _um(finalidade='diagnostico', data_ultimo_exame='2026-10-01')
    assert (r['cor'], r['codigo_do_motivo']) == ('verde', 'indicacao_informada')


def test_fora_do_escopo_e_sem_regra():
    assert _um(carater='urgencia')['cor'] == _um(regime='internado')['cor'] == 'fora_do_escopo'
    assert _um(carater='Emergência')['acao'] == 'passaria direto'
    assert _um(codigo_tuss='40301010')['codigo_do_motivo'] == 'sem_regra'           # código de laboratório sem regra
    assert _um(codigo_tuss='99999999')['codigo_do_motivo'] == 'codigo_desconhecido'
    assert _um(codigo_tuss='99999999')['cor'] == 'verde'
    assert _um(idade='12', finalidade='rastreio')['codigo_do_motivo'] == 'idade_fora_do_motor'


def test_linha_invalida_nao_e_classificada():
    resultados, resumo = op.classificar_lote([_linha(sexo='X', codigo_tuss='123'), _linha(idade='abc'),
                                              {'id_pedido': 'p9'}, _linha(data_ultimo_exame='2027-01-01'), _linha()])
    assert [bool(r['erro']) for r in resultados] == [True, True, True, True, False]
    assert 'sexo inválido' in resultados[0]['erro'] and 'codigo_tuss inválido' in resultados[0]['erro']
    assert 'falta id_beneficiario' in resultados[2]['erro'] and resultados[0]['cor'] == ''
    assert (resumo['linhas'], resumo['invalidas'], resumo['por_cor']) == (5, 4, {'verde': 1})


def test_resumo_separa_o_que_depende_de_presumir_rastreio():
    _, resumo = op.classificar_lote([
        _linha(finalidade='rastreio', valor='18,50'),
        _linha(data_ultimo_exame='2025-11-01', valor='18,50'),
        _linha(codigo_tuss=VITAMINA_D, valor='1.042,00'),
        _linha(codigo_tuss=PSA, idade='60', cid='Z00.0', valor='30.00'),
    ])
    assert resumo['por_cor'] == {'verde': 1, 'vermelho': 2, 'amarelo': 1}
    assert resumo['origem_da_finalidade'] == {'amarelo': {'cid': 1}, 'vermelho': {'presumida': 2}}
    assert resumo['valor_por_cor'] == {'verde': 18.5, 'vermelho': 1060.5, 'amarelo': 30.0}
    assert resumo['mais_barrados'][0][1] == 1 and resumo['versao'] == op.VERSAO


def test_arquivo_csv_com_ponto_e_virgula_e_script(tmp_path):
    entrada = tmp_path / 'pedidos.csv'
    entrada.write_text('﻿id_pedido;id_beneficiario;idade;sexo;data_pedido;codigo_tuss;carater;regime;finalidade\n'
                       f'p1;b1;52;M;2026-11-10;{HBA1C};eletivo;ambulatorial;rastreio\n'
                       f'p2;b2;44;F;2026-11-10;{VITAMINA_D};eletivo;ambulatorial;\n', encoding='utf-8')
    execucao = subprocess.run([sys.executable, str(RAIZ / 'scripts' / 'modo_sombra.py'), str(entrada)],
                              capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 0, execucao.stderr
    assert 'nada foi barrado' in execucao.stdout and 'Barraria: 1 (50.0%)' in execucao.stdout
    linhas = op.ler_csv((tmp_path / 'pedidos_classificado.csv').read_text(encoding='utf-8'))
    assert [(x['id_pedido'], x['cor']) for x in linhas] == [('p1', 'verde'), ('p2', 'vermelho')]
    assert linhas[1]['referencia'] == 'Endocrine Society 2024' and linhas[0]['versao'] == op.VERSAO


def test_o_motor_fora_do_servidor_nao_registra_uso(monkeypatch):
    """O modo sombra chama o motor direto; só a rota do check-up conta uso."""
    from src.routes.checkup_intelligent import recomendar
    from src.utils import uso

    def falhar(*_a, **_k):
        raise AssertionError('uso registrado fora da rota')
    monkeypatch.setattr(uso, 'registrar', falhar)
    resposta, status = recomendar({'idade': 52, 'sexo': 'masculino', 'tabagismo': 'nunca_fumou'})
    assert status == 200 and resposta['recommendations']
    resposta, status = recomendar({'idade': 12, 'sexo': 'masculino', 'tabagismo': 'nunca_fumou'})
    assert status == 400 and resposta['codigo'] == 'entrada_invalida'
