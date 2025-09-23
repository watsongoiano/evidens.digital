"""Simplified Flask API and static asset server for Vercel deployment."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# Resolve project paths relative to the repository root so the function works on Vercel
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_SRC_DIR = BASE_DIR / "src" / "static"

# Additional directories that contain public assets (login/dashboard, JS, CSS, etc.)
ADDITIONAL_STATIC_DIRS = [
    BASE_DIR,
    BASE_DIR / "styles",
    BASE_DIR / "js",
    BASE_DIR / "assets",
]

# Allow-list of file extensions that can be served as static assets
ALLOWED_STATIC_EXTENSIONS = {
    ".css",
    ".html",
    ".ico",
    ".jpg",
    ".jpeg",
    ".js",
    ".json",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".webmanifest",
    ".woff",
    ".woff2",
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")


def _find_static_asset(path: str) -> tuple[Path, str] | None:
    """Locate a static asset that can be safely served."""

    if not path:
        path = "index.html"

    candidate = Path(path)

    # Prevent path traversal attempts like "../../etc/passwd"
    if any(part == ".." for part in candidate.parts):
        return None

    candidates = [candidate]
    if candidate.suffix:
        if candidate.suffix.lower() not in ALLOWED_STATIC_EXTENSIONS:
            return None
    else:
        candidates.append(candidate.with_suffix(".html"))

    search_dirs = [STATIC_SRC_DIR, *ADDITIONAL_STATIC_DIRS]

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue

        resolved_base = base_dir.resolve()
        for option in candidates:
            absolute = (resolved_base / option).resolve()
            try:
                relative = absolute.relative_to(resolved_base)
            except ValueError:
                continue

            if absolute.is_file() and absolute.suffix.lower() in ALLOWED_STATIC_EXTENSIONS:
                return resolved_base, relative.as_posix()

    return None

def get_db_connection():
    """Get database connection"""
    db_path = '/tmp/evidens.db'  # Use /tmp for Vercel
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with users"""
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create default users if they don't exist
    try:
        # Create medico user using pbkdf2 for broader platform support
        medico_hash = generate_password_hash('medico123', method='pbkdf2:sha256')
        conn.execute('''
            INSERT OR IGNORE INTO users (email, password_hash, role, name)
            VALUES (?, ?, ?, ?)
        ''', ('medico@evidens.digital', medico_hash, 'medico', 'Dr. Médico'))
        
        # Create admin user
        admin_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        conn.execute('''
            INSERT OR IGNORE INTO users (email, password_hash, role, name)
            VALUES (?, ?, ?, ?)
        ''', ('admin@evidens.digital', admin_hash, 'admin', 'Administrador'))
        
        conn.commit()
    except Exception as e:
        print(f"Error creating users: {e}")
    finally:
        conn.close()

# Database will be initialized lazily when needed

# Authentication decorators
def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # For API requests, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'error': 'NOT_AUTHENTICATED'}), 401
            # For regular requests, redirect to login
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """Decorator to require specific role for routes"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != required_role:
                if request.path.startswith('/api/'):
                    return jsonify({'ok': False, 'error': 'INSUFFICIENT_PERMISSIONS'}), 403
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/login/<role>', methods=['POST'])
def login(role):
    """Login endpoint"""
    ensure_db_initialized()  # Initialize database if needed
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': 'INVALID_DATA'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'ok': False, 'error': 'MISSING_FIELDS'}), 400

        # Get user from database
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND role = ? AND is_active = 1',
            (email, role)
        ).fetchone()
        
        if not user:
            conn.close()
            return jsonify({'ok': False, 'error': 'INVALID_CREDENTIALS'}), 401
        
        # Verify password
        if not check_password_hash(user['password_hash'], password):
            conn.close()
            return jsonify({'ok': False, 'error': 'INVALID_CREDENTIALS'}), 401
        
        # Update last login
        conn.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.now().isoformat(), user['id'])
        )
        conn.commit()
        conn.close()
        
        # Set session
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        session['user_name'] = user['name']
        
        return jsonify({
            'ok': True,
            'redirect': '/dashboard',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'role': user['role'],
                'name': user['name']
            }
        })
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'ok': False, 'error': 'SERVER_ERROR'}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Logout endpoint"""
    # Clear all session data
    session.clear()
    return jsonify({'ok': True, 'redirect': '/login.html'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_user():
    """Get current user info"""
    return jsonify({
        'ok': True,
        'user': {
            'id': session['user_id'],
            'email': session['user_email'],
            'role': session['user_role'],
            'name': session['user_name']
        }
    })

@app.route('/dashboard')
@app.route('/dashboard.html')
@login_required
def dashboard():
    """Protected dashboard route"""
    # Serve the dashboard.html file
    return send_from_directory(BASE_DIR, 'dashboard.html')

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')

    # Mock statistics - replace with real data from your database
    stats = {
        'total_checkups': 156,
        'pending_reviews': 12,
        'completed_today': 8,
        'user_role': user_role,
        'user_name': session.get('user_name')
    }

    return jsonify({'ok': True, 'stats': stats})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path: str):
    """Serve static assets and fall back to the SPA entry point."""

    if path.startswith('api/'):
        abort(404)

    asset_info = _find_static_asset(path)
    if asset_info:
        base_dir, relative_path = asset_info
        return send_from_directory(base_dir, relative_path)

    fallback = _find_static_asset('index.html')
    if fallback:
        base_dir, relative_path = fallback
        return send_from_directory(base_dir, relative_path)

    abort(404)


# Default handler for Vercel
def handler(request):
    """Adapt incoming Vercel requests to the Flask application."""

    path = getattr(request, "path", "/")
    method = getattr(request, "method", "GET")
    data = request.get_data() if hasattr(request, "get_data") else None
    headers = getattr(request, "headers", None)
    if headers is not None:
        if hasattr(headers, "items"):
            try:
                headers = list(headers.items())
            except TypeError:
                headers = list(headers.items(multi=True))  # type: ignore[attr-defined]
        else:
            headers = list(headers)

    query_string = getattr(request, "query_string", None)
    if isinstance(query_string, str):
        query_string = query_string.encode("utf-8")

    with app.test_request_context(
        path=path,
        method=method,
        data=data,
        headers=headers,
        query_string=query_string,
    ):
        response = app.full_dispatch_request()

        # ``send_from_directory`` sets ``direct_passthrough`` so Flask can stream
        # files efficiently.  The Vercel runtime eagerly reads the body from the
        # returned response, which raises ``RuntimeError`` if passthrough mode is
        # still enabled.  Disabling it keeps the response compatible without
        # affecting normal Flask behaviour.
        if getattr(response, "direct_passthrough", False):
            response.direct_passthrough = False

        return response

# Global flag to track database initialization
_db_initialized = False

def ensure_db_initialized():
    """Ensure database is initialized (lazy initialization)"""
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize database: {e}")

# Also expose the app directly for Vercel
application = app

if __name__ == '__main__':
    app.run(debug=True)
