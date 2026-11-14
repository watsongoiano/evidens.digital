"""Rotina de pré-natal pela idade gestacional (Einstein v.3, MS 2012/2016, Williams 26e)."""
import re

import pytest

from src.utils import pdf_minutas, prenatal


def _g(**kw):
    base = {'idade_gestacional': '10', 'primeira_consulta': 'nao', 'fator_rh': 'desconhecido',
            'toxoplasmose': 'desconhecido', 'gestacao_condicoes': []}
    base.update(kw)
    return prenatal.normalizar(base)


def _titulos(g, idade=30, **kw):
    return [r['titulo'] for r in prenatal.exames(g, idade, **kw)]


def _proximas(g, idade=30, **kw):
    return [r['titulo'] for r in prenatal.programacao(g, idade, **kw)[1]]


def test_primeira_consulta_tem_a_rotina_inicial():
    t = _titulos(_g(idade_gestacional='8', primeira_consulta='sim'))
    for item in ('Hemograma completo', 'Glicemia de jejum, soro', 'Urocultura com antibiograma',
                 'HIV 1/2 (anticorpos e antígeno p24), soro', 'Sífilis: teste treponêmico ou VDRL, soro',
                 'HBsAg, soro', 'Anti-HCV IgG, soro', 'Toxoplasmose IgG e IgM, soro',
                 'Tipagem sanguínea ABO e fator Rh', 'Ultrassonografia obstétrica transvaginal'):
        assert item in t, item
    # próxima janela NÃO vai para a lista nem para o PDF: só como lembrete
    assert 'Ultrassonografia morfológica de 1º trimestre (translucência nucal)' not in t
    assert 'Ultrassonografia morfológica de 1º trimestre (translucência nucal)' in _proximas(_g(idade_gestacional='8'))


def test_janela_de_24_semanas():
    t = _titulos(_g(idade_gestacional='24'))
    assert 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro' in t
    assert 'Hemograma completo' in t          # Williams, Tab. 10-1: hemoglobina/hematócrito de 24-28 semanas
    assert 'Urocultura com antibiograma' not in t and 'Urocultura com antibiograma' in _proximas(_g(idade_gestacional='24'))
    assert 'Ultrassonografia morfológica de 2º trimestre' in t   # 20-24+6
    assert 'Ultrassonografia morfológica de 2º trimestre' not in _titulos(_g(idade_gestacional='25'))


def test_diabetica_nao_faz_totg_e_rh_negativo_faz_coombs():
    t = _titulos(_g(idade_gestacional='25', fator_rh='negativo'), diabetica=True)
    assert not any(x.startswith('TOTG') for x in t)
    assert 'Coombs indireto, soro' in t


def test_toxo_imune_nao_repete():
    assert 'Toxoplasmose IgG e IgM, soro' not in _titulos(_g(idade_gestacional='21', toxoplasmose='imune'))
    assert 'Toxoplasmose IgG e IgM, soro' in _titulos(_g(idade_gestacional='21', toxoplasmose='suscetivel'))


def test_estreptococo_b_no_fim():
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in _titulos(_g(idade_gestacional='36'))
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' not in _titulos(_g(idade_gestacional='30'))
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in _proximas(_g(idade_gestacional='30'))
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' not in _titulos(_g(idade_gestacional='22'))


def test_hipertensa_tem_exames_basais_de_pre_eclampsia_e_aas():
    recs = prenatal.exames(_g(idade_gestacional='14'), 42, hipertensa=True)
    upcr = next(r for r in recs if r['titulo'] == 'Relação proteína/creatinina, urina')
    assert 'AAS' in upcr['descricao']


def test_parto_prematuro_previo_antecipa_colo():
    t = _titulos(_g(idade_gestacional='16', gestacao_condicoes=['prematuro_previo']))
    assert 'Ultrassonografia transvaginal para medida do colo uterino' in t


def test_clamidia_na_primeira_consulta_para_todas_e_reteste_no_terceiro_trimestre_ate_25_anos():
    """Williams 26e, Tab. 10-1: clamídia tem ponto na 1ª consulta; reteste (C/D) no 3º trimestre se risco."""
    assert any('Clamídia' in x for x in _titulos(_g(primeira_consulta='sim'), idade=22))
    assert any('Clamídia' in x for x in _titulos(_g(primeira_consulta='sim'), idade=30))
    assert any('Clamídia' in x for x in _titulos(_g(idade_gestacional='32'), idade=22))
    assert not any('Clamídia' in x for x in _titulos(_g(idade_gestacional='32'), idade=30))


