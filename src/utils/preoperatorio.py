"""Avaliação pré-operatória de cirurgia não cardíaca: indicação de avaliação cardiológica, escores, exames e
cuidados pós-operatórios.

Referências-base, usadas em conjunto (com aviso quando divergem):
- AHA/ACC 2026 (reafirmação da diretriz de 2024, texto e recomendações idênticos): Guideline for Perioperative
  Cardiovascular Management for Noncardiac Surgery.
- SBC 2024: Diretriz de Avaliação Cardiovascular Perioperatória (Gualandro et al., Arq Bras Cardiol 2024;121(9)).
- Escores pelos artigos originais (RCRI, AUB-HAS2, VSG-CRI, DASI, ARISCAT, STOP-Bang, CFS, Cockcroft-Gault).
- Exames laboratoriais de rotina: NICE NG45 (2016). Risco pulmonar: ACP 2006 e ARISCAT.

O Gupta NSQIP MICA fica de fora até os coeficientes serem conferidos no artigo original (Circulation 2011).
A classe de recomendação vem de cada diretriz; "AHA 1" e "SBC I" são as classes mais fortes de cada uma.
"""
from __future__ import annotations

from datetime import date

# ── Referências ──────────────────────────────────────────────────────────────

def _ref(label, url):
    return {'label': label, 'url': url}


AHA = _ref('AHA/ACC 2026', 'https://professional.heart.org/en/science-news/'
                           '2026-guideline-for-perioperative-cardiovascular-management-for-noncardiac-surgery')
SBC = _ref('SBC 2024', 'https://doi.org/10.36660/abc.20240590')
LEE = _ref('Lee 1999 (RCRI)', 'https://doi.org/10.1161/01.cir.100.10.1043')
AUB = _ref('Dakik 2019 (AUB-HAS2)', 'https://doi.org/10.1016/j.jacc.2019.04.023')
VSG = _ref('Bertges 2010 (VSG-CRI)', 'https://doi.org/10.1016/j.jvs.2010.03.031')
DASI = _ref('Hlatky 1989 (DASI)', 'https://doi.org/10.1016/0002-9149(89)90496-7')
ARISCAT = _ref('Canet 2010 (ARISCAT)', 'https://doi.org/10.1097/ALN.0b013e3181fc6e0a')
ACP = _ref('ACP 2006', 'https://doi.org/10.7326/0003-4819-144-8-200604180-00008')
STOPBANG = _ref('Chung 2016 (STOP-Bang)', 'https://doi.org/10.1378/chest.15-0903')
CFS = _ref('Rockwood 2005 (CFS)', 'https://doi.org/10.1503/cmaj.050051')
CG = _ref('Cockcroft-Gault 1976', 'https://doi.org/10.1159/000180580')
NICE = _ref('NICE NG45', 'https://www.nice.org.uk/guidance/ng45/chapter/recommendations')
TABAGISMO = _ref('Wong 2012', 'https://doi.org/10.1007/s12630-011-9652-x')

# ── Cirurgias ────────────────────────────────────────────────────────────────
# risco: risco intrínseco de morte CV, IAM ou AVC em 30 dias (SBC 2024 Tabela 3 = ESC 2022 Tabela 5).
# rcri: cirurgia intraperitoneal, intratorácica ou vascular suprainguinal (Lee 1999).
# vascular: cirurgia vascular arterial (AUB-HAS2; ativa o VSG-CRI, recomendado pela SBC para esses casos).
# incisao: ARISCAT (periferica, abdome_superior, intratoracica). porte: grau cirúrgico do NICE NG45.
_C = lambda rotulo, risco, rcri, incisao, porte, vascular=False, urologica=False: {  # noqa: E731
    'rotulo': rotulo, 'risco': risco, 'rcri': rcri, 'incisao': incisao, 'porte': porte, 'vascular': vascular,
    'urologica': urologica}

CIRURGIAS = {
    # Baixo risco (< 1%)
    'catarata': _C('Oftalmológica (catarata e outras)', 'baixo', False, 'periferica', 'menor'),
    'odontologica': _C('Odontológica', 'baixo', False, 'periferica', 'menor'),
    'endoscopia': _C('Endoscopia ou colonoscopia', 'baixo', False, 'periferica', 'menor'),
    'pele': _C('Superficial (pele e partes moles, biópsia)', 'baixo', False, 'periferica', 'menor'),
    'mama': _C('Mama', 'baixo', False, 'periferica', 'intermediaria'),
    'tireoide': _C('Tireoide ou paratireoide', 'baixo', False, 'periferica', 'maior'),
    'ginecologica_menor': _C('Ginecológica menor', 'baixo', False, 'periferica', 'intermediaria'),
    'ortopedica_menor': _C('Ortopédica menor (artroscopia, menisco)', 'baixo', False, 'periferica', 'intermediaria'),
    'plastica': _C('Reconstrutiva ou plástica', 'baixo', False, 'periferica', 'intermediaria'),
    'rtu': _C('Urológica menor (RTU de próstata ou bexiga)', 'baixo', False, 'periferica', 'maior',
              urologica=True),
    'vats_menor': _C('Videotoracoscopia com ressecção pulmonar menor', 'baixo', True, 'intratoracica', 'maior'),
    'hernia': _C('Hérnia inguinal ou umbilical', 'baixo', False, 'periferica', 'intermediaria'),
    # Intermediário (1–5%)
    'carotida_assintomatica': _C('Carótida assintomática (endarterectomia ou stent)', 'intermediario', False,
                                 'periferica', 'maior', vascular=True),
    'endarterectomia_sintomatica': _C('Endarterectomia de carótida sintomática', 'intermediario', False,
                                      'periferica', 'maior', vascular=True),
    'evar': _C('Aneurisma de aorta por via endovascular (EVAR)', 'intermediario', True, 'periferica', 'maior',
               vascular=True),
    'angioplastia_periferica': _C('Angioplastia arterial periférica', 'intermediario', False, 'periferica',
                                  'intermediaria', vascular=True),
    'cabeca_pescoco': _C('Cabeça e pescoço', 'intermediario', False, 'periferica', 'maior'),
    'colecistectomia': _C('Intraperitoneal: colecistectomia, hérnia hiatal, esplenectomia', 'intermediario', True,
                          'abdome_superior', 'maior'),
    'colectomia': _C('Intraperitoneal: colectomia ou outra cirurgia intestinal', 'intermediario', True,
                     'abdome_superior', 'maior'),
    'intratoracica': _C('Intratorácica não maior', 'intermediario', True, 'intratoracica', 'maior'),
    'coluna': _C('Coluna ou neurocirurgia', 'intermediario', False, 'periferica', 'maior'),
    'quadril': _C('Ortopédica maior (quadril, joelho, artroplastia)', 'intermediario', False, 'periferica', 'maior'),
    'transplante_renal': _C('Transplante renal', 'intermediario', False, 'periferica', 'maior', urologica=True),
    'urologica_maior': _C('Urológica maior (prostatectomia, nefrectomia)', 'intermediario', True, 'periferica',
                          'maior', urologica=True),
    'ginecologica_maior': _C('Ginecológica maior (histerectomia abdominal)', 'intermediario', True, 'periferica',
                             'maior'),
    # Alto (> 5%)
    'adrenal': _C('Ressecção de adrenal', 'alto', True, 'abdome_superior', 'maior'),
    'aorta_aberta': _C('Aorta ou cirurgia vascular maior aberta', 'alto', True, 'abdome_superior', 'maior',
                       vascular=True),
    'stent_carotida_sintomatica': _C('Stent de carótida sintomática', 'alto', False, 'periferica', 'maior',
                                     vascular=True),
    'revascularizacao_mmii': _C('Revascularização aberta de membro inferior ou amputação', 'alto', False,
                                'periferica', 'maior', vascular=True),
    'pancreas': _C('Duodenopancreatectomia', 'alto', True, 'abdome_superior', 'maior'),
    'figado': _C('Ressecção hepática ou de vias biliares', 'alto', True, 'abdome_superior', 'maior'),
    'esofagectomia': _C('Esofagectomia', 'alto', True, 'intratoracica', 'maior'),
    'pneumectomia': _C('Pneumectomia', 'alto', True, 'intratoracica', 'maior'),
    'transplante_figado_pulmao': _C('Transplante hepático ou pulmonar', 'alto', True, 'abdome_superior', 'maior'),
    'perfuracao_intestinal': _C('Reparo de perfuração intestinal', 'alto', True, 'abdome_superior', 'maior'),
    'cistectomia': _C('Cistectomia total', 'alto', True, 'periferica', 'maior', urologica=True),
}
RISCO_DA_CIRURGIA = {'baixo': 'Baixo (< 1%)', 'intermediario': 'Intermediário (1–5%)', 'alto': 'Alto (> 5%)'}

