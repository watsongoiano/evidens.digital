"""Exames mais comuns com campo de resultado (src/utils/exames_comuns.py): definição, leitura do resultado no laudo,
validação do que o médico digita e o cartão "Resultados informados". Dados fictícios."""
from pathlib import Path

import pytest

from src.utils import exames_comuns as E
from src.utils import laudos
from src.utils.catalogo import catalogo
from tests.test_laudos import HOJE, _cabecalho, _pdf
from tests.test_periodicidade import BASE

TELA = Path(__file__).resolve().parent.parent / 'intelligent-tools.html'


def test_ao_menos_40_exames_todos_do_catalogo_e_com_nome_curto():
    titulos = set(catalogo()['laboratorio'])
    assert len(E.EXAMES) >= 40
    assert all(t in titulos for _, t, _ in E.EXAMES)
    assert all(t in titulos for t in E.COMPONENTES)
    assert set(E.CURTO) == set(E.POR_TITULO)


def test_campos_do_motor_mantem_o_nome():
    assert set(E.DO_MOTOR) <= set(E.CAMPOS)


def test_outros_nomes_do_mesmo_exame_levam_aos_mesmos_campos():
    assert E.apelidos()['Glicemia de jejum, soro'] == ('Glicose, soro', ['glicose'])
    assert E.apelidos()['Colesterol (HDL)'] == ('Colesterol total e frações, soro', ['hdl'])
    assert E.campos_do_exame('Creatina') == [E.LIVRE]                 # fora da lista: resultado livre
    assert E.campos_do_exame('EAS - Elementos Anormais e Sedimentoscopia') == [E.LIVRE]


@pytest.mark.parametrize('titulo, linhas, esperado', [
    ('Colesterol total e frações, soro',
     ['Colesterol total: 190 mg/dL  Desejável: < 190', 'Colesterol não-HDL: 145 mg/dL', 'HDL: 45 mg/dL Desejavel > 40',
      'LDL (calculado): 120 mg/dL', 'VLDL: 25', 'Triglicerídeos: 150 mg/dL'],
     {'colesterol': 190, 'hdl': 45, 'ldl': 120, 'triglicerideos': 150}),
    ('Hemograma completo com plaquetas',
     ['Eritrocitos: 4,31', 'Hemoglobina......: 13,5 g/dL', 'Hemoglobina corpuscular media: 29 pg',
      'Leucocitos......: 7.500 /mm3', 'Plaquetas......: 250.000 /mm3'],
     {'hemoglobina': 13.5, 'leucocitos': 7500, 'plaquetas': 250000}),
    ('Hemoglobina glicada (HbA1c), soro', ['MATERIAL - SANGUE', 'RESULTADO: HEMOGLOBINA GLICADA (A1C): 5,2%'], {'hba1c': 5.2}),
    ('Hormônio Tireoestimulante (TSH), soro', ['   2,10 uUI/mL     0,45 a 4,5'], {'tsh': 2.1}),
    ('Anti-HIV 1 e 2, soro', ['Resultado: NÃO REAGENTE', 'Valor de referência: Não reagente'], {'anti_hiv': 'nao_reagente'}),
    ('Anti-HIV 1 e 2, soro', ['REAGENTE     Referência: Não reagente'], {'anti_hiv': 'reagente'}),
    ('HBsAg, anti-HBc total e anti-HBs', ['HBsAg: Não reagente', 'Anti-HBc total: Não reagente', 'Anti-HBs: 120 mUI/mL - Reagente'],
     {'hbsag': 'nao_reagente', 'anti_hbc': 'nao_reagente', 'anti_hbs': 'reagente'}),
    ('Sangue oculto nas fezes (FIT)', ['Resultado: Negativo'], {'fit': 'negativo'}),
    # Algum tipo de HPV detectado: o passo seguinte depende do tipo e da citologia, e fica com o médico.
    ('Pesquisa do Papilomavírus Humano (HPV), por técnica molecular', ['HPV 16: Não detectado', 'HPV 18: Detectado'], {}),
    ('Pesquisa do Papilomavírus Humano (HPV), por técnica molecular', ['Resultado: Não detectado'], {'hpv_resultado': 'nao_detectado'}),
    # Milhar só com a unidade dizendo: "500 /mm³" é 500; "7,5 mil/mm³" e "250 x10³/µL" são 7.500 e 250.000.
    ('Hemograma completo com plaquetas', ['Leucocitos: 500 /mm3', 'Plaquetas: 250 x10³/uL'], {'leucocitos': 500, 'plaquetas': 250000}),
    ('Hemograma completo com plaquetas', ['Leucocitos: 7,5 mil/mm3', 'Plaquetas: 180 /mm3'], {'leucocitos': 7500}),
    # A referência nunca vira resultado; número fora da faixa possível não é lido.
    ('Creatinina, soro', ['Valores de referência: 0,7 a 1,3 mg/dL'], {}),
    ('Creatinina, soro', ['Resultado: 90 mg/dL'], {}),
])
def test_resultado_lido_no_bloco_do_exame(titulo, linhas, esperado):
    assert E.valores_do_bloco(titulo, linhas) == esperado


