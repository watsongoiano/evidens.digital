"""Avaliação pré-operatória de cirurgia não cardíaca: indicação de avaliação cardiológica, escores, exames e
cuidados pós-operatórios.

Referências-base, usadas em conjunto (com aviso quando divergem):
- AHA/ACC 2026 (reafirmação da diretriz de 2024, texto e recomendações idênticos): Guideline for Perioperative
  Cardiovascular Management for Noncardiac Surgery.
- SBC 2024: Diretriz de Avaliação Cardiovascular Perioperatória (Gualandro et al., Arq Bras Cardiol 2024;121(9)).
- Escores pelos artigos originais (RCRI, AUB-HAS2, VSG-CRI, DASI, ARISCAT, STOP-Bang, CFS, Cockcroft-Gault).
- Exames laboratoriais de rotina: NICE NG45 (2016). Risco pulmonar: ACP 2006 e ARISCAT.

Gupta NSQIP MICA: coeficientes conferidos na Tabela 2 do artigo original (Circulation 2011;124:381-387), incluindo
creatinina ausente (−0,10); não se aplica a oftalmologia, odontologia, endoscopia nem transplante (fora do NSQIP).
A classe de recomendação vem de cada diretriz; "AHA 1" e "SBC I" são as classes mais fortes de cada uma.
"""
from __future__ import annotations

import math
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
GUPTA = _ref('Gupta 2011 (NSQIP MICA)', 'https://doi.org/10.1161/CIRCULATIONAHA.110.015701')
CFS2 = _ref('Rockwood 2020 (CFS 2.0)', 'https://doi.org/10.5770/cgj.23.463')
NICE = _ref('NICE NG45', 'https://www.nice.org.uk/guidance/ng45/chapter/recommendations')
CHEST = _ref('CHEST 2022', 'https://doi.org/10.1016/j.chest.2022.07.025')
IDSA = _ref('IDSA 2019', 'https://doi.org/10.1093/cid/ciy1121')
SBC_ICP = _ref('SBC 2022 (ICP)', 'https://doi.org/10.36660/abc.20220039')
SASM = _ref('SASM 2016', 'https://doi.org/10.1213/ANE.0000000000001416')
PERISCOPE = _ref('Mazo 2014 (PERISCOPE)', 'https://doi.org/10.1097/ALN.0000000000000334')
COCHRANE_IS = _ref('Cochrane 2014 (incentivador)', 'https://doi.org/10.1002/14651858.CD006058.pub3')
COCHRANE_IMT = _ref('Cochrane 2015 (treino inspiratório)', 'https://doi.org/10.1002/14651858.CD010356.pub2')
TABAGISMO = _ref('Wong 2012', 'https://doi.org/10.1007/s12630-011-9652-x')
CAROTIDA_AHA = _ref('AHA/ASA 2021 (prevenção secundária do AVC)', 'https://doi.org/10.1161/STR.0000000000000375')
CAROTIDA_ESVS = _ref('ESVS 2023 (doença carotídea)', 'https://doi.org/10.1016/j.ejvs.2022.04.011')
SBD = _ref('SBD/SBA/ABESO 2026 (Diabetol Metab Syndr 2026;18:91)', 'https://doi.org/10.1186/s13098-025-02060-5')

# ── Cirurgias ────────────────────────────────────────────────────────────────
# risco: risco intrínseco de morte CV, IAM ou AVC em 30 dias (SBC 2024 Tabela 3 = ESC 2022 Tabela 5).
# rcri: cirurgia intraperitoneal, intratorácica ou vascular suprainguinal (Lee 1999).
# vascular: cirurgia vascular arterial (AUB-HAS2; ativa o VSG-CRI, recomendado pela SBC para esses casos).
# incisao: ARISCAT (periferica, abdome_superior, intratoracica). porte: grau cirúrgico do NICE NG45.
# endourologica: rastrear bacteriúria antes (IDSA 2019). ariscat: False onde o ARISCAT não foi derivado (anestesia só
# local ou bloqueio periférico, ambulatoriais, transplantes; Canet 2010).
# mica: categoria do procedimento no Gupta NSQIP MICA (None = sem categoria ou fora do NSQIP).
_C = lambda rotulo, risco, rcri, incisao, porte, vascular=False, urologica=False, endourologica=False, ariscat=True, mica=None: {  # noqa: E731
    'rotulo': rotulo, 'risco': risco, 'rcri': rcri, 'incisao': incisao, 'porte': porte, 'vascular': vascular,
    'urologica': urologica, 'endourologica': endourologica, 'ariscat': ariscat, 'mica': mica}

