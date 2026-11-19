"""Tela do cadastro de pacientes (fase 2): página /pacientes e seletor no check-up, só para o administrador.

A conta comum não vê nada: nem página, nem link, nem botão, nem seção. Os elementos do administrador são criados
por script, depois de a página saber quem está na sessão. Todos os dados destes testes são fictícios.
"""
import re
import sys
from pathlib import Path

import pytest

from src.utils import contas, i18n, pacientes

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))

import extrair_textos  # noqa: E402

SCRIPTS = ('static/pacientes.js', 'static/pacientes-checkup.js')
AVISO = 'Fase de testes: use apenas dados fictícios até a atualização dos Termos de Uso.'
CHAVE_FICTICIA = 'chave-ficticia-da-tela-do-cadastro-apenas-para-os-testes'
CABECALHO = {'X-Requested-With': 'evidens'}


def _ler(nome):
    return (RAIZ / nome).read_text(encoding='utf-8')


def _codigo(nome):
    """O script sem os comentários de linha (que citam, em prosa, o que o código não pode fazer)."""
    return re.sub(r'^\s*//.*$', '', _ler(nome), flags=re.M)


@pytest.fixture()
def com_chave():
    with pytest.MonkeyPatch.context() as remendo:
        remendo.setenv('PACIENTES_CHAVE', CHAVE_FICTICIA)
        yield


# --- Quem vê ---------------------------------------------------------------

def test_pagina_e_so_do_administrador(app, client, admin):
    resposta = admin.get('/pacientes')
    assert resposta.status_code == 200 and resposta.headers['Cache-Control'] == 'no-store'
    html = resposta.get_data(as_text=True)
    assert AVISO in html and 'data-pacientes' in html and '/static/pacientes.js' in html
    comum = client.get('/pacientes')                          # a médica comum volta ao check-up, como nas outras
    assert comum.status_code == 302 and comum.headers['Location'].endswith('/intelligent-tools')
    anonimo = app.test_client().get('/pacientes')
    assert anonimo.status_code == 302 and anonimo.headers['Location'].endswith('/login')
    for cliente in (admin, client, app.test_client()):
        assert cliente.get('/pacientes.html').status_code == 404     # só pela rota, que confere quem pede


def test_pagina_segue_a_mesma_regra_das_rotas(app, client, monkeypatch):
    """A página pergunta a `pacientes.habilitado_para`, como a API: no dia em que a regra abrir, as duas abrem."""
    monkeypatch.setattr(pacientes, 'habilitado_para', lambda usuario: bool(usuario))
    assert client.get('/pacientes').status_code == 200
    assert app.test_client().get('/pacientes').status_code == 302


@pytest.mark.parametrize('rota', ['/', '/intelligent-tools', '/conta', '/contact', '/cadastro', '/termos'])
def test_conta_comum_e_anonimo_nao_recebem_link_botao_nem_secao(app, client, rota):
    for cliente in (client, app.test_client()):
        html = cliente.get(rota, follow_redirects=True).get_data(as_text=True)
        for trecho in ('href="/pacientes"', '/static/pacientes', 'pacienteCadastrado', 'Paciente cadastrado',
                       'Salvar paciente no cadastro', '>Pacientes<', AVISO):
            assert trecho not in html, (rota, trecho)


def test_home_e_termos_nao_mudaram():
    """A home e os Termos continuam como estavam: não citam o cadastro nem carregam o script que cria o link."""
    for pagina in ('index.html', 'termos.html'):
        html = _ler(pagina)
        assert '/pacientes' not in html and 'conta.js' not in html and 'pacientes.js' not in html, pagina
    assert 'dados do paciente gravados' in _ler('index.html')


