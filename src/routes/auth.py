from __future__ import annotations

from datetime import datetime
import os
import re

from flask import Blueprint, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from src.models.user import LoginAttempt, User, db
from src.utils.rate_limiter import rate_limit
from src.utils.oauth import apple_oauth, google_oauth

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def log_login_attempt(email, success, failure_reason=None, oauth_provider=None):
    """Log login attempt for audit purposes"""
    attempt = LoginAttempt(
        email=email,
        ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        user_agent=request.headers.get('User-Agent'),
        success=success,
        failure_reason=failure_reason,
        oauth_provider=oauth_provider
    )
    db.session.add(attempt)
    db.session.commit()


def send_password_reset_email(email: str, token: str) -> bool:
    """Placeholder password reset email sender.

    The real implementation should integrate with the organisation's email
    provider. The function returns ``True`` so tests can assert it was called
    successfully.
    """

    reset_url = url_for('auth.reset_password', _external=True)
    print(f"Password reset requested for {email}. Token: {token}. Reset URL: {reset_url}")
    return True

def perform_login(email: str | None, password: str | None, expected_role: str) -> tuple[dict, int]:
    """Perform login with security checks."""

    if not email or not password:
        return {"ok": False, "error": "EMAIL_PASSWORD_REQUIRED"}, 400

    if not validate_email(email):
        return {"ok": False, "error": "INVALID_EMAIL_FORMAT"}, 400

    email = email.lower().strip()
    user = User.query.filter_by(email=email).first()

    if not user:
        log_login_attempt(email, False, "USER_NOT_FOUND")
        return {"ok": False, "error": "USER_NOT_FOUND"}, 404

    if user.is_locked():
        log_login_attempt(email, False, "ACCOUNT_LOCKED")
        lockout_remaining = int((user.locked_until - datetime.utcnow()).total_seconds()) if user.locked_until else 0
        return {
            "ok": False,
            "error": "ACCOUNT_LOCKED",
            "retry_after_sec": max(0, lockout_remaining),
        }, 429

    if user.role != expected_role:
        user.increment_failed_attempts()
        log_login_attempt(email, False, "WRONG_ROLE")
        return {"ok": False, "error": "WRONG_ROLE"}, 403

    if not user.check_password(password):
        user.increment_failed_attempts()
        log_login_attempt(email, False, "WRONG_PASSWORD")
        return {"ok": False, "error": "INVALID_CREDENTIALS"}, 401

    # Successful login
    user.reset_failed_attempts()
    login_user(user, remember=True)
    log_login_attempt(email, True)

    return {
        "ok": True,
        "redirect": "/dashboard",
        "user": user.to_dict(),
    }, 200

@auth_bp.route('/login/medico', methods=['POST'])
@rate_limit("login", per_minute=10)
def login_medico():
    """Login endpoint for medical professionals"""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "JSON_REQUIRED"}), 400
    
    result, status = perform_login(
        data.get('email'),
        data.get('password'),
        'medico'
    )
    return jsonify(result), status

@auth_bp.route('/login/admin', methods=['POST'])
@auth_bp.route('/login/administrador', methods=['POST'])
@rate_limit("login", per_minute=5)  # Stricter rate limit for admin
def login_admin():
    """Login endpoint for administrators"""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "JSON_REQUIRED"}), 400
    
    result, status = perform_login(
        data.get('email'),
        data.get('password'),
        'administrador'
    )
    return jsonify(result), status

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout current user"""
    logout_user()
    return jsonify({"ok": True, "message": "Logged out successfully"})

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user information"""
    return jsonify({
        "ok": True,
        "user": current_user.to_dict()
    })

@auth_bp.route('/register', methods=['POST'])
@rate_limit("register", per_minute=3)
def register():
    """Register new user (admin only for now)"""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "JSON_REQUIRED"}), 400
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    role = data.get('role', 'medico')
    
    if not email or not password:
        return jsonify({"ok": False, "error": "EMAIL_PASSWORD_REQUIRED"}), 400
    
    if not validate_email(email):
        return jsonify({"ok": False, "error": "INVALID_EMAIL_FORMAT"}), 400
    
    if len(password) < 8:
        return jsonify({"ok": False, "error": "PASSWORD_TOO_SHORT"}), 400
    
    if role not in ['medico', 'administrador']:
        return jsonify({"ok": False, "error": "INVALID_ROLE"}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"ok": False, "error": "EMAIL_ALREADY_EXISTS"}), 409
    
    # Create new user
    user = User(email=email, role=role)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        "ok": True,
        "message": "User created successfully",
        "user": user.to_dict()
    }), 201

