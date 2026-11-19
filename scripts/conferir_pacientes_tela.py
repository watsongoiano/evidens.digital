"""Conferência da tela do cadastro de pacientes em navegador de verdade (docs/pacientes.md, "Conferência no navegador").

O repositório não tem teste de navegador: a suíte só lê o código das telas. Este roteiro cobre o que ela não
alcança (o comportamento do seletor do check-up e da página /pacientes) e é obrigatório antes de cada mudança
nessas telas. Não entra na suíte nem nas dependências do projeto.

Uso (fora da hospedagem, numa máquina de desenvolvimento):

    python scripts/conferir_pacientes_tela.py [--capturas PASTA] [--chrome /caminho/do/chrome]

Precisa de `playwright` instalado no Python que roda o roteiro (não está em requirements.txt, de propósito) e de
um Chrome/Chromium. O roteiro sobe o próprio servidor, num banco sqlite temporário, com uma PACIENTES_CHAVE
sorteada na hora e só na memória do processo: nenhuma chave fica em arquivo e nenhum banco real é tocado. Todos
os pacientes são inventados aqui. O ViaCEP e a lista de exames em APAC são simulados: nada sai da máquina.

Sai com código 0 se tudo conferiu; senão lista as falhas e sai com 1.
"""
import argparse
import asyncio
import importlib.util
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date, datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENHA = 'senha-de-conferencia-123456'
ADMIN, COMUM = 'admin-conferencia@exemplo.test', 'medica-conferencia@exemplo.test'


# ── Servidor de conferência (processo filho) ────────────────────────────────────

def servir(porta):
    """Sobe a aplicação com duas contas inventadas (administrador e médica comum), já com os Termos aceitos."""
    sys.path.insert(0, RAIZ)
    os.chdir(RAIZ)
    spec = importlib.util.spec_from_file_location('evidens_api_index', os.path.join(RAIZ, 'api', 'index.py'))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    from src.utils import contas, termos
    with modulo.app.app_context():
        admin = contas.criar(ADMIN, 'Administrador de Conferência', 'CRM-GO 11111', 'medico', SENHA, administrador=True)
        contas.registrar_aceite(admin['id'], termos.VERSAO)
        comum = contas.criar(COMUM, 'Médica de Conferência', 'CRM-GO 22222', 'medico', SENHA)
        contas.registrar_aceite(comum['id'], termos.VERSAO)
        contas.definir_situacao(comum['id'], 'aprovado')
    modulo.app.run(host='127.0.0.1', port=porta, debug=False)


def subir_servidor():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        porta = s.getsockname()[1]
    pasta = tempfile.mkdtemp(prefix='evidens-conferencia-')
    ambiente = dict(os.environ)
    ambiente.pop('VERCEL', None)
    ambiente.update({
        'DATABASE_URL': 'sqlite:///' + os.path.join(pasta, 'contas.sqlite'),
        'SECRET_KEY': secrets.token_hex(32),
        'SETUP_TOKEN': secrets.token_hex(8),
        'PACIENTES_CHAVE': secrets.token_hex(32),      # sorteada a cada execução; nunca vai para arquivo
    })
    registro = open(os.path.join(pasta, 'servidor.log'), 'w')
    filho = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--servir', str(porta)], env=ambiente,
                             stdout=registro, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{porta}'
    for _ in range(80):
        try:
            urllib.request.urlopen(base + '/login', timeout=1)
            return filho, base
        except Exception:
            if filho.poll() is not None:
                break
            time.sleep(0.25)
    filho.kill()
    raise SystemExit('O servidor de conferência não subiu: veja ' + registro.name)


# ── Dados inventados ────────────────────────────────────────────────────────────

def cns(n):
    corpo = '2' + f'{31415926 + n:010d}'
    for final in range(10 ** 4):
        numero = corpo + f'{final:04d}'
        if sum(int(d) * (15 - i) for i, d in enumerate(numero)) % 11 == 0:
            return numero


