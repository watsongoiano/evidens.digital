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


# Laboratório de hospital: vários exames por página; "Data Coleta" só em parte dos exames; no cabeçalho, a data
# da internação ("Dt. Atendimento") e a da solicitação ("Dt. Solic"), o sexo, o nascimento e o setor.
def _cabecalho_c():
    return ['Laboratorio de Analises Clinicas',
            'Dt. Atendimento: 05/11/2026                                         Dt. Solic:     14/11/2026',
            'Atendimento: 123456                                                 Sexo:          F',
            'Paciente: 654321                                                    Nasc.:         01/01/1980',
            f'Nome Paciente: {PACIENTE.upper()}                                  Pedido no:     999',
            'Medico Solic.: MEDICO DE TESTE                                      Dt. Laudo:     14/11/2026',
            'Nome da Mae: MAE DE TESTE FICTICIA',
            'Setor:                  HOSPITAL DE TESTE - U.I CLINICA MEDICA', '',
            'BIOMEDICO DE TESTE', ' CRBM - 0000', 'Endereco: Rua de Teste, 1', '(62 0000-0000)']


FORMATO_C = [
    _cabecalho_c() + [
        'HEMOGRAMA', '', 'Material: Sangue', 'Método: Contador automatizado e microscopia óptica',
        'Data Coleta: 13/11/2026', 'Hora Coleta: 08:00', '',
        '                           Valores Obtidos                         Valores de Referência',
        'Hemácias 4,58 x106/mm³ 4,50 a 6,00³x106/mm', 'Hemoglobina 12,30 g/dL 13,00 a 18,00 g/dL',
        'Hematócrito 37,00 % 40,00 a 52,00 %', 'Eritroblastos 0/100 leuc 0/100 leuc',
        'Plaquetas 250.000 /mm³ 150.000 a 600.000 /mm³', 'Leucócitos Totais 7.500/mm³ 4.000 a 11.000/mm³',
        'Neutrófilos', 'Segmentados 60% 4.500/mm³ 39 a 70% 1.560 a 7.700/mm³'],
    _cabecalho_c() + ['Basófilos 0% 0/mm³ 0 a 1% 0 a 110 /mm³', 'Linfócitos', 'Atípicos 0% 0/mm³  0% 0/mm³',
                      'OBSERVAÇÕES:'],
    _cabecalho_c() + [
        'TAP - TEMPO DE ATIVIDADE DA PROTROMBINA (RNI)', '', 'Material: Plasma', 'Método: Coagulometria automatizada',
        '', 'RESULTADO: TEMPO    : 14,0 SEGUNDOS', '           ATIVIDADE: 60,0 %', '           R.N.I.   : 1,35',
        '                        ISI      : 0,97', '           PLASMA CONTROLE: 10,5', '',
        'Valor de referência: Maior ou igual a 70%', '                     RNI: Até 1,20', '',
        'Obs.:O valor do INR é indicado para controle de tratamento com anticoagulante oral.',
        '- Faixa Terapêutica em INR: 2,0 a 3,0', '',
        'TEMPO PARCIAL DE TROMBOPLASTINA ATIVADO', '', 'Material: Plasma', 'Método: Coagulometria automatizada', '',
        'RESULTADO:', 'TEMPO: 30,0 seg.', 'RELAÇÃO PACIENTE/CONTROLE:1,10', 'PLASMA NORMAL: 26,90 seg.', '',
        'Valor de referência: Inferior A 1,22'],
    _cabecalho_c() + [
        'CREATININA', '', 'Material: Soro', 'Método: Colorimétrico Automatizado', '', 'RESULTADO: 0,90 mg/dL', '',
        'Valor de Referência :   Homem : De 0,70 a 1,30 mg/dL', '                          Mulher: De 0,60 a 1,20 mg/dL',
        'FÓSFORO', '', 'Material: Soro', 'Método: Colorimétrico Automatizado.', '', 'RESULTADO: 3,5 mg/dL', '',
        'Valores de Referência: Adultos  : DE 2,5 A 5,0 mg/dL'],
    _cabecalho_c() + [
        'URÉIA', '', 'Material: Soro', 'Método: Enzimático automatizado.', 'Data coleta: 14/11/2026',
        'Hora coleta: 08:00', '', 'RESULTADO: 33 mg/dL', '', 'Valor de Referência: 7 - 40 mg/dL', '',
        'CÁLCIO IÔNICO', '', 'Material: Sangue', 'Método: Colorimétrico automatizado / Cálculo', '',
        'RESULTADO: 1,14 mmol/L', '', 'Valor de referência: 1,02 a 1,27 mmol/L',
        'SÓDIO', 'Material: Sangue', 'Método: Eletrodo Seletivo.', 'RESULTADO:140 mEq/L',
        'Valor de Referência: 136 a 145 mEq/L'],
    _cabecalho_c() + [
        'BILIRRUBINAS TOTAIS E FRAÇÕES', '', 'Material: Soro', 'Método: Colorimétrico Automatizado', '',
        'RESULTADO: DIRETA  : 0,20 mg/dL', ' INDIRETA: 0,70 mg/dL', ' TOTAL   : 0,90 mg/dL', '',
        'VALORES DE REFERÊNCIA:', '   BILIRRUBINA DIRETA  : Até 0,5 mg/dL', '   BILIRRUBINA INDIRETA: Até 0,7 mg/dL',
        '   BILIRRUBINA TOTAL (ADULTO): Até 1,2 mg/dL',
        'Obs: A dosagem de Bilirrubinas sofre alta variação, chegando a um erro total de até 31%.'],
    _cabecalho_c() + [
        'TRANSAMINASE OXALACÉTICA (TGO-AST)', '', 'Material: Soro', 'Método: Colorimétrico', '', 'RESULTADO:20 U/L',
        '', 'Valor de Referência: Inferior a 40,0 U/L',
        'TRANSAMINASE PIRÚVICA - TGP', '', 'Material: Soro', 'Método: Colorimétrico', '', 'RESULTADO: 28 U/L', '',
        'VALORES DE REFERÊNCIA: HOMEM : Inferior a 45,0 U/L', '                       MULHER: Inferior a 34,0 U/L'],
    _cabecalho_c() + [
        'CREATINOFOSFOQUINASE - CPK', '', 'Material: Soro', 'Método: Colorimétrico cinético', '', 'RESULTADO: 80 U/L',
        '', 'Valor de Referência: 30 - 223 U/L',
        'PROTEÍNAS TOTAIS E FRAÇÕES', '', 'Material: Soro', 'Método: Colorimétrico Automatizado', '',
        'RESULTADO: ALBUMINA', ':', '3,90 g/dL', ':', '2,60 g/dL', ' PROTEÍNAS', 'TOTAIS:', '6,50 g/dL', '',
        'VALORES DE REFERÊNCIA:', '    ALBUMINA:         3,5 - 5,5 g/dL', '    PROTEÍNAS TOTAIS: 6,3 - 8,2 g/dL'],
    _cabecalho_c() + [
        'PROTEINA C REATIVA', '', 'Material: Soro', 'Método: Imunoensaio Turbidimétrico Automatizado.', '',
        'RESULTADO:12,50 mg/L', '', 'Valor de referência:', '10-50 mg/L  - Inflamação ligeira',
        '50-100 mg/L - Inflamação mais grave', '',
        'ÁCIDO LÁCTICO - LACTATO', '', 'Material: Plasma Fluoretado', 'Método: Enzimático colorimétrico', '',
        'RESULTADO: 1,8 mmol/L', '', 'Valor de referência: 0,5 a 2,2 mmol/L',
        'CÁLCIO TOTAL', '', 'Material: Soro', 'Método: Colorimétrico Automatizado', '', 'RESULTADO: 9,10 mg/dL', '',
        'Valor de Referência: 8,6 a 10,3 mg/dL',
        'Obs: A dosagem de Cálcio total é influenciada pelas proteínas séricas.'],
]


