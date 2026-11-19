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
ASA_JEJUM = _ref('ASA 2017 (jejum pré-operatório)', 'https://doi.org/10.1097/ALN.0000000000001452')
ASA_JEJUM_2023 = _ref('ASA 2023 (líquidos com carboidrato)', 'https://doi.org/10.1097/ALN.0000000000004381')
COCHRANE_GOMA = _ref('Cochrane 2015 (goma de mascar)', 'https://doi.org/10.1002/14651858.CD006506.pub3')
WINTER = _ref('Winter 2012 (Cockcroft-Gault e peso)', 'https://doi.org/10.1002/j.1875-9114.2012.01098.x')
KDIGO_DRC = _ref('KDIGO 2024 (avaliação da DRC)', 'https://doi.org/10.1016/j.kint.2023.10.018')
BULA_RIVAROXABANA = _ref('Rivaroxabana: ClCr dos estudos com peso real (J&J Medical Information)',
                         'https://www.jnjmedicalconnect.com/products/xarelto/medical-content/'
                         'xarelto-creatinine-clearance-or-estimated-glomerular-filtration-rate-in-adults')
ASA_PS = _ref('ASA 2020 (classificação do estado físico)', 'https://www.asahq.org/standards-and-practice-parameters/'
                                                          'statement-on-asa-physical-status-classification-system')
NSQIP_PANCREAS = _ref('Maggino 2018, NSQIP', 'https://doi.org/10.1016/j.jamcollsurg.2018.01.004')
QUADRIL_TEMPO = _ref('Cantrell 2019', 'https://doi.org/10.2106/JBJS.OA.19.00047')
TEMPO_COLECISTECTOMIA = _ref('Wang 2022', 'https://doi.org/10.1177/00031348221117032')
TEMPO_HERNIA_HIATAL = _ref('Wyland 2025, NSQIP', 'https://doi.org/10.3389/fsurg.2025.1607633')
TEMPO_ESPLENECTOMIA = _ref('Farooq 2026, NSQIP', 'https://doi.org/10.1007/s00464-026-12964-6')
TEMPO_HERNIA = _ref('Sereysky 2019, NSQIP', 'https://doi.org/10.1007/s10029-019-02050-3')
TEMPO_CAROTIDA = _ref('Perri 2017, VQI', 'https://doi.org/10.1016/j.jvs.2017.03.426')
TEMPO_AORTA = _ref('Deery 2017', 'https://doi.org/10.1016/j.jvs.2016.08.100')
TEMPO_COLUNA = _ref('Badhiwala 2021', 'https://doi.org/10.1097/BRS.0000000000003858')
TEMPO_ARTRODESE = _ref('Nooh 2017, NSQIP', 'https://doi.org/10.1177/2192568217699193')
TEMPO_HISTERECTOMIA = _ref('Stewart 2022, NSQIP', 'https://doi.org/10.1016/j.jmig.2022.04.009')
TEMPO_ADRENAL = _ref('Kawashima 2025', 'https://doi.org/10.1007/s11701-025-02882-5')
TEMPO_PONTE = _ref('Radtka 2024, VQI', 'https://doi.org/10.1016/j.jss.2024.05.023')
TEMPO_FIGADO = _ref('Parente 2025, NSQIP', 'https://doi.org/10.1002/jso.70065')
TEMPO_ESOFAGO = _ref('Jacobs 2024, NSQIP', 'https://doi.org/10.1016/j.surg.2024.06.021')
TEMPO_CISTECTOMIA = _ref('Haeuser 2022', 'https://doi.org/10.1159/000522141')
TEMPO_COLECTOMIA = _ref('Al-Temimi 2019, NSQIP', 'https://doi.org/10.1007/s00384-019-03334-x')
TEMPO_LOBECTOMIA = _ref('Dexter 2022', 'https://doi.org/10.1016/j.athoracsur.2022.01.040')
TEMPO_RTU = _ref('Jiang 2021, NSQIP', 'https://doi.org/10.1089/end.2020.0941')
TEMPO_MAMA = _ref('Towfighi 2022, NSQIP', 'https://doi.org/10.1007/s10549-022-06628-x')
TEMPO_TIREOIDE = _ref('Goldfarb 2011, NSQIP', 'https://doi.org/10.1245/s10434-011-1938-2')
TEMPO_ARTROSCOPIA = _ref('Gowd 2019, NSQIP', 'https://doi.org/10.1016/j.arthro.2019.01.059')
TEMPO_PROSTATECTOMIA = _ref('Xia 2018, NSQIP', 'https://doi.org/10.1089/end.2018.0210')
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
    # A linha "colecistectomia, hérnia hiatal, esplenectomia" da SBC/ESC fica em três: o risco cardíaco é o mesmo, mas
    # o de sangramento e a duração não. MICA (Gupta 2011): vesícula e baço em GBAAS; hérnia hiatal em foregut.
    'colecistectomia': _C('Intraperitoneal: colecistectomia', 'intermediario', True, 'abdome_superior', 'maior',
                          mica='gbaas'),
    'hernia_hiatal': _C('Intraperitoneal: hérnia hiatal', 'intermediario', True, 'abdome_superior', 'maior',
                        mica='foregut_hpb'),
    'esplenectomia': _C('Intraperitoneal: esplenectomia', 'intermediario', True, 'abdome_superior', 'maior',
                        mica='gbaas'),
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

CIRURGIAS_ABDOMINAIS = {'colecistectomia', 'hernia_hiatal', 'esplenectomia', 'colectomia', 'perfuracao_intestinal', 'pancreas', 'figado', 'cistectomia',
                        'ginecologica_maior', 'aorta_aberta', 'adrenal', 'urologica_maior', 'transplante_hepatico',
                        'esofagectomia'}

# Liberado depois de passar pelo risco elevado ou por um modificador: o título não diz "não indicado"
TITULO_DO_CAMINHO = {'capacidade_boa': 'Boa capacidade funcional: operar sem prova funcional.'}
TITULO_DA_CONCLUSAO = {'nao_indicada': 'Risco cardiológico não indicado para este paciente.',
                       'incompleto': 'Faltam dados para decidir o risco cardiológico.',
                       'indicada': 'Risco cardiológico indicado para este paciente.',
                       'adiar': 'Estabilizar e adiar a cirurgia eletiva; risco cardiológico indicado.',
                       'emergencia': 'Cirurgia de emergência: operar sem exames que atrasem.'}

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
             'tev', 'tev_recente_3m', 'tev_3_12m', 'tev_mais_12m', 'cancer_ativo', 'trombofilia_grave', 'tabagismo',
             'obesidade',
             'hepatopatia', 'doenca_renal', 'dislipidemia', 'historia_familiar_dac', 'cardiopatia_congenita')
# Fluxo da AHA/ACC (Figura 1). Fatores de risco cardiovascular (nota *): hipertensão, tabagismo, colesterol alto,
# diabetes, obesidade, história familiar de doença coronária precoce, mulher > 65 anos, homem > 55 anos.
FATORES_DE_RISCO = {'hipertensao': 'hipertensão', 'tabagismo': 'tabagismo', 'dislipidemia': 'dislipidemia',
                    'diabetes': 'diabetes', 'obesidade': 'obesidade',
                    'historia_familiar_dac': 'história familiar de doença coronária precoce'}
