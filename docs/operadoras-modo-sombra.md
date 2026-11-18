# Conta de operadora: modo sombra

O modo sombra classifica pedidos de exame laboratorial que a operadora já recebeu. **Nada é barrado**: o resultado
mostra o que seria liberado, o que pediria esclarecimento e o que seria barrado, para medir antes de ligar qualquer
fila. O escopo completo (auditor, prazos, Rol da ANS, LGPD) está no documento de escopo do projeto.

## Como rodar

```
python scripts/modo_sombra.py pedidos.csv [resultado.csv]
python scripts/modo_sombra.py --laudos laudo1.pdf laudo2.pdf [--saida resultado.csv]
```

O resultado repete as colunas da entrada e acrescenta `cor`, `acao`, `codigo_do_motivo`, `motivo`, `exame`, `grau`,
`referencia`, `link`, `aviso`, `finalidade_usada`, `origem_da_finalidade`, `ultimo_exame_usado`,
`origem_do_ultimo_exame`, `proxima_data_elegivel`, `versao` e `erro`. O resumo sai na tela. A coluna `aviso` traz a
divergência entre diretrizes, quando há. Coluna da entrada com nome igual ao de uma coluna de saída sai com o sufixo
`_entrada`.

## Na tela: conferência do pedido pelo check-up

`/operadoras` (por enquanto só a conta de administrador; botão "Operadoras (conferência do pedido)" na página da
conta). A ideia é uma só: usar o check-up do Evidēns como ele é, sem regra a mais nem a menos, para saber se o que o
médico pediu tem evidência para aquele paciente.

1. **Pedido do médico.** PDF com os exames pedidos (até 8 arquivos, 4 MB no total). O leitor entende o laudo de
   laboratório nos formatos conhecidos e, se o PDF não for laudo, uma lista de nomes de exame ou de códigos TUSS.
   PDF escaneado, sem texto, não é lido.
2. **Dados do paciente.** O formulário é o do check-up, com os mesmos itens, dentro da própria página (um quadro com
   o formulário do check-up: há um formulário só, sem cópia para manter).
3. **Resultado.** O motor do check-up roda para o paciente e cada exame pedido sai como:
   - **Indicado**: está entre os exames que o check-up recomenda para o paciente. Vêm o grupo, a periodicidade, o
     grau e as referências da própria recomendação.
   - **Não indicado**: não está. Se o check-up o deixou de fora por um motivo que ele mesmo declara (já feito e em
     dia, adiado na gestação, recomendação de não fazer), o motivo aparece. Senão, vai a justificativa formal, com a
     fonte e o link (ver "Justificativa do exame não indicado").
   A tela mostra também a lista do que o check-up indica para o paciente, com o que foi e o que não foi pedido, e
   baixa o resultado em CSV.

### Justificativa do exame não indicado

Não basta dizer que o exame não está no check-up. Para cada exame não indicado, a tela mostra:

1. **O que a diretriz diz sobre pedir o exame de rotina**, com a referência e o link. A ordem de busca é: parecer de
   sociedade médica já cadastrado (tabela "Pareceres de sociedades médicas", abaixo), se a sociedade é aceita, e,
   depois, o registro `SEM_INDICACAO_DE_ROTINA` em `src/utils/operadora.py`.
2. **Para quem o check-up indica o exame** ("Adultos com HAS", "Em uso de lítio"...), cada situação com a referência
   que o check-up usa nela, e a observação de que nenhuma foi informada. Vem de `src/data/indicacoes_motor.json`,
   gerado pela varredura do motor (`python scripts/gerar_catalogo.py`; o teste falha se o arquivo estiver
   desatualizado).

Exame que ainda não foi pesquisado sai com "Ainda não há justificativa de diretriz registrada para ele", e a linha
fica marcada (`sem_justificativa`) para a pesquisa e o registro. Nenhum texto entra no registro sem conferência na
fonte.

