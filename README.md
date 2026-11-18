# 🩺 Evidens Digital

Apoio à decisão para o médico: check-up preventivo do adulto, avaliação pré-operatória de cirurgia não cardíaca e
conferência de pedidos de exame para operadoras de plano de saúde. A partir dos dados informados no formulário, o
sistema sugere exames laboratoriais, exames de imagem e vacinas, mostra a fonte de cada item e gera os pedidos em
PDF, como minuta para assinatura e carimbo ou assinados digitalmente com certificado ICP-Brasil.

> **Estado atual (novembro de 2026).** As saídas são sugestões para avaliação do médico e não constituem
> prescrição. O motor é feito de regras escritas em código, sem modelo de IA. Uma auditoria clínica em 15/11/2026
> conferiu as condutas do motor nas diretrizes vigentes; os perigos conhecidos, o que controla cada um e o que
> segue parcial ou em aberto estão em [`docs/registro-de-perigos.md`](docs/registro-de-perigos.md).

## 🧭 O que o sistema faz

| Área | O que faz | Onde está |
|---|---|---|
| Check-up | Rastreios, exames por comorbidade e medicação, pré-natal e vacinas, com fonte e grau de evidência; aviso quando as diretrizes divergem | `src/routes/checkup_intelligent.py`, `src/utils/condicoes.py`, `rastreio_cancer.py`, `colo_utero.py`, `prenatal.py`, `hiv.py`, `aconselhamento.py` |
| Segurança de vacinas | Triagem de três valores (sim, não, não informado) para vacinas de vírus vivo; conferida de novo ao gerar o PDF | `src/utils/seguranca_vacinas.py` |
| Risco cardiovascular | Equações PREVENT em 10 e 30 anos, com as categorias SBC 2025 e ACC/AHA 2026; não calcula com dado ausente ou fora da faixa | `src/utils/prevent.py` |
| Função renal | TFG (CKD-EPI 2021), categorias G e A e risco de falência renal (KFRE) | `src/utils/funcao_renal.py` |
| Exames já realizados | O exame ainda em dia não é pedido de novo; a data pode ser digitada ou lida do laudo em PDF, por código, sem guardar o arquivo | `src/utils/periodicidade.py`, `laudos.py`, `exames_comuns.py` ([docs](docs/periodicidade.md)) |
| Pré-operatório | Indicação de avaliação cardiológica, escores, exames e conduta de cada medicamento de uso contínuo | `src/utils/preoperatorio.py`, `preop_medicamentos.py` |
| Pedidos em PDF | Exames laboratoriais, exames de imagem e receita de vacinas, sobre o receituário ou o timbrado do médico | `src/utils/pdf_minutas.py`, `receituario.py`, `timbrado.py` |
| Assinatura digital | PAdES com certificado ICP-Brasil em nuvem (hoje, BirdID); sem sessão aberta o PDF sai como minuta | `src/utils/assinatura.py` |
| Plano de saúde e SUS | Guia SP/SADT preenchida (código TUSS) e laudo de APAC (tabela SIGTAP) | `src/utils/tuss.py`, `sigtap.py` ([docs](docs/guia-do-plano.md)) |
| Operadoras | Confere um pedido de exames pelo motor do check-up e diz o que seria liberado, esclarecido ou barrado, sem barrar nada | `src/utils/operadora.py`, `scripts/modo_sombra.py` ([docs](docs/operadoras-modo-sombra.md)) |
| Contas | Cadastro, login, Termos de Uso, painel do administrador, e-mails e painel de uso | `src/routes/auth.py`, `src/utils/contas.py`, `termos.py`, `notificacoes.py`, `comunicados.py`, `uso.py` |
| Inglês | Versão em inglês a partir de um único dicionário | `src/utils/i18n.py`, `static/i18n/en.json` ([docs](docs/versao-em-ingles.md)) |

## 🏗️ Estrutura do projeto

```
evidens.digital/
├── api/
│   ├── index.py                  # Entrada única da aplicação (Flask); é o que a Vercel executa
│   └── requirements.txt          # Dependências de produção
├── src/
│   ├── routes/
│   │   ├── checkup_intelligent.py    # Motor do check-up, pré-operatório, leitura de laudos e PDFs
│   │   └── auth.py                   # Contas, termos, receituário, planos, SUS, assinatura e administração
│   ├── utils/                        # Regras clínicas e serviços (tabela acima)
│   ├── data/                         # Coeficientes do PREVENT, catálogo, códigos TUSS e formulário da APAC
│   └── static/styles/                # Estilos usados por contato e analytics
├── static/
│   ├── evidens.src.css           # Fonte do CSS (Tailwind + componentes)
│   ├── evidens.css               # CSS compilado, publicado (não editar à mão)
│   ├── i18n.js, i18n/en.json     # Versão em inglês
│   └── termos/                   # Termos de Uso em PDF
├── index.html                    # Página inicial
├── intelligent-tools.html        # Formulário do check-up e do pré-operatório, com os resultados
├── operadoras.html               # Conferência de pedidos (conta de administrador)
├── login.html, cadastro.html, conta.html, termos.html, configurar.html   # Área de acesso
├── admin.html, analytics.html    # Administração e painel de uso
├── contact.html                  # Contato
├── scripts/                      # Geradores das listas das páginas, do catálogo e o modo sombra
├── tests/                        # Suíte de testes (pytest)
├── docs/                         # Registro de perigos, deploy e a documentação de cada área
├── tailwind.config.js            # Cores e fontes do design Evidēns
├── vercel.json                   # Encaminha todas as rotas para api/index.py
├── requirements.txt              # Aponta para api/requirements.txt
└── requirements-dev.txt          # Produção + pytest
```

