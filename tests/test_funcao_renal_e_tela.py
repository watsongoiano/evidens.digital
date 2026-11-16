"""Função renal (CKD-EPI 2021, KDIGO 2024, KFRE), coerência de idade e tabagismo, texto das orientações e guia TISS."""
import math
import re
from pathlib import Path

import pytest

from src.utils import funcao_renal

RAIZ = Path(__file__).resolve().parents[1]
BASE = dict(sexo='masculino', tabagismo='nunca', comorbidades=[], medicacoes=[], historia_familiar=[],
            imunossupressao='nao', gestante='nao', lactante='nao')


def _post(client, **dados):
    return client.post('/api/checkup-intelligent', json=dict(BASE, **dados))


# --- KFRE e categorias ------------------------------------------------------------------------

def test_kfre_no_paciente_medio_da_coorte_e_a_sobrevida_basal():
    """Com as variáveis na média da coorte (e o termo de sexo zerado), o risco é 1 - S0 (Tangri 2016)."""
    c = funcao_renal._KFRE_COEF
    # termo de sexo: (1 - 0,5642) * 0,2467 para homem; o restante zerado pela centragem
    r = funcao_renal.kfre(c['idade_media'] * 10, 'feminino', c['tfg_media'] * 5, math.exp(c['ln_uacr_medio']))
    ajuste = math.exp(c['masculino'] * -c['masculino_medio'])
    assert r[2] == pytest.approx(1 - 0.9832 ** ajuste, abs=1e-9)
    assert r[5] == pytest.approx(1 - 0.9365 ** ajuste, abs=1e-9)


def test_kfre_sobe_com_albuminuria_e_cai_com_a_tfg():
    baixo = funcao_renal.kfre(65, 'masculino', 50, 30)[5]
    assert funcao_renal.kfre(65, 'masculino', 50, 300)[5] > baixo
    assert funcao_renal.kfre(65, 'masculino', 25, 30)[5] > baixo


@pytest.mark.parametrize('tfg, g', [(95, 'G1'), (60, 'G2'), (59, 'G3a'), (44, 'G3b'), (29, 'G4'), (14, 'G5')])
def test_categoria_g(tfg, g):
    assert funcao_renal.categoria_g(tfg)['categoria'] == g


@pytest.mark.parametrize('uacr, a', [(29, 'A1'), (30, 'A2'), (300, 'A2'), (301, 'A3')])
def test_categoria_a(uacr, a):
    assert funcao_renal.categoria_a(uacr)['categoria'] == a


def test_cartao_renal_na_resposta(client):
    sem = _post(client, idade=50).get_json()
    assert sem['funcao_renal'] is None
    # TFG < 60 sem DRC marcada: TFG e categoria, sem KFRE, com a confirmação em 3 meses
    isolada = _post(client, idade=65, creatinina='2.0', uacr=500).get_json()['funcao_renal']
    assert isolada['tfg'] < 60 and isolada['kfre'] is None and isolada['drc'] is False
    assert 'repetir a creatinina e a uACR em 3 meses' in ' '.join(isolada['observacoes'])
    # DRC marcada, sem uACR: pede a uACR para o KFRE
    sem_uacr = _post(client, idade=65, creatinina='2.0', comorbidades=['doenca_renal']).get_json()['funcao_renal']
    assert sem_uacr['kfre'] is None and 'uACR' in ' '.join(sem_uacr['observacoes'])
    # DRC marcada com uACR: KFRE em 2 e 5 anos, com as fontes
    drc = _post(client, idade=65, creatinina='2.0', uacr=500, comorbidades=['doenca_renal']).get_json()['funcao_renal']
    assert drc['g']['categoria'] == 'G3b' and drc['a']['categoria'] == 'A3'
    assert 0 < drc['kfre']['dois_anos'] < drc['kfre']['cinco_anos'] < 1
    assert any('jama.2015.18202' in f['link'] for f in drc['fontes'])
    assert 'encaminhamento ao nefrologista' in ' '.join(drc['observacoes'])


def test_uacr_entra_no_prevent(client):
    dados = dict(idade=55, creatinina='1.0', colesterol=200, hdl=45, pas=130, pad=80, peso=80, altura=175)
    assert _post(client, **dados).get_json()['risco_cardiovascular']['modelo'] == 'base'
    assert _post(client, uacr=40, **dados).get_json()['risco_cardiovascular']['modelo'] == 'uacr'


def test_uacr_fora_da_faixa_e_recusada(client):
    r = _post(client, idade=50, uacr=50000)
    assert r.status_code == 400


# --- Idade e tabagismo ------------------------------------------------------------------------

@pytest.mark.parametrize('idade', [17, 121, 150, 25.5])
def test_idade_impossivel_e_recusada(client, idade):
    assert _post(client, idade=idade).status_code == 400


def test_anos_sem_fumar_e_macos_ano_coerentes_com_a_idade(client):
    r = _post(client, idade=30, tabagismo='ex', anos_parou_fumar=50, macos_ano=10)
    assert r.status_code == 400 and 'incompatível com a idade' in r.get_json()['erros'][0]['mensagem']
    r = _post(client, idade=20, tabagismo='atual', macos_ano=200)
    assert r.status_code == 400
    assert _post(client, idade=60, tabagismo='ex', anos_parou_fumar=20, macos_ano=40).status_code == 200


