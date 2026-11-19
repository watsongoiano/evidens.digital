"""
Evidens Digital - API Principal
Sistema de Check-up Médico Inteligente
"""
from datetime import timedelta

from flask import Flask, request, jsonify, redirect, send_from_directory
import io
import json
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importar módulos do sistema
from src.routes.checkup_intelligent import checkup_intelligent_bp
from src.utils import uso
from src.routes import auth
from src.routes.auth import auth_bp, exigir_administrador, usuario_atual
from src.routes.pacientes import pacientes_bp, tela_liberada as tela_de_pacientes_liberada
from src.utils import i18n

# Criar aplicação Flask
# Sem a pasta estática automática do Flask: tudo o que é publicado passa pela
# lista ARQUIVOS_PUBLICOS abaixo (a rota /static/<arquivo> serviria a pasta inteira).
app = Flask(__name__, static_folder=None)


class _PedidoEmMemoria(app.request_class):
    """Arquivo enviado fica só na memória. O padrão do Werkzeug passa para um arquivo temporário em disco o que
    tem mais de 500 KiB, e os laudos e as planilhas (limitados a 4 MB pelas rotas) não devem tocar o disco."""

    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()


app.request_class = _PedidoEmMemoria
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', auth.CHAVE_PADRAO)

# Sessão: cookie assinado, inacessível a scripts, só por HTTPS na Vercel,
# não enviado em requisições iniciadas por outros sites, válido por 12 horas.
app.config.update(
    SESSION_COOKIE_NAME='evidens_sessao',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=bool(os.environ.get('VERCEL')),
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=1024 * 1024,
)

# O site e a API ficam no mesmo endereço: não há liberação para outros sites
# (CORS), e envios vindos de outra origem são recusados.
@app.before_request
def _recusar_envio_de_outro_site():
    if request.method == 'POST' and request.path.startswith('/api/') and not auth.origem_confiavel():
        return jsonify({'error': 'Requisição recusada: origem não reconhecida.'}), 403


# Todo o check-up (recomendações e PDFs) exige conta aprovada.
@checkup_intelligent_bp.before_request
def _checkup_exige_login():
    if not auth.disponivel():
        return jsonify({'error': auth.MSG_INDISPONIVEL}), 503
    if usuario_atual() is None:
        return jsonify({'error': auth.MSG_LOGIN, 'login': '/login'}), 401
    if auth.termos_pendentes():
        return auth.resposta_termos_pendentes()


