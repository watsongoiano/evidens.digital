#!/usr/bin/env python3
"""
Test server configuration
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_with_auth import create_app
from src.models.user import User, db

def test_server_config():
    """Test server configuration"""
    app = create_app()
    
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    with app.app_context():
        # Check if users exist
        users = User.query.all()
        print(f"Users found: {len(users)}")
        
        for user in users:
            print(f"  - {user.email} ({user.role})")
            
        # Test specific user
        medico = User.query.filter_by(email='medico@evidens.digital').first()
        if medico:
            print(f"Medico user found: {medico.email}")
            print(f"Password check: {medico.check_password('medico123')}")
        else:
            print("Medico user NOT found!")

if __name__ == "__main__":
    test_server_config()
