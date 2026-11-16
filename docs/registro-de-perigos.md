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
| P-03 | Vacina atenuada sugerida a pessoa imunossuprimida ou vivendo com HIV | Não havia regra de imunossupressão nem uso do CD4 | Mesma triagem: imunossupressão "sim" e HIV com CD4 abaixo de 200 são contraindicação; HIV com CD4 a partir de 200 é precaução (não entra automaticamente); HIV sem CD4 é dado insuficiente | `test_vacinas_atenuadas.py` (casos de HIV e imunossupressão) |
| P-04 | Febre amarela ou dengue sugerida a nutriz; febre amarela sugerida a partir de 60 anos sem avaliação | Não havia pergunta sobre amamentação nem limite de idade | Mesma triagem: febre amarela contraindicada com criança menor de 6 meses e precaução a partir de 60 anos; dengue contraindicada na amamentação | `test_vacinas_atenuadas.py` (casos de nutriz e de 60 anos) |
| P-05 | Ausência de informação tratada como ausência de risco | Caixas de seleção e `data.get(campo, False)`: não marcado valia como "não" | Gestação, amamentação e imunossupressão têm três respostas; "não informado" retém as vacinas atenuadas como dado insuficiente. Tabagismo deixou de ter "nunca fumou" pré-selecionado | `test_validacao_entrada.py::TestTriagemDeTresValores`; `test_vacinas_atenuadas.py::test_triagem_nao_respondida_nao_vale_como_nao`; `test_site.py::test_tabagismo_exige_escolha_explicita` |
| P-06 | Risco cardiovascular errado apresentado como PREVENT | Servidor usava uma regressão de 6 termos que não é o PREVENT; a tela não recebia diabetes, tabagismo nem tratamento, e completava campos vazios com valores padrão | Implementação única no servidor (`src/utils/prevent.py`), coeficientes completos do PREVENT com o erratum de 2026 de HbA1c; não completa campo vazio (lista o que falta); recusa fora de 30–79 anos, fora das faixas de derivação, na gestação e com cardiopatia; a tela só exibe | `test_prevent.py` (8 vetores do preventr, 10 e 30 anos, os 5 desfechos); `test_site.py` (API = módulo, incompleto, não aplicável) |
| P-07 | Entrada impossível aceita (idade vazia derrubava a API; idade −5 ou 150 gerava recomendações) | Conversões diretas sem validação | `src/utils/validacao.py`: idade, sexo e tabagismo obrigatórios; faixas plausíveis para medidas e exames; resposta 400 com a lista de problemas | `test_validacao_entrada.py` |
| P-08 | Conteúdo enviado pelo navegador interpretado como HTML na geração do PDF | Templates sem escape; delimitador multipart fixo | Escape automático nos templates; delimitador aleatório por requisição; limites de quantidade e tamanho; erro do serviço de PDF não é repassado ao cliente | `test_pdf.py` |
| P-09 | PDF de vacinas impresso a partir de uma lista que não corresponde mais ao formulário | A lista ficava na tela depois de o formulário mudar | A página descarta o resultado quando um dado clínico muda; o servidor confere de novo a triagem no pedido de PDF e recusa a lista se houver vacina não liberada | `test_pdf.py` (segunda linha de defesa) |
| P-10 | Dados de paciente gravados sem intenção | O endpoint tentava gravar nome e dados clínicos em banco a cada consulta | Gravação removida; o nome do paciente não é mais enviado com o pedido de recomendações e é opcional | `test_site.py::test_motor_nao_tem_acesso_a_banco_de_dados`; `test_site.py::test_nome_do_paciente_e_opcional_e_nao_vai_com_as_recomendacoes` |
| P-11 | Telas antigas e arquivos internos acessíveis por URL | Qualquer `.html`, `.js` ou `.json` do repositório era servido | Lista explícita de arquivos publicados em `api/index.py` | `test_site.py::test_arquivos_internos_e_telas_antigas_nao_sao_servidos` |
| P-17 | Diagnóstico inferido de dado isolado | Uma PA de 132/80 marcava hipertensão e disparava MAPA, ecocardiograma, potássio e ácido úrico | Uma PA de consultório isolada não rotula HAS (SBC 2025; AHA/ACC 2025): fora da gestação só a PA ≥ 180/110 marca a caixa. PA ≥ 130/80 sem HAS conhecida vira o estado "PA alterada, HAS a confirmar", que pede só MRPA ou MAPA e orienta repetir a PA; o bloco de HAS só entra com HAS marcada, anti-hipertensivo em uso ou PA ≥ 180/110. A categoria SBC aparece ao lado da AHA (`pa_classificacao.sbc`) e, na faixa 130-139/80-89, como aviso de divergência. Mesma regra na tela (`intelligent-tools.html`) | `test_coerencia.py::test_pa_isolada_so_marca_has_a_partir_de_180_110`, `test_pa_alterada_sem_has_fica_a_confirmar`, `test_api_pa_alterada_pede_so_mrpa_ou_mapa`, `test_api_bloco_de_has_so_com_has_confirmada`; `test_rastreamento_geral.py` |
| P-18 | Rastreio da própria doença em quem já tem o diagnóstico; item duplicado | Diabético recebia o rastreio de diabetes; albuminúria, anti-HCV, hemograma, EAS, sódio/potássio, hepatite B e fundo de olho saíam duas vezes com nomes diferentes | Glicemia e HbA1c do diabético são de controle. A deduplicação final (`deduplicar_recomendacoes`) agrupa pelo código TUSS: sinônimos viram um item (título preferido em `tuss.TITULO_PREFERIDO`) e o exame pedido sozinho entra no combinado que o contém ("Potássio" em "Sódio e potássio", "Antígeno HBs" no painel de hepatite B); exames sem código que são o mesmo pedido estão em `tuss.MESMO_EXAME_SEM_CODIGO`. O item que fica mostra todos os motivos e todas as fontes com link | `test_rastreamento_geral.py::test_mesmo_exame_com_nomes_diferentes_sai_uma_vez`, `test_deduplicacao_por_codigo_une_sinonimos_e_absorve_o_exame_no_combinado`; `test_recomendacoes.py::test_diabetico_nao_recebe_totg_e_a_glicemia_vira_acompanhamento` |

