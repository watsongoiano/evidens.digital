"""Contas de usuário: armazenamento e regras.

Guarda só o que a área de acesso precisa: nome, e-mail, registro profissional
(CRM ou matrícula), perfil, senha (como hash) e situação da conta. Dados de
pacientes continuam não sendo gravados em lugar nenhum.

Banco: Postgres em produção (variável DATABASE_URL ou POSTGRES_URL, entregue
pela integração Neon da Vercel). Nos testes e na execução local, um arquivo
SQLite (DATABASE_URL=sqlite:///caminho). As consultas usam "?" como marcador e
são convertidas para o Postgres.
"""
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

from werkzeug.security import check_password_hash, generate_password_hash

PERFIS = ('medico', 'residente', 'estudante')
SITUACOES = ('pendente', 'aprovado', 'bloqueado')

SENHA_MINIMA = 10
SENHA_MAXIMA = 200
JANELA_TENTATIVAS = 15 * 60          # segundos
MAX_FALHAS_POR_EMAIL = 5
MAX_FALHAS_POR_IP = 30

_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Hash de uma senha qualquer, para gastar o mesmo tempo quando o e-mail não
# existe (não dá para descobrir quem tem conta medindo a demora da resposta).
_HASH_DE_FACHADA = generate_password_hash(secrets.token_urlsafe(16))


class ContasIndisponiveis(Exception):
    """Não há banco de dados configurado."""


class DadosInvalidos(Exception):
    def __init__(self, erros):
        super().__init__('; '.join(erros))
        self.erros = erros


def _url():
    return os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or ''


def configurado():
    return bool(_url())


def _eh_sqlite(url):
    return url.startswith('sqlite:')


_ESQUEMA_PRONTO = set()

_ESQUEMA = [
    """CREATE TABLE IF NOT EXISTS usuarios (
        id {pk},
        email TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        registro TEXT NOT NULL,
        perfil TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        situacao TEXT NOT NULL DEFAULT 'pendente',
        administrador INTEGER NOT NULL DEFAULT 0,
        versao_sessao INTEGER NOT NULL DEFAULT 1,
        criado_em BIGINT NOT NULL,
        decidido_em BIGINT
    )""",
    """CREATE TABLE IF NOT EXISTS tentativas_login (
        id {pk},
        email TEXT NOT NULL,
        ip TEXT NOT NULL,
        quando BIGINT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS tentativas_login_quando ON tentativas_login (quando)",
    # Primeiro e-mail de cada conta: boas-vindas OU agradecimento, nunca os dois. A unicidade é por
    # conta, então a reserva vale para os dois caminhos de envio ao mesmo tempo.
    """CREATE TABLE IF NOT EXISTS emails_enviados (
        id {pk},
        usuario_id BIGINT NOT NULL UNIQUE,
        tipo TEXT NOT NULL,
        quando BIGINT NOT NULL
    )""",
    # No máximo um administrador: a regra fica no banco, para que duas instalações
    # simultâneas com o código certo não criem duas contas privilegiadas.
    "CREATE UNIQUE INDEX IF NOT EXISTS um_so_administrador ON usuarios (administrador) WHERE administrador = 1",
    # Credenciamento do médico em cada plano de saúde (dados que vão na guia SP/SADT).
    # Nenhuma senha de operadora é guardada aqui.
    """CREATE TABLE IF NOT EXISTS credenciamentos (
        id {pk},
        usuario_id BIGINT NOT NULL,
        operadora TEXT NOT NULL,
        registro_ans TEXT NOT NULL DEFAULT '',
        codigo_prestador TEXT NOT NULL,
        nome_contratado TEXT NOT NULL,
        cbo TEXT NOT NULL DEFAULT '',
        criado_em BIGINT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS credenciamentos_usuario ON credenciamentos (usuario_id)",
]


@contextmanager
def _conexao():
    url = _url()
    if not url:
        raise ContasIndisponiveis()
    if _eh_sqlite(url):
        con = sqlite3.connect(url.split('sqlite:///', 1)[1])
        marcador, pk = '?', 'INTEGER PRIMARY KEY AUTOINCREMENT'
    else:
        import psycopg  # só é necessário em produção
        con = psycopg.connect(url, connect_timeout=10)
        marcador, pk = '%s', 'BIGSERIAL PRIMARY KEY'

    def executar(sql, params=()):
        cur = con.cursor()
        cur.execute(sql.replace('?', marcador), tuple(params))
        return cur

    try:
        if url not in _ESQUEMA_PRONTO:
            for comando in _ESQUEMA:
                executar(comando.format(pk=pk))
            con.commit()
            _ESQUEMA_PRONTO.add(url)
        yield executar
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


_COLUNAS = ('id', 'email', 'nome', 'registro', 'perfil', 'senha_hash', 'situacao',
            'administrador', 'versao_sessao', 'criado_em', 'decidido_em')
_SELECT = 'SELECT ' + ', '.join(_COLUNAS) + ' FROM usuarios '


def _usuario(linha):
    if linha is None:
        return None
    u = dict(zip(_COLUNAS, linha))
    u['administrador'] = bool(u['administrador'])
    return u


def publico(u):
    """O que pode sair para o navegador (nunca o hash da senha)."""
    return {k: u[k] for k in ('id', 'email', 'nome', 'registro', 'perfil', 'situacao',
                              'administrador', 'criado_em', 'decidido_em')}


def normalizar_email(email):
    return (email or '').strip().lower()


def validar_senha(senha):
    if not isinstance(senha, str) or len(senha) < SENHA_MINIMA:
        return f'A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.'
    if len(senha) > SENHA_MAXIMA:
        return f'A senha pode ter no máximo {SENHA_MAXIMA} caracteres.'
    return None


UFS = ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR',
       'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO')


