# Cadastro de pacientes

Fases 1 e 2 (novembro de 2026): **servidor e tela, só para o administrador.** O cadastro está no ar para ser
testado antes de abrir a todos. Código em `src/utils/pacientes.py` (regras, cifra, banco) e
`src/routes/pacientes.py` (rotas); tabelas em `src/utils/contas.py`; tela em `pacientes.html`,
`static/pacientes.js` e `static/pacientes-checkup.js` (seção "Tela", abaixo); testes em `tests/test_pacientes.py`
e `tests/test_pacientes_tela.py`.

É a única exceção à regra "nenhum dado de paciente é gravado". **Para o usuário comum nada mudou:** o check-up, o
pré-operatório, os PDFs (pedidos, guia SP/SADT, laudo de APAC) e as operadoras continuam recebendo os dados,
calculando e descartando. Os Termos de Uso v2.0, a home e a página de cadastro continuam dizendo isso, e continuam
verdadeiros para quem não é o administrador. A lista do que precisa mudar antes de abrir está no fim desta página.

> **Só dados fictícios, por enquanto.** Enquanto os Termos de Uso e a home não forem atualizados, a fase de testes
> (API e tela) só pode ser usada com dados fictícios (pacientes inventados, CPF e CNS gerados para teste), inclusive pelo administrador.
> Os textos publicados ainda dizem que nenhum dado de paciente é gravado, e as obrigações da LGPD não dependem de
> quantas contas usam o cadastro: base legal, encarregado e retenção valem desde o primeiro paciente real, mesmo
> que ele seja só do administrador. Ver "LGPD e uso na fase 1", abaixo.

## O que é guardado

Um registro por paciente, sempre de uma conta (a que cadastrou). Só `nome` é obrigatório.

| Campo | Regra | Como fica guardado |
|---|---|---|
| `nome` | 2 a 150 caracteres | texto |
| `nome_social` | até 150 | texto |
| `nascimento` | `AAAA-MM-DD`, de 1900 até hoje | `AAAA-MM-DD` |
| `sexo` | `masculino` ou `feminino` | minúsculas |
| `cpf` | 11 dígitos com os dois verificadores corretos; com ou sem pontuação | só dígitos |
| `cns` | 15 dígitos válidos (a mesma conferência do laudo de APAC, `contas.cns_valido`) | só dígitos |
| `mae` | até 120 | texto |
| `raca` | `branca`, `preta`, `parda`, `amarela` ou `indigena` (aceita maiúsculas e acento) | a chave |
| `prontuario` | até 20 | texto |
| `responsavel` | até 120 | texto |
| `telefone` | até 20 | texto |
| `email` | e-mail válido, até 254 | minúsculas |
| `cep` | 8 dígitos; com ou sem hífen | só dígitos |
| `endereco` | até 150 | texto |
| `municipio` | até 60 | texto |
| `ibge` | 7 dígitos | só dígitos |
| `uf` | sigla de um estado | maiúsculas |
| `planos` | lista de até 5 itens `{operadora, carteira, validade}`: operadora obrigatória (2 a 80), carteira até 30, validade `AAAA-MM` ou `AAAA-MM-DD` | lista |
| `ficha` | objeto livre com o retrato do formulário do check-up (peso, altura, PA, comorbidades, medicações…): cada valor é texto, número, sim/não, vazio ou lista desses; até 64 KB em JSON | como veio |

- Os tetos de `nome`, `mae`, `telefone`, `endereco`, `municipio`, `prontuario` e `responsavel` são os mesmos do
  pedido em PDF e do laudo de APAC (um teste confere que continuam iguais). `carteira` e `operadora` seguem a guia
  do plano e o credenciamento.
- Chave que não está na tabela é recusada (também dentro de cada plano). Texto maior que o teto é recusado, não
  cortado.
- O servidor não interpreta a `ficha`: só confere a forma e o tamanho. Lista de objetos não é aceita; por isso
  `exames_anteriores`, que o formulário do check-up monta a partir dos laudos lidos, não cabe na ficha como está.
- A `ficha` recusa as chaves `__proto__`, `constructor` e `prototype` (400), com ou sem espaços em volta. Ela só
  tem um nível (objeto dentro de objeto já é recusado), então a conferência vale para a ficha inteira; fora da
  ficha, chave que não está na tabela é recusada de qualquer modo. **Na tela**: mostrar nomes e valores da ficha, e
  qualquer outro campo do paciente, só com `textContent` (nunca `innerHTML` nem montagem de HTML por texto), e não
  copiar a ficha para dentro de outro objeto com chaves vindas do servidor sem conferir.
