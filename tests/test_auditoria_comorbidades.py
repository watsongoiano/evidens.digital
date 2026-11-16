"""Acompanhamento de comorbidades e monitorização de medicações (auditoria clínica de 15/11/2026, relatório D,
mais M-03 e M-08 do relatório A). Todos os pacientes são fictícios."""
import pytest

from src.utils import condicoes, hiv, periodicidade, tuss
from src.utils.reference_links import build_reference_links


def _resposta(client, **dados):
    base = dict(idade=50, sexo='masculino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
                comorbidades=[], medicacoes=[], historia_familiar=[])
    r = client.post('/api/checkup-intelligent', json=dict(base, **dados))
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    return {x['titulo']: x for x in d['recommendations']}, {o['titulo']: o for o in d.get('orientacoes', [])}


def _rodar(comorbidades=(), medicacoes=(), idade=50, sexo='masculino', familia=(), **extra):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, list(comorbidades), list(medicacoes), list(familia), **extra)
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


UACR = 'Relação albumina/creatinina urinária (uACR)'
HEMOGRAMA = 'Hemograma completo com plaquetas'


# --- D-01 / M-03: doença renal crônica ------------------------------------------------------------

def test_drc_isolada_pede_uacr_e_tfg_pelo_menos_anuais(client):
    recs, orient = _resposta(client, idade=55, sexo='feminino', comorbidades=['doenca_renal'])
    assert UACR in recs and 'Doença renal crônica | Anual' in recs[UACR]['subtitulo']
    assert 'Doença renal crônica | Anual' in recs['Creatinina, soro']['subtitulo']
    assert 'KDIGO 2024 (DRC)' in recs[UACR]['referencia']
    assert 'Doença renal crônica: informe o estágio' in orient
    # sem o estágio, nada de G3a em diante
    assert 'Paratormônio (PTH), soro' not in recs


@pytest.mark.parametrize('detalhes, frequencia', [
    (['drc_g1_g2', 'drc_a1'], 'Anual'), (['drc_g1_g2', 'drc_a3'], 'A cada 6 meses'), (['drc_g3a', 'drc_a1'], 'Anual'),
    (['drc_g3a', 'drc_a2'], 'A cada 6 meses'), (['drc_g3a', 'drc_a3'], 'A cada 4 meses'), (['drc_g3b', 'drc_a1'], 'A cada 6 meses'),
    (['drc_g4', 'drc_a2'], 'A cada 4 meses'), (['drc_g4', 'drc_a3'], 'A cada 3 meses'), (['drc_g5'], 'A cada 3 meses')])
def test_drc_segue_o_mapa_g_x_a_do_kdigo(detalhes, frequencia):
    recs, _ = _rodar(['doenca_renal'] + detalhes)
    assert recs[UACR]['subtitulo'].endswith(frequencia), recs[UACR]['subtitulo']
    assert recs['Creatinina, soro']['subtitulo'].endswith(frequencia)


@pytest.mark.parametrize('tfg, estagio', [(60, 'G1-G2'), (59.9, 'G3a'), (45, 'G3a'), (44, 'G3b'), (30, 'G3b'),
                                          (29, 'G4'), (15, 'G4'), (14, 'G5')])
def test_estagio_g_pela_tfg_nos_limites(tfg, estagio):
    assert condicoes.estagio_drc({'doenca_renal'}, tfg) == (estagio, None)


def test_estagio_usa_o_pior_entre_tfg_e_detalhe():
    assert condicoes.estagio_drc({'doenca_renal', 'drc_g4', 'drc_a2'}, 50) == ('G4', 'A2')
    assert condicoes.estagio_drc({'doenca_renal', 'drc_g3a'}, 20) == ('G4', None)


def test_drc_g3a_pede_anemia_mineral_osseo_potassio_e_bicarbonato(client):
    # creatinina 1,6 numa mulher de 55 anos: TFG de cerca de 37 (G3b)
    recs, _ = _resposta(client, idade=55, sexo='feminino', comorbidades=['doenca_renal'], creatinina='1.6')
    for titulo in (HEMOGRAMA, 'Cálcio iônico, soro', 'Fósforo, soro', 'Paratormônio (PTH), soro', 'Fosfatase alcalina, soro',
                   '25-hidroxivitamina D, soro', 'Potássio, soro', 'Reserva alcalina (bicarbonato)'):
        assert titulo in recs and 'G3b' in recs[titulo]['subtitulo'], titulo
    assert recs['Cálcio iônico, soro']['subtitulo'].endswith('A cada 6-12 meses')
    assert recs[HEMOGRAMA]['subtitulo'].endswith('Anual')


def test_drc_g4_aumenta_as_frequencias_e_encaminha():
    recs, orient = _rodar(['doenca_renal', 'drc_g4'])
    assert recs['Cálcio iônico, soro']['subtitulo'].endswith('A cada 3-6 meses')
    assert recs['Paratormônio (PTH), soro']['subtitulo'].endswith('A cada 6-12 meses')
    assert recs[HEMOGRAMA]['subtitulo'].endswith('A cada 6 meses')
    assert 'Doença renal crônica: encaminhar ao nefrologista' in orient


