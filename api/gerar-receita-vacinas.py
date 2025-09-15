from flask import Flask, request, make_response
import json

app = Flask(__name__)
@app.route('/health', methods=['GET'])
def health():
    return make_response('ok', 200)


def _corsify(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp


@app.route('/', methods=['POST', 'OPTIONS'])
def generate_vaccine_prescription():
    if request.method == 'OPTIONS':
        return _corsify(make_response('', 204))

    try:
        data = request.get_json(silent=True) or {}
        html = data.get('html')
        if not html:
            recs = data.get('recommendations') or []
            lines = []
            for rec in recs:
                if (rec.get('categoria') or '').lower() != 'vacina':
                    continue
                titulo = rec.get('titulo') or 'Vacina'
                ref_html = rec.get('referencia_html') or ''
                if ref_html:
                    lines.append(f"<div><strong>{titulo}</strong><br><small>Ref.: {ref_html}</small></div>")
                else:
                    lines.append(f"<div><strong>{titulo}</strong></div>")
            html = """
            <!DOCTYPE html>
            <html><head><meta charset=\"UTF-8\"><title>Receita de Vacinas</title></head>
            <body>{items}</body></html>
            """.format(items='\n'.join(lines))

        resp = make_response(html, 200)
        resp.mimetype = 'text/html'
        return _corsify(resp)
    except Exception as e:
        err = make_response(f"<html><body>Erro: {str(e)}</body></html>", 500)
        err.mimetype = 'text/html'
        return _corsify(err)