def test_tela_tem_limites_nos_campos_numericos():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    for campo in ('idade', 'peso', 'altura', 'pas', 'pad', 'creatinina', 'hba1c', 'uacr', 'macos_ano', 'anos_parou_fumar'):
        assert re.search(rf'<input type="number" id="{campo}"[^>]* min="[^"]+" max="[^"]+"', html), campo
    assert 'conferirNumeros()' in html


# --- Orientações ------------------------------------------------------------------------------

def test_orientacoes_sem_motor_e_sem_imperativo_de_rastreio():
    fontes = [RAIZ / 'src' / 'routes' / 'checkup_intelligent.py'] + list((RAIZ / 'src' / 'utils').glob('*.py'))
    texto = '\n'.join(p.read_text(encoding='utf-8') for p in fontes)
    literais = ' '.join(re.findall(r"'([^'\n]*)'", texto))
    assert not re.search(r'\b[Oo] motor (segue|seguiu|pede|não pede|mostra|só)\b', literais)
    assert not re.search(r'\bRastreie\b', literais)
    assert 'Nós optamos por seguir a referência' in literais


def test_orientacoes_recolhiveis_e_sem_aviso_de_pdf():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert 'Orientações · não entram nos PDFs' not in html
    assert '<details class="risco-cartao orientacoes-recolhidas" data-orientacoes>' in html


# --- Colo do útero e lista de exames ------------------------------------------------------------

def test_campos_do_colo_dependem_da_idade_e_do_risco():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    corpo = html[html.index('function atualizarCamposDoColo()'):]
    corpo = corpo[:corpo.index('\n        }\n')]
    assert "(imuno || idade >= 25)" in corpo and "idade >= 60" in corpo and "histerectomia_total" in corpo


def test_exames_ja_feitos_usam_a_lista_do_catalogo():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert '<datalist' not in html
    assert "listaDeBusca(nome, () => examesDoCatalogo(['laboratorio', 'imagem'])" in html
    assert "listaDeBusca(document.getElementById('acrescimoBusca')" in html


def test_uacr_define_a_categoria_a_da_drc(client):
    r = _post(client, idade=65, creatinina='2.0', uacr=500, comorbidades=['doenca_renal']).get_json()
    uacr = next(x for x in r['recommendations'] if x['titulo'] == 'Relação albumina/creatinina urinária (uACR)')
    assert 'G3b A3' in uacr['subtitulo']
    assert 'Doença renal crônica: estágio incompleto' not in [o['titulo'] for o in r['orientacoes']]


def test_selecionar_exame_na_lista_invalida_o_resultado():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    trecho = html[html.index("listaDeBusca(nome, () => examesDoCatalogo"):]
    assert "nome.dispatchEvent(new Event('change', { bubbles: true }))" in trecho[:400]


def test_cartao_renal_traz_estagio_e_risco_kdigo(client):
    r = _post(client, idade=60, sexo='feminino', creatinina='1.0', uacr=10, comorbidades=['doenca_renal']).get_json()
    renal = r['funcao_renal']
    assert renal['estagio'] == 'Estágio 2' and renal['risco_kdigo'] == 'baixo'
    r = _post(client, idade=65, creatinina='2.0', uacr=500, comorbidades=['doenca_renal']).get_json()
    assert r['funcao_renal']['estagio'] == 'Estágio 3b' and r['funcao_renal']['risco_kdigo'] == 'muito alto'
    # sem DRC marcada não há estágio
    assert _post(client, idade=60, creatinina='1.0').get_json()['funcao_renal']['estagio'] is None


@pytest.mark.parametrize('g, a, risco', [('G1', 'A1', 'baixo'), ('G2', 'A2', 'moderado'), ('G3a', 'A1', 'moderado'),
                                         ('G3a', 'A2', 'alto'), ('G3b', 'A1', 'alto'), ('G3b', 'A2', 'muito alto'),
                                         ('G4', 'A1', 'muito alto')])
def test_mapa_de_risco_kdigo(g, a, risco):
    assert funcao_renal.risco_kdigo(g, a) == risco


def test_aviso_de_exames_alternativos_antes_do_pdf():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert "itens: ['Colonoscopia de Rastreio com ou sem biópsia', 'Sangue oculto nas fezes (FIT)']" in html
    assert 'id="conflitoPainel"' in html and 'desenharConflitos();' in html
    assert '&& !retirados.has(rec.titulo)' in html


def test_drc_sem_opcoes_de_estagio_na_tela():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    bloco = html.split('id="detalhes-doenca_renal"')[1].split('</div>')[0]
    assert 'det_drc_' not in bloco and 'Exames já realizados' in bloco


def test_conflito_vale_para_itens_acrescentados_e_e_redesenhado():
    html = (RAIZ / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert "!presentes.has(t.toLowerCase()) && !retirados.has(t)" in html
    trecho = html[html.index('function adicionarDoCampo()'):]
    assert 'desenharConflitos();' in trecho[:1200]


def test_resultado_de_hpv_depois_dos_65_segue_o_fluxo(client):
    """Sem sugerir rastreio depois dos 65, um HPV 16/18 já informado ainda leva à colposcopia."""
    r = _post(client, idade=70, sexo='feminino', hpv_resultado='hpv_16_18').get_json()
    assert any('olposcopia' in x['titulo'] for x in r['recommendations'])
