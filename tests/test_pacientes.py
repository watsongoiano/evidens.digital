"""Cadastro de pacientes (src/utils/pacientes.py e /api/pacientes): cifrado, com dono, só do administrador.

Todos os dados são fictícios: nomes inventados, CPF e CNS gerados aqui só para fechar os dígitos verificadores.
"""
import ast
import itertools
import os
import re
from pathlib import Path

import pytest

from src.utils import pacientes

RAIZ = Path(__file__).resolve().parent.parent
_seq = itertools.count(1)

CHECKUP = dict(idade=50, sexo='feminino', tabagismo='nunca', imunossupressao='nao', gestante='nao', lactante='nao',
               comorbidades=[], historia_familiar=[], medicacoes=[])

# Toda rota do cadastro (método, caminho). test_lista_de_rotas_esta_completa garante que nenhuma fica de fora.
ROTAS = [('GET', '/api/pacientes'), ('POST', '/api/pacientes/buscar'), ('POST', '/api/pacientes'), ('GET', '/api/pacientes/{id}'), ('POST', '/api/pacientes/{id}'),
         ('POST', '/api/pacientes/{id}/excluir'), ('GET', '/api/pacientes/{id}/exportar')]


# Chave fictícia do cadastro, só para os testes (PACIENTES_CHAVE; 32 caracteres ou mais). Nenhum ambiente a usa.
CHAVE_FICTICIA = 'chave-ficticia-do-cadastro-apenas-para-os-testes'
CABECALHO = {'X-Requested-With': 'evidens'}


@pytest.fixture(autouse=True)
def _chave_do_cadastro():
    # Remendo próprio: o `monkeypatch.undo()` de um teste não tira a chave do ambiente.
    with pytest.MonkeyPatch.context() as remendo:
        remendo.setenv('PACIENTES_CHAVE', CHAVE_FICTICIA)
        yield


def _com_cabecalho(cliente):
    """Como a tela vai fazer: todo pedido ao cadastro leva `X-Requested-With: evidens`."""
    cliente.environ_base['HTTP_X_REQUESTED_WITH'] = 'evidens'
    return cliente


@pytest.fixture()
def admin(admin):
    return _com_cabecalho(admin)


@pytest.fixture()
def client(client):
    return _com_cabecalho(client)


@pytest.fixture()
def anonimo(anonimo):
    return _com_cabecalho(anonimo)


def _buscar(cliente, termo):
    return cliente.post('/api/pacientes/buscar', json={'busca': termo})


def _cpf():
    """CPF fictício válido: nove dígitos de uma sequência e os dois verificadores calculados."""
    base = f'{700100200 + next(_seq):09d}'
    for n in (9, 10):
        base += str(sum(int(base[i]) * (n + 1 - i) for i in range(n)) * 10 % 11 % 10)
    return base


def _cns():
    """CNS fictício válido (como em tests/test_apac.py): o final é ajustado para a soma ponderada fechar em 11."""
    corpo = '2' + f'{31415926 + next(_seq):010d}'
    for final in range(10 ** 4):
        cns = corpo + f'{final:04d}'
        if sum(int(d) * (15 - i) for i, d in enumerate(cns)) % 11 == 0:
            return cns
    raise AssertionError


def _ficticio(**outros):
    n = next(_seq)
    return {'nome': f'Paciente Fictícia Xavante {n:03d}', 'nome_social': f'Xavi Fictícia {n:03d}',
            'nascimento': '1931-04-23', 'sexo': 'feminino', 'cpf': _cpf(), 'cns': _cns(),
            'mae': f'Mãe Fictícia Zuleica {n:03d}', 'raca': 'parda', 'prontuario': f'PRT-{n:05d}',
            'responsavel': f'Responsável Fictício Quirino {n:03d}', 'telefone': '(62) 90000-0000',
            'email': f'paciente.ficticio{n}@exemplo.test', 'cep': '74000-000',
            'endereco': f'Rua Fictícia das Acácias, nº {n}', 'municipio': 'Goiânia', 'ibge': '5208707', 'uf': 'GO',
            'planos': [{'operadora': 'Operadora Fictícia Jatobá', 'carteira': f'CARTEIRA-FICT-{n:06d}',
                        'validade': '2031-12'}],
            'ficha': {'peso': 71.5, 'altura': 162, 'pas': '128', 'comorbidades': ['hipertensao', 'diabetes'],
                      'medicacoes': ['losartana'], 'observacao': f'Anotação fictícia Ipê-roxo {n:03d}',
                      'gestante': False, 'hba1c': None},
            **outros}


def _segredos(dados):
    """O que não pode aparecer em claro nem voltar numa recusa: os textos e os números do paciente."""
    partes = [dados.get(c) for c in ('nome', 'nome_social', 'mae', 'cpf', 'cns', 'responsavel', 'email', 'endereco',
                                     'prontuario', 'nascimento')]
    planos, ficha = dados.get('planos'), dados.get('ficha')
    for plano in planos if isinstance(planos, list) else []:
        partes += [plano.get('carteira'), plano.get('operadora')] if isinstance(plano, dict) else []
    partes += list(ficha.values()) if isinstance(ficha, dict) else []
    return [str(p) for p in partes if isinstance(p, (str, int)) and not isinstance(p, bool) and 6 <= len(str(p)) < 200]


def _banco_cru():
    """Os bytes do arquivo do banco dos testes: tudo o que está gravado, em qualquer tabela."""
    return Path(os.environ['DATABASE_URL'].split('sqlite:///', 1)[1]).read_bytes()


def _contagens(contas):
    with contas._conexao() as executar:
        return tuple(executar(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0]
                     for tabela in ('pacientes', 'pacientes_acessos', 'eventos_uso'))


def _criar(admin, **outros):
    dados = _ficticio(**outros)
    r = admin.post('/api/pacientes', json=dados)
    assert r.status_code == 201, r.get_json()
    return dados, r.get_json()['paciente']


def _pedir(cliente, metodo, caminho, pid=1, json=None, **kw):
    caminho = caminho.format(id=pid)
    return cliente.get(caminho, **kw) if metodo == 'GET' else cliente.post(caminho, json=json if json is not None else {}, **kw)


# --- Esquema ---------------------------------------------------------------------------------

def test_esquema_das_tabelas(contas):
    with contas._conexao() as executar:
        colunas = {t: [c[1] for c in executar(f'PRAGMA table_info({t})').fetchall()]
                   for t in ('pacientes', 'pacientes_acessos')}
        indices = {t: {i[1]: bool(i[2]) for i in executar(f'PRAGMA index_list({t})').fetchall()}
                   for t in ('pacientes', 'pacientes_acessos')}
        nulos = {c[1]: not c[3] for c in executar('PRAGMA table_info(pacientes)').fetchall()}
    assert colunas['pacientes'] == ['id', 'usuario_id', 'dados', 'indice_cns', 'indice_cpf', 'criado_em', 'atualizado_em']
    assert colunas['pacientes_acessos'] == ['id', 'paciente_id', 'usuario_id', 'acao', 'quando']
    assert indices['pacientes']['pacientes_usuario'] is False                      # índice por dono
    assert indices['pacientes']['pacientes_cns_da_conta'] and indices['pacientes']['pacientes_cpf_da_conta']   # únicos
    assert 'pacientes_acessos_usuario' in indices['pacientes_acessos']
    assert nulos['indice_cns'] and nulos['indice_cpf'] and not nulos['dados'] and not nulos['usuario_id']


# --- Ciclo completo pela API -------------------------------------------------------------------

