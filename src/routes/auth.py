"""Área de acesso: cadastro (liberado na hora ou, com a aprovação manual ligada, depois de aprovado),
login, senha e administração de contas."""
import hmac
import os
import time
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, request, session

from src.utils import contas, notificacoes, termos

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


def termos_pendentes(u=None):
    """True se a conta da sessão ainda não aceitou a versão em vigor dos Termos de Uso."""
    u = u or usuario_atual()
    if u is None:
        return False
    if 'termos_pendentes' not in g:
        g.termos_pendentes = not contas.aceitou(u['id'], termos.VERSAO)
    return g.termos_pendentes


def resposta_termos_pendentes():
    resposta = jsonify({'error': termos.MSG_PENDENTE, 'termos': '/termos?aceitar=1'})
    resposta.headers[termos.CABECALHO] = 'pendente'
    return resposta, 403


def exigir_login(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if not disponivel():
            return jsonify({'error': MSG_INDISPONIVEL}), 503
        if usuario_atual() is None:
            return jsonify({'error': MSG_LOGIN, 'login': '/login'}), 401
        if termos_pendentes():
            return resposta_termos_pendentes()
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
        if termos_pendentes(u):
            return resposta_termos_pendentes()
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
    if not u:
        return jsonify({'usuario': None})
    return jsonify({'usuario': contas.publico(u), 'termos_pendentes': termos_pendentes(u), 'termos_versao': termos.VERSAO})


@auth_bp.route('/auth/termos/aceitar', methods=['POST'])
def aceitar_termos():
    """Aceite da versão em vigor. Só pede sessão: é justamente o que libera o resto."""
    u = usuario_atual()
    if u is None:
        return jsonify({'error': MSG_LOGIN, 'login': '/login'}), 401
    if _corpo().get('versao') != termos.VERSAO:
        return jsonify({'error': 'Os Termos foram atualizados. Recarregue a página e leia a versão atual.'}), 409
    contas.registrar_aceite(u['id'], termos.VERSAO)
    g.termos_pendentes = False
    return jsonify({'ok': True, 'versao': termos.VERSAO})


@auth_bp.route('/auth/cadastro', methods=['POST'])
def cadastro():
    d = _corpo()
    if d.get('aceite_termos') not in (True, 'on', 'true', '1', 1):
        return jsonify({'error': 'Confira os dados informados.',
                        'erros': ['Para criar a conta, leia e aceite os Termos de Uso.']}), 400
    try:
        perfil = _texto(d, 'perfil')
        registro = contas.montar_registro(perfil, _texto(d, 'registro'), _texto(d, 'crm_uf'), _texto(d, 'crm_numero'))
        novo = contas.criar(_texto(d, 'email'), _texto(d, 'nome'), registro, perfil, _texto(d, 'senha'))
    except contas.DadosInvalidos as e:
        return jsonify({'error': 'Confira os dados informados.', 'erros': e.erros}), 400
    if novo:
        contas.registrar_aceite(novo['id'], termos.VERSAO)
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
    # Mesma resposta para e-mail novo e e-mail já cadastrado: ela depende só do modo de aprovação.
    if contas.aprovacao_manual():
        return jsonify({'ok': True, 'liberado': False,
                        'mensagem': 'Cadastro recebido. Você poderá entrar assim que a conta for aprovada.'}), 202
    return jsonify({'ok': True, 'liberado': True,
                    'mensagem': 'Conta criada com sucesso.'}), 201


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
        if contas.aprovacao_manual():
            return jsonify({'error': 'Sua conta ainda aguarda aprovação.'}), 403
        # Pedido feito quando a aprovação manual estava ligada: com ela desligada, libera agora
        # (só se continuar pendente; reativar conta bloqueada é só pelo administrador).
        u = contas.liberar_pendente(u['id'])
    if u['situacao'] != 'aprovado':
        return jsonify({'error': 'Esta conta está bloqueada. Fale com o responsável técnico.'}), 403
    _abrir_sessao(u)
    from src.utils import uso
    uso.registrar('login', u)
    return jsonify({'ok': True, 'usuario': contas.publico(u), 'termos_pendentes': termos_pendentes(u)})


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    try:
        u = usuario_atual() if disponivel() else None
        if u:
            encerrar_assinatura(u['id'])     # sair da conta também fecha a sessão no provedor do certificado
    except Exception as exc:
        # Banco fora do ar não pode impedir a saída: a sessão de assinatura vence sozinha.
        print(f'⚠️ Assinatura digital: sessão não encerrada na saída ({type(exc).__name__})')
    finally:
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


# ── Credenciamentos em planos de saúde (dados da guia SP/SADT; nenhuma senha de operadora) ──

MSG_SO_QUEM_ASSINA = 'O credenciamento em planos de saúde é só para médicos e residentes.'


@auth_bp.route('/auth/credenciamentos')
@exigir_login
def credenciamentos():
    u = usuario_atual()
    if not contas.pode_ter_credenciamento(u):
        return jsonify({'credenciamentos': [], 'disponivel': False})
    return jsonify({'credenciamentos': contas.credenciamentos_de(u['id']), 'disponivel': True})


@auth_bp.route('/auth/credenciamentos', methods=['POST'])
@exigir_login
def credenciamentos_criar():
    u = usuario_atual()
    if not contas.pode_ter_credenciamento(u):
        return jsonify({'error': MSG_SO_QUEM_ASSINA}), 403
    try:
        novo = contas.criar_credenciamento(u['id'], _corpo())
    except contas.DadosInvalidos as e:
        return jsonify({'error': 'Confira os dados informados.', 'erros': e.erros}), 400
    return jsonify({'ok': True, 'credenciamento': novo, 'mensagem': 'Plano salvo.'}), 201


@auth_bp.route('/auth/credenciamentos/<int:cid>/excluir', methods=['POST'])
@exigir_login
def credenciamentos_excluir(cid):
    u = usuario_atual()
    if not contas.excluir_credenciamento(u['id'], cid):
        return jsonify({'error': 'Plano não encontrado.'}), 404
    return jsonify({'ok': True})


# ── Receituário: modelo enviado, montado na tela ou papel já timbrado (só de quem assina) ─────
# src/utils/receituario.py decide o fundo e as margens de cada modo; src/utils/timbrado.py lê o modelo.

MSG_RECEITUARIO = 'O receituário personalizado é só para médicos e residentes.'


def _meta_do_timbrado(t):
    from src.utils import timbrado
    largura, altura = timbrado.dimensoes(t['arquivo'])
    return {'nome': t['nome'], 'enviado_em': t['enviado_em'], 'margem_topo': t['margem_topo'],
            'margem_base': t['margem_base'], 'largura': largura, 'altura': altura}


def _estado_do_receituario(uid):
    from src.utils import receituario
    t = contas.timbrado_de(uid)
    r = contas.receituario_de(uid) or {'dados': {}, 'logo': None}
    montado = {k: v for k, v in r['dados'].items() if k in (*receituario.CAMPOS, 'tema', 'alinhamento', 'cor',
                                                            'margem_topo', 'margem_base')}
    topo, base = receituario.margens_do_papel(r['dados'])
    try:
        ativo = receituario.para_o_pdf(contas, uid)
    except Exception:
        ativo = None
    return {
        'disponivel': True, 'modo': receituario.modo_de(contas, uid),
        'timbrado': _meta_do_timbrado(t) if t else None,
        'montado': dict(montado, tem_logo=bool(r['logo'])) if montado.get('nome') else None,
        'papel': {'margem_topo': topo, 'margem_base': base},
        'ativo': {k: ativo[k] for k in ('largura', 'altura', 'margem_topo', 'margem_base')} if ativo else None,
        'opcoes': {'temas': list(receituario.TEMAS), 'alinhamentos': list(receituario.ALINHAMENTOS),
                   'cores': {k: '#%02x%02x%02x' % v for k, v in receituario.CORES.items()}},
    }


def _medico_do_receituario():
    u = usuario_atual()
    return u if contas.pode_ter_credenciamento(u) else None


def _erro_do_receituario(erro, status=400):
    """Resposta de erro pelo código da exceção: só mensagens fixas escritas para o médico, nunca o texto dela."""
    from src.utils import receituario, timbrado
    codigo = getattr(erro, 'codigo', None)
    mensagem = receituario.MENSAGENS.get(codigo) or timbrado.MENSAGENS.get(codigo) or receituario.MENSAGENS['modo']
    return jsonify({'error': mensagem, 'codigo': codigo if isinstance(codigo, str) else None}), status


@auth_bp.route('/auth/timbrado')
@exigir_login
def timbrado_estado():
    u = _medico_do_receituario()
    if not u:
        return jsonify({'timbrado': None, 'disponivel': False})
    return jsonify(_estado_do_receituario(u['id']))


@auth_bp.route('/auth/timbrado', methods=['POST'])
@exigir_login
def timbrado_enviar():
    """Recebe o modelo do médico (campo `arquivo`: PDF, PNG ou JPG), mede a área livre e passa a usá-lo."""
    from src.utils import timbrado
    u = _medico_do_receituario()
    if not u:
        return jsonify({'error': MSG_RECEITUARIO}), 403
    request.max_content_length = timbrado.TAMANHO_MAXIMO + 64 * 1024
    try:
        arquivo = request.files.get('arquivo')
    except Exception:
        return jsonify({'error': timbrado.MENSAGENS['grande']}), 413
    if arquivo is None:
        return jsonify({'error': timbrado.MENSAGENS['nao_pdf']}), 400
    conteudo = arquivo.read(timbrado.TAMANHO_MAXIMO + 1)
    try:
        if timbrado.eh_imagem(conteudo):     # PNG ou JPG: vira uma página A4 em PDF
            conteudo = timbrado.imagem_para_pdf(conteudo)
        topo, base = timbrado.margens_sugeridas(conteudo)
    except timbrado.TimbradoInvalido as erro:
        return jsonify({'error': timbrado.MENSAGENS.get(erro.codigo, timbrado.MENSAGENS['invalido'])}), 422
    nome = (arquivo.filename or 'timbrado.pdf').rsplit('/', 1)[-1].rsplit('\\', 1)[-1][:120]
    contas.salvar_timbrado(u['id'], conteudo, nome, topo, base)
    contas.salvar_receituario(u['id'], 'modelo')
    return jsonify({'ok': True, **_estado_do_receituario(u['id'])}), 201


@auth_bp.route('/auth/timbrado/modo', methods=['POST'])
@exigir_login
def timbrado_modo():
    """Corpo: {modo: padrao | modelo | montado | papel}."""
    from src.utils import receituario
    u = _medico_do_receituario()
    if not u:
        return jsonify({'error': MSG_RECEITUARIO}), 403
    try:
        receituario.escolher_modo(contas, u['id'], _corpo().get('modo'))
    except receituario.ReceituarioInvalido as erro:
        return _erro_do_receituario(erro)
    return jsonify({'ok': True, **_estado_do_receituario(u['id'])})


@auth_bp.route('/auth/timbrado/montado', methods=['POST'])
@exigir_login
def timbrado_montado():
    """Formulário (multipart): nome, registro, especialidade, endereco, contato, tema, alinhamento, cor,
    `logo` (imagem, opcional) e `remover_logo`. Gera o fundo, mede a área livre e passa a usá-lo."""
    from src.utils import receituario
    u = _medico_do_receituario()
    if not u:
        return jsonify({'error': MSG_RECEITUARIO}), 403
    request.max_content_length = receituario.LOGO_MAXIMO + 64 * 1024
    try:
        campos = request.form.to_dict()
        arquivo = request.files.get('logo')
    except Exception:
        return _erro_do_receituario(receituario.ReceituarioInvalido('logo'), 413)
    logo = arquivo.read(receituario.LOGO_MAXIMO + 1) if arquivo and arquivo.filename else None
    from src.utils import timbrado
    try:
        receituario.salvar_montado(contas, u['id'], campos, logo, remover_logo=campos.get('remover_logo') == '1')
    except (receituario.ReceituarioInvalido, timbrado.TimbradoInvalido) as erro:
        return _erro_do_receituario(erro)
    return jsonify({'ok': True, **_estado_do_receituario(u['id'])})


@auth_bp.route('/auth/timbrado/margens', methods=['POST'])
@exigir_login
def timbrado_margens():
    from src.utils import receituario, timbrado
    u = _medico_do_receituario()
    if not u or receituario.modo_de(contas, u['id']) == 'padrao':
        return jsonify({'error': 'Escolha um receituário antes de ajustar os espaços.'}), 404
    d = _corpo()
    try:
        receituario.ajustar_margens(contas, u['id'], d.get('margem_topo'), d.get('margem_base'))
    except (timbrado.TimbradoInvalido, receituario.ReceituarioInvalido) as erro:
        return _erro_do_receituario(erro)
    return jsonify({'ok': True, **_estado_do_receituario(u['id'])})


@auth_bp.route('/auth/timbrado/remover', methods=['POST'])
@exigir_login
def timbrado_remover():
    """Apaga o modelo enviado; se era ele que valia, os pedidos voltam ao modelo do Evidēns."""
    from src.utils import receituario
    uid = usuario_atual()['id']
    era_o_modelo = receituario.modo_de(contas, uid) == 'modelo'
    contas.remover_timbrado(uid)
    if era_o_modelo:
        contas.salvar_receituario(uid, 'padrao')
    return jsonify({'ok': True, **(_estado_do_receituario(uid) if _medico_do_receituario() else {})})


def _sem_cache(resposta):
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@auth_bp.route('/auth/timbrado/imagem')
@exigir_login
def timbrado_imagem():
    """Imagem do fundo do receituário atual, para ajustar os espaços arrastando as linhas."""
    import io
    from flask import send_file
    from src.utils import receituario
    u = _medico_do_receituario()
    if not u:
        return jsonify({'error': MSG_RECEITUARIO}), 403
    png = receituario.imagem(receituario.para_o_pdf(contas, u['id']))
    return _sem_cache(send_file(io.BytesIO(png), mimetype='image/png', download_name='receituario.png'))


@auth_bp.route('/auth/timbrado/previa')
@exigir_login
def timbrado_previa():
    """Pedido de exemplo (paciente fictício) no receituário atual, para o médico conferir a área livre."""
    import io
    from flask import send_file
    from src.utils import pdf_minutas, receituario
    u = _medico_do_receituario()
    if not u:
        return jsonify({'error': MSG_RECEITUARIO}), 403
    exemplo = [{'titulo': titulo} for titulo in (
        'Hemograma completo com plaquetas', 'Glicose, soro', 'Hemoglobina glicada (HbA1c), soro',
        'Colesterol total e frações, soro', 'Creatinina, soro', 'Hormônio Tireoestimulante (TSH), soro')]
    pdf = pdf_minutas.gerar_pdf_exames_laboratoriais(
        {'nome': 'Paciente de exemplo', 'idade': 50, 'sexo': 'feminino'}, exemplo,
        responsavel=pdf_minutas.responsavel_de(u), timbrado=receituario.para_o_pdf(contas, u['id']))
    return _sem_cache(send_file(io.BytesIO(pdf), mimetype='application/pdf', download_name='previa-receituario.pdf'))


@auth_bp.route('/auth/configurar', methods=['POST'])
def configurar():
    """Cria o primeiro administrador. Só funciona com o código de instalação e enquanto não houver administrador."""
    d = _corpo()
    codigo = os.environ.get('SETUP_TOKEN', '')
    if not codigo or not hmac.compare_digest(codigo.encode(), _texto(d, 'codigo').encode()):
        return jsonify({'error': 'Código de instalação inválido.'}), 403
    if contas.existe_administrador():
        return jsonify({'error': 'O administrador já foi criado.'}), 409
    if d.get('aceite_termos') not in (True, 'on', 'true', '1', 1):
        return jsonify({'error': 'Confira os dados informados.',
                        'erros': ['Para criar a conta, leia e aceite os Termos de Uso.']}), 400
    try:
        registro = contas.montar_registro('medico', _texto(d, 'registro'), _texto(d, 'crm_uf'), _texto(d, 'crm_numero'))
        u = contas.criar(_texto(d, 'email'), _texto(d, 'nome'), registro, 'medico', _texto(d, 'senha'), administrador=True)
    except contas.DadosInvalidos as e:
        return jsonify({'error': 'Confira os dados informados.', 'erros': e.erros}), 400
    if u is None:
        return jsonify({'error': 'Já existe uma conta com este e-mail, ou o administrador acabou de ser criado.'}), 409
    contas.registrar_aceite(u['id'], termos.VERSAO)
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
                    'agradecimento_pendentes': len(contas.sem_email()),
                    'comunicado': _estado_do_comunicado()})


