"""Área de acesso: cadastro com aprovação, login, senha e administração de contas."""
import hmac
import os
import time
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, request, session

from src.utils import contas, notificacoes

auth_bp = Blueprint('auth', __name__)

CHAVE_PADRAO = 'dev-secret-key-change-in-production'
MSG_INDISPONIVEL = 'A área de acesso ainda não está configurada neste ambiente.'
MSG_LOGIN = 'Entre com a sua conta para continuar.'


def disponivel():
    """Há banco e há chave de sessão própria (em produção, nunca a chave padrão)."""
    if not contas.configurado():
        return False
    chave = current_app.config.get('SECRET_KEY')
    return bool(chave) and (chave != CHAVE_PADRAO or current_app.config.get('TESTING'))


def usuario_atual():
    """Usuário da sessão, se a conta continua aprovada e a sessão não foi encerrada."""
    if 'usuario' in g:
        return g.usuario
    g.usuario = None
    uid = session.get('uid')
    if uid is not None and disponivel():
        u = contas.por_id(uid)
        if u and u['situacao'] == 'aprovado' and u['versao_sessao'] == session.get('v'):
            g.usuario = u
        else:
            session.clear()
    return g.usuario


def _abrir_sessao(u):
    session.clear()
    session.permanent = True
    session['uid'] = u['id']
    session['v'] = u['versao_sessao']
    g.usuario = u


