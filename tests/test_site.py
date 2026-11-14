"""O que o site publica, o que a página do check-up contém e o que foi desativado.

Cobre P-06 (risco cardiovascular), P-10 (persistência) e a exposição de arquivos
internos e telas antigas por URL.
"""
import importlib.util
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Páginas vistas por uma médica com conta aprovada (o fixture `client`).
PAGINAS = ['/', '/intelligent-tools', '/contact', '/cadastro', '/conta']
PAGINAS_DO_ADMIN = ['/admin', '/analytics']


# --- Arquivos publicados ----------------------------------------------------

@pytest.mark.parametrize('rota', PAGINAS + [
    '/index.html',
    '/static/conta.js',
    '/favicon.ico',
    '/favicon.png',
    '/src/static/styles/base.css',
    '/static/evidens.css',
])
def test_paginas_e_recursos_publicos_respondem(client, rota):
    assert client.get(rota).status_code == 200


@pytest.mark.parametrize('rota', [
    '/src/static/index.html',                 # tela antiga, com cálculo de risco próprio
    '/intelligent-tools.html',                # só pela rota /intelligent-tools, que exige login
    '/analytics.html',
    '/admin.html',
    '/conta.html',
    '/src/utils/contas.py',
    '/dist/index.html',
    '/src/static/database_dashboard.html',
    '/config/base_recommendations.json',
    '/config/medical_references.json',
    '/package.json',
    '/vercel.json',
    '/tailwind.config.js',
    '/static/evidens.src.css',
    '/prevent_calculator.js',
    '/src/routes/checkup_intelligent.py',
    '/requirements.txt',
    '/.env',
    '/../api/index.py',
])
def test_arquivos_internos_e_telas_antigas_nao_sao_servidos(client, rota):
    assert client.get(rota).status_code == 404


def _referencias_locais(html):
    for atributo, valor in re.findall(r'\b(src|href)="([^"]+)"', html):
        if valor.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'data:')):
            continue
        if valor.startswith('/_vercel/'):   # injetado pela plataforma em produção
            continue
        yield valor


@pytest.mark.parametrize('pagina', PAGINAS)
def test_toda_referencia_local_das_paginas_existe(client, pagina):
    """Nenhuma página pode apontar para um arquivo que o site não publica."""
    html = client.get(pagina).get_data(as_text=True)
    for referencia in _referencias_locais(html):
        caminho = referencia if referencia.startswith('/') else '/' + referencia
        # /login redireciona para o check-up quem já entrou: vale a página final.
        assert client.get(caminho, follow_redirects=True).status_code == 200, f'{pagina} -> {referencia}'


@pytest.mark.parametrize('pagina', PAGINAS)
def test_toda_rota_de_api_chamada_pelas_paginas_existe(app, client, pagina):
    """O painel de analytics chegou a consultar uma rota que não existia."""
    html = client.get(pagina).get_data(as_text=True)
    rotas = app.url_map.bind('localhost')
    for caminho in sorted(set(re.findall(r"'(/api/[A-Za-z0-9_\-/]+)'", html))):
        encontrados = []
        for metodo in ('GET', 'POST'):
            try:
                endpoint, _ = rotas.match(caminho, method=metodo)
            except Exception:
                continue
            if endpoint != 'serve_static':
                encontrados.append(endpoint)
        assert encontrados, f'{pagina} chama {caminho}, que não existe'
        assert not any(e.startswith('checkup_intelligent.desativado_') for e in encontrados), caminho


def test_painel_de_analytics_recebe_os_campos_que_exibe(admin):
    dados = admin.get('/api/analytics/stats').get_json()
    for periodo in ('total', 'today', 'this_month'):
        assert set(dados[periodo]) >= {'visits', 'recommendations', 'exam_requests', 'vaccine_prescriptions'}


# --- P-06: risco cardiovascular pelo PREVENT ---------------------------------

PERFIL_COMPLETO = {
    'idade': '55', 'sexo': 'masculino', 'tabagismo': 'atual', 'macos_ano': '30',
    'pas': '132', 'pad': '80', 'colesterol': '200', 'hdl': '45', 'creatinina': '1.0',
    'peso': '80', 'altura': '175',
    'comorbidades': ['diabetes'], 'medicacoes': ['anti_hipertensivos'], 'imunossupressao': 'nao',
}


