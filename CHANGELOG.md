
# Patches applied (2025-08-26T12:12:23)

## 2026-11-19 — Cadastro de pacientes: correções da revisão de segurança

Ainda fase 1 (só o servidor, só o administrador, sem tela). Contrato atualizado em `docs/pacientes.md`.

- **Chave própria**: a cifra e os índices passam a derivar de `PACIENTES_CHAVE`, variável de ambiente só do
  cadastro, e não mais da `SECRET_KEY`. Sem ela, com menos de 32 caracteres ou com o mesmo valor da chave de sessão,
  o cadastro responde 503 (`sem_chave`); a `SECRET_KEY` nunca entra no lugar. **É preciso criar a variável na
  hospedagem**; registros gravados antes desta versão não abrem mais (só havia dados de teste).
- **Edição simultânea**: em Postgres a edição trava a linha (`SELECT … FOR UPDATE`); nos dois bancos confere-se
  quantas linhas o `UPDATE` alcançou. Paciente excluído no meio da edição responde 404, sem "salvo" e sem "editar"
  na trilha; registro alterado no meio responde 409 (`conflito`).
- **API**: todo pedido precisa do cabeçalho `X-Requested-With: evidens` (403 sem ele); `GET /api/pacientes?busca=`
  deixou de existir (400), a busca fica só em `POST /api/pacientes/buscar`; teto de 5.000 pacientes por conta
  (409, `limite`).
- **Validação**: o tamanho do e-mail é conferido antes da expressão regular (também em `/api/auth/cadastro`);
  e-mail com caractere de controle ou substituto solto é recusado com 400 (dava 500); a ficha recusa as chaves
  `__proto__`, `constructor` e `prototype`.
- O número do registro vai dentro do texto cifrado, junto com o dono: texto cifrado trocado de linha não abre.
- Documentação: enquanto os Termos e a home não mudarem, a fase 1 só pode ser usada com dados fictícios.

## 2026-11-19 — Cadastro de pacientes: fase 1, só no servidor e só para o administrador

Detalhes, contrato da API, limites e o que falta antes de abrir em `docs/pacientes.md`.

- Para o usuário comum nada mudou: o check-up, o pré-operatório, os PDFs e as operadoras continuam sem gravar
  dado de paciente, e os Termos, a home e a página de cadastro não foram alterados. Não há tela nesta fase.
- Tabelas novas: `pacientes` (um JSON cifrado com todos os campos; CNS e CPF só como HMAC, para o banco recusar
  duplicado na mesma conta) e `pacientes_acessos` (trilha: quem fez o quê e quando, sem dado de paciente). Nada do
  paciente fica em claro no banco, nem o nome. As chaves derivavam de `SECRET_KEY` (trocado na entrada acima:
  agora derivam de `PACIENTES_CHAVE`); sem a chave o cadastro se recusa a gravar.
- Rotas novas em `/api/pacientes` (listar e buscar, criar, ler, atualizar, excluir, exportar), todas só para o
  administrador: conta comum recebe 403 e, sem login, 401. Cada paciente é da conta que o cadastrou; o de outra
  conta responde 404, também para o administrador.
- Campos: identificação (nome, nome social, nascimento, sexo, CPF, CNS, mãe, raça/cor, prontuário, responsável),
  contato e endereço (os do laudo de APAC), até 5 planos (operadora, carteira, validade) e a ficha clínica (retrato
  do formulário do check-up, até 64 KB). Tudo é validado no servidor; chave desconhecida é recusada.
- A regra de quem pode usar fica em `pacientes.habilitado_para`. Abrir a todos é trocar essa linha, depois da nova
  versão dos Termos, dos textos da home e do cadastro e da política de retenção.
- Registro de perigos: P-10 passa a ter uma exceção controlada; P-26 (dados guardados no cadastro) é novo.

## 2026-11-17 — APAC no formulário do SUS, orientações em subtópicos e resumo dos exames

- O laudo de APAC passa a usar o formulário do SUS como fundo (`src/data/apac_sus.pdf`; do modelo recebido só saiu
  "Estado de Santa Catarina"). O Evidēns escreve os dados nas caixas e não redesenha nada.
- Formulário da APAC: CEP primeiro, com busca do endereço (ViaCEP), e máscaras de data, telefone, CEP e CNS.
- Orientações em três subtópicos; legenda de todos os graus de evidência, com cor própria abaixo de A e B.
- Caixa "Exames já realizados": os exames lidos dos laudos em uma linha por data, sem referência e sem nome.

## 2026-11-17 — Conta de operadora: modo sombra

- `scripts/modo_sombra.py` classifica um arquivo de pedidos de exame laboratorial de operadora (liberaria, pediria
  esclarecimento, barraria), sem barrar nada. Regras em `src/utils/operadora.py`: as do check-up, mais pareceres de
  sociedades médicas (listas do Choosing Wisely dos EUA, do Canadá e do Brasil), o intervalo mínimo da HbA1c e os
  exames alternativos que as diretrizes aceitam. Formato do arquivo e regras em `docs/operadoras-modo-sombra.md`.
- Uma auditoria com quatro agentes, antes do merge, corrigiu: exame de imagem recomendado saía como "barraria"; CID
  de pré-operatório, de suspeita e de seguimento (Z01.8, Z03, Z04, Z08, Z09) era lido como rastreio; glicemia de jejum
  e citologia, aceitas pelas diretrizes do check-up, saíam como "barraria"; falha do motor virava liberação; valor em
  formato ambíguo era somado errado.