URGENCIAS = {
    'eletiva': 'Eletiva',
    'tempo_sensivel': 'Tempo-sensível (pode esperar até 3 meses)',
    'urgencia': 'Urgência (2 a 24 h)',
    'emergencia': 'Emergência (< 2 h)',
}

# Condições cardiovasculares graves ou instáveis (SBC 2024 Tabela 2): adiar a cirurgia eletiva.
INSTAVEIS = {
    'sca': 'Síndrome coronariana aguda',
    'ic_descompensada': 'Insuficiência cardíaca descompensada (NYHA III/IV)',
    'angina_grave': 'Angina CCS III/IV',
    'valvopatia_grave_sintomatica': 'Estenose aórtica ou mitral importante sintomática',
    'arritmia_grave': 'Bradi ou taquiarritmia grave (BAVT, TV)',
    'fa_alta_resposta': 'FA com FC > 120 bpm',
    'hap_sintomatica': 'Hipertensão arterial pulmonar sintomática',
    'aorta_instavel': 'Doença instável da aorta torácica',
    'edema_choque': 'Edema agudo de pulmão ou choque cardiogênico',
}

CONDICOES = ('dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'ic_fe_reduzida', 'avc_ait',
             'avc_ait_recente', 'diabetes', 'diabetes_insulina', 'hipertensao', 'fa', 'valvopatia', 'protese_mecanica',
             'protese_mecanica_mitral', 'dpoc', 'doenca_arterial_periferica', 'marcapasso_cdi', 'hipertensao_pulmonar',
             'tev', 'tev_recente_3m', 'tev_3_12m', 'cancer_ativo', 'trombofilia_grave', 'tabagismo', 'obesidade',
             'hepatopatia', 'doenca_renal')
SINTOMAS = {'angina': 'Angina ou dor torácica', 'dispneia': 'Dispneia nova ou em piora', 'palpitacoes': 'Palpitações',
            'sincope': 'Síncope', 'sopro': 'Sopro cardíaco', 'sinais_ic': 'Sinais de insuficiência cardíaca'}

# DASI (Hlatky 1989; AHA 2026 Tabela 5): item → peso
DASI_ITENS = {
    'cuidar_de_si': ('Cuidar de si (comer, vestir-se, tomar banho)', 2.75),
    'andar_em_casa': ('Andar dentro de casa', 1.75),
    'andar_quarteiroes': ('Andar 1 a 2 quarteirões no plano', 2.75),
    'subir_lance': ('Subir um lance de escada ou uma ladeira', 5.50),
    'correr': ('Correr uma distância curta', 8.00),
    'domestico_leve': ('Serviço doméstico leve (tirar pó, lavar louça)', 2.70),
    'domestico_moderado': ('Serviço doméstico moderado (varrer, carregar compras)', 3.50),
    'domestico_pesado': ('Serviço doméstico pesado (esfregar chão, mover móveis)', 8.00),
    'jardinagem': ('Jardinagem (varrer folhas, capinar)', 4.50),
    'relacoes_sexuais': ('Ter relações sexuais', 5.25),
    'recreacao_moderada': ('Recreação moderada (dança, tênis em duplas)', 6.00),
    'esporte_extenuante': ('Esporte extenuante (natação, futebol)', 7.50),
}

STOP_BANG_ITENS = {'ronco': 'Ronco alto', 'cansaco': 'Cansaço ou sonolência diurna',
                   'apneia_observada': 'Apneia observada durante o sono', 'imc_35': 'IMC > 35 kg/m²',
                   'pescoco_40': 'Pescoço > 40 cm'}

DURACOES = {'menos_2h': 'Menos de 2 h', '2_3h': '2 a 3 h', 'mais_3h': 'Mais de 3 h'}
SANGRAMENTOS = {'minimo': 'Mínimo (catarata, dentária ou pele simples)',
                'baixo_moderado': 'Baixo ou moderado (< 2% em 30 dias)', 'alto': 'Alto (≥ 2% em 30 dias)'}


# ── Leitura ──────────────────────────────────────────────────────────────────

class EntradaInvalida(ValueError):
    pass


def _num(valor, nome, minimo, maximo, obrigatorio=False):
    if valor in (None, ''):
        if obrigatorio:
            raise EntradaInvalida(f'Informe {nome}.')
        return None
    try:
        numero = float(str(valor).replace(',', '.'))
    except ValueError:
        raise EntradaInvalida(f'Confira {nome}.')
    if not minimo <= numero <= maximo:
        raise EntradaInvalida(f'Confira {nome}: aceito de {minimo:g} a {maximo:g}.')
    return numero


def _escolha(valor, opcoes, nome, obrigatorio=False):
    if valor in (None, ''):
        if obrigatorio:
            raise EntradaInvalida(f'Escolha {nome}.')
        return None
    if valor not in opcoes:
        raise EntradaInvalida(f'Opção inválida em {nome}.')
    return valor


def _lista(valor, permitidos, nome):
    if valor in (None, ''):
        return set()
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list) or len(valor) > 60:
        raise EntradaInvalida(f'{nome} em formato inválido.')
    return {v for v in valor if isinstance(v, str) and v in permitidos}


def _meses_desde(ano_mes, hoje):
    """'AAAA-MM' → meses completos até hoje."""
    try:
        ano, mes = (int(p) for p in str(ano_mes).split('-')[:2])
        inicio = date(ano, mes, 1)
    except (TypeError, ValueError):
        raise EntradaInvalida('Confira a data da angioplastia (mês e ano).')
    if inicio > hoje:
        raise EntradaInvalida('A data da angioplastia não pode estar no futuro.')
    return (hoje.year - ano) * 12 + hoje.month - mes