def test_api_devolve_risco_prevent_igual_ao_modulo(client):
    from src.utils import prevent
    risco = client.post('/api/checkup-intelligent', json=PERFIL_COMPLETO).get_json()['risco_cardiovascular']
    assert risco['status'] == 'calculado'
    esperado = prevent.estimar(idade=55, sexo='masculino', colesterol_total=200, hdl=45, pas=132,
                               diabetes=True, fumante=True, imc_valor=risco['imc'],
                               egfr=prevent.egfr_ckd_epi_2021(1.0, 55, 'masculino'),
                               anti_hipertensivo=True, estatina=False)
    assert risco['dez_anos'] == esperado['dez_anos']
    assert risco['trinta_anos'] == esperado['trinta_anos']
    # 55 anos, homem, DM2: alto pela regra do diabetes da SBC 2025, qualquer que seja o escore.
    assert risco['categoria_sbc_2025']['categoria'] == 'alto'
    assert 'categoria_acc_aha_2026' in risco


def test_risco_lista_o_que_falta(client):
    perfil = {k: v for k, v in PERFIL_COMPLETO.items() if k not in ('creatinina', 'peso')}
    risco = client.post('/api/checkup-intelligent', json=perfil).get_json()['risco_cardiovascular']
    assert risco['status'] == 'incompleto'
    assert set(risco['faltando']) == {'creatinina', 'peso'}


@pytest.mark.parametrize('ajuste, status', [
    ({'idade': '25'}, 'nao_aplicavel'),
    ({'comorbidades': ['dcv_aterosclerotica']}, 'nao_aplicavel'),
    ({'comorbidades': ['insuficiencia_cardiaca']}, 'nao_aplicavel'),
    ({'comorbidades': ['cardiopatia']}, 'nao_aplicavel'),   # valor antigo
    ({'colesterol': '400'}, 'fora_da_faixa'),
])
def test_risco_nao_calcula_fora_da_populacao(client, ajuste, status):
    risco = client.post('/api/checkup-intelligent', json={**PERFIL_COMPLETO, **ajuste}).get_json()['risco_cardiovascular']
    assert risco['status'] == status
    assert risco['motivo']


def test_calculadoras_antigas_continuam_fora():
    assert importlib.util.find_spec('src.utils.prevent_calculator') is None
    assert not (RAIZ / 'prevent_calculator.js').exists()
    assert not (RAIZ / 'config' / 'prevent_coefficients.json').exists()


def test_pagina_exibe_risco_sem_calcular_no_navegador(client):
    html = client.get('/intelligent-tools').get_data(as_text=True)
    for trecho in ('prevent_calculator', 'PreventCalculator', 'Math.exp'):
        assert trecho not in html
    assert 'exibirRisco(result.risco_cardiovascular)' in html
    assert 'temporariamente desativado' not in html


# --- Página do check-up -------------------------------------------------------

@pytest.fixture()
def pagina(client):
    return client.get('/intelligent-tools').get_data(as_text=True)


def _select(html, nome):
    bloco = re.search(rf'<select id="{nome}"[^>]*>(.*?)</select>', html, re.S)
    assert bloco, f'select {nome} não encontrado'
    return bloco.group(0), re.findall(r'<option value="([^"]*)"', bloco.group(1))


@pytest.mark.parametrize('campo, opcoes', [
    ('imunossupressao', ['desconhecido', 'nao', 'sim']),
    ('gestante', ['desconhecido', 'nao', 'sim']),
    ('lactante', ['desconhecido', 'nao', 'sim_menor_6m', 'sim_6m_ou_mais']),
])
def test_triagem_tem_tres_valores_e_comeca_em_nao_informado(pagina, campo, opcoes):
    _, valores = _select(pagina, campo)
    assert valores == opcoes


def test_tabagismo_exige_escolha_explicita(pagina):
    # Chips (botões de opção) sem valor pré-marcado; o primeiro leva "required",
    # o que obriga a escolher um do grupo.
    radios = re.findall(r'<input[^>]*type="radio"[^>]*name="tabagismo"[^>]*>', pagina)
    assert [re.search(r'value="([^"]*)"', r).group(1) for r in radios] == ['nunca', 'ex', 'atual']
    assert all('checked' not in r for r in radios)
    assert any('required' in r for r in radios)


def test_opcoes_sao_chips_como_na_home(pagina):
    css = (RAIZ / 'static' / 'evidens.src.css').read_text(encoding='utf-8')
    assert '.opcao:has(input:checked) { @apply bg-teal border-teal text-white; }' in css
    assert 'rounded-full' in css.split('.opcao {')[1].split('\n')[0]


def test_nome_do_paciente_e_opcional_e_nao_vai_com_as_recomendacoes(pagina):
    campo = re.search(r'<input[^>]*id="nome_paciente"[^>]*>', pagina).group(0)
    assert 'required' not in campo
    assert 'delete payload.nome_paciente' in pagina


def test_seletor_de_pais_sem_efeito_foi_retirado(pagina):
    assert 'name="pais"' not in pagina