@pytest.mark.parametrize('texto, campo, esperado', [
    (' Totais 9.200/mm³ 4.000 a 11.000/mm³', 'leucocitos', 9200),       # unidade colada no número
    (' 299.000 /mm³ 150.000 a 600.000 /mm³', 'plaquetas', 299000),
    (' 0/100 leuc 0/100 leuc', 'leucocitos', None),                      # fração não é resultado
    (' 16/11/2026', 'creatinina', None),                                 # data não é resultado
    (' 0,71 mg/dL', 'creatinina', 0.71),
])
def test_numero_com_unidade_colada(texto, campo, esperado):
    assert E._numero(texto, E.CAMPOS[campo]) == esperado


def test_limite_e_faixa_de_referencia_nao_sao_resultado():
    """Depois de "Valores de referência", "Até 1,2" e "2,0 a 3,0" não são lidos como o resultado do campo."""
    bilirrubinas = ['RESULTADO: DIRETA : 0,20 mg/dL', 'INDIRETA: 0,70 mg/dL', 'TOTAL : 0,90 mg/dL',
                    'VALORES DE REFERÊNCIA:', 'BILIRRUBINA TOTAL (ADULTO): Até 1,2 mg/dL']
    assert E.valores_do_bloco('Bilirrubinas totais e frações, soro', bilirrubinas) == {'bilirrubina_total': 0.9}
    # Sem a linha do total, nada é lido: nem a direta, nem o limite da referência
    assert E.valores_do_bloco('Bilirrubinas totais e frações, soro', bilirrubinas[:2] + bilirrubinas[3:]) == {}
    tap = ['RESULTADO: TEMPO : 14,0 SEGUNDOS', 'ATIVIDADE: 60,0 %', 'R.N.I. : 1,35',
           'Valor de referência: Maior ou igual a 70%', 'RNI: Até 1,20', '- Faixa Terapêutica em INR: 2,0 a 3,0']
    assert E.valores_do_bloco('Tempo de protrombina (TP/INR), plasma', tap) == {'inr': 1.35}
    assert E.valores_do_bloco('Tempo de protrombina (TP/INR), plasma', tap[:2] + tap[3:]) == {}
    # Antes da seção de referência, o resultado escrito ao lado do nome continua valendo
    assert E.valores_do_bloco('Tempo de protrombina (TP/INR), plasma', ['INR: 2,5', 'Valor de referência: até 1,2']) == {'inr': 2.5}
    # A primeira linha que começa por número só vale antes da seção de referência
    pcr = ['RESULTADO:', 'Valor de referência:', '10-50 mg/L - Inflamação ligeira']
    assert E.valores_do_bloco('Proteína C reativa, soro', pcr) == {}
    assert E.valores_do_bloco('Proteína C reativa, soro', ['RESULTADO:', '12,5 mg/L'] + pcr[1:]) == {'pcr': 12.5}


