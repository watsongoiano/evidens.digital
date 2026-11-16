"""Rastreamento geral de adultos (relatório de auditoria A, novembro de 2026).

Cada regra corrigida tem caso positivo, negativo e limítrofe, com pacientes fictícios.
"""
import pytest

BASE = dict(sexo='masculino', tabagismo='nunca', imunossupressao='nao', comorbidades=[], medicacoes=[], historia_familiar=[])
MULHER = dict(sexo='feminino', gestante='nao', lactante='nao')


def _resposta(client, **dados):
    corpo = dict(BASE, **dados)
    r = client.post('/api/checkup-intelligent', json=corpo)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _recs(client, **dados):
    return {r['titulo']: r for r in _resposta(client, **dados)['recommendations']}


def _orientacoes(client, **dados):
    return {o['titulo']: o for o in _resposta(client, **dados)['orientacoes']}


ECG = 'Eletrocardiograma de repouso'
HBA1C = 'Hemoglobina glicada (HbA1c), soro'
GLICOSE = 'Glicose, soro'
CREATININA = 'Creatinina, soro'
UACR = 'Relação albumina/creatinina urinária (uACR)'
HIV = 'Anti-HIV 1 e 2, soro'
HCV = 'Anti-HCV IgG, soro'
HBV = 'HBsAg, anti-HBc total e anti-HBs'
SIFILIS = 'Sífilis: teste treponêmico ou VDRL, soro'
AAA = 'Ultrassonografia com Doppler de Aorta Abdominal'
DEXA = 'Densitometria óssea (DEXA)'
LIPIDIOS = 'Colesterol total e frações, soro'
LPA = 'Lipoproteína(a) - Lp(a), soro'
MAPA = 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)'
ECO = 'Ecocardiograma transtorácico'


# ── A-01: ECG não é rastreio (USPSTF 2018, D no baixo risco) ─────────────────────

@pytest.mark.parametrize('idade', [18, 25, 40, 64, 88])
def test_adulto_higido_nao_recebe_ecg(client, idade):
    assert ECG not in _recs(client, idade=idade)


def test_ecg_entra_na_has_com_avaliacao_inicial_e_anual(client):
    ecg = _recs(client, idade=30, comorbidades=['hipertensao'])[ECG]
    assert ecg['subtitulo'].startswith('Adultos com HAS | Anual') and 'SBC 2025' in ecg['referencia']
    assert 'AHA 2022' not in ecg['referencia'] and 'SBC 2018' not in ecg['referencia']


def test_diabetico_sem_has_nao_recebe_ecg_mas_ve_a_divergencia(client):
    assert ECG not in _recs(client, idade=55, comorbidades=['diabetes'])
    assert 'Divergência entre diretrizes: ECG no diabetes' in _orientacoes(client, idade=55, comorbidades=['diabetes'])
    # com HAS, o ECG é o da HAS e o aviso não aparece
    assert ECG in _recs(client, idade=55, comorbidades=['diabetes', 'hipertensao'])
    assert 'Divergência entre diretrizes: ECG no diabetes' not in _orientacoes(client, idade=55, comorbidades=['diabetes', 'hipertensao'])


def test_gatilho_familiar_de_ecg_continua(client):
    assert ECG in _recs(client, idade=25, historia_familiar=['morte_subita'])


# ── A-02: HIV dos 15 aos 65 anos (USPSTF 2019, A) e anual até 30 (MS) ─────────────

@pytest.mark.parametrize('idade, subtitulo', [
    (25, 'Adolescentes e jovens ≤30 anos | Anual'), (30, 'Adolescentes e jovens ≤30 anos | Anual'),
    (31, 'Adultos 15-65 anos | Pelo menos 1x na vida'), (50, 'Adultos 15-65 anos | Pelo menos 1x na vida'),
    (65, 'Adultos 15-65 anos | Pelo menos 1x na vida'),
])
def test_hiv_em_toda_a_faixa_de_15_a_65(client, idade, subtitulo):
    assert _recs(client, idade=idade)[HIV]['subtitulo'] == subtitulo


def test_hiv_depois_dos_65_so_orientacao_e_nunca_em_quem_vive_com_hiv(client):
    assert HIV not in _recs(client, idade=66)
    assert 'HIV depois dos 65 anos' in _orientacoes(client, idade=66)
    assert HIV not in _recs(client, idade=40, comorbidades=['hiv'], exames_hiv_previos='nao')


