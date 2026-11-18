"""Endocrinologia nas "Outras comorbidades": nódulo de tireoide (ATA 2015), hiperparatireoidismo primário (5º Workshop
Internacional, 2022), incidentaloma adrenal (ESE/ENSAT 2023), hipogonadismo masculino (Endocrine Society 2018) e
hiperprolactinemia (Endocrine Society 2011 e Pituitary Society 2023). Sociedades aprovadas pelo responsável clínico
em 18/11/2026. Cada exame sai com a diretriz, o grau e o momento em que ela o pede."""
import pytest

from src.utils import condicoes, reference_links, sigtap, tuss

NOVAS = ('nodulo_tireoide', 'hiperparatireoidismo_primario', 'incidentaloma_adrenal', 'hipogonadismo_masculino',
         'hiperprolactinemia')


def _rodar(comorbidades, idade=45, sexo='feminino', medicacoes=(), **extra):
    recs = []
    orient = condicoes.aplicar(recs, idade, sexo, comorbidades, list(medicacoes), [], **extra)
    return {r['titulo']: r for r in recs}, {o['titulo']: o for o in orient}


def _item(recs, titulo, subtitulo, referencia, grau):
    rec = recs[titulo]
    assert rec['subtitulo'] == subtitulo, (titulo, rec['subtitulo'])
    assert referencia in rec['referencia'], (titulo, rec['referencia'])
    assert rec['grau_evidencia'] == grau, (titulo, rec['grau_evidencia'])


@pytest.mark.parametrize('chave', NOVAS)
def test_condicao_esta_na_lista_e_a_referencia_tem_link(chave):
    assert chave in condicoes.COMORBIDADES
    recs, orient = _rodar([chave], sexo='masculino' if chave == 'hipogonadismo_masculino' else 'feminino')
    assert recs or orient
    for item in list(recs.values()) + list(orient.values()):
        links = reference_links.build_reference_links(item['titulo'], item['referencia'])
        assert len(links) == len(item['referencia'].split(' / ')), item['referencia']
        for link in links:
            assert link['url'].startswith('https://doi.org/'), link


def test_nodulo_de_tireoide():
    recs, orient = _rodar(['nodulo_tireoide'])
    assert set(recs) == {'Hormônio Tireoestimulante (TSH), soro', 'Ultrassonografia de tireoide'}
    _item(recs, 'Hormônio Tireoestimulante (TSH), soro', 'Nódulo de tireoide | Avaliação inicial', 'ATA 2015', 'B')
    _item(recs, 'Ultrassonografia de tireoide', 'Nódulo de tireoide | Conforme o padrão ultrassonográfico', 'ATA 2015', 'B')
    assert 'linfonodos cervicais' in recs['Ultrassonografia de tireoide']['descricao']
    # O que a diretriz não recomenda de rotina fica nas orientações, sem pedido
    aviso = orient['Nódulo de tireoide: o que a ATA não recomenda de rotina']['descricao']
    assert 'tireoglobulina' in aviso and 'calcitonina' in aviso
    assert not any('ireoglobulina' in t or 'alcitonina' in t for t in recs)


def test_hiperparatireoidismo_primario():
    recs, _ = _rodar(['hiperparatireoidismo_primario'], idade=62)
    inicial, ref = 'Hiperparatireoidismo primário | Avaliação inicial', 'Workshop Internacional 2022'
    for titulo in ('Paratormônio (PTH), soro', 'Fósforo, soro', 'Calciúria de 24 horas',
                   'Radiografia de coluna torácica e lombar (perfil)', 'Ultrassonografia de rins e vias urinárias'):
        _item(recs, titulo, inicial, ref, 'E')
    for titulo in ('Cálcio iônico, soro', '25-hidroxivitamina D, soro', 'Creatinina, soro'):
        _item(recs, titulo, 'Hiperparatireoidismo primário | Anual', ref, 'E')
    _item(recs, 'Densitometria óssea (DEXA)', 'Hiperparatireoidismo primário | A cada 1-2 anos', ref, 'E')
    assert 'terço distal do rádio' in recs['Densitometria óssea (DEXA)']['descricao']
    # Regra da casa: o cálcio pedido é sempre o iônico
    assert not any(t.startswith('Cálcio total') for t in recs)


