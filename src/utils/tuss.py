"""Código TUSS (tabela 22, Procedimentos e Eventos em Saúde) de cada exame do Evidēns.

A guia SP/SADT do padrão TISS pede, para cada exame solicitado, a tabela (22),
o código de oito dígitos e a descrição da TUSS. Este arquivo liga cada título
de exame do motor e do catálogo ao(s) código(s) correspondente(s).

Como foi conferido: cada código abaixo foi localizado, com a descrição
correspondente, em tabelas TUSS publicadas por operadoras e órgãos públicos
(lista em `docs/guia-do-plano.md`). A tabela oficial vigente é a da ANS
(consulta pública de terminologias); operadoras podem usar código próprio para
alguns itens. Por isso a regra aqui é conservadora:

- exame sem código conferido NÃO recebe código inventado: fica em `SEM_CODIGO`,
  com o motivo, e sai na guia com o campo do código em branco;
- um título que reúne vários exames (por exemplo "TGO e TGP") vira uma linha
  por código;
- código "por lado" (unilateral, monocular) sai com quantidade 2;
- quando o código depende do sexo, a escolha é feita pelo sexo do paciente.

Um teste garante que todo título de laboratório e de imagem do motor e do
catálogo esteja em `CODIGOS` ou em `SEM_CODIGO`.
"""
import re
import unicodedata

TABELA = '22'