def test_pontos_da_tabela_10_1_do_williams():
    """Cada item com ponto na tabela é pedido na coluna correspondente."""
    primeira = _titulos(_g(idade_gestacional='10', primeira_consulta='sim'), idade=30)
    for exame in ('Hemograma completo', 'Tipagem sanguínea ABO e fator Rh', 'Coombs indireto, soro',
                  'EAS - Elementos Anormais e Sedimentoscopia', 'Urocultura com antibiograma', 'Rubéola IgG, soro',
                  'Sífilis: teste treponêmico ou VDRL, soro', 'Clamídia e gonococo, PCR (urina ou swab)', 'HBsAg, soro',
                  'HIV 1/2 (anticorpos e antígeno p24), soro'):
        assert exame in primeira, exame
    meio = _titulos(_g(idade_gestacional='26'), idade=30)
    assert 'Hemograma completo' in meio and 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro' in meio
    assert 'Coombs indireto, soro' not in meio                       # letra A: só se indicado (Rh negativo)
    assert 'Coombs indireto, soro' in _titulos(_g(idade_gestacional='26', fator_rh='negativo'), idade=30)
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in _titulos(_g(idade_gestacional='36'), idade=30)


def test_papanicolaou_da_primeira_consulta_vem_do_rastreio_de_colo(client):
    dados = dict(idade=27, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[], imunossupressao='nao',
                 gestante='sim', lactante='nao', idade_gestacional=10, primeira_consulta='sim')
    t = [x['titulo'] for x in client.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']]
    assert 'Citologia cervicovaginal (Papanicolaou)' in t


@pytest.mark.parametrize('campo, valor', [('idade_gestacional', '50'), ('fator_rh', 'x'),
                                          ('toxoplasmose', 'x'), ('gestacao_condicoes', ['outra'])])
def test_entrada_invalida(campo, valor):
    with pytest.raises(prenatal.GestacaoInvalida):
        _g(**{campo: valor})


def test_adiados_na_gestacao():
    recs = [{'titulo': 'Mamografia Digital - Bilateral', 'categoria': 'imagem'},
            {'titulo': 'Colesterol total e frações, soro', 'categoria': 'laboratorio'},
            {'titulo': 'Hemoglobina glicada (HbA1c), soro', 'categoria': 'laboratorio'},
            {'titulo': 'Creatinina, soro', 'categoria': 'laboratorio'}]
    mantidas, adiadas = prenatal.adiar(recs)
    assert [r['titulo'] for r in mantidas] == ['Creatinina, soro']
    assert {a['estado'] for a in adiadas} == {'adiado_gestacao'}
    mantidas, _ = prenatal.adiar(recs, diabetica=True)
    assert 'Hemoglobina glicada (HbA1c), soro' in [r['titulo'] for r in mantidas]


CASO_DA_HOME = {   # gestante 42 a, 24 semanas, hipertensa, ex-tabagista 25 maços-ano, mãe com CCR
    'idade': '42', 'sexo': 'feminino', 'tabagismo': 'ex', 'macos_ano': '25', 'anos_parou_fumar': '3',
    'comorbidades': ['hipertensao'], 'historia_familiar': ['cancer_colorretal'],
    'gestante': 'sim', 'lactante': 'nao', 'imunossupressao': 'nao',
    'idade_gestacional': '24', 'primeira_consulta': 'sim', 'fator_rh': 'desconhecido',
    'toxoplasmose': 'desconhecido',
}


def test_api_gestante_de_24_semanas(client):
    r = client.post('/api/checkup-intelligent', json=CASO_DA_HOME).get_json()
    titulos = [x['titulo'] for x in r['recommendations']]
    assert 'TOTG-75g gestacional (jejum, 1 h e 2 h), soro' in titulos
    assert 'Relação proteína/creatinina, urina' in titulos
    assert 'Mamografia Digital - Bilateral' not in titulos
    assert not any(t.startswith('Colesterol total') for t in titulos)
    adiados = {x['titulo'] for x in r['adiados_gestacao']}
    assert all(x['categoria'] == 'vacina' for x in r['nao_incluidas'])
    assert 'Mamografia Digital - Bilateral' in adiados
    # vacinas de vírus vivo continuam barradas pela triagem
    assert not any('Febre Amarela' in t or 'Tríplice Viral' in t for t in titulos)
    assert r['gestacao']['ig'] == 24
    proximas = {x['titulo'] for x in r['proximas_gestacao']}
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' in proximas
    assert 'Cultura para estreptococo do grupo B (swab vaginal e retal)' not in titulos


def test_api_recusa_ig_impossivel(client):
    r = client.post('/api/checkup-intelligent', json={**CASO_DA_HOME, 'idade_gestacional': '60'})
    assert r.status_code == 400
    assert r.get_json()['erros'][0]['campo'] == 'idade_gestacional'


def test_nao_gestante_ignora_subcampos(client):
    r = client.post('/api/checkup-intelligent', json={**CASO_DA_HOME, 'gestante': 'nao', 'idade_gestacional': '60'})
    assert r.status_code == 200
    assert r.get_json()['gestacao'] is None


def test_colo_tem_janela_propria_com_prematuro_previo():
    g = _g(idade_gestacional='17', gestacao_condicoes=['prematuro_previo'])
    assert 'Ultrassonografia transvaginal para medida do colo uterino' in _titulos(g)
    assert 'Ultrassonografia morfológica de 2º trimestre' not in _titulos(g)       # 20-24
    assert 'Ultrassonografia morfológica de 2º trimestre' in _proximas(g)
    assert 'Ultrassonografia transvaginal para medida do colo uterino' not in _titulos(_g(idade_gestacional='17'))


def test_nenhum_exame_da_lista_e_de_janela_futura():
    for ig in range(5, 41):
        g = _g(idade_gestacional=str(ig), fator_rh='negativo', toxoplasmose='suscetivel',
               gestacao_condicoes=['prematuro_previo'])
        for r in prenatal.exames(g, 30):
            assert 'antecipado' not in r.get('quando_pdf', '').lower()
            assert 'Deixar pedido' not in r['subtitulo']


def test_janela_gestacional_vai_para_o_pdf(client):
    from pypdf import PdfReader
    import io
    recs = prenatal.exames(_g(idade_gestacional='8', primeira_consulta='nao'), 30)
    imagem = [r for r in recs if r['categoria'] == 'imagem']
    corpo = {'dados_paciente': {'nome': 'Teste', 'idade': 30, 'sexo': 'feminino'}, 'recomendacoes': imagem}
    resp = client.post('/api/gerar-pdf-exames-imagem', json=corpo)
    assert resp.status_code == 200
    texto = ' '.join(' '.join(p.extract_text() for p in PdfReader(io.BytesIO(resp.data)).pages).split())
    assert 'Realizar com 7-9 semanas de gestação' in texto
    assert 'translucência nucal' not in texto


@pytest.mark.parametrize('falta', ['idade_gestacional', 'primeira_consulta'])
def test_gestante_exige_ig_e_primeira_consulta(falta):
    with pytest.raises(prenatal.GestacaoInvalida) as exc:
        _g(**{falta: ''})
    assert exc.value.erros[0]['campo'] == falta


def test_pdf_recusa_janela_gestacional_longa_demais(client):
    corpo = {'dados_paciente': {'nome': 'T'}, 'recomendacoes': [
        {'titulo': 'Hemograma completo', 'categoria': 'laboratorio', 'quando_pdf': 'x' * 500}]}
    assert client.post('/api/gerar-pdf-exames-laboratoriais', json=corpo).status_code == 400


@pytest.mark.parametrize('ig, dtpa_agora, vsr_agora', [('14', False, False), ('22', True, False), ('30', True, True)])
def test_vacinas_da_gestacao_so_na_janela(client, ig, dtpa_agora, vsr_agora):
    r = client.post('/api/checkup-intelligent', json={**CASO_DA_HOME, 'idade_gestacional': ig}).get_json()
    agora = ' '.join(x['titulo'] for x in r['recommendations'])
    depois = ' '.join(x['titulo'] for x in r['proximas_gestacao'])
    assert ('dTpa' in agora) is dtpa_agora and ('dTpa' in depois) is (not dtpa_agora)
    assert ('Abrysvo' in agora) is vsr_agora and ('Abrysvo' in depois) is (not vsr_agora)


# ---------------------------------------------------------------------------
# TOTG fora da janela, exames equivalentes, HIV e fontes clicáveis
# ---------------------------------------------------------------------------
def _pedido_api(client, **extra):
    dados = dict(idade=30, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
                 imunossupressao='nao', gestante='sim', lactante='nao', idade_gestacional=35, primeira_consulta='nao')
    dados.update(extra)
    resposta = client.post('/api/checkup-intelligent', json=dados)
    assert resposta.status_code == 200, resposta.get_json()
    return resposta.get_json()


def _titulos_api(r):
    return [x['titulo'] for x in r['recommendations']]


def test_totg_e_pedido_depois_de_28_semanas_se_nao_consta_como_feito(client):
    r = _pedido_api(client, idade_gestacional=35)
    totg = next(x for x in r['recommendations'] if x['titulo'].startswith('TOTG-75g gestacional'))
    assert 'fazer agora' in totg['subtitulo'] and 'quando_pdf' not in totg   # o atraso fica na tela, não no pedido


def test_totg_informado_como_feito_nao_e_pedido_de_novo(client):
    r = _pedido_api(client, idade_gestacional=35, totg_feito='sim')
    assert not any(t.startswith('TOTG-75g') for t in _titulos_api(r))
    assert any(p['estado'] == 'etapa_anterior' and p['titulo'].startswith('TOTG-75g') for p in r['proximas_gestacao'])


def test_totg_na_janela_e_antes_dela(client):
    assert any(t.startswith('TOTG-75g gestacional') for t in _titulos_api(_pedido_api(client, idade_gestacional=26)))
    cedo = _pedido_api(client, idade_gestacional=12)
    assert not any(t.startswith('TOTG-75g gestacional') for t in _titulos_api(cedo))
    assert any(p['titulo'].startswith('TOTG-75g') and p['estado'] == 'proxima_janela' for p in cedo['proximas_gestacao'])


def test_totg_nao_se_pede_a_diabetica(client):
    r = _pedido_api(client, idade_gestacional=30, comorbidades=['diabetes'])
    assert not any(t.startswith('TOTG-75g gestacional') for t in _titulos_api(r))


def test_primeira_consulta_tardia_pede_iniciais_totg_e_ultrassonografia(client):
    r = _pedido_api(client, idade_gestacional=26, primeira_consulta='sim')
    t = _titulos_api(r)
    for esperado in ('Rubéola IgG, soro', 'Citomegalovírus IgG e IgM, soro', 'Anti-HCV IgG, soro',
                     'TOTG-75g gestacional (jejum, 1 h e 2 h), soro', 'Ultrassonografia obstétrica'):
        assert esperado in t, esperado


def test_seguimento_avisa_que_os_exames_iniciais_foram_considerados_feitos(client):
    r = _pedido_api(client, idade_gestacional=35, primeira_consulta='nao')
    aviso = next(p for p in r['proximas_gestacao'] if p['estado'] == 'etapa_anterior' and 'iniciais' in p['titulo'])
    assert 'rubéola' in aviso['motivo'] and 'Primeira consulta' in aviso['motivo']
    assert 'Rubéola IgG, soro' not in _titulos_api(r)


def test_gestante_nao_recebe_o_mesmo_exame_com_dois_nomes(client):
    t = [x.lower() for x in _titulos_api(_pedido_api(client, idade=25, idade_gestacional=30, primeira_consulta='sim'))]
    assert 'hiv 1/2 (anticorpos e antígeno p24), soro' in t and 'anti-hiv 1 e 2, soro' not in t
    assert t.count('anti-hcv igg, soro') == 1


def test_gestante_com_hiv_nao_repete_rastreio_de_hiv_nem_exames_equivalentes(client):
    r = _pedido_api(client, idade_gestacional=30, primeira_consulta='sim', comorbidades=['hiv'], cd4='500')
    t = [x.lower() for x in _titulos_api(r)]
    for fora in ('hiv 1/2 (anticorpos e antígeno p24), soro', 'anti-hiv 1 e 2, soro', 'vdrl, soro', 'antígeno hbs, soro',
                 'anticorpos anti-hcv, soro', 'hemograma completo com plaquetas'):
        assert fora not in t, fora
    assert 'carga viral do hiv (hiv rna)' in t and 'sífilis: teste treponêmico ou vdrl, soro' in t


@pytest.mark.parametrize('gestante', ['nao', 'sim'])
def test_beta_hcg_nao_e_pedido_a_mulher_com_hiv(client, gestante):
    extra = dict(idade_gestacional=20, primeira_consulta='sim') if gestante == 'sim' else {}
    dados = dict(idade=30, sexo='feminino', tabagismo='nunca', comorbidades=['hiv'], cd4='500', historia_familiar=[],
                 imunossupressao='nao', gestante=gestante, lactante='nao', **extra)
    r = client.post('/api/checkup-intelligent', json=dados).get_json()
    assert not any('hcg' in x['titulo'].lower() for x in r['recommendations'])
    assert 'anti-hiv 1 e 2, soro' not in [x['titulo'].lower() for x in r['recommendations']]


def test_fontes_do_pre_natal_sao_clicaveis(client):
    r = _pedido_api(client, idade_gestacional=35, primeira_consulta='sim', gestacao_condicoes=['pe_previa'])
    pn = [x for x in r['recommendations'] if (x.get('subtitulo') or '').startswith('Pré-natal')]
    assert len(pn) > 10
    for x in pn:
        assert x['referencia_html'].count('<a href="https://') == len(x['referencias']), (x['titulo'], x['referencia_html'])
    html = ' '.join(x['referencia_html'] for x in pn)
    for dominio in ('medicalsuite.einstein.br', 'bvsms.saude.gov.br', 'acog.org', 'uspreventiveservicestaskforce.org'):
        assert dominio in html, dominio


def test_fontes_das_listas_e_das_sindromes_sao_clicaveis(client):
    dados = dict(idade=45, sexo='feminino', tabagismo='nunca', comorbidades=['cirurgia_bariatrica', 'masld'],
                 medicacoes=['varfarina', 'apixabana', 'quetiapina', 'enalapril'],
                 historia_familiar=['brca', 'lynch', 'nem2', 'hemocromatose', 'cardiomiopatia_hipertrofica'],
                 imunossupressao='nao', gestante='nao', lactante='nao')
    r = client.post('/api/checkup-intelligent', json=dados).get_json()
    sem_link = [(x['titulo'], x.get('referencia')) for x in r['recommendations'] if '<a href="http' not in (x.get('referencia_html') or '')]
    assert not sem_link, sem_link


def test_pedido_so_leva_a_janela_gestacional_como_observacao():
    """No receituário, só a instrução de quando fazer o exame ("Realizar com 35-37 semanas de gestação.").
    "Primeira consulta de pré-natal", "Basal: alto risco de pré-eclâmpsia" e o aviso de TOTG atrasado são
    o motivo do pedido: ficam na tela, não no papel."""
    vistas = set()
    for ig in range(5, 41):
        for primeira in ('sim', 'nao'):
            g = _g(idade_gestacional=str(ig), primeira_consulta=primeira, fator_rh='negativo', toxoplasmose='suscetivel',
                   gestacao_condicoes=['prematuro_previo', 'pe_previa', 'gemelar'])
            for r in prenatal.exames(g, 30, hipertensa=True):
                if 'quando_pdf' in r:
                    vistas.add(r['quando_pdf'])
    assert vistas and all(re.fullmatch(r'Realizar com .+ de gestação\.', q) for q in vistas), vistas


def test_observacao_sai_em_italico_com_obs_no_pdf():
    from pypdf import PdfReader
    import io
    itens = [{'titulo': 'Cultura para estreptococo do grupo B (swab vaginal e retal)', 'categoria': 'laboratorio',
              'quando_pdf': 'Realizar com 35-37 semanas de gestação.'},
             {'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}]
    pdf = pdf_minutas.gerar_pdf_exames_laboratoriais({'nome': 'Paciente', 'sexo': 'feminino', 'idade': 30}, itens)
    texto = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    assert 'Obs.: Realizar com 35-37 semanas de gestação.' in texto
    assert texto.count('Obs.:') == 1
    assert b'DejaVuSans-Oblique' in pdf or b'DejaVu-Oblique' in pdf or b'Oblique' in pdf
    pdf_en = pdf_minutas.gerar_pdf_exames_laboratoriais({'nome': 'Paciente', 'sexo': 'feminino', 'idade': 30}, itens, idioma='en')
    assert 'Note: ' in PdfReader(io.BytesIO(pdf_en)).pages[0].extract_text()