Não há etapa de build no deploy: as páginas são HTML estático servido pela própria aplicação, que publica apenas a
lista de arquivos declarada em `api/index.py` (`ARQUIVOS_PUBLICOS`). O CSS é compilado localmente e versionado;
veja a seção **CSS** em `docs/deploy.md`.

## 🛠️ Desenvolvimento local

Pré-requisito: Python 3.12.

```bash
git clone https://github.com/watsongoiano/evidens.digital.git
cd evidens.digital
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # SECRET_KEY, DATABASE_URL (SQLite local) e SETUP_TOKEN

python api/index.py                # http://localhost:5000
python -m pytest                   # testes
```

O check-up exige login: sem `SECRET_KEY` e `DATABASE_URL` a área de acesso fica desligada. O primeiro
administrador é criado em `/configurar`, com o `SETUP_TOKEN`. Os PDFs são gerados pela própria aplicação; não há
serviço externo a subir.

## 🚀 Deploy

O deploy é feito pela Vercel a cada push na branch `main`; os detalhes e as variáveis de ambiente estão em
[`docs/deploy.md`](docs/deploy.md).

## 🔌 API principal e documentos gerados

Todas as rotas ficam sob `/api`. As do check-up, abaixo, exigem conta aprovada com os Termos de Uso aceitos; as
de `/api/admin` e o painel de uso, conta de administrador. Envio vindo de outro site é recusado (`403`).

### POST /api/checkup-intelligent
Gera recomendações personalizadas.

- Corpo (JSON): dados do paciente. `idade` (18 a 120), `sexo` e `tabagismo` são obrigatórios; medidas e exames
  são opcionais e, quando informados, precisam estar em faixas plausíveis. Nenhum campo recebe valor padrão clínico.
- Triagem de segurança para vacinas: `gestante` e `imunossupressao` (`sim` | `nao` | `desconhecido`) e `lactante`
  (`nao` | `sim_menor_6m` | `sim_6m_ou_mais` | `desconhecido`). Resposta ausente vale como `desconhecido`.
- Entrada inválida: `400` com `codigo: "entrada_invalida"` e a lista `erros` (`campo`, `mensagem`).
- Resposta (JSON), campos principais:
	- `recommendations`: lista de recomendações. Cada item inclui `titulo`, `descricao`, `categoria`,
	  `prioridade`, `referencia`, `referencias` (lista com `{label,url}`) e `referencia_html` (links clicáveis)
	- `nao_incluidas`: o que ficou fora da lista automática, com `estado`, `motivo` e `referencia`: vacinas
	  retidas pela triagem (`contraindicada` | `precaucao` | `dados_insuficientes`), exames ainda em dia e
	  rastreios não recomendados
	- `orientacoes`: avisos e aconselhamento, com os urgentes primeiro; inclui as divergências entre diretrizes
	- `triagem_vacinas`: as respostas de triagem como foram lidas
	- `risco_cardiovascular`: `status` (`calculado` | `incompleto` | `nao_aplicavel` | `fora_da_faixa`). Quando
	  calculado, traz o risco em 10 e 30 anos e as categorias SBC 2025 e ACC/AHA 2026; nos outros casos, o `motivo`
	- `funcao_renal`, `pa_classificacao`, `gestacao`, `adiados_gestacao`, `proximas_gestacao`,
	  `diabetes_a_confirmar`, `drc_a_confirmar`

O PREVENT tem implementação única, no servidor (`src/utils/prevent.py`), conferida contra os vetores do pacote
`preventr`. Não completa campo vazio, vale de 30 a 79 anos e não é calculado na gestação nem com doença
cardiovascular estabelecida. Foi derivado em população dos EUA e não tem validação em coorte brasileira; a
resposta traz essa limitação.

### POST /api/preoperatorio
Avaliação pré-operatória de cirurgia não cardíaca: quando a avaliação cardiológica é indicada, escores, exames e
a conduta perioperatória de cada medicamento de uso contínuo.

### POST /api/laudos/ler
Lê um laudo laboratorial em PDF (campo `arquivo`, até 4 MB) e devolve os exames, as datas de coleta e os
resultados reconhecidos, para o médico conferir em "Exames já realizados". A leitura é feita por código, sem IA;
o arquivo fica só na memória e é descartado.

