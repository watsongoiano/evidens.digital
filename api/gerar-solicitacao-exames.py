from flask import Flask, request, make_response
from src.utils.cors import sanitize_private_network_header
import json

app = Flask(__name__)
@app.route('/health', methods=['GET'])
def health():
    return make_response('ok', 200)


def _corsify(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return sanitize_private_network_header(resp)


@app.route('/', methods=['POST', 'OPTIONS'])
def generate_exams_document():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        data = request.get_json(silent=True) or {}
        html = data.get('html')
        # For serverless compatibility, we accept payloads with recommendations and patient_data
        # but we render only the HTML (frontend already expects .text()).
        if not html:
            # Minimal passthrough HTML if backend sent structured recommendations
            recs = data.get('recommendations') or []
            lines = []
            for rec in recs:
                titulo = rec.get('titulo') or 'Exame'
                ref_html = rec.get('referencia_html') or ''
                if ref_html:
                    lines.append(f"<li>• {titulo}<br><small>Ref.: {ref_html}</small></li>")
                else:
                    lines.append(f"<li>• {titulo}</li>")
            html = """
            <!DOCTYPE html>
            <html><head><meta charset=\"UTF-8\"><title>Solicitação de Exames</title></head>
            <body><ul>{items}</ul></body></html>
            """.format(items='\n'.join(lines))

        resp = make_response(html, 200)
        resp.mimetype = 'text/html'
        return _corsify(resp)
    except Exception as e:
        err = make_response(f"<html><body>Erro: {str(e)}</body></html>", 500)
        err.mimetype = 'text/html'
        return _corsify(err)

# Vercel handler
def handler(request):
    return app(request.environ, lambda status, headers: None)