# Registrar blueprints
app.register_blueprint(checkup_intelligent_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
# Cadastro de pacientes: por enquanto só o administrador usa, pela API e pela tela /pacientes (docs/pacientes.md).
app.register_blueprint(pacientes_bp, url_prefix='/api')


def _pagina(arquivo, privada=False):
    resposta = send_from_directory(BASE_DIR, arquivo)
    # Páginas HTML sempre revalidadas: um navegador que guardou a home antiga
    # (botões sem destino) deixaria de ver a área de acesso mesmo depois do deploy.
    resposta.headers['Cache-Control'] = 'no-store' if privada else 'no-cache'
    return resposta

@app.route('/')
def index():
    """Página inicial."""
    if not uso.eh_robo(request.headers.get('User-Agent')):
        uso.registrar('visita', usuario_atual())
    return _pagina('index.html')

@app.route('/intelligent-tools')
def intelligent_tools():
    """Check-up: só para quem entrou."""
    u = usuario_atual()
    if u is None:
        return redirect('/login?destino=check-up')
    if auth.termos_pendentes():
        return redirect('/termos?aceitar=1')
    uso.registrar('acesso', u)
    return _pagina('intelligent-tools.html', privada=True)


@app.route('/login')
def login_page():
    if usuario_atual() is not None:
        return redirect('/intelligent-tools')
    return _pagina('login.html', privada=True)


@app.route('/cadastro')
def cadastro_page():
    return _pagina('cadastro.html')


@app.route('/configurar')
def configurar_page():
    return _pagina('configurar.html', privada=True)


@app.route('/conta')
def conta_page():
    if usuario_atual() is None:
        return redirect('/login')
    if auth.termos_pendentes():
        return redirect('/termos?aceitar=1&destino=conta')
    return _pagina('conta.html', privada=True)


@app.route('/admin')
def admin_page():
    u = usuario_atual()
    if u is None:
        return redirect('/login')
    if not u['administrador']:
        return redirect('/intelligent-tools')
    if auth.termos_pendentes(u):
        return redirect('/termos?aceitar=1&destino=admin')
    return _pagina('admin.html', privada=True)

@app.route('/termos')
def termos_page():
    """Termos de Uso e Política de Privacidade (públicos; o aceite aparece para quem está com ele pendente)."""
    return _pagina('termos.html')

@app.route('/contact')
def contact_page():
    """Rota para página de contato"""
    return _pagina('contact.html')

@app.route('/analytics')
def analytics_page():
    """Painel de uso: só para o administrador."""
    u = usuario_atual()
    if u is None:
        return redirect('/login')
    if not u['administrador']:
        return redirect('/intelligent-tools')
    if auth.termos_pendentes(u):
        return redirect('/termos?aceitar=1&destino=analytics')
    return _pagina('analytics.html', privada=True)

@app.route('/operadoras')
def operadoras_page():
    """Modo sombra das operadoras: por enquanto, só para o administrador."""
    u = usuario_atual()
    if u is None:
        return redirect('/login')
    if not u['administrador']:
        return redirect('/intelligent-tools')
    if auth.termos_pendentes(u):
        return redirect('/termos?aceitar=1&destino=operadoras')
    return _pagina('operadoras.html', privada=True)


@app.route('/pacientes')
def pacientes_page():
    """Tela do cadastro de pacientes: por enquanto, só para o administrador (a mesma regra da API, em
    `pacientes.habilitado_para`). A página não traz dado de paciente: tudo vem de /api/pacientes."""
    u = usuario_atual()
    if u is None:
        return redirect('/login')
    if not tela_de_pacientes_liberada(u):
        return redirect('/intelligent-tools')
    if auth.termos_pendentes(u):
        return redirect('/termos?aceitar=1&destino=pacientes')
    return _pagina('pacientes.html', privada=True)


@app.route('/api/admin/operadoras/conferir', methods=['POST'])
@exigir_administrador
def conferir_pedido_de_exames():
    """Confere um pedido de exames pelo check-up: `paciente` (JSON com os dados do formulário do check-up) e `pedido`
    (um ou mais PDFs com os exames pedidos). Devolve cada exame pedido como indicado ou não indicado pelo check-up.

    Tudo é lido em memória e descartado: nada dos arquivos nem do paciente é gravado ou registrado."""
    from src.utils import laudos, operadora
    if not auth.origem_confiavel():
        return jsonify({'error': 'Envio recusado.'}), 403
    request.max_content_length = operadora.TAMANHO_MAXIMO_DO_ENVIO + 64 * 1024
    try:
        pdfs, bruto = request.files.getlist('pedido'), request.form.get('paciente') or ''
    except Exception:  # corpo maior que o limite
        return jsonify({'error': 'O envio passa de 4 MB. Divida em arquivos menores.'}), 413
    try:
        paciente = json.loads(bruto)
    except ValueError:
        paciente = None
    if not isinstance(paciente, dict):
        return jsonify({'error': 'Informe os dados do paciente.'}), 400
    if not pdfs:
        return jsonify({'error': 'Anexe o PDF com os exames pedidos.'}), 400
    if len(pdfs) > operadora.MAXIMO_DE_ARQUIVOS_NA_TELA:
        return jsonify({'error': f'Envie até {operadora.MAXIMO_DE_ARQUIVOS_NA_TELA} arquivos por vez.'}), 413
    pedidos, avisos, internacao = [], [], False
    for numero, pdf in enumerate(pdfs, 1):
        nome = os.path.splitext(os.path.basename(pdf.filename or ''))[0][:60] or f'pedido{numero}'
        try:
            do_arquivo, soltos, regime = operadora.exames_do_pedido(pdf.read(laudos.TAMANHO_MAXIMO + 1), nome)
        except laudos.LaudoIlegivel as erro:
            avisos.append(f'{nome}: não lido ({laudos.MENSAGENS.get(erro.codigo, laudos.MENSAGENS["invalido"])})')
            continue
        internacao = internacao or bool(regime)
        vistos = {p['exame'] for p in pedidos}
        pedidos += [p for p in do_arquivo if p['exame'] not in vistos]
        if soltos:
            avisos.append(f'{nome}: exames não identificados, que ficaram fora da conferência: {", ".join(soltos)}.')
        if not do_arquivo:
            avisos.append(f'{nome}: nenhum exame identificado.')
    if not pedidos:
        return jsonify({'error': 'Nenhum exame foi identificado no pedido. ' + ' '.join(avisos)}), 422
    resultado, erro = operadora.conferir_pedido(paciente, pedidos)
    if erro:
        return jsonify({'error': erro}), 422
    if internacao:
        avisos.append('O PDF é de internação ou de pronto-socorro. O check-up avalia exames de rotina de consultório.')
    return jsonify({**resultado, 'avisos': avisos})


@app.route('/api/analytics/stats')
@exigir_administrador
def get_analytics_stats():
    """Painel de uso: totais por período, série dos últimos 30 dias e uma linha por usuário."""
    return jsonify(uso.resumo())

# Arquivos que o site publica. A lista é explícita: antes, qualquer arquivo do
# repositório com extensão .html, .js ou .json era servido, o que deixava
# acessíveis por URL as telas antigas (com o cálculo de risco desativado e o
# fluxo de documentos removido) e os arquivos de configuração.
ARQUIVOS_PUBLICOS = frozenset({
    'index.html',
    'contact.html',
    'static/conta.js',
    'static/termos.js',
    'static/termos/evidens-termos-de-uso-v2.0.pdf',
    'static/analytics.js',
    'static/operadoras.js',
    'static/pacientes.js',
    'static/pacientes-checkup.js',
    'static/i18n.js',
    'static/i18n/en.json',
    'favicon.ico',
    'favicon.png',
    'favicon.svg',
    'apple-touch-icon.png',
    'og-image.png',
    'new_logo.png',
    'evidenscheck.png',
    'evidenscheck.svg',
    'static/evidens.css',
    'src/static/styles/tokens.css',
    'src/static/styles/base.css',
    'src/static/styles/components.css',
})


# Campos das respostas da API que carregam frases para a pessoa ler. Só eles são traduzidos:
# identificadores (categoria, prioridade), dados digitados e links ficam como estão.
CAMPOS_DE_TEXTO = frozenset({'error', 'erros', 'mensagem'})


@app.after_request
def responder_no_idioma(resposta):
    """Em inglês (cookie do seletor ou ?lang=en), traduz as frases das respostas da API."""
    idioma = i18n.idioma_do_pedido(request)
    # O cadastro de pacientes fica de fora: a resposta leva o que o médico digitou (a ficha pode ter um campo
    # chamado "mensagem"), e dado de paciente nunca passa pelo tradutor.
    if idioma == 'pt' or not request.path.startswith('/api/') or request.path.startswith(('/api/admin', '/api/analytics', '/api/pacientes')):
        return resposta
    if resposta.mimetype != 'application/json' or resposta.direct_passthrough:
        return resposta
    dados = resposta.get_json(silent=True)
    if not isinstance(dados, (dict, list)):
        return resposta

    def percorrer(valor, traduzir=False):
        if isinstance(valor, str):
            return i18n.traduzir(valor, idioma) if traduzir else valor
        if isinstance(valor, list):
            return [percorrer(v, traduzir) for v in valor]
        if isinstance(valor, dict):
            return {k: percorrer(v, traduzir or k in CAMPOS_DE_TEXTO) for k, v in valor.items()}
        return valor

    resposta.set_data(json.dumps(percorrer(dados), ensure_ascii=False))
    return resposta


@app.route('/<path:filename>')
def serve_static(filename):
    """Servir apenas os arquivos estáticos publicados pelo site."""
    # O caminho servido vem da própria lista, nunca do texto da requisição.
    publicado = next((nome for nome in ARQUIVOS_PUBLICOS if nome == filename), None)
    if publicado is not None and (BASE_DIR / publicado).is_file():
        return send_from_directory(BASE_DIR, publicado)

    return jsonify({'error': 'File not found'}), 404

@app.errorhandler(404)
def not_found(e):
    """Handler para erros 404"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handler para erros 500"""
    return jsonify({'error': 'Internal server error'}), 500

# Para execução local. Escuta só na própria máquina; o modo de depuração (que
# permite executar código pelo navegador) fica desligado, a menos que FLASK_DEBUG=1.
if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='127.0.0.1', port=5000)