def test_hiv_ate_30_mostra_a_divergencia_de_frequencia(client):
    assert 'Divergência entre diretrizes: frequência do teste de HIV' in _orientacoes(client, idade=25)
    assert 'Divergência entre diretrizes: frequência do teste de HIV' not in _orientacoes(client, idade=31)


# ── A-03: PA isolada (decisão do responsável clínico) ─────────────────────────────

@pytest.mark.parametrize('pas, pad, a_confirmar', [(129, 79, False), (130, 79, True), (132, 82, True), (150, 95, True),
                                                   (179, 109, True)])
def test_pa_alterada_sem_has_pede_so_mrpa_ou_mapa(client, pas, pad, a_confirmar):
    recs = _recs(client, idade=40, pas=pas, pad=pad)
    assert (MAPA in recs) is a_confirmar
    for exame in ('Potássio, soro', 'Ácido úrico, soro', UACR, ECG, ECO, CREATININA):
        assert exame not in recs, exame
    if a_confirmar:
        assert recs[MAPA]['subtitulo'] == 'PA de consultório alterada, HAS a confirmar | Para confirmar o diagnóstico'


def test_pa_grave_dispara_o_bloco_de_has(client):
    recs = _recs(client, idade=40, pas=182, pad=100)
    assert {'Potássio, soro', CREATININA, UACR, ECG} <= set(recs)
    assert 'Para confirmar' not in recs[MAPA]['subtitulo']


def test_gestante_com_pa_alterada_fica_com_as_regras_do_pre_natal(client):
    r = _resposta(client, idade=30, **dict(MULHER, gestante='sim'), idade_gestacional=12, primeira_consulta='sim', pas=134, pad=84)
    assert not any(o['titulo'] == 'PA alterada: confirmar antes de rotular HAS' for o in r['orientacoes'])


# ── A-04: aneurisma de aorta em quem já fumou (USPSTF 2019, B) ───────────────────

@pytest.mark.parametrize('idade, tabagismo, macos, recebe', [
    (67, 'ex', 5, True), (67, 'atual', 1, True), (65, 'ex', 0.5, True), (75, 'ex', 30, True),
    (64, 'ex', 30, False), (76, 'ex', 30, False), (67, 'nunca', '', False),
])
def test_aaa_em_homem_que_ja_fumou(client, idade, tabagismo, macos, recebe):
    dados = dict(idade=idade, tabagismo=tabagismo, macos_ano=macos)
    if tabagismo == 'ex':
        dados['anos_parou_fumar'] = 20
    recs = _recs(client, **dados)
    assert (AAA in recs) is recebe
    if recebe:
        assert recs[AAA]['subtitulo'] == 'Homens 65-75 anos que já fumaram | Uma vez'


def test_aaa_nunca_fumante_e_oferta_seletiva_e_dpoc_nao_basta(client):
    assert AAA not in _recs(client, idade=67, comorbidades=['dpoc'])
    assert 'Aneurisma de aorta: homem que nunca fumou' in _orientacoes(client, idade=67)
    assert AAA not in _recs(client, idade=67, tabagismo='ex', macos_ano=30, anos_parou_fumar=20, **MULHER)


# ── M-01: rastreio de diabetes (ADA 2026; USPSTF 2021) ───────────────────────────

@pytest.mark.parametrize('dados, recebe', [
    (dict(idade=25), False), (dict(idade=34), False), (dict(idade=35), True), (dict(idade=70), True), (dict(idade=71), False),
    (dict(idade=25, peso=82, altura=175, historia_familiar=['diabetes']), True),     # IMC 26,8 + pai/mãe com DM
    (dict(idade=25, peso=76, altura=175, historia_familiar=['diabetes']), False),    # IMC 24,8: limítrofe abaixo
    (dict(idade=25, peso=105, altura=175), False),                                   # IMC 34 sozinho não é fator
    (dict(idade=25, peso=82, altura=175, hdl=30), True),
    (dict(idade=80, peso=82, altura=175, historia_familiar=['diabetes']), True),
])
def test_rastreio_de_diabetes(client, dados, recebe):
    recs = _recs(client, **dados)
    assert (HBA1C in recs) is recebe
    assert GLICOSE not in recs   # um exame basta: a glicemia de jejum fica como alternativa na descrição
    if recebe:
        assert 'glicemia de jejum' in recs[HBA1C]['descricao'] and 'ADA 2026' in recs[HBA1C]['referencia']


