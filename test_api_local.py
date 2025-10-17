#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste local da API para debug do erro 500
"""

import sys
import os
import json
from io import StringIO
from unittest.mock import Mock

# Adicionar o diretório da API ao path
sys.path.insert(0, '/home/ubuntu/evidens-deploy/api')

def test_api():
    """Testa a API localmente"""
    try:
        # Importar o módulo da API
        import checkup_intelligent_v3
        
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
        
        # Simular requisição HTTP
        class MockRequest:
            def __init__(self, data):
                self.data = json.dumps(data).encode('utf-8')
            
            def makefile(self, mode):
                return StringIO(self.data.decode('utf-8'))
        
        # Simular resposta HTTP
        class MockResponse:
            def __init__(self):
                self.status = None
                self.headers = {}
                self.content = []
            
            def send_response(self, status):
                self.status = status
                print(f"Status: {status}")
            
            def send_header(self, key, value):
                self.headers[key] = value
                print(f"Header: {key} = {value}")
            
            def end_headers(self):
                print("Headers ended")
            
            def wfile_write(self, data):
                self.content.append(data)
                print(f"Response: {data}")
        
        # Criar mock da requisição
        mock_request = MockRequest(test_data)
        mock_response = MockResponse()
        
        # Tentar executar a função handler
        print("=== Testando API localmente ===")
        
        # Simular o handler do Vercel
        try:
            # Executar o código da API diretamente
            result = checkup_intelligent_v3.generate_recommendations(test_data)
            print("✅ API executada com sucesso!")
            print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
            
        except Exception as e:
            print(f"❌ Erro na execução da API: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
