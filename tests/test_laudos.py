"""Laudo em PDF → "Exames já realizados" (src/utils/laudos.py). Laudos de teste fictícios, nos dois
formatos vistos em laboratórios de Goiânia: um exame por página com a coleta no cabeçalho, e vários
exames por página com "[DATA DA COLETA : ...]" abaixo de cada título."""
import io
from datetime import date

import pytest
from fpdf import FPDF

from src.utils import laudos

HOJE = date(2026, 11, 15)
PACIENTE = 'Fulana de Teste Ficticia'


def _pdf(paginas):
    pdf = FPDF()
    pdf.set_font('Helvetica', size=9)
    for linhas in paginas:
        pdf.add_page()
        for linha in linhas:
            pdf.cell(0, 5, linha, new_x='LMARGIN', new_y='NEXT')
    return bytes(pdf.output())


def _cabecalho(coleta):
    return [f'Paciente      {PACIENTE}        Dt. Nascimento   01/01/1980      Atendimento: 123',
            f'Medico        Medico de Teste                                    Coleta    {coleta} 16:31',
            'CNES          0000000                                            Impressao 24/09/2026 12:49', '']


# Um exame por página; coleta no cabeçalho; o hemograma vem sem "Método".
FORMATO_A = [
    _cabecalho('23/09/2026') + ['GLICEMIA', 'Metodo: Enzimatico', 'Material: Soro', 'Resultado: 90 mg/dL'],
    _cabecalho('23/09/2026') + ['TRANSAMINASE GLUTAMICO PIRUVICA', 'Metodo: Cinetico', 'Material: Soro'],
    _cabecalho('23/09/2026') + ['HEMOGRAMA COMPLETO', 'Sangue Total em EDTA', 'Eritrocitos........: 4,31 /uL'],
    _cabecalho('23/09/2026') + ['GASOMETRIA VENOSA', 'Metodo: Eletrodo Seletivo', 'Sodio : 138 mmol/L',
                                 'Glicose : 101 mg/dL'],
]

# Vários exames por página; data da coleta abaixo de cada título.
FORMATO_B = [[
    'Nome                                                   Data de Nascimento',
    PACIENTE.upper() + '    01/01/1980 (46 anos)',
    'Solicitante                                  Data Entrada   Pedido',
    'MEDICO DE TESTE - CRM-GO 1                   13/11/2026 1051976',
    'HEMOGLOBINA GLICADA (HBA1C)',
    '[DATA DA COLETA : 13/11/2026 08:06] Coleta de amostra realizada pela equipe do laboratorio',
    'MATERIAL - SANGUE', 'RESULTADO: HEMOGLOBINA GLICADA (A1C): 5,2%', 'GLICEMIA MEDIA ESTIMADA',
    'PARATORMONIO PTH INTACTO (MOLECULA INTEIRA)',
    '[DATA DA COLETA : 13/11/2026 08:06] Coleta de amostra realizada pela equipe do laboratorio',
    'ACTH',
    '[DATA DA COLETA : 13/11/2026 08:06] Coleta de amostra realizada pela equipe do laboratorio',
    'PESQUISA DE HPV',
    '[DATA DA COLETA : 10/11/2025 08:06]',
]]


def _nomes(lido):
    return {e['exame']: e['data'] for e in lido['exames']}


def test_formato_com_coleta_no_cabecalho():
    lido = laudos.ler(_pdf(FORMATO_A), HOJE)
    assert _nomes(lido) == {'Glicemia de jejum, soro': '2026-09-23', 'Alanina aminotransferase, soro': '2026-09-23',
                            'Hemograma completo': '2026-09-23'}
    assert lido['nao_reconhecidos'] == ['GASOMETRIA VENOSA']    # sódio e glicose da gasometria não contam


def test_formato_com_data_abaixo_de_cada_exame():
    lido = laudos.ler(_pdf(FORMATO_B), HOJE)
    nomes = _nomes(lido)
    assert nomes['Hemoglobina glicada (HbA1c), soro'] == '2026-11-13'
    assert nomes['Paratormônio (PTH), soro'] == '2026-11-13'
    assert nomes['Pesquisa do Papilomavírus Humano (HPV), por técnica molecular'] == '2025-11-10'
    assert lido['nao_reconhecidos'] == ['ACTH']


def test_nome_do_paciente_nunca_volta_na_resposta():
    for paginas in (FORMATO_A, FORMATO_B):
        lido = laudos.ler(_pdf(paginas), HOJE)
        assert PACIENTE.lower() not in str(lido).lower()


def test_exame_repetido_fica_com_a_coleta_mais_recente():
    antigo = _cabecalho('10/01/2025') + ['GLICEMIA', 'Metodo: Enzimatico']
    novo = _cabecalho('23/09/2026') + ['GLICOSE', 'Metodo: Enzimatico']
    assert _nomes(laudos.ler(_pdf([antigo, novo]), HOJE)) == {'Glicemia de jejum, soro': '2026-09-23'}