def test_drc_g1_g2_nao_pede_exames_de_g3():
    recs, orient = _rodar(['doenca_renal', 'drc_g1_g2', 'drc_a2'])
    assert not {'Paratormônio (PTH), soro', 'Reserva alcalina (bicarbonato)', HEMOGRAMA} & set(recs)
    assert 'Doença renal crônica: encaminhar ao nefrologista' not in orient


def test_tfg_baixa_inferida_marca_drc_e_pede_uacr(client):
    recs, _ = _resposta(client, idade=50, creatinina='1.6')   # TFG < 60: coerencia marca doenca_renal
    assert UACR in recs and 'G3' in recs[UACR]['subtitulo']


def test_detalhes_da_drc_e_da_osteoporose_estao_na_tela(client):
    pagina = client.get('/intelligent-tools').get_data(as_text=True)
    for chave in ('doenca_renal', 'osteoporose'):
        assert f'data-comorbidade="{chave}"' in pagina
    assert 'value="drc_g3b"' in pagina and 'value="osteoporose_diagnostico"' in pagina


# --- D-02 e D-12: insuficiência cardíaca e antagonista mineralocorticoide --------------------------

def test_ic_pede_ferro_hemograma_peptideo_e_tsh(client):
    recs, _ = _resposta(client, idade=65, comorbidades=['insuficiencia_cardiaca'])
    for titulo in (HEMOGRAMA, 'Ferritina, soro', 'Índice de saturação de transferrina, soro'):
        assert recs[titulo]['subtitulo'] == 'Insuficiência cardíaca | Anual', titulo
        assert 'ESC 2021 (insuficiência cardíaca)' in recs[titulo]['referencia']
    assert recs['Peptídeo natriurético BNP/PROBNP']['subtitulo'] == 'Insuficiência cardíaca | Avaliação inicial'
    assert 'Insuficiência cardíaca | Avaliação inicial' in recs['Hormônio Tireoestimulante (TSH), soro']['subtitulo']


def test_sem_ic_nao_pede_perfil_de_ferro(client):
    recs, _ = _resposta(client, idade=65)
    assert 'Ferritina, soro' not in recs and 'Peptídeo natriurético BNP/PROBNP' not in recs


def test_arm_ou_arni_na_ic_pede_potassio_a_cada_3_4_meses():
    recs, _ = _rodar(['insuficiencia_cardiaca'], ['arni', 'espironolactona', 'diuretico_alca'])
    k = recs['Potássio, soro']['subtitulo']
    assert 'Insuficiência cardíaca em uso de sacubitril/valsartana, Espironolactona / eplerenona | A cada 3-4 meses' in k
    assert 'Em uso de Diurético de alça | Anual' in k
    assert periodicidade.intervalo(k) == {'tipo': 'intervalo', 'unidade': 'meses', 'n': 3, 'texto': 'A cada 3-4 meses'}


def test_arni_sem_ic_segue_anual_com_controle_precoce():
    recs, _ = _rodar([], ['arni'])
    assert recs['Potássio, soro']['subtitulo'] == 'Em uso de sacubitril/valsartana | Anual'
    assert '2-4 semanas após iniciar ou ajustar' in recs['Potássio, soro']['descricao']   # D-34


def test_espironolactona_na_has_tambem_a_cada_3_4_meses():
    recs, _ = _rodar(['hipertensao'], ['espironolactona', 'tiazidico'])
    assert 'Em uso de Espironolactona / eplerenona | A cada 3-4 meses' in recs['Creatinina, soro']['subtitulo']


# --- D-03 clozapina, D-04 PrEP, D-05 ocrelizumabe e natalizumabe, D-06 tenofovir ------------------

def test_clozapina_pede_hemograma_frequente_e_orienta_miocardite(client):
    recs, orient = _resposta(client, idade=30, sexo='feminino', medicacoes=['clozapina'])
    assert recs[HEMOGRAMA]['subtitulo'] == 'Em uso de clozapina | A cada 1-4 semanas'
    assert recs[HEMOGRAMA]['prioridade'] == 'alta'
    assert 'dias 7, 14, 21 e 28' in orient['Clozapina: neutrófilos e miocardite']['descricao']
    # outro antipsicótico atípico não pede hemograma
    recs, _ = _resposta(client, idade=30, sexo='feminino', medicacoes=['quetiapina'])
    assert HEMOGRAMA not in recs