def _estado_do_comunicado():
    from src.utils import comunicados
    chave = next(iter(comunicados.COMUNICADOS))
    quando = comunicados.COMUNICADOS[chave][0]
    return {'chave': chave, 'pendentes': len(contas.sem_comunicado(chave)), 'a_partir': quando.isoformat(),
            'cron': bool((os.environ.get('CRON_SECRET') or '').strip())}


@auth_bp.route('/admin/comunicado/teste', methods=['POST'])
@exigir_administrador
def admin_comunicado_teste():
    """Envia ao próprio administrador o comunicado de novidades, para conferir o texto antes do envio."""
    from src.utils import comunicados
    u = usuario_atual()
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'O envio aos usuários está desligado: falta RESEND_API_KEY ou o remetente do domínio '
                                 '(AVISO_CADASTRO_DE).'}), 502
    chave = next(iter(comunicados.COMUNICADOS))
    assunto, texto = comunicados.COMUNICADOS[chave][1](u, _url_do_site())
    ok, detalhe = notificacoes.enviar([u['email']], assunto, texto)
    if not ok:
        return jsonify({'error': f'Não foi possível enviar o comunicado de teste: {detalhe}'}), 502
    return jsonify({'ok': True, 'destinatarios': [u['email']]})


@auth_bp.route('/admin/comunicado', methods=['POST'])
@exigir_administrador
def admin_comunicado():
    """Envia agora o comunicado (um lote; a página chama de novo enquanto houver restantes)."""
    from src.utils import comunicados
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'O envio aos usuários está desligado: falta RESEND_API_KEY ou o remetente do domínio '
                                 '(AVISO_CADASTRO_DE).'}), 502
    chave = next(iter(comunicados.COMUNICADOS))
    enviados, falha, restantes = comunicados.enviar(chave, _url_do_site(), contas)
    return jsonify({'ok': True, 'enviados': enviados, 'falhas': 1 if falha else 0, 'motivo': falha, 'restantes': restantes})


