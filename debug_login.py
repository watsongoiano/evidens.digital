#!/usr/bin/env python3
"""
Debug script to test login functionality
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.user import User, db
from app_with_auth import create_app

def test_user_password():
    """Test user password verification"""
    app = create_app()
    
    with app.app_context():
        # Get the medical user
        user = User.query.filter_by(email='medico@evidens.digital').first()
        
        if not user:
            print("❌ User not found!")
            return False
        
        print(f"✅ User found: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Username: {user.username}")
        print(f"   Password hash: {user.password_hash[:50]}...")
        
        # Test password verification
        test_passwords = ['medico123', 'wrong_password', 'admin123']
        
        for password in test_passwords:
            result = user.check_password(password)
            print(f"   Password '{password}': {'✅ VALID' if result else '❌ INVALID'}")
        
        return True

def test_login_api():
    """Test login API directly"""
    app = create_app()
    
    with app.test_client() as client:
        # Test login request
        response = client.post('/api/login/medico', 
            json={
                'email': 'medico@evidens.digital',
                'password': 'medico123'
            },
            content_type='application/json'
        )
        
        print(f"\n🔍 API Test Results:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.get_json()}")
        
        return response.status_code == 200

if __name__ == "__main__":
    print("🔍 Debug Login Functionality")
    print("=" * 50)
    
    print("\n1. Testing user password verification...")
    test_user_password()
    
    print("\n2. Testing login API...")
    test_login_api()
    
    print("\n" + "=" * 50)
    print("Debug completed!")