def _nomes(lido):
    return {e['exame']: e['data'] for e in lido['exames']}


def _resultados(lido):
    return {e['exame']: e['resultados'] for e in lido['exames']}


def test_formato_de_laboratorio_de_hospital():
    """Todos os exames do laudo são identificados; a data é a "Data Coleta" do exame ou, sem ela, a "Dt. Solic"
    do cabeçalho. A "Dt. Atendimento" (internação) nunca é usada."""
    lido = laudos.ler(_pdf(FORMATO_C), HOJE)
    assert lido['nao_reconhecidos'] == [] and lido['sem_data'] == []
    nomes = _nomes(lido)
    assert nomes == {
        'Hemograma completo': '2026-11-13',                      # "Data Coleta" do próprio exame
        'Tempo de protrombina (TP/INR), plasma': '2026-11-14', 'Tempo de tromboplastina parcial ativada': '2026-11-14',
        'Creatinina, soro': '2026-11-14', 'Fósforo, soro': '2026-11-14', 'Ureia, soro': '2026-11-14',
        'Cálcio iônico, soro': '2026-11-14', 'Sódio, soro': '2026-11-14',
        'Bilirrubinas totais e frações, soro': '2026-11-14', 'Aspartato aminotransferase, soro': '2026-11-14',
        'Alanina aminotransferase, soro': '2026-11-14', 'Creatino fosfoquinase total (CK)': '2026-11-14',
        'Proteínas totais albumina e globulina': '2026-11-14', 'Proteína C reativa ultrassensível, soro': '2026-11-14',
        'Ácido láctico (lactato)': '2026-11-14', 'Cálcio': '2026-11-14'}
    assert '2026-11-05' not in nomes.values()


