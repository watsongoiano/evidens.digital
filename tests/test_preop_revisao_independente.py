"""Revisão independente do pré-operatório (18/11/2026): cinco achados de segurança clínica, cada um com o teste que
reproduz a falha e guarda a correção. Pacientes fictícios.

1. TEV sem data não é TEV há mais de 12 meses: sem o tempo, o risco tromboembólico não é classificado.
2. ARISCAT sem SpO₂, hemoglobina ou duração sai como incompleto, sem categoria de risco.
3. TFG e ClCr comparados com os limiares sem arredondar (o arredondamento é só para exibir).
4. Classe ASA (e CFS) só aceitam inteiros.
5. TEV há menos de 3 meses em cirurgia eletiva: aviso para considerar o adiamento (AHA/ACC, texto do §7.6).
"""
import itertools
import re
from datetime import date
from pathlib import Path

import pytest

from src.utils import funcao_renal, i18n, preoperatorio as po, preop_medicamentos as pm, prevent

RAIZ = Path(__file__).resolve().parents[1]
HOJE = date(2026, 11, 18)
_SEQ = itertools.count(1)
AVISO_PONTE = 'Varfarina: risco tromboembólico e ponte'
FALTA_TEMPO_TEV = 'há quanto tempo foi o TEV'


def _p(**extra):
    base = dict(idade=60, sexo='masculino', cirurgia='colectomia', urgencia='eletiva')
    base.update(extra)
    return po.ler(base, hoje=HOJE)


def _varfarina(**ctx):
    ctx.setdefault('sangramento', 'baixo_moderado')
    ctx.setdefault('urgencia', 'eletiva')
    r = pm.condutas(['varfarina'], ctx)
    aviso = next(a for a in r['avisos'] if a['titulo'] == AVISO_PONTE)
    return r['itens'][0], aviso


