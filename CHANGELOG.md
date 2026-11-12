
# Patches applied (2025-08-26T12:12:23)

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
