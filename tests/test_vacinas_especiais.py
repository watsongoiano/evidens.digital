"""Vacinação em grupos especiais (auditoria C, 15/11/2026): HIV, DRC, diabetes, imunossupressão, câncer e gestação.

Cada regra tem caso positivo, negativo e limítrofe, com perfis fictícios. Fontes: SBIm 2026/2027 (adulto, idoso,
gestante), SBIm Pacientes Especiais 2026/2027, IN CNV 2026 (MS), Manual dos CRIE e CDC/ACIP 2025.
"""
import pytest

from src.utils import seguranca_vacinas as sv
from src.utils.validacao import NAO, SIM

PNEUMO = 'Pneumocócica conjugada 20-valente (Prevenar 20®)'
ZOSTER = 'Herpes Zóster (Shingrix®)'
VSR = 'VSR - Vírus Sincicial Respiratório (Arexvy® ou Abrysvo®)'
HPV = 'Gardasil 9® (Vacina HPV 9-Valente)'
HEP_AB = 'Hepatites A e B (Twinrix® ou vacinas isoladas)'
HEP_B = 'Hepatite B (Engerix-B® ou Euvax B®)'
ACWY = 'Meningocócica ACWY (Menactra® ou Menveo®)'
HIB = 'Haemophilus influenzae tipo b (Hib)'
COVID = 'COVID-19 (Comirnaty®, Spikevax® ou outras)'
INFLUENZA = 'Influenza (trivalente ou quadrivalente)'
ATENUADAS = ('Tríplice Viral', 'Varicela', 'Febre Amarela', 'Dengue')


def _consultar(client, **campos):
    corpo = {'tabagismo': 'nunca', 'imunossupressao': 'nao', 'comorbidades': [], 'medicacoes': [], **campos}
    if campos.get('sexo') == 'feminino':
        corpo.setdefault('gestante', 'nao')
        corpo.setdefault('lactante', 'nao')
    if corpo.get('gestante') == 'sim':
        corpo.setdefault('idade_gestacional', '30')
        corpo.setdefault('primeira_consulta', 'sim')
    resposta = client.post('/api/checkup-intelligent', json=corpo)
    assert resposta.status_code == 200, resposta.get_json()
    return resposta.get_json()


def _vacinas(dados):
    return {r['titulo']: r for r in dados['recommendations'] if r.get('categoria') == 'vacina'}


def _retiradas(dados):
    return {i['titulo'].split(' (')[0].split(' - ')[0]: i for i in dados['nao_incluidas'] if i.get('categoria') == 'vacina'}


def _orientacoes(dados):
    return {o['titulo']: o for o in dados['orientacoes']}


def _atenuadas_na_lista(dados):
    return [t for t in _vacinas(dados) if any(a in t for a in ATENUADAS)]


# --- C-01 / D-07: VPC20 antes dos 50 anos em HIV, DRC e diabetes ----------------------------------

@pytest.mark.parametrize('idade', [30, 49])
@pytest.mark.parametrize('com', [['hiv'], ['doenca_renal'], ['diabetes'], ['diabetes_tipo_1']])
def test_vpc20_em_qualquer_idade_com_hiv_drc_ou_diabetes(client, idade, com):
    dados = _consultar(client, idade=idade, sexo='masculino', comorbidades=com, cd4=500 if com == ['hiv'] else None)
    assert PNEUMO in _vacinas(dados)
    assert 'Comorbidade de risco' in _vacinas(dados)[PNEUMO]['subtitulo']


def test_vpc20_nao_entra_aos_30_sem_comorbidade_de_risco(client):
    assert PNEUMO not in _vacinas(_consultar(client, idade=30, sexo='masculino', comorbidades=['hipertensao']))


def test_vpc20_aos_50_vem_do_calendario_por_idade(client):
    assert 'A partir de 50 anos' in _vacinas(_consultar(client, idade=50, sexo='masculino', comorbidades=['diabetes']))[PNEUMO]['subtitulo']


# --- C-02 / D-08: zóster recombinante no HIV de 18 a 49 anos ---------------------------------------

