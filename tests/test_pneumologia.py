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


def test_hipertensao_arterial_pulmonar_conta_como_risco_para_a_vsr_de_60_a_69_anos():
    """A regra da SBIm que o motor já aplica dá a VSR de 60 a 69 anos a quem tem cardiopatia ou pneumopatia. Sem a
    doença na lista de risco, o sistema dizia "sem fator de risco nas listas" (achado de revisão do PR #196)."""
    recs, orient = _rodar([HAP], idade=63)
    assert recs[condicoes.VSR]['subtitulo'].startswith('60-69 anos com fator de risco')
    assert 'VSR de 60 a 69 anos: só com fator de risco' not in orient
    # Sem a doença, a orientação continua valendo
    recs, orient = _rodar([], idade=63)
    assert condicoes.VSR not in recs and 'VSR de 60 a 69 anos: só com fator de risco' in orient


def test_bronquiectasias_painel_da_avaliacao_inicial():
    """ERS 2025, recomendação 1 (forte; certeza moderada): testagem padronizada. O painel é o que o resumo dos autores
    da diretriz (Mosgrove 2026, p. 2 e Tabela 1) manda fazer em todo paciente com bronquiectasias confirmadas."""
    from src.utils import tuss
    # A diretriz trata do adulto, fora da fibrose cística: o rótulo diz isso
    assert condicoes.COMORBIDADES['bronquiectasias']['rotulo'] == 'Bronquiectasias (adulto, sem fibrose cística)'
    recs, orient = _rodar(['bronquiectasias'], idade=55)
    painel = {'Hemograma completo com plaquetas', 'Imunoglobulina G (IgG), soro', 'Imunoglobulina A (IgA), soro',
              'Imunoglobulina M (IgM), soro', 'Eletroforese de proteínas, soro', 'Imunoglobulina E (IgE) total, soro',
              'IgE específica para Aspergillus, soro', 'IgG específica para Aspergillus, soro',
              'Cultura de escarro (bactérias)', 'Cultura para micobactérias, escarro'}
    assert set(recs) == painel
    for titulo in painel:
        rec = recs[titulo]
        assert rec['subtitulo'] == 'Bronquiectasias | Avaliação inicial' and rec['grau_evidencia'] == 'A', titulo
        assert rec['categoria'] == 'laboratorio' and 'todo paciente com o diagnóstico confirmado' in rec['descricao']
        links = reference_links.build_reference_links(titulo, rec['referencia'])
        assert [l['url'] for l in links] == ['https://doi.org/10.1183/13993003.01126-2025',
                                             'https://doi.org/10.1038/s41533-026-00528-z'], titulo
        # Todo exame do painel tem código TUSS conferido ou a explicação de por que não tem
        assert tuss.CODIGOS.get(titulo) or titulo in tuss.SEM_CODIGO, titulo
    assert tuss.CODIGOS['Imunoglobulina M (IgM), soro'] == ['40307301']
    assert tuss.CODIGOS['Imunoglobulina E (IgE) total, soro'] == ['40307271']
    assert tuss.CODIGOS['Cultura para micobactérias, escarro'] == ['40310159']
    assert 'IgG específica para Aspergillus, soro' in tuss.SEM_CODIGO


def test_bronquiectasias_o_que_fica_so_na_orientacao():
    """O resumo não fixa intervalo de consulta, de cultura nem de espirometria no paciente estável e não trata de
    vacinas: nada disso vira pedido. Escarro na exacerbação e antes de macrolídeo prolongado fica como orientação."""
    recs, orient = _rodar(['bronquiectasias'], idade=55)
    escarro = orient['Bronquiectasias: escarro no seguimento']['descricao']
    assert 'exacerbação' in escarro and 'macrolídeo' in escarro and 'Pseudomonas' in escarro
    # Conferido contra a fonte por revisor independente: os qualificadores da diretriz ficam no texto
    for trecho in ('de preferência antes do antibiótico', 'que não melhoram com antibiótico',
                   'repetir a cultura e discutir de imediato com o especialista', 'recomendação condicional',
                   'a cultura positiva isolada não é motivo para antibiótico'):
        assert trecho in escarro, trecho
    resto = orient['Bronquiectasias: o que não vira pedido automático']['descricao']
    for trecho in ('espirometria', 'não fixa intervalo', 'vacinas', 'discinesia ciliar', 'risco cardiovascular',
                   'quando os exames iniciais são negativos', 'doença de via aérea associada', 'não relacionadas à fibrose cística'):
        assert trecho in resto, trecho
    assert not any('Espirometria' in t or 'Tomografia' in t or 'Alfa-1' in t for t in recs)
    assert not any(r['categoria'] == 'vacina' for r in recs.values())
    assert not _rodar([], idade=55)[1].get('Bronquiectasias: escarro no seguimento')


