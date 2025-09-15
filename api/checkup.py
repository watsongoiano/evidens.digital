from flask import Flask, request, jsonify, make_response
from src.utils.cors import sanitize_private_network_header

app = Flask(__name__)


def _corsify(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return sanitize_private_network_header(resp)


@app.route('/checkup', methods=['POST', 'OPTIONS'])
def handle_checkup():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        data = request.get_json(silent=True) or {}
        return _corsify(jsonify({"ok": True, "data": data})), 200
    except Exception as e:
        return _corsify(jsonify({"ok": False, "error": str(e)})), 500