@pytest.mark.parametrize('cd4', [150, 350, 900])
def test_zoster_recombinante_no_hiv_qualquer_cd4(client, cd4):
    dados = _consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], cd4=cd4)
    assert 'HIV' in _vacinas(dados)[ZOSTER]['subtitulo']


def test_zoster_recombinante_no_hiv_aos_18(client):
    assert ZOSTER in _vacinas(_consultar(client, idade=18, sexo='feminino', comorbidades=['hiv'], cd4=500))


def test_zoster_nao_entra_aos_35_sem_imunocomprometimento(client):
    assert ZOSTER not in _vacinas(_consultar(client, idade=35, sexo='masculino'))


def test_hiv_nao_marca_imunossupressao_na_triagem(client):
    """O HIV segue pela faixa de CD4: a triagem não vira "Sim" só pelo HIV."""
    dados = _consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], cd4=500)
    assert dados['triagem_vacinas']['imunossupressao'] == NAO
    assert all(i['estado'] == 'precaucao' for t, i in _retiradas(dados).items() if t != 'Gardasil 9®')


# --- C-03: corticoide sem dose ---------------------------------------------------------------------

def test_prednisona_sem_dose_retem_as_vivas(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['prednisona'])
    assert not _atenuadas_na_lista(dados)
    retiradas = _retiradas(dados)
    assert {'Tríplice Viral', 'Varicela', 'Febre Amarela', 'Dengue'} <= set(retiradas)
    assert all(retiradas[t]['estado'] == 'dados_insuficientes' for t in ('Tríplice Viral', 'Varicela', 'Febre Amarela', 'Dengue'))
    assert 'dose e duração' in retiradas['Febre Amarela']['motivo']


def test_prednisona_so_com_a_dose_ainda_retem_as_vivas(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['prednisona'], dose__prednisona='5')
    assert not _atenuadas_na_lista(dados)


def test_prednisona_em_dose_baixa_informada_libera_as_vivas(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['prednisona'], dose__prednisona='10', duracao__prednisona='1')
    assert len(_atenuadas_na_lista(dados)) == 4


def test_prednisona_no_limiar_imunossupressor_contraindica(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['prednisona'], dose__prednisona='20', duracao__prednisona='2')
    assert not _atenuadas_na_lista(dados)
    assert _retiradas(dados)['Varicela']['estado'] == 'contraindicada'


def test_chave_de_classe_antiga_de_corticoide_retem_as_vivas(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['corticoide_sistemico'])
    assert not _atenuadas_na_lista(dados)


# --- C-05: metotrexato e azatioprina em baixo grau -------------------------------------------------

def test_metotrexato_baixo_grau_poe_vivas_em_precaucao_e_contraindica_dengue(client):
    dados = _consultar(client, idade=35, sexo='feminino', medicacoes=['metotrexato'], dose__metotrexato='15', peso=70, altura=165)
    assert not _atenuadas_na_lista(dados)
    retiradas = _retiradas(dados)
    assert retiradas['Dengue']['estado'] == 'contraindicada'
    assert {retiradas[t]['estado'] for t in ('Tríplice Viral', 'Varicela', 'Febre Amarela')} == {'precaucao'}
    # As inativadas não mudam: sem VZR nem VPC20 só pelo baixo grau
    assert ZOSTER not in _vacinas(dados) and PNEUMO not in _vacinas(dados)


def test_metotrexato_no_limite_do_baixo_grau(client):
    """28 mg/semana com 70 kg (0,4 mg/kg): ainda baixo grau, precaução e não contraindicação."""
    dados = _consultar(client, idade=35, sexo='feminino', medicacoes=['metotrexato'], dose__metotrexato='28', peso=70, altura=165)
    assert _retiradas(dados)['Varicela']['estado'] == 'precaucao'


def test_metotrexato_acima_do_baixo_grau_contraindica(client):
    dados = _consultar(client, idade=35, sexo='feminino', medicacoes=['metotrexato'], dose__metotrexato='30', peso=70, altura=165)
    assert _retiradas(dados)['Varicela']['estado'] == 'contraindicada'