def test_prep_pede_hiv_a_cada_120_dias_e_o_seguimento_do_pcdt(client):
    recs, _ = _resposta(client, idade=35, medicacoes=['tenofovir_entricitabina'])
    assert recs['Anti-HIV 1 e 2, soro']['subtitulo'] == 'PrEP | A cada 4 meses'
    assert recs['Sífilis: teste treponêmico ou VDRL, soro']['subtitulo'] == 'PrEP | A cada 4 meses'
    assert recs['Anticorpos anti-HCV, soro']['subtitulo'] == 'PrEP | A cada 4 meses'
    assert recs['Antígeno HBs, soro']['subtitulo'] == 'PrEP | Anual'
    assert recs['Clamídia e gonococo, PCR (urina ou swab)']['subtitulo'] == 'PrEP | A cada 6 meses'
    assert 'PrEP | A cada 6 meses' in recs['Creatinina, soro']['subtitulo']   # sem ClCr calculado: semestral
    assert 'Beta-hCG, soro' not in recs


def test_prep_creatinina_anual_so_abaixo_de_50_sem_comorbidade_e_clcr_90():
    jovem, _ = _rodar(medicacoes=['prep'], idade=35, creatinina='0.9', peso='80')   # ClCr por volta de 130
    assert jovem['Creatinina, soro']['subtitulo'] == 'PrEP | Anual'
    limite, _ = _rodar(medicacoes=['prep'], idade=50, creatinina='0.9', peso='80')
    assert limite['Creatinina, soro']['subtitulo'] == 'PrEP | A cada 6 meses'
    hipertenso, _ = _rodar(['hipertensao'], ['prep'], idade=35, creatinina='0.9', peso='80', hipertensao=True)
    assert hipertenso['Creatinina, soro']['subtitulo'] == 'PrEP | A cada 6 meses'
    mulher, _ = _rodar(medicacoes=['prep'], idade=30, sexo='feminino')
    assert mulher['Beta-hCG, soro']['subtitulo'] == 'PrEP | A cada 4 meses'


def test_tenofovir_com_hiv_nao_e_prep(client):
    recs, _ = _resposta(client, idade=40, comorbidades=['hiv'], cd4=600, em_tarv='sim', supressao_viral='sim',
                        medicacoes=['tenofovir_entricitabina', 'dolutegravir'])
    assert 'Anti-HIV 1 e 2, soro' not in recs
    assert 'PrEP' not in recs['Sífilis: teste treponêmico ou VDRL, soro']['subtitulo']


def test_regra_do_tenofovir_dispara_pela_classe_do_principio_ativo(client):
    recs, _ = _resposta(client, idade=40, comorbidades=['hiv'], cd4=600, em_tarv='sim', supressao_viral='sim',
                        medicacoes=['tenofovir_lamivudina_dolutegravir'])
    eas = recs['EAS - Elementos Anormais e Sedimentoscopia, urina']
    assert eas['subtitulo'].endswith('A cada 3-6 meses') and 'tenofovir' in eas['subtitulo']
    # sem tenofovir, anual
    recs, _ = _resposta(client, idade=40, comorbidades=['hiv'], cd4=600, em_tarv='sim', supressao_viral='sim',
                        medicacoes=['dolutegravir', 'darunavir_ritonavir'])
    assert recs['EAS - Elementos Anormais e Sedimentoscopia, urina']['subtitulo'].endswith('Anual')


def test_risco_renal_do_hiv_inclui_dm1_e_has_por_medicacao(client):
    recs, _ = _resposta(client, idade=40, comorbidades=['hiv', 'diabetes_tipo_1'], cd4=600, em_tarv='sim',
                        supressao_viral='sim', medicacoes=['dolutegravir'])
    assert recs['EAS - Elementos Anormais e Sedimentoscopia, urina']['subtitulo'].endswith('A cada 3-6 meses')


def test_taf_avisa_da_divergencia(client):
    _, orient = _resposta(client, idade=40, comorbidades=['hiv'], cd4=600,
                          medicacoes=['bictegravir_entricitabina_tenofovir_alafenamida'])
    assert 'Tenofovir alafenamida: intervalo da função renal' in orient
    _, orient = _resposta(client, idade=40, comorbidades=['hiv'], cd4=600, medicacoes=['tenofovir_lamivudina_dolutegravir'])
    assert 'Tenofovir alafenamida: intervalo da função renal' not in orient


def test_hiv_recomendar_com_tenofovir():
    recs, _ = hiv.recomendar(40, 'masculino', cd4=600, carga_viral=0, em_tarv=True, supressao_viral=True, gestante=False,
                             tenofovir=True, risco_renal=False)
    creat = next(r for r in recs if r['titulo'] == 'Creatinina, soro')
    assert creat['subtitulo'].endswith('A cada 3-6 meses')


def test_ocrelizumabe_rastreia_hbv_e_pede_igg(client):
    recs, _ = _resposta(client, idade=35, sexo='feminino', imunossupressao='sim', medicacoes=['ocrelizumabe'])
    for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro', 'Anticorpos anti-HCV, soro',
                   'Prova tuberculínica (PPD) ou IGRA'):
        assert titulo in recs, titulo
    assert recs['Imunoglobulina G (IgG), soro']['subtitulo'] == 'Em uso de ocrelizumabe | Antes de cada ciclo'