def test_criar_ler_listar_buscar_atualizar_exportar_e_excluir(admin, administrador):
    dados, criado = _criar(admin, nome='Paciente Fictícia Xavante Jequitibá', nome_social='Xavi Fictícia Sucupira')
    pid = criado['id']
    # O que volta é o que foi enviado, normalizado: números só com dígitos, raça pela chave, todas as chaves presentes.
    assert criado['nome'] == dados['nome'] and criado['cpf'] == dados['cpf'] and criado['cns'] == dados['cns']
    assert criado['cep'] == '74000000' and criado['uf'] == 'GO' and criado['raca'] == 'parda'
    assert criado['planos'] == dados['planos'] and criado['ficha'] == dados['ficha']
    assert set(criado) == {'id', 'criado_em', 'atualizado_em', *pacientes.CAMPOS}
    assert admin.get(f'/api/pacientes/{pid}').get_json()['paciente'] == criado

    # A lista traz só o resumo.
    lista = admin.get('/api/pacientes').get_json()
    item = next(p for p in lista['pacientes'] if p['id'] == pid)
    assert item == {'id': pid, 'nome': dados['nome'], 'nascimento': '1931-04-23', 'sexo': 'feminino',
                    'cns_final': dados['cns'][-4:], 'atualizado_em': criado['atualizado_em']}
    assert lista['truncado'] is False and lista['ilegiveis'] == 0 and lista['total'] == len(lista['pacientes'])

    # Busca: parte do nome (sem acento, sem maiúsculas, em qualquer ordem), nome social e final do CNS;
    # o termo vai sempre no corpo.
    for termo in ('jequitiba ficticia', 'XAVANTE jequitibá', '  xavi   SUCUPIRA ', dados['cns'], f"{dados['cns'][:3]} {dados['cns'][3:]}"):
        pelo_corpo = _buscar(admin, termo).get_json()
        assert [p['id'] for p in pelo_corpo['pacientes']] == [pid] and pelo_corpo['total'] == 1, termo
        assert set(pelo_corpo) == {'pacientes', 'total', 'truncado', 'ilegiveis'}
    pelo_final = _buscar(admin, dados['cns'][-4:]).get_json()['pacientes']
    assert pid in [p['id'] for p in pelo_final] and all(p['cns_final'] == dados['cns'][-4:] for p in pelo_final)
    for termo in ('nome-que-ninguem-tem', 'jequitiba sucupira inexistente', '0000000000000000', dados['cpf']):
        assert _buscar(admin, termo).get_json()['pacientes'] == [], termo
    assert pid in [p['id'] for p in admin.post('/api/pacientes/buscar', json={}).get_json()['pacientes']]      # sem termo: todos

    # Atualizar: troca o que foi enviado, mantém o resto; '' apaga; planos e ficha são substituídos por inteiro.
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis', 'telefone': '', 'mae': None,
                                                  'ficha': {'peso': 80}, 'planos': []})
    assert r.status_code == 200
    novo = r.get_json()['paciente']
    assert novo['municipio'] == 'Anápolis' and novo['telefone'] == '' and novo['mae'] == ''
    assert novo['ficha'] == {'peso': 80} and novo['planos'] == []
    assert novo['nome'] == dados['nome'] and novo['cpf'] == dados['cpf'] and novo['criado_em'] == criado['criado_em']
    assert admin.get(f'/api/pacientes/{pid}').get_json()['paciente'] == novo
    assert admin.post(f'/api/pacientes/{pid}', json={'nome': ''}).status_code == 400          # o nome não pode sair

    # Exportar: tudo o que há guardado, como arquivo; o nome do arquivo não leva o nome do paciente.
    r = admin.get(f'/api/pacientes/{pid}/exportar')
    assert r.status_code == 200 and r.mimetype == 'application/json'
    assert r.headers['Content-Disposition'] == f'attachment; filename="paciente-{pid}.json"'
    exportado = r.get_json()
    assert exportado['formato'] == 'evidens-paciente' and exportado['versao'] == 1 and exportado['paciente'] == novo

    # Excluir: some da leitura, da lista e da exportação.
    assert admin.post(f'/api/pacientes/{pid}/excluir').get_json() == {'ok': True}
    for metodo, caminho in ROTAS[3:]:
        assert _pedir(admin, metodo, caminho, pid).status_code == 404, caminho
    assert pid not in [p['id'] for p in admin.get('/api/pacientes').get_json()['pacientes']]
    assert pacientes.ler(administrador['id'], pid) is None


def test_respostas_nao_ficam_em_cache(admin):
    _, criado = _criar(admin)
    for metodo, caminho in ROTAS:
        assert _pedir(admin, metodo, caminho, criado['id'], json={'municipio': 'Goiânia'}).headers['Cache-Control'] == 'no-store'
    assert admin.get('/api/pacientes/999999999').headers['Cache-Control'] == 'no-store'


def test_lista_em_ordem_alfabetica_com_teto(admin, monkeypatch):
    marca = f'Teto{next(_seq)}'
    nomes = [f'{inicial} Fictício {marca}' for inicial in ('Érico', 'Abel', 'Davi', 'Caio', 'Bento')]
    for nome in nomes:
        _criar(admin, nome=nome)
    monkeypatch.setattr(pacientes, 'LOTE_DA_LISTA', 2)        # a leitura em lotes não perde nem repete ninguém
    todos = _buscar(admin, marca).get_json()
    assert [p['nome'].split()[0] for p in todos['pacientes']] == ['Abel', 'Bento', 'Caio', 'Davi', 'Érico']
    monkeypatch.setattr(pacientes, 'LIMITE_DA_LISTA', 3)
    cortada = _buscar(admin, marca).get_json()
    assert [p['nome'].split()[0] for p in cortada['pacientes']] == ['Abel', 'Bento', 'Caio']
    assert cortada['total'] == 5 and cortada['truncado'] is True


def test_tetos_do_cadastro():
    assert pacientes.LIMITE_DA_LISTA == 500 and pacientes.MAX_PLANOS == 5 and pacientes.MAX_FICHA == 64 * 1024


# --- Cifra em repouso ---------------------------------------------------------------------------

def test_nada_do_paciente_fica_em_claro_no_banco(admin, contas):
    dados, criado = _criar(admin)
    pid = criado['id']
    # Passa por todas as ações, inclusive a busca pelo nome, antes de olhar o banco.
    admin.get(f'/api/pacientes/{pid}')
    _buscar(admin, dados['nome'])
    admin.post('/api/pacientes/buscar', json={'busca': dados['mae']})
    admin.post(f'/api/pacientes/{pid}', json={'endereco': dados['endereco'] + ' fundos'})
    admin.get(f'/api/pacientes/{pid}/exportar')
    with contas._conexao() as executar:
        linha = executar('SELECT id, usuario_id, dados, indice_cns, indice_cpf, criado_em, atualizado_em '
                         'FROM pacientes WHERE id = ?', (pid,)).fetchone()
    cifrado, indice_cns, indice_cpf = linha[2], linha[3], linha[4]
    assert cifrado.startswith('v1:gAAAA') and re.fullmatch(r'v1:[A-Za-z0-9_\-=]+', cifrado)        # Fernet
    assert re.fullmatch(r'[0-9a-f]{64}', indice_cns) and re.fullmatch(r'[0-9a-f]{64}', indice_cpf)   # HMAC-SHA256
    segredos = _segredos(dados)
    assert len(segredos) >= 13
    cru, texto_da_linha = _banco_cru(), ' '.join(str(c) for c in linha)
    for segredo in segredos:
        assert segredo not in texto_da_linha, segredo
        assert segredo.encode() not in cru, segredo           # nem em outra tabela, nem na trilha, nem no uso
    assert b'Xavante' not in cru and b'Zuleica' not in cru and b'Quirino' not in cru and 'Jatobá'.encode() not in cru


def test_mesma_ficha_gravada_duas_vezes_da_textos_cifrados_diferentes(admin, contas):
    _, a = _criar(admin, cpf='', cns='', nome='Gêmea Fictícia Um')
    _, b = _criar(admin, cpf='', cns='', nome='Gêmea Fictícia Um')
    with contas._conexao() as executar:
        linhas = executar('SELECT dados, indice_cns, indice_cpf FROM pacientes WHERE id IN (?, ?)', (a['id'], b['id'])).fetchall()
    assert linhas[0][0] != linhas[1][0]
    assert all(l[1] is None and l[2] is None for l in linhas)          # sem CNS e sem CPF: índices nulos


def test_chaves_derivam_da_chave_propria_do_cadastro_e_nao_da_chave_de_sessao(monkeypatch):
    assert pacientes.ROTULO_DA_CIFRA == b'evidens-pacientes-v1' and pacientes.ROTULO_DO_INDICE == b'evidens-pacientes-indice-v1'
    assert pacientes.VARIAVEL_DA_CHAVE == 'PACIENTES_CHAVE' and pacientes.MIN_DA_CHAVE == 32
    cifra, indice = pacientes._chave(pacientes.ROTULO_DA_CIFRA), pacientes._chave(pacientes.ROTULO_DO_INDICE)
    assert len(cifra) == 32 and len(indice) == 32 and cifra != indice
    # Trocar a chave de sessão não muda nada no cadastro...
    monkeypatch.setenv('SECRET_KEY', 'outra-chave-de-sessao-apenas-para-este-teste')
    assert pacientes._chave(pacientes.ROTULO_DA_CIFRA) == cifra and pacientes._chave(pacientes.ROTULO_DO_INDICE) == indice
    # ...e trocar a do cadastro muda as duas chaves derivadas.
    monkeypatch.setenv('PACIENTES_CHAVE', 'outra-chave-ficticia-do-cadastro-so-para-este-teste')
    assert pacientes._chave(pacientes.ROTULO_DA_CIFRA) != cifra and pacientes._chave(pacientes.ROTULO_DO_INDICE) != indice


def test_registro_continua_abrindo_quando_a_chave_de_sessao_muda(admin, monkeypatch):
    dados, criado = _criar(admin)
    monkeypatch.setenv('SECRET_KEY', 'chave-de-sessao-trocada-apenas-para-este-teste')
    assert admin.get(f"/api/pacientes/{criado['id']}").get_json()['paciente']['nome'] == dados['nome']


def test_sem_chave_propria_ou_com_chave_fraca_o_cadastro_fica_indisponivel(admin, administrador, contas, monkeypatch):
    """Sem PACIENTES_CHAVE, ou com menos de 32 caracteres, nada é gravado nem aberto. A SECRET_KEY (que está
    definida e é forte o bastante para a sessão) nunca entra no lugar."""
    from src.routes import auth
    assert pacientes._CHAVE_DE_DESENVOLVIMENTO == auth.CHAVE_PADRAO and len(auth.CHAVE_PADRAO) >= 32
    _, existente = _criar(admin)
    antes = _contagens(contas)
    sessao = 'chave-de-sessao-longa-apenas-para-este-teste-0123456789'
    monkeypatch.setenv('SECRET_KEY', sessao)
    for chave in (None, '', '   ', 'a', '1234', 'f' * 31, ' ' * 20 + 'g' * 31 + ' ' * 20, auth.CHAVE_PADRAO, sessao):
        if chave is None:
            monkeypatch.delenv('PACIENTES_CHAVE')
        else:
            monkeypatch.setenv('PACIENTES_CHAVE', chave)
        with pytest.raises(pacientes.CadastroIndisponivel, match='PACIENTES_CHAVE'):
            pacientes.criar(administrador['id'], _ficticio())
        with pytest.raises(pacientes.CadastroIndisponivel):
            pacientes._chave(pacientes.ROTULO_DO_INDICE)
        for metodo, caminho in ROTAS:
            if caminho.endswith('/excluir'):
                continue                      # apagar não depende da chave
            r = _pedir(admin, metodo, caminho, existente['id'], json=_ficticio())
            assert r.status_code == 503 and r.get_json()['codigo'] == 'sem_chave', (chave, caminho)
            assert 'Fict' not in r.get_data(as_text=True)
    assert _contagens(contas) == antes
    monkeypatch.setenv('PACIENTES_CHAVE', 'h' * 32)               # 32 caracteres já servem
    assert len(pacientes._chave(pacientes.ROTULO_DA_CIFRA)) == 32


