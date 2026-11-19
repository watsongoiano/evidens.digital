// Termos de Uso: para quem está com o aceite pendente, mostra o pedido de aceite no topo da página.
(function () {
  'use strict';
  const DESTINOS = { 'check-up': '/intelligent-tools', conta: '/conta', admin: '/admin', analytics: '/analytics', operadoras: '/operadoras', pacientes: '/pacientes' };
  const params = new URLSearchParams(window.location.search);
  const destino = DESTINOS[params.get('destino')] || '/intelligent-tools';
  const caixa = document.querySelector('[data-aceite]');
  const marcar = caixa.querySelector('[data-aceite-caixa]');
  const botao = caixa.querySelector('[data-aceitar]');
  const erro = caixa.querySelector('[data-erro]');
  const versao = document.querySelector('[data-versao]').dataset.versao;
  // Imprimir: o PDF numa moldura escondida, que abre o diálogo de impressão do navegador
  // (em navegadores que não deixam, abre o PDF em outra aba para imprimir de lá).
  const imprimir = document.querySelector('[data-imprimir]');
  const pdf = document.querySelector('[data-baixar]');
  if (imprimir && pdf) imprimir.addEventListener('click', () => {
    const moldura = document.createElement('iframe');
    moldura.style.cssText = 'position:fixed;width:0;height:0;border:0;right:0;bottom:0';
    moldura.src = pdf.getAttribute('href');
    moldura.onload = () => {
      try { moldura.contentWindow.focus(); moldura.contentWindow.print(); }
      catch (e) { window.open(pdf.getAttribute('href'), '_blank', 'noopener'); }
    };
    document.body.appendChild(moldura);
  });

  if (!caixa) return;
  function falha(texto) { erro.textContent = texto; erro.style.display = 'block'; }

  fetch('/api/auth/eu', { credentials: 'same-origin' }).then(r => r.json()).then(d => {
    if (!d.usuario || !d.termos_pendentes) return;
    if (d.termos_versao !== versao) { falha('Os Termos foram atualizados. Recarregue a página.'); }
    caixa.hidden = false;
    if (params.get('aceitar')) caixa.scrollIntoView({ block: 'start' });
  }).catch(() => {});

  marcar.addEventListener('change', () => { botao.disabled = !marcar.checked; });
  botao.addEventListener('click', async () => {
    botao.disabled = true;
    erro.style.display = 'none';
    try {
      const r = await fetch('/api/auth/termos/aceitar', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ versao }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) { falha(d.error || 'Não foi possível registrar o aceite. Tente de novo.'); botao.disabled = !marcar.checked; return; }
      window.location.href = destino;
    } catch (e) {
      falha('Sem conexão com o servidor. Tente de novo.');
      botao.disabled = !marcar.checked;
    }
  });
  caixa.querySelector('[data-sair]').addEventListener('click', async () => {
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }); } catch (e) { /* segue */ }
    window.location.href = '/';
  });
}());