CNS_A, CNS_MEDICO = cns(1), cns(2)
PACIENTE_A = {'nome': 'Maria Fictícia da Silva', 'nascimento': '1961-03-15', 'sexo': 'feminino', 'cns': CNS_A,
              'mae': 'Ana Fictícia da Silva', 'telefone': '(62) 99999-0000', 'cep': '74000000', 'ibge': '5208707',
              'endereco': 'Rua Inventada, nº 10, Centro', 'municipio': 'Goiânia', 'uf': 'GO',
              'planos': [{'operadora': 'Unimed Goiânia', 'carteira': '0012345678', 'validade': '2031-12'}]}
PACIENTE_B = {'nome': 'João Inventado Pereira', 'nascimento': '1978-07-02', 'sexo': 'masculino'}
PACIENTE_C = {'nome': 'Carla Modelo de Souza', 'nascimento': '1970-01-20', 'sexo': 'feminino', 'cep': '74000000',
              'planos': [{'operadora': 'Unimed Goiânia', 'carteira': '5550001', 'validade': '2024-01'}]}
DADOS_DE_A = [CNS_A, 'Ana Fictícia', '15/03/1961', '99999-0000', 'Rua Inventada', '74000']

falhas = []


def ok(rotulo, condicao, extra=''):
    print(('OK    ' if condicao else 'FALHA ') + rotulo + (f'  [{extra}]' if extra != '' else ''))
    if not condicao:
        falhas.append(rotulo)


CHAMAR = """async ([caminho, corpo]) => {
    const r = await fetch(caminho, { method: corpo === null ? 'GET' : 'POST', credentials: 'same-origin',
        headers: { 'X-Requested-With': 'evidens', 'Content-Type': 'application/json' },
        body: corpo === null ? undefined : JSON.stringify(corpo) });
    let dados = null; try { dados = await r.json(); } catch (e) {}
    return { status: r.status, dados };
}"""


async def entrar(contexto, base, email):
    pagina = await contexto.new_page()
    await pagina.goto(base + '/login')
    await pagina.fill('input[name=email]', email)
    await pagina.fill('input[name=senha]', SENHA)
    await pagina.click('button[type=submit]')
    await pagina.wait_for_url('**/intelligent-tools')
    return pagina


async def simular_rede(contexto):
    """Nada sai da máquina: ViaCEP inventado; a lista de exames em APAC falha (o servidor é quem decide)."""
    consultas = []

    async def viacep(rota):
        consultas.append(rota.request.url)
        await rota.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'cep': '74000-000', 'logradouro': 'Rua Simulada', 'bairro': 'Centro', 'localidade': 'Goiânia', 'uf': 'GO',
             'ibge': '5208707'}), headers={'Access-Control-Allow-Origin': '*'})
    await contexto.route('https://viacep.com.br/**', viacep)
    await contexto.route('**/api/apac/exames', lambda rota: rota.fulfill(status=503, body='{}'))
    return consultas


async def abrir_checkup(pagina, base, idioma=''):
    await pagina.goto(base + '/intelligent-tools' + idioma)
    await pagina.wait_for_selector('#pacienteCadastrado')
    await pagina.wait_for_function("document.getElementById('pacientePlano').options.length > 1")


async def escolher(pagina, termo, nome):
    await pagina.fill('#pacienteBusca', termo)
    await pagina.wait_for_selector('#pacienteResultados button:not([disabled])')
    await pagina.click('#pacienteResultados button')
    await pagina.wait_for_function("n => document.getElementById('nome_paciente').value === n", arg=nome)
    await pagina.wait_for_timeout(150)


async def gerar(pagina):
    await pagina.click('#checkupForm button[type=submit]')
    await pagina.wait_for_function("document.getElementById('recommendations').style.display === 'block'", timeout=30000)


