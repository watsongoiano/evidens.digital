# Cadastro de pacientes

Fase 1 (novembro de 2026): **só o servidor, só para o administrador, sem tela.** O cadastro está no ar para ser
testado antes de abrir a todos. Código em `src/utils/pacientes.py` (regras, cifra, banco) e
`src/routes/pacientes.py` (rotas); tabelas em `src/utils/contas.py`; testes em `tests/test_pacientes.py`.

É a única exceção à regra "nenhum dado de paciente é gravado". **Para o usuário comum nada mudou:** o check-up, o
pré-operatório, os PDFs (pedidos, guia SP/SADT, laudo de APAC) e as operadoras continuam recebendo os dados,
calculando e descartando. Os Termos de Uso v2.0, a home e a página de cadastro continuam dizendo isso, e continuam
verdadeiros para quem não é o administrador. A lista do que precisa mudar antes de abrir está no fim desta página.

> **Só dados fictícios, por enquanto.** Enquanto os Termos de Uso e a home não forem atualizados, a fase 1 só pode
> ser usada com dados fictícios (pacientes inventados, CPF e CNS gerados para teste), inclusive pelo administrador.
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
  mandaria com permissão do servidor (CORS), que não é dada. A tela (fase 2) manda o cabeçalho em todas as
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

- **Enquanto os Termos de Uso e a home não forem atualizados, a fase 1 só pode ser usada com dados fictícios.**
  Vale para o administrador também: restringir o cadastro a uma conta reduz o risco, mas não muda o que os textos
  publicados prometem nem o que a lei exige.
- **Base legal, encarregado e retenção valem desde o primeiro paciente real**, mesmo que só o administrador use o
  cadastro. Dado de saúde é dado pessoal sensível: antes do primeiro registro verdadeiro é preciso ter definido a
  base legal do tratamento, quem é o controlador, quem é o encarregado e por qual canal o titular faz seus
  pedidos, e por quanto tempo o registro e as cópias de segurança ficam guardados. Nada disso está definido hoje
  (itens 1 a 4 da lista abaixo); são decisões para tomar com assessoria jurídica.
- O servidor não tem como saber se um dado é fictício: essa regra é de uso, não de código.
- `termos.html` e `index.html` não foram alterados nesta fase.

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
7. **Tela**: mandar `X-Requested-With: evidens` em toda chamada, buscar pelo corpo, mostrar os dados só com
   `textContent`, tratar o 409 `conflito` e o 409 `limite`, mostrar a trilha de acessos, pedir confirmação antes
   de excluir.
8. **Inglês**: as mensagens destas rotas estão só em português.
9. **Registro de perigos**: rever P-10, P-14 e P-26 em `docs/registro-de-perigos.md`.
