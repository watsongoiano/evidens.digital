# Versão em inglês

As páginas e o motor continuam escritos em português. A versão em inglês sai de um único dicionário,
`static/i18n/en.json`, usado pelo navegador (`static/i18n.js`) e pelo servidor (`src/utils/i18n.py`).

## Como o idioma é escolhido

- Seletor no cabeçalho de cada página (`<span data-idioma></span>`): BR/PT ou US/EN. A escolha fica no
  navegador (localStorage) e num cookie (`evidens_idioma`), que o servidor lê.
- `?lang=en` ou `?lang=pt` no endereço força o idioma.
- Sem escolha, português.
- O painel do administrador fica em português.

## O que é traduzido, e onde

| O quê | Onde |
| --- | --- |
| Textos das páginas e o que o script escreve na tela | navegador, ao carregar e a cada mudança da página |
| Recomendações, orientações e motivos do motor | navegador (o motor responde em português) |
| Mensagens de erro da API (`error`, `erros`, `mensagem`) | servidor |
| PDFs de pedido e de receita | servidor (`src/utils/pdf_minutas.py`) |
| E-mails | não são traduzidos |

O pedido de PDF leva sempre os títulos em português: a posologia e a triagem de segurança das vacinas são
decididas por eles. Só o texto impresso muda.

## O dicionário

- `textos`: frase em português → frase em inglês (igualdade exata, sem contar espaços repetidos).
- `padroes`: pares `[expressão regular, saída]` para frases montadas. Na saída, `$1` é o grupo traduzido de
  novo (precisa ter par) e `%1` é o grupo como veio, só com o número no formato inglês.
- `manter`: o que é igual nos dois idiomas (siglas, nomes de fontes).

Números mudam de formato sozinhos (16,7 → 16.7; 7.000 → 7,000). Frases emendadas pelo motor são cortadas
no fim de cada frase e traduzidas uma a uma.

## Ao mudar um texto

Os testes de `tests/test_i18n.py` falham quando falta par em inglês para:

- qualquer texto das páginas (`python scripts/extrair_textos.py --faltando` lista o que falta);
- qualquer frase que o motor devolve (varredura por comorbidade, medicação, história familiar, idades,
  exames, gestação, doses e erros);
- os itens do catálogo de acréscimo e os textos fixos dos PDFs.

No navegador, `evidensIdioma.faltando()` no console lista o que apareceu na tela sem par.

## Revisão clínica

A tradução dos textos clínicos (títulos de exames, descrições, posologias) precisa da revisão de um médico
antes de ser usada com pacientes.
