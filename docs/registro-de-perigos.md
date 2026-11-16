# Registro de perigos

Lista curta dos modos pelos quais o Evidens pode causar dano, o que controla cada um e
qual teste verifica o controle. É a referência para revisar mudanças: uma alteração que
toque em um controle precisa manter (ou substituir) o teste correspondente.

- **Controlado**: há controle no código e teste automatizado que falha se ele for removido.
- **Parcial**: há mitigação, mas o perigo não está eliminado.
- **Aberto**: conhecido e ainda não tratado.

Os testes ficam em `tests/` e rodam com `python -m pytest`.

## Controlados

| ID | Perigo | Causa encontrada | Controle | Verificação |
|---|---|---|---|---|
| P-01 | Documento que declara assinatura digital sem assinatura real, em nome de um médico identificado | Endpoints `/api/gerar-receita-vacinas` e `/api/gerar-solicitacao-exames` montavam o documento com nome e CRM fixos e conteúdo enviado pelo cliente, sem autenticação | Endpoints removidos; as rotas respondem 410. Os PDFs são minutas com campo de assinatura e carimbo e o aviso "Documento sem assinatura digital", exceto quando o médico abre a sessão no provedor do certificado ICP-Brasil: aí o PDF é assinado de fato (PAdES) e só então diz "Assinado digitalmente". Pedido de assinatura sem sessão, ou com falha no provedor, é recusado: nunca sai minuta no lugar do assinado nem frase de assinatura sem assinatura. A assinatura devolvida é conferida com o certificado antes de entrar no PDF | `test_documentos_legados.py`; `test_pdf.py::test_minuta_traz_campo_de_assinatura_e_nao_declara_assinatura_digital`; `test_assinatura.py` |
| P-02 | Vacina de vírus vivo atenuado (tríplice viral, varicela, febre amarela, dengue) ou HPV sugerida a gestante | `gestante` só alterava a vacina de VSR | Triagem de segurança aplicada como última etapa do motor (`src/utils/seguranca_vacinas.py`); o item sai da lista e aparece em `nao_incluidas` como contraindicado, com motivo | `test_vacinas_atenuadas.py::test_gestante_nao_recebe_atenuadas_nem_hpv` e o teste de invariantes sobre a grade de pacientes |
| P-03 | Vacina atenuada sugerida a pessoa imunossuprimida ou vivendo com HIV | Não havia regra de imunossupressão nem uso do CD4. Depois (auditoria C, 2026-11): corticoide sem dose, metotrexato/azatioprina em dose de baixo grau e oncológicos sem a marca de imunossupressão (pembrolizumabe, trastuzumabe) liberavam as vivas | Mesma triagem: imunossupressão "sim" e HIV com CD4 abaixo de 200 são contraindicação; HIV com CD4 a partir de 200 é precaução (não entra automaticamente); HIV sem CD4 é dado insuficiente. Pelas classes de medicação: corticoide sem dose e duração é dado insuficiente; metotrexato ≤ 0,4 mg/kg/semana e azatioprina ≤ 3 mg/kg/dia são precaução, com dengue contraindicada; tratamento sistêmico do câncer é precaução | `test_vacinas_atenuadas.py` (casos de HIV e imunossupressão); `test_vacinas_especiais.py` (C-03, C-05, C-06) |
| P-04 | Febre amarela ou dengue sugerida a nutriz; febre amarela sugerida a partir de 60 anos sem avaliação | Não havia pergunta sobre amamentação nem limite de idade | Mesma triagem: febre amarela contraindicada com criança menor de 6 meses e precaução a partir de 60 anos; dengue contraindicada na amamentação | `test_vacinas_atenuadas.py` (casos de nutriz e de 60 anos) |
| P-05 | Ausência de informação tratada como ausência de risco | Caixas de seleção e `data.get(campo, False)`: não marcado valia como "não" | Gestação, amamentação e imunossupressão têm três respostas; "não informado" retém as vacinas atenuadas como dado insuficiente. Tabagismo deixou de ter "nunca fumou" pré-selecionado | `test_validacao_entrada.py::TestTriagemDeTresValores`; `test_vacinas_atenuadas.py::test_triagem_nao_respondida_nao_vale_como_nao`; `test_site.py::test_tabagismo_exige_escolha_explicita` |
| P-06 | Risco cardiovascular errado apresentado como PREVENT | Servidor usava uma regressão de 6 termos que não é o PREVENT; a tela não recebia diabetes, tabagismo nem tratamento, e completava campos vazios com valores padrão | Implementação única no servidor (`src/utils/prevent.py`), coeficientes completos do PREVENT com o erratum de 2026 de HbA1c; não completa campo vazio (lista o que falta); recusa fora de 30–79 anos, fora das faixas de derivação, na gestação e com cardiopatia; a tela só exibe | `test_prevent.py` (8 vetores do preventr, 10 e 30 anos, os 5 desfechos); `test_site.py` (API = módulo, incompleto, não aplicável) |
| P-07 | Entrada impossível aceita (idade vazia derrubava a API; idade −5 ou 150 gerava recomendações) | Conversões diretas sem validação | `src/utils/validacao.py`: idade, sexo e tabagismo obrigatórios; faixas plausíveis para medidas e exames; resposta 400 com a lista de problemas | `test_validacao_entrada.py` |
| P-08 | Conteúdo enviado pelo navegador interpretado como HTML na geração do PDF | Templates sem escape; delimitador multipart fixo | Escape automático nos templates; delimitador aleatório por requisição; limites de quantidade e tamanho; erro do serviço de PDF não é repassado ao cliente | `test_pdf.py` |
| P-09 | PDF de vacinas impresso a partir de uma lista que não corresponde mais ao formulário | A lista ficava na tela depois de o formulário mudar. A segunda conferência só lia a resposta da triagem: com adalimumabe na lista e a triagem "Não", a febre amarela era impressa | A página descarta o resultado quando um dado clínico muda; o servidor confere de novo a triagem no pedido de PDF, agora com as comorbidades, as medicações (com dose, duração e peso) e a mesma implicação de imunossupressão das recomendações, e recusa a lista se houver vacina não liberada | `test_pdf.py` (segunda linha de defesa); `test_vacinas_especiais.py::test_pdf_recusa_viva_com_imunossupressao_das_listas` |
| P-10 | Dados de paciente gravados sem intenção | O endpoint tentava gravar nome e dados clínicos em banco a cada consulta | Gravação removida; o nome do paciente não é mais enviado com o pedido de recomendações e é opcional | `test_site.py::test_motor_nao_tem_acesso_a_banco_de_dados`; `test_site.py::test_nome_do_paciente_e_opcional_e_nao_vai_com_as_recomendacoes` |
| P-24 | Falso negativo silencioso por dado ausente | Fumante sem maços-ano informados não recebia rastreio de câncer de pulmão nem aviso de que faltava o dado; ex-fumante sem "anos desde que parou" era tratado como se tivesse acabado de parar | `src/utils/rastreio_cancer.py`: maços-ano ou anos desde a cessação ausentes não viram zero; a TC de baixa dose aparece em `nao_incluidas` como dados insuficientes, com o que falta (USPSTF 2021 / SBCT-SBPT-CBR 2024) | `test_rastreio_cancer.py::test_tc_de_baixa_dose_e_dado_ausente`; vinheta `h60_fumante_sem_macos_ano` |
| P-11 | Telas antigas e arquivos internos acessíveis por URL | Qualquer `.html`, `.js` ou `.json` do repositório era servido | Lista explícita de arquivos publicados em `api/index.py` | `test_site.py::test_arquivos_internos_e_telas_antigas_nao_sao_servidos` |
| P-G1 | Hipertensão na gestação tratada como HAS ambulatorial, sem alerta de pré-eclâmpsia nem de faixa grave (parte gestacional de P-17) | Na gestante, PA ≥ 140/90 marcava "HAS estágio 2 (AHA/ACC)" e disparava MAPA, ecocardiograma e exames "basais"; 165/112 não gerava alerta | Na gestação a PA não marca HAS (`coerencia.inferir`); `prenatal.classificar_pa` usa ≥ 140/90 e ≥ 160/110; com ≥ 20 semanas os exames de pré-eclâmpsia entram como investigação "Agora" (ACOG PB 222); faixa grave vira orientação urgente no topo (ACOG CO 767); itens de HAS de fora da gestação saem (`prenatal.fora_da_gestacao`) | `test_gestacao_e_saude_da_mulher.py` (E-01); `test_coerencia.py::test_pa_na_gestacao_nao_marca_hipertensao` |
| P-G2 | Prevenção de pré-eclâmpsia omitida ou fora da janela | Lúpus, SAF e doença renal não contavam como alto risco; fatores moderados ignorados; AAS sugerido com 34 semanas, dentro da descrição de um exame de urina | `prenatal.fatores_pre_eclampsia` (USPSTF 2021; FEBRASGO 2023) e `prenatal.orientacao_aas` por idade gestacional (não iniciar depois de 28 semanas), com aviso de divergência de dose | `test_gestacao_e_saude_da_mulher.py` (E-02, E-04, E-05) |
| P-G3 | Rastreio grau B omitido em mulheres jovens | Clamídia/gonococo só no pré-natal e no HIV | `prenatal.clamidia_fora_da_gestacao`: mulheres sexualmente ativas até 24 anos (USPSTF 2021, B); "não informado" não vale como "não"; aviso de divergência com o MS | `test_gestacao_e_saude_da_mulher.py` (E-03) |
| P-G4 | Regra de fora da gestação aplicada à gestante; exame repetido com outro nome (parte gestacional de P-18) | Carga viral "a cada 6 meses" na gestante com HIV; cálcio/vitamina D do diabético; HIV, HCV, HBsAg e toxoplasmose do check-up geral repetidos; adiados em dobro | `hiv.recomendar(gestante=True)` (FEBRASGO 2025); `prenatal.fora_da_gestacao` e `prenatal.adiar` (um aviso por título) | `test_gestacao_e_saude_da_mulher.py` (E-06, E-09, E-13) |