def test_natalizumabe_pede_anti_jcv_semestral_e_fingolimode_tem_monitorizacao(client):
    recs, _ = _resposta(client, idade=35, sexo='feminino', imunossupressao='sim', medicacoes=['natalizumabe', 'fingolimode'])
    assert recs['Anticorpo anti-JCV (vírus JC), soro']['subtitulo'] == 'Em uso de natalizumabe | A cada 6 meses'
    assert 'Antígeno HBs, soro' in recs
    assert 'Em uso de fingolimode | Antes do tratamento' in recs['Eletrocardiograma de repouso']['subtitulo']
    assert recs['Avaliação oftalmológica (fundo de olho)']['subtitulo'] == 'Em uso de fingolimode | 3-4 meses após o início'
    assert 'Varicela, IgG' in recs


# --- D-09, D-10 e M-08: cálcio, vitamina D e fósforo no diabetes ---------------------------------

@pytest.mark.parametrize('comorbidades', [['diabetes'], ['diabetes_tipo_1']])
def test_diabetico_comum_nao_recebe_calcio_vitamina_d_nem_fosforo(client, comorbidades):
    recs, _ = _resposta(client, idade=40, comorbidades=comorbidades)
    assert not {'Cálcio iônico, soro', '25-hidroxivitamina D, soro', 'Fósforo, soro'} & set(recs)


def test_diabetico_com_drc_g3_ou_bariatrica_recebe_pelo_modulo_proprio(client):
    recs, _ = _resposta(client, idade=60, comorbidades=['diabetes', 'doenca_renal', 'drc_g3a'])
    assert 'G3a' in recs['25-hidroxivitamina D, soro']['subtitulo'] and 'G3a' in recs['Fósforo, soro']['subtitulo']
    recs, _ = _resposta(client, idade=60, comorbidades=['diabetes', 'cirurgia_bariatrica'])
    assert recs['25-hidroxivitamina D, soro']['subtitulo'].startswith('Cirurgia bariátrica')


# --- D-11: lipídios --------------------------------------------------------------------------------

@pytest.mark.parametrize('dados, grupo', [
    (dict(comorbidades=['diabetes'], medicacoes=['atorvastatina'], idade=60), 'Dislipidemia ou tratamento hipolipemiante'),
    (dict(comorbidades=['dislipidemia'], medicacoes=['rosuvastatina']), 'Dislipidemia ou tratamento hipolipemiante'),
    (dict(comorbidades=['dcv_aterosclerotica'], medicacoes=['atorvastatina', 'clopidogrel'], idade=58), 'DCV aterosclerótica'),
    (dict(medicacoes=['ezetimiba']), 'Dislipidemia ou tratamento hipolipemiante')])
def test_lipidios_em_tratamento_ou_com_dcv_a_cada_3_12_meses(client, dados, grupo):
    recs, _ = _resposta(client, **dados)
    lip = recs['Colesterol total e frações, soro']
    assert lip['subtitulo'].startswith(f'{grupo} | A cada 3-12 meses') and '4-6 anos' not in lip['subtitulo']
    assert 'ACC/AHA 2018 (colesterol)' in lip['referencia']


def test_dcv_traz_a_meta_de_ldl_da_sbc():
    recs, _ = _rodar(['dcv_aterosclerotica'])
    assert 'LDL-c < 50 mg/dL' in recs['Colesterol total e frações, soro']['descricao']


def test_lipidios_no_diabetes_sem_estatina_pela_idade(client):
    recs, _ = _resposta(client, idade=40, comorbidades=['diabetes'])
    assert recs['Colesterol total e frações, soro']['subtitulo'] == 'Diabéticos | Anual'
    recs, _ = _resposta(client, idade=39, comorbidades=['diabetes'])
    assert recs['Colesterol total e frações, soro']['subtitulo'].endswith('A cada 5 anos')


def test_lipidios_sem_indicacao_continuam_no_rastreio(client):
    recs, _ = _resposta(client, idade=50)
    assert recs['Colesterol total e frações, soro']['subtitulo'] == 'Adultos ≥40 anos | A cada 4-6 anos'


def test_lipidios_do_hiv_ficam_somados_a_regra_de_tratamento():
    recs = [{'titulo': 'Colesterol total e frações, soro', 'subtitulo': 'PVHA | Anual', 'referencia': 'MS 2024 (PCDT HIV)',
             'prioridade': 'media', 'descricao': 'x'}]
    condicoes.aplicar(recs, 50, 'masculino', [], ['estatina'], [])
    assert recs[0]['subtitulo'].startswith('PVHA | Anual | Também: Dislipidemia ou tratamento hipolipemiante')


def test_diabetes_com_estatina_avisa_da_divergencia_ada():
    _, orient = _rodar(['diabetes'], ['estatina'])
    assert 'Perfil lipídico no diabetes em uso de estatina: diretrizes divergem' in orient
    _, orient = _rodar(['dislipidemia'], ['estatina'])
    assert 'Perfil lipídico no diabetes em uso de estatina: diretrizes divergem' not in orient


# --- D-13, D-30 e Dúvida 1: hipertensão ------------------------------------------------------------