def montar_registro(perfil, registro='', crm_uf='', crm_numero=''):
    """Registro gravado: 'CRM-UF número' para médico e residente; matrícula e faculdade para estudante.

    O CRM chega em dois campos (lista de UF + número). Um registro já no formato
    'CRM-GO 12345' também é aceito, para quem envia o campo único.
    """
    registro, uf, numero = (registro or '').strip(), (crm_uf or '').strip().upper(), (crm_numero or '').strip()
    if perfil == 'estudante':
        return registro
    if not uf and not numero:
        m = re.match(r'^CRM[-\s/]*([A-Za-z]{2})[-\s/]*([\d.]{1,9})$', registro, re.I)
        if m:
            uf, numero = m.group(1).upper(), m.group(2)
    numero = numero.replace('.', '').lstrip('0')
    erros = []
    if uf not in UFS:
        erros.append('Escolha o estado (UF) do CRM.')
    if not re.fullmatch(r'\d{1,7}', numero or ''):
        erros.append('Informe o número do CRM, só com algarismos.')
    if erros:
        raise DadosInvalidos(erros)
    return f'CRM-{uf} {numero}'


def crm_de(usuario):
    """'CRM-GO 12345' se o registro do usuário é um CRM; senão None (estudante)."""
    r = ((usuario or {}).get('registro') or '').strip()
    # contas antigas gravaram o CRM em texto livre ('CRM GO 26.815', 'crm/go 26815')
    m = re.match(r'^CRM[-\s/]*([A-Za-z]{2})[-\s/]*([\d.]{1,9})$', r, re.I)
    if not m or m.group(1).upper() not in UFS:
        return None
    return f"CRM-{m.group(1).upper()} {m.group(2).replace('.', '')}"


def _validar_cadastro(email, nome, registro, perfil, senha):
    erros = []
    if not _EMAIL.match(email) or len(email) > 254:
        erros.append('Informe um e-mail válido.')
    if not (3 <= len(nome) <= 150):
        erros.append('Informe o nome completo.')
    if not (3 <= len(registro) <= 40):
        erros.append('Informe o CRM com UF ou a matrícula da faculdade.')
    if perfil not in PERFIS:
        erros.append('Escolha o perfil: médico, residente ou estudante.')
    erro_senha = validar_senha(senha)
    if erro_senha:
        erros.append(erro_senha)
    if erros:
        raise DadosInvalidos(erros)


def criar(email, nome, registro, perfil, senha, administrador=False):
    """Cria a conta. Administrador já nasce aprovado; os demais ficam pendentes.

    Devolve o usuário, ou None se o e-mail já tinha conta (quem chama responde
    do mesmo jeito nos dois casos, para não revelar quem está cadastrado).
    """
    email = normalizar_email(email)
    nome = (nome or '').strip()
    registro = (registro or '').strip()
    _validar_cadastro(email, nome, registro, perfil, senha)
    agora = int(time.time())
    with _conexao() as executar:
        if executar(_SELECT + 'WHERE email = ?', (email,)).fetchone():
            return None
        try:
            executar(
                'INSERT INTO usuarios (email, nome, registro, perfil, senha_hash, situacao, administrador, criado_em, decidido_em) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (email, nome, registro, perfil, generate_password_hash(senha),
                 'aprovado' if administrador else 'pendente', 1 if administrador else 0,
                 agora, agora if administrador else None))
        except Exception as erro:
            # Outra requisição criou o mesmo e-mail (ou o administrador) no intervalo.
            if 'unique' in str(erro).lower() or 'IntegrityError' in type(erro).__name__ or 'UniqueViolation' in type(erro).__name__:
                return None
            raise
        return _usuario(executar(_SELECT + 'WHERE email = ?', (email,)).fetchone())


def por_id(uid):
    with _conexao() as executar:
        return _usuario(executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone())