def test_pagina_avisa_que_a_saida_e_sugestao_e_que_o_pdf_e_minuta(pagina):
    assert 'não constituem prescrição' in pagina
    assert 'minutas sem assinatura digital' in pagina


def test_pagina_nao_chama_endpoints_desativados(pagina):
    for rota in ('gerar-receita-vacinas', 'gerar-solicitacao-exames', 'generate-pdf'):
        assert rota not in pagina


# --- P-10: nada é gravado ------------------------------------------------------

def test_motor_nao_tem_acesso_a_banco_de_dados():
    import src.routes.checkup_intelligent as motor

    for nome in ('db', 'Patient', 'Checkup', 'Recomendacao'):
        assert not hasattr(motor, nome)
    fonte = Path(motor.__file__).read_text(encoding='utf-8')
    assert 'db.session' not in fonte
    assert 'src.models' not in fonte


def test_resposta_pendente_e_descartada_se_o_formulario_mudar(pagina):
    """A resposta de um envio só vale se o formulário não mudou enquanto ela chegava."""
    invalidar = re.search(r'function invalidarResultados\(evento\) \{(.*?)\n        \}', pagina, re.S).group(1)
    # O contador avança antes do teste de "resultado visível": vale também com resposta pendente.
    assert invalidar.index('revisaoDoFormulario += 1') < invalidar.index("recommendationsDiv.style.display === 'block'")

    envio = re.search(r"checkupForm\.addEventListener\('submit'.*?\n        \}\);", pagina, re.S).group(0)
    assert 'const revisaoDoEnvio = revisaoDoFormulario;' in envio
    conferencia = envio.index('if (revisaoDoEnvio !== revisaoDoFormulario)')
    assert envio.index("await fetch('/api/checkup-intelligent'") < conferencia
    assert conferencia < envio.index('currentRecommendations = result.recommendations')
    assert conferencia < envio.index('mostrarErros(')


# --- Novo front-end ---------------------------------------------------------

@pytest.mark.parametrize('rota', ['/', '/intelligent-tools'])
def test_paginas_usam_o_css_compilado_e_nao_o_tailwind_pelo_cdn(client, rota):
    html = client.get(rota).get_data(as_text=True)
    assert '/static/evidens.css' in html
    assert 'cdn.tailwindcss.com' not in html
    assert '<style>' not in html


def test_css_compilado_cobre_as_classes_dos_cartoes_gerados_por_script(client):
    css = client.get('/static/evidens.css').get_data(as_text=True)
    for seletor in ('.recommendation-card', '.nao-incluida-card', '.selo', '.btn-escuro', '.campo', '.rv.in'):
        assert seletor in css, seletor


def test_home_leva_ao_check_up_e_nao_se_apresenta_como_prototipo(client):
    html = client.get('/').get_data(as_text=True)
    assert 'href="/intelligent-tools"' in html
    assert 'href="#"' not in html
    for trecho in ('Nenhuma análise clínica', 'sem motor clínico', 'Sem motor clínico', 'Neko Health', 'cdn.tailwindcss.com'):
        assert trecho not in html, trecho
    # A estratificação de risco está desativada; a home não pode anunciá-la como recurso.
    assert 'Estratificação' not in html


@pytest.mark.parametrize('rota', ['/', '/intelligent-tools', '/contact'])
def test_paginas_mantem_o_vercel_analytics(client, rota):
    assert '/_vercel/insights/script.js' in client.get(rota).get_data(as_text=True)


# --- Números da home conferidos contra o motor ----------------------------