@auth_bp.route('/cron/comunicados')
def cron_comunicados():
    """Chamado pelo cron da Vercel (vercel.json). Só com o CRON_SECRET no cabeçalho; sem a variável, recusa."""
    import hmac
    from src.utils import comunicados
    segredo = (os.environ.get('CRON_SECRET') or '').strip()
    recebido = request.headers.get('Authorization', '')
    if not segredo or not hmac.compare_digest(recebido, f'Bearer {segredo}'):
        return jsonify({'error': 'não autorizado'}), 401
    if not notificacoes.boas_vindas_ligadas():
        return jsonify({'error': 'envio desligado'}), 503
    resumo = {}
    for chave in comunicados.devidos():
        total, falha, restantes = 0, None, None
        for _ in range(5):   # até 500 contas por execução
            enviados, falha, restantes = comunicados.enviar(chave, _url_do_site(), contas)
            total += enviados
            if falha or not restantes or not enviados:
                break
        resumo[chave] = {'enviados': total, 'restantes': restantes, 'falha': falha}
    return jsonify({'ok': True, 'comunicados': resumo})


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
    return jsonify({'usuarios': [contas.publico(u) for u in contas.listar()],
                    'aprovacao_manual': contas.aprovacao_manual()})


@auth_bp.route('/admin/aprovacao-manual', methods=['POST'])
@exigir_administrador
def admin_aprovacao_manual():
    """Liga ou desliga a aprovação manual de contas novas (reserva para fechar o cadastro)."""
    ligada = _corpo().get('ligada') in (True, 'true', '1', 1, 'on')
    return jsonify({'ok': True, 'aprovacao_manual': contas.definir_aprovacao_manual(ligada)})