def ler(dados, hoje=None):
    """Valida o pedido da tela. Devolve o dicionário normalizado (ou levanta EntradaInvalida)."""
    hoje = hoje or date.today()
    if not isinstance(dados, dict):
        raise EntradaInvalida('Pedido inválido.')
    p = {
        'idade': int(_num(dados.get('idade'), 'a idade', 18, 120, obrigatorio=True)),
        'sexo': _escolha(dados.get('sexo'), ('masculino', 'feminino'), 'o sexo', obrigatorio=True),
        'peso': _num(dados.get('peso'), 'o peso (kg)', 25, 350),
        'cirurgia': _escolha(dados.get('cirurgia'), CIRURGIAS, 'a cirurgia proposta', obrigatorio=True),
        'urgencia': _escolha(dados.get('urgencia'), URGENCIAS, 'a urgência', obrigatorio=True),
        'asa': _num(dados.get('asa'), 'a classe ASA', 1, 5),
        'duracao': _escolha(dados.get('duracao'), DURACOES, 'a duração prevista'),
        'sangramento': _escolha(dados.get('sangramento'), SANGRAMENTOS, 'o risco de sangramento'),
        'neuroaxial': dados.get('neuroaxial') in (True, 'sim'),
        'instaveis': _lista(dados.get('instaveis'), INSTAVEIS, 'Condições instáveis'),
        'condicoes': _lista(dados.get('condicoes'), CONDICOES, 'Condições clínicas'),
        'sintomas': _lista(dados.get('sintomas'), SINTOMAS, 'Sintomas'),
        'pas': _num(dados.get('pas'), 'a pressão sistólica', 50, 300),
        'pad': _num(dados.get('pad'), 'a pressão diastólica', 20, 200),
        'spo2': _num(dados.get('spo2'), 'a SpO₂', 50, 100),
        'infeccao_respiratoria': dados.get('infeccao_respiratoria') in (True, 'sim'),
        'escadas': _escolha(dados.get('escadas'), ('sim', 'nao', 'nao_sabe'), 'a pergunta das escadas'),
        'dasi': _lista(dados.get('dasi'), DASI_ITENS, 'DASI'),
        'dasi_respondido': dados.get('dasi_respondido') in (True, 'sim'),
        'cfs': _num(dados.get('cfs'), 'a Escala Clínica de Fragilidade', 1, 9),
        'stop_bang': _lista(dados.get('stop_bang'), STOP_BANG_ITENS, 'STOP-Bang'),
        'medicacoes': [m for m in (dados.get('medicacoes') or []) if isinstance(m, str)][:80],
        'aas_indicacao': _escolha(dados.get('aas_indicacao'), ('primaria', 'secundaria'), 'a indicação do AAS'),
        'creatinina': _num(dados.get('creatinina'), 'a creatinina', 0.1, 25),
        'hemoglobina': _num(dados.get('hemoglobina'), 'a hemoglobina', 2, 25),
        'hba1c_meses': _num(dados.get('hba1c_meses'), 'a data da HbA1c', 0, 1200),
        'exames_feitos': [],   # [(chaves do exame, meses desde o exame, data dd/mm/aaaa)] (aplicar_exames_anteriores)
    }
    if p['pas'] is not None and p['pad'] is not None and p['pad'] >= p['pas']:
        raise EntradaInvalida('A pressão diastólica tem de ser menor que a sistólica.')
    stent = None
    if 'stent' in p['condicoes']:
        bruto = dados.get('stent') if isinstance(dados.get('stent'), dict) else {}
        tipo = _escolha(bruto.get('tipo'), ('farmacologico', 'convencional', 'balao'), 'o tipo de angioplastia')
        indicacao = _escolha(bruto.get('indicacao'), ('sca', 'dac_cronica'), 'a indicação da angioplastia')
        meses = _meses_desde(bruto['data'], hoje) if bruto.get('data') else None
        stent = {'tipo': tipo, 'indicacao': indicacao, 'meses': meses}
    p['stent'] = stent
    # Diabetes com insulina é diabetes; IAM prévio e stent são doença coronária; FE reduzida é IC.
    c = p['condicoes']
    from src.utils.medicamentos import MEDICAMENTOS
    if any('insulina' in MEDICAMENTOS.get(m, {}).get('classes', ()) for m in p['medicacoes']):
        c.add('diabetes_insulina')   # insulina em uso conta no RCRI e no VSG-CRI
    if 'diabetes_insulina' in c:
        c.add('diabetes')
    if c & {'iam_previo', 'stent', 'revascularizacao_cirurgica'}:
        c.add('dac')
    if 'ic_fe_reduzida' in c:
        c.add('ic')
    if 'avc_ait_recente' in c:
        c.add('avc_ait')
    if 'protese_mecanica_mitral' in c:
        c.add('protese_mecanica')
    return p


# ── Escores ──────────────────────────────────────────────────────────────────

def clcr(p):
    """Cockcroft-Gault (mL/min). None sem creatinina ou peso."""
    if not p.get('creatinina') or not p.get('peso'):
        return None
    valor = (140 - p['idade']) * p['peso'] / (72 * p['creatinina'])
    return round(valor * (0.85 if p['sexo'] == 'feminino' else 1), 1)


def _medicacao_com_classe(p, classe):
    from src.utils.medicamentos import MEDICAMENTOS
    return any(classe in MEDICAMENTOS.get(m, {}).get('classes', ()) for m in p['medicacoes'])


def rcri(p):
    cir, c = CIRURGIAS[p['cirurgia']], p['condicoes']
    itens = [('Doença coronária', 'dac' in c), ('Insuficiência cardíaca', 'ic' in c),
             ('AVC ou AIT', 'avc_ait' in c), ('Diabetes com insulina', 'diabetes_insulina' in c),
             ('Creatinina > 2,0 mg/dL', (p['creatinina'] or 0) > 2.0),
             ('Cirurgia intraperitoneal, intratorácica ou vascular suprainguinal', cir['rcri'])]
    pontos = sum(1 for _, sim in itens if sim)
    classe = ('I', 'II', 'III', 'IV')[min(pontos, 3)]
    nivel = 'baixo' if pontos <= 1 else 'intermediario' if pontos == 2 else 'alto'
    return {'nome': 'RCRI (Lee)', 'valor': pontos, 'classe': classe, 'nivel': nivel,
            'faixa': f'Classe {classe} · ' + {'baixo': 'baixo', 'intermediario': 'intermediário', 'alto': 'alto'}[nivel],
            'elevado_aha': pontos > 1,
            'itens': [n for n, sim in itens if sim],
            'falta': [] if p['creatinina'] is not None else ['creatinina'],
            'referencias': [LEE, SBC, AHA]}