def _cliente(app, contas):
    """Navegador de uma conta nova e aprovada (e-mail próprio deste arquivo)."""
    from conftest import SENHA_DE_TESTE, aceitar_termos
    n = next(_SEQ)
    u = contas.criar(f'revisao{n}@exemplo.test', f'Dra. Revisão {n}', f'CRM-GO 8123{n}', 'medico', SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente


def _preop(cliente, **dados):
    corpo = dict(idade=60, sexo='masculino', cirurgia='colectomia', urgencia='eletiva')
    corpo.update(dados)
    r = cliente.post('/api/preoperatorio', json=corpo)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _med(resposta, chave):
    return next(i for i in resposta['medicamentos']['itens'] if i['chave'] == chave)


# ── 1. TEV sem data ──────────────────────────────────────────────────────────────────────────────────────────────

def test_tev_sem_data_nao_classifica_o_risco_nem_dispensa_a_ponte():
    """Antes: 'tev' sem o tempo era lido como TEV há > 12 meses (baixo risco, "sem ponte"). Uma trombose de 3 semanas
    com o tempo em branco saía como baixo risco."""
    item, aviso = _varfarina(idade=60, sexo='masculino', condicoes={'tev'})
    assert item['conduta'] == 'individualizar'
    assert 'sem ponte' not in item['resumo'].lower() and 'Sem ponte' not in item['texto']
    assert FALTA_TEMPO_TEV in item['texto']
    assert 'baixo' not in aviso['texto'] and 'Sem ponte' not in aviso['texto']
    assert FALTA_TEMPO_TEV in aviso['texto'] and 'menos de 3 meses' in aviso['texto']
    assert item['divergencia'] == '' and aviso['divergencia'] == ''
    for classifica in (pm._risco_te_aha, pm._risco_te_sbc):
        categoria, motivos, _ = classifica({'condicoes': {'tev'}})
        assert categoria is None and motivos == []


def test_tev_ha_mais_de_12_meses_so_e_baixo_risco_quando_o_medico_escolhe():
    item, aviso = _varfarina(idade=60, sexo='masculino', condicoes={'tev', 'tev_mais_12m'})
    assert item['resumo'] == 'Suspender 5 dias antes, sem ponte'
    assert 'AHA (Tabela 14): baixo (TEV há >12 meses)' in aviso['texto'] and FALTA_TEMPO_TEV not in aviso['texto']
    # O mais recente vale: com dois tempos marcados (TEV de repetição), fica o de maior risco
    item, _ = _varfarina(condicoes={'tev', 'tev_mais_12m', 'tev_recente_3m'})
    assert 'com ponte' in item['resumo']
    assert pm._risco_te_aha({'condicoes': {'tev', 'tev_3_12m'}})[0] == 'moderado'
    assert pm._risco_te_sbc({'condicoes': {'tev', 'tev_3_12m'}})[0] == 'moderado'


def test_tev_sem_data_com_outra_indicacao():
    # FA de baixo risco + TEV sem data: o TEV pode ser de alto risco; nada de "baixo" nem de "sem ponte"
    item, aviso = _varfarina(idade=60, sexo='masculino', condicoes={'fa', 'hipertensao', 'tev'})
    assert item['conduta'] == 'individualizar' and 'sem ponte' not in item['resumo']
    assert 'CHA₂DS₂-VASc = 1' in aviso['texto'] and FALTA_TEMPO_TEV in aviso['texto']
    assert 'Tabela 14): baixo' not in aviso['texto'] and 'Sem ponte' not in aviso['texto']
    # Prótese mitral já é alto risco, qualquer que seja o tempo do TEV: a ponte vale, e o dado que falta é pedido
    item, aviso = _varfarina(idade=50, sexo='masculino', condicoes={'protese_mecanica_mitral', 'tev'})
    assert item['resumo'] == 'Suspender 5 dias antes, com ponte de heparina'
    assert 'AHA (Tabela 14): alto (prótese mecânica mitral)' in aviso['texto'] and FALTA_TEMPO_TEV in aviso['texto']
    # Alto pela AHA (CHA₂DS₂-VASc 7) e sem classificação pela SBC (CHADS₂ 4 + TEV sem data): não se afirma a
    # divergência "SBC: sem ponte"
    ctx = dict(idade=80, sexo='feminino', condicoes={'fa', 'ic', 'hipertensao', 'diabetes', 'dac', 'tev'})
    item, aviso = _varfarina(**ctx)
    assert 'com ponte' in item['resumo'] and 'SBC (Tabela 11): não classificado' in aviso['texto']
    assert 'SBC: risco' not in item['divergencia'] + aviso['divergencia']


def test_tela_e_motor_tem_a_opcao_ha_mais_de_12_meses(app, contas):
    assert 'tev_mais_12m' in po.CONDICOES
    assert 'tev_mais_12m' in _p(condicoes=['tev', 'tev_mais_12m'])['condicoes']
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    bloco = re.search(r'data-detalhe-de="po_c_tev" hidden>(.*?)</span>', html).group(1)
    assert re.findall(r'value="(tev_[a-z_0-9]+)"', bloco) == ['tev_recente_3m', 'tev_3_12m', 'tev_mais_12m']
    assert 'Há mais de 12 meses' in bloco and i18n.coberto('Há mais de 12 meses')
    # Pela rota, como a tela envia: só a caixa de cima marcada
    cliente = _cliente(app, contas)
    r = _preop(cliente, condicoes=['tev'], medicacoes=['varfarina'], sangramento='alto')
    assert 'sem ponte' not in _med(r, 'varfarina')['resumo'] and FALTA_TEMPO_TEV in _med(r, 'varfarina')['texto']
    r = _preop(cliente, condicoes=['tev', 'tev_mais_12m'], medicacoes=['varfarina'], sangramento='alto')
    assert _med(r, 'varfarina')['resumo'] == 'Suspender 5 dias antes, sem ponte'


# ── 2. ARISCAT incompleto ────────────────────────────────────────────────────────────────────────────────────────

def test_ariscat_sem_variavel_obrigatoria_sai_incompleto_sem_categoria():
    """Antes: 60 anos, colectomia, sem SpO₂, hemoglobina nem duração = 18 pontos, "Baixo". Com SpO₂ de 90% (24),
    hemoglobina de 9 (11) e mais de 3 h (23), seriam 76, "Alto"."""
    r = po.ariscat(_p())
    assert r['status'] == 'incompleto' and r['faltando'] == ['SpO₂', 'hemoglobina', 'duração da cirurgia']
    assert r['nivel'] is None and r['faixa'] == 'Faltam dados' and r['valor'] == '—'
    assert r['minimo'] == 18 and 'pontuação mínima é 18' in r['nota'] and 'não é classificado' in r['nota']
    assert r['falta'] == r['faltando']                 # a tela lista o que falta em "Para calcular, informe:"
    completo = po.ariscat(_p(spo2=90, hemoglobina=9, duracao='mais_3h'))
    assert (completo['status'], completo['valor'], completo['nivel'], completo['faltando']) == ('calculado', 76, 'alto', [])


@pytest.mark.parametrize('falta, dados', [
    ('SpO₂', dict(hemoglobina=13, duracao='menos_2h')),
    ('hemoglobina', dict(spo2=98, duracao='menos_2h')),
    ('duração da cirurgia', dict(spo2=98, hemoglobina=13)),
])
def test_ariscat_cada_variavel_que_falta_impede_a_categoria(falta, dados):
    r = po.ariscat(_p(**dados))
    assert r['status'] == 'incompleto' and r['faltando'] == [falta] and r['nivel'] is None
    assert not isinstance(r['valor'], int)


def test_ariscat_completo_e_nao_aplicavel_continuam_como_antes():
    r = po.ariscat(_p(idade=72, spo2=97, hemoglobina=13, duracao='2_3h'))
    assert (r['valor'], r['nivel'], r['faixa'], r['status'], r['falta']) == (34, 'intermediario', 'Intermediário', 'calculado', [])
    r = po.ariscat(_p(cirurgia='catarata'))
    assert r['faixa'] == 'Não se aplica' and r['status'] == 'nao_aplicavel' and not r['aplicavel'] and r['falta'] == []


def test_ariscat_incompleto_guarda_o_minimo_para_as_medidas_e_nao_vale_como_baixo():
    # Mínimo já na faixa intermediária (esofagectomia 24 + idade 3): a nota diz "pelo menos", sem categoria
    r = po.avaliar(_p(cirurgia='esofagectomia'))
    escore = r['pulmonar']['escore']
    assert escore['status'] == 'incompleto' and escore['nivel'] is None and escore['minimo'] == 27
    assert 'pelo menos intermediário' in escore['nota']
    assert any(m['titulo'] == 'Expansão pulmonar no pós-operatório' for m in r['pulmonar']['medidas'])
    # Mínimo baixo: as medidas não são afirmadas, e o resumo curto (que supõe ARISCAT baixo) não sai
    r = po.avaliar(_p(idade=28, sexo='feminino', cirurgia='hernia'))
    assert r['pulmonar']['escore']['status'] == 'incompleto' and r['pulmonar']['medidas'] == []
    assert not r['resumido']
    assert po.avaliar(_p(idade=28, sexo='feminino', cirurgia='hernia', spo2=98, hemoglobina=13.5,
                         duracao='menos_2h'))['resumido']
    # Mínimo já alto: a nota diz que o risco já é alto
    alto = po.ariscat(_p(idade=85, cirurgia='esofagectomia', infeccao_respiratoria=True))
    assert alto['minimo'] == 57 and alto['nivel'] is None and 'já está na faixa de risco alto' in alto['nota']


def test_tela_mostra_o_ariscat_incompleto():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    bloco = html[html.index('// ── Aba "Pré-operatório"'):]
    # O cartão pede o que falta ("Para calcular, informe:"), marca os itens como "Já somados:" e o texto do
    # prontuário diz "incompleto" em vez de um número com faixa
    assert bloco.count("status === 'incompleto'") >= 3
    assert "const incompleto = e => e.status === 'incompleto' || e.valor === '—';" in bloco
    for texto in ('Já somados:', 'incompleto, falta informar', 'Para calcular, informe:'):
        assert f"'{texto}'" in bloco and i18n.coberto(texto)


# ── 3. TFG e ClCr sem arredondar nas comparações ─────────────────────────────────────────────────────────────────

def test_tfg_exata_e_inteira_para_exibir():
    exata = prevent.tfg_ckd_epi_2021(2.5, 55, 'masculino')
    assert exata == pytest.approx(29.60, abs=0.005)
    assert prevent.egfr_ckd_epi_2021(2.5, 55, 'masculino') == 30          # inteira: PREVENT e exibição
    assert prevent.egfr_ckd_epi_2021(1.0, 50, 'feminino') == 69


def test_numero_exibido_nao_atravessa_o_limiar():
    f = funcao_renal.para_exibir
    assert f(29.6, (30, 45)) == 29.6 and f(29.96, (30, 45)) == 29.9      # 29,6 não vira 30 ao lado de "abaixo de 30"
    assert f(29.4, (30, 45)) == 29 and f(30.4, (30, 45)) == 30 and f(52.6, (30, 45)) == 53
    assert f(29.955, (15, 30, 50), 1) == 29.95 and f(46.04, (15, 30, 50), 1) == 46.0
    assert f(39.135, (15, 30, 50), 1) == 39.1


def test_metformina_com_tfg_29_6_e_contraindicada(app, contas):
    """Homem de 55 anos, creatinina 2,5 mg/dL: TFG 29,6. Antes: arredondada para 30, sem o alerta de contraindicação."""
    cliente = _cliente(app, contas)
    r = _preop(cliente, idade=55, creatinina=2.5, medicacoes=['metformina'])
    m = _med(r, 'metformina')
    assert m['resumo'] == 'Suspender (TFG < 30)' and 'contraindicada abaixo de 30' in m['texto']
    assert 'TFG 29,6 mL/min/1,73 m²' in m['texto'] and i18n.coberto(m['texto'])
    assert r['tfg'] == 29.6                              # a tela não mostra "30" ao lado de "abaixo de 30"
    # 75 anos, creatinina 1,6: TFG 44,65 (antes 45, sem o teto de dose)
    m = _med(_preop(cliente, idade=75, creatinina=1.6, medicacoes=['metformina']), 'metformina')
    assert 'dose máxima de 1.000 mg/dia' in m['texto'] and 'TFG 44,6 mL/min/1,73 m²' in m['texto']
    assert i18n.coberto(m['texto'])
    # Longe do limiar, nada muda: inteiro
    r = _preop(cliente, idade=60, creatinina=1.0, medicacoes=['metformina'])
    assert r['tfg'] == prevent.egfr_ckd_epi_2021(1.0, 60, 'masculino') and 'TFG' not in _med(r, 'metformina')['resumo']


def test_clcr_29_96_segue_a_linha_renal_da_tabela_13(app, contas):
    """Homem de 41 anos, 61 kg, creatinina 2,8: ClCr 29,96 mL/min. Antes: 30,0 e esquema de função renal normal."""
    assert po.clcr_exato(_p(idade=41, peso=61, creatinina=2.8)) == pytest.approx(29.955, abs=0.001)
    cliente = _cliente(app, contas)
    r = _preop(cliente, idade=41, peso=61, creatinina=2.8, cirurgia='hernia', sangramento='baixo_moderado',
               condicoes=['fa'], medicacoes=['rivaroxabana'])
    m = _med(r, 'rivaroxabana')
    assert m['resumo'].startswith('Sem dose do D-2 ao D0 (última no D-3)') and 'ClCr 29,95 mL/min' in m['texto']
    assert i18n.coberto(m['texto'])
    assert r['clcr'] == 29.95
    # Dabigatrana: 45 anos, 53 kg, creatinina 1,4 → ClCr 49,95 (corte de 50)
    r = _preop(cliente, idade=45, peso=53, creatinina=1.4, cirurgia='hernia', sangramento='baixo_moderado',
               condicoes=['fa'], medicacoes=['dabigatrana'])
    assert _med(r, 'dabigatrana')['resumo'].startswith('Sem dose do D-2 ao D0 (última no D-3)')
    # Longe do corte, o valor mostrado continua com uma casa
    assert po.clcr(_p(idade=72, peso=78, creatinina=1.6)) == 46.0


def test_cartao_renal_do_checkup_classifica_pela_tfg_exata(client):
    """Mulher de 54 anos, creatinina 1,1: TFG 59,7. Antes: 60, categoria G2, sem pedir a confirmação da DRC."""
    cartao = funcao_renal.avaliar('1.1', 54, 'feminino')
    assert cartao['g']['categoria'] == 'G3a' and cartao['tfg'] == 59.7
    assert any('TFG < 60 sem doença renal crônica marcada' in o for o in cartao['observacoes'])
    assert funcao_renal.avaliar('1.0', 50, 'feminino')['tfg'] == 69
    base = dict(sexo='feminino', tabagismo='nunca', comorbidades=[], medicacoes=[], historia_familiar=[],
                imunossupressao='nao', gestante='nao', lactante='nao')
    r = client.post('/api/checkup-intelligent', json=dict(base, idade=54, creatinina='1.1')).get_json()
    assert r['drc_a_confirmar'] is True and r['funcao_renal']['g']['categoria'] == 'G3a'
    # DRC marcada, homem de 75 anos, creatinina 1,6: TFG 44,65 é G3b (antes 45, G3a)
    r = client.post('/api/checkup-intelligent', json=dict(base, sexo='masculino', idade=75, creatinina='1.6',
                                                           comorbidades=['doenca_renal'])).get_json()
    creatinina = next(x for x in r['recommendations'] if x['titulo'] == 'Creatinina, soro')
    assert 'Doença renal crônica G3b' in creatinina['subtitulo']
    assert r['funcao_renal']['g']['categoria'] == 'G3b' and r['funcao_renal']['estagio'] == 'Estágio 3b'


# ── 4. Classe ASA e CFS: só inteiros ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('asa', [2.9, '2,9', '3.5', 1.5])
def test_asa_decimal_e_recusada(asa):
    """Antes: ASA 2,9 era aceita e virava 2 no Gupta MICA."""
    with pytest.raises(po.EntradaInvalida) as erro:
        _p(asa=asa)
    assert 'classe ASA' in erro.value.mensagem and 'inteiro' in erro.value.mensagem
    assert i18n.coberto(erro.value.mensagem)


@pytest.mark.parametrize('asa, lida', [(1, 1), ('3', 3), (5, 5), (2.0, 2), ('', None), (None, None)])
def test_asa_inteira_de_1_a_5_e_aceita(asa, lida):
    assert _p(asa=asa)['asa'] == lida


@pytest.mark.parametrize('asa', [0, 6, 'III', True])
def test_asa_fora_do_conjunto_e_recusada(asa):
    with pytest.raises(po.EntradaInvalida):
        _p(asa=asa)


def test_asa_decimal_pela_rota_e_erro_de_validacao(app, contas):
    cliente = _cliente(app, contas)
    r = cliente.post('/api/preoperatorio', json=dict(idade=60, sexo='masculino', cirurgia='colectomia',
                                                     urgencia='eletiva', asa=2.9, funcional='independente'))
    assert r.status_code == 400 and r.get_json()['codigo'] == 'entrada_invalida'
    assert 'classe ASA' in r.get_json()['erros'][0]['mensagem']
    # a tela só oferece I a V
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    campo = html[html.index('<select id="po_asa">'):]
    assert re.findall(r'<option value="([^"]*)"', campo[:campo.index('</select>')]) == ['', '1', '2', '3', '4', '5']


def test_cfs_decimal_tambem_e_recusada():
    """Mesmo problema da ASA: CFS 4,9 virava 4 (pré-frágil) em vez de recusar."""
    with pytest.raises(po.EntradaInvalida) as erro:
        _p(cfs=4.9)
    assert 'Fragilidade' in erro.value.mensagem and i18n.coberto(erro.value.mensagem)
    assert _p(cfs='5')['cfs'] == 5 and po.fragilidade(_p(cfs=5))['nivel'] == 'alto'


# ── 5. TEV recente e adiamento da cirurgia eletiva ───────────────────────────────────────────────────────────────

TITULO_TEV = 'TEV há menos de 3 meses: considerar adiar a cirurgia eletiva'


def _aviso_tev(meds=('varfarina',), **ctx):
    ctx.setdefault('sangramento', 'baixo_moderado')
    ctx.setdefault('urgencia', 'eletiva')
    return next((a for a in pm.condutas(list(meds), ctx)['avisos'] if a['titulo'] == TITULO_TEV), None)


def test_tev_recente_em_cirurgia_eletiva_gera_aviso_com_a_fonte():
    """AHA/ACC 2026, §7.6, texto de apoio da rec. 1: "delaying elective NCS may permit safer interruption of OAC"."""
    aviso = _aviso_tev(condicoes={'tev', 'tev_recente_3m'})
    assert aviso and 'AHA' in aviso['texto'] and '§7.6' in aviso['texto'] and 'sem classe' in aviso['texto']
    rotulos = [r['label'] for r in aviso['referencias']]
    assert any(r.startswith('AHA/ACC 2026, §7.6') for r in rotulos)
    assert all(r['url'].startswith('https://') for r in aviso['referencias'])
    assert 'SBC' in aviso['divergencia']                 # a SBC classifica o risco, mas não fala em adiar
    assert i18n.coberto(aviso['titulo']) and i18n.coberto(aviso['texto']) and i18n.coberto(aviso['divergencia'])
    # vale para qualquer anticoagulante e também sem a lista de medicamentos preenchida
    assert _aviso_tev(meds=('rivaroxabana',), condicoes={'tev_recente_3m'}, clcr=80.0)
    assert _aviso_tev(meds=(), condicoes={'tev_recente_3m'})


@pytest.mark.parametrize('ctx', [
    dict(condicoes={'tev', 'tev_recente_3m'}, urgencia='tempo_sensivel'),
    dict(condicoes={'tev', 'tev_recente_3m'}, urgencia='urgencia'),
    dict(condicoes={'tev', 'tev_recente_3m'}, urgencia='emergencia'),
    dict(condicoes={'tev', 'tev_3_12m'}),
    dict(condicoes={'tev', 'tev_mais_12m'}),
    dict(condicoes={'tev'}),
    dict(condicoes={'tev', 'tev_recente_3m'}, sangramento='minimo'),     # anticoagulante mantido: nada a interromper
    dict(condicoes={'fa'}),
])
def test_aviso_de_adiamento_so_no_tev_recente_e_na_cirurgia_eletiva(ctx):
    assert _aviso_tev(**ctx) is None


def test_aviso_de_adiamento_chega_pela_rota(app, contas):
    cliente = _cliente(app, contas)
    r = _preop(cliente, condicoes=['tev', 'tev_recente_3m'], medicacoes=['varfarina'], sangramento='alto')
    aviso = next(a for a in r['medicamentos']['avisos'] if a['titulo'] == TITULO_TEV)
    assert '<a href="https://' in aviso['referencia_html']
    r = _preop(cliente, condicoes=['tev', 'tev_recente_3m'], medicacoes=['varfarina'], sangramento='alto',
               urgencia='urgencia')
    assert TITULO_TEV not in [a['titulo'] for a in r['medicamentos']['avisos']]
