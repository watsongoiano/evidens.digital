"""SUS: estabelecimentos por CNES (cadastro compartilhado), vínculo do médico com o CNS dele e o laudo de
solicitação de APAC que sai junto do pedido de exames de imagem. Dados fictícios."""
import io
import re
import itertools

import pytest
from pypdf import PdfReader

from conftest import SENHA_DE_TESTE, aceitar_termos
from src.utils import catalogo, sigtap

_seq = itertools.count(1)
PACIENTE = {'nome': 'Maria de Teste', 'idade': '65', 'sexo': 'feminino'}


def _paginas(dados):
    assert dados.startswith(b'%PDF')
    return [p.extract_text() for p in PdfReader(io.BytesIO(dados)).pages]


def _conta(app, contas, perfil='medico'):
    """Cliente logado numa conta nova e aprovada (e-mails próprios deste arquivo)."""
    n = next(_seq)
    registro = 'CRM-GO 5432' + str(n) if perfil != 'estudante' else '2023002 · UFG'
    u = contas.criar(f'apac{n}@exemplo.test', f'Dra. Apac {n}', registro, perfil, SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def _cns(prefixo='7'):
    """CNS fictício válido: 14 dígitos e o último ajustado para a soma ponderada fechar em múltiplo de 11."""
    for final in range(10 ** 4):
        cns = (prefixo + '0' * 10 + str(final).zfill(4))[:15]
        if sum(int(d) * (15 - i) for i, d in enumerate(cns)) % 11 == 0:
            return cns
    raise AssertionError


def test_cns_e_cnes(contas):
    assert contas.cns_valido(_cns()) and contas.cns_valido(_cns('1'))
    assert not contas.cns_valido('700000000000001') and not contas.cns_valido('123')
    assert contas.cnes_limpo('123.456-7') == '1234567' and contas.cnes_limpo('123456') == ''


def test_estabelecimento_e_compartilhado_e_o_cns_fica_na_conta(app, contas):
    a, ua = _conta(app, contas)
    b, ub = _conta(app, contas)
    r = a.post('/api/auth/vinculos-sus', json={'cnes': '7654321', 'nome': 'Hospital Fictício', 'cns': _cns()})
    assert r.status_code == 201
    # O segundo médico acha o estabelecimento pelo CNES e só informa o próprio CNS.
    assert b.get('/api/auth/estabelecimentos?cnes=7654321').get_json()['estabelecimentos'][0]['nome'] == 'Hospital Fictício'
    assert b.post('/api/auth/vinculos-sus', json={'cnes': '7654321', 'cns': _cns('1')}).status_code == 201
    vb = b.get('/api/auth/vinculos-sus').get_json()['vinculos']
    assert len(vb) == 1 and vb[0]['cns'] == _cns('1') and vb[0]['nome'] == 'Hospital Fictício'
    assert all(v['cns'] != _cns() for v in vb)
    # Só quem cadastrou corrige o nome.
    eid = vb[0]['estabelecimento_id']
    assert b.post(f'/api/auth/estabelecimentos/{eid}/nome', json={'nome': 'Outro nome'}).status_code == 403
    assert a.post(f'/api/auth/estabelecimentos/{eid}/nome', json={'nome': 'Hospital Fictício Central'}).status_code == 200


def test_cadastro_recusa_dados_errados(app, contas):
    cliente, _ = _conta(app, contas)
    erros = cliente.post('/api/auth/vinculos-sus', json={'cnes': '12', 'cns': '123'}).get_json()['erros']
    assert any('CNES' in e for e in erros) and any('CNS' in e for e in erros)
    sem_nome = cliente.post('/api/auth/vinculos-sus', json={'cnes': '1112223', 'cns': _cns()})
    assert sem_nome.status_code == 400 and 'nome do estabelecimento' in sem_nome.get_json()['erros'][0]
    estudante, _ = _conta(app, contas, perfil='estudante')
    assert estudante.post('/api/auth/vinculos-sus', json={'cnes': '1112223', 'nome': 'X Y Z', 'cns': _cns()}).status_code == 403


def _vinculo(cliente):
    r = cliente.post('/api/auth/vinculos-sus', json={'cnes': '2223334', 'nome': 'Policlínica Fictícia', 'cns': _cns()})
    return r.get_json()['vinculo']['id']


def test_pedido_de_imagem_pelo_sus_sai_com_laudo_de_apac_so_nos_exames_que_pedem(app, contas):
    cliente, medico = _conta(app, contas)
    vid = _vinculo(cliente)
    itens = [{'titulo': 'Tomografia computadorizada de tórax de baixa dose (LDCT)', 'categoria': 'imagem'},
             {'titulo': 'Ultrassonografia de abdome total', 'categoria': 'imagem'}]
    apac = {'vinculo_id': vid, 'cid': 'z12.2',
            'paciente': {'cns': _cns('8'), 'nascimento': '01/02/1960', 'mae': 'Mãe Fictícia', 'municipio': 'Goiânia', 'uf': 'GO'}}
    r = cliente.post('/api/gerar-pdf-exames-imagem', json={
        'dados_paciente': PACIENTE, 'recomendacoes': itens, 'apac': apac, 'justificativa': 'Rastreamento de câncer de pulmão'})
    assert r.status_code == 200
    paginas = _paginas(r.data)
    assert len(paginas) == 3                                     # 2 pedidos + 1 APAC (só a tomografia)
    laudo = paginas[2]
    for esperado in ('APAC', 'Laudo de Solicitação', 'Policlínica Fictícia', '2223334', '02.06.02.003-1',
                     'Tomografia computadorizada de tórax', 'Z12.2', 'Mãe Fictícia', _cns('8'), _cns(),
                     'Rastreamento de câncer de pulmão', medico['nome']):
        assert esperado in laudo, esperado
    assert 'Ultrassonografia' not in laudo


def test_apac_recusada_fora_da_imagem_com_cns_ou_cid_errados(app, contas):
    cliente, _ = _conta(app, contas)
    vid = _vinculo(cliente)
    itens = [{'titulo': 'Ressonância magnética de crânio', 'categoria': 'imagem'}]
    lab = cliente.post('/api/gerar-pdf-exames-laboratoriais', json={
        'dados_paciente': PACIENTE, 'recomendacoes': [{'titulo': 'Creatinina, soro', 'categoria': 'laboratorio'}],
        'apac': {'vinculo_id': vid}})
    assert lab.status_code == 400
    for apac in ({'vinculo_id': vid, 'paciente': {'cns': '123456789012345'}}, {'vinculo_id': vid, 'cid': 'abc'},
                 {'vinculo_id': 99999}):
        assert cliente.post('/api/gerar-pdf-exames-imagem', json={
            'dados_paciente': PACIENTE, 'recomendacoes': itens, 'apac': apac}).status_code == 400, apac


def test_tabela_sigtap_so_com_exames_do_catalogo_e_codigos_bem_formados():
    titulos = set(catalogo.catalogo()['imagem'])
    for titulo, (codigo, _) in sigtap.PROCEDIMENTOS.items():
        assert titulo in titulos, titulo
        assert codigo == '' or (len(codigo) == 10 and codigo.isdigit() and codigo.startswith('02')), titulo
    assert sigtap.formatado('0206020031') == '02.06.02.003-1'
    assert sigtap.vai_em_apac('Ressonância magnética de crânio') and not sigtap.vai_em_apac('Ultrassonografia de abdome total')


def test_tela_tem_o_sus_no_seletor_e_os_campos_da_apac():
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    html = (raiz / 'intelligent-tools.html').read_text(encoding='utf-8')
    assert "fetch('/api/auth/vinculos-sus'" in html and "o.value = 'sus:' + v.id" in html
    assert 'id="apacCampos"' in html and 'function apacDoDialogo(categoria)' in html
    conta = (raiz / 'conta.html').read_text(encoding='utf-8')
    assert 'data-sus' in conta and 'name="cns"' in conta


def test_cid_automatico_pelas_comorbidades():
    assert sigtap.cid_do_exame('Colonoscopia', ['hipertensao', 'crohn_colon']) == ('K50.1', 'I10')
    assert sigtap.cid_do_exame('Colonoscopia', ['hipertensao']) == ('Z12.1', 'I10')
    assert sigtap.cid_do_exame('Tomografia de tórax de baixa dose', ['dpoc']) == ('Z12.2', 'J44.9')
    assert sigtap.cid_do_exame('Densitometria óssea (DEXA)', ['osteoporose_diagnostico']) == ('M81.9', '')
    assert sigtap.cid_do_exame('Endoscopia digestiva alta', ['diabetes', 'obesidade']) == ('E11.9', 'E66.9')
    assert sigtap.cid_do_exame('Endoscopia digestiva alta', []) == ('Z00.0', '')
    # O que o médico digita prevalece.
    assert sigtap.cid_do_exame('Colonoscopia', ['crohn_colon'], 'K63.5') == ('K63.5', 'K50.1')
    assert all(re.fullmatch(r'[A-Z]\d{2}(\.\d)?', c) for c in sigtap.CID_DA_COMORBIDADE.values())


def test_tela_envia_comorbidades_para_o_cid():
    html = open('intelligent-tools.html', encoding='utf-8').read()
    assert "cid: v('apacCid').toUpperCase(), comorbidades" in html


def test_dados_da_apac_somem_quando_muda_o_paciente():
    """Nome ou dados clínicos novos depois de um resultado, ou "limpar guia": o laudo do paciente anterior é apagado."""
    html = open('intelligent-tools.html', encoding='utf-8').read()
    for campo in ('apacCns', 'apacNascimento', 'apacMae', 'apacCid', 'apacEndereco'):
        assert f"'{campo}'" in html.split('const CAMPOS_DA_APAC')[1].split(';')[0]
    confirmacao = html.split('function pedirConfirmacaoDoPlano()')[1].split('\n        }')[0]
    limpeza = html.split('function limparGuia()')[1].split('\n        }')[0]
    assert 'limparApac()' in confirmacao and 'limparApac()' in limpeza