DOENCA_CARDIOVASCULAR = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'avc_ait', 'fa', 'valvopatia',
                         'doenca_arterial_periferica', 'protese_mecanica', 'hipertensao_pulmonar', 'marcapasso_cdi',
                         'cardiopatia_congenita'}
# Modificadores de risco da mesma figura: seguem para a capacidade funcional com qualquer risco calculado.
MODIFICADORES_DE_RISCO = (
    ({'valvopatia'}, 'valvopatia moderada ou grave'), ({'hipertensao_pulmonar'}, 'hipertensão pulmonar'),
    ({'cardiopatia_congenita'}, 'cardiopatia congênita de risco elevado'),
    ({'stent', 'revascularizacao_cirurgica'}, 'stent coronário ou cirurgia de revascularização'),
    ({'avc_ait_recente'}, 'AVC ou AIT recente'), ({'marcapasso_cdi'}, 'marca-passo ou CDI'))
# Exames cardíacos: quando o fluxo libera o paciente, não são marcados sozinhos (ficam "a considerar", com o aviso)
EXAMES_CARDIACOS = {'Eletrocardiograma de repouso', 'Ecocardiograma transtorácico', 'Peptídeo natriurético BNP/PROBNP',
                    'Troponina, soro'}
# 'incompleto_capacidade_boa': faltou dado para fechar o escore, mas a capacidade funcional libera de qualquer jeito
CAMINHOS_QUE_LIBERAM = ('sem_fatores', 'cirurgia_baixo_risco', 'risco_baixo', 'incompleto_capacidade_boa')
NOTA_DO_FLUXO = ('Nós optamos por seguir o fluxo da AHA/ACC 2026 (Figura 1), que libera este paciente para a cirurgia '
                 'sem exames cardíacos: o exame não foi marcado e fica a considerar.')
# Classe ASA mínima sugerida pelos exemplos aprovados pela ASA (2014, emenda de 2020). É só o ponto de partida do
# campo "Classe ASA": o médico ajusta. IV: IAM, AVC, AIT ou stent há menos de 3 meses, isquemia em curso, disfunção
# valvar grave, choque; a IC descompensada entra pela definição (ameaça constante à vida), não por exemplo listado.
# III: história (> 3 meses) de IAM, AVC, AIT ou DAC/stent, DPOC, marca-passo, fração de ejeção reduzida.
# II: hipertensão ou diabetes controlados, tabagismo, obesidade (IMC 30–40; ≥ 40 é III, calculado na tela).
ASA_MINIMA = {
    'sca': 4, 'angina_grave': 4, 'valvopatia_grave_sintomatica': 4, 'edema_choque': 4, 'ic_descompensada': 4,
    'avc_ait_recente': 4,
    'dac': 3, 'iam_previo': 3, 'stent': 3, 'revascularizacao_cirurgica': 3, 'avc_ait': 3, 'dpoc': 3,
    'marcapasso_cdi': 3, 'ic_fe_reduzida': 3,
    'hipertensao': 2, 'diabetes': 2, 'diabetes_insulina': 2, 'tabagismo': 2, 'obesidade': 2,
}

# Duração típica (faixas do ARISCAT) só onde há série publicada com o tempo operatório; a tela preenche ao escolher a
# cirurgia e o médico ajusta ao caso (a duração real depende da via, da equipe e do paciente).
DURACAO_TIPICA = {
    'rtu': ('menos_2h', 'mediana de 50 min nas cirurgias de hiperplasia prostática', TEMPO_RTU),
    'hernia': ('menos_2h', 'mediana de 53 min na hernioplastia inguinal aberta', TEMPO_HERNIA),
    'colecistectomia': ('menos_2h', 'mediana de 63 min na colecistectomia laparoscópica', TEMPO_COLECISTECTOMIA),
    'hernia_hiatal': ('2_3h', 'mediana de 130 min no reparo laparoscópico (147 min com tela)', TEMPO_HERNIA_HIATAL),
    'esplenectomia': ('2_3h', '130 min na esplenectomia laparoscópica (152 min na robótica)', TEMPO_ESPLENECTOMIA),
    'colectomia': ('mais_3h', 'média de 189 min na colectomia esquerda laparoscópica (219 min na robótica)',
                   TEMPO_COLECTOMIA),
    'carotida_assintomatica': ('menos_2h', 'média de 114 min na endarterectomia de carótida', TEMPO_CAROTIDA),
    'endarterectomia_sintomatica': ('menos_2h', 'média de 114 min na endarterectomia de carótida', TEMPO_CAROTIDA),
    'evar': ('2_3h', 'mediana de 131 a 138 min no reparo endovascular', TEMPO_AORTA),
    'aorta_aberta': ('mais_3h', 'mediana de 215 a 226 min no reparo aberto do aneurisma de aorta abdominal', TEMPO_AORTA),
    'revascularizacao_mmii': ('mais_3h', 'mediana de 210 min na ponte femoropoplítea com veia (155 min com prótese)',
                              TEMPO_PONTE),
    'intratoracica': ('mais_3h', 'média de 185 min na lobectomia por vídeo (178 min na aberta, 214 min na robótica)',
                      TEMPO_LOBECTOMIA),
    'coluna': ('2_3h', 'média de 153 min na laminectomia lombar e de 170 min com artrodese', TEMPO_COLUNA),
    'quadril': ('menos_2h', 'média de 93 min na artroplastia total de quadril', QUADRIL_TEMPO),
    'urologica_maior': ('mais_3h', '195 min na prostatectomia radical minimamente invasiva', TEMPO_PROSTATECTOMIA),
    'ginecologica_maior': ('2_3h', 'mediana de 125 min na histerectomia por doença benigna', TEMPO_HISTERECTOMIA),
    'adrenal': ('2_3h', 'mediana de 131 min na adrenalectomia robótica (168 min na laparoscópica)', TEMPO_ADRENAL),
    'pancreas': ('mais_3h', 'mediana de 358 min na duodenopancreatectomia', NSQIP_PANCREAS),
    'figado': ('mais_3h', 'média de 203 min na hepatectomia laparoscópica (221 min na robótica)', TEMPO_FIGADO),
    'esofagectomia': ('mais_3h', 'mediana de 402 min na esofagectomia minimamente invasiva (321 min na aberta)',
                      TEMPO_ESOFAGO),
    'cistectomia': ('mais_3h', 'média de 5,5 h na cistectomia radical', TEMPO_CISTECTOMIA),
    'mama': ('menos_2h', 'média de 115 min na mastectomia total por câncer de mama', TEMPO_MAMA),
    'tireoide': ('2_3h', 'média de 122 min na tireoidectomia', TEMPO_TIREOIDE),
    'ortopedica_menor': ('menos_2h', 'média de 31 min na artroscopia de joelho', TEMPO_ARTROSCOPIA),
}
# Onde a mesma linha junta operações de durações diferentes, a dica avisa
NOTA_DA_DURACAO = {'coluna': 'Artrodese lombar em série maior: média de 205 min, mais de 3 h (Nooh 2017, NSQIP).',
                   'tireoide': 'Média no limite das 2 h: 119 min na doença benigna e 123 min na maligna. Confira a '
                               'duração prevista.'}

