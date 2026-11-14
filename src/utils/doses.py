"""Dose e duração das medicações em que isso muda a conduta.

Corticoide sistêmico, metotrexato, azatioprina, hidroxicloroquina e bisfosfonato: a dose e o
tempo de uso definem se há imunossupressão (vacinas de vírus vivo), se cabe densitometria e
que outras complicações rastrear. A tela pergunta só o que cada um precisa; aqui a resposta
vira classe (``condicoes.MEDICACOES``) e orientação.

Limiares e fontes
- Corticoide imunossupressor: ≥ 20 mg/dia de prednisona (ou equivalente) por ≥ 14 dias. Vacinas
  de vírus vivo só 4 semanas depois de suspender (SBIm 2026/2027; CDC/ACIP).
- Risco de fratura: ≥ 2,5 mg/dia de prednisona por ≥ 3 meses (ACR 2022).
- Tuberculose latente: ≥ 15 mg/dia de prednisona por ≥ 1 mês (MS, Manual de Tuberculose 2019).
- Pneumocistose: ≥ 20 mg/dia por ≥ 4 semanas, com outro fator de imunossupressão (ATS 2011).
- Metotrexato ≤ 0,4 mg/kg/semana e azatioprina ≤ 3 mg/kg/dia: imunossupressão de baixo grau
  (CDC/ACIP; IDSA 2013). Sem o peso, metotrexato ≤ 20 mg/semana conta como baixo grau.
- Hidroxicloroquina: retinopatia sobe com dose > 5 mg/kg/dia e com mais de 5 anos de uso (AAO 2016).
- Bisfosfonato: reavaliar pausa após 5 anos (oral) ou 3 anos (ácido zoledrônico) (ASBMR 2016).
"""
from __future__ import annotations

# O que a tela pergunta, por tipo de detalhe.
DETALHES = {
    'corticoide': {'dose': 'Dose (mg/dia)', 'duracao': 'Há quantas semanas',
                   'ajuda': 'Define imunossupressão (≥ 20 mg/dia de prednisona por ≥ 2 semanas) e risco de fratura (≥ 2,5 mg/dia por ≥ 3 meses).'},
    'metotrexato': {'dose': 'Dose (mg/semana)',
                    'ajuda': 'Até 0,4 mg/kg/semana conta como imunossupressão de baixo grau.'},
    'azatioprina': {'dose': 'Dose (mg/dia)',
                    'ajuda': 'Até 3 mg/kg/dia conta como imunossupressão de baixo grau (informe o peso).'},
    'hidroxicloroquina': {'dose': 'Dose (mg/dia)', 'duracao': 'Há quantos anos',
                          'ajuda': 'Retinopatia: risco maior acima de 5 mg/kg/dia e depois de 5 anos.'},
    'bisfosfonato': {'duracao': 'Há quantos anos', 'ajuda': 'Reavaliar pausa após 5 anos (oral) ou 3 anos (zoledrônico).'},
}

# medicamento -> (tipo de detalhe, parâmetro). Corticoide: mg de prednisona por mg do fármaco.
# Bisfosfonato: anos até reavaliar a pausa.
POR_MEDICAMENTO = {
    'prednisona': ('corticoide', 1.0), 'prednisolona': ('corticoide', 1.0), 'metilprednisolona': ('corticoide', 1.25),
    'deflazacorte': ('corticoide', 5 / 6), 'dexametasona': ('corticoide', 5 / 0.75), 'hidrocortisona': ('corticoide', 0.25),
    'metotrexato': ('metotrexato', None), 'azatioprina': ('azatioprina', None),
    'hidroxicloroquina': ('hidroxicloroquina', None),
    'alendronato': ('bisfosfonato', 5), 'risedronato': ('bisfosfonato', 5), 'ibandronato': ('bisfosfonato', 5),
    'acido_zoledronico': ('bisfosfonato', 3),
}

LIMITES = {'dose': (0, 5000), 'duracao': (0, 3000)}


class DetalheInvalido(ValueError):
    def __init__(self, erros):
        super().__init__('; '.join(e['mensagem'] for e in erros))
        self.erros = erros


def _numero(valor):
    if valor in (None, ''):
        return None
    return float(str(valor).replace(',', '.'))


def ler(entrada, medicacoes):
    """Lê ``dose__<medicamento>`` e ``duracao__<medicamento>`` do pedido, só dos medicamentos escolhidos."""
    detalhes, erros = {}, []
    for chave in medicacoes:
        if chave not in POR_MEDICAMENTO:
            continue
        item = {}
        for campo in ('dose', 'duracao'):
            bruto = entrada.get(f'{campo}__{chave}')
            try:
                numero = _numero(bruto)
            except (TypeError, ValueError):
                numero = -1
            if numero is None:
                continue
            minimo, maximo = LIMITES[campo]
            if not minimo <= numero <= maximo:
                erros.append({'campo': f'{campo}__{chave}',
                              'mensagem': f"{'Dose' if campo == 'dose' else 'Duração'} de {chave.replace('_', ' ')}: valor inválido."})
                continue
            item[campo] = numero
        detalhes[chave] = item
    if erros:
        raise DetalheInvalido(erros)
    return detalhes


