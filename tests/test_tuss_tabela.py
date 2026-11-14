"""Tabela TUSS de laboratório (planilha do responsável clínico) e os exames que ela acrescenta ao catálogo."""
import io
import re

from pypdf import PdfReader

from src.utils import catalogo, tuss

# Códigos de laboratório usados pelo Evidēns que a planilha não cobre (ela vai de 40301010 a 40314030):
# hormônios (40316...), biologia molecular depois de 40314030 e o sangue oculto imunológico.
FORA_DA_PLANILHA = {'40303250', '40314120', '40314146', '40314154'}


def test_tabela_tem_codigos_unicos_de_oito_digitos_e_nome():
    tabela = tuss.TABELA_DE_LABORATORIO
    assert len(tabela) == 859 == len(tuss.DA_TABELA)
    assert all(re.fullmatch(r'403(0\d|1[0-4])\d{3}', codigo) for codigo, _ in tabela)
    assert all(nome.strip() and len(nome) <= 300 for _, nome in tabela)
    nomes = [tuss._chave(nome) for _, nome in tabela]
    assert len(set(nomes)) == len(nomes), 'dois códigos com o mesmo nome'
    assert [codigo for codigo, _ in tabela] == sorted(tuss.DA_TABELA)


def test_codigos_de_laboratorio_do_motor_conferem_com_a_planilha():
    """Todo código de laboratório escrito à mão em tuss.py que cai na faixa da planilha existe nela."""
    na_faixa = [c for c in tuss.DESCRICOES if '40301010' <= c <= '40314030']
    fora = sorted(c for c in na_faixa if c not in tuss.DA_TABELA)
    assert fora == ['40303250'], fora
    de_outras_fontes = {c for c in tuss.DESCRICOES if c.startswith('403') and c not in tuss.DA_TABELA}
    assert FORA_DA_PLANILHA <= de_outras_fontes
    assert all(c.startswith('40316') for c in de_outras_fontes - FORA_DA_PLANILHA)


def test_nome_da_tuss_e_nome_do_evidens_dao_o_mesmo_codigo():
    assert tuss.linhas_da_guia('Ácido úrico')[0]['codigo'] == tuss.linhas_da_guia('Ácido úrico, soro')[0]['codigo'] == '40301150'
    assert tuss.linhas_da_guia('Acetaminofen') == [{'codigo': '40301036', 'descricao': 'Acetaminofen', 'quantidade': 1}]
    # a planilha traz duas descrições para 40310434; vale a que confere com a outra fonte
    assert tuss.DA_TABELA['40310434'] == 'Leishmania, pesquisa'
    assert [l['codigo'] for l in tuss.linhas_da_guia('Fator reumatoide e anti-CCP')] == ['40306860', '40308804']
    assert 'Fator reumatoide e anti-CCP' not in tuss.SEM_CODIGO


def test_catalogo_ganha_os_exames_da_tabela_sem_repetir_os_que_ja_existem():
    laboratorio = catalogo.catalogo()['laboratorio']
    assert len(laboratorio) > 850 and len(set(map(str.lower, laboratorio))) == len(laboratorio)
    for novo in ('Acetaminofen', 'Colesterol (HDL)', 'IgM', 'Ácido láctico (lactato)', 'Leishmania, pesquisa'):
        assert novo in laboratorio, novo
    # já estavam no catálogo com o nome do Evidēns: o nome da TUSS não entra de novo
    for repetido in ('Creatinina', 'Glicose', 'Ácido úrico', 'Albumina', 'Cálcio iônico'):
        assert repetido not in laboratorio, repetido
    assert 'Creatinina, soro' in laboratorio and 'Cálcio iônico, soro' in laboratorio
    # cálcio total fica de fora: o cálcio dos pedidos é sempre o iônico
    assert 'Cálcio' not in laboratorio
    # imagem e vacinas não mudam
    assert not set(tuss.DA_TABELA.values()) & set(catalogo.catalogo()['imagem'] + catalogo.catalogo()['vacina'])


def test_exame_da_tabela_entra_no_pedido_e_sai_na_guia_com_o_codigo(app, contas):
    from test_guia_do_plano import PACIENTE, PLANO, _conta
    cliente, _ = _conta(app, contas)
    cid = cliente.post('/api/auth/credenciamentos', json=PLANO).get_json()['credenciamento']['id']
    itens = [{'titulo': t, 'categoria': 'laboratorio'} for t in ('Acetaminofen', 'Colesterol (HDL)')]
    resposta = cliente.post('/api/gerar-pdf-exames-laboratoriais',
                            json={'dados_paciente': PACIENTE, 'recomendacoes': itens, 'guia': {'credenciamento_id': cid}})
    assert resposta.status_code == 200
    pedido, guia = [p.extract_text() for p in PdfReader(io.BytesIO(resposta.data)).pages]
    assert 'Acetaminofen' in pedido and 'Colesterol (HDL)' in pedido
    assert '40301036' in guia and '40301583' in guia


def test_exame_da_tabela_e_reconhecido_em_exames_ja_realizados(client):
    from src.utils import periodicidade
    assert not periodicidade.nao_reconhecidos([{'exame': 'Acetaminofen'}, {'exame': 'ácido úrico'}])
    assert periodicidade.nao_reconhecidos([{'exame': 'Exame inventado'}]) == ['Exame inventado']
    assert 'Acetaminofen' in client.get('/api/exames-conhecidos').get_json()['exames']