# Risco de sangramento de cada cirurgia: (classe que a tela marca, piso, fonte, nota). Toda cirurgia tem classe; abaixo
# do piso a tela não deixa marcar e o motor sobe para o piso. O piso é a menor classe que a diretriz dá a um
# procedimento daquela linha (ex.: mama é alto no câncer e baixo na biópsia: marca alto, aceita baixo, não aceita mínimo).
# 'sbc': SBC 2024, Tabela 12 (alto: aneurisma de aorta, qualquer grande cirurgia > 45 min, urológica, cabeça e pescoço,
# abdominal, neurocirurgia, câncer de mama, laminectomia, RTU de próstata; baixo: hernioplastia, histerectomia
# abdominal, colecistectomia, endoscopia e broncoscopia com ou sem biópsia, biópsias de mama e de tireoide, dissecção
# de nódulo axilar, curetagem, artroscopia, angiografia não coronariana) e a legenda do manejo dos DOAC (alto:
# neurocirurgia, torácica maior, aorta, revascularização de membros inferiores, endarterectomia de carótida, abdominal
# e pélvica maior, artroplastia de quadril ou joelho). 'aha': AHA/ACC, Tabela 13 (mínimo: catarata, odontologia,
# dermatologia menores).
FONTES_DO_SANGRAMENTO = {'sbc': ('SBC 2024 (Tabela 12 e manejo dos DOAC)', SBC['url']),
                         'aha': ('AHA/ACC 2026 (Tabela 13)', AHA['url'])}
_ALTO_SBC = ('alto', 'alto', 'sbc', '')
_BAIXO_SBC = ('baixo_moderado', 'baixo_moderado', 'sbc', '')
_MAIS_45_MIN = 'Alto em qualquer operação com mais de 45 min.'
_SO_ANGIOGRAFIA = ('baixo_moderado', 'baixo_moderado', 'sbc',
                   'A Tabela 12 lista a angiografia não coronariana; a angioplastia e o stent não são citados.')
SANGRAMENTO_TIPICO = {
    'catarata': ('minimo', 'minimo', 'aha', ''),
    'odontologica': ('minimo', 'minimo', 'aha', ''),
    'endoscopia': ('baixo_moderado', 'baixo_moderado', 'sbc', 'Com polipectomia: alto.'),
    'pele': ('baixo_moderado', 'minimo', 'sbc', 'Procedimento dermatológico menor: mínimo (AHA).'),
    'mama': ('alto', 'baixo_moderado', 'sbc',
             'Alto no câncer de mama; biópsia de mama ou dissecção de linfonodo axilar: baixo.'),
    'tireoide': ('alto', 'baixo_moderado', 'sbc',
                 'Alto na cirurgia de cabeça e pescoço e em qualquer operação com mais de 45 min; biópsia de tireoide: '
                 'baixo.'),
    'ginecologica_menor': _BAIXO_SBC,
    'ortopedica_menor': _BAIXO_SBC,
    'plastica': ('alto', 'baixo_moderado', 'sbc', _MAIS_45_MIN),
    'vats_menor': ('alto', 'baixo_moderado', 'sbc', _MAIS_45_MIN),
    'hernia': _BAIXO_SBC,
    'angioplastia_periferica': _SO_ANGIOGRAFIA,
    'stent_carotida_sintomatica': _SO_ANGIOGRAFIA,
    'colecistectomia': _BAIXO_SBC,
    'intratoracica': ('alto', 'baixo_moderado', 'sbc',
                      'Alto na cirurgia torácica maior e em qualquer operação com mais de 45 min; broncoscopia com ou '
                      'sem biópsia: baixo.'),
    'ginecologica_maior': ('baixo_moderado', 'baixo_moderado', 'sbc', 'Câncer de endométrio ou de ovário: alto.'),
    'quadril': ('alto', 'baixo_moderado', 'sbc',
                'Divergência: a Tabela 12 da SBC (varfarina) lista a prótese de quadril ou joelho como '
                'baixo risco; nós optamos pelo alto, como no manejo dos DOAC da própria SBC.'),
    **{k: _ALTO_SBC for k in (
        'rtu', 'carotida_assintomatica', 'endarterectomia_sintomatica', 'evar', 'cabeca_pescoco', 'hernia_hiatal',
        'esplenectomia', 'colectomia', 'coluna', 'neurocirurgia', 'transplante_renal', 'urologica_maior', 'adrenal',
        'aorta_aberta', 'revascularizacao_mmii', 'pancreas', 'figado', 'esofagectomia', 'pneumectomia',
        'transplante_hepatico', 'transplante_pulmonar', 'perfuracao_intestinal', 'cistectomia')},
}

# O que uma condição grave já diz sobre os antecedentes (a tela marca sozinha; o motor garante o mesmo). SCA e angina
# CCS III/IV são dor isquêmica atual, critério de doença coronária de Lee 1999; IC descompensada e edema agudo são IC.
INSTAVEL_IMPLICA = {'sca': 'dac', 'angina_grave': 'dac', 'ic_descompensada': 'ic', 'edema_choque': 'ic',
                    'valvopatia_grave_sintomatica': 'valvopatia', 'hap_sintomatica': 'hipertensao_pulmonar',
                    'fa_alta_resposta': 'fa'}

def sugestoes_da_tela():
    """O que a tela preenche sozinha a partir do que já foi informado (scripts/gerar_preop.py grava na página)."""
    from src.utils import preop_medicamentos as pm
    from src.utils.medicamentos import MEDICAMENTOS
    return {
        'implica': INSTAVEL_IMPLICA,
        'duracao': {k: {'faixa': faixa, 'texto': texto, 'fonte': ref['label'], 'url': ref['url'],
                        'nota': NOTA_DA_DURACAO.get(k, '')}
                    for k, (faixa, texto, ref) in DURACAO_TIPICA.items()},
        # A duração só entra no ARISCAT: onde ele não se aplica, a tela nem pergunta
        'sem_duracao': sorted(k for k, c in CIRURGIAS.items() if not c['ariscat']),
        'sangramento': {k: {'classe': classe, 'piso': piso, 'fonte': FONTES_DO_SANGRAMENTO[fonte][0],
                            'url': FONTES_DO_SANGRAMENTO[fonte][1], 'nota': nota}
                        for k, (classe, piso, fonte, nota) in SANGRAMENTO_TIPICO.items()},
        # AAS: com doença aterosclerótica ou inibidor de P2Y12 a indicação já é prevenção secundária (não se pergunta)
        'aas_secundaria': sorted(pm._SECUNDARIA), 'p2y12': sorted(pm._P2Y12),
        # Estatina em uso: dislipidemia em tratamento, fator de risco na Figura 1 da AHA/ACC (a tela marca sozinha)
        'estatinas': sorted(m for m, d in MEDICAMENTOS.items() if 'estatina' in d.get('classes', ())),
        'asa_url': ASA_PS['url'],
    }


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


