#!/usr/bin/env python3
"""
Rollback script for authentication system
This script helps revert the authentication changes if needed
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def print_step(message):
    """Print a step message"""
    print(f"🔄 {message}")

def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")

def print_warning(message):
    """Print a warning message"""
    print(f"⚠️  {message}")

def run_command(command, description):
    """Run a shell command and handle errors"""
    print_step(f"{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to {description.lower()}: {e}")
        if e.stderr:
            print(e.stderr.strip())
        return False

def backup_files():
    """Create backup of current files before rollback"""
    print_step("Creating backup of current authentication files...")
    
    backup_dir = Path("auth_backup")
    backup_dir.mkdir(exist_ok=True)
    
    files_to_backup = [
        "login.html",
        "dashboard.html",
        "styles/login.css",
        "js/auth.js",
        "src/models/user.py",
        "src/routes/auth.py",
        "src/utils/oauth.py",
        "src/utils/rate_limiter.py",
        "init_auth_database.py",
        "tests/test_auth.py",
        "requirements.txt",
        ".env.example"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            try:
                shutil.copy2(file_path, backup_dir / Path(file_path).name)
                print(f"  ✓ Backed up {file_path}")
            except Exception as e:
                print_warning(f"Could not backup {file_path}: {e}")
    
    print_success("Backup completed")

def remove_auth_files():
    """Remove authentication-related files"""
    print_step("Removing authentication files...")
    
    files_to_remove = [
        "login.html",
        "dashboard.html",
        "styles/login.css",
        "js/auth.js",
        "src/utils/oauth.py",
        "src/utils/rate_limiter.py",
        "init_auth_database.py",
        "tests/test_auth.py",
        "rollback_auth.py"
    ]
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed {file_path}")
            except Exception as e:
                print_warning(f"Could not remove {file_path}: {e}")
    
    # Remove empty directories
    dirs_to_check = ["styles", "js", "tests"]
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            try:
                os.rmdir(dir_path)
                print(f"  ✓ Removed empty directory {dir_path}")
            except Exception as e:
                print_warning(f"Could not remove directory {dir_path}: {e}")
    
    print_success("Authentication files removed")

def revert_modified_files():
    """Revert modifications to existing files"""
    print_step("Reverting modifications to existing files...")
    
    # Revert src/models/user.py to basic version
    basic_user_model = '''"""
Basic User model without authentication
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Basic user model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'
'''
    
    try:
        with open("src/models/user.py", "w") as f:
            f.write(basic_user_model)
        print("  ✓ Reverted src/models/user.py")
    except Exception as e:
        print_warning(f"Could not revert src/models/user.py: {e}")
    
    # Remove auth routes from src/routes/auth.py
    try:
        os.remove("src/routes/auth.py")
        print("  ✓ Removed src/routes/auth.py")
    except Exception as e:
        print_warning(f"Could not remove src/routes/auth.py: {e}")
    
    # Revert requirements.txt
    print_step("Reverting requirements.txt...")
    try:
        # Read current requirements
        with open("requirements.txt", "r") as f:
            lines = f.readlines()
        
        # Remove authentication dependencies
        auth_deps = [
            "flask-login", "flask-migrate", "flask-limiter", 
            "bcrypt", "pyjwt", "authlib", "python-dotenv",
            "email-validator", "redis", "celery"
        ]
        
        filtered_lines = []
        skip_section = False
        
        for line in lines:
            line = line.strip()
            if line == "# Authentication dependencies":
                skip_section = True
                continue
            elif skip_section and (line == "" or line.startswith("#")):
                skip_section = False
                continue
            elif skip_section:
                continue
            elif not any(dep in line.lower() for dep in auth_deps):
                filtered_lines.append(line + "\n")
        
        with open("requirements.txt", "w") as f:
            f.writelines(filtered_lines)
        
        print("  ✓ Reverted requirements.txt")
    except Exception as e:
        print_warning(f"Could not revert requirements.txt: {e}")
    
    print_success("File modifications reverted")

def revert_git_changes():
    """Revert git changes if in a git repository"""
    if os.path.exists(".git"):
        print_step("Reverting git changes...")
        
        # Check if we're on the auth branch
        result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
        current_branch = result.stdout.strip()
        
        if current_branch == "feature/auth-system":
            # Switch back to main and delete auth branch
            if run_command("git checkout main", "Switch to main branch"):
                run_command("git branch -D feature/auth-system", "Delete auth branch")
        else:
            # Reset changes on current branch
            run_command("git reset --hard HEAD~10", "Reset recent commits")
            run_command("git clean -fd", "Clean untracked files")
        
        print_success("Git changes reverted")
    else:
        print_warning("Not in a git repository, skipping git revert")

def main():
    """Main rollback function"""
    print("🔄 Authentication System Rollback")
    print("=" * 50)
    
    # Confirm rollback
    response = input("Are you sure you want to rollback the authentication system? (y/N): ")
    if response.lower() != 'y':
        print("Rollback cancelled")
        return
    
    print("\nStarting rollback process...")
    
    # Step 1: Backup current files
    backup_files()
    
    # Step 2: Remove authentication files
    remove_auth_files()
    
    # Step 3: Revert modified files
    revert_modified_files()
    
    # Step 4: Revert git changes (optional)
    git_response = input("\nDo you want to revert git changes? (y/N): ")
    if git_response.lower() == 'y':
        revert_git_changes()
    
    print("\n" + "=" * 50)
    print_success("Rollback completed successfully!")
    print("\nNext steps:")
    print("1. Review the changes")
    print("2. Test the application")
    print("3. If needed, restore from backup in 'auth_backup' directory")
    print("4. Commit the rollback changes")

if __name__ == "__main__":
    main()