def test_rastreio_de_diabetes_avisa_as_divergencias(client):
    assert 'Divergência entre diretrizes: rastreio de diabetes sem sobrepeso' in _orientacoes(client, idade=40)
    assert 'Divergência entre diretrizes: rastreio de diabetes sem sobrepeso' not in _orientacoes(client, idade=40, peso=85, altura=175)
    assert 'Divergência entre diretrizes: rastreio de diabetes depois dos 70 anos' in _orientacoes(client, idade=72)


def test_diabetico_continua_com_glicemia_e_hba1c_de_controle(client):
    recs = _recs(client, idade=25, comorbidades=['diabetes_tipo_1'])
    assert recs[HBA1C]['subtitulo'] == 'Diabéticos | A cada 3-6 meses' and recs[GLICOSE]['subtitulo'] == 'Diabéticos | Junto da HbA1c'


# ── M-02: creatinina e uACR só com risco de DRC (KDIGO 2024, PP 1.1.1.1) ─────────

@pytest.mark.parametrize('dados, recebe', [
    (dict(idade=25), False), (dict(idade=70), False),
    (dict(idade=25, comorbidades=['hipertensao']), True), (dict(idade=50, comorbidades=['dcv_aterosclerotica']), True),
    (dict(idade=50, comorbidades=['insuficiencia_cardiaca']), True), (dict(idade=30, historia_familiar=['rim_policistico']), True),
])
def test_creatinina_e_uacr_juntas_so_com_risco(client, dados, recebe):
    recs = _recs(client, **dados)
    assert (CREATININA in recs) is recebe and (UACR in recs) is recebe
    if recebe:
        assert 'KDIGO 2024' in recs[CREATININA]['referencia'] and recs[CREATININA]['grau_evidencia'] in ('PP', 'A')


# ── M-04: ecocardiograma só com indicação ────────────────────────────────────────

def test_ecocardiograma_so_na_has_resistente(client):
    assert ECO not in _recs(client, idade=45, comorbidades=['hipertensao'])
    eco = _recs(client, idade=45, comorbidades=['has_resistente'])[ECO]
    assert eco['subtitulo'] == 'HAS resistente | Conforme indicação clínica' and '1-2 anos' not in eco['subtitulo']


# ── M-05: hepatite B (decisão do responsável clínico) ─────────────────────────────

def test_hepatite_b_painel_uma_vez_em_adulto(client):
    hbv = _recs(client, idade=18)[HBV]
    assert hbv['subtitulo'] == 'Adultos ≥18 anos sem vacinação documentada | Pelo menos 1x na vida'
    assert 'CDC 2023' in hbv['referencia'] and 'USPSTF 2020' in hbv['referencia'] and 'vacinar' in hbv['descricao']
    assert 'Divergência entre diretrizes: rastreio de hepatite B' in _orientacoes(client, idade=18)
    assert HBV in _recs(client, idade=88)


def test_hepatite_b_cronica_e_gestante_nao_recebem_o_painel_de_rastreio(client):
    assert 'Adultos ≥18 anos sem vacinação' not in (_recs(client, idade=40, comorbidades=['hepatite_b_cronica']).get(HBV) or {}).get('subtitulo', '')
    r = _resposta(client, idade=30, **dict(MULHER, gestante='sim'), idade_gestacional=12, primeira_consulta='sim')
    assert not any('sem vacinação documentada' in (x.get('subtitulo') or '') for x in r['recommendations'])


# ── M-06: sífilis com risco (PCDT IST 2022; USPSTF 2022) ─────────────────────────

def test_sifilis_com_prep_e_orientacao_nos_demais(client):
    assert SIFILIS not in _recs(client, idade=25)
    assert 'Sífilis: testar com risco aumentado' in _orientacoes(client, idade=25)
    recs = _recs(client, idade=25, medicacoes=['tenofovir_entricitabina'])
    assert recs[SIFILIS]['subtitulo'] == 'PrEP | A cada 4 meses'   # PCDT PrEP 2024, Quadro 5 (src/utils/condicoes.py)
    assert 'Sífilis: testar com risco aumentado' not in _orientacoes(client, idade=25, medicacoes=['tenofovir_entricitabina'])


# ── M-07 e B-05: densitometria ───────────────────────────────────────────────────