def aub_has2(p):
    cir, c = CIRURGIAS[p['cirurgia']], p['condicoes']
    historia = bool(c & {'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'fa', 'valvopatia'})
    itens = [('História de doença cardíaca', historia),
             ('Angina ou dispneia', bool(p['sintomas'] & {'angina', 'dispneia'})),
             ('Idade ≥ 75 anos', p['idade'] >= 75),
             ('Hemoglobina < 12 g/dL', p['hemoglobina'] is not None and p['hemoglobina'] < 12),
             ('Cirurgia vascular arterial', cir['vascular']),
             ('Cirurgia de emergência', p['urgencia'] == 'emergencia')]
    pontos = sum(1 for _, sim in itens if sim)
    nivel = 'baixo' if pontos <= 1 else 'intermediario' if pontos <= 3 else 'alto'
    return {'nome': 'AUB-HAS2', 'valor': pontos, 'nivel': nivel,
            'faixa': {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}[nivel],
            'itens': [n for n, sim in itens if sim],
            'falta': [] if p['hemoglobina'] is not None else ['hemoglobina'],
            'nota': 'Ainda não validado na população brasileira (SBC 2024).',
            'referencias': [AUB, SBC]}


def vsg_cri(p):
    """Só em cirurgia vascular arterial (SBC 2024, Tabelas 6 e 7)."""
    if not CIRURGIAS[p['cirurgia']]['vascular']:
        return None
    c, idade = p['condicoes'], p['idade']
    itens = []
    if idade >= 80:
        itens.append(('Idade ≥ 80 anos', 4))
    elif idade >= 70:
        itens.append(('Idade 70–79 anos', 3))
    elif idade >= 60:
        itens.append(('Idade 60–69 anos', 2))
    for chave, rotulo, pts in (('dac', 'Doença coronária', 2), ('ic', 'Insuficiência cardíaca', 2),
                               ('dpoc', 'DPOC', 2), ('tabagismo', 'Tabagismo', 1),
                               ('diabetes_insulina', 'Diabetes com insulina', 1)):
        if chave in c:
            itens.append((rotulo, pts))
    if (p['creatinina'] or 0) > 1.8:
        itens.append(('Creatinina > 1,8 mg/dL', 2))
    if _medicacao_com_classe(p, 'betabloqueador'):
        itens.append(('Betabloqueador crônico', 1))
    if c & {'stent', 'revascularizacao_cirurgica'}:
        itens.append(('Revascularização miocárdica prévia', -1))
    pontos = sum(pts for _, pts in itens)
    nivel = 'baixo' if pontos <= 4 else 'intermediario' if pontos <= 6 else 'alto'
    return {'nome': 'VSG-CRI', 'valor': pontos, 'nivel': nivel,
            'faixa': {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}[nivel],
            'itens': [f'{n} ({pts:+d})' for n, pts in itens],
            'falta': [] if p['creatinina'] is not None else ['creatinina'],
            'nota': 'Recomendado pela SBC para cirurgia vascular arterial.',
            'referencias': [VSG, SBC]}


def capacidade_funcional(p):
    """Duas perguntas: dois lances de escada (SBC 2024 I-B) e DASI (AHA 2026 2a; ≤ 34 = capacidade baixa)."""
    dasi = round(sum(DASI_ITENS[i][1] for i in p['dasi']), 2) if (p['dasi'] or p['dasi_respondido']) else None
    mets = round((0.43 * dasi + 9.6) / 3.5, 1) if dasi is not None else None
    escadas = p['escadas']
    baixa_dasi = dasi is not None and dasi <= 34
    baixa_escadas = escadas == 'nao'
    if dasi is None and escadas in (None, 'nao_sabe'):
        estado = 'desconhecida'
    elif baixa_dasi or baixa_escadas:
        estado = 'baixa'
    else:
        estado = 'boa'
    detalhe = []
    if dasi is not None:
        detalhe.append(f'DASI {_br(dasi)} (≈ {_br(mets)} METs)')
    if escadas == 'sim':
        detalhe.append('sobe 2 lances de escada')
    elif escadas == 'nao':
        detalhe.append('não sobe 2 lances de escada')
    discordante = dasi is not None and escadas in ('sim', 'nao') and baixa_dasi != baixa_escadas
    return {'nome': 'Capacidade funcional', 'estado': estado, 'dasi': dasi, 'mets': mets,
            'valor': {'boa': 'Boa', 'baixa': 'Baixa', 'desconhecida': 'Desconhecida'}[estado],
            'nivel': {'boa': 'baixo', 'baixa': 'alto', 'desconhecida': 'intermediario'}[estado],
            'itens': detalhe,
            'nota': ('A pergunta das escadas e o DASI discordam; vale a capacidade mais baixa. O corte do DASI (34) '
                     'corresponde a cerca de 7 METs, mais exigente que os 4 METs das escadas.') if discordante else
                    ('Capacidade desconhecida conta como baixa (AHA 2026).' if estado == 'desconhecida' else ''),
            'referencias': [DASI, AHA, SBC]}


def ariscat(p):
    cir = CIRURGIAS[p['cirurgia']]
    itens, falta = [], []
    idade = p['idade']
    if idade > 80:
        itens.append(('Idade > 80 anos', 16))
    elif idade > 50:
        itens.append(('Idade 51–80 anos', 3))
    spo2 = p['spo2']
    if spo2 is None:
        falta.append('SpO₂')
    elif spo2 <= 90:
        itens.append(('SpO₂ ≤ 90%', 24))
    elif spo2 <= 95:
        itens.append(('SpO₂ 91–95%', 8))
    if p['infeccao_respiratoria']:
        itens.append(('Infecção respiratória no último mês', 17))
    if p['hemoglobina'] is None:
        falta.append('hemoglobina')
    elif p['hemoglobina'] <= 10:
        itens.append(('Hemoglobina ≤ 10 g/dL', 11))
    if cir['incisao'] == 'abdome_superior':
        itens.append(('Incisão em abdome superior', 15))
    elif cir['incisao'] == 'intratoracica':
        itens.append(('Incisão intratorácica', 24))
    if p['duracao'] is None:
        falta.append('duração da cirurgia')
    elif p['duracao'] == '2_3h':
        itens.append(('Duração de 2 a 3 h', 16))
    elif p['duracao'] == 'mais_3h':
        itens.append(('Duração > 3 h', 23))
    if p['urgencia'] == 'emergencia':
        itens.append(('Cirurgia de emergência', 8))
    pontos = sum(pts for _, pts in itens)
    nivel = 'baixo' if pontos < 26 else 'intermediario' if pontos < 45 else 'alto'
    taxa = {'baixo': '1,6%', 'intermediario': '13,3%', 'alto': '42,1%'}[nivel]
    return {'nome': 'ARISCAT', 'valor': pontos, 'nivel': nivel,
            'faixa': {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}[nivel],
            'itens': [f'{n} ({pts})' for n, pts in itens],
            'nota': f'Complicação pulmonar pós-operatória na validação: {taxa}.', 'falta': falta,
            'referencias': [ARISCAT]}


def stop_bang(p):
    itens = [STOP_BANG_ITENS[i] for i in ('ronco', 'cansaco', 'apneia_observada', 'imc_35', 'pescoco_40')
             if i in p['stop_bang']]
    if 'hipertensao' in p['condicoes']:
        itens.append('Hipertensão')
    if p['idade'] > 50:
        itens.append('Idade > 50 anos')
    if p['sexo'] == 'masculino':
        itens.append('Sexo masculino')
    pontos = len(itens)
    stop = len(p['stop_bang'] & {'ronco', 'cansaco', 'apneia_observada'}) + ('hipertensao' in p['condicoes'])
    alto = pontos >= 5 or (pontos >= 3 and stop >= 2 and (p['sexo'] == 'masculino' or p['stop_bang'] & {'imc_35', 'pescoco_40'}))
    nivel = 'alto' if alto else 'intermediario' if pontos >= 3 else 'baixo'
    return {'nome': 'STOP-Bang', 'valor': pontos, 'nivel': nivel,
            'faixa': {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}[nivel],
            'itens': itens, 'nota': 'Risco de apneia obstrutiva do sono moderada a grave. Itens não marcados contam como "não".',
            'referencias': [STOPBANG, AHA]}


def fragilidade(p):
    if p['cfs'] is None:
        return None
    cfs = int(p['cfs'])
    nivel = 'baixo' if cfs <= 3 else 'intermediario' if cfs == 4 else 'alto'
    return {'nome': 'Fragilidade (CFS)', 'valor': cfs, 'nivel': nivel,
            'faixa': {'baixo': 'Robusto', 'intermediario': 'Pré-frágil', 'alto': 'Frágil'}[nivel],
            'itens': [], 'nota': 'SBC 2024: 1–3 robusto, 4 pré-frágil, ≥ 5 frágil.', 'referencias': [CFS, SBC, AHA]}


def _br(numero):
    texto = f'{numero:.2f}'.rstrip('0').rstrip('.') if isinstance(numero, float) else str(numero)
    return texto.replace('.', ',')


# ── Exames ───────────────────────────────────────────────────────────────────

def _item(titulo, categoria, estado, motivo, aha='', sbc='', outra='', refs=(), divergencia='', grupo=''):
    return {'titulo': titulo, 'categoria': categoria, 'estado': estado, 'motivo': motivo, 'aha': aha, 'sbc': sbc,
            'outra': outra, 'referencias': list(refs), 'divergencia': divergencia, 'grupo': grupo}


def _ha_meses(meses):
    meses = int(meses)
    return 'há menos de 1 mês' if meses < 1 else 'há 1 mês' if meses == 1 else f'há {meses} meses'


def _feito(p, titulo):
    """(meses, data) do exame mais recente que cobre o título, ou None."""
    from src.utils import periodicidade
    alvo = periodicidade.chaves(titulo)
    achados = [(meses, data) for chaves, meses, data in p['exames_feitos'] if chaves & alvo]
    return min(achados) if achados else None


def _feito_ha(p, titulo):
    achado = _feito(p, titulo)
    return achado[0] if achado else None


def aplicar_exames_anteriores(p, anteriores, hoje=None):
    """Exames já realizados (lidos por periodicidade.ler_exames_anteriores): datas e resultados para o motor.

    O resultado digitado no formulário vale; sem ele, entra o do exame mais recente.
    """
    from src.utils import periodicidade
    hoje = hoje or date.today()
    mais_recente = {}
    for exame in anteriores or []:
        meses = max(0, (hoje - exame['data']).days // 30)
        p['exames_feitos'].append((periodicidade.chaves(exame['exame']), meses, exame['data'].strftime('%d/%m/%Y')))
        for item in exame.get('resultados') or []:
            campo = item.get('campo')
            if campo not in ('creatinina', 'hemoglobina', 'hba1c'):
                continue
            try:
                valor = float(str(item['valor']).replace('.', '').replace(',', '.'))
            except (KeyError, ValueError):
                continue
            if campo not in mais_recente or exame['data'] > mais_recente[campo][0]:
                mais_recente[campo] = (exame['data'], valor, meses)
    for campo in ('creatinina', 'hemoglobina'):
        if p.get(campo) is None and campo in mais_recente:
            p[campo] = mais_recente[campo][1]
    if p.get('hba1c_meses') is None:
        hba1c = _feito_ha(p, 'Hemoglobina glicada (HbA1c), soro')
        if hba1c is not None:
            p['hba1c_meses'] = hba1c
    return p


def exames(p, ctx):
    """Exames sugeridos ('indicado'), a considerar ('considerar') e não indicados ('nao_indicado')."""
    c, sint, idade = p['condicoes'], p['sintomas'], p['idade']
    cir = CIRURGIAS[p['cirurgia']]
    cir_ia = cir['risco'] != 'baixo'                     # SBC/ESC: cirurgia de risco intermediário ou alto
    cir_elev = ctx['cir_elev']                            # AHA: cirurgia de risco elevado
    pac_ia = ctx['pac_ia']                                # SBC: risco intermediário/alto pelo algoritmo
    dcv = ctx['dcv']
    emergencia = p['urgencia'] == 'emergencia'
    saida = []
    if emergencia:
        return [_item('Exames que atrasem a cirurgia', 'outro', 'nao_indicado',
                      'Cirurgia de emergência: nenhum exame que atrase a operação.', aha='Tabela 2', sbc='Seção 2.1.2',
                      refs=[AHA, SBC])]

    # ECG de repouso
    aha_ecg = ('2a' if (dcv or sint) and cir_elev else '2b' if cir_elev else '3: sem benefício' if not sint else '')
    motivos_sbc = []
    if dcv or sint:
        motivos_sbc.append(('I', 'história ou exame sugestivos de doença cardiovascular'))
    if cir_ia:
        motivos_sbc.append(('I', 'cirurgia de risco intermediário ou alto'))
    if pac_ia:
        motivos_sbc.append(('I', 'risco intermediário ou alto pelo escore'))
    if 'diabetes' in c:
        motivos_sbc.append(('I', 'diabetes'))
    if 'obesidade' in c:
        motivos_sbc.append(('IIa', 'obesidade'))
    if idade > 40:
        motivos_sbc.append(('IIa', 'idade acima de 40 anos'))
    sbc_ecg = 'I' if any(cl == 'I' for cl, _ in motivos_sbc) else 'IIa' if motivos_sbc else 'III'
    indicado = aha_ecg in ('2a', '2b') or sbc_ecg in ('I', 'IIa')
    div = ''
    if aha_ecg.startswith('3') and sbc_ecg in ('I', 'IIa'):
        div = (f'A AHA não recomenda ECG de rotina em assintomático antes de cirurgia de baixo risco; a SBC indica '
               f'({motivos_sbc[0][1]}). Nós optamos por sugerir o ECG, sinalizando a diferença.')
    elif aha_ecg in ('2a', '2b') and sbc_ecg == 'I':
        div = f'Classe I na SBC e {aha_ecg} na AHA.'
    elif not aha_ecg and sbc_ecg in ('I', 'IIa'):
        div = 'Indicado pela SBC; a AHA não tem recomendação para este perfil.'
    feito = _feito_ha(p, 'Eletrocardiograma de repouso')
    estado = 'indicado' if indicado else 'nao_indicado'
    motivo = '; '.join(m for _, m in motivos_sbc) or 'Assintomático em cirurgia de baixo risco.'
    if indicado and feito is not None and feito < 12 and not sint:
        estado, motivo = 'ja_feito', f'Feito {_ha_meses(feito)}, sem sintomas novos: pode valer o atual.'
    saida.append(_item('Eletrocardiograma de repouso', 'imagem', estado, motivo, aha=aha_ecg or '—', sbc=sbc_ecg,
                       refs=[AHA, SBC], divergencia=div))

    # Ecocardiograma transtorácico
    sint_ic = bool(sint & {'dispneia', 'sinais_ic'})
    aha_eco, sbc_eco, motivo = '', '', ''
    if sint_ic:
        aha_eco, motivo = '1', 'Dispneia nova ou sinais de insuficiência cardíaca.'
        sbc_eco = 'I' if cir_ia else ''
    elif 'sopro' in sint or 'valvopatia' in c:
        aha_eco, motivo = '1', 'Suspeita ou valvopatia moderada a grave conhecida.'
        sbc_eco = 'I' if cir_ia else ''
    elif 'protese_mecanica' in c and cir_ia:
        sbc_eco, motivo = 'IIa', 'Prótese valvar, sem ecocardiograma no último ano.'
    elif cir['risco'] == 'alto':
        aha_eco, sbc_eco = '3: sem benefício', 'IIb'
        motivo = 'Assintomático antes de cirurgia de alto risco.'
    else:
        aha_eco, sbc_eco = '3: sem benefício', 'III'
        motivo = 'Assintomático e estável: ecocardiograma de rotina não muda a conduta.'
    if aha_eco in ('1', '2a') or sbc_eco in ('I', 'IIa'):
        estado = 'indicado'
    elif sbc_eco == 'IIb':
        estado = 'considerar'
    else:
        estado = 'nao_indicado'
    div = ''
    if sbc_eco == 'IIb' and aha_eco.startswith('3'):
        div = 'Assintomático antes de cirurgia de alto risco: a SBC admite (IIb); a AHA não vê benefício.'
    elif aha_eco == '1' and not sbc_eco:
        div = 'A AHA indica em qualquer cirurgia; a SBC restringe a cirurgias de risco intermediário ou alto.'
    feito = _feito_ha(p, 'Ecocardiograma transtorácico')
    if estado == 'indicado' and feito is not None and feito < 12 and not sint_ic and 'sopro' not in sint:
        estado, motivo = 'ja_feito', f'Feito {_ha_meses(feito)}, sem piora clínica: pode valer o atual.'
    saida.append(_item('Ecocardiograma transtorácico', 'imagem', estado, motivo, aha=aha_eco or '—',
                       sbc=sbc_eco or '—', refs=[AHA, SBC], divergencia=div))

    # BNP / NT-proBNP
    aha_bnp = '2a' if (dcv or idade >= 65 or (idade >= 45 and sint)) and cir_elev else ''
    fr_icfep = bool(c & {'diabetes', 'hipertensao', 'dac', 'obesidade', 'fa'})
    sbc_bnp = 'I' if cir_ia and (idade > 65 or (45 <= idade <= 64 and (dcv or fr_icfep))) else ''
    if aha_bnp or sbc_bnp:
        div = ''
        if sbc_bnp and not aha_bnp:
            div = ('A SBC indica (classe I) a partir de 65 anos ou de 45 com fator de risco; a AHA só com doença '
                   'cardiovascular, 65 anos ou mais, ou sintomas, em cirurgia de risco elevado.')
        elif aha_bnp and not sbc_bnp:
            div = 'A AHA indica (2a); pelos critérios da SBC não haveria indicação.'
        elif aha_bnp and sbc_bnp:
            div = 'Classe I na SBC e 2a na AHA.'
        saida.append(_item('Peptídeo natriurético BNP/PROBNP', 'laboratorio', 'indicado',
                           'Estratifica o risco: BNP > 92 ng/L ou NT-proBNP ≥ 300 ng/L indicam risco aumentado.',
                           aha=aha_bnp or '—', sbc=sbc_bnp or '—', refs=[AHA, SBC], divergencia=div))

    # Troponina (antes e 24/48 h depois)
    aha_tn_pre = '2b' if (dcv or idade >= 65 or (idade >= 45 and sint)) and cir_elev else ''
    sbc_tn = 'I' if pac_ia and cir_ia else ''
    if aha_tn_pre or sbc_tn:
        div = 'Classe I na SBC e 2b na AHA.' if aha_tn_pre and sbc_tn else (
            'Indicada só pela SBC (risco intermediário ou alto pelo escore em cirurgia de risco intermediário ou alto).'
            if sbc_tn else 'Indicada só pela AHA (2b); pela SBC o paciente é de baixo risco.')
        saida.append(_item('Troponina, soro', 'laboratorio', 'indicado',
                           'Dosagem antes da cirurgia e com 24 e 48 h depois, para detectar injúria miocárdica.',
                           aha=aha_tn_pre or '—', sbc=sbc_tn or '—', refs=[AHA, SBC], divergencia=div))
    elif not cir_ia:
        saida.append(_item('Troponina, soro', 'laboratorio', 'nao_indicado', 'Cirurgia de baixo risco.',
                           aha='3: sem benefício', sbc='III', refs=[AHA, SBC]))

    # Prova funcional e angio-TC: só risco elevado com capacidade baixa ou desconhecida, se mudar a conduta
    if ctx['investigar_isquemia']:
        if p['urgencia'] == 'urgencia':
            saida.append(_item('Prova funcional para isquemia', 'outro', 'nao_indicado',
                               'Cirurgia de urgência: o resultado não mudaria a conduta.', aha='—', sbc='—',
                               refs=[SBC]))
        else:
            div = 'Prova funcional com imagem: SBC IIa; AHA 2b.'
            saida.append(_item('Cintilografia de perfusão miocárdica (estresse e repouso)', 'imagem', 'considerar',
                               'Só se o resultado puder mudar a conduta (revascularização ou adiar a cirurgia).',
                               aha='2b', sbc='IIa', refs=[AHA, SBC], divergencia=div, grupo='isquemia'))
            saida.append(_item('Ecocardiograma de estresse com dobutamina', 'imagem', 'considerar',
                               'Alternativa à cintilografia, com o mesmo critério.', aha='2b', sbc='IIa',
                               refs=[AHA, SBC], divergencia=div, grupo='isquemia'))
            saida.append(_item('Angiotomografia de coronárias', 'imagem', 'considerar',
                               'Procura anatomia de alto risco (tronco ≥ 50% ou triarterial ≥ 70%).', aha='2b',
                               sbc='—', refs=[AHA, SBC],
                               divergencia='Admitida pela AHA (2b); a SBC não a recomenda para estratificar o risco.',
                               grupo='isquemia'))
    elif cir_ia or cir_elev:
        saida.append(_item('Prova funcional ou angiotomografia de coronárias', 'outro', 'nao_indicado',
                           'Risco baixo pelo escore ou boa capacidade funcional: sem benefício.',
                           aha='3: sem benefício', sbc='III', refs=[AHA, SBC]))
    if cir_ia or cir_elev:
        saida.append(_item('Cateterismo cardíaco de rotina', 'outro', 'nao_indicado',
                           'Só com as mesmas indicações de fora da cirurgia (SCA, isquemia extensa).',
                           aha='3: sem benefício', sbc='III', refs=[AHA, SBC]))

    # HbA1c
    if 'diabetes' in c and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        meses = p['hba1c_meses']
        if meses is not None and meses <= 3:
            saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'ja_feito',
                               f'Feita {_ha_meses(meses)} (vale até 3 meses).', aha='2a', refs=[AHA]))
        else:
            saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'indicado',
                               'Diabetes, sem HbA1c nos últimos 3 meses.', aha='2a', sbc='—', refs=[AHA]))

    # Exames laboratoriais de rotina (NICE NG45): pelo porte da cirurgia e pela classe ASA
    asa, porte = p['asa'], cir['porte']
    renal = 'doenca_renal' in c
    if porte == 'maior' or (porte == 'intermediaria' and asa and asa >= 3 and (dcv or renal)):
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'indicado',
                           'Cirurgia de grande porte.' if porte == 'maior' else 'ASA ≥ 3 com doença cardiovascular ou renal.',
                           outra='NICE', refs=[NICE]))
    elif p['hemoglobina'] is None:
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'considerar',
                           'A hemoglobina entra no AUB-HAS2 e no ARISCAT.', outra='Escores', refs=[AUB, ARISCAT]))
    meds = ctx['classes_medicacoes']
    usa_renal = bool(meds & {'ieca_bra', 'arni', 'tiazidico', 'diuretico_alca', 'espironolactona', 'doac', 'metformina',
                             'isglt2'})
    if (porte == 'maior' and asa and asa >= 2) or (porte == 'intermediaria' and asa and asa >= 3) or renal:
        saida.append(_item('Creatinina, soro', 'laboratorio', 'indicado', 'Porte da cirurgia e classe ASA.',
                           outra='NICE', refs=[NICE]))
        saida.append(_item('Sódio e potássio, soro', 'laboratorio', 'indicado', 'Junto da função renal.',
                           outra='NICE', refs=[NICE]))
    elif p['creatinina'] is None or usa_renal:
        motivo = ('Necessária para o RCRI e a depuração (Cockcroft-Gault).' if p['creatinina'] is None
                  else 'Medicamento que depende da função renal.')
        saida.append(_item('Creatinina, soro', 'laboratorio', 'indicado' if usa_renal else 'considerar', motivo,
                           outra='NICE' if usa_renal else 'Escores', refs=[NICE] if usa_renal else [LEE, CG]))
    if 'varfarina' in ctx['classes_medicacoes']:
        saida.append(_item('Tempo de protrombina (TP/INR), plasma', 'laboratorio', 'indicado',
                           'Uso de varfarina: INR antes da cirurgia.', outra='NICE', refs=[NICE, SBC]))
    elif 'hepatopatia' in c and asa and asa >= 3 and porte != 'menor':
        saida.append(_item('Coagulograma (TP/INR e TTPa)', 'laboratorio', 'indicado',
                           'Hepatopatia crônica, ASA ≥ 3.', outra='NICE', refs=[NICE]))
    else:
        saida.append(_item('Coagulograma (TP/INR e TTPa)', 'laboratorio', 'nao_indicado',
                           'Sem anticoagulante nem hepatopatia: não é exame de rotina.', outra='NICE', refs=[NICE]))
    if cir['urologica']:
        saida.append(_item('Urina tipo I (EAS)', 'laboratorio', 'considerar',
                           'Cirurgia urológica: se uma infecção urinária mudar a decisão de operar.', outra='NICE',
                           refs=[NICE]))
    saida.append(_item('Radiografia de tórax', 'imagem', 'nao_indicado',
                       'Não é exame de rotina; só com sinais ou sintomas cardiopulmonares novos.', outra='NICE · ACP',
                       refs=[NICE, ACP]))
    if p['sexo'] == 'feminino' and idade <= 55:
        saida.append(_item('Beta-hCG, soro', 'laboratorio', 'considerar',
                           'Perguntar sobre gravidez; testar, com consentimento, se houver dúvida.', outra='NICE',
                           refs=[NICE]))
    for item in saida:
        achado = _feito(p, item['titulo']) if item['categoria'] != 'outro' else None
        if achado:
            item['ultimo'] = f'Último em {achado[1]} ({_ha_meses(achado[0])})'
    return saida


