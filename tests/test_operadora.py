"""Modo sombra da conta de operadora (src/utils/operadora.py). Todos os dados são fictícios."""
import subprocess
import sys
from pathlib import Path

import pytest

from src.utils import operadora as op, tuss
from tests.test_laudos import FORMATO_A, FORMATO_B, FORMATO_C, _pdf

RAIZ = Path(__file__).resolve().parents[1]
HBA1C = tuss.CODIGOS['Hemoglobina glicada (HbA1c), soro'][0]
GLICEMIA = tuss.CODIGOS['Glicemia de jejum, soro'][0]
PSA = tuss.CODIGOS['PSA total, soro'][0]
LPA = tuss.CODIGOS['Lipoproteína(a) - Lp(a), soro'][0]
HIV = tuss.CODIGOS['Anti-HIV 1 e 2, soro'][0]
CREATININA = tuss.CODIGOS['Creatinina, soro'][0]
FIT = tuss.CODIGOS['Sangue oculto nas fezes (FIT)'][0]
CITOLOGIA = tuss.CODIGOS['Citologia cervicovaginal (Papanicolaou)'][0]
VITAMINA_D, VITAMINA_D_ATIVA, TESTOSTERONA, UROCULTURA, HERPES_IGG = '40302830', '40305015', '40316513', '40310213', '40307085'
VHS, ACIDO_URICO, ELETROFORESE, FAN, PAINEL_REUMATOLOGICO = '40304370', '40301150', '40301761', '40306852', '40312127'
ANTI_TPO, T4_LIVRE, TSH = '40306437', '40316491', '40316521'
SANGRAMENTO_IVY, H_PYLORI_IGG, FOLATO_ERITROCITARIO = '40304612', '40306917', '40301087'
MAMOGRAFIA = '40808041'


def _linha(**campos):
    base = dict(id_pedido='p1', id_beneficiario='b1', idade='52', sexo='M', data_pedido='2026-11-10',
                codigo_tuss=HBA1C, carater='eletivo', regime='ambulatorial')
    base.update(campos)
    return base


def _um(**campos):
    resultados, _ = op.classificar_lote([_linha(**campos)])
    assert not resultados[0]['erro'], resultados[0]['erro']
    return resultados[0]


def _cor(**campos):
    r = _um(**campos)
    return r['cor'], r['codigo_do_motivo']


def _erro(**campos):
    resultados, _ = op.classificar_lote([_linha(**campos)])
    return resultados[0]['erro']


def test_recomendado_e_dentro_do_intervalo_e_liberado():
    r = _um(finalidade='rastreio')
    assert (r['cor'], r['acao'], r['codigo_do_motivo'], r['grau']) == ('verde', 'liberaria', 'recomendado', 'B')
    assert r['exame'] == 'Hemoglobina glicada (HbA1c), soro' and r['link'].startswith('https://')
    assert r['finalidade_usada'] == 'rastreio' and r['origem_da_finalidade'] == 'informada'


def test_antes_do_intervalo_do_check_up_seria_barrado():
    """FIT anual (a mesma periodicidade do check-up): repetido antes de um ano."""
    r = _um(codigo_tuss=FIT, finalidade='rastreio', data_ultimo_exame='2026-06-01')
    assert (r['cor'], r['acao'], r['codigo_do_motivo']) == ('vermelho', 'barraria', 'antes_do_intervalo')
    assert r['proxima_data_elegivel'] == '2027-06-01' and '01/06/2027' in r['motivo']
    assert (r['ultimo_exame_usado'], r['origem_do_ultimo_exame']) == ('2026-06-01', 'informada')
    assert _cor(codigo_tuss=FIT, finalidade='rastreio', data_ultimo_exame='2025-06-01') == ('verde', 'recomendado')
    assert _cor(codigo_tuss=FIT, finalidade='rastreio', data_ultimo_exame='01/06/2026')[0] == 'vermelho'      # data brasileira


def test_intervalo_que_depende_do_resultado_anterior_fica_no_amarelo():
    """HbA1c "a cada 3 anos se normal": no pré-diabetes é anual, e o pedido não traz o resultado anterior."""
    r = _um(finalidade='rastreio', data_ultimo_exame='2025-11-01')
    assert (r['cor'], r['codigo_do_motivo'], r['proxima_data_elegivel']) == (
        'amarelo', 'intervalo_depende_do_resultado', '2028-11-01')
    assert 'resultado anterior' in r['motivo']
    assert _cor(finalidade='rastreio', data_ultimo_exame='2023-11-01') == ('verde', 'recomendado')