@pytest.mark.parametrize('idade', [65, 80])
def test_densitometria_sem_intervalo_fixo(client, idade):
    dexa = _recs(client, idade=idade, **MULHER)[DEXA]
    assert dexa['subtitulo'] == 'Mulheres ≥65 anos | Repetir conforme o resultado (T-score)' and 'USPSTF 2025' in dexa['referencia']


@pytest.mark.parametrize('dados, recebe', [
    (dict(idade=55, tabagismo='atual', macos_ano=10), True), (dict(idade=55, peso=45, altura=165), True),
    (dict(idade=55, alcoolismo='pesado'), True), (dict(idade=55, comorbidades=['artrite_reumatoide']), True),
    (dict(idade=55), False), (dict(idade=49, tabagismo='atual', macos_ano=10), False), (dict(idade=64, tabagismo='atual', macos_ano=10), True),
])
def test_densitometria_pos_menopausa_com_fator_de_risco(client, dados, recebe):
    recs = _recs(client, **MULHER, **dados)
    assert (DEXA in recs) is recebe
    if recebe:
        assert 'FRAX' in recs[DEXA]['descricao'] and 'pós-menopausa' in recs[DEXA]['descricao']


def test_densitometria_por_fratura_familiar_no_homem_nao_cita_a_uspstf(client):
    homem = _recs(client, idade=55, historia_familiar=['osteoporose_fratura'])[DEXA]
    assert 'USPSTF' not in homem['referencia'] and 'BHOF 2022' in homem['referencia'] and 'compartilhada' in homem['descricao']
    mulher = _recs(client, idade=55, **MULHER, historia_familiar=['osteoporose_fratura'])[DEXA]
    assert 'USPSTF 2025' in mulher['referencia']
    assert 'Divergência entre diretrizes: densitometria no homem' in _orientacoes(client, idade=70)
    assert 'Divergência entre diretrizes: densitometria no homem' not in _orientacoes(client, idade=69)


# ── B-01, B-02: um pedido por exame (código TUSS) ────────────────────────────────

def test_mesmo_exame_com_nomes_diferentes_sai_uma_vez(client):
    from src.utils import tuss
    r = _resposta(client, idade=62, **MULHER, comorbidades=['diabetes', 'hipertensao', 'lupus', 'fibrilacao_atrial', 'dpoc', 'hiv'],
                  medicacoes=['adalimumabe', 'prednisona'], exames_hiv_previos='nao')
    vistos = {}
    for rec in r['recommendations']:
        if rec['categoria'] in ('laboratorio', 'imagem'):
            for linha in tuss.linhas_da_guia(rec['titulo'], 'feminino'):
                if linha['codigo']:
                    assert linha['codigo'] not in vistos, (rec['titulo'], vistos.get(linha['codigo']))
                    vistos[linha['codigo']] = rec['titulo']
    titulos = {rec['titulo'] for rec in r['recommendations']}
    assert UACR in titulos and 'Razão albumina/creatinina, urina' not in titulos
    assert 'Sódio e potássio, soro' in titulos and not {'Sódio, soro', 'Potássio, soro'} & titulos
    assert HBV in titulos and not {'Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro'} & titulos
    assert 'Anticorpos anti-HCV, soro' in titulos and HCV not in titulos
    # fundo de olho: a avaliação com tonometria cobre a do diabético
    assert 'Avaliação oftalmológica com tonometria e fundoscopia' in titulos and 'Fundoscopia (Exame de fundo de olho)' not in titulos
    # os dois motivos aparecem, e cada fonte tem link
    uacr = next(x for x in r['recommendations'] if x['titulo'] == UACR)
    assert 'Diabéticos' in uacr['subtitulo'] and 'fator de risco para DRC' in uacr['subtitulo']
    assert uacr['referencia_html'].count('<a href="https://') == len(uacr['referencias'])


