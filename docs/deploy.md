# Deploy

## Aplicação (Vercel)

- O projeto na Vercel está ligado ao repositório. Cada push na branch `main` gera um deploy de produção; cada
  pull request gera um deploy de pré-visualização.
- `vercel.json` encaminha todas as rotas para `api/index.py`, que serve as páginas e a API. Não há etapa de build
  na Vercel: o CSS já vai compilado no repositório (ver **CSS**, abaixo).
- As dependências instaladas são as de `api/requirements.txt`.
- Só mescle um pull request com a verificação **Testes** aprovada (`.github/workflows/tests.yml`).

### Variáveis de ambiente (Vercel → Settings → Environment Variables)

| Variável | Obrigatória | Uso |
|---|---|---|
| `GOTENBERG_URL` | sim | Endereço do serviço de PDF |
| `SECRET_KEY` | sim | Chave do Flask; use um valor aleatório longo |
| `GOTENBERG_API_BASIC_AUTH_USERNAME` | recomendada | Usuário da autenticação básica do serviço de PDF |
| `GOTENBERG_API_BASIC_AUTH_PASSWORD` | recomendada | Senha da autenticação básica do serviço de PDF |

## CSS

As páginas `index.html` e `intelligent-tools.html` usam `static/evidens.css`, gerado com Tailwind a partir de
`static/evidens.src.css` e `tailwind.config.js` (cores, fontes). Depois de mudar classes nas páginas ou os tokens,
recompile e faça commit do resultado:

```bash
npx tailwindcss@3.4.17 -c tailwind.config.js -i static/evidens.src.css -o static/evidens.css --minify
```

A verificação **Testes → css** no GitHub falha se o arquivo publicado não estiver atualizado.

As imagens da página inicial estão hospedadas fora do projeto (UX Pilot). Para não depender desse endereço,
salve-as em `assets/`, inclua-as em `ARQUIVOS_PUBLICOS` (`api/index.py`) e troque os endereços em `index.html`.

## Serviço de PDF (Gotenberg, no Railway)

O serviço fica em outro repositório (`gotenberg-pdf-service`). Enquanto ele aceitar requisições sem
autenticação, qualquer pessoa que conheça o endereço pode usá-lo. Para fechar:

1. No Railway, defina `GOTENBERG_API_BASIC_AUTH_USERNAME` e `GOTENBERG_API_BASIC_AUTH_PASSWORD`.
2. Inicie o Gotenberg com a opção `--api-enable-basic-auth` (confira o nome da opção na documentação da versão em uso).
3. Na Vercel, defina as mesmas duas variáveis, com os mesmos valores.
4. Gere um PDF pela página para confirmar.

Faça os passos 1 a 3 juntos: com a autenticação ligada só de um lado, a geração de PDF para de funcionar.

## Conferência depois de um deploy

1. Abrir `/`, conferir imagens, ícones e o botão **Abrir o check-up**.
1. Abrir `/intelligent-tools`, preencher um paciente e gerar as recomendações.
2. Conferir que a tela não mostra risco cardiovascular e que a triagem de vacinas aparece.
3. Gerar um PDF de exames e um de vacinas.
4. Conferir que `/api/gerar-receita-vacinas` responde 410 e que `/src/routes/checkup_intelligent.py` responde 404.

## O que não é mais usado

- GitHub Pages: o fluxo que publicava a raiz do repositório como site estático foi removido. O site depende da
  API e não funciona como página estática. Se o Pages estiver ativo em Settings → Pages, desative.
- Netlify, `build.py`, pasta `dist/`: removidos.