def test_azatioprina_baixo_grau_em_precaucao(client):
    dados = _consultar(client, idade=35, sexo='masculino', medicacoes=['azatioprina'], dose__azatioprina='150', peso=70, altura=175)
    retiradas = _retiradas(dados)
    assert retiradas['Febre Amarela']['estado'] == 'precaucao' and retiradas['Dengue']['estado'] == 'contraindicada'


# --- C-06: oncológicos sem a marca de imunossupressão ----------------------------------------------

@pytest.mark.parametrize('remedio', ['pembrolizumabe', 'trastuzumabe'])
def test_oncologico_retem_vivas_e_indica_vzr_e_vpc20(client, remedio):
    dados = _consultar(client, idade=45, sexo='feminino', medicacoes=[remedio])
    assert not _atenuadas_na_lista(dados)
    assert _retiradas(dados)['Varicela']['estado'] == 'precaucao'
    assert ZOSTER in _vacinas(dados) and PNEUMO in _vacinas(dados)


def test_bloqueio_hormonal_isolado_nao_e_oncologico(client):
    dados = _consultar(client, idade=45, sexo='masculino', medicacoes=['leuprorrelina'])
    assert len(_atenuadas_na_lista(dados)) == 4


# --- C-04: "Sim" só na triagem ---------------------------------------------------------------------

def test_imunossupressao_so_na_triagem_traz_as_inativadas(client):
    dados = _consultar(client, idade=40, sexo='masculino', imunossupressao='sim')
    v = _vacinas(dados)
    assert {ZOSTER, PNEUMO, VSR} <= set(v)
    assert '3 doses (0-2-6m)' in v[HPV]['subtitulo']
    assert 'Imunossupressão informada na triagem' in _orientacoes(dados)


def test_triagem_nao_sem_causa_nao_traz_as_inativadas(client):
    dados = _consultar(client, idade=40, sexo='masculino', imunossupressao='nao')
    assert not {ZOSTER, PNEUMO, VSR} & set(_vacinas(dados))
    assert 'Imunossupressão informada na triagem' not in _orientacoes(dados)


# --- C-08: hepatite B em dose dobrada --------------------------------------------------------------

@pytest.mark.parametrize('campos', [dict(comorbidades=['doenca_renal']), dict(comorbidades=['hiv'], cd4=500),
                                    dict(comorbidades=['transplante'])])
def test_hepatite_b_dobrada_na_drc_hiv_e_imunossupressao(client, campos):
    v = _vacinas(_consultar(client, idade=40, sexo='masculino', **campos))
    assert '4 doses dobradas' in v[HEP_AB]['subtitulo'] and 'anti-HBs' in v[HEP_AB]['descricao']


def test_hepatite_b_dobrada_em_60_mais_usa_o_cartao_de_hepatite_b(client):
    v = _vacinas(_consultar(client, idade=70, sexo='masculino', comorbidades=['doenca_renal']))
    assert '4 doses dobradas' in v[HEP_B]['subtitulo'] and HEP_AB not in v


def test_hepatite_b_de_rotina_sem_grupo_especial(client):
    assert '4 doses' not in _vacinas(_consultar(client, idade=40, sexo='masculino'))[HEP_AB]['descricao']


# --- C-09 / C-14 / D-6: MenACWY e Hib ---------------------------------------------------------------

def test_menacwy_no_hiv_duas_doses_e_reforco(client):
    v = _vacinas(_consultar(client, idade=35, sexo='masculino', comorbidades=['hiv'], cd4=500))
    assert v[ACWY]['subtitulo'].startswith('HIV | 2 doses') and v[ACWY]['prioridade'] == 'alta'
    assert v[ACWY]['esquema_pdf'] == 'hiv' and v[HIB]['esquema_pdf'] == 'hiv'


def test_menacwy_no_hiv_tambem_em_60_mais(client):
    assert ACWY in _vacinas(_consultar(client, idade=65, sexo='masculino', comorbidades=['hiv'], cd4=500))