def test_deduplicacao_por_codigo_une_sinonimos_e_absorve_o_exame_no_combinado():
    from src.routes.checkup_intelligent import deduplicar_recomendacoes
    rec = lambda t, s, p='media': {'titulo': t, 'categoria': 'laboratorio', 'subtitulo': s, 'referencia': 'X 2020',  # noqa: E731
                                   'descricao': t, 'prioridade': p}
    unidos = deduplicar_recomendacoes([rec('Hemograma completo, sangue total', 'DPOC | Anual'),
                                       rec('Hemograma completo com plaquetas', 'Diabéticos | Anual', 'alta'),
                                       rec('Potássio, soro', 'Adultos com HAS | Anual'), rec('Sódio e potássio, soro', 'FA | Avaliação inicial'),
                                       rec('Creatinina, soro', 'Adultos com HAS | Anual')])
    assert [u['titulo'] for u in unidos] == ['Hemograma completo com plaquetas', 'Sódio e potássio, soro', 'Creatinina, soro']
    assert unidos[0]['prioridade'] == 'alta' and 'Também: ' in unidos[0]['subtitulo']
    assert 'Adultos com HAS | Anual' in unidos[1]['_subtitulos']
    # exames diferentes não se unem; vacinas continuam pelo título
    assert len(deduplicar_recomendacoes([rec('Glicose, soro', 'A | Anual'), rec('Hemoglobina glicada (HbA1c), soro', 'A | Anual')])) == 2


# ── B-03, B-04: referências vigentes e com link ───────────────────────────────────

def test_referencias_do_rastreio_geral_sao_as_vigentes(client):
    recs = _recs(client, idade=45, peso=85, altura=175)
    assert 'USPSTF 2024' not in recs[HCV]['referencia'] and 'MS 2026 (PCDT Hepatite C)' in recs[HCV]['referencia']
    assert recs[LIPIDIOS]['referencia'] == 'ACC/AHA 2026' and recs[LPA]['referencia'] == 'ACC/AHA 2026'
    assert 'ADA 2024' not in recs[HBA1C]['referencia']
    urls = {link['label']: link['url'] for rec in recs.values() for link in rec.get('referencias', [])}
    assert urls['ACC/AHA 2026'] == 'https://doi.org/10.1161/CIR.0000000000001423'
    assert urls['ADA 2026'] == 'https://doi.org/10.2337/dc26-S002'
    assert 'hepatite-c' in urls['MS 2026 (PCDT Hepatite C)']
    hba1c = {link['label']: link['url'] for link in recs[HBA1C]['referencias']}
    assert hba1c['USPSTF 2021'].endswith('screening-for-prediabetes-and-type-2-diabetes')


# ── B-06: idade de parada de Lp(a) e lipídios ────────────────────────────────────

@pytest.mark.parametrize('idade, lpa', [(20, True), (75, True), (76, False), (88, False)])
def test_lpa_ate_75_anos(client, idade, lpa):
    assert (LPA in _recs(client, idade=idade)) is lpa


def test_lipidios_depois_dos_75_sao_decisao_individual(client):
    assert _recs(client, idade=75)[LIPIDIOS]['subtitulo'] == 'Adultos ≥40 anos | A cada 4-6 anos'
    assert _recs(client, idade=76)[LIPIDIOS]['subtitulo'].startswith('Adultos ≥76 anos | Decisão individual')


# ── B-07: o motivo do diabetes entra no perfil lipídico ──────────────────────────

def test_perfil_lipidico_do_diabetico(client):
    # Regra única em src/utils/condicoes.py (auditoria D, D-11): ADA 2026 sem estatina; ACC/AHA 2018 com tratamento.
    sem = _recs(client, idade=55, comorbidades=['diabetes'])[LIPIDIOS]
    assert sem['subtitulo'] == 'Diabéticos | Anual' and 'ADA 2026 (seção 10)' in sem['referencia']
    assert _recs(client, idade=35, comorbidades=['diabetes'])[LIPIDIOS]['subtitulo'].endswith('A cada 5 anos')
    com = _recs(client, idade=55, comorbidades=['diabetes'], medicacoes_continuo='atorvastatina 20 mg')[LIPIDIOS]
    assert com['subtitulo'].endswith('A cada 3-12 meses')
    assert 'Diabéticos' not in _recs(client, idade=55)[LIPIDIOS]['subtitulo']


# ── B-08: MAPA com a MRPA como alternativa e o rótulo conforme o caso ────────────

def test_mapa_na_has_estabelecida_avalia_controle(client):
    mapa = _recs(client, idade=40, comorbidades=['hipertensao'])[MAPA]
    assert 'suspeita' not in mapa['subtitulo'] and 'avaliar controle' in mapa['subtitulo'] and 'MRPA' in mapa['descricao']


# ── B-09: medir a PA quando não foi informada ────────────────────────────────────