@auth_bp.route('/forgot-password', methods=['POST'])
@rate_limit("forgot_password", per_minute=3)
def forgot_password():
    """Request password reset"""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "JSON_REQUIRED"}), 400

    email = data.get('email', '').lower().strip()

    if not email or not validate_email(email):
        return jsonify({"ok": False, "error": "INVALID_EMAIL"}), 400

    user = User.query.filter_by(email=email).first()

    # Always return success to prevent email enumeration
    if user:
        token = user.generate_reset_token()
        send_password_reset_email(user.email, token)

    return jsonify({
        "ok": True,
        "message": "If the email exists, a reset link has been sent"
    })

@auth_bp.route('/reset-password', methods=['POST'])
@rate_limit("reset_password", per_minute=5)
def reset_password():
    """Reset password with token"""
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "JSON_REQUIRED"}), 400
    
    token = data.get('token')
    new_password = data.get('new_password') or data.get('password')

    if not token or not new_password:
        return jsonify({"ok": False, "error": "TOKEN_PASSWORD_REQUIRED"}), 400

    if len(new_password) < 8:
        return jsonify({"ok": False, "error": "PASSWORD_TOO_SHORT"}), 400

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.verify_reset_token(token):
        return jsonify({"ok": False, "error": "INVALID_TOKEN"}), 400

    user.set_password(new_password)
    user.clear_reset_token()

    return jsonify({
        "ok": True,
        "message": "Password reset successfully"
    })

# OAuth routes
@auth_bp.route('/login/google')
def google_login():
    """Redirect to Google OAuth"""
    try:
        from src.utils.oauth import google_oauth
        role = request.args.get('role', 'medico')
        
        if role not in ['medico', 'administrador']:
            return jsonify({"ok": False, "error": "INVALID_ROLE"}), 400
        
        return google_oauth.get_authorization_url(role)
        
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return jsonify({"ok": False, "error": "OAUTH_CONFIG_ERROR"}), 500

@auth_bp.route('/auth/callback/google')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        from src.utils.oauth import google_oauth
        from flask_login import login_user
        
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            error_description = request.args.get('error_description', 'OAuth error')
            return redirect(f'/login?error={error_description}')
        
        if not code or not state:
            return redirect('/login?error=Missing OAuth parameters')
        
        # Handle OAuth callback
        user, is_new = google_oauth.handle_callback(code, state)
        
        # Log in user
        login_user(user, remember=True)
        
        # Redirect to dashboard
        return redirect('/dashboard')
        
    except ValueError as e:
        return redirect(f'/login?error={str(e)}')
    except Exception as e:
        print(f"Google OAuth callback error: {e}")
        return redirect('/login?error=OAuth authentication failed')

@auth_bp.route('/login/apple')
def apple_login():
    """Redirect to Apple OAuth"""
    try:
        from src.utils.oauth import apple_oauth
        role = request.args.get('role', 'medico')
        
        if role not in ['medico', 'administrador']:
            return jsonify({"ok": False, "error": "INVALID_ROLE"}), 400
        
        return apple_oauth.get_authorization_url(role)
        
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        print(f"Apple OAuth error: {e}")
        return jsonify({"ok": False, "error": "OAUTH_CONFIG_ERROR"}), 500

@auth_bp.route('/auth/callback/apple', methods=['POST'])
def apple_callback():
    """Handle Apple OAuth callback"""
    try:
        from src.utils.oauth import apple_oauth
        from flask_login import login_user
        
        code = request.form.get('code')
        state = request.form.get('state')
        id_token = request.form.get('id_token')
        error = request.form.get('error')
        
        if error:
            error_description = request.form.get('error_description', 'OAuth error')
            return redirect(f'/login?error={error_description}')
        
        if not code or not state:
            return redirect('/login?error=Missing OAuth parameters')
        
        # Handle OAuth callback
        user, is_new = apple_oauth.handle_callback(code, state, id_token)
        
        # Log in user
        login_user(user, remember=True)
        
        # Redirect to dashboard
        return redirect('/dashboard')
        
    except ValueError as e:
        return redirect(f'/login?error={str(e)}')
    except Exception as e:
        print(f"Apple OAuth callback error: {e}")
        return redirect('/login?error=OAuth authentication failed')