CIRURGIAS = {
    # Baixo risco (< 1%)
    'catarata': _C('Oftalmológica (catarata e outras)', 'baixo', False, 'periferica', 'menor', ariscat=False),
    'odontologica': _C('Odontológica', 'baixo', False, 'periferica', 'menor', ariscat=False),
    'endoscopia': _C('Endoscopia ou colonoscopia', 'baixo', False, 'periferica', 'menor', ariscat=False),
    'pele': _C('Superficial (pele e partes moles, biópsia)', 'baixo', False, 'periferica', 'menor', ariscat=False, mica='pele'),
    'mama': _C('Mama', 'baixo', False, 'periferica', 'intermediaria', mica='mama'),
    'tireoide': _C('Tireoide ou paratireoide', 'baixo', False, 'periferica', 'maior', mica='pescoco'),
    'ginecologica_menor': _C('Ginecológica menor', 'baixo', False, 'periferica', 'intermediaria', mica='obstetrica_ginecologica'),
    'ortopedica_menor': _C('Ortopédica menor (artroscopia, menisco)', 'baixo', False, 'periferica', 'intermediaria', mica='ortopedica'),
    'plastica': _C('Reconstrutiva ou plástica', 'baixo', False, 'periferica', 'intermediaria', mica='pele'),
    'rtu': _C('Urológica menor (RTU de próstata ou bexiga)', 'baixo', False, 'periferica', 'maior',
              urologica=True, endourologica=True, mica='urologia'),
    'vats_menor': _C('Videotoracoscopia com ressecção pulmonar menor', 'baixo', True, 'intratoracica', 'maior', mica='toracica'),
    'hernia': _C('Hérnia inguinal ou umbilical', 'baixo', False, 'periferica', 'intermediaria', mica='hernia'),
    # Intermediário (1–5%)
    'carotida_assintomatica': _C('Carótida assintomática (endarterectomia ou stent)', 'intermediario', False,
                                 'periferica', 'maior', vascular=True, mica='vascular_periferica'),
    'endarterectomia_sintomatica': _C('Endarterectomia de carótida sintomática', 'intermediario', False,
                                      'periferica', 'maior', vascular=True, mica='vascular_periferica'),
    'evar': _C('Aneurisma de aorta por via endovascular (EVAR)', 'intermediario', True, 'periferica', 'maior',
               vascular=True, mica='aortica'),
    'angioplastia_periferica': _C('Angioplastia arterial periférica', 'intermediario', False, 'periferica',
                                  'intermediaria', vascular=True, mica='vascular_periferica'),
    'cabeca_pescoco': _C('Cabeça e pescoço', 'intermediario', False, 'periferica', 'maior', mica='orl'),
    'colecistectomia': _C('Intraperitoneal: colecistectomia, hérnia hiatal, esplenectomia', 'intermediario', True,
                          'abdome_superior', 'maior', mica='gbaas'),
    'colectomia': _C('Intraperitoneal: colectomia ou outra cirurgia intestinal', 'intermediario', True,
                     'abdome_superior', 'maior', mica='intestinal'),
    'intratoracica': _C('Intratorácica não maior', 'intermediario', True, 'intratoracica', 'maior', mica='toracica'),
    'coluna': _C('Coluna', 'intermediario', False, 'periferica', 'maior', mica='coluna'),
    'neurocirurgia': _C('Neurocirurgia intracraniana', 'intermediario', False, 'periferica', 'maior', mica='cerebral'),
    'quadril': _C('Ortopédica maior (quadril, joelho, artroplastia)', 'intermediario', False, 'periferica', 'maior', mica='ortopedica'),
    'transplante_renal': _C('Transplante renal', 'intermediario', False, 'periferica', 'maior', urologica=True,
                            ariscat=False),
    'urologica_maior': _C('Urológica maior (prostatectomia, nefrectomia)', 'intermediario', True, 'periferica',
                          'maior', urologica=True, mica='urologia'),
    'ginecologica_maior': _C('Ginecológica maior (histerectomia abdominal)', 'intermediario', True, 'periferica',
                             'maior', mica='obstetrica_ginecologica'),
    # Alto (> 5%)
    'adrenal': _C('Ressecção de adrenal', 'alto', True, 'abdome_superior', 'maior', mica='gbaas'),
    'aorta_aberta': _C('Aorta ou cirurgia vascular maior aberta', 'alto', True, 'abdome_superior', 'maior',
                       vascular=True, mica='aortica'),
    'stent_carotida_sintomatica': _C('Stent de carótida sintomática', 'alto', False, 'periferica', 'maior',
                                     vascular=True, mica='vascular_periferica'),
    'revascularizacao_mmii': _C('Revascularização aberta de membro inferior ou amputação', 'alto', False,
                                'periferica', 'maior', vascular=True, mica='vascular_periferica'),
    'pancreas': _C('Duodenopancreatectomia', 'alto', True, 'abdome_superior', 'maior', mica='foregut_hpb'),
    'figado': _C('Ressecção hepática ou de vias biliares', 'alto', True, 'abdome_superior', 'maior', mica='foregut_hpb'),
    'esofagectomia': _C('Esofagectomia', 'alto', True, 'intratoracica', 'maior', mica='foregut_hpb'),
    'pneumectomia': _C('Pneumectomia', 'alto', True, 'intratoracica', 'maior', mica='toracica'),
    'transplante_hepatico': _C('Transplante hepático', 'alto', True, 'abdome_superior', 'maior', ariscat=False),
    'transplante_pulmonar': _C('Transplante pulmonar', 'alto', True, 'intratoracica', 'maior', ariscat=False),
    'perfuracao_intestinal': _C('Reparo de perfuração intestinal', 'alto', True, 'abdome_superior', 'maior', mica='intestinal'),
    'cistectomia': _C('Cistectomia total', 'alto', True, 'periferica', 'maior', urologica=True, mica='urologia'),
}
# Gupta NSQIP MICA, Tabela 2 (modelo final): β por categoria de procedimento (referência: hérnia)
MICA_PROCEDIMENTO = {
    'hernia': 0.0, 'anorretal': -0.16, 'aortica': 1.60, 'bariatrica': -0.25, 'cerebral': 1.40, 'mama': -1.61,
    'cardiaca': 1.01, 'orl': 0.71, 'foregut_hpb': 1.39, 'gbaas': 0.59, 'intestinal': 1.14, 'pescoco': 0.18,
    'obstetrica_ginecologica': 0.76, 'ortopedica': 0.80, 'outra_abdominal': 1.13, 'vascular_periferica': 0.86,
    'pele': 0.54, 'coluna': 0.21, 'toracica': 0.40, 'veia': -1.09, 'urologia': -0.26,
}
MICA_ASA = {1: -5.17, 2: -3.29, 3: -1.92, 4: -0.95, 5: 0.0}
MICA_FUNCIONAL = {'independente': 0.0, 'parcial': 0.65, 'total': 1.03}
ESTADOS_FUNCIONAIS = {'independente': 'Independente', 'parcial': 'Parcialmente dependente',
                      'total': 'Totalmente dependente'}

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

CONDICOES = ('dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'ic_fe_reduzida', 'ic_recente', 'avc_ait',
             'avc_ait_recente', 'diabetes', 'diabetes_insulina', 'hipertensao', 'fa', 'valvopatia', 'protese_mecanica',
             'protese_mecanica_mitral', 'dpoc', 'doenca_arterial_periferica', 'marcapasso_cdi', 'hipertensao_pulmonar',
             'tev', 'tev_recente_3m', 'tev_3_12m', 'cancer_ativo', 'trombofilia_grave', 'tabagismo', 'obesidade',
             'hepatopatia', 'doenca_renal')
