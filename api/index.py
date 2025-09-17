"""
Main Flask application entry point for Vercel deployment
"""
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from app_with_auth.py
from app_with_auth import app

# This is the entry point for Vercel
if __name__ == "__main__":
    app.run()
