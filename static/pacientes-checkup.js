// Check-up: seletor "Paciente cadastrado" e botão "Salvar paciente no cadastro" (por enquanto só o administrador).
// static/conta.js só carrega este arquivo para quem pode usar o cadastro; para as outras contas a página do
// check-up não ganha nenhum elemento. Depende de static/pacientes.js (window.evidensPacientes: pedidos com o
// cabeçalho próprio, mensagens e formatos) e da ponte window.evidensCheckup, definida em intelligent-tools.html.
//
// Regras:
//  - só dados de identificação vão e voltam (nome, sexo, nascimento, CNS, mãe, telefone, endereço, plano e
//    carteira); nenhum dado clínico ou resultado é gravado, e a `ficha` do cadastro não é lida nem enviada;
//  - dado de paciente só entra na página por textContent ou value; nada vai para o endereço nem fica guardado
//    no navegador (o paciente escolhido vive só na memória desta página);
//  - preencher a partir do cadastro não confirma o plano: a guarda da guia (planoAConfirmar) é levantada como em
//    qualquer troca de paciente e só o médico a baixa; com ela pendente, o plano e a carteira não são gravados.
(function () {
  'use strict';
  const P = window.evidensPacientes, tela = window.evidensCheckup;
  const secao = document.querySelector('section[aria-labelledby="s-identificacao"]');
  if (!P || !tela || tela.embutido || !secao || document.getElementById('pacienteCadastrado')) return;
  const { T, pedir, caminhoDo, mensagemDeErro, soDigitos, dataBr, dataIso, idadeDe, semAcento, el, dado, API } = P;

  const MAX_NA_LISTA = 8, MAX_PLANOS = 5;
  const porId = id => document.getElementById(id);
  let vinculado = null;     // registro completo do paciente escolhido (só na memória)
  let rodada = 0, espera = null;

  // ── Bloco no início da Identificação ──
  const bloco = el('div', 'mb-6 pb-6 border-b border-ink/10');
  bloco.id = 'pacienteCadastrado';
  const aviso = el('p', 'aviso aviso-atencao mb-5', T('Fase de testes: use apenas dados fictícios até a atualização dos Termos de Uso.'));
  aviso.setAttribute('role', 'note');
  const caixaDaBusca = el('div', 'campo');
  const rotulo = el('label', '', T('Paciente cadastrado')); rotulo.htmlFor = 'pacienteBusca';
  const busca = el('input'); busca.type = 'text'; busca.id = 'pacienteBusca'; busca.maxLength = 80; busca.autocomplete = 'off';
  busca.placeholder = T('Buscar no cadastro: parte do nome ou os últimos dígitos do CNS');
  busca.setAttribute('aria-controls', 'pacienteResultados');
  const resultados = el('div', 'flex flex-col gap-2 mt-3'); resultados.id = 'pacienteResultados';
  caixaDaBusca.append(rotulo, busca, resultados);
  const escolhido = el('p', 'text-[14px] text-ink/75 mt-4'); escolhido.id = 'pacienteVinculado'; escolhido.hidden = true;
  const estado = el('p', 'text-[13px] text-ink/60 mt-3'); estado.id = 'pacienteEstado';
  estado.setAttribute('role', 'status'); estado.setAttribute('aria-live', 'polite');
  const acoes = el('p', 'flex flex-wrap items-center gap-3 mt-4');
  const salvar = el('button', 'btn-claro'); salvar.type = 'button'; salvar.id = 'pacienteSalvar';
  const icone = el('i', 'fa-solid fa-floppy-disk text-[12px]'); icone.setAttribute('aria-hidden', 'true');
  salvar.append(icone, el('span', '', T('Salvar paciente no cadastro')));
  const soltar = el('button', 'btn-claro', T('Limpar seleção')); soltar.type = 'button'; soltar.id = 'pacienteSoltar'; soltar.hidden = true;
  const irAoCadastro = el('a', 'text-[13px] text-teal underline underline-offset-2', T('Abrir o cadastro de pacientes')); irAoCadastro.href = '/pacientes';
  acoes.append(salvar, soltar, irAoCadastro);
  const nota = el('p', 'text-[12px] text-ink/50 mt-3', T('O cadastro guarda só a identificação (nome, sexo, nascimento, CNS, mãe, telefone, endereço, plano e carteira). Dados clínicos e resultados não são gravados.'));
  bloco.append(aviso, caixaDaBusca, escolhido, acoes, estado, nota);
  secao.insertBefore(bloco, secao.querySelector('.grade'));

  // O que se digita na busca não é dado do formulário: não invalida o resultado na tela nem envia o check-up.
  ['input', 'change'].forEach(tipo => bloco.addEventListener(tipo, evento => evento.stopPropagation()));

  function dizer(texto, erro) {
    estado.textContent = texto || '';
    estado.className = 'text-[13px] mt-3 ' + (erro ? 'text-[#7B241C]' : 'text-ink/60');
  }

  // ── Busca ──
  function mostrarResultados(lista, total) {
    resultados.replaceChildren();
    lista.slice(0, MAX_NA_LISTA).forEach(p => {
      const b = el('button', 'recommendation-card !mb-0 text-left flex flex-wrap items-baseline gap-x-4 gap-y-1 hover:border-teal');
      b.type = 'button'; b.dataset.paciente = String(p.id);
      b.append(dado('span', 'text-[15px] font-medium', p.nome));
      const idade = idadeDe(p.nascimento);
      if (p.nascimento) b.append(dado('span', 'text-[13px] text-ink/55', dataBr(p.nascimento) + (idade === null ? '' : ` (${idade})`)));
      if (p.cns_final) {
        const cns = el('span', 'text-[13px] text-ink/55');
        cns.append(el('span', '', T('CNS com final')), ' ', dado('span', 'font-mono', p.cns_final));
        b.append(cns);
      }
      resultados.append(b);
    });
    if (!lista.length) resultados.append(el('p', 'text-[13px] text-ink/55', T('Nenhum paciente encontrado com este termo.')));
    else if (total > MAX_NA_LISTA) resultados.append(el('p', 'text-[13px] text-ink/55', T('Há mais pacientes com este termo: digite mais um pedaço do nome.')));
  }

  async function buscar() {
    const termo = busca.value.trim();
    const minha = ++rodada;
    if (termo.length < 2) { resultados.replaceChildren(); return; }
    const r = await pedir(API + '/buscar', { busca: termo });
    if (minha !== rodada) return;                       // chegou depois de uma busca mais nova
    if (!r.ok) { resultados.replaceChildren(); dizer(mensagemDeErro(r).texto, true); return; }
    dizer('');
    const lista = Array.isArray(r.dados.pacientes) ? r.dados.pacientes : [];
    mostrarResultados(lista, Number(r.dados.total) || lista.length);
  }
  busca.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(buscar, 300); });
  busca.addEventListener('keydown', evento => {
    if (evento.key !== 'Enter') return;
    evento.preventDefault();                            // Enter aqui busca; não envia o check-up
    clearTimeout(espera); buscar();
  });

  // ── Do cadastro para a tela ──
  function definir(id, valor) {
    const campo = porId(id);
    if (!campo) return;
    campo.value = valor == null ? '' : String(valor);
    ['input', 'change'].forEach(tipo => {
      const evento = new Event(tipo, { bubbles: true });
      evento.doUsuario = true;                          // vale como escolha do médico: ele escolheu o paciente
      campo.dispatchEvent(evento);
    });
  }

  // O plano do cadastro só serve à guia se o médico for credenciado nele: procura pelo nome da operadora entre os
  // credenciamentos da lista "Plano de saúde do paciente" (o SUS não entra: é escolha do médico a cada pedido).
  function credenciamentoDo(paciente) {
    const lista = porId('pacientePlano');
    const opcoes = lista ? [...lista.options].filter(o => o.value && !o.value.startsWith('sus:')) : [];
    for (const plano of paciente.planos || []) {
      const opcao = opcoes.find(o => semAcento(o.textContent) === semAcento(plano.operadora));
      if (opcao) return { id: opcao.value, carteira: plano.carteira || '' };
    }
    return null;
  }

  function mostrarVinculo() {
    escolhido.replaceChildren();
    escolhido.hidden = soltar.hidden = !vinculado;
    if (!vinculado) return;
    escolhido.append(el('span', '', T('Paciente do cadastro:')), ' ', dado('strong', 'font-medium text-ink', vinculado.nome));
    if (vinculado.nascimento) escolhido.append(' · ', dado('span', '', dataBr(vinculado.nascimento)));
  }

  function preencher(paciente) {
    vinculado = paciente;
    // 1. Identificação. Os eventos são os mesmos de quem digita: o resultado na tela é invalidado e, se havia um,
    //    o plano e a carteira passam a pedir confirmação.
    const idade = idadeDe(paciente.nascimento);
    definir('nome_paciente', paciente.nome);
    definir('idade', idade === null ? '' : idade);
    definir('sexo', paciente.sexo === 'masculino' || paciente.sexo === 'feminino' ? paciente.sexo : '');
    // 2. Plano e carteira: preenchidos se o médico é credenciado no plano do cadastro. Em todo caso é troca de
    //    paciente: a guarda sobe se houver plano ou carteira na tela, e o laudo de APAC do anterior é apagado.
    const plano = credenciamentoDo(paciente);
    tela.trocarDePaciente(plano);
    // 3. Dados do paciente no laudo de APAC (aparecem no diálogo do pedido pelo SUS).
    const cep = soDigitos(paciente.cep, 8);
    tela.enderecoDoCadastro(cep, soDigitos(paciente.ibge, 7));
    definir('apacCep', cep);
    definir('apacMunicipio', paciente.municipio);
    definir('apacUf', paciente.uf);
    definir('apacEndereco', paciente.endereco);
    definir('apacCns', paciente.cns);
    definir('apacNascimento', dataBr(paciente.nascimento));
    definir('apacMae', paciente.mae);
    definir('apacTelefone', paciente.telefone);

    resultados.replaceChildren();
    busca.value = '';
    mostrarVinculo();
    const partes = [T('Identificação preenchida a partir do cadastro.')];
    if (plano) partes.push(T('O plano e a carteira vieram do cadastro: confirme que são deste paciente antes de gerar a guia.'));
    else if ((paciente.planos || []).length) partes.push(T('O plano do cadastro não está entre os seus credenciamentos: a guia não foi preenchida.'));
    if (idade !== null && idade < 18) partes.push(T('O check-up é para adultos: este paciente tem menos de 18 anos.'));
    dizer(partes.join(' '));
  }

  resultados.addEventListener('click', async evento => {
    const botao = evento.target.closest('button[data-paciente]');
    if (!botao) return;
    botao.disabled = true;
    const r = await pedir(caminhoDo(botao.dataset.paciente));
    if (!r.ok || !r.dados.paciente) { botao.disabled = false; dizer(mensagemDeErro(r).texto, true); return; }
    preencher(r.dados.paciente);
  });

  // Soltar o paciente escolhido: o que está na tela pode passar a ser de outra pessoa, então vale a mesma regra de
  // troca de paciente (guarda do plano e laudo de APAC limpo). Nome, idade e sexo ficam para o médico corrigir.
  soltar.addEventListener('click', () => {
    vinculado = null;
    tela.trocarDePaciente(null);
    tela.enderecoDoCadastro('', '');
    mostrarVinculo();
    dizer(T('Seleção limpa: "Salvar paciente no cadastro" passa a criar um paciente novo.'));
  });

  // ── Da tela para o cadastro ──
  // Só o que está preenchido é enviado: campo em branco na tela não apaga o que o cadastro já tem (o laudo de APAC
  // é limpo sozinho a cada troca de paciente). Para apagar um dado, use a página do cadastro.
  function identificacaoDaTela() {
    const v = id => (porId(id) ? porId(id).value.trim() : '');
    const dados = {}, rotulos = [];
    const por = (campo, valor, rotulo) => { if (valor) { dados[campo] = valor; rotulos.push(T(rotulo)); } };
    por('nome', v('nome_paciente'), 'nome');
    por('sexo', v('sexo'), 'sexo');
    por('nascimento', dataIso(v('apacNascimento')), 'nascimento');
    por('cns', soDigitos(v('apacCns'), 15), 'CNS');
    por('mae', v('apacMae'), 'nome da mãe');
    por('telefone', v('apacTelefone'), 'telefone');
    const cep = soDigitos(v('apacCep'), 8);
    por('cep', cep, 'CEP');
    por('endereco', v('apacEndereco'), 'endereço');
    por('municipio', v('apacMunicipio'), 'município');
    por('uf', v('apacUf').toUpperCase(), 'UF');
    if (cep && tela.ibge()) dados.ibge = tela.ibge();
    return { dados, rotulos };
  }

  // Plano e carteira da tela, como item da lista `planos` do cadastro; null se particular ou SUS.
  function planoDaTela() {
    const lista = porId('pacientePlano');
    if (!lista || !lista.value || lista.value.startsWith('sus:') || !lista.selectedOptions[0]) return null;
    return { operadora: lista.selectedOptions[0].textContent.trim(), carteira: (porId('pacienteCarteira').value || '').trim() };
  }
  // A lista de planos é gravada inteira: o plano da tela entra no lugar do de mesma operadora, ou no fim.
  function planosCom(atuais, novo) {
    const planos = (atuais || []).map(p => ({ operadora: p.operadora, carteira: p.carteira || '', validade: p.validade || '' }));
    const igual = planos.find(p => semAcento(p.operadora) === semAcento(novo.operadora));
    if (igual) { if (novo.carteira) igual.carteira = novo.carteira; return planos; }
    if (planos.length >= MAX_PLANOS) return null;
    return planos.concat([{ operadora: novo.operadora, carteira: novo.carteira, validade: '' }]);
  }

  salvar.addEventListener('click', async () => {
    const { dados, rotulos } = identificacaoDaTela();
    if (!dados.nome || dados.nome.length < 2) {
      dizer(T('Informe o nome do paciente para salvar no cadastro.'), true);
      porId('nome_paciente').focus();
      return;
    }
    const plano = planoDaTela();
    if (plano && tela.planoPendente()) {
      // A guarda está de pé: o plano e a carteira podem ser de outro paciente e não vão para o cadastro assim.
      dizer(T('Antes de salvar, confirme acima se o plano e a carteira são deste paciente.'), true);
      const confirmar = porId('planoManter');
      if (confirmar) { confirmar.scrollIntoView({ block: 'nearest' }); confirmar.focus(); }
      return;
    }
    let atual = null;
    if (vinculado) {
      if (semAcento(vinculado.nome) !== semAcento(dados.nome)
          && !window.confirm(T('O nome na tela é diferente do nome do paciente escolhido no cadastro. Atualizar o registro desse paciente mesmo assim? Para cadastrar outra pessoa, cancele e use "Limpar seleção".'))) return;
      // Relê o registro: os planos são gravados como lista inteira e podem ter mudado na página do cadastro.
      const lido = await pedir(caminhoDo(vinculado.id));
      if (!lido.ok || !lido.dados.paciente) {
        dizer(mensagemDeErro(lido).texto, true);
        if (lido.status === 404) { vinculado = null; mostrarVinculo(); }
        return;
      }
      atual = lido.dados.paciente;
    }
    if (plano) {
      const planos = planosCom(atual ? atual.planos : [], plano);
      if (planos === null) { dizer(T('Este paciente já tem 5 planos no cadastro: o plano da tela não foi incluído. Ajuste na página do cadastro.'), true); return; }
      dados.planos = planos;
      rotulos.push(T('plano e carteira'));
    }
    salvar.disabled = true;
    const r = await pedir(atual ? caminhoDo(atual.id) : API, dados);
    salvar.disabled = false;
    if (!r.ok || !r.dados.paciente) {
      const m = mensagemDeErro(r);
      let texto = m.texto;
      if (r.status === 400 && m.itens.length) texto += ' ' + m.itens.join(' ');
      if (m.duplicado) texto += ' ' + T('Escolha-o em "Paciente cadastrado" para atualizar o registro.');
      if (r.status === 404) { vinculado = null; mostrarVinculo(); }
      dizer(texto, true);
      return;
    }
    vinculado = r.dados.paciente;
    mostrarVinculo();
    dizer(T(atual ? 'Cadastro atualizado. Gravados:' : 'Paciente cadastrado. Gravados:') + ' ' + rotulos.join(', ') + '.');
  });
})();
