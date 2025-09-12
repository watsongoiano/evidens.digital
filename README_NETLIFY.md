# Deploy no Netlify - Sistema de Check-up Médico

Este guia explica como fazer o deploy do Sistema de Check-up Médico no Netlify.

## 📋 Pré-requisitos

- Conta no Netlify
- Código fonte em um repositório Git (GitHub, GitLab, etc.)
- Python 3.11+ (para build local)

## 🚀 Opções de Deploy

### Opção 1: Deploy Frontend Estático (Recomendado para começar)

Esta opção faz deploy apenas do frontend, sem as funcionalidades de API.

#### Passos:

1. **Build local:**
   ```bash
   python build.py
   ```

2. **Upload manual no Netlify:**
   - Acesse [netlify.com](https://netlify.com)
   - Faça login em sua conta
   - Clique em "Add new site" > "Deploy manually"
   - Arraste e solte a pasta `dist` criada pelo build

3. **Deploy automático via Git:**
   - Conecte seu repositório no Netlify
   - Configurações de build:
     - **Build command:** `python build.py`
     - **Publish directory:** `dist`

### Opção 2: Deploy com Netlify Functions (Para APIs)

Se você precisar manter as funcionalidades de API, será necessário migrar para Netlify Functions.

#### Limitações das APIs no Netlify:
- ⚠️ **Banco de dados SQLite:** Não funciona no Netlify (sistema de arquivos efêmero)
- ⚠️ **Sessões:** Precisam ser repensadas
- ⚠️ **Armazenamento de arquivos:** Temporário entre deploys

#### Soluções recomendadas:
- **Banco de dados:** PostgreSQL (Supabase, Neon, etc.)
- **Autenticação:** Netlify Identity ou Auth0
- **Storage:** Cloudinary, AWS S3, etc.

## 🔧 Configurações

### Variáveis de Ambiente no Netlify

1. No painel do Netlify, vá em **Site settings** > **Environment variables**
2. Adicione as seguintes variáveis:

```env
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
API_BASE_URL=https://your-backend-api.com
ANALYTICS_ENABLED=true
```

### Configurações de DNS (Opcional)

Se você tem um domínio personalizado:
1. **Site settings** > **Domain management**
2. **Add custom domain**
3. Configure os DNS conforme instruções

## 📁 Estrutura de Arquivos

```
checkup-medico-branch-24/
├── build.py              # Script de build
├── netlify.toml          # Configuração do Netlify
├── package.json          # Metadados do projeto
├── .env.example          # Exemplo de variáveis de ambiente
├── dist/                 # Pasta de build (criada automaticamente)
├── src/
│   └── static/           # Arquivos estáticos originais
└── README_NETLIFY.md     # Este arquivo
```

## 🔍 Testando Localmente

1. **Build:**
   ```bash
   python build.py
   ```

2. **Serve local:**
   ```bash
   # Opção 1: Python
   cd dist && python -m http.server 8000
   
   # Opção 2: Node.js (se tiver instalado)
   npx serve dist
   ```

3. **Acesse:** http://localhost:8000

## 🐛 Solução de Problemas

### Build falha
- Verifique se o Python está instalado
- Verifique se a pasta `src/static` existe
- Execute `python build.py` localmente primeiro

### Site não carrega
- Verifique se o `publish directory` está configurado como `dist`
- Verifique se o arquivo `index.html` existe em `dist/`

### APIs não funcionam
- Lembre-se: no modo estático, as APIs Flask não funcionarão
- Considere migrar para Netlify Functions ou use um backend separado

### Rotas SPA não funcionam
- O arquivo `_redirects` deve estar em `dist/`
- Verifique as configurações no `netlify.toml`

## 📚 Recursos Adicionais

- [Documentação do Netlify](https://docs.netlify.com/)
- [Netlify Functions](https://docs.netlify.com/functions/overview/)
- [Deploy contínuo](https://docs.netlify.com/site-deploys/create-deploys/)

## 📞 Suporte

Se você encontrar problemas:
1. Verifique os logs de build no painel do Netlify
2. Teste o build localmente primeiro
3. Consulte a documentação oficial do Netlify