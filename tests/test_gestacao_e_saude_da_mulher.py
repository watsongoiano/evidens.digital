"""Correções da auditoria de gestação, pré-natal, puerpério e saúde da mulher (relatório E, 15/11/2026).

Dados fictícios. Cada regra tem caso positivo, negativo e limítrofe.
"""
import pytest

from src.utils import hiv, prenatal


def _g(**kw):
    base = {'idade_gestacional': '12', 'primeira_consulta': 'nao', 'fator_rh': 'positivo',
            'toxoplasmose': 'imune', 'gestacao_condicoes': []}
    base.update(kw)
    return prenatal.normalizar(base)


def _api(client, **extra):
    dados = dict(idade=28, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
                 imunossupressao='nao', gestante='sim', lactante='nao', idade_gestacional=26, primeira_consulta='nao',
                 fator_rh='positivo', toxoplasmose='imune')
    dados.update(extra)
    r = client.post('/api/checkup-intelligent', json=dados)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _titulos(r):
    return [x['titulo'] for x in r['recommendations']]


def _rec(r, titulo):
    return next(x for x in r['recommendations'] if x['titulo'] == titulo)


def _orient(r):
    return [o['titulo'] for o in r['orientacoes']]


# ---------------------------------------------------------------------------
# E-01: PA ≥ 140/90 na gestação (ACOG PB 222; ACOG CO 767)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('pas, pad, categoria', [
    (139, 89, 'normal'), (140, 85, 'hipertensao'), (130, 90, 'hipertensao'),
    (159, 109, 'hipertensao'), (160, 100, 'grave'), (150, 110, 'grave'), (None, 95, 'hipertensao'), (135, None, 'incompleta'),
])
def test_classificacao_da_pa_na_gestacao_sem_estagios_da_aha(pas, pad, categoria):
    assert prenatal.classificar_pa(pas, pad)['categoria'] == categoria
    assert 'estágio' not in prenatal.classificar_pa(pas, pad)['rotulo']


def test_pa_145_95_com_26_semanas_e_investigacao_de_pre_eclampsia_nao_has_cronica(client):
    r = _api(client, pas=145, pad=95)
    assert 'hipertensao' not in [i['valor'] for i in r['inferencias']]
    assert r['pa_classificacao']['categoria'] == 'hipertensao'
    t = _titulos(r)
    for exame in ('Relação proteína/creatinina, urina', 'Hemograma completo', 'Creatinina, soro', 'TGO e TGP, soro',
                  'Desidrogenase láctica (LDH), soro'):
        assert _rec(r, exame)['subtitulo'] == 'Pré-natal | Investigação de pré-eclâmpsia | Agora', exame
    # seguimento ambulatorial de HAS não entra
    assert not any(x.startswith(('MAPA', 'Ecocardiograma transtorácico', 'Ácido úrico', 'Potássio')) for x in t)
    assert 'Hipertensão na gestação com 20 semanas ou mais' in _orient(r)
    assert not any(o.get('urgente') and 'faixa grave' in o['titulo'] for o in r['orientacoes'])
    assert 'AAS para prevenção de pré-eclâmpsia' not in _orient(r)       # sem fator de alto risco, e já depois de 16 sem


def test_pa_em_faixa_grave_e_alerta_urgente_no_topo(client):
    r = _api(client, idade_gestacional=34, pas=165, pad=112)
    primeiro = r['orientacoes'][0]
    assert primeiro.get('urgente') and 'faixa grave' in primeiro['titulo']
    assert '15 minutos' in primeiro['descricao'] and '30-60 minutos' in primeiro['descricao']
    assert all(l['url'] for l in primeiro['referencias'])
    assert r['pa_classificacao']['categoria'] == 'grave'


def test_pa_normal_na_gestacao_nao_gera_alerta_nem_investigacao(client):
    r = _api(client, pas=135, pad=85)
    assert r['pa_classificacao']['categoria'] == 'normal'
    assert 'Relação proteína/creatinina, urina' not in _titulos(r)
    assert not any('140/90' in t or 'faixa grave' in t for t in _orient(r))