def test_link_botao_e_seletor_sao_criados_so_para_o_administrador():
    conta = _ler('static/conta.js')
    funcao = re.search(r'function abrirCadastroDePacientes\(usuario\) \{(.*?)\n  \}', conta, re.S).group(1)
    # a primeira linha da função recusa quem não é administrador (e o formulário embutido das operadoras)
    assert funcao.strip().startswith("if (!usuario || !usuario.administrador || document.documentElement.classList.contains('embutido')) return;")
    # fora dela, o script não cita o cadastro
    assert '/pacientes' not in _codigo('static/conta.js').replace(funcao, '')
    for trecho in ("link.href = '/pacientes'", "link.textContent = 'Pacientes'", "'/static/pacientes.js', '/static/pacientes-checkup.js'",
                   "document.getElementById('checkupForm')"):
        assert trecho in funcao, trecho
    # só é chamada com a resposta de /api/auth/eu, nas páginas de quem entrou (as que têm o botão "Sair" no menu)
    assert "if (document.querySelector('header nav [data-sair]')) quemSou().then(abrirCadastroDePacientes)" in conta
    # o check-up não carrega os scripts do cadastro por conta própria
    assert 'src="/static/pacientes' not in _ler('intelligent-tools.html') and 'href="/pacientes"' not in _ler('intelligent-tools.html')
    # o seletor não aparece no formulário embutido das operadoras nem duas vezes
    assert "tela.embutido" in _ler('static/pacientes-checkup.js')


def test_seletor_fica_no_inicio_da_identificacao():
    script = _codigo('static/pacientes-checkup.js')
    assert """document.querySelector('section[aria-labelledby="s-identificacao"]')""" in script
    assert "secao.insertBefore(bloco, secao.querySelector('.grade'))" in script
    for trecho in ("T('Paciente cadastrado')", "T('Salvar paciente no cadastro')", f"T('{AVISO}')"):
        assert trecho in script, trecho
    tela = _ler('intelligent-tools.html')
    secao = tela[tela.index('aria-labelledby="s-identificacao"'):tela.index('aria-labelledby="s-clinicos"')]
    assert secao.index('class="secao-nota"') < secao.index('<div class="grade">') < secao.index('id="nome_paciente"')


# --- Segurança da tela -----------------------------------------------------

@pytest.mark.parametrize('nome', SCRIPTS)
def test_scripts_nao_montam_html_nem_guardam_dado_no_navegador(nome):
    script = _codigo(nome)
    for proibido in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'DOMParser', 'createContextualFragment',
                     'localStorage', 'sessionStorage', 'indexedDB', 'document.cookie', 'URLSearchParams', 'location.search',
                     'location.hash', 'history.pushState', 'history.replaceState', 'eval(', 'new Function'):
        assert proibido not in script, (nome, proibido)
    # nenhum texto vai para o endereço: nada é concatenado depois de "?" e a busca não usa GET
    assert not re.search(r"""['"`][^'"`\n]*\?[^'"`\n]*=['"`]?\s*\+""", script), nome
    assert 'encodeURIComponent' not in script


def test_todo_pedido_leva_o_cabecalho_proprio():
    comum, checkup = _codigo('static/pacientes.js'), _codigo('static/pacientes-checkup.js')
    # um único fetch nos dois arquivos, dentro de `pedir`, que sempre manda o cabeçalho
    assert comum.count('fetch(') == 1 and 'fetch(' not in checkup and 'XMLHttpRequest' not in comum + checkup
    pedir = re.search(r'async function pedir\(caminho, corpo\) \{(.*?)\n  \}', comum, re.S).group(1)
    assert 'fetch(caminho, pedido)' in pedir and 'headers: Object.assign({}, CABECALHOS)' in pedir
    assert "const CABECALHOS = { 'X-Requested-With': 'evidens' };" in comum
    # a busca vai no corpo; a exportação é baixada pela resposta do fetch, não por um link para a rota
    assert "pedir(API + '/buscar', { busca: ultimaBusca })" in comum and "pedir(API + '/buscar', { busca: termo })" in checkup
    assert "pedir(caminhoDo(id, 'exportar'))" in comum and 'URL.createObjectURL(new Blob(' in comum
    assert '/exportar"' not in _ler('pacientes.html') and 'href="/api' not in _ler('pacientes.html')


@pytest.mark.parametrize('nome', SCRIPTS)
def test_dado_de_paciente_entra_por_textcontent_e_fica_fora_do_tradutor(nome):
    script = _codigo(nome)
    # `dado` é o único jeito de mostrar um valor do paciente: textContent, com data-i18n-manter
    fabrica = re.search(r'function dado\(tag, classe, texto\) \{(.*?)\n  \}', _codigo('static/pacientes.js'), re.S).group(1)
    assert "e.setAttribute('data-i18n-manter', '')" in fabrica
    for campo in ('nome', 'cns_final'):
        usos = re.findall(r'\b(\w+)\([^()\n]*\bp\.%s\b' % campo, script)
        assert usos and set(usos) <= {'dado'}, (nome, campo, usos)
    assert not re.search(r'\bel\([^()\n]*(paciente|vinculado)\.', script), nome