@auth_bp.route('/admin/usuarios/<int:uid>/<acao>', methods=['POST'])
@exigir_administrador
def admin_acao(uid, acao):
    alvo = contas.por_id(uid)
    if alvo is None:
        return jsonify({'error': 'Usuário não encontrado.'}), 404
    if alvo['administrador']:
        return jsonify({'error': 'A conta do administrador não pode ser alterada por aqui.'}), 400
    if acao == 'aprovar':
        usuario, anterior = contas.aprovar(uid)
        # Avisa a pessoa quando o acesso passa a valer (aprovação ou reativação). A falha no envio
        # não desfaz a aprovação: a resposta diz se o aviso saiu, para o administrador saber.
        aviso = None
        if anterior is not None:
            try:
                enviado, detalhe = notificacoes.enviar_aprovacao(usuario, _url_do_site(), reativada=(anterior == 'bloqueado'))
            except Exception as erro:
                enviado, detalhe = False, type(erro).__name__
            aviso = {'enviado': enviado, 'motivo': None if enviado else detalhe}
        return jsonify({'ok': True, 'usuario': contas.publico(usuario), 'aviso': aviso})
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


# ── Assinatura digital (certificado ICP-Brasil em nuvem; só de quem assina) ───
#
# O médico abre uma sessão no provedor do certificado (OAuth 2.0 com PKCE, API do DOC-ICP-17.01 do ITI) e,
# enquanto ela vale, os pedidos saem assinados. O login do Evidēns não muda. Ver src/utils/assinatura.py.

