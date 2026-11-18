// Conferência do pedido pelo check-up (/operadoras, por enquanto só administrador).
// O formulário do paciente é o do check-up, num quadro com a própria página do check-up (um formulário só, sem
// cópia). Ele envia os dados e o PDF anexado aqui para /api/admin/operadoras/conferir e entrega o resultado, que
// esta página mostra. Nada fica guardado: recarregar a página apaga tudo.
(function () {
  'use strict';
  const VEREDITOS = {
    indicado: { rotulo: 'Indicado', classe: 'bg-mist text-teal-dark', borda: 'border-teal/20' },
    nao_indicado: { rotulo: 'Não indicado', classe: 'bg-[#C0392B] text-white', borda: 'border-[#E5B7B1]' },
  };
  let dados = null;
  let filtro = '';

  const $ = sel => document.querySelector(sel);
  const numero = n => Number(n || 0).toLocaleString('pt-BR');
  function el(tag, classe, texto) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  const dataBr = iso => (/^\d{4}-\d{2}-\d{2}$/.test(iso || '') ? iso.split('-').reverse().join('/') : '');
  function ligacoes(alvo, referencias) {      // as fontes, cada uma com o seu link, separadas por " | "
    (referencias || []).forEach((r, i) => {
      if (i) alvo.append(' | ');
      if (/^https:\/\/[^\s"'<>]+$/.test(r.url || '')) {
        const a = el('a', 'underline', r.label); a.href = r.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
        alvo.append(a);
      } else alvo.append(r.label || '');
    });
    return alvo;
  }
  function fontes(referencias, grau) {
    const linha = ligacoes(el('p', 'text-[12px] text-ink/50 mt-2'), referencias);
    if (grau) linha.append((referencias || []).length ? ' · ' : '', `grau ${grau}`);
    return linha.childNodes.length ? linha : null;
  }

  function resumo() {
    const r = dados.resumo;
    const cartao = (rotulo, valor, nota) => {
      const c = el('div', 'recommendation-card');
      c.append(el('p', 'text-[12px] text-ink/55 leading-snug', rotulo),
               el('p', 'text-[32px] font-light tracking-tightest leading-none mt-3', numero(valor)),
               el('p', 'text-[12px] text-ink/50 mt-2', nota));
      return c;
    };
    $('[data-cartoes]').replaceChildren(
      cartao('Exames no pedido', r.pedidos, ''),
      cartao('Indicados pelo check-up', r.indicados, 'liberaria'),
      cartao('Não indicados', r.nao_indicados, 'barraria'));
    $('[data-notas]').replaceChildren(...(dados.avisos || []).map(t => el('span', 'block', t)));
    $('[data-do-checkup-contagem]').textContent = `(${r.do_checkup})`;
    $('[data-do-checkup]').replaceChildren(...dados.do_checkup.map(item => {
      const li = el('li', 'flex flex-wrap items-baseline gap-x-2');
      li.append(el('span', item.pedido ? 'text-teal-dark' : 'text-ink/45', item.pedido ? '✓ pedido' : 'não pedido'),
                el('span', '', item.titulo), el('span', 'text-[12px] text-ink/50', item.motivo));
      return li;
    }));
  }

  function lista() {
    const linhas = dados.linhas.filter(l => !filtro || l.veredito === filtro);
    $('[data-contagem]').textContent = `(${linhas.length})`;
    document.querySelectorAll('[data-filtro]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.filtro === filtro)));
    if (!linhas.length) { $('[data-linhas]').replaceChildren(el('p', 'text-[14px] text-ink/50', 'Nenhum exame neste filtro.')); return; }
    $('[data-linhas]').replaceChildren(...linhas.map(l => {
      const v = VEREDITOS[l.veredito] || VEREDITOS.nao_indicado;
      const cartao = el('div', 'nao-incluida-card ' + v.borda);
      cartao.append(el('span', 'selo ' + v.classe, v.rotulo), el('h5', '', l.exame));
      const detalhe = [l.nome_no_pedido && l.nome_no_pedido !== l.exame ? `No pedido: ${l.nome_no_pedido}` : '', dataBr(l.data)].filter(Boolean).join(' · ');
      if (detalhe) cartao.append(el('p', 'text-[12px] text-ink/50', detalhe));
      if (l.no_checkup && l.no_checkup !== l.exame) cartao.append(el('p', 'text-[12px] text-ink/50', `No check-up: ${l.no_checkup}`));
      cartao.append(el('p', 'text-[14px] text-ink/75 mt-2', l.motivo));
      if (l.aviso) cartao.append(el('p', 'text-[13px] text-[#C0392B] mt-1', l.aviso));
      const rodape = fontes(l.referencias, l.grau);
      if (rodape) cartao.append(rodape);
      const situacoes = (l.indicado_para || {}).situacoes || [];
      if (situacoes.length) {   // em que situações o check-up indica este exame, com a referência que ele usa em cada uma
        cartao.append(el('p', 'text-[13px] text-ink/60 mt-3', 'No check-up, este exame é indicado para:'));
        const lista = el('ul', 'text-[13px] text-ink/60 list-disc pl-5 mt-1');
        situacoes.slice(0, 6).forEach(s => {
          const item = el('li', '', s.grupo);
          if ((s.referencias || []).length) { item.append(': '); ligacoes(item, s.referencias); }
          lista.append(item);
        });
        const resto = situacoes.length - 6;
        cartao.append(lista, el('p', 'text-[13px] text-ink/60 mt-1',
          (resto === 1 ? 'E mais 1 situação. ' : resto > 1 ? `E outras ${resto} situações. ` : '') + 'Nenhuma foi informada para este paciente.'));
      }
      return cartao;
    }));
  }

  function baixar() {
    if (!dados) return;
    const campo = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const linhas = [['exame', 'nome_no_pedido', 'data', 'arquivo', 'conferencia', 'justificativa', 'no_checkup', 'grau', 'referencias', 'no_checkup_indicado_para']]
      .concat(dados.linhas.map(l => [l.exame, l.nome_no_pedido, l.data, l.arquivo, (VEREDITOS[l.veredito] || {}).rotulo || l.veredito,
        [l.motivo, l.aviso].filter(Boolean).join(' '), l.no_checkup, l.grau, (l.referencias || []).map(r => `${r.label} ${r.url || ''}`.trim()).join(' | '),
        ((l.indicado_para || {}).situacoes || []).map(s => `${s.grupo} (${(s.referencias || []).map(r => r.label).join(', ')})`).join('; ')]));
    const link = el('a');
    link.href = URL.createObjectURL(new Blob(['﻿' + linhas.map(l => l.map(campo).join(';')).join('\n')], { type: 'text/csv;charset=utf-8' }));
    link.download = 'conferencia_do_pedido.csv';
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function desatualizar() {
    if (dados) $('[data-desatualizado]').style.display = '';
  }

  document.addEventListener('DOMContentLoaded', () => {
    $('[data-baixar]').addEventListener('click', baixar);
    $('[data-pedido-pdf]').addEventListener('change', desatualizar);
    document.querySelectorAll('[data-filtro]').forEach(b => b.addEventListener('click', () => { filtro = b.dataset.filtro; if (dados) lista(); }));
    // Mensagens do formulário (mesma origem): altura que ele ocupa, andamento e resultado da conferência.
    window.addEventListener('message', e => {
      if (e.origin !== window.location.origin || !e.data) return;
      const quadro = $('[data-formulario]');
      if (e.source !== quadro.contentWindow) return;
      if (e.data.tipo === 'operadoras_altura' && e.data.altura > 0) quadro.style.height = (e.data.altura + 24) + 'px';
      if (e.data.tipo === 'operadoras_alterado') desatualizar();
      if (e.data.tipo === 'operadoras_enviando') $('[data-andamento]').style.display = '';
      if (e.data.tipo === 'operadoras_erro' || e.data.tipo === 'operadoras_descartado') $('[data-andamento]').style.display = 'none';
      if (e.data.tipo === 'operadoras_resultado' && e.data.corpo) {
        dados = e.data.corpo; filtro = '';
        $('[data-andamento]').style.display = 'none';
        $('[data-desatualizado]').style.display = 'none';
        $('[data-resultado]').style.display = '';
        resumo(); lista();
        $('[data-resultado]').scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
})();