## Parciais

| ID | Perigo | Situação |
|---|---|---|
| P-12 | Serviço de PDF externo aceitava requisições de qualquer origem | Resolvido: os PDFs passaram a ser gerados dentro da própria função; não há mais serviço externo |
| P-13 | O PDF imprime a lista que o navegador envia | O conteúdo é validado, limitado e escapado, e as vacinas atenuadas são conferidas de novo, com a imunossupressão implicada pelas comorbidades e medicações enviadas. O servidor ainda não recalcula as recomendações a partir dos dados do paciente |
| P-16 | Rastreio sem idade de parada | Rastreamento de câncer: resolvido. PSA só de 55 a 69 anos por decisão compartilhada (40-69 com BRCA, 45-69 com pai ou irmão acometido) e, a partir de 70, em `nao_incluidas` como não recomendado (USPSTF D); mamografia até 74 anos (também na história familiar); colonoscopia e FIT até 75 (também na história familiar); vigilância por síndrome hereditária de câncer até 75; depois disso, orientação de decisão individual pela expectativa de vida (`test_rastreio_cancer.py`; vinhetas `h69`, `h70`, `h76`, `h88`). Continua aberto fora do câncer: Lp(a) aos 88 anos |
| P-14 | Nome do paciente trafega até o servidor e o serviço de PDF | Passou a ser opcional e só acompanha o pedido de PDF. Continua saindo do navegador quando informado |

