# Guia do plano de saúde (SP/SADT)

Vínculo com os planos de saúde, etapa 1: o pedido de exames sai acompanhado da guia
SP/SADT do plano, preenchida. O envio eletrônico da autorização à operadora é a etapa 2
e ainda não existe.

## Como funciona

1. **Minha conta → Planos de saúde.** O médico (ou residente) cadastra cada plano em que é
   credenciado: nome da operadora, registro ANS (opcional), o seu código na operadora (ou
   CPF/CNPJ do contrato), o nome do contratado (clínica ou o próprio nome) e o CBO (opcional).
   Estudante não tem essa seção. **Nenhuma senha de operadora é pedida nem guardada.**
2. **Na identificação do paciente** (seção 01 do check-up), quem tem plano cadastrado escolhe
   o plano do paciente e informa o número da carteira. Sem plano escolhido ("Particular"), o
   PDF sai como sempre. Plano e carteira não entram no cálculo das recomendações.
   **Ao gerar o PDF de exames** (laboratório ou imagem), o diálogo repete o plano e a
   carteira, que ainda podem ser corrigidos ali, e traz a indicação clínica sugerida
   ("Check-up — 65 anos, diabetes tipo 2, hipertensão"), que pode ser reescrita.
   **Troca de paciente:** se os dados clínicos ou o nome mudam depois de um resultado, o plano
   e a carteira continuam na tela, mas pedem confirmação ("ainda são deste paciente?"). A
   guia não sai enquanto o médico não confirmar, corrigir ou limpar.
3. **O PDF** traz o pedido carimbável na primeira página e, em seguida, a guia SP/SADT
   (paisagem), com cinco procedimentos por guia, como no formulário impresso do padrão.

O número da carteira e a indicação clínica só passam pelo servidor para entrar no PDF; não
são gravados. Quem não tem plano cadastrado vê um convite para cadastrar.

## O que a guia traz

Campos do padrão TISS (ANS) preenchidos: 1 (registro ANS), 8 (carteira), 10 (nome),
12 (atendimento a RN: N), 13 e 14 (código e nome do contratado), 15 a 19 (profissional
solicitante, conselho, número, UF, CBO), 21 (caráter: eletivo), 22 (data), 23 (indicação
clínica) e 24 a 27 (tabela 22, código TUSS, descrição, quantidade). Senha, validade,
autorização (campos 3 a 7 e 28) e os dados do executante (29 em diante) ficam em branco:
são da operadora e de quem executa o exame.

A guia sai sempre em português, mesmo com o site em inglês: é um formulário brasileiro.

## Códigos TUSS

`src/utils/tuss.py` liga cada título de exame do motor e do catálogo ao código da TUSS 22.
Regras:

- **Nada de código inventado.** Exame sem código conferido fica em `SEM_CODIGO`, com o
  motivo, e sai na guia com o código em branco. O mesmo vale para item digitado à mão.
- Título que reúne vários exames vira uma linha por código (o perfil lipídico sai como
  colesterol total, HDL, LDL e triglicerídeos).
- Código "por lado" (RM de mama, Doppler arterial de membro inferior) sai com quantidade 2.
- Ultrassonografia de vias urinárias depende do sexo do paciente.
- Quando o pedido aceita dois exames ("PPD ou IGRA", "plasma ou urina de 24 h",
  "treponêmico ou VDRL"), a guia leva o código do primeiro que tem código conferido.
- O mesmo código pedido duas vezes sai numa linha só.

Um teste impede que um exame novo entre no motor ou no catálogo sem código nem motivo
(`tests/test_guia_do_plano.py`).

### Como os códigos foram conferidos

- **Laboratório, códigos 40301010 a 40314030:** planilha TUSS_LABORATORIO do responsável
  clínico (correlação THM, LPM e CBHPM com a TUSS), guardada em
  `src/data/tuss_laboratorio.json` com 859 exames. Dos 68 códigos dessa faixa usados pelo
  Evidēns, 67 conferem com ela; a exceção é o sangue oculto imunológico (40303250), que é
  mais novo que a planilha e foi conferido na tabela da Unimed BH.
- **Hormônios (40316...), biologia molecular depois de 40314030, imagem e métodos:** a
  planilha não cobre. Foram localizados, com a descrição, numa lista TUSS pública de 2017 e
  em tabelas publicadas por operadoras e órgãos públicos (Unimed Assis, Unimed BH, Unimed
  Curitiba, TRF5, TRE-PA, Fundação Copel).
- A planilha traz duas descrições para o código 40310434 ("Antígenos bacterianos / vários
  materiais" e "Leishmania, pesquisa"); ficou a segunda, que confere com a lista de 2017.

A tabela oficial vigente é a da ANS (consulta pública das terminologias do padrão TISS), que
não pôde ser baixada daqui. Operadoras podem exigir código próprio para alguns itens; a
escolha entre códigos próximos (teste ergométrico convencional × computadorizado,
antibiograma manual × automatizado, mamografia digital) segue o mais comum e pode precisar de
ajuste por plano. **Antes de usar com um plano, vale conferir uma guia impressa com a tabela
dele.**

### Exames da tabela no catálogo

Os exames da planilha entram no catálogo do que o médico pode acrescentar ao pedido de
laboratório, com o nome da própria TUSS (`src/utils/catalogo.py`). Regras:

- o exame que já estava no catálogo com o nome do Evidēns não entra de novo ("Creatinina" da
  TUSS é a "Creatinina, soro" que já existe);
- o cálcio total (40301400) fica de fora: o cálcio dos pedidos é sempre o iônico;
- no site em inglês esses nomes continuam em português, porque é com eles que o exame sai
  na guia do plano;
- o nome da TUSS também é reconhecido em "Exames já realizados".

## Limites desta etapa

- Não há envio eletrônico nem consulta de elegibilidade: a guia é para imprimir ou
  transcrever no autorizador da operadora.
- A guia é o formulário genérico do padrão TISS, sem o logotipo da operadora. Planos que
  exigem formulário próprio ou guia numerada por eles vão precisar de modelo específico.
- Cinco procedimentos por guia: um check-up com muitos exames gera várias guias.
