// Painel de uso (/analytics). Lê /api/analytics/stats (só administrador). Nenhum dado de paciente.
(function () {
  'use strict';
  const COLUNAS = ['checkup', 'pdf_laboratorio', 'pdf_imagem', 'pdf_vacinas', 'guia_plano', 'login'];
  const CARTOES = ['checkup', 'pdf_laboratorio', 'pdf_imagem', 'pdf_vacinas', 'guia_plano', 'acesso', 'login', 'visita'];
  const PERFIS = { medico: 'Médico', residente: 'Residente', estudante: 'Estudante' };
  let dados = null;
  let periodo = 'mes';

  const $ = sel => document.querySelector(sel);
  const numero = n => Number(n || 0).toLocaleString('pt-BR');
  function dataHora(iso) {
    const d = new Date(iso);
    return isNaN(d) ? '—' : d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' });
  }
  function el(tag, classe, texto) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  function cartoes() {
    const valores = dados.periodos[periodo];
    $('[data-cartoes]').replaceChildren(...CARTOES.map(tipo => {
      const c = el('div', 'recommendation-card');
      c.append(el('p', 'text-[12px] text-ink/55 leading-snug', dados.tipos[tipo]),
               el('p', 'text-[32px] font-light tracking-tightest leading-none mt-3', numero(valores[tipo])));
      return c;
    }));
    document.querySelectorAll('[data-periodo]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.periodo === periodo)));
  }

  function grafico() {
    const serie = dados.serie;
    const maximo = Math.max(1, ...serie.map(d => d.checkup));
    $('[data-grafico]').replaceChildren(...serie.map(d => {
      const barra = el('div', 'flex-1 rounded-t-[3px] ' + (d.checkup ? 'bg-teal' : 'bg-ink/10'));
      barra.style.height = Math.max(3, Math.round(d.checkup / maximo * 100)) + '%';
      barra.title = `${d.dia.split('-').reverse().join('/')}: ${d.checkup} check-up(s)`;
      return barra;
    }));
    const total = serie.reduce((s, d) => s + d.checkup, 0);
    $('[data-grafico]').setAttribute('aria-label', `${total} check-ups nos últimos 30 dias`);
    const br = d => d.split('-').reverse().slice(0, 2).join('/');
    $('[data-grafico-inicio]').textContent = br(serie[0].dia);
    $('[data-grafico-fim]').textContent = br(serie[serie.length - 1].dia);
  }

  function tabela() {
    const chave = periodo;   // cada linha traz hoje, sete_dias, mes e total
    const linhas = dados.usuarios;
    $('[data-contagem]').textContent = `(${linhas.length})`;
    if (!linhas.length) {
      const tr = el('tr'); const td = el('td', 'px-4 py-6 text-ink/50', 'Nenhum uso registrado ainda.'); td.colSpan = 8;
      tr.append(td); $('[data-usuarios]').replaceChildren(tr); return;
    }
    $('[data-usuarios]').replaceChildren(...linhas.map(u => {
      const tr = el('tr', 'border-b border-ink/5 last:border-0');
      const nome = el('td', 'px-4 py-3');
      nome.append(el('p', 'font-medium', u.nome), el('p', 'text-[12px] text-ink/50', [u.email, PERFIS[u.perfil] || ''].filter(Boolean).join(' · ')));
      tr.append(nome, ...COLUNAS.map(t => el('td', 'px-3 py-3 text-right tabular-nums' + (u[chave][t] ? '' : ' text-ink/30'), numero(u[chave][t]))),
                el('td', 'px-4 py-3 text-ink/65 whitespace-nowrap', dataHora(u.ultima_atividade)));
      return tr;
    }));
  }

  async function carregar() {
    const erro = $('[data-erro]');
    try {
      const r = await fetch('/api/analytics/stats', { credentials: 'same-origin' });
      if (!r.ok) throw new Error(r.status);
      dados = await r.json();
      erro.style.display = 'none';
      cartoes(); grafico(); tabela();
      $('[data-atualizado]').textContent = 'Atualizado em ' + dataHora(dados.gerado_em) + '.';
    } catch (e) {
      erro.textContent = 'Não foi possível carregar os números. Tente de novo.';
      erro.style.display = 'block';
    }
  }

  document.querySelectorAll('[data-periodo]').forEach(b => b.addEventListener('click', () => {
    periodo = b.dataset.periodo;
    if (dados) { cartoes(); tabela(); }
  }));
  $('[data-atualizar]').addEventListener('click', carregar);
  carregar();
}());