#### Só sociedade que o algoritmo já cita

Decisão do responsável clínico (17/11/2026): a fonte da justificativa é só **sociedade que o check-up já cita**.
Referência, aqui, é a sociedade (USPSTF, AHA/ACC, KDIGO, AASLD, NICE...), não uma diretriz específica: qualquer
recomendação de uma sociedade aceita pode ser usada. Fonte de fora pode contradizer o que o check-up recomenda.

- `sociedades_do_algoritmo()` lê as sociedades das referências que o motor cita (`indicacoes_motor.json`).
- Aceitas à parte por ele: a **Surviving Sepsis Campaign** (qualquer exame) e a **CSCC, Choosing Wisely Canada**,
  só na TGO (`SOCIEDADES_ACEITAS_A_PARTE` e `FONTES_ACEITAS_POR_EXAME`).
- Recusadas por ele: o **ACP** na creatinina (vale a KDIGO) e a **CSCC** na ureia e nas bilirrubinas.
- Parecer do modo em lote cuja fonte é só de sociedade de fora (CAMB, ASCP, CRA, CSEM, SBPC/ML) não vai para a tela:
  o exame sai com o que a USPSTF diz. Volta quando a sociedade for aprovada.
- O teste `test_justificativa_so_cita_sociedade_que_o_algoritmo_ja_cita` falha se entrar fonte de fora.

