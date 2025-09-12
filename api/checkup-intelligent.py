from flask import Flask, request, jsonify
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.routes.checkup_intelligent import checkup_intelligent_bp

app = Flask(__name__)
app.register_blueprint(checkup_intelligent_bp)

def handler(event, context):
    """Vercel serverless function handler"""
    return app(event, context)

# For development
if __name__ == "__main__":
    app.run(debug=True)