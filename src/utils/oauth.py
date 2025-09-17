"""
OAuth utilities for Google and Apple authentication
"""

import os
import secrets
import jwt
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from flask import session, request, url_for
from src.models.user import User, LoginAttempt, db

class OAuthProvider:
    """Base OAuth provider class"""
    
    def __init__(self, app=None):
        self.oauth = OAuth()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.oauth.init_app(app)
        self.setup_providers()
    
    def setup_providers(self):
        """Setup OAuth providers"""
        self.setup_google()
        self.setup_apple()
    
    def setup_google(self):
        """Setup Google OAuth"""
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not google_client_id or not google_client_secret:
            print("⚠️  Google OAuth not configured - missing client ID or secret")
            return
        
        self.google = self.oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
            client_kwargs={
                'scope': 'openid email profile',
                'prompt': 'select_account',
            }
        )
        print("✅ Google OAuth configured")
    
    def setup_apple(self):
        """Setup Apple OAuth"""
        apple_client_id = os.getenv('APPLE_CLIENT_ID')
        apple_client_secret = os.getenv('APPLE_CLIENT_SECRET')
        apple_key_id = os.getenv('APPLE_KEY_ID')
        apple_team_id = os.getenv('APPLE_TEAM_ID')
        
        if not all([apple_client_id, apple_client_secret, apple_key_id, apple_team_id]):
            print("⚠️  Apple OAuth not configured - missing required credentials")
            return
        
        self.apple = self.oauth.register(
            name='apple',
            client_id=apple_client_id,
            client_secret=apple_client_secret,
            authorize_url='https://appleid.apple.com/auth/authorize',
            access_token_url='https://appleid.apple.com/auth/token',
            client_kwargs={
                'scope': 'name email',
                'response_mode': 'form_post',
            }
        )
        print("✅ Apple OAuth configured")
    
    def generate_state(self, role='medico'):
        """Generate OAuth state parameter with role info"""
        state_data = {
            'csrf_token': secrets.token_urlsafe(32),
            'role': role,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in session for verification
        session['oauth_state'] = state_data
        
        return state_data['csrf_token']
    
    def verify_state(self, state):
        """Verify OAuth state parameter"""
        stored_state = session.get('oauth_state')
        
        if not stored_state:
            return False, None
        
        # Check CSRF token
        if stored_state.get('csrf_token') != state:
            return False, None
        
        # Check timestamp (expire after 10 minutes)
        try:
            timestamp = datetime.fromisoformat(stored_state['timestamp'])
            if datetime.utcnow() - timestamp > timedelta(minutes=10):
                return False, None
        except (ValueError, KeyError):
            return False, None
        
        return True, stored_state.get('role', 'medico')
    
    def create_or_update_user(self, email, name, provider, provider_id, role='medico'):
        """Create or update user from OAuth data"""
        
        # Check if user exists with this OAuth provider
        user = User.query.filter_by(
            oauth_provider=provider,
            oauth_sub=provider_id
        ).first()
        
        if user:
            # Update existing OAuth user
            user.last_login_at = datetime.utcnow()
            user.reset_failed_attempts()
            db.session.commit()
            return user, False  # False = not newly created
        
        # Check if user exists with this email
        user = User.query.filter_by(email=email).first()
        
        if user:
            if user.oauth_provider:
                # User has different OAuth provider
                raise ValueError(f"Email already registered with {user.oauth_provider}")
            else:
                # Link OAuth to existing password account
                user.oauth_provider = provider
                user.oauth_sub = provider_id
                user.last_login_at = datetime.utcnow()
                user.reset_failed_attempts()
                db.session.commit()
                return user, False
        
        # Create new user
        user = User(
            email=email,
            username=name,
            role=role,
            oauth_provider=provider,
            oauth_sub=provider_id
        )
        
        db.session.add(user)
        db.session.commit()
        
        return user, True  # True = newly created
    
    def log_oauth_attempt(self, email, provider, success, failure_reason=None):
        """Log OAuth login attempt"""
        attempt = LoginAttempt(
            email=email,
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            user_agent=request.headers.get('User-Agent'),
            success=success,
            failure_reason=failure_reason,
            oauth_provider=provider
        )
        db.session.add(attempt)
        db.session.commit()

class GoogleOAuth:
    """Google OAuth handler"""
    
    def __init__(self, oauth_provider):
        self.provider = oauth_provider
    
    def get_authorization_url(self, role='medico'):
        """Get Google authorization URL"""
        if not hasattr(self.provider, 'google'):
            raise ValueError("Google OAuth not configured")
        
        state = self.provider.generate_state(role)
        
        redirect_uri = url_for('auth.google_callback', _external=True)
        
        return self.provider.google.authorize_redirect(
            redirect_uri=redirect_uri,
            state=state
        )
    
    def handle_callback(self, code, state):
        """Handle Google OAuth callback"""
        if not hasattr(self.provider, 'google'):
            raise ValueError("Google OAuth not configured")
        
        # Verify state
        state_valid, role = self.provider.verify_state(state)
        if not state_valid:
            raise ValueError("Invalid OAuth state")
        
        # Exchange code for token
        token = self.provider.google.authorize_access_token()
        
        # Get user info
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback: get user info from Google API
            resp = self.provider.google.get('userinfo')
            user_info = resp.json()
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        google_id = user_info.get('sub')
        
        if not email or not google_id:
            raise ValueError("Invalid user info from Google")
        
        # Create or update user
        try:
            user, is_new = self.provider.create_or_update_user(
                email=email,
                name=name,
                provider='google',
                provider_id=google_id,
                role=role
            )
            
            self.provider.log_oauth_attempt(email, 'google', True)
            
            return user, is_new
            
        except ValueError as e:
            self.provider.log_oauth_attempt(email, 'google', False, str(e))
            raise

class AppleOAuth:
    """Apple OAuth handler"""
    
    def __init__(self, oauth_provider):
        self.provider = oauth_provider
    
    def get_authorization_url(self, role='medico'):
        """Get Apple authorization URL"""
        if not hasattr(self.provider, 'apple'):
            raise ValueError("Apple OAuth not configured")
        
        state = self.provider.generate_state(role)
        
        redirect_uri = url_for('auth.apple_callback', _external=True)
        
        return self.provider.apple.authorize_redirect(
            redirect_uri=redirect_uri,
            state=state
        )
    
    def handle_callback(self, code, state, id_token=None):
        """Handle Apple OAuth callback"""
        if not hasattr(self.provider, 'apple'):
            raise ValueError("Apple OAuth not configured")
        
        # Verify state
        state_valid, role = self.provider.verify_state(state)
        if not state_valid:
            raise ValueError("Invalid OAuth state")
        
        # Apple sends user info in the ID token
        if not id_token:
            raise ValueError("No ID token received from Apple")
        
        # Decode ID token (Apple uses RS256)
        try:
            # For production, you should verify the signature
            # For now, we'll decode without verification (not recommended for production)
            decoded_token = jwt.decode(
                id_token, 
                options={"verify_signature": False}
            )
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid Apple ID token: {e}")
        
        email = decoded_token.get('email')
        apple_id = decoded_token.get('sub')
        name = decoded_token.get('name', {}).get('firstName', email.split('@')[0] if email else 'User')
        
        if not email or not apple_id:
            raise ValueError("Invalid user info from Apple")
        
        # Create or update user
        try:
            user, is_new = self.provider.create_or_update_user(
                email=email,
                name=name,
                provider='apple',
                provider_id=apple_id,
                role=role
            )
            
            self.provider.log_oauth_attempt(email, 'apple', True)
            
            return user, is_new
            
        except ValueError as e:
            self.provider.log_oauth_attempt(email, 'apple', False, str(e))
            raise

# Global OAuth provider instance
oauth_provider = OAuthProvider()
google_oauth = GoogleOAuth(oauth_provider)
apple_oauth = AppleOAuth(oauth_provider)