def test_has_ganha_os_exames_basicos_da_avaliacao_inicial(client):
    recs, orient = _resposta(client, idade=40, comorbidades=['hipertensao'])
    for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Cálcio iônico, soro', 'Sódio, soro', HEMOGRAMA):
        assert 'Adultos com HAS | Avaliação inicial' in recs[titulo]['subtitulo'], titulo
    assert recs['Ácido úrico, soro']['subtitulo'] == 'Adultos com HAS | Avaliação inicial'
    assert recs['EAS - Elementos Anormais e Sedimentoscopia']['subtitulo'] == 'Adultos com HAS | Avaliação inicial'
    assert 'Ácido úrico na hipertensão: diretrizes divergem' in orient
    assert 'Hiperaldosteronismo primário: diretrizes divergem' in orient


def test_sem_has_nao_ha_exames_da_has():
    recs, orient = _rodar([], hipertensao=False)
    assert not recs and 'Hiperaldosteronismo primário: diretrizes divergem' not in orient


def test_has_com_apneia_rastreia_hiperaldosteronismo_e_resistente_nao_repete_polissonografia(client):
    recs, _ = _resposta(client, idade=45, comorbidades=['hipertensao', 'apneia_sono'])
    assert recs['Relação Aldosterona/Renina (A/R)']['subtitulo'] == 'HAS com apneia do sono | Avaliação inicial'
    recs, _ = _resposta(client, idade=45, comorbidades=['hipertensao'])
    assert 'Relação Aldosterona/Renina (A/R)' not in recs
    recs, _ = _resposta(client, idade=52, comorbidades=['has_resistente', 'apneia_sono'])
    assert 'Polissonografia' not in recs and 'Relação Aldosterona/Renina (A/R)' in recs
    recs, _ = _resposta(client, idade=52, comorbidades=['has_resistente'])
    assert 'Polissonografia' in recs


# --- D-14: corticoide (dose baixa e curta) — ver também tests/test_doses.py ------------------------

def test_corticoide_nao_pede_mapa():
    recs, orient = _rodar([], ['corticoide_sistemico', 'corticoide_cronico'])
    assert 'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)' not in recs
    assert 'Corticoide sistêmico: pressão arterial' in orient
    assert 'Vitamina D no corticoide crônico: diretrizes divergem' in orient


# --- D-15 a D-21 e D-31 a D-35: outras medicações -------------------------------------------------

def test_amiodarona_pede_rx_pft_t4_e_avisa_da_varfarina():
    recs, orient = _rodar([], ['amiodarona', 'varfarina'], idade=70)
    assert recs['Radiografia de tórax']['subtitulo'] == 'Em uso de amiodarona | Anual'
    assert recs['Prova de função pulmonar completa com difusão (DLCO)']['subtitulo'] == 'Em uso de amiodarona | Basal'
    assert recs['T4 livre, soro']['subtitulo'] == 'Em uso de amiodarona | A cada 6 meses'
    assert 'Amiodarona com varfarina' in orient
    _, orient = _rodar([], ['amiodarona'], idade=70)
    assert 'Amiodarona com varfarina' not in orient


def test_metotrexato_fase_inicial_sorologias_e_rx():
    recs, _ = _rodar(['artrite_reumatoide'], ['metotrexato'], idade=45, sexo='feminino')
    for titulo in (HEMOGRAMA, 'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Creatinina, soro', 'Albumina, soro'):
        assert recs[titulo]['subtitulo'] == 'Em uso de metotrexato | A cada 2-12 semanas', titulo
        assert recs[titulo]['referencia'] == 'BSR 2017'
    for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro', 'Anticorpos anti-HCV, soro'):
        assert recs[titulo]['subtitulo'] == 'Em uso de metotrexato | Avaliação inicial'
    assert recs['Radiografia de tórax']['subtitulo'] == 'Em uso de metotrexato | Avaliação inicial'


def test_azatioprina_pede_tpmt_e_tem_codigo_ou_motivo():
    recs, _ = _rodar(['lupus'], ['azatioprina'], sexo='feminino')
    tpmt = 'Atividade da TPMT ou genotipagem TPMT/NUDT15'
    assert recs[tpmt]['subtitulo'] == 'Em uso de azatioprina | Antes do tratamento' and 'CPIC 2018' in recs[tpmt]['referencia']
    assert tpmt in tuss.SEM_CODIGO and 'Anticorpo anti-JCV (vírus JC), soro' in tuss.SEM_CODIGO
    assert tpmt not in _rodar([], ['metotrexato'])[0]


def test_sulfassalazina_e_mesalazina():
    recs, _ = _rodar(['retocolite'], ['sulfassalazina', 'aminossalicilato'])
    assert recs[HEMOGRAMA]['subtitulo'].startswith('Em uso de sulfassalazina | A cada 2-12 semanas')
    assert 'Em uso de mesalazina | Anual' in recs['Creatinina, soro']['subtitulo']