# ── Indicação, adiamentos e pós-operatório ──────────────────────────────────

def _passo(pergunta, resposta, estado, texto):
    return {'pergunta': pergunta, 'resposta': resposta, 'estado': estado, 'texto': texto}


def adiamentos(p):
    """Situações em que a cirurgia eletiva deve esperar (ou que pedem discussão), com classe."""
    saida = []
    eletiva = p['urgencia'] in ('eletiva', 'tempo_sensivel')
    for chave in sorted(p['instaveis']):
        saida.append({'titulo': INSTAVEIS[chave],
                      'texto': 'Condição grave ou instável: estabilizar antes; adiar a cirurgia eletiva.',
                      'classe': 'SBC Tabela 2', 'referencias': [SBC, AHA], 'divergencia': ''})
    st = p['stent']
    if st and st.get('meses') is not None:
        m, tipo, ind = st['meses'], st.get('tipo'), st.get('indicacao')
        if tipo == 'balao' and m < 0.5:
            saida.append({'titulo': 'Angioplastia com balão há menos de 14 dias',
                          'texto': 'Esperar pelo menos 14 dias para a cirurgia eletiva.', 'classe': 'AHA 1',
                          'referencias': [AHA], 'divergencia': 'A SBC não aborda angioplastia só com balão.'})
        elif tipo in ('farmacologico', 'convencional') and m < 1:
            saida.append({'titulo': 'Stent há menos de 30 dias',
                          'texto': 'Cirurgia eletiva que interrompa antiagregante é potencialmente danosa: adiar.',
                          'classe': 'AHA 3: dano · SBC III', 'referencias': [AHA, SBC], 'divergencia': ''})
        elif tipo == 'farmacologico' and ind == 'sca' and m < 12:
            sbc = 'IIa' if m >= 6 else 'IIb'
            saida.append({'titulo': f'Stent farmacológico por SCA {_ha_meses(m)}',
                          'texto': ('O ideal é esperar 12 meses para cirurgia eletiva que interrompa antiagregante. '
                                    f'Entre 6 e 12 meses (SBC IIa) ou de 30 dias a 6 meses (SBC IIb), só com discussão '
                                    'multidisciplinar e mantendo o AAS.'),
                          'classe': f'AHA 1 (≥ 12 meses) · SBC {sbc} na faixa atual', 'referencias': [AHA, SBC],
                          'divergencia': 'A SBC gradua as faixas intermediárias; a AHA só a de 3 meses em cirurgia '
                                         'tempo-sensível (2b).'})
        elif tipo == 'farmacologico' and ind == 'dac_cronica' and m < 6:
            sbc = 'IIa' if m >= 3 else 'IIb'
            saida.append({'titulo': f'Stent farmacológico por doença coronária crônica {_ha_meses(m)}',
                          'texto': ('O ideal é esperar 6 meses para cirurgia eletiva que interrompa antiagregante; '
                                    'em cirurgia tempo-sensível, a partir de 3 meses se o atraso for mais arriscado.'),
                          'classe': f'AHA 2a (≥ 6 meses) · SBC {sbc} na faixa atual', 'referencias': [AHA, SBC],
                          'divergencia': 'Esperar 6 meses: SBC I-A; AHA 2a.'})
        elif tipo in ('farmacologico', 'convencional', 'balao'):
            nome = {'farmacologico': 'Stent farmacológico', 'convencional': 'Stent convencional',
                    'balao': 'Angioplastia com balão'}[tipo]
            saida.append({'titulo': f'{nome} {_ha_meses(m)}: fora do período de maior risco', 'ok': True,
                          'texto': 'O intervalo mínimo para cirurgia eletiva já passou. Manter o AAS.',
                          'classe': 'AHA · SBC', 'referencias': [AHA, SBC], 'divergencia': ''})
    elif st:
        saida.append({'titulo': 'Data da angioplastia não informada',
                      'texto': 'Sem a data não dá para saber se a cirurgia eletiva precisa esperar '
                               '(14 dias após balão; 6 meses após stent farmacológico por doença crônica; 12 meses por SCA).',
                      'classe': 'AHA · SBC', 'referencias': [AHA, SBC], 'divergencia': ''})
    if 'avc_ait_recente' in p['condicoes'] and eletiva:
        saida.append({'titulo': 'AVC ou AIT há menos de 3 meses',
                      'texto': 'Adiar a cirurgia eletiva para pelo menos 3 meses depois do evento.',
                      'classe': 'AHA 2a', 'referencias': [AHA], 'divergencia': ''})
    if p['pas'] and p['pad'] and (p['pas'] >= 180 or p['pad'] >= 110) and eletiva:
        saida.append({'titulo': f'PA {int(p["pas"])} × {int(p["pad"])} mmHg',
                      'texto': 'Hipertensão não controlada: adiar a cirurgia eletiva e controlar a pressão.',
                      'classe': 'SBC I (cirurgia de alto risco) · AHA 2b', 'referencias': [SBC, AHA],
                      'divergencia': 'A SBC adia (I-C) em cirurgia de alto risco; a AHA "pode considerar" (2b) em '
                                     'cirurgia de risco elevado com fator de risco do RCRI.'})
    return saida