def test_resultados_do_laudo_de_hospital_nunca_vem_da_referencia():
    r = _resultados(laudos.ler(_pdf(FORMATO_C), HOJE))
    assert r['Hemograma completo'] == {'hemoglobina': 12.3, 'leucocitos': 7500, 'plaquetas': 250000}
    assert r['Tempo de protrombina (TP/INR), plasma'] == {'inr': 1.35}        # não "RNI: Até 1,20" nem "INR: 2,0 a 3,0"
    assert r['Bilirrubinas totais e frações, soro'] == {'bilirrubina_total': 0.9}   # não a direta nem "Até 1,2"
    assert r['Creatinina, soro'] == {'creatinina': 0.9} and r['Fósforo, soro'] == {'fosforo': 3.5}
    assert r['Ureia, soro'] == {'ureia': 33} and r['Sódio, soro'] == {'sodio': 140}
    assert r['Cálcio iônico, soro'] == {'calcio_ionico': 1.14}
    assert r['Aspartato aminotransferase, soro'] == {'tgo': 20} and r['Alanina aminotransferase, soro'] == {'tgp': 28}
    assert r['Proteína C reativa ultrassensível, soro'] == {'pcr': 12.5}      # não o "10-50 mg/L" da referência
    # Exame fora da lista, com um resultado só: fica o texto do resultado
    assert r['Creatino fosfoquinase total (CK)'] == {'resultado': '80 U/L'}
    assert r['Cálcio'] == {'resultado': '9,10 mg/dL'} and r['Ácido láctico (lactato)'] == {'resultado': '1,8 mmol/L'}
    # Vários valores no mesmo exame, sem campo na lista: nada é lido (o médico confere no laudo)
    assert r['Tempo de tromboplastina parcial ativada'] == {} and r['Proteínas totais albumina e globulina'] == {}


def test_nomes_do_cabecalho_do_laudo_de_hospital_nunca_voltam():
    lido = str(laudos.ler(_pdf(FORMATO_C), HOJE)).lower()
    for nome in (PACIENTE, 'mae de teste', 'medico de teste', 'biomedico de teste', '654321', '01/01/1980'):
        assert nome.lower() not in lido


def test_cabecalho_do_laudo_para_o_modo_sombra():
    dados = laudos.cabecalho(laudos.textos_do_pdf(_pdf(FORMATO_C)), HOJE)
    assert dados == {'sexo': 'feminino', 'nascimento': date(1980, 1, 1),
                     'setor': 'HOSPITAL DE TESTE - U.I CLINICA MEDICA'}
    assert laudos.cabecalho(laudos.textos_do_pdf(_pdf(FORMATO_B)), HOJE) == {'sexo': None, 'nascimento': None, 'setor': ''}


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
    assert laudos.ler(_pdf(sem), HOJE) == {'exames': [], 'nao_reconhecidos': [], 'sem_data': ['CREATININA'], 'resumo': []}


