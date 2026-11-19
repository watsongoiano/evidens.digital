// Cadastro de pacientes (/pacientes; por enquanto só o administrador). Contrato em docs/pacientes.md.
// Regras desta tela:
//  - todo pedido sai de `pedir`, com o cabeçalho X-Requested-With: evidens (a API recusa sem ele);
//  - dado de paciente só entra na página por textContent ou value, nunca como HTML;
//  - nenhum dado de paciente vai para o endereço da página nem fica guardado no navegador: a busca vai no corpo
//    do pedido e recarregar a página apaga tudo o que estava na tela.
// A primeira parte (window.evidensPacientes) também serve ao seletor do check-up (static/pacientes-checkup.js).
(function () {
  'use strict';

  const T = t => (window.evidensIdioma ? window.evidensIdioma.traduzir(t) : t);
  const API = '/api/pacientes';
  const CABECALHOS = { 'X-Requested-With': 'evidens' };
  // Esta parte roda em duas páginas: /pacientes (tem [data-pacientes]) e o check-up (não tem).
  const NO_CHECKUP = !document.querySelector('[data-pacientes]');

  // ── Parte comum: pedidos, mensagens e formatos ──────────────────────────────

  // Único ponto de saída para a API. Com `corpo`, POST em JSON; sem ele, GET.
  async function pedir(caminho, corpo) {
    const pedido = { method: corpo === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store',
                     headers: Object.assign({}, CABECALHOS),
                     semVoltarAoLogin: NO_CHECKUP };     // lido pela página do check-up, que vigia todo fetch
    if (corpo !== undefined) {
      pedido.headers['Content-Type'] = 'application/json';
      pedido.body = JSON.stringify(corpo);
    }
    let resposta;
    try {
      resposta = await fetch(caminho, pedido);
    } catch (e) {
      return { status: 0, ok: false, dados: {} };
    }
    // Sessão terminada: /pacientes volta ao login. No check-up não: sair da página apagaria o formulário que o
    // médico preencheu; quem chamou mostra o aviso (mensagemDeErro) e ele entra de novo em outra aba.
    // Termos pendentes: depois do aceite, volta-se à página de onde o pedido saiu.
    if (resposta.status === 401) { if (!NO_CHECKUP) window.location.href = '/login'; }
    else if (resposta.status === 403 && resposta.headers.get('X-Evidens-Termos')) {
      window.location.href = NO_CHECKUP ? '/termos?aceitar=1&destino=check-up' : '/termos?aceitar=1&destino=pacientes';
    }
    let dados = null;
    try { dados = await resposta.json(); } catch (e) { dados = null; }
    return { status: resposta.status, ok: resposta.ok, dados: dados && typeof dados === 'object' ? dados : {} };
  }

  const caminhoDo = (id, acao) => API + '/' + String(Math.trunc(Number(id))) + (acao ? '/' + acao : '');

  // A frase que a tela mostra para cada recusa. As do servidor só entram no 400 (são frases fixas, sem o que foi
  // digitado); nas outras a tela usa as suas, mais curtas.
  function mensagemDeErro(r) {
    const d = r.dados || {};
    if (r.status === 0) return { texto: T('Sem conexão com o servidor. Tente de novo.') };
    if (r.status === 400) return { texto: T('Confira os dados informados.'), itens: Array.isArray(d.erros) ? d.erros.map(String) : [], campos: Array.isArray(d.campos) ? d.campos.map(String) : [] };
    if (r.status === 401) return { texto: T(NO_CHECKUP ? 'A sessão terminou. Entre de novo em outra aba e repita.' : 'A sessão terminou. Entre de novo.') };
    if (r.status === 403) return { texto: T('O cadastro de pacientes não está disponível para esta conta.') };
    if (r.status === 404) return { texto: T('Paciente não encontrado: o registro pode ter sido excluído.') };
    if (r.status === 409 && d.codigo === 'duplicado') {
      return { texto: T(d.campo === 'cpf' ? 'Já existe um paciente com este CPF no seu cadastro.' : 'Já existe um paciente com este CNS no seu cadastro.'),
               duplicado: Number(d.paciente_id) || null };
    }
    if (r.status === 409 && d.codigo === 'conflito') return { texto: T('Este cadastro foi alterado em outro lugar. Reabra e repita a alteração.'), conflito: true };
    if (r.status === 409 && d.codigo === 'limite') return { texto: T('O cadastro chegou ao limite de pacientes por conta. Nada foi gravado: exclua registros que não usa mais para cadastrar outros.') };
    if (r.status === 413) return { texto: T('O envio é grande demais. Nada foi gravado.') };
    if (r.status === 500 && d.codigo === 'ilegivel') return { texto: T('Este registro não pôde ser aberto com a chave atual da instalação. Nenhum dado foi alterado.') };
    if (r.status === 503 && d.codigo === 'sem_chave') return { texto: T('O cadastro de pacientes ainda não foi ativado nesta instalação.'), semChave: true };
    if (r.status === 503) return { texto: T('O cadastro de pacientes está indisponível no momento. Tente de novo mais tarde.') };
    return { texto: T('Não foi possível concluir. Tente de novo.') };
  }

  const soDigitos = (texto, maximo) => String(texto == null ? '' : texto).replace(/\D/g, '').slice(0, maximo);
  const dataBr = iso => (/^\d{4}-\d{2}-\d{2}$/.test(iso || '') ? iso.split('-').reverse().join('/') : '');
  // "dd/mm/aaaa" completo e possível vira "aaaa-mm-dd"; qualquer outra coisa, ''.
  function dataIso(br) {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(br || '').trim());
    if (!m) return '';
    const dia = new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
    return dia.getUTCFullYear() === +m[3] && dia.getUTCMonth() === +m[2] - 1 && dia.getUTCDate() === +m[1] ? `${m[3]}-${m[2]}-${m[1]}` : '';
  }
  // Idade em anos completos hoje; null sem data válida.
  function idadeDe(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null;
    const [ano, mes, dia] = iso.split('-').map(Number);
    const hoje = new Date();
    let idade = hoje.getFullYear() - ano;
    if (hoje.getMonth() + 1 < mes || (hoje.getMonth() + 1 === mes && hoje.getDate() < dia)) idade -= 1;
    return idade >= 0 && idade <= 130 ? idade : null;
  }
  const MASCARAS = {
    cpf: v => { const d = soDigitos(v, 11); return [d.slice(0, 3), d.slice(3, 6), d.slice(6, 9)].filter(Boolean).join('.') + (d.length > 9 ? '-' + d.slice(9) : ''); },
    cns: v => soDigitos(v, 15),
    cep: v => { const d = soDigitos(v, 8); return d.length > 5 ? d.slice(0, 5) + '-' + d.slice(5) : d; },
    ibge: v => soDigitos(v, 7),
  };
  // A data de hoje no relógio de quem usa a tela (toISOString daria a data em UTC: à noite, no Brasil, já é amanhã).
  function hojeLocal() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  // Para comparar nomes (de pessoa ou de operadora) sem acento, caixa nem espaço a mais.
  const semAcento = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();

  function el(tag, classe, texto) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  // Elemento que mostra dado de paciente: o texto entra por textContent e o tradutor da página não mexe nele.
  function dado(tag, classe, texto) {
    const e = el(tag, classe, texto);
    e.setAttribute('data-i18n-manter', '');
    return e;
  }

  window.evidensPacientes = { T, pedir, caminhoDo, mensagemDeErro, soDigitos, dataBr, dataIso, idadeDe, hojeLocal, semAcento, el, dado, API };

  // ── Página /pacientes ───────────────────────────────────────────────────────
  const pagina = document.querySelector('[data-pacientes]');
  if (!pagina) return;

  const $ = sel => pagina.querySelector(sel);
  const CAMPOS = ['nome', 'nome_social', 'nascimento', 'sexo', 'cpf', 'cns', 'mae', 'raca', 'prontuario', 'responsavel',
                  'telefone', 'email', 'cep', 'endereco', 'municipio', 'ibge', 'uf'];
  const MAX_PLANOS = 5;
  const SEXOS = { masculino: 'Masculino', feminino: 'Feminino' };
  const formulario = $('[data-formulario]');
  const campo = nome => formulario.querySelector(`[data-campo="${nome}"]`);
  let emEdicao = null;      // id do paciente aberto no formulário; null = paciente novo
  let versaoEmEdicao = null; // atualizado_em do registro quando o formulário abriu: a API recusa a edição se mudou
  let ultimaBusca = '';     // só na memória da página
  let rodada = 0;           // descarta a resposta de uma busca mais antiga que chega depois

  function avisar(seletor, texto, itens) {
    const caixa = $(seletor);
    caixa.replaceChildren();
    if (texto) caixa.append(el('p', '', texto));
    if (itens && itens.length) {
      const ul = el('ul', 'mt-2 ml-5 list-disc');
      itens.forEach(i => ul.append(el('li', '', i)));
      caixa.append(ul);
    }
    caixa.style.display = texto ? 'block' : 'none';
    return caixa;
  }
  const limparAvisos = () => { avisar('[data-erro-geral]', ''); avisar('[data-ok-geral]', ''); };

  // Recusa fora do formulário (lista, abrir, excluir, exportar).
  function recusaGeral(r) {
    const m = mensagemDeErro(r);
    avisar('[data-erro-geral]', m.texto, m.itens).scrollIntoView({ block: 'nearest' });
    if (m.semChave) pagina.querySelectorAll('[data-novo], [data-busca] button, #busca').forEach(b => { b.disabled = true; });
    return m;
  }

  // ── Lista ──
  function linha(p) {
    const cartao = el('div', 'recommendation-card flex flex-wrap items-center justify-between gap-4');
    cartao.dataset.paciente = String(p.id);
    const quem = el('div', 'min-w-0');
    quem.append(dado('h5', '!pr-0 truncate', p.nome));
    const meta = el('p', 'text-[13px] text-ink/55 mt-1 flex flex-wrap gap-x-4 gap-y-1');
    if (p.nascimento) {
      const nasc = el('span');
      const idade = idadeDe(p.nascimento);
      nasc.append(el('span', '', T('Nascimento:')), ' ', dado('span', '', dataBr(p.nascimento) + (idade === null ? '' : ` (${idade})`)));
      meta.append(nasc);
    }
    if (SEXOS[p.sexo]) meta.append(el('span', '', T(SEXOS[p.sexo])));
    if (p.cns_final) {
      const cns = el('span');
      cns.append(el('span', '', T('CNS com final')), ' ', dado('span', 'font-mono', p.cns_final));
      meta.append(cns);
    }
    quem.append(meta);
    const acoes = el('div', 'flex flex-wrap items-center gap-2');
    const botao = (rotulo, acao, icone) => {
      const b = el('button', 'btn-claro !h-9 !px-4 !text-[13px]');
      b.type = 'button'; b.dataset.acao = acao;
      const i = el('i', `fa-solid ${icone} text-[11px]`); i.setAttribute('aria-hidden', 'true');
      b.append(i, el('span', '', T(rotulo)));
      return b;
    };
    acoes.append(botao('Editar', 'editar', 'fa-pen'), botao('Exportar', 'exportar', 'fa-download'), botao('Excluir', 'excluir', 'fa-trash'));
    cartao.append(quem, acoes);
    return cartao;
  }

  async function carregar(busca) {
    const minha = ++rodada;
    ultimaBusca = busca || '';
    const r = ultimaBusca ? await pedir(API + '/buscar', { busca: ultimaBusca }) : await pedir(API);
    if (minha !== rodada) return;
    const linhas = $('[data-linhas]'), notas = $('[data-notas]');
    if (!r.ok) {
      linhas.replaceChildren(); notas.replaceChildren(); $('[data-total]').textContent = '';
      recusaGeral(r);
      return;
    }
    const lista = Array.isArray(r.dados.pacientes) ? r.dados.pacientes : [];
    $('[data-total]').textContent = `(${Number(r.dados.total) || lista.length})`;
    notas.replaceChildren();
    if (!lista.length) notas.append(el('span', 'block', T(ultimaBusca ? 'Nenhum paciente encontrado com este termo.' : 'Nenhum paciente cadastrado ainda. Use "Novo paciente" para começar.')));
    if (r.dados.truncado) notas.append(el('span', 'block', T('Há mais pacientes do que a lista mostra (ela para em 500): refine a busca.')));
    if (Number(r.dados.ilegiveis) > 0) notas.append(el('span', 'block', T('Há registros que não puderam ser abertos com a chave atual da instalação; eles não aparecem na lista.')));
    linhas.replaceChildren(...lista.map(linha));
  }

  // ── Formulário ──
  function linhaDePlano(plano) {
    const p = plano || {};
    const caixa = el('div', 'grade sm:grid-cols-[2fr_1.4fr_1fr_auto] items-end');
    caixa.setAttribute('data-plano', '');
    const n = pagina.querySelectorAll('[data-plano]').length + 1 + '-' + Date.now().toString(36);
    const coluna = (rotulo, chave, maximo, dica) => {
      const c = el('div', 'campo');
      const r = el('label', '', T(rotulo)); r.htmlFor = `plano_${chave}_${n}`;
      const i = el('input'); i.type = 'text'; i.id = r.htmlFor; i.maxLength = maximo; i.autocomplete = 'off';
      i.dataset.planoCampo = chave;
      if (dica) i.placeholder = dica;
      i.value = p[chave] || '';
      c.append(r, i);
      return c;
    };
    const validade = coluna('Validade', 'validade', 10, 'MM/AAAA');
    validade.querySelector('input').value = validadeBr(p.validade);
    const tirar = el('button', 'btn-claro !h-11', T('Remover')); tirar.type = 'button'; tirar.dataset.tirarPlano = '';
    caixa.append(coluna('Operadora', 'operadora', 80, T('Ex: Unimed Goiânia')), coluna('Número da carteira', 'carteira', 30), validade, tirar);
    return caixa;
  }
  // No cadastro a validade é AAAA-MM ou AAAA-MM-DD; na tela, MM/AAAA ou DD/MM/AAAA.
  function validadeBr(iso) {
    const t = String(iso || '');
    if (/^\d{4}-\d{2}$/.test(t)) return t.slice(5) + '/' + t.slice(0, 4);
    return dataBr(t);
  }
  function validadeIso(br) {
    const t = String(br || '').trim();
    const m = /^(\d{2})\/(\d{4})$/.exec(t);
    if (m) return +m[1] >= 1 && +m[1] <= 12 ? `${m[2]}-${m[1]}` : null;
    return t ? (dataIso(t) || null) : '';
  }
  function atualizarPlanos() {
    $('[data-mais-plano]').disabled = pagina.querySelectorAll('[data-plano]').length >= MAX_PLANOS;
  }

  function limparErros() {
    avisar('[data-erro]', '');
    formulario.querySelectorAll('[data-erro-de]').forEach(p => { p.textContent = ''; p.hidden = true; });
    formulario.querySelectorAll('[aria-invalid]').forEach(c => c.removeAttribute('aria-invalid'));
  }
  function erroNoCampo(nome, texto) {
    const p = formulario.querySelector(`[data-erro-de="${nome}"]`);
    if (p && texto) { p.textContent = texto; p.hidden = false; }
    const c = campo(nome);
    if (c) c.setAttribute('aria-invalid', 'true');
  }

  function abrirFormulario(paciente) {
    limparErros();
    emEdicao = paciente ? paciente.id : null;
    versaoEmEdicao = paciente && Number.isFinite(Number(paciente.atualizado_em)) ? Number(paciente.atualizado_em) : null;
    $('[data-titulo-da-ficha]').textContent = T(paciente ? 'Editar paciente' : 'Novo paciente');
    CAMPOS.forEach(nome => {
      const valor = paciente ? String(paciente[nome] || '') : '';
      campo(nome).value = MASCARAS[nome] ? MASCARAS[nome](valor) : valor;
    });
    $('[data-pac-planos]').replaceChildren(...((paciente && paciente.planos) || []).slice(0, MAX_PLANOS).map(linhaDePlano));
    atualizarPlanos();
    campo('nascimento').max = hojeLocal();
    $('[data-ficha]').style.display = '';
    $('[data-ficha]').scrollIntoView({ block: 'start', behavior: 'smooth' });
    campo('nome').focus({ preventScroll: true });
  }
  function fecharFormulario() {
    emEdicao = null; versaoEmEdicao = null;
    formulario.reset();                         // nada do paciente fica nos campos escondidos
    $('[data-pac-planos]').replaceChildren();
    limparErros();
    $('[data-ficha]').style.display = 'none';
  }

  async function abrir(id) {
    limparAvisos();
    const r = await pedir(caminhoDo(id));
    if (!r.ok || !r.dados.paciente) {
      recusaGeral(r);
      if (r.status === 404) { fecharFormulario(); carregar(ultimaBusca); }
      return;
    }
    abrirFormulario(r.dados.paciente);
  }

  // O que vai para a API: todos os campos de identificação (vazio apaga o campo na edição). A ficha clínica não é
  // enviada por esta tela: fica como está no servidor.
  function lerFormulario() {
    const dados = {}, erros = [];
    CAMPOS.forEach(nome => { dados[nome] = campo(nome).value.trim(); });
    dados.planos = [];
    pagina.querySelectorAll('[data-plano]').forEach(caixa => {
      const v = chave => caixa.querySelector(`[data-plano-campo="${chave}"]`).value.trim();
      if (!v('operadora') && !v('carteira') && !v('validade')) return;       // linha em branco não conta
      const validade = validadeIso(v('validade'));
      if (validade === null) erros.push(T('Validade do plano: use MM/AAAA (ou DD/MM/AAAA).'));
      if (!v('operadora')) erros.push(T('Em cada plano de saúde, informe a operadora.'));
      dados.planos.push({ operadora: v('operadora'), carteira: v('carteira'), validade: validade || '' });
    });
    if (dados.nome.length < 2) erros.push(T('Informe o nome do paciente.'));
    return { dados, erros: [...new Set(erros)] };
  }

  formulario.addEventListener('submit', async evento => {
    evento.preventDefault();
    limparErros(); limparAvisos();
    const { dados, erros } = lerFormulario();
    if (erros.length) {
      if (dados.nome.length < 2) erroNoCampo('nome');
      avisar('[data-erro]', T('Confira os dados informados.'), erros);
      return;
    }
    const botao = $('[data-salvar]');
    botao.disabled = true;
    const editando = emEdicao;
    // Na edição vai junto a versão lida ao abrir: se o registro mudou em outro lugar desde então (outra aba, o
    // check-up), a API responde 409 e nada é sobrescrito.
    if (editando !== null && versaoEmEdicao !== null) dados.atualizado_em = versaoEmEdicao;
    const r = await pedir(editando === null ? API : caminhoDo(editando), dados);
    botao.disabled = false;
    if (r.ok) {
      fecharFormulario();
      avisar('[data-ok-geral]', T(editando === null ? 'Paciente cadastrado.' : 'Paciente salvo.'));
      carregar(ultimaBusca);
      return;
    }
    const m = mensagemDeErro(r);
    if (r.status === 400) {
      // Uma frase por campo recusado: fica embaixo do campo. Se a conta não fechar, todas vão para o aviso.
      const porCampo = m.itens.length === m.campos.length;
      m.campos.forEach((nome, i) => erroNoCampo(nome, porCampo ? m.itens[i] : ''));
      avisar('[data-erro]', T('Confira os campos destacados.'), porCampo ? [] : m.itens);
      const primeiro = formulario.querySelector('[aria-invalid="true"]');
      if (primeiro) primeiro.focus();
      return;
    }
    const aviso = avisar('[data-erro]', m.texto);
    if (m.duplicado) {
      erroNoCampo(r.dados.campo === 'cpf' ? 'cpf' : 'cns');
      const ir = el('button', 'btn-claro mt-3', T('Abrir o paciente que já existe')); ir.type = 'button';
      ir.addEventListener('click', () => abrir(m.duplicado));
      aviso.append(ir);
    }
    if (r.status === 404) { fecharFormulario(); recusaGeral(r); carregar(ultimaBusca); }
  });

  // Quem corrige um campo recusado deixa de ver a recusa dele.
  formulario.addEventListener('input', evento => {
    const nome = evento.target.dataset && evento.target.dataset.campo;
    if (!nome) return;
    evento.target.removeAttribute('aria-invalid');
    const p = formulario.querySelector(`[data-erro-de="${nome}"]`);
    if (p) { p.textContent = ''; p.hidden = true; }
  });
  Object.keys(MASCARAS).forEach(nome => {
    campo(nome).addEventListener('input', () => { campo(nome).value = MASCARAS[nome](campo(nome).value); });
  });
  $('[data-mais-plano]').addEventListener('click', () => {
    if (pagina.querySelectorAll('[data-plano]').length >= MAX_PLANOS) return;
    const nova = linhaDePlano();
    $('[data-pac-planos]').append(nova);
    atualizarPlanos();
    nova.querySelector('input').focus();
  });
  $('[data-pac-planos]').addEventListener('click', evento => {
    const tirar = evento.target.closest('[data-tirar-plano]');
    if (!tirar) return;
    tirar.closest('[data-plano]').remove();
    atualizarPlanos();
  });
  $('[data-novo]').addEventListener('click', () => { limparAvisos(); abrirFormulario(null); });
  $('[data-cancelar]').addEventListener('click', fecharFormulario);
  $('[data-busca]').addEventListener('submit', evento => {
    evento.preventDefault();
    limparAvisos();
    carregar($('#busca').value.trim());
  });

  // ── Ações de cada linha ──
  async function exportar(id) {
    const r = await pedir(caminhoDo(id, 'exportar'));
    if (!r.ok) { recusaGeral(r); if (r.status === 404) carregar(ultimaBusca); return; }
    // O arquivo é montado aqui, a partir da resposta: um link comum para a rota não levaria o cabeçalho próprio.
    const endereco = URL.createObjectURL(new Blob([JSON.stringify(r.dados, null, 2)], { type: 'application/json' }));
    const a = el('a'); a.href = endereco; a.download = `paciente-${Math.trunc(Number(id))}.json`;
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(endereco), 1000);
    avisar('[data-ok-geral]', T('Arquivo do paciente baixado.'));
  }

  // Excluir pede confirmação na própria linha: o botão vira "Confirmar exclusão" e "Cancelar".
  function pedirConfirmacao(cartao) {
    if (cartao.querySelector('[data-confirmar]')) return;
    const caixa = el('div', 'aviso aviso-erro basis-full flex flex-wrap items-center justify-between gap-3');
    caixa.setAttribute('data-confirmar', ''); caixa.setAttribute('role', 'alert');
    caixa.append(el('p', '', T('Excluir este paciente do cadastro? A exclusão não pode ser desfeita.')));
    const botoes = el('p', 'flex flex-wrap gap-2');
    const sim = el('button', 'btn-claro !h-9 !px-4 !text-[13px]', T('Confirmar exclusão')); sim.type = 'button'; sim.dataset.acao = 'confirmar-exclusao';
    const nao = el('button', 'btn-claro !h-9 !px-4 !text-[13px]', T('Cancelar')); nao.type = 'button'; nao.dataset.acao = 'cancelar-exclusao';
    botoes.append(sim, nao);
    caixa.append(botoes);
    cartao.append(caixa);
    nao.focus();
  }
  async function excluir(id) {
    const r = await pedir(caminhoDo(id, 'excluir'), {});
    if (!r.ok && r.status !== 404) { recusaGeral(r); return; }
    if (emEdicao === id) fecharFormulario();
    if (r.ok) avisar('[data-ok-geral]', T('Paciente excluído.')); else recusaGeral(r);
    carregar(ultimaBusca);
  }

  $('[data-linhas]').addEventListener('click', evento => {
    const botao = evento.target.closest('button[data-acao]');
    if (!botao) return;
    const cartao = botao.closest('[data-paciente]');
    const id = Number(cartao.dataset.paciente);
    const acao = botao.dataset.acao;
    if (acao !== 'excluir' && acao !== 'cancelar-exclusao') limparAvisos();
    if (acao === 'editar') abrir(id);
    else if (acao === 'exportar') exportar(id);
    else if (acao === 'excluir') pedirConfirmacao(cartao);
    else if (acao === 'cancelar-exclusao') cartao.querySelector('[data-confirmar]').remove();
    else if (acao === 'confirmar-exclusao') { botao.disabled = true; excluir(id); }
  });

  carregar('');
})();
