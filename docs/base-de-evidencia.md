# Base de evidência: quantas páginas e quantas instituições

A home do Evidēns diz "mais de 7 mil páginas" e "mais de 40 sociedades". Este arquivo registra de onde saem esses números.

## Como foi contado

- A lista vem das referências que o motor devolve: uma varredura de perfis (idade, sexo, comorbidades, medicações, história familiar e gestação) e a coleta de cada rótulo de fonte citado.
- Cada documento conta inteiro, e uma vez só. O Williams, por exemplo, entra com o livro todo, embora o pré-natal use principalmente a Tabela 10-1.
- **As páginas são aproximadas.** Vêm da paginação da publicação (intervalo de páginas da revista) ou do PDF oficial, anotadas de memória, sem abrir documento por documento. Onde havia dúvida, usei o valor menor (sumário executivo em vez do texto completo, por exemplo).
- Confirmado na fonte: Williams Obstetrics 26ª edição, 1.328 páginas.

## Resultado

- **66 documentos ou famílias de documentos. cerca de 7.216 páginas** (5.888 sem o Williams).
- **47 instituições** na grade da home (5 nacionais e 42 internacionais). O teste `test_home_so_lista_instituicoes_que_o_motor_cita` falha se a home listar alguma que o motor não cita.

Ao acrescentar ou retirar uma fonte do motor, atualize esta tabela e, se o total mudar de faixa, os números da home.

## Obstetrícia e pré-natal

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| Williams 26e | Williams Obstetrics. 26ª edição (livro inteiro) | 1.328 |
| MS 2012-2016 | Cadernos de Atenção Básica nº 32: atenção ao pré-natal de baixo risco | 318 |
| Consenso brasileiro de DMG 2017 | Rastreamento e diagnóstico de diabetes mellitus gestacional no Brasil (OPAS. MS. FEBRASGO. SBD) | 32 |
| Einstein Pré-Natal v.3 (2024) | Protocolo de pré-natal de baixo risco | 30 |
| ACOG PB 222 (2020) | Gestational Hypertension and Preeclampsia | 24 |
| ACOG 2025 | Practice advisory: vacinação materna contra VSR | 5 |
| | **Subtotal** | **1.737** |

## Diabetes

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| ADA 2025 | Standards of Care in Diabetes 2025 (Diabetes Care 48. supl. 1) | 352 |
| ADA 2024 | Standards of Care in Diabetes 2024 (Diabetes Care 47. supl. 1) | 321 |
| ADA/APA 2004 | Consenso sobre antipsicóticos. obesidade e diabetes | 6 |
| | **Subtotal** | **679** |

## Cardiovascular

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| ACC/AHA 2022 | Diretriz de doença da aorta | 149 |
| AHA/ACC/HFSA 2022 | Diretriz de insuficiência cardíaca | 138 |
| SBC 2025 | Diretrizes brasileiras de hipertensão e de dislipidemias | 120 |
| AHA 2025 | Diretriz AHA/ACC de pressão arterial | 100 |
| SBC 2018 | Atualização das diretrizes brasileiras de prevenção e dislipidemias | 80 |
| ESC/EAS 2019 | Diretriz de dislipidemias | 78 |
| SVS 2018 | Diretriz de aneurisma de aorta abdominal | 76 |
| AHA/ACC 2024 | Diretriz de cardiomiopatia hipertrófica | 73 |
| EHRA 2021 | Guia prático de anticoagulantes orais diretos | 65 |
| AHA/ACC/HRS 2017 | Diretriz de síncope | 63 |
| ACC/AHA 2019 | Diretriz de prevenção primária | 51 |
| CHEST 2012 | Terapia antitrombótica. 9ª edição (sumário executivo) | 41 |
| AHA/ASA 2015 | Aneurismas intracranianos não rotos | 33 |
| HRS/EHRA/APHRS 2013 | Consenso de síndromes arrítmicas hereditárias | 32 |
| EAS 2022 | Consenso de lipoproteína(a) | 22 |
| AHA 2022 | Declaração científica | 15 |
| HRS 2007 (Goldschlager) | Guia prático de amiodarona | 10 |
| | **Subtotal** | **1.146** |