def test_data_futura_ou_ausente_nao_vira_data():
    futura = [['UREIA', '[DATA DA COLETA : 01/01/2030 08:00]', 'Material: Soro']]
    sem = [['CREATININA', 'Metodo: Jaffe', 'Material: Soro']]
    assert laudos.ler(_pdf(futura), HOJE)['sem_data'] == ['UREIA']
    assert laudos.ler(_pdf(sem), HOJE) == {'exames': [], 'nao_reconhecidos': [], 'sem_data': ['CREATININA']}


@pytest.mark.parametrize('nome, titulo', [
    ('TRANSAMINASE GLUTÂMICO OXALACÉTICA', 'Aspartato aminotransferase, soro'),
    ('GAMA GLUTAMIL TRANSFERASE - GAMA GT', 'Gama-GT, soro'),
    ('BILIRRUBINAS TOTAIS E FRAÇOES', 'Bilirrubinas totais e frações, soro'),
    ('TSH - HORMÔNIO TIREOESTIMULANTE', 'Hormônio Tireoestimulante (TSH), soro'),
    ('URINA TIPO I', 'EAS - Elementos Anormais e Sedimentoscopia, urina'),
    ('COMPLEMENTO SÉRICO C3', 'Complemento C3'),
    ('Ferritina', 'Ferritina, soro'),
])
def test_sinonimos_dos_laboratorios(nome, titulo):
    assert laudos.reconhecer(nome) == titulo


def test_proteina_c_reativa_comum_nao_vira_ultrassensivel():
    assert laudos.reconhecer('PROTEINA C REATIVA') != 'Proteína C reativa ultrassensível, soro'


@pytest.mark.parametrize('conteudo, trecho', [
    (b'nao sou pdf', 'não é um PDF'),
    (b'%PDF-1.4 quebrado', 'Não foi possível abrir'),
])
def test_arquivo_invalido(conteudo, trecho):
    with pytest.raises(laudos.LaudoIlegivel, match=trecho):
        laudos.ler(conteudo, HOJE)


def test_pdf_sem_texto_pede_digitacao():
    pdf = FPDF(); pdf.add_page(); pdf.rect(10, 10, 50, 50)
    with pytest.raises(laudos.LaudoIlegivel, match='escaneado'):
        laudos.ler(bytes(pdf.output()), HOJE)


def test_pdf_protegido_so_contra_edicao_e_lido():
    from pypdf import PdfReader, PdfWriter
    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(_pdf(FORMATO_A))))
    escritor.encrypt(user_password='', owner_password='dono')
    saida = io.BytesIO(); escritor.write(saida)
    assert 'Glicemia de jejum, soro' in _nomes(laudos.ler(saida.getvalue(), HOJE))


# ── Rota ─────────────────────────────────────────────────────────────────────

def _enviar(cliente, conteudo, nome='laudo.pdf'):
    return cliente.post('/api/laudos/ler', data={'arquivo': (io.BytesIO(conteudo), nome)},
                        content_type='multipart/form-data')


def test_rota_exige_login(anonimo):
    assert _enviar(anonimo, _pdf(FORMATO_A)).status_code == 401


def test_rota_devolve_os_exames(client):
    r = _enviar(client, _pdf(FORMATO_A))
    assert r.status_code == 200
    assert 'Glicemia de jejum, soro' in {e['exame'] for e in r.get_json()['exames']}


def test_rota_recusa_o_que_nao_e_pdf_e_sem_arquivo(client):
    assert _enviar(client, b'texto').status_code == 422
    assert client.post('/api/laudos/ler', data={}, content_type='multipart/form-data').status_code == 400


def test_rota_aceita_laudo_maior_que_o_limite_geral_e_recusa_acima_de_4_mb(client):
    grande = _pdf(FORMATO_A * 1) + b'%' + b'0' * (2 * 1024 * 1024)   # 2 MB: acima do 1 MB das outras rotas
    assert _enviar(client, grande).status_code == 200
    enorme = b'%PDF-1.4\n' + b'0' * (5 * 1024 * 1024)
    assert _enviar(client, enorme).status_code in (413, 422)


def test_nomes_lidos_estao_na_lista_de_exames_conhecidos(client):
    conhecidos = set(client.get('/api/exames-conhecidos').get_json()['exames'])
    for paginas in (FORMATO_A, FORMATO_B):
        for exame in laudos.ler(_pdf(paginas), HOJE)['exames']:
            assert exame['exame'] in conhecidos, exame


def test_laudo_lido_adia_o_exame_em_dia(client):
    """Do laudo ao motor: HPV feito há 1 ano, periodicidade de 5 anos (MS 2025) → não é pedido."""
    lido = laudos.ler(_pdf(FORMATO_B), date.today())
    corpo = dict(idade=40, sexo='feminino', tabagismo='nunca', exames_anteriores=lido['exames'])
    dados = client.post('/api/checkup-intelligent', json=corpo).get_json()
    pedidos = {r['titulo'] for r in dados['recommendations']}
    adiados = {r['titulo'] for r in dados.get('nao_incluidas', []) if r.get('estado') == 'em_dia'}
    hpv = 'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular'
    assert hpv not in pedidos and hpv in adiados
