# 🩺 Evidens Digital

Apoio à decisão para check-up preventivo do adulto, voltado ao médico. A partir dos dados informados no
formulário, o sistema sugere exames laboratoriais, exames de imagem e vacinas, mostra a fonte de cada item e
gera minutas em PDF para impressão, assinatura e carimbo.

> **Estado atual (novembro de 2026): versão em contenção.** As saídas são sugestões para avaliação do médico e
> não constituem prescrição. O cálculo de risco cardiovascular está desativado e as regras de rastreio ainda
> não foram revistas contra as fontes primárias. Os perigos conhecidos, o que controla cada um e o que segue em
> aberto estão em [`docs/registro-de-perigos.md`](docs/registro-de-perigos.md).

## 🏗️ Estrutura do projeto

```
evidens.digital/
├── api/
│   ├── index.py                  # Entrada única da aplicação (Flask); é o que a Vercel executa
│   └── requirements.txt          # Dependências de produção
├── src/
│   ├── routes/
│   │   └── checkup_intelligent.py    # Motor de recomendações e endpoints de PDF
│   ├── utils/
│   │   ├── validacao.py              # Validação e normalização da entrada
│   │   ├── seguranca_vacinas.py      # Triagem de segurança das vacinas
│   │   ├── pdf_minutas.py            # Minutas em PDF (fpdf2, fontes em assets/fonts)
│   │   ├── reference_links.py        # Links das fontes citadas
│   │   └── analytics.py              # Contadores de uso
│   └── static/styles/                # Estilos usados por contato e analytics
├── static/
│   ├── evidens.src.css           # Fonte do CSS (Tailwind + componentes)
│   └── evidens.css               # CSS compilado, publicado (não editar à mão)
├── login.html, cadastro.html, conta.html, admin.html, configurar.html   # Área de acesso
├── tailwind.config.js            # Cores e fontes do design Evidēns
├── index.html                    # Página inicial
├── intelligent-tools.html        # Formulário do check-up e resultados
├── contact.html, analytics.html  # Contato e painel de uso
├── tests/                        # Suíte de testes (pytest)
├── docs/                         # Registro de perigos e deploy
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

python api/index.py                # http://localhost:5000
python -m pytest                   # testes
```

Os PDFs são gerados pela própria aplicação; não há serviço externo a subir.

## 🚀 Deploy

O deploy é feito pela Vercel a cada push na branch `main`; os detalhes e as variáveis de ambiente estão em
[`docs/deploy.md`](docs/deploy.md).

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
- `tests/test_estrutura.py` impede que código sem uso volte a se acumular.
- A integração contínua (`.github/workflows/tests.yml`) roda a suíte em todo pull request.

## 🔧 Tecnologias

- **Backend:** Python e Flask, em função serverless na Vercel; contas em Postgres (Neon).
- **Frontend:** HTML, CSS e JavaScript sem framework.
- **PDF:** fpdf2, dentro da própria função.

## 📝 Variáveis de ambiente

Veja `.env.example`. As que a aplicação usa em produção:

| Variável | Uso |
|---|---|
| `DATABASE_URL` | Postgres das contas (a integração Neon da Vercel preenche) |
| `SECRET_KEY` | Assina o cookie de sessão |
| `SETUP_TOKEN` | Código de instalação do primeiro administrador |
| `RESEND_API_KEY` | Opcional: liga o aviso por e-mail ao administrador a cada novo pedido de conta (docs/deploy.md) |

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