def avaliar(p):
    """Resultado completo da avaliação pré-operatória."""
    from src.utils.medicamentos import classes_de
    cir = CIRURGIAS[p['cirurgia']]
    c = p['condicoes']
    escore_rcri, escore_aub, escore_vsg = rcri(p), aub_has2(p), vsg_cri(p)
    cap = capacidade_funcional(p)
    dcv = bool(c & {'dac', 'ic', 'avc_ait', 'fa', 'valvopatia', 'doenca_arterial_periferica', 'protese_mecanica',
                    'hipertensao_pulmonar', 'marcapasso_cdi'})
    elevado_por = []
    if escore_rcri['valor'] >= 2:
        elevado_por.append(f'RCRI {escore_rcri["valor"]}')
    if escore_aub['valor'] >= 2:
        elevado_por.append(f'AUB-HAS2 {escore_aub["valor"]}')
    if escore_vsg and escore_vsg['valor'] >= 5:
        elevado_por.append(f'VSG-CRI {escore_vsg["valor"]}')
    pac_ia = bool(elevado_por)
    cir_elev = cir['risco'] != 'baixo' or pac_ia
    emergencia = p['urgencia'] == 'emergencia'
    adiar = adiamentos(p)

    passos, conclusao = [], None
    passos.append(_passo('Cirurgia de emergência?', 'Sim' if emergencia else 'Não', 'atencao' if emergencia else 'ok',
                         'Operar sem exames que atrasem a cirurgia; só monitorização e redução de risco.'))
    if emergencia:
        conclusao = ('emergencia', 'Cirurgia de emergência: sem avaliação que atrase a operação. Monitorização, '
                                   'troponina pós-operatória se houver risco e manejo dos medicamentos.')
    if not conclusao:
        inst = bool(p['instaveis'])
        passos.append(_passo('Condição cardiovascular grave ou instável?', 'Sim' if inst else 'Não',
                             'atencao' if inst else 'ok',
                             'SCA, IC descompensada, angina CCS III/IV, estenose aórtica ou mitral importante '
                             'sintomática, BAVT/TV, FA com FC > 120, PA > 180 × 110, HAP sintomática.'))
        if inst:
            conclusao = ('adiar', 'Condição grave ou instável: estabilizar e adiar a cirurgia eletiva; '
                                  'avaliação cardiológica indicada.')
    baixo_risco_cirurgia = cir['risco'] == 'baixo'
    if not conclusao:
        passos.append(_passo('Risco intrínseco da cirurgia', RISCO_DA_CIRURGIA[cir['risco']].split(' (')[0],
                             'ok' if baixo_risco_cirurgia else 'atencao',
                             'Baixo risco (< 1%) em paciente estável: não há avaliação cardiológica nem exames '
                             'cardíacos indicados.'))
        if baixo_risco_cirurgia:
            conclusao = ('nao_indicada', 'Cirurgia de baixo risco em paciente estável: avaliação cardiológica e exames '
                                         'cardíacos não indicados. Pode operar.')
    if not conclusao:
        passos.append(_passo('Risco do paciente pelos escores', 'Elevado' if pac_ia else 'Baixo',
                             'atencao' if pac_ia else 'ok',
                             'RCRI 0–1 e AUB-HAS2 0–1 (risco < 1%): liberar sem testes de isquemia.'))
        if not pac_ia:
            conclusao = ('nao_indicada', 'Risco baixo pelos escores: liberar sem investigação de isquemia.')
    investigar = False
    if not conclusao:
        estado = cap['estado']
        passos.append(_passo('Capacidade funcional', cap['valor'], 'ok' if estado == 'boa' else 'atencao',
                             '≥ 4 METs (sobe 2 lances) ou DASI > 34, sem sintomas: liberar sem prova funcional. '
                             'Baixa ou desconhecida: biomarcadores e, só se mudar a conduta, prova funcional.'))
        sint_isq = bool(p['sintomas'] & {'angina', 'dispneia'})
        if estado == 'boa' and not sint_isq:
            conclusao = ('nao_indicada', 'Risco elevado, mas boa capacidade funcional e sem sintomas: liberar sem '
                                         'prova funcional.')
        else:
            investigar = p['urgencia'] in ('eletiva', 'tempo_sensivel')
            motivos = [f'cirurgia de risco {RISCO_DA_CIRURGIA[cir["risco"]].split(" (")[0].lower()}',
                       ', '.join(elevado_por), f'capacidade funcional {cap["valor"].lower()}']
            conclusao = ('indicada', 'Avaliação cardiológica indicada: ' + '; '.join(m for m in motivos if m) + '.')
    if any(not a.get('ok') for a in adiar) and conclusao[0] in ('nao_indicada', 'indicada'):
        conclusao = (conclusao[0], conclusao[1] + ' Antes, veja o que pede adiamento.')

    classes_meds = set(classes_de(p['medicacoes']))
    ctx = {'cir_elev': cir_elev, 'pac_ia': pac_ia, 'dcv': dcv, 'investigar_isquemia': investigar,
           'classes_medicacoes': classes_meds}
    lista_exames = exames(p, ctx)

    escores = [escore_rcri, escore_aub]
    if escore_vsg:
        escores.append(escore_vsg)
    escores.append(cap)
    frag = fragilidade(p)
    if frag:
        escores.append(frag)
    depuracao = clcr(p)

    orientacoes = []
    if p['idade'] >= 65 and cir_elev and frag is None:
        orientacoes.append({'titulo': 'Avaliar fragilidade', 'texto': 'Com instrumento validado (CFS, FRAIL) em quem '
                            'tem 65 anos ou mais e vai a cirurgia de risco intermediário ou alto.',
                            'classe': 'AHA 2a · SBC IIa', 'referencias': [AHA, SBC, CFS]})
    sb = stop_bang(p)
    if 'tabagismo' in c and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        orientacoes.append({'titulo': 'Parar de fumar', 'texto': 'Parar 4 semanas ou mais antes reduz complicações '
                            'respiratórias e de cicatrização; parar mais perto da cirurgia não aumenta o risco.',
                            'classe': 'Metanálise', 'referencias': [TABAGISMO]})

    pulmonar = ariscat(p)
    medidas_pulmonares = []
    if pulmonar['nivel'] != 'baixo' or 'dpoc' in c:
        medidas_pulmonares.append({'titulo': 'Expansão pulmonar no pós-operatório',
                                   'texto': 'Fisioterapia respiratória, exercícios de respiração profunda ou '
                                            'incentivador.', 'classe': 'ACP 2006 (A)', 'referencias': [ACP]})
        medidas_pulmonares.append({'titulo': 'Sonda nasogástrica só quando necessária',
                                   'texto': 'Uso seletivo (náusea, distensão), não de rotina.',
                                   'classe': 'ACP 2006 (B)', 'referencias': [ACP]})

    pos = []
    if not emergencia or dcv:
        aha_tn = ('2b' if cir_elev and (dcv or p['sintomas'] or (p['idade'] >= 65 and c & {'hipertensao', 'diabetes',
                                                                                            'tabagismo', 'obesidade'}))
                  else '')
        sbc_tn = 'I' if pac_ia and cir['risco'] != 'baixo' else ''
        if aha_tn or sbc_tn:
            pos.append({'titulo': 'Troponina com 24 e 48 h', 'texto': 'Para detectar injúria miocárdica após a cirurgia.',
                        'classe': ' · '.join(x for x in (f'AHA {aha_tn}' if aha_tn else '', f'SBC {sbc_tn}' if sbc_tn else '') if x),
                        'referencias': [AHA, SBC]})
        if sbc_tn:
            pos.append({'titulo': 'ECG no 1º e no 2º dia', 'texto': 'Junto da troponina.', 'classe': 'SBC I',
                        'referencias': [SBC]})
            nivel = escore_rcri['nivel'] if escore_rcri['nivel'] != 'baixo' else 'intermediario'
            pos.append({'titulo': 'Unidade de terapia intensiva por 48 h',
                        'texto': 'Risco alto pelo escore.' if nivel == 'alto' else 'Risco intermediário pelo escore: considerar.',
                        'classe': 'SBC I' if nivel == 'alto' else 'SBC IIa', 'referencias': [SBC]})
    if 'hipertensao' in c:
        pos.append({'titulo': 'Reintroduzir os anti-hipertensivos', 'texto': 'Assim que clinicamente possível.',
                    'classe': 'AHA 1 · SBC I', 'referencias': [AHA, SBC]})
    pos.append({'titulo': 'Evitar hipotensão', 'texto': 'Manter PAM ≥ 60–65 mmHg ou PAS ≥ 90 mmHg e tratar a '
                'hipotensão no pós-operatório.', 'classe': 'AHA 1 · SBC I', 'referencias': [AHA, SBC]})

    return {
        'cirurgia': {'rotulo': cir['rotulo'], 'risco': RISCO_DA_CIRURGIA[cir['risco']],
                     'urgencia': URGENCIAS[p['urgencia']]},
        'indicacao': {'passos': passos, 'tipo': conclusao[0], 'conclusao': conclusao[1],
                      'referencias': [AHA, SBC],
                      'divergencia': ('A AHA recomenda o escore em quem tem doença cardiovascular conhecida (2a) e '
                                      'classifica o risco em baixo ou elevado (≥ 1%); a SBC calcula para todos, em '
                                      'baixo, intermediário ou alto. Nós optamos por calcular para todos e mostrar '
                                      'as duas classificações.')},
        'adiar': adiar,
        'escores': escores,
        'clcr': depuracao,
        'exames': lista_exames,
        'orientacoes': orientacoes,
        'pulmonar': {'escore': pulmonar, 'stop_bang': sb, 'medidas': medidas_pulmonares},
        'pos_operatorio': pos,
        'contexto': {'cir_elev': cir_elev, 'pac_ia': pac_ia, 'dcv': dcv},
    }