def test_menacwy_de_rotina_sem_hiv(client):
    assert 'Conforme situação epidemiológica' in _vacinas(_consultar(client, idade=35, sexo='masculino'))[ACWY]['subtitulo']


def test_hib_na_asplenia_traz_as_duas_posicoes(client):
    dados = _consultar(client, idade=30, sexo='masculino', comorbidades=['asplenia'])
    hib = _vacinas(dados)[HIB]
    assert 'SBIm/CRIE: 2 doses' in hib['subtitulo'] and 'ACIP: 1 dose' in hib['subtitulo']
    assert 'Hib no adulto: diretrizes divergem' in _orientacoes(dados)
    assert 'Meningocócica B na asplenia: diretrizes divergem' in _orientacoes(dados)


def test_menb_na_asplenia_em_tres_doses_com_os_dois_reforcos(client):
    """VAC-01: MenB-4C no alto risco em 3 doses (ACIP out/2024, bula FDA ago/2024; SBIm Pacientes Especiais)."""
    dados = _consultar(client, idade=30, sexo='masculino', comorbidades=['anemia_falciforme'])
    menb = _vacinas(dados)['Meningocócica B (Bexsero®)']
    assert menb['subtitulo'].startswith('Asplenia | 3 doses (0, 1-2, 6m)') and menb['esquema_pdf'] == 'asplenia'
    assert '2-3 anos (ACIP)' in menb['descricao'] and '3 anos (SBIm)' in menb['descricao']
    assert 'CDC/ACIP 2024 (MenB-4C)' in menb['referencia']
    assert 'reforços seguintes' in _orientacoes(dados)['Meningocócica B na asplenia: diretrizes divergem']['descricao']


def test_menb_sem_asplenia_segue_o_cartao_de_rotina(client):
    menb = _vacinas(_consultar(client, idade=30, sexo='masculino'))['Meningocócica B (Bexsero®)']
    assert 'Asplenia' not in menb['subtitulo'] and 'esquema_pdf' not in menb


def test_posologia_da_menb_no_pdf_da_asplenia():
    from src.utils.pdf_minutas import posologia_da_vacina
    texto = posologia_da_vacina('Meningocócica B (Bexsero®)', 'asplenia')
    assert 'três doses' in texto and '0, 1-2 e 6 meses' in texto and 'duas doses' not in texto


def test_hib_nao_entra_sem_asplenia_nem_hiv(client):
    dados = _consultar(client, idade=30, sexo='masculino')
    assert HIB not in _vacinas(dados) and 'Hib no adulto: diretrizes divergem' not in _orientacoes(dados)


# --- C-10: HPV em 3 doses -----------------------------------------------------------------------------

@pytest.mark.parametrize('campos', [dict(comorbidades=['hiv'], cd4=500), dict(comorbidades=['transplante'])])
def test_hpv_tres_doses_no_imunossuprimido_com_menos_de_20(client, campos):
    hpv = _vacinas(_consultar(client, idade=19, sexo='masculino', **campos))[HPV]
    assert '3 doses (0-2-6m)' in hpv['subtitulo'] and 'PNI: HPV4 9-45 anos' in hpv['subtitulo']


def test_hpv_duas_doses_aos_19_sem_imunossupressao(client):
    assert '2 doses (0-6m)' in _vacinas(_consultar(client, idade=19, sexo='masculino'))[HPV]['subtitulo']


def test_hpv_nao_volta_depois_dos_45_no_hiv(client):
    assert HPV not in _vacinas(_consultar(client, idade=46, sexo='masculino', comorbidades=['hiv'], cd4=500))


# --- C-11 / D-1: VSR de 60 a 69 anos ------------------------------------------------------------------

@pytest.mark.parametrize('idade', [60, 69])
def test_vsr_60_69_sem_fator_de_risco_vira_orientacao(client, idade):
    dados = _consultar(client, idade=idade, sexo='feminino')
    assert VSR not in _vacinas(dados)
    assert 'VSR de 60 a 69 anos: só com fator de risco' in _orientacoes(dados)