APAC_NA_TELA = """() => Object.fromEntries(['apacCns', 'apacNascimento', 'apacMae', 'apacTelefone', 'apacCep', 'apacEndereco',
    'apacMunicipio', 'apacUf'].map(id => [id, document.getElementById(id).value]))"""
VINCULO = "document.getElementById('pacienteVinculado').hidden ? '' : document.getElementById('pacienteVinculado').textContent"


async def pedir_pdf_de_imagem(pagina):
    """Abre o diálogo do pedido de exames de imagem e manda gerar; devolve o corpo do POST, ou None se não saiu."""
    corpos = []
    ouvir = lambda pedido: corpos.append(pedido.post_data) if 'gerar-pdf-exames-imagem' in pedido.url else None
    pagina.on('request', ouvir)
    avisos = []
    async def aceitar(dialogo):
        avisos.append(dialogo.message)
        try:
            await dialogo.accept()
        except Exception:
            pass
    pagina.on('dialog', aceitar)
    await pagina.click('#recommendations button[onclick="gerarPDFExamesImagem()"]')
    await pagina.wait_for_selector('#dialogoAcrescimo[open]')
    await pagina.wait_for_timeout(300)
    await pagina.click('#acrescimoGerar')
    await pagina.wait_for_timeout(1200)
    pagina.remove_listener('request', ouvir)
    pagina.remove_listener('dialog', aceitar)
    return (json.loads(corpos[0]) if corpos else None), avisos


async def recortar(pagina, seletor, caminho):
    """Captura só o elemento, na página inteira (o aviso fixo do topo não fica por cima do recorte)."""
    await pagina.evaluate('window.scrollTo(0, 0)')
    caixa = await pagina.locator(seletor).bounding_box()
    await pagina.screenshot(path=caminho, full_page=True, clip=caixa)


# ── Roteiros ────────────────────────────────────────────────────────────────────

async def conta_comum(navegador, base):
    contexto = await navegador.new_context(viewport={'width': 1280, 'height': 900})
    pagina = await entrar(contexto, base, COMUM)
    pedidos = []
    pagina.on('request', lambda r: pedidos.append(r.url))
    await pagina.goto(base + '/intelligent-tools')
    await pagina.wait_for_timeout(1500)
    ok('conta comum: sem seletor no check-up', await pagina.locator('#pacienteCadastrado').count() == 0)
    ok('conta comum: sem link "Pacientes"', await pagina.locator('a[href="/pacientes"]').count() == 0)
    ok('conta comum: os scripts do cadastro não são baixados', not any('pacientes' in u for u in pedidos))
    ok('conta comum: sem a frase do seletor', 'Paciente cadastrado' not in await pagina.inner_text('body'))
    r = await pagina.evaluate(CHAMAR, ['/api/pacientes', None])
    ok('conta comum: a API recusa', r['status'] == 403, r['status'])
    await pagina.goto(base + '/pacientes')
    await pagina.wait_for_timeout(500)
    ok('conta comum: /pacientes volta ao check-up', pagina.url.endswith('/intelligent-tools'), pagina.url)
    await contexto.close()


async def preparar_administrador(navegador, base):
    contexto = await navegador.new_context(viewport={'width': 1280, 'height': 1300}, locale='pt-BR')
    consultas = await simular_rede(contexto)
    pagina = await entrar(contexto, base, ADMIN)
    erros = []
    pagina.on('pageerror', lambda e: erros.append(str(e)))
    r = await pagina.evaluate("""c => fetch('/api/auth/credenciamentos', {method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(c)}).then(r => r.status)""",
        {'operadora': 'Unimed Goiânia', 'codigo_prestador': '12345', 'nome_contratado': 'Clínica Fictícia'})
    ok('preparo: credenciamento do médico', r in (200, 201), r)
    r = await pagina.evaluate("""c => fetch('/api/auth/vinculos-sus', {method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(c)}).then(r => r.status)""",
        {'cnes': '1234567', 'nome': 'Unidade Fictícia de Saúde', 'cns': CNS_MEDICO})
    ok('preparo: vínculo do médico com o SUS', r in (200, 201), r)
    ids = {}
    for chave, paciente in (('A', PACIENTE_A), ('B', PACIENTE_B), ('C', PACIENTE_C)):
        r = await pagina.evaluate(CHAMAR, ['/api/pacientes', paciente])
        ok(f'preparo: paciente {chave} criado', r['status'] == 201, r['status'])
        ids[chave] = r['dados']['paciente']['id']
    return contexto, pagina, erros, consultas, ids