| Exame | O que a diretriz diz | Fonte |
|---|---|---|
| TGP (ALT) | Sem rastreio de doença hepática esteatótica na população geral; a pesquisa de fibrose (FIB-4) fica para diabetes tipo 2, obesidade com complicações, consumo de álcool ou história familiar de cirrose | [AASLD 2023](https://doi.org/10.1097/HEP.0000000000000323); [USPSTF, recomendações A e B](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations) |
| TGO (AST) | Não pedir de rotina na avaliação inicial, nem junto da TGP, que é mais específica | [CSCC 2024, Choosing Wisely Canada](https://choosingwiselycanada.org/download/17612); [AASLD 2023](https://doi.org/10.1097/HEP.0000000000000323) |
| Creatinina | Pesquisar doença renal crônica, com a TFG estimada pela creatinina e a albuminúria, em quem tem risco para a doença ou já a tem (ponto de prática 1.1.1.1; recomendação 1.1.2.1, grau 1B). Sem recomendação de testar o adulto assintomático sem fator de risco | [KDIGO 2024](https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf); [USPSTF, recomendações A e B](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations) |
| PCR | Evidência insuficiente para somar a PCR ultrassensível à avaliação do risco cardiovascular (declaração I) | [USPSTF 2018](https://doi.org/10.1001/jama.2018.8359) |
| TP/INR e TTPA | Fora dos rastreios recomendados. Nem antes de cirurgia eletiva são de rotina: só se consideram na doença hepática crônica (ASA 3 ou 4, cirurgia de porte intermediário ou maior) | [USPSTF, recomendações A e B](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations); [NICE NG45](https://www.nice.org.uk/guidance/ng45/chapter/recommendations) |
| Lactato | Não é exame de rastreio; indicado na suspeita de sepse ou de hipoperfusão | [Surviving Sepsis Campaign 2021](https://doi.org/10.1007/s00134-021-06506-y) |
| CK total | Não é exame de rastreio, nem de rotina em uso de estatina (classe III) | [AHA/ACC 2018](https://doi.org/10.1161/CIR.0000000000000625) |
| T4 livre e provas de função tireoidiana | Evidência insuficiente para o rastreio de disfunção tireoidiana em adultos assintomáticos fora da gestação (grau I) | [USPSTF 2015](https://www.uspreventiveservicestaskforce.org/uspstf/document/clinical-summary142/thyroid-dysfunction-screening) |
| Ureia, bilirrubinas, sódio, potássio, cálcio, cálcio iônico, magnésio, fósforo, proteínas totais e frações, hemograma | Fora dos rastreios que a USPSTF recomenda ao adulto assintomático (graus A e B) | [USPSTF, recomendações A e B](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations) |
| VHS, ácido úrico, eletroforese de proteínas, FAN, perfil reumatológico, anti-TPO, tempo de sangramento, sorologia para Helicobacter pylori, folato eritrocitário | Fora dos rastreios que a USPSTF recomenda (graus A e B). O parecer do modo em lote é de sociedade que o algoritmo não cita e não vai para a tela | [USPSTF, recomendações A e B](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations) |

O que **não** entra na conferência: cores, finalidade, CID, regime, pareceres de sociedades e intervalos mínimos do
modo em lote (abaixo). O veredito (indicado ou não indicado) é sempre o do check-up; os pareceres e o registro acima
só explicam o exame não indicado. O cálcio total conta como cálcio iônico.

**Exame aceito como alternativa.** A glicemia de jejum pedida conta como indicada quando o check-up recomenda a HbA1c
e a própria recomendação a cita "como alternativa" (rastreio e confirmação do diabetes: ADA 2026; USPSTF 2021). Um
exame basta: com a HbA1c no mesmo pedido, a glicemia sai como não indicada. No acompanhamento do diabético não há
alternativa: o check-up recomenda os dois. Fica em `ALTERNATIVAS_NA_CONFERENCIA`, em `src/utils/operadora.py`, que escolhe
quais alternativas do modo em lote valem na tela (a citologia no lugar do DNA-HPV ainda não) (decisão do responsável
clínico, 18/11/2026).

Os dados do paciente vão à rota `POST /api/admin/operadoras/conferir` no campo `paciente`, em JSON no formato que o
formulário do check-up envia; é a porta de entrada prevista para os dados que virão do cadastro da operadora. "Exames
já realizados" vai junto, como no check-up. Nada é gravado: o PDF e os dados são lidos em memória e descartados.

**Limite conhecido.** O check-up pede um exame por indicação. Quando ele recomenda a HbA1c para rastrear diabetes, a
glicemia de jejum pedida no lugar sai como não indicada, embora a própria recomendação a cite como alternativa.

O modo em lote, por planilha, continua disponível pelo script (seções seguintes) e não aparece na tela.

## Modo em lote: dados do paciente, cálcio e exames que não são de rastreio

- **Dados do paciente.** Com comorbidades e medicações informadas nas colunas da planilha, o pedido é comparado com o
  que o check-up recomenda para aquele paciente, e não só para a idade e o sexo. As chaves são as do check-up
  (`comorbidades_validas()` e `medicacoes_validas()` em `src/utils/operadora.py`); chave fora da lista invalida a linha.
- **Exame que o check-up não indica.** Sem recomendação do check-up e sem parecer contrário específico de sociedade,
  o pedido sai como "pediria esclarecimento" (pedir a indicação clínica), e não como barrado. A regra geral contra
  exames de sangue de rotina (SBMFC e CFPC, Choosing Wisely) foi retirada por decisão do responsável clínico; os
  pareceres específicos por exame continuam valendo.
- **Cálcio.** O cálcio total (40301400) é tratado como o cálcio iônico (40301419) nas regras, por decisão do
  responsável clínico. No check-up, o cálcio total já feito também conta como cálcio iônico feito.
- **Exames que não são de rastreio.** Exame que aparece nos laudos das operadoras e não tem regra no check-up é
  pesquisado e registrado em `NAO_SAO_DE_RASTREIO` (`src/utils/operadora.py`), com a indicação reconhecida e a fonte.
  Como rastreio, seria barrado; com finalidade diagnóstica ou de seguimento, liberado.

| Exame | Indicação reconhecida | Fonte |
|---|---|---|
| Lactato (40301109) | Suspeita de sepse ou de hipoperfusão | [Surviving Sepsis Campaign 2021](https://doi.org/10.1007/s00134-021-06506-y) |
| CK total (40301648) | Sintoma muscular grave ou fraqueza objetiva em uso de estatina; a dosagem de rotina não é útil | [AHA/ACC 2018](https://doi.org/10.1161/CIR.0000000000000625) |
| Proteínas totais e frações (40302385) | Nenhum rastreio recomendado a inclui; sem fonte própria, pede esclarecimento em vez de barrar | — |

## Arquivo de entrada

CSV em UTF-8 (o script também lê Windows-1252, o que o Excel grava), separado por vírgula ou ponto e vírgula, uma
linha por exame pedido. Valor inválido em qualquer coluna, mesmo opcional, invalida a linha: ela sai com a coluna
`erro` preenchida e não é classificada.

| Coluna | Obrigatória | Conteúdo |
|---|---|---|
| `id_pedido` | sim | Identificador do pedido na operadora |
| `id_beneficiario` | sim | Pseudonimizado; sem nome, CPF ou número da carteira |
| `idade` | sim | Em anos, na data do pedido |
| `sexo` | sim | F ou M |
| `data_pedido` | sim | AAAA-MM-DD (aceita DD/MM/AAAA) |
| `codigo_tuss` | sim | 8 dígitos, tabela 22 |
| `carater` | sim | eletivo ou urgencia (aceita "Urgência/Emergência", 1 e 2) |
| `regime` | sim | ambulatorial, internado ou pronto-socorro (aceita domiciliar e telessaúde, tratados como ambulatorial) |
| `segmentacao` | não | Segmentação do plano (ainda não usada) |
| `finalidade` | não | rastreio (ou rotina), diagnostico, seguimento ou nao_informada |
| `cid` | não | CID-10 informado no pedido |
| `indicacao_clinica` | não | Texto livre da guia (ainda não usado) |
| `data_ultimo_exame` | não | Data do último exame com o mesmo código |
| `comorbidades` | não | Chaves das comorbidades do check-up, separadas por barra vertical: `hipertensao\|doenca_renal` |
| `medicacoes` | não | Chaves das medicações de uso contínuo do check-up, separadas por barra vertical: `sinvastatina\|levotiroxina` |
| `valor` | não | Valor pago, para estimar a economia: 1234,56, 1.234,56 ou 1234.56. "1.234" é ambíguo e dá erro |

**Último exame.** Sem `data_ultimo_exame`, vale o pedido anterior do mesmo beneficiário e do mesmo código no próprio
arquivo (`origem_do_ultimo_exame` igual a `arquivo`). Quando a coluna vem preenchida, vale a data mais recente entre a
informada e a do arquivo. Por isso o arquivo histórico rende mais quando cobre vários meses.

## Entrada por laudo em PDF

Com `--laudos`, cada exame identificado no laudo vira um pedido. A leitura é a mesma do check-up
(`src/utils/laudos.py`, por código e sem IA); o laudo é lido em memória e nada dele é gravado.

| Dado do pedido | De onde vem |
|---|---|
| `id_beneficiario` | Nome do arquivo, sem a extensão. Não use o nome do paciente |
| `codigo_tuss` | Código do exame identificado (`src/utils/tuss.py`) |
| `data_pedido` | Data da coleta do exame; sem ela, a data da solicitação do cabeçalho |
| `sexo` e `idade` | "Sexo" e "Nasc." do cabeçalho do laudo, ou `--sexo` e `--idade` |
| `regime` | `--regime`; sem ele, o setor do laudo (unidade de internação, UTI, enfermaria ou pronto-socorro) ou ambulatorial |
| `carater`, `finalidade`, `cid` | `--carater` (eletivo), `--finalidade` e `--cid`, iguais para todos os exames |

O resumo lista, por laudo, quantos exames foram identificados e quais títulos ficaram de fora (nome não reconhecido,
sem data ou sem código TUSS conferido). Laudo de paciente internado sai como fora do escopo, como qualquer pedido de
internado.

## Regras

As regras são as do check-up (`src/routes/checkup_intelligent.py`, função `recomendar`), para a idade e o sexo do
beneficiário, sem comorbidade: a guia não traz esse dado. O intervalo vem da periodicidade da própria recomendação
(`docs/periodicidade.md`). O exame é reconhecido pelo código TUSS (`src/utils/tuss.py`). A elas se somam os pareceres
de sociedades médicas das tabelas abaixo.

| Cor | Quando |
|---|---|
| Verde (liberaria) | Rastreio recomendado e dentro do intervalo; exame alternativo aceito; finalidade diagnóstica ou de seguimento; exame de laboratório sem regra; código de laboratório fora da tabela conferida; idade fora do que o motor atende |
| Amarelo (pediria esclarecimento) | Decisão individual (grau C); "pelo menos uma vez na vida" já feito; intervalo que depende do resultado anterior; evidência insuficiente (USPSTF grau I); divergência entre diretrizes que muda a conduta; urocultura de rastreio em mulher em idade reprodutiva |
| Vermelho (barraria) | Antes do intervalo; indicado uma única vez e já feito; recomendação contrária; parecer de sociedade contra o exame; sem recomendação de rastreio para o perfil |
| Fora do escopo | Urgência, emergência, pronto-socorro ou paciente internado; exame que não é de laboratório (grupos da TUSS fora de 403 e 406) |

O exame de imagem ou de endoscopia não é julgado nesta versão, mesmo quando o check-up tem regra para ele
(mamografia, colonoscopia, densitometria).

Finalidade do pedido:
- informada na coluna `finalidade`: vale o que foi informado;
- não informada, com CID: Z00, Z01 (menos Z01.8), Z02 e Z10 a Z13 (exame de rotina ou de rastreamento) contam como
  rastreio; qualquer outro CID conta como indicação diagnóstica ou de seguimento. Z01.8 é usado na avaliação
  pré-operatória; Z03 e Z04 são observação por suspeita; Z08 e Z09, seguimento após tratamento;
- não informada e sem CID: tratado como rastreio, com `origem_da_finalidade` igual a `presumida`. O resumo diz quanto
  do amarelo e do vermelho depende dessa presunção.

Intervalos:
- "pelo menos uma vez na vida" já feito fica no amarelo, porque a repetição depende de risco que a guia não informa.
  O check-up, que conhece o risco do paciente, simplesmente não volta a indicar o exame;
- "a cada 3 anos se normal" (HbA1c) repetido antes do prazo fica no amarelo: no pré-diabetes o intervalo é anual, e a
  guia não traz o resultado anterior.

Exame alternativo ao recomendado, aceito pelas mesmas diretrizes do check-up:
- glicemia de jejum no lugar da HbA1c no rastreio de diabetes (35 a 70 anos), com a mesma periodicidade;
- citologia no lugar do teste de DNA-HPV (25 a 64 anos), onde o teste não está disponível (MS 2025): a cada 3 anos
  após dois exames anuais normais.
Os dois exames no mesmo pedido ainda não são apontados como duplicidade.

O exame sem recomendação do check-up para o perfil, e sem parecer contrário específico, sai como "pediria
esclarecimento", sem referência: a regra geral do Choosing Wisely contra exames de rotina foi retirada.

## Pareceres de sociedades médicas

Listas do Choosing Wisely revistas em 17/11/2026: ASCP (EUA, 25 recomendações, 2014 a 2018), Endocrine Society e AACE
(EUA, 2013), Choosing Wisely Canada (lista de laboratório de 2022, CAMB 2020 e CSCC 2024), SBPC/ML (Brasil, 2019 e
2023), SBMFC (Brasil, 2018), SBI (Brasil, 2019) e SBEM, Departamento de Tireoide (Brasil, 2021). Só entram na
classificação os exames cujo código TUSS está conferido no repositório: a tabela de laboratório (40301010 a 40314030)
e os códigos dos exames do check-up. Os pareceres valem para adultos (18 anos ou mais).

O Choosing Wisely Canada declara que as recomendações dele não foram feitas para definir pagamento ou cobertura, e
sim para orientar a conversa entre médico e paciente. No modo sombra elas só medem; antes de ligar qualquer fila,
esse ponto entra na análise jurídica do escopo.

### Contra o pedido de rotina (valem quando a finalidade é rastreio)

| Exame | Parecer | Fonte |
|---|---|---|
| 25-hidroxivitamina D, até 60 anos | Sugestão condicional contra a dosagem de rotina em adultos sem indicação estabelecida. Aviso de divergência: para o USPSTF 2021 a evidência é insuficiente (grau I); SBPC/ML e SBEM 2017 indicam a dosagem em grupos de risco, como gestantes e lactantes | [Endocrine Society 2024](https://doi.org/10.1210/clinem/dgae290); [USPSTF 2021](https://einstein.elsevierpure.com/en/publications/screening-for-vitamin-d-deficiency-in-adults-us-preventive-servic/); [SBPC/ML e SBEM 2017](https://www.redalyc.org/pdf/3935/393554303005.pdf) |
| 1,25-di-hidroxivitamina D | Não dosar de rotina; só com hipercalcemia ou função renal reduzida | [Endocrine Society, Choosing Wisely 2013, atualizado em 2017](https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/endocrine-society--choosing-wisely.pdf?la=en) |
| Testosterona total, em mulheres | Contra o diagnóstico de deficiência androgênica em mulheres saudáveis; a testosterona total não diagnostica o transtorno do desejo sexual hipoativo. Não vale para investigação de hiperandrogenismo nem para controle de terapia com testosterona | [Endocrine Society 2014](https://doi.org/10.1210/jc.2014-2260); [Consenso Global 2019](https://doi.org/10.1080/13697137.2019.1637079) |
| Testosterona total, em homens | Contra o rastreio de hipogonadismo na população geral (recomendação forte, evidência de baixa qualidade). Não vale para busca de casos em doença hipofisária, uso crônico de opioide ou glicocorticoide, infertilidade e osteoporose | [Endocrine Society 2018](https://doi.org/10.1210/jc.2018-00229) |
| Herpes simples, IgG e IgM | Contra o rastreio sorológico de herpes genital em assintomáticos, gestantes incluídas (grau D). Não vale para pessoas com HIV ou imunossupressão | [USPSTF 2023](https://pubmed.ncbi.nlm.nih.gov/36786784/) |
| Urocultura, em homens e em mulheres a partir de 50 anos | Contra a urocultura de rastreio em adulto assintomático fora da gestação e sem doença urológica crônica (grau D). Não vale antes de procedimento urológico (IDSA 2019) | [USPSTF 2019](https://www.uspreventiveservicestaskforce.org/uspstf/document/ClinicalSummaryFinal/asymptomatic-bacteriuria-in-adults-screening) |
| VHS | Não usar para rastrear assintomáticos nem como teste geral de inflamação; a proteína C reativa é preferível | [CAMB 2020](https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf); [ASCP 2015](https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf) |
| Ácido úrico | Não pedir na avaliação de rotina de risco cardiovascular, obesidade ou diabetes | [CAMB 2020](https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf) |
| Eletroforese de proteínas séricas | Não pedir em assintomáticos; cabe com hipercalcemia, insuficiência renal, anemia ou lesão óssea lítica sem explicação | [CAMB 2020](https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf) |
| FAN | Não pedir como rastreio sem sinais ou sintomas específicos de lúpus ou de outra doença do tecido conjuntivo | [CRA, Choosing Wisely Canada](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| Perfil reumatológico (ácido úrico, eletroforese, FAN, VHS) | Os exames do painel não devem ser pedidos como rastreio | [CAMB 2020](https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf); [CRA](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| Anti-TPO | Não pedir de rotina | [CSEM, Choosing Wisely Canada](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| T4 livre e provas de função tireoidiana (T3, T4, índices e TSH) | Não usar T4 livre ou T3 para rastrear hipotireoidismo; o exame inicial é o TSH | [CSEM](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf); [ASCP 2015](https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf); [SBPC/ML 2019, em reportagem](https://medicinasa.com.br/sbpcml-recomendacoes/) |
| PSA a partir de 70 anos | Contra o rastreio (grau D); já era regra do check-up | USPSTF 2018 |

### Evidência insuficiente ou divergência que muda a conduta (amarelo)

| Exame | Parecer | Fonte |
|---|---|---|
| 25-hidroxivitamina D, acima de 60 anos | Divergência: SBPC/ML e SBEM 2017 indicam a dosagem em idosos acima de 60 anos; a Endocrine Society 2024 sugere não dosar de rotina, inclusive a partir de 75 anos | [SBPC/ML e SBEM 2017](https://www.redalyc.org/pdf/3935/393554303005.pdf); [Endocrine Society 2024](https://doi.org/10.1210/clinem/dgae290) |
| Urocultura, em mulheres de 18 a 49 anos | O rastreio é recomendado na gestação (grau B) e contraindicado fora dela (grau D); o pedido não informa gestação. A faixa é a idade reprodutiva da OMS (15 a 49 anos) | [USPSTF 2019](https://www.uspreventiveservicestaskforce.org/uspstf/document/ClinicalSummaryFinal/asymptomatic-bacteriuria-in-adults-screening) |
| TSH | Evidência insuficiente para o rastreio de disfunção tireoidiana em adultos assintomáticos fora da gestação (grau I). Aviso de divergência: SBMFC 2018 e CFPC são contra pedir função tireoidiana de rotina em assintomáticos | [USPSTF 2015](https://www.uspreventiveservicestaskforce.org/uspstf/document/clinical-summary142/thyroid-dysfunction-screening); [CFPC](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf); [SBMFC 2018, em reportagem](https://portal.afya.com.br/saude/choosing-wisely-veja-dicas-para-manejo-de-pacientes-ambulatoriais) |

### Contra o exame em qualquer finalidade (valem também no pedido diagnóstico)

| Exame | Parecer | Fonte |
|---|---|---|
| Tempo de sangramento (Duke e Ivy) | Não usar para orientar a conduta | [ASCP 2014](https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf); [SBPC/ML 2023, em reportagem](https://medicinasa.com.br/sbpcml-choosing-wisely/) |
| Sorologia para Helicobacter pylori (IgA, IgG, IgM) | Não pedir sorologia; usar o antígeno fecal ou o teste respiratório | [ASCP 2016](https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf); [SBPC/ML 2023, em reportagem](https://medicinasa.com.br/sbpcml-choosing-wisely/) |
| Folato eritrocitário | Não pedir; na anemia macrocítica, considerar a suplementação de ácido fólico | [ASCP 2017](https://www.ascp.org/content/docs/default-source/get-involved-pdfs/25-things-to-question.pdf) |

### Intervalo mínimo fora do rastreio

| Exame | Regra | Fonte |
|---|---|---|
| HbA1c | Não repetir em menos de 3 meses em paciente estável. Vale em qualquer finalidade; no rastreio vale o intervalo do check-up | [CSCC 2024](https://choosingwiselycanada.org/download/17612); [SBPC/ML 2023, em reportagem](https://medicinasa.com.br/sbpcml-choosing-wisely/) |

### Aviso de divergência em exame que o check-up recomenda

| Exame | Aviso | Fonte |
|---|---|---|
| PSA de 55 a 69 anos (grau C, amarelo) | A SBMFC 2018 é contra o rastreio de rotina com PSA | [SBMFC 2018, em reportagem](https://portal.afya.com.br/saude/choosing-wisely-veja-dicas-para-manejo-de-pacientes-ambulatoriais) |

### Levantados, à espera do código TUSS conferido (não entram na classificação)

A tabela conferida do repositório vai de 40301010 a 40314030; hormônios e marcadores tumorais (403160xx em diante)
só têm os códigos dos exames do check-up.

| Exame | Parecer | Fonte |
|---|---|---|
| T3 total e T3 livre, como rastreio | Não usar T3 para rastrear hipotireoidismo; o exame inicial é o TSH | [CSEM, Choosing Wisely Canada](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| T3 total e T3 livre, no ajuste de levotiroxina | Não pedir para avaliar a dose no hipotireoidismo | [Endocrine Society, Choosing Wisely 2013, atualizado em 2017](https://www.mainlinehealth.org/-/media/files/pdf/basic-content/physicians/mlhpp/choosing-wisely/endocrine-society--choosing-wisely.pdf?la=en) |
| T3 reverso | Não pedir na avaliação da função tireoidiana | [SBEM 2021](https://www.scielo.br/j/aem/a/xXbFTk7Lsr7jYkxGg8JNz3w/) |
| CA-125 | Contra o rastreio de câncer de ovário em mulheres assintomáticas sem síndrome hereditária de alto risco conhecida (grau D) | [USPSTF 2018](https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/ovarian-cancer-screening); [SBPC/ML 2019, em reportagem](https://medicinasa.com.br/sbpcml-recomendacoes/) |
| HLA-B27 | Só com suspeita de espondiloartrite por sinais ou sintomas específicos | [CRA, Choosing Wisely Canada](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| Ácido fólico sérico | Não pedir sem anemia macrocítica e suspeita de deficiência nutricional | [CAMB 2020](https://choosingwiselycanada.org/wp-content/uploads/2020/03/Medical-Biochemistry_EN.pdf) |
| Painel de IgG para alimentos | Não pedir | [CSACI, Choosing Wisely Canada](https://choosingwiselycanada.org/wp-content/uploads/2022/10/Choosing-Wisely-Canada-Labs-Recommendations-Full-List.pdf) |
| Teste genético HFE | Não pedir sem sobrecarga de ferro comprovada | [CSCC 2024](https://choosingwiselycanada.org/download/17612); [SBPC/ML 2019, em reportagem](https://medicinasa.com.br/sbpcml-recomendacoes/) |

### Dependem de dado clínico que o pedido não traz (não entram na classificação)

Exames pré-operatórios de rotina em cirurgia de baixo risco (ASCP 2014, SBPC/ML 2019, CAS e CAP; o módulo
pré-operatório do Evidēns já trata disso para o médico); repetição de carga viral de hepatite C fora do tratamento;
anti-TPO repetido na tireoidite de Hashimoto já confirmada; IgG de toxoplasmose repetido em quem já é positivo; CD4
repetido em quem tem carga viral suprimida; FSH, LH e estradiol para diagnosticar menopausa; IgE específica sem
história compatível; pesquisa de trombofilia após trombose com fator desencadeante; AST e ureia na triagem inicial.

## Limites desta versão

- Não há comorbidade nem gestação no pedido. Um exame de seguimento sem CID é lido como rastreio (origem
  `presumida`): dosagem de lítio ou de tacrolimo, CD4 e carga viral do HIV sem CID saem como "barraria".
- O pedido pré-operatório (CID Z01.8) é liberado sem análise; o módulo pré-operatório ainda não é consultado.
- O CID só é conferido no formato; um código que não existe conta como indicação.
- A situação do exame no Rol da ANS (Anexo I e DUT) ainda não entra: depende da correlação oficial entre TUSS e Rol.
- Fora da HbA1c, o intervalo de exame de diagnóstico ou de seguimento ainda não é avaliado.
- O motor do check-up atende de 18 a 120 anos.
