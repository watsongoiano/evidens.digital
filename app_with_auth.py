"""
Main Flask application with authentication system
"""

import os
from flask import Flask, request, jsonify, redirect, send_from_directory, render_template_string, url_for
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from src.models.user import db, User
from src.routes.auth import auth_bp
from src.utils.oauth import oauth_provider
from src.utils.rate_limiter import RateLimiter

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    # Database configuration
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'database', 'app.db')
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{database_path}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # OAuth Configuration
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    app.config['APPLE_CLIENT_ID'] = os.getenv('APPLE_CLIENT_ID')
    app.config['APPLE_CLIENT_SECRET'] = os.getenv('APPLE_CLIENT_SECRET')
    app.config['APPLE_KEY_ID'] = os.getenv('APPLE_KEY_ID')
    app.config['APPLE_TEAM_ID'] = os.getenv('APPLE_TEAM_ID')
    
    # Rate Limiting Configuration
    app.config['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, supports_credentials=True)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize OAuth
    oauth_provider.init_app(app)
    
    # Initialize database migration
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    
    # Test route for debugging
    @app.route('/api/test-login', methods=['POST'])
    def test_login():
        """Test login endpoint for debugging"""
        from flask import request, jsonify
        from src.models.user import User
        
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({"error": "User not found", "email": email}), 404
        
        password_valid = user.check_password(password)
        
        return jsonify({
            "user_found": True,
            "email": user.email,
            "role": user.role,
            "password_valid": password_valid,
            "expected_role": "medico"
        })
    
    # Routes
    @app.route('/')
    def index():
        """Home page"""
        if current_user.is_authenticated:
            return redirect('/dashboard')
        return send_from_directory('.', 'index.html')
    
    @app.route('/login')
    def login():
        """Login page"""
        if current_user.is_authenticated:
            return redirect('/dashboard')
        return send_from_directory('.', 'login.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard page - requires authentication"""
        return send_from_directory('.', 'dashboard.html')
    
    @app.route('/intelligent-tools')
    def intelligent_tools():
        """Intelligent tools page"""
        return send_from_directory('.', 'intelligent-tools.html')
    
    @app.route('/analytics')
    @login_required
    def analytics():
        """Analytics page - requires authentication"""
        # For now, redirect to intelligent tools
        return redirect('/intelligent-tools')
    
    # Static file routes
    @app.route('/styles/<path:filename>')
    def styles(filename):
        return send_from_directory('styles', filename)
    
    @app.route('/js/<path:filename>')
    def javascript(filename):
        return send_from_directory('js', filename)
    
    # Removed conflicting /api/<path:filename> route to avoid conflicts with auth API
    
    @app.route('/src/<path:filename>')
    def src_files(filename):
        return send_from_directory('src', filename)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Página não encontrada</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #E74C3C; }
                a { color: #4A90E2; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>404 - Página não encontrada</h1>
            <p>A página que você está procurando não existe.</p>
            <a href="/">Voltar ao início</a>
        </body>
        </html>
        '''), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>500 - Erro interno</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #E74C3C; }
                a { color: #4A90E2; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>500 - Erro interno do servidor</h1>
            <p>Ocorreu um erro interno. Tente novamente mais tarde.</p>
            <a href="/">Voltar ao início</a>
        </body>
        </html>
        '''), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

# For backwards compatibility, keep the original app.py structure
app = create_app()

if __name__ == '__main__':
    # Development server
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    print("🚀 Starting evidēns application...")
    print(f"   Debug mode: {debug_mode}")
    print(f"   Port: {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