def test_nenhuma_chave_do_cadastro_esta_gravada_no_repositorio():
    exemplo = (RAIZ / '.env.example').read_text(encoding='utf-8')
    assert re.search(r'^PACIENTES_CHAVE=$', exemplo, re.M)                 # só o nome, sem valor
    for arquivo in ('vercel.json', 'api/index.py', 'src/utils/pacientes.py', 'src/routes/pacientes.py', 'docs/pacientes.md',
                    'docs/deploy.md', 'README.md'):
        assert not re.search(r'PACIENTES_CHAVE\s*[=:]\s*["\']?[A-Za-z0-9_\-+/]{8,}', (RAIZ / arquivo).read_text(encoding='utf-8')), arquivo
    fonte = (RAIZ / 'src' / 'utils' / 'pacientes.py').read_text(encoding='utf-8')
    assert "environ.get('SECRET_KEY')" in fonte and fonte.count("environ.get(") == 2      # a de sessão só para recusar valor igual


def test_registro_nao_abre_com_outra_chave_e_ainda_pode_ser_excluido(admin, contas, monkeypatch):
    dados, criado = _criar(admin)
    pid = criado['id']
    monkeypatch.setenv('PACIENTES_CHAVE', 'chave-ficticia-trocada-apenas-para-este-teste')
    for caminho in (f'/api/pacientes/{pid}', f'/api/pacientes/{pid}/exportar'):
        r = admin.get(caminho)
        assert r.status_code == 500 and r.get_json()['codigo'] == 'ilegivel'
        assert not any(s in r.get_data(as_text=True) for s in _segredos(dados))
    assert admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Goiânia'}).status_code == 500
    lista = admin.get('/api/pacientes').get_json()
    assert lista['ilegiveis'] >= 1 and pid not in [p['id'] for p in lista['pacientes']]
    with contas._conexao() as executar:      # a tentativa de edição não mexeu na linha
        assert executar('SELECT atualizado_em FROM pacientes WHERE id = ?', (pid,)).fetchone()[0] == criado['atualizado_em']
    assert admin.post(f'/api/pacientes/{pid}/excluir').status_code == 200
    monkeypatch.undo()
    assert admin.get(f'/api/pacientes/{pid}').status_code == 404


def test_linha_copiada_para_outra_conta_direto_no_banco_nao_abre(admin, administrador, medica_aprovada, contas):
    """O dono vai dentro do texto cifrado: mexer em `usuario_id` no banco não dá a outra conta acesso ao paciente."""
    dados, criado = _criar(admin)
    pid = criado['id']
    with contas._conexao() as executar:
        executar('UPDATE pacientes SET usuario_id = ? WHERE id = ?', (medica_aprovada['id'], pid))
    try:
        with pytest.raises(pacientes.RegistroIlegivel):
            pacientes.ler(medica_aprovada['id'], pid)
        with pytest.raises(pacientes.RegistroIlegivel):
            pacientes.exportar(medica_aprovada['id'], pid)
        lista = pacientes.listar(medica_aprovada['id'])
        assert lista['ilegiveis'] == 1 and pid not in [p['id'] for p in lista['pacientes']]
    finally:
        with contas._conexao() as executar:
            executar('UPDATE pacientes SET usuario_id = ? WHERE id = ?', (administrador['id'], pid))
    assert pacientes.ler(administrador['id'], pid)['nome'] == dados['nome']


# --- Duplicado ---------------------------------------------------------------------------------

@pytest.mark.parametrize('campo', ['cns', 'cpf'])
def test_cns_ou_cpf_repetido_na_mesma_conta_e_recusado_com_o_registro_existente(admin, administrador, medica_aprovada, contas, campo):
    dados, criado = _criar(admin)
    numero = dados[campo]
    com_pontuacao = f'{numero[:3]}.{numero[3:6]}.{numero[6:9]}-{numero[9:]}' if campo == 'cpf' else f'{numero[:3]} {numero[3:7]} {numero[7:11]} {numero[11:]}'
    outro = {'nome': 'Outro Fictício Duplicado', campo: com_pontuacao}
    antes = _contagens(contas)
    r = admin.post('/api/pacientes', json=outro)
    assert r.status_code == 409 and _contagens(contas) == antes          # recusa não grava nem entra na trilha
    corpo = r.get_json()
    assert corpo == {'error': f'Já existe um paciente com este {campo.upper()} no seu cadastro.', 'codigo': 'duplicado',
                     'campo': campo, 'paciente_id': criado['id']}
    assert numero not in r.get_data(as_text=True)
    # Outra conta pode ter o mesmo número: o índice é por conta, e nem o índice se repete entre contas.
    da_medica = pacientes.criar(medica_aprovada['id'], dict(outro))
    with contas._conexao() as executar:
        indices = dict(executar(f'SELECT usuario_id, indice_{campo} FROM pacientes WHERE id IN (?, ?)',
                                (criado['id'], da_medica['id'])).fetchall())
    assert indices[administrador['id']] != indices[medica_aprovada['id']]
    # Editar outro paciente para o número repetido também é recusado; regravar o próprio número, não.
    _, terceiro = _criar(admin)
    r = admin.post(f"/api/pacientes/{terceiro['id']}", json={campo: numero})
    assert r.status_code == 409 and r.get_json()['paciente_id'] == criado['id']
    assert admin.get(f"/api/pacientes/{terceiro['id']}").get_json()['paciente'][campo] != numero
    assert admin.post(f"/api/pacientes/{criado['id']}", json={campo: com_pontuacao, 'municipio': 'Trindade'}).status_code == 200
    # Tirar o número libera o índice.
    assert admin.post(f"/api/pacientes/{criado['id']}", json={campo: ''}).status_code == 200
    assert admin.post(f"/api/pacientes/{terceiro['id']}", json={campo: numero}).status_code == 200
    assert pacientes.excluir(medica_aprovada['id'], da_medica['id'])


def test_duas_gravacoes_simultaneas_do_mesmo_numero_o_banco_recusa_a_segunda(administrador, monkeypatch):
    """Sem a conferência anterior à gravação (duas requisições no mesmo instante), o índice único do banco recusa."""
    primeiro = pacientes.criar(administrador['id'], _ficticio())
    conferir, chamadas = pacientes._recusar_duplicado, []

    def so_depois_da_gravacao(*args, **kwargs):
        chamadas.append(1)
        if len(chamadas) > 1:
            conferir(*args, **kwargs)
    monkeypatch.setattr(pacientes, '_recusar_duplicado', so_depois_da_gravacao)
    with pytest.raises(pacientes.Duplicado) as recusa:
        pacientes.criar(administrador['id'], {'nome': 'Corrida Fictícia', 'cns': primeiro['cns']})
    assert recusa.value.campo == 'cns' and recusa.value.paciente_id == primeiro['id'] and len(chamadas) == 2


# --- Validação -----------------------------------------------------------------------------------

def test_cpf_valido():
    assert pacientes.cpf_valido(_cpf()) and pacientes.cpf_valido('529.982.247-25')
    for errado in ('529.982.247-26', '11111111111', '00000000000', '5299822472', '529982247255', '', None, 52998224725):
        assert not pacientes.cpf_valido(errado), errado