def test_exame_fora_da_lista_fica_com_o_texto_do_resultado_unico():
    assert E.do_laudo('Creatino fosfoquinase total (CK)', ['Material: Soro', 'RESULTADO: 80 U/L',
                                                           'Valor de Referência: 30 - 223 U/L']) == {'resultado': '80 U/L'}
    assert E.do_laudo('Creatino fosfoquinase total (CK)', ['RESULTADO:', 'TEMPO: 30,0 seg.']) == {}
    assert E.do_laudo('Creatino fosfoquinase total (CK)', ['Valor de referência:', 'RESULTADO: 80 U/L']) == {}
    assert E.do_laudo('Creatino fosfoquinase total (CK)', ['RESULTADO: NEGATIVO PARA CELULAS NEOPLASICAS']) == {}


def test_titulo_do_motor_leva_aos_campos_do_exame_da_lista():
    """"Glicemia de jejum, soro" (título do motor) é o exame "Glicose, soro" da lista: o resultado vai para o
    campo numérico. O fósforo tem na lista o mesmo título do motor; o nome antigo ("Fósforo") continua valendo."""
    assert E.apelidos()['Glicemia de jejum, soro'] == ('Glicose, soro', ['glicose'])
    assert E.do_laudo('Glicemia de jejum, soro', ['Material: Soro', 'RESULTADO: 92 mg/dL']) == {'glicose': 92.0}
    assert E.apelidos()['Fósforo, soro'] == ('Fósforo, soro', ['fosforo'])
    assert E.apelidos()['Fósforo'] == ('Fósforo, soro', ['fosforo'])
    for titulo in ('Fósforo, soro', 'Fósforo'):
        assert E.do_laudo(titulo, ['Material: Soro', 'RESULTADO: 3,5 mg/dL']) == {'fosforo': 3.5}


def test_laudo_devolve_os_resultados_de_cada_exame():
    paginas = [_cabecalho('10/11/2026') + [
        'COLESTEROL TOTAL E FRACOES', 'Metodo: Enzimatico', 'Colesterol total: 198 mg/dL', 'HDL: 52 mg/dL',
        'LDL: 118 mg/dL', 'Triglicerideos: 140 mg/dL',
        'DOSAGEM DE CREATININA', 'Metodo: Jaffe', 'Resultado: 0,9 mg/dL',
        'ANTI HIV 1 E 2', 'Metodo: Quimioluminescencia', 'Resultado: NAO REAGENTE   Referencia: Nao reagente']]
    lido = {e['exame']: e['resultados'] for e in laudos.ler(_pdf(paginas), HOJE)['exames']}
    assert lido['Colesterol total e frações, soro'] == {'colesterol': 198, 'hdl': 52, 'ldl': 118, 'triglicerideos': 140}
    assert lido['Creatinina, soro'] == {'creatinina': 0.9}
    assert lido['Anti-HIV 1 e 2 (4ª geração)'] == {'anti_hiv': 'nao_reagente'}


def test_resultado_digitado_e_validado():
    itens, erros = E.ler_resultados('Creatinina, soro', {'creatinina': '1,2'})
    assert itens == [{'campo': 'creatinina', 'rotulo': 'Creatinina', 'valor': '1,2', 'unidade': 'mg/dL'}] and not erros
    itens, erros = E.ler_resultados('Creatina', {'resultado': '  210   U/L '})
    assert itens[0]['valor'] == '210 U/L' and not erros
    assert E.ler_resultados('Creatinina, soro', {'creatinina': '90'})[1]
    assert E.ler_resultados('Anti-HIV 1 e 2, soro', {'anti_hiv': 'talvez'})[1]
    assert E.ler_resultados('Anti-HIV 1 e 2, soro', {'anti_hiv': 'nao_reagente'})[0][0]['valor'] == 'Não reagente'
    assert E.ler_resultados('Creatinina, soro', {'glicose': '90'}) == ([], [])     # campo de outro exame é ignorado


