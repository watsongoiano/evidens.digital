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
| P-01 | Documento que declara assinatura digital sem assinatura real, em nome de um médico identificado | Endpoints `/api/gerar-receita-vacinas` e `/api/gerar-solicitacao-exames` montavam o documento com nome e CRM fixos e conteúdo enviado pelo cliente, sem autenticação | Endpoints removidos; as rotas respondem 410. Os PDFs restantes são minutas com campo de assinatura e carimbo e o aviso "Documento sem assinatura digital" | `test_documentos_legados.py`; `test_pdf.py::test_minuta_traz_campo_de_assinatura_e_nao_declara_assinatura_digital` |
| P-02 | Vacina de vírus vivo atenuado (tríplice viral, varicela, febre amarela, dengue) ou HPV sugerida a gestante | `gestante` só alterava a vacina de VSR | Triagem de segurança aplicada como última etapa do motor (`src/utils/seguranca_vacinas.py`); o item sai da lista e aparece em `nao_incluidas` como contraindicado, com motivo | `test_vacinas_atenuadas.py::test_gestante_nao_recebe_atenuadas_nem_hpv` e o teste de invariantes sobre a grade de pacientes |
| P-03 | Vacina atenuada sugerida a pessoa imunossuprimida ou vivendo com HIV | Não havia regra de imunossupressão nem uso do CD4 | Mesma triagem: imunossupressão "sim" e HIV com CD4 abaixo de 200 são contraindicação; HIV com CD4 a partir de 200 é precaução (não entra automaticamente); HIV sem CD4 é dado insuficiente | `test_vacinas_atenuadas.py` (casos de HIV e imunossupressão) |
| P-04 | Febre amarela ou dengue sugerida a nutriz; febre amarela sugerida a partir de 60 anos sem avaliação | Não havia pergunta sobre amamentação nem limite de idade | Mesma triagem: febre amarela contraindicada com criança menor de 6 meses e precaução a partir de 60 anos; dengue contraindicada na amamentação | `test_vacinas_atenuadas.py` (casos de nutriz e de 60 anos) |
| P-05 | Ausência de informação tratada como ausência de risco | Caixas de seleção e `data.get(campo, False)`: não marcado valia como "não" | Gestação, amamentação e imunossupressão têm três respostas; "não informado" retém as vacinas atenuadas como dado insuficiente. Tabagismo deixou de ter "nunca fumou" pré-selecionado | `test_validacao_entrada.py::TestTriagemDeTresValores`; `test_vacinas_atenuadas.py::test_triagem_nao_respondida_nao_vale_como_nao`; `test_site.py::test_tabagismo_exige_escolha_explicita` |
| P-06 | Risco cardiovascular errado apresentado como PREVENT | Servidor usava uma regressão de 6 termos que não é o PREVENT; a tela não recebia diabetes, tabagismo nem tratamento, e completava campos vazios com valores padrão | Cálculo retirado da tela e do servidor; as duas implementações foram apagadas. Só volta com implementação única, validada contra os vetores de teste oficiais | `test_site.py` (risco desativado na API, na página e nos arquivos) |
| P-07 | Entrada impossível aceita (idade vazia derrubava a API; idade −5 ou 150 gerava recomendações) | Conversões diretas sem validação | `src/utils/validacao.py`: idade, sexo e tabagismo obrigatórios; faixas plausíveis para medidas e exames; resposta 400 com a lista de problemas | `test_validacao_entrada.py` |
| P-08 | Conteúdo enviado pelo navegador interpretado como HTML na geração do PDF | Templates sem escape; delimitador multipart fixo | Escape automático nos templates; delimitador aleatório por requisição; limites de quantidade e tamanho; erro do serviço de PDF não é repassado ao cliente | `test_pdf.py` |
| P-09 | PDF de vacinas impresso a partir de uma lista que não corresponde mais ao formulário | A lista ficava na tela depois de o formulário mudar | A página descarta o resultado quando um dado clínico muda; o servidor confere de novo a triagem no pedido de PDF e recusa a lista se houver vacina não liberada | `test_pdf.py` (segunda linha de defesa) |
| P-10 | Dados de paciente gravados sem intenção | O endpoint tentava gravar nome e dados clínicos em banco a cada consulta | Gravação removida; o nome do paciente não é mais enviado com o pedido de recomendações e é opcional | `test_site.py::test_motor_nao_tem_acesso_a_banco_de_dados`; `test_site.py::test_nome_do_paciente_e_opcional_e_nao_vai_com_as_recomendacoes` |
| P-11 | Telas antigas e arquivos internos acessíveis por URL | Qualquer `.html`, `.js` ou `.json` do repositório era servido | Lista explícita de arquivos publicados em `api/index.py` | `test_site.py::test_arquivos_internos_e_telas_antigas_nao_sao_servidos` |

## Parciais

| ID | Perigo | Situação |
|---|---|---|
| P-12 | Serviço de PDF externo aceitava requisições de qualquer origem | Resolvido: os PDFs passaram a ser gerados dentro da própria função; não há mais serviço externo |
| P-13 | O PDF imprime a lista que o navegador envia | O conteúdo é validado, limitado e escapado, e as vacinas atenuadas são conferidas de novo. O servidor ainda não recalcula as recomendações a partir dos dados do paciente |
| P-14 | Nome do paciente trafega até o servidor e o serviço de PDF | Passou a ser opcional e só acompanha o pedido de PDF. Continua saindo do navegador quando informado |

## Abertos

| ID | Perigo | Exemplo observado |
|---|---|---|
| P-15 | Excesso de exames em pessoa assintomática | Homem de 25 anos hígido recebe glicemia, HbA1c, TOTG, perfil lipídico, Lp(a), creatinina, HIV, HCV e ECG |
| P-16 | Rastreio sem idade de parada | Homem de 88 anos recebe PSA e Lp(a) |
| P-17 | Diagnóstico inferido de dado isolado | Uma PA de 132/80 marca hipertensão e dispara MAPA, ecocardiograma, potássio e ácido úrico |
| P-18 | Rastreio da própria doença em quem já tem o diagnóstico; item duplicado | Diabético recebe o rastreio de diabetes; albuminúria aparece duas vezes com nomes diferentes |
| P-19 | Vacina sugerida a quem já está vacinado | Não há entrada de histórico vacinal |
| P-20 | Regra diferente da fonte que ela cita | Aneurisma de aorta exige DPOC ou 10 maços-ano; PSA anual a partir dos 50; título de HPV molecular com texto de citologia trienal; densitometria bienal |
| P-21 | Grau de evidência atribuído sem correspondência com a fonte | Graus digitados à mão em cada regra |
| P-22 | Diretriz desatualizada | As fontes citadas são de 2024 e 2025; não há data de revisão por regra |
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
