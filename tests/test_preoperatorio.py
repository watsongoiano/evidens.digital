"""Aba "Pré-operatório" (src/utils/preoperatorio.py e /api/preoperatorio). Dados fictícios."""
from datetime import date

import pytest

from src.utils import preoperatorio as po

HOJE = date(2026, 11, 16)


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
    r = po.avaliar(_p(idade=50, condicoes=[]))
    assert r['indicacao']['tipo'] == 'nao_indicada' and r['indicacao']['passos'][-1]['resposta'] == 'Baixo'


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
    assert stent.get('ok') and '8 meses' in stent['titulo']
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
    assert ecg['sbc'] == 'I' and ecg['aha'].startswith('3') and ecg['estado'] == 'indicado' and ecg['divergencia']
    # Assintomático antes de cirurgia de alto risco: eco IIb na SBC, sem benefício na AHA
    r = po.avaliar(_p(cirurgia='pancreas', condicoes=['dac']))
    eco = _exame(r, 'Ecocardiograma transtorácico')
    assert eco['estado'] == 'considerar' and eco['sbc'] == 'IIb' and eco['divergencia']
    # IC conhecida, sem eco no último ano, em cirurgia de risco intermediário ou alto: SBC I-B; AHA sem benefício
    eco = _exame(po.avaliar(_p(cirurgia='quadril', condicoes=['ic'])), 'Ecocardiograma transtorácico')
    assert eco['estado'] == 'indicado' and eco['sbc'] == 'I' and eco['aha'].startswith('3') and eco['divergencia']
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
    assert 'Creatinina > 2,0 mg/dL' in r['escores'][0]['itens']
    ecg = _exame(r, 'Eletrocardiograma de repouso')
    assert ecg['estado'] == 'ja_feito' and ecg['ultimo'].startswith('Último em 01/08/2026')


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
        assert f'<option value="{chave}">' in html
    for chave in list(po.CONDICOES) + list(po.INSTAVEIS) + list(po.SINTOMAS) + list(po.DASI_ITENS) + list(po.STOP_BANG_ITENS):
        assert f'value="{chave}"' in html, chave
    assert 'data-aba="preop"' in html and "fetch('/api/preoperatorio'" in html
    # A frase introdutória do pré-operatório foi retirada a pedido.
    assert 'Risco cardiovascular e pulmonar para cirurgia não cardíaca' not in html


def test_rota_do_preoperatorio(app, contas):
    from tests.test_apac import _conta
    cliente, _ = _conta(app, contas)
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


def test_jovem_sem_comorbidade_em_cirurgia_de_baixo_risco_recebe_orientacao_curta():
    r = po.avaliar(_p(idade=28, sexo='feminino', cirurgia='pele'))
    assert r['resumido'] and r['resumo']['titulo'] == 'Avaliação cardiológica não indicada'
    assert 'cirurgia de baixo risco' in r['resumo']['texto'] and r['resumo']['referencias']
    assert not any(e['estado'] == 'indicado' for e in r['exames'])
    # Com doença cardiovascular ou sintomas, mesmo em cirurgia de baixo risco, o resultado completo continua.
    assert not po.avaliar(_p(idade=28, cirurgia='pele', condicoes=['fa']))['resumido']
    assert not po.avaliar(_p(idade=28, cirurgia='pele', sintomas=['sincope']))['resumido']
    # Risco elevado pelo escore com boa capacidade não é o resumo curto.
    assert not po.avaliar(_p(condicoes=['dac'], escadas='sim'))['resumido']