@pytest.mark.parametrize('com', [['diabetes'], ['obesidade'], ['doenca_renal'], ['cirrose'], ['dpoc'], ['insuficiencia_cardiaca']])
def test_vsr_60_69_com_fator_de_risco(client, com):
    dados = _consultar(client, idade=65, sexo='masculino', comorbidades=com)
    assert _vacinas(dados)[VSR]['subtitulo'].startswith('60-69 anos com fator de risco')


def test_vsr_aos_70_e_rotina_com_aviso_de_divergencia(client):
    dados = _consultar(client, idade=70, sexo='feminino')
    assert 'Rotina' in _vacinas(dados)[VSR]['subtitulo']
    assert 'VSR: diretrizes divergem' in _orientacoes(dados)


def test_vsr_aos_75_sem_aviso_de_divergencia(client):
    assert 'VSR: diretrizes divergem' not in _orientacoes(_consultar(client, idade=75, sexo='feminino'))


# --- C-12 / D-8: VSR de 18 a 59 anos -----------------------------------------------------------------

@pytest.mark.parametrize('campos', [dict(comorbidades=['transplante']), dict(medicacoes=['adalimumabe']),
                                    dict(comorbidades=['neoplasia_ativa']), dict(comorbidades=['hiv'], cd4=150)])
def test_vsr_na_imunodeficiencia_moderada_grave(client, campos):
    dados = _consultar(client, idade=40, sexo='masculino', **campos)
    assert _vacinas(dados)[VSR]['subtitulo'].startswith('Imunodeficiência moderada/grave')
    assert 'VSR: diretrizes divergem' in _orientacoes(dados)


def test_vsr_no_hiv_com_cd4_a_partir_de_200_nao_entra(client):
    assert VSR not in _vacinas(_consultar(client, idade=40, sexo='masculino', comorbidades=['hiv'], cd4=200))


def test_vsr_no_corticoide_imunossupressor_mantem_o_cartao_proprio(client):
    dados = _consultar(client, idade=40, sexo='masculino', medicacoes=['prednisona'], dose__prednisona='40', duracao__prednisona='4')
    assert _vacinas(dados)[VSR]['subtitulo'] == 'Corticoide em dose imunossupressora | Dose única'


@pytest.mark.parametrize('com', [['diabetes'], ['doenca_renal'], ['hepatite_c']])
def test_vsr_a_partir_de_50_no_diabetes_drc_e_hepatopatia(client, com):
    assert 'Diabetes, nefropatia ou hepatopatia' in _vacinas(_consultar(client, idade=50, sexo='masculino', comorbidades=com))[VSR]['subtitulo']


@pytest.mark.parametrize('com, idade', [(['diabetes'], 49), (['doenca_renal'], 30), (['obesidade'], 59)])
def test_vsr_a_criterio_medico_vira_orientacao(client, com, idade):
    dados = _consultar(client, idade=idade, sexo='masculino', comorbidades=com)
    assert VSR not in _vacinas(dados) and 'VSR a critério médico' in _orientacoes(dados)


def test_vsr_a_criterio_nao_aparece_sem_a_condicao(client):
    assert 'VSR a critério médico' not in _orientacoes(_consultar(client, idade=45, sexo='masculino'))


# --- C-13: COVID-19 --------------------------------------------------------------------------------------

def test_covid_na_gestante_uma_dose_a_cada_gestacao(client):
    v = _vacinas(_consultar(client, idade=30, sexo='feminino', gestante='sim', idade_gestacional='20'))
    assert v[COVID]['subtitulo'] == 'Gestante | 1 dose a cada gestação'


def test_covid_no_imunocomprometido_e_no_hiv_a_cada_6_meses(client):
    for campos in (dict(comorbidades=['transplante']), dict(comorbidades=['hiv'], cd4=500)):
        assert _vacinas(_consultar(client, idade=40, sexo='masculino', **campos))[COVID]['subtitulo'].startswith('Imunocomprometido')