@pytest.mark.parametrize('nome, titulo', [
    ('TRANSAMINASE GLUTÂMICO OXALACÉTICA', 'Aspartato aminotransferase, soro'),
    ('GAMA GLUTAMIL TRANSFERASE - GAMA GT', 'Gama-GT, soro'),
    ('BILIRRUBINAS TOTAIS E FRAÇOES', 'Bilirrubinas totais e frações, soro'),
    ('TSH - HORMÔNIO TIREOESTIMULANTE', 'Hormônio Tireoestimulante (TSH), soro'),
    ('URINA TIPO I', 'EAS - Elementos Anormais e Sedimentoscopia, urina'),
    ('COMPLEMENTO SÉRICO C3', 'Complemento C3'),
    ('Ferritina', 'Ferritina, soro'),
    ('TAP - TEMPO DE ATIVIDADE DA PROTROMBINA (RNI)', 'Tempo de protrombina (TP/INR), plasma'),
    ('TEMPO PARCIAL DE TROMBOPLASTINA ATIVADO', 'Tempo de tromboplastina parcial ativada'),
    ('TRANSAMINASE OXALACÉTICA (TGO-AST)', 'Aspartato aminotransferase, soro'),
    ('CREATINOFOSFOQUINASE - CPK', 'Creatino fosfoquinase total (CK)'),
    ('CÁLCIO TOTAL', 'Cálcio'),
    ('PROTEÍNAS TOTAIS E FRAÇÕES', 'Proteínas totais albumina e globulina'),
])
def test_sinonimos_dos_laboratorios(nome, titulo):
    assert laudos.reconhecer(nome) == titulo


@pytest.mark.parametrize('nome', ['GLICOSE (URINA)', 'PSA (LIVRE)', 'CREATININA - URINA 24 HORAS', 'TSH (NEONATAL)'])
def test_qualificador_desconhecido_deixa_o_titulo_sem_reconhecer(nome):
    """Material ou fração diferente não pode virar o exame do soro (adiaria um exame que não foi feito)."""
    assert laudos.reconhecer(nome) is None


def test_data_de_um_exame_nao_passa_para_o_seguinte():
    pagina = [['GLICEMIA', '[DATA DA COLETA : 10/09/2026 08:00]', 'Material: Soro',
               'CREATININA', 'Metodo: Jaffe', 'Material: Soro',
               'UREIA', '[DATA DA COLETA : 01/01/2030 08:00]', 'Material: Soro']]
    lido = laudos.ler(_pdf(pagina), HOJE)
    assert _nomes(lido) == {'Glicemia de jejum, soro': '2026-09-10'}
    assert lido['sem_data'] == ['CREATININA', 'UREIA']


def test_data_do_cabecalho_vale_para_os_exames_sem_data_propria():
    pagina = [_cabecalho('23/09/2026') + ['UREIA', 'Material: Soro', 'CREATININA', 'Material: Soro']]
    assert _nomes(laudos.ler(_pdf(pagina), HOJE)) == {'Ureia, soro': '2026-09-23', 'Creatinina, soro': '2026-09-23'}


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


# Sistema Matrix/MV: "Valores de Referência" na linha do título, "DOSAGEM DE ..." e a coleta em
# "Coletado(dd/mm/aaaa hh:mm) Liberado(...)" no fim de cada exame; o "Cadastro" do cabeçalho é a data do
# pedido. Um exame pode terminar (com o "Coletado") na página seguinte.
def _cabecalho_mv():
    return ['Avenida Ficticia, s/n', f'Sr(a): {PACIENTE.upper()}', 'Pedido Matrix: 1 Prontuario MV: 2',
            'Medico Solicitante: CRM-GO-1 MEDICO DE TESTE', 'Cadastro: 01/11/2026 10:35:00']