def test_hba1c_repetida_em_menos_de_tres_meses_em_qualquer_finalidade():
    for campos in (dict(finalidade='rastreio'), dict(cid='E11.9'), dict(finalidade='seguimento')):
        r = _um(data_ultimo_exame='2026-09-01', **campos)
        assert (r['cor'], r['codigo_do_motivo'], r['proxima_data_elegivel']) == ('vermelho', 'antes_do_intervalo', '2026-12-01')
        assert r['referencia'] == 'CSCC 2024 e SBPC/ML 2023 (Choosing Wisely)' and r['link'].startswith('https://')
    assert _cor(cid='E11.9', data_ultimo_exame='2026-08-01') == ('verde', 'indicacao_pelo_cid')     # diabético, 3 meses depois


def test_uma_vez_na_vida():
    r = _um(codigo_tuss=LPA, finalidade='rastreio', data_ultimo_exame='2024-01-01')
    assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'ja_realizado')
    assert r['motivo'] == 'Indicação de uma única vez (dose única na vida); já feito em 01/01/2024.'
    # "Pelo menos uma vez": repetir depende de risco, que o pedido não informa
    r = _um(codigo_tuss=HIV, finalidade='rastreio', data_ultimo_exame='2024-01-01')
    assert (r['cor'], r['acao'], r['codigo_do_motivo']) == ('amarelo', 'pediria esclarecimento', 'repeticao_depende_de_risco')