SINTOMAS = {'angina': 'Angina (dor opressiva aos esforços)', 'dispneia': 'Dispneia aos esforços habituais',
            'dispneia_nova': 'Dispneia nova ou em piora', 'palpitacoes': 'Palpitações',
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
    """Dado da tela recusado. ``mensagem`` é o texto que vai para o usuário (escrito aqui, sem rastro da exceção)."""

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


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


def _dias_desde(texto, hoje):
    """'AAAA-MM-DD' → (dias até hoje, exata). 'AAAA-MM' (só mês) não é exata e conta do último dia do mês (ou de hoje,
    no mês corrente): o menor intervalo possível, para não liberar antes do prazo."""
    import calendar
    try:
        partes = [int(x) for x in str(texto).split('-')[:3]]
        exata = len(partes) == 3
        inicio = date(partes[0], partes[1], partes[2] if exata else 1)
    except (TypeError, ValueError, IndexError):
        raise EntradaInvalida('Confira a data da angioplastia.')
    if inicio > hoje:
        raise EntradaInvalida('A data da angioplastia não pode estar no futuro.')
    if not exata:
        inicio = min(date(partes[0], partes[1], calendar.monthrange(partes[0], partes[1])[1]), hoje)
    if inicio > hoje:
        raise EntradaInvalida('A data da angioplastia não pode estar no futuro.')
    return (hoje - inicio).days, exata


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
        'funcional': _escolha(dados.get('funcional'), ESTADOS_FUNCIONAIS, 'o estado funcional'),
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
        'hba1c_dias': _num(dados.get('hba1c_dias'), 'a data da HbA1c', 0, 40000),
        'exames_feitos': [],   # [(chaves do exame, meses desde o exame, data dd/mm/aaaa)] (aplicar_exames_anteriores)
    }
    if p['pas'] is not None and p['pad'] is not None and p['pad'] >= p['pas']:
        raise EntradaInvalida('A pressão diastólica tem de ser menor que a sistólica.')
    # PA ≥ 180 × 110 (sistólica OU diastólica): hipertensão não controlada, condição grave da SBC (Tabela 2)
    p['pa_descontrolada'] = bool((p['pas'] or 0) >= 180 or (p['pad'] or 0) >= 110)
    stent = None
    if 'stent' in p['condicoes']:
        bruto = dados.get('stent') if isinstance(dados.get('stent'), dict) else {}
        tipo = _escolha(bruto.get('tipo'), ('farmacologico', 'convencional', 'balao'), 'o tipo de angioplastia')
        indicacao = _escolha(bruto.get('indicacao'), ('sca', 'dac_cronica'), 'a indicação da angioplastia')
        dias, exata = _dias_desde(bruto['data'], hoje) if bruto.get('data') else (None, False)
        stent = {'tipo': tipo, 'indicacao': indicacao, 'dias': dias, 'data_exata': exata,
                 'meses': None if dias is None else dias // 30}
    p['stent'] = stent
    # Diabetes com insulina é diabetes; IAM prévio e stent são doença coronária; FE reduzida é IC.
    c = p['condicoes']
    from src.utils.medicamentos import MEDICAMENTOS
    if any('insulina' in MEDICAMENTOS.get(m, {}).get('classes', ()) for m in p['medicacoes']):
        c.add('diabetes_insulina')   # insulina em uso conta no RCRI e no VSG-CRI
    if 'diabetes_insulina' in c:
        c.add('diabetes')
    # No RCRI, revascularização isolada não é doença coronária (Lee 1999: só com outro critério); o IAM prévio é.
    if 'iam_previo' in c:
        c.add('dac')
    if c & {'ic_fe_reduzida', 'ic_recente'}:
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
    sint = p['sintomas']
    # Lee 1999: doença isquêmica inclui angina atual; IC inclui sinais (edema pulmonar, B3, estertores, DPN).
    itens = [('Doença coronária', 'dac' in c or 'angina' in sint), ('Insuficiência cardíaca', 'ic' in c or 'sinais_ic' in sint),
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
    # Dakik 2019: IAM, revascularização, cirurgia cardíaca (prótese valvar), IC, FA ou valvopatia moderada/grave
    historia = bool(c & {'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'fa', 'valvopatia',
                         'protese_mecanica'}) or 'sinais_ic' in p['sintomas']
    itens = [('História de doença cardíaca', historia),
             ('Angina ou dispneia', bool(p['sintomas'] & {'angina', 'dispneia', 'dispneia_nova'})),
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


def mica(p):
    """Gupta NSQIP MICA: risco de IAM ou parada cardíaca em 30 dias (%). None quando não se aplica."""
    categoria = CIRURGIAS[p['cirurgia']]['mica']
    base = {'nome': 'Gupta NSQIP MICA', 'referencias': [GUPTA, AHA],
            'nota': 'IAM ou parada cardíaca em 30 dias. Elevado: ≥ 1% (AHA 2026). A classe ASA é subjetiva e pesa muito.'}
    if categoria is None:
        return dict(base, valor='—', nivel='baixo', faixa='Não se aplica', itens=[], falta=[],
                    nota='Procedimento sem categoria no NSQIP (oftalmologia, odontologia, endoscopia ou transplante).')
    falta = [nome for nome, valor in (('classe ASA', p['asa']), ('estado funcional', p['funcional'])) if valor is None]
    if falta:
        return dict(base, valor='—', nivel='baixo', faixa='Faltam dados', itens=[], falta=falta, risco=None)
    creat = p['creatinina']
    x = (-5.25 + 0.02 * p['idade'] + MICA_ASA[int(p['asa'])] + MICA_FUNCIONAL[p['funcional']]
         + (-0.10 if creat is None else 0.61 if creat >= 1.5 else 0.0) + MICA_PROCEDIMENTO[categoria])
    risco = 100 * math.exp(x) / (1 + math.exp(x))
    elevado = risco >= 1
    return dict(base, valor=f'{risco:.1f}%'.replace('.', ','), risco=round(risco, 2),
                nivel='alto' if risco >= 5 else 'intermediario' if elevado else 'baixo',
                faixa='Elevado (≥ 1%)' if elevado else 'Baixo (< 1%)',
                itens=[f'ASA {int(p["asa"])}', ESTADOS_FUNCIONAIS[p['funcional']],
                       'creatinina não informada' if creat is None else f'creatinina {_br(creat)} mg/dL'],
                falta=[])


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
    externa = {'baixo': '3,4%', 'intermediario': '13,0%', 'alto': '38,0%'}[nivel]
    resultado = {'nome': 'ARISCAT', 'valor': pontos, 'nivel': nivel, 'aplicavel': cir['ariscat'],
                 'faixa': {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}[nivel],
                 'itens': [f'{n} ({pts})' for n, pts in itens],
                 'nota': (f'Complicação pulmonar pós-operatória: {taxa} na validação original e {externa} na validação '
                          'externa (PERISCOPE).'),
                 'falta': falta, 'referencias': [ARISCAT, PERISCOPE]}
    if not cir['ariscat']:
        resultado.update(faixa='Não se aplica', nivel='baixo', falta=[],
                         nota='O ARISCAT não foi derivado neste tipo de procedimento (anestesia só local, ambulatorial '
                              'ou transplante).')
    return resultado


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
    faixa = 'Doente terminal' if cfs == 9 else {'baixo': 'Robusto', 'intermediario': 'Pré-frágil', 'alto': 'Frágil'}[nivel]
    nota = 'SBC 2024: 1–3 robusto, 4 pré-frágil, ≥ 5 frágil.'
    if cfs == 9:
        nota = 'CFS 9: expectativa de vida < 6 meses, sem fragilidade evidente; não é um grau de fragilidade (CFS 2.0).'
    return {'nome': 'Fragilidade (CFS)', 'valor': cfs, 'nivel': nivel, 'faixa': faixa,
            'itens': [], 'nota': nota, 'referencias': [CFS2, CFS, SBC, AHA]}


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


def _ha_dias(dias):
    return _ha_meses(dias // 30)


def _fmt(x):
    """Número no formato brasileiro, sem casas desnecessárias: 8.0 → '8'; 8.25 → '8,3'."""
    x = round(float(x), 1)
    return (str(int(x)) if x == int(x) else f'{x:.1f}').replace('.', ',')


def _feito(p, titulo):
    """(dias, data) do exame mais recente que cobre o título, ou None."""
    from src.utils import periodicidade
    alvo = periodicidade.chaves(titulo)
    achados = [(dias, data) for chaves, dias, data in p['exames_feitos'] if chaves & alvo]
    return min(achados) if achados else None


def _feito_ha_dias(p, titulo):
    achado = _feito(p, titulo)
    return achado[0] if achado else None


def aplicar_exames_anteriores(p, anteriores, hoje=None):
    """Exames já realizados (lidos por periodicidade.ler_exames_anteriores): datas e resultados para o motor.

    O resultado digitado no formulário vale; sem ele, entra o do exame mais recente. As janelas de validade são
    contadas em dias (HbA1c ≤ 92 dias = 3 meses).
    """
    from src.utils import periodicidade
    hoje = hoje or date.today()
    mais_recente = {}
    for exame in anteriores or []:
        dias = max(0, (hoje - exame['data']).days)
        p['exames_feitos'].append((periodicidade.chaves(exame['exame']), dias, exame['data'].strftime('%d/%m/%Y')))
        for item in exame.get('resultados') or []:
            campo = item.get('campo')
            if campo not in ('creatinina', 'hemoglobina', 'hba1c'):
                continue
            try:
                valor = float(str(item['valor']).replace('.', '').replace(',', '.'))
            except (KeyError, ValueError):
                continue
            if campo not in mais_recente or exame['data'] > mais_recente[campo][0]:
                mais_recente[campo] = (exame['data'], valor)
    for campo in ('creatinina', 'hemoglobina', 'hba1c'):
        if p.get(campo) is None and campo in mais_recente:
            p[campo] = mais_recente[campo][1]
    if p.get('hba1c_dias') is None:
        p['hba1c_dias'] = _feito_ha_dias(p, 'Hemoglobina glicada (HbA1c), soro')
    return p


def exames(p, ctx):
    """Exames sugeridos ('indicado'), a considerar ('considerar'), já feitos ('ja_feito') e não indicados.

    O risco "elevado" das recomendações da AHA ancoradas na cirurgia ("elevated-risk NCS") é a cirurgia de risco
    intermediário ou alto (AHA Tabela 2, nota †); o escore do paciente entra onde a recomendação o cita.
    """
    c, sint, idade = p['condicoes'], p['sintomas'], p['idade']
    cir = CIRURGIAS[p['cirurgia']]
    cir_ia = cir['risco'] != 'baixo'
    pac_ia, dcv = ctx['pac_ia'], ctx['dcv']
    hepatico = p['cirurgia'] == 'transplante_hepatico'
    saida = []
    if p['urgencia'] == 'emergencia':
        return [_item('Exames que atrasem a cirurgia', 'outro', 'nao_indicado',
                      'Cirurgia de emergência: nenhum exame que atrase a operação.', aha='Tabela 2', sbc='Seção 2.1.2',
                      refs=[AHA, SBC])]

    # ECG de repouso (AHA ECG recs. 1, 3 e 4; SBC Quadro 3; transplante hepático: SBC Quadro 16)
    if cir_ia:
        aha_ecg = '2a' if (dcv or sint) else '2b'
    else:
        aha_ecg = '3: sem benefício' if not sint else ''
    motivos_sbc = []
    if hepatico:
        motivos_sbc.append(('I', 'transplante hepático'))
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
    sbc_ecg = 'I' if any(cl == 'I' for cl, _ in motivos_sbc) else 'IIa' if motivos_sbc else ''
    indicado = aha_ecg in ('2a', '2b') or sbc_ecg in ('I', 'IIa')
    div = ''
    if aha_ecg.startswith('3') and sbc_ecg in ('I', 'IIa'):
        div = (f'A AHA não recomenda ECG de rotina em assintomático antes de cirurgia de baixo risco; a SBC indica '
               f'({motivos_sbc[0][1]}). Nós optamos por sugerir o ECG, sinalizando a diferença.')
    elif aha_ecg in ('2a', '2b') and sbc_ecg == 'I':
        div = f'Classe I na SBC e {aha_ecg} na AHA.'
    elif not aha_ecg and sbc_ecg in ('I', 'IIa'):
        div = 'Indicado pela SBC; a AHA não tem recomendação para este perfil.'
    feito = _feito_ha_dias(p, 'Eletrocardiograma de repouso')
    estado = 'indicado' if indicado else 'nao_indicado'
    motivo = '; '.join(m for _, m in motivos_sbc) or 'Assintomático em cirurgia de baixo risco.'
    if pac_ia and cir_ia:
        motivo += '; linha de base para o ECG do 1º e 2º dia (SBC Quadro 30)'
    elif indicado and feito is not None and feito <= 365 and not sint:
        estado, motivo = 'ja_feito', f'Feito {_ha_dias(feito)}, sem sintomas novos: pode valer o atual.'
    saida.append(_item('Eletrocardiograma de repouso', 'imagem', estado, motivo, aha=aha_ecg or '—',
                       sbc=sbc_ecg or '—', refs=[AHA, SBC], divergencia=div))

    # Ecocardiograma transtorácico (AHA §4.2 e §6.5; SBC Quadros 4, 15 e 16)
    sint_ic = bool(sint & {'dispneia_nova', 'sinais_ic'})
    aha_eco, sbc_eco, motivo, janela, div = '', '', '', 365, ''
    if sint_ic:
        aha_eco, motivo = '1', 'Dispneia nova ou sinais de insuficiência cardíaca.'
        sbc_eco = 'I' if cir_ia else ''
        if not cir_ia:
            div = 'A AHA indica em qualquer cirurgia (classe 1); a SBC, só em cirurgia de risco intermediário ou alto.'
    elif 'sopro' in sint:
        aha_eco, motivo = '1', 'Sopro: suspeita de valvopatia moderada ou grave.'
        sbc_eco = 'I' if cir_ia else ''
        if not cir_ia:
            div = ('Na suspeita de regurgitação, a AHA indica antes de qualquer cirurgia eletiva; na de estenose '
                   'aórtica, só em cirurgia de risco elevado. A SBC restringe a cirurgias de risco intermediário ou alto.')
    elif 'dispneia' in sint and cir_ia:
        sbc_eco, motivo = 'I', 'Dispneia aos esforços: sintoma sugestivo de insuficiência cardíaca, sem eco no último ano.'
        div = 'A SBC indica (I-B) com sintoma sugestivo de IC; a AHA só recomenda na dispneia nova ou em piora.'
    elif 'valvopatia' in c:
        janela = 183 if cir_ia else 365
        if cir_ia:
            aha_eco, sbc_eco = '1', 'I'
            motivo = 'Valvopatia moderada ou grave: ecocardiograma dos últimos 6 meses (SBC).'
        else:
            aha_eco = '2a'
            motivo = 'Cirurgia de baixo risco: razoável operar se houver eco do último ano, sem sintomas e com FEVE normal.'
    elif hepatico:
        sbc_eco, motivo = 'I', 'Transplante hepático: ecocardiograma para todos (SBC Quadro 16).'
    elif 'ic' in c and cir_ia:
        aha_eco, sbc_eco = '3: sem benefício', 'I'
        motivo = 'Insuficiência cardíaca conhecida, sem ecocardiograma no último ano.'
        div = ('A SBC indica (I-B) na IC conhecida sem eco no último ano; a AHA não vê benefício no paciente estável '
               'e assintomático. Nós optamos por sugerir, sinalizando a diferença.')
    elif 'protese_mecanica' in c and cir_ia:
        sbc_eco, motivo = 'IIa', 'Prótese valvar, sem ecocardiograma no último ano.'
    elif cir['risco'] == 'alto':
        aha_eco, sbc_eco = '3: sem benefício', 'IIb'
        motivo = 'Assintomático antes de cirurgia de alto risco.'
        div = 'Assintomático antes de cirurgia de alto risco: a SBC admite (IIb); a AHA não vê benefício.'
    else:
        aha_eco, sbc_eco = '3: sem benefício', 'III'
        motivo = 'Assintomático e estável: ecocardiograma de rotina não muda a conduta.'
    if aha_eco == '1' or sbc_eco in ('I', 'IIa'):
        estado = 'indicado'
    elif sbc_eco == 'IIb' or aha_eco == '2a':
        estado = 'considerar'
    else:
        estado = 'nao_indicado'
    feito = _feito_ha_dias(p, 'Ecocardiograma transtorácico')
    if estado in ('indicado', 'considerar') and feito is not None and feito <= janela and not sint_ic \
            and 'sopro' not in sint:
        estado, motivo = 'ja_feito', f'Feito {_ha_dias(feito)}, sem piora clínica: pode valer o atual.'
    saida.append(_item('Ecocardiograma transtorácico', 'imagem', estado, motivo, aha=aha_eco or '—',
                       sbc=sbc_eco or '—', refs=[AHA, SBC], divergencia=div))

    # BNP / NT-proBNP (AHA biomarcadores rec. 1; SBC Quadro 29). A SBC escreve "> 65" e "45 a 64": usamos ≥ 65
    # (como a AHA e a CCS 2017) para não deixar sem critério quem tem exatamente 65 anos.
    aha_bnp = '2a' if cir_ia and (dcv or idade >= 65 or (idade >= 45 and sint)) else ''
    fr_icfep = bool(c & {'diabetes', 'hipertensao', 'dac', 'obesidade', 'fa'})
    sbc_bnp = 'I' if cir_ia and (idade >= 65 or (45 <= idade < 65 and (dcv or fr_icfep))) else ''
    if aha_bnp or sbc_bnp:
        if sbc_bnp and not aha_bnp:
            div = ('A SBC indica (classe I) a partir de 65 anos ou de 45 com fator de risco; a AHA só com doença '
                   'cardiovascular, 65 anos ou mais, ou sintomas.')
        elif aha_bnp and not sbc_bnp:
            div = 'A AHA indica (2a); pelos critérios da SBC não haveria indicação.'
        else:
            div = 'Classe I na SBC e 2a na AHA.'
        saida.append(_item('Peptídeo natriurético BNP/PROBNP', 'laboratorio', 'indicado',
                           'Estratifica o risco: BNP > 92 ng/L ou NT-proBNP ≥ 300 ng/L indicam risco aumentado.',
                           aha=aha_bnp or '—', sbc=sbc_bnp or '—', refs=[AHA, SBC], divergencia=div))
    elif not cir_ia:
        saida.append(_item('Peptídeo natriurético BNP/PROBNP', 'laboratorio', 'nao_indicado',
                           'Cirurgia de baixo risco: biomarcadores não mudam a conduta.', aha='—', sbc='—',
                           refs=[AHA, SBC]))

    # Troponina antes da cirurgia (AHA biomarcadores rec. 2; SBC Quadro 30). A de 24/48 h fica no pós-operatório.
    aha_tn = '2b' if cir_ia and (dcv or idade >= 65 or (idade >= 45 and sint)) else ''
    sbc_tn = 'I' if (pac_ia and cir_ia) or p['cirurgia'] == 'transplante_renal' else ''
    if aha_tn or sbc_tn:
        if aha_tn and sbc_tn:
            div = 'Classe I na SBC e 2b na AHA.'
        elif sbc_tn and p['cirurgia'] == 'transplante_renal':
            div = 'Indicada pela SBC no transplante renal (Quadro 17, I-B), qualquer que seja o escore.'
        elif sbc_tn:
            div = 'Indicada só pela SBC (risco intermediário ou alto pelo escore em cirurgia de risco intermediário ou alto).'
        else:
            div = 'Só a AHA admite (2b, "pode ser razoável"); pela SBC o paciente é de baixo risco.'
        saida.append(_item('Troponina, soro', 'laboratorio', 'indicado' if sbc_tn else 'considerar',
                           'Valor basal antes da cirurgia, para comparar com as dosagens do pós-operatório.',
                           aha=aha_tn or '—', sbc=sbc_tn or '—', refs=[AHA, SBC], divergencia=div))
    elif not cir_ia:
        saida.append(_item('Troponina, soro', 'laboratorio', 'nao_indicado', 'Cirurgia de baixo risco.',
                           aha='3: sem benefício', sbc='III', refs=[AHA, SBC]))

    # Prova funcional e angiotomografia: risco elevado com capacidade baixa ou desconhecida, só se mudar a conduta
    if p['instaveis']:
        saida.append(_item('Prova funcional ou angiotomografia de coronárias', 'outro', 'nao_indicado',
                           'Condição instável: estabilizar primeiro; prova de estresse contraindicada na SCA de alto '
                           'risco.', aha='—', sbc='—', refs=[SBC, AHA]))
    elif ctx['investigar_isquemia']:
        if p['urgencia'] == 'urgencia':
            saida.append(_item('Prova funcional ou angiotomografia de coronárias', 'outro', 'nao_indicado',
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
    elif cir_ia and ctx.get('capacidade') in ('baixa', 'desconhecida') and c & {'dac', 'iam_previo', 'stent',
            'revascularizacao_cirurgica'} and p['urgencia'] == 'eletiva' and not sint & {'angina', 'dispneia_nova'}:
        saida.append(_item('Cintilografia de perfusão miocárdica (estresse e repouso)', 'imagem', 'considerar',
                           'Risco baixo pelo escore, mas baixa capacidade funcional com doença coronária conhecida: '
                           'só se o resultado puder mudar a conduta.', aha='—', sbc='IIb', refs=[SBC, AHA],
                           divergencia='A SBC admite (IIb-B, Quadro 6); pela AHA, risco < 1% libera sem testes.',
                           grupo='isquemia'))
    elif cir_ia:
        if pac_ia:
            motivo, sbc = 'Boa capacidade funcional e sintomas estáveis: sem benefício.', 'sem classe (texto)'
        else:
            motivo, sbc = 'Risco baixo pelo escore: sem benefício.', 'III'
        saida.append(_item('Prova funcional ou angiotomografia de coronárias', 'outro', 'nao_indicado', motivo,
                           aha='3: sem benefício', sbc=sbc, refs=[AHA, SBC]))
    else:
        saida.append(_item('Prova funcional ou angiotomografia de coronárias', 'outro', 'nao_indicado',
                           'Cirurgia de baixo risco: sem benefício.', aha='3: sem benefício', sbc='III', refs=[AHA, SBC]))
    if 'sca' in p['instaveis']:
        saida.append(_item('Cineangiocoronariografia', 'outro', 'indicado',
                           'Síndrome coronariana aguda de alto risco: estratificação invasiva, como fora da cirurgia.',
                           aha='1 (diretriz de SCA)', sbc='I', refs=[SBC, AHA]))
    else:
        saida.append(_item('Cateterismo cardíaco de rotina', 'outro', 'nao_indicado',
                           'Só com as mesmas indicações de fora da cirurgia (SCA, isquemia extensa na prova funcional).',
                           aha='3: sem benefício', sbc='III' if not cir_ia else 'sem classe (texto)', refs=[AHA, SBC]))

    # Glicemia (AHA §7.8 rec. 1, 2a B-NR: diabetes ou risco de diabetes, eletiva, sem HbA1c em ≤ 3 meses;
    # SBD/SBA/ABESO 2026 R1, I-B: rastrear diabetes com glicemia de jejum e HbA1c, sobretudo com ≥ 35 anos ou fator
    # de risco; R2, I-B: no diabetes conhecido, HbA1c < 8% desejável). A NICE não oferece HbA1c a quem não tem diabetes.
    if p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        dias = p['hba1c_dias']
        valor = p.get('hba1c')
        feita = (f'Feita {_ha_dias(dias)}' + (f', {_fmt(valor)}%' if valor is not None else '') + ' (vale até 3 meses).'
                 if dias is not None else '')
        if 'diabetes' in c:
            if dias is not None and dias <= 92:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'ja_feito', feita,
                                   aha='2a', sbc='—', outra='SBD I-B', refs=[AHA, SBD, NICE]))
            else:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'indicado',
                                   'Diabetes, sem HbA1c nos últimos 3 meses (meta < 8% antes da cirurgia eletiva).',
                                   aha='2a', sbc='—', outra='SBD I-B · NICE', refs=[AHA, SBD, NICE]))
        elif idade >= 35 or c & {'hipertensao', 'obesidade', 'dac', 'iam_previo', 'avc_ait',
                                 'doenca_arterial_periferica'}:
            motivo = ('Sem diagnóstico de diabetes, com 35 anos ou mais' if idade >= 35 else
                      'Sem diagnóstico de diabetes, com fator de risco') + ': rastreio de diabetes.'
            div = ('A NICE NG45 não oferece HbA1c de rotina a quem não tem diabetes. Nós optamos por seguir a '
                   'SBD/SBA/ABESO 2026 (I-B) e a AHA (2a), que incluem quem tem risco de diabetes.')
            if dias is not None and dias <= 92:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'ja_feito', feita,
                                   aha='2a', sbc='—', outra='SBD I-B', refs=[SBD, AHA, NICE], divergencia=div))
            else:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'indicado', motivo,
                                   aha='2a', sbc='—', outra='SBD I-B', refs=[SBD, AHA, NICE], divergencia=div))
            gdias = _feito_ha_dias(p, 'Glicose, soro')
            if gdias is not None and gdias <= 92:
                saida.append(_item('Glicose, soro', 'laboratorio', 'ja_feito', f'Feita {_ha_dias(gdias)}.',
                                   outra='SBD I-B', refs=[SBD]))
            else:
                saida.append(_item('Glicose, soro', 'laboratorio', 'indicado', motivo + ' Glicemia de jejum.',
                                   outra='SBD I-B', refs=[SBD]))

    # Exames de rotina (NICE NG45): "Offer" = indicado; "Consider" = considerar
    asa, porte = p['asa'], cir['porte']
    renal = 'doenca_renal' in c
    meds = ctx['classes_medicacoes']
    if porte == 'maior':
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'indicado', 'Cirurgia de grande porte.',
                           outra='NICE', refs=[NICE]))
    elif porte == 'intermediaria' and asa and asa >= 3 and (dcv or renal):
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'considerar',
                           'ASA ≥ 3 com doença cardiovascular ou renal.', outra='NICE', refs=[NICE]))
    elif p['hemoglobina'] is None and cir_ia:
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'considerar',
                           'A hemoglobina entra no AUB-HAS2 e no ARISCAT.', outra='Escores', refs=[AUB, ARISCAT]))
    usa_renal = bool(meds & {'ieca_bra', 'arni', 'tiazidico', 'diuretico_alca', 'espironolactona', 'doac',
                             'metformina', 'isglt2'})
    if (porte == 'maior' and asa and asa >= 2) or (porte == 'intermediaria' and asa and asa >= 3):
        estado_renal, motivo_renal, ref_renal = 'indicado', 'Porte da cirurgia e classe ASA.', [NICE]
    elif renal or usa_renal:
        estado_renal, ref_renal = 'considerar', [NICE]
        motivo_renal = 'Doença renal ou medicamento que depende da função renal (ajuste e risco de lesão renal aguda).'
    elif p['creatinina'] is None and cir_ia:
        estado_renal, motivo_renal, ref_renal = 'considerar', 'Necessária para o RCRI e a depuração (Cockcroft-Gault).', [LEE, CG]
    else:
        estado_renal = None
    if estado_renal:
        saida.append(_item('Creatinina, soro', 'laboratorio', estado_renal, motivo_renal, outra='NICE', refs=ref_renal))
        saida.append(_item('Sódio e potássio, soro', 'laboratorio', estado_renal, 'Junto da função renal.',
                           outra='NICE', refs=[NICE]))
    if 'varfarina' in meds:
        saida.append(_item('Tempo de protrombina (TP/INR), plasma', 'laboratorio', 'indicado',
                           'Uso de varfarina: INR antes da cirurgia.', outra='NICE', refs=[NICE, SBC]))
    elif 'doac' in meds:
        saida.append(_item('Coagulograma (TP/INR e TTPa)', 'laboratorio', 'nao_indicado',
                           'O coagulograma não mede o efeito do anticoagulante direto: a suspensão é guiada pelo tempo '
                           'e pela função renal.', outra='NICE · CHEST', refs=[NICE, CHEST]))
    elif 'hepatopatia' in c and asa and asa >= 3 and porte != 'menor':
        saida.append(_item('Coagulograma (TP/INR e TTPa)', 'laboratorio', 'considerar',
                           'Hepatopatia crônica, ASA ≥ 3.', outra='NICE', refs=[NICE]))
    else:
        saida.append(_item('Coagulograma (TP/INR e TTPa)', 'laboratorio', 'nao_indicado',
                           'Sem anticoagulante nem hepatopatia: não é exame de rotina.', outra='NICE', refs=[NICE]))
    if cir.get('endourologica'):
        saida.append(_item('Urocultura com antibiograma', 'laboratorio', 'indicado',
                           'Procedimento endourológico com trauma de mucosa: rastrear e tratar a bacteriúria antes.',
                           outra='IDSA 2019', refs=[IDSA]))
    elif cir['urologica']:
        saida.append(_item('Urocultura com antibiograma', 'laboratorio', 'considerar',
                           'Se uma infecção urinária mudar a decisão de operar.', outra='NICE', refs=[NICE]))
    if hepatico:
        saida.append(_item('Radiografia de tórax', 'imagem', 'indicado', 'Transplante hepático: para todos.',
                           sbc='I', refs=[SBC]))
    else:
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
            item['ultimo'] = f'Último em {achado[1]} ({_ha_dias(achado[0])})'
    return saida