- O `email` não aceita caractere de controle, caractere invisível nem substituto solto (400), e o tamanho é
  conferido antes do formato.
- A raça/cor não tinha lista no sistema (o laudo de APAC aceita texto livre de até 20 caracteres). O cadastro usa
  as cinco categorias do IBGE que os formulários do SUS adotam; `pacientes.RACAS` traz o rótulo de cada chave.

## Como é cifrado

- **Tabela `pacientes`**: `id`, `usuario_id` (o dono), `dados`, `indice_cns`, `indice_cpf`, `criado_em`,
  `atualizado_em`. Nenhuma coluna tem dado de paciente em claro, nem o nome.
- **`dados`** é `v1:` seguido de um texto Fernet (AES-128-CBC com HMAC-SHA256, da biblioteca `cryptography`, a
  mesma primitiva que já cifra o token da assinatura digital). O que é cifrado é um JSON com todos os campos e o
  número da conta dona e o número do registro. Por isso uma linha copiada para outra conta direto no banco não
  abre, nem um texto cifrado trocado de linha dentro da mesma conta (resposta 500, `ilegivel`).
- **Chave própria**: `PACIENTES_CHAVE`, uma variável de ambiente só do cadastro, separada da chave de sessão
  (`SECRET_KEY`, que assina o cookie de login). Quem obtiver a chave de sessão não abre os pacientes, e trocar a
  chave de sessão não mexe no cadastro. Dela derivam, por HMAC-SHA256, duas chaves, uma para cada uso:
  `evidens-pacientes-v1` (cifra) e `evidens-pacientes-indice-v1` (índices).
- **Como criar a chave**: gere um texto aleatório de pelo menos 32 caracteres com um gerador de senhas (o do
  gerenciador de senhas, por exemplo) e cadastre-o como `PACIENTES_CHAVE` nas variáveis de ambiente da hospedagem
  (Vercel → Settings → Environment Variables), só nos ambientes que vão usar o cadastro. Não reaproveite o valor
  da `SECRET_KEY` nem de outra variável, não o escreva em arquivo do repositório, em mensagem ou em chamado, e
  guarde uma cópia em lugar seguro fora da hospedagem.
- **Perder a chave** (apagar a variável sem ter cópia) torna todos os registros gravados ilegíveis para sempre:
  não há como recuperar os dados sem ela. Trocar o valor tem o mesmo efeito enquanto o valor antigo não voltar.
- **`indice_cns` e `indice_cpf`**: HMAC-SHA256 de `conta:campo:número`, nulos quando o número não foi informado.
  Servem só para achar duplicado: um índice único no banco recusa o segundo paciente com o mesmo CNS ou o mesmo
  CPF **na mesma conta**, inclusive em duas gravações simultâneas. O mesmo número em duas contas dá índices
  diferentes, então o banco não revela que duas contas atendem a mesma pessoa.
- **Sem `PACIENTES_CHAVE`**, com menos de 32 caracteres, com o mesmo valor da `SECRET_KEY` ou com a chave padrão
  de desenvolvimento, o cadastro fica indisponível: erro `CadastroIndisponivel`, resposta 503 com
  `codigo: "sem_chave"`. O cadastro nunca usa a `SECRET_KEY` no lugar, e nada é gravado em claro
  "provisoriamente". O resto do sistema funciona sem essa variável.

## Quem acessa

- A regra fica em um lugar só: `pacientes.habilitado_para(usuario)`. Hoje ela só aceita o administrador.
- Toda rota passa pela mesma porta (`exigir_cadastro`, em `src/routes/pacientes.py`), que hoje aplica
  `exigir_administrador`: sem login, 401; conta comum, 403; Termos pendentes, 403; sem banco ou sem chave, 503.
- **Posse por conta**: cada paciente é da conta que o cadastrou. O registro de outra conta responde 404, como se
  não existisse, também para o administrador. Não existe leitura "de todos".
- Pedido vindo de outro site é recusado (403), também nas leituras. As respostas saem com
  `Cache-Control: no-store`.
- **Cabeçalho próprio**: todo pedido, de leitura ou de gravação, tem de levar `X-Requested-With: evidens`; sem
  ele a resposta é 403, mesmo com a sessão do administrador. Soma-se à conferência de origem: um link, um
  formulário ou uma imagem em outro site não conseguem mandar esse cabeçalho, e um `fetch` de outro site só o
  mandaria com permissão do servidor (CORS), que não é dada. A tela manda o cabeçalho em todas as
  chamadas; abrir `/api/pacientes/<id>/exportar` como link comum não funciona, o arquivo tem de ser baixado por
  `fetch`.