def _inteiro(valor, nome, minimo, maximo):
    """Como ``_num``, mas só aceita número inteiro: classe ASA 2,9 não vira 2."""
    numero = _num(valor, nome, minimo, maximo)
    if numero is not None and numero != int(numero):
        raise EntradaInvalida(f'Confira {nome}: aceito só número inteiro, de {minimo:g} a {maximo:g}.')
    return None if numero is None else int(numero)


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
        'altura': _num(dados.get('altura'), 'a altura (cm)', 100, 250),
        'cirurgia': _escolha(dados.get('cirurgia'), CIRURGIAS, 'a cirurgia proposta', obrigatorio=True),
        'urgencia': _escolha(dados.get('urgencia'), URGENCIAS, 'a urgência', obrigatorio=True),
        'asa': _inteiro(dados.get('asa'), 'a classe ASA', 1, 5),
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
        'fc': _num(dados.get('fc'), 'a frequência cardíaca', 20, 300),
        'infeccao_respiratoria': dados.get('infeccao_respiratoria') in (True, 'sim'),
        'escadas': _escolha(dados.get('escadas'), ('sim', 'nao', 'nao_sabe'), 'a pergunta das escadas'),
        'dasi': _lista(dados.get('dasi'), DASI_ITENS, 'DASI'),
        'dasi_respondido': dados.get('dasi_respondido') in (True, 'sim'),
        'cfs': _inteiro(dados.get('cfs'), 'a Escala Clínica de Fragilidade', 1, 9),
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
    # FA com FC > 120 bpm medida: condição grave da SBC (Tabela 2), mesmo que o item não tenha sido marcado
    if 'fa' in p['condicoes'] and (p['fc'] or 0) > 120:
        p['instaveis'].add('fa_alta_resposta')
    # Peso e altura já dizem a obesidade (IMC ≥ 30) e o item do STOP-Bang (IMC > 35)
    if p['peso'] and p['altura']:
        imc = p['peso'] / (p['altura'] / 100) ** 2
        if imc >= 30:
            p['condicoes'].add('obesidade')
        if imc > 35:
            p['stop_bang'].add('imc_35')
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
    # Risco de sangramento abaixo do que a diretriz dá àquela cirurgia não é aceito (a tela bloqueia; aqui sobe ao piso)
    piso = SANGRAMENTO_TIPICO[p['cirurgia']][1]
    ordem = list(SANGRAMENTOS)
    if p['sangramento'] is not None and ordem.index(p['sangramento']) < ordem.index(piso):
        p['sangramento'] = piso
    for instavel, antecedente in INSTAVEL_IMPLICA.items():
        if instavel in p['instaveis']:
            c.add(antecedente)
    from src.utils.medicamentos import MEDICAMENTOS
    if any('estatina' in MEDICAMENTOS.get(m, {}).get('classes', ()) for m in p['medicacoes']):
        c.add('dislipidemia')        # colesterol alto em tratamento segue sendo fator de risco (AHA/ACC, Figura 1)
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

def clcr_exato(p):
    """Cockcroft-Gault (mL/min), sem arredondar: o valor que se compara com os cortes dos anticoagulantes (15, 30 e
    50). None sem creatinina ou peso."""
    if not p.get('creatinina') or not p.get('peso'):
        return None
    valor = (140 - p['idade']) * p['peso'] / (72 * p['creatinina'])
    return valor * (0.85 if p['sexo'] == 'feminino' else 1)


def clcr(p):
    """Cockcroft-Gault (mL/min) para mostrar, com uma casa; perto de um corte, sem atravessá-lo (29,96 não vira
    30,0). Para decidir, ``clcr_exato``."""
    from src.utils import funcao_renal
    valor = clcr_exato(p)
    return None if valor is None else funcao_renal.para_exibir(valor, funcao_renal.LIMIARES_CLCR, 1)


def _medicacao_com_classe(p, classe):
    from src.utils.medicamentos import MEDICAMENTOS
    return any(classe in MEDICAMENTOS.get(m, {}).get('classes', ()) for m in p['medicacoes'])