# ── Indicação, adiamentos e pós-operatório ──────────────────────────────────

def _passo(pergunta, resposta, estado, texto):
    return {'pergunta': pergunta, 'resposta': resposta, 'estado': estado, 'texto': texto}


def _adiar(titulo, texto, classe, refs, divergencia='', ok=False):
    item = {'titulo': titulo, 'texto': texto, 'classe': classe, 'referencias': refs, 'divergencia': divergencia}
    if ok:
        item['ok'] = True
    return item


def adiamentos(p):
    """Situações em que a cirurgia eletiva deve esperar (ou que pedem discussão), com classe.

    Em urgência e emergência nada é adiado: o stent recente pede só a conduta da SBC (Quadro 21, I-C).
    """
    saida = []
    eletiva = p['urgencia'] in ('eletiva', 'tempo_sensivel')
    for chave in sorted(p['instaveis']):
        texto = ('Condição grave ou instável: estabilizar antes; adiar a cirurgia eletiva.' if eletiva else
                 'Condição grave ou instável: estabilizar o quanto o tempo permitir, sem atrasar a cirurgia.')
        saida.append(_adiar(INSTAVEIS[chave], texto, 'SBC Tabela 2', [SBC, AHA]))
    if p['pa_descontrolada'] and eletiva:
        pa = ' × '.join(str(int(v)) for v in (p['pas'], p['pad']) if v)
        saida.append(_adiar(f'PA {pa} mmHg',
                            'Hipertensão não controlada (≥ 180 × 110): controlar a pressão e adiar a cirurgia eletiva.',
                            'SBC Tabela 2 e Quadro 9 · AHA 2b', [SBC, AHA],
                            'A SBC trata como condição grave (Tabela 2) e adia (I-C) a cirurgia de alto risco; a AHA '
                            '"pode considerar" adiar (2b) em cirurgia de risco elevado com fator de risco do RCRI.'))
    if 'ic_recente' in p['condicoes'] and eletiva:
        saida.append(_adiar('Insuficiência cardíaca recente, tratamento ainda não otimizado',
                            'Adiar a cirurgia eletiva por pelo menos 3 meses, para ajustar as doses do tratamento.',
                            'SBC I-C', [SBC]))
    st = p['stent']
    if st:
        saida.extend(_adiamentos_do_stent(st, p['urgencia']))
    a1c = p.get('hba1c')
    if 'diabetes' in p['condicoes'] and a1c is not None and a1c > 8 and eletiva:
        if p['urgencia'] == 'eletiva':
            texto = ('Encaminhar ao endocrinologista para otimizar o controle e considerar adiar a cirurgia eletiva até '
                     'a HbA1c ficar abaixo de 8%, sem hipoglicemia. No dia, glicemia acima de 250 mg/dL: considerar '
                     'adiar.')
        else:
            texto = ('Cirurgia tempo-sensível: avaliação do endocrinologista antes, sem esperar a meta. No dia, glicemia '
                     'acima de 250 mg/dL: considerar adiar.')
        saida.append(_adiar(f'HbA1c {_fmt(a1c)}% (acima de 8%)', texto, 'SBD/SBA/ABESO I-B (meta < 8%) · AHA: texto',
                            [SBD, AHA]))
    carotida = p['cirurgia'] in ('endarterectomia_sintomatica', 'stent_carotida_sintomatica')
    if 'avc_ait_recente' in p['condicoes'] and carotida:
        saida.append(_adiar('AVC ou AIT recente com doença carotídea sintomática',
                            'A revascularização carotídea é o tratamento do evento: fazer de preferência nas 2 semanas '
                            'seguintes, sem esperar 3 meses.', 'AHA/ASA 2021 2a · ESVS 2023 I',
                            [CAROTIDA_AHA, CAROTIDA_ESVS, AHA], ok=True))
    elif 'avc_ait_recente' in p['condicoes'] and eletiva:
        saida.append(_adiar('AVC ou AIT há menos de 3 meses',
                            'Adiar a cirurgia eletiva para pelo menos 3 meses depois do evento.', 'AHA 2a', [AHA]))
    return saida