def exigir_login(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if not disponivel():
            return jsonify({'error': MSG_INDISPONIVEL}), 503
        if usuario_atual() is None:
            return jsonify({'error': MSG_LOGIN, 'login': '/login'}), 401
        return funcao(*args, **kwargs)
    return protegida


def exigir_administrador(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if not disponivel():
            return jsonify({'error': MSG_INDISPONIVEL}), 503
        u = usuario_atual()
        if u is None:
            return jsonify({'error': MSG_LOGIN, 'login': '/login'}), 401
        if not u['administrador']:
            return jsonify({'error': 'Acesso restrito ao administrador.'}), 403
        return funcao(*args, **kwargs)
    return protegida


def origem_confiavel():
    """Recusa envios vindos de outro site (o cookie de sessão não pode ser usado por terceiros)."""
    origem = request.headers.get('Origin')
    if origem:
        return urlsplit(origem).netloc == request.host
    return request.headers.get('Sec-Fetch-Site', 'same-origin') in ('same-origin', 'none')


def _corpo():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _ip():
    return (request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()) or 'desconhecido'


def _texto(dados, campo):
    valor = dados.get(campo)
    return valor if isinstance(valor, str) else ''


@auth_bp.before_request
def _conferir_ambiente():
    if not disponivel():
        return jsonify({'error': MSG_INDISPONIVEL}), 503


@auth_bp.route('/auth/saude')
def saude():
    """Verifica a conexão com o banco de contas (sem expor dados)."""
    try:
        contas.existe_administrador()
    except Exception:
        return jsonify({'ok': False, 'error': 'Sem conexão com o banco de contas.'}), 503
    return jsonify({'ok': True})


@auth_bp.route('/auth/eu')
def eu():
    u = usuario_atual()
    return jsonify({'usuario': contas.publico(u) if u else None})


@auth_bp.route('/auth/cadastro', methods=['POST'])
def cadastro():
    d = _corpo()
    try:
        perfil = _texto(d, 'perfil')
        registro = contas.montar_registro(perfil, _texto(d, 'registro'), _texto(d, 'crm_uf'), _texto(d, 'crm_numero'))
        novo = contas.criar(_texto(d, 'email'), _texto(d, 'nome'), registro, perfil, _texto(d, 'senha'))
    except contas.DadosInvalidos as e:
        return jsonify({'error': 'Confira os dados informados.', 'erros': e.erros}), 400
    if novo and notificacoes.configurado():
        # E-mails do cadastro (aviso ao administrador e boas-vindas); falha no envio não impede o cadastro.
        try:
            na_ultima_hora = contas.criados_desde(time.time() - 3600)
            notificacoes.avisar_novo_cadastro(novo, contas.listar(), _url_do_site() + '/admin',
                                              pedidos_na_ultima_hora=na_ultima_hora)
            # A reserva vem antes do envio e vale também contra o agradecimento: a conta recebe um ou outro.
            if notificacoes.boas_vindas_cabem(na_ultima_hora) and contas.reservar_email(novo['id'], 'boas_vindas'):
                if not notificacoes.enviar_boas_vindas(novo, _url_do_site(), pedidos_na_ultima_hora=na_ultima_hora):
                    contas.liberar_email(novo['id'], 'boas_vindas')
        except Exception as erro:
            print(f'⚠️ E-mail de cadastro falhou: {type(erro).__name__}')
    # Mesma resposta para e-mail novo e e-mail já cadastrado.
    return jsonify({'ok': True, 'mensagem': 'Cadastro recebido. Você poderá entrar assim que a conta for aprovada.'}), 202


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    d = _corpo()
    email, ip = contas.normalizar_email(_texto(d, 'email')), _ip()
    if contas.bloqueado_por_tentativas(email, ip):
        return jsonify({'error': 'Muitas tentativas. Aguarde 15 minutos e tente de novo.'}), 429
    u = contas.autenticar(email, _texto(d, 'senha'), ip)
    if u is None:
        return jsonify({'error': 'E-mail ou senha incorretos.'}), 401
    if u['situacao'] == 'pendente':
        return jsonify({'error': 'Sua conta ainda aguarda aprovação.'}), 403
    if u['situacao'] != 'aprovado':
        return jsonify({'error': 'Esta conta está bloqueada. Fale com o responsável técnico.'}), 403
    _abrir_sessao(u)
    return jsonify({'ok': True, 'usuario': contas.publico(u)})


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@auth_bp.route('/auth/senha', methods=['POST'])
@exigir_login
def senha():
    d = _corpo()
    u = usuario_atual()
    if not contas.senha_confere(u, _texto(d, 'senha_atual')):
        return jsonify({'error': 'A senha atual não confere.'}), 400
    try:
        u = contas.trocar_senha(u['id'], _texto(d, 'nova_senha'))
    except contas.DadosInvalidos as e:
        return jsonify({'error': e.erros[0], 'erros': e.erros}), 400
    _abrir_sessao(u)  # as outras sessões caem; esta continua
    return jsonify({'ok': True})


@auth_bp.route('/auth/configurar', methods=['POST'])
def configurar():
    """Cria o primeiro administrador. Só funciona com o código de instalação e enquanto não houver administrador."""
    d = _corpo()
    codigo = os.environ.get('SETUP_TOKEN', '')
    if not codigo or not hmac.compare_digest(codigo.encode(), _texto(d, 'codigo').encode()):
        return jsonify({'error': 'Código de instalação inválido.'}), 403
    if contas.existe_administrador():
        return jsonify({'error': 'O administrador já foi criado.'}), 409
    try:
        registro = contas.montar_registro('medico', _texto(d, 'registro'), _texto(d, 'crm_uf'), _texto(d, 'crm_numero'))
        u = contas.criar(_texto(d, 'email'), _texto(d, 'nome'), registro, 'medico', _texto(d, 'senha'), administrador=True)
    except contas.DadosInvalidos as e:
        return jsonify({'error': 'Confira os dados informados.', 'erros': e.erros}), 400
    if u is None:
        return jsonify({'error': 'Já existe uma conta com este e-mail, ou o administrador acabou de ser criado.'}), 409
    _abrir_sessao(u)
    return jsonify({'ok': True, 'usuario': contas.publico(u)}), 201


def _url_do_site():
    # Endereço fixo (não o cabeçalho Host do pedido), para o link do e-mail não poder ser forjado.
    return (os.environ.get('SITE_URL') or '').strip().rstrip('/') or 'https://evidens.life'


def _url_do_admin():
    return _url_do_site() + '/admin'


@auth_bp.route('/admin/aviso')
@exigir_administrador
def admin_aviso_estado():
    """Diz se o aviso por e-mail está ligado e para quem vai (sem expor a chave)."""
    return jsonify({'configurado': notificacoes.configurado(),
                    'destinatarios': notificacoes.destinatarios(contas.listar()),
                    'boas_vindas': notificacoes.boas_vindas_ligadas(),
                    'agradecimento_pendentes': len(contas.sem_email())})


@auth_bp.route('/admin/aviso/teste', methods=['POST'])
@exigir_administrador
def admin_aviso_teste():
    """Envia um e-mail de teste aos destinatários do aviso de novo cadastro."""
    para = notificacoes.destinatarios(contas.listar())
    ok, detalhe = notificacoes.enviar(
        para, 'Evidēns: teste do aviso de novo cadastro',
        'Este é um teste. Quando alguém pedir abertura de conta, você receberá um e-mail como este, '
        f'com os dados do pedido e o link {_url_do_admin()}')
    if not ok:
        return jsonify({'error': f'Não foi possível enviar o e-mail de teste: {detalhe}'}), 502
    return jsonify({'ok': True, 'destinatarios': para})


@auth_bp.route('/admin/boas-vindas/teste', methods=['POST'])
@exigir_administrador
def admin_boas_vindas_teste():
    """Envia ao próprio administrador o e-mail de boas-vindas, para conferir o texto e a entrega."""
    u = usuario_atual()
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'As boas-vindas estão desligadas: falta RESEND_API_KEY ou o remetente do domínio '
                                 '(AVISO_CADASTRO_DE).'}), 502
    assunto, texto = notificacoes.mensagem_de_boas_vindas(u, _url_do_site())
    ok, detalhe = notificacoes.enviar([u['email']], assunto, texto)
    if not ok:
        return jsonify({'error': f'Não foi possível enviar o e-mail de boas-vindas: {detalhe}'}), 502
    return jsonify({'ok': True, 'destinatarios': [u['email']]})


