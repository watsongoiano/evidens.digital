# Guia do plano de saúde (SP/SADT)

Vínculo com os planos de saúde, etapa 1: o pedido de exames sai acompanhado da guia
SP/SADT do plano, preenchida. O envio eletrônico da autorização à operadora é a etapa 2
e ainda não existe.

## Como funciona

1. **Minha conta → Planos de saúde.** O médico (ou residente) cadastra cada plano em que é
   credenciado: nome da operadora, registro ANS (opcional), o seu código na operadora (ou
   CPF/CNPJ do contrato), o nome do contratado (clínica ou o próprio nome) e o CBO (opcional).
   Estudante não tem essa seção. **Nenhuma senha de operadora é pedida nem guardada.**
2. **Ao gerar o PDF de exames** (laboratório ou imagem), o diálogo mostra "Guia do plano de
   saúde" para quem tem plano cadastrado. Escolhido o plano, pede o número da carteira do
   paciente e a indicação clínica, que já vem sugerida ("Check-up — 65 anos, diabetes tipo 2,
   hipertensão") e pode ser reescrita. Sem plano escolhido, o PDF sai como sempre.
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

A tabela oficial vigente é a da ANS (consulta pública das terminologias do padrão TISS),
que não pôde ser baixada daqui. Cada código foi localizado, com a descrição
correspondente, em tabelas TUSS publicadas por terceiros:

- lista TUSS de 2017 de um repositório público (4.146 termos), usada para conferir 121 dos
  123 códigos;
- tabelas publicadas por operadoras e órgãos públicos para os dois restantes e para a
  redação atual das descrições ("pesquisa e/ou dosagem"): Unimed Assis (exames simples),
  Unimed BH (códigos de patologia), Unimed Curitiba (exames sem autorização prévia),
  TRF5 (exames periódicos, 2023), TRE-PA e Fundação Copel.

Limites conhecidos: operadoras podem exigir código próprio para alguns itens; a escolha
entre códigos próximos (teste ergométrico convencional × computadorizado, antibiograma
manual × automatizado, mamografia digital) segue o mais comum e pode precisar de ajuste por
plano. **Antes de usar com um plano, vale conferir uma guia impressa com a tabela dele.**

## Limites desta etapa

- Não há envio eletrônico nem consulta de elegibilidade: a guia é para imprimir ou
  transcrever no autorizador da operadora.
- A guia é o formulário genérico do padrão TISS, sem o logotipo da operadora. Planos que
  exigem formulário próprio ou guia numerada por eles vão precisar de modelo específico.
- Cinco procedimentos por guia: um check-up com muitos exames gera várias guias.