FORMATO_MV = [
    _cabecalho_mv() + [
        'TEMPO DE PROTROMBINA                     Valores de Referencia',
        '   82,0 %Atividade: 70,0 - 100,0 %', 'Material : Plasma', 'Metodo : Coagulometrico',
        'Hash laudo: 9F589E504AA8',
        'Coletado(13/11/2026 10:49) Liberado(13/11/2026 11:27)', 'Liberacao: Biomedico de Teste - CRBM 1'],
    _cabecalho_mv() + [
        'DOSAGEM DE CREATININA                    Valores de Referencia', 'Resultado: 0,9 mg/dL',
        'Material: Soro', 'Coletado(12/11/2026 10:49) Liberado(12/11/2026 11:32)',
        'DOSAGEM DE POTASSIO TLR                  Valores de referencia', 'Resultado: 4,1 mmol/L',
        'Material: Sangue Total', 'Coletado(12/11/2026 10:49) Liberado(12/11/2026 11:27)',
        'DOSAGEM DE HDL COLESTEROL', 'HDL: 45 mg/dL', 'Material: Soro'],
    _cabecalho_mv() + ['Hash laudo: 1B2B', 'Coletado(10/11/2026 10:49) Liberado(10/11/2026 11:27)',
                       'HORMONIO TIREOESTIMULANTE                Valores de Referencia',
                       'Resultado: 2,1 uUI/mL', 'Coletado(09/11/2026 16:10) Liberado(09/11/2026 17:30)'],
]


def test_laudo_matrix_mv_le_titulo_sem_coluna_e_coleta_no_fim_do_exame():
    lido = laudos.ler(_pdf(FORMATO_MV), HOJE)
    assert _nomes(lido) == {
        'Tempo de protrombina (TP/INR), plasma': '2026-11-13',
        'Creatinina, soro': '2026-11-12',
        'Potássio, soro': '2026-11-12',
        'Colesterol (HDL)': '2026-11-10',     # o "Coletado" ficou no topo da página seguinte
        'Hormônio Tireoestimulante (TSH), soro': '2026-11-09',
    }
    assert lido['sem_data'] == [] and lido['nao_reconhecidos'] == []
    assert '2026-11-01' not in _nomes(lido).values()      # "Cadastro" não é coleta


def test_resumo_em_uma_linha_por_data_sem_referencia_e_sem_nome():
    """"14/11/2026 - RNI 1,35 | ... | Cr 0,90": só o que o laudo traz escrito, na ordem da evolução clínica."""
    lido = laudos.ler(_pdf(FORMATO_C), HOJE)
    assert lido['resumo'] == [
        {'data': '2026-11-14', 'texto': 'RNI 1,35 | TTPA 1,10 | Cr 0,90 | Ur 33 | Na 140 | CaT 9,10 | CaI 1,14 | P 3,5 | '
                                        'TGO 20 | TGP 28 | BT 0,90 (BD 0,20 / BI 0,70) | PT 6,50 (Alb 3,90) | CPK 80 | '
                                        'PCR 12,50 | Lact 1,8'},
        {'data': '2026-11-13', 'texto': 'Hb 12,3 | Ht 37,0% | Leuc 7.500 | Plaq 250.000'}]
    # Nada da referência entra ("Até 1,2", "2,0 a 3,0", "10-50 mg/L"), nem dado de identificação
    texto = str(lido['resumo'])
    assert '1,20' not in texto and '2,0' not in texto and 'Até' not in texto
    assert PACIENTE.lower() not in texto.lower() and 'resumo' not in lido['exames'][0]
    assert laudos.ler(_pdf(FORMATO_A), HOJE)['resumo'] == [{'data': '2026-09-23', 'texto': 'Gli 90'}]
    assert laudos.ler(_pdf(FORMATO_B), HOJE)['resumo'] == []          # sem valor reconhecível: nada é inventado


@pytest.mark.parametrize('resultado, esperado', [('1.25 mg/dL', 'Cr 1,25'), ('0.71 mg/dL', 'Cr 0,71'), ('0,71 mg/dL', 'Cr 0,71'),
                                                  ('2 mg/dL', 'Cr 2'), ('1.2.3', None), ('16/11/2026', None)])
def test_resumo_nunca_fica_com_um_pedaco_do_numero(resultado, esperado):
    paginas = [['CREATININA', '[DATA DA COLETA : 13/11/2026 08:06]', 'Material: Soro', f'RESULTADO: {resultado}']]
    resumo = laudos.ler(_pdf(paginas), HOJE)['resumo']
    assert resumo == ([{'data': '2026-11-13', 'texto': esperado}] if esperado else [])
    assert laudos._itens_do_resumo('Hemograma completo', ['Leucócitos Totais 9.200/mm³', 'Plaquetas 299.000 /mm³']) == [(0, 'Leuc 9.200 | Plaq 299.000')]