@pytest.mark.parametrize('troca, campo, trecho', [
    ({'cpf': '529.982.247-26'}, 'cpf', 'CPF'),
    ({'cpf': '111.111.111-11'}, 'cpf', 'CPF'),
    ({'cpf': 52998224725}, 'cpf', 'CPF'),
    ({'cns': '700000000000001'}, 'cns', 'CNS'),
    ({'cns': '123'}, 'cns', 'CNS'),
    ({'nascimento': '2999-01-01'}, 'nascimento', 'data de nascimento'),
    ({'nascimento': '23/04/1931'}, 'nascimento', 'data de nascimento'),
    ({'nascimento': '1931-02-30'}, 'nascimento', 'data de nascimento'),
    ({'nascimento': '1899-12-31'}, 'nascimento', 'data de nascimento'),
    ({'uf': 'XX'}, 'uf', 'UF'),
    ({'uf': 'Goiás'}, 'uf', 'UF'),
    ({'sexo': 'outro'}, 'sexo', 'Sexo'),
    ({'raca': 'azul'}, 'raca', 'Raça/cor'),
    ({'email': 'sem-arroba'}, 'email', 'e-mail'),
    ({'email': 'a\ud800@b.co'}, 'email', 'e-mail'),                 # substituto solto: dava 500
    ({'email': 'fic\x00ticio@exemplo.test'}, 'email', 'e-mail'),
    ({'email': 'ficticio@exemplo.test\x07'}, 'email', 'e-mail'),
    ({'email': 'ficticio\u200b@exemplo.test'}, 'email', 'e-mail'),
    ({'email': 'f' * 242 + '@exemplo.test'}, 'email', 'e-mail'),      # 255 caracteres
    ({'email': 'a@' * 30000}, 'email', 'e-mail'),
    ({'cep': '7400'}, 'cep', 'CEP'),
    ({'ibge': '52087'}, 'ibge', 'IBGE'),
    ({'nome': ''}, 'nome', 'nome do paciente'),
    ({'nome': 'X'}, 'nome', 'nome do paciente'),
    ({'nome': 'N' * 151}, 'nome', '150 caracteres'),
    ({'mae': 'M' * 121}, 'mae', '120 caracteres'),
    ({'prontuario': ['1']}, 'prontuario', 'texto'),
    ({'planos': [{'operadora': 'Plano Fictício'}] * 6}, 'planos', 'até 5 planos'),
    ({'planos': [{'carteira': '123'}]}, 'planos', 'operadora'),
    ({'planos': [{'operadora': 'Plano Fictício', 'senha': 'x'}]}, 'planos', 'formato inválido'),
    ({'planos': [{'operadora': 'Plano Fictício', 'validade': '12/2031'}]}, 'planos', 'Validade'),
    ({'planos': [{'operadora': 'Plano Fictício', 'validade': '2031-13'}]}, 'planos', 'Validade'),
    ({'planos': [{'operadora': 'Plano Fictício', 'carteira': '9' * 31}]}, 'planos', '30 caracteres'),
    ({'planos': 'Plano Fictício'}, 'planos', 'lista'),
    ({'ficha': {'observacao': 'x' * (64 * 1024)}}, 'ficha', '64 KB'),
    ({'ficha': {'exames': {'hba1c': 7}}}, 'ficha', 'Ficha clínica'),
    ({'ficha': {'lista': [['aninhada']]}}, 'ficha', 'Ficha clínica'),
    ({'ficha': ['peso', 70]}, 'ficha', 'Ficha clínica'),
    ({'ficha': {'__proto__': 'x'}}, 'ficha', 'nome reservado'),
    ({'ficha': {'peso': 70, 'constructor': 'x'}}, 'ficha', 'nome reservado'),
    ({'ficha': {'prototype': ['x']}}, 'ficha', 'nome reservado'),
    ({'ficha': {' __proto__ ': 1}}, 'ficha', 'nome reservado'),
    ({'ficha': {'__proto__': {'admin': True}}}, 'ficha', 'nome reservado'),
    ({'planos': [{'operadora': 'Plano Fictício', '__proto__': 'x'}]}, 'planos', 'formato inválido'),
])
def test_dado_invalido_e_recusado_sem_gravar_e_sem_devolver_o_que_foi_enviado(admin, contas, troca, campo, trecho):
    dados = _ficticio(**troca)
    antes = _contagens(contas)
    r = admin.post('/api/pacientes', json=dados)
    assert r.status_code == 400, r.get_json()
    corpo = r.get_json()
    assert corpo['error'] == 'Confira os dados informados.' and corpo['campos'] == [campo]
    assert len(corpo['erros']) == 1 and trecho in corpo['erros'][0], corpo['erros']
    assert set(corpo) == {'error', 'erros', 'campos'}
    texto = r.get_data(as_text=True)
    assert not any(s in texto for s in _segredos(dados))
    assert _contagens(contas) == antes                      # nada gravado, nem na trilha


def test_chave_desconhecida_e_recusada_sem_repetir_o_nome_dela(admin):
    r = admin.post('/api/pacientes', json=_ficticio(**{'Apelido Secreto Fictício': 'Tico', 'id': 7}))
    assert r.status_code == 400 and r.get_json()['campos'] == []
    assert r.get_json()['erros'] == ['Há campos que o cadastro de pacientes não aceita.']
    assert 'Apelido' not in r.get_data(as_text=True) and 'Tico' not in r.get_data(as_text=True)
    _, criado = _criar(admin)
    assert admin.post(f"/api/pacientes/{criado['id']}", json={'usuario_id': 1}).status_code == 400


def test_varios_erros_voltam_juntos_e_a_edicao_tambem_valida(admin):
    r = admin.post('/api/pacientes', json={'cpf': '1', 'uf': 'XX', 'nascimento': 'ontem'})
    assert r.status_code == 400 and r.get_json()['campos'] == ['nascimento', 'cpf', 'uf', 'nome']
    _, criado = _criar(admin)
    r = admin.post(f"/api/pacientes/{criado['id']}", json={'cns': '123', 'ficha': {'a': float('nan')}})
    assert r.status_code == 400 and r.get_json()['campos'] == ['cns', 'ficha']
    assert admin.get(f"/api/pacientes/{criado['id']}").get_json()['paciente'] == criado      # nada mudou


@pytest.mark.parametrize('corpo', [None, [], 'texto', 12, [{'nome': 'Lista Fictícia'}]])
def test_corpo_que_nao_e_objeto_json_e_recusado(admin, corpo):
    _, criado = _criar(admin)
    for caminho in ('/api/pacientes', f"/api/pacientes/{criado['id']}"):
        r = admin.post(caminho, json=corpo) if corpo is not None else admin.post(caminho, data='nome=Formulário', content_type='application/x-www-form-urlencoded')
        assert r.status_code == 400 and r.get_json()['erros'] == ['Envie os dados do paciente em JSON.']


def test_envio_grande_demais_e_recusado(admin):
    r = admin.post('/api/pacientes', json=_ficticio(ficha={'observacao': 'x' * (200 * 1024)}))
    assert r.status_code == 413 and r.get_json() == {'error': 'O envio passa de 128 KB.'}


def test_campos_aceitos_e_normalizacao():
    limpo = pacientes.validar({'nome': '  Paciente   Fictício\tNormalizado ', 'cpf': '529.982.247-25', 'uf': 'go',
                               'sexo': ' Masculino ', 'raca': 'Indígena', 'email': ' Pessoa@Exemplo.TEST ', 'cep': '74.000-000',
                               'nascimento': pacientes._hoje().isoformat(), 'nome_social': '', 'mae': None, 'planos': [],
                               'ficha': {}, 'telefone': '   '})
    assert limpo == {'nome': 'Paciente Fictício Normalizado', 'nascimento': pacientes._hoje().isoformat(), 'sexo': 'masculino',
                     'cpf': '52998224725', 'raca': 'indigena', 'email': 'pessoa@exemplo.test', 'cep': '74000000', 'uf': 'GO'}
    plano = pacientes.validar({'nome': 'Plano Fictício', 'planos': [{'operadora': ' Operadora  Fictícia ', 'validade': '2031-12-31'}]})
    assert plano['planos'] == [{'operadora': 'Operadora Fictícia', 'carteira': '', 'validade': '2031-12-31'}]
    assert set(pacientes.RACAS) == {'branca', 'preta', 'parda', 'amarela', 'indigena'}
    assert pacientes.CAMPOS == ('nome', 'nome_social', 'nascimento', 'sexo', 'cpf', 'cns', 'mae', 'raca', 'prontuario',
                                'responsavel', 'telefone', 'email', 'cep', 'endereco', 'municipio', 'ibge', 'uf', 'planos', 'ficha')


def test_tetos_dos_campos_sao_os_mesmos_do_laudo_de_apac_e_do_pedido():
    """Os campos que o sistema já pedia têm, no cadastro, o mesmo teto de onde já eram pedidos."""
    from src.routes import checkup_intelligent as rotas
    from src.utils import contas, validacao
    for campo in ('mae', 'telefone', 'endereco', 'municipio', 'prontuario', 'responsavel'):
        assert pacientes.LIMITES[campo] == rotas._CAMPOS_PACIENTE_APAC[campo], campo
    assert pacientes.LIMITES['nome'] == rotas.MAX_TAMANHO_NOME
    assert max(len(rotulo) for rotulo in pacientes.RACAS.values()) <= rotas._CAMPOS_PACIENTE_APAC['raca']
    assert pacientes.SEXOS is validacao.SEXOS
    assert pacientes._ler_uf('go') == 'GO' and set(contas.UFS) >= {'GO', 'DF', 'SP'}
    fonte = Path(pacientes.__file__).read_text(encoding='utf-8')
    assert 'contas.cns_valido(' in fonte and 'contas.UFS' in fonte and 'contas._EMAIL' in fonte


# --- Posse -------------------------------------------------------------------------------------

def test_paciente_de_outra_conta_nao_existe_nem_para_o_administrador(admin, administrador, medica_aprovada, contas):
    dados = _ficticio()
    da_medica = pacientes.criar(medica_aprovada['id'], dados)
    pid = da_medica['id']
    antes = _contagens(contas)
    # Pela API, o administrador não lê, não edita, não exporta, não exclui e não vê na lista.
    for metodo, caminho in ROTAS[3:]:
        r = _pedir(admin, metodo, caminho, pid, json={'municipio': 'Goiânia'})
        assert r.status_code == 404 and r.get_json() == {'error': 'Paciente não encontrado.'}, caminho
    assert _contagens(contas) == antes                       # recusa não entra na trilha nem mexe em nada
    for termo in ('', dados['nome'], dados['cns'][-4:]):
        assert pid not in [p['id'] for p in _buscar(admin, termo).get_json()['pacientes']]
    # Pelo módulo, com o usuario_id errado, a mesma coisa.
    outro = administrador['id']
    assert pacientes.ler(outro, pid) is None and pacientes.exportar(outro, pid) is None
    assert pacientes.atualizar(outro, pid, {'nome': 'Trocado Fictício'}) is None and pacientes.excluir(outro, pid) is False
    assert pid not in [p['id'] for p in pacientes.listar(outro)['pacientes']]
    assert pacientes.trilha(outro, pid) == []
    # Continua inteiro para a dona.
    assert pacientes.ler(medica_aprovada['id'], pid) == da_medica
    assert [p['id'] for p in pacientes.listar(medica_aprovada['id'], dados['nome'])['pacientes']] == [pid]
    assert pacientes.excluir(medica_aprovada['id'], pid) is True