def test_ficha_clinica_nao_e_lida_nem_enviada_pela_tela():
    """Fase 2: só identificação. Nenhum dos scripts cita a `ficha`, nem os campos clínicos do formulário."""
    for nome in SCRIPTS:
        script = _codigo(nome)
        assert 'ficha' not in script.replace('data-ficha', '').replace('titulo-da-ficha', ''), nome
    checkup = _codigo('static/pacientes-checkup.js')
    for clinico in ('peso', 'altura', "'pas'", "'pad'", 'comorbidades', 'medicacoes', 'tabagismo', 'lerFormulario',
                    'currentRecommendations', 'apacAnamnese', 'apacExames', 'apacCid'):
        assert clinico not in checkup, clinico


# --- Campos e mensagens ----------------------------------------------------

def test_formulario_tem_os_campos_da_api_com_os_mesmos_limites():
    html, script = _ler('pacientes.html'), _codigo('static/pacientes.js')
    campos = [c for c in pacientes.CAMPOS if c not in ('planos', 'ficha')]
    assert sorted(re.findall(r'data-campo="(\w+)"', html)) == sorted(campos)
    assert re.search(r"const CAMPOS = \[(.*?)\];", script, re.S).group(1).replace('\n', ' ').replace("'", '').replace(' ', '').split(',') == campos
    for campo in campos:
        assert f'data-erro-de="{campo}"' in html, campo
        marca = re.search(r'<(?:input|select)[^>]*data-campo="%s"[^>]*>' % campo, html).group(0)
        if campo in pacientes.LIMITES:
            assert f'maxlength="{pacientes.LIMITES[campo]}"' in marca, campo
    for chave in pacientes.RACAS:
        assert f'<option value="{chave}">' in html
    for sexo in pacientes.SEXOS:
        assert f'<option value="{sexo}">' in html
    assert re.findall(r'<option value="([A-Z]{2})" data-i18n-manter>', html) == sorted(contas.UFS)
    for chave in pacientes.CAMPOS_DO_PLANO:
        assert f"'{chave}'" in script
    for arquivo in SCRIPTS:
        assert re.search(r'\bMAX_PLANOS = %d\b' % pacientes.MAX_PLANOS, _codigo(arquivo)), arquivo
    assert f"coluna('Operadora', 'operadora', {pacientes.LIMITES['operadora']}" in script
    assert f"coluna('Número da carteira', 'carteira', {pacientes.LIMITES['carteira']})" in script


def test_cada_recusa_da_api_tem_mensagem_propria():
    script = _codigo('static/pacientes.js')
    mensagens = re.search(r'function mensagemDeErro\(r\) \{(.*?)\n  \}', script, re.S).group(1)
    for trecho in ('r.status === 400', 'r.status === 403', 'r.status === 404', "d.codigo === 'duplicado'", "d.codigo === 'conflito'",
                   "d.codigo === 'limite'", 'r.status === 413', "r.status === 500 && d.codigo === 'ilegivel'",
                   "r.status === 503 && d.codigo === 'sem_chave'", 'r.status === 0'):
        assert trecho in mensagens, trecho
    assert "T('O cadastro de pacientes ainda não foi ativado nesta instalação.')" in mensagens
    # 400: uma frase embaixo de cada campo recusado; 409 duplicado: leva ao registro que já existe
    assert 'm.campos.forEach((nome, i) => erroNoCampo(nome, porCampo ? m.itens[i] : \'\'))' in script
    assert "T('Abrir o paciente que já existe')" in script
    # excluir só depois da confirmação na própria linha
    assert "else if (acao === 'excluir') pedirConfirmacao(cartao);" in script
    assert "else if (acao === 'confirmar-exclusao') { botao.disabled = true; excluir(id); }" in script
    assert script.count("'excluir'), {})") == 1


def test_aviso_de_fase_de_testes_fica_fixo_no_topo():
    html = _ler('pacientes.html')
    aviso = re.search(r'<p data-aviso-de-teste[^>]*>.*?</p>', html, re.S).group(0)
    assert AVISO in aviso and 'sticky' in aviso and 'aviso-atencao' in aviso
    assert html.index('data-aviso-de-teste') < html.index('<h1')