def test_orienta_medir_a_pa_quando_nao_informada(client):
    assert 'Medir a pressão arterial' in _orientacoes(client, idade=25)
    assert 'Medir a pressão arterial' not in _orientacoes(client, idade=25, pas=118, pad=76)
    assert 'Medir a pressão arterial' not in _orientacoes(client, idade=25, pas=118)   # um componente já é PA medida


# ── Anti-HCV depois dos 79 anos: aviso de divergência ────────────────────────────

def test_anti_hcv_sem_idade_limite_com_aviso_depois_dos_79(client):
    assert HCV in _recs(client, idade=85)
    assert 'Divergência entre diretrizes: anti-HCV depois dos 79 anos' in _orientacoes(client, idade=80)
    assert 'Divergência entre diretrizes: anti-HCV depois dos 79 anos' not in _orientacoes(client, idade=79)


# ── Revisão externa: exame isolado não confirma doença ───────────────────────────
# REN-01: TFG < 60 isolada (KDIGO 2024, PP 1.1.3.1 e 1.1.3.2). DM-02: HbA1c ≥ 6,5% isolada (ADA 2026, seção 2).

@pytest.mark.parametrize('creatinina, a_confirmar', [('1.6', True), ('1.3', False)])   # H 50: TFG ~52 e ~66
def test_tfg_abaixo_de_60_isolada_pede_repeticao_em_3_meses(client, creatinina, a_confirmar):
    r = _resposta(client, idade=50, creatinina=creatinina)
    assert r['drc_a_confirmar'] is a_confirmar
    assert not [i for i in r['inferencias'] if i['valor'] == 'doenca_renal']
    recs = {x['titulo']: x for x in r['recommendations']}
    titulos_o = [o['titulo'] for o in r['orientacoes']]
    if a_confirmar:
        for exame in (CREATININA, UACR):
            assert recs[exame]['subtitulo'] == 'TFG < 60 isolada, DRC a confirmar | Repetir em 3 meses'
        assert 'TFG < 60: confirmar a doença renal crônica' in titulos_o
    else:
        assert CREATININA not in recs and 'TFG < 60: confirmar a doença renal crônica' not in titulos_o


def test_tfg_baixa_com_drc_marcada_nao_pede_confirmacao(client):
    r = _resposta(client, idade=50, creatinina='1.6', comorbidades=['doenca_renal'])
    assert r['drc_a_confirmar'] is False
    assert 'TFG < 60: confirmar a doença renal crônica' not in [o['titulo'] for o in r['orientacoes']]


def test_tfg_a_confirmar_soma_ao_risco_de_drc_sem_perder_a_confirmacao(client):
    recs = _recs(client, idade=50, creatinina='1.6', comorbidades=['hipertensao'])
    assert recs[CREATININA]['subtitulo'].startswith('TFG < 60 isolada, DRC a confirmar | Repetir em 3 meses')


@pytest.mark.parametrize('hba1c, a_confirmar', [('6.4', False), ('6.5', True), ('11', True)])
def test_hba1c_isolada_pede_so_a_confirmacao(client, hba1c, a_confirmar):
    r = _resposta(client, idade=40, hba1c=hba1c)
    assert r['diabetes_a_confirmar'] is a_confirmar
    recs = {x['titulo']: x for x in r['recommendations']}
    if a_confirmar:
        assert 'Para confirmar o diagnóstico' in recs[HBA1C]['subtitulo'] and 'glicemia de jejum' in recs[HBA1C]['descricao']
        assert not {UACR, 'Fundoscopia (Exame de fundo de olho)', 'Cálcio iônico, soro'} & set(recs)
        assert GLICOSE not in recs
    else:
        assert 'Para confirmar o diagnóstico' not in recs[HBA1C]['subtitulo']   # 6,4: rastreio/pré-diabetes


@pytest.mark.parametrize('extra', [dict(comorbidades=['diabetes']), dict(medicacoes=['insulina_nph']),
                                   dict(medicacoes_continuo='glibenclamida 5 mg')], ids=['marcado', 'insulina', 'antidiabetico'])
def test_hba1c_alta_com_diabetes_conhecido_segue_o_acompanhamento(client, extra):
    r = _resposta(client, idade=40, hba1c='8.0', **extra)
    assert r['diabetes_a_confirmar'] is False
    recs = {x['titulo']: x for x in r['recommendations']}
    assert recs[HBA1C]['subtitulo'].startswith('Diabéticos | A cada 3-6 meses') and UACR in recs
