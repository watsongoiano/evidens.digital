#!/usr/bin/env python3
"""
Database initialization script for authentication system
Creates tables and seeds initial admin user
"""

import os
import sys
from datetime import datetime

# Add project root to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask
from src.models.user import db, User, LoginAttempt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    
    # Database configuration
    database_path = os.path.join(BASE_DIR, 'src', 'database', 'app.db')
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    db.init_app(app)
    return app

def init_database():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Check if admin already exists
        admin_email = "admin@evidens.digital"
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if existing_admin:
            print(f"⚠️  Admin user already exists: {admin_email}")
        else:
            # Create default admin user
            admin_user = User(
                email=admin_email,
                role="administrador",
                username="admin"
            )
            admin_user.set_password("admin123")  # Change this in production!
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✅ Default admin user created:")
            print(f"   Email: {admin_email}")
            print(f"   Password: admin123")
            print(f"   ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
        
        # Create sample medical user
        medico_email = "medico@evidens.digital"
        existing_medico = User.query.filter_by(email=medico_email).first()
        
        if existing_medico:
            print(f"⚠️  Sample medical user already exists: {medico_email}")
        else:
            medico_user = User(
                email=medico_email,
                role="medico",
                username="medico_demo"
            )
            medico_user.set_password("medico123")
            
            db.session.add(medico_user)
            db.session.commit()
            
            print(f"✅ Sample medical user created:")
            print(f"   Email: {medico_email}")
            print(f"   Password: medico123")
        
        print(f"\n📊 Database statistics:")
        print(f"   Total users: {User.query.count()}")
        print(f"   Administrators: {User.query.filter_by(role='administrador').count()}")
        print(f"   Medical professionals: {User.query.filter_by(role='medico').count()}")
        print(f"   Login attempts logged: {LoginAttempt.query.count()}")

def reset_database():
    """Reset database (drop and recreate all tables)"""
    print("🗑️  Resetting database...")
    
    app = create_app()
    
    with app.app_context():
        db.drop_all()
        print("✅ All tables dropped")
        
        db.create_all()
        print("✅ Tables recreated")
        
        init_database()

def show_users():
    """Show all users in database"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("📭 No users found in database")
            return
        
        print(f"\n👥 Users in database ({len(users)} total):")
        print("-" * 80)
        print(f"{'ID':<4} {'Email':<30} {'Role':<15} {'Created':<20} {'Last Login':<20}")
        print("-" * 80)
        
        for user in users:
            last_login = user.last_login_at.strftime('%Y-%m-%d %H:%M') if user.last_login_at else 'Never'
            created = user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'Unknown'
            
            print(f"{user.id:<4} {user.email:<30} {user.role:<15} {created:<20} {last_login:<20}")

def show_login_attempts():
    """Show recent login attempts"""
    app = create_app()
    
    with app.app_context():
        attempts = LoginAttempt.query.order_by(LoginAttempt.timestamp.desc()).limit(20).all()
        
        if not attempts:
            print("📭 No login attempts found")
            return
        
        print(f"\n🔐 Recent login attempts ({len(attempts)} shown):")
        print("-" * 100)
        print(f"{'Email':<30} {'Success':<8} {'Reason':<20} {'Provider':<10} {'Timestamp':<20}")
        print("-" * 100)
        
        for attempt in attempts:
            success = "✅ YES" if attempt.success else "❌ NO"
            reason = attempt.failure_reason or "-"
            provider = attempt.oauth_provider or "Password"
            timestamp = attempt.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"{attempt.email:<30} {success:<8} {reason:<20} {provider:<10} {timestamp:<20}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init_auth_database.py [init|reset|users|attempts]")
        print("  init     - Initialize database and create default users")
        print("  reset    - Reset database (WARNING: deletes all data)")
        print("  users    - Show all users")
        print("  attempts - Show recent login attempts")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "init":
        init_database()
    elif command == "reset":
        confirm = input("⚠️  This will delete ALL data. Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("❌ Reset cancelled")
    elif command == "users":
        show_users()
    elif command == "attempts":
        show_login_attempts()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