def rcri(p):
    cir, c = CIRURGIAS[p['cirurgia']], p['condicoes']
    sint = p['sintomas']
    # Lee 1999: doença isquêmica inclui angina atual; IC inclui sinais (edema pulmonar, B3, estertores, DPN).
    itens = [('Doença coronária', 'dac' in c or 'angina' in sint), ('Insuficiência cardíaca', 'ic' in c or 'sinais_ic' in sint),
             ('AVC ou AIT', 'avc_ait' in c), ('Diabetes com insulina', 'diabetes_insulina' in c),
             ('Creatinina ≥ 2,0 mg/dL', p['creatinina'] is not None and p['creatinina'] >= 2.0),
             ('Cirurgia intraperitoneal, intratorácica ou vascular suprainguinal', cir['rcri'])]
    pontos = sum(1 for _, sim in itens if sim)
    classe = ('I', 'II', 'III', 'IV')[min(pontos, 3)]
    nivel = 'baixo' if pontos <= 1 else 'intermediario' if pontos == 2 else 'alto'
    return {'nome': 'RCRI (Lee)', 'valor': pontos, 'classe': classe, 'nivel': nivel,
            'faixa': f'Classe {classe} · ' + {'baixo': 'baixo', 'intermediario': 'intermediário', 'alto': 'alto'}[nivel],
            'elevado_aha': pontos > 1,
            'itens': [n for n, sim in itens if sim],
            'falta': [] if p['creatinina'] is not None else ['creatinina'],
            # Lee 1999 e SBC 2024 (Tabela 4): "> 2,0"; AHA/ACC 2024–2026 (Tabela 4): "≥ 2,0". Só difere em 2,0 exato.
            'divergencia': ('Creatinina de exatamente 2,0 mg/dL: a AHA (Tabela 4) conta o ponto (≥ 2,0); o estudo '
                            'original de Lee e a SBC só contam acima de 2,0. Nós optamos por seguir a AHA, mais '
                            'conservadora.') if p['creatinina'] is not None and abs(p['creatinina'] - 2.0) < 1e-9 else '',
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
        return dict(base, valor='—', nivel=None, faixa='Faltam dados', itens=[], falta=falta, risco=None)
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


_ARISCAT_NIVEL = {'baixo': 'Baixo', 'intermediario': 'Intermediário', 'alto': 'Alto'}
# Pontos que cada variável obrigatória pode acrescentar quando falta (Canet 2010: SpO₂ 91–95% 8 e ≤ 90% 24;
# hemoglobina ≤ 10 g/dL 11; duração de 2 a 3 h 16 e > 3 h 23)
_ARISCAT_PODE_SOMAR = {'SpO₂': 'SpO₂, até 24 pontos', 'hemoglobina': 'hemoglobina, 11 pontos',
                       'duração da cirurgia': 'duração da cirurgia, até 23 pontos'}


def _nivel_ariscat(pontos):
    return 'baixo' if pontos < 26 else 'intermediario' if pontos < 45 else 'alto'


def ariscat(p):
    """ARISCAT (Canet 2010). SpO₂, hemoglobina e duração da cirurgia são obrigatórias: sem uma delas, o escore sai
    ``status: 'incompleto'``, com ``faltando``, sem categoria (``nivel`` None) e sem valor. Dado ausente não vale zero
    ponto. ``minimo`` é a soma só do que foi informado e ``nivel_minimo`` a faixa dessa soma: o risco é pelo menos
    esse (as medidas que dependem de risco intermediário ou alto usam ``nivel_minimo``, nunca um "baixo" presumido).
    """
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
    nivel = _nivel_ariscat(pontos)
    taxa = {'baixo': '1,6%', 'intermediario': '13,3%', 'alto': '42,1%'}[nivel]
    externa = {'baixo': '3,4%', 'intermediario': '13,0%', 'alto': '38,0%'}[nivel]
    resultado = {'nome': 'ARISCAT', 'valor': pontos, 'nivel': nivel, 'aplicavel': cir['ariscat'],
                 'faixa': _ARISCAT_NIVEL[nivel], 'status': 'calculado', 'faltando': [], 'nivel_minimo': nivel,
                 'itens': [f'{n} ({pts})' for n, pts in itens],
                 'nota': (f'Complicação pulmonar pós-operatória: {taxa} na validação original e {externa} na validação '
                          'externa (PERISCOPE).'),
                 'falta': [], 'referencias': [ARISCAT, PERISCOPE]}
    if not cir['ariscat']:
        resultado.update(faixa='Não se aplica', nivel='baixo', nivel_minimo='baixo', status='nao_aplicavel',
                         nota='O ARISCAT não foi derivado neste tipo de procedimento (anestesia só local, ambulatorial '
                              'ou transplante).')
    elif falta:
        # Variável obrigatória ausente: sem categoria e sem valor. A soma do que foi informado é só o piso do escore.
        if nivel == 'alto':
            piso = (f'Com o que foi informado, a pontuação mínima é {pontos}: já está na faixa de risco alto (≥ 45), '
                    'qualquer que seja o dado que falta.')
        elif nivel == 'intermediario':
            piso = (f'Com o que foi informado, a pontuação mínima é {pontos}: o risco é pelo menos intermediário '
                    '(26 a 44) e passa a alto com 45 ou mais.')
        else:
            piso = (f'Com o que foi informado, a pontuação mínima é {pontos}; a faixa (baixo < 26, intermediário 26 a '
                    '44, alto ≥ 45) depende do que falta.')
        resultado.update(valor='—', nivel=None, faixa='Faltam dados', status='incompleto', faltando=falta, falta=falta,
                         minimo=pontos,
                         nota='Escore incompleto: o risco pulmonar não é classificado. ' + piso + ' O que falta pode '
                              'somar: ' + '; '.join(_ARISCAT_PODE_SOMAR[f] for f in falta) + '.')
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
        div = (f'A AHA não vê benefício no ECG de rotina em assintomático antes de cirurgia de baixo risco '
               f'(classe 3); a SBC indica ({motivos_sbc[0][1]}).')
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
               'e assintomático.')
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
            rastreio = 'indicado'
            if ctx.get('liberado'):
                rastreio = 'considerar'
                div += (' É rastreio oportunístico e não depende do risco cardiológico: com o paciente liberado pelo '
                        'fluxo, não foi marcado e fica a considerar.')
            if dias is not None and dias <= 92:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', 'ja_feito', feita,
                                   aha='2a', sbc='—', outra='SBD I-B', refs=[SBD, AHA, NICE], divergencia=div))
            else:
                saida.append(_item('Hemoglobina glicada (HbA1c), soro', 'laboratorio', rastreio, motivo,
                                   aha='2a', sbc='—', outra='SBD I-B', refs=[SBD, AHA, NICE], divergencia=div))
            gdias = _feito_ha_dias(p, 'Glicose, soro')
            if gdias is not None and gdias <= 92:
                saida.append(_item('Glicose, soro', 'laboratorio', 'ja_feito', f'Feita {_ha_dias(gdias)}.',
                                   outra='SBD I-B', refs=[SBD]))
            else:
                saida.append(_item('Glicose, soro', 'laboratorio', rastreio, motivo + ' Glicemia de jejum.',
                                   outra='SBD I-B', refs=[SBD], divergencia=div if rastreio == 'considerar' else ''))

    # Anemia antes da eletiva: pesquisar ferropenia para tratar com ferro (AHA, manejo da anemia, rec. 2: 2a B-R)
    hb = p.get('hemoglobina')
    if hb is not None and p['urgencia'] in ('eletiva', 'tempo_sensivel') and hb < (13 if p['sexo'] == 'masculino' else 12):
        for titulo in ('Ferritina, soro', 'Índice de saturação de transferrina, soro'):
            saida.append(_item(titulo, 'laboratorio', 'indicado',
                               f'Anemia (hemoglobina {_fmt(hb)} g/dL): pesquisar ferropenia, que se trata com ferro antes '
                               'da cirurgia eletiva.', aha='2a (tratamento)', sbc='—', refs=[AHA]))

    # Exames de rotina (NICE NG45): "Offer" = indicado; "Consider" = considerar
    asa, porte = p['asa'], cir['porte']
    renal = 'doenca_renal' in c
    meds = ctx['classes_medicacoes']
    faltam = ctx.get('faltam_para_o_risco') or set()
    if porte == 'maior':
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'indicado', 'Cirurgia de grande porte.',
                           outra='NICE', refs=[NICE]))
    elif 'hemoglobina' in faltam:
        saida.append(_item('Hemograma completo com plaquetas', 'laboratorio', 'indicado',
                           'A hemoglobina falta para fechar o AUB-HAS2 e pode mudar a indicação do risco cardiológico.',
                           outra='Escores', refs=[AUB, SBC]))
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
    if 'creatinina' in faltam and estado_renal != 'indicado':
        estado_renal, ref_renal = 'indicado', [LEE, SBC]
        motivo_renal = 'A creatinina falta para fechar o escore e pode mudar a indicação do risco cardiológico.'
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
    transplante = p['cirurgia'] in ('transplante_hepatico', 'transplante_renal', 'transplante_pulmonar')
    for item in saida:
        if item['titulo'] not in EXAMES_CARDIACOS or item['estado'] != 'indicado':
            continue
        if ctx.get('liberado') and not transplante and not item['aha'].startswith('1'):
            item['estado'] = 'considerar'
            item['divergencia'] = (item['divergencia'] + ' ' + NOTA_DO_FLUXO).strip()
        elif item['aha'].startswith('3'):
            item['divergencia'] = (item['divergencia'] + ' Nós optamos por sugerir, sinalizando a diferença.').strip()
    for item in saida:
        achado = _feito(p, item['titulo']) if item['categoria'] != 'outro' else None
        if achado:
            item['ultimo'] = f'Último em {achado[1]} ({_ha_dias(achado[0])})'
    return saida


# ── Indicação, adiamentos e pós-operatório ──────────────────────────────────

def _passo(pergunta, resposta, estado, texto, refs=(), libera=False):
    return {'pergunta': pergunta, 'resposta': resposta, 'estado': estado, 'texto': texto, 'referencias': list(refs),
            'libera': libera}


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