def _varredura(client):
    """Passa uma grade de perfis pelo motor e devolve os itens e as referências que aparecem."""
    import itertools
    itens, refs = {}, set()
    grade = itertools.product(
        (20, 30, 40, 50, 60, 70, 80), ('masculino', 'feminino'), ('nunca', 'atual', 'ex'),
        ([], ['diabetes'], ['hipertensao'], ['hiv'], ['doenca_renal', 'dcv_aterosclerotica'], ['insuficiencia_cardiaca'], ['dpoc'],
         ['obesidade', 'dislipidemia'], ['has_resistente']),
        ([], ['cancer_mama', 'cancer_colorretal', 'cancer_ovario']), ('nao', 'sim'))
    for idade, sexo, tabagismo, comorbidades, familia, gestante in grade:
        if gestante == 'sim' and (sexo != 'feminino' or idade > 50):
            continue
        dados = dict(idade=idade, sexo=sexo, tabagismo=tabagismo, comorbidades=comorbidades,
                     historia_familiar=familia, imunossupressao='nao', gestante=gestante, lactante='nao',
                     idade_gestacional='20' if gestante == 'sim' else '', primeira_consulta='sim',
                     macos_ano='30' if tabagismo != 'nunca' else '', anos_parou_fumar='5' if tabagismo == 'ex' else '',
                     cd4='500' if 'hiv' in comorbidades else '')
        for rec in client.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']:
            itens[rec['titulo']] = rec['categoria']
            refs.add(rec.get('referencia') or '')
    # Gestação: todas as janelas do pré-natal, com Rh negativo, toxoplasmose suscetível e risco
    for idade, ig in itertools.product((22, 35), (8, 12, 15, 22, 26, 32, 36)):
        dados = dict(idade=idade, sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[],
                     imunossupressao='nao', gestante='sim', lactante='nao', idade_gestacional=ig,
                     primeira_consulta='sim', fator_rh='negativo', toxoplasmose='suscetivel',
                     gestacao_condicoes=['pe_previa', 'dmg_previo', 'prematuro_previo'])
        for rec in client.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']:
            itens[rec['titulo']] = rec['categoria']
            refs.add(rec.get('referencia') or '')
    # Listas suspensas (comorbidades, medicações e família): cada item sozinho, em idades e sexos distintos
    from src.utils import condicoes
    for idade, sexo in itertools.product((30, 47, 68), ('masculino', 'feminino')):
        casos = ([dict(comorbidades=[k]) for k in condicoes.COMORBIDADES]
                 + [dict(medicacoes=[k]) for k in condicoes.MEDICACOES]
                 + [dict(historia_familiar=[k]) for k in list(condicoes.FAMILIA) + ['cancer_colorretal', 'cancer_mama', 'dac_precoce']])
        for caso in casos:
            dados = dict(dict(idade=idade, sexo=sexo, tabagismo='nunca', comorbidades=[], medicacoes=[],
                              historia_familiar=[], imunossupressao='nao', gestante='nao', lactante='nao'), **caso)
            for rec in client.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']:
                itens[rec['titulo']] = rec['categoria']
                refs.add(rec.get('referencia') or '')
    return itens, ' '.join(refs)


def test_numeros_da_home_correspondem_ao_motor(client):
    html = client.get('/').get_data(as_text=True)
    itens, refs = _varredura(client)
    assert html.count(f'{len(itens)} recomendações') == 2  # faixa do hero e FAQ
    # 15 sociedades e órgãos citados na home; todos precisam aparecer nas referências do motor.
    fontes = ['SBIm', 'SBC', 'MS', 'USPSTF', 'CDC', 'NIH', 'AHA', 'ACC', 'ADA', 'ACOG', 'ESC', 'EAS', 'EACS', 'KDIGO', 'GOLD']
    assert len(fontes) == 15
    for fonte in fontes:
        assert fonte in refs, fonte
    assert '15<span' in html and '15 sociedades e órgãos de saúde' in html


def test_caso_de_exemplo_da_home_e_a_saida_real_do_motor(client):
    """Os números e as linhas do paciente de exemplo da home vêm do motor; se o motor mudar, a home muda junto."""
    caso = dict(idade=52, sexo='masculino', tabagismo='nunca', comorbidades=['hipertensao', 'dislipidemia'],
                historia_familiar=[], imunossupressao='nao')
    r = client.post('/api/checkup-intelligent', json=caso).get_json()
    recs = r['recommendations']
    por_tipo = {}
    for rec in recs:
        por_tipo[rec['categoria']] = por_tipo.get(rec['categoria'], 0) + 1
    assert (len(recs), por_tipo['laboratorio'], por_tipo['imagem'], por_tipo['vacina']) == (27, 12, 4, 11)
    assert r['nao_incluidas'] == []
    html = client.get('/').get_data(as_text=True)
    for trecho in ('4 de 27', '27 recomendações<br>', 'px-3 py-1">12</span>', 'px-3 py-1">4</span>', 'px-3 py-1">11</span>'):
        assert trecho in html, trecho
    # As quatro linhas da tabela de conduta: item, fonte e grau de evidência como o motor devolve.
    def achar(pedaco):
        return next(rec for rec in recs if pedaco in rec['titulo'])
    for pedaco, fonte, grau in (('Colonoscopia', 'USPSTF 2021', 'B'), ('Glicose, soro', 'ADA 2024', 'A'),
                                ('Razão albumina/creatinina', 'SBC 2025', 'A'), ('Herpes Zóster', 'SBIm 2026/2027', 'A')):
        rec = achar(pedaco)
        assert fonte in rec['referencia'] and rec['grau_evidencia'] == grau, pedaco