## Parciais

| ID | Perigo | Situação |
|---|---|---|
| P-12 | Serviço de PDF externo aceitava requisições de qualquer origem | Resolvido: os PDFs passaram a ser gerados dentro da própria função; não há mais serviço externo |
| P-13 | O PDF imprime a lista que o navegador envia | O conteúdo é validado, limitado e escapado, e as vacinas atenuadas são conferidas de novo. O servidor ainda não recalcula as recomendações a partir dos dados do paciente |
| P-14 | Nome do paciente trafega até o servidor e o serviço de PDF | Passou a ser opcional e só acompanha o pedido de PDF. Continua saindo do navegador quando informado |
| P-15 | Excesso de exames em pessoa assintomática | Rastreamento geral corrigido (relatório de auditoria A): ECG, creatinina, glicemia e HbA1c deixaram de ser universais. O adulto hígido de 25 anos recebe perfil lipídico, Lp(a), anti-HIV, anti-HCV e o painel de hepatite B (cada um com fonte); glicemia/HbA1c a partir dos 35 anos ou com IMC ≥ 25 e fator de risco (ADA 2026); creatinina e uACR com fator de risco para DRC (KDIGO 2024). Falta revisar os rastreios das demais áreas |
| P-16 | Rastreio sem idade de parada | Lp(a) só até 75 anos; perfil lipídico a partir dos 76 vira decisão individual; rastreio automático de diabetes para aos 70 (com aviso da divergência com a ADA). O PSA é da área de oncologia |
| P-20 | Regra diferente da fonte que ela cita | Corrigidos: aneurisma de aorta (homem de 65-75 anos que já fumou, USPSTF 2019) e densitometria (sem intervalo fixo; mulher pós-menopausa < 65 anos com fator de risco; homem só pela BHOF). PSA e HPV ficam com as respectivas áreas |
| P-22 | Diretriz desatualizada | Rastreamento geral com as fontes vigentes e link direto: ADA 2026, ACC/AHA 2026 (dislipidemia), MS 2026 (PCDT Hepatite C), CDC 2023 (hepatite B), USPSTF 2019-2025. Continua sem data de revisão por regra |

## Abertos

| ID | Perigo | Exemplo observado |
|---|---|---|
| P-19 | Vacina sugerida a quem já está vacinado | Não há entrada de histórico vacinal |
| P-21 | Grau de evidência atribuído sem correspondência com a fonte | Graus digitados à mão em cada regra |
| P-23 | Dado relevante coletado e ignorado | País, álcool, doença renal, história familiar de câncer e de cardiopatia |
| P-24 | Falso negativo silencioso por dado ausente | Fumante sem maços-ano informados não recebe rastreio de câncer de pulmão nem aviso de que falta o dado |

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
- a vacina de dengue é tratada como contraindicada em qualquer fase da amamentação.