def _orientacoes_perioperatorias(p, cir_ia):
    """Orientações gerais, cada uma só para quem está na situação (jejum, higiene oral, anemia, sangramento, íleo)."""
    saida = []
    eletiva = p['urgencia'] in ('eletiva', 'tempo_sensivel')
    if eletiva:
        saida.append({'titulo': 'Jejum antes da anestesia',
                      'texto': 'Líquidos claros (água, chá, café sem leite, suco sem polpa) até 2 h antes; refeição leve '
                               'até 6 h antes; frituras, gordura ou carne até 8 h antes. Bebida clara com carboidrato pode '
                               'ser tomada até 2 h antes por adultos. Em uso de aGLP-1 ou tirzepatida, vale a orientação '
                               'própria (dieta líquida nas 24 h antes e jejum de 8 a 12 h).',
                      'classe': 'ASA 2017 e 2023: diretriz de prática', 'referencias': [ASA_JEJUM, ASA_JEJUM_2023]})
    if cir_ia:
        saida.append({'titulo': 'Higiene oral com antisséptico',
                      'texto': 'Bochecho com 15 mL de clorexidina 0,2% (ou iodopovidona 5%) por 30 a 60 s antes e depois '
                               'da cirurgia, para reduzir infecção; tratar doença periodontal ou dentária antes da eletiva.',
                      'classe': 'SBC IIa-B', 'referencias': [SBC]})
    hb = p.get('hemoglobina')
    if hb is not None and eletiva and hb < (13 if p['sexo'] == 'masculino' else 12):
        saida.append({'titulo': f'Anemia (hemoglobina {_fmt(hb)} g/dL)',
                      'texto': 'Pesquisar ferropenia: ferritina < 100 ng/mL, saturação de transferrina < 20% ou '
                               'microcitose. Se ferropriva, ferro antes da cirurgia eletiva reduz transfusão e eleva a '
                               'hemoglobina; com menos de 2 semanas até a cirurgia, o ferro venoso funciona melhor que o '
                               'oral.',
                      'classe': 'AHA 2a (B-R)', 'referencias': [AHA]})
    if p['sangramento'] == 'alto' or CIRURGIAS[p['cirurgia']]['porte'] == 'maior':
        saida.append({'titulo': 'Ácido tranexâmico se houver perda sanguínea esperada',
                      'texto': 'Reduz o sangramento, a transfusão e a anemia pós-operatória; decisão da equipe cirúrgica '
                               'e da anestesia, pesando as contraindicações.',
                      'classe': 'AHA 2a (A)', 'referencias': [AHA]})
    if p['cirurgia'] in CIRURGIAS_ABDOMINAIS:
        saida.append({'titulo': 'Mascar chiclete depois da cirurgia abdominal',
                      'texto': 'Mascar goma é uma "alimentação simulada": estimula o nervo vago e o reflexo '
                               'cefálico, que aceleram o retorno do intestino e ajudam a evitar o íleo paralítico. Em 81 '
                               'ensaios (9.072 pacientes), antecipou os flatos em cerca de 10 h e a evacuação em cerca de '
                               '13 h e encurtou a internação em cerca de 0,7 dia, sem mais complicações. Ensaios pequenos e '
                               'de qualidade baixa; o efeito é menor dentro de protocolos de recuperação acelerada (ERAS).',
                      'classe': 'Cochrane 2015: evidência de qualidade baixa', 'referencias': [COCHRANE_GOMA]})
    return saida


def _detalhe_da_conclusao(conclusao, nota):
    """Linha sob o título da conclusão: o motivo (o passo do fluxo que liberou ou que indicou)."""
    tipo, texto = conclusao
    if tipo == 'nao_indicada':
        return texto        # a tela põe o rótulo "Motivo:" na frente
    prefixo = 'Avaliação cardiológica indicada: '
    return 'Motivo: ' + texto[len(prefixo):] if texto.startswith(prefixo) else texto