# --- Guarda de conferência do plano ----------------------------------------

def test_preencher_pelo_cadastro_nao_contorna_a_guarda_do_plano():
    tela = _ler('intelligent-tools.html')
    ponte = tela[tela.index('window.evidensCheckup = {'):tela.index('function preencherPlanos(seletor, lista)')]
    trocar = re.search(r'trocarDePaciente\(plano\) \{(.*?)\n            \},', ponte, re.S).group(1)
    # preencher o plano passa pela mesma função de qualquer troca de paciente, depois de pôr os valores na tela
    assert trocar.index('campoCarteira().value = plano.carteira') < trocar.index('pedirConfirmacaoDoPlano();')
    # a ponte só lê a guarda: não a baixa nem chama o que vale como confirmação do médico
    for proibido in ('planoAConfirmar =', 'planoEditado(', 'confirmarPlano(', 'limparGuia('):
        assert proibido not in ponte, proibido
    assert 'planoPendente: () => planoAConfirmar,' in ponte
    script = _codigo('static/pacientes-checkup.js')
    for proibido in ('planoAConfirmar', 'planoEditado', 'confirmarPlano', 'limparGuia', 'guiaManter', "getElementById('planoManter').click",
                     '.click()'):
        assert proibido not in script, proibido
    preencher = re.search(r'function preencher\(paciente\) \{(.*?)\n  \}', script, re.S).group(1)
    # a troca de paciente (que apaga o laudo de APAC do anterior) vem antes de preencher o laudo do novo
    assert preencher.index('tela.trocarDePaciente(plano)') < preencher.index("definir('apacCns'")
    # com a guarda de pé, o plano e a carteira não são gravados no cadastro
    salvar = script[script.index("salvar.addEventListener('click'"):]
    assert salvar.index('if (plano && tela.planoPendente())') < salvar.index('dados.planos = planos;') < salvar.index('pedir(atual ? caminhoDo(atual.id) : API, dados)')


def test_salvar_pelo_check_up_so_envia_o_que_esta_preenchido():
    """Campo em branco na tela não apaga o que o cadastro tem (o laudo de APAC é limpo a cada troca de paciente)."""
    script = _codigo('static/pacientes-checkup.js')
    assert "const por = (campo, valor, rotulo) => { if (valor) { dados[campo] = valor; rotulos.push(T(rotulo)); } };" in script
    enviados = set(re.findall(r"\bpor\('(\w+)'", script)) | {'ibge', 'planos'}
    assert enviados == {'nome', 'sexo', 'nascimento', 'cns', 'mae', 'telefone', 'cep', 'endereco', 'municipio', 'uf', 'ibge', 'planos'}
    assert enviados <= set(pacientes.CAMPOS)
    assert 'window.confirm(' in script        # nome diferente do paciente escolhido: confirma antes de atualizar


def test_api_aceita_o_que_a_tela_envia(admin, com_chave):
    """A página manda todos os campos de identificação (vazios inclusive); o check-up, só os preenchidos."""
    ident = [c for c in pacientes.CAMPOS if c not in ('planos', 'ficha')]
    novo = admin.post('/api/pacientes', headers=CABECALHO, json={**{c: '' for c in ident}, 'nome': 'Paciente Fictícia da Tela', 'planos': [],
                                                                 'nascimento': '1970-02-03', 'prontuario': 'TELA-1'})
    assert novo.status_code == 201, novo.get_data(as_text=True)
    pid = novo.get_json()['paciente']['id']
    try:
        parcial = admin.post(f'/api/pacientes/{pid}', headers=CABECALHO, json={
            'nome': 'Paciente Fictícia da Tela', 'sexo': 'feminino',
            'planos': [{'operadora': 'Plano Inventado', 'carteira': '000111', 'validade': ''}]})
        assert parcial.status_code == 200
        salvo = parcial.get_json()['paciente']
        assert salvo['prontuario'] == 'TELA-1' and salvo['nascimento'] == '1970-02-03' and salvo['sexo'] == 'feminino'
        assert salvo['planos'] == [{'operadora': 'Plano Inventado', 'carteira': '000111', 'validade': ''}] and salvo['ficha'] == {}
        assert admin.post('/api/pacientes/buscar', json={'busca': 'ficticia da tela'}).status_code == 403     # sem o cabeçalho
    finally:
        assert admin.post(f'/api/pacientes/{pid}/excluir', headers=CABECALHO, json={}).status_code == 200