def existe_administrador():
    with _conexao() as executar:
        return executar('SELECT 1 FROM usuarios WHERE administrador = 1 LIMIT 1').fetchone() is not None


def criados_desde(instante):
    """Quantas contas foram criadas a partir de ``instante`` (segundos desde a época)."""
    with _conexao() as executar:
        return executar('SELECT COUNT(*) FROM usuarios WHERE criado_em >= ?', (int(instante),)).fetchone()[0]


def reservar_email(uid, tipo):
    """Reserva a conta para o e-mail ``tipo`` antes de enviar. False se a conta já tinha reserva
    (de boas-vindas ou de agradecimento): quem perde a disputa não envia."""
    with _conexao() as executar:
        cur = executar('INSERT INTO emails_enviados (usuario_id, tipo, quando) VALUES (?, ?, ?) '
                       'ON CONFLICT (usuario_id) DO NOTHING', (int(uid), tipo, int(time.time())))
        return cur.rowcount == 1


def liberar_email(uid, tipo):
    """Desfaz a marca quando o envio falhou, para a conta voltar à fila."""
    with _conexao() as executar:
        executar('DELETE FROM emails_enviados WHERE usuario_id = ? AND tipo = ?', (int(uid), tipo))


def sem_email(limite=None):
    """Contas (fora o administrador e as bloqueadas) que ainda não receberam nenhum e-mail nosso,
    da mais antiga para a mais nova."""
    with _conexao() as executar:
        linhas = executar(_SELECT + "WHERE administrador = 0 AND situacao <> 'bloqueado' "
                          'AND id NOT IN (SELECT usuario_id FROM emails_enviados) ORDER BY criado_em, id').fetchall()
    usuarios = [_usuario(l) for l in linhas]
    return usuarios if limite is None else usuarios[:limite]


def listar():
    with _conexao() as executar:
        linhas = executar(_SELECT + 'ORDER BY criado_em DESC').fetchall()
    return [_usuario(l) for l in linhas]


def bloqueado_por_tentativas(email, ip):
    desde = int(time.time()) - JANELA_TENTATIVAS
    with _conexao() as executar:
        executar('DELETE FROM tentativas_login WHERE quando < ?', (desde,))
        por_email = executar('SELECT COUNT(*) FROM tentativas_login WHERE email = ? AND quando >= ?', (email, desde)).fetchone()[0]
        por_ip = executar('SELECT COUNT(*) FROM tentativas_login WHERE ip = ? AND quando >= ?', (ip, desde)).fetchone()[0]
    return por_email >= MAX_FALHAS_POR_EMAIL or por_ip >= MAX_FALHAS_POR_IP


def autenticar(email, senha, ip):
    """Devolve o usuário se e-mail e senha conferem; senão None (e registra a falha)."""
    email = normalizar_email(email)
    senha = senha if isinstance(senha, str) else ''
    with _conexao() as executar:
        u = _usuario(executar(_SELECT + 'WHERE email = ?', (email,)).fetchone())
        confere = check_password_hash(u['senha_hash'] if u else _HASH_DE_FACHADA, senha[:SENHA_MAXIMA])
        if u and confere:
            executar('DELETE FROM tentativas_login WHERE email = ?', (email,))
            return u
        executar('INSERT INTO tentativas_login (email, ip, quando) VALUES (?, ?, ?)', (email[:254], ip[:64], int(time.time())))
        return None


def definir_situacao(uid, situacao):
    assert situacao in SITUACOES
    with _conexao() as executar:
        # Mudar a situação encerra as sessões abertas do usuário.
        executar('UPDATE usuarios SET situacao = ?, decidido_em = ?, versao_sessao = versao_sessao + 1 WHERE id = ? AND administrador = 0',
                 (situacao, int(time.time()), uid))
        return _usuario(executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone())


def aprovar(uid):
    """Aprova (ou reativa) a conta e encerra as sessões abertas, como ``definir_situacao``.

    Devolve ``(usuario, anterior)``: ``anterior`` é a situação que a conta tinha ('pendente' ou
    'bloqueado'), ou None se ela já estava aprovada. A troca é condicional no banco, então dois
    pedidos simultâneos não avisam a pessoa duas vezes.
    """
    agora = int(time.time())
    with _conexao() as executar:
        linha = executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone()
        anterior = _usuario(linha)['situacao'] if linha else None
        mudou = executar("UPDATE usuarios SET situacao = 'aprovado', decidido_em = ?, versao_sessao = versao_sessao + 1 "
                         "WHERE id = ? AND administrador = 0 AND situacao <> 'aprovado'", (agora, uid)).rowcount == 1
        if not mudou:
            executar("UPDATE usuarios SET situacao = 'aprovado', decidido_em = ?, versao_sessao = versao_sessao + 1 "
                     'WHERE id = ? AND administrador = 0', (agora, uid))
        return _usuario(executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone()), (anterior if mudou else None)


