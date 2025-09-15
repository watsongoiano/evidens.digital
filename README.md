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

## � API principal e documentos gerados

### POST /checkup-intelligent
Gera recomendações personalizadas.

- Corpo (JSON): dados do paciente (idade, sexo, medidas, histórico)
- Resposta (JSON):
	- `prevent_risk`: objeto com riscos calculados (10 e 30 anos)
	- `risk_classification`: baixo | borderline | intermediario | alto
	- `recommendations`: lista de recomendações
		- Cada item inclui: `titulo`, `descricao`, `categoria`, `prioridade`, `referencia`
		- Novos campos: `referencias` (lista com `{label,url}`) e `referencia_html` (HTML com links clicáveis)

Observação: Os campos de referência são construídos automaticamente a partir de `referencia` via heurísticas internas, incluindo mapeamentos para USPSTF, ADA, AHA/ACC, KDIGO, SBIm/ANVISA, entre outros.

### POST /gerar-solicitacao-exames e /gerar-receita-vacinas
Geram documentos HTML imprimíveis a partir da lista de recomendações retornadas pelo endpoint acima.

- Corpo (JSON): `{ recommendations: [...], patient_data: { nome, sexo, ... } }`
- Negociação de conteúdo:
	- Por padrão, retorna HTML se o cabeçalho `Accept` contiver `text/html`.
	- Retorna JSON se o `Accept` for `application/json` ou se `?format=json`.
	- Parâmetro `?format=html|json` (ou `response_type`) tem precedência sobre o cabeçalho.
- Em caso de erro, a resposta acompanha o mesmo formato (HTML com página amigável ou JSON com `{error: ...}`).

### Novas recomendações base por idade/sexo (exemplos)
- HPV (Gardasil 9) até 45 anos, maior prioridade até 26 anos.
- Hepatite B (esquema 0-1-6) em não vacinados.
- Pneumocócicas a partir de 50 anos (VPC15/VPC13 e VPP23).

## 🧪 Testes rápidos (smoke)

Um script simples em `scripts/test_smoke.py` valida:
- Inclusão de HPV, Hepatite B e Pneumococo nas recomendações quando aplicável
- Presença de `referencia_html` em pelo menos uma recomendação
- Negociação de conteúdo dos endpoints de documentos (HTML vs JSON)

Como executar localmente:

```bash
python scripts/test_smoke.py
```

## �🔧 Tecnologias Utilizadas

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