def test_pa_alta_antes_de_20_semanas_e_provavel_has_cronica(client):
    r = _api(client, idade_gestacional=19.9, pas=150, pad=95)
    assert 'PA ≥ 140/90 antes de 20 semanas' in _orient(r)
    assert 'Relação proteína/creatinina, urina' not in _titulos(r)
    # com 20 semanas exatas já é investigação de pré-eclâmpsia
    r20 = _api(client, idade_gestacional=20, pas=150, pad=95)
    assert _rec(r20, 'Relação proteína/creatinina, urina')['subtitulo'].endswith('Investigação de pré-eclâmpsia | Agora')


def test_has_cronica_com_pa_alta_depois_de_20_semanas_investiga_pre_eclampsia_sobreposta(client):
    r = _api(client, comorbidades=['hipertensao'], pas=150, pad=96)
    assert 'HAS crônica com PA ≥ 140/90 depois de 20 semanas' in _orient(r)
    assert _rec(r, 'Relação proteína/creatinina, urina')['subtitulo'] == 'Pré-natal | Investigação de pré-eclâmpsia | Agora'
    assert not any(x.startswith('MAPA') or x.startswith('Ecocardiograma transtorácico') for x in _titulos(r))


# ---------------------------------------------------------------------------
# E-02, E-04, E-05: fatores de risco e AAS (USPSTF 2021; ACOG PB 222; FEBRASGO 2023)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('comorbidade, nome', [('lupus', 'lúpus'), ('saf', 'síndrome antifosfolípide'),
                                               ('doenca_renal', 'doença renal crônica')])
def test_lupus_saf_e_doenca_renal_sao_alto_risco_de_pre_eclampsia(client, comorbidade, nome):
    r = _api(client, idade=30, idade_gestacional=12, comorbidades=[comorbidade])
    aas = next(o for o in r['orientacoes'] if o['titulo'] == 'AAS para prevenção de pré-eclâmpsia')
    assert nome in aas['descricao'] and 'Iniciar agora' in aas['descricao'] and '100-150 mg' in aas['descricao']
    assert nome in _rec(r, 'Relação proteína/creatinina, urina')['descricao']
    assert any(t.startswith('Gestação de alto risco') and nome in t for t in _orient(r))
    assert any(t == 'Divergência entre diretrizes: dose e duração do AAS' for t in _orient(r))


def test_sem_fator_de_risco_nao_ha_aas():
    g = _g()
    assert prenatal.orientacao_aas(g['ig'], *prenatal.fatores_pre_eclampsia(g, 30)) is None


def test_dois_fatores_moderados_indicam_considerar_aas_e_um_so_nao():
    g = _g()
    altos, moderados = prenatal.fatores_pre_eclampsia(g, 35, imc=35)
    assert altos == [] and moderados == ['idade ≥ 35 anos', 'IMC > 30']
    assert prenatal.orientacao_aas(12, altos, moderados)['titulo'] == 'Considerar AAS para prevenção de pré-eclâmpsia'
    # limítrofe: IMC 30 não conta (USPSTF: > 30), 34 anos não conta
    assert prenatal.orientacao_aas(12, *prenatal.fatores_pre_eclampsia(g, 35, imc=30)) is None
    assert prenatal.orientacao_aas(12, *prenatal.fatores_pre_eclampsia(_g(gestacao_condicoes=['nulipara']), 34, imc=31)) \
        is not None
    assert prenatal.orientacao_aas(12, *prenatal.fatores_pre_eclampsia(_g(gestacao_condicoes=['nulipara']), 34)) is None


def test_rastreio_combinado_alto_e_alto_risco_pela_febrasgo():
    altos, _ = prenatal.fatores_pre_eclampsia(_g(gestacao_condicoes=['rastreio_pe_alto']), 28)
    assert altos == ['rastreio combinado ≥ 1:100']


@pytest.mark.parametrize('ig, trecho', [
    (10, 'Iniciar a partir de 12 semanas'), (12, 'Iniciar agora'), (15.9, 'Iniciar agora'),
    (16, 'Ainda pode ser iniciado até 28 semanas'), (27.9, 'Ainda pode ser iniciado'),
    (28, 'Não iniciar depois de 28 semanas'), (34, 'manter até 36 semanas'), (36, 'suspende com 36 semanas'),
])
def test_aas_depende_da_idade_gestacional(ig, trecho):
    o = prenatal.orientacao_aas(ig, ['pré-eclâmpsia prévia'], [])
    assert trecho in o['descricao']
    assert ('100-150 mg' in o['descricao']) is (ig < 28)