# Descrições da TUSS 22 usadas na guia (uma por código).
DESCRICOES = {
    # Bioquímica
    '40301150': 'Ácido úrico - pesquisa e/ou dosagem',
    '40301222': 'Albumina - pesquisa e/ou dosagem',
    '40301249': 'Alfa-1-antitripsina - pesquisa e/ou dosagem no soro',
    '40301362': 'Apolipoproteína B (Apo B) - pesquisa e/ou dosagem',
    '40301397': 'Bilirrubinas (direta, indireta e total) - pesquisa e/ou dosagem',
    '40301419': 'Cálcio iônico - pesquisa e/ou dosagem',
    '40301427': 'Capacidade de fixação de ferro - pesquisa e/ou dosagem',
    '40301559': 'Cloro - pesquisa e/ou dosagem',
    '40301583': 'Colesterol (HDL) - pesquisa e/ou dosagem',
    '40301591': 'Colesterol (LDL) - pesquisa e/ou dosagem',
    '40301605': 'Colesterol total - pesquisa e/ou dosagem',
    '40301630': 'Creatinina - pesquisa e/ou dosagem',
    '40301761': 'Eletroforese de proteínas',
    '40301842': 'Ferro sérico - pesquisa e/ou dosagem',
    '40301885': 'Fosfatase alcalina - pesquisa e/ou dosagem',
    '40301931': 'Fósforo - pesquisa e/ou dosagem',
    '40301990': 'Gama-glutamil transferase - pesquisa e/ou dosagem',
    '40302016': 'Gasometria (pH, pCO2, SA, O2, excesso base) - pesquisa e/ou dosagem',
    '40302040': 'Glicose - pesquisa e/ou dosagem',
    '40302113': 'Homocisteína - pesquisa e/ou dosagem',
    '40302210': 'Lipoproteína (a) - Lp (a) - pesquisa e/ou dosagem',
    '40302229': 'Lítio - pesquisa e/ou dosagem',
    '40302237': 'Magnésio - pesquisa e/ou dosagem',
    '40302318': 'Potássio - pesquisa e/ou dosagem',
    '40302423': 'Sódio - pesquisa e/ou dosagem',
    '40302504': 'Transaminase oxalacética (amino transferase aspartato) - pesquisa e/ou dosagem',
    '40302512': 'Transaminase pirúvica (amino transferase de alanina) - pesquisa e/ou dosagem',
    '40302547': 'Triglicerídeos - pesquisa e/ou dosagem',
    '40302580': 'Ureia - pesquisa e/ou dosagem',
    '40302709': 'Teste oral de tolerância à glicose - 2 dosagens',
    '40302733': 'Hemoglobina glicada (fração A1c) - pesquisa e/ou dosagem',
    '40302830': 'Vitamina "D" 25 hidroxi, pesquisa e/ou dosagem (vitamina D3)',
    # Fezes
    '40303110': 'Parasitológico - nas fezes',
    '40303128': 'Parasitológico, colheita múltipla com fornecimento do líquido conservante - nas fezes',
    '40303250': 'Sangue oculto nas fezes, pesquisa imunológica',
    # Hematologia
    '40304299': 'Grupo sanguíneo ABO, e fator Rho (inclui Du) - determinação',
    '40304361': 'Hemograma com contagem de plaquetas ou frações (eritrograma, leucograma, plaquetas)',
    '40304370': 'Hemossedimentação (VHS) - pesquisa e/ou dosagem',
    '40304590': 'Tempo de protrombina - determinação',
    '40304639': 'Tempo de tromboplastina parcial ativada - determinação',
    '40304884': 'Coombs indireto',
    # Endocrinologia
    '40305465': 'Paratormônio - PTH ou fração (cada) - pesquisa e/ou dosagem',
    '40305767': 'Hormônio gonadotrófico coriônico quantitativo (HCG-Beta-HCG) - pesquisa e/ou dosagem',
    '40316050': 'Aldosterona - pesquisa e/ou dosagem',
    '40316130': 'Antígeno específico prostático livre (PSA livre) - pesquisa e/ou dosagem',
    '40316149': 'Antígeno específico prostático total (PSA) - pesquisa e/ou dosagem',
    '40316165': 'Calcitonina - pesquisa e/ou dosagem',
    '40316246': 'Estradiol - pesquisa e/ou dosagem',
    '40316270': 'Ferritina - pesquisa e/ou dosagem',
    '40316289': 'Folículo estimulante, hormônio (FSH) - pesquisa e/ou dosagem',
    '40316335': 'Hormônio luteinizante (LH) - pesquisa e/ou dosagem',
    '40316360': 'Insulina - pesquisa e/ou dosagem',
    '40316416': 'Prolactina - pesquisa e/ou dosagem',
    '40316432': 'Renina - pesquisa e/ou dosagem',
    '40316491': 'T4 livre - pesquisa e/ou dosagem',
    '40316513': 'Testosterona total - pesquisa e/ou dosagem',
    '40316521': 'Tireoestimulante, hormônio (TSH) - pesquisa e/ou dosagem',
    '40316572': 'Vitamina B12 - pesquisa e/ou dosagem',
    # Imunologia
    '40306666': 'Citomegalovírus IgG - pesquisa e/ou dosagem',
    '40306674': 'Citomegalovírus IgM - pesquisa e/ou dosagem',
    '40306852': 'Fator antinúcleo (FAN) - pesquisa e/ou dosagem',
    '40306950': 'Hepatite B - HBcAc - IgG (anti-core IgG ou Acoreg) - pesquisa e/ou dosagem',
    '40306992': 'Hepatite B - HBsAc (anti-antígeno de superfície) - pesquisa e/ou dosagem',
    '40307018': 'Hepatite B - HBsAg (AU, antígeno Austrália) - pesquisa e/ou dosagem',
    '40307026': 'Hepatite C - anti-HCV - pesquisa e/ou dosagem',
    '40307182': 'HIV1 + HIV2 (determinação conjunta), pesquisa de anticorpos',
    '40307220': 'IgA - pesquisa e/ou dosagem',
    '40307433': 'Linfócitos T "helper", contagem de (IF com OKT-4) (CD-4+), citometria de fluxo',
    '40307638': 'PPD (tuberculina), IDeR',
    '40307697': 'Rubéola - IgG - pesquisa e/ou dosagem',
    '40307760': 'Sífilis - VDRL',
    '40307824': 'Toxoplasmose IgG - pesquisa e/ou dosagem',
    '40307832': 'Toxoplasmose IgM - pesquisa e/ou dosagem',
    '40308391': 'Proteína C reativa, quantitativa - pesquisa e/ou dosagem',
    '40308553': 'Anti-transglutaminase tecidual - IgA',
    # Microbiologia
    '40310124': 'Cultura bacteriana (em diversos materiais biológicos)',
    '40310213': 'Cultura, urina com contagem de colônias',
    '40310418': 'Antibiograma (teste de sensibilidade a antibióticos e quimioterápicos), por bactéria - não automatizado',
    # Urina
    '40311163': 'Metanefrinas urinárias - pesquisa e/ou dosagem',
    '40311171': 'Microalbuminúria',
    '40311210': 'Rotina de urina (caracteres físicos, elementos anormais e sedimentoscopia)',
    # Biologia molecular
    '40314120': 'HIV - carga viral PCR',
    '40314146': 'HIV, genotipagem',
    '40314154': 'HPV (vírus do papiloma humano) + subtipagem quando necessário, PCR',
    # Citopatologia
    '40601137': 'Procedimento diagnóstico em citopatologia cérvico-vaginal oncótica',
    # Métodos gráficos, endoscopia e provas funcionais
    '20102020': 'Holter de 24 horas - 3 canais - digital',
    '20102038': 'Monitorização ambulatorial da pressão arterial - MAPA (24 horas)',
    '40101010': 'ECG convencional de até 12 derivações',
    '40101045': 'Teste ergométrico convencional - 3 ou mais derivações simultâneas (inclui ECG basal convencional)',
    '40103072': 'Audiometria tonal limiar com testes de discriminação',
    '40103528': 'Polissonografia de noite inteira (PSG) (inclui polissonogramas)',
    '40105075': 'Prova de função pulmonar completa (ou espirometria)',
    '40201082': 'Colonoscopia (inclui a retossigmoidoscopia)',
    '40201120': 'Endoscopia digestiva alta',
    '41401115': 'Teste de caminhada de 6 minutos',
    # Radiologia e densitometria
    '40802035': 'RX - Coluna dorsal - 2 incidências',
    '40802051': 'RX - Coluna lombo-sacra - 3 incidências',
    '40805026': 'RX - Tórax - 2 incidências',
    '40808041': 'Mamografia digital bilateral',
    '40808130': 'Densitometria óssea - rotina: coluna e fêmur (ou dois segmentos)',
    # Ultrassonografia
    '40901106': 'Ecodopplercardiograma transtorácico',
    '40901114': 'US - Mamas',
    '40901122': 'US - Abdome total (abdome superior, rins, bexiga, aorta, veia cava inferior e adrenais)',
    '40901130': 'US - Abdome superior (fígado, vias biliares, vesícula, pâncreas e baço)',
    '40901157': 'US - Aparelho urinário feminino (rins, ureteres e bexiga)',
    '40901165': 'US - Aparelho urinário masculino (rins, ureteres, bexiga e próstata)',
    '40901173': 'US - Abdome inferior masculino (bexiga, próstata e vesículas seminais)',
    '40901203': 'US - Órgãos superficiais (tireoide ou escroto ou pênis ou crânio)',
    '40901238': 'US - Obstétrica',
    '40901246': 'US - Obstétrica convencional com Doppler colorido',
    '40901254': 'US - Obstétrica com translucência nucal',
    '40901262': 'US - Obstétrica morfológica',
    '40901297': 'US - Obstétrica 1º trimestre (endovaginal)',
    '40901300': 'US - Transvaginal (inclui abdome inferior feminino)',
    '40901360': 'Doppler colorido de vasos cervicais arteriais bilateral (carótidas e vertebrais)',
    '40901394': 'Doppler colorido de aorta e artérias renais',
    '40901408': 'Doppler colorido de aorta e ilíacas',
    '40901475': 'Doppler colorido arterial de membro inferior - unilateral',
    # Tomografia e ressonância
    '41001079': 'TC - Tórax',
    '41001087': 'TC - Coração - para avaliação do escore de cálcio coronariano',
    '41101014': 'RM - Crânio (encéfalo)',
    '41101162': 'RM - Mama (unilateral)',
    '41101324': 'Angio-RM (crânio ou pescoço ou tórax ou abdome superior ou pelve) - arterial ou venosa',
}

