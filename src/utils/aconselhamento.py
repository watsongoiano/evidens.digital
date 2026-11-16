"""Recomendações A e B do USPSTF que não geram exame: rastreio por pergunta ou questionário, aconselhamento e
medicação preventiva. Cada uma só aparece para quem está no quadro a que ela se refere, informado no formulário
(fumante, consumo pesado de álcool, IMC de 30 ou mais, hipertensão ou dislipidemia, PrEP, história familiar de câncer
de mama, gestação, aleitamento). Rastreios universais por pergunta (depressão, ansiedade, violência por parceiro
íntimo, uso de drogas) e a prevenção de quedas (sem campo de risco de queda) ficam de fora, por decisão do Dr. Rodolfo.
Questionário citado no texto leva o link no próprio nome (campo ``links``).

Fonte única (lista oficial, com a população e o grau de cada item):
https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations
- Uso de álcool: rastreio e aconselhamento breve (B, 2018); aqui, só com consumo pesado informado. O AUDIT é o
  questionário da OMS para estimar a gravidade.
- Tabagismo: a quem fuma, intervenção comportamental e, fora da gestação, farmacoterapia (A, 2021).
- Obesidade: intervenção comportamental intensiva com IMC de 30 ou mais (B, 2018).
- Dieta e atividade física: adultos com fator de risco cardiovascular (B, 2020).
- IST: aconselhamento comportamental para adultos com risco aumentado (B, 2020); aqui, em uso de PrEP.
- Câncer de mama: medicação para reduzir o risco em mulheres de 35 anos ou mais com risco aumentado (B, 2019).
- Gestação: aleitamento (B, 2025), ganho de peso (B, 2021) e prevenção da depressão perinatal com risco
  aumentado (B, 2019).
"""
REF = 'USPSTF A e B'
AUDIT = ('AUDIT', 'https://www.who.int/publications/i/item/audit-the-alcohol-use-disorders-identification-test-guidelines-for-use-in-primary-health-care')
FAMILIA_MAMA = {'cancer_mama', 'mama_ate_50', 'mama_bilateral', 'mama_masculino', 'mama_triplo_negativo', 'brca'}
RISCO_CARDIOVASCULAR = {'hipertensao': 'hipertensão', 'dislipidemia': 'dislipidemia'}


def orientacoes(idade, sexo, *, gestante=False, lactante=False, tabagismo=None, imc=None, comorbidades=(),
                historia_familiar=(), medicacoes=(), prep=False, alcool=None):
    """Lista de orientações {'titulo', 'descricao', 'referencia'} do perfil."""
    if idade is None or idade < 18:
        return []
    com, fam, o = set(comorbidades or ()), set(historia_familiar or ()), []

    def orientar(titulo, descricao, ano, links=()):
        item = {'titulo': titulo, 'descricao': descricao, 'referencia': f'{REF} ({ano})'}   # sem vírgula: é um link só
        if links:
            item['links'] = [{'texto': t, 'url': u} for t, u in links]
        o.append(item)

    if alcool == 'pesado':
        orientar('Consumo pesado de álcool: aconselhamento breve',
                 'Com consumo pesado informado, sugerimos aplicar o AUDIT para estimar a gravidade, fazer aconselhamento '
                 'breve e, com sinais de dependência, encaminhar para tratamento.', 'álcool 2018', links=[AUDIT])
    if tabagismo == 'atual':
        orientar('Tabagismo: oferecer tratamento para parar de fumar',
                 'Sugerimos aconselhar a parar e oferecer intervenção comportamental. ' +
                 ('Na gestação, a recomendação é a intervenção comportamental; a evidência sobre farmacoterapia é '
                  'insuficiente.' if gestante else
                  'Fora da gestação, associar farmacoterapia aprovada (reposição de nicotina, bupropiona ou vareniclina).'),
                 'tabagismo 2021')
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