def _texto(numero):
    return f'{numero:g}'.replace('.', ',')


def avaliar(medicacoes, detalhes, peso=None, rotulos=None):
    """Devolve ``(acrescentar, excluir, orientacoes)`` a partir da dose e da duração.

    ``acrescentar`` são classes novas. ``excluir`` é ``{medicamento: {classes}}``: a classe sai só da
    contribuição daquele medicamento, de modo que outro medicamento que a traga continua valendo
    (metotrexato em dose baixa junto de um imunobiológico segue como imunossupressão).

    Sem dose ou duração, vale o comportamento conservador: corticoide tratado como uso crônico,
    metotrexato e azatioprina como imunossupressores; e a orientação pede o dado que falta.
    """
    rotulos = rotulos or {}
    acrescentar, excluir, orientacoes = set(), {}, []

    def nome(chave):
        return rotulos.get(chave, chave.replace('_', ' ').capitalize())

    def orientar(titulo, descricao, referencia):
        orientacoes.append({'titulo': titulo, 'descricao': descricao, 'referencia': referencia})

    corticoides = [m for m in medicacoes if POR_MEDICAMENTO.get(m, ('', 0))[0] == 'corticoide']
    if corticoides:
        completos = [m for m in corticoides if 'dose' in detalhes.get(m, {}) and 'duracao' in detalhes.get(m, {})]
        if len(completos) < len(corticoides):
            orientar('Corticoide sistêmico: informe dose e duração',
                     'Sem dose e duração, o uso foi tratado como crônico (≥ 3 meses). Com os dois, a ferramenta diz se há '
                     'imunossupressão (vacinas de vírus vivo) e se cabe densitometria. A avaliação laboratorial e a '
                     'monitorização do corticoide valem em qualquer dose.',
                     'ACR 2022 / SBIm 2026/2027')
        else:
            equivalente = {m: detalhes[m]['dose'] * POR_MEDICAMENTO[m][1] for m in corticoides}

            def mantida_por(semanas):
                """Dose (em prednisona) mantida por pelo menos ``semanas``: soma só de quem tem essa duração."""
                return sum(equivalente[m] for m in corticoides if detalhes[m]['duracao'] >= semanas)

            imunossupressor = mantida_por(2) >= 20
            tb_latente = mantida_por(4) >= 15
            dose_alta_prolongada = mantida_por(4) >= 20
            cronico = mantida_por(12) >= 2.5
            resumo = '; '.join(f"{nome(m)} {_texto(round(equivalente[m], 1))} mg/dia de prednisona (equivalente) há "
                               f"{_texto(detalhes[m]['duracao'])} semanas" for m in corticoides)
            if not cronico:
                for m in corticoides:
                    excluir.setdefault(m, set()).add('corticoide_cronico')
            if imunossupressor:
                acrescentar.add('corticoide_imunossupressor')
                orientar('Corticoide em dose imunossupressora',
                         f'{resumo}. A partir de 20 mg/dia por 14 dias ou mais há imunossupressão: vacinas de vírus vivo '
                         'atenuado (tríplice viral, varicela, febre amarela, dengue) ficam contraindicadas e só voltam 4 semanas '
                         'depois de suspender. Manter em dia as inativadas: influenza, COVID-19, pneumocócica, herpes-zóster '
                         'recombinante, HPV, VSR, dTpa, hepatites A e B nos não vacinados e meningocócicas quando indicadas. '
                         'Durante o uso: avaliação laboratorial basal, glicemia e HbA1c, perfil lipídico, pressão arterial '
                         '(MAPA) e exame oftalmológico; densitometria se o uso passar de 3 meses.',
                         'SBIm 2026/2027 / CDC/ACIP 2025 / CGH 2025 (Feuerstein) / Drugs Aging 2024 (Sparling)')
            if tb_latente:
                acrescentar.add('rastreio_tb_latente')
            if dose_alta_prolongada:
                orientar('Corticoide em dose alta por 4 semanas ou mais',
                         'Considerar profilaxia de pneumocistose quando houver outro fator de imunossupressão (outro '
                         'imunossupressor, neoplasia hematológica, vasculite) e tratar ou pesquisar estrongiloidíase antes de '
                         'manter dose alta (área endêmica).', 'ATS 2011 / MS 2019')
            if cronico:
                orientar('Corticoide por 3 meses ou mais',
                         f'{resumo}. Além da avaliação de fratura (densitometria, imagem da coluna e FRAX): cálcio '
                         '800-1.000 mg/dia e vitamina D 600-800 UI/dia (a ACR 2022 fala em 1.000-1.200 mg de cálcio), acompanhar '
                         'glicemia, lipídios e pressão arterial, exame oftalmológico periódico (catarata e glaucoma) e, na '
                         'suspensão, redução gradual pelo risco de insuficiência adrenal.', 'ACR 2022 / CGH 2025 (Feuerstein)')
            elif not imunossupressor:
                orientar('Corticoide sistêmico em dose ou tempo baixos',
                         f'{resumo}: abaixo dos limiares de imunossupressão (20 mg/dia por 2 semanas) e de risco de fratura '
                         '(2,5 mg/dia por 3 meses). Não muda as vacinas nem indica densitometria; a avaliação laboratorial e a '
                         'monitorização do corticoide (glicemia, lipídios, pressão, olhos) seguem indicadas.',
                         'ACR 2022 / SBIm 2026/2027 / CGH 2025 (Feuerstein)')

    if 'metotrexato' in medicacoes:
        dose = detalhes.get('metotrexato', {}).get('dose')
        if dose is None:
            orientar('Metotrexato: informe a dose semanal',
                     'Sem a dose, foi tratado como imunossupressor. Até 0,4 mg/kg/semana (ou 20 mg/semana, sem o peso) conta '
                     'como imunossupressão de baixo grau.', 'CDC/ACIP 2025 / IDSA 2013')
        else:
            limite = 0.4 * float(peso) if peso else 20
            if dose <= limite:
                excluir.setdefault('metotrexato', set()).add('imunossupressor')
                orientar('Metotrexato em dose de baixo grau de imunossupressão',
                         f'{_texto(dose)} mg/semana (limite de baixo grau: {_texto(round(limite, 1))} mg/semana). Vacinas '
                         'inativadas seguem indicadas; as de vírus vivo podem ser consideradas caso a caso, e a resposta de '
                         '"Imunossupressão" na triagem de vacinas fica a critério do médico.', 'CDC/ACIP 2025 / IDSA 2013')
    if 'azatioprina' in medicacoes:
        dose = detalhes.get('azatioprina', {}).get('dose')
        if dose is None or not peso:
            orientar('Azatioprina: informe dose e peso',
                     'Sem dose e peso, foi tratada como imunossupressora. Até 3 mg/kg/dia conta como imunossupressão de baixo grau.',
                     'CDC/ACIP 2025 / IDSA 2013')
        elif dose <= 3 * float(peso):
            excluir.setdefault('azatioprina', set()).add('imunossupressor')
            orientar('Azatioprina em dose de baixo grau de imunossupressão',
                     f'{_texto(dose)} mg/dia ({_texto(round(dose / float(peso), 1))} mg/kg/dia; limite de baixo grau: 3 mg/kg/dia). '
                     'Vacinas de vírus vivo podem ser consideradas caso a caso.', 'CDC/ACIP 2025 / IDSA 2013')
    if 'hidroxicloroquina' in medicacoes:
        d = detalhes.get('hidroxicloroquina', {})
        dose, anos = d.get('dose'), d.get('duracao')
        acima = bool(dose and peso and dose > 5 * float(peso))
        if (anos is not None and anos >= 5) or acima:
            motivo = ' e '.join(x for x in (
                f'{_texto(round(dose / float(peso), 1))} mg/kg/dia (acima de 5 mg/kg/dia)' if acima else '',
                f'{_texto(anos)} anos de uso' if anos is not None and anos >= 5 else '') if x)
            orientar('Hidroxicloroquina: rastreamento anual de retinopatia indicado',
                     f'{motivo}. Avaliação oftalmológica anual com campo visual automatizado 10-2 e OCT de domínio espectral.'
                     + (' Ajustar a dose para até 5 mg/kg/dia de peso real.' if acima else ''), 'AAO 2016')
            acrescentar.add('hidroxicloroquina_rastreio')
    bisf = [m for m in medicacoes if POR_MEDICAMENTO.get(m, ('', 0))[0] == 'bisfosfonato']
    longos = [m for m in bisf if detalhes.get(m, {}).get('duracao') is not None
              and detalhes[m]['duracao'] >= POR_MEDICAMENTO[m][1]]
    if longos:
        acrescentar.add('bisfosfonato_longo')
        orientar('Bisfosfonato: reavaliar a continuidade',
                 f"{' + '.join(nome(m) for m in longos)} por tempo suficiente para reavaliar (5 anos por via oral, 3 anos de "
                 'ácido zoledrônico). Com baixo risco de fratura, considerar pausa de 2-3 anos; com alto risco, manter '
                 '(até 10 anos por via oral) ou trocar de classe.', 'ASBMR 2016')
    return acrescentar, excluir, orientacoes