def test_saf_esta_na_lista_de_comorbidades():
    from src.utils.condicoes import COMORBIDADES
    assert COMORBIDADES['saf']['rotulo'] == 'Síndrome antifosfolípide'


# ---------------------------------------------------------------------------
# E-03: clamídia e gonococo em mulheres até 24 anos (USPSTF 2021, B)
# ---------------------------------------------------------------------------
def _mulher(client, **extra):
    dados = dict(idade=22, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
                 imunossupressao='nao', gestante='nao', lactante='nao')
    dados.update(extra)
    r = client.post('/api/checkup-intelligent', json=dados)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


@pytest.mark.parametrize('idade, ativa, pede', [
    (22, 'sim', True), (24, 'sim', True), (24, 'desconhecido', True), (25, 'sim', False), (22, 'nao', False),
])
def test_clamidia_e_gonococo_ate_24_anos(client, idade, ativa, pede):
    r = _mulher(client, idade=idade, sexualmente_ativa=ativa)
    assert (prenatal.CLAMIDIA in _titulos(r)) is pede
    if pede:
        rec = _rec(r, prenatal.CLAMIDIA)
        assert rec['subtitulo'] == 'Mulheres sexualmente ativas ≤ 24 anos | Anual' and rec['grau_evidencia'] == 'B'
        assert 'chlamydia-and-gonorrhea-screening' in rec['referencia_html']
        assert 'Divergência entre diretrizes: clamídia e gonococo' in _orient(r)
        assert ('não informada' in rec['descricao']) is (ativa != 'sim')


def test_clamidia_a_partir_de_25_anos_so_com_risco(client):
    assert 'Clamídia e gonococo a partir de 25 anos' in _orient(_mulher(client, idade=30, sexualmente_ativa='sim'))
    assert 'Clamídia e gonococo a partir de 25 anos' not in _orient(_mulher(client, idade=30))


def test_homem_nao_recebe_rastreio_de_clamidia_nem_campo_vale(client):
    r = client.post('/api/checkup-intelligent', json=dict(idade=22, sexo='masculino', tabagismo='nunca',
                                                         imunossupressao='nao', sexualmente_ativa='sim')).get_json()
    assert prenatal.CLAMIDIA not in _titulos(r)


def test_resposta_invalida_de_vida_sexual_e_recusada(client):
    r = client.post('/api/checkup-intelligent', json=dict(idade=22, sexo='feminino', tabagismo='nunca',
                                                         imunossupressao='nao', sexualmente_ativa='talvez'))
    assert r.status_code == 400 and r.get_json()['erros'][0]['campo'] == 'sexualmente_ativa'


# ---------------------------------------------------------------------------
# E-06: HIV na gestação (FEBRASGO 2025 / PCDT TV 2022)
# ---------------------------------------------------------------------------
def test_gestante_com_hiv_carga_viral_e_cd4_da_gestacao():
    recs, orient = hiv.recomendar(28, 'feminino', cd4=600, carga_viral=0, em_tarv=True, supressao_viral=True, gestante=True)
    por = {r['titulo']: r for r in recs}
    assert '34 semanas' in por['Carga Viral do HIV (HIV RNA)']['subtitulo']
    assert por['Contagem de linfócitos T CD4+']['subtitulo'] == 'Gestante com HIV | 1ª consulta e com 34 semanas'
    assert 'Radiografia de tórax' not in por
    assert any(o['titulo'] == 'HIV na gestação: radiografia de tórax' for o in orient)
    # fora da gestação continua a regra do MS
    recs, _ = hiv.recomendar(28, 'feminino', cd4=600, carga_viral=0, em_tarv=True, supressao_viral=True)
    por = {r['titulo']: r for r in recs}
    assert por['Carga Viral do HIV (HIV RNA)']['subtitulo'] == 'HIV+ | A cada 6 meses' and 'Radiografia de tórax' in por