MSG_ASSINATURA = {
    'indisponivel': 'A assinatura digital não está disponível nesta conta.',
    'provedor': 'Escolha o provedor do seu certificado digital.',
    'duracao': 'Escolha por quanto tempo manter a sessão de assinatura.',
    'retorno': 'Não foi possível confirmar a autorização. Feche esta aba e tente de novo.',
    'recusada': 'A autorização não foi concluída no provedor do certificado.',
    'sem_certificado': 'Nenhum certificado ICP-Brasil válido foi encontrado nesta conta do provedor.',
    'provedor_fora': 'O provedor do certificado não respondeu. Tente de novo em instantes.',
}
VALIDADE_DO_PEDIDO_DE_SESSAO = 15 * 60     # segundos para concluir a autorização no provedor


def _pode_assinar(usuario):
    from src.utils import assinatura
    return bool(usuario and contas.pode_ter_credenciamento(usuario) and assinatura.disponiveis())


def _retorno_da_assinatura():
    return _url_do_site() + '/api/auth/assinatura/retorno'


def _preferencias_de_assinatura(uid, provedores):
    from src.utils import assinatura
    p = contas.preferencias_de_assinatura(uid) or {}
    ids = [x['id'] for x in provedores]
    return {'provedor': p.get('provedor') if p.get('provedor') in ids else (ids[0] if ids else None),
            'horas': p.get('horas') if p.get('horas') in assinatura.DURACOES else assinatura.DURACAO_PADRAO,
            'assinar': bool(p.get('assinar'))}


