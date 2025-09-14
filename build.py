#!/usr/bin/env python3
"""
Build script para preparar os arquivos estáticos para deploy
"""

import os
import shutil
import json
from pathlib import Path

# Resolve all paths relative to the script directory (repo root)
SCRIPT_DIR = Path(__file__).parent.resolve()

def create_build_directory():
    """Cria o diretório de build"""
    build_dir = SCRIPT_DIR / "dist"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    return build_dir

def copy_static_files(build_dir):
    """Copia arquivos estáticos para o diretório de build"""
    static_dir = SCRIPT_DIR / "src/static"
    
    if not static_dir.exists():
        print("❌ Diretório src/static não encontrado")
        return False
    
    # Copia todos os arquivos estáticos
    for file_path in static_dir.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(static_dir)
            dest_path = build_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"✅ Copiado: {relative_path}")
    
    return True

def create_redirects(build_dir):
    """Cria arquivo _redirects para SPA routing"""
    redirects_content = """# SPA redirects
/*    /index.html   200
"""
    
    with open(build_dir / "_redirects", "w") as f:
        f.write(redirects_content)
    print("✅ Arquivo _redirects criado")

def create_headers(build_dir):
    """Cria arquivo _headers para configurações de cache"""
    headers_content = """# Cache static assets for 1 year
*.css
  Cache-Control: public, max-age=31536000
*.js
  Cache-Control: public, max-age=31536000
*.ico
  Cache-Control: public, max-age=31536000

# Cache HTML for 1 hour
*.html
  Cache-Control: public, max-age=3600
"""
    
    with open(build_dir / "_headers", "w") as f:
        f.write(headers_content)
    print("✅ Arquivo _headers criado")

def update_html_for_static(build_dir):
    """Atualiza referências no HTML para funcionamento estático"""
    index_path = build_dir / "index.html"
    
    if not index_path.exists():
        print("❌ index.html não encontrado")
        return
    
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Atualiza referências para funcionar como site estático
    # Se houver chamadas para /api/, você precisará configurar um backend alternativo
    content = content.replace('href="/favicon.ico"', 'href="./favicon.ico"')
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ HTML atualizado para funcionamento estático")

def main():
    """Função principal do build"""
    print("🚀 Iniciando build para deploy...")
    
    build_dir = create_build_directory()
    print(f"✅ Diretório de build criado: {build_dir}")
    
    if not copy_static_files(build_dir):
        print("❌ Falha ao copiar arquivos estáticos")
        return False
    
    create_redirects(build_dir)
    create_headers(build_dir)
    update_html_for_static(build_dir)
    
    print(f"\n✅ Build concluído!")
    print(f"📁 Arquivos prontos em: {build_dir.absolute()}")
    print(f"📋 Para fazer deploy:")
    print(f"   1. Faça upload da pasta '{build_dir}' no provedor de hosting")
    print(f"   2. Ou configure deploy automático do GitHub")
    
    return True

if __name__ == "__main__":
    main()