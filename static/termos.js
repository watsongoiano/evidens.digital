// Termos de Uso: para quem está com o aceite pendente, mostra o pedido de aceite no topo da página.
(function () {
  'use strict';
  const DESTINOS = { 'check-up': '/intelligent-tools', conta: '/conta', admin: '/admin', analytics: '/analytics' };
  const params = new URLSearchParams(window.location.search);
  const destino = DESTINOS[params.get('destino')] || '/intelligent-tools';
  const caixa = document.querySelector('[data-aceite]');
  if (!caixa) return;
  const marcar = caixa.querySelector('[data-aceite-caixa]');
  const botao = caixa.querySelector('[data-aceitar]');
  const erro = caixa.querySelector('[data-erro]');
  const versao = document.querySelector('[data-versao]').getAttribute('datetime');

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