def _sessao_publica(s):
    from src.utils import assinatura
    return {'provedor': s['provedor'], 'nome': assinatura.nome_do_provedor(s['provedor']),
            'titular': s['titular'], 'expira_em': s['expira_em']} if s else None


@auth_bp.route('/auth/assinatura')
@exigir_login
def assinatura_estado():
    from src.utils import assinatura
    u = usuario_atual()
    if not _pode_assinar(u):
        return jsonify({'disponivel': False})
    provedores = assinatura.disponiveis()
    return jsonify({
        'disponivel': True, 'provedores': provedores, 'em_breve': list(assinatura.EM_BREVE),
        'duracoes': list(assinatura.DURACOES),
        'preferencias': _preferencias_de_assinatura(u['id'], provedores),
        'sessao': _sessao_publica(contas.sessao_de_assinatura(u['id'])),
    })


@auth_bp.route('/auth/assinatura/preferencias', methods=['POST'])
@exigir_login
def assinatura_preferencias():
    """Corpo: {provedor?, horas?, assinar?}; o que não vem fica como estava."""
    from src.utils import assinatura
    u = usuario_atual()
    if not _pode_assinar(u):
        return jsonify({'error': MSG_ASSINATURA['indisponivel']}), 403
    corpo = request.get_json(silent=True) or {}
    provedores = assinatura.disponiveis()
    atual = _preferencias_de_assinatura(u['id'], provedores)
    if 'provedor' in corpo:
        if corpo['provedor'] not in [p['id'] for p in provedores]:
            return jsonify({'error': MSG_ASSINATURA['provedor']}), 400
        atual['provedor'] = corpo['provedor']
    if 'horas' in corpo:
        if isinstance(corpo['horas'], bool) or corpo['horas'] not in assinatura.DURACOES:
            return jsonify({'error': MSG_ASSINATURA['duracao']}), 400
        atual['horas'] = corpo['horas']
    if 'assinar' in corpo:
        atual['assinar'] = corpo['assinar'] is True
    contas.salvar_preferencias_de_assinatura(u['id'], atual['provedor'], atual['horas'], atual['assinar'])
    return jsonify({'ok': True, 'preferencias': atual})


