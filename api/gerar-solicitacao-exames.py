from flask import Flask, request, make_response
import json

app = Flask(__name__)

def _corsify(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp

@app.route('/', methods=['POST', 'OPTIONS'])
def generate_exams_document():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        data = request.get_json(silent=True) or {}
        html = data.get('html')
        
        if not html:
            recs = data.get('recommendations') or []
            lines = []
            for rec in recs:
                if rec.get('categoria', '').lower() == 'exame':
                    titulo = rec.get('titulo') or 'Exame'
                    ref_html = rec.get('referencia_html') or ''
                    if ref_html:
                        lines.append(f"<li>• {titulo}<br><small>Ref.: {ref_html}</small></li>")
                    else:
                        lines.append(f"<li>• {titulo}</li>")
            
            html = f"""
            <!DOCTYPE html>
            <html><head><meta charset="UTF-8"><title>Solicitação de Exames</title></head>
            <body><h2>Solicitação de Exames</h2><ul>{''.join(lines)}</ul></body></html>
            """

        resp = make_response(html, 200)
        resp.mimetype = 'text/html'
        return _corsify(resp)
    except Exception as e:
        err = make_response(f"<html><body>Erro: {str(e)}</body></html>", 500)
        err.mimetype = 'text/html'
        return _corsify(err)

# For Vercel
def handler(request):
    return app(request.environ, lambda status, headers: None)