@pytest.mark.parametrize('sexo, idade, aviso', [('feminino', 45, True), ('feminino', 55, True), ('feminino', 56, False),
                                                ('masculino', 30, False)])
def test_valproato_em_mulher_que_pode_engravidar(sexo, idade, aviso):
    _, orient = _rodar([], ['valproato', 'carbamazepina'], idade=idade, sexo=sexo)
    assert ('Valproato em mulher que pode engravidar' in orient) == aviso
    assert ('Anticonvulsivante indutor enzimático e contracepção' in orient) == aviso


def test_micofenolato_e_inibidor_de_mtor():
    recs, _ = _rodar(['transplante'], ['micofenolato', 'inibidor_mtor'])
    assert recs[HEMOGRAMA]['subtitulo'] == 'Em uso de micofenolato | A cada 1-4 semanas'
    assert 'Sirolimo ou everolimo, sangue total (nível de vale)' in recs
    assert recs['Relação proteína/creatinina, urina']['subtitulo'] == 'Em uso de sirolimo ou everolimo | Periódico'
    assert 'Sirolimo ou everolimo, sangue total (nível de vale)' not in _rodar([], ['inibidor_mtor'])[0]


@pytest.mark.parametrize('idade, familia, psa', [(55, [], True), (69, [], True), (70, [], False), (54, [], False),
                                                 (45, ['cancer_prostata'], True), (39, ['cancer_prostata'], False)])
def test_testosterona_hematocrito_e_psa(idade, familia, psa):
    recs, _ = _rodar([], ['testosterona'], idade=idade, familia=familia)
    assert recs[HEMOGRAMA]['subtitulo'] == 'Em uso de testosterona | Anual'
    assert ('PSA total, soro' in recs) == psa
    assert not _rodar([], ['testosterona'], sexo='feminino')[0]


def test_metimazol_t4_livre_e_cuidados_e_hipertireoidismo_sem_droga_pede_basais():
    recs, orient = _rodar(['hipertireoidismo'], ['antitireoidiano'], sexo='feminino')
    assert recs['T4 livre, soro']['subtitulo'] == 'Hipertireoidismo / antitireoidiano | A cada 4-8 semanas'
    assert 'Antitireoidiano: agranulocitose e hepatotoxicidade' in orient and HEMOGRAMA not in recs
    recs, _ = _rodar(['hipertireoidismo'], sexo='feminino')
    assert recs[HEMOGRAMA]['subtitulo'] == 'Hipertireoidismo | Antes do tratamento'


def test_alopurinol_zoledronico_denosumabe_e_sotalol():
    recs, orient = _rodar([], ['alopurinol', 'zoledronico', 'denosumabe', 'sotalol'], idade=70, sexo='feminino')
    assert 'Alopurinol: HLA-B*58:01' in orient
    assert 'Em uso de ácido zoledrônico | Antes de cada dose' in recs['Creatinina, soro']['subtitulo']
    assert 'Em uso de denosumabe | Antes de cada dose' in recs['Cálcio iônico, soro']['subtitulo']
    assert recs['Eletrocardiograma de repouso']['subtitulo'] == 'Em uso de sotalol | No início e a cada ajuste de dose'


# --- D-22, D-23, D-24, D-36: diabetes e obesidade --------------------------------------------------

def test_fib4_no_dm2_e_no_pre_diabetes_mas_nao_no_dm1_sem_fator(client):
    recs, orient = _resposta(client, idade=60, comorbidades=['diabetes'])
    assert recs['Alanina aminotransferase, soro']['subtitulo'] == 'Diabetes tipo 2 ou pré-diabetes | FIB-4 a cada 1-2 anos'
    assert 'Diabetes: exame dos pés' in orient
    recs, _ = _resposta(client, idade=30, sexo='feminino', comorbidades=['diabetes_tipo_1'])
    assert 'Alanina aminotransferase, soro' not in recs
    assert recs['Anticorpo antitransglutaminase tecidual IgA, soro']['subtitulo'] == 'Diabetes tipo 1 | Avaliação inicial'
    assert 'Imunoglobulina A (IgA), soro' in recs
    recs, _ = _resposta(client, idade=30, sexo='feminino', comorbidades=['diabetes_tipo_1', 'obesidade'])
    assert recs['Alanina aminotransferase, soro']['subtitulo'].startswith('Diabetes tipo 1 com obesidade ou MASLD')
    recs, _ = _rodar(['pre_diabetes'])
    assert 'FIB-4 a cada 1-2 anos' in recs['Alanina aminotransferase, soro']['subtitulo']


def test_obesidade_com_fator_metabolico_pede_fib4():
    sem, _ = _rodar(['obesidade'], idade=38, sexo='feminino')
    assert 'Alanina aminotransferase, soro' not in sem
    com, _ = _rodar(['obesidade', 'dislipidemia'], idade=38, sexo='feminino')
    assert com['Alanina aminotransferase, soro']['subtitulo'] == 'Obesidade com fator de risco metabólico | FIB-4 a cada 1-2 anos'
    pelo_imc, _ = _rodar([], idade=38, sexo='feminino', imc=31, hipertensao=True)
    assert 'Alanina aminotransferase, soro' in pelo_imc
    limite, _ = _rodar([], idade=38, sexo='feminino', imc=29.9, hipertensao=True)
    assert 'Alanina aminotransferase, soro' not in limite


