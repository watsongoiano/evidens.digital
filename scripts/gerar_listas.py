"""Regera, em intelligent-tools.html, as listas com busca (comorbidades, medicações, família).

As opções saem de src/utils/condicoes.py e src/utils/medicamentos.py; o HTML entre os
marcadores ``<!-- lista:NOME:inicio -->`` e ``<!-- lista:NOME:fim -->`` é substituído.
Uso: python scripts/gerar_listas.py   (tests/test_site.py confere se está em dia)
"""
import html
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import json  # noqa: E402

from src.utils import condicoes, doses, medicamentos  # noqa: E402

PAGINA = RAIZ / 'intelligent-tools.html'
# O que a tela marca quando o item é escolhido (as caixas de classe saíram da tela).
MARCA_NA_TELA = {'estatinas': 'dislipidemia', 'anti_hipertensivos': 'hipertensao'}


def _marcas(classes):
    alvos = []
    for c in classes:
        for m in condicoes.MEDICACOES.get(c, {}).get('marca', []):
            m = MARCA_NA_TELA.get(m, m)
            if m not in alvos:
                alvos.append(m)
    return alvos


def _imuno(classes):
    return any(condicoes.MEDICACOES.get(c, {}).get('imunossupressao') for c in classes)


def _talvez(classes):
    """Caixas que o item não marca sozinho (outras indicações), descontadas as que ele já marca."""
    ja = _marcas(classes)
    alvos = []
    for c in classes:
        for m in condicoes.MEDICACOES.get(c, {}).get('talvez', []):
            if m not in ja and m not in alvos:
                alvos.append(m)
    return alvos


def _atributos(marca=(), imuno=False, chave=None, talvez=()):
    detalhe = ''
    if chave in doses.POR_MEDICAMENTO:
        tipo, parametro = doses.POR_MEDICAMENTO[chave]
        detalhe = f' data-detalhe="{tipo}"' + (f' data-parametro="{round(parametro, 4):g}"' if parametro else '')
    return ((f' data-marca="{" ".join(marca)}"' if marca else '') + (f' data-talvez="{" ".join(talvez)}"' if talvez else '')
            + (' data-imuno="1"' if imuno else '') + detalhe)


def _opcao(valor, rotulo, busca, extra='', alvo=None):
    alvo = f' data-alvo="{alvo}"' if alvo else ''
    return (f'            <li role="option" data-valor="{valor}" data-busca="{html.escape(busca)}"{alvo}{extra}>'
            f'{html.escape(rotulo)}</li>')


def _combo(ident, campo, rotulo, exemplo, dica, linhas):
    return f'''      <div class="campo mt-5 combo" id="{ident}" data-campo="{campo}">
        <label for="{ident}-busca">{rotulo}</label>
        <div class="relative">
          <input type="text" id="{ident}-busca" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="{ident}-opcoes" aria-describedby="{ident}-dica" autocomplete="off" placeholder="Digite para buscar: {exemplo}">
          <ul id="{ident}-opcoes" role="listbox" class="combo-lista" hidden>
{chr(10).join(linhas)}
            <li class="combo-vazio" role="presentation" hidden>Nada encontrado.</li>
          </ul>
        </div>
        <div class="opcoes mt-3" id="{ident}-itens"></div>
        <p id="{ident}-dica" class="text-[12px] text-ink/50 mt-2">{dica}</p>
      </div>
'''


def blocos(pagina):
    def simples(itens):
        """O que já é botão na tela não entra na lista (sem duplicata); itens com 'grupo' vêm agrupados."""
        linhas, grupo = [], object()
        for chave, item in itens.items():
            if item.get('grupo') != grupo:
                grupo = item.get('grupo')
                linhas.append(f'            <li class="combo-grupo" role="presentation">{html.escape(grupo or "Outras condições")}</li>'
                              if any(i.get('grupo') for i in itens.values()) else None)
            busca = medicamentos.sem_acento(f"{item['rotulo']} {item.get('busca', '')} {item.get('grupo') or ''}")
            linhas.append(_opcao(chave, item['rotulo'], busca, _atributos(imuno=item.get('imunossupressao'))))
        return [li for li in linhas if li]

    chips = []
    for chave in medicamentos.MAIS_USADOS:
        m = medicamentos.MEDICAMENTOS[chave]
        rotulo = m['rotulo'].split(' (')[0]
        chips.append(f'        <label class="opcao" for="lista_medicacoes_{chave}"><input type="checkbox" id="lista_medicacoes_{chave}" '
                     f'name="medicacoes" value="{chave}" data-rotulo="{html.escape(rotulo)}"'
                     f'{_atributos(_marcas(m["classes"]), _imuno(m["classes"]), chave, _talvez(m["classes"]))}>{html.escape(rotulo)}</label>')
    linhas, grupo = [], None
    for chave, m in medicamentos.MEDICAMENTOS.items():
        if chave in medicamentos.MAIS_USADOS:
            continue  # já é botão
        if m['grupo'] != grupo:
            grupo = m['grupo']
            linhas.append(f'            <li class="combo-grupo" role="presentation">{html.escape(grupo)}</li>')
        linhas.append(_opcao(chave, m['rotulo'], m['busca'],
                             _atributos(_marcas(m['classes']), _imuno(m['classes']), chave, _talvez(m['classes']))))

    return {
        'comorbidades': _combo('lista_comorbidades', 'comorbidades', 'Outras comorbidades', 'hipotireoidismo, asma, gota…',
                               'Digite o nome ou escolha na lista. Os itens com exame, vacina ou alerta próprios entram nas recomendações.',
                               simples(condicoes.COMORBIDADES)),
        'medicacoes': '      <div class="opcoes mt-4">\n' + '\n'.join(chips) + '\n      </div>\n'
                      + _combo('lista_medicacoes', 'medicacoes', 'Outras medicações', 'anlodipino, rosuvastatina, bombinha…',
                               'Busca por princípio ativo ou classe. A medicação define monitorização laboratorial, vacinas e '
                               'coerência com as comorbidades.', linhas)
                      + '      <div id="medicacoes-detalhes" class="bloco-condicional" hidden>\n'
                        '        <p class="campo-rotulo">Dose e duração</p>\n'
                        '        <div id="medicacoes-detalhes-linhas" class="flex flex-col gap-4"></div>\n'
                        '      </div>\n'
                      + f'      <script type="application/json" id="detalhes-medicacao">{json.dumps(doses.DETALHES, ensure_ascii=False)}</script>\n',
        'familia': _combo('lista_familia', 'historia_familiar', 'Outras condições em parente de 1º grau',
                          'BRCA, Lynch, hipercolesterolemia familiar…', 'Síndromes hereditárias trazem o rastreamento específico; as demais mudam idade de início ou indicação.',
                          simples(condicoes.FAMILIA)),
    }


def aplicar(pagina):
    for nome, bloco in blocos(pagina).items():
        ini, fim = f'<!-- lista:{nome}:inicio -->\n', f'      <!-- lista:{nome}:fim -->\n'
        a, b = pagina.index(ini) + len(ini), pagina.index(fim)
        pagina = pagina[:a] + bloco + pagina[b:]
    return pagina


if __name__ == '__main__':
    PAGINA.write_text(aplicar(PAGINA.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'{len(medicamentos.MEDICAMENTOS)} medicamentos, {len(condicoes.COMORBIDADES)} comorbidades, {len(condicoes.FAMILIA)} condições familiares')