def test_grau_da_recomendacao():
    r = _um(codigo_tuss=PSA, idade='60', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo'], r['grau']) == ('amarelo', 'decisao_individual', 'C')
    assert r['aviso'].startswith('Divergência: a SBMFC 2018')
    r = _um(codigo_tuss=PSA, idade='72', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo'], r['aviso']) == ('vermelho', 'recomendacao_contraria', '')
    assert 'grau D' in r['motivo'] and r['referencia'] == 'USPSTF 2018' and r['link'].startswith('https://')


def test_sem_recomendacao_para_o_perfil_pede_esclarecimento_e_nao_barra():
    """Exame que o check-up não indica e que não tem parecer contrário de sociedade não é barrado: pede-se a
    indicação clínica. A regra geral contra exames de rotina (Choosing Wisely) foi retirada pelo responsável clínico."""
    r = _um(codigo_tuss=CREATININA, idade='30', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo']) == ('amarelo', 'sem_recomendacao_para_o_perfil')
    assert r['referencia'] == '' and r['link'] == '' and 'Choosing Wisely' not in r['motivo']
    assert r['motivo'].endswith('Pedir a indicação clínica.')


def test_exame_alternativo_ao_recomendado_e_aceito():
    """O check-up aceita a glicemia pela HbA1c e, onde não há DNA-HPV, a citologia (MS 2025)."""
    r = _um(codigo_tuss=GLICEMIA, idade='50')
    assert (r['cor'], r['codigo_do_motivo'], r['exame']) == ('verde', 'alternativa_aceita', 'Glicose, soro')
    assert r['referencia'] == 'ADA 2026 / USPSTF 2021' and r['link'].startswith('https://')
    assert _cor(codigo_tuss=GLICEMIA, idade='50', data_ultimo_exame='2025-11-01') == ('amarelo', 'intervalo_depende_do_resultado')
    assert _cor(codigo_tuss=GLICEMIA, idade='25') == ('amarelo', 'sem_recomendacao_para_o_perfil')      # fora de 35-70
    assert _cor(codigo_tuss=CITOLOGIA, sexo='F', idade='35') == ('verde', 'alternativa_aceita')
    assert _cor(codigo_tuss=CITOLOGIA, sexo='F', idade='22') == ('verde', 'recomendado')                 # o próprio check-up
    r = _um(codigo_tuss=CITOLOGIA, sexo='F', idade='35', data_ultimo_exame='2025-11-01')
    assert (r['cor'], r['codigo_do_motivo']) == ('amarelo', 'intervalo_depende_do_resultado')
    assert 'após dois exames anuais normais' in r['motivo']
    assert _cor(codigo_tuss=CITOLOGIA, sexo='F', idade='70') == ('amarelo', 'sem_recomendacao_para_o_perfil')


def test_pareceres_contra_o_pedido_de_rotina():
    r = _um(codigo_tuss=VITAMINA_D, idade='44', sexo='F')
    assert (r['cor'], r['codigo_do_motivo'], r['referencia']) == ('vermelho', 'parecer_contrario', 'Endocrine Society 2024')
    assert r['link'] == 'https://doi.org/10.1210/clinem/dgae290' and 'USPSTF 2021' in r['aviso']
    assert _cor(codigo_tuss=VITAMINA_D_ATIVA) == ('vermelho', 'parecer_contrario')
    mulher, homem = _um(codigo_tuss=TESTOSTERONA, sexo='F', idade='38'), _um(codigo_tuss=TESTOSTERONA, sexo='M', idade='61')
    assert mulher['codigo_do_motivo'] == homem['codigo_do_motivo'] == 'parecer_contrario'
    assert 'Endocrine Society 2014' in mulher['motivo'] and 'Endocrine Society 2018' in homem['motivo']
    herpes = _um(codigo_tuss=HERPES_IGG, sexo='F')
    assert (herpes['codigo_do_motivo'], herpes['referencia']) == ('parecer_contrario', 'USPSTF 2023 e SBI 2019')
    for codigo in (VHS, ACIDO_URICO, ELETROFORESE, FAN, PAINEL_REUMATOLOGICO, ANTI_TPO, T4_LIVRE):
        r = _um(codigo_tuss=codigo)
        assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'parecer_contrario'), codigo
        assert 'Choosing Wisely' in r['motivo'] and r['link'].startswith('https://')
    # O parecer é sobre rotina: com indicação informada, o exame é liberado
    assert _cor(codigo_tuss=TESTOSTERONA, sexo='M', idade='61', cid='E29.1') == ('verde', 'indicacao_pelo_cid')
    assert _cor(codigo_tuss=VITAMINA_D, finalidade='seguimento') == ('verde', 'indicacao_informada')
    assert _cor(codigo_tuss=VHS, cid='M05.9') == ('verde', 'indicacao_pelo_cid')
    assert _cor(codigo_tuss=VITAMINA_D, idade='16')[1] != 'parecer_contrario'            # os pareceres são de adultos


def test_urocultura_de_rastreio_depende_de_gestacao():
    """USPSTF 2019: grau B na gestação, grau D fora dela. O pedido não informa gestação."""
    r = _um(codigo_tuss=UROCULTURA, sexo='M', idade='33')
    assert (r['cor'], r['codigo_do_motivo'], r['referencia']) == ('vermelho', 'parecer_contrario', 'USPSTF 2019 e SBI 2019')
    assert _cor(codigo_tuss=UROCULTURA, sexo='F', idade='33') == ('amarelo', 'depende_de_gestacao')
    assert _cor(codigo_tuss=UROCULTURA, sexo='F', idade='49') == ('amarelo', 'depende_de_gestacao')
    assert _cor(codigo_tuss=UROCULTURA, sexo='F', idade='50') == ('vermelho', 'parecer_contrario')


def test_evidencia_insuficiente_e_divergencia_ficam_no_amarelo_com_aviso():
    r = _um(codigo_tuss=TSH)
    assert (r['cor'], r['codigo_do_motivo'], r['referencia']) == ('amarelo', 'evidencia_insuficiente', 'USPSTF 2015')
    assert 'grau I' in r['motivo'] and r['aviso'].startswith('Divergência: SBMFC 2018 e CFPC')
    r = _um(codigo_tuss=VITAMINA_D, idade='70')                       # SBPC/ML e SBEM 2017 indicam acima de 60 anos
    assert (r['cor'], r['codigo_do_motivo']) == ('amarelo', 'divergencia_entre_diretrizes')
    assert r['aviso'].startswith('Divergência: SBPC/ML e SBEM 2017')
    assert _cor(codigo_tuss=VITAMINA_D, idade='60') == ('vermelho', 'parecer_contrario')


def test_parecer_contra_o_exame_vale_em_qualquer_finalidade():
    assert _cor(codigo_tuss=SANGRAMENTO_IVY, finalidade='diagnostico') == ('vermelho', 'parecer_contrario')
    r = _um(codigo_tuss=H_PYLORI_IGG, cid='K29.7')
    assert (r['cor'], r['codigo_do_motivo']) == ('vermelho', 'parecer_contrario')
    assert 'antígeno fecal' in r['motivo'] and r['finalidade_usada'] == 'diagnostico'
    assert _cor(codigo_tuss=FOLATO_ERITROCITARIO, finalidade='seguimento') == ('vermelho', 'parecer_contrario')
    assert _cor(codigo_tuss=SANGRAMENTO_IVY, carater='urgencia')[0] == 'fora_do_escopo'


def test_todo_parecer_tem_codigo_conferido_fonte_e_link():
    tabela = {**tuss.DA_TABELA, **tuss.DESCRICOES}
    for parecer in op.PARECERES_CONTRARIOS + op.INTERVALOS_MINIMOS:
        assert parecer['codigos'] and all(codigo in tabela for codigo in parecer['codigos']), parecer
        assert parecer['link'].startswith('https://') and parecer['referencia']
    for parecer in op.PARECERES_CONTRARIOS:
        assert parecer['motivo'].endswith('.') and parecer['sexo'] in (None, 'feminino', 'masculino')
        assert parecer['cor'] in ('vermelho', 'amarelo') and parecer['escopo'] in ('rastreio', 'sempre')
        assert 18 <= parecer['idade_min'] <= parecer['idade_max'] <= 120
        assert not parecer['aviso'] or parecer['aviso'].startswith('Divergência')
    for alternativa in op.ALTERNATIVAS:
        assert alternativa['codigo'] in tabela and alternativa['no_lugar_de'] in tabela
    assert all(codigo in tabela for codigo in op.AVISOS_DE_DIVERGENCIA)


def test_finalidade_informada_pelo_cid_ou_presumida():
    r = _um(cid='E11.9')                                            # diabético em seguimento não é rastreio
    assert (r['cor'], r['codigo_do_motivo'], r['origem_da_finalidade']) == ('verde', 'indicacao_pelo_cid', 'cid')
    assert 'E11.9' in r['motivo']
    r = _um(codigo_tuss=FIT, cid='Z00.0', data_ultimo_exame='2026-06-01')            # CID de exame de rotina: rastreio
    assert (r['cor'], r['finalidade_usada'], r['origem_da_finalidade']) == ('vermelho', 'rastreio', 'cid')
    r = _um(codigo_tuss=FIT, data_ultimo_exame='2026-06-01')         # sem finalidade nem CID: presume rastreio
    assert (r['cor'], r['origem_da_finalidade']) == ('vermelho', 'presumida')
    assert _cor(codigo_tuss=FIT, finalidade='diagnostico', data_ultimo_exame='2026-10-01') == ('verde', 'indicacao_informada')
    assert _um(codigo_tuss=VHS, finalidade='Rotina')['finalidade_usada'] == 'rastreio'


@pytest.mark.parametrize('cid, rastreio', [
    ('Z00.0', True), ('Z01.4', True), ('Z02.1', True), ('Z10.0', True), ('Z12.5', True), ('Z13.1', True),
    ('Z01.8', False),      # usado na avaliação pré-operatória
    ('Z03.1', False), ('Z04.8', False),      # observação por suspeita
    ('Z08.0', False), ('Z09.0', False),      # seguimento após tratamento
    ('Z14', False), ('N39.0', False),
])
def test_cid_de_rotina(cid, rastreio):
    r = _um(codigo_tuss=PSA, idade='72', cid=cid)
    assert r['finalidade_usada'] == ('rastreio' if rastreio else 'diagnostico')
    assert r['cor'] == ('vermelho' if rastreio else 'verde')


def test_fora_do_escopo_e_sem_regra():
    for campos in (dict(carater='urgencia'), dict(regime='internado'), dict(carater='Urgência/Emergência'),
                   dict(carater='2'), dict(regime='Pronto-socorro')):
        assert _cor(**campos) == ('fora_do_escopo', 'urgencia_ou_internado'), campos
    assert _um(carater='Emergência')['acao'] == 'passaria direto'
    # Exame que não é de laboratório não é julgado, mesmo quando o check-up o recomenda
    r = _um(codigo_tuss=MAMOGRAFIA, sexo='F', idade='50', finalidade='rastreio')
    assert (r['cor'], r['codigo_do_motivo']) == ('fora_do_escopo', 'nao_laboratorial')
    assert _cor(codigo_tuss='10101012') == ('fora_do_escopo', 'nao_laboratorial')
    assert _cor(codigo_tuss='40301010') == ('verde', 'sem_regra')           # código de laboratório sem regra
    assert _cor(codigo_tuss='40399999') == ('verde', 'codigo_desconhecido')
    assert _cor(idade='12', finalidade='rastreio') == ('verde', 'idade_fora_do_motor')


def test_nome_do_exame_no_codigo_de_exame_combinado():
    """O ferro sérico não leva o nome do exame combinado do check-up (saturação de transferrina)."""
    assert _um(codigo_tuss='40301842')['exame'].startswith('Ferro sérico')
    assert _um(codigo_tuss=UROCULTURA)['exame'] == 'Cultura, urina com contagem de colônias'


def test_com_dois_titulos_para_o_mesmo_codigo_vale_o_da_lista_de_exames_comuns():
    assert _um(codigo_tuss='40308391')['exame'] == 'Proteína C reativa, soro'      # não "ultrassensível"
    assert _um(codigo_tuss='40304361')['exame'] == 'Hemograma completo com plaquetas'


def test_pedidos_do_laudo_em_pdf():
    """O laudo vira uma linha de pedido por exame identificado, com o código TUSS, a data da coleta, o sexo e a
    idade do cabeçalho e o regime indicado pelo setor."""
    linhas, soltos = op.pedidos_do_laudo(_pdf(FORMATO_C), 'laudo-teste')
    assert soltos == [] and len(linhas) == 16
    por_codigo = {linha['codigo_tuss']: linha for linha in linhas}
    assert set(por_codigo) == {
        '40304361', '40304590', '40304639', '40301630', '40301931', '40302580', '40301419', '40302423', '40301397',
        '40302504', '40302512', '40301648', '40302385', '40308391', '40301109', '40301400'}
    hemograma, creatinina = por_codigo['40304361'], por_codigo[CREATININA]
    assert (hemograma['data_pedido'], creatinina['data_pedido']) == ('2026-11-13', '2026-11-14')
    assert (creatinina['sexo'], creatinina['idade'], creatinina['regime']) == ('F', '46', 'internado')
    assert creatinina['id_beneficiario'] == 'laudo-teste' and len({linha['id_pedido'] for linha in linhas}) == 16
    assert not any('teste' in valor.lower() for linha in linhas for chave, valor in linha.items()
                   if chave not in ('id_pedido', 'id_beneficiario'))
    # Internado: o modo sombra não julga
    resultados, resumo = op.classificar_lote(linhas)
    assert resumo['por_cor'] == {'fora_do_escopo': 16} and not any(r['erro'] for r in resultados)
    # Informando o regime, o exame é classificado como qualquer pedido
    linhas, _ = op.pedidos_do_laudo(_pdf(FORMATO_C), 'laudo-teste', regime='ambulatorial', cid='N18.3')
    resultados, resumo = op.classificar_lote(linhas)
    assert set(resumo['por_cor']) == {'verde'} and not any(r['erro'] for r in resultados)
    assert all(r['exame'] for r in resultados)


def test_laudo_sem_sexo_ou_nascimento_pede_os_dados():
    with pytest.raises(ValueError, match='informe o sexo'):
        op.pedidos_do_laudo(_pdf(FORMATO_A), 'laudo-a')
    with pytest.raises(ValueError, match='informe a idade'):
        op.pedidos_do_laudo(_pdf(FORMATO_B), 'laudo-b', sexo='F')          # o nascimento vem em outra linha
    linhas, soltos = op.pedidos_do_laudo(_pdf(FORMATO_A), 'laudo-a', sexo='F')
    assert {linha['codigo_tuss'] for linha in linhas} == {GLICEMIA, '40302512', '40304361'}
    assert soltos == ['GASOMETRIA VENOSA'] and {linha['regime'] for linha in linhas} == {'ambulatorial'}
    assert {linha['idade'] for linha in linhas} == {'46'}                 # nascida em 01/01/1980, coleta em 23/09/2026
    assert {linha['idade'] for linha in op.pedidos_do_laudo(_pdf(FORMATO_A), 'laudo-a', sexo='F', idade=50)[0]} == {'50'}


@pytest.mark.parametrize('setor, regime', [
    ('HOSPITAL DE TESTE - U.I CLINICA MEDICA', 'internado'), ('UTI ADULTO 2', 'internado'),
    ('Enfermaria B', 'internado'), ('PRONTO SOCORRO ADULTO', 'pronto-socorro'), ('Emergência', 'pronto-socorro'),
    ('AMBULATORIO DE CLINICA MEDICA', None), ('Coleta externa', None), ('', None),
])
def test_regime_pelo_setor_do_laudo(setor, regime):
    assert op.regime_do_setor(setor) == regime


def test_script_le_laudos_em_pdf(tmp_path):
    laudo = tmp_path / 'beneficiario-01.pdf'
    laudo.write_bytes(_pdf(FORMATO_C))
    script = [sys.executable, str(RAIZ / 'scripts' / 'modo_sombra.py')]
    execucao = subprocess.run(script + ['--laudos', str(laudo)], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 0, execucao.stderr
    assert 'beneficiario-01.pdf: 16 exames identificados, regime internado.' in execucao.stdout
    linhas = op.ler_csv((tmp_path / 'laudos_classificado.csv').read_text(encoding='utf-8'))
    assert len(linhas) == 16 and {x['cor'] for x in linhas} == {'fora_do_escopo'}
    assert {x['id_beneficiario'] for x in linhas} == {'beneficiario-01'}
    # Não é PDF: avisa e sai com 2, sem derrubar
    (tmp_path / 'nao_e_laudo.pdf').write_text('texto', encoding='utf-8')
    execucao = subprocess.run(script + ['--laudos', str(tmp_path / 'nao_e_laudo.pdf')], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 2 and 'não lido (O arquivo não é um PDF.)' in execucao.stdout


def test_linha_invalida_nao_e_classificada():
    resultados, resumo = op.classificar_lote([_linha(sexo='X', codigo_tuss='123'), _linha(idade='abc'),
                                              {'id_pedido': 'p9'}, _linha(data_ultimo_exame='2027-01-01'), _linha()])
    assert [bool(r['erro']) for r in resultados] == [True, True, True, True, False]
    assert 'sexo inválido' in resultados[0]['erro'] and 'codigo_tuss inválido' in resultados[0]['erro']
    assert 'falta id_beneficiario' in resultados[2]['erro'] and resultados[0]['cor'] == ''
    assert (resumo['linhas'], resumo['invalidas'], resumo['por_cor']) == (5, 4, {'verde': 1})
    assert 'data_pedido no futuro' in _erro(data_pedido='2099-01-01')
    assert 'AAAA-MM-DD ou DD/MM/AAAA' in _erro(data_pedido='10.11.2026')
    assert 'colunas a mais' in op.classificar_lote([{**_linha(), None: ['50']}])[0][0]['erro']
    assert _um(idade='52.0')['cor'] == 'verde'


@pytest.mark.parametrize('texto, valor', [('18,50', 18.5), ('1.042,00', 1042.0), ('1,042.00', 1042.0), ('30.00', 30.0),
                                           ('R$ 9,9', 9.9), ('120', 120.0)])
def test_valor_aceito(texto, valor):
    linha, erros = op.ler_linha(_linha(valor=texto))
    assert not erros and linha['valor'] == valor


@pytest.mark.parametrize('texto', ['1.234', '1,234', 'nan', '-10', 'dez', '1.2.3'])
def test_valor_ambiguo_ou_invalido_e_erro(texto):
    assert 'valor inválido' in _erro(valor=texto)


def test_resumo_separa_o_que_depende_de_presumir_rastreio():
    _, resumo = op.classificar_lote([
        _linha(finalidade='rastreio', valor='18,50'),
        _linha(id_beneficiario='b2', data_ultimo_exame='2025-11-01', valor='18,50'),
        _linha(codigo_tuss=VITAMINA_D, valor='1.042,00'),
        _linha(codigo_tuss=PSA, idade='60', cid='Z00.0', valor='30.00'),
    ])
    assert resumo['por_cor'] == {'verde': 1, 'vermelho': 1, 'amarelo': 2}
    assert resumo['origem_da_finalidade'] == {'amarelo': {'presumida': 1, 'cid': 1}, 'vermelho': {'presumida': 1}}
    assert resumo['valor_por_cor'] == {'verde': 18.5, 'vermelho': 1042.0, 'amarelo': 48.5}
    assert resumo['mais_barrados'] == [('25-hidroxivitamina D, soro', 1)] and resumo['versao'] == op.VERSAO


def test_mais_barrados_desempata_pelo_nome():
    _, resumo = op.classificar_lote([_linha(codigo_tuss=VHS), _linha(codigo_tuss=FAN), _linha(codigo_tuss=ACIDO_URICO)])
    nomes = [nome for nome, _ in resumo['mais_barrados']]
    assert nomes == sorted(nomes) and len(nomes) == 3


def test_ultimo_exame_vem_do_proprio_arquivo():
    """Sem data_ultimo_exame, vale o pedido anterior do mesmo beneficiário e código."""
    resultados, _ = op.classificar_lote([
        _linha(id_pedido='p1', data_pedido='2026-01-10', cid='E11.9'),
        _linha(id_pedido='p2', data_pedido='2026-03-01', cid='E11.9'),
        _linha(id_pedido='p3', data_pedido='2026-11-10', cid='E11.9'),
        _linha(id_pedido='p4', data_pedido='2026-03-01', cid='E11.9', id_beneficiario='outro'),
        _linha(id_pedido='p5', data_pedido='2026-03-01', cid='E11.9', data_ultimo_exame='2026-02-20'),
    ])
    assert [r['cor'] for r in resultados] == ['verde', 'vermelho', 'verde', 'verde', 'vermelho']
    assert (resultados[1]['ultimo_exame_usado'], resultados[1]['origem_do_ultimo_exame']) == ('2026-01-10', 'arquivo')
    assert 'pedido anterior no arquivo' in resultados[1]['motivo'] and resultados[1]['proxima_data_elegivel'] == '2026-04-10'
    assert (resultados[2]['ultimo_exame_usado'], resultados[2]['origem_do_ultimo_exame']) == ('2026-03-01', 'arquivo')
    assert resultados[0]['ultimo_exame_usado'] == resultados[3]['ultimo_exame_usado'] == ''
    # O informado na coluna vale quando é mais recente que o do arquivo
    assert (resultados[4]['ultimo_exame_usado'], resultados[4]['origem_do_ultimo_exame']) == ('2026-02-20', 'informada')


def test_falha_do_motor_vira_erro_e_nao_liberacao(monkeypatch):
    import src.routes.checkup_intelligent as motor
    op._perfil.cache_clear()
    monkeypatch.setattr(motor, 'recomendar', lambda *_a, **_k: ({'error': 'x'}, 500))
    resultados, resumo = op.classificar_lote([_linha(finalidade='rastreio')])
    assert 'o motor do check-up falhou' in resultados[0]['erro'] and resultados[0]['cor'] == ''
    assert resumo['invalidas'] == 1
    monkeypatch.undo()
    assert _cor(finalidade='rastreio') == ('verde', 'recomendado')        # a falha não ficou guardada


def test_arquivo_csv_com_ponto_e_virgula_e_script(tmp_path):
    entrada = tmp_path / 'pedidos.csv'
    entrada.write_text('﻿id_pedido;id_beneficiario;idade;sexo;data_pedido;codigo_tuss;carater;regime;finalidade;motivo\n'
                       f'p1;b1;52;M;2026-11-10;{HBA1C};eletivo;ambulatorial;rastreio;check-up\n'
                       f'p2;b2;44;F;2026-11-10;{VITAMINA_D};eletivo;ambulatorial;;\n', encoding='utf-8')
    execucao = subprocess.run([sys.executable, str(RAIZ / 'scripts' / 'modo_sombra.py'), str(entrada)],
                              capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 0, execucao.stderr
    assert 'nada foi barrado' in execucao.stdout and 'Barraria: 1 (50,0%)' in execucao.stdout
    linhas = op.ler_csv((tmp_path / 'pedidos_classificado.csv').read_text(encoding='utf-8'))
    assert [(x['id_pedido'], x['cor']) for x in linhas] == [('p1', 'verde'), ('p2', 'vermelho')]
    assert linhas[1]['referencia'] == 'Endocrine Society 2024' and linhas[0]['versao'] == op.VERSAO
    # A coluna da entrada com nome de coluna de saída não é sobrescrita
    assert linhas[0]['motivo_entrada'] == 'check-up' and linhas[0]['motivo'].startswith('Adultos 35-70 anos')
    assert set(op.SAIDA) <= set(linhas[0])


def test_script_recusa_arquivo_inexistente_e_saida_igual_a_entrada(tmp_path):
    script = [sys.executable, str(RAIZ / 'scripts' / 'modo_sombra.py')]
    execucao = subprocess.run(script + [str(tmp_path / 'nao_existe.csv')], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 2 and 'Arquivo não encontrado' in execucao.stdout
    entrada = tmp_path / 'pedidos.csv'
    cabecalho = 'id_pedido,id_beneficiario,idade,sexo,data_pedido,codigo_tuss,carater,regime\n'
    entrada.write_bytes((cabecalho + f'p1,b1,52,M,2026-11-10,{HBA1C},eletivo,Internação\n').encode('cp1252'))
    execucao = subprocess.run(script + [str(entrada), str(entrada)], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 2 and entrada.read_bytes().startswith(b'id_pedido')
    # Arquivo gravado pelo Excel (Windows-1252) é lido
    execucao = subprocess.run(script + [str(entrada)], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 0, execucao.stderr
    assert 'Fora do escopo (urgência, internado ou exame que não é de laboratório): 1' in execucao.stdout
    # Sem linha válida, o script avisa e sai com 1
    entrada.write_text(cabecalho, encoding='utf-8')
    execucao = subprocess.run(script + [str(entrada)], capture_output=True, text=True, cwd=RAIZ)
    assert execucao.returncode == 1 and 'Nenhuma linha válida' in execucao.stdout


def test_linha_com_campo_a_mais_nao_derruba_o_arquivo():
    brutas = op.ler_csv('id_pedido,id_beneficiario,idade,sexo,data_pedido,codigo_tuss,carater,regime,valor\n'
                        f'p1,b1,52,M,2026-11-10,{HBA1C},eletivo,ambulatorial,18,50\n'
                        f'p2,b2,52,M,2026-11-10,{HBA1C},eletivo,ambulatorial,18.50\n')
    resultados, resumo = op.classificar_lote(brutas)
    assert 'colunas a mais' in resultados[0]['erro'] and not resultados[1]['erro']
    assert resumo['valor_por_cor'] == {'verde': 18.5}
    assert op.escrever_csv(brutas, resultados).count('\n') == 3


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


# ── Perfil do paciente (comorbidades e medicações), equivalência do cálcio e exames que não são de rastreio ──

SODIO, CALCIO_TOTAL, LACTATO, CK = '40302423', '40301400', '40301109', '40301648'


def test_com_comorbidade_informada_vale_o_que_o_check_up_recomenda_para_o_paciente():
    assert _um(codigo_tuss=SODIO, finalidade='rastreio')['cor'] == 'amarelo'
    com_has = _um(codigo_tuss=SODIO, finalidade='rastreio', comorbidades='hipertensao')
    assert com_has['cor'] == 'verde' and com_has['motivo'] == 'Adultos com HAS: exame recomendado (grau B).'
    sem_indicacao = _um(codigo_tuss='40302237', finalidade='rastreio', comorbidades='hipertensao|dislipidemia',
                        medicacoes='sinvastatina')                                   # magnésio
    assert sem_indicacao['cor'] == 'amarelo' and 'as comorbidades e as medicações informadas' in sem_indicacao['motivo']


def test_comorbidade_ou_medicacao_fora_da_lista_do_check_up_invalida_a_linha():
    for campos, trecho in ((dict(comorbidades='hipertensao|inventada'), 'comorbidades fora da lista'),
                           (dict(medicacoes='remedio_inventado'), 'medicacoes fora da lista')):
        resultados, _ = op.classificar_lote([_linha(codigo_tuss=SODIO, **campos)])
        assert trecho in resultados[0]['erro']


def test_calcio_total_e_tratado_como_calcio_ionico():
    total = _um(codigo_tuss=CALCIO_TOTAL, finalidade='rastreio', comorbidades='hipertensao')
    ionico = _um(codigo_tuss='40301419', finalidade='rastreio', comorbidades='hipertensao')
    assert total['cor'] == ionico['cor'] == 'verde' and total['motivo'] == ionico['motivo']
    assert total['exame'] == 'Cálcio (tratado como Cálcio iônico, soro)'
    assert _um(codigo_tuss=CALCIO_TOTAL, finalidade='rastreio')['codigo_do_motivo'] == 'sem_recomendacao_para_o_perfil'


def test_exames_registrados_como_fora_de_rastreio_trazem_a_indicacao_e_a_fonte():
    lactato = _um(codigo_tuss=LACTATO, finalidade='rastreio')
    assert lactato['cor'] == 'vermelho' and lactato['codigo_do_motivo'] == 'nao_e_de_rastreio'
    assert 'sepse' in lactato['motivo'] and lactato['link'].startswith('https://doi.org/')
    ck = _um(codigo_tuss=CK, finalidade='rastreio', medicacoes='sinvastatina')
    assert ck['cor'] == 'vermelho' and ck['referencia'] == 'AHA/ACC 2018 (colesterol)'
    assert _um(codigo_tuss=LACTATO, finalidade='diagnostico')['cor'] == 'verde'
    assert _um(codigo_tuss='40302385', finalidade='rastreio')['cor'] == 'amarelo'      # sem fonte própria: não barra
    for item in op.NAO_SAO_DE_RASTREIO.values():
        assert item['motivo'] and (item['link'] is None or item['link'].startswith('https://'))


def test_calcio_total_feito_cobre_o_calcio_ionico_no_check_up():
    from datetime import date
    from src.utils import periodicidade
    rec = [{'titulo': 'Cálcio iônico, soro', 'categoria': 'laboratorio', 'subtitulo': 'Adultos com HAS | Avaliação inicial'}]
    lidos, erros = periodicidade.ler_exames_anteriores([{'exame': 'Cálcio', 'data': '2026-11-16'}], date(2026, 11, 17))
    assert not erros
    mantidas, em_dia = periodicidade.aplicar(rec, lidos, 'M', date(2026, 11, 17))
    assert not mantidas and em_dia[0]['titulo'] == 'Cálcio iônico, soro'


def test_detalhes_das_condicoes_do_check_up_sao_aceitos_no_perfil():
    """Com "osteoporose recém-diagnosticada", o check-up pede fosfatase alcalina; o modo sombra tem de aceitar a chave."""
    validas = op.comorbidades_validas()
    assert 'osteoporose_diagnostico' in validas and validas['les_nefrite'].startswith('Lúpus eritematoso sistêmico: ')
    fosfatase = '40301885'
    assert _um(codigo_tuss=fosfatase, finalidade='rastreio', comorbidades='osteoporose')['cor'] == 'amarelo'
    assert _um(codigo_tuss=fosfatase, finalidade='rastreio', comorbidades='osteoporose|osteoporose_diagnostico')['cor'] == 'verde'
