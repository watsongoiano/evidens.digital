"""Pneumologia nas "Outras comorbidades". Sociedades aprovadas pelo responsável clínico em 18/11/2026.
Hipertensão arterial pulmonar: ESC/ERS 2022, texto integral lido (Tabela 17 e notas; Recommendation Tables 4 e 5;
seções 6.3.1.6 e 6.3.1.7). Classe I sai como grau A; o que a diretriz só sugere em tabela, sem classe, sai como E."""
from src.utils import condicoes, reference_links

HAP = 'hipertensao_arterial_pulmonar'


def _rodar(comorbidades, idade=45, sexo='feminino', **extra):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, comorbidades, [], [], **extra)
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


def test_hipertensao_arterial_pulmonar_seguimento():
    assert condicoes.COMORBIDADES[HAP]['rotulo'] == 'Hipertensão arterial pulmonar (grupo 1)'
    recs, orient = _rodar([HAP], idade=44)
    # Risco em quatro estratos no seguimento: classe funcional, teste de caminhada e BNP/NT-proBNP (classe I, nível B)
    for titulo in ('Peptídeo natriurético BNP/PROBNP', 'Teste de caminhada de 6 minutos'):
        assert recs[titulo]['subtitulo'] == 'Hipertensão arterial pulmonar | A cada 3-6 meses'
        assert recs[titulo]['grau_evidencia'] == 'A' and 'quatro níveis' in recs[titulo]['descricao']
    # Gravidade por painel de dados, que inclui o ecocardiograma (classe I, nível B)
    eco = recs['Ecocardiograma transtorácico']
    assert eco['subtitulo'] == 'Hipertensão arterial pulmonar | Conforme a evolução' and eco['grau_evidencia'] == 'A'
    # Exames básicos da Tabela 17 (nota b): sugeridos, sem classe de recomendação
    for titulo in ('Hemograma completo com plaquetas', 'Creatinina, soro', 'Sódio e potássio, soro',
                   'Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro',
                   'Bilirrubinas totais e frações, soro'):
        assert recs[titulo]['subtitulo'] == 'Hipertensão arterial pulmonar | A cada 3-6 meses', titulo
        assert recs[titulo]['grau_evidencia'] == 'E', titulo
    # Ferro: monitorização regular, sem intervalo na diretriz; critério de deficiência no texto
    for titulo in ('Ferritina, soro', 'Ferro sérico e saturação de transferrina'):
        assert recs[titulo]['subtitulo'] == 'Hipertensão arterial pulmonar | Periódico' and recs[titulo]['grau_evidencia'] == 'E'
        assert 'abaixo de 100 µg/L' in recs[titulo]['descricao'] and 'abaixo de 20%' in recs[titulo]['descricao']
    for rec in recs.values():
        links = reference_links.build_reference_links(rec['titulo'], rec['referencia'])
        assert links and all(l['url'].startswith('https://') for l in links), rec['titulo']
    assert all('ESC/ERS 2022' in r['referencia'] for r in recs.values())
    texto = orient['Hipertensão arterial pulmonar: seguimento e vacinas']['descricao']
    for trecho in ('centro de referência', 'gasometria', 'cateterismo direito', 'TSH', 'influenza, pneumocócica e COVID-19'):
        assert trecho in texto, trecho
    # TSH, troponina e ácido úrico são "conforme o quadro": ficam na orientação, não no pedido
    assert not any('TSH' in t or 'Troponina' in t or 'úrico' in t for t in recs)


def test_hipertensao_arterial_pulmonar_vacina_pneumococica_antes_dos_50():
    """Vacinas contra pneumococo, influenza e COVID-19: classe I, nível C. Antes dos 50 anos a pneumocócica não
    está no calendário de rotina, então entra pela doença."""
    recs, _ = _rodar([HAP], idade=44)
    vpc = recs[condicoes.PNEUMO]
    assert vpc['subtitulo'] == 'Hipertensão arterial pulmonar | Dose única' and vpc['grau_evidencia'] == 'A'
    assert 'ESC/ERS 2022' in vpc['referencia']
    assert condicoes.PNEUMO not in _rodar([HAP], idade=63)[0]     # a partir dos 50 vem do calendário por idade
    assert condicoes.PNEUMO not in _rodar([], idade=44)[0]


def test_sem_a_condicao_nada_muda():
    recs, orient = _rodar([], idade=44)
    assert 'Teste de caminhada de 6 minutos' not in recs and not any('Hipertensão arterial pulmonar' in t for t in orient)