- As respostas de erro trazem só frases fixas: nunca repetem o que foi enviado, nem o nome de uma chave recusada.
- As respostas destas rotas não passam pelo tradutor para o inglês (ele mexeria em campos da ficha chamados
  `mensagem`, `error` ou `erros`). As mensagens ficam em português, como no painel do administrador.

## API

Todas em `/api`, com a sessão do administrador e o cabeçalho `X-Requested-With: evidens`. Corpo e resposta em JSON. Datas de registro (`criado_em`,
`atualizado_em`, `exportado_em`) são segundos desde 1970 (UTC).

| Rota | O que faz | Resposta |
|---|---|---|
| `GET /api/pacientes` | Lista inteira da conta, em ordem alfabética (sem filtro) | 200 `{pacientes, total, truncado, ilegiveis}` |
| `POST /api/pacientes/buscar` com `{busca}` | A lista filtrada; o termo vai só no corpo | 200, igual à lista |
| `POST /api/pacientes` com os campos | Cria | 201 `{ok, paciente, mensagem}` |
| `GET /api/pacientes/<id>` | Lê | 200 `{paciente}` |
| `POST /api/pacientes/<id>` com os campos a trocar | Atualiza | 200 `{ok, paciente, mensagem}` |
| `POST /api/pacientes/<id>/excluir` | Apaga | 200 `{ok}` |
| `GET /api/pacientes/<id>/exportar` | Baixa tudo em JSON | 200, arquivo `paciente-<id>.json` |

- **Item da lista**: só `id`, `nome`, `nascimento`, `sexo`, `cns_final` (os 4 últimos dígitos do CNS) e
  `atualizado_em`. Saem até 500; `total` conta todos os que combinam e `truncado` diz se passou de 500.
  `ilegiveis` conta os registros que não abriram com a chave atual.
- **Busca**: palavras procuram no nome e no nome social, sem diferenciar maiúsculas nem acentos, e todas têm de
  aparecer. Um termo só de algarismos procura pelo final do CNS. Sem termo, vêm todos. A busca existe só em
  `POST /api/pacientes/buscar`: `GET /api/pacientes?busca=…` não existe mais e responde 400, para o termo (um
  nome) nunca ir no endereço, que costuma ficar nos registros de acesso da hospedagem.
- **`paciente`**: `id`, `criado_em`, `atualizado_em` e todos os campos da tabela acima. O que não foi informado vem
  como `""` (`planos` como `[]`, `ficha` como `{}`). Cada plano vem com as três chaves.
- **Atualizar** troca os campos enviados e mantém os outros. Campo enviado como `""` ou `null` é apagado (o nome
  não pode ser apagado). `planos` e `ficha`, quando enviados, substituem os anteriores por inteiro.
- **Dois pedidos ao mesmo tempo sobre o mesmo paciente**: em Postgres (produção) a edição lê a linha com
  `SELECT … FOR UPDATE`, e o segundo pedido espera o primeiro terminar e parte do que ele gravou. Nos dois bancos
  o servidor confere quantas linhas o `UPDATE` alcançou. Se o paciente foi excluído entre a leitura e a gravação,
  a edição responde 404, sem "Paciente salvo." e sem linha `editar` na trilha depois de `excluir`. Se o registro
  mudou nesse intervalo (só acontece em sqlite, que não tem a trava), responde 409 com `codigo: "conflito"` e nada
  é gravado: a tela deve reler o paciente e repetir a alteração.
- **Versão do registro (`atualizado_em`) na edição**: quem edita pode enviar, junto com os campos, o
  `atualizado_em` que recebeu ao ler o paciente. Se o registro foi alterado depois dessa leitura (outra aba, o
  check-up), a edição responde 409 com `codigo: "conflito"` e nada é gravado, para um formulário aberto há tempo
  não sobrescrever a mudança feita em outro lugar. Sem o campo, a edição vale como antes. O valor tem de ser o
  número recebido (outra coisa é 400); não é campo do paciente e não é aceito na criação. Cada edição avança o
  `atualizado_em` em pelo menos 1 segundo, de modo que duas edições no mesmo segundo ficam com versões diferentes.
- **"Hoje"** (data de nascimento não pode ser futura) é o dia no horário de Brasília, como no resto do sistema
  (`uso.FUSO`).