def test_fundo_de_olho_a_cada_1_2_anos_e_referencias_atuais(client):
    recs, _ = _resposta(client, idade=60, comorbidades=['diabetes'], medicacoes=['metformina'])
    assert recs['Fundoscopia (Exame de fundo de olho)']['subtitulo'] == 'Diabéticos | A cada 1-2 anos'
    assert recs['Fundoscopia (Exame de fundo de olho)']['referencia'] == 'ADA 2026 (seção 12)'
    assert recs['Vitamina B12, soro']['referencia'] == 'ADA 2026 (seção 9)'
    assert 'infecções' not in recs[HEMOGRAMA]['descricao']
    # nenhuma referência com HTML gravado (D-28)
    assert not any('<a ' in (r.get('referencia') or '') for r in recs.values())


# --- D-25 DPOC, D-26 DOAC, D-37 osteoporose --------------------------------------------------------

def test_dpoc_pede_alfa1_e_tira_eletrolitos(client):
    recs, _ = _resposta(client, idade=62, comorbidades=['dpoc'])
    assert recs['Alfa-1 antitripsina, soro']['subtitulo'] == 'DPOC | Uma vez'
    assert recs['Gasometria arterial, sangue arterial']['prioridade'] == 'media'
    assert not {'Sódio, soro', 'Potássio, soro', 'Cloreto, soro', 'Hemograma completo, sangue total'} & set(recs)
    assert 'eosinófilos' in recs[HEMOGRAMA]['descricao'].lower() and recs[HEMOGRAMA]['referencia'] == 'GOLD 2026'


@pytest.mark.parametrize('idade, creatinina, peso, renal', [
    (60, None, None, 'Anual'), (75, None, None, 'A cada 6 meses'), (74, None, None, 'Anual'),
    (82, '1.4', '50', 'A cada 2 meses'),   # ClCr ~25 mL/min (Cockcroft-Gault, mulher)
    (60, '1.3', '60', 'A cada 4 meses')])  # ClCr ~44
def test_doac_frequencia_da_funcao_renal(idade, creatinina, peso, renal):
    recs, _ = _rodar(['fibrilacao_atrial'], ['doac'], idade=idade, sexo='feminino', creatinina=creatinina, peso=peso)
    assert f'Em uso de anticoagulante oral direto | {renal}' in recs['Creatinina, soro']['subtitulo']
    assert 'Alanina aminotransferase, soro' in recs


def test_osteoporose_em_tratamento_nao_repete_causas_secundarias():
    recs, orient = _rodar(['osteoporose'], ['antiosteoporose'], idade=68, sexo='feminino')
    assert 'Paratormônio (PTH), soro' not in recs and 'Osteoporose: causas secundárias' in orient
    recs, _ = _rodar(['osteoporose', 'osteoporose_diagnostico'], idade=68, sexo='feminino')
    assert recs['Paratormônio (PTH), soro']['subtitulo'] == 'Osteoporose | Avaliação inicial'


# --- Fontes ---------------------------------------------------------------------------------------

def test_toda_fonte_nova_tem_link():
    novas = ('KDIGO_DRC', 'KDIGO_DMO', 'KDIGO_ANEMIA', 'ESC_IC', 'ESC_IC_2023', 'ACC_AHA_COLESTEROL', 'SBC_DISLIPIDEMIA',
             'ADA_FIGADO', 'ADA_LIPIDIOS', 'ADA_PES', 'ADA_METFORMINA', 'AASLD_MASLD', 'FDA_CLOZAPINA', 'ANVISA_CLOZAPINA',
             'RONALDSON', 'PCDT_PREP', 'FDA_OCRELIZUMABE', 'EMA_NATALIZUMABE', 'EMA_FINGOLIMODE', 'EMA_MICOFENOLATO',
             'EMA_SIROLIMO', 'EMA_ZOLEDRONICO', 'EMA_DENOSUMABE', 'EMA_VALPROATO', 'ENDO_TESTOSTERONA', 'ENDO_VITAMINA_D',
             'ENDO_PA_2016', 'ENDO_PA_2025', 'ACC_AHA_HAS_2017', 'ACR_GIOP', 'BSR', 'CPIC_TIOPURINA', 'BSG_2019', 'AHA_FA_2023',
             'ATA_HIPERTIREOIDISMO', 'GINA')
    rotulos = [getattr(condicoes, k) for k in novas] + [
        'GOLD 2026', 'ADA 2026 (seção 6)', 'ADA 2026 (seção 11)', 'MS 2024 (PCDT HIV) / HIVMA/IDSA 2024']
    for rotulo in rotulos:
        for link in build_reference_links('Exame', rotulo):
            assert link['url'].startswith('http'), rotulo
    assert build_reference_links('x', 'KDIGO 2024 (DRC)')[0]['url'].endswith('KDIGO-2024-CKD-Guideline.pdf')
    assert build_reference_links('x', 'ESC 2021 (insuficiência cardíaca)')[0]['url'] == 'https://doi.org/10.1093/eurheartj/ehab368'