### POST /api/gerar-pdf-exames-laboratoriais, /api/gerar-pdf-exames-imagem e /api/gerar-pdf-vacinas
Geram os pedidos em PDF a partir da lista de recomendações retornadas pelo endpoint do check-up.

- Corpo (JSON): `{ dados_paciente: { nome, idade, sexo, gestante, lactante, imunossupressao, hiv, cd4 }, recomendacoes: [...] }`
- O pedido é validado e limitado (até 80 itens) e o conteúdo é escapado.
- No PDF de vacinas a triagem é conferida de novo: se a lista tiver vacina de vírus vivo atenuado não liberada
  para o paciente, a resposta é `400` com `codigo: "triagem_vacinas"`.
- Opcionais: `guia` (guia SP/SADT do plano de saúde, nos exames) e `apac` (laudo de APAC, nos exames de imagem),
  para médicos e residentes com o plano ou o vínculo cadastrado na conta.
- Assinatura: sem `assinar: true`, o PDF é uma minuta com campo de assinatura e carimbo e o aviso de que não tem
  assinatura digital. Com `assinar: true` e a sessão aberta no provedor do certificado, o PDF sai assinado
  (PAdES, ICP-Brasil). Pedido de assinatura sem sessão, ou com falha no provedor, é recusado: nunca sai minuta
  no lugar do assinado.

### Endpoints desativados
`/api/gerar-receita-vacinas`, `/api/gerar-solicitacao-exames` e `/api/generate-pdf` respondem `410 Gone`. Os dois
primeiros montavam documentos que declaravam assinatura digital sem que ela existisse; o terceiro não gerava nada.

## 🧪 Testes

Os testes ficam em `tests/` e exercitam a aplicação pela entrada de produção (`api/index.py`).

```bash
pip install -r requirements-dev.txt
python -m pytest
```

- Cada controle de segurança do registro de perigos tem um teste que falha se o controle for removido.
- `tests/test_caracterizacao.py` registra a saída do motor para um conjunto fixo de vinhetas. Ele não afirma que
  as saídas estão corretas; serve para que toda mudança de comportamento apareça no pull request. Para atualizar
  o registro quando a mudança for intencional:
  `ATUALIZAR_CARACTERIZACAO=1 python -m pytest tests/test_caracterizacao.py`
- `tests/test_prevent.py` confere o PREVENT contra os vetores do `preventr`; os arquivos `tests/test_preop_casos_*.py`
  conferem o pré-operatório contra casos transcritos das tabelas das diretrizes.
- `tests/test_estrutura.py` impede que código sem uso volte a se acumular.
- A integração contínua (`.github/workflows/tests.yml`) roda a suíte em todo pull request e confere o CSS compilado.
- Os testes usam SQLite; em produção o banco é Postgres.

## 🔧 Tecnologias

- **Backend:** Python e Flask, em função serverless na Vercel; contas em Postgres (Neon).
- **Frontend:** HTML, CSS (Tailwind compilado) e JavaScript sem framework.
- **PDF:** fpdf2 para gerar, pypdf para ler laudos e timbrados, pyHanko para a assinatura PAdES.

## 📝 Variáveis de ambiente

Veja `.env.example` e [`docs/deploy.md`](docs/deploy.md), que explica cada uma.

| Variável | Uso |
|---|---|
| `DATABASE_URL` (ou `POSTGRES_URL`) | Postgres das contas (a integração Neon da Vercel preenche) |
| `SECRET_KEY` | Assina o cookie de sessão; sem ela a área de acesso fica desligada |
| `SETUP_TOKEN` | Código de instalação do primeiro administrador |
| `RESEND_API_KEY`, `AVISO_CADASTRO_PARA`, `AVISO_CADASTRO_DE`, `EMAIL_CONTATO`, `SITE_URL` | Opcionais: e-mails de cadastro, boas-vindas, aprovação e comunicados |
| `CRON_SECRET` | Autoriza a execução diária dos comunicados (`/api/cron/comunicados`) |
| `BIRDID_CLIENT_ID`, `BIRDID_CLIENT_SECRET`, `BIRDID_URL` | Assinatura digital; sem as duas primeiras, os pedidos saem só como minuta |
| `ASSINATURA_CHAVE` | Opcional: cifra o token da sessão de assinatura no banco; sem ela usa-se a `SECRET_KEY` |

## 🔒 Segurança

Como relatar uma vulnerabilidade e o que o sistema guarda: [`SECURITY.md`](SECURITY.md).

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
- Website: [evidens.life](https://evidens.life)

## 🆘 Suporte

Para suporte, abra uma [issue](https://github.com/watsongoiano/evidens.digital/issues) ou entre em contato.

---

⭐ **Se este projeto foi útil, considere dar uma estrela!**

🚀 **Deploy agora:** [evidens.life](https://evidens.life)