def test_gestante_com_hiv_carga_viral_de_34_semanas_como_proxima_etapa(client):
    r = _api(client, idade_gestacional=20, comorbidades=['hiv'], cd4=600, carga_viral=0, em_tarv='sim', supressao_viral='sim')
    assert any(p['titulo'] == 'Carga Viral do HIV (HIV RNA)' and p['semana'] == 34 for p in r['proximas_gestacao'])
    r34 = _api(client, idade_gestacional=34, comorbidades=['hiv'], cd4=600, carga_viral=0, em_tarv='sim', supressao_viral='sim')
    assert not any(p['titulo'] == 'Carga Viral do HIV (HIV RNA)' for p in r34['proximas_gestacao'])
    t = [x.lower() for x in _titulos(r)]
    for duplicado in ('toxoplasmose igg, soro', 'anticorpos anti-hcv, soro', 'antígeno hbs, soro'):
        assert duplicado not in t, duplicado


# ---------------------------------------------------------------------------
# E-07, E-21: puerpério (ADA 2026, seção 15)
# ---------------------------------------------------------------------------
def test_dmg_atual_programa_totg_pos_parto(client):
    r = _api(client, idade_gestacional=30, gestacao_condicoes=['dmg_atual'])
    assert any(p['titulo'] == 'TOTG-75g pós-parto (jejum e 2 h)' for p in r['proximas_gestacao'])
    assert not any(p['titulo'] == 'TOTG-75g pós-parto (jejum e 2 h)' for p in _api(client, idade_gestacional=30)['proximas_gestacao'])


@pytest.mark.parametrize('lactante, comorbidades, totg', [
    ('sim_menor_6m', ['diabetes_gestacional_previo'], True), ('sim_6m_ou_mais', ['diabetes_gestacional_previo'], False),
    ('sim_menor_6m', [], False), ('sim_menor_6m', ['diabetes_gestacional_previo', 'diabetes'], False),
])
def test_puerperio_recente_pos_dmg_pede_totg(client, lactante, comorbidades, totg):
    r = _mulher(client, idade=41, lactante=lactante, comorbidades=comorbidades)
    tem = any(x['titulo'].startswith('TOTG-75g') and 'puerpério' in x['subtitulo'] for x in r['recommendations'])
    assert tem is totg
    assert ('Puerpério recente: lípides e HbA1c' in _orient(r)) is (lactante == 'sim_menor_6m')


# ---------------------------------------------------------------------------
# E-08: TSH universal na 1ª consulta (FEBRASGO/SBEM 2022), com aviso de divergência (ATA 2017)
# ---------------------------------------------------------------------------
def test_tsh_na_primeira_consulta_com_aviso_de_divergencia(client):
    r = _api(client, idade_gestacional=10, primeira_consulta='sim')
    tsh = _rec(r, 'Hormônio Tireoestimulante (TSH), soro')
    assert tsh['subtitulo'] == 'Pré-natal | 1ª consulta' and '4,0' in tsh['descricao']
    assert 'Divergência entre diretrizes: TSH na gestação' in _orient(r)
    seguimento = _api(client, idade_gestacional=10, primeira_consulta='nao')
    assert 'Hormônio Tireoestimulante (TSH), soro' not in _titulos(seguimento)
    assert 'Divergência entre diretrizes: TSH na gestação' not in _orient(seguimento)


# ---------------------------------------------------------------------------
# E-09: DM pré-gestacional na gestação
# ---------------------------------------------------------------------------
def test_dm_pre_gestacional_na_gestacao(client):
    r = _api(client, idade=30, idade_gestacional=22, comorbidades=['diabetes_tipo_1'])
    t = _titulos(r)
    assert 'Ecocardiograma fetal' in t
    assert _rec(r, 'Fundoscopia (Exame de fundo de olho)')['subtitulo'].startswith('DM pré-gestacional | 1º trimestre')
    for fora in ('Cálcio iônico, soro', '25-hidroxivitamina D, soro', 'Fósforo, soro'):
        assert fora not in t   # saíram da rotina do diabetes (ADA 2026; auditoria D) e não aparecem na gestação
    cedo = _api(client, idade=30, idade_gestacional=12, comorbidades=['diabetes_tipo_1'])
    assert any(p['titulo'] == 'Ecocardiograma fetal' and p['semana'] == 20 for p in cedo['proximas_gestacao'])
    assert 'Ecocardiograma fetal' not in _titulos(_api(client, idade=30, idade_gestacional=22))