def trocar_senha(uid, nova_senha):
    erro = validar_senha(nova_senha)
    if erro:
        raise DadosInvalidos([erro])
    with _conexao() as executar:
        executar('UPDATE usuarios SET senha_hash = ?, versao_sessao = versao_sessao + 1 WHERE id = ?',
                 (generate_password_hash(nova_senha), uid))
        return _usuario(executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone())


def senha_confere(u, senha):
    return isinstance(senha, str) and check_password_hash(u['senha_hash'], senha[:SENHA_MAXIMA])


def gerar_senha_temporaria(uid):
    """Troca a senha do usuário por uma temporária e a devolve (é mostrada uma única vez)."""
    temporaria = secrets.token_urlsafe(12)
    u = trocar_senha(uid, temporaria)
    return (u, temporaria) if u else (None, None)


# ── Credenciamentos em planos de saúde ──────────────────────────────────────

MAX_CREDENCIAMENTOS = 20
_COLUNAS_CRED = ('id', 'operadora', 'registro_ans', 'codigo_prestador', 'nome_contratado', 'cbo', 'criado_em')
_SELECT_CRED = 'SELECT ' + ', '.join(_COLUNAS_CRED) + ' FROM credenciamentos '


def pode_ter_credenciamento(usuario):
    """Só quem assina pedidos (médico e residente) é credenciado em plano de saúde."""
    return bool(usuario) and usuario.get('perfil') in ('medico', 'residente')


def _limpo(valor, maximo):
    s = valor if isinstance(valor, str) else ''
    s = ' '.join(''.join(c if c.isprintable() else ' ' for c in s).split())
    return s[:maximo]


def validar_credenciamento(dados):
    """Devolve os campos normalizados ou levanta `DadosInvalidos` com a lista do que corrigir."""
    dados = dados if isinstance(dados, dict) else {}
    operadora = _limpo(dados.get('operadora'), 80)
    registro_ans = re.sub(r'\D', '', _limpo(dados.get('registro_ans'), 20))
    codigo = _limpo(dados.get('codigo_prestador'), 20)
    contratado = _limpo(dados.get('nome_contratado'), 120)
    cbo = re.sub(r'\D', '', _limpo(dados.get('cbo'), 20))
    erros = []
    if len(operadora) < 2:
        erros.append('Informe o nome do plano de saúde.')
    if registro_ans and len(registro_ans) != 6:
        erros.append('O registro ANS da operadora tem 6 dígitos.')
    if not codigo:
        erros.append('Informe o seu código na operadora (ou o CPF/CNPJ do contrato).')
    if len(contratado) < 2:
        erros.append('Informe o nome do contratado (clínica ou o seu nome, como está no contrato).')
    if cbo and len(cbo) != 6:
        erros.append('O código CBO tem 6 dígitos.')
    if erros:
        raise DadosInvalidos(erros)
    return {'operadora': operadora, 'registro_ans': registro_ans, 'codigo_prestador': codigo,
            'nome_contratado': contratado, 'cbo': cbo}


def _credenciamento(linha):
    return dict(zip(_COLUNAS_CRED, linha)) if linha else None


def credenciamentos_de(uid):
    with _conexao() as executar:
        linhas = executar(_SELECT_CRED + 'WHERE usuario_id = ? ORDER BY operadora, id', (uid,)).fetchall()
    return [_credenciamento(linha) for linha in linhas]


def credenciamento_de(uid, cid):
    """O credenciamento `cid`, só se for do usuário `uid`."""
    with _conexao() as executar:
        return _credenciamento(executar(_SELECT_CRED + 'WHERE id = ? AND usuario_id = ?', (cid, uid)).fetchone())


def criar_credenciamento(uid, dados):
    campos = validar_credenciamento(dados)
    with _conexao() as executar:
        total = executar('SELECT COUNT(*) FROM credenciamentos WHERE usuario_id = ?', (uid,)).fetchone()[0]
        if total >= MAX_CREDENCIAMENTOS:
            raise DadosInvalidos([f'O limite é de {MAX_CREDENCIAMENTOS} planos por conta.'])
        executar('INSERT INTO credenciamentos (usuario_id, operadora, registro_ans, codigo_prestador, nome_contratado, cbo, criado_em) '
                 'VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (uid, campos['operadora'], campos['registro_ans'], campos['codigo_prestador'],
                  campos['nome_contratado'], campos['cbo'], int(time.time())))
        linha = executar(_SELECT_CRED + 'WHERE usuario_id = ? ORDER BY id DESC', (uid,)).fetchone()
    return _credenciamento(linha)


def excluir_credenciamento(uid, cid):
    with _conexao() as executar:
        return executar('DELETE FROM credenciamentos WHERE id = ? AND usuario_id = ?', (cid, uid)).rowcount > 0
