from flask import Flask, jsonify
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.analytics import analytics

app = Flask(__name__)

@app.route('/api/analytics/stats')
def get_analytics_stats():
    """Endpoint para visualizar estatísticas de acesso"""
    return jsonify(analytics.get_summary())

@app.route('/api/analytics/full')
def get_full_analytics():
    """Endpoint para visualizar estatísticas completas (admin)"""
    return jsonify(analytics.get_stats())

def handler(event, context):
    """Vercel serverless function handler"""
    return app(event, context)

# For development
if __name__ == "__main__":
    app.run(debug=True)