"""Regera, em intelligent-tools.html, as "Condições clínicas" da aba Pré-operatório e as sugestões automáticas.

As chaves saem de src/utils/preoperatorio.py (CONDICOES, INSTAVEIS, SINTOMAS, ASA_MINIMA e sugestoes_da_tela); a
arrumação em grupos e sub-itens fica aqui. O HTML entre ``<!-- preop:condicoes:inicio -->`` e
``<!-- preop:condicoes:fim -->`` e a linha entre ``// preop:sugestoes:inicio`` e ``// preop:sugestoes:fim`` são
substituídos.
Uso: python scripts/gerar_preop.py   (tests/test_preoperatorio.py confere se está em dia)
"""
import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.utils import preoperatorio as po  # noqa: E402

PAGINA = RAIZ / 'intelligent-tools.html'

# Tipo do item: 'c' condição, 'i' grave ou instável, 's' sintoma. Cada item é (tipo, chave, rótulo, sub-itens); o
# sub-item só aparece com o item de cima marcado, e é ali que ficam o detalhe que muda a conduta e o quadro grave
# daquela doença (em vez de um segundo item solto para a mesma doença).
NOME = {'c': 'po_condicoes', 'i': 'po_instaveis', 's': 'po_sintomas'}
GRUPOS = [
    ('instaveis', 'Grave ou instável agora',
     'IC descompensada, estenose importante sintomática, FA rápida, hipertensão pulmonar sintomática e angina '
     'CCS III/IV abrem dentro do item da doença.', [
         ('i', 'sca', 'Síndrome coronariana aguda', []),
         ('i', 'arritmia_grave', 'Bradi ou taquiarritmia grave (BAVT, TV)', []),
         ('i', 'aorta_instavel', 'Doença instável da aorta torácica', []),
         ('i', 'edema_choque', 'Edema agudo de pulmão ou choque cardiogênico', []),
     ]),
    ('cardiovascular', 'Cardiovascular', '', [
        ('c', 'dac', 'Doença coronária', [('c', 'iam_previo', 'IAM prévio')]),
        ('c', 'stent', 'Angioplastia ou stent', []),
        ('c', 'revascularizacao_cirurgica', 'Cirurgia de revascularização', []),
        ('c', 'ic', 'Insuficiência cardíaca', [
            ('c', 'ic_fe_reduzida', 'Fração de ejeção reduzida'),
            ('c', 'ic_recente', 'Recente, tratamento não otimizado'),
            ('i', 'ic_descompensada', 'Descompensada (NYHA III/IV)')]),
        ('c', 'fa', 'FA (fibrilação atrial)', [('i', 'fa_alta_resposta', 'FC > 120 bpm')]),
        ('c', 'valvopatia', 'Valvopatia moderada ou grave', [
            ('i', 'valvopatia_grave_sintomatica', 'Estenose aórtica ou mitral importante sintomática')]),
        ('c', 'protese_mecanica', 'Prótese valvar mecânica', [('c', 'protese_mecanica_mitral', 'Em posição mitral')]),
        ('c', 'marcapasso_cdi', 'Marca-passo ou CDI', []),
        ('c', 'hipertensao', 'Hipertensão', []),
        ('c', 'avc_ait', 'AVC ou AIT', [('c', 'avc_ait_recente', 'Há menos de 3 meses')]),
        ('c', 'doenca_arterial_periferica', 'Doença arterial periférica', []),
        ('c', 'hipertensao_pulmonar', 'Hipertensão pulmonar', [('i', 'hap_sintomatica', 'Sintomática')]),
        ('c', 'cardiopatia_congenita', 'Cardiopatia congênita de risco elevado', []),
    ]),
    ('outras', 'Outras doenças', '', [
        ('c', 'diabetes', 'Diabetes', [('c', 'diabetes_insulina', 'Em uso de insulina')]),
        ('c', 'dislipidemia', 'Dislipidemia', []),
        ('c', 'obesidade', 'Obesidade', []),
        ('c', 'dpoc', 'DPOC', []),
        ('c', 'tabagismo', 'Tabagismo atual', []),
        ('c', 'historia_familiar_dac', 'História familiar de doença coronária precoce', []),
        ('c', 'doenca_renal', 'Doença renal crônica', []),
        ('c', 'hepatopatia', 'Hepatopatia crônica', []),
        # O tempo desde o TEV define o risco tromboembólico; sem ele, o motor não classifica (não presume > 12 meses).
        ('c', 'tev', 'Trombose venosa ou TEP prévio', [
            ('c', 'tev_recente_3m', 'Há menos de 3 meses'), ('c', 'tev_3_12m', 'Entre 3 e 12 meses'),
            ('c', 'tev_mais_12m', 'Há mais de 12 meses')]),
        ('c', 'trombofilia_grave', 'Trombofilia grave ou antifosfolípide', []),
        ('c', 'cancer_ativo', 'Câncer ativo', []),
    ]),
    ('sintomas', 'Sintomas e sinais', '', [
        ('s', 'angina', 'Angina', [('i', 'angina_grave', 'CCS III/IV')]),
        ('s', 'dispneia', 'Dispneia aos esforços', [('s', 'dispneia_nova', 'Nova ou em piora')]),
        ('s', 'palpitacoes', 'Palpitações', []),
        ('s', 'sincope', 'Síncope', []),
        ('s', 'sopro', 'Sopro cardíaco', []),
        ('s', 'sinais_ic', 'Sinais de insuficiência cardíaca ao exame (estertores, B3, turgência jugular)', []),
    ]),
]

