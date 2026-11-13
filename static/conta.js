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
          window.location.href = form.dataset.destino;
          return;
        }
        form.reset();
        mostrar(ok, r.mensagem || 'Pronto.');
      } catch (e) {
        mostrar(erro, 'Sem conexão com o servidor. Tente de novo.');
      } finally {
        botao.disabled = false;
      }
    });
  });

  // Quem acabou de se cadastrar chega ao login com o aviso de que a conta aguarda aprovação.
  const login = document.querySelector('form[data-form="login"]');
  if (login && new URLSearchParams(window.location.search).get('cadastro') === 'recebido') {
    mostrar(login.querySelector('[data-ok]'),
      'Cadastro recebido. Assim que o responsável técnico conferir o seu registro e aprovar a conta, entre aqui com o e-mail e a senha que você cadastrou.');
  }

  document.querySelectorAll('[data-sair]').forEach(botao => botao.addEventListener('click', async () => {
    try { await enviar('/api/auth/logout'); } finally { window.location.href = '/'; }
  }));

  // Página "Minha conta"
  const nome = document.querySelector('[data-nome]');
  if (nome) {
    fetch('/api/auth/eu', { credentials: 'same-origin' }).then(r => r.json()).then(({ usuario }) => {
      if (!usuario) { window.location.href = '/login'; return; }
      nome.textContent = usuario.nome.split(' ')[0] + '.';
      const perfis = { medico: 'Médico(a)', residente: 'Residente', estudante: 'Estudante de medicina' };
      const resumo = document.querySelector('[data-resumo]');
      if (resumo) resumo.textContent = `${perfis[usuario.perfil] || ''} · ${usuario.registro} · ${usuario.email}`;
      if (usuario.administrador) document.querySelectorAll('[data-so-admin]').forEach(el => { el.style.display = 'block'; });
    }).catch(() => {});
  }

  // Painel de aprovação
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
      const { usuarios } = await r.json();
      listas.forEach(lista => {
        const situacao = lista.dataset.lista;
        const itens = usuarios.filter(u => u.situacao === situacao);
        lista.replaceChildren(...itens.map(cartao));
        if (!itens.length) { const p = document.createElement('p'); p.className = 'text-[14px] text-ink/50'; p.textContent = 'Ninguém aqui.'; lista.appendChild(p); }
        const n = document.querySelector(`[data-contagem="${situacao}"]`); if (n) n.textContent = itens.length;
      });
    }

    async function agir(u, acao) {
      mostrar(erro, ''); mostrar(ok, '');
      const { resposta, dados } = await enviar(`/api/admin/usuarios/${u.id}/${acao}`);
      if (!resposta.ok) { mostrar(erro, dados.error || 'Não foi possível concluir.'); return; }
      if (dados.senha_temporaria) {
        mostrar(ok, `Senha temporária de ${u.nome}: ${dados.senha_temporaria} — anote agora; ela não será mostrada de novo. Peça que a pessoa troque a senha ao entrar.`);
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
      fetch('/api/admin/aviso', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null).then(d => {
        if (!d) { estado.textContent = 'Não foi possível verificar o aviso por e-mail.'; return; }
        estadoBv.textContent = d.boas_vindas
          ? 'Boas-vindas: ligadas. Quem pede a conta recebe um e-mail explicando a aprovação, a fase de desenvolvimento e o convite a dar feedback.'
          : 'Boas-vindas: desligadas. Para enviar e-mail a quem se cadastra, verifique o domínio evidens.life na Resend e defina AVISO_CADASTRO_DE na Vercel (passo a passo em docs/deploy.md).';
        botaoBv.disabled = !d.boas_vindas;
        if (!d.configurado) {
          estado.textContent = 'Desligado. Para receber um e-mail a cada novo pedido de conta, cadastre a variável RESEND_API_KEY na Vercel (passo a passo em docs/deploy.md).';
          return;
        }
        estado.textContent = d.destinatarios.length
          ? 'Ligado. Cada novo pedido de conta é avisado a: ' + d.destinatarios.join(', ') + '.'
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
