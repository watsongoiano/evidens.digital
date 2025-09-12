
# Patches applied (2025-08-26T12:12:23)
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
