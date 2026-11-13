"""
Evidens Digital - API Principal
Sistema de Check-up Médico Inteligente
"""
from datetime import timedelta

from flask import Flask, request, jsonify, redirect, send_from_directory
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Importar módulos do sistema
from src.routes.checkup_intelligent import checkup_intelligent_bp
from src.utils.analytics import analytics
from src.routes import auth
from src.routes.auth import auth_bp, exigir_administrador, usuario_atual

# Criar aplicação Flask
# Sem a pasta estática automática do Flask: tudo o que é publicado passa pela
# lista ARQUIVOS_PUBLICOS abaixo (a rota /static/<arquivo> serviria a pasta inteira).
app = Flask(__name__, static_folder=None)
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


# Registrar blueprints
app.register_blueprint(checkup_intelligent_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')


def _pagina(arquivo, privada=False):
    resposta = send_from_directory(BASE_DIR, arquivo)
    # Páginas HTML sempre revalidadas: um navegador que guardou a home antiga
    # (botões sem destino) deixaria de ver a área de acesso mesmo depois do deploy.
    resposta.headers['Cache-Control'] = 'no-store' if privada else 'no-cache'
    return resposta

@app.route('/')
def index():
    """Página inicial."""
    return _pagina('index.html')

@app.route('/intelligent-tools')
def intelligent_tools():
    """Check-up: só para quem entrou."""
    if usuario_atual() is None:
        return redirect('/login?destino=check-up')
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
    return _pagina('conta.html', privada=True)


@app.route('/admin')
def admin_page():
    u = usuario_atual()
    if u is None:
        return redirect('/login')
    if not u['administrador']:
        return redirect('/intelligent-tools')
    return _pagina('admin.html', privada=True)

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
    return _pagina('analytics.html', privada=True)

@app.route('/api/analytics/stats')
@exigir_administrador
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    return jsonify(analytics.get_summary())

@app.route('/api/analytics/full')
@exigir_administrador
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas"""
    return jsonify(analytics.get_stats())

# Arquivos que o site publica. A lista é explícita: antes, qualquer arquivo do
# repositório com extensão .html, .js ou .json era servido, o que deixava
# acessíveis por URL as telas antigas (com o cálculo de risco desativado e o
# fluxo de documentos removido) e os arquivos de configuração.
ARQUIVOS_PUBLICOS = frozenset({
    'index.html',
    'contact.html',
    'static/conta.js',
    'favicon.ico',
    'favicon.png',
    'favicon.svg',
    'apple-touch-icon.png',
    'new_logo.png',
    'evidenscheck.png',
    'evidenscheck.svg',
    'static/evidens.css',
    'src/static/styles/tokens.css',
    'src/static/styles/base.css',
    'src/static/styles/components.css',
})


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

