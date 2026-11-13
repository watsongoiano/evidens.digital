"""Aviso por e-mail ao administrador quando alguém pede abertura de conta.

Usa a API HTTP da Resend (https://resend.com), que funciona em ambiente serverless
sem dependência extra. Configuração por variáveis de ambiente:

- ``RESEND_API_KEY``      chave da Resend. Sem ela o aviso fica desligado (nada é enviado).
- ``AVISO_CADASTRO_PARA`` destinatários, separados por vírgula. Padrão: e-mail dos administradores.
- ``AVISO_CADASTRO_DE``   remetente. Padrão: ``Evidēns <onboarding@resend.dev>``, que a Resend só
                          entrega ao e-mail do dono da conta Resend; para outros destinatários,
                          verifique um domínio na Resend e use um remetente dele.

O envio nunca derruba o cadastro: qualquer falha vira uma linha de log, sem a chave.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

URL_RESEND = 'https://api.resend.com/emails'
REMETENTE_PADRAO = 'Evidēns <onboarding@resend.dev>'
PERFIS = {'medico': 'Médico(a)', 'residente': 'Residente', 'estudante': 'Estudante de medicina'}
TEMPO_LIMITE = 4  # segundos


def configurado() -> bool:
    return bool((os.environ.get('RESEND_API_KEY') or '').strip())


def destinatarios(administradores=()):
    """Lista de e-mails que recebem o aviso (variável de ambiente ou administradores aprovados)."""
    fixos = [e.strip() for e in (os.environ.get('AVISO_CADASTRO_PARA') or '').split(',') if e.strip()]
    return fixos or [u['email'] for u in administradores if u.get('administrador') and u.get('situacao') == 'aprovado']


def _sem_quebra(texto, maximo=200):
    """Dado digitado por quem se cadastra: uma linha só, tamanho limitado."""
    return ' '.join(str(texto or '').split())[:maximo]


def mensagem_de_cadastro(usuario, url_admin):
    nome = _sem_quebra(usuario.get('nome'))
    corpo = '\n'.join([
        'Há um novo pedido de abertura de conta no Evidēns.',
        '',
        f'Nome: {nome}',
        f"Perfil: {PERFIS.get(usuario.get('perfil'), _sem_quebra(usuario.get('perfil')))}",
        f"Registro: {_sem_quebra(usuario.get('registro'))}",
        f"E-mail: {_sem_quebra(usuario.get('email'))}",
        '',
        f'Confira o registro profissional e aprove ou recuse em: {url_admin}',
    ])
    return f'Evidēns: novo pedido de conta ({nome})', corpo


def enviar(para, assunto, texto):
    """Envia pela Resend. Devolve ``(ok, detalhe)``; nunca levanta exceção."""
    chave = (os.environ.get('RESEND_API_KEY') or '').strip()
    if not chave:
        return False, 'RESEND_API_KEY não configurada.'
    if not para:
        return False, 'Nenhum destinatário (defina AVISO_CADASTRO_PARA ou crie o administrador).'
    corpo = json.dumps({
        'from': (os.environ.get('AVISO_CADASTRO_DE') or '').strip() or REMETENTE_PADRAO,
        'to': list(para), 'subject': assunto, 'text': texto,
    }).encode('utf-8')
    pedido = urllib.request.Request(URL_RESEND, data=corpo, method='POST', headers={
        'Authorization': f'Bearer {chave}', 'Content-Type': 'application/json',
        'User-Agent': 'evidens-digital/1.0',  # a Resend recusa o agente padrão do urllib
    })
    try:
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
            return 200 <= resposta.status < 300, f'HTTP {resposta.status}'
    except urllib.error.HTTPError as erro:
        try:
            detalhe = json.loads(erro.read().decode('utf-8', 'replace')).get('message', '')
        except Exception:
            detalhe = ''
        return False, f'HTTP {erro.code} {detalhe}'.strip()[:300]
    except Exception as erro:  # rede, tempo esgotado
        return False, type(erro).__name__


def avisar_novo_cadastro(usuario, administradores, url_admin):
    """Avisa os administradores. Falha vira log; o cadastro segue."""
    if not configurado():
        return False
    assunto, texto = mensagem_de_cadastro(usuario, url_admin)
    ok, detalhe = enviar(destinatarios(administradores), assunto, texto)
    if not ok:
        print(f'⚠️ Aviso de novo cadastro não enviado: {detalhe}')
    return ok
