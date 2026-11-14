"""Acompanhamento laboratorial da pessoa vivendo com HIV ou aids (PVHA).

Fontes (lidas para estas regras)
- MS 2024: PCDT para Manejo da Infecção pelo HIV em Adultos, Módulo 1 (Tratamento). Quadro 2 (exames
  da abordagem inicial), seção 3.5.1 (prova tuberculínica/IGRA só com CD4 acima de 350), seção 3.6
  (LF-CrAg com CD4 abaixo de 200), Quadro 4 (genotipagem pré-tratamento), Quadros 7 a 10 (consultas,
  CD4, carga viral e exames do seguimento, p. 49-53), seção 9.3 (genotipagem na falha) e Quadro 11.
- HIVMA/IDSA 2024: Primary Care Guidance for Providers of Care for Persons With HIV (Clin Infect Dis,
  doi 10.1093/cid/ciae479). Tabela 4 (exames iniciais) e Tabela 5 (manutenção).

Regra de escolha: o PCDT do MS é a base (é o protocolo do SUS e o que os planos seguem); a HIVMA/IDSA
entra com o que o PCDT não cobre (eletrólitos, teste de gravidez antes da TARV, clamídia/gonococo,
tricomonas, rastreio anal). Onde as duas divergem, vale o MS e a descrição diz o que a HIVMA faria.
O colo do útero fica em src/utils/colo_utero.py (MS 2025: DNA-HPV a cada 3 anos com HIV).
"""

MS = 'MS 2024 (PCDT HIV)'
HIVMA = 'HIVMA/IDSA 2024'
AMBOS = f'{MS} / {HIVMA}'

CV_GENOTIPAGEM = 500          # MS: falha confirmada com a última carga viral > 500 cópias/mL
CD4_TB = 350                  # MS: PT/IGRA só acima de 350; abaixo, avaliar TPT sem teste
CD4_CRIPTOCOCO = 200          # MS: LF-CrAg abaixo de 200 (HIVMA: abaixo de 100)
IDADE_FERTIL_FIM = 50         # "potencial de engravidar": aproximação pela idade

GRUPO = 'HIV+'


def _rec(titulo, descricao, subtitulo, referencia, grau='A', categoria='laboratorio', prioridade='alta'):
    return {'titulo': titulo, 'descricao': descricao, 'subtitulo': subtitulo, 'categoria': categoria,
            'prioridade': prioridade, 'referencia': referencia, 'grau_evidencia': grau}


def _inteiro(valor):
    try:
        return int(str(valor).strip()) if valor is not None and str(valor).strip() else None
    except (TypeError, ValueError):
        return None


SEM_RESULTADO = 'Avaliação inicial'


def _frequencia_cd4(cd4, em_tarv, suprimido):
    """MS 2024, Quadro 8. Sem CD4 anterior, pedir agora: o resultado define o resto."""
    if cd4 is None:
        return SEM_RESULTADO
    if not em_tarv or not suprimido:
        return 'A cada 6 meses'
    if cd4 < 350:
        return 'A cada 6 meses'
    if cd4 <= 500:
        return 'Anual'
    return 'Não solicitar se >500 em 2 exames consecutivos com intervalo de 6 meses'


def _frequencia_cv(carga_viral, em_tarv, suprimido):
    """MS 2024, Quadro 9."""
    if carga_viral is None:
        return SEM_RESULTADO
    if not em_tarv:
        return 'Antes de iniciar a TARV'
    if suprimido:
        return 'A cada 6 meses'
    return 'Após 8 semanas do início ou mudança de TARV'