def test_home_so_lista_instituicoes_que_o_motor_cita(client):
    import re as _re
    html = client.get('/').get_data(as_text=True)
    bloco = html[html.index('id="referencias"'):html.index('id="visao"')]
    siglas = _re.findall(r'<p class="text-\[17px\] font-medium tracking-tight">([^<]+)</p>', bloco)
    _, refs = _varredura(client)
    assert len(siglas) == 15 and '15 instituições de referência' in bloco
    for sigla in siglas:
        assert sigla in refs, sigla


@pytest.mark.parametrize('pagina', PAGINAS_DO_ADMIN)
def test_paginas_do_administrador_respondem_e_nao_tem_referencia_quebrada(admin, pagina):
    resposta = admin.get(pagina)
    assert resposta.status_code == 200
    for referencia in _referencias_locais(resposta.get_data(as_text=True)):
        caminho = referencia if referencia.startswith('/') else '/' + referencia
        assert admin.get(caminho, follow_redirects=True).status_code == 200, f'{pagina} -> {referencia}'


@pytest.mark.parametrize('pagina', ['index.html', 'intelligent-tools.html', 'login.html', 'cadastro.html',
                                    'conta.html', 'configurar.html', 'admin.html'])
def test_logo_do_cabecalho_e_a_mesma_palavra_do_rodape(pagina):
    """Cabeçalho mantém o ícone de pontos e usa a palavra "evidēns" no mesmo tamanho do rodapé (28 px)."""
    html = (RAIZ / pagina).read_text(encoding='utf-8')
    cabecalho = html.split('</header>')[0]
    assert 'grid-cols-3 gap-[3px]' in cabecalho
    assert 'text-[28px] font-medium tracking-tight leading-none">evidēns' in cabecalho
    rodape = (RAIZ / 'index.html').read_text(encoding='utf-8').split('<footer')[1]
    assert 'text-[28px] font-medium tracking-tight">evidēns' in rodape


def test_icone_da_aba_e_servido(client):
    for caminho in ('/favicon.ico', '/favicon.png', '/favicon.svg', '/apple-touch-icon.png'):
        assert client.get(caminho).status_code == 200, caminho
    svg = client.get('/favicon.svg')
    assert svg.mimetype == 'image/svg+xml'
    # cor do ícone acompanha o tema do navegador (claro/escuro), sem fundo próprio
    corpo = svg.get_data(as_text=True)
    assert '@media (prefers-color-scheme:dark)' in corpo and '<rect class="m"' in corpo


def test_cardiopatia_generica_saiu_do_formulario(pagina):
    assert 'value="cardiopatia"' not in pagina.split('name="historia_familiar"')[0].split('s-comorbidades')[1]
    assert 'value="dcv_aterosclerotica"' in pagina and 'value="insuficiencia_cardiaca"' in pagina


