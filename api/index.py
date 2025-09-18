"""Simplified Flask API and static asset server for Vercel deployment."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

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

# Initialize database on import
init_db()

@app.route('/api/login/<role>', methods=['POST'])
def login(role):
    """Login endpoint"""
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
def logout():
    """Logout endpoint"""
    session.clear()
    return jsonify({'ok': True, 'redirect': '/login'})

@app.route('/api/user', methods=['GET'])
def get_user():
    """Get current user info"""
    if 'user_id' not in session:
        return jsonify({'ok': False, 'error': 'NOT_AUTHENTICATED'}), 401
    
    return jsonify({
        'ok': True,
        'user': {
            'id': session['user_id'],
            'email': session['user_email'],
            'role': session['user_role'],
            'name': session['user_name']
        }
    })

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
    return app(request.environ, lambda *args: None)

if __name__ == '__main__':
    app.run(debug=True)