# Dentro do grupo, logo depois dos itens.
EXTRA = {
    'cardiovascular': '''        <div id="po_stent" class="bloco-condicional grade" hidden>
          <div class="campo">
            <label for="po_stent_tipo">Angioplastia: tipo</label>
            <select id="po_stent_tipo">
              <option value="">Selecione...</option>
              <option value="farmacologico">Stent farmacológico</option>
              <option value="convencional">Stent convencional</option>
              <option value="balao">Só balão</option>
            </select>
          </div>
          <div class="campo">
            <label for="po_stent_indicacao">Indicação</label>
            <select id="po_stent_indicacao">
              <option value="">Selecione...</option>
              <option value="dac_cronica">Doença coronária crônica</option>
              <option value="sca">Síndrome coronariana aguda</option>
            </select>
          </div>
          <div class="campo">
            <label for="po_stent_data">Data da angioplastia</label>
            <input type="date" id="po_stent_data">
          </div>
        </div>
''',
}
# Último item do grupo de sintomas: entra no ARISCAT, não é sintoma cardíaco (campo próprio do pedido).
ITEM_SOLTO = {
    'sintomas': '          <label class="opcao" for="po_infeccao"><input type="checkbox" id="po_infeccao" value="sim">'
                'Infecção respiratória no último mês</label>\n',
}


def _caixa(tipo, chave, rotulo, classe='opcao'):
    asa = po.ASA_MINIMA.get(chave)
    asa = f' data-asa="{asa}"' if asa else ''
    ident = f'po_{tipo}_{chave}'
    return (f'<label class="{classe}" for="{ident}"><input type="checkbox" id="{ident}" name="{NOME[tipo]}" '
            f'value="{chave}"{asa}>{html.escape(rotulo, quote=False)}</label>')


def _grupo(ident, titulo, nota, itens):
    linhas = []
    for tipo, chave, rotulo, filhos in itens:
        linhas.append('          ' + _caixa(tipo, chave, rotulo))
        if filhos:
            dentro = ''.join(_caixa(t, k, r, 'opcao po-filho po-grave' if t == 'i' else 'opcao po-filho')
                             for t, k, r in filhos)
            linhas.append(f'          <span class="po-detalhe-de" data-detalhe-de="po_{tipo}_{chave}" hidden>{dentro}</span>')
    nota = f'        <p class="po-nota-do-grupo">{html.escape(nota, quote=False)}</p>\n' if nota else ''
    return (f'      <details class="po-grupo" id="po_g_{ident}">\n'
            f'        <summary><span>{titulo}</span><span class="exames-comuns-conta" data-conta hidden></span>'
            '<i class="fa-solid fa-chevron-down exames-comuns-seta"></i></summary>\n'
            f'{nota}        <div class="opcoes">\n' + '\n'.join(linhas) + '\n' + ITEM_SOLTO.get(ident, '')
            + '        </div>\n' + EXTRA.get(ident, '') + '      </details>\n')


def chaves_da_tela():
    """{tipo: [chaves]} na ordem da tela, com os sub-itens."""
    saida = {'c': [], 'i': [], 's': []}
    for _, _, _, itens in GRUPOS:
        for tipo, chave, _, filhos in itens:
            saida[tipo].append(chave)
            for t, k, _ in filhos:
                saida[t].append(k)
    return saida


def condicoes_html():
    usadas = chaves_da_tela()
    for tipo, tabela in (('c', po.CONDICOES), ('i', po.INSTAVEIS), ('s', po.SINTOMAS)):
        assert sorted(usadas[tipo]) == sorted(tabela), f'tela e motor diferem em {NOME[tipo]}'
    return ''.join(_grupo(*g) for g in GRUPOS)


def sugestoes_js():
    return ('        const PO_SUGESTOES = '
            + json.dumps(po.sugestoes_da_tela(), ensure_ascii=False, separators=(',', ':')) + ';\n')


def aplicar(pagina):
    for ini, fim, bloco in (('<!-- preop:condicoes:inicio -->\n', '      <!-- preop:condicoes:fim -->\n', condicoes_html()),
                            ('// preop:sugestoes:inicio\n', '        // preop:sugestoes:fim\n', sugestoes_js())):
        a, b = pagina.index(ini) + len(ini), pagina.index(fim)
        pagina = pagina[:a] + bloco + pagina[b:]
    return pagina


if __name__ == '__main__':
    PAGINA.write_text(aplicar(PAGINA.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'{sum(len(v) for v in chaves_da_tela().values())} itens em {len(GRUPOS)} grupos')