async def c1_apac_de_outro_paciente(pagina, base):
    """C1: paciente A escolhido, SUS no plano, outro nome digitado por cima, PDF de imagem."""
    await abrir_checkup(pagina, base)
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    ok('C1: a APAC de A é preenchida pelo cadastro', (await pagina.evaluate(APAC_NA_TELA))['apacCns'] == CNS_A)
    sus = await pagina.evaluate("[...document.getElementById('pacientePlano').options].find(o => o.value.startsWith('sus:')).value")
    await pagina.select_option('#pacientePlano', sus)
    await pagina.fill('#nome_paciente', 'Pedro Diferente dos Santos')
    await pagina.fill('#idade', '66')
    await pagina.click('label[for=tabagismo_nunca]')
    ok('C1: nome novo solta o vínculo, de forma visível', await pagina.evaluate(VINCULO) == ''
       and await pagina.locator('#pacienteSoltar').is_hidden(), await pagina.evaluate(VINCULO))
    ok('C1: o estado explica', 'seleção' in (await pagina.inner_text('#pacienteEstado')).lower(), await pagina.inner_text('#pacienteEstado'))
    na_tela = await pagina.evaluate(APAC_NA_TELA)
    ok('C1: nome novo limpa a APAC sem resultado na tela', not any(na_tela.values()), na_tela)
    await gerar(pagina)
    corpo, avisos = await pedir_pdf_de_imagem(pagina)
    texto = json.dumps(corpo, ensure_ascii=False)
    print('      POST /api/gerar-pdf-exames-imagem (sem as recomendações):',
          json.dumps({k: v for k, v in (corpo or {}).items() if k != 'recomendacoes'}, ensure_ascii=False))
    ok('C1: o pedido saiu com o nome novo', bool(corpo) and corpo['dados_paciente'].get('nome') == 'Pedro Diferente dos Santos')
    ok('C1: o POST não leva dado de A', bool(corpo) and not any(d in texto for d in DADOS_DE_A), [d for d in DADOS_DE_A if d in texto])
    ok('C1: apac.paciente vazio', bool(corpo) and (corpo.get('apac') or {}).get('paciente') == {}, (corpo or {}).get('apac'))
    if await pagina.locator('#dialogoAcrescimo[open]').count():
        await pagina.click('#acrescimoCancelar')


async def c1_guarda_da_geracao(pagina, base):
    """C1 (c): mesmo que o nome mude sem evento nenhum (preenchimento por código), o PDF não leva a APAC do vínculo."""
    await abrir_checkup(pagina, base)
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    sus = await pagina.evaluate("[...document.getElementById('pacientePlano').options].find(o => o.value.startsWith('sus:')).value")
    await pagina.select_option('#pacientePlano', sus)
    await pagina.click('label[for=tabagismo_nunca]')
    await gerar(pagina)
    ok('C1c: preparo, APAC de A na tela com o vínculo', (await pagina.evaluate(APAC_NA_TELA))['apacCns'] == CNS_A
       and PACIENTE_A['nome'] in await pagina.evaluate(VINCULO))
    await pagina.evaluate("document.getElementById('nome_paciente').value = 'Nome Trocado Sem Evento'")
    corpo, avisos = await pedir_pdf_de_imagem(pagina)
    texto = json.dumps(corpo, ensure_ascii=False)
    ok('C1c: a geração é barrada com aviso, ou sai sem dado de A', (corpo is None and bool(avisos))
       or (corpo is not None and not any(d in texto for d in DADOS_DE_A)), avisos or texto[:200])
    ok('C1c: a APAC foi limpa e o vínculo solto', not any((await pagina.evaluate(APAC_NA_TELA)).values())
       and await pagina.evaluate(VINCULO) == '')
    if await pagina.locator('#dialogoAcrescimo[open]').count():
        await pagina.click('#acrescimoCancelar')


async def a1_troca_de_paciente(pagina, base, capturas):
    """A1 e M3: A com dados clínicos e plano na tela; escolhe-se B (sem plano)."""
    await abrir_checkup(pagina, base)
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    ok('A1: primeiro paciente não gera aviso', await pagina.locator('#pacienteLimparClinicos').count() == 0
       or await pagina.locator('#pacienteLimparClinicos').is_hidden())
    await pagina.click('#planoManter')
    await pagina.click('label[for=diabetes]')
    await pagina.click('label[for=tabagismo_atual]')
    await pagina.fill('#peso', '82')
    await escolher(pagina, 'joão', PACIENTE_B['nome'])
    estado = await pagina.inner_text('#pacienteEstado')
    ok('A1: aviso de dados clínicos do anterior', 'Os dados clínicos na tela são do paciente anterior.' in estado, estado)
    ok('A1: botão "Limpar dados clínicos"', await pagina.locator('#pacienteLimparClinicos').is_visible())
    ok('M3: plano e carteira de A saem da tela', await pagina.input_value('#pacientePlano') == ''
       and await pagina.input_value('#pacienteCarteira') == '' and await pagina.evaluate('window.evidensCheckup.planoPendente()') is False,
       [await pagina.input_value('#pacientePlano'), await pagina.input_value('#pacienteCarteira')])
    if capturas and await pagina.locator('#pacienteLimparClinicos').count():
        await pagina.locator('#pacienteCadastrado').screenshot(path=os.path.join(capturas, 'aviso_dados_clinicos.png'))
    if await pagina.locator('#pacienteLimparClinicos').count():
        await pagina.click('#pacienteLimparClinicos')
    await pagina.wait_for_timeout(200)
    clinicos = await pagina.evaluate("""() => ({ diabetes: document.getElementById('diabetes').checked, peso: document.getElementById('peso').value,
        fumo: (document.querySelector('input[name=tabagismo]:checked') || {}).value || '', nome: document.getElementById('nome_paciente').value,
        idade: document.getElementById('idade').value, sexo: document.getElementById('sexo').value })""")
    ok('A1: limpar zera os dados clínicos', clinicos['diabetes'] is False and clinicos['peso'] == '' and clinicos['fumo'] == '', clinicos)
    ok('A1: a identificação de B fica', clinicos['nome'] == PACIENTE_B['nome'] and clinicos['sexo'] == 'masculino' and clinicos['idade'] != '', clinicos)
    ok('A1: o vínculo com B fica e o aviso some', PACIENTE_B['nome'] in await pagina.evaluate(VINCULO)
       and (await pagina.locator('#pacienteLimparClinicos').count() == 0 or await pagina.locator('#pacienteLimparClinicos').is_hidden()))
    # nome digitado (sem vínculo) com dados clínicos, depois um paciente do cadastro: também avisa
    await abrir_checkup(pagina, base)
    await pagina.fill('#nome_paciente', 'Digitado de Teste')
    await pagina.click('label[for=hipertensao]')
    await escolher(pagina, 'joão', PACIENTE_B['nome'])
    ok('A1: avisa também quando o anterior foi digitado', 'paciente anterior' in await pagina.inner_text('#pacienteEstado'))


