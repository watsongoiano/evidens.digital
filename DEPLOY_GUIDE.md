# 🚀 Guia de Deploy - Sistema de Autenticação evidēns

Este guia detalha como fazer o deploy do sistema de autenticação do evidēns.digital no Vercel.

## 📋 Pré-requisitos

- [x] Conta no Vercel
- [x] Vercel CLI instalado (`npm install -g vercel`)
- [x] Repositório Git configurado
- [x] Variáveis de ambiente configuradas

## 🔧 Configuração de Ambiente

### 1. Variáveis de Ambiente no Vercel

Configure as seguintes variáveis no dashboard do Vercel:

```bash
SECRET_KEY=sua-chave-secreta-super-segura-aqui
GOOGLE_CLIENT_ID=seu-google-client-id
GOOGLE_CLIENT_SECRET=seu-google-client-secret
APPLE_CLIENT_ID=seu-apple-client-id (opcional)
APPLE_CLIENT_SECRET=seu-apple-client-secret (opcional)
```

### 2. OAuth Configuration

#### Google OAuth:
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione existente
3. Ative a Google+ API
4. Crie credenciais OAuth 2.0
5. Configure URLs de redirecionamento:
   - `https://seu-dominio.vercel.app/api/auth/google/callback`

#### Apple OAuth (Opcional):
1. Acesse [Apple Developer](https://developer.apple.com/)
2. Configure Sign in with Apple
3. Adicione domínio autorizado

## 🚀 Deploy

### Método 1: Script Automático
```bash
./deploy-auth.sh
```

### Método 2: Manual
```bash
# 1. Copiar configuração
cp vercel-auth.json vercel.json

# 2. Deploy
vercel --prod
```

## 📁 Estrutura de Arquivos

```
evidens.digital/
├── app_with_auth.py          # Aplicação Flask principal
├── login.html                # Página de login
├── dashboard.html            # Dashboard pós-login
├── styles/
│   └── login.css            # Estilos da página de login
├── js/
│   └── auth-simple.js       # JavaScript de autenticação
├── src/
│   ├── models/
│   │   └── user.py          # Modelo de usuário
│   ├── routes/
│   │   └── auth.py          # Rotas de autenticação
│   ├── utils/
│   │   ├── oauth.py         # Utilitários OAuth
│   │   └── rate_limiter.py  # Rate limiting
│   └── database/
│       └── app.db           # Banco de dados SQLite
├── vercel.json              # Configuração do Vercel
├── requirements.txt         # Dependências Python
└── .env.production         # Variáveis de ambiente
```

## 🔍 Testes Pós-Deploy

### 1. Funcionalidades Básicas
- [ ] Página de login carrega corretamente
- [ ] Design responsivo funciona
- [ ] Tabs de papel funcionam (Médico/Administrador)

### 2. Autenticação
- [ ] Login com email/senha funciona
- [ ] Logout funciona
- [ ] Redirecionamento para dashboard
- [ ] Sessões persistem corretamente

### 3. OAuth (se configurado)
- [ ] Login com Google funciona
- [ ] Login com Apple funciona (se configurado)
- [ ] Redirecionamento OAuth correto

### 4. Segurança
- [ ] Rate limiting ativo
- [ ] Senhas hasheadas corretamente
- [ ] Sessões seguras (HTTPS)
- [ ] Logs de auditoria funcionando

## 🛠️ Troubleshooting

### Problema: "Internal Server Error"
**Solução:** Verifique logs no Vercel dashboard e variáveis de ambiente.

### Problema: "Database not found"
**Solução:** Execute `python3 init_auth_database.py` localmente e faça novo deploy.

### Problema: OAuth não funciona
**Solução:** Verifique URLs de callback e credenciais OAuth.

### Problema: JavaScript não carrega
**Solução:** Verifique rotas estáticas no `vercel.json`.

## 📞 Suporte

Para problemas específicos:
1. Verifique logs no Vercel dashboard
2. Teste localmente primeiro
3. Verifique configurações de ambiente
4. Consulte documentação do Vercel

## 🔄 Rollback

Para reverter para versão anterior:
```bash
# Voltar para branch main
git checkout main

# Deploy da versão anterior
vercel --prod
```

## 📈 Monitoramento

- **Logs**: Vercel Dashboard > Functions > Logs
- **Analytics**: Vercel Dashboard > Analytics
- **Performance**: Vercel Dashboard > Speed Insights
- **Uptime**: Configure monitoring externo (ex: UptimeRobot)

---

**✅ Sistema pronto para produção!** 🎉
