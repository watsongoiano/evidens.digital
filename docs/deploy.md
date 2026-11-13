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
| `SECRET_KEY` | sim | Chave do Flask; use um valor aleatório longo |

## Área de acesso (contas)

O check-up inteiro exige login. As contas ficam num banco Postgres; dados de pacientes continuam não sendo gravados.

Variáveis de ambiente na Vercel:

| Variável | Para quê |
| --- | --- |
| `DATABASE_URL` (ou `POSTGRES_URL`) | Conexão com o Postgres. A integração **Neon** da Vercel (Storage → Create Database → Neon) cria e preenche sozinha. |
| `SECRET_KEY` | Assina o cookie de sessão. Valor longo e aleatório. Sem ela (ou com o valor padrão), a área de acesso fica desligada. |
| `SETUP_TOKEN` | Código de instalação, usado uma única vez em `/configurar` para criar o administrador. Pode ser apagado depois. |
| `RESEND_API_KEY` | Opcional. Liga o aviso por e-mail ao administrador a cada novo pedido de conta (ver abaixo). |
| `AVISO_CADASTRO_PARA` | Opcional. Destinatários do aviso, separados por vírgula. Padrão: e-mail dos administradores. |
| `AVISO_CADASTRO_DE` | Opcional. Remetente dos e-mails. Padrão: `Evidēns <onboarding@resend.dev>`. Com um remetente do domínio verificado, liga também as boas-vindas. |
| `EMAIL_RESPOSTA` | Opcional. Endereço de resposta (reply-to) do e-mail de boas-vindas. |
| `SITE_URL` | Opcional. Endereço usado no link do e-mail. Padrão: `https://evidens.life`. |

Sem banco ou sem chave, a home continua no ar e o check-up responde 503 ("área de acesso ainda não configurada").

Fluxo:

1. O administrador é criado em `/configurar`, com o código de instalação. A página deixa de funcionar assim que existe um administrador.
2. Médicos, residentes e estudantes se cadastram em `/cadastro` e ficam **pendentes**.
3. O administrador confere o registro e aprova (ou recusa) em `/admin`. Bloquear derruba na hora as sessões da pessoa.
4. Não há envio de e-mail: quem esquece a senha pede uma **senha temporária**, gerada pelo administrador em `/admin` e mostrada uma única vez.

Proteções: senha com hash (scrypt), mínimo de 10 caracteres; bloqueio de 15 minutos após 5 senhas erradas para o mesmo e-mail; cookie de sessão `HttpOnly`, `Secure` e `SameSite=Lax`, válido por 12 horas; envios vindos de outro site são recusados; trocar a senha encerra as outras sessões.

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

## PDFs

As minutas (pedidos de exames e receita de vacinas) são geradas dentro da própria função, com a biblioteca
`fpdf2` e as fontes DejaVu em `assets/fonts`. Não há serviço externo nem variável de ambiente para isso.
O serviço Gotenberg no Railway, usado antes, pode ser desligado.

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

## Aviso por e-mail de novo cadastro

A cada pedido de abertura de conta, o administrador recebe um e-mail com nome, perfil, registro e e-mail de quem pediu, e o link de `/admin`. O envio usa a [Resend](https://resend.com) e fica desligado enquanto `RESEND_API_KEY` não existir.

1. Crie uma conta na Resend **com o mesmo e-mail que deve receber os avisos** (o do administrador).
2. Em *API Keys*, crie uma chave com permissão de envio.
3. Na Vercel, em *Settings → Environment Variables*, cadastre `RESEND_API_KEY` com essa chave (ambiente *Production*) e refaça o deploy.
4. Em `/admin`, a seção "Aviso por e-mail" mostra se está ligado e tem o botão "Enviar e-mail de teste".

Com o remetente padrão (`onboarding@resend.dev`), a Resend só entrega ao e-mail do dono da conta Resend. Para avisar outros endereços, verifique o domínio `evidens.life` na Resend (registros DNS na GoDaddy) e defina `AVISO_CADASTRO_DE`, por exemplo `Evidēns <avisos@evidens.life>`.

Uma falha no envio não impede o cadastro: fica registrada no log da função e o pedido continua aparecendo em `/admin`.

## E-mail de boas-vindas

Quem pede a conta recebe um e-mail dizendo o que acontece agora (aprovação pelo responsável técnico), que a ferramenta está em fase de desenvolvimento e que feedbacks são bem-vindos, com o link da página de contato.

O remetente padrão da Resend só entrega ao dono da conta Resend, então as boas-vindas ficam desligadas até existir um remetente do próprio domínio:

1. Na Resend, em *Domains*, adicione `evidens.life`. A Resend mostra os registros DNS a criar (TXT de DKIM e SPF e um MX do subdomínio de envio).
2. Na GoDaddy, em *DNS* do domínio, crie esses registros exatamente como mostrados e aguarde a Resend marcar o domínio como verificado.
3. Na Vercel, cadastre `AVISO_CADASTRO_DE`, por exemplo `Evidēns <contato@evidens.life>` (Production), e refaça o deploy.
4. Em `/admin`, use "Enviar boas-vindas de teste para mim".

Com isso o aviso ao administrador também passa a sair do domínio e pode ir a qualquer endereço. As boas-vindas respeitam o mesmo limite de 10 e-mails por hora e só vão para contas recém-criadas (um e-mail já cadastrado não recebe nada).
