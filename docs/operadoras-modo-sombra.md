# Conta de operadora: modo sombra

O modo sombra classifica pedidos de exame laboratorial que a operadora já recebeu. **Nada é barrado**: o resultado
mostra o que seria liberado, o que pediria esclarecimento e o que seria barrado, para medir antes de ligar qualquer
fila. O escopo completo (auditor, prazos, Rol da ANS, LGPD) está no documento de escopo do projeto.

## Como rodar

```
python scripts/modo_sombra.py pedidos.csv [resultado.csv]
```

O resultado repete as colunas da entrada e acrescenta `cor`, `acao`, `codigo_do_motivo`, `motivo`, `exame`, `grau`,
`referencia`, `link`, `finalidade_usada`, `origem_da_finalidade`, `proxima_data_elegivel`, `versao` e `erro`. O resumo
sai na tela.

## Arquivo de entrada

CSV em UTF-8, separado por vírgula ou ponto e vírgula, uma linha por exame pedido.

| Coluna | Obrigatória | Conteúdo |
|---|---|---|
| `id_pedido` | sim | Identificador do pedido na operadora |
| `id_beneficiario` | sim | Pseudonimizado; sem nome, CPF ou número da carteira |
| `idade` | sim | Em anos, na data do pedido |
| `sexo` | sim | F ou M |
| `data_pedido` | sim | AAAA-MM-DD (aceita DD/MM/AAAA) |
| `codigo_tuss` | sim | 8 dígitos, tabela 22 |
| `carater` | sim | eletivo ou urgencia |
| `regime` | sim | ambulatorial ou internado |
| `segmentacao` | não | Segmentação do plano (ainda não usada) |
| `finalidade` | não | rastreio, diagnostico, seguimento ou nao_informada |
| `cid` | não | CID-10 informado no pedido |
| `indicacao_clinica` | não | Texto livre da guia (ainda não usado) |
| `data_ultimo_exame` | não | Data do último exame com o mesmo código |
| `valor` | não | Valor pago, para estimar a economia |

## Regras

As regras são as do check-up (`src/routes/checkup_intelligent.py`, função `recomendar`), para a idade e o sexo do
beneficiário, sem comorbidade: a guia não traz esse dado. O intervalo vem da periodicidade da própria recomendação
(`docs/periodicidade.md`). O exame é reconhecido pelo código TUSS (`src/utils/tuss.py`).

| Cor | Quando |
|---|---|
| Verde (liberaria) | Rastreio recomendado e dentro do intervalo; finalidade diagnóstica ou de seguimento; exame sem regra |
| Amarelo (pediria esclarecimento) | Decisão individual (grau C); "pelo menos uma vez na vida" já feito |
| Vermelho (barraria) | Antes do intervalo; indicado uma única vez e já feito; recomendação contrária; parecer de sociedade contra a rotina; sem recomendação de rastreio para o perfil |
| Fora do escopo | Urgência, emergência ou paciente internado |

Finalidade do pedido:
- informada na coluna `finalidade`: vale o que foi informado;
- não informada, com CID: Z00 a Z13 (exame de rotina ou de rastreamento) conta como rastreio; qualquer outro CID
  conta como indicação diagnóstica ou de seguimento;
- não informada e sem CID: tratado como rastreio, com `origem_da_finalidade` igual a `presumida`. O resumo diz quanto
  do amarelo e do vermelho depende dessa presunção.

## Pareceres contra o pedido de rotina

Valem quando a finalidade é rastreio. Só entram exames cujo código TUSS está na tabela conferida do repositório.

| Exame | Parecer | Fonte |
|---|---|---|
| 25-hidroxivitamina D | Contra a dosagem de rotina em adultos saudáveis | [Endocrine Society 2024](https://doi.org/10.1210/clinem/dgae290) |
| 1,25-di-hidroxivitamina D | Não dosar de rotina; só com hipercalcemia ou função renal reduzida | [Endocrine Society e AACE, Choosing Wisely 2013](https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/endocrine-society--choosing-wisely.pdf?la=en) |
| Testosterona total, em mulheres | Não diagnostica o transtorno do desejo sexual hipoativo; nenhum ponto de corte separa mulheres com e sem disfunção sexual | [Consenso Global 2019](https://doi.org/10.1080/13697137.2019.1637079) |
| Testosterona total, em homens | Contra o rastreio de hipogonadismo na população geral | [Endocrine Society 2018](https://doi.org/10.1210/jc.2018-00229) |
| Herpes simples, IgG e IgM | Contra o rastreio sorológico de herpes genital em assintomáticos (grau D) | [USPSTF 2023](https://pubmed.ncbi.nlm.nih.gov/36786784/) |
| Urocultura, em homens | Contra o rastreio de bacteriúria assintomática em adultos fora da gestação (grau D). Em mulheres a regra não é aplicada: o rastreio é recomendado na gestação (grau B), que o pedido não informa | [USPSTF 2019](https://www.uspreventiveservicestaskforce.org/uspstf/document/ClinicalSummaryFinal/asymptomatic-bacteriuria-in-adults-screening) |

Pareceres já levantados, à espera do código TUSS conferido (não entram na classificação). A tabela conferida do
repositório vai de 40301010 a 40314030; hormônios e marcadores tumorais (403160xx em diante) só têm os códigos dos
exames do check-up.

| Exame | Parecer | Fonte |
|---|---|---|
| T3 total e T3 livre | Não pedir sem suspeita clínica ou diagnóstico de hipertireoidismo | [SBEM, Choosing Wisely Brasil](https://proqualis.fiocruz.br/sites/proqualis.fiocruz.br/files/CWB%20Tireoide.pdf) |
| T3 total e T3 livre, no ajuste de levotiroxina | Não pedir para avaliar a dose no hipotireoidismo | [Endocrine Society e AACE, Choosing Wisely 2013](https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/endocrine-society--choosing-wisely.pdf?la=en) |
| T3 reverso | Não pedir na avaliação da função tireoidiana | [SBEM, Choosing Wisely Brasil](https://proqualis.fiocruz.br/sites/proqualis.fiocruz.br/files/CWB%20Tireoide.pdf) |
| CA-125 | Contra o rastreio de câncer de ovário em mulheres assintomáticas (grau D) | [USPSTF 2018](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/ovarian-cancer-screening) |

## Limites desta versão

- Não há comorbidade nem gestação no pedido. Um exame de seguimento sem CID é lido como rastreio (origem `presumida`).
- A situação do exame no Rol da ANS (Anexo I e DUT) ainda não entra: depende da correlação oficial entre TUSS e Rol.
- Intervalo de exame de diagnóstico ou de seguimento ainda não é avaliado.
- O motor do check-up atende de 18 a 120 anos.
