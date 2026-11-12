"""
Serviço de geração de PDFs usando Gotenberg (Chromium).

Os templates das minutas ficam em `pdf_service_gotenberg_simple.py`.
"""

import os
import urllib.request
import urllib.error

# URL do microserviço Gotenberg no Railway
# Será definida via variável de ambiente
GOTENBERG_URL = os.getenv('GOTENBERG_URL', 'http://localhost:3000')


def gerar_pdf_via_gotenberg(html_content):
    """Gera PDF usando Gotenberg (Chromium)"""
    
    try:
        import base64
        import io
        import secrets

        # Endpoint do Gotenberg para conversão HTML -> PDF
        url = f"{GOTENBERG_URL}/forms/chromium/convert/html"

        # Delimitador aleatório por requisição: um delimitador fixo permitiria que um
        # texto contendo o próprio delimitador encerrasse a parte e acrescentasse campos.
        boundary = '----EvidensFormBoundary' + secrets.token_hex(16)

        # Construir corpo da requisição multipart/form-data
        body = io.BytesIO()
        body.write(f'--{boundary}\r\n'.encode())
        body.write(b'Content-Disposition: form-data; name="files"; filename="index.html"\r\n')
        body.write(b'Content-Type: text/html\r\n\r\n')
        body.write(html_content.encode('utf-8'))
        body.write(f'\r\n--{boundary}--\r\n'.encode())

        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }

        # Autenticação básica, quando configurada. Usa os mesmos nomes de variável que o
        # Gotenberg lê no servidor (--api-enable-basic-auth), para configurar igual nos dois lados.
        usuario = os.getenv('GOTENBERG_API_BASIC_AUTH_USERNAME')
        senha = os.getenv('GOTENBERG_API_BASIC_AUTH_PASSWORD')
        if usuario and senha:
            credencial = base64.b64encode(f'{usuario}:{senha}'.encode()).decode()
            headers['Authorization'] = f'Basic {credencial}'

        # Criar requisição
        req = urllib.request.Request(
            url,
            data=body.getvalue(),
            headers=headers,
            method='POST'
        )
        
        # Fazer requisição
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
        
    except urllib.error.HTTPError as e:
        raise Exception(f"Erro HTTP ao gerar PDF via Gotenberg: {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Erro de conexão ao gerar PDF via Gotenberg: {str(e.reason)}")
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF via Gotenberg: {str(e)}")


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    """Gera PDF de solicitação de exames laboratoriais (formato simplificado)"""
    from .pdf_service_gotenberg_simple import gerar_html_exames_simples
    html = gerar_html_exames_simples(dados_paciente, exames, tipo_exame="LABORATORIAIS")
    return gerar_pdf_via_gotenberg(html)


def gerar_pdf_exames_imagem(dados_paciente, exames):
    """Gera PDF de solicitação de exames de imagem (formato simplificado)"""
    from .pdf_service_gotenberg_simple import gerar_html_exames_simples
    html = gerar_html_exames_simples(dados_paciente, exames, tipo_exame="IMAGEM")
    return gerar_pdf_via_gotenberg(html)


def gerar_pdf_vacinas(dados_paciente, vacinas):
    """Gera PDF de prescrição de vacinas (formato Receita Simples)"""
    from .pdf_service_gotenberg_simple import gerar_html_prescricao_vacinas_simples
    html = gerar_html_prescricao_vacinas_simples(dados_paciente, vacinas)
    return gerar_pdf_via_gotenberg(html)