def test_rota_devolve_resultados_informados(client):
    exames = [{'exame': 'Creatinina, soro', 'data': '2026-09-01', 'resultados': {'creatinina': '1.1'}},
              {'exame': 'Colesterol total e frações, soro', 'data': '2026-10-01',
               'resultados': {'colesterol': '205', 'ldl': '130'}},
              {'exame': 'Hemograma completo', 'data': '2026-10-01'}]
    r = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames))
    assert r.status_code == 200
    informados = r.get_json()['resultados_informados']
    assert [i['exame'] for i in informados] == ['Colesterol total e frações, soro', 'Creatinina, soro']
    assert informados[0]['data'] == '01/10/2026'
    assert [(i['rotulo'], i['valor'], i['unidade']) for i in informados[0]['itens']] == [
        ('Colesterol total', '205', 'mg/dL'), ('LDL', '130', 'mg/dL')]


def test_rota_recusa_resultado_impossivel(client):
    exames = [{'exame': 'Potássio, soro', 'data': '2026-09-01', 'resultados': {'potassio': '45'}}]
    r = client.post('/api/checkup-intelligent', json=dict(BASE, exames_anteriores=exames))
    assert r.status_code == 400
    assert 'Potássio' in r.get_json()['erros'][0]['mensagem']


def test_rota_da_definicao(client, anonimo):
    assert anonimo.get('/api/exames-comuns').status_code == 401
    dados = client.get('/api/exames-comuns').get_json()
    assert len(dados['exames']) >= 40
    assert dados['apelidos']['Glicemia de jejum, soro'] == {'titulo': 'Glicose, soro', 'campos': ['glicose']}
    assert all('no_laudo' not in c for e in dados['exames'] for c in e['campos'])


def test_tela_tem_os_cartoes_e_o_resumo():
    html = TELA.read_text(encoding='utf-8')
    assert 'id="examesComunsPainel"' in html and 'data-cartoes-do-grupo' in html   # o cartão abre junto do grupo
    assert 'montagemDosComuns' in html                                             # montado uma vez só
    assert 'exames-comuns-abrir' in html and 'opcoes.hidden = true' in html        # cada grupo recolhido num botão
    assert "fetch('/api/exames-comuns'" in html
    assert '<div id="resultadosInformados" hidden>' in html                       # resumo oculto a pedido
    for nome in E.DO_MOTOR:
        assert f'data-campo="{nome}"' in html



def test_nenhuma_funcao_da_tela_e_declarada_duas_vezes():
    """Duas declarações com o mesmo nome: a segunda apaga a primeira sem erro (já aconteceu com limparResultados)."""
    import re
    from collections import Counter
    html = TELA.read_text(encoding='utf-8')
    repetidas = [n for n, q in Counter(re.findall(r'^ {8}(?:async\s+)?function\s+(\w+)\s*\(', html, re.M)).items() if q > 1]
    assert not repetidas, repetidas


def test_lista_sem_repeticao():
    titulos = [t for _, t, _ in E.EXAMES]
    assert len(titulos) == len(set(titulos))
    assert len(set(E.CURTO.values())) == len(E.CURTO)                 # nenhum botão com o mesmo nome
    nomes = [c['nome'] for _, _, campos in E.EXAMES for c in campos]
    assert len(nomes) == len(set(nomes))                               # nenhum campo de resultado em dois exames
    grupos = [g for g, _, _ in E.EXAMES]
    assert [g for i, g in enumerate(grupos) if i == 0 or grupos[i - 1] != g] == list(dict.fromkeys(grupos))   # grupos contíguos
