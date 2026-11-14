"""Lista os textos visíveis das páginas (e os do motor) que ainda não têm tradução.

Uso:  python scripts/extrair_textos.py            # resumo por página
      python scripts/extrair_textos.py --faltando # um texto por linha, só os que faltam

A versão em inglês não duplica as páginas: static/i18n.js troca cada texto pelo par que está em
static/i18n/en.json. Este script (e tests/test_i18n.py) garante que nenhum texto fique de fora.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAGINAS = ['index.html', 'intelligent-tools.html', 'login.html', 'cadastro.html', 'conta.html',
           'configurar.html', 'contact.html']
ATRIBUTOS = ('placeholder', 'title', 'aria-label', 'alt')
IGNORAR_DENTRO = {'script', 'style', 'noscript', 'template'}


def normalizar(texto):
    return ' '.join((texto or '').split())


def tem_letras(texto):
    return bool(re.search(r'[A-Za-zÀ-ÿ]{2,}', texto))


class Coletor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textos, self.pilha, self.manter = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        vazio = tag in ('br', 'img', 'input', 'meta', 'link', 'hr', 'source')
        if not vazio:
            self.pilha.append((tag, 'data-i18n-manter' in a))
            if 'data-i18n-manter' in a:
                self.manter += 1
        if self.manter or any(t in IGNORAR_DENTRO for t, _ in self.pilha):
            return
        for nome in ATRIBUTOS:
            if a.get(nome):
                self.textos.append(normalizar(a[nome]))
        if tag == 'meta' and a.get('name') == 'description' and a.get('content'):
            self.textos.append(normalizar(a['content']))
        if tag == 'input' and a.get('type') in ('submit', 'button') and a.get('value'):
            self.textos.append(normalizar(a['value']))

    def handle_endtag(self, tag):
        for i in range(len(self.pilha) - 1, -1, -1):
            if self.pilha[i][0] == tag:
                for _, m in self.pilha[i:]:
                    self.manter -= 1 if m else 0
                del self.pilha[i:]
                break

    def handle_data(self, data):
        if self.manter or any(t in IGNORAR_DENTRO for t, _ in self.pilha):
            return
        t = normalizar(data)
        if t:
            self.textos.append(t)


def textos_da_pagina(nome):
    c = Coletor()
    c.feed((RAIZ / nome).read_text(encoding='utf-8'))
    vistos, saida = set(), []
    for t in c.textos:
        if tem_letras(t) and t not in vistos:
            vistos.add(t)
            saida.append(t)
    return saida


def carregar_dicionario():
    caminho = RAIZ / 'static' / 'i18n' / 'en.json'
    if not caminho.exists():
        return {'textos': {}, 'padroes': [], 'manter': []}
    return json.loads(caminho.read_text(encoding='utf-8'))


def main():
    sys.path.insert(0, str(RAIZ))
    try:
        from src.utils import i18n
        coberto = i18n.coberto
    except Exception:
        d = carregar_dicionario()
        coberto = lambda t: t in d['textos'] or t in d.get('manter', [])
    so_faltando = '--faltando' in sys.argv
    total = falta = 0
    for pagina in PAGINAS:
        textos = textos_da_pagina(pagina)
        faltando = [t for t in textos if not coberto(t)]
        total += len(textos); falta += len(faltando)
        if so_faltando:
            for t in faltando:
                print(t)
        else:
            print(f'{pagina:26s} {len(textos):5d} textos, {len(faltando):5d} sem tradução')
    if not so_faltando:
        print(f'{"total":26s} {total:5d} textos, {falta:5d} sem tradução')


if __name__ == '__main__':
    main()