@auth_bp.route('/admin/usuarios')
@exigir_administrador
def admin_usuarios():
    return jsonify({'usuarios': [contas.publico(u) for u in contas.listar()]})


@auth_bp.route('/admin/usuarios/<int:uid>/<acao>', methods=['POST'])
@exigir_administrador
def admin_acao(uid, acao):
    alvo = contas.por_id(uid)
    if alvo is None:
        return jsonify({'error': 'Usuário não encontrado.'}), 404
    if alvo['administrador']:
        return jsonify({'error': 'A conta do administrador não pode ser alterada por aqui.'}), 400
    if acao == 'aprovar':
        return jsonify({'ok': True, 'usuario': contas.publico(contas.definir_situacao(uid, 'aprovado'))})
    if acao == 'bloquear':
        return jsonify({'ok': True, 'usuario': contas.publico(contas.definir_situacao(uid, 'bloqueado'))})
    if acao == 'redefinir-senha':
        u, temporaria = contas.gerar_senha_temporaria(uid)
        return jsonify({'ok': True, 'usuario': contas.publico(u), 'senha_temporaria': temporaria})
    return jsonify({'error': 'Ação desconhecida.'}), 404


LOTE_DE_AGRADECIMENTO = 5  # por pedido: cabe no tempo da função e no limite de envios por segundo da Resend


@auth_bp.route('/admin/agradecimento/teste', methods=['POST'])
@exigir_administrador
def admin_agradecimento_teste():
    """Envia ao próprio administrador o e-mail de agradecimento, para conferir o texto antes do envio."""
    u = usuario_atual()
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'O envio a quem se cadastra está desligado: falta RESEND_API_KEY ou o remetente '
                                 'do domínio (AVISO_CADASTRO_DE).'}), 502
    assunto, texto = notificacoes.mensagem_de_agradecimento(u, _url_do_site())
    ok, detalhe = notificacoes.enviar([u['email']], assunto, texto)
    if not ok:
        return jsonify({'error': f'Não foi possível enviar o e-mail de agradecimento: {detalhe}'}), 502
    return jsonify({'ok': True, 'destinatarios': [u['email']]})


@auth_bp.route('/admin/agradecimento', methods=['POST'])
@exigir_administrador
def admin_agradecimento():
    """Envia o agradecimento a um lote de contas que ainda não receberam e-mail nosso.

    Cada conta recebe uma vez só: a marca é feita antes do envio e desfeita se o envio falhar.
    A página chama de novo enquanto houver ``restantes`` e o lote anterior tiver enviado algo.
    """
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'O envio a quem se cadastra está desligado: falta RESEND_API_KEY ou o remetente '
                                 'do domínio (AVISO_CADASTRO_DE).'}), 502
    enviados, falhas = 0, []
    for i, conta in enumerate(contas.sem_email(LOTE_DE_AGRADECIMENTO)):
        if not contas.reservar_email(conta['id'], 'agradecimento'):
            continue  # outro pedido simultâneo já pegou esta conta
        if i:
            time.sleep(0.6)
        ok, detalhe = notificacoes.enviar_agradecimento(conta, _url_do_site())
        if ok:
            enviados += 1
        else:
            contas.liberar_email(conta['id'], 'agradecimento')
            falhas.append(detalhe)
    return jsonify({'ok': True, 'enviados': enviados, 'falhas': len(falhas),
                    'motivo': falhas[0] if falhas else None, 'restantes': len(contas.sem_email())})