def _adiamentos_do_stent(st, urgencia):
    """Prazos após angioplastia (AHA §7.5 recs. 2–6; SBC Quadros 21–23; SBC 2022 de ICP).

    A SBC gradua pela indicação da angioplastia (eletiva por doença crônica ou SCA), qualquer que seja o stent; a AHA
    dá classe aos prazos do stent farmacológico e marca como dano a cirurgia em ≤ 30 dias de qualquer stent.
    """
    tipo, ind, dias, exata = st.get('tipo'), st.get('indicacao'), st.get('dias'), st.get('data_exata')
    refs = [AHA, SBC]
    if urgencia in ('urgencia', 'emergencia'):
        if dias is not None and dias < 365:
            return [_adiar('Angioplastia recente em cirurgia que não pode esperar',
                           'Manter o AAS e, se o risco de sangramento permitir, o segundo antiagregante; operar em '
                           'centro com suporte multidisciplinar e hemodinâmica.', 'SBC I-C', [SBC])]
        return []
    if not tipo:
        return [_adiar('Tipo da angioplastia não informado',
                       'Informe se foi só balão, stent convencional ou farmacológico: os prazos mudam.', 'AHA · SBC', refs)]
    if dias is None:
        return [_adiar('Data da angioplastia não informada',
                       'Sem a data não dá para saber se a cirurgia eletiva precisa esperar (14 dias após balão; '
                       '30 dias após qualquer stent; 6 meses na doença coronária crônica; 12 meses na SCA).',
                       'AHA · SBC', refs)]
    aviso_data = '' if exata else ' A data foi informada só com mês e ano; confira o dia nos prazos curtos.'
    if tipo == 'balao':
        if dias < 14:
            return [_adiar('Angioplastia com balão há menos de 14 dias',
                           'Esperar pelo menos 14 dias para a cirurgia eletiva.' + aviso_data, 'AHA 1',
                           [AHA, SBC_ICP])]
        return [_adiar(f'Angioplastia com balão {_ha_dias(dias)}: fora do período de maior risco',
                       'O intervalo mínimo (14 dias) já passou.' + aviso_data, 'AHA 1', [AHA, SBC_ICP], ok=True)]
    if dias <= 30:
        return [_adiar('Stent há 30 dias ou menos',
                       'Cirurgia eletiva que interrompa antiagregante é potencialmente danosa: adiar.' + aviso_data,
                       'AHA 3: dano · SBC III', refs)]
    nome = 'Stent farmacológico' if tipo == 'farmacologico' else 'Stent convencional'
    sem_indicacao = ind is None
    ind = ind or 'sca'
    meses = dias / 30.4
    if ind == 'sca' and meses < 12:
        sbc = 'IIa' if meses >= 6 else 'IIb'
        aha = 'AHA 1 (≥ 12 meses) · ' if tipo == 'farmacologico' else ''
        texto = ('O ideal é esperar 12 meses para cirurgia eletiva que interrompa antiagregante. Entre 6 e 12 meses '
                 '(SBC IIa) ou de 30 dias a 6 meses (SBC IIb), só com discussão multidisciplinar e mantendo o AAS.')
        if tipo == 'farmacologico':
            texto += ' Em cirurgia tempo-sensível, a AHA admite operar a partir de 3 meses se o atraso for mais arriscado (2b).'
        if sem_indicacao:
            texto += ' Sem a indicação da angioplastia, valeu o prazo mais longo (SCA).'
        return [_adiar(f'{nome} por SCA {_ha_dias(dias)}' if not sem_indicacao else f'{nome} {_ha_dias(dias)}',
                       texto + aviso_data, f'{aha}SBC {sbc} na faixa atual', refs,
                       'A SBC gradua as faixas intermediárias pela indicação; a AHA dá classe ao stent farmacológico '
                       '(12 meses na SCA; 3 meses em cirurgia tempo-sensível, 2b).')]
    if ind == 'dac_cronica' and meses < 6:
        sbc = 'IIa' if meses >= 3 else 'IIb'
        aha = 'AHA 2a (≥ 6 meses) · ' if tipo == 'farmacologico' else ''
        return [_adiar(f'{nome} por doença coronária crônica {_ha_dias(dias)}',
                       'O ideal é esperar 6 meses para cirurgia eletiva que interrompa antiagregante; em cirurgia '
                       'tempo-sensível, a partir de 3 meses se o atraso for mais arriscado.' + aviso_data,
                       f'{aha}SBC {sbc} na faixa atual', refs, 'Esperar 6 meses: SBC I-A; AHA 2a.')]
    return [_adiar(f'{nome} {_ha_dias(dias)}: fora do período de maior risco',
                   'O intervalo mínimo para cirurgia eletiva já passou. Manter o AAS.', 'AHA · SBC', refs, ok=True)]


