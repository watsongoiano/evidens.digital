"""E-mails do cadastro: aviso ao administrador e boas-vindas a quem pediu a conta.

Usa a API HTTP da Resend (https://resend.com), que funciona em ambiente serverless
sem dependência extra. Configuração por variáveis de ambiente:

- ``RESEND_API_KEY``      chave da Resend. Sem ela o aviso fica desligado (nada é enviado).
- ``AVISO_CADASTRO_PARA`` destinatários, separados por vírgula. Padrão: e-mail dos administradores.
- ``AVISO_CADASTRO_DE``   remetente. Padrão: ``Evidēns <onboarding@resend.dev>``, que a Resend só
                          entrega ao e-mail do dono da conta Resend; para outros destinatários,
                          verifique um domínio na Resend e use um remetente dele.

- ``EMAIL_CONTATO``       opcional: e-mail de contato mostrado nas boas-vindas e usado como resposta (reply-to).

Boas-vindas: enviadas a quem acabou de pedir a conta, só quando ``AVISO_CADASTRO_DE`` aponta um
remetente de domínio verificado (o remetente padrão da Resend não entrega a terceiros).

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
LIMITE_POR_HORA = 10  # avisos individuais por hora; acima disso sai um único aviso de volume


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


def remetente_proprio() -> str:
    """Remetente de domínio verificado, se configurado; vazio enquanto vale o padrão da Resend."""
    return (os.environ.get('AVISO_CADASTRO_DE') or '').strip()


def boas_vindas_ligadas() -> bool:
    return configurado() and bool(remetente_proprio())


def email_de_contato() -> str:
    """Endereço mostrado no e-mail de boas-vindas e usado como resposta (reply-to), se configurado."""
    return _sem_quebra(os.environ.get('EMAIL_CONTATO'))


def _primeiro_nome(usuario):
    return (_sem_quebra(usuario.get('nome')).split(' ') or [''])[0]


def _apresentacao():
    # Números do artigo (Zhi M et al., PLOS ONE 2013, metanálise de 15 anos): 20,6% de excesso e
    # 44,8% de subutilização. A matéria de Harvard arredonda os dois para "cerca de 30%".
    return ('você sabia que cerca de 21% dos exames laboratoriais pedidos são desnecessários, e que cerca de 45% '
            'dos exames indicados deixam de ser pedidos? Foi o que mostrou uma metanálise de 15 anos de literatura, '
            'feita por pesquisadores ligados à Harvard Medical School (Zhi et al., PLOS ONE, 2013; resumo em '
            'https://hms.harvard.edu/news/unnecessary-testing). '
            'O Evidēns nasceu para ajudar nos dois lados: é uma ferramenta de apoio ao check-up baseada em evidências '
            'científicas, que indica o que pedir, para quem e com qual referência.')


def _fecho(url_site):
    contato = email_de_contato()
    return [
        'Lembre-se: o Evidēns está em fase de desenvolvimento e as recomendações são sugestões para a avaliação '
        'médica. Sempre revise e individualize cada item antes de solicitar ou prescrever, e desconfie do que '
        'parecer estranho!',
        '',
        'Ficamos felizes com qualquer feedback: um erro encontrado, uma referência desatualizada, uma ideia de '
        f'melhoria. É só escrever pela página de contato: {url_site}/contact'
        + (f' ou pelo e-mail {contato}' if contato else ''),
        '',
        'Muito obrigado por testar!',
        '',
        'Dr. Rodolfo Cambraia Frota · CRM-GO 26815',
        'Criador e responsável técnico · Evidēns',
    ]


def mensagem_de_boas_vindas(usuario, url_site):
    """Texto de boas-vindas: por que a ferramenta existe, o que acontece agora, fase de desenvolvimento
    e convite a dar feedback."""
    primeiro_nome = _primeiro_nome(usuario)
    corpo = '\n'.join([
        f'Olá, {primeiro_nome}.' if primeiro_nome else 'Olá.',
        '',
        'Ficamos felizes com o seu pedido de conta no Evidēns!',
        '',
        'Uma breve apresentação: ' + _apresentacao(),
        '',
        'O seu pedido já foi enviado para a nossa equipe conferir o cadastro e liberar o acesso. É só aguardar: '
        f'assim que a conta for aprovada, entre em {url_site}/login com o e-mail e a senha que você cadastrou!',
        '',
    ] + _fecho(url_site))
    return 'Bem-vindo(a) ao Evidēns', corpo


def mensagem_de_agradecimento(usuario, url_site):
    """Agradecimento a quem criou a conta antes de existir o e-mail de boas-vindas. O parágrafo do acesso
    muda conforme a conta já esteja aprovada ou ainda em conferência."""
    primeiro_nome = _primeiro_nome(usuario)
    if usuario.get('situacao') == 'aprovado':
        acesso = (f'A sua conta já está liberada: é só entrar em {url_site}/login com o e-mail e a senha que '
                  'você cadastrou!')
    else:
        acesso = ('O seu cadastro está em conferência pela nossa equipe. Assim que a conta for aprovada, entre em '
                  f'{url_site}/login com o e-mail e a senha que você cadastrou!')
    corpo = '\n'.join([
        f'Olá, {primeiro_nome}.' if primeiro_nome else 'Olá.',
        '',
        'Muito obrigado por já ter criado a sua conta no Evidēns! Você está entre os primeiros a testar a '
        'plataforma, e isso faz diferença para nós.',
        '',
        'Para quem ainda não conhece a nossa motivação: ' + _apresentacao(),
        '',
        acesso,
        '',
    ] + _fecho(url_site))
    return 'Obrigado por testar o Evidēns', corpo


def enviar(para, assunto, texto, responder_para=None):
    """Envia pela Resend. Devolve ``(ok, detalhe)``; nunca levanta exceção."""
    chave = (os.environ.get('RESEND_API_KEY') or '').strip()
    if not chave:
        return False, 'RESEND_API_KEY não configurada.'
    if not para:
        return False, 'Nenhum destinatário (defina AVISO_CADASTRO_PARA ou crie o administrador).'
    corpo = json.dumps({
        'from': (os.environ.get('AVISO_CADASTRO_DE') or '').strip() or REMETENTE_PADRAO,
        'to': list(para), 'subject': assunto, 'text': texto,
        **({'reply_to': responder_para} if responder_para else {}),
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


def avisar_novo_cadastro(usuario, administradores, url_admin, pedidos_na_ultima_hora=1):
    """Avisa os administradores. Falha vira log; o cadastro segue.

    O cadastro é aberto a qualquer pessoa, então o número de e-mails é limitado: até
    ``LIMITE_POR_HORA`` avisos individuais por hora; o pedido seguinte gera um único aviso de
    volume e os demais daquela hora não geram e-mail (continuam aparecendo em /admin).
    """
    if not configurado():
        return False
    if pedidos_na_ultima_hora > LIMITE_POR_HORA + 1:
        return False
    if pedidos_na_ultima_hora == LIMITE_POR_HORA + 1:
        assunto = 'Evidēns: muitos pedidos de conta na última hora'
        texto = (f'Mais de {LIMITE_POR_HORA} pedidos de abertura de conta chegaram na última hora. '
                 'Os avisos individuais ficam suspensos até o volume baixar, para não lotar a sua caixa.\n\n'
                 f'Confira os pedidos em: {url_admin}')
    else:
        assunto, texto = mensagem_de_cadastro(usuario, url_admin)
    ok, detalhe = enviar(destinatarios(administradores), assunto, texto)
    if not ok:
        print(f'⚠️ Aviso de novo cadastro não enviado: {detalhe}')
    return ok


def boas_vindas_cabem(pedidos_na_ultima_hora=1) -> bool:
    """Boas-vindas ligadas e dentro do limite por hora (o mesmo do aviso ao administrador)."""
    return boas_vindas_ligadas() and pedidos_na_ultima_hora <= LIMITE_POR_HORA


def enviar_boas_vindas(usuario, url_site, pedidos_na_ultima_hora=1):
    """Boas-vindas a quem pediu a conta. Mesmo limite por hora do aviso; falha vira log."""
    if not boas_vindas_cabem(pedidos_na_ultima_hora):
        return False
    assunto, texto = mensagem_de_boas_vindas(usuario, url_site)
    ok, detalhe = enviar([usuario['email']], assunto, texto,
                         responder_para=email_de_contato() or None)
    if not ok:
        print(f'⚠️ E-mail de boas-vindas não enviado: {detalhe}')
    return ok


def enviar_agradecimento(usuario, url_site):
    """Agradecimento a uma conta que já existia. Devolve ``(ok, detalhe)``."""
    if not boas_vindas_ligadas():
        return False, 'envio a terceiros desligado (falta RESEND_API_KEY ou AVISO_CADASTRO_DE)'
    assunto, texto = mensagem_de_agradecimento(usuario, url_site)
    return enviar([usuario['email']], assunto, texto, responder_para=email_de_contato() or None)