def test_identificador_fora_da_faixa_e_paciente_inexistente(admin, administrador):
    assert admin.get(f'/api/pacientes/{2 ** 70}').status_code == 404
    assert admin.post(f'/api/pacientes/{2 ** 70}/excluir').status_code == 404
    assert admin.get('/api/pacientes/0').status_code == 404 and admin.get('/api/pacientes/-1').status_code == 404
    assert pacientes.ler(administrador['id'], 'abc') is None and pacientes.excluir(administrador['id'], None) is False


# --- Quem pode usar ----------------------------------------------------------------------------

def test_lista_de_rotas_esta_completa(app):
    """Rota nova do cadastro tem de entrar em ROTAS, para passar pelos testes de acesso abaixo."""
    do_app = {(metodo, re.sub(r'<[^>]+>', '{id}', regra.rule)) for regra in app.url_map.iter_rules()
              if regra.rule.startswith('/api/pacientes') for metodo in regra.methods - {'HEAD', 'OPTIONS'}}
    assert do_app == {(metodo, caminho.split('?')[0]) for metodo, caminho in ROTAS}
    # Fora da API só existe a página /pacientes (api/index.py), que não devolve dado de paciente.
    outras = {regra.rule: regra.endpoint for regra in app.url_map.iter_rules()
              if 'pacientes' in regra.rule and not regra.endpoint.startswith('pacientes.')}
    assert outras == {'/pacientes': 'pacientes_page'}


@pytest.mark.parametrize('metodo, caminho', ROTAS)
def test_sem_login_a_resposta_e_401(anonimo, admin, contas, metodo, caminho):
    _, criado = _criar(admin)
    antes = _contagens(contas)
    r = _pedir(anonimo, metodo, caminho, criado['id'], json=_ficticio())
    assert r.status_code == 401 and r.get_json()['login'] == '/login'
    assert 'Fict' not in r.get_data(as_text=True) and _contagens(contas) == antes


@pytest.mark.parametrize('metodo, caminho', ROTAS)
def test_usuario_comum_aprovado_recebe_403(client, admin, contas, metodo, caminho):
    _, criado = _criar(admin)
    antes = _contagens(contas)
    r = _pedir(client, metodo, caminho, criado['id'], json=_ficticio())
    assert r.status_code == 403 and r.get_json() == {'error': 'Acesso restrito ao administrador.'}
    assert _contagens(contas) == antes
    assert admin.get(f"/api/pacientes/{criado['id']}").get_json()['paciente'] == criado


@pytest.mark.parametrize('metodo, caminho', ROTAS)
def test_pedido_vindo_de_outro_site_e_recusado(admin, contas, metodo, caminho):
    _, criado = _criar(admin)
    antes = _contagens(contas)
    for cabecalhos in ({'Origin': 'https://outro.exemplo'}, {'Sec-Fetch-Site': 'cross-site'}):
        r = _pedir(admin, metodo, caminho, criado['id'], json=_ficticio(), headers=cabecalhos)
        assert r.status_code == 403 and 'origem' in r.get_json()['error'], cabecalhos
    assert _contagens(contas) == antes


@pytest.mark.parametrize('metodo, caminho', ROTAS)
def test_sem_o_cabecalho_proprio_o_pedido_e_recusado(app, administrador, admin, contas, metodo, caminho):
    """Leitura ou gravação sem `X-Requested-With: evidens` responde 403, mesmo com a sessão do administrador e
    vinda do próprio site: página de outro site não consegue mandar esse cabeçalho sem a permissão do servidor."""
    from tests.conftest import _entrar
    _, criado = _criar(admin)
    sem = app.test_client()
    assert _entrar(sem, administrador['email']).status_code == 200
    antes = _contagens(contas)
    for cabecalhos in ({}, {'X-Requested-With': 'XMLHttpRequest'}, {'X-Requested-With': ''},
                       {'Origin': 'http://localhost', 'Sec-Fetch-Site': 'same-origin'}):
        r = _pedir(sem, metodo, caminho, criado['id'], json=_ficticio(), headers=cabecalhos)
        assert r.status_code == 403 and 'X-Requested-With' in r.get_json()['error'], cabecalhos
        assert 'Fict' not in r.get_data(as_text=True) and r.headers['Cache-Control'] == 'no-store'
    assert _contagens(contas) == antes
    r = _pedir(sem, metodo, caminho, criado['id'], json=_ficticio(), headers={'X-Requested-With': 'Evidens'})
    assert r.status_code in (200, 201)


def test_busca_pela_url_nao_existe_mais(admin, contas):
    """O termo (um nome) não pode ir no endereço: fica nos registros de acesso da hospedagem."""
    dados, criado = _criar(admin)
    antes = _contagens(contas)
    for consulta in ({'busca': dados['nome']}, {'busca': ''}):
        r = admin.get('/api/pacientes', query_string=consulta)
        assert r.status_code == 400 and 'POST /api/pacientes/buscar' in r.get_json()['error']
        assert 'pacientes' not in r.get_json() and 'Fict' not in r.get_data(as_text=True)
    assert _contagens(contas) == antes
    fonte = (RAIZ / 'src' / 'routes' / 'pacientes.py').read_text(encoding='utf-8')
    assert "request.args.get('busca'" not in fonte
    assert criado['id'] in [p['id'] for p in admin.get('/api/pacientes').get_json()['pacientes']]


def test_sem_banco_ou_com_termos_pendentes_o_cadastro_fica_fechado(app, admin, administrador, contas, monkeypatch):
    from src.utils import termos
    _, criado = _criar(admin)
    monkeypatch.setattr(termos, 'VERSAO', '99.0-de-teste')              # o administrador ainda não aceitou esta versão
    r = admin.get(f"/api/pacientes/{criado['id']}")
    assert r.status_code == 403 and r.headers[termos.CABECALHO] == 'pendente' and 'paciente' not in r.get_json()
    monkeypatch.undo()
    monkeypatch.delenv('DATABASE_URL')
    assert app.test_client().get('/api/pacientes', headers=CABECALHO).status_code == 503


def test_regra_de_quem_pode_usar_fica_num_lugar_so(administrador, medica_aprovada):
    assert pacientes.habilitado_para(administrador) is True
    assert pacientes.habilitado_para(medica_aprovada) is False
    assert pacientes.habilitado_para(None) is False and pacientes.habilitado_para({}) is False
    # As rotas não repetem a regra: todas passam pela mesma porta, que pergunta a `habilitado_para`.
    fonte = (RAIZ / 'src' / 'routes' / 'pacientes.py').read_text(encoding='utf-8')
    assert fonte.count('@exigir_cadastro') == fonte.count('@pacientes_bp.route(') == len({c.split('?')[0] + m for m, c in ROTAS})
    assert 'exigir_administrador(conferida)' in fonte and fonte.count("['administrador']") == 1


def test_abrir_o_cadastro_e_trocar_so_a_regra_e_cada_conta_ve_so_os_seus(app, client, admin, anonimo, medica_aprovada, monkeypatch):
    """Ensaio da abertura: com a regra aceitando contas aprovadas, a médica usa o cadastro e fica isolada do
    administrador nos dois sentidos. Sem a troca, ela recebe 403 (teste acima)."""
    _, do_admin = _criar(admin)
    monkeypatch.setattr(pacientes, 'habilitado_para', lambda u: bool(u) and u.get('situacao') == 'aprovado')
    dados = _ficticio()
    r = client.post('/api/pacientes', json=dados)
    assert r.status_code == 201
    da_medica = r.get_json()['paciente']
    assert [p['id'] for p in client.get('/api/pacientes').get_json()['pacientes']] == [da_medica['id']]
    assert client.get(f"/api/pacientes/{da_medica['id']}").get_json()['paciente']['nome'] == dados['nome']
    for metodo, caminho in ROTAS[3:]:
        assert _pedir(client, metodo, caminho, do_admin['id'], json={'municipio': 'Goiânia'}).status_code == 404, caminho
        assert _pedir(admin, metodo, caminho, da_medica['id'], json={'municipio': 'Goiânia'}).status_code == 404, caminho
    assert da_medica['id'] not in [p['id'] for p in admin.get('/api/pacientes').get_json()['pacientes']]
    assert admin.get(f"/api/pacientes/{do_admin['id']}").status_code == 200
    assert anonimo.get('/api/pacientes').status_code == 401                       # sem login continua fechado
    assert client.post(f"/api/pacientes/{da_medica['id']}/excluir").status_code == 200
    # Regra que recusa todo mundo fecha também para o administrador.
    monkeypatch.setattr(pacientes, 'habilitado_para', lambda u: False)
    assert admin.get('/api/pacientes').status_code == 403 and client.get('/api/pacientes').status_code == 403


# --- Trilha de auditoria -----------------------------------------------------------------------

