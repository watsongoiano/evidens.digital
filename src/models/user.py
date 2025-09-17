from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import os

db = SQLAlchemy()
ph = PasswordHasher(
    time_cost=int(os.getenv('ARGON2_TIME_COST', 2)),
    memory_cost=int(os.getenv('ARGON2_MEMORY_COST', 65536)),
    parallelism=int(os.getenv('ARGON2_PARALLELISM', 1))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='medico')  # 'medico' or 'administrador'
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_sub = db.Column(db.String(255), nullable=True)
    
    # Security fields
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # MFA (for future use)
    mfa_enabled = db.Column(db.Boolean, default=False)
    
    # Password reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Hash and set password using Argon2"""
        self.password_hash = ph.hash(password)
    
    def check_password(self, password):
        """Verify password using Argon2"""
        if not self.password_hash:
            return False
        try:
            ph.verify(self.password_hash, password)
            return True
        except VerifyMismatchError:
            return False
    
    def is_locked(self):
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self):
        """Lock account for specified duration"""
        lockout_duration = int(os.getenv('LOCKOUT_DURATION', 900))  # 15 minutes default
        self.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
        db.session.commit()
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.failed_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def increment_failed_attempts(self):
        """Increment failed login attempts and lock if necessary"""
        self.failed_attempts += 1
        max_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
        
        if self.failed_attempts >= max_attempts:
            self.lock_account()
        else:
            db.session.commit()
    
    def reset_failed_attempts(self):
        """Reset failed attempts on successful login"""
        self.failed_attempts = 0
        self.last_login_at = datetime.utcnow()
        db.session.commit()
    
    def generate_reset_token(self):
        """Generate password reset token"""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify password reset token"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if datetime.utcnow() > self.reset_token_expires:
            return False
        return self.reset_token == token
    
    def clear_reset_token(self):
        """Clear password reset token"""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'mfa_enabled': self.mfa_enabled
        }

class LoginAttempt(db.Model):
    """Audit log for login attempts"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    success = db.Column(db.Boolean, nullable=False)
    failure_reason = db.Column(db.String(100), nullable=True)
    oauth_provider = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        status = "SUCCESS" if self.success else f"FAILED ({self.failure_reason})"
        return f'<LoginAttempt {self.email} - {status} at {self.timestamp}>'