- **Teto por conta**: 5.000 pacientes. Acima disso, criar responde 409 com `codigo: "limite"`; ler, editar,
  exportar e excluir continuam funcionando, e excluir abre vaga.
- **Exportar** devolve `{formato: "evidens-paciente", versao: 1, exportado_em, paciente}`.

Erros (sempre `{error: "frase"}`, mais o que a tabela indica):

| Código | Quando | A mais |
|---|---|---|
| 400 | Dado inválido, chave desconhecida ou corpo que não é um objeto JSON; `?busca=` no endereço da lista | `erros` (frases) e `campos` (nomes dos campos a corrigir), menos no caso do `?busca=` |
| 401 | Sem login | `login: "/login"` |
| 403 | Conta que não é o administrador; Termos pendentes; pedido de outro site; pedido sem `X-Requested-With: evidens` | |
| 404 | Paciente que não existe ou é de outra conta | |
| 409 | CNS ou CPF já cadastrado na conta | `codigo: "duplicado"`, `campo` (`cns` ou `cpf`), `paciente_id` (o que já existe) |
| 409 | A conta chegou ao teto de 5.000 pacientes | `codigo: "limite"`, `limite` (o teto) |
| 409 | O registro mudou enquanto era editado | `codigo: "conflito"` |
| 413 | Envio maior que 128 KB | |
| 500 | O registro não abre com a chave atual, ou o texto cifrado não é o daquela linha | `codigo: "ilegivel"` |
| 503 | Área de acesso desligada (sem banco ou sem `SECRET_KEY`), ou cadastro sem `PACIENTES_CHAVE` utilizável | `codigo: "sem_chave"` quando falta a chave do cadastro |

## Tela

Fase 2. Só o administrador vê: a página, o link e o seletor do check-up seguem a mesma regra das rotas. **Para a
conta comum nada aparece**: nem página, nem link, nem botão, nem seção. `index.html` e `termos.html` não mudaram.
Testes em `tests/test_pacientes_tela.py`.

### Quem vê

- **Página `/pacientes`** (`pacientes.html`): a rota em `api/index.py` pergunta a `pacientes.habilitado_para`
  (por `tela_liberada`, em `src/routes/pacientes.py`). Sem login, vai para `/login`; conta comum, para o check-up,
  como nas outras páginas do administrador; Termos pendentes, para o aceite. `/pacientes.html` não é servido. A
  página não traz dado de paciente: tudo vem da API.
- **Link "Pacientes"** no menu das páginas de quem entrou e botão "Pacientes" em "Minha conta": criados por
  `static/conta.js` (`abrirCadastroDePacientes`) só depois de `/api/auth/eu` dizer que a conta é do administrador.
  Não existem no HTML, nem escondidos.
- **Seletor no check-up**: `static/conta.js` só carrega `static/pacientes.js` e `static/pacientes-checkup.js`
  para o administrador; a conta comum nem baixa os dois arquivos. O seletor não aparece no formulário embutido
  da página das operadoras.
- No dia em que `habilitado_para` aceitar outras contas, a condição de `abrirCadastroDePacientes` (hoje
  `usuario.administrador`) precisa acompanhar: o servidor já seguiria a regra nova, a tela não.

### Página `/pacientes`

- Aviso fixo no topo: "Fase de testes: use apenas dados fictícios até a atualização dos Termos de Uso."
- **Lista**: `GET /api/pacientes` ao abrir; com termo, `POST /api/pacientes/buscar`. Mostra nome, nascimento
  (com a idade), sexo e o final do CNS; avisa quando a lista foi cortada em 500 e quando há registros ilegíveis.
- **Criar e editar**: um formulário só, com todos os campos de identificação da API e até 5 planos
  (`{operadora, carteira, validade}`; a validade é digitada como MM/AAAA ou DD/MM/AAAA e enviada como a API
  pede). A edição envia todos os campos: o que ficou em branco é apagado no cadastro. A `ficha` não é enviada.
- **Excluir**: o botão pede confirmação na própria linha ("Confirmar exclusão" / "Cancelar").
- **Exportar**: o arquivo `paciente-<id>.json` é montado a partir da resposta do `fetch` (um link para a rota não
  levaria o cabeçalho próprio).
- CPF, CNS, CEP e código IBGE têm máscara. O CEP não é consultado em serviço externo nesta página.
- A data máxima do nascimento é a data local de quem usa a tela (não a data em UTC). Cada campo aponta para o
  parágrafo do seu erro (`aria-describedby`).

Mensagens (em `mensagemDeErro`, `static/pacientes.js`):

