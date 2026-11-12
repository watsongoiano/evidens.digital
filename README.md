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

- Corpo (JSON): dados do paciente. `idade` (18 a 120), `sexo` e `tabagismo` são obrigatórios; medidas e exames
  são opcionais e, quando informados, precisam estar em faixas plausíveis. Nenhum campo recebe valor padrão clínico.
- Triagem de segurança para vacinas: `gestante` e `imunossupressao` (`sim` | `nao` | `desconhecido`) e `lactante`
  (`nao` | `sim_menor_6m` | `sim_6m_ou_mais` | `desconhecido`). Resposta ausente vale como `desconhecido`.
- Entrada inválida: `400` com `codigo: "entrada_invalida"` e a lista `erros` (`campo`, `mensagem`).
- Resposta (JSON):
	- `recommendations`: lista de recomendações
		- Cada item inclui: `titulo`, `descricao`, `categoria`, `prioridade`, `referencia`,
		  `referencias` (lista com `{label,url}`) e `referencia_html` (HTML com links clicáveis)
	- `nao_incluidas`: vacinas retiradas da lista automática pela triagem, com `estado`
	  (`contraindicada` | `precaucao` | `dados_insuficientes`), `motivo` e `referencia`
	- `triagem_vacinas`: as respostas de triagem como foram lidas
	- `risco_cardiovascular`: `{status: "desativado", motivo}`. `prevent_risk` e `risk_classification`
	  continuam na resposta por compatibilidade e são sempre `null`

Observação: Os campos de referência são construídos automaticamente a partir de `referencia` via heurísticas internas, incluindo mapeamentos para USPSTF, ADA, AHA/ACC, KDIGO, SBIm/ANVISA, entre outros.

O cálculo de risco cardiovascular está desativado: as implementações anteriores não correspondiam às equações
PREVENT publicadas. Os perigos conhecidos, os controles e os testes de cada um estão em
[`docs/registro-de-perigos.md`](docs/registro-de-perigos.md).

### POST /gerar-pdf-exames-laboratoriais, /gerar-pdf-exames-imagem e /gerar-pdf-vacinas
Geram minutas em PDF a partir da lista de recomendações retornadas pelo endpoint acima.

- Corpo (JSON): `{ dados_paciente: { nome, idade, sexo, gestante, lactante, imunossupressao, hiv, cd4 }, recomendacoes: [...] }`
- O pedido é validado e limitado (até 80 itens) e o conteúdo é escapado.
- No PDF de vacinas a triagem é conferida de novo: se a lista tiver vacina de vírus vivo atenuado não liberada
  para o paciente, a resposta é `400` com `codigo: "triagem_vacinas"`.
- Resposta: PDF com campo de assinatura e carimbo do médico. Os documentos não têm assinatura digital.

### Endpoints desativados
`/gerar-receita-vacinas`, `/gerar-solicitacao-exames` e `/generate-pdf` respondem `410 Gone`. Os dois primeiros
montavam documentos que declaravam assinatura digital sem que ela existisse; o terceiro não gerava nada.

### Novas recomendações base por idade/sexo (exemplos)
- HPV (Gardasil 9) até 45 anos, maior prioridade até 26 anos.
- Hepatite B (esquema 0-1-6) em não vacinados.
- Pneumocócicas a partir de 50 anos (VPC15/VPC13 e VPP23).

## 🧪 Testes

Os testes ficam em `tests/` e exercitam a aplicação pela entrada de produção (`api/index.py`).

```bash
pip install -r requirements-dev.txt
python -m pytest
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