async def m1_corrida_no_salvar(pagina, base, ids):
    await abrir_checkup(pagina, base)
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    await pagina.click('#planoManter')

    async def atrasar(rota):
        if rota.request.method == 'POST':
            await asyncio.sleep(1.5)
        await rota.continue_()
    await pagina.route(f'**/api/pacientes/{ids["A"]}', atrasar)
    await pagina.click('#pacienteSalvar')
    await pagina.wait_for_timeout(500)          # a releitura (GET) já voltou; o POST está preso
    ok('M1: busca desabilitada durante o salvamento', await pagina.locator('#pacienteBusca').is_disabled())
    await pagina.evaluate("document.getElementById('pacienteSoltar').click()")      # o usuário solta a seleção no meio
    await pagina.wait_for_timeout(1800)
    ok('M1: resposta atrasada não refaz o vínculo', await pagina.evaluate(VINCULO) == '', await pagina.evaluate(VINCULO))
    ok('M1: busca volta depois', not await pagina.locator('#pacienteBusca').is_disabled())
    await pagina.unroute(f'**/api/pacientes/{ids["A"]}')


async def m2_dado_clinico_do_mesmo_paciente(pagina, base):
    await abrir_checkup(pagina, base)
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    await pagina.click('label[for=tabagismo_nunca]')
    await gerar(pagina)
    await pagina.fill('#peso', '70')
    await pagina.wait_for_timeout(200)
    ok('M2: o resultado é invalidado', await pagina.evaluate("document.getElementById('recommendations').style.display") != 'block')
    apac = await pagina.evaluate(APAC_NA_TELA)
    ok('M2: a APAC do vínculo é repreenchida', apac['apacCns'] == CNS_A and apac['apacMae'] == PACIENTE_A['mae']
       and apac['apacNascimento'] == '15/03/1961' and PACIENTE_A['nome'] in await pagina.evaluate(VINCULO), apac)
    ok('M2: o IBGE do cadastro continua', await pagina.evaluate('window.evidensCheckup.ibge()') == '5208707')
    ok('M2: a guarda do plano sobe', await pagina.evaluate('window.evidensCheckup.planoPendente()') is True)


async def m4_sessao_expirada(pagina, base):
    await abrir_checkup(pagina, base)
    await pagina.fill('#nome_paciente', 'Formulário em Andamento')
    await pagina.fill('#peso', '77')
    await pagina.route('**/api/pacientes/buscar', lambda rota: rota.fulfill(status=401, content_type='application/json', body='{"error": "x"}'))
    await pagina.fill('#pacienteBusca', 'maria')
    await pagina.wait_for_timeout(1200)
    ok('M4: sem redirecionar para o login', pagina.url.endswith('/intelligent-tools'), pagina.url)
    ok('M4: o formulário fica', pagina.url.endswith('/intelligent-tools') and await pagina.input_value('#peso') == '77')
    estado = await pagina.inner_text('#pacienteEstado') if pagina.url.endswith('/intelligent-tools') else ''
    ok('M4: mensagem no estado', estado == 'A sessão terminou. Entre de novo em outra aba e repita.', estado)
    await pagina.unroute('**/api/pacientes/buscar')
    # Termos pendentes: o destino depois do aceite é a página de origem
    await pagina.route('**/api/pacientes/buscar', lambda rota: rota.fulfill(status=403, content_type='application/json',
                       headers={'X-Evidens-Termos': '1'}, body='{"error": "x"}'))
    await pagina.fill('#pacienteBusca', 'joão')
    for _ in range(25):
        if '/termos' in pagina.url:
            break
        await pagina.wait_for_timeout(200)
    ok('M4: Termos pendentes no check-up voltam ao check-up', 'destino=check-up' in pagina.url, pagina.url)
    await pagina.unroute('**/api/pacientes/buscar')