| Resposta | O que a tela faz |
|---|---|
| 400 | A frase do servidor aparece embaixo de cada campo recusado, e o campo fica destacado |
| 401 | Em `/pacientes`, volta para o login. No check-up, não sai da página (o formulário preenchido se perderia): "A sessão terminou. Entre de novo em outra aba e repita." |
| 403 | "O cadastro de pacientes não está disponível para esta conta." (Termos pendentes: vai para o aceite e, depois dele, volta à página de onde o pedido saiu) |
| 404 | "Paciente não encontrado: o registro pode ter sido excluído.", e a lista é recarregada |
| 409 `duplicado` | "Já existe um paciente com este CPF/CNS no seu cadastro.", com o botão "Abrir o paciente que já existe" |
| 409 `conflito` | "Este cadastro foi alterado em outro lugar. Reabra e repita a alteração." A edição envia o `atualizado_em` lido ao abrir o formulário |
| 409 `limite` | Avisa que a conta chegou ao limite e que nada foi gravado |
| 500 `ilegivel` | "Este registro não pôde ser aberto com a chave atual da instalação. Nenhum dado foi alterado." |
| 503 `sem_chave` | "O cadastro de pacientes ainda não foi ativado nesta instalação.", e os botões de buscar e criar são desligados |
| Sem rede | "Sem conexão com o servidor. Tente de novo." |

### Check-up: "Paciente cadastrado" e "Salvar paciente no cadastro"

O bloco fica no início da seção Identificação (`static/pacientes-checkup.js`), com o mesmo aviso de fase de
testes. Só dados de identificação vão e voltam; **nenhum dado clínico nem resultado é gravado**, e a `ficha` não é
lida nem enviada.

- **Buscar e escolher**: a busca (a partir de 2 letras) usa `POST /api/pacientes/buscar`; ao escolher, a tela lê
  o registro (`GET /api/pacientes/<id>`) e preenche:

  | Campo da tela | Do cadastro |
  |---|---|
  | Nome do paciente | `nome` |
  | Idade | calculada de `nascimento` (em branco se não houver) |
  | Sexo | `sexo` |
  | Plano de saúde do paciente e Número da carteira (guia SP/SADT) | o primeiro item de `planos` cuja operadora tem o mesmo nome de um credenciamento do médico |
  | Laudo de APAC: CNS, data de nascimento, nome da mãe, telefone, CEP, endereço, município, UF | `cns`, `nascimento`, `mae`, `telefone`, `cep`, `endereco`, `municipio`, `uf` (o `ibge` segue com o CEP) |

  CPF, nome social, raça/cor, prontuário, responsável e e-mail não têm campo no check-up: ficam só no cadastro.
  O vínculo do SUS não é escolhido sozinho.
- Os campos são preenchidos com os mesmos eventos de quem digita: resultado na tela é invalidado, como em
  qualquer mudança de idade ou sexo.