def avaliar(p):
    """Resultado completo da avaliação pré-operatória."""
    from src.utils.medicamentos import classes_de
    cir = CIRURGIAS[p['cirurgia']]
    c = p['condicoes']
    escore_rcri, escore_aub, escore_vsg, escore_mica = rcri(p), aub_has2(p), vsg_cri(p), mica(p)
    cap = capacidade_funcional(p)
    dcv = bool(c & {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'avc_ait', 'fa', 'valvopatia',
                    'doenca_arterial_periferica', 'protese_mecanica', 'hipertensao_pulmonar', 'marcapasso_cdi'})
    # Risco do paciente pelos algoritmos da SBC (RCRI, AUB-HAS2; VSG-CRI na vascular arterial): "pac_ia".
    elevado_por = []
    if escore_rcri['valor'] >= 2:
        elevado_por.append(f'RCRI {escore_rcri["valor"]}')
    if escore_aub['valor'] >= 2:
        elevado_por.append(f'AUB-HAS2 {escore_aub["valor"]}')
    if escore_vsg and escore_vsg['valor'] >= 5:
        elevado_por.append(f'VSG-CRI {escore_vsg["valor"]}')
    pac_ia = bool(elevado_por)
    # A AHA aceita qualquer calculadora validada (risco ≥ 1%): o MICA também conta para "risco elevado".
    mica_elevado = (escore_mica.get('risco') or 0) >= 1
    risco_elevado = pac_ia or mica_elevado
    if mica_elevado:
        elevado_por.append(f'Gupta MICA {escore_mica["valor"]}')
    cir_ia = cir['risco'] != 'baixo'
    emergencia = p['urgencia'] == 'emergencia'
    adiar = adiamentos(p)
    sint_isq_novo = bool(p['sintomas'] & {'angina', 'dispneia_nova'})

    passos, conclusao = [], None
    passos.append(_passo('Cirurgia de emergência?', 'Sim' if emergencia else 'Não', 'atencao' if emergencia else 'ok',
                         'Operar sem exames que atrasem a cirurgia; só monitorização e redução de risco.'))
    if emergencia:
        conclusao = ('emergencia', 'Cirurgia de emergência: sem avaliação que atrase a operação. Monitorização, '
                                   'troponina pós-operatória se houver risco e manejo dos medicamentos.')
    if not conclusao:
        inst = bool(p['instaveis']) or p['pa_descontrolada']
        passos.append(_passo('Condição cardiovascular grave ou instável?', 'Sim' if inst else 'Não',
                             'atencao' if inst else 'ok',
                             'SCA, IC descompensada, angina CCS III/IV, estenose aórtica ou mitral importante '
                             'sintomática, BAVT/TV, FA com FC > 120, PA ≥ 180 × 110, HAP sintomática.'))
        if inst and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
            conclusao = ('adiar', 'Condição grave ou instável: estabilizar e adiar a cirurgia eletiva; '
                                  'avaliação cardiológica indicada.')
        elif inst:
            conclusao = ('indicada', 'Condição grave ou instável em cirurgia de urgência: estabilizar o quanto o tempo '
                                     'permitir, sem atrasar a operação; avaliação cardiológica e monitorização '
                                     'perioperatória.')
    if not conclusao:
        passos.append(_passo('Risco intrínseco da cirurgia', RISCO_DA_CIRURGIA[cir['risco']].split(' (')[0],
                             'ok' if not cir_ia else 'atencao',
                             'Baixo risco (< 1%) em paciente estável: não há avaliação cardiológica nem exames '
                             'cardíacos de rotina indicados.'))
        if not cir_ia:
            conclusao = ('nao_indicada', 'Cirurgia de baixo risco em paciente estável: avaliação cardiológica e '
                                         'exames cardíacos de rotina não indicados. Pode operar.')
    if not conclusao:
        passos.append(_passo('Risco do paciente pelos escores', 'Elevado' if risco_elevado else 'Baixo',
                             'atencao' if risco_elevado else 'ok',
                             'RCRI 0–1, AUB-HAS2 0–1 e Gupta MICA < 1%: risco baixo; liberar sem testes de isquemia.'))
        if not risco_elevado:
            conclusao = ('nao_indicada', 'Risco baixo pelos escores: liberar sem investigação de isquemia.')
    investigar = False
    if not conclusao:
        estado = cap['estado']
        passos.append(_passo('Capacidade funcional', cap['valor'], 'ok' if estado == 'boa' else 'atencao',
                             '≥ 4 METs (sobe 2 lances) ou DASI > 34, com sintomas estáveis: liberar sem prova funcional. '
                             'Baixa ou desconhecida: biomarcadores e, só se mudar a conduta, prova funcional.'))
        if estado == 'boa':
            texto = 'Risco elevado, mas boa capacidade funcional: liberar sem prova funcional.'
            if sint_isq_novo:
                texto += (' Angina ou dispneia nova ou em mudança: investigar como fora do contexto cirúrgico, pelas '
                          'diretrizes de dor torácica e doença coronária.')
            conclusao = ('nao_indicada', texto)
        else:
            investigar = p['urgencia'] in ('eletiva', 'tempo_sensivel', 'urgencia')
            motivos = [f'cirurgia de risco {RISCO_DA_CIRURGIA[cir["risco"]].split(" (")[0].lower()}',
                       ', '.join(elevado_por), f'capacidade funcional {cap["valor"].lower()}']
            conclusao = ('indicada', 'Avaliação cardiológica indicada: ' + '; '.join(m for m in motivos if m) + '.')
    # Dispneia nova, sinais de IC ou sopro: avaliar o VE ou a valva antes de qualquer cirurgia eletiva (AHA §4.2, 1;
    # §6.5, 1), qualquer que seja o escore ou a capacidade.
    if conclusao[0] == 'nao_indicada' and p['sintomas'] & {'dispneia_nova', 'sinais_ic', 'sopro'} \
            and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        conclusao = ('indicada', 'Dispneia nova, sinais de insuficiência cardíaca ou sopro: avaliar a função '
                                 'ventricular ou a valva (ecocardiograma) antes de operar.')
    if any(not a.get('ok') for a in adiar) and conclusao[0] in ('nao_indicada', 'indicada'):
        conclusao = (conclusao[0], conclusao[1] + ' Antes, veja o que pede adiamento.')

    classes_meds = set(classes_de(p['medicacoes']))
    ctx = {'cir_elev': cir_ia, 'pac_ia': pac_ia, 'dcv': dcv, 'investigar_isquemia': investigar,
           'classes_medicacoes': classes_meds, 'capacidade': cap['estado']}
    lista_exames = exames(p, ctx)

    escores = [escore_rcri, escore_aub]
    if escore_vsg:
        escores.append(escore_vsg)
    escores.append(escore_mica)
    escores.append(cap)
    frag = fragilidade(p)
    if frag:
        escores.append(frag)
    depuracao = clcr(p)

    orientacoes = []
    if p['idade'] >= 65 and cir_ia and frag is None:
        orientacoes.append({'titulo': 'Avaliar fragilidade', 'texto': 'Com instrumento validado (CFS, FRAIL) em quem '
                            'tem 65 anos ou mais e vai a cirurgia de risco intermediário ou alto.',
                            'classe': 'AHA 2a · SBC IIa', 'referencias': [AHA, SBC, CFS]})
    sb = stop_bang(p)
    if sb['nivel'] == 'alto':
        orientacoes.append({'titulo': 'Suspeita de apneia obstrutiva do sono moderada a grave',
                            'texto': 'Avisar a anestesia para as precauções perioperatórias. Sem doença sistêmica '
                                     'descompensada, não é preciso adiar a cirurgia para fazer polissonografia; quem já '
                                     'usa CPAP deve levar o aparelho.',
                            'classe': 'SASM 2016 · AHA 2a (rastreio)', 'referencias': [SASM, AHA]})
    if 'tabagismo' in c and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        orientacoes.append({'titulo': 'Parar de fumar', 'texto': 'Parar 4 semanas ou mais antes reduz complicações '
                            'respiratórias e de cicatrização; parar mais perto da cirurgia não aumenta o risco.',
                            'classe': 'Metanálise', 'referencias': [TABAGISMO]})

    pulmonar = ariscat(p)
    medidas_pulmonares = []
    if (pulmonar.get('aplicavel', True) and pulmonar['nivel'] != 'baixo') or 'dpoc' in c or 'ic' in c \
            or p['funcional'] in ('parcial', 'total'):
        medidas_pulmonares.append({'titulo': 'Expansão pulmonar no pós-operatório',
                                   'texto': 'Exercícios de respiração profunda ou incentivador. Estudos posteriores não '
                                            'mostraram benefício do incentivador isolado; o treino muscular inspiratório '
                                            'antes de cirurgia de grande porte reduziu pneumonia.',
                                   'classe': 'ACP 2006 (A)', 'referencias': [ACP, COCHRANE_IS, COCHRANE_IMT]})
        medidas_pulmonares.append({'titulo': 'Sonda nasogástrica só quando necessária',
                                   'texto': 'Uso seletivo (náusea, distensão), não de rotina.',
                                   'classe': 'ACP 2006 (B)', 'referencias': [ACP]})

    pos = []
    fr = bool(c & {'hipertensao', 'diabetes', 'tabagismo', 'obesidade'}) or p['sexo'] == 'masculino' or p['idade'] > 65
    aha_tn = '2b' if cir_ia and (dcv or p['sintomas'] or (p['idade'] >= 65 and fr)) else ''
    sbc_tn = 'I' if (pac_ia and cir_ia) or p['cirurgia'] == 'transplante_renal' else ''
    if aha_tn or sbc_tn:
        pos.append({'titulo': 'Troponina com 24 e 48 h', 'texto': 'Para detectar injúria miocárdica após a cirurgia.',
                    'classe': ' · '.join(x for x in (f'AHA {aha_tn}' if aha_tn else '', f'SBC {sbc_tn}' if sbc_tn else '') if x),
                    'referencias': [AHA, SBC]})
    if pac_ia and cir_ia:
        pos.append({'titulo': 'ECG no 1º e no 2º dia', 'texto': 'Junto da troponina.', 'classe': 'SBC I',
                    'referencias': [SBC]})
        niveis = [e['nivel'] for e in (escore_rcri, escore_aub, escore_vsg) if e]
        alto = 'alto' in niveis
        pos.append({'titulo': 'Unidade de terapia intensiva por 48 h',
                    'texto': ('Risco alto pelo escore.' if alto else 'Risco intermediário pelo escore: considerar.')
                    + ' Recomendação só da SBC (Quadro 30), por opinião de especialistas.',
                    'classe': 'SBC I-C' if alto else 'SBC IIa-C', 'referencias': [SBC, AHA],
                    'divergencia': 'A AHA/ACC 2026 não recomenda UTI pelo risco dos escores; cita cuidado intensivo só '
                                   'em situações específicas (hipertensão pulmonar grave, 2a; cardiomiopatia '
                                   'hipertrófica obstrutiva; estenose mitral). Nós optamos por seguir a SBC.'})
    if 'hipertensao' in c:
        pos.append({'titulo': 'Reintroduzir os anti-hipertensivos', 'texto': 'Assim que clinicamente possível.',
                    'classe': 'AHA 1 · SBC I', 'referencias': [AHA, SBC]})
    pos.append({'titulo': 'Evitar hipotensão', 'texto': 'Manter PAM ≥ 60–65 mmHg ou PAS ≥ 90 mmHg e tratar a '
                'hipotensão no pós-operatório.', 'classe': 'AHA 1 · SBC I', 'referencias': [AHA, SBC]})

    # Sem indicação de avaliação cardiológica num paciente sem doença cardiovascular, sem sintomas e sem risco pelos
    # escores (o jovem sem comorbidade em cirurgia de baixo risco): a tela mostra só uma orientação curta.
    pulmonar_risco = ariscat(p)
    resumido = (conclusao[0] == 'nao_indicada' and not cir_ia and p['idade'] < 65 and not c
                and not risco_elevado and not p['sintomas'] and not p['instaveis'] and not p['pa_descontrolada']
                and not any(not a.get('ok') for a in adiar)
                and (not pulmonar_risco.get('aplicavel', True) or pulmonar_risco['nivel'] == 'baixo')
                and sb['nivel'] != 'alto' and (frag is None or (frag['valor'] or 0) < 5))
    resumo = None
    if resumido:
        resumo = {'titulo': 'Avaliação cardiológica não indicada',
                  'texto': 'Motivo: cirurgia de baixo risco (< 1%), em paciente com menos de 65 anos, sem '
                           'comorbidade, sem sintomas e sem condição instável. Exames cardíacos adicionais não mudam '
                           'a conduta neste perfil; pode operar.',
                  'referencias': [AHA, SBC]}

    return {
        'resumido': resumido,
        'resumo': resumo,
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
        'contexto': {'cir_elev': cir_ia, 'pac_ia': pac_ia, 'risco_elevado': risco_elevado, 'dcv': dcv},
    }