## Rim, pulmão e fígado

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| KDIGO 2025 (DRPAD) | Diretriz de doença renal policística autossômica dominante | 239 |
| GOLD COPD 2023 | Relatório GOLD | 205 |
| KDIGO 2024 | Diretriz de doença renal crônica | 198 |
| KDIGO 2009 (transplante) | Diretriz do receptor de transplante renal | 155 |
| ATS/ERS 2003 | Deficiência de alfa-1 antitripsina | 83 |
| AASLD 2018 | Hepatite B | 40 |
| AASLD 2023 | Doença hepática esteatótica | 39 |
| EASL 2022 | Hemocromatose | 24 |
| | **Subtotal** | **983** |

## HIV, infecções e vacinas

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| NIH/CDC HIV Guidelines · NIH 2024 | Diretrizes de terapia antirretroviral e de infecções oportunistas em adultos | 400 |
| MS 2019 (Manual de Tuberculose) | Manual de recomendações para o controle da tuberculose. 2ª edição | 364 |
| PCDT-IST MS 2022 | Protocolo clínico de infecções sexualmente transmissíveis | 211 |
| EACS 11.1 | Diretrizes europeias de HIV | 150 |
| MS Brasil PCDT HIV 2024 · MS 2024 | Protocolo clínico de manejo da infecção pelo HIV em adultos | 100 |
| CDC/ACIP 2022 e 2025 | Calendários e recomendações de vacinação do adulto | 40 |
| SBIm 2026/2027 | Calendários de vacinação do adulto. do idoso e de pacientes especiais | 20 |
| | **Subtotal** | **1.285** |

## Rastreamento e oncologia

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| NCCN 2024 e 2025 | Diretrizes de risco genético e familiar (mama. ovário. pâncreas. colorretal) e de rastreamento | 350 |
| EAU 2024 | Diretriz de câncer de próstata | 150 |
| USPSTF 2018 a 2025 | Declarações de recomendação (cerca de 15) | 135 |
| ACG 2015. 2019. 2021 e 2023 | Diretrizes de síndromes hereditárias gastrointestinais e de rastreamento | 100 |
| AUA/SUO 2023 | Detecção precoce do câncer de próstata | 30 |
| ACS 2007 | Ressonância de mamas no rastreamento | 15 |
| ASCO 2019 | Diretriz | 15 |
| USMSTF 2017 | Rastreamento do câncer colorretal | 15 |
| IGCLC 2020 | Câncer gástrico difuso hereditário | 12 |
| Kratz 2017 | Vigilância na síndrome de Li-Fraumeni | 8 |
| | **Subtotal** | **830** |

## Endocrinologia, osso e reumatologia

| Rótulo no motor | Documento | Páginas (aprox.) |
|---|---|---:|
| ATA 2014 | Hipotireoidismo | 82 |
| ATA 2016 | Hipertireoidismo | 79 |
| ASMBS 2019 | Nutrição no paciente bariátrico | 73 |
| NICE CG185 | Transtorno bipolar (versão resumida) | 58 |
| BHOF 2022 | Guia clínico de osteoporose | 54 |
| ATA 2015 | Carcinoma medular de tireoide | 44 |
| ACR 2020 | Saúde reprodutiva | 28 |
| Endocrine Society 2012 | Neoplasia endócrina múltipla tipo 1 | 22 |
| ASBMR 2016 | Uso prolongado de bisfosfonatos | 20 |
| BSR 2017 | Monitorização de imunossupressores | 20 |
| ACR 2021 | Artrite reumatoide | 16 |
| ACR 2022 | Vacinação em doenças reumáticas | 16 |
| ACR 2023 | Osteoporose induzida por corticoide | 15 |
| CGH 2025 (Feuerstein) | Corticoide na doença inflamatória intestinal: uso e complicações (revisão; Clin Gastroenterol Hepatol 23:2068-82) | 15 |
| Drugs Aging 2024 (Sparling) | Corticoide oral no idoso: como reduzir efeitos adversos (revisão; Drugs Aging 41:795-808) | 14 |
| | **Subtotal** | **556** |