async def m5_edicao_concorrente(pagina, base, ids, capturas):
    await pagina.goto(base + '/pacientes')
    await pagina.wait_for_selector('[data-linhas] [data-paciente]')
    if capturas:
        await recortar(pagina, '[data-pac-lista]', os.path.join(capturas, 'lista.png'))
    await pagina.click(f'[data-paciente="{ids["A"]}"] [data-acao=editar]')
    await pagina.wait_for_function("document.getElementById('p_nome').value !== ''")
    # B2: a data máxima do nascimento é a data local do navegador
    local = await pagina.evaluate("(() => { const d = new Date(); return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-'); })()")
    ok('B2: nascimento.max é a data local', await pagina.get_attribute('#p_nascimento', 'max') == local,
       [await pagina.get_attribute('#p_nascimento', 'max'), local])
    ok('B5: campo ligado ao seu erro', await pagina.get_attribute('#p_cpf', 'aria-describedby') == await pagina.get_attribute('[data-erro-de="cpf"]', 'id')
       and bool(await pagina.get_attribute('#p_cpf', 'aria-describedby')))
    if capturas:
        await pagina.wait_for_timeout(600)
        await recortar(pagina, '[data-ficha]', os.path.join(capturas, 'formulario.png'))
    # outra aba altera o registro enquanto o formulário está aberto
    await pagina.wait_for_timeout(1100)
    r = await pagina.evaluate(CHAMAR, [f'/api/pacientes/{ids["A"]}', {'responsavel': 'Filha Fictícia'}])
    ok('M5: preparo, alteração feita em outro lugar', r['status'] == 200, r['status'])
    await pagina.fill('#p_prontuario', 'PRT-777')
    await pagina.click('[data-salvar]')
    await pagina.wait_for_timeout(800)
    erro = await pagina.inner_text('[data-ficha] [data-erro]')
    ok('M5: a tela avisa o conflito', erro.strip() == 'Este cadastro foi alterado em outro lugar. Reabra e repita a alteração.', erro)
    r = await pagina.evaluate(CHAMAR, [f'/api/pacientes/{ids["A"]}', None])
    ok('M5: nada foi sobrescrito', r['dados']['paciente'].get('responsavel') == 'Filha Fictícia' and not r['dados']['paciente'].get('prontuario'),
       {k: r['dados']['paciente'].get(k) for k in ('responsavel', 'prontuario')})
    # reabrir e repetir funciona
    await pagina.click('[data-cancelar]')
    await pagina.click(f'[data-paciente="{ids["A"]}"] [data-acao=editar]')
    await pagina.wait_for_function("document.getElementById('p_responsavel').value !== ''")
    await pagina.fill('#p_prontuario', 'PRT-777')
    await pagina.click('[data-salvar]')
    await pagina.wait_for_function("document.querySelector('[data-ok-geral]').textContent.includes('Paciente salvo.')")
    ok('M5: reabrir e repetir grava', True)
    await pagina.evaluate(CHAMAR, [f'/api/pacientes/{ids["A"]}', {'prontuario': '', 'responsavel': ''}])


async def b3_b4_cep_e_validade(pagina, base, consultas, capturas):
    await abrir_checkup(pagina, base)
    del consultas[:]
    await escolher(pagina, 'carla', PACIENTE_C['nome'])
    await pagina.wait_for_timeout(600)
    ok('B3: CEP do cadastro sem IBGE dispara a busca do CEP', len(consultas) == 1 and '74000000' in consultas[0], consultas)
    ok('B3: o IBGE vem da busca', await pagina.evaluate('window.evidensCheckup.ibge()') == '5208707')
    estado = await pagina.inner_text('#pacienteEstado')
    ok('B4: validade vencida é avisada', 'A validade da carteira no cadastro venceu em 01/2024.' in estado, estado)
    ok('B4: o plano é preenchido mesmo assim', await pagina.input_value('#pacienteCarteira') == '5550001')
    del consultas[:]
    await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
    await pagina.wait_for_timeout(600)
    ok('B3: CEP com IBGE no cadastro não é buscado de novo', consultas == [] and await pagina.evaluate('window.evidensCheckup.ibge()') == '5208707', consultas)
    ok('B4: validade em dia não gera aviso', 'venceu' not in await pagina.inner_text('#pacienteEstado'))
    ok('B5: #pacienteVinculado é região viva', await pagina.get_attribute('#pacienteVinculado', 'aria-live') == 'polite')
    if capturas:
        await pagina.locator('section[aria-labelledby=s-identificacao]').screenshot(path=os.path.join(capturas, 'checkup_seletor.png'))


