"""Idiomas no servidor: o mesmo dicionário que static/i18n.js usa no navegador.

static/i18n/en.json tem três partes:
- ``textos``: frase em português -> frase em inglês (comparação exata, espaços normalizados);
- ``padroes``: pares [expressão regular, substituição com $1, $2...] para frases com partes variáveis;
- ``manter``: textos que ficam iguais nos dois idiomas (nomes próprios, marcas, siglas com minúsculas).

O servidor usa o dicionário para traduzir as respostas da API e os PDFs quando o pedido chega
com o idioma inglês (cookie ``evidens_idioma`` ou ``?lang=en``).
"""
import json
import re
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
IDIOMAS = ('pt', 'en')
COOKIE = 'evidens_idioma'
_NEUTRO = re.compile(r'^[A-Z0-9][A-Z0-9 ./()+,:;&%–—-]*$')
_LETRAS = re.compile(r'[A-Za-zÀ-ÿ]{2,}')


def normalizar(texto):
    return ' '.join(str(texto or '').split())


@lru_cache(maxsize=None)
def dicionario(idioma='en'):
    caminho = RAIZ / 'static' / 'i18n' / f'{idioma}.json'
    bruto = json.loads(caminho.read_text(encoding='utf-8')) if caminho.is_file() else {}
    padroes = [(re.compile(expressao), re.sub(r'\$(\d)', r'\\g<\1>', saida)) for expressao, saida in bruto.get('padroes', [])]
    return {'textos': bruto.get('textos', {}), 'padroes': padroes, 'manter': set(bruto.get('manter', []))}


def idioma_do_pedido(pedido):
    """'en' ou 'pt', pelo endereço (?lang=) ou pelo cookie gravado pelo seletor."""
    escolha = (pedido.args.get('lang') or pedido.cookies.get(COOKIE) or 'pt').lower()
    return escolha if escolha in IDIOMAS else 'pt'


def _traduzir(texto, d):
    """Devolve ``(traduzido, coberto)``. ``coberto`` é False quando há letras e nenhum par no dicionário."""
    n = normalizar(texto)
    if not n:
        return texto, True
    if n in d['textos']:
        return d['textos'][n], True
    if not _LETRAS.search(n) or n in d['manter'] or _NEUTRO.match(n):
        return texto, True
    for expressao, saida in d['padroes']:
        m = expressao.match(n)
        if m:
            # cada parte variável também passa pelo dicionário (um nome de exame dentro de uma frase)
            partes = {str(i): d['textos'].get(normalizar(g), g) if g is not None else '' for i, g in enumerate(m.groups(), 1)}
            return re.sub(r'\\g<(\d)>', lambda k: partes.get(k.group(1), ''), saida), True
    return texto, False


def traduzir(texto, idioma='en'):
    if idioma == 'pt' or not isinstance(texto, str):
        return texto
    return _traduzir(texto, dicionario(idioma))[0]


def coberto(texto, idioma='en'):
    """O texto tem tradução (ou não precisa de uma)?"""
    return _traduzir(texto, dicionario(idioma))[1]


def traduzir_estrutura(valor, idioma='en', fora=()):
    """Traduz as frases de uma resposta da API (dicionários e listas aninhados). ``fora``: chaves que
    carregam dado digitado pela pessoa ou identificador, e não devem ser tocadas."""
    if idioma == 'pt':
        return valor
    if isinstance(valor, str):
        return traduzir(valor, idioma)
    if isinstance(valor, list):
        return [traduzir_estrutura(v, idioma, fora) for v in valor]
    if isinstance(valor, dict):
        return {k: (v if k in fora else traduzir_estrutura(v, idioma, fora)) for k, v in valor.items()}
    return valor