def test_incidentaloma_adrenal():
    recs, orient = _rodar(['incidentaloma_adrenal'], idade=58, sexo='masculino')
    assert set(recs) == {'Cortisol após 1 mg de dexametasona, soro'}
    _item(recs, 'Cortisol após 1 mg de dexametasona, soro', 'Incidentaloma adrenal | Avaliação inicial', 'ESE/ENSAT 2023', 'B')
    texto = orient['Incidentaloma adrenal: metanefrinas, imagem e seguimento']['descricao']
    assert 'metanefrinas' in texto and '10 UH' in texto and 'relação aldosterona/renina' in texto
    # Com hipertensão, a relação aldosterona/renina vira pedido e sai da frase final da orientação
    recs, orient = _rodar(['incidentaloma_adrenal'], idade=58, sexo='masculino', hipertensao=True)
    _item(recs, 'Relação Aldosterona/Renina (A/R)', 'Incidentaloma adrenal com HAS | Avaliação inicial', 'ESE/ENSAT 2023', 'C')
    assert 'pedir a relação aldosterona/renina' not in orient['Incidentaloma adrenal: metanefrinas, imagem e seguimento']['descricao']


def test_hipogonadismo_masculino():
    recs, orient = _rodar(['hipogonadismo_masculino'], idade=52, sexo='masculino')
    _item(recs, 'FSH e LH, soro', 'Hipogonadismo masculino | Avaliação inicial', 'Endocrine Society 2018', 'B')
    _item(recs, 'Testosterona total, soro', 'Hipogonadismo masculino | Para confirmar o diagnóstico', 'Endocrine Society 2018', 'B')
    assert 'duas dosagens' in recs['Testosterona total, soro']['descricao']
    assert 'hematócrito' in orient['Hipogonadismo masculino: seguimento da reposição de testosterona']['descricao']
    # Só em homens
    recs, orient = _rodar(['hipogonadismo_masculino'], idade=52, sexo='feminino')
    assert 'FSH e LH, soro' not in recs and not any('Hipogonadismo' in t for t in orient)
    # Em reposição, a testosterona é pedida pela regra da medicação, não para confirmar o diagnóstico
    recs, _ = _rodar(['hipogonadismo_masculino'], idade=52, sexo='masculino', medicacoes=['testosterona'])
    assert recs.get('Testosterona total, soro', {}).get('subtitulo') != 'Hipogonadismo masculino | Para confirmar o diagnóstico'


def test_hiperprolactinemia():
    recs, orient = _rodar(['hiperprolactinemia'], idade=34)
    inicial = 'Hiperprolactinemia | Avaliação inicial'
    for titulo in ('Hormônio Tireoestimulante (TSH), soro', 'Creatinina, soro'):
        _item(recs, titulo, inicial, 'Endocrine Society 2011', 'A')
    _item(recs, 'Beta-hCG, soro', inicial, 'Pituitary Society 2023', 'E')
    _item(recs, 'Ressonância magnética de sela túrcica', inicial, 'Endocrine Society 2011', 'A')
    assert 'Pituitary Society 2023' in recs['Ressonância magnética de sela túrcica']['referencia']
    _item(recs, 'Prolactina, soro', 'Hiperprolactinemia | Conforme o tratamento', 'Endocrine Society 2011', 'E')
    assert set(recs) == {'Hormônio Tireoestimulante (TSH), soro', 'Creatinina, soro', 'Beta-hCG, soro',
                         'Ressonância magnética de sela túrcica', 'Prolactina, soro'}
    # Beta-hCG só em quem pode engravidar e ainda não está grávida
    assert 'Beta-hCG, soro' not in _rodar(['hiperprolactinemia'], idade=34, sexo='masculino')[0]
    assert 'Beta-hCG, soro' not in _rodar(['hiperprolactinemia'], idade=58)[0]
    assert 'Beta-hCG, soro' not in _rodar(['hiperprolactinemia'], idade=30, gestante=True)[0]
    # Onde as duas sociedades divergem, a orientação avisa (regra do responsável clínico)
    confirmar = orient['Hiperprolactinemia: confirmar a prolactina alta']['descricao']
    assert confirmar.startswith('Aviso de divergência') and '5 vezes o limite superior' in confirmar
    seguimento = orient['Hiperprolactinemia: hipófise, osso e seguimento']['descricao']
    assert 'Aviso de divergência sobre o ecocardiograma' in seguimento and 'IGF-1' in seguimento
    # Ecocardiograma e IGF-1 não viram pedido: a indicação depende da dose e do caso
    assert not any('cocardiograma' in t or 'IGF' in t for t in recs)


def test_ressonancia_de_sela_tem_codigo_e_vai_em_apac():
    assert tuss.CODIGOS['Ressonância magnética de sela túrcica'] == ['41101022']
    assert sigtap.vai_em_apac('Ressonância magnética de sela túrcica')
