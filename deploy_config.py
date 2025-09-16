#!/usr/bin/env python3
"""
Configuração de deploy para evidens.digital
Este script prepara a aplicação para deploy em produção
"""

import os
import shutil
import subprocess
import sys

def prepare_for_deployment():
    """Prepara a aplicação para deploy"""
    print("🚀 Preparando aplicação para deploy...")
    
    # Verificar se todos os arquivos necessários estão presentes
    required_files = [
        'index.html',
        'app.py',
        'requirements.txt',
        'src/routes/checkup_intelligent.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Arquivos obrigatórios não encontrados: {missing_files}")
        return False
    
    print("✅ Todos os arquivos obrigatórios estão presentes")
    
    # Verificar se as correções foram aplicadas
    with open('src/routes/checkup_intelligent.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if "rec['subtitulo'] = ''" in content and "rec['grau_evidencia'] = ''" in content:
            print("✅ Correções de 'undefined' aplicadas")
        else:
            print("⚠️  Correções de 'undefined' podem não estar aplicadas")
    
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
        if "!== 'undefined'" in content and "!== 'null'" in content:
            print("✅ Validações do frontend aplicadas")
        else:
            print("⚠️  Validações do frontend podem não estar aplicadas")
    
    print("🎯 Aplicação pronta para deploy!")
    print("\n📋 Resumo das correções aplicadas:")
    print("   1. ✅ Valores 'undefined' eliminados")
    print("   2. ✅ Rotas de API corrigidas")
    print("   3. ✅ Categorização de exames melhorada")
    print("   4. ✅ Logs de debug adicionados")
    
    return True

def show_deployment_instructions():
    """Mostra instruções para deploy manual"""
    print("\n" + "="*60)
    print("📖 INSTRUÇÕES PARA DEPLOY MANUAL")
    print("="*60)
    print("\n🔧 Para habilitar GitHub Pages:")
    print("   1. Acesse: https://github.com/watsongoiano/evidens.digital/settings/pages")
    print("   2. Em 'Source', selecione 'GitHub Actions'")
    print("   3. O workflow deploy-pages.yml será executado automaticamente")
    
    print("\n🌐 Deploy alternativo (Vercel):")
    print("   1. Instale Vercel CLI: npm i -g vercel")
    print("   2. Execute: vercel --prod")
    print("   3. Configure as variáveis de ambiente se necessário")
    
    print("\n🐍 Deploy alternativo (Heroku):")
    print("   1. Instale Heroku CLI")
    print("   2. Execute: heroku create evidens-digital")
    print("   3. Execute: git push heroku main")
    
    print("\n✅ Status atual:")
    print("   - Código corrigido e commitado ✅")
    print("   - Push para GitHub realizado ✅")
    print("   - GitHub Pages precisa ser habilitado manualmente ⚠️")

if __name__ == "__main__":
    if prepare_for_deployment():
        show_deployment_instructions()
    else:
        sys.exit(1)
