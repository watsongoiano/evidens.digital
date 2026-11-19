// Área de acesso: formulários de login, cadastro, instalação e senha; painel de aprovação.
(function () {
  'use strict';

  async function enviar(caminho, corpo) {
    const resposta = await fetch(caminho, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(corpo || {}),
    });
    let dados = null;
    try { dados = await resposta.json(); } catch (e) { dados = null; }
    return { resposta, dados: dados || {} };
  }

  function mostrar(el, texto, itens) {
    if (!el) return;
    el.textContent = texto || '';
    if (itens && itens.length) {
      const ul = document.createElement('ul');
      ul.className = 'mt-2 ml-5 list-disc';
      itens.forEach(i => { const li = document.createElement('li'); li.textContent = i; ul.appendChild(li); });
      el.appendChild(ul);
    }
    el.style.display = texto ? 'block' : 'none';
  }

  const ROTAS = {
    login: '/api/auth/login',
    cadastro: '/api/auth/cadastro',
    configurar: '/api/auth/configurar',
    senha: '/api/auth/senha',
    credenciamento: '/api/auth/credenciamentos',
  };

  document.querySelectorAll('form[data-form]').forEach(form => {
    const erro = form.querySelector('[data-erro]');
    const ok = form.querySelector('[data-ok]');
    form.addEventListener('submit', async evento => {
      evento.preventDefault();
      mostrar(erro, ''); mostrar(ok, '');
      const dados = Object.fromEntries(new FormData(form).entries());
      const senhaNova = dados.nova_senha !== undefined ? dados.nova_senha : dados.senha;
      if (dados.senha2 !== undefined && dados.senha2 !== senhaNova) {
        mostrar(erro, 'As duas senhas não são iguais.');
        return;
      }
      delete dados.senha2;
      const botao = form.querySelector('button[type="submit"]');
      botao.disabled = true;
      try {
        const { resposta, dados: r } = await enviar(ROTAS[form.dataset.form], dados);
        if (!resposta.ok) {
          mostrar(erro, r.error || 'Não foi possível concluir. Tente de novo.', r.erros);
          return;
        }
        if (form.dataset.destino) {
          // Cadastro com a conta já liberada (aprovação manual desligada) chega ao login com outro aviso.
          window.location.href = r.liberado ? form.dataset.destino.replace('cadastro=recebido', 'cadastro=liberado')
                                            : form.dataset.destino;
          return;
        }
        form.reset();
        mostrar(ok, r.mensagem || 'Pronto.');
        form.dispatchEvent(new CustomEvent('salvo'));
      } catch (e) {
        mostrar(erro, 'Sem conexão com o servidor. Tente de novo.');
      } finally {
        botao.disabled = false;
      }
    });
  });

  // Quem acabou de se cadastrar chega ao login com o aviso do que acontece agora.
  const login = document.querySelector('form[data-form="login"]');
  const cadastro = new URLSearchParams(window.location.search).get('cadastro');
  if (login && cadastro === 'liberado') {
    mostrar(login.querySelector('[data-ok]'), 'Conta criada com sucesso.');
  } else if (login && cadastro === 'recebido') {
    mostrar(login.querySelector('[data-ok]'),
      'Cadastro recebido. Assim que o responsável técnico conferir o seu registro e aprovar a conta, entre aqui com o e-mail e a senha que você cadastrou.');
  }

  document.querySelectorAll('[data-sair]').forEach(botao => botao.addEventListener('click', async () => {
    try { await enviar('/api/auth/logout'); } finally { window.location.href = '/'; }
  }));

  // Quem está na sessão: uma consulta só por página.
  let consultaDaSessao = null;
  function quemSou() {
    if (!consultaDaSessao) {
      consultaDaSessao = fetch('/api/auth/eu', { credentials: 'same-origin' }).then(r => r.json()).then(d => (d && d.usuario) || null);
    }
    return consultaDaSessao;
  }

  // Cadastro de pacientes: por enquanto só o administrador (docs/pacientes.md). O link do menu, o botão em "Minha
  // conta" e, no check-up, o seletor de paciente são criados aqui, só para ele: para as outras contas as páginas
  // não ganham nenhum elemento, nem escondido. A home e os Termos não carregam este arquivo.
  function abrirCadastroDePacientes(usuario) {
    if (!usuario || !usuario.administrador || document.documentElement.classList.contains('embutido')) return;
    const menu = document.querySelector('header nav');
    if (menu && window.location.pathname !== '/pacientes' && !menu.querySelector('a[href="/pacientes"]')) {
      const link = document.createElement('a');
      link.href = '/pacientes'; link.className = 'hidden sm:inline hover:text-teal transition'; link.textContent = 'Pacientes';
      menu.insertBefore(link, menu.querySelector('a[href="/conta"]') || menu.querySelector('[data-sair]'));
    }
    const atalhos = document.querySelector('p[data-so-admin]');
    if (atalhos) {
      const botao = document.createElement('a');
      botao.href = '/pacientes'; botao.className = 'btn-claro mt-2';
      const icone = document.createElement('i'); icone.className = 'fa-solid fa-address-book text-[12px]'; icone.setAttribute('aria-hidden', 'true');
      botao.append(icone, 'Pacientes');
      atalhos.append(' ', botao);
    }
    if (document.getElementById('checkupForm')) {
      ['/static/pacientes.js', '/static/pacientes-checkup.js'].forEach(endereco => {
        const script = document.createElement('script');
        script.src = endereco; script.async = false;      // na ordem: o segundo depende do primeiro
        document.head.appendChild(script);
      });
    }
  }
  if (document.querySelector('header nav [data-sair]')) quemSou().then(abrirCadastroDePacientes).catch(() => {});

  // Página "Minha conta"
  const nome = document.querySelector('[data-nome]');
  if (nome) {
    quemSou().then(usuario => {
      if (!usuario) { window.location.href = '/login'; return; }
      nome.textContent = usuario.nome.split(' ')[0] + '.';
      const perfis = { medico: 'Médico(a)', residente: 'Residente', estudante: 'Estudante de medicina' };
      const resumo = document.querySelector('[data-resumo]');
      if (resumo) resumo.textContent = `${perfis[usuario.perfil] || ''} · ${usuario.registro} · ${usuario.email}`;
      if (usuario.administrador) document.querySelectorAll('[data-so-admin]').forEach(el => { el.style.display = 'block'; });
      if (usuario.perfil === 'medico' || usuario.perfil === 'residente') { abrirPlanos(usuario); abrirSus(); abrirTimbrado(usuario); abrirAssinatura(); }
    }).catch(() => {});
  }

  // Assinatura digital: preferências e sessão aberta no provedor do certificado (só de quem assina)
  async function abrirAssinatura() {
    const secao = document.querySelector('[data-assinatura]');
    if (!secao) return;
    let dados;
    try {
      const r = await fetch('/api/auth/assinatura', { credentials: 'same-origin' });
      dados = r.ok ? await r.json() : {};
    } catch (e) { return; }
    if (!dados.disponivel) return;       // sem provedor configurado, a seção não aparece
    secao.style.display = 'block';
    const erro = secao.querySelector('[data-erro]'), ok = secao.querySelector('[data-ok]');
    const provedor = document.getElementById('assinaturaProvedor'), horas = document.getElementById('assinaturaHoras');
    const sempre = document.getElementById('assinaturaSempre');
    const T = t => (window.evidensIdioma ? window.evidensIdioma.traduzir(t) : t);
    dados.provedores.forEach(p => { const o = document.createElement('option'); o.value = p.id; o.textContent = p.nome; provedor.appendChild(o); });
    (dados.em_breve || []).forEach(n => { const o = document.createElement('option'); o.disabled = true; o.textContent = `${n} (${T('em breve')})`; provedor.appendChild(o); });
    dados.duracoes.forEach(h => { const o = document.createElement('option'); o.value = h; o.textContent = h === 1 ? T('1 hora') : `${h} ${T('horas')}`; horas.appendChild(o); });
    provedor.value = dados.preferencias.provedor; horas.value = dados.preferencias.horas; sempre.checked = !!dados.preferencias.assinar;

    function mostrarSessao(s) {
      const linha = secao.querySelector('[data-assinatura-sessao]');
      secao.querySelector('[data-assinatura-acoes]').style.display = s ? 'flex' : 'none';
      if (!s) { linha.textContent = T('Nenhuma sessão de assinatura aberta.'); return; }
      const ate = new Date(s.expira_em * 1000).toLocaleString(document.documentElement.lang || 'pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
      linha.textContent = `${T('Assinatura ativa')} · ${s.nome} · ${s.titular} · ${T('até')} ${ate}`;
    }
    mostrarSessao(dados.sessao);

    async function guardar() {
      mostrar(erro, ''); mostrar(ok, '');
      try {
        const { resposta, dados: r } = await enviar('/api/auth/assinatura/preferencias',
          { provedor: provedor.value, horas: Number(horas.value), assinar: sempre.checked });
        if (!resposta.ok) { mostrar(erro, r.error || 'Não foi possível salvar.'); return; }
        mostrar(ok, 'Preferência salva.');
      } catch (e) { mostrar(erro, 'Sem conexão com o servidor. Tente de novo.'); }
    }
    [provedor, horas, sempre].forEach(el => el.addEventListener('change', guardar));
    secao.querySelector('[data-assinatura-encerrar]').addEventListener('click', async () => {
      mostrar(erro, ''); mostrar(ok, '');
      try {
        const { resposta } = await enviar('/api/auth/assinatura/encerrar');
        if (!resposta.ok) { mostrar(erro, 'Não foi possível encerrar a sessão. Tente de novo.'); return; }
        mostrarSessao(null);
        mostrar(ok, 'Sessão de assinatura encerrada.');
      } catch (e) { mostrar(erro, 'Sem conexão com o servidor. Tente de novo.'); }
    });
  }

  // Receituário: modelo do Evidēns, modelo enviado, montado na tela ou papel já timbrado (só de quem assina)
  function abrirTimbrado(usuario) {
    const secao = document.querySelector('[data-timbrado]');
    if (!secao) return;
    secao.style.display = 'block';
    const T = t => (window.evidensIdioma ? window.evidensIdioma.traduzir(t) : t);
    const erro = secao.querySelector('[data-erro]'), ok = secao.querySelector('[data-ok]');
    const entrada = document.getElementById('timbradoPdf');
    const topo = document.getElementById('margem_topo'), base = document.getElementById('margem_base');
    const form = secao.querySelector('form[data-bloco="montado"]');
    const ajuste = secao.querySelector('[data-ajuste]');
    const folha = secao.querySelector('[data-folha]'), img = secao.querySelector('[data-folha-img]');
    let estado = null, aberto = null;

    // [hidden] perde para as classes de display (flex) do Tailwind: mostrar e esconder pelo style.
    const ver = (el, sim) => { el.hidden = false; el.style.display = sim ? '' : 'none'; };
    function limpar() { mostrar(erro, ''); mostrar(ok, ''); }
    function falhou(dados, padrao) { mostrar(erro, T((dados && dados.error) || padrao)); }

    function desenharLinhas() {
      const a = estado && estado.ativo;
      if (!a) return;
      const t = Math.max(0, Number(topo.value) || 0), b = Math.max(0, Number(base.value) || 0);
      const pt = (t / a.altura) * 100, pb = (b / a.altura) * 100;
      secao.querySelector('[data-sombra="topo"]').style.height = pt + '%';
      secao.querySelector('[data-sombra="base"]').style.height = pb + '%';
      secao.querySelector('[data-linha="topo"]').style.top = pt + '%';
      const linhaBase = secao.querySelector('[data-linha="base"]');
      linhaBase.style.bottom = pb + '%';
      secao.querySelector('[data-linha="topo"]').setAttribute('aria-valuenow', Math.round(t));
      linhaBase.setAttribute('aria-valuenow', Math.round(b));
    }

    function aplicar(novo) {
      estado = novo;
      const modo = estado.modo;
      aberto = aberto || modo;
      secao.querySelectorAll('[data-modo]').forEach(b => b.setAttribute('aria-checked', b.dataset.modo === aberto ? 'true' : 'false'));
      secao.querySelectorAll('[data-modo]').forEach(b => b.classList.toggle('bg-teal', b.dataset.modo === modo));
      secao.querySelectorAll('[data-modo]').forEach(b => b.classList.toggle('text-white', b.dataset.modo === modo));
      secao.querySelectorAll('[data-bloco]').forEach(el => ver(el, el.dataset.bloco === aberto));
      const t = estado.timbrado;
      ver(secao.querySelector('[data-timbrado-atual]'), !!t);
      if (t) secao.querySelector('[data-timbrado-nome]').textContent =
        `${t.nome} · ${t.largura} × ${t.altura} mm · ${T('enviado em')} ${new Date(t.enviado_em * 1000).toLocaleDateString(document.documentElement.lang || 'pt-BR')}`;
      const m = estado.montado;
      if (m) ['nome', 'registro', 'especialidade', 'endereco', 'contato', 'tema', 'alinhamento', 'cor'].forEach(c => { if (m[c] !== undefined) form.elements[c].value = m[c]; });
      else if (!form.elements.nome.value && usuario) { form.elements.nome.value = usuario.nome; form.elements.registro.value = usuario.registro || ''; }
      ver(secao.querySelector('[data-tem-logo]'), !!(m && m.tem_logo));
      document.getElementById('rec_remover_logo').checked = false;
      document.getElementById('rec_logo').value = '';
      // O ajuste dos espaços aparece para o receituário que está valendo, quando é o que está aberto.
      const comAjuste = modo !== 'padrao' && modo === aberto && estado.ativo;
      ver(ajuste, !!comAjuste);
      if (comAjuste) {
        topo.value = Math.round(estado.ativo.margem_topo); base.value = Math.round(estado.ativo.margem_base);
        topo.max = base.max = Math.floor(estado.ativo.altura * 0.4);
        img.src = '/api/auth/timbrado/imagem?v=' + Date.now();
        secao.querySelector('[data-timbrado-previa]').href = '/api/auth/timbrado/previa?v=' + Date.now();
        desenharLinhas();
      }
    }

    async function postar(caminho, corpo, mensagem) {
      limpar();
      try {
        const r = await fetch(caminho, corpo instanceof FormData
          ? { method: 'POST', body: corpo, credentials: 'same-origin' }
          : { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify(corpo || {}) });
        const dados = await r.json().catch(() => ({}));
        if (!r.ok) { falhou(dados, 'Não foi possível salvar.'); return false; }
        aplicar(dados);
        if (mensagem) mostrar(ok, T(mensagem));
        return true;
      } catch (e) { mostrar(erro, T('Sem conexão com o servidor. Tente de novo.')); return false; }
    }

    // Escolher o modo: o que já tem conteúdo passa a valer na hora; o que falta preencher só abre.
    secao.querySelectorAll('[data-modo]').forEach(botao => botao.addEventListener('click', () => {
      const modo = botao.dataset.modo;
      aberto = modo;
      const pronto = modo === 'padrao' || modo === 'papel' || (modo === 'modelo' && estado.timbrado) || (modo === 'montado' && estado.montado);
      if (pronto && modo !== estado.modo) {
        const msg = { padrao: 'Os pedidos saem no modelo do Evidēns.', papel: 'Os pedidos saem sem fundo, para o seu papel timbrado. Ajuste os espaços abaixo.',
                      modelo: 'Os pedidos voltam a sair no seu modelo.', montado: 'Os pedidos saem no receituário que você montou.' }[modo];
        postar('/api/auth/timbrado/modo', { modo }, msg);
      } else { limpar(); aplicar(estado); }
    }));

    async function enviarArquivo(arquivo) {
      if (!arquivo) return;
      const corpo = new FormData(); corpo.append('arquivo', arquivo);
      mostrar(ok, T('Enviando…'));
      await postar('/api/auth/timbrado', corpo, 'Modelo salvo. Confira os espaços e a prévia: os próximos pedidos já saem nele.');
    }
    entrada.addEventListener('change', () => { enviarArquivo(entrada.files[0]); entrada.value = ''; });
    const soltar = secao.querySelector('[data-soltar]');
    ['dragenter', 'dragover'].forEach(n => soltar.addEventListener(n, e => { e.preventDefault(); soltar.classList.add('border-teal'); }));
    ['dragleave', 'drop'].forEach(n => soltar.addEventListener(n, e => { e.preventDefault(); soltar.classList.remove('border-teal'); }));
    soltar.addEventListener('drop', e => enviarArquivo(e.dataTransfer.files[0]));
    secao.querySelector('[data-timbrado-remover]').addEventListener('click', () =>
      postar('/api/auth/timbrado/remover', {}, 'Modelo removido.'));

    form.addEventListener('submit', e => {
      e.preventDefault();
      if (!form.elements.nome.value.trim()) { mostrar(erro, T('Informe o nome que vai no cabeçalho.')); return; }
      postar('/api/auth/timbrado/montado', new FormData(form), 'Receituário salvo. Confira os espaços e a prévia: os próximos pedidos já saem nele.');
    });

    // Arrastar as linhas (mouse, toque e setas do teclado)
    function arrastar(qual) {
      const linha = secao.querySelector(`[data-linha="${qual}"]`);
      const campo = qual === 'topo' ? topo : base;
      function mover(ev) {
        const caixa = folha.getBoundingClientRect();
        const y = Math.min(Math.max(ev.clientY - caixa.top, 0), caixa.height);
        const mm = (qual === 'topo' ? y : caixa.height - y) / caixa.height * estado.ativo.altura;
        campo.value = Math.round(mm);
        desenharLinhas();
      }
      linha.addEventListener('pointerdown', ev => {
        ev.preventDefault(); linha.setPointerCapture(ev.pointerId);
        linha.addEventListener('pointermove', mover);
        linha.addEventListener('pointerup', () => linha.removeEventListener('pointermove', mover), { once: true });
      });
      linha.addEventListener('keydown', ev => {
        const passo = { ArrowDown: 1, ArrowUp: -1 }[ev.key];
        if (!passo) return;
        ev.preventDefault();
        campo.value = Math.max(0, (Number(campo.value) || 0) + (qual === 'topo' ? passo : -passo));
        desenharLinhas();
      });
    }
    arrastar('topo'); arrastar('base');
    [topo, base].forEach(c => c.addEventListener('input', desenharLinhas));
    secao.querySelector('[data-timbrado-margens]').addEventListener('click', () =>
      postar('/api/auth/timbrado/margens', { margem_topo: topo.value, margem_base: base.value }, 'Espaços salvos. Confira a prévia.'));

    fetch('/api/auth/timbrado', { credentials: 'same-origin' }).then(r => r.json()).then(d => { if (d.disponivel) aplicar(d); }).catch(() => {});
  }

  // SUS: estabelecimentos (CNES, cadastro compartilhado) e o CNS do médico, para o laudo de APAC
  function abrirSus() {
    const secao = document.querySelector('[data-sus]');
    if (!secao) return;
    secao.style.display = 'block';
    const lista = secao.querySelector('[data-lista-sus]');
    const form = secao.querySelector('form');
    const erro = form.querySelector('[data-erro]'), ok = form.querySelector('[data-ok]');
    const cnes = form.querySelector('[name="cnes"]'), nome = form.querySelector('[name="nome"]');
    const achado = form.querySelector('[data-sus-achado]');

    // CNES já cadastrado por outro médico: o nome vem do cadastro e não é digitado de novo.
    async function conferirCnes() {
      const digitos = cnes.value.replace(/\D/g, '');
      achado.hidden = true; nome.readOnly = false;
      if (digitos.length !== 7) return;
      try {
        const r = await fetch('/api/auth/estabelecimentos?cnes=' + digitos, { credentials: 'same-origin' });
        const { estabelecimentos } = await r.json();
        if (estabelecimentos && estabelecimentos.length) {
          nome.value = estabelecimentos[0].nome; nome.readOnly = true;
          achado.textContent = 'Estabelecimento já cadastrado no Evidēns.'; achado.hidden = false;
        }
      } catch (e) { /* segue com o nome digitado */ }
    }
    cnes.addEventListener('input', conferirCnes);

    function linha(v) {
      const div = document.createElement('div');
      div.className = 'recommendation-card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3';
      const info = document.createElement('div');
      const h = document.createElement('h5'); h.textContent = v.nome;
      const p = document.createElement('p'); p.className = 'text-[14px] text-ink/60 mt-1';
      p.textContent = `CNES ${v.cnes} · seu CNS ${v.cns}`;
      info.append(h, p);
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn-claro shrink-0'; b.textContent = 'Remover';
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          const { resposta, dados } = await enviar(`/api/auth/vinculos-sus/${v.id}/excluir`);
          if (!resposta.ok) { mostrar(erro, dados.error || 'Não foi possível remover. Tente de novo.'); return; }
          carregar();
        } catch (e) {
          mostrar(erro, 'Sem conexão com o servidor. Tente de novo.');
        } finally { b.disabled = false; }
      });
      div.append(info, b);
      return div;
    }

    async function carregar() {
      try {
        const r = await fetch('/api/auth/vinculos-sus', { credentials: 'same-origin' });
        const { vinculos } = await r.json();
        lista.replaceChildren(...(vinculos || []).map(linha));
      } catch (e) { /* a lista fica como está */ }
    }

    form.addEventListener('submit', async ev => {
      ev.preventDefault();
      mostrar(erro, ''); mostrar(ok, '');
      const botao = form.querySelector('button[type="submit"]');
      botao.disabled = true;
      try {
        const { resposta, dados } = await enviar('/api/auth/vinculos-sus', Object.fromEntries(new FormData(form).entries()));
        if (!resposta.ok) { mostrar(erro, dados.error || 'Não foi possível salvar. Tente de novo.', dados.erros); return; }
        mostrar(ok, dados.mensagem || 'Salvo.');
        form.reset(); nome.readOnly = false; achado.hidden = true;
        carregar();
      } catch (e) {
        mostrar(erro, 'Sem conexão com o servidor. Tente de novo.');
      } finally { botao.disabled = false; }
    });
    carregar();
  }

  // Planos de saúde em que o médico é credenciado (dados da guia SP/SADT)
  function abrirPlanos(usuario) {
    const secao = document.querySelector('[data-planos]');
    if (!secao) return;
    secao.style.display = 'block';
    const lista = secao.querySelector('[data-lista-planos]');
    const form = secao.querySelector('form');
    const erro = form.querySelector('[data-erro]');
    const contratado = form.querySelector('[name="nome_contratado"]');
    const sugerirNome = () => { if (!contratado.value) contratado.value = usuario.nome; };
    sugerirNome();

    function linha(plano) {
      const div = document.createElement('div');
      div.className = 'recommendation-card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3';
      const info = document.createElement('div');
      const h = document.createElement('h5'); h.textContent = plano.operadora;
      const p = document.createElement('p'); p.className = 'text-[14px] text-ink/60 mt-1';
      const partes = [plano.codigo_prestador, plano.nome_contratado];
      if (plano.registro_ans) partes.push(`ANS ${plano.registro_ans}`);
      if (plano.cbo) partes.push(`CBO ${plano.cbo}`);
      p.textContent = partes.join(' · ');
      info.append(h, p);
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn-claro shrink-0'; b.textContent = 'Remover';
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          const { resposta, dados } = await enviar(`/api/auth/credenciamentos/${plano.id}/excluir`);
          if (!resposta.ok) { mostrar(erro, dados.error || 'Não foi possível remover. Tente de novo.'); return; }
          carregar();
        } catch (e) {
          mostrar(erro, 'Sem conexão com o servidor. Tente de novo.');
        } finally {
          b.disabled = false;
        }
      });
      div.append(info, b);
      return div;
    }

    async function carregar() {
      try {
        const r = await fetch('/api/auth/credenciamentos', { credentials: 'same-origin' });
        const { credenciamentos } = await r.json();
        lista.replaceChildren(...(credenciamentos || []).map(linha));
      } catch (e) { /* a lista fica como está */ }
    }

    form.addEventListener('salvo', () => { sugerirNome(); carregar(); });
    carregar();
  }

  // Painel de contas
  const listas = document.querySelectorAll('[data-lista]');
  if (listas.length) {
    const erro = document.querySelector('main > [data-erro]');
    const ok = document.querySelector('main > [data-ok]');
    const perfis = { medico: 'Médico(a)', residente: 'Residente', estudante: 'Estudante' };
    const ACOES = {
      pendente: [['aprovar', 'Aprovar', 'btn-escuro'], ['bloquear', 'Recusar', 'btn-claro']],
      aprovado: [['bloquear', 'Bloquear', 'btn-claro'], ['redefinir-senha', 'Gerar senha temporária', 'btn-claro']],
      bloqueado: [['aprovar', 'Reativar', 'btn-claro']],
    };

    function cartao(u) {
      const div = document.createElement('div');
      div.className = 'recommendation-card flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4';
      const info = document.createElement('div');
      const h = document.createElement('h5'); h.textContent = u.nome + (u.administrador ? ' (administrador)' : '');
      const p = document.createElement('p'); p.className = 'text-[14px] text-ink/60 mt-1';
      p.textContent = `${perfis[u.perfil] || u.perfil} · ${u.registro} · ${u.email} · cadastro em ${new Date(u.criado_em * 1000).toLocaleDateString('pt-BR')}`;
      info.append(h, p);
      const botoes = document.createElement('div'); botoes.className = 'flex flex-wrap gap-2 shrink-0';
      if (!u.administrador) (ACOES[u.situacao] || []).forEach(([acao, texto, classe]) => {
        const b = document.createElement('button'); b.type = 'button'; b.className = classe; b.textContent = texto;
        b.addEventListener('click', () => agir(u, acao));
        botoes.appendChild(b);
      });
      div.append(info, botoes);
      return div;
    }

    async function carregar() {
      const r = await fetch('/api/admin/usuarios', { credentials: 'same-origin' });
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) { mostrar(erro, 'Não foi possível carregar os cadastros.'); return; }
      const { usuarios, aprovacao_manual } = await r.json();
      pintarAprovacao(aprovacao_manual);
      listas.forEach(lista => {
        const situacao = lista.dataset.lista;
        const itens = usuarios.filter(u => u.situacao === situacao);
        lista.replaceChildren(...itens.map(cartao));
        if (!itens.length) { const p = document.createElement('p'); p.className = 'text-[14px] text-ink/50'; p.textContent = 'Ninguém aqui.'; lista.appendChild(p); }
        const n = document.querySelector(`[data-contagem="${situacao}"]`); if (n) n.textContent = itens.length;
      });
    }

    // Reserva: aprovação manual de contas novas (desligada, a conta nasce liberada)
    const aprovacao = document.querySelector('[data-aprovacao]');
    let manual = false;
    function pintarAprovacao(ligada) {
      if (!aprovacao) return;
      manual = !!ligada;
      aprovacao.querySelector('[data-aprovacao-estado]').textContent = manual
        ? 'Ligada: contas novas ficam em "Aguardando aprovação" até você aprovar.'
        : 'Desligada: a conta é liberada assim que é criada. Ligue se precisar fechar o cadastro de novo.';
      aprovacao.querySelector('[data-aprovacao-botao]').textContent = manual ? 'Desligar a aprovação manual' : 'Ligar a aprovação manual';
    }
    const botaoAprovacao = aprovacao && aprovacao.querySelector('[data-aprovacao-botao]');
    if (botaoAprovacao) botaoAprovacao.addEventListener('click', async () => {
      mostrar(erro, ''); mostrar(ok, '');
      botaoAprovacao.disabled = true;
      const { resposta, dados } = await enviar('/api/admin/aprovacao-manual', { ligada: !manual });
      botaoAprovacao.disabled = false;
      if (!resposta.ok) { mostrar(erro, (dados && dados.error) || 'Não foi possível mudar a aprovação manual.'); return; }
      pintarAprovacao(dados.aprovacao_manual);
      mostrar(ok, dados.aprovacao_manual ? 'Aprovação manual ligada.' : 'Aprovação manual desligada: contas novas já nascem liberadas.');
    });

    async function agir(u, acao) {
      mostrar(erro, ''); mostrar(ok, '');
      const { resposta, dados } = await enviar(`/api/admin/usuarios/${u.id}/${acao}`);
      if (!resposta.ok) { mostrar(erro, dados.error || 'Não foi possível concluir.'); return; }
      if (dados.senha_temporaria) {
        mostrar(ok, `Senha temporária de ${u.nome}: ${dados.senha_temporaria} — anote agora; ela não será mostrada de novo. Peça que a pessoa troque a senha ao entrar.`);
      }
      if (dados.aviso) {  // aprovação ou reativação: diz se a pessoa foi avisada por e-mail
        mostrar(ok, dados.aviso.enviado
          ? `Conta de ${u.nome} liberada. O aviso foi enviado para ${u.email}.`
          : `Conta de ${u.nome} liberada. O e-mail de aviso não foi enviado: ${dados.aviso.motivo}. Avise a pessoa por outro meio.`);
      }
      carregar();
    }

    carregar();

    // Aviso por e-mail a cada novo pedido de conta
    const aviso = document.querySelector('[data-aviso]');
    if (aviso) {
      const estado = aviso.querySelector('[data-aviso-estado]');
      const botao = aviso.querySelector('[data-aviso-teste]');
      const estadoBv = aviso.querySelector('[data-boas-vindas-estado]');
      const botaoBv = aviso.querySelector('[data-boas-vindas-teste]');
      botaoBv.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        botaoBv.disabled = true;
        const { resposta, dados } = await enviar('/api/admin/boas-vindas/teste');
        botaoBv.disabled = false;
        if (!resposta.ok) { mostrar(erro, (dados && dados.error) || 'Não foi possível enviar o e-mail de boas-vindas.'); return; }
        mostrar(ok, 'Boas-vindas de teste enviadas a ' + dados.destinatarios.join(', ') + '.');
      });
      // Agradecimento a quem criou a conta antes de existir o e-mail de boas-vindas
      const estadoAg = aviso.querySelector('[data-agradecimento-estado]');
      const testeAg = aviso.querySelector('[data-agradecimento-teste]');
      const enviarAg = aviso.querySelector('[data-agradecimento-enviar]');
      let pendentesAg = 0, confirmarAg = false, ligadoAg = false;
      function pintarAgradecimento(ligado) {
        if (ligado !== undefined) ligadoAg = !!ligado;
        confirmarAg = false;
        const n = pendentesAg, pessoas = n === 1 ? '1 conta' : n + ' contas';
        estadoAg.textContent = n
          ? 'Agradecimento: ' + pessoas + ' ainda não ' + (n === 1 ? 'recebeu' : 'receberam') + ' e-mail nosso (contas criadas antes das boas-vindas). Cada conta recebe uma vez só.'
            + (ligadoAg ? '' : ' O envio fica disponível quando as boas-vindas estiverem ligadas.')
          : 'Agradecimento: todas as contas já receberam e-mail nosso.';
        enviarAg.textContent = n ? 'Enviar agradecimento a ' + pessoas : 'Enviar agradecimento';
        enviarAg.disabled = !ligadoAg || !n;
        testeAg.disabled = !ligadoAg;
      }
      testeAg.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        testeAg.disabled = true;
        const { resposta, dados } = await enviar('/api/admin/agradecimento/teste');
        testeAg.disabled = false;
        if (!resposta.ok) { mostrar(erro, (dados && dados.error) || 'Não foi possível enviar o e-mail de agradecimento.'); return; }
        mostrar(ok, 'Agradecimento de teste enviado a ' + dados.destinatarios.join(', ') + '.');
      });
      enviarAg.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        if (!confirmarAg) {  // dois cliques: o primeiro só pede a confirmação
          confirmarAg = true;
          enviarAg.textContent = 'Confirmar: enviar a ' + (pendentesAg === 1 ? '1 conta' : pendentesAg + ' contas');
          return;
        }
        enviarAg.disabled = true; testeAg.disabled = true;
        let total = 0, falhas = 0, motivo = '';
        while (true) {
          enviarAg.textContent = 'Enviando… ' + total + ' enviado' + (total === 1 ? '' : 's');
          const { resposta, dados } = await enviar('/api/admin/agradecimento');
          if (!resposta.ok) { motivo = (dados && dados.error) || 'Não foi possível enviar o agradecimento.'; break; }
          total += dados.enviados; falhas = dados.falhas; pendentesAg = dados.restantes;
          if (dados.falhas) motivo = 'Falha no envio: ' + (dados.motivo || 'erro desconhecido') + '.';
          if (!dados.restantes || !dados.enviados) break;
        }
        pintarAgradecimento();
        if (total) mostrar(ok, 'Agradecimento enviado a ' + (total === 1 ? '1 conta' : total + ' contas') + '.');
        if (motivo) mostrar(erro, motivo + (pendentesAg ? ' Restam ' + pendentesAg + ' sem receber; tente de novo em instantes.' : ''));
      });
      // Comunicado de novidades: sai sozinho pelo cron na data marcada; o botão envia antes, se preciso.
      const estadoCo = aviso.querySelector('[data-comunicado-estado]');
      const testeCo = aviso.querySelector('[data-comunicado-teste]');
      const enviarCo = aviso.querySelector('[data-comunicado-enviar]');
      let comunicado = null, confirmarCo = false, ligadoCo = false;
      function pintarComunicado() {
        confirmarCo = false;
        if (!comunicado) return;
        const n = comunicado.pendentes, pessoas = n === 1 ? '1 conta' : n + ' contas';
        const quando = new Date(comunicado.a_partir).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
        estadoCo.textContent = (n ? 'Novidades: ' + pessoas + ' a receber. Envio automático a partir de ' + quando + '.'
                                  : 'Novidades: todas as contas aprovadas já receberam.')
          + (comunicado.cron ? '' : ' O envio automático precisa da variável CRON_SECRET na Vercel; sem ela, use o botão.');
        enviarCo.textContent = n ? 'Enviar novidades agora a ' + pessoas : 'Enviar novidades agora';
        enviarCo.disabled = !ligadoCo || !n;
        testeCo.disabled = !ligadoCo;
      }
      testeCo.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        testeCo.disabled = true;
        const { resposta, dados } = await enviar('/api/admin/comunicado/teste');
        testeCo.disabled = false;
        if (!resposta.ok) { mostrar(erro, (dados && dados.error) || 'Não foi possível enviar o teste.'); return; }
        mostrar(ok, 'Novidades de teste enviadas a ' + dados.destinatarios.join(', ') + '.');
      });
      enviarCo.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        if (!confirmarCo) { confirmarCo = true; enviarCo.textContent = 'Confirmar: enviar agora'; return; }
        enviarCo.disabled = true; testeCo.disabled = true;
        let total = 0, motivo = '';
        while (true) {
          const { resposta, dados } = await enviar('/api/admin/comunicado');
          if (!resposta.ok) { motivo = (dados && dados.error) || 'Não foi possível enviar.'; break; }
          total += dados.enviados; comunicado.pendentes = dados.restantes;
          if (dados.falhas) { motivo = 'Falha no envio: ' + (dados.motivo || 'erro desconhecido') + '.'; break; }
          if (!dados.restantes || !dados.enviados) break;
        }
        pintarComunicado();
        if (total) mostrar(ok, 'Novidades enviadas a ' + (total === 1 ? '1 conta' : total + ' contas') + '.');
        if (motivo) mostrar(erro, motivo);
      });
      fetch('/api/admin/aviso', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null).then(d => {
        if (!d) { estado.textContent = 'Não foi possível verificar o aviso por e-mail.'; return; }
        estadoBv.textContent = d.boas_vindas
          ? 'Boas-vindas: ligadas. Quem cria a conta recebe um e-mail com a apresentação, a fase de desenvolvimento e o convite a dar feedback.'
          : 'Boas-vindas: desligadas. Para enviar e-mail a quem se cadastra, verifique o domínio evidens.life na Resend e defina AVISO_CADASTRO_DE na Vercel (passo a passo em docs/deploy.md).';
        botaoBv.disabled = !d.boas_vindas;
        pendentesAg = d.agradecimento_pendentes || 0;
        pintarAgradecimento(d.boas_vindas);
        comunicado = d.comunicado || null; ligadoCo = !!d.boas_vindas;
        pintarComunicado();
        if (!d.configurado) {
          estado.textContent = 'Desligado. Para receber um e-mail a cada conta nova, cadastre a variável RESEND_API_KEY na Vercel (passo a passo em docs/deploy.md).';
          return;
        }
        estado.textContent = d.destinatarios.length
          ? 'Ligado. Cada conta nova é avisada a: ' + d.destinatarios.join(', ') + '.'
          : 'Ligado, mas sem destinatário: defina AVISO_CADASTRO_PARA na Vercel.';
        botao.disabled = !d.destinatarios.length;
      }).catch(() => { estado.textContent = 'Não foi possível verificar o aviso por e-mail.'; });
      botao.addEventListener('click', async () => {
        mostrar(erro, ''); mostrar(ok, '');
        botao.disabled = true;
        const { resposta, dados } = await enviar('/api/admin/aviso/teste');
        botao.disabled = false;
        if (!resposta.ok) { mostrar(erro, (dados && dados.error) || 'Não foi possível enviar o e-mail de teste.'); return; }
        mostrar(ok, 'E-mail de teste enviado a ' + dados.destinatarios.join(', ') + '. Confira também a caixa de spam.');
      });
    }
  }
})();