def test_cultura_de_escarro_nao_se_funde_com_outra_cultura_do_mesmo_codigo():
    """"Cultura bacteriana" (40310124) e "IgE, por alérgeno" (40307263) são códigos da TUSS que servem a vários exames.
    Na gestante de 36 semanas com bronquiectasias, a cultura de escarro e a do estreptococo do grupo B são dois exames
    (achado do revisor independente: a de escarro sumia). Na guia, a quantidade soma."""
    import io
    from pypdf import PdfReader
    from src.routes.checkup_intelligent import deduplicar_recomendacoes
    from src.utils import pdf_minutas, tuss
    assert tuss.CODIGOS_DE_VARIOS_EXAMES == {'40307263', '40310124'}
    gbs = next(t for t, c in tuss.CODIGOS.items() if c == ['40310124'] and 'estreptococo' in t)
    recs = [{'titulo': gbs, 'categoria': 'laboratorio', 'subtitulo': 'Gestante | 36-37 semanas', 'referencia': 'ACOG',
             'descricao': 'x', 'prioridade': 'alta', 'grau_evidencia': 'A'},
            {'titulo': 'Cultura de escarro (bactérias)', 'categoria': 'laboratorio', 'descricao': 'y', 'prioridade': 'media',
             'subtitulo': 'Bronquiectasias | Avaliação inicial', 'referencia': condicoes.ERS_BRONQUIECTASIAS, 'grau_evidencia': 'A'}]
    titulos = [r['titulo'] for r in deduplicar_recomendacoes(recs, 'feminino')]
    assert titulos == [gbs, 'Cultura de escarro (bactérias)']
    # O mesmo exame pedido duas vezes continua virando um item só
    assert len(deduplicar_recomendacoes([dict(recs[1]), dict(recs[1])], 'feminino')) == 1
    # Exames de código único continuam se unindo pelo código
    par = [{'titulo': 'Hemograma completo com plaquetas', 'categoria': 'laboratorio', 'subtitulo': 'a', 'referencia': 'r',
            'descricao': 'x', 'prioridade': 'media'},
           {'titulo': 'Hemograma completo, sangue total', 'categoria': 'laboratorio', 'subtitulo': 'b', 'referencia': 'r',
            'descricao': 'x', 'prioridade': 'media'}]
    assert len(deduplicar_recomendacoes(par, 'feminino')) == 1


def test_cultura_de_estreptococo_nao_poe_a_cultura_de_escarro_em_dia():
    """Achado da revisão do PR #198: as duas culturas dividem o código 40310124 e são exames diferentes."""
    from datetime import date, timedelta
    from src.utils import periodicidade
    hoje = date(2026, 11, 19)
    rec = {'titulo': 'Cultura de escarro (bactérias)', 'categoria': 'laboratorio',
           'subtitulo': 'Bronquiectasias | Avaliação inicial'}
    outra = next(t for t in periodicidade.exames_conhecidos() if 'strepto' in t.lower() or 'estreptococo' in t.lower())
    assert periodicidade.chaves(outra) == periodicidade.chaves(rec['titulo'])
    mantidas, em_dia = periodicidade.aplicar([rec], [{'exame': outra, 'data': hoje - timedelta(days=1)}], hoje_=hoje)
    assert [r['titulo'] for r in mantidas] == [rec['titulo']] and not em_dia
    mantidas, em_dia = periodicidade.aplicar([rec], [{'exame': rec['titulo'], 'data': hoje - timedelta(days=1)}], hoje_=hoje)
    assert not mantidas and len(em_dia) == 1
    assert rec['titulo'] in periodicidade.exames_conhecidos()