- Leitura de laudos: novo modelo de laboratório de hospital ("Data Coleta" em parte dos exames e "Dt. Solic" no
  cabeçalho), com seis nomes de exame novos. Corrigido: o limite de referência era lido como resultado quando vinha
  em linha separada (bilirrubina total "Até 1,2", "RNI: Até 1,20"); leucócitos com a unidade colada ("9.200/mm³") e
  fósforo não eram lidos. Exame fora da lista com um resultado só fica com o texto do resultado.
- O modo sombra aceita laudos em PDF (`--laudos`): cada exame identificado vira um pedido, com o código TUSS.
- O motor do check-up virou a função `recomendar`, chamável fora do servidor; a rota só entrega o resultado e registra
  o uso. Nenhuma saída do motor mudou (`tests/test_caracterizacao.py`).

## 2026-11-12 — Limpeza de código fora do caminho de produção

- Removidos pontos de entrada alternativos, banco de dados e rotas de pacientes, motor antigo, geradores de PDF
  sem uso, telas antigas (`dist/`, `src/static/*.html`, cópias `.original`/`.new`), build e deploy obsoletos
  (GitHub Pages, Netlify, `package.json`) e relatórios de depuração. Nenhuma saída do motor mudou
  (`tests/test_caracterizacao.py`).
- Dependências de produção reduzidas a Flask e flask-cors, em `api/requirements.txt`.
- `analytics.html` passou a consultar `/api/analytics/stats` (a rota anterior não existia).
- Testes de estrutura (`tests/test_estrutura.py`) impedem que código sem uso volte a se acumular.

## 2026-11-12 — Contenção de segurança clínica e documental

Detalhes, controles e testes em `docs/registro-de-perigos.md`.

- Documentos
  - Removidos `/api/gerar-receita-vacinas` e `/api/gerar-solicitacao-exames`, que montavam documentos com
    identificação fixa de médico e declaração de assinatura digital sem assinatura real; removido `/api/generate-pdf`,
    que não gerava nada. As três rotas respondem 410.
  - PDFs: escape automático nos templates, limites de quantidade e tamanho, delimitador multipart aleatório,
    aviso "Documento sem assinatura digital" e autenticação básica opcional para o Gotenberg.
- Vacinas
  - Triagem de segurança com três valores (gestante, amamentando, imunossupressão). Vacinas de vírus vivo
    atenuado e HPV só entram quando a triagem libera; o que fica de fora volta em `nao_incluidas`, com motivo.
  - A triagem é conferida de novo no pedido do PDF de vacinas.
- Risco cardiovascular
  - Cálculo desativado na tela e no servidor; as duas implementações foram apagadas.
- Entrada
  - Validação com resposta 400 e mensagens por campo. Idade, sexo e tabagismo obrigatórios; sem valores padrão.
  - O nome do paciente passou a ser opcional e não é mais enviado com o pedido de recomendações.
  - Nenhum dado de paciente é gravado.
- Site
  - Lista explícita de arquivos publicados: telas antigas e arquivos de configuração deixaram de ser servidos.
  - Página do check-up: retirado o seletor de país (não tinha efeito), avisos de uso e de minuta, resultado
    descartado quando o formulário muda.
- Testes
  - Suíte pytest em `tests/` rodando pela entrada de produção, com integração contínua em `.github/workflows/tests.yml`.

## 2025-09-16
- Segurança: Remoção explícita do cabeçalho `Access-Control-Allow-Private-Network` em todas as respostas Flask para mitigar o comportamento inseguro introduzido no Flask-CORS 4.0.1.
- Testes de fumaça verificam a ausência do cabeçalho de rede privada nas rotas principais.
- index.html
  - Valores normalizados de tabagismo (`fumante_atual` / `ex_fumante`).
  - Seletor de País (BR/EUA) que envia `pais` no payload.
  - Payload inclui também `tabagismo_status` e `tabagismo_macos_ano` achatados para compatibilidade.
  - Exibição de *chips* de status (Devido / Em atraso / Recente) nos cards.

- checkup.py
  - AAA agora só aparece para homens 65–75 **que já fumaram** (ever smokers) com base em `tabagismo`.
  - Função `_parse_smoking_status` para aceitar string ou dict.
  - Deduplicação melhora: chave (titulo,categoria,referencia) e preserva maior prioridade.

- checkup_intelligent.py
  - Suporte robusto a `tabagismo` vindo como dict ou campos achatados; normalização dos valores.
  - Novo parâmetro `pais` (BR/EUA) aceito.
  - **RSV** corrigido para **dose única** (≥75; 50–74 com risco) e sem reforço periódico.
  - **QDenga®** exibida **apenas no Brasil** (`pais='BR'`) e com referência **SBIm/ANVISA 2024** (≤60 anos).
  - Adicionadas recomendações **não recomendadas** (carótidas, ovário, Vitamina D) para educação e redução de overuse.
  - AAA incluído no fluxo inteligente (homens 65–75 ever smokers).
  - Deduplicação e ordenação por prioridade.

## 2025-09-15
- vercel.json
  - Adicionado `version: 2` e removido `builds` legado para evitar erro "Function Runtimes must have a valid version".
  - Mantidos `routes` para mapear `/checkup-intelligent`, `/gerar-solicitacao-exames`, `/gerar-receita-vacinas`.
  - Declarado `functions.runtime` para Python 3.11 em `api/**/*.py`.
- API serverless
  - Endpoints de saúde `/health` para cada função.
  - Normalização dos campos e `referencia_html` nas recomendações.
