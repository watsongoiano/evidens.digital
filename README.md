# 🩺 Evidens Digital - Sistema de Check-up Médico Inteligente

Sistema completo de check-up médico com interface moderna e análises inteligentes, desenvolvido para ser hospedado em plataformas de deploy estático como Vercel.

## 🌟 Características

- 📋 **Check-up Médico Completo** - Questionário abrangente de saúde
- 🤖 **Análise Inteligente** - Processamento automatizado dos dados
- 📊 **Analytics Integrado** - Dashboard com métricas e insights
- 🎨 **Interface Moderna** - Design responsivo e intuitivo
- ⚡ **Deploy Fácil** - Configurado para Vercel e outros provedores
- 🔒 **Seguro** - Implementação de boas práticas de segurança

## 🏗️ Estrutura do Projeto

```
evidens-digital/
├── 📁 src/                     # Código fonte principal
│   ├── 📄 main.py             # Aplicação Flask principal
│   ├── 📁 models/             # Modelos de dados
│   │   └── 📄 user.py         # Modelo de usuário
│   ├── 📁 routes/             # Rotas da aplicação
│   │   ├── 📄 checkup.py      # Rotas do check-up
│   │   ├── 📄 checkup_intelligent.py # Análises inteligentes
│   │   └── 📄 user.py         # Rotas de usuário
│   ├── 📁 static/             # Arquivos estáticos
│   │   ├── 📄 index.html      # Interface principal
│   │   ├── 📄 analytics.html  # Dashboard de analytics
│   │   └── 📄 favicon.ico     # Ícone do site
│   ├── 📁 utils/              # Utilitários
│   │   └── 📄 analytics.py    # Funções de análise
│   └── 📁 database/           # Configurações de banco
├── 📁 dist/                   # Arquivos buildados (gerado)
├── 📄 build.py               # Script de build
├── 📄 run_server.py          # Servidor de desenvolvimento
├── 📄 vercel.json            # Configuração do Vercel
├── 📄 package.json           # Configuração do projeto
├── 📄 requirements.txt       # Dependências Python
└── 📄 .env.example          # Variáveis de ambiente exemplo

```

## 🚀 Deploy no Vercel

### Deploy Automático (Recomendado)

1. **Fork/Clone** este repositório
2. Acesse [vercel.com](https://vercel.com) e faça login
3. Clique em **"New Project"**
4. Importe do GitHub: `juniorpagedown/evidens.digital`
5. As configurações serão detectadas automaticamente
6. Clique em **"Deploy"**

### Configurações do Vercel

O projeto já inclui `vercel.json` com:
- Build command: `python build.py`
- Output directory: `dist`
- Redirects para SPA
- Otimizações automáticas

## 🛠️ Desenvolvimento Local

### Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

### Instalação

1. **Clone o repositório:**
```bash
git clone https://github.com/juniorpagedown/evidens.digital.git
cd evidens.digital
```

2. **Crie um ambiente virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### Executar Localmente

**Servidor de desenvolvimento:**
```bash
python run_server.py
```

**Ou usando npm:**
```bash
npm run dev
```

Acesse: `http://localhost:5000`

### Build para Produção

```bash
# Gerar arquivos estáticos
python build.py
# ou
npm run build
```

Os arquivos buildados estarão em `dist/`

## 🏥 Funcionalidades

### Check-up Médico
- Questionário completo de saúde
- Validação de dados em tempo real
- Interface intuitiva e responsiva

### Analytics Dashboard
- Métricas de uso em tempo real
- Gráficos interativos
- Relatórios detalhados

### Sistema Inteligente
- Análise automatizada de respostas
- Sugestões baseadas em dados
- Relatórios personalizados

## 🔧 Tecnologias Utilizadas

### Backend
- **Flask** - Framework web Python
- **SQLAlchemy** - ORM para banco de dados
- **OpenAI** - Integração com IA
- **Flask-CORS** - Controle de CORS

### Frontend
- **HTML5/CSS3** - Interface moderna
- **JavaScript** - Interatividade
- **Responsive Design** - Compatibilidade móvel

### Deploy
- **Vercel** - Hospedagem e deploy
- **Python Build System** - Sistema de build customizado

## 📊 Scripts Disponíveis

```bash
# Desenvolvimento
npm run dev          # Iniciar servidor de desenvolvimento
python run_server.py # Iniciar servidor Python

# Build
npm run build        # Build para produção
python build.py      # Build Python

# Vercel
npm run vercel-build # Build específico para Vercel
```

## 🌐 Deploy em Outras Plataformas

### Netlify
1. Configure `netlify.toml` (se necessário)
2. Deploy automático do GitHub

### Heroku
1. Configure `Procfile`
2. Deploy via git push

### GitHub Pages
1. Configure GitHub Actions
2. Deploy automático

## 📝 Variáveis de Ambiente

```env
# Exemplo de .env
OPENAI_API_KEY=sua_chave_aqui
DATABASE_URL=sua_url_do_banco
SECRET_KEY=sua_chave_secreta
ENVIRONMENT=production
```

## 📁 Arquitetura de Arquivos HTML

### Arquivo Canônico
- **`index.html`** (raiz do repositório) - Este é o arquivo HTML canônico servido na aplicação em produção
- Contém a lógica de categorização robusta e mais recente
- É a fonte única da verdade para a interface do usuário

### Arquivos Arquivados
- **`docs/archive/index.html.new`** - Variante histórica arquivada
- **`docs/archive/index.html.original`** - Versão original arquivada

Estes arquivos foram movidos para o diretório de arquivo para evitar divergência e confusão no desenvolvimento. Todos os novos desenvolvimentos e modificações devem ser feitos no arquivo canônico `index.html` na raiz do repositório.

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👨‍💻 Autor

**Junior Pagedown**
- GitHub: [@juniorpagedown](https://github.com/juniorpagedown)
- Website: [evidens.digital](https://evidens.digital)

## 🆘 Suporte

Para suporte, abra uma [issue](https://github.com/juniorpagedown/evidens.digital/issues) ou entre em contato.

---

⭐ **Se este projeto foi útil, considere dar uma estrela!**

🚀 **Deploy agora:** [evidens.digital](https://evidens.digital)