@auth_bp.route('/auth/assinatura/iniciar', methods=['POST'])
@exigir_login
def assinatura_iniciar():
    """Corpo: {provedor, horas}. Devolve o endereço do provedor onde o médico autoriza a sessão."""
    import secrets
    from src.utils import assinatura
    u = usuario_atual()
    if not _pode_assinar(u):
        return jsonify({'error': MSG_ASSINATURA['indisponivel']}), 403
    corpo = request.get_json(silent=True) or {}
    provedor, horas = corpo.get('provedor'), corpo.get('horas')
    if provedor not in [p['id'] for p in assinatura.disponiveis()]:
        return jsonify({'error': MSG_ASSINATURA['provedor']}), 400
    if isinstance(horas, bool) or horas not in assinatura.DURACOES:
        return jsonify({'error': MSG_ASSINATURA['duracao']}), 400
    verificador, desafio = assinatura.novo_pkce()
    estado = secrets.token_urlsafe(24)
    # O verificador do PKCE e o estado ficam no cookie de sessão (assinado) até a volta do provedor.
    session['assinatura'] = {'e': estado, 'v': verificador, 'p': provedor, 'h': horas, 't': int(time.time())}
    antes = contas.preferencias_de_assinatura(u['id']) or {}
    contas.salvar_preferencias_de_assinatura(u['id'], provedor, horas, antes.get('assinar', True))
    return jsonify({'url': assinatura.url_de_autorizacao(provedor, _retorno_da_assinatura(), estado, desafio, horas)})