def test_vitamina_d_nao_e_rotina_do_diabetico_fora_da_gestacao(client):
    r = _mulher(client, idade=40, comorbidades=['diabetes_tipo_1'])
    assert '25-hidroxivitamina D, soro' not in _titulos(r)   # ADA 2026: sem dosagem de rotina (auditoria D)


# ---------------------------------------------------------------------------
# E-10: ultrassonografia do 3º trimestre
# ---------------------------------------------------------------------------
def test_doppler_so_no_alto_risco_e_crescimento_como_protocolo_institucional(client):
    baixo = _api(client, idade_gestacional=30)
    usg = _rec(baixo, 'Ultrassonografia obstétrica')
    assert usg['grau_evidencia'] == 'C' and 'Protocolo institucional' in usg['subtitulo']
    assert 'Ultrassonografia obstétrica com Doppler' not in _titulos(baixo)
    assert 'Divergência entre diretrizes: exames do protocolo institucional' in _orient(baixo)
    alto = _api(client, idade_gestacional=30, gestacao_condicoes=['pe_previa'])
    assert _rec(alto, 'Ultrassonografia obstétrica com Doppler')['grau_evidencia'] == 'B'


# ---------------------------------------------------------------------------
# E-11: alto risco e gemelar
# ---------------------------------------------------------------------------
def test_alto_risco_sinalizado_e_monocorionica_com_ultrassonografia_seriada(client):
    r = _api(client, idade_gestacional=18, gestacao_condicoes=['monocorionica'])
    assert r['gestacao']['condicoes'] == ['gemelar', 'monocorionica']
    assert any(t.startswith('Gestação de alto risco') for t in _orient(r))
    usg = _rec(r, 'Ultrassonografia obstétrica')
    assert 'A cada 2 semanas a partir de 16 semanas' in usg['subtitulo']
    gemelar = _api(client, idade_gestacional=12, gestacao_condicoes=['gemelar'])
    alto = next(o for o in gemelar['orientacoes'] if o['titulo'].startswith('Gestação de alto risco'))
    assert 'corionicidade' in alto['descricao']
    assert not any(t.startswith('Gestação de alto risco') for t in _orient(_api(client)))


# ---------------------------------------------------------------------------
# E-12: suplementos
# ---------------------------------------------------------------------------
def test_suplementos_na_gestacao_e_acido_folico_fora_dela(client):
    assert 'Suplementação na gestação' in _orient(_api(client))
    assert 'Ácido fólico se pode engravidar' in _orient(_mulher(client, idade=30))
    assert 'Ácido fólico se pode engravidar' in _orient(_mulher(client, idade=45))
    assert 'Ácido fólico se pode engravidar' not in _orient(_mulher(client, idade=46))
    assert 'Ácido fólico se pode engravidar' not in _orient(_mulher(client, idade=30, comorbidades=['histerectomia_total']))


# ---------------------------------------------------------------------------
# E-13, E-18: duplicatas e itens que não são do pré-natal de risco habitual
# ---------------------------------------------------------------------------
def test_seguimento_nao_repete_rastreios_gerais_nem_ecg_e_creatinina(client):
    r = _api(client, idade=25, idade_gestacional=20, primeira_consulta='nao')
    t = [x.lower() for x in _titulos(r)]
    for fora in ('anti-hiv 1 e 2, soro', 'anti-hcv igg, soro', 'eletrocardiograma de repouso', 'creatinina, soro'):
        assert fora not in t, fora
    adiados = [a['titulo'] for a in r['adiados_gestacao']]
    assert len(adiados) == len(set(adiados))
    # com indicação (HAS crônica), creatinina e ECG continuam
    com_has = [x.lower() for x in _titulos(_api(client, idade=45, idade_gestacional=20, comorbidades=['hipertensao']))]
    assert 'creatinina, soro' in com_has and 'eletrocardiograma de repouso' in com_has


# ---------------------------------------------------------------------------
# E-14: adolescente gestante
# ---------------------------------------------------------------------------
def test_gestante_adolescente_recebe_explicacao(client):
    r = client.post('/api/checkup-intelligent', json=dict(idade=16, sexo='feminino', tabagismo='nunca', gestante='sim',
                                                         idade_gestacional=8, primeira_consulta='sim'))
    assert r.status_code == 400 and 'adolescentes' in r.get_json()['erros'][0]['mensagem']
    r = client.post('/api/checkup-intelligent', json=dict(idade=16, sexo='feminino', tabagismo='nunca', gestante='nao'))
    assert 'adolescentes' not in r.get_json()['erros'][0]['mensagem']