_URINARIO = {'feminino': '40901157', 'masculino': '40901165'}

# título → lista de códigos. Cada item é o código, ou (código, quantidade), ou {sexo: código}.
CODIGOS = {
    # ── Laboratório (motor)
    '25-hidroxivitamina D, soro': ['40302830'],
    'Alanina aminotransferase, soro': ['40302512'],
    'Albumina, soro': ['40301222'],
    'Alfa-1 antitripsina, soro': ['40301249'],
    'Anti-HCV IgG, soro': ['40307026'],
    'Anticorpos anti-HCV, soro': ['40307026'],
    'Anti-HCV': ['40307026'],
    'Anti-HIV 1 e 2, soro': ['40307182'],
    'Anti-HIV 1 e 2 (4ª geração)': ['40307182'],
    'HIV 1/2 (anticorpos e antígeno p24), soro': ['40307182'],
    'Anticorpo antitransglutaminase tecidual IgA, soro': ['40308553'],
    'Anticorpos anti-HBc total, soro': ['40306950'],
    'Anticorpos anti-HBs, soro': ['40306992'],
    'Antígeno HBs, soro': ['40307018'],
    'HBsAg, soro': ['40307018'],
    'HBsAg, anti-HBc total e anti-HBs': ['40307018', '40306950', '40306992'],
    'Aspartato aminotransferase, soro': ['40302504'],
    'Bilirrubinas totais e frações, soro': ['40301397'],
    'Calcitonina, soro': ['40316165'],
    'Carga Viral do HIV (HIV RNA)': ['40314120'],
    'Citologia cervicovaginal (Papanicolaou)': ['40601137'],
    'Citomegalovírus IgG e IgM, soro': ['40306666', '40306674'],
    'Citomegalovírus IgG e IgM': ['40306666', '40306674'],
    'Cloreto, soro': ['40301559'],
    'Colesterol total e frações, soro': ['40301605', '40301583', '40301591', '40302547'],
    'Contagem de linfócitos T CD4+': ['40307433'],
    'Coombs indireto, soro': ['40304884'],
    'Creatinina, soro': ['40301630'],
    'Cultura para estreptococo do grupo B (swab vaginal e retal)': ['40310124'],
    'Cálcio iônico, soro': ['40301419'],
    'EAS - Elementos Anormais e Sedimentoscopia': ['40311210'],
    'EAS - Elementos Anormais e Sedimentoscopia, urina': ['40311210'],
    'Urina tipo I (EAS)': ['40311210'],
    'Ferritina, soro': ['40316270'],
    'Fosfatase alcalina, soro': ['40301885'],
    'Fósforo, soro': ['40301931'],
    'Gasometria arterial, sangue arterial': ['40302016'],
    'Genotipagem do HIV (Teste de Resistência)': ['40314146'],
    'Glicemia de jejum, soro': ['40302040'],
    'Glicose, soro': ['40302040'],
    'Hemoglobina glicada (HbA1c), soro': ['40302733'],
    'Hemograma completo': ['40304361'],
    'Hemograma completo com plaquetas': ['40304361'],
    'Hemograma completo, sangue total': ['40304361'],
    'Hormônio Tireoestimulante (TSH), soro': ['40316521'],
    'TSH, soro': ['40316521'],
    'Imunoglobulina A (IgA), soro': ['40307220'],
    'Lipoproteína(a) - Lp(a), soro': ['40302210'],
    'Lítio, soro': ['40302229'],
    'Magnésio, soro': ['40302237'],
    'Metanefrinas, plasma ou urina de 24h': ['40311163'],
    'Parasitológico de fezes': ['40303110'],
    'Parasitológico de fezes (3 amostras)': ['40303128'],
    'Paratormônio (PTH), soro': ['40305465'],
    'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular': ['40314154'],
    'Potássio, soro': ['40302318'],
    'Prolactina, soro': ['40316416'],
    'Prova tuberculínica (PPD) ou IGRA': ['40307638'],
    'PSA total, soro': ['40316149'],
    'PSA total e livre, soro': ['40316149', '40316130'],
    'Razão albumina/creatinina, urina': ['40311171'],
    'Relação albumina/creatinina urinária (uACR)': ['40311171'],
    'Relação Aldosterona/Renina (A/R)': ['40316050', '40316432'],
    'Rubéola IgG, soro': ['40307697'],
    'Rubéola IgG': ['40307697'],
    'Sífilis: teste treponêmico ou VDRL, soro': ['40307760'],
    'VDRL, soro': ['40307760'],
    'VDRL / teste treponêmico': ['40307760'],
    'Sódio, soro': ['40302423'],
    'Tempo de protrombina (TP/INR), plasma': ['40304590'],
    'Coagulograma (TP/INR e TTPa)': ['40304590', '40304639'],
    'TGO e TGP, soro': ['40302504', '40302512'],
    'TGO (AST) e TGP (ALT), soro': ['40302504', '40302512'],
    'Tipagem sanguínea ABO e fator Rh': ['40304299'],
    'TOTG-75g (Teste Oral de Tolerância à Glicose), soro': ['40302709'],
    'Toxoplasmose IgG e IgM, soro': ['40307824', '40307832'],
    'Toxoplasmose IgG e IgM': ['40307824', '40307832'],
    'Ureia, soro': ['40302580'],
    'Urocultura com antibiograma': ['40310213', '40310418'],
    'Vitamina B12, soro': ['40316572'],
    'Ácido úrico, soro': ['40301150'],
    'Índice de saturação de transferrina, soro': ['40301842', '40301427'],
    # ── Laboratório (catálogo)
    'T4 livre, soro': ['40316491'],
    'Ferro sérico e saturação de transferrina': ['40301842', '40301427'],
    'Sódio e potássio, soro': ['40302423', '40302318'],
    'Gama-GT, soro': ['40301990'],
    'Proteína C reativa ultrassensível, soro': ['40308391'],
    'VHS': ['40304370'],
    'Insulina de jejum, soro': ['40316360'],
    'Apolipoproteína B, soro': ['40301362'],
    'Homocisteína, soro': ['40302113'],
    'Sangue oculto nas fezes (FIT)': ['40303250'],
    'Testosterona total, soro': ['40316513'],
    'FSH e LH, soro': ['40316289', '40316335'],
    'Estradiol, soro': ['40316246'],
    'Beta-hCG, soro': ['40305767'],
    'Eletroforese de proteínas, soro': ['40301761'],
    'FAN (fator antinuclear)': ['40306852'],
    # ── Imagem e métodos (motor)
    'Angiorressonância de crânio': ['41101324'],
    'Colonoscopia de Rastreio com ou sem biópsia': ['40201082'],
    'Colonoscopia': ['40201082'],
    'Densitometria óssea (DEXA)': ['40808130'],
    'Densitometria óssea (coluna lombar e fêmur)': ['40808130'],
    'Doppler de artérias renais': ['40901394'],
    'Ecocardiograma transtorácico': ['40901106'],
    'Eletrocardiograma de repouso': ['40101010'],
    'Endoscopia digestiva alta': ['40201120'],
    'Espirometria, com broncodilatador': ['40105075'],
    'Mamografia Digital - Bilateral': ['40808041'],
    'Mamografia bilateral': ['40808041'],
    'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)': ['20102038'],
    'MAPA de 24 horas': ['20102038'],
    'Polissonografia': ['40103528'],
    'Radiografia de coluna torácica e lombar (perfil)': ['40802035', '40802051'],
    'Radiografia de tórax': ['40805026'],
    'Radiografia de tórax (PA e perfil)': ['40805026'],
    'Ressonância magnética de crânio': ['41101014'],
    'Ressonância magnética de mamas': [('41101162', 2)],
    'Teste de caminhada de 6 minutos': ['41401115'],
    'Tomografia computadorizada de tórax de baixa dose (LDCT)': ['41001079'],
    'Tomografia de tórax de baixa dose': ['41001079'],
    'Ultrassonografia com Doppler de Aorta Abdominal': ['40901408'],
    'Ultrassonografia de abdome superior': ['40901130'],
    'Ultrassonografia de abdome total': ['40901122'],
    'Ultrassonografia de rins e vias urinárias': [_URINARIO],
    'Ultrassonografia de vias urinárias': [_URINARIO],
    'Ultrassonografia de tireoide': ['40901203'],
    'Ultrassonografia de mamas': ['40901114'],
    'Ultrassonografia morfológica de 1º trimestre (translucência nucal)': ['40901254'],
    'Ultrassonografia morfológica de 2º trimestre': ['40901262'],
    'Ultrassonografia morfológica (20–24 semanas)': ['40901262'],
    'Ultrassonografia obstétrica': ['40901238'],
    'Ultrassonografia obstétrica com Doppler': ['40901246'],
    'Ultrassonografia obstétrica transvaginal': ['40901297'],
    'Ultrassonografia transvaginal para medida do colo uterino': ['40901300'],
    'Ultrassonografia pélvica transvaginal': ['40901300'],
    'Ultrassonografia de próstata (via abdominal)': ['40901173'],
    'Doppler de carótidas e vertebrais': ['40901360'],
    'Doppler arterial de membros inferiores': [('40901475', 2)],
    'Teste ergométrico': ['40101045'],
    'Holter de 24 horas': ['20102020'],
    'Escore de cálcio coronariano (TC)': ['41001087'],
    'Audiometria tonal': ['40103072'],
}

