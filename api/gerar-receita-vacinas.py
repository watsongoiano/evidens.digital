from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            # Ler dados do request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
            
            html = data.get('html')
            
            if not html:
                recs = data.get('recommendations') or []
                lines = []
                for rec in recs:
                    if (rec.get('categoria') or '').lower() == 'vacina':
                        titulo = rec.get('titulo') or 'Vacina'
                        ref_html = rec.get('referencia_html') or ''
                        if ref_html:
                            lines.append(f"<div><strong>{titulo}</strong><br><small>Ref.: {ref_html}</small></div>")
                        else:
                            lines.append(f"<div><strong>{titulo}</strong></div>")
                
                html = f"""
                <!DOCTYPE html>
                <html><head><meta charset="UTF-8"><title>Receita de Vacinas</title></head>
                <body><h2>Receita de Vacinas</h2>{''.join(lines)}</body></html>
                """

            # Enviar resposta
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            # Enviar erro
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_html = f"<html><body>Erro: {str(e)}</body></html>"
            self.wfile.write(error_html.encode('utf-8'))
