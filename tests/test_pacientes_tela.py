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
    trocar = re.search(r'trocarDePaciente\(plano, semPlano\) \{(.*?)\n            \},', ponte, re.S).group(1)
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
    assert preencher.index('tela.trocarDePaciente(plano, !plano)') < preencher.index('preencherApac(paciente)')
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
    # nome diferente do paciente escolhido: o vínculo é solto e o registro dele não é sobrescrito
    salvar = script[script.index("salvar.addEventListener('click'"):]
    assert salvar.index('if (vinculado && !mesmoNome(vinculado.nome, dados.nome)) { soltarVinculo(') < salvar.index('await pedir(')


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


# --- Correções da revisão: o que a tela não pode voltar a fazer ---------------
# O comportamento é conferido em navegador por scripts/conferir_pacientes_tela.py (o repositório não tem teste de
# navegador). Estes testes travam, no código, cada correção.

def _trecho(texto, inicio, fim):
    return texto[texto.index(inicio):texto.index(fim, texto.index(inicio))]


def test_nome_alterado_limpa_a_apac_com_ou_sem_resultado_na_tela():
    """C1 (a): o laudo de APAC pode ter vindo do cadastro antes de haver resultado; o nome novo o limpa sempre."""
    tela = _ler('intelligent-tools.html')
    funcao = _trecho(tela, 'function semEfeitoNasRecomendacoes(evento) {', 'function invalidarResultados(evento) {')
    limpa = "if (campo.id === 'nome_paciente' && apacPreenchida()) limparApac();"
    assert limpa in funcao
    # fora (e antes) da condição que depende de haver resultado na tela, e para qualquer tipo de evento
    assert funcao.index(limpa) < funcao.index("recommendationsDiv.style.display === 'block'")
    linha = [l for l in funcao.split('\n') if 'limparApac()' in l]
    assert len(linha) == 1 and 'evento.type' not in linha[0] and 'style.display' not in linha[0]
    assert "const apacPreenchida = () => CAMPOS_DA_APAC.some(id => document.getElementById(id).value.trim() !== '');" in tela
    assert "checkupForm.addEventListener('input', invalidarResultados);" in tela
    assert "checkupForm.addEventListener('change', invalidarResultados);" in tela


def test_nome_diferente_do_vinculo_solta_o_vinculo_a_vista():
    """C1 (b): com paciente escolhido, o nome digitado diferente tem o mesmo efeito de "Limpar seleção"."""
    script = _codigo('static/pacientes-checkup.js')
    ouvinte = _trecho(script, "['input', 'change'].forEach(tipo => porId('nome_paciente').addEventListener(tipo", '}));')
    assert 'if (preenchendo) return;' in ouvinte                       # o próprio seletor escrevendo não conta
    assert 'if (vinculado && !mesmoNome(nomeNaTela(), vinculado.nome)) soltarVinculo(T(SOLTO_PELO_NOME));' in ouvinte
    soltar = re.search(r'function soltarVinculo\(texto\) \{(.*?)\n  \}', script, re.S).group(1)
    for passo in ('vinculado = null;', 'tela.trocarDePaciente(null);', "tela.enderecoDoCadastro('', '');", 'mostrarVinculo();', 'dizer(texto);'):
        assert passo in soltar, passo
    assert "soltar.addEventListener('click', () => soltarVinculo(" in script       # o mesmo caminho do botão
    # o botão "Limpar seleção" some de verdade (a classe do botão tem display próprio)
    assert "soltar.style.display = vinculado ? '' : 'none';" in script
    # o seletor escreve nos campos com a marca levantada, e a baixa mesmo se algo falhar
    preencher = re.search(r'function preencher\(paciente\) \{(.*?)\n  \}', script, re.S).group(1)
    assert preencher.index('preenchendo = true;') < preencher.index("definir('nome_paciente'") < preencher.index('preenchendo = false;')
    assert 'finally' in preencher


