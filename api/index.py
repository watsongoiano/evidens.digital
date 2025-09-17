"""
Simplified Flask API for Vercel deployment
"""
from flask import Flask, request, jsonify, session
import os
import sys
import sqlite3
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Password hasher
ph = PasswordHasher()

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
        # Create medico user
        medico_hash = ph.hash('medico123')
        conn.execute('''
            INSERT OR IGNORE INTO users (email, password_hash, role, name)
            VALUES (?, ?, ?, ?)
        ''', ('medico@evidens.digital', medico_hash, 'medico', 'Dr. Médico'))
        
        # Create admin user
        admin_hash = ph.hash('admin123')
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
        try:
            ph.verify(user['password_hash'], password)
        except VerifyMismatchError:
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

# Default handler for Vercel
def handler(request):
    return app(request.environ, lambda *args: None)

if __name__ == '__main__':
    app.run(debug=True)