# ---------------------------------------------------------------------------
# E-15, E-16: estreptococo do grupo B e fim da gestação
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('ig, agora', [(35.9, False), (36, True), (37.9, True), (38, False)])
def test_estreptococo_b_com_36_a_37_semanas(ig, agora):
    t = [r['titulo'] for r in prenatal.exames(_g(idade_gestacional=str(ig)), 30)]
    assert ('Cultura para estreptococo do grupo B (swab vaginal e retal)' in t) is agora


def test_fim_da_gestacao(client):
    r39 = _api(client, idade_gestacional=39)
    assert not any(t.startswith('TOTG-75g gestacional') for t in _titulos(r39))
    assert 'TOTG-75g não realizado' in _orient(r39) and 'Sífilis e HIV no fim da gestação' in _orient(r39)
    assert 'Gestação com 40 semanas ou mais' not in _orient(r39)
    assert 'Gestação com 40 semanas ou mais' in _orient(_api(client, idade_gestacional=40))
    r36 = _api(client, idade_gestacional=36.9)
    assert any(t.startswith('TOTG-75g gestacional') for t in _titulos(r36))
    assert 'Sífilis e HIV no fim da gestação' not in _orient(r36)


# ---------------------------------------------------------------------------
# E-17: vacinas com texto da gestação
# ---------------------------------------------------------------------------
def test_vacinas_da_gestante_com_texto_da_gestacao(client):
    r = _api(client, idade_gestacional=22)
    assert _rec(r, 'dTpa (Adacel® ou Boostrix®)')['subtitulo'] == 'Gestante | 1 dose a cada gestação a partir de 20 semanas'
    assert 'em qualquer idade gestacional' in _rec(r, 'COVID-19 (Comirnaty®, Spikevax® ou outras)')['subtitulo']
    fora = _mulher(client, idade=30)
    assert _rec(fora, 'dTpa (Adacel® ou Boostrix®)')['subtitulo'].startswith('Rotina')


# ---------------------------------------------------------------------------
# E-19, E-20 e dúvida 4: divergências e fontes
# ---------------------------------------------------------------------------
def test_divergencias_da_gestante_so_quando_relevantes(client):
    jovem = _api(client, idade=22, idade_gestacional=10, primeira_consulta='sim')
    assert 'Divergência entre diretrizes: clamídia e gonococo na gestante a partir de 25 anos' not in _orient(jovem)
    adulta = _api(client, idade=25, idade_gestacional=10, primeira_consulta='sim')
    assert 'Divergência entre diretrizes: clamídia e gonococo na gestante a partir de 25 anos' in _orient(adulta)
    rh = _api(client, idade_gestacional=20, fator_rh='negativo')
    assert 'Divergência entre diretrizes: Coombs indireto na Rh negativa' in _orient(rh)
    assert 'Divergência entre diretrizes: Coombs indireto na Rh negativa' not in _orient(_api(client, idade_gestacional=20))
    assert 'Fator Rh não informado' in _orient(_api(client, idade_gestacional=20, fator_rh='desconhecido'))


def test_toda_orientacao_da_gestacao_tem_fonte_clicavel(client):
    perfis = [dict(idade_gestacional=34, pas=165, pad=112, comorbidades=['lupus'], fator_rh='negativo',
                   primeira_consulta='sim', gestacao_condicoes=['gemelar']),
              dict(idade=36, idade_gestacional=40, comorbidades=['diabetes_tipo_1', 'hiv'], cd4=600, em_tarv='sim',
                   gestacao_condicoes=['dmg_previo'], fator_rh='desconhecido')]
    for extra in perfis:
        r = _api(client, **extra)
        for o in r['orientacoes']:
            assert o.get('referencias') and all(l['url'] for l in o['referencias']), (o['titulo'], o['referencia'])
        for x in r['recommendations']:
            if (x.get('subtitulo') or '').startswith('Pré-natal'):
                assert x['referencia_html'].count('<a href="https://') == len(x['referencias']), x['titulo']