def test_pdf_tem_guarda_propria_contra_apac_de_outro_paciente():
    """C1 (c): vínculo do cadastro com outro nome na tela: o pedido não leva os dados do paciente do cadastro."""
    tela = _ler('intelligent-tools.html')
    divergente = re.search(r'function vinculoDivergente\(\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert 'ponte.nomeDoVinculo()' in divergente and "document.getElementById('nome_paciente').value" in divergente
    apac = _trecho(tela, 'function apacDoDialogo(categoria) {', 'function guiaDoDialogo() {')
    assert apac.index('if (!vinculoDivergente()) {') < apac.index("['cns', 'apacCns']") < apac.index('return { vinculo_id:')
    gerar = _trecho(tela, "document.getElementById('acrescimoGerar').addEventListener('click'", 'const doc = DOCUMENTOS[categoria];')
    barra = gerar.index("if (categoria !== 'vacina' && vinculoDivergente()) {")
    assert barra < gerar.index('guiaDoDialogo()')
    assert tela.index("if (categoria !== 'vacina' && vinculoDivergente()) {") < tela.index("const apac = categoria === 'vacina' ? null : apacDoDialogo(categoria);")
    bloco = gerar[barra:gerar.index('const guia =')]
    for passo in ('ponte.soltarVinculo()', 'pedirConfirmacaoDoPlano();', 'alert(T(', 'return;'):
        assert passo in bloco, passo
    script = _codigo('static/pacientes-checkup.js')
    assert "tela.nomeDoVinculo = () => (vinculado ? vinculado.nome : '');" in script
    assert 'tela.soltarVinculo = () => { if (vinculado) soltarVinculo(T(SOLTO_PELO_NOME)); };' in script


def test_troca_de_paciente_avisa_dos_dados_clinicos_e_oferece_limpar():
    """A1: o cadastro só traz identificação; comorbidades, medicações, exames e hábitos do anterior ficam na tela."""
    script = _codigo('static/pacientes-checkup.js')
    preencher = re.search(r'function preencher\(paciente\) \{(.*?)\n  \}', script, re.S).group(1)
    assert 'const anterior = vinculado ? vinculado.id !== paciente.id' in preencher
    assert preencher.index('const clinicosDoAnterior = anterior && tela.temDadosClinicos();') < preencher.index('vinculado = paciente;')
    assert "dizer(partes.join(' '), false, clinicosDoAnterior);" in preencher
    dizer = re.search(r'function dizer\(texto, erro, clinicos\) \{(.*?)\n  \}', script, re.S).group(1)
    for trecho in ("T('Os dados clínicos na tela são do paciente anterior.')", "T('Limpar dados clínicos')", "limpar.id = 'pacienteLimparClinicos';",
                   'tela.limparDadosClinicos();'):
        assert trecho in dizer, trecho
    # a limpeza é a da página: o reset do formulário, com a identificação reposta e os ouvintes avisados
    tela = _ler('intelligent-tools.html')
    limpar = re.search(r'function limparDadosClinicos\(\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert limpar.index('checkupForm.reset();') < limpar.index('identificacao.forEach(([campo, valor]) => { campo.value = valor; });')
    assert "new Event(tipo, { bubbles: true })" in limpar and ".exame-anterior .exame-retirar" in limpar
    assert "const CAMPOS_DE_IDENTIFICACAO = ['nome_paciente', 'idade', 'sexo', 'pacientePlano', 'pacienteCarteira'];" in tela
    ponte = _trecho(tela, 'window.evidensCheckup = {', 'function preencherPlanos(seletor, lista)')
    assert 'temDadosClinicos,' in ponte and 'limparDadosClinicos,' in ponte


def test_resposta_atrasada_nao_refaz_o_vinculo():
    """M1: salvar e escolher guardam a rodada antes do pedido e descartam a resposta se a seleção mudou."""
    script = _codigo('static/pacientes-checkup.js')
    clique = _trecho(script, "resultados.addEventListener('click'", 'preencher(r.dados.paciente);')
    assert clique.index('const minha = ++selecao;') < clique.index('await pedir(') < clique.index('if (minha !== selecao) return;')
    assert 'if (!botao || salvando) return;' in clique
    salvar = script[script.index("salvar.addEventListener('click'"):]
    assert salvar.index('const minha = selecao;') < salvar.index('ocupar(true);') < salvar.index('await pedir(')
    assert salvar.index('const mudou = minha !== selecao;') < salvar.index('vinculado = r.dados.paciente;')
    assert 'if (mudou || !mesmoNome(nomeNaTela(), r.dados.paciente.nome)) {' in salvar
    assert salvar.index('} finally {') < salvar.index('ocupar(false);')
    ocupar = re.search(r'function ocupar\(sim\) \{(.*?)\n  \}', script, re.S).group(1)
    assert 'salvar.disabled = busca.disabled = sim;' in ocupar and "button[data-paciente]').forEach(b => { b.disabled = sim; });" in ocupar
    for muda in ('function soltarVinculo(texto) {\n    selecao += 1;', 'selecao += 1;\n    vinculado = paciente;'):
        assert muda in script, muda


def test_apac_do_vinculo_volta_depois_de_uma_limpeza_do_mesmo_paciente():
    """M2: dado clínico alterado com resultado na tela limpa o laudo; com o vínculo e o mesmo nome, ele é reposto."""
    tela = _ler('intelligent-tools.html')
    limpar = re.search(r'function limparApac\(\) \{(.*?)\n        \}', tela, re.S).group(1)
    assert limpar.index("CAMPOS_DA_APAC.forEach(id => { document.getElementById(id).value = ''; });") < limpar.index('ponte.aoLimparApac();')
    script = _codigo('static/pacientes-checkup.js')
    volta = _trecho(script, 'tela.aoLimparApac = () => {', '};')
    assert 'if (!vinculado || preenchendo || !mesmoNome(nomeNaTela(), vinculado.nome)) return;' in volta
    assert 'preencherApac(vinculado);' in volta
    for clinico in ('apacAnamnese', 'apacExames', 'apacCid'):        # o que é clínico no laudo não volta do cadastro
        assert clinico not in script


def test_plano_do_paciente_anterior_sai_quando_o_cadastro_nao_traz_plano():
    """M3: sem plano que sirva no cadastro do paciente escolhido, o plano e a carteira da tela são de outro."""
    tela = _ler('intelligent-tools.html')
    ponte = _trecho(tela, 'window.evidensCheckup = {', 'function preencherPlanos(seletor, lista)')
    trocar = re.search(r'trocarDePaciente\(plano, semPlano\) \{(.*?)\n            \},', ponte, re.S).group(1)
    ramo = _trecho(trocar, '} else if (semPlano) {', 'if (plano || semPlano) {')
    assert "if (!ehSus(campoPlano().value)) campoPlano().value = '';" in ramo and "campoCarteira().value = '';" in ramo
    assert trocar.index('} else if (semPlano) {') < trocar.index('pedirConfirmacaoDoPlano();')
    script = _codigo('static/pacientes-checkup.js')
    assert 'tela.trocarDePaciente(plano, !plano);' in script
    assert 'tela.trocarDePaciente(null);' in script                    # "Limpar seleção" não apaga o plano: sobe a guarda


def test_sessao_terminada_no_check_up_nao_descarta_o_formulario():
    """M4: no check-up o 401 do cadastro vira aviso; os Termos voltam para a página de origem."""
    script = _codigo('static/pacientes.js')
    pedir = re.search(r'async function pedir\(caminho, corpo\) \{(.*?)\n  \}', script, re.S).group(1)
    assert "const NO_CHECKUP = !document.querySelector('[data-pacientes]');" in script
    assert "if (resposta.status === 401) { if (!NO_CHECKUP) window.location.href = '/login'; }" in pedir
    assert "NO_CHECKUP ? '/termos?aceitar=1&destino=check-up' : '/termos?aceitar=1&destino=pacientes'" in pedir
    assert 'semVoltarAoLogin: NO_CHECKUP' in pedir
    assert "T(NO_CHECKUP ? 'A sessão terminou. Entre de novo em outra aba e repita.' : 'A sessão terminou. Entre de novo.')" in script
    tela = _ler('intelligent-tools.html')
    vigia = _trecho(tela, 'window.fetch = async function (...args) {', '};')
    assert 'const ficaNaPagina = !!(args[1] && args[1].semVoltarAoLogin);' in vigia
    assert "if (!ficaNaPagina) window.location.href = '/login?destino=check-up';" in vigia
    assert "window.location.href = '/termos?aceitar=1&destino=check-up';" in vigia
    termos = _ler('static/termos.js')
    assert "'check-up': '/intelligent-tools'" in termos and "pacientes: '/pacientes'" in termos


def test_edicao_envia_a_versao_lida_e_a_tela_explica_o_conflito():
    """M5: o formulário de /pacientes (e o "Salvar" do check-up) mandam o `atualizado_em` lido; o 409 tem frase."""
    script = _codigo('static/pacientes.js')
    assert 'versaoEmEdicao = paciente && Number.isFinite(Number(paciente.atualizado_em)) ? Number(paciente.atualizado_em) : null;' in script
    envio = _trecho(script, "formulario.addEventListener('submit'", 'if (r.ok) {')
    assert envio.index('if (editando !== null && versaoEmEdicao !== null) dados.atualizado_em = versaoEmEdicao;') < envio.index('await pedir(')
    assert "T('Este cadastro foi alterado em outro lugar. Reabra e repita a alteração.')" in script
    checkup = _codigo('static/pacientes-checkup.js')
    salvar = checkup[checkup.index("salvar.addEventListener('click'"):]
    assert salvar.index('dados.atualizado_em = Number(atual.atualizado_em);') < salvar.index('pedir(atual ? caminhoDo(atual.id) : API, dados)')


def test_datas_da_tela_usam_o_relogio_local():
    """B2 e B4: nada de toISOString (UTC) para saber que dia é hoje."""
    for nome in SCRIPTS:
        assert 'toISOString' not in _codigo(nome), nome
    script = _codigo('static/pacientes.js')
    assert "campo('nascimento').max = hojeLocal();" in script
    hoje = re.search(r'function hojeLocal\(\) \{(.*?)\n  \}', script, re.S).group(1)
    assert 'getFullYear()' in hoje and 'getMonth() + 1' in hoje and 'getDate()' in hoje and 'UTC' not in hoje
    checkup = _codigo('static/pacientes-checkup.js')
    assert "T('A validade da carteira no cadastro venceu em') + ' ' + venceu + '.'" in checkup
    assert 'hojeLocal()' in re.search(r'function validadeVencida\(validade\) \{(.*?)\n  \}', checkup, re.S).group(1)


def test_cep_do_cadastro_sem_ibge_nao_conta_como_buscado():
    """B3: sem o código IBGE no cadastro, a busca de sempre do CEP acontece."""
    tela = _ler('intelligent-tools.html')
    assert "enderecoDoCadastro(cep, ibge) { cepBuscado = ibge ? cep : ''; apacIbge = ibge || ''; }," in tela
    script = _codigo('static/pacientes-checkup.js')
    apac = re.search(r'function preencherApac\(paciente\) \{(.*?)\n  \}', script, re.S).group(1)
    assert apac.index('tela.enderecoDoCadastro(cep, soDigitos(paciente.ibge, 7));') < apac.index("definir('apacCep', cep);")
    assert apac.index("definir('apacEndereco'") < apac.index("definir('apacCep', cep);")      # a busca não troca o endereço


def test_acessibilidade_dos_erros_do_icone_e_do_vinculo():
    """B5."""
    html = _ler('pacientes.html')
    campos = re.findall(r'data-campo="(\w+)" aria-describedby="p_erro_(\w+)"', html)
    assert len(campos) == 17 and all(a == b for a, b in campos)
    for nome, _ in campos:
        assert f'<p id="p_erro_{nome}" data-erro-de="{nome}"' in html, nome
    assert len(re.findall(r'data-campo="', html)) == 17
    conta = _codigo('static/conta.js')
    cadastro = re.search(r'function abrirCadastroDePacientes\(usuario\) \{(.*?)\n  \}', conta, re.S).group(1)
    assert "icone.className = 'fa-solid fa-address-book text-[12px]'; icone.setAttribute('aria-hidden', 'true');" in cadastro
    assert "escolhido.setAttribute('aria-live', 'polite');" in _codigo('static/pacientes-checkup.js')


def test_exemplo_de_operadora_tem_par_em_ingles():
    """B6: o exemplo do campo da operadora é traduzido como os outros exemplos ("Ex: …" → "E.g. …")."""
    assert i18n.traduzir('Ex: Unimed Goiânia') == 'E.g. Unimed Goiânia'


def test_roteiro_de_navegador_esta_versionado_sem_chave_nem_dado_real():
    """A2: sem infraestrutura de navegador na suíte, o roteiro fica em scripts/ e a documentação o exige."""
    roteiro = _ler('scripts/conferir_pacientes_tela.py')
    assert "'PACIENTES_CHAVE': secrets.token_hex(32)" in roteiro           # sorteada na hora, só no ambiente do filho
    assert not re.search(r"PACIENTES_CHAVE['\"]?\s*[:=]\s*['\"]", roteiro)   # nenhuma chave escrita no arquivo
    assert 'tempfile.mkdtemp(' in roteiro and "'sqlite:///'" in roteiro
    assert "contexto.route('https://viacep.com.br/**'" in roteiro            # nada sai da máquina
    for cenario in ('c1_apac_de_outro_paciente', 'c1_guarda_da_geracao', 'a1_troca_de_paciente', 'conta_comum', 'm1_corrida_no_salvar',
                    'm2_dado_clinico_do_mesmo_paciente', 'm4_sessao_expirada', 'm5_edicao_concorrente', 'b3_b4_cep_e_validade'):
        assert f'async def {cenario}(' in roteiro, cenario
    for nome in ('requirements.txt', 'requirements-dev.txt'):
        arquivo = RAIZ / nome
        assert not arquivo.exists() or 'playwright' not in arquivo.read_text(encoding='utf-8').lower()
    doc = _ler('docs/pacientes.md')
    assert 'scripts/conferir_pacientes_tela.py' in doc and 'obrigatória' in doc