def test_cada_acao_entra_na_trilha_sem_dado_de_paciente(admin, administrador, contas):
    uid = administrador['id']
    with contas._conexao() as executar:
        ultimo = executar('SELECT COALESCE(MAX(id), 0) FROM pacientes_acessos').fetchone()[0]
    dados, criado = _criar(admin)
    pid = criado['id']
    admin.get(f'/api/pacientes/{pid}')
    _buscar(admin, dados['nome'])
    admin.post('/api/pacientes/buscar', json={'busca': dados['cns'][-4:]})
    admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Aparecida de Goiânia'})
    admin.get(f'/api/pacientes/{pid}/exportar')
    admin.post(f'/api/pacientes/{pid}/excluir')
    # O que não aconteceu não entra: pedido recusado, paciente que não existe.
    admin.post('/api/pacientes', json={'nome': ''})
    admin.get(f'/api/pacientes/{pid}')
    admin.post(f'/api/pacientes/{pid}/excluir')
    with contas._conexao() as executar:
        linhas = executar('SELECT id, paciente_id, usuario_id, acao, quando FROM pacientes_acessos WHERE id > ? ORDER BY id',
                          (ultimo,)).fetchall()
    assert [(l[1], l[2], l[3]) for l in linhas] == [
        (pid, uid, 'criar'), (pid, uid, 'ver'), (None, uid, 'listar'), (None, uid, 'listar'), (pid, uid, 'editar'),
        (pid, uid, 'exportar'), (pid, uid, 'excluir')]
    assert all(isinstance(l[4], int) and abs(l[4] - criado['criado_em']) < 300 for l in linhas)
    assert {l[3] for l in linhas} == set(pacientes.ACOES)
    # Só números e o nome da ação: nada do paciente, nem o termo da busca.
    texto = ' '.join(str(c) for l in linhas for c in l)
    assert re.fullmatch(r'[0-9a-zN ]+', texto) and not any(s in texto for s in _segredos(dados))
    # Excluir apagou o registro e manteve a trilha dele.
    with contas._conexao() as executar:
        assert executar('SELECT COUNT(*) FROM pacientes WHERE id = ?', (pid,)).fetchone()[0] == 0
    assert [a['acao'] for a in pacientes.trilha(uid, pid)] == ['excluir', 'exportar', 'editar', 'ver', 'criar']
    assert all(set(a) == {'paciente_id', 'acao', 'quando'} for a in pacientes.trilha(uid))


def test_se_a_trilha_nao_grava_a_acao_nao_acontece(administrador, contas, monkeypatch):
    criado = pacientes.criar(administrador['id'], _ficticio())
    antes = _contagens(contas)

    def trilha_fora(*args, **kwargs):
        raise RuntimeError('trilha fora do ar')
    monkeypatch.setattr(pacientes, '_registrar', trilha_fora)
    for acao in (lambda: pacientes.criar(administrador['id'], _ficticio()),
                 lambda: pacientes.atualizar(administrador['id'], criado['id'], {'municipio': 'Senador Canedo'}),
                 lambda: pacientes.excluir(administrador['id'], criado['id']),
                 lambda: pacientes.ler(administrador['id'], criado['id']),
                 lambda: pacientes.exportar(administrador['id'], criado['id']),
                 lambda: pacientes.listar(administrador['id'])):
        with pytest.raises(RuntimeError, match='trilha fora do ar'):
            acao()
    monkeypatch.undo()
    assert _contagens(contas) == antes
    assert pacientes.ler(administrador['id'], criado['id'])['municipio'] == 'Goiânia'


# --- O resto do sistema continua sem guardar nada -----------------------------------------------

def test_eventos_de_uso_continuam_com_as_mesmas_colunas_e_sem_dado_de_paciente(admin, contas):
    from src.utils import uso
    with contas._conexao() as executar:
        antes = executar('SELECT COUNT(*) FROM eventos_uso').fetchone()[0]
    dados, criado = _criar(admin)
    for metodo, caminho in ROTAS:
        _pedir(admin, metodo, caminho, criado['id'], json={'municipio': 'Goiânia'})
    with contas._conexao() as executar:
        colunas = [c[1] for c in executar('PRAGMA table_info(eventos_uso)').fetchall()]
        depois = executar('SELECT COUNT(*) FROM eventos_uso').fetchone()[0]
        tipos = {l[0] for l in executar('SELECT DISTINCT tipo FROM eventos_uso').fetchall()}
    assert colunas == ['id', 'usuario_id', 'tipo', 'criado_em']
    assert depois == antes                                  # o cadastro não gera evento de uso
    assert tipos <= set(uso.TIPOS) and not any('paciente' in t for t in uso.TIPOS)
    painel = admin.get('/api/analytics/stats').get_data(as_text=True)
    assert not any(s in painel for s in _segredos(dados))