## Abertos

| ID | Perigo | Exemplo observado |
|---|---|---|
| P-15 | Excesso de exames em pessoa assintomática | Homem de 25 anos hígido recebe glicemia, HbA1c, TOTG, perfil lipídico, Lp(a), creatinina, HIV, HCV e ECG |
| P-17 | Diagnóstico inferido de dado isolado | Uma PA de 132/80 marca hipertensão e dispara MAPA, ecocardiograma, potássio e ácido úrico |
| P-18 | Rastreio da própria doença em quem já tem o diagnóstico; item duplicado | Diabético recebe o rastreio de diabetes; albuminúria aparece duas vezes com nomes diferentes |
| P-19 | Vacina sugerida a quem já está vacinado | Não há entrada de histórico vacinal |
| P-20 | Regra diferente da fonte que ela cita | Aneurisma de aorta exige DPOC ou 10 maços-ano; título de HPV molecular com texto de citologia trienal; densitometria bienal |
| P-21 | Grau de evidência atribuído sem correspondência com a fonte | Graus digitados à mão em cada regra |
| P-22 | Diretriz desatualizada | As fontes citadas são de 2024 e 2025; não há data de revisão por regra |
| P-23 | Dado relevante coletado e ignorado | País, álcool, doença renal, história familiar de câncer e de cardiopatia |

## Critérios clínicos da triagem de vacinas

Os critérios implementados em `src/utils/seguranca_vacinas.py` são conservadores de propósito:
na dúvida, o item sai da lista automática e a decisão volta para o médico. Fontes usadas:
Calendários de vacinação SBIm 2026/2027 (adulto, idoso e gestante), Ministério da Saúde/PNI
(febre amarela em gestantes, nutrizes e idosos) e Manual dos CRIE, 6ª edição, 2023 (pessoas
vivendo com HIV e imunossuprimidos). Devem ser revistos a cada nova edição dessas fontes.

Pontos que dependem de decisão clínica do responsável pelo projeto:

- acima de 55 anos, gestação e amamentação sem resposta valem como "não se aplica";
- toda pessoa vivendo com HIV fica fora da lista automática de atenuadas, mesmo com CD4 alto;
- imunossupressão "sim" é tratada como contraindicação para todas as atenuadas, sem graduar a imunossupressão;
- metotrexato e azatioprina em dose de baixo grau não marcam "sim": as atenuadas ficam em precaução e a dengue, contraindicada (SBIm Pacientes Especiais 2026/2027; IN CNV 2026);
- corticoide sistêmico sem dose e duração retém as atenuadas como dado insuficiente;
- imunoterapia, anti-HER2 e demais oncológicos sem a marca de imunossupressão deixam as atenuadas em precaução;
- HIV com CD4 a partir de 350 continua em precaução (a SBIm considera imunossupressão leve ou ausente; o motivo diz isso);
- a vacina de dengue é tratada como contraindicada em qualquer fase da amamentação.
