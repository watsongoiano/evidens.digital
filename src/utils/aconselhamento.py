"""Recomendações A e B do USPSTF que não geram exame: rastreio por pergunta ou questionário, aconselhamento e
medicação preventiva. Cada uma só aparece para o perfil a que se aplica (idade, sexo, gestação, tabagismo, IMC,
comorbidades, história familiar).

Fonte única (lista oficial, com a população e o grau de cada item):
https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations
- Depressão: adultos, incluídos gestantes, puérperas e idosos (B, 2023). Ansiedade: adultos até 64 anos (B, 2023).
- Uso de álcool (B, 2018) e de outras drogas (B, 2020): adultos a partir de 18 anos.
- Tabagismo: perguntar a todos; a quem fuma, intervenção comportamental e, fora da gestação, farmacoterapia (A, 2021).
- Violência por parceiro íntimo: mulheres em idade reprodutiva, incluídas gestantes e puérperas (B, 2025).
- Quedas: exercício para quem tem 65 anos ou mais e risco aumentado (B, 2024).
- Obesidade: intervenção comportamental intensiva com IMC de 30 ou mais (B, 2018).
- Dieta e atividade física: adultos com fator de risco cardiovascular (B, 2020).
- IST: aconselhamento comportamental para adultos com risco aumentado (B, 2020).
- Câncer de mama: medicação para reduzir o risco em mulheres de 35 anos ou mais com risco aumentado (B, 2019).
- Gestação: aleitamento (B, 2025), ganho de peso (B, 2021) e prevenção da depressão perinatal com risco
  aumentado (B, 2019).

O que o formulário não pergunta (risco de queda, pele clara, comportamento sexual) não é presumido: a orientação
de quedas diz a quem se aplica, e o aconselhamento de câncer de pele (pele clara, até 24 anos) fica de fora.
"""
REF = 'USPSTF A e B'
IDADE_REPRODUTIVA = (18, 45)   # a mesma faixa que o sistema usa em "pode engravidar" (ácido fólico)
FAMILIA_MAMA = {'cancer_mama', 'mama_ate_50', 'mama_bilateral', 'mama_masculino', 'mama_triplo_negativo', 'brca'}
RISCO_CARDIOVASCULAR = {'hipertensao': 'hipertensão', 'dislipidemia': 'dislipidemia'}


