/* Idiomas do Evidēns (português e inglês).
 *
 * As páginas são escritas em português. Em inglês, cada texto visível é trocado pelo par que está em
 * /static/i18n/en.json ("textos": frase exata; "padroes": frases com partes variáveis). O mesmo arquivo
 * é lido pelo servidor (src/utils/i18n.py) para as respostas do check-up e os PDFs.
 *
 * - A escolha fica no navegador (localStorage e cookie "evidens_idioma") e vale para todas as páginas.
 * - ?lang=en ou ?lang=pt no endereço força o idioma (bom para compartilhar um link).
 * - Um elemento com data-i18n-manter nunca é traduzido (nomes próprios, dados digitados).
 * - Um elemento com data-idioma recebe o seletor (globo + BR/PT ou US/EN).
 */
(function () {
  'use strict';

  var CHAVE = 'evidens_idioma';
  var IDIOMAS = {
    pt: { sigla: 'BR/PT', nome: 'Português', lang: 'pt-BR' },
    en: { sigla: 'US/EN', nome: 'English', lang: 'en' }
  };
  var ATRIBUTOS = ['placeholder', 'title', 'aria-label', 'alt'];
  var NAO_ENTRAR = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, TEMPLATE: 1 };

  function guardar(idioma) {
    try { localStorage.setItem(CHAVE, idioma); } catch (e) { /* navegação privada */ }
    document.cookie = CHAVE + '=' + idioma + '; path=/; max-age=31536000; samesite=lax';
  }

  function escolhido() {
    var daUrl = null;
    try { daUrl = new URLSearchParams(location.search).get('lang'); } catch (e) { /* sem URLSearchParams */ }
    if (daUrl && IDIOMAS[daUrl]) { guardar(daUrl); return daUrl; }
    var salvo = null;
    try { salvo = localStorage.getItem(CHAVE); } catch (e) { /* navegação privada */ }
    if (!salvo) {
      var m = document.cookie.match(new RegExp('(?:^|; )' + CHAVE + '=(\\w+)'));
      salvo = m ? m[1] : null;
    }
    return IDIOMAS[salvo] ? salvo : 'pt';
  }

  var idioma = escolhido();
  guardar(idioma);
  document.documentElement.lang = IDIOMAS[idioma].lang;

  // ---------------------------------------------------------------- tradução
  var textos = null, padroes = [], manter = {};
  var faltando = {};

  function normalizar(t) { return String(t || '').replace(/\s+/g, ' ').trim(); }
  function temLetras(t) { return /[A-Za-zÀ-ÿ]{2,}/.test(t); }
  // siglas, números e pontuação não mudam de um idioma para o outro
  function neutro(t) { return /^[A-Z0-9][A-Z0-9 .\/()+,:;&%–—-]*$/.test(t); }

  function traduzir(original) {
    var n = normalizar(original);
    if (!n || !textos || !temLetras(n)) return null;
    if (Object.prototype.hasOwnProperty.call(textos, n)) return textos[n];
    if (manter[n] || neutro(n)) return null;
    for (var i = 0; i < padroes.length; i++) {
      if (padroes[i][0].test(n)) {
        return n.replace(padroes[i][0], function () {
          var grupos = arguments, saida = padroes[i][1];
          // cada parte variável também passa pelo dicionário (um nome de exame dentro de uma frase)
          return saida.replace(/\$(\d)/g, function (_, k) {
            var parte = grupos[+k] === undefined ? '' : grupos[+k];
            var t = Object.prototype.hasOwnProperty.call(textos, normalizar(parte)) ? textos[normalizar(parte)] : null;
            return t === null ? parte : t;
          });
        });
      }
    }
    faltando[n] = 1;
    return null;
  }

  function dentroDeManter(no) {
    for (var e = no.nodeType === 1 ? no : no.parentNode; e && e.nodeType === 1; e = e.parentNode) {
      if (NAO_ENTRAR[e.tagName] || e.hasAttribute('data-i18n-manter')) return true;
    }
    return false;
  }

  function traduzirTexto(no) {
    var valor = no.nodeValue;
    var t = traduzir(valor);
    if (t === null || t === normalizar(valor)) return;
    var antes = valor.match(/^\s*/)[0], depois = valor.match(/\s*$/)[0];
    no.nodeValue = antes + t + depois;
  }

  function traduzirAtributos(el) {
    for (var i = 0; i < ATRIBUTOS.length; i++) {
      var v = el.getAttribute(ATRIBUTOS[i]);
      if (v) { var t = traduzir(v); if (t !== null && t !== v) el.setAttribute(ATRIBUTOS[i], t); }
    }
    if (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button') && el.value) {
      var tv = traduzir(el.value); if (tv !== null) el.value = tv;
    }
  }

  function traduzirArvore(raiz) {
    if (!raiz) return;
    if (raiz.nodeType === 3) { if (!dentroDeManter(raiz)) traduzirTexto(raiz); return; }
    if (raiz.nodeType !== 1 || dentroDeManter(raiz)) return;
    traduzirAtributos(raiz);
    var andador = document.createTreeWalker(raiz, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function (no) {
        if (no.nodeType === 1 && (NAO_ENTRAR[no.tagName] || no.hasAttribute('data-i18n-manter'))) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var no;
    while ((no = andador.nextNode())) {
      if (no.nodeType === 3) traduzirTexto(no); else traduzirAtributos(no);
    }
  }

  function traduzirPagina() {
    var t = traduzir(document.title); if (t !== null) document.title = t;
    var meta = document.querySelector('meta[name="description"]');
    if (meta && meta.content) { var m = traduzir(meta.content); if (m !== null) meta.content = m; }
    traduzirArvore(document.body);
    // o que a página escrever depois (resultados do check-up, avisos) também é traduzido
    new MutationObserver(function (mudancas) {
      for (var i = 0; i < mudancas.length; i++) {
        var mu = mudancas[i];
        if (mu.type === 'characterData') { if (!dentroDeManter(mu.target)) traduzirTexto(mu.target); }
        else if (mu.type === 'attributes') { if (!dentroDeManter(mu.target)) traduzirAtributos(mu.target); }
        else for (var j = 0; j < mu.addedNodes.length; j++) traduzirArvore(mu.addedNodes[j]);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATRIBUTOS });
  }

  var pronto = function () { document.documentElement.classList.remove('i18n-carregando'); };

  if (idioma !== 'pt') {
    // esconde a página até a tradução entrar, para o português não piscar na tela
    document.documentElement.classList.add('i18n-carregando');
    var esconder = document.createElement('style');
    esconder.textContent = 'html.i18n-carregando body{visibility:hidden}';
    document.head.appendChild(esconder);
    setTimeout(pronto, 3000);  // se o dicionário demorar, mostra a página assim mesmo

    var dicionario = fetch('/static/i18n/' + idioma + '.json', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    var dom = new Promise(function (resolver) {
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', resolver); else resolver();
    });
    Promise.all([dicionario, dom]).then(function (r) {
      var d = r[0];
      if (d) {
        textos = d.textos || {};
        padroes = (d.padroes || []).map(function (p) { return [new RegExp(p[0]), p[1]]; });
        (d.manter || []).forEach(function (t) { manter[t] = 1; });
        traduzirPagina();
      }
      pronto();
    });
  }

  // ---------------------------------------------------------------- seletor
  var GLOBO = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.8 4 5.8 4 9s-1.4 6.2-4 9c-2.6-2.8-4-5.8-4-9s1.4-6.2 4-9z"/></svg>';
  var SETA = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  var ESTILO = [
    '.idioma{position:relative;display:inline-flex;font-family:inherit}',
    '.idioma-botao{display:inline-flex;align-items:center;gap:6px;height:40px;padding:0 10px;border:1px solid rgba(20,41,47,.15);border-radius:3px;background:#fff;color:rgba(20,41,47,.75);font:inherit;font-size:13px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;transition:color .15s,border-color .15s}',
    '.idioma-botao:hover,.idioma-botao[aria-expanded="true"]{color:#0E97B5;border-color:#0E97B5}',
    '.idioma-botao svg:first-child{color:#0E97B5}',
    '.idioma-menu{position:absolute;top:calc(100% + 6px);right:0;z-index:60;min-width:190px;margin:0;padding:6px;list-style:none;background:#fff;border:1px solid rgba(20,41,47,.1);border-radius:12px;box-shadow:0 14px 40px -12px rgba(20,41,47,.35)}',
    '.idioma-menu[hidden]{display:none}',
    '.idioma-opcao{display:flex;align-items:baseline;gap:10px;width:100%;padding:9px 10px;border:0;border-radius:8px;background:none;color:#14292F;font:inherit;font-size:14px;text-align:left;cursor:pointer}',
    '.idioma-opcao:hover{background:#DCEBEE}',
    '.idioma-opcao b{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;font-weight:500;letter-spacing:.14em;color:rgba(20,41,47,.55)}',
    '.idioma-opcao[aria-checked="true"]{color:#0E97B5}.idioma-opcao[aria-checked="true"] b{color:#0E97B5}',
    '.idioma-opcao[aria-checked="true"]::after{content:"";margin-left:auto;width:6px;height:6px;border-radius:50%;background:#0E97B5;align-self:center}'
  ].join('');

  function trocar(novo) {
    if (novo === idioma) return;
    guardar(novo);
    var url = new URL(location.href);
    url.searchParams.delete('lang');
    var destino = url.toString();
    if (destino === location.href) location.reload(); else location.replace(destino);
  }

  function montarSeletor(alvo) {
    var caixa = document.createElement('div');
    caixa.className = 'idioma';
    caixa.setAttribute('data-i18n-manter', '');
    var botao = document.createElement('button');
    botao.type = 'button'; botao.className = 'idioma-botao';
    botao.setAttribute('aria-haspopup', 'true'); botao.setAttribute('aria-expanded', 'false');
    botao.setAttribute('aria-label', idioma === 'en' ? 'Language: English. Change language' : 'Idioma: português. Trocar idioma');
    botao.innerHTML = GLOBO + '<span></span>' + SETA;
    botao.querySelector('span').textContent = IDIOMAS[idioma].sigla;
    var menu = document.createElement('div');
    menu.className = 'idioma-menu'; menu.setAttribute('role', 'menu'); menu.hidden = true;
    Object.keys(IDIOMAS).forEach(function (codigo) {
      var op = document.createElement('button');
      op.type = 'button'; op.className = 'idioma-opcao';
      op.setAttribute('role', 'menuitemradio'); op.setAttribute('aria-checked', String(codigo === idioma));
      op.setAttribute('lang', IDIOMAS[codigo].lang);
      var sigla = document.createElement('b'); sigla.textContent = IDIOMAS[codigo].sigla;
      var nome = document.createElement('span'); nome.textContent = IDIOMAS[codigo].nome;
      op.appendChild(sigla); op.appendChild(nome);
      op.addEventListener('click', function () { trocar(codigo); });
      menu.appendChild(op);
    });
    function fechar() { menu.hidden = true; botao.setAttribute('aria-expanded', 'false'); }
    botao.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var abrir = menu.hidden;
      menu.hidden = !abrir; botao.setAttribute('aria-expanded', String(abrir));
      if (abrir) menu.querySelector('[aria-checked="true"]').focus();
    });
    document.addEventListener('click', function (ev) { if (!caixa.contains(ev.target)) fechar(); });
    caixa.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { fechar(); botao.focus(); } });
    caixa.appendChild(botao); caixa.appendChild(menu);
    alvo.appendChild(caixa);
  }

  function seletores() {
    var alvos = document.querySelectorAll('[data-idioma]');
    if (!alvos.length) return;
    var estilo = document.createElement('style'); estilo.textContent = ESTILO; document.head.appendChild(estilo);
    for (var i = 0; i < alvos.length; i++) montarSeletor(alvos[i]);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', seletores); else seletores();

  // para as páginas e para a conferência: idioma atual, tradução avulsa e textos sem par
  window.evidensIdioma = {
    atual: idioma,
    traduzir: function (t) { var r = traduzir(t); return r === null ? t : r; },
    faltando: function () { return Object.keys(faltando); },
    trocar: trocar
  };
})();