# --- Revisão externa (16/11/2026) -----------------------------------------------------------------

US = 'Ultrassonografia de abdome superior'


@pytest.mark.parametrize('sexo, idade, vigilancia', [('masculino', 18, True), ('masculino', 17, False), ('feminino', 40, True),
                                                     ('feminino', 39, False)])
def test_hbv_com_hiv_vigilancia_de_chc_sem_cirrose(sexo, idade, vigilancia):
    """AASLD/IDSA 2025, recomendação 8 (condicional): homens a partir de 18 anos e mulheres a partir de 40."""
    recs, _ = _rodar(['hepatite_b_cronica', 'hiv'], idade=idade, sexo=sexo)
    assert (US in recs) == vigilancia
    if vigilancia:
        assert recs[US]['subtitulo'] == 'Hepatite B com HIV | A cada 6 meses'
    assert US not in _rodar(['hepatite_b_cronica'], idade=idade, sexo=sexo)[0]


def test_anti_hdv_para_todo_hbsag_reagente():
    recs, _ = _rodar(['hepatite_b_cronica'])
    assert recs['Hepatite delta, anticorpo IgG']['referencia'] == 'OMS 2024 (hepatite B)'


@pytest.mark.parametrize('idade, trecho', [(65, 'abaixo de 2,0'), (64, 'abaixo de 1,3'), (35, 'abaixo de 1,3'),
                                           (34, 'pouco confiável')])
def test_fib4_interpretado_pela_idade(idade, trecho):
    recs, _ = _rodar(['masld'], idade=idade)
    assert trecho in recs['Alanina aminotransferase, soro']['descricao']


def test_hidroxicloroquina_pela_aao_2025():
    _, orient = _rodar([], ['hidroxicloroquina'])
    texto = orient['Hidroxicloroquina']['descricao']
    assert 'autofluorescência' in texto and 'peso real' in texto and 'desde o início' not in texto
    assert orient['Hidroxicloroquina']['referencia'] == 'AAO 2025 (hidroxicloroquina)'
    for extra in (dict(comorbidades=['doenca_renal']), dict(medicacoes=['hidroxicloroquina', 'tamoxifeno'])):
        _, orient = _rodar(extra.get('comorbidades', []), extra.get('medicacoes', ['hidroxicloroquina']))
        assert 'rastreio anual desde o início' in orient['Hidroxicloroquina']['descricao']


def test_dm1_orienta_inicio_da_uacr_e_dm2_nao():
    assert 'Diabetes tipo 1: quando começar a uACR' in _rodar(['diabetes_tipo_1'])[1]
    assert 'Diabetes tipo 1: quando começar a uACR' not in _rodar(['diabetes'])[1]


@pytest.mark.parametrize('idade, tabagismo, familia, endoscopia', [
    (55, 'nunca', ['barrett_esofago'], True),    # homem + > 50 + familiar
    (45, 'nunca', ['barrett_esofago'], False),   # homem + familiar
    (55, 'nunca', [], False)])                   # homem + > 50
def test_barrett_conta_o_familiar_de_1o_grau(idade, tabagismo, familia, endoscopia):
    recs, orient = _rodar(['drge'], idade=idade, tabagismo=tabagismo, familia=familia, imc=24)
    assert ('Endoscopia digestiva alta' in recs) == endoscopia
    if not endoscopia:
        assert 'raça branca' in orient['Refluxo: rastreio de esôfago de Barrett']['descricao']


def test_aldosterona_renina_pela_endocrine_society_2025(client):
    recs, _ = _resposta(client, idade=52, comorbidades=['has_resistente'])
    texto = recs['Relação Aldosterona/Renina (A/R)']['descricao']
    assert 'sentado' in texto and 'método do laboratório' in texto and '2 horas em pé' not in texto


def test_nefrite_lupica_complemento_em_cada_consulta():
    recs, _ = _rodar(['lupus', 'les_nefrite'], sexo='feminino')
    assert recs['Complemento C3']['subtitulo'] == 'Nefrite lúpica | Em cada consulta, no máximo mensal'
    assert recs['Anti-DNA']['referencia'] == 'ACR 2024 (nefrite lúpica)'
    recs, _ = _rodar(['lupus'], sexo='feminino')
    assert recs['Complemento C3']['subtitulo'].endswith('Conforme indicação clínica')


def test_antitireoidiano_pede_t4_livre_com_o_tsh():
    recs, _ = _rodar([], ['antitireoidiano'], sexo='feminino')
    assert recs['T4 livre, soro']['subtitulo'] == recs['Hormônio Tireoestimulante (TSH), soro']['subtitulo']
    assert 'T3 total' in recs['T4 livre, soro']['descricao']