def avaliar(p):
    """Resultado completo da avaliação pré-operatória."""
    from src.utils.medicamentos import classes_de
    cir = CIRURGIAS[p['cirurgia']]
    c = p['condicoes']
    escore_rcri, escore_aub, escore_vsg, escore_mica = rcri(p), aub_has2(p), vsg_cri(p), mica(p)
    cap = capacidade_funcional(p)
    dcv = bool(c & DOENCA_CARDIOVASCULAR)
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
    # Dado ausente não é dado normal: se o que falta pode levar o escore ao risco elevado, o risco do paciente fica
    # "incompleto" em vez de "baixo" (creatinina no RCRI e no VSG-CRI; hemoglobina no AUB-HAS2).
    faltam_para_o_risco = []
    if not risco_elevado:
        rcri_sobe = p['creatinina'] is None and escore_rcri['valor'] == 1
        vsg_sobe = p['creatinina'] is None and escore_vsg is not None and 3 <= escore_vsg['valor'] <= 4
        if rcri_sobe or vsg_sobe:
            efeito = ' e '.join(x for x in ('com ≥ 2,0 mg/dL, o RCRI passa a 2' if rcri_sobe else '',
                                            'com > 1,8 mg/dL, o VSG-CRI passa a 5 ou mais' if vsg_sobe else '') if x)
            faltam_para_o_risco.append(('creatinina', f'creatinina ({efeito})'))
        if p['hemoglobina'] is None and escore_aub['valor'] == 1:
            faltam_para_o_risco.append(('hemoglobina', 'hemoglobina (com < 12 g/dL, o AUB-HAS2 passa a 2)'))
    incompleto = bool(faltam_para_o_risco)
    mica_sem_dados = escore_mica.get('risco') is None and bool(escore_mica.get('falta'))
    sint_isq_novo = bool(p['sintomas'] & {'angina', 'dispneia_nova'})

    # AHA/ACC, Figura 1, primeira pergunta: fator de risco, doença ou sintoma cardiovascular
    fatores = [rotulo for k, rotulo in FATORES_DE_RISCO.items() if k in c]
    if (p['sexo'] == 'feminino' and p['idade'] > 65) or (p['sexo'] == 'masculino' and p['idade'] > 55):
        fatores.append('mulher com mais de 65 anos' if p['sexo'] == 'feminino' else 'homem com mais de 55 anos')
    tem_fator_doenca_ou_sintoma = bool(fatores or dcv or p['sintomas'] or p['instaveis'] or p['pa_descontrolada'])
    # Modificadores de risco da mesma figura (fragilidade: CFS ≥ 5)
    frag = fragilidade(p)
    modificadores = [rotulo for chaves, rotulo in MODIFICADORES_DE_RISCO if c & chaves]
    if frag and frag['valor'] >= 5 and frag['valor'] != 9:
        modificadores.append('fragilidade')

    passos, conclusao, nota_conclusao, caminho = [], None, '', None

    def liberar(texto, por):
        passos[-1]['libera'] = True
        return ('nao_indicada', texto), por

    passos.append(_passo('Cirurgia de emergência?', 'Sim' if emergencia else 'Não', 'atencao' if emergencia else 'ok',
                         'Operar sem exames que atrasem a cirurgia; só monitorização e redução de risco.',
                         refs=[AHA, SBC]))
    if emergencia:
        conclusao, caminho = ('emergencia', 'Cirurgia de emergência: sem avaliação que atrase a operação. '
                              'Monitorização, troponina pós-operatória se houver risco e manejo dos medicamentos.'), \
            'emergencia'
    if not conclusao:
        # Sem fator, doença ou sintoma, a AHA libera. Nós só liberamos aqui se o escore também não estiver elevado e
        # não houver doença renal (item do RCRI): a SBC calcula o escore para todos.
        pesa = ', '.join(elevado_por) or ('doença renal crônica (item do RCRI)' if 'doenca_renal' in c else '')
        saudavel = not tem_fator_doenca_ou_sintoma and not pesa
        texto_passo = ('Sem nenhum deles, o paciente é liberado para a cirurgia, sem avaliação cardiológica nem exames '
                       'cardíacos. Fatores de risco: hipertensão, tabagismo, dislipidemia, diabetes, obesidade, '
                       'história familiar de doença coronária precoce, mulher com mais de 65 anos, homem com mais '
                       'de 55.')
        if tem_fator_doenca_ou_sintoma:
            tem = fatores[:] + (['doença cardiovascular'] if dcv or p['instaveis'] else []) \
                + (['sintomas'] if p['sintomas'] else []) + (['PA ≥ 180 × 110'] if p['pa_descontrolada'] else [])
            texto_passo += ' Neste paciente: ' + ', '.join(tem) + '.'
        elif pesa:
            texto_passo += f' Este paciente não tem nenhum deles, mas segue no fluxo: {pesa}.'
        passos.append(_passo('Fator de risco, doença ou sintoma cardiovascular?',
                             'Sim' if tem_fator_doenca_ou_sintoma else 'Não',
                             'ok' if saudavel else 'atencao', texto_passo, refs=[AHA]))
        if saudavel:
            conclusao, caminho = liberar('Sem fator de risco, doença ou sintoma cardiovascular: liberar para a '
                                         'cirurgia, sem avaliação cardiológica nem exames cardíacos.', 'sem_fatores')
    if not conclusao:
        inst = bool(p['instaveis']) or p['pa_descontrolada']
        passos.append(_passo('Condição cardiovascular grave ou instável?', 'Sim' if inst else 'Não',
                             'atencao' if inst else 'ok',
                             'SCA, IC descompensada, angina CCS III/IV, estenose aórtica ou mitral importante '
                             'sintomática, BAVT/TV, FA com FC > 120, PA ≥ 180 × 110, HAP sintomática.',
                             refs=[AHA, SBC]))
        if inst and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
            conclusao, caminho = ('adiar', 'Condição grave ou instável: estabilizar e adiar a cirurgia eletiva; '
                                  'avaliação cardiológica indicada.'), 'instavel'
        elif inst:
            conclusao, caminho = ('indicada', 'Condição grave ou instável em cirurgia de urgência: estabilizar o '
                                  'quanto o tempo permitir, sem atrasar a operação; avaliação cardiológica e '
                                  'monitorização perioperatória.'), 'instavel'
    if not conclusao:
        passos.append(_passo('Risco intrínseco da cirurgia', RISCO_DA_CIRURGIA[cir['risco']].split(' (')[0],
                             'ok' if not cir_ia else 'atencao',
                             'Baixo risco (< 1%) em paciente estável: não há avaliação cardiológica nem exames '
                             'cardíacos de rotina indicados.', refs=[SBC, AHA]))
        if not cir_ia:
            conclusao, caminho = liberar('Cirurgia de baixo risco em paciente estável: avaliação cardiológica e '
                                         'exames cardíacos de rotina não indicados. Pode operar.',
                                         'cirurgia_baixo_risco')
    if not conclusao:
        texto_passo = ('RCRI 0–1, AUB-HAS2 0–1 e Gupta MICA < 1%, sem modificador de risco: risco baixo; liberar sem '
                       'testes de isquemia. Modificadores: valvopatia grave, hipertensão pulmonar grave, cardiopatia '
                       'congênita de risco elevado, stent coronário ou cirurgia de revascularização, AVC recente, '
                       'marca-passo ou CDI, fragilidade. Com modificador, o fluxo segue com qualquer risco calculado.')
        if modificadores:
            texto_passo += ' Neste paciente: ' + ', '.join(modificadores) + '.'
        if incompleto:
            texto_passo += ' Faltam dados que podem mudar o escore: ' + '; '.join(t for _, t in faltam_para_o_risco) + '.'
        if mica_sem_dados and not risco_elevado:
            artigos = [{'classe ASA': 'a classe ASA', 'estado funcional': 'o estado funcional'}.get(x, x)
                       for x in escore_mica['falta']]
            texto_passo += (' Gupta MICA não calculado: ' + ('faltam ' if len(artigos) > 1 else 'falta ')
                            + ' e '.join(artigos) + '.')
        passos.append(_passo('Risco calculado e modificadores de risco',
                             'Elevado' if risco_elevado else 'Modificador' if modificadores
                             else 'Incompleto' if incompleto else 'Baixo',
                             'atencao' if risco_elevado or modificadores or incompleto else 'ok', texto_passo,
                             refs=[AHA, SBC]))
        if not risco_elevado and not modificadores and not incompleto:
            conclusao, caminho = liberar('Risco calculado baixo e sem modificador de risco: liberar sem '
                                         'investigação de isquemia.', 'risco_baixo')
    investigar = False
    if not conclusao:
        estado = cap['estado']
        passos.append(_passo('Capacidade funcional', cap['valor'], 'ok' if estado == 'boa' else 'atencao',
                             '≥ 4 METs (sobe 2 lances) ou DASI > 34, com sintomas estáveis: liberar sem prova funcional. '
                             'Baixa ou desconhecida: biomarcadores e, só se mudar a conduta, prova funcional.',
                             refs=[AHA, SBC]))
        if estado == 'boa':
            if risco_elevado:
                texto = 'Risco elevado, mas boa capacidade funcional: liberar sem prova funcional.'
            elif modificadores:
                texto = ('Modificador de risco (' + ', '.join(modificadores) + '), mas boa capacidade funcional: '
                         'liberar sem prova funcional. Com modificador, a AHA/ACC sugere discutir em equipe o '
                         'momento da cirurgia e os exames.')
            else:
                texto = 'Risco do paciente incompleto, mas boa capacidade funcional: liberar sem prova funcional.'
            if sint_isq_novo:
                nota_conclusao = ('Angina ou dispneia nova ou em mudança: investigar como fora do contexto cirúrgico, '
                                  'pelas diretrizes de dor torácica e doença coronária.')
                texto += ' ' + nota_conclusao
            passos[-1]['libera'] = True
            conclusao = ('nao_indicada', texto)
            caminho = 'capacidade_boa' if risco_elevado or modificadores else 'incompleto_capacidade_boa'
        elif incompleto and not modificadores:
            # Sem o dado, não se sabe se o risco é elevado: o exame que falta vem antes de qualquer teste de isquemia.
            conclusao, caminho = ('incompleto', 'Faltam dados para fechar o risco do paciente: '
                                  + '; '.join(t for _, t in faltam_para_o_risco) + '. Com o resultado: risco elevado, '
                                  'avaliação cardiológica indicada; risco baixo, liberar sem investigação de '
                                  'isquemia.'), 'incompleto'
        else:
            # Prova de isquemia só com risco calculado elevado (AHA 2b; SBC IIa); só com modificador, a avaliação é
            # indicada (equipe, biomarcadores), sem prova funcional de saída
            investigar = risco_elevado and p['urgencia'] in ('eletiva', 'tempo_sensivel', 'urgencia')
            motivos = [f'cirurgia de risco {RISCO_DA_CIRURGIA[cir["risco"]].split(" (")[0].lower()}',
                       ', '.join(elevado_por), *modificadores, f'capacidade funcional {cap["valor"].lower()}']
            conclusao, caminho = ('indicada', 'Avaliação cardiológica indicada: '
                                  + '; '.join(m for m in motivos if m) + '.'), 'investigar'
    # Dispneia nova, sinais de IC ou sopro: avaliar o VE ou a valva antes de qualquer cirurgia eletiva (AHA §4.2, 1;
    # §6.5, 1), qualquer que seja o escore ou a capacidade.
    if conclusao[0] in ('nao_indicada', 'incompleto') and p['sintomas'] & {'dispneia_nova', 'sinais_ic', 'sopro'} \
            and p['urgencia'] in ('eletiva', 'tempo_sensivel'):
        conclusao = ('indicada', 'Dispneia nova, sinais de insuficiência cardíaca ou sopro: avaliar a função '
                                 'ventricular ou a valva (ecocardiograma) antes de operar.')
        caminho = 'sintoma_novo'
        for passo in passos:
            passo['libera'] = False
    if any(not a.get('ok') for a in adiar) and conclusao[0] in ('nao_indicada', 'indicada', 'incompleto'):
        conclusao = (conclusao[0], conclusao[1] + ' Antes, veja o que pede adiamento.')

    classes_meds = set(classes_de(p['medicacoes']))
    liberado = conclusao[0] == 'nao_indicada' and caminho in CAMINHOS_QUE_LIBERAM
    ctx = {'cir_elev': cir_ia, 'pac_ia': pac_ia, 'dcv': dcv, 'investigar_isquemia': investigar, 'liberado': liberado,
           'classes_medicacoes': classes_meds, 'capacidade': cap['estado'],
           'faltam_para_o_risco': {k for k, _ in faltam_para_o_risco} if conclusao[0] == 'incompleto' else set()}
    lista_exames = exames(p, ctx)

    escores = [escore_rcri, escore_aub]
    if escore_vsg:
        escores.append(escore_vsg)
    escores.append(escore_mica)
    escores.append(cap)
    if frag:
        escores.append(frag)
    # ClCr e TFG: os valores exatos vão para as regras (cortes de 15, 30, 45 e 50); a tela recebe os de exibição,
    # que nunca aparecem do outro lado de um corte (TFG de 29,6 não é mostrada como 30).
    from src.utils import funcao_renal, prevent
    depuracao_exata = clcr_exato(p)
    depuracao = clcr(p)
    tfg_exata = prevent.tfg_ckd_epi_2021(float(p['creatinina']), p['idade'], p['sexo']) if p['creatinina'] else None
    tfg = None if tfg_exata is None else funcao_renal.para_exibir(tfg_exata, funcao_renal.LIMIARES_TFG)
    notas_renais = []
    if depuracao is not None and ('obesidade' in c or 'imc_35' in p['stop_bang']):
        notas_renais.append({'texto': 'Obesidade: o Cockcroft-Gault com peso real superestima a depuração; o peso '
                                      'ajustado erra menos. Nós optamos pelo peso real, o mesmo do Cockcroft-Gault dos '
                                      'estudos dos anticoagulantes (por exemplo, ROCKET AF e EINSTEIN); com o ClCr perto '
                                      'de um limiar de dose ou de suspensão, decida com cautela.',
                             'referencias': [WINTER, BULA_RIVAROXABANA]})
    if depuracao is not None or tfg is not None:
        notas_renais.append({'texto': 'O ClCr e a TFG supõem creatinina estável: na lesão renal aguda, não valem.',
                             'referencias': [KDIGO_DRC]})

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
    orientacoes.extend(_orientacoes_perioperatorias(p, cir_ia))

    pulmonar = ariscat(p)
    medidas_pulmonares = []
    # Com o ARISCAT incompleto vale o piso (nivel_minimo): as medidas entram quando o risco é pelo menos intermediário
    if (pulmonar.get('aplicavel', True) and pulmonar['nivel_minimo'] != 'baixo') or 'dpoc' in c or 'ic' in c \
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
    # ARISCAT incompleto não é ARISCAT baixo: sem a categoria, o resultado completo fica à vista.
    resumido = (conclusao[0] == 'nao_indicada' and not cir_ia and p['idade'] < 65 and not c
                and not risco_elevado and not p['sintomas'] and not p['instaveis'] and not p['pa_descontrolada']
                and not any(not a.get('ok') for a in adiar)
                and (not pulmonar.get('aplicavel', True) or pulmonar['nivel'] == 'baixo')
                and sb['nivel'] != 'alto' and (frag is None or (frag['valor'] or 0) < 5))
    resumo = None
    if resumido:
        resumo = {'titulo': 'Risco cardiológico não indicado para este paciente.',
                  'texto': 'Motivo: cirurgia de baixo risco (< 1%), em paciente com menos de 65 anos, sem '
                           'comorbidade, sem sintomas e sem condição instável. Exames cardíacos adicionais não mudam '
                           'a conduta neste perfil; pode operar.',
                  'referencias': [AHA, SBC]}

    return {
        'resumido': resumido,
        'resumo': resumo,
        'cirurgia': {'rotulo': cir['rotulo'], 'risco': RISCO_DA_CIRURGIA[cir['risco']],
                     'urgencia': URGENCIAS[p['urgencia']]},
        'indicacao': {'passos': passos, 'tipo': conclusao[0], 'conclusao': conclusao[1], 'caminho': caminho,
                      'liberado': liberado,
                      'titulo': TITULO_DO_CAMINHO.get(caminho, TITULO_DA_CONCLUSAO[conclusao[0]]),
                      'nota': nota_conclusao,
                      'detalhe': _detalhe_da_conclusao(conclusao, nota_conclusao),
                      'referencias': [AHA, SBC],
                      'divergencia': ('A AHA recomenda o escore em quem tem doença cardiovascular conhecida (2a) e '
                                      'classifica o risco em baixo ou elevado (≥ 1%); a SBC calcula para todos, em '
                                      'baixo, intermediário ou alto. Nós optamos por calcular para todos e mostrar '
                                      'as duas classificações.')},
        'adiar': adiar,
        'escores': escores,
        'clcr': depuracao,
        'tfg': tfg,
        'clcr_exato': depuracao_exata,
        'tfg_exata': tfg_exata,
        'exames': lista_exames,
        'orientacoes': orientacoes,
        'pulmonar': {'escore': pulmonar, 'stop_bang': sb, 'medidas': medidas_pulmonares},
        'pos_operatorio': pos,
        'notas_renais': notas_renais,
        'contexto': {'cir_elev': cir_ia, 'pac_ia': pac_ia, 'risco_elevado': risco_elevado, 'dcv': dcv,
                     'risco_incompleto': incompleto},
    }
