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


def neutro(texto):
    """Siglas curtas, códigos e números não mudam de um idioma para o outro ("HIV", "KDIGO 2024", "GO").
    Palavra inteira em maiúsculas ("IDADE") não entra aqui: precisa de par no dicionário."""
    return bool(_NEUTRO.match(texto)) and (any(c.isdigit() for c in texto) or all(len(p) <= 4 for p in re.findall(r'[A-Z]+', texto)))


def normalizar(texto):
    return ' '.join(str(texto or '').split())


@lru_cache(maxsize=None)
def dicionario(idioma='en'):
    caminho = RAIZ / 'static' / 'i18n' / f'{idioma}.json'
    bruto = json.loads(caminho.read_text(encoding='utf-8')) if caminho.is_file() else {}
    padroes = [(re.compile(expressao), saida) for expressao, saida in bruto.get('padroes', [])]
    return {'textos': bruto.get('textos', {}), 'padroes': padroes, 'manter': set(bruto.get('manter', []))}


def idioma_do_pedido(pedido):
    """'en' ou 'pt', pelo endereço (?lang=) ou pelo cookie gravado pelo seletor."""
    escolha = (pedido.args.get('lang') or pedido.cookies.get(COOKIE) or 'pt').lower()
    return escolha if escolha in IDIOMAS else 'pt'


_NUMERO = re.compile(r'^[<>≥≤~≈±]?\s*-?\d[\d.,]*\s*%?$')
_SEPARADORES = ('; ', ', ', ' + ')


def numero(texto):
    """Número no formato inglês: "16,7" -> "16.7", "7.000" -> "7,000". Só mexe em texto que é só número."""
    if not _NUMERO.match(texto.strip()):
        return texto
    t = re.sub(r'\.(?=\d{3}(?:\D|$))', '§', texto)
    return t.replace(',', '.').replace('§', ',')


def _traduzir(texto, d):
    """Devolve ``(traduzido, coberto)``. ``coberto`` é False quando há letras e nenhum par no dicionário."""
    n = normalizar(texto)
    if not n:
        return texto, True
    if n in d['textos']:
        return d['textos'][n], True
    if not _LETRAS.search(n):
        return numero(texto), True
    if n in d['manter'] or neutro(n):
        return texto, True
    parcial = None
    for expressao, saida in d['padroes']:
        m = expressao.match(n)
        if m:
            # $1: a parte passa de novo pelo tradutor (um nome de exame dentro de uma frase, outra frase
            # composta, uma lista); a frase só conta como coberta se todas as partes estiverem.
            # %1: a parte entra como está (número, nome próprio), só com o número no formato do idioma.
            tudo = True

            def trocar(k):
                nonlocal tudo
                g = m.group(int(k.group(2))) or ''
                if k.group(1) == '%':
                    return numero(g)
                parte, ok = _parte(g, d)
                tudo = tudo and ok
                return parte
            resultado = re.sub(r'([$%])(\d)', trocar, saida)
            if tudo:
                return resultado, True
            parcial = parcial or resultado  # casou, mas sobrou parte sem par: outro padrão pode servir melhor
    # frases emendadas: o motor junta as descrições quando o mesmo exame tem dois motivos, e as mensagens
    # de erro quando há mais de um campo errado. O corte é depois de um texto conhecido ou no fim de uma frase.
    for i, c in enumerate(n):
        if c != ' ':
            continue
        if n[:i] in d['textos']:
            inicio = d['textos'][n[:i]]
        elif n[i - 1] == '.':
            inicio, ok = _traduzir(n[:i], d)
            if not ok:
                continue
        else:
            continue
        resto, ok = _traduzir(n[i + 1:], d)
        if ok:
            return inicio + ' ' + resto, True
    return (parcial or texto), False


def _parte(g, d):
    parte, ok = _traduzir(g, d)
    if ok:
        return parte, True
    for sep in _SEPARADORES:  # lista dentro da frase: "colesterol total, HDL, peso"
        if sep in g:
            pedacos = [_traduzir(x, d) for x in g.split(sep)]
            if all(c for _, c in pedacos):
                return sep.join(t for t, _ in pedacos), True
    return parte, False


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
