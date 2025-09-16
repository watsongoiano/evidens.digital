#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste específico da classe handler da API
"""

import sys
import os
import json
from io import BytesIO, StringIO
from unittest.mock import Mock

# Adicionar o diretório da API ao path
sys.path.insert(0, '/home/ubuntu/evidens-deploy/api')

def test_handler():
    """Testa a classe handler da API"""
    try:
        # Importar o módulo da API
        from checkup_intelligent_v3 import handler
        
        # Dados de teste simples
        test_data = {
            'idade': 45,
            'sexo': 'feminino',
            'peso': 70,
            'altura': 165,
            'pressao_sistolica': 130,
            'colesterol_total': 200,
            'hdl_colesterol': 50,
            'creatinina': 1.0,
            'comorbidades': [],
            'medicacoes_especificas': [],
            'tabagismo': 'nunca_fumou'
        }
        
        # Simular requisição HTTP POST
        post_data = json.dumps(test_data).encode('utf-8')
        
        # Mock da requisição
        class MockRequest:
            def __init__(self, data):
                self.rfile = BytesIO(data)
                self.wfile = BytesIO()
                self.headers = {'Content-Length': str(len(data))}
                self.path = '/api/checkup_intelligent_v3'
                self.command = 'POST'
                self.client_address = ('127.0.0.1', 12345)
                self.server = Mock()
                
            def send_response(self, code):
                print(f"Response code: {code}")
                
            def send_header(self, key, value):
                print(f"Header: {key} = {value}")
                
            def end_headers(self):
                print("Headers ended")
        
        # Criar instância do handler
        mock_request = MockRequest(post_data)
        api_handler = handler(mock_request, mock_request.client_address, mock_request.server)
        
        print("=== Testando Handler da API ===")
        
        # Executar método POST
        try:
            api_handler.do_POST()
            
            # Ler resposta
            response_data = mock_request.wfile.getvalue()
            if response_data:
                response_text = response_data.decode('utf-8')
                print("✅ Handler executado com sucesso!")
                print(f"Resposta: {response_text}")
                
                # Tentar parsear JSON
                try:
                    response_json = json.loads(response_text)
                    print(f"JSON válido com {len(response_json.get('recommendations', []))} recomendações")
                except json.JSONDecodeError:
                    print("⚠️ Resposta não é JSON válido")
            else:
                print("⚠️ Nenhuma resposta recebida")
                
            return True
            
        except Exception as e:
            print(f"❌ Erro na execução do handler: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_handler()
    sys.exit(0 if success else 1)