def test_insuficiencia_cardiaca_puxa_vacinas_de_risco_antes_dos_50(client):
    base = {'idade': '40', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao'}
    sem = {r['titulo'] for r in client.post('/api/checkup-intelligent', json=base).get_json()['recommendations']}
    com = {r['titulo'] for r in client.post('/api/checkup-intelligent',
                                           json={**base, 'comorbidades': ['insuficiencia_cardiaca']}).get_json()['recommendations']}
    novas = com - sem
    assert any('Pneumocócica' in t for t in novas) and any('Sincicial' in t for t in novas)
    recs = client.post('/api/checkup-intelligent', json={**base, 'comorbidades': ['insuficiencia_cardiaca']}).get_json()['recommendations']
    pneumo = next(r for r in recs if 'Pneumocócica' in r['titulo'])
    assert 'A partir de 50 anos' not in pneumo['subtitulo'] and 'Comorbidade de risco' in pneumo['subtitulo']


def test_dcv_aterosclerotica_nao_vira_hipertensao(client):
    base = {'idade': '45', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao'}
    com = {r['titulo'] for r in client.post('/api/checkup-intelligent',
                                           json={**base, 'comorbidades': ['dcv_aterosclerotica']}).get_json()['recommendations']}
    assert not any('MAPA' in t for t in com)


@pytest.mark.parametrize('hba1c, diabetico', [('6.4', False), ('6.5', True), ('8.1', True)])
def test_hba1c_a_partir_de_6_5_conta_como_diabetes(client, hba1c, diabetico):
    corpo = {'idade': '50', 'sexo': 'masculino', 'tabagismo': 'nunca', 'imunossupressao': 'nao', 'hba1c': hba1c}
    r = client.post('/api/checkup-intelligent', json=corpo).get_json()
    assert r['diabetes_por_hba1c'] is diabetico


def test_hba1c_marca_o_chip_de_diabetes_na_tela(pagina):
    assert "hb >= 6.5" in pagina and "input[data-marca]:checked" in pagina


def test_exames_laboratoriais_so_aparecem_se_houver(pagina):
    bloco = pagina.split('id="exames-bloco"')[1].split('</section>')[0]
    for campo in ('colesterol', 'hdl', 'creatinina', 'hba1c'):
        assert f'id="{campo}"' in bloco
    assert 'id="exames-bloco" class="bloco-condicional" hidden' in pagina
    assert 'name="tem_exames" value="sim"' in pagina and 'name="tem_exames" value="nao"' in pagina


def test_campo_tem_exames_e_aceito_pela_api(client):
    r = client.post('/api/checkup-intelligent', json={'idade': '40', 'sexo': 'feminino', 'tabagismo': 'nunca',
                                                      'imunossupressao': 'nao', 'tem_exames': 'nao'})
    assert r.status_code == 200


def test_listas_com_busca_substituem_o_texto_livre(pagina):
    for antigo in ('outras_comorbidades', 'medicacoes_continuo', 'outras_condicoes_familiares', '<select id="lista_'):
        assert antigo not in pagina
    from src.utils import condicoes, medicamentos
    for lista, itens in (('comorbidades', condicoes.COMORBIDADES), ('medicacoes', medicamentos.MEDICAMENTOS),
                         ('historia_familiar', condicoes.FAMILIA)):
        assert f'data-campo="{lista}"' in pagina
        for chave in itens:
            if chave in medicamentos.MAIS_USADOS:   # já é botão: não repete na lista
                assert f'role="option" data-valor="{chave}"' not in pagina, chave
            else:
                assert f'role="option" data-valor="{chave}"' in pagina, chave
    assert 'value="dac_precoce"' in pagina and 'inferencias_recusadas' in pagina
    assert pagina.count('role="combobox" aria-autocomplete') == 3


def test_listas_da_pagina_estao_em_dia_com_o_gerador(pagina):
    import importlib.util
    spec = importlib.util.spec_from_file_location('gerar_listas', 'scripts/gerar_listas.py')
    gerador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gerador)
    assert gerador.aplicar(pagina) == pagina, 'rode: python scripts/gerar_listas.py'


def test_classes_de_medicacao_sairam_dos_botoes(pagina):
    """No lugar de "Estatinas" e "Anti-hipertensivos", os 12 princípios ativos mais usados."""
    from src.utils import medicamentos
    assert 'id="estatinas"' not in pagina and 'id="anti_hipertensivos"' not in pagina
    assert len(medicamentos.MAIS_USADOS) == 12
    for chave in medicamentos.MAIS_USADOS:
        assert f'id="lista_medicacoes_{chave}" name="medicacoes" value="{chave}"' in pagina


@pytest.mark.parametrize('remedio, classe, marcadas', [
    ('losartana', 'ieca_bra', {'anti_hipertensivos', 'hipertensao'}),
    ('sinvastatina', 'estatina', {'estatinas', 'dislipidemia'}),
    ('glibenclamida', 'sulfonilureia', {'diabetes'}),
    ('losartana_hidroclorotiazida', 'tiazidico', {'anti_hipertensivos', 'hipertensao'}),
])
def test_principio_ativo_vale_pela_classe(client, remedio, classe, marcadas):
    from src.utils import medicamentos
    assert classe in medicamentos.classes_de([remedio])
    dados = dict(idade=55, sexo='masculino', tabagismo='nunca', comorbidades=[], medicacoes=[remedio],
                 historia_familiar=[], imunossupressao='nao', gestante='nao', lactante='nao')
    r = client.post('/api/checkup-intelligent', json=dados).get_json()
    assert marcadas <= {i['valor'] for i in r['inferencias']}, r['inferencias']


@pytest.mark.parametrize('dados, titulo', [
    (dict(idade=42, historia_familiar=['cancer_colorretal']), 'Colonoscopia'),
    (dict(idade=47, sexo='masculino', historia_familiar=['cancer_prostata']), 'PSA'),
    (dict(idade=35, medicacoes=['metformina']), 'B12'),
    (dict(idade=35, medicacoes=['levotiroxina']), 'TSH'),
    (dict(idade=35, medicacoes=['ieca_bra']), 'Potássio'),
    (dict(idade=35, medicacoes=['enalapril']), 'Potássio'),
    (dict(idade=60, medicacoes=['varfarina']), 'protrombina'),
    (dict(idade=60, medicacoes=['apixabana']), 'Creatinina'),
    (dict(idade=30, medicacoes=['quetiapina']), 'Glicose'),
    (dict(idade=55, medicacoes=['anastrozol']), 'Densitometria'),
    (dict(idade=40, comorbidades=['cirurgia_bariatrica']), 'Ferritina'),
    (dict(idade=40, historia_familiar=['hemocromatose']), 'transferrina'),
])
def test_itens_das_listas_acionam_exames(client, dados, titulo):
    base = dict(sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[], imunossupressao='nao',
                gestante='nao', lactante='nao')
    recs = client.post('/api/checkup-intelligent', json=dict(base, **dados)).get_json()['recommendations']
    assert any(titulo.lower() in r['titulo'].lower() for r in recs), [r['titulo'] for r in recs]


def test_hpv_a_cada_cinco_anos_e_citologia_a_cada_tres(client):
    base = dict(sexo='feminino', tabagismo='nunca', comorbidades=[], historia_familiar=[], imunossupressao='nao',
                gestante='nao', lactante='nao')
    def colo(idade):
        recs = client.post('/api/checkup-intelligent', json=dict(base, idade=idade)).get_json()['recommendations']
        return next(r for r in recs if 'HPV' in r['titulo'] or 'Papanicolaou' in r['titulo'])
    assert '3 anos' in str(colo(25)) and 'Papanicolaou' in colo(25)['titulo']
    assert '5 anos' in str(colo(40)) and 'HPV' in colo(40)['titulo']


def test_botoes_de_pdf_ficam_abaixo_das_recomendacoes(pagina):
    assert pagina.index('id="recommendationsContent"') < pagina.index('gerarPDFExamesLaboratoriais()"') < pagina.index('id="naoIncluidasContent"')


def test_check_up_nao_usa_o_atributo_das_listas_do_admin(pagina):
    """static/conta.js preenche todo [data-lista] com os cadastros (tela do admin). No check-up,
    isso apagava as listas com busca de quem é administrador ("Ninguém aqui.")."""
    assert 'data-lista' not in pagina


def test_triagem_de_vacinas_e_o_ultimo_topico_do_formulario(pagina):
    ordem = [pagina.index(f'id="{i}"') for i in ('s-identificacao', 's-clinicos', 's-comorbidades', 's-medicacoes',
                                                  's-familia', 's-habitos', 's-vacinas')]
    assert ordem == sorted(ordem)
    assert '<span class="secao-num">07</span>Triagem de segurança para vacinas' in pagina
    assert pagina.index('id="s-vacinas"') < pagina.index('Gerar recomendações')


def test_lista_nao_repete_o_que_ja_e_botao(pagina):
    import html as _html
    import re
    from src.utils.medicamentos import sem_acento
    nome = lambda t: sem_acento(_html.unescape(t)).split(' (')[0].strip()
    botoes = {nome(t) for t in re.findall(r'<label class="opcao" for="\w+"><input type="checkbox"[^>]*>([^<]+)</label>', pagina)}
    lista = {nome(t) for t in re.findall(r'<li role="option"[^>]*>([^<]+)</li>', pagina)}
    assert len(botoes) > 20 and not (botoes & lista), botoes & lista


def test_listas_suspensas_curtas_viram_botoes(pagina):
    assert "checkupForm.querySelectorAll('select')" in pagina and "setAttribute('role', 'radio')" in pagina


@pytest.mark.parametrize('dados, titulos', [
    (dict(idade=32, sexo='feminino', historia_familiar=['brca']), ['Ressonância magnética de mamas', 'Mamografia']),
    (dict(idade=45, sexo='masculino', historia_familiar=['brca']), ['PSA']),
    (dict(idade=30, sexo='feminino', historia_familiar=['li_fraumeni']),
     ['Ressonância magnética de corpo inteiro', 'Ressonância magnética de crânio', 'Ressonância magnética de mamas', 'Colonoscopia']),
    (dict(idade=28, sexo='masculino', historia_familiar=['lynch']), ['Colonoscopia']),
    (dict(idade=35, sexo='feminino', historia_familiar=['lynch']), ['Colonoscopia', 'Endoscopia digestiva alta']),
    (dict(idade=22, sexo='masculino', historia_familiar=['paf']), ['Colonoscopia', 'Endoscopia digestiva alta']),
    (dict(idade=35, sexo='feminino', historia_familiar=['cdh1']), ['Endoscopia digestiva alta', 'Ressonância magnética de mamas']),
    (dict(idade=42, sexo='feminino', historia_familiar=['cowden']), ['Ultrassonografia de tireoide', 'Colonoscopia', 'Ressonância magnética de mamas']),
    (dict(idade=30, sexo='masculino', historia_familiar=['nem1']), ['Paratormônio', 'Prolactina', 'Cálcio']),
    (dict(idade=30, sexo='masculino', historia_familiar=['nem2']), ['Calcitonina', 'Metanefrinas']),
    (dict(idade=30, sexo='masculino', historia_familiar=['cardiomiopatia_hipertrofica']), ['Ecocardiograma', 'Eletrocardiograma']),
    (dict(idade=30, sexo='masculino', historia_familiar=['aorta_toracica']), ['Ecocardiograma']),
    (dict(idade=30, sexo='masculino', historia_familiar=['aneurisma_cerebral']), ['Angiorressonância de crânio']),
    (dict(idade=30, sexo='masculino', historia_familiar=['alfa1']), ['Alfa-1 antitripsina']),
    (dict(idade=30, sexo='masculino', historia_familiar=['doenca_celiaca_familiar']), ['antitransglutaminase']),
])
def test_sindromes_hereditarias_trazem_o_rastreamento_especifico(client, dados, titulos):
    base = dict(tabagismo='nunca', comorbidades=[], imunossupressao='nao', gestante='nao', lactante='nao')
    r = client.post('/api/checkup-intelligent', json=dict(base, **dados)).get_json()
    recs = [x['titulo'] for x in r['recommendations']]
    for t in titulos:
        assert any(t.lower() in x.lower() for x in recs), (t, recs)
    assert r['orientacoes'] or dados['historia_familiar'][0] in ('aneurisma_cerebral', 'alfa1', 'doenca_celiaca_familiar')


def test_colonoscopia_de_lynch_nao_aparece_duas_vezes(client):
    dados = dict(idade=55, sexo='masculino', tabagismo='nunca', comorbidades=[], historia_familiar=['lynch'],
                 imunossupressao='nao', gestante='nao', lactante='nao')
    recs = client.post('/api/checkup-intelligent', json=dados).get_json()['recommendations']
    colo = [r for r in recs if 'colonoscopia' in r['titulo'].lower()]
    assert len(colo) == 1 and '1-2 anos' in colo[0]['descricao']


def test_escolha_manual_de_imunossupressao_nao_e_desfeita_pela_lista(pagina):
    """O clique no botão marca o evento como escolha do médico; a marcação automática só desfaz o que ela mesma fez."""
    assert 'ev.doUsuario = true' in pagina and 'e.isTrusted || e.doUsuario' in pagina


def test_tela_explica_o_que_nao_marcou_e_recusa_vale_por_fonte(pagina):
    """Medicação com outras indicações e PA elevada geram dica; a recusa de uma caixa vale só para as
    fontes que a pediam (um motivo novo volta a marcar)."""
    assert 'id="coerencia-dica"' in pagina and 'input[data-talvez]:checked' in pagina
    assert 'elevada pela AHA/ACC 2025' in pagina
    # sem a diastólica a tela pede o dado em vez de dizer que não é hipertensão (125/95 é estágio 2)
    assert 'informe a diastólica para classificar' in pagina and 'pad === null) frases.push' in pagina
    assert 'const recusados = new Map();' in pagina and "r[id].some(x => !fontes.has(x.fonte))" in pagina
    # os 12 botões: atenolol marca hipertensão e metformina marca diabetes
    import re
    for chave, caixa in (('atenolol', 'hipertensao'), ('metformina', 'diabetes'), ('losartana', 'hipertensao')):
        item = re.search(r'id="lista_medicacoes_%s"[^>]*>' % chave, pagina).group(0)
        assert f'data-marca="{caixa}"' in item, item


def test_home_mostra_a_evidencia_com_fonte_em_cada_numero():
    """Painel 'O que a evidência mostra': quatro números, cada um com a sua fonte clicável."""
    import pathlib
    home = pathlib.Path(__file__).resolve().parents[1].joinpath('index.html').read_text(encoding='utf-8')
    i = home.index('id="evidencia"'); painel = home[i:home.index('id="stats"')]
    assert 'É pedir os certos.' in painel
    for numero in ('21<span', '45<span', '76–101', '−36<span'):
        assert numero in painel, numero
    for fonte in ('https://doi.org/10.1371/journal.pone.0078962', 'https://doi.org/10.1001/jama.2019.13978',
                  'https://www.thelancet.com/journals/lanprc/article/PIIS3050-5143(26)00035-X/fulltext'):
        assert f'href="{fonte}" target="_blank" rel="noopener"' in painel, fonte
    # os números do painel são os do artigo, não os arredondados da matéria
    assert '20,6% de excesso e 44,8% de subutilização' in painel and 'US$ 75,7 a 101,2 bilhões' in painel
    # o painel vem depois da abertura da seção e antes dos três números da base
    assert home.index('A interface não precisa.') < i < home.index('01 — Reunir')