# --- Publicação, estilo e inglês -------------------------------------------

def test_scripts_sao_publicados_e_o_css_cobre_a_tela(client):
    for nome in SCRIPTS:
        assert client.get('/' + nome).status_code == 200
    config = _ler('tailwind.config.js')
    for arquivo in ('./pacientes.html', './static/pacientes.js', './static/pacientes-checkup.js'):
        assert arquivo in config, arquivo
    css = _ler('static/evidens.css')
    assert '[aria-invalid=true]' in css.replace('"', '') and '.sticky' in css
    html = _ler('pacientes.html')
    assert '/static/evidens.css' in html and 'cdn.tailwindcss.com' not in html and 'name="robots" content="noindex"' in html
    assert 'pacientes.html' in extrair_textos.PAGINAS
    assert "pacientes: '/pacientes'" in _ler('static/termos.js')      # aceite pendente volta para a página


_FORA_DA_TELA = {'X-Requested-With', 'Content-Type', 'X-Evidens-Termos', 'Enter'}
_ROTULOS_MINUSCULOS = ('nome', 'sexo', 'nascimento', 'nome da mãe', 'telefone', 'endereço', 'município', 'plano e carteira',
                       'MM/AAAA', 'CNS', 'CEP', 'UF', 'Pacientes')


@pytest.mark.parametrize('nome', SCRIPTS + ('static/conta.js',))
def test_toda_frase_dos_scripts_tem_par_em_ingles(nome):
    script = _codigo(nome)
    if nome == 'static/conta.js':
        script = re.search(r'function abrirCadastroDePacientes\(usuario\) \{(.*?)\n  \}', script, re.S).group(1)
    frases = [' '.join(f.split()) for f in re.findall(r"'((?:[^'\\\n]|\\.)*)'", script)]
    visiveis = [f for f in frases if re.match(r'[A-ZÀ-Ý"(]', f) and re.search(r'[a-zà-ÿ]{2}', f) and f not in _FORA_DA_TELA]
    assert len(visiveis) >= (1 if nome == 'static/conta.js' else 20)
    faltando = [f for f in visiveis + list(_ROTULOS_MINUSCULOS) if not i18n.coberto(f)]
    assert not faltando, faltando
    assert '`' not in re.sub(r'`[^`\n]*\$\{[^`\n]*`', '', script) or nome == 'static/conta.js'      # crase só em texto montado, sem frase


def test_frases_fixas_do_400_tem_par_em_ingles():
    """No 400 a tela mostra a frase do servidor embaixo do campo: em inglês ela não pode sair pela metade."""
    ruins = {'nome': 'x', 'nascimento': '2999-01-01', 'sexo': 'x', 'cpf': '111', 'cns': '1', 'raca': 'x', 'email': 'x', 'cep': '1',
             'ibge': '1', 'uf': 'XX'}
    with pytest.raises(pacientes.DadosInvalidos) as recusa:
        pacientes.validar(ruins)
    assert recusa.value.campos == list(ruins) and len(recusa.value.erros) == len(ruins)
    frases = list(recusa.value.erros)
    for planos in ([{'operadora': ''}], [{'operadora': 'Plano Inventado', 'validade': '12/2027'}], [{'x': 1}], 'x',
                   [{'operadora': 'Plano Inventado'}] * (pacientes.MAX_PLANOS + 1)):
        with pytest.raises(pacientes.DadosInvalidos) as recusa:
            pacientes.validar({'nome': 'Paciente Fictício', 'planos': planos})
        frases += recusa.value.erros
    for dados in ({'nome': 'Paciente Fictício', 'outro': 1}, 'x'):
        with pytest.raises(pacientes.DadosInvalidos) as recusa:
            pacientes.validar(dados)
        frases += recusa.value.erros
    faltando = sorted({f for f in frases if not i18n.coberto(f)})
    assert not faltando, faltando


def test_documentacao_descreve_a_tela():
    doc = _ler('docs/pacientes.md')
    for trecho in ('## Tela', '`/pacientes`', 'static/pacientes.js', 'static/pacientes-checkup.js', 'window.evidensCheckup',
                   'planoAConfirmar', 'textContent', AVISO, 'tests/test_pacientes_tela.py'):
        assert trecho in doc, trecho
