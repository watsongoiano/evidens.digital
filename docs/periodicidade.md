# Periodicidade dos exames

O médico informa o exame que o paciente já fez e a data. O motor confere a periodicidade
da própria regra: o que ainda está em dia sai do pedido e aparece em "Itens não incluídos
automaticamente", com a data do exame e a data a partir da qual volta a ser indicado.

Esta é a etapa 1 (data digitada). A etapa 2 lê o laudo em PDF, por código e sem IA, e
preenche os mesmos campos; o laudo é lido em memória e descartado.

## De onde vem o intervalo

Nenhum intervalo novo foi criado. Cada recomendação do motor já traz a periodicidade no
subtítulo, ao lado da diretriz ("Diabéticos | A cada 3-6 meses", ADA). O módulo
`src/utils/periodicidade.py` só transforma esse texto em número. Regras de leitura, todas
conservadoras (na dúvida, o exame continua sendo pedido):

| O que a regra diz | O que o motor faz |
| --- | --- |
| Intervalo fixo ("Anual", "A cada 2 anos") | Adia até a data do exame mais o intervalo |
| Faixa ("A cada 3-6 meses", "A cada 4-6 anos") | Usa o limite inferior: só adia se foi feito há menos que o menor intervalo admitido |
| Uma vez ("Dose única na vida", "Pelo menos 1x na vida") | Feito uma vez, não repete |
| Sem intervalo ("Basal", "Conforme necessidade", pré-natal) | Não adia; mostra a data no cartão do exame e o médico decide |
| Duas indicações no mesmo exame ("Anual / Também: Em uso de lítio / A cada 6 meses") | Vale o menor intervalo; se uma delas não tem intervalo, não adia |
| "Junto da HbA1c" (glicemia do diabético) | Só é adiada se a HbA1c também estiver em dia |
| Intervalo vencido | Continua no pedido, com "Intervalo vencido desde ..." |

Meses e anos são de calendário (01/10 + 3 meses = 01/01).

## Como se sabe que é o mesmo exame

Pelo código TUSS (`src/utils/tuss.py`). "Hemograma completo" e "Hemograma completo com
plaquetas" são o mesmo código. Um exame combinado cobre as partes ("TGO e TGP" cobre a ALT
pedida sozinha); uma recomendação combinada só está em dia se todas as partes foram feitas, e
vale a data mais antiga entre elas. Exame sem código é comparado pelo nome.

## Na tela

Seção 08 do formulário, "Exames já realizados" (opcional): nome do exame, com sugestão da
lista, e a data. As datas vão ao servidor só para o cálculo e não são guardadas. Para pedir
mesmo assim um exame em dia, o médico retira a linha ou acrescenta o exame no diálogo do PDF.

## Situação atual das regras

Dos 280 pares exame + indicação de laboratório e imagem que o motor produz, 136 têm
periodicidade utilizável (131 com intervalo, 4 de uma única vez, 1 "junto da HbA1c"). Outros 36
são do pré-natal, onde manda a idade gestacional. Os 108 restantes não têm intervalo na
referência atual e por isso nunca são adiados:

| O que a regra diz hoje | Exames |
| --- | --- |
| Conforme necessidade | Doppler de artérias renais; Fósforo, soro; MAPA - Monitorização Ambulatorial da Pressão Arterial (24h); Metanefrinas, plasma ou urina de 24h; Polissonografia; Relação Aldosterona/Renina (A/R) |
| Antes ou no início do tratamento | Prova tuberculínica (PPD) ou IGRA |
| Antes do tratamento | Anticorpos anti-HBc total, soro; Antígeno HBs, soro |
| (só o grupo: Osteoporose) | 25-hidroxivitamina D, soro |
| (só o grupo: Em uso de inibidor de aromatase) | Densitometria óssea (DEXA) |
| Avaliação inicial ou falha virológica | Genotipagem do HIV (Teste de Resistência) |
| Avaliação inicial | Anticorpos anti-HBc total, soro; Anticorpos anti-HBs, soro; Antígeno HBs, soro |
| Periódico | Avaliação oftalmológica com tonometria e fundoscopia; Vitamina B12, soro |
| Basal e periódico | Colesterol total e frações, soro; Glicose, soro; Hemoglobina glicada (HbA1c), soro |
| Basal | 25-hidroxivitamina D, soro; Alanina aminotransferase, soro; Albumina, soro; Aspartato aminotransferase, soro; Bilirrubinas totais e frações, soro; Creatinina, soro; Cálcio iônico, soro; Fosfatase alcalina, soro; Hemograma completo com plaquetas; Potássio, soro; Sódio, soro; Ureia, soro |
| Durante o uso | MAPA - Monitorização Ambulatorial da Pressão Arterial (24h) |
| Até 6 meses do início | Densitometria óssea (DEXA) |
| Avaliação de fratura | Radiografia de coluna torácica e lombar (perfil) |
| Conforme indicação clínica | Gasometria arterial, sangue arterial; Radiografia de tórax |
| Conforme uso de medicações | Cloreto, soro |
| (só o grupo: Hipertireoidismo / antitireoidiano) | Hormônio Tireoestimulante (TSH), soro |
| (só o grupo: Deficiência de alfa-1 antitripsina na família) | Alfa-1 antitripsina, soro |
| (só o grupo: Aneurisma cerebral em 2 ou mais parentes de 1º grau) | Angiorressonância de crânio |
| (só o grupo: Doença da aorta torácica na família) | Ecocardiograma transtorácico |
| (só o grupo: Canalopatia na família) | Eletrocardiograma de repouso |
| (só o grupo: Doença celíaca na família) | Anticorpo antitransglutaminase tecidual IgA, soro; Imunoglobulina A (IgA), soro |
| Rastreio em cascata | Colesterol total e frações, soro; Ferritina, soro; Índice de saturação de transferrina, soro |
| (só o grupo: Morte súbita precoce na família) | Eletrocardiograma de repouso |
| Portador ou parente de 1º grau não testado | Endoscopia digestiva alta; Ultrassonografia de tireoide |
| Adulto em risco | Ultrassonografia de rins e vias urinárias |
| Alvo < 6 mg/dL | Ácido úrico, soro |
| Para confirmar o diagnóstico | TOTG-75g (Teste Oral de Tolerância à Glicose), soro |
| Reavaliação | Densitometria óssea (DEXA) |
| Não solicitar se >500 em 2 exames consecutivos com intervalo de 6 meses | Contagem de linfócitos T CD4+ |
| Portador ou parente de 1º grau não testado / A partir de 40 anos | PSA total, soro |
| A partir de 45 anos | PSA total, soro |
| Fator de risco | Densitometria óssea (DEXA) |

Para estes, o próximo passo é procurar em diretriz o intervalo de cada um e citar a fonte
antes de codificar. "Basal" e "Antes do tratamento" dependem do início do tratamento, que o
sistema não conhece: a data sozinha não diz se o exame serve como basal.

## Garantias

- Um teste percorre o motor e falha se aparecer periodicidade nova sem classificação
  (`tests/test_periodicidade.py`).
- Data no futuro, data inválida ou exame sem nome são recusados com mensagem.
- Vacinas não passam por esta regra (têm a triagem e o esquema próprios).