def orientacoes(idade, sexo, *, gestante=False, lactante=False, tabagismo=None, imc=None, comorbidades=(),
                historia_familiar=(), medicacoes=(), prep=False):
    """Lista de orientações {'titulo', 'descricao', 'referencia'} do perfil."""
    if idade is None or idade < 18:
        return []
    com, fam, o = set(comorbidades or ()), set(historia_familiar or ()), []

    def orientar(titulo, descricao, ano):
        o.append({'titulo': titulo, 'descricao': descricao, 'referencia': f'{REF} ({ano})'})   # sem vírgula: é um link só

    # Saúde mental: rastreio é para quem não tem o diagnóstico.
    alvos = [nome for chave, nome, limite in (('depressao', 'depressão', 200), ('ansiedade', 'ansiedade', 64))
             if chave not in com and idade <= limite]
    if alvos:
        orientar('Rastrear ' + ' e '.join(alvos),
                 'Sugerimos rastrear ' + ' e '.join(alvos) + ' com questionário validado (por exemplo, '
                 + ' e '.join({'depressão': 'PHQ-2/PHQ-9', 'ansiedade': 'GAD-7'}[x] for x in alvos) + '), com seguimento e tratamento para quem tiver '
                 'resultado positivo.' + ('' if 'ansiedade' in alvos or 'ansiedade' in com else
                                          ' A partir dos 65 anos, a evidência para rastrear ansiedade é insuficiente.'),
                 'depressão e ansiedade 2023')
    orientar('Perguntar sobre álcool e outras drogas',
             'Sugerimos rastrear o uso nocivo de álcool (por exemplo, AUDIT-C) com aconselhamento breve para quem bebe '
             'em padrão de risco, e perguntar sobre o uso de outras drogas quando houver como oferecer ou encaminhar '
             'para diagnóstico e tratamento.', 'álcool 2018 e drogas 2020')
    if tabagismo == 'atual':
        orientar('Tabagismo: oferecer tratamento para parar de fumar',
                 'Sugerimos aconselhar a parar e oferecer intervenção comportamental. ' +
                 ('Na gestação, a recomendação é a intervenção comportamental; a evidência sobre farmacoterapia é '
                  'insuficiente.' if gestante else
                  'Fora da gestação, associar farmacoterapia aprovada (reposição de nicotina, bupropiona ou vareniclina).'),
                 'tabagismo 2021')
    if sexo == 'feminino' and (gestante or lactante or IDADE_REPRODUTIVA[0] <= idade <= IDADE_REPRODUTIVA[1]):
        orientar('Rastrear violência por parceiro íntimo',
                 'Sugerimos perguntar sobre violência por parceiro íntimo às mulheres em idade reprodutiva, incluídas '
                 'gestantes e puérperas, e oferecer ou encaminhar quem tiver rastreio positivo para suporte continuado.',
                 'violência por parceiro íntimo 2025')
    if idade >= 65:
        orientar('Prevenção de quedas a partir dos 65 anos',
                 'Para quem vive na comunidade e tem risco aumentado de quedas (queda prévia, alteração de marcha ou de '
                 'equilíbrio), sugerimos exercício supervisionado (equilíbrio, marcha e força). Intervenção '
                 'multifatorial fica para casos selecionados, por decisão individual.', 'quedas 2024')
    if (imc or 0) >= 30 or 'obesidade' in com:
        orientar('Obesidade: intervenção comportamental intensiva',
                 'Com IMC de 30 kg/m² ou mais, sugerimos oferecer ou encaminhar para intervenção comportamental '
                 'intensiva e multicomponente (dieta, atividade física e suporte comportamental).', 'obesidade 2018')
    fatores = [nome for chave, nome in RISCO_CARDIOVASCULAR.items() if chave in com]
    if fatores and not gestante:
        orientar('Aconselhamento de dieta e atividade física',
                 'Com fator de risco cardiovascular (' + ', '.join(fatores) + '), sugerimos oferecer ou encaminhar para '
                 'aconselhamento comportamental de alimentação saudável e atividade física.', 'dieta e atividade física 2020')
    if prep:
        orientar('Aconselhamento para prevenção de IST',
                 'Para adultos com risco aumentado de infecção sexualmente transmissível, sugerimos aconselhamento '
                 'comportamental (uso de preservativo, redução de risco), além da testagem periódica.', 'IST 2020')
    if sexo == 'feminino' and idade >= 35 and fam & FAMILIA_MAMA and not {'oncologico', 'tamoxifeno'} & set(medicacoes or ()) and not gestante:
        orientar('Câncer de mama: avaliar medicação para reduzir o risco',
                 'Com história familiar de câncer de mama, sugerimos estimar o risco com ferramenta validada. Se o risco '
                 'for aumentado e o de efeitos adversos for baixo, discutir tamoxifeno, raloxifeno ou inibidor de '
                 'aromatase. Sem risco aumentado, o uso de rotina não é recomendado.', 'medicação para risco de câncer de mama 2019')
    if gestante:
        orientar('Gestação: aleitamento, ganho de peso e saúde mental',
                 'Sugerimos apoiar o aleitamento materno durante a gestação e depois do parto; aconselhar sobre ganho de '
                 'peso saudável na gestação; e, com risco aumentado de depressão perinatal (história de depressão, '
                 'sintomas depressivos atuais, fatores socioeconômicos), oferecer ou encaminhar para aconselhamento.',
                 'aleitamento 2025 e ganho de peso 2021 e depressão perinatal 2019')
    elif lactante:
        orientar('Puerpério: apoio ao aleitamento e saúde mental',
                 'Sugerimos apoiar o aleitamento materno e, com risco aumentado de depressão perinatal, oferecer ou '
                 'encaminhar para aconselhamento.', 'aleitamento 2025 e depressão perinatal 2019')
    return o