def test_covid_na_comorbidade_uma_dose_por_ano_e_sem_ela_rotina(client):
    assert _vacinas(_consultar(client, idade=40, sexo='masculino', comorbidades=['doenca_renal']))[COVID]['subtitulo'] == 'Comorbidade | 1 dose/ano'
    assert _vacinas(_consultar(client, idade=40, sexo='masculino'))[COVID]['subtitulo'].startswith('Rotina')
    assert _vacinas(_consultar(client, idade=60, sexo='masculino', comorbidades=['doenca_renal']))[COVID]['subtitulo'].startswith('60+')


# --- C-15 a C-20: textos ------------------------------------------------------------------------------

def test_vpc20_texto_do_pni_por_idade(client):
    sub = lambda i: _vacinas(_consultar(client, idade=i, sexo='masculino'))[PNEUMO]['subtitulo']
    assert 'PNI: sim (≥ 85 anos)' in sub(85)
    assert 'acamados/institucionalizados' in sub(84) and 'acamados/institucionalizados' in sub(60)
    assert 'grupos de risco (CRIE)' in sub(59)


def test_abrysvo_texto_e_aviso_de_divergencia(client):
    dados = _consultar(client, idade=30, sexo='feminino', gestante='sim', idade_gestacional='38')
    abrysvo = next(r for t, r in _vacinas(dados).items() if 'Abrysvo' in t)
    assert 'sem limite superior' in abrysvo['descricao'] and 'ACOG 2023' in abrysvo['referencia']
    assert 'VSR na gestação (Abrysvo®): diretrizes divergem' in _orientacoes(dados)
    assert 'VSR na gestação (Abrysvo®): diretrizes divergem' not in _orientacoes(_consultar(client, idade=30, sexo='feminino'))


def test_dtpa_da_gestante(client):
    dtpa = _vacinas(_consultar(client, idade=30, sexo='feminino', gestante='sim', idade_gestacional='22'))['dTpa (Adacel® ou Boostrix®)']
    assert dtpa['subtitulo'].startswith('Gestante | 1 dose a cada gestação a partir de 20 sem')
    assert '45 dias' in dtpa['descricao']
    assert _vacinas(_consultar(client, idade=30, sexo='feminino'))['dTpa (Adacel® ou Boostrix®)']['subtitulo'].startswith('Rotina')


def test_um_cartao_de_hepatite_em_60_mais_com_hepatopatia(client):
    v = _vacinas(_consultar(client, idade=65, sexo='masculino', comorbidades=['hepatite_c']))
    assert HEP_AB not in v and 'hepatite A' in v[HEP_B]['descricao']


def test_dengue_texto_completo(client):
    d = _vacinas(_consultar(client, idade=30, sexo='masculino'))['Dengue (Qdenga®)']['descricao']
    assert '30 dias' in d and '10 a 14 anos' in d and 'Butantan-DV' in d


def test_hd3v_na_imunossupressao_grave_abaixo_de_60(client):
    assert 'HD3V' in _vacinas(_consultar(client, idade=40, sexo='masculino', comorbidades=['transplante']))[INFLUENZA]['descricao']
    assert 'HD3V' in _vacinas(_consultar(client, idade=40, sexo='masculino', comorbidades=['hiv'], cd4=199))[INFLUENZA]['descricao']
    assert 'HD3V' not in _vacinas(_consultar(client, idade=40, sexo='masculino', comorbidades=['hiv'], cd4=200))[INFLUENZA]['descricao']


# --- D-4, D-9, D-11: orientações --------------------------------------------------------------------------

def test_tabagismo_antes_dos_50_avisa_a_divergencia_da_pneumococica(client):
    titulo = 'Pneumocócica no tabagismo antes dos 50 anos: diretrizes divergem'
    assert titulo in _orientacoes(_consultar(client, idade=40, sexo='masculino', tabagismo='atual', macos_ano='10'))
    assert titulo not in _orientacoes(_consultar(client, idade=40, sexo='masculino'))
    assert titulo not in _orientacoes(_consultar(client, idade=50, sexo='masculino', tabagismo='atual', macos_ano='10'))


def test_transplante_orienta_revacinacao_do_tcth(client):
    assert 'Transplante de medula óssea (TCTH): revacinação' in _orientacoes(_consultar(client, idade=40, sexo='masculino', comorbidades=['transplante']))