def test_rotas_do_checkup_do_preoperatorio_e_dos_pdfs_nao_tocam_no_cadastro(client, admin, contas, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError('o check-up não pode chamar o cadastro de pacientes')
    with contas._conexao() as executar:
        antes = [executar(f'SELECT COUNT(*), COALESCE(MAX(id), 0) FROM {t}').fetchone() for t in ('pacientes', 'pacientes_acessos')]
    for nome in ('criar', 'listar', 'ler', 'atualizar', 'excluir', 'exportar', '_registrar', '_cofre'):
        monkeypatch.setattr(pacientes, nome, proibido)
    nome_ficticio = 'Paciente Fictícia Do Check-up Umburana'
    paciente = {'nome': nome_ficticio, 'idade': '50', 'sexo': 'feminino'}
    assert client.post('/api/checkup-intelligent', json=dict(CHECKUP, nome_paciente=nome_ficticio)).status_code == 200
    preop = dict(idade=72, sexo='masculino', peso=78, cirurgia='colectomia', urgencia='eletiva', condicoes=['dac'],
                 medicacoes=['losartana'], nome_paciente=nome_ficticio)
    assert client.post('/api/preoperatorio', json=preop).status_code == 200
    for rota, item in (('gerar-pdf-exames-laboratoriais', {'titulo': 'Hemograma completo', 'categoria': 'laboratorio'}),
                       ('gerar-pdf-exames-imagem', {'titulo': 'Radiografia de tórax', 'categoria': 'imagem'})):
        assert client.post(f'/api/{rota}', json={'dados_paciente': paciente, 'recomendacoes': [item]}).status_code == 200
    assert admin.post('/api/checkup-intelligent', json=dict(CHECKUP, nome_paciente=nome_ficticio)).status_code == 200
    with contas._conexao() as executar:
        depois = [executar(f'SELECT COUNT(*), COALESCE(MAX(id), 0) FROM {t}').fetchone() for t in ('pacientes', 'pacientes_acessos')]
    assert depois == antes
    assert b'Umburana' not in _banco_cru()


def test_so_as_rotas_do_cadastro_importam_o_modulo_de_pacientes():
    """O motor, os PDFs, as contas e o painel de uso não conhecem o cadastro: só src/routes/pacientes.py o usa."""
    quem_importa = set()
    for arquivo in [*(RAIZ / 'src').rglob('*.py'), *(RAIZ / 'api').rglob('*.py'), *(RAIZ / 'scripts').rglob('*.py')]:
        for no in ast.walk(ast.parse(arquivo.read_text(encoding='utf-8'))):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                nomes = [f'{no.module}.{a.name}' for a in no.names] + [no.module or '']
            if any(n == 'src.utils.pacientes' or n.startswith('src.utils.pacientes.') for n in nomes):
                quem_importa.add(str(arquivo.relative_to(RAIZ)))
    assert quem_importa == {'src/routes/pacientes.py'}
    motor = (RAIZ / 'src' / 'routes' / 'checkup_intelligent.py').read_text(encoding='utf-8')
    assert 'utils.pacientes' not in motor and 'import pacientes' not in motor and 'pacientes_bp' not in motor
    assert 'pacientes' not in (RAIZ / 'src' / 'utils' / 'uso.py').read_text(encoding='utf-8')


def test_so_a_tela_do_cadastro_chama_as_rotas(app, client, admin):
    """Fase 2: a tela existe, só para o administrador (tests/test_pacientes_tela.py). As rotas só são citadas pelos
    scripts do cadastro; as páginas não trazem o endereço da API, e /pacientes.html não é servido."""
    citam = {pagina.name for pagina in sorted(RAIZ.glob('*.html')) + sorted((RAIZ / 'static').glob('*.js'))
             if '/api/pacientes' in pagina.read_text(encoding='utf-8')}
    assert citam == {'pacientes.js'}
    assert admin.get('/pacientes').status_code == 200 and client.get('/pacientes').status_code == 302
    for cliente in (client, admin):
        assert cliente.get('/pacientes.html').status_code == 404


def test_documentacao_acompanha_o_contrato():
    """A tela (fase 2) vai ser escrita a partir de docs/pacientes.md: campos, rotas e códigos têm de estar lá."""
    doc = (RAIZ / 'docs' / 'pacientes.md').read_text(encoding='utf-8')
    for campo in (*pacientes.CAMPOS, *pacientes.RACAS, *pacientes.ACOES, 'cns_final', 'truncado', 'ilegiveis',
                  'paciente_id', 'criado_em', 'atualizado_em'):
        assert f'`{campo}`' in doc, campo
    for trecho in ('{operadora, carteira, validade}', '{pacientes, total, truncado, ilegiveis}', '"duplicado"',
                   '"sem_chave"', '"ilegivel"', 'pacientes.habilitado_para', 'Cache-Control: no-store'):
        assert trecho in doc, trecho
    for metodo, caminho in ROTAS:
        assert f"`{metodo} {caminho.split('?')[0].replace('{id}', '<id>')}" in doc, caminho
    for codigo in ('400', '401', '403', '404', '409', '413', '500', '503'):
        assert f'| {codigo} |' in doc, codigo
    assert str(pacientes.LIMITE_DA_LISTA) in doc and '64 KB' in doc and 'evidens-pacientes-v1' in doc
    perigos = (RAIZ / 'docs' / 'registro-de-perigos.md').read_text(encoding='utf-8')
    assert '| P-26 |' in perigos and 'docs/pacientes.md' in perigos.split('| P-10 |')[1].split('\n')[0]


def test_resposta_do_cadastro_nao_passa_pelo_tradutor(admin):
    """Em inglês, a API traduz os campos "error", "erros" e "mensagem". No cadastro isso mexeria no que o médico
    digitou: a ficha pode ter um campo com esses nomes."""
    ficha = {'mensagem': 'Conta criada com sucesso.', 'erros': ['Informe um e-mail válido.'], 'error': 'Plano salvo.'}
    r = admin.post('/api/pacientes?lang=en', json=_ficticio(ficha=ficha))
    assert r.status_code == 201 and r.get_json()['paciente']['ficha'] == ficha and r.get_json()['mensagem'] == 'Paciente salvo.'
    pid = r.get_json()['paciente']['id']
    assert admin.get(f'/api/pacientes/{pid}?lang=en').get_json()['paciente']['ficha'] == ficha
    assert admin.get(f'/api/pacientes/{pid}/exportar?lang=en').get_json()['paciente']['ficha'] == ficha
    assert admin.post('/api/pacientes?lang=en', json={'nome': ''}).get_json()['error'] == 'Confira os dados informados.'


# --- Achados da revisão de segurança -----------------------------------------------------------

class _RegexVigiada:
    """Fica no lugar de `contas._EMAIL` e anota o tamanho de cada texto que chega à expressão regular."""

    def __init__(self, original):
        self.original, self.tamanhos = original, []

    def match(self, texto):
        self.tamanhos.append(len(texto))
        return self.original.match(texto)


def test_email_longo_e_recusado_antes_da_expressao_regular(admin, anonimo, contas, monkeypatch):
    """A expressão do e-mail tem custo quadrático: texto acima do teto não chega a ela, nem no cadastro de
    pacientes nem em /api/auth/cadastro. Dentro do teto, o que era aceito continua aceito."""
    vigia = _RegexVigiada(contas._EMAIL)
    monkeypatch.setattr(contas, '_EMAIL', vigia)
    for longo in ('a@' * 30000, 'f' * 242 + '@exemplo.test', '@' * 255, ' ' * 10 + 'f' * 300 + '@exemplo.test'):
        r = admin.post('/api/pacientes', json=_ficticio(email=longo))
        assert r.status_code == 400 and r.get_json()['campos'] == ['email']
        r = anonimo.post('/api/auth/cadastro', json=dict(email=longo, nome='Pessoa Fictícia Longa', registro='CRM-GO 33333',
                                                         perfil='medico', senha='senha-de-teste-123', aceite_termos=True))
        assert r.status_code == 400 and r.get_json()['erros'] == ['Informe um e-mail válido.']
        with pytest.raises(contas.DadosInvalidos):
            contas._validar_cadastro(longo, 'Pessoa Fictícia Longa', 'CRM-GO 33333', 'medico', 'senha-de-teste-123')
    assert vigia.tamanhos == []                                   # nenhum deles chegou à expressão regular
    # No teto (254) e abaixo dele nada mudou.
    no_teto = 'f' * 241 + '@exemplo.test'
    assert len(no_teto) == 254
    assert pacientes.validar({'nome': 'Teto Fictício', 'email': f'  {no_teto.upper()}  '})['email'] == no_teto
    contas._validar_cadastro(no_teto, 'Pessoa Fictícia Teto', 'CRM-GO 33333', 'medico', 'senha-de-teste-123')
    contas._validar_cadastro('ficticia.teto@exemplo.test', 'Pessoa Fictícia Teto', 'CRM-GO 33333', 'medico', 'senha-de-teste-123')
    for errado in ('sem-arroba', 'a@b', 'a b@exemplo.test', ''):
        with pytest.raises(contas.DadosInvalidos):
            contas._validar_cadastro(errado, 'Pessoa Fictícia Teto', 'CRM-GO 33333', 'medico', 'senha-de-teste-123')
    assert vigia.tamanhos and max(vigia.tamanhos) <= 254
    # Substituto solto no e-mail da conta: 400, não 500.
    r = anonimo.post('/api/auth/cadastro', json=dict(email='a\ud800@b.co', nome='Pessoa Fictícia Solta', registro='CRM-GO 33333',
                                                     perfil='medico', senha='senha-de-teste-123', aceite_termos=True))
    assert r.status_code == 400 and r.get_json()['erros'] == ['Informe um e-mail válido.']


def test_email_com_substituto_solto_na_edicao_tambem_e_400(admin):
    _, criado = _criar(admin)
    r = admin.post(f"/api/pacientes/{criado['id']}", json={'email': 'a\ud800@b.co'})
    assert r.status_code == 400 and r.get_json()['campos'] == ['email']
    assert admin.get(f"/api/pacientes/{criado['id']}").get_json()['paciente'] == criado


def test_ficha_recusa_nomes_reservados_e_aceita_os_parecidos():
    assert pacientes.CHAVES_RESERVADAS == {'__proto__', 'constructor', 'prototype'}
    ficha = {'proto': 1, 'construtor': 'x', 'Constructor': 2, 'observacao': '__proto__'}
    assert pacientes.validar({'nome': 'Ficha Fictícia', 'ficha': ficha})['ficha'] == ficha
    for chave in pacientes.CHAVES_RESERVADAS:
        for corpo in ({chave: 'Nome Fictício'}, {'nome': 'Reservado Fictício', chave: 1}):
            with pytest.raises(pacientes.DadosInvalidos):
                pacientes.validar(corpo)


def test_paciente_excluido_no_meio_da_edicao_responde_404_sem_gravar(admin, administrador, contas, monkeypatch):
    """Outro pedido exclui o paciente entre a leitura e a gravação da edição: a edição responde 404, não diz
    "salvo" e não deixa linha "editar" na trilha depois de "excluir"."""
    uid = administrador['id']
    _, criado = _criar(admin)
    pid = criado['id']
    validar = pacientes.validar

    def exclui_e_valida(dados):
        assert pacientes.excluir(uid, pid) is True            # outra conexão, no meio da edição
        return validar(dados)
    monkeypatch.setattr(pacientes, 'validar', exclui_e_valida)
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis'})
    monkeypatch.undo()
    assert r.status_code == 404 and r.get_json() == {'error': 'Paciente não encontrado.'}
    assert [a['acao'] for a in pacientes.trilha(uid, pid)] == ['excluir', 'criar']
    with contas._conexao() as executar:
        assert executar('SELECT COUNT(*) FROM pacientes WHERE id = ?', (pid,)).fetchone()[0] == 0
    assert admin.get(f'/api/pacientes/{pid}').status_code == 404


def test_paciente_alterado_no_meio_da_edicao_responde_409_e_nao_perde_a_outra_gravacao(admin, administrador, monkeypatch):
    uid = administrador['id']
    _, criado = _criar(admin)
    pid = criado['id']
    validar, vezes = pacientes.validar, []

    def edita_e_valida(dados):
        vezes.append(1)
        if len(vezes) == 1:                                   # outra conexão grava primeiro
            assert pacientes.atualizar(uid, pid, {'telefone': '(62) 91111-1111'})['telefone'] == '(62) 91111-1111'
        return validar(dados)
    monkeypatch.setattr(pacientes, 'validar', edita_e_valida)
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis'})
    monkeypatch.undo()
    assert r.status_code == 409 and r.get_json()['codigo'] == 'conflito' and 'paciente' not in r.get_json()
    assert 'Fict' not in r.get_data(as_text=True)
    atual = pacientes.ler(uid, pid)
    assert atual['telefone'] == '(62) 91111-1111' and atual['municipio'] == 'Goiânia'
    assert [a['acao'] for a in pacientes.trilha(uid, pid)] == ['ver', 'editar', 'criar']      # só a edição que gravou
    # Repetir o pedido, agora sozinho, grava.
    assert admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis'}).status_code == 200


def test_update_que_nao_alcanca_nenhuma_linha_nao_vira_salvo(admin, administrador, contas, monkeypatch):
    """O número de linhas do UPDATE é conferido: 0 linhas nunca responde "Paciente salvo." nem entra na trilha."""
    from contextlib import contextmanager
    uid = administrador['id']
    _, criado = _criar(admin)
    pid = criado['id']
    conexao, comandos = contas._conexao, []

    class _NenhumaLinha:
        rowcount = 0

    @contextmanager
    def update_sem_efeito():
        with conexao() as executar:
            def vigiado(sql, params=()):
                comandos.append(sql)
                return _NenhumaLinha() if sql.startswith('UPDATE pacientes') else executar(sql, params)
            yield vigiado
    monkeypatch.setattr(contas, '_conexao', update_sem_efeito)
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis'})
    monkeypatch.undo()
    assert r.status_code == 409 and r.get_json()['codigo'] == 'conflito' and r.get_json().get('ok') is None
    assert any(c.startswith('UPDATE pacientes') for c in comandos)
    assert not any(c.startswith('INSERT INTO pacientes_acessos') for c in comandos)
    assert [a['acao'] for a in pacientes.trilha(uid, pid)] == ['criar']
    assert pacientes.ler(uid, pid)['municipio'] == 'Goiânia'


def test_em_postgres_a_edicao_trava_a_linha_com_for_update(administrador, contas, monkeypatch):
    """Em produção (Postgres) a leitura da edição usa SELECT … FOR UPDATE; em sqlite, que não tem a cláusula, a
    proteção é a condição do UPDATE (testes acima)."""
    from contextlib import contextmanager
    uid = administrador['id']
    criado = pacientes.criar(uid, _ficticio())
    conexao, comandos = contas._conexao, []

    @contextmanager
    def anotando():
        with conexao() as executar:
            def vigiado(sql, params=()):
                comandos.append(sql)
                return executar(sql.replace(' FOR UPDATE', ''), params)      # o sqlite dos testes não conhece a cláusula
            yield vigiado
    monkeypatch.setattr(contas, '_conexao', anotando)
    pacientes.atualizar(uid, criado['id'], {'municipio': 'Trindade'})
    assert not any('FOR UPDATE' in c for c in comandos)                       # sqlite
    comandos.clear()
    monkeypatch.setattr(pacientes, '_em_postgres', lambda: True)
    assert pacientes.atualizar(uid, criado['id'], {'municipio': 'Inhumas'})['municipio'] == 'Inhumas'
    travas = [c for c in comandos if 'FOR UPDATE' in c]
    assert len(travas) == 1 and travas[0].startswith('SELECT dados, criado_em, atualizado_em FROM pacientes WHERE id = ? AND usuario_id = ?')
    assert comandos.index(travas[0]) < next(i for i, c in enumerate(comandos) if c.startswith('UPDATE pacientes'))
    pacientes.ler(uid, criado['id'])
    assert sum('FOR UPDATE' in c for c in comandos) == 1                      # leitura comum não trava


def test_teto_de_pacientes_por_conta(admin, administrador, medica_aprovada, contas, monkeypatch):
    assert pacientes.MAX_PACIENTES_POR_CONTA == 5000
    uid = administrador['id']
    _, criado = _criar(admin)
    with contas._conexao() as executar:
        total = executar('SELECT COUNT(*) FROM pacientes WHERE usuario_id = ?', (uid,)).fetchone()[0]
    monkeypatch.setattr(pacientes, 'MAX_PACIENTES_POR_CONTA', total)
    antes = _contagens(contas)
    dados = _ficticio()
    r = admin.post('/api/pacientes', json=dados)
    assert r.status_code == 409 and r.get_json()['codigo'] == 'limite' and str(total) in r.get_json()['error']
    assert not any(s in r.get_data(as_text=True) for s in _segredos(dados)) and _contagens(contas) == antes
    # O teto é de cada conta, e não impede ler, editar nem excluir; excluir abre vaga.
    da_medica = pacientes.criar(medica_aprovada['id'], _ficticio())
    assert pacientes.excluir(medica_aprovada['id'], da_medica['id'])
    assert admin.post(f"/api/pacientes/{criado['id']}", json={'municipio': 'Goianira'}).status_code == 200
    assert admin.post(f"/api/pacientes/{criado['id']}/excluir").status_code == 200
    assert admin.post('/api/pacientes', json=dados).status_code == 201


def test_texto_cifrado_trocado_de_linha_na_mesma_conta_nao_abre(admin, administrador, contas):
    """O número do registro vai dentro do texto cifrado, junto com o dono: quem mexer direto no banco não faz o
    paciente A aparecer com os dados do paciente B."""
    uid = administrador['id']
    dados_a, a = _criar(admin)
    dados_b, b = _criar(admin)
    with contas._conexao() as executar:
        cifrados = dict(executar('SELECT id, dados FROM pacientes WHERE id IN (?, ?)', (a['id'], b['id'])).fetchall())
        executar('UPDATE pacientes SET dados = ? WHERE id = ?', (cifrados[b['id']], a['id']))
        executar('UPDATE pacientes SET dados = ? WHERE id = ?', (cifrados[a['id']], b['id']))
    try:
        for pid in (a['id'], b['id']):
            r = admin.get(f'/api/pacientes/{pid}')
            assert r.status_code == 500 and r.get_json()['codigo'] == 'ilegivel'
            assert not any(s in r.get_data(as_text=True) for s in _segredos(dados_a) + _segredos(dados_b))
            assert admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Goiânia'}).status_code == 500
        lista = admin.get('/api/pacientes').get_json()
        assert lista['ilegiveis'] >= 2 and not {a['id'], b['id']} & {p['id'] for p in lista['pacientes']}
    finally:
        with contas._conexao() as executar:
            for pid, cifrado in cifrados.items():
                executar('UPDATE pacientes SET dados = ? WHERE id = ?', (cifrado, pid))
    assert pacientes.ler(uid, a['id'])['nome'] == dados_a['nome'] and pacientes.ler(uid, b['id'])['nome'] == dados_b['nome']
    # Depois de editar, o registro continua preso ao próprio número.
    assert admin.post(f"/api/pacientes/{a['id']}", json={'municipio': 'Nerópolis'}).status_code == 200
    assert pacientes.ler(uid, a['id'])['municipio'] == 'Nerópolis'


def test_documentacao_registra_os_achados_da_revisao():
    doc = (RAIZ / 'docs' / 'pacientes.md').read_text(encoding='utf-8')
    plano = ' '.join(doc.split())
    assert '`SECRET_KEY` lê tudo' not in plano
    for trecho in ('`PACIENTES_CHAVE`', 'separada da chave de sessão', 'menos de 32 caracteres', 'nunca usa a `SECRET_KEY`',
                   'Perder a chave', 'ilegíveis para sempre', 'gerador de senhas', 'só pode ser usada com dados fictícios',
                   'desde o primeiro paciente real', 'base legal', 'encarregado', 'retenção',
                   '`X-Requested-With: evidens`', 'FOR UPDATE', '"conflito"', '"limite"', '5.000',
                   '`__proto__`', '`constructor`', '`prototype`', '`textContent`', 'innerHTML'):
        assert trecho in plano, trecho
    assert '?busca=' not in doc.split('## API')[1].split('## Trilha')[0].split('Erros (')[0].replace('`GET /api/pacientes?busca=…` não existe', '')
    for arquivo in ('README.md', 'docs/deploy.md', '.env.example', 'CHANGELOG.md', 'docs/registro-de-perigos.md'):
        assert 'PACIENTES_CHAVE' in (RAIZ / arquivo).read_text(encoding='utf-8'), arquivo
    # Fase 1: os Termos e a home não mudam.
    assert 'PACIENTES_CHAVE' not in (RAIZ / 'termos.html').read_text(encoding='utf-8')


# --- Versão do registro na edição (formulário aberto há tempo) -------------

def test_edicao_com_versao_antiga_responde_409_e_nao_sobrescreve(admin, administrador, contas):
    """A tela envia o `atualizado_em` que leu ao abrir o formulário; se o registro mudou depois, nada é gravado."""
    uid = administrador['id']
    _, criado = _criar(admin)
    pid, versao = criado['id'], criado['atualizado_em']
    # outra aba (ou o check-up) altera o registro enquanto o formulário está aberto
    outra = admin.post(f'/api/pacientes/{pid}', json={'telefone': '(62) 92222-2222'})
    assert outra.status_code == 200 and outra.get_json()['paciente']['atualizado_em'] > versao
    antes = _contagens(contas)
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis', 'telefone': '', 'atualizado_em': versao})
    assert r.status_code == 409 and r.get_json()['codigo'] == 'conflito' and 'paciente' not in r.get_json()
    assert 'Fict' not in r.get_data(as_text=True) and _contagens(contas) == antes        # nem gravação, nem trilha
    atual = pacientes.ler(uid, pid)
    assert atual['telefone'] == '(62) 92222-2222' and atual['municipio'] == 'Goiânia'
    # com a versão atual a edição entra, e a versão avança
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Anápolis', 'atualizado_em': atual['atualizado_em']})
    assert r.status_code == 200 and r.get_json()['paciente']['municipio'] == 'Anápolis'
    assert r.get_json()['paciente']['atualizado_em'] > atual['atualizado_em']
    assert 'atualizado_em' not in pacientes.CAMPOS                 # é versão do registro, não campo do paciente


def test_cada_edicao_avanca_a_versao_mesmo_no_mesmo_segundo(admin, administrador, monkeypatch):
    """`atualizado_em` é em segundos: duas edições no mesmo segundo não podem ficar com a mesma versão."""
    _, criado = _criar(admin)
    pid = criado['id']
    monkeypatch.setattr(pacientes.time, 'time', lambda: criado['atualizado_em'])       # o relógio não anda
    primeira = pacientes.atualizar(administrador['id'], pid, {'municipio': 'Trindade'})
    segunda = pacientes.atualizar(administrador['id'], pid, {'municipio': 'Inhumas'})
    assert criado['atualizado_em'] < primeira['atualizado_em'] < segunda['atualizado_em']
    r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Goianira', 'atualizado_em': primeira['atualizado_em']})
    assert r.status_code == 409 and r.get_json()['codigo'] == 'conflito'


def test_edicao_sem_versao_continua_valendo_e_versao_invalida_e_400(admin):
    _, criado = _criar(admin)
    pid = criado['id']
    assert admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Trindade'}).status_code == 200
    for invalida in ('ontem', 1.5, True, [1]):
        r = admin.post(f'/api/pacientes/{pid}', json={'municipio': 'Inhumas', 'atualizado_em': invalida})
        assert r.status_code == 400, invalida
    # na criação não existe versão: a chave é recusada como qualquer campo desconhecido
    assert admin.post('/api/pacientes', json={'nome': 'Outra Pessoa Fictícia', 'atualizado_em': 1}).status_code == 400


def test_hoje_do_cadastro_usa_o_fuso_do_resto_do_sistema(monkeypatch):
    from datetime import datetime, timezone
    from src.utils import uso
    assert pacientes.FUSO is uso.FUSO

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 3, 10, 1, 30, tzinfo=timezone.utc).astimezone(tz)      # 22h30 do dia 9 em Brasília
    monkeypatch.setattr(pacientes, 'datetime', Relogio)
    assert pacientes._hoje().isoformat() == '2026-03-09'