def recomendar(idade, sexo, cd4=None, carga_viral=None, em_tarv=False, supressao_viral=False,
               gestante=False, tenofovir=False, risco_renal=False):
    """Devolve (recomendações, orientações) para uma PVHA adulta."""
    cd4, carga_viral = _inteiro(cd4), _inteiro(carga_viral)
    suprimido = bool(em_tarv and (supressao_viral or carga_viral == 0))
    recs, orient = [], []
    add = recs.append

    # ---- Exames do HIV (MS 2024, Quadros 8 e 9) ----
    add(_rec('Contagem de linfócitos T CD4+',
             (f'CD4 atual: {cd4} células/mm³. ' if cd4 is not None else 'Sem CD4 anterior: pedir agora. ') + 'Em TARV, assintomático e com carga viral '
             'indetectável: abaixo de 350 a cada 6 meses; 350-500 anual; acima de 500 em 2 exames com 6 meses de intervalo, '
             'não é mais necessário. Sem TARV, evento clínico ou falha virológica: a cada 6 meses. Em profilaxia ou com '
             'infecção oportunista: a cada 3 meses.',
             f'{GRUPO} | {_frequencia_cd4(cd4, em_tarv, suprimido)}', MS))
    add(_rec('Carga Viral do HIV (HIV RNA)',
             (f'Carga viral atual: {carga_viral} cópias/mL. ' if carga_viral is not None else 'Sem carga viral anterior: pedir agora. ') + 'Supressão viral com '
             'estabilidade clínica e imunológica: a cada 6 meses. Início ou troca da TARV: 8 semanas depois. Carga viral '
             'detectável: repetir em 4 semanas para confirmar a falha.',
             f'{GRUPO} | {_frequencia_cv(carga_viral, em_tarv, suprimido)}', MS))

    # Genotipagem: na falha confirmada (MS 9.3) ou, antes da TARV, só nas indicações do Quadro 4.
    if em_tarv and carga_viral is not None and carga_viral > CV_GENOTIPAGEM:
        add(_rec('Genotipagem do HIV (Teste de Resistência)',
                 'Falha virológica confirmada (duas cargas virais detectáveis, a última acima de 500 cópias/mL): pedir a '
                 'genotipagem o quanto antes. Abaixo de 500 cópias/mL o teste não é liberado no SUS.',
                 f'{GRUPO} em TARV com carga viral >500 | Avaliação inicial ou falha virológica', MS))
    elif not em_tarv and gestante:
        add(_rec('Genotipagem do HIV (Teste de Resistência)',
                 'Genotipagem pré-tratamento indicada na gestação (MS 2024, Quadro 4).',
                 f'{GRUPO} gestante | Antes de iniciar a TARV', MS))
    if not em_tarv:
        orient.append({
            'titulo': 'HIV: genotipagem antes da TARV',
            'descricao': 'Pelo MS a genotipagem pré-tratamento é só para quem se infectou com parceria em TARV, gestantes, '
                         'crianças e adolescentes, uso de PrEP no período provável da infecção e coinfecção TB-HIV; acrescente-a '
                         'pelo catálogo nesses casos. A HIVMA/IDSA pede genotipagem basal para todos que nunca usaram TARV.',
            'referencia': AMBOS})

    # ---- Seguimento (MS 2024, Quadro 10) ----
    add(_rec('Hemograma completo com plaquetas',
             'Pré-TARV e a cada 6-12 meses. Com zidovudina ou outro mielotóxico: a cada 3-6 meses e repetir 2-8 semanas após '
             'iniciar ou trocar.', f'{GRUPO} | A cada 6-12 meses', MS))

    renal = tenofovir or risco_renal
    motivo_renal = 'tenofovir, nefrotóxico ou risco renal' if renal else ''
    add(_rec('Creatinina, soro',
             'Creatinina com TFGe: pré-TARV e anual; a cada 3-6 meses com tenofovir ou outro nefrotóxico, TFGe abaixo de '
             '60 mL/min ou risco de doença renal (diabetes, hipertensão).',
             f'{GRUPO} com {motivo_renal} | A cada 3-6 meses' if renal else f'{GRUPO} | Anual', MS))
    add(_rec('EAS - Elementos Anormais e Sedimentoscopia, urina',
             'Pré-TARV e anual; a cada 3-6 meses com tenofovir ou outro nefrotóxico, TFGe abaixo de 60 mL/min, proteinúria '
             'ou risco de doença renal.',
             f'{GRUPO} com {motivo_renal} | A cada 3-6 meses' if renal else f'{GRUPO} | Anual', MS))

    # Eletrólitos e ureia: o PCDT não os lista; a HIVMA põe no painel bioquímico.
    eletrolitos = f'{GRUPO} | A cada 6 meses' if em_tarv else f'{GRUPO} | A cada 6-12 meses'
    for titulo in ('Sódio, soro', 'Potássio, soro', 'Ureia, soro'):
        add(_rec(titulo, 'Painel bioquímico (eletrólitos, ureia e creatinina): 1-2 meses após iniciar ou trocar a TARV e depois a '
                 'cada 6 meses; sem TARV, a cada 6-12 meses.', eletrolitos, HIVMA, 'B'))

    for titulo in ('Aspartato aminotransferase, soro', 'Alanina aminotransferase, soro', 'Fosfatase alcalina, soro',
                   'Bilirrubinas totais e frações, soro'):
        add(_rec(titulo, 'AST, ALT, fosfatase alcalina e bilirrubinas: pré-TARV e a cada 3-12 meses; mais frequente com '
                 'hepatotóxicos, doença hepática ou coinfecção HBV/HCV.', f'{GRUPO} | A cada 3-12 meses', MS))

    add(_rec('Colesterol total e frações, soro',
             'Pré-TARV e anual; a cada 6 meses se a última análise estava alterada. A HIVMA/IDSA aceita a cada 5 anos se '
             'normal e pede uma dosagem 1-3 meses após iniciar a TARV.', f'{GRUPO} | Anual', MS))
    add(_rec('Glicose, soro',
             'Glicemia de jejum pré-TARV e anual; entre 100 e 125 mg/dL, considerar TOTG. A HbA1c não deve ser usada para '
             'diagnosticar diabetes na PVHA (subestima a glicemia em TARV).', f'{GRUPO} | Anual', MS))

    # ---- Coinfecções e IST ----
    add(_rec('Sífilis: teste treponêmico ou VDRL, soro',
             'Teste imunológico para sífilis pré-TARV e semestral; mais frequente se houver risco ou exposição. A HIVMA/IDSA '
             'pede ao menos anual, a cada 3-6 meses com risco.', f'{GRUPO} | Semestral ou conforme indicação', MS))
    add(_rec('Clamídia e gonococo, PCR (urina ou swab)',
             'Teste molecular em todos os locais de exposição sexual (urina ou swab vaginal, swab retal e de orofaringe). '
             'Na entrada e ao menos anual; a cada 3-6 meses conforme as práticas sexuais.', f'{GRUPO} | Anual', HIVMA, 'B'))
    if sexo == 'feminino':
        add(_rec('Trichomonas vaginalis, PCR (swab vaginal)',
                 'Quem tem relação vaginal receptiva: teste molecular em swab vaginal ou endocervical, ao menos anual.',
                 f'{GRUPO} | Anual', HIVMA, 'B'))
    add(_rec('Anticorpos anti-HCV, soro',
             'Pré-TARV e anual ou conforme risco ou exposição. Anti-HCV reagente ou suspeita de infecção aguda: pedir a carga '
             'viral do HCV (HCV-RNA). Com CD4 baixo o anticorpo pode falhar: considerar o HCV-RNA.',
             f'{GRUPO} | Anual ou conforme indicação', AMBOS))
    for titulo in ('Antígeno HBs, soro', 'Anticorpos anti-HBc total, soro', 'Anticorpos anti-HBs, soro'):
        add(_rec(titulo, 'Triagem de hepatite B na avaliação inicial. HBsAg reagente: carga viral do HBV. Vacinar quem não é '
                 'imune; com anti-HBs reagente não é preciso repetir. Repetir a sorologia antes de trocar para esquema sem '
                 'tenofovir.', f'{GRUPO} | Avaliação inicial', AMBOS))
    add(_rec('Anticorpos anti-HAV IgG, soro',
             'Imunidade para hepatite A na avaliação inicial; não reagente: vacinar.', f'{GRUPO} | Avaliação inicial', AMBOS))
    add(_rec('Toxoplasmose IgG, soro',
             'IgG para toxoplasmose na avaliação inicial (orienta a profilaxia com CD4 baixo).', f'{GRUPO} | Avaliação inicial', MS))
    add(_rec('Sorologia para HTLV 1 e 2, soro', 'Na avaliação inicial. Coinfecção com HTLV pode superestimar o CD4 absoluto.',
             f'{GRUPO} | Avaliação inicial', MS, 'B'))

    # Tuberculose: MS 3.5.1 e Quadro 10. Sem CD4 não dá para decidir entre PT/IGRA e TPT direto.
    if cd4 is None:
        orient.append({
            'titulo': 'HIV sem CD4 anterior: o que depende do resultado',
            'descricao': 'Com o CD4 em mãos: abaixo de 200, pedir LF-CrAg (antígeno criptocócico) mesmo sem sintomas; até 350, '
                         'avaliar o tratamento preventivo da tuberculose (TPT) sem prova tuberculínica, depois de afastar TB ativa; '
                         'acima de 350, prova tuberculínica ou IGRA. O CD4 também define as profilaxias de infecções oportunistas e '
                         'a periodicidade do próprio CD4; a carga viral, a do seguimento.',
            'referencia': MS})
    elif cd4 > CD4_TB:
        add(_rec('Prova tuberculínica (PPD) ou IGRA',
                 'Pré-TARV com CD4 acima de 350; anual se o exame anterior foi PT abaixo de 5 mm ou IGRA negativo. PT de 5 mm '
                 'ou mais ou IGRA positivo: afastar TB ativa (sintomas e radiografia de tórax) e tratar a infecção latente.',
                 f'{GRUPO} | Anual', AMBOS))
    else:
        orient.append({
            'titulo': 'HIV com CD4 até 350: infecção latente por tuberculose',
            'descricao': 'Com CD4 abaixo de 350 o MS não pede prova tuberculínica nem IGRA: avaliar os critérios de tratamento '
                         'preventivo da tuberculose (TPT) direto, depois de afastar TB ativa (rastreio de sintomas em toda '
                         'consulta e radiografia de tórax).',
            'referencia': MS})
    add(_rec('Radiografia de tórax', 'Na abordagem inicial; também para afastar TB ativa antes do tratamento da infecção latente.',
             f'{GRUPO} | Avaliação inicial', MS, 'B', categoria='imagem'))

    if cd4 is not None and cd4 < CD4_CRIPTOCOCO:
        add(_rec('Antígeno criptocócico (LF-CrAg), soro',
                 'Rastreio de doença criptocócica mesmo sem sintomas, com CD4 abaixo de 200 e sem meningite criptocócica prévia '
                 '(MS; a HIVMA/IDSA usa CD4 abaixo de 100). Reagente: avaliar punção lombar.',
                 f'{GRUPO} com CD4 <200 | Avaliação inicial', AMBOS))

    if sexo == 'feminino' and idade < IDADE_FERTIL_FIM and not gestante and not em_tarv:
        add(_rec('Beta-hCG, soro', 'Pessoa com potencial de engravidar: teste de gravidez antes de iniciar a TARV.',
                 f'{GRUPO} | Antes de iniciar a TARV', HIVMA, 'B'))

    orient.append({
        'titulo': 'HIV: o que mais o seguimento pede',
        'descricao': 'Teste de gravidez antes de iniciar ou trocar a TARV em quem pode engravidar (HIVMA/IDSA). Sorologia para '
                     'doença de Chagas e leishmaniose conforme a epidemiologia (MS). Escore de risco cardiovascular anual e a '
                     'cada troca de TARV (MS). Consultas: 7-15 dias após iniciar ou trocar a TARV; mensal ou bimestral até a '
                     'adaptação; até 6 meses com supressão viral e sem sintomas (MS).',
        'referencia': AMBOS})
    orient.append({
        'titulo': 'HIV: rastreio de câncer anal',
        'descricao': 'MS: toque retal anual em quem tem relação anal receptiva, antecedente de HPV ou histologia vulvar ou '
                     'cervical alterada; anuscopia se alterado. HIVMA/IDSA: onde houver anuscopia de alta resolução, citologia '
                     'anal com pesquisa de HPV para homens que fazem sexo com homens e mulheres trans acima de 35 anos e para as '
                     'demais PVHA acima de 45; LSIL ou pior: anuscopia de alta resolução. Toque retal anual em todos.',
        'referencia': AMBOS})
    return recs, orient