# Exames que saem na guia sem código, com o motivo (nada de código inventado).
SEM_CODIGO = {
    'Clamídia e gonococo, PCR (urina ou swab)':
        'são dois testes moleculares; só o de clamídia tem código conferido (40314243)',
    'Relação proteína/creatinina, urina':
        'sem código específico conferido; operadoras usam "componente urinário" (40311180) ou tabela própria',
    'TOTG-75g gestacional (jejum, 1 h e 2 h), soro':
        'são 3 dosagens; a TUSS conferida traz o teste com 2 dosagens (40302709) e a curva de 4 (40301680)',
    'Ácido fólico, soro':
        'a TUSS conferida só traz a dosagem nos eritrócitos (40301087)',
    'Fator reumatoide e anti-CCP':
        'o código do anti-CCP não foi conferido',
    'Avaliação oftalmológica com tonometria e fundoscopia':
        'é consulta com o oftalmologista, não exame com código próprio',
    'Avaliação oftalmológica (fundo de olho)':
        'é consulta com o oftalmologista, não exame com código próprio',
    'Fundoscopia (Exame de fundo de olho)':
        'é consulta com o oftalmologista, não exame com código próprio',
    'Ressonância magnética de corpo inteiro':
        'sem código conferido na TUSS',
    'Angiotomografia de coronárias':
        'código não conferido',
}


def _chave(titulo):
    s = unicodedata.normalize('NFD', str(titulo or '').strip().lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s)


_POR_CHAVE = {_chave(t): v for t, v in CODIGOS.items()}


def linhas_da_guia(titulo, sexo=None):
    """Linhas da guia para um exame: [{'codigo', 'descricao', 'quantidade'}].

    Exame sem código conferido (ou digitado à mão pelo médico) devolve uma linha
    com o código vazio e o próprio título como descrição.
    """
    itens = _POR_CHAVE.get(_chave(titulo))
    if not itens:
        return [{'codigo': '', 'descricao': str(titulo or '').strip(), 'quantidade': 1}]
    linhas = []
    for item in itens:
        quantidade = 1
        if isinstance(item, tuple):
            item, quantidade = item
        if isinstance(item, dict):
            item = item.get(sexo if sexo in item else None)
            if not item:
                return [{'codigo': '', 'descricao': str(titulo or '').strip(), 'quantidade': 1}]
        linhas.append({'codigo': item, 'descricao': DESCRICOES[item], 'quantidade': quantidade})
    return linhas
