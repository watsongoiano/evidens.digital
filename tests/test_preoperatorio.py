"""Aba "Pré-operatório" (src/utils/preoperatorio.py e /api/preoperatorio). Dados fictícios."""
import itertools
from datetime import date

import pytest

from src.utils import preoperatorio as po

HOJE = date(2026, 11, 16)
_SEQ_CONTAS = itertools.count(1)


def _p(**extra):
    base = dict(idade=60, sexo='masculino', cirurgia='colectomia', urgencia='eletiva')
    base.update(extra)
    return po.ler(base, hoje=HOJE)


def _exame(r, titulo):
    return next((e for e in r['exames'] if e['titulo'] == titulo), None)


# ── Leitura ──────────────────────────────────────────────────────────────────

def test_campos_obrigatorios_e_valores_impossiveis():
    with pytest.raises(po.EntradaInvalida):
        po.ler({'idade': 60, 'sexo': 'masculino', 'urgencia': 'eletiva'})          # sem cirurgia
    with pytest.raises(po.EntradaInvalida):
        po.ler(dict(idade=60, sexo='masculino', cirurgia='inexistente', urgencia='eletiva'))
    with pytest.raises(po.EntradaInvalida):
        _p(pas=120, pad=130)
    with pytest.raises(po.EntradaInvalida):
        _p(condicoes=['stent'], stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2027-01'})


def test_implicacoes_entre_condicoes():
    p = _p(condicoes=['iam_previo', 'ic_fe_reduzida'], medicacoes=['insulina_glargina'])
    assert {'dac', 'ic', 'diabetes', 'diabetes_insulina'} <= p['condicoes']


# ── Escores ──────────────────────────────────────────────────────────────────

def test_rcri_conta_os_seis_itens_e_classifica_como_sbc_e_aha():
    r = po.rcri(_p(condicoes=['dac', 'ic', 'avc_ait', 'diabetes_insulina'], creatinina=2.4))
    assert r['valor'] == 6 and r['classe'] == 'IV' and r['nivel'] == 'alto' and r['elevado_aha']
    r = po.rcri(_p(cirurgia='catarata'))
    assert r['valor'] == 0 and r['classe'] == 'I' and r['nivel'] == 'baixo' and not r['elevado_aha']
    r = po.rcri(_p(condicoes=['dac']))                       # coronária + intraperitoneal
    assert r['valor'] == 2 and r['nivel'] == 'intermediario' and r['elevado_aha']
    assert po.rcri(_p())['falta'] == ['creatinina']


def test_aub_has2():
    r = po.aub_has2(_p(idade=80, condicoes=['fa'], sintomas=['dispneia'], hemoglobina=11,
                       cirurgia='aorta_aberta', urgencia='emergencia'))
    assert r['valor'] == 6 and r['nivel'] == 'alto'
    # Doença coronária sem IAM nem revascularização não é "história de doença cardíaca" no AUB-HAS2
    assert po.aub_has2(_p(condicoes=['dac']))['valor'] == 0
    assert po.aub_has2(_p(condicoes=['stent'], hemoglobina=11.9))['valor'] == 2


def test_vsg_cri_so_em_cirurgia_vascular_arterial():
    assert po.vsg_cri(_p()) is None
    p = _p(idade=82, cirurgia='aorta_aberta', condicoes=['dac', 'ic', 'dpoc', 'tabagismo', 'diabetes_insulina',
                                                            'revascularizacao_cirurgica'],
           creatinina=2.0, medicacoes=['atenolol'])
    r = po.vsg_cri(p)
    # 4 + 2 + 2 + 2 + 1 + 1 + 2 (creatinina) + 1 (betabloqueador) − 1 = 14
    assert r['valor'] == 14 and r['nivel'] == 'alto'
    assert po.vsg_cri(_p(idade=65, cirurgia='evar'))['nivel'] == 'baixo'


def test_dasi_e_escadas():
    tudo = list(po.DASI_ITENS)
    assert po.capacidade_funcional(_p(dasi=tudo))['dasi'] == 58.2
    cap = po.capacidade_funcional(_p(dasi=['cuidar_de_si', 'andar_em_casa', 'subir_lance'], escadas='sim'))
    assert cap['dasi'] == 10 and cap['estado'] == 'baixa' and 'discordam' in cap['nota']
    assert po.capacidade_funcional(_p())['estado'] == 'desconhecida'
    assert po.capacidade_funcional(_p(escadas='sim'))['estado'] == 'boa'


def test_ariscat_pontos_e_classes():
    p = _p(idade=72, spo2=93, infeccao_respiratoria=True, hemoglobina=9.5, duracao='mais_3h',
           cirurgia='esofagectomia', urgencia='emergencia')
    r = po.ariscat(p)
    assert r['valor'] == 3 + 8 + 17 + 11 + 24 + 23 + 8 and r['nivel'] == 'alto'
    r = po.ariscat(_p(idade=72, spo2=97, hemoglobina=13, duracao='2_3h'))
    assert r['valor'] == 34 and r['nivel'] == 'intermediario'
    assert po.ariscat(_p(idade=40, spo2=99, hemoglobina=14, duracao='menos_2h', cirurgia='mama'))['nivel'] == 'baixo'


def test_stop_bang_e_cockcroft_gault():
    r = po.stop_bang(_p(idade=55, stop_bang=['ronco', 'apneia_observada'], condicoes=['hipertensao']))
    assert r['valor'] == 5 and r['nivel'] == 'alto'      # ronco, apneia, HAS, > 50 anos, homem
    assert po.stop_bang(_p(idade=40, sexo='feminino'))['nivel'] == 'baixo'
    assert po.clcr(_p(idade=72, peso=78, creatinina=1.6)) == 46.0
    assert po.clcr(_p(idade=72, sexo='feminino', peso=78, creatinina=1.6)) == pytest.approx(39.1, abs=0.05)
    assert po.clcr(_p()) is None


# ── Indicação da avaliação cardiológica ─────────────────────────────────────

def test_emergencia_nao_pede_exames():
    r = po.avaliar(_p(urgencia='emergencia', condicoes=['dac']))
    assert r['indicacao']['tipo'] == 'emergencia'
    assert all(e['estado'] == 'nao_indicado' for e in r['exames'])


def test_condicao_instavel_adia():
    r = po.avaliar(_p(instaveis=['sca']))
    assert r['indicacao']['tipo'] == 'adiar' and r['adiar'][0]['titulo'] == 'Síndrome coronariana aguda'


def test_cirurgia_de_baixo_risco_nao_indica_avaliacao_nem_exames_cardiacos():
    r = po.avaliar(_p(cirurgia='catarata', idade=35))
    assert r['indicacao']['tipo'] == 'nao_indicada'
    assert _exame(r, 'Eletrocardiograma de repouso')['estado'] == 'nao_indicado'
    assert _exame(r, 'Troponina, soro')['estado'] == 'nao_indicado'
    assert _exame(r, 'Peptídeo natriurético BNP/PROBNP')['estado'] == 'nao_indicado'


def test_risco_baixo_pelos_escores_libera():
    r = po.avaliar(_p(idade=50, condicoes=['hipertensao'], creatinina=0.9, hemoglobina=14))
    ind = r['indicacao']
    assert ind['tipo'] == 'nao_indicada' and ind['passos'][-1]['resposta'] == 'Baixo'
    assert ind['caminho'] == 'risco_baixo' and ind['liberado'] and ind['passos'][-1]['libera']


def test_fluxo_da_aha_libera_quem_nao_tem_fator_doenca_nem_sintoma():
    """AHA/ACC, Figura 1, primeira pergunta. Fatores: hipertensão, tabagismo, dislipidemia, diabetes, obesidade,
    história familiar de doença coronária precoce, mulher > 65 anos, homem > 55 anos."""
    r = po.avaliar(_p(idade=45, cirurgia='pancreas'))
    ind = r['indicacao']
    assert (ind['tipo'], ind['caminho'], ind['liberado']) == ('nao_indicada', 'sem_fatores', True)
    assert ind['titulo'] == 'Risco cardiológico não indicado para este paciente.'
    assert ind['detalhe'].startswith('Sem fator de risco, doença ou sintoma cardiovascular')
    assert [x['pergunta'] for x in ind['passos']] == ['Cirurgia de emergência?',
                                                      'Fator de risco, doença ou sintoma cardiovascular?']
    assert ind['passos'][-1]['resposta'] == 'Não' and ind['passos'][-1]['libera']
    assert all(x['referencias'] for x in ind['passos'])
    # Cada fator de risco leva o paciente ao passo seguinte
    for extra in (dict(condicoes=['hipertensao']), dict(condicoes=['dislipidemia']), dict(condicoes=['tabagismo']),
                  dict(condicoes=['historia_familiar_dac']), dict(condicoes=['obesidade']), dict(idade=56),
                  dict(idade=66, sexo='feminino'), dict(medicacoes=['atorvastatina']), dict(sintomas=['palpitacoes'])):
        ind = po.avaliar(_p(**dict(dict(idade=45, cirurgia='pancreas', creatinina=0.9, hemoglobina=14), **extra)))['indicacao']
        assert ind['caminho'] != 'sem_fatores', extra
    assert po.avaliar(_p(idade=65, sexo='feminino', cirurgia='pancreas'))['indicacao']['caminho'] == 'sem_fatores'
    assert po.avaliar(_p(idade=55, cirurgia='pancreas'))['indicacao']['caminho'] == 'sem_fatores'
    # Sem fator, mas com escore elevado ou doença renal (item do RCRI): não libera neste passo, e o passo diz por quê
    ind = po.avaliar(_p(idade=40, sexo='feminino', cirurgia='aorta_aberta', creatinina=0.8, hemoglobina=10.5,
                        escadas='nao'))['indicacao']
    assert ind['tipo'] == 'indicada' and 'AUB-HAS2 2' in ind['passos'][1]['texto']
    assert ind['passos'][1]['resposta'] == 'Não' and ind['passos'][1]['estado'] == 'atencao'
    assert po.avaliar(_p(idade=45, condicoes=['doenca_renal'], escadas='nao'))['indicacao']['caminho'] == 'incompleto'


def test_liberado_pelo_fluxo_nao_marca_exame_cardiaco():
    """Risco cardiológico não indicado → nenhum exame cardíaco marcado sozinho; o que só a SBC indica (ou que a AHA
    recomenda fora do fluxo) fica a considerar, com o aviso."""
    casos = (dict(idade=45, cirurgia='hernia'),                                           # sem fatores
             dict(idade=68, sexo='feminino', cirurgia='catarata', condicoes=['diabetes']),  # cirurgia de baixo risco
             dict(idade=66, condicoes=['hipertensao', 'fa'], creatinina=1.0, hemoglobina=14))  # risco calculado baixo
    for caso in casos:
        r = po.avaliar(_p(**caso))
        assert r['indicacao']['liberado'], caso
        cardiacos = [e for e in r['exames'] if e['titulo'] in po.EXAMES_CARDIACOS]
        assert cardiacos and not [e['titulo'] for e in cardiacos if e['estado'] == 'indicado'], caso
        assert po.NOTA_DO_FLUXO in _exame(r, 'Eletrocardiograma de repouso')['divergencia'], caso
    # FA em cirurgia intermediária: ECG 2a na AHA e I na SBC, BNP 2a/I: aparecem, mas a considerar
    ecg, bnp = _exame(r, 'Eletrocardiograma de repouso'), _exame(r, 'Peptídeo natriurético BNP/PROBNP')
    assert (ecg['estado'], ecg['aha'], ecg['sbc']) == ('considerar', '2a', 'I')
    assert (bnp['estado'], bnp['aha'], bnp['sbc']) == ('considerar', '2a', 'I')
    assert po.NOTA_DO_FLUXO in bnp['divergencia']
    # O que não é do risco cardiológico segue a sua própria regra (NICE pelo porte e ASA; HbA1c no diabetes)
    assert _exame(r, 'Hemograma completo com plaquetas')['estado'] == 'indicado'
    r = po.avaliar(_p(idade=68, sexo='feminino', cirurgia='catarata', condicoes=['diabetes']))
    assert _exame(r, 'Hemoglobina glicada (HbA1c), soro')['estado'] == 'indicado'
    # Transplante tem recomendação própria da SBC: fica marcado
    r = po.avaliar(_p(idade=40, cirurgia='transplante_hepatico'))
    assert r['indicacao']['liberado'] and _exame(r, 'Ecocardiograma transtorácico')['estado'] == 'indicado'


def test_risco_elevado_ou_modificador_com_boa_capacidade_nao_diz_nao_indicado():
    """Passou pelo risco elevado ou por um modificador e foi liberado pela capacidade: os exames do ramo ficam e o
    título não diz "não indicado"."""
    r = po.avaliar(_p(idade=70, condicoes=['dac'], creatinina=1.0, hemoglobina=14, escadas='sim'))
    ind = r['indicacao']
    assert (ind['tipo'], ind['caminho'], ind['liberado']) == ('nao_indicada', 'capacidade_boa', False)
    assert ind['titulo'] == 'Boa capacidade funcional: operar sem prova funcional.'
    assert _exame(r, 'Eletrocardiograma de repouso')['estado'] == 'indicado'
    # Modificador (stent), risco calculado baixo: segue para a capacidade funcional
    base = dict(idade=50, cirurgia='quadril', condicoes=['stent'], creatinina=1.0, hemoglobina=14,
                stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2024-01-10'})
    ind = po.avaliar(_p(escadas='sim', **base))['indicacao']
    assert ind['caminho'] == 'capacidade_boa' and 'stent coronário' in ind['conclusao']
    passo = next(x for x in ind['passos'] if x['pergunta'] == 'Risco calculado e modificadores de risco')
    assert passo['resposta'] == 'Modificador' and 'Neste paciente: stent coronário' in passo['texto']
    r = po.avaliar(_p(escadas='nao', **base))
    assert r['indicacao']['tipo'] == 'indicada' and 'stent coronário' in r['indicacao']['conclusao']
    # Prova de isquemia de saída só com risco calculado elevado (AHA 2b; SBC IIa)
    assert not [e for e in r['exames'] if e.get('grupo') == 'isquemia' and e['aha'] == '2b']
    # Fragilidade (CFS ≥ 5) e os demais modificadores
    for extra in (dict(cfs=5), dict(condicoes=['marcapasso_cdi']), dict(condicoes=['valvopatia']),
                  dict(condicoes=['hipertensao_pulmonar']), dict(condicoes=['cardiopatia_congenita']),
                  dict(condicoes=['avc_ait_recente'])):
        ind = po.avaliar(_p(**dict(dict(idade=60, cirurgia='quadril', creatinina=1.0, hemoglobina=14, escadas='sim'),
                                   **extra)))['indicacao']
        assert ind['caminho'] in ('capacidade_boa', 'instavel') or ind['tipo'] == 'adiar', extra
    assert po.avaliar(_p(idade=60, cirurgia='quadril', creatinina=1.0, hemoglobina=14, escadas='sim',
                         cfs=4))['indicacao']['caminho'] == 'risco_baixo'


def test_dado_ausente_nao_vira_risco_baixo():
    """Auditoria PREOP-04: sem creatinina, RCRI 1 pode ser 2; o risco fica incompleto, não baixo."""
    r = po.avaliar(_p(idade=50, condicoes=['hipertensao'], escadas='nao'))
    ind = r['indicacao']
    assert ind['tipo'] == 'incompleto' and ind['titulo'] == 'Faltam dados para decidir o risco cardiológico.'
    passo = next(x for x in ind['passos'] if x['pergunta'] == 'Risco calculado e modificadores de risco')
    assert passo['resposta'] == 'Incompleto' and passo['estado'] == 'atencao'
    assert 'creatinina (com ≥ 2,0 mg/dL, o RCRI passa a 2)' in ind['conclusao']
    assert _exame(r, 'Creatinina, soro')['estado'] == 'indicado'
    assert not any(e.get('grupo') == 'isquemia' and e['estado'] != 'nao_indicado' for e in r['exames'])
    # Com boa capacidade, o dado que falta não muda a conduta: libera
    r = po.avaliar(_p(idade=50, condicoes=['hipertensao'], escadas='sim'))
    assert r['indicacao']['tipo'] == 'nao_indicada' and 'incompleto' in r['indicacao']['conclusao']
    assert r['indicacao']['caminho'] == 'incompleto_capacidade_boa' and r['indicacao']['liberado']
    assert r['indicacao']['titulo'] == 'Risco cardiológico não indicado para este paciente.'
    assert _exame(r, 'Eletrocardiograma de repouso')['estado'] == 'considerar'
    # Sem fator de risco, doença nem sintoma, a creatinina que falta não segura o paciente (AHA, Figura 1)
    assert po.avaliar(_p(idade=50, escadas='nao'))['indicacao']['caminho'] == 'sem_fatores'
    # RCRI 0 sem creatinina não sobe a 2: continua baixo
    assert po.avaliar(_p(idade=50, cirurgia='hernia', escadas='nao'))['indicacao']['tipo'] == 'nao_indicada'
    # Hemoglobina no AUB-HAS2 (idade ≥ 75 já soma 1)
    r = po.avaliar(_p(idade=78, sexo='feminino', cirurgia='quadril', creatinina=0.8))
    assert r['indicacao']['tipo'] == 'incompleto' and 'hemoglobina' in r['indicacao']['conclusao']
    assert r['contexto']['risco_incompleto']


def test_mica_sem_dados_nao_e_risco_baixo():
    m = po.mica(_p(asa=None))
    assert m['risco'] is None and m['nivel'] is None and m['faixa'] == 'Faltam dados'
    r = po.avaliar(_p(idade=50, condicoes=['hipertensao'], creatinina=0.9, hemoglobina=14))
    passo = next(x for x in r['indicacao']['passos'] if x['pergunta'] == 'Risco calculado e modificadores de risco')
    assert 'Gupta MICA não calculado: faltam a classe ASA e o estado funcional.' in passo['texto']


def test_creatinina_de_2_conta_no_rcri_como_na_aha():
    """Auditoria PREOP-03: AHA Tabela 4 "≥ 2,0"; Lee e SBC "> 2,0". Seguimos a AHA, com aviso só na fronteira."""
    r = po.rcri(_p(creatinina=2.0))
    assert 'Creatinina ≥ 2,0 mg/dL' in r['itens'] and r['valor'] == 2 and 'AHA' in r['divergencia']
    r = po.rcri(_p(creatinina=1.99))
    assert r['valor'] == 1 and not r['divergencia']
    assert po.rcri(_p(creatinina=2.3))['divergencia'] == ''


def test_notas_sobre_clcr_e_tfg():
    r = po.avaliar(_p(peso=120, creatinina=1.0, condicoes=['obesidade']))
    textos = [n['texto'] for n in r['notas_renais']]
    assert any(t.startswith('Obesidade: o Cockcroft-Gault com peso real') for t in textos)
    assert any('lesão renal aguda' in t for t in textos)
    r = po.avaliar(_p(peso=70, creatinina=1.0))
    assert [n['texto'] for n in r['notas_renais']] == ['O ClCr e a TFG supõem creatinina estável: na lesão renal aguda, não valem.']
    assert po.avaliar(_p())['notas_renais'] == []


def test_risco_elevado_com_boa_capacidade_libera_sem_prova_funcional():
    r = po.avaliar(_p(condicoes=['dac'], escadas='sim', dasi=list(po.DASI_ITENS)))
    assert r['indicacao']['tipo'] == 'nao_indicada'
    assert not any(e['grupo'] == 'isquemia' for e in r['exames'])


def test_caso_completo_da_previa():
    p = _p(idade=72, peso=78, condicoes=['dac', 'stent', 'diabetes_insulina', 'hipertensao'],
           stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2026-03'}, asa=3, duracao='2_3h',
           spo2=97, escadas='nao', dasi=['cuidar_de_si', 'andar_em_casa', 'andar_quarteiroes', 'subir_lance',
                                         'domestico_leve', 'domestico_moderado', 'relacoes_sexuais'],
           creatinina=1.6, hemoglobina=11.5, hba1c_dias=80)
    r = po.avaliar(p)
    assert r['indicacao']['tipo'] == 'indicada'
    assert [e['valor'] for e in r['escores'][:2]] == [3, 2]
    assert r['clcr'] == 46.0
    assert _exame(r, 'Eletrocardiograma de repouso')['estado'] == 'indicado'
    bnp = _exame(r, 'Peptídeo natriurético BNP/PROBNP')
    assert bnp['aha'] == '2a' and bnp['sbc'] == 'I' and bnp['divergencia']
    assert _exame(r, 'Troponina, soro')['sbc'] == 'I'
    assert _exame(r, 'Cintilografia de perfusão miocárdica (estresse e repouso)')['estado'] == 'considerar'
    assert _exame(r, 'Hemoglobina glicada (HbA1c), soro')['estado'] == 'ja_feito'
    assert _exame(r, 'Ecocardiograma transtorácico')['estado'] == 'nao_indicado'
    stent = r['adiar'][0]
    assert stent.get('ok') and '7 meses' in stent['titulo']       # só o mês: conta do último dia (31/03)
    assert r['pulmonar']['escore']['valor'] == 34
    titulos_pos = [x['titulo'] for x in r['pos_operatorio']]
    assert 'Troponina com 24 e 48 h' in titulos_pos and 'Unidade de terapia intensiva por 48 h' in titulos_pos


def test_prazos_depois_da_angioplastia():
    def adiar(tipo, indicacao, data):
        return po.adiamentos(_p(condicoes=['stent'], stent={'tipo': tipo, 'indicacao': indicacao, 'data': data}))
    assert '30 dias ou menos' in adiar('farmacologico', 'dac_cronica', '2026-11-01')[0]['titulo']
    assert 'menos de 14 dias' in adiar('balao', 'dac_cronica', '2026-11-10')[0]['titulo']
    assert adiar('balao', 'dac_cronica', '2026-10-20')[0].get('ok')
    # Stent convencional por SCA segue o prazo da indicação (SBC), não fica liberado por ser convencional
    assert 'SBC IIb' in adiar('convencional', 'sca', '2026-08-01')[0]['classe']
    # Sem indicação: prazo mais longo (SCA)
    assert 'SBC IIa' in po.adiamentos(_p(condicoes=['stent'], stent={'tipo': 'farmacologico', 'data': '2026-03-01'}))[0]['classe']
    # Urgência: nada é adiado; conduta da SBC
    urg = po.adiamentos(_p(urgencia='urgencia', condicoes=['stent'],
                           stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-10-01'}))
    assert urg[0]['classe'] == 'SBC I-C' and 'hemodinâmica' in urg[0]['texto']
    assert 'SBC IIb' in adiar('farmacologico', 'dac_cronica', '2026-09')[0]['classe']    # 2 meses
    assert 'SBC IIa' in adiar('farmacologico', 'dac_cronica', '2026-07')[0]['classe']    # 4 meses
    assert 'SBC IIa' in adiar('farmacologico', 'sca', '2026-03')[0]['classe']            # 8 meses por SCA
    assert adiar('farmacologico', 'sca', '2025-01')[0].get('ok')
    sem_data = po.adiamentos(_p(condicoes=['stent'], stent={'tipo': 'farmacologico'}))
    assert 'não informada' in sem_data[0]['titulo']


def test_pa_e_avc_recente_adiam_eletiva():
    titulos = [a['titulo'] for a in po.adiamentos(_p(pas=185, pad=100, condicoes=['avc_ait_recente']))]
    assert 'PA 185 × 100 mmHg' in titulos and 'AVC ou AIT há menos de 3 meses' in titulos
    assert not po.adiamentos(_p(pas=185, pad=100, urgencia='urgencia'))


def test_divergencias_ecg_e_eco():
    # Diabético de 45 anos em cirurgia de baixo risco: SBC indica ECG (I), AHA não vê benefício
    r = po.avaliar(_p(idade=45, cirurgia='catarata', condicoes=['diabetes']))
    ecg = _exame(r, 'Eletrocardiograma de repouso')
    assert ecg['sbc'] == 'I' and ecg['aha'].startswith('3') and ecg['estado'] == 'considerar'
    assert 'a SBC indica (diabetes)' in ecg['divergencia'] and po.NOTA_DO_FLUXO in ecg['divergencia']
    # Assintomático antes de cirurgia de alto risco: eco IIb na SBC, sem benefício na AHA
    r = po.avaliar(_p(cirurgia='pancreas', condicoes=['dac']))
    eco = _exame(r, 'Ecocardiograma transtorácico')
    assert eco['estado'] == 'considerar' and eco['sbc'] == 'IIb' and eco['divergencia']
    # IC conhecida, sem eco no último ano, em cirurgia de risco intermediário ou alto: SBC I-B; AHA sem benefício
    eco = _exame(po.avaliar(_p(cirurgia='quadril', condicoes=['ic'])), 'Ecocardiograma transtorácico')
    assert eco['estado'] == 'indicado' and eco['sbc'] == 'I' and eco['aha'].startswith('3')
    assert eco['divergencia'].endswith('Nós optamos por sugerir, sinalizando a diferença.')
    # Dispneia nova: eco classe 1 na AHA
    r = po.avaliar(_p(sintomas=['dispneia_nova']))
    assert _exame(r, 'Ecocardiograma transtorácico')['aha'] == '1'


def test_exames_de_rotina_pelo_nice():
    r = po.avaliar(_p(cirurgia='pele', idade=30, asa=1))
    assert _exame(r, 'Radiografia de tórax')['estado'] == 'nao_indicado'
    assert _exame(r, 'Coagulograma (TP/INR e TTPa)')['estado'] == 'nao_indicado'
    r = po.avaliar(_p(asa=3, medicacoes=['varfarina']))
    assert _exame(r, 'Hemograma completo com plaquetas')['estado'] == 'indicado'
    assert _exame(r, 'Creatinina, soro')['estado'] == 'indicado'
    assert _exame(r, 'Tempo de protrombina (TP/INR), plasma')['estado'] == 'indicado'


def test_exames_anteriores_alimentam_o_motor():
    from src.utils import periodicidade
    anteriores, erros = periodicidade.ler_exames_anteriores([
        {'exame': 'Creatinina, soro', 'data': '2026-10-15', 'resultados': {'creatinina': '2,3'}},
        {'exame': 'Hemograma completo com plaquetas', 'data': '2026-10-15', 'resultados': {'hemoglobina': '10,5'}},
        {'exame': 'Eletrocardiograma de repouso', 'data': '2026-08-01'},
    ], hoje_=HOJE)
    assert not erros
    p = _p(condicoes=['dac'])
    po.aplicar_exames_anteriores(p, anteriores, hoje=HOJE)
    assert p['creatinina'] == 2.3 and p['hemoglobina'] == 10.5
    r = po.avaliar(p)
    assert 'Creatinina ≥ 2,0 mg/dL' in r['escores'][0]['itens']
    ecg = _exame(r, 'Eletrocardiograma de repouso')
    # RCRI 3 em cirurgia intraperitoneal: ECG de base para o 1º e 2º dia (SBC Quadro 30), mesmo com um recente
    assert ecg['estado'] == 'indicado' and 'linha de base' in ecg['motivo']
    assert ecg['ultimo'].startswith('Último em 01/08/2026')
    p = _p(idade=50, cirurgia='hernia', condicoes=['hipertensao'])
    po.aplicar_exames_anteriores(p, anteriores, hoje=HOJE)
    assert _exame(po.avaliar(p), 'Eletrocardiograma de repouso')['estado'] == 'ja_feito'


def test_toda_saida_tem_referencia_com_link():
    r = po.avaliar(_p(idade=72, condicoes=['dac', 'stent', 'diabetes_insulina', 'tabagismo'],
                      stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-07'}, pas=190, pad=95))
    blocos = (r['adiar'] + r['escores'] + r['exames'] + r['orientacoes'] + r['pos_operatorio']
              + [r['indicacao'], r['pulmonar']['escore'], r['pulmonar']['stop_bang']] + r['pulmonar']['medidas'])
    for bloco in blocos:
        assert bloco['referencias'] and all(ref['url'].startswith('https://') for ref in bloco['referencias']), bloco


# ── Tela e rota ──────────────────────────────────────────────────────────────

def test_tela_tem_as_opcoes_do_motor():
    html = open('intelligent-tools.html', encoding='utf-8').read()
    for chave in po.CIRURGIAS:
        assert f'<option value="{chave}"' in html
    for chave in list(po.CONDICOES) + list(po.INSTAVEIS) + list(po.SINTOMAS) + list(po.DASI_ITENS) + list(po.STOP_BANG_ITENS):
        assert f'value="{chave}"' in html, chave
    assert 'data-aba="preop"' in html and "fetch('/api/preoperatorio'" in html
    # A frase introdutória do pré-operatório foi retirada a pedido.
    assert 'Risco cardiovascular e pulmonar para cirurgia não cardíaca' not in html


def _conta_preop(app, contas):
    """Cliente logado numa conta nova e aprovada (e-mails próprios deste arquivo)."""
    from conftest import SENHA_DE_TESTE, aceitar_termos
    n = next(_SEQ_CONTAS)
    u = contas.criar(f'preop{n}@exemplo.test', f'Dra. Preop {n}', f'CRM-GO 7654{n}', 'medico', SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def test_rota_do_preoperatorio(app, contas):
    cliente, _ = _conta_preop(app, contas)
    corpo = dict(idade=72, sexo='masculino', peso=78, cirurgia='colectomia', urgencia='eletiva',
                 condicoes=['dac'], medicacoes=['aas_acido_acetilsalicilico', 'losartana'],
                 exames_anteriores=[{'exame': 'Creatinina, soro', 'data': '2026-10-01', 'resultados': {'creatinina': '1,6'}}])
    r = cliente.post('/api/preoperatorio', json=corpo)
    assert r.status_code == 200, r.get_json()
    dados = r.get_json()
    assert dados['clcr'] and dados['indicacao']['referencia_html'].startswith('<a href="https://')
    assert 'itens' in dados['medicamentos']
    assert cliente.post('/api/preoperatorio', json=dict(corpo, cirurgia='')).status_code == 400
    assert app.test_client().post('/api/preoperatorio', json=corpo).status_code == 401


def test_dose_da_enoxaparina_e_lida_e_validada():
    """Campo "Dose da enoxaparina": plena, profilática ou vazio (não informada); outro valor é recusado."""
    assert po.DOSES_HEPARINA == {'plena': 'Plena (terapêutica)', 'profilatica': 'Profilática'}
    assert _p()['dose_heparina'] == '' and _p(dose_heparina=None)['dose_heparina'] == ''
    assert _p(dose_heparina='')['dose_heparina'] == ''
    for dose in po.DOSES_HEPARINA:
        assert _p(dose_heparina=dose)['dose_heparina'] == dose
    for errado in ('x', 'PLENA', 'terapeutica', 1, True, ['plena'], {'plena': 1}):
        with pytest.raises(po.EntradaInvalida) as erro:
            _p(dose_heparina=errado)
        assert erro.value.mensagem == 'Opção inválida em a dose da enoxaparina.'


def test_rota_leva_a_dose_da_enoxaparina_ate_a_conduta(app, contas):
    cliente, _ = _conta_preop(app, contas)
    corpo = dict(idade=64, sexo='feminino', peso=70, cirurgia='colectomia', urgencia='eletiva', sangramento='alto',
                 condicoes=['tev'], medicacoes=['enoxaparina', 'apixabana'], creatinina=0.9)

    def itens(**extra):
        r = cliente.post('/api/preoperatorio', json=dict(corpo, **extra))
        assert r.status_code == 200, r.get_json()
        return {i['chave']: i for i in r.get_json()['medicamentos']['itens']}

    sem = itens()
    assert sem == itens(dose_heparina='') == itens(dose_heparina=None)
    assert sem['enoxaparina']['resumo'] == 'Dose plena: última dose 24 h antes'
    assert sem['enoxaparina']['texto'].startswith('Informe se a dose é plena ou profilática.')
    plena = itens(dose_heparina='plena')['enoxaparina']
    assert plena['resumo'] == 'Dose plena: última dose na manhã da véspera, com metade da dose diária'
    assert plena['divergencia'].endswith('Nós optamos por seguir a ACCP 2022.')
    assert '<a href="https://doi.org/10.1056/EVIDra2200322"' in plena['referencia_html']
    profilatica = itens(dose_heparina='profilatica')
    assert profilatica['enoxaparina']['conduta'] == 'individualizar'
    assert profilatica['enoxaparina']['resumo'] == 'Dose profilática: horário da última dose combinado com a equipe'
    assert '<a href="https://doi.org/10.1056/EVIDra2200322"' in profilatica['enoxaparina']['referencia_html']
    # o DOAC do mesmo pedido leva a frase da dose, e a dose da enoxaparina não mexe nele
    assert sem['apixabana']['texto'].endswith('ele depende do fármaco, do ClCr e do risco de sangramento.')
    assert profilatica['apixabana'] == sem['apixabana']
    # valor fora da lista: erro de validação, como nos campos vizinhos
    r = cliente.post('/api/preoperatorio', json=dict(corpo, dose_heparina='dobrada'))
    assert r.status_code == 400
    assert r.get_json()['erros'] == [{'campo': '', 'mensagem': 'Opção inválida em a dose da enoxaparina.'}]


def test_tela_pergunta_a_dose_da_enoxaparina_so_com_a_enoxaparina_marcada():
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / 'intelligent-tools.html').read_text(encoding='utf-8')
    # O campo nasce escondido, ao lado da anestesia neuroaxial, com as três opções do motor
    campo = re.search(r'<div class="campo" id="po_dose_heparina_campo" hidden>(.*?)</div>', html, re.S)
    assert campo, 'campo "Dose da enoxaparina" ausente ou visível desde o início'
    assert '<label for="po_dose_heparina">Dose da enoxaparina</label>' in campo.group(1)
    assert '<select id="po_dose_heparina">' in campo.group(1)
    opcoes = re.findall(r'<option value="([^"]*)">([^<]+)</option>', campo.group(1))
    assert opcoes == [('', 'Não informada')] + list(po.DOSES_HEPARINA.items())
    cirurgia = html[html.index('id="s-cirurgia"'):html.index('id="s-condicoes"')]
    assert cirurgia.index('id="po_neuroaxial"') < cirurgia.index('id="po_dose_heparina_campo"')
    # Aparece só com a enoxaparina entre as medicações em uso (a lista de medicações tem a enoxaparina)
    assert 'data-valor="enoxaparina"' in html
    assert "const meds = [...checkupForm.querySelectorAll('input[name=\"medicacoes\"]:checked')].map(i => i.value);" in html
    assert "document.getElementById('po_dose_heparina_campo').hidden = !meds.includes('enoxaparina');" in html
    # Vai no pedido como dose_heparina; escondido, vai vazio
    assert ("dose_heparina: document.getElementById('po_dose_heparina_campo').hidden ? '' : v('po_dose_heparina'),"
            in html)
    envio = html[html.index('function lerPreop()'):html.index('async function avaliarPreop()')]
    assert 'dose_heparina:' in envio and "neuroaxial: v('po_neuroaxial') === 'sim'" in envio
    # Sem estilo próprio: só as classes dos campos vizinhos
    assert '<style' not in html


def test_jovem_sem_comorbidade_em_cirurgia_de_baixo_risco_recebe_orientacao_curta():
    r = po.avaliar(_p(idade=28, sexo='feminino', cirurgia='pele'))
    assert r['resumido'] and r['resumo']['titulo'] == 'Risco cardiológico não indicado para este paciente.'
    assert 'cirurgia de baixo risco' in r['resumo']['texto'] and r['resumo']['referencias']
    assert not any(e['estado'] == 'indicado' for e in r['exames'])
    # Com doença cardiovascular ou sintomas, mesmo em cirurgia de baixo risco, o resultado completo continua.
    assert not po.avaliar(_p(idade=28, cirurgia='pele', condicoes=['fa']))['resumido']
    assert not po.avaliar(_p(idade=28, cirurgia='pele', sintomas=['sincope']))['resumido']
    # Risco elevado pelo escore com boa capacidade não é o resumo curto.
    assert not po.avaliar(_p(condicoes=['dac'], escadas='sim'))['resumido']


# ── SBD/SBA/ABESO 2026: rastreio de diabetes, HbA1c e UTI pela SBC ──────────────────────────────────────────────
SBD_URL = 'https://doi.org/10.1186/s13098-025-02060-5'


def test_rastreio_de_diabetes_em_quem_tem_35_anos_ou_mais():
    # Liberado pelo fluxo: o rastreio é oportunístico, aparece a considerar (não é marcado sozinho)
    r = po.avaliar(_p(idade=40, cirurgia='hernia'))
    a1c, gli = _exame(r, 'Hemoglobina glicada (HbA1c), soro'), _exame(r, 'Glicose, soro')
    assert a1c['estado'] == gli['estado'] == 'considerar' and 'rastreio oportunístico' in a1c['divergencia']
    r = po.avaliar(_p(idade=70, condicoes=['dac'], creatinina=1.0, hemoglobina=14, escadas='sim'))
    a1c, gli = _exame(r, 'Hemoglobina glicada (HbA1c), soro'), _exame(r, 'Glicose, soro')
    assert a1c['estado'] == gli['estado'] == 'indicado' and a1c['outra'] == 'SBD I-B'
    assert 'NICE' in a1c['divergencia'] and SBD_URL in {x['url'] for x in a1c['referencias']}
    jovem = po.avaliar(_p(idade=28, cirurgia='hernia'))
    assert _exame(jovem, 'Glicose, soro') is None
    assert _exame(po.avaliar(_p(idade=28, cirurgia='hernia', condicoes=['hipertensao'])), 'Glicose, soro')
    assert _exame(po.avaliar(_p(idade=40, cirurgia='hernia', urgencia='urgencia')), 'Glicose, soro') is None


def test_hba1c_acima_de_8_no_diabetico_pede_endocrinologista_e_pode_adiar():
    p = _p(condicoes=['diabetes'])
    po.aplicar_exames_anteriores(p, [{'exame': 'Hemoglobina glicada (HbA1c), soro', 'data': date(2026, 10, 1),
                                      'resultados': [{'campo': 'hba1c', 'valor': '9,2'}]}], hoje=HOJE)
    r = po.avaliar(p)
    adiar = [a for a in r['adiar'] if a['titulo'].startswith('HbA1c')]
    assert adiar and adiar[0]['titulo'] == 'HbA1c 9,2% (acima de 8%)' and 'endocrinologista' in adiar[0]['texto']
    assert _exame(r, 'Hemoglobina glicada (HbA1c), soro')['estado'] == 'ja_feito'
    assert '9,2%' in _exame(r, 'Hemoglobina glicada (HbA1c), soro')['motivo']


def test_uti_pela_sbc_com_nivel_e_aviso_da_aha():
    r = po.avaliar(_p(idade=75, condicoes=['dac', 'ic', 'diabetes_insulina'], creatinina=2.3, asa=3))
    uti = next(x for x in r['pos_operatorio'] if x['titulo'].startswith('Unidade de terapia intensiva'))
    assert uti['classe'] == 'SBC I-C' and 'AHA/ACC 2026 não recomenda UTI' in uti['divergencia']
    r = po.avaliar(_p(condicoes=['dac']))                    # RCRI 2: risco intermediário
    uti = next(x for x in r['pos_operatorio'] if x['titulo'].startswith('Unidade de terapia intensiva'))
    assert uti['classe'] == 'SBC IIa-C'


# ── Conclusão com título, orientações perioperatórias e anemia ─────────────────────────────────────────────────
def test_titulo_da_conclusao_do_risco_cardiologico():
    assert po.avaliar(_p(cirurgia='hernia'))['indicacao']['titulo'] == 'Risco cardiológico não indicado para este paciente.'
    r = po.avaliar(_p(idade=72, condicoes=['dac', 'ic'], escadas='nao'))
    assert r['indicacao']['tipo'] == 'indicada' and r['indicacao']['titulo'] == 'Risco cardiológico indicado para este paciente.'
    r = po.avaliar(_p(idade=72, condicoes=['dac', 'ic'], escadas='sim', sintomas=['angina']))
    assert r['indicacao']['tipo'] == 'nao_indicada' and 'fora do contexto cirúrgico' in r['indicacao']['nota']


def test_orientacoes_perioperatorias_so_para_quem_esta_na_situacao():
    titulos = lambda r: {o['titulo'] for o in r['orientacoes']}
    colectomia = po.avaliar(_p(idade=60, cirurgia='colectomia', sangramento='alto', hemoglobina=10.2))
    t = titulos(colectomia)
    assert {'Jejum antes da anestesia', 'Higiene oral com antisséptico', 'Anemia (hemoglobina 10,2 g/dL)',
            'Ácido tranexâmico se houver perda sanguínea esperada', 'Mascar chiclete depois da cirurgia abdominal'} <= t
    goma = next(o for o in colectomia['orientacoes'] if o['titulo'].startswith('Mascar chiclete'))
    assert 'íleo paralítico' in goma['texto'] and goma['referencias'][0]['url'].endswith('CD006506.pub3')
    assert {'Ferritina, soro', 'Índice de saturação de transferrina, soro'} <= {e['titulo'] for e in colectomia['exames']}
    catarata = titulos(po.avaliar(_p(idade=40, cirurgia='catarata', hemoglobina=13.5)))
    assert 'Mascar chiclete depois da cirurgia abdominal' not in catarata and 'Higiene oral com antisséptico' not in catarata
    assert not any(t.startswith('Anemia') for t in catarata)
    assert 'Jejum antes da anestesia' not in titulos(po.avaliar(_p(cirurgia='colectomia', urgencia='emergencia')))


def test_tfg_pela_ckd_epi_ao_lado_do_clcr():
    r = po.avaliar(_p(idade=80, sexo='feminino', peso=45, creatinina=1.2))
    assert r['tfg'] is not None and r['clcr'] is not None and r['tfg'] != r['clcr']
    assert po.avaliar(_p())['tfg'] is None


def test_fa_com_fc_acima_de_120_entra_como_condicao_grave():
    p = _p(condicoes=['fa'], fc=132)
    assert 'fa_alta_resposta' in p['instaveis']
    assert po.avaliar(p)['indicacao']['tipo'] == 'adiar'
    assert 'fa_alta_resposta' not in _p(condicoes=['fa'], fc=120)['instaveis']
    assert 'fa_alta_resposta' not in _p(fc=140)['instaveis']          # taquicardia sem FA não é este item


def test_tela_gerada_das_tabelas_do_motor():
    """As condições (grupos e sub-itens) e as sugestões automáticas saem de scripts/gerar_preop.py."""
    import importlib.util
    import re
    spec = importlib.util.spec_from_file_location('gerar_preop', 'scripts/gerar_preop.py')
    gerador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gerador)
    html = open('intelligent-tools.html', encoding='utf-8').read()
    assert gerador.aplicar(html) == html, 'rode: python scripts/gerar_preop.py'
    # Classe ASA mínima de cada item (ASA 2020), nos atributos que a tela lê
    na_tela = {m[0]: int(m[1]) for m in re.findall(r'name="po_(?:condicoes|instaveis)" value="([a-z_0-9]+)" data-asa="(\d)"', html)}
    assert na_tela == po.ASA_MINIMA
    # Quadro grave como sub-item da própria doença: o motor implica o mesmo antecedente
    for bloco, dentro in re.findall(r'data-detalhe-de="po_c_([a-z_]+)" hidden>(.*?)</span>', html):
        for instavel in re.findall(r'name="po_instaveis" value="([a-z_]+)"', dentro):
            assert po.INSTAVEL_IMPLICA[instavel] == bloco, instavel
    # SpO₂ e frequência cardíaca ficam nos dados clínicos; o histórico do colo é só do check-up
    clinicos = html[html.index('id="s-clinicos"'):html.index('id="s-cirurgia"')]
    assert 'id="po_spo2"' in clinicos and 'id="po_fc"' in clinicos
    assert '<div data-modo="checkup">\n      <div class="grade mt-4" id="colo-historico"' in html


def test_sugestoes_da_tela_tem_fonte_e_chaves_validas():
    s = po.sugestoes_da_tela()
    # Toda cirurgia tem risco de sangramento vinculado; a duração, só onde há série publicada e o ARISCAT se aplica
    assert set(s['sangramento']) == set(po.CIRURGIAS)
    assert set(s['duracao']) <= set(po.CIRURGIAS) - set(s['sem_duracao'])
    assert set(s['sem_duracao']) == {k for k, c in po.CIRURGIAS.items() if not c['ariscat']}
    ordem = list(po.SANGRAMENTOS)
    assert all(ordem.index(d['piso']) <= ordem.index(d['classe']) for d in s['sangramento'].values())
    assert all(d['faixa'] in po.DURACOES and d['url'].startswith('https://') for d in s['duracao'].values())
    assert all(d['classe'] in po.SANGRAMENTOS and d['url'].startswith('https://') for d in s['sangramento'].values())
    # Onde a SBC diverge de si mesma (prótese de quadril ou joelho), a sugestão avisa
    assert s['sangramento']['quadril']['classe'] == 'alto' and s['sangramento']['quadril']['nota'].startswith('Divergência:')
    # Mínimo só onde a AHA nomeia (catarata e odontologia)
    assert {k for k, d in s['sangramento'].items() if d['classe'] == 'minimo'} == {'catarata', 'odontologica'}
    assert set(s['aas_secundaria']) <= set(po.CONDICOES) and 'dac' in s['aas_secundaria']
    assert set(s['implica'].values()) <= set(po.CONDICOES) and set(s['implica']) <= set(po.INSTAVEIS)
    # Tudo o que a tela mostra dessas sugestões tem par em inglês
    from src.utils import i18n
    textos = ([d['texto'] for d in s['duracao'].values()] + [d['fonte'] for d in s['duracao'].values()]
              + [d['nota'] for d in s['duracao'].values() if d['nota']]
              + [d['fonte'] for d in s['sangramento'].values()] + [d['nota'] for d in s['sangramento'].values() if d['nota']])
    assert not [t for t in textos if not i18n.coberto(t)]


def test_risco_de_sangramento_nao_fica_abaixo_do_da_cirurgia():
    """Esplenectomia é cirurgia abdominal (alto na Tabela 12 da SBC): mínimo ou baixo não são aceitos; o motor sobe."""
    assert po.SANGRAMENTO_TIPICO['esplenectomia'][:2] == ('alto', 'alto')
    assert po.SANGRAMENTO_TIPICO['colecistectomia'][:2] == ('baixo_moderado', 'baixo_moderado')
    assert po.SANGRAMENTO_TIPICO['hernia_hiatal'][:2] == ('alto', 'alto')
    assert _p(cirurgia='esplenectomia', sangramento='minimo')['sangramento'] == 'alto'
    assert _p(cirurgia='esplenectomia', sangramento='baixo_moderado')['sangramento'] == 'alto'
    assert _p(cirurgia='colecistectomia', sangramento='minimo')['sangramento'] == 'baixo_moderado'
    # Acima do piso o médico escolhe; sem resposta continua sem resposta (a tela é que preenche)
    assert _p(cirurgia='colecistectomia', sangramento='alto')['sangramento'] == 'alto'
    assert _p(cirurgia='esplenectomia')['sangramento'] is None
    # Linha com procedimentos de riscos diferentes: marca o maior, aceita o menor que a diretriz nomeia
    assert po.SANGRAMENTO_TIPICO['mama'][:2] == ('alto', 'baixo_moderado')
    assert _p(cirurgia='mama', sangramento='baixo_moderado')['sangramento'] == 'baixo_moderado'
    assert _p(cirurgia='mama', sangramento='minimo')['sangramento'] == 'baixo_moderado'
    assert _p(cirurgia='catarata', sangramento='minimo')['sangramento'] == 'minimo'


def test_linha_intraperitoneal_em_tres_cirurgias_com_o_mesmo_risco_cardiaco():
    tres = [po.CIRURGIAS[k] for k in ('colecistectomia', 'hernia_hiatal', 'esplenectomia')]
    assert all((c['risco'], c['rcri'], c['incisao'], c['porte']) == ('intermediario', True, 'abdome_superior', 'maior')
               for c in tres)
    # Gupta 2011: vesícula e baço em GBAAS; hérnia hiatal (esôfago/estômago) em foregut
    assert [c['mica'] for c in tres] == ['gbaas', 'foregut_hpb', 'gbaas']
    assert {po.DURACAO_TIPICA[k][0] for k in ('hernia_hiatal', 'esplenectomia')} == {'2_3h'}
    assert po.DURACAO_TIPICA['colecistectomia'][0] == 'menos_2h'


def test_duracao_tipica_de_mama_tireoide_e_artroscopia():
    """Só entra duração onde há série publicada com o tempo operatório (pedido de 18/11/2026). Mama: Towfighi 2022,
    NSQIP, 15.167 mastectomias, 114,9 min. Tireoide: Goldfarb 2011, NSQIP, 10.838 pacientes, 121,8 min (no limite
    das 2 h: a tela avisa). Ortopédica menor: Gowd 2019, NSQIP, 78.864 artroscopias de joelho, 31,2 min."""
    esperado = {'mama': ('menos_2h', '115 min', '10.1007/s10549-022-06628-x'),
                'tireoide': ('2_3h', '122 min', '10.1245/s10434-011-1938-2'),
                'ortopedica_menor': ('menos_2h', '31 min', '10.1016/j.arthro.2019.01.059')}
    tela = po.sugestoes_da_tela()['duracao']
    for chave, (faixa, minutos, doi) in esperado.items():
        assert po.DURACAO_TIPICA[chave][0] == faixa and minutos in po.DURACAO_TIPICA[chave][1], chave
        assert tela[chave]['faixa'] == faixa and tela[chave]['url'] == 'https://doi.org/' + doi, chave
        assert po.CIRURGIAS[chave]['ariscat']          # a duração só entra no ARISCAT
    assert 'limite das 2 h' in tela['tireoide']['nota'] and tela['mama']['nota'] == ''
    # Linhas que seguem sem duração automática: não achamos série publicada que represente a linha inteira
    for chave in ('ginecologica_menor', 'plastica', 'vats_menor', 'angioplastia_periferica', 'cabeca_pescoco',
                  'neurocirurgia', 'stent_carotida_sintomatica', 'pneumectomia', 'perfuracao_intestinal'):
        assert chave in po.CIRURGIAS and chave not in po.DURACAO_TIPICA, chave
    # Nessas linhas a tela diz por que o campo ficou em branco
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert 'Sem sugestão automática: o Evidēns ainda não tem uma série publicada do tempo operatório que represente esta linha.' in html
    assert 'else if (cirurgia && !semDuracao) {' in html


def test_condicao_grave_implica_o_antecedente():
    """SCA e angina CCS III/IV são dor isquêmica atual (doença coronária em Lee 1999); IC descompensada é IC."""
    assert _p(instaveis=['sca'])['condicoes'] >= {'dac'}
    assert _p(instaveis=['ic_descompensada'])['condicoes'] >= {'ic'}
    assert _p(condicoes=['fa'], fc=130)['condicoes'] >= {'fa'}
    r = po.rcri(_p(instaveis=['angina_grave', 'edema_choque'], urgencia='urgencia', creatinina=1.0))
    assert {'Doença coronária', 'Insuficiência cardíaca'} <= set(r['itens'])


def test_peso_e_altura_dizem_a_obesidade_e_o_item_do_stop_bang():
    p = _p(peso=118, altura=165)                       # IMC 43
    assert 'obesidade' in p['condicoes'] and 'imc_35' in p['stop_bang']
    p = _p(peso=90, altura=170)                        # IMC 31
    assert 'obesidade' in p['condicoes'] and 'imc_35' not in p['stop_bang']
    p = _p(peso=70, altura=170)
    assert 'obesidade' not in p['condicoes']
    assert 'obesidade' not in _p(peso=118)['condicoes']   # sem altura não há IMC