async def ingles(pagina, base):
    try:
        await abrir_checkup(pagina, base, '?lang=en')
        await pagina.wait_for_timeout(800)
        await escolher(pagina, 'maria fic', PACIENTE_A['nome'])
        await pagina.click('label[for=diabetes]')
        await escolher(pagina, 'joão', PACIENTE_B['nome'])
        texto = await pagina.inner_text('#pacienteCadastrado')
        ok('inglês: aviso e botão traduzidos, nome intacto', 'belongs to the previous patient' in texto
           and 'Clear clinical data' in texto and PACIENTE_B['nome'] in texto, texto.replace('\n', ' | ')[:400])
    finally:
        await pagina.goto(base + '/intelligent-tools?lang=pt')      # o idioma fica guardado: volta ao português


async def principal(argumentos):
    from playwright.async_api import async_playwright
    filho, base = subir_servidor()
    capturas = argumentos.capturas
    if capturas:
        os.makedirs(capturas, exist_ok=True)
    try:
        async with async_playwright() as p:
            navegador = await p.chromium.launch(executable_path=argumentos.chrome, args=['--no-sandbox', '--lang=pt-BR'])
            await conta_comum(navegador, base)
            contexto, pagina, erros, consultas, ids = await preparar_administrador(navegador, base)
            roteiros = [
                ('C1', lambda: c1_apac_de_outro_paciente(pagina, base)),
                ('C1c', lambda: c1_guarda_da_geracao(pagina, base)),
                ('A1/M3', lambda: a1_troca_de_paciente(pagina, base, capturas)),
                ('M1', lambda: m1_corrida_no_salvar(pagina, base, ids)),
                ('M2', lambda: m2_dado_clinico_do_mesmo_paciente(pagina, base)),
                ('B3/B4', lambda: b3_b4_cep_e_validade(pagina, base, consultas, capturas)),
                ('inglês', lambda: ingles(pagina, base)),
                ('M5/B2', lambda: m5_edicao_concorrente(pagina, base, ids, capturas)),
                ('M4', lambda: m4_sessao_expirada(pagina, base)),
            ]
            for nome, roteiro in roteiros:
                if argumentos.so and nome not in argumentos.so.split(','):
                    continue
                try:
                    await roteiro()
                except Exception as erro:            # um roteiro que quebra não esconde os outros
                    ok(f'{nome}: roteiro completo', False, f'{type(erro).__name__}: {str(erro)[:300]}')
            ok('nenhum erro de script na página', not erros, erros[:5])
            await pagina.goto(base + '/intelligent-tools')
            await pagina.wait_for_selector('#pacienteCadastrado')
            armazenado = await pagina.evaluate('JSON.stringify([Object.assign({}, localStorage), Object.assign({}, sessionStorage)])')
            ok('nada de paciente no armazenamento do navegador', not any(t in armazenado for t in ('Maria', 'Fict', CNS_A, 'Inventado')))
            await navegador.close()
    finally:
        filho.terminate()
    print(f'\n{len(falhas)} falha(s).' + (' ' + '; '.join(falhas) if falhas else ''))
    return 1 if falhas else 0


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--servir':
        servir(int(sys.argv[2]))
    else:
        leitor = argparse.ArgumentParser(description='Conferência da tela do cadastro de pacientes no navegador.')
        leitor.add_argument('--capturas', help='pasta onde gravar as capturas de tela (opcional)')
        leitor.add_argument('--chrome', default=os.environ.get('CHROME', '/usr/bin/google-chrome'))
        leitor.add_argument('--so', help='só estes roteiros, separados por vírgula (ex.: C1,M2)')
        sys.exit(asyncio.run(principal(argumentos=leitor.parse_args())))
