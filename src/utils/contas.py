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
        executar(
            'INSERT INTO usuarios (email, nome, registro, perfil, senha_hash, situacao, administrador, criado_em, decidido_em) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (email, nome, registro, perfil, generate_password_hash(senha),
             'aprovado' if administrador else 'pendente', 1 if administrador else 0,
             agora, agora if administrador else None))
        return _usuario(executar(_SELECT + 'WHERE email = ?', (email,)).fetchone())


def por_id(uid):
    with _conexao() as executar:
        return _usuario(executar(_SELECT + 'WHERE id = ?', (uid,)).fetchone())


def existe_administrador():
    with _conexao() as executar:
        return executar('SELECT 1 FROM usuarios WHERE administrador = 1 LIMIT 1').fetchone() is not None


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
