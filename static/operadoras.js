// Modo sombra das operadoras (/operadoras, só administrador). Envia a planilha ou os laudos para
// /api/admin/operadoras/classificar e mostra o resultado. Nada fica guardado: recarregar a página apaga tudo.
(function () {
  'use strict';
  const ROTULOS = { verde: 'Liberaria', amarelo: 'Pediria esclarecimento', vermelho: 'Barraria', fora_do_escopo: 'Fora do escopo' };
  const CORES = { verde: 'bg-mist text-teal-dark', amarelo: 'bg-sand text-ink', vermelho: 'bg-[#C0392B] text-white', fora_do_escopo: 'bg-ink/10 text-ink' };
  const MODELO = 'id_pedido;id_beneficiario;idade;sexo;data_pedido;codigo_tuss;carater;regime;finalidade;cid;data_ultimo_exame;valor\n'
    + 'P0001;B0001;52;F;2026-11-10;40316521;eletivo;ambulatorial;rastreio;Z00.0;;18,50\n'
    + 'P0001;B0001;52;F;2026-11-10;40302830;eletivo;ambulatorial;rastreio;Z00.0;;45,00\n';
  let dados = null;
  let filtro = '';

  const $ = sel => document.querySelector(sel);
  const numero = n => Number(n || 0).toLocaleString('pt-BR');
  const reais = v => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  function el(tag, classe, texto) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function erro(mensagem) {
    const caixa = $('[data-erro]');
    caixa.textContent = mensagem || '';
    caixa.style.display = mensagem ? '' : 'none';
  }
  function baixar(nome, texto) {
    const link = el('a');
    link.href = URL.createObjectURL(new Blob(['﻿' + texto], { type: 'text/csv;charset=utf-8' }));
    link.download = nome;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function resumo() {
    const r = dados.resumo;
    const validas = r.linhas - r.invalidas;
    $('[data-versao]').textContent = `versão ${r.versao}`;
    $('[data-cartoes]').replaceChildren(...Object.keys(ROTULOS).map(cor => {
      const n = (r.por_cor || {})[cor] || 0;
      const c = el('div', 'recommendation-card');
      c.append(el('p', 'text-[12px] text-ink/55 leading-snug', ROTULOS[cor]),
               el('p', 'text-[32px] font-light tracking-tightest leading-none mt-3', numero(n)),
               el('p', 'text-[12px] text-ink/50 mt-2', (validas ? (100 * n / validas).toFixed(1).replace('.', ',') + '%' : '')
                 + ((r.valor_por_cor || {})[cor] ? ' · ' + reais(r.valor_por_cor[cor]) : '')));
      return c;
    }));
    const notas = [`${numero(r.linhas)} linhas lidas; ${numero(r.invalidas)} com erro de preenchimento.`]
      .concat(dados.avisos || []);
    if ((r.mais_barrados || []).length) notas.push('Mais barrados: ' + r.mais_barrados.map(([exame, n]) => `${exame} (${n})`).join('; ') + '.');
    $('[data-notas]').replaceChildren(...notas.map(t => el('span', 'block', t)));
  }

  function tabela() {
    const linhas = dados.linhas.filter(l => !filtro || l.cor === filtro);
    $('[data-contagem]').textContent = `(${linhas.length})`;
    document.querySelectorAll('[data-filtro]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.filtro === filtro)));
    if (!linhas.length) {
      const tr = el('tr'); const td = el('td', 'px-4 py-6 text-ink/50', 'Nenhum pedido neste filtro.'); td.colSpan = 4;
      tr.append(td); $('[data-linhas]').replaceChildren(tr); return;
    }
    $('[data-linhas]').replaceChildren(...linhas.map(l => {
      const tr = el('tr', 'border-b border-ink/5 last:border-0 align-top');
      const pedido = el('td', 'px-4 py-3');
      pedido.append(el('span', 'block', l.id_pedido || '—'),
                    el('span', 'block text-[12px] text-ink/50', [l.id_beneficiario, l.data_pedido].filter(Boolean).join(' · ')));
      const exame = el('td', 'px-3 py-3');
      exame.append(el('span', 'block', l.exame || '—'), el('span', 'block text-[12px] text-ink/50 font-mono', l.codigo_tuss));
      const parecer = el('td', 'px-3 py-3 whitespace-nowrap');
      parecer.append(l.erro ? el('span', 'selo bg-ink/15 text-ink', 'Linha com erro')
                            : el('span', 'selo ' + (CORES[l.cor] || 'bg-ink/10 text-ink'), ROTULOS[l.cor] || l.cor));
      // No celular a coluna do motivo some e o texto vai para baixo do exame.
      exame.append(el('span', 'block md:hidden text-[13px] text-ink/75 mt-2', l.erro || l.motivo));
      const motivo = el('td', 'px-3 py-3 hidden md:table-cell');
      motivo.append(el('span', 'block', l.erro || l.motivo));
      if (l.aviso) motivo.append(el('span', 'block text-[12px] text-[#C0392B] mt-1', l.aviso));
      if (l.referencia) {
        const fonte = el('span', 'block text-[12px] text-ink/50 mt-1');
        const url = (l.link || '').split(' | ')[0];
        if (/^https:\/\/[^\s"'<>]+$/.test(url)) {
          const a = el('a', 'underline', l.referencia); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer';
          fonte.append(a);
        } else fonte.textContent = l.referencia;
        if (l.grau) fonte.append(` · grau ${l.grau}`);
        motivo.append(fonte);
      }
      tr.append(pedido, exame, parecer, motivo);
      return tr;
    }));
  }

  async function enviar(formulario) {
    erro('');
    $('[data-andamento]').style.display = '';
    formulario.querySelectorAll('button').forEach(b => { b.disabled = true; });
    try {
      const r = await fetch('/api/admin/operadoras/classificar', { method: 'POST', body: new FormData(formulario), credentials: 'same-origin' });
      const corpo = await r.json().catch(() => ({}));
      if (r.status === 401) { window.location.href = '/login'; return; }
      if (!r.ok) throw new Error(corpo.error || 'Não foi possível classificar o arquivo.');
      dados = corpo; filtro = '';
      $('[data-resultado]').style.display = '';
      resumo(); tabela();
      $('[data-resultado]').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
      erro(e.message);
    } finally {
      $('[data-andamento]').style.display = 'none';
      formulario.querySelectorAll('button').forEach(b => { b.disabled = false; });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('[data-form-csv]').addEventListener('submit', e => { e.preventDefault(); enviar(e.target); });
    $('[data-form-laudos]').addEventListener('submit', e => { e.preventDefault(); enviar(e.target); });
    $('[data-modelo]').addEventListener('click', () => baixar('modelo_pedidos.csv', MODELO));
    $('[data-baixar]').addEventListener('click', () => { if (dados) baixar('pedidos_classificados.csv', dados.csv); });
    document.querySelectorAll('[data-filtro]').forEach(b => b.addEventListener('click', () => { filtro = b.dataset.filtro; if (dados) tabela(); }));
  });
})();