- **Guarda do plano (`planoAConfirmar`)**: preencher pelo cadastro não vale como conferência. A ponte
  `window.evidensCheckup.trocarDePaciente` (em `intelligent-tools.html`) põe o plano e a carteira na tela e chama
  `pedirConfirmacaoDoPlano()`, a mesma função de qualquer troca de paciente: havendo plano ou carteira na tela, a
  guia só sai depois de o médico confirmar ("Sim, manter"), e o laudo de APAC do paciente anterior é apagado
  antes de entrar o do novo. Se o cadastro do paciente escolhido não tem plano que o médico atenda, o plano e a
  carteira que estavam na tela saem (são do paciente anterior); a escolha do SUS fica, porque é do médico a cada
  pedido. Se a validade da carteira no cadastro já passou, o plano é preenchido e a tela avisa ("A validade da
  carteira no cadastro venceu em MM/AAAA."). A ponte só lê a guarda; nunca a baixa.
- **O vínculo vale só para o nome do cadastro.** O pedido nunca pode sair com o nome de um paciente e o CNS, a
  mãe, o nascimento ou o endereço de outro. São três trancas:
  1. na página, qualquer alteração do nome com algum dado no laudo de APAC limpa o laudo, haja ou não resultado
     na tela (`semEfeitoNasRecomendacoes`);
  2. no seletor, nome alterado e diferente do nome do paciente escolhido solta o vínculo à vista do médico, com
     o mesmo efeito de "Limpar seleção" e uma frase que explica (para corrigir o nome de um cadastrado, use a
     página do cadastro);
  3. na geração do PDF, se há paciente escolhido e o nome na tela é outro (`vinculoDivergente`), o pedido não
     sai: o vínculo é solto, o laudo é limpo, o plano passa a pedir confirmação e a tela avisa; e
     `apacDoDialogo` não monta os dados do paciente nessa situação.
- **Mesmo paciente, dado clínico alterado**: com resultado na tela, a mudança limpa o laudo de APAC (regra antiga
  da página). Se o paciente do cadastro continua escolhido e o nome é o dele, os dados dele voltam ao laudo
  (`aoLimparApac`); anamnese, exames realizados e CID, que são clínicos, não voltam.
- **Dados clínicos do paciente anterior**: o cadastro só traz identificação. Ao escolher um paciente diferente do
  que está na tela (outro registro, ou um nome digitado diferente) com dados clínicos preenchidos, o seletor
  avisa "Os dados clínicos na tela são do paciente anterior." e oferece "Limpar dados clínicos", que zera o
  formulário pelo `reset` dele (a limpeza que a página já conhecia), mantém nome, idade, sexo, plano e carteira e
  avisa os ouvintes de cada campo. Nada é limpo sem o médico pedir.
- **CEP sem código IBGE no cadastro**: o CEP não conta como já buscado e a busca de sempre (ViaCEP) acontece.
- **Salvar paciente no cadastro**: sem paciente escolhido, cria; com um escolhido, atualiza esse registro. Só o
  que está preenchido é enviado: campo em branco no check-up não apaga o que o cadastro tem (o laudo de APAC é
  limpo a cada troca de paciente). A idade não é gravada; o nascimento vem do campo do laudo de APAC. O plano da
  tela entra na lista `planos` no lugar do de mesma operadora, ou no fim. Com a guarda do plano pendente, nada é
  gravado até o médico confirmar. A edição leva o `atualizado_em` relido na hora. Durante o salvamento a busca e
  os resultados ficam desabilitados; se o médico soltar a seleção ou trocar o nome enquanto o pedido está fora, a
  resposta atrasada não refaz o vínculo (o mesmo vale para a resposta de uma escolha anterior).
- **Limpar seleção** solta o paciente escolhido e trata a tela como troca de paciente (guarda do plano e laudo de
  APAC limpo); o próximo "Salvar" cria um paciente novo.
- **Sessão terminada**: o seletor mostra "A sessão terminou. Entre de novo em outra aba e repita." e a página
  não é trocada.

### Conferência no navegador (obrigatória antes de cada mudança na tela)

A suíte só lê o código das telas: o repositório não tem teste de navegador nem de execução de JavaScript, e não
ganhou dependência para isso. O comportamento é conferido por `scripts/conferir_pacientes_tela.py`, que é
**conferência manual obrigatória antes de cada mudança** em `pacientes.html`, `static/pacientes.js`,
`static/pacientes-checkup.js`, na ponte `window.evidensCheckup` ou nas guardas do laudo de APAC e do plano em
`intelligent-tools.html`:

```
python scripts/conferir_pacientes_tela.py [--capturas PASTA] [--so C1,M2]
```

- Precisa de `playwright` no Python que roda o roteiro (fora do `requirements.txt`, de propósito) e de um Chrome
  (`--chrome` ou a variável `CHROME`).
- Sobe o próprio servidor num banco sqlite temporário, com uma `PACIENTES_CHAVE` sorteada na hora e passada só
  pelo ambiente do processo: **nenhuma chave em arquivo, nenhum banco real, nenhum dado real** (os pacientes são
  inventados no roteiro). O ViaCEP e a lista de exames em APAC são simulados; nada sai da máquina.
- Cobre: conta comum (nada aparece, API recusa); laudo de APAC com outro nome na tela (o corpo do `POST` do PDF
  é impresso e não pode levar dado do paciente do cadastro), também quando o nome muda sem evento; troca de
  paciente com dados clínicos e com plano na tela; corrida no "Salvar"; dado clínico alterado do mesmo paciente;
  CEP sem IBGE; validade vencida; inglês; edição concorrente em `/pacientes`; sessão terminada e Termos.
- Sai com código 0 se tudo conferiu. Os testes de `tests/test_pacientes_tela.py` travam as mesmas correções no
  código, mas não substituem o roteiro.

### Segurança da tela

- Todo pedido sai de uma função só (`pedir`, em `static/pacientes.js`), com `X-Requested-With: evidens`.
- Dado de paciente só entra na página por `textContent` ou `value`; os scripts não usam `innerHTML` nem montam
  HTML por texto. Os elementos com dado de paciente levam `data-i18n-manter`, para o tradutor não mexer neles.
- Nada de paciente vai para o endereço da página nem para `localStorage`/`sessionStorage`: a busca vai no corpo
  do pedido, e o paciente escolhido no check-up vive só na memória da página (recarregar apaga).
- O endereço das rotas leva só o número do registro (`/api/pacientes/<id>`).

### O que a tela ainda não faz

- Não grava nem mostra a `ficha` (dados clínicos e resultados), nem a trilha de acessos.
- Não busca o endereço pelo CEP na página `/pacientes` (no check-up, a busca do CEP do laudo de APAC continua
  como era).
- Os avisos do check-up para a conta comum ("o número da carteira não é guardado", "não são guardados") não
  mudaram: continuam verdadeiros para ela, e para o administrador enquanto ele não usa "Salvar paciente no
  cadastro". Entram na lista do que muda antes de abrir.
- Em inglês, as frases da tela e as frases fixas do 400 têm par em `static/i18n/en.json`; as recusas de tamanho
  ("no máximo N caracteres"), que a tela evita com o limite de cada campo, sairiam em português.

## Trilha de acessos

Tabela `pacientes_acessos`: `id`, `paciente_id`, `usuario_id`, `acao` (`criar`, `ver`, `listar`, `editar`,
`excluir`, `exportar`) e `quando`. Não tem dado de paciente: nem o termo da busca entra. Na listagem,
`paciente_id` fica nulo.

- A linha da trilha é gravada na mesma transação da ação. Se a trilha não grava, a ação não acontece, nem a
  leitura.
- Pedido recusado (401, 403, 404, 400, 409) não entra na trilha: não houve acesso. Vale para a edição que
  encontra o paciente já excluído ou alterado por outro pedido.
- `pacientes.trilha(usuario_id, paciente_id)` lê a trilha. Ainda não há rota nem tela para isso.

## Exclusão e exportação

- **Excluir** apaga a linha inteira do paciente. A trilha fica, só com o número do registro. Excluir não depende da
  chave: um registro que não abre mais também pode ser apagado.
- **Exportar** entrega tudo o que há guardado do paciente, em um arquivo JSON. O nome do arquivo não leva o nome
  do paciente.

## O que continua sem guardar nada

- As rotas do check-up, do pré-operatório, dos PDFs e das operadoras não importam o módulo do cadastro. Um teste
  confere que só `src/routes/pacientes.py` o importa, e outro, que essas rotas não mexem nas duas tabelas novas.
- `eventos_uso` (painel `/analytics`) tem as mesmas colunas e não recebe nenhum evento do cadastro.
- Nada do cadastro é escrito em log pela aplicação.

## Limites conhecidos

- **Dependência de `PACIENTES_CHAVE`.** Trocar o valor dela torna ilegíveis todos os registros gravados (resposta
  500, `ilegivel`; a lista os conta em `ilegiveis`). Voltar ao valor antigo recupera a leitura; perder o valor,
  não há como recuperar. Não há ainda procedimento de troca de chave: o prefixo `v1:` de cada registro existe
  para permitir um. Quem tiver o banco **e** a `PACIENTES_CHAVE` lê tudo; a chave de sessão (`SECRET_KEY`)
  sozinha não abre nenhum registro. As duas ficam nas variáveis de ambiente da mesma hospedagem: quem tem acesso
  de administração ao projeto na hospedagem alcança as duas.
- **Busca em memória.** O banco não procura em texto cifrado: a listagem lê todos os registros da conta (em lotes
  de 200), decifra e filtra no servidor. Por isso o teto de 5.000 pacientes por conta. O teto é conferido antes
  de gravar, sem trava: dois cadastros no mesmo instante, com a conta no limite, podem passar um registro do teto.
- **Índices.** CPF e CNS têm poucos valores possíveis: quem tiver o banco e a `PACIENTES_CHAVE` consegue testar
  números contra o índice. Sem a chave, não.
- **Índices trocados de linha.** O texto cifrado está preso à conta e ao número do registro; as colunas
  `indice_cns` e `indice_cpf` não. Quem alterar essas colunas direto no banco consegue atrapalhar a conferência
  de duplicado, mas não ler nem trocar dados de paciente.
- **O que a cifra não esconde.** Quantos pacientes cada conta tem, quando cada registro foi criado e alterado, o
  tamanho aproximado de cada registro e a trilha de acessos.
- **Cópias do banco.** A exclusão apaga a linha no banco em uso. Cópias de segurança e o histórico de restauração
  do provedor do banco podem guardar o texto cifrado pelo prazo que estiver configurado lá.
- **Edição simultânea.** Em Postgres as duas edições são gravadas, uma depois da outra (cada uma troca só os
  campos que enviou). Se as duas trocam o mesmo campo, vale a que gravar por último; não há aviso de que o
  registro mudou desde que a tela o abriu.
- **Conta bloqueada.** Os pacientes de uma conta bloqueada continuam guardados; ninguém mais os alcança pela
  aplicação.
- Os dados chegam ao servidor em claro (por HTTPS) e são cifrados antes de ir ao banco: não é cifra de ponta a
  ponta.

## LGPD e uso na fase 1

- **Enquanto os Termos de Uso e a home não forem atualizados, a fase de testes (API e tela) só pode ser usada com
  dados fictícios.**
  Vale para o administrador também: restringir o cadastro a uma conta reduz o risco, mas não muda o que os textos
  publicados prometem nem o que a lei exige.
- **Base legal, encarregado e retenção valem desde o primeiro paciente real**, mesmo que só o administrador use o
  cadastro. Dado de saúde é dado pessoal sensível: antes do primeiro registro verdadeiro é preciso ter definido a
  base legal do tratamento, quem é o controlador, quem é o encarregado e por qual canal o titular faz seus
  pedidos, e por quanto tempo o registro e as cópias de segurança ficam guardados. Nada disso está definido hoje
  (itens 1 a 4 da lista abaixo); são decisões para tomar com assessoria jurídica.
- O servidor não tem como saber se um dado é fictício: essa regra é de uso, não de código.
- `termos.html` e `index.html` não foram alterados nas fases 1 e 2. A tela repete o aviso de dados fictícios no
  topo da página e no bloco do check-up.

## Antes de abrir a todos

Abrir é trocar uma linha em `pacientes.habilitado_para` (as rotas já estão prontas para contas comuns: um teste
ensaia a abertura e confere que cada conta só vê os seus). **Antes dessa troca:**

1. **Termos de Uso e Política de Privacidade**: nova versão, que deixe de dizer que nada é guardado e diga o que
   é guardado, para quê, por quanto tempo, quem acessa e como pedir exportação e exclusão. São o PDF em
   `static/termos/` e o resumo em `termos.html` ("os dados do paciente não são gravados em cadastro vinculado à
   conta"). Trocar o PDF e a versão em `src/utils/termos.py` faz todas as contas aceitarem de novo.
2. **Home, página de cadastro e check-up**: os textos que prometem que nada é gravado, com a tradução em
   `static/i18n/en.json`: a faixa de números da home ("dados do paciente gravados", em `index.html`), "Dados de
   pacientes não são gravados" em `cadastro.html` e os avisos de que a carteira e os dados da APAC não são
   guardados em `intelligent-tools.html`. Os testes que travam esses textos estão em `tests/test_site.py`,
   `tests/test_guia_do_plano.py` e `tests/test_apac.py`.
3. **Política de retenção**: por quanto tempo o registro fica, o que acontece com os pacientes de uma conta
   bloqueada ou encerrada, e o prazo das cópias de segurança do banco. Decidir se o cadastro faz parte do
   prontuário (a guarda do prontuário tem regras próprias: Lei 13.787/2018 e Resolução CFM 1.821/2007).
4. **LGPD**: dado de saúde é dado pessoal sensível. Definir a base legal, quem é o controlador (cada médico ou o
   Evidēns), o encarregado e o canal para os pedidos do titular. É decisão para tomar com assessoria jurídica.
5. **Chave**: o cadastro já tem chave própria (`PACIENTES_CHAVE`). Falta escrever o procedimento de troca de
   chave e definir onde fica a cópia de segurança dela, antes de haver muitos registros.
6. **Limites de uso**: o teto de pacientes por conta existe (5.000); falta o de gravações por hora (hoje só o
   administrador grava).
7. **Tela**: já existe para o administrador (seção "Tela"). Falta mostrar a trilha de acessos, decidir se a
   `ficha` clínica entra, trocar a condição `usuario.administrador` de `static/conta.js` pela regra nova e rever
   os avisos do check-up que dizem que a carteira e os dados do laudo de APAC não são guardados.
8. **Inglês**: as frases da tela e as frases fixas do 400 têm par; as demais mensagens destas rotas estão só em
   português (as respostas do cadastro não passam pelo tradutor do servidor).
9. **Registro de perigos**: rever P-10, P-14 e P-26 em `docs/registro-de-perigos.md`.