def test_situacoes_especiais_do_idoso(client):
    assert 'Vacinas em situações especiais (60+)' in _orientacoes(_consultar(client, idade=60, sexo='masculino'))
    assert 'Vacinas em situações especiais (60+)' not in _orientacoes(_consultar(client, idade=59, sexo='masculino'))


# --- D-5: HIV com CD4 a partir de 350 ---------------------------------------------------------------------

def test_hiv_cd4_350_continua_em_precaucao_com_o_texto_da_sbim():
    triagem = {'gestante': NAO, 'lactante': NAO, 'imunossupressao': NAO}
    alto = sv.avaliar_vacina(sv.VARICELA, triagem, {'idade': 30, 'hiv': True, 'cd4': 350})
    medio = sv.avaliar_vacina(sv.VARICELA, triagem, {'idade': 30, 'hiv': True, 'cd4': 349})
    assert alto['estado'] == medio['estado'] == sv.PRECAUCAO
    assert 'imunossupressão leve' in alto['motivo'] and 'imunossupressão leve' not in medio['motivo']


def test_contraindicacao_da_gestacao_vence_as_classes_de_medicacao():
    triagem = {'gestante': SIM, 'lactante': NAO, 'imunossupressao': NAO}
    r = sv.avaliar_vacina(sv.VARICELA, triagem, {'idade': 30, 'classes': [sv.IMUNOSSUPRESSAO_BAIXO_GRAU]})
    assert r['estado'] == sv.CONTRAINDICADA


# --- C-07: segunda conferência no PDF ------------------------------------------------------------------

FEBRE_AMARELA = {'titulo': 'Febre Amarela (Stamaril®)', 'categoria': 'vacina'}
INFLUENZA_PDF = {'titulo': 'Influenza (trivalente ou quadrivalente)', 'categoria': 'vacina'}
HOMEM = {'nome': 'Paciente de Teste', 'idade': '40', 'sexo': 'masculino', 'imunossupressao': 'nao'}


def _pdf(client, dados_paciente, itens):
    return client.post('/api/gerar-pdf-vacinas', json={'dados_paciente': dados_paciente, 'recomendacoes': itens})


@pytest.mark.parametrize('extra', [dict(medicacoes=['adalimumabe']), dict(comorbidades=['transplante']),
                                   dict(medicacoes=['prednisona']), dict(medicacoes=['pembrolizumabe']),
                                   dict(medicacoes=['metotrexato'], dose__metotrexato='15', peso='70'),
                                   dict(comorbidades=['hiv'], cd4='500')])
def test_pdf_recusa_viva_com_imunossupressao_das_listas(client, extra):
    resposta = _pdf(client, {**HOMEM, **extra}, [FEBRE_AMARELA])
    assert resposta.status_code == 400 and resposta.get_json()['codigo'] == 'triagem_vacinas'


def test_pdf_libera_viva_com_corticoide_em_dose_baixa_informada(client):
    resposta = _pdf(client, {**HOMEM, 'medicacoes': ['prednisona'], 'dose__prednisona': '5', 'duracao__prednisona': '1'},
                    [FEBRE_AMARELA])
    assert resposta.status_code == 200


def test_pdf_inativada_com_imunossupressor_e_liberada(client):
    assert _pdf(client, {**HOMEM, 'medicacoes': ['adalimumabe']}, [INFLUENZA_PDF]).status_code == 200


def test_pdf_recusa_lista_de_medicacoes_malformada(client):
    resposta = _pdf(client, {**HOMEM, 'medicacoes': [{'x': 1}]}, [INFLUENZA_PDF])
    assert resposta.status_code == 400


def test_pdf_esquema_hiv_da_hib_e_da_acwy_e_aceito(client):
    itens = [{'titulo': ACWY, 'categoria': 'vacina', 'esquema_pdf': 'hiv'}, {'titulo': HIB, 'categoria': 'vacina', 'esquema_pdf': 'hiv'}]
    assert _pdf(client, {**HOMEM, 'comorbidades': ['hiv'], 'hiv': True, 'cd4': '500'}, itens).status_code == 200