def _pagina_de_retorno(ok, mensagem):
    """Página mínima da aba aberta para o provedor: avisa a aba do pedido e se fecha."""
    from html import escape
    from flask import make_response
    titulo = 'Assinatura digital ativada' if ok else 'Assinatura digital não ativada'
    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>{titulo} · Evidēns</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4f7f8;color:#14292f;display:grid;place-items:center;
min-height:100vh;margin:0}}main{{max-width:26rem;padding:2rem;text-align:center}}h1{{font-size:1.25rem}}
p{{line-height:1.5;color:#3d4f54}}a{{color:#0e97b5;font-weight:600}}</style></head>
<body><main><h1>{titulo}</h1><p>{escape(mensagem)}</p>
<p><a href="/intelligent-tools.html">Voltar ao Evidēns</a></p></main>
<script>try{{localStorage.setItem('evidens-assinatura',JSON.stringify({{ok:{'true' if ok else 'false'},t:Date.now()}}))}}catch(e){{}}
{'setTimeout(function(){window.close()},1500)' if ok else ''}</script></body></html>'''
    resposta = make_response(html, 200 if ok else 400)
    resposta.headers['Content-Type'] = 'text/html; charset=utf-8'
    resposta.headers['Cache-Control'] = 'no-store'
    resposta.headers['Referrer-Policy'] = 'no-referrer'
    return resposta


@auth_bp.route('/auth/assinatura/retorno')
def assinatura_retorno():
    """Volta do provedor com o código de autorização: troca pelo token e abre a sessão de assinatura."""
    from src.utils import assinatura
    u = usuario_atual() if disponivel() else None
    pedido = session.pop('assinatura', None)
    if not _pode_assinar(u) or not isinstance(pedido, dict):
        return _pagina_de_retorno(False, MSG_ASSINATURA['retorno'])
    estado = request.args.get('state') or ''
    codigo = request.args.get('code') or ''
    if (not hmac.compare_digest(estado, str(pedido.get('e') or '')) or len(codigo) > 2000
            or time.time() - int(pedido.get('t') or 0) > VALIDADE_DO_PEDIDO_DE_SESSAO):
        return _pagina_de_retorno(False, MSG_ASSINATURA['retorno'])
    if not codigo:
        return _pagina_de_retorno(False, MSG_ASSINATURA['recusada'])
    try:
        token = assinatura.trocar_codigo(pedido['p'], codigo, pedido['v'], _retorno_da_assinatura(), pedido['h'])
        cert = assinatura.escolher_certificado(assinatura.certificados(pedido['p'], token['token']))
        contas.abrir_sessao_de_assinatura(
            u['id'], pedido['p'], assinatura.cifrar(token['token'], current_app.config['SECRET_KEY']),
            cert['alias'], cert['pem'], cert['titular'], min(token['expira_em'], cert['valido_ate']))
    except assinatura.FalhaNaAssinatura as exc:
        print(f'⚠️ Assinatura digital: sessão não aberta ({exc})')
        chave = exc.codigo if exc.codigo in ('sem_certificado', 'provedor_fora') else 'recusada'
        return _pagina_de_retorno(False, MSG_ASSINATURA[chave])
    return _pagina_de_retorno(True, 'Pode fechar esta aba e voltar ao pedido: ele já sai assinado.')


def encerrar_assinatura(uid):
    """Apaga a sessão de assinatura da conta e pede ao provedor que invalide o token."""
    from src.utils import assinatura
    s = contas.sessao_de_assinatura(uid)
    if not s:
        return
    contas.encerrar_sessao_de_assinatura(uid)
    try:
        assinatura.revogar(s['provedor'], assinatura.decifrar(s['token'], current_app.config['SECRET_KEY']))
    except assinatura.FalhaNaAssinatura:
        pass


@auth_bp.route('/auth/assinatura/encerrar', methods=['POST'])
@exigir_login
def assinatura_encerrar():
    encerrar_assinatura(usuario_atual()['id'])
    return jsonify({'ok': True})
