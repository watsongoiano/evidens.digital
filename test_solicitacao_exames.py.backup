#!/usr/bin/env python3
"""
Teste para validar a funcionalidade de geração de solicitação de exames em PDF
"""

import json
import requests
import base64
import os
from datetime import datetime

def test_gerar_solicitacao_exames():
    """Testa a geração de solicitação de exames"""
    
    # Dados de teste
    test_data = {
        "medico": {
            "nome": "Dr. João Silva",
            "crm": "12345-GO"
        },
        "patient_data": {
            "nome": "Maria Santos",
            "cpf": "123.456.789-00",
            "sexo": "Feminino",
            "idade": "35"
        },
        "recommendations": [
            {
                "titulo": "Hemograma Completo",
                "categoria": "Exames Laboratoriais",
                "descricao": "Exame de sangue completo"
            },
            {
                "titulo": "Glicemia de Jejum",
                "categoria": "Exames Laboratoriais",
                "descricao": "Dosagem de glicose no sangue"
            },
            {
                "titulo": "Tomografia Computadorizada do Tórax",
                "categoria": "Exames de Imagem",
                "descricao": "Exame de imagem do tórax"
            },
            {
                "titulo": "Ultrassom Abdominal",
                "categoria": "Exames de Imagem",
                "descricao": "Exame de ultrassom do abdômen"
            },
            {
                "titulo": "Colesterol Total e Frações",
                "categoria": "Exames Laboratoriais",
                "descricao": "Dosagem de colesterol"
            }
        ]
    }
    
    print("🧪 Iniciando teste de geração de solicitação de exames...")
    
    try:
        # Importar e testar diretamente a função
        import sys
        sys.path.append('/home/ubuntu/evidens.digital/api')
        
        from gerar_solicitacao_exames import categorizar_exames, gerar_pdf_solicitacao
        
        # Teste 1: Categorização de exames
        print("📋 Testando categorização de exames...")
        exames_lab, exames_img = categorizar_exames(test_data["recommendations"])
        
        print(f"   ✅ Exames laboratoriais encontrados: {len(exames_lab)}")
        for exame in exames_lab:
            print(f"      - {exame}")
            
        print(f"   ✅ Exames de imagem encontrados: {len(exames_img)}")
        for exame in exames_img:
            print(f"      - {exame}")
        
        # Teste 2: Geração de PDF para exames laboratoriais
        if exames_lab:
            print("📄 Testando geração de PDF para exames laboratoriais...")
            pdf_lab = gerar_pdf_solicitacao(
                exames_lab,
                'Laboratorial',
                test_data["medico"],
                test_data["patient_data"]
            )
            
            # Salvar PDF de teste
            with open('/home/ubuntu/evidens.digital/teste_solicitacao_laboratorial.pdf', 'wb') as f:
                f.write(pdf_lab)
            print("   ✅ PDF laboratorial gerado com sucesso!")
        
        # Teste 3: Geração de PDF para exames de imagem
        if exames_img:
            print("📄 Testando geração de PDF para exames de imagem...")
            pdf_img = gerar_pdf_solicitacao(
                exames_img,
                'Imagem',
                test_data["medico"],
                test_data["patient_data"]
            )
            
            # Salvar PDF de teste
            with open('/home/ubuntu/evidens.digital/teste_solicitacao_imagem.pdf', 'wb') as f:
                f.write(pdf_img)
            print("   ✅ PDF de imagem gerado com sucesso!")
        
        print("🎉 Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Testa o endpoint da API"""
    
    print("🌐 Testando endpoint da API...")
    
    # Dados de teste
    test_data = {
        "medico": {
            "nome": "Dr. João Silva",
            "crm": "12345-GO"
        },
        "patient_data": {
            "nome": "Maria Santos",
            "cpf": "123.456.789-00",
            "sexo": "Feminino",
            "idade": "35"
        },
        "recommendations": [
            {
                "titulo": "Hemograma Completo",
                "categoria": "Exames Laboratoriais"
            },
            {
                "titulo": "Tomografia do Tórax",
                "categoria": "Exames de Imagem"
            }
        ]
    }
    
    try:
        # Simular requisição HTTP
        import sys
        sys.path.append('/home/ubuntu/evidens.digital/api')
        
        from gerar_solicitacao_exames import handler
        from http.server import HTTPServer
        import threading
        import time
        
        # Criar servidor de teste
        server = HTTPServer(('localhost', 8001), handler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        time.sleep(1)  # Aguardar servidor iniciar
        
        # Fazer requisição
        response = requests.post(
            'http://localhost:8001',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        server.shutdown()
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ API respondeu com sucesso!")
            print(f"   📊 PDFs gerados: {result.get('total_pdfs', 0)}")
            print(f"   🧪 Exames laboratoriais: {result.get('exames_laboratoriais', 0)}")
            print(f"   🖼️  Exames de imagem: {result.get('exames_imagem', 0)}")
            return True
        else:
            print(f"   ❌ API retornou erro: {response.status_code}")
            print(f"   📝 Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar API: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando testes da funcionalidade de solicitação de exames\n")
    
    # Executar testes
    test1_ok = test_gerar_solicitacao_exames()
    print()
    test2_ok = test_api_endpoint()
    
    print("\n" + "="*60)
    if test1_ok and test2_ok:
        print("🎉 TODOS OS TESTES PASSARAM! Funcionalidade implementada com sucesso.")
    else:
        print("❌ ALGUNS TESTES FALHARAM. Verifique os erros acima.")
    print("="*60)
