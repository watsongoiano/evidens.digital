"""
Unit tests for authentication system
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Set up test environment before importing app
os.environ['TESTING'] = 'True'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app
from src.models.user import User, LoginAttempt, db
from src.utils.rate_limiter import RateLimiter

class AuthTestCase(unittest.TestCase):
    """Test cases for authentication system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create all tables
        db.create_all()
        
        # Create test users
        self.test_user_medico = User(
            email='medico@test.com',
            username='Dr. Test',
            role='medico'
        )
        self.test_user_medico.set_password('password123')
        
        self.test_user_admin = User(
            email='admin@test.com',
            username='Admin Test',
            role='administrador'
        )
        self.test_user_admin.set_password('admin123')
        
        db.session.add(self.test_user_medico)
        db.session.add(self.test_user_admin)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_user_model_creation(self):
        """Test user model creation and password hashing"""
        user = User(
            email='test@example.com',
            username='Test User',
            role='medico'
        )
        user.set_password('testpassword')
        
        self.assertTrue(user.check_password('testpassword'))
        self.assertFalse(user.check_password('wrongpassword'))
        self.assertIsNotNone(user.password_hash)
        self.assertNotEqual(user.password_hash, 'testpassword')
    
    def test_login_success_medico(self):
        """Test successful login for medico"""
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertIn('user', data)
        self.assertEqual(data['user']['role'], 'medico')
    
    def test_login_success_admin(self):
        """Test successful login for admin"""
        response = self.client.post('/api/login/administrador', 
            data=json.dumps({
                'email': 'admin@test.com',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertIn('user', data)
        self.assertEqual(data['user']['role'], 'administrador')
    
    def test_login_wrong_credentials(self):
        """Test login with wrong credentials"""
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'INVALID_CREDENTIALS')
    
    def test_login_wrong_role(self):
        """Test login with wrong role"""
        response = self.client.post('/api/login/administrador', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'WRONG_ROLE')
    
    def test_login_nonexistent_user(self):
        """Test login with nonexistent user"""
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'nonexistent@test.com',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'USER_NOT_FOUND')
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com'
                # Missing password
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'EMAIL_PASSWORD_REQUIRED')
    
    def test_login_invalid_email_format(self):
        """Test login with invalid email format"""
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'invalid-email',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'INVALID_EMAIL_FORMAT')
    
    def test_account_lockout(self):
        """Test account lockout after multiple failed attempts"""
        # Make 5 failed login attempts
        for i in range(5):
            response = self.client.post('/api/login/medico', 
                data=json.dumps({
                    'email': 'medico@test.com',
                    'password': 'wrongpassword'
                }),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 401)
        
        # 6th attempt should be locked
        response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'ACCOUNT_LOCKED')
        self.assertIn('retry_after_sec', data)
    
    def test_forgot_password(self):
        """Test forgot password functionality"""
        with patch('src.routes.auth.send_password_reset_email') as mock_send:
            mock_send.return_value = True
            
            response = self.client.post('/api/forgot-password', 
                data=json.dumps({
                    'email': 'medico@test.com'
                }),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['ok'])
            mock_send.assert_called_once()
    
    def test_forgot_password_nonexistent_email(self):
        """Test forgot password with nonexistent email"""
        response = self.client.post('/api/forgot-password', 
            data=json.dumps({
                'email': 'nonexistent@test.com'
            }),
            content_type='application/json'
        )
        
        # Should return success for security reasons
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
    
    def test_reset_password_valid_token(self):
        """Test password reset with valid token"""
        user = User.query.filter_by(email='medico@test.com').first()
        token = user.generate_reset_token()
        
        response = self.client.post('/api/reset-password', 
            data=json.dumps({
                'token': token,
                'new_password': 'newpassword123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        
        # Verify password was changed
        user = User.query.filter_by(email='medico@test.com').first()
        self.assertTrue(user.check_password('newpassword123'))
    
    def test_reset_password_invalid_token(self):
        """Test password reset with invalid token"""
        response = self.client.post('/api/reset-password', 
            data=json.dumps({
                'token': 'invalid-token',
                'new_password': 'newpassword123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'INVALID_TOKEN')
    
    def test_me_endpoint_authenticated(self):
        """Test /api/me endpoint when authenticated"""
        # Login first
        login_response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, 200)
        
        # Test /api/me
        response = self.client.get('/api/me')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'medico@test.com')
    
    def test_me_endpoint_unauthenticated(self):
        """Test /api/me endpoint when not authenticated"""
        response = self.client.get('/api/me')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'NOT_AUTHENTICATED')
    
    def test_logout(self):
        """Test logout functionality"""
        # Login first
        login_response = self.client.post('/api/login/medico', 
            data=json.dumps({
                'email': 'medico@test.com',
                'password': 'password123'
            }),
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, 200)
        
        # Logout
        response = self.client.post('/api/logout')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        
        # Verify user is logged out
        me_response = self.client.get('/api/me')
        self.assertEqual(me_response.status_code, 401)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        rate_limiter = RateLimiter()
        
        # Test within limit
        for i in range(5):
            allowed, remaining, reset_time = rate_limiter.is_allowed('test-key', limit=10, window=60)
            self.assertTrue(allowed)
            self.assertEqual(remaining, 10 - i - 1)
        
        # Test exceeding limit
        for i in range(6):
            rate_limiter.is_allowed('test-key-2', limit=5, window=60)
        
        allowed, remaining, reset_time = rate_limiter.is_allowed('test-key-2', limit=5, window=60)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)

class OAuthTestCase(unittest.TestCase):
    """Test cases for OAuth functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    @patch('src.utils.oauth.google_oauth')
    def test_google_oauth_redirect(self, mock_google):
        """Test Google OAuth redirect"""
        mock_google.get_authorization_url.return_value = MagicMock()
        
        response = self.client.get('/api/login/google?role=medico')
        
        # Should redirect or return authorization URL
        self.assertIn(response.status_code, [200, 302])
        mock_google.get_authorization_url.assert_called_once_with('medico')
    
    def test_oauth_invalid_role(self):
        """Test OAuth with invalid role"""
        response = self.client.get('/api/login/google?role=invalid')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'INVALID_ROLE')

if __name__ == '__main__':
    unittest.main()
