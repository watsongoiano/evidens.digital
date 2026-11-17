"""Validação clínica do pré-operatório por pacientes inteiros (dados fictícios).

Cada caso é um paciente completo. O resultado de `preoperatorio.avaliar` é comparado com um ORÁCULO escrito neste
arquivo a partir das fontes primárias, sem copiar a lógica do módulo:

- RCRI: Lee TH et al., Circulation 1999;100:1043 (doi:10.1161/01.cir.100.10.1043). Doença isquêmica = IAM, prova
  funcional positiva, angina isquêmica, nitrato ou onda Q; revascularização prévia só conta com outro critério.
  IC = história de IC, edema pulmonar, DPN, estertores bilaterais/B3 ou redistribuição na radiografia.
- AUB-HAS2: Dakik HA et al., JACC 2019;73:3067 (doi:10.1016/j.jacc.2019.04.023) e JAHA 2020;9:e016228
  (doi:10.1161/JAHA.119.016228): história de doença cardíaca = IAM, angioplastia, CIRURGIA CARDÍACA, IC, FA ou
  valvopatia moderada/grave; 0–1 baixo, 2–3 intermediário, > 3 alto.
- VSG-CRI: Bertges DJ et al., J Vasc Surg 2010;52:674 (doi:10.1016/j.jvs.2010.03.031); SBC 2024 Tabelas 6–7.
- DASI: Hlatky MA et al., Am J Cardiol 1989;64:651 (doi:10.1016/0002-9149(89)90496-7); ≤ 34 = capacidade baixa
  (Wijeysundera, BJA 2020, doi:10.1016/j.bja.2019.11.025; AHA 2026 nota das recomendações de estresse).
- ARISCAT: Canet J et al., Anesthesiology 2010;113:1338 (doi:10.1097/ALN.0b013e3181fc6e0a).
- STOP-Bang: Chung F et al., Chest 2016;149:631 (doi:10.1378/chest.15-0903).
- Cockcroft DW, Gault MH, Nephron 1976;16:31 (doi:10.1159/000180580).
- AHA/ACC 2026 (= 2024, doi:10.1161/CIR.0000000000001285): Tabela 2, Figura 1 e recomendações (ECG, função de VE,
  BNP, troponina, estresse, CCTA, ICA, PA, ICP, AVC, HbA1c, fragilidade, AOS, MINS).
- SBC 2024 (Gualandro et al., doi:10.36660/abc.20240590): Tabelas 2–7 e Quadros 1–7, 9, 16, 17, 22, 23, 29, 30.
- NICE NG45 (2016): exames de rotina por ASA × porte (https://www.nice.org.uk/guidance/ng45).

Divergências entre o módulo e o oráculo ficam marcadas como xfail(strict=True) com a fonte. Data de referência:
16/11/2026.
"""
from datetime import date

import pytest

from src.utils import periodicidade
from src.utils import preoperatorio as po

HOJE = date(2026, 11, 16)
TX_HEP = 'transplante_hepatico' if 'transplante_hepatico' in po.CIRURGIAS else 'transplante_figado_pulmao'

# ════════════════════════════════════════════════════════════════════════════
# ORÁCULO
# ════════════════════════════════════════════════════════════════════════════

# Cirurgia → (risco SBC/ESC, RCRI "alto risco" (Lee), incisão ARISCAT (Canet), porte NICE (None = ambíguo),
#             vascular arterial (AUB-HAS2 / VSG-CRI), transplante hepático, urológica)
B, M, A = 'baixo', 'intermediario', 'alto'
PER, ABD, TOR = 'periferica', 'abdome_superior', 'intratoracica'
SURG = {
    'catarata': (B, False, PER, 'menor', False, False, False),
    'odontologica': (B, False, PER, 'menor', False, False, False),
    'endoscopia': (B, False, PER, 'menor', False, False, False),
    'pele': (B, False, PER, 'menor', False, False, False),
    'mama': (B, False, PER, None, False, False, False),
    'tireoide': (B, False, PER, 'maior', False, False, False),           # NICE: tireoidectomia = maior
    'ginecologica_menor': (B, False, PER, None, False, False, False),
    'ortopedica_menor': (B, False, PER, 'intermediaria', False, False, False),  # NICE: artroscopia de joelho
    'plastica': (B, False, PER, None, False, False, False),
    'rtu': (B, False, PER, 'maior', False, False, True),                 # NICE: ressecção endoscópica de próstata
    'vats_menor': (B, True, TOR, 'maior', False, False, False),          # intratorácica (Lee); pulmão (NICE)
    'hernia': (B, False, PER, 'intermediaria', False, False, False),     # NICE: hérnia inguinal
    'carotida_assintomatica': (M, False, PER, None, True, False, False),
    'endarterectomia_sintomatica': (M, False, PER, None, True, False, False),
    'evar': (M, True, PER, 'maior', True, False, False),                 # aorta = vascular suprainguinal
    'angioplastia_periferica': (M, False, PER, None, True, False, False),
    'cabeca_pescoco': (M, False, PER, 'maior', False, False, False),
    'colecistectomia': (M, True, ABD, None, False, False, False),
    'hernia_hiatal': (M, True, ABD, None, False, False, False),
    'esplenectomia': (M, True, ABD, None, False, False, False),
    'colectomia': (M, True, ABD, 'maior', False, False, False),
    'intratoracica': (M, True, TOR, 'maior', False, False, False),
    'coluna': (M, False, PER, 'maior', False, False, False),
    'neurocirurgia': (M, False, PER, 'maior', False, False, False),      # SBC Tabela 3: neurológica
    'quadril': (M, False, PER, 'maior', False, False, False),
    'transplante_renal': (M, False, PER, 'maior', False, False, True),
    'urologica_maior': (M, True, PER, 'maior', False, False, True),
    'ginecologica_maior': (M, True, PER, 'maior', False, False, False),  # abdome inferior = periférica (ARISCAT)
    'adrenal': (A, True, ABD, 'maior', False, False, False),
    'aorta_aberta': (A, True, ABD, 'maior', True, False, False),
    'stent_carotida_sintomatica': (A, False, PER, None, True, False, False),
    'revascularizacao_mmii': (A, False, PER, 'maior', True, False, False),  # infrainguinal: não pontua no RCRI
    'pancreas': (A, True, ABD, 'maior', False, False, False),
    'figado': (A, True, ABD, 'maior', False, False, False),
    'esofagectomia': (A, True, TOR, 'maior', False, False, False),
    'pneumectomia': (A, True, TOR, 'maior', False, False, False),
    TX_HEP: (A, True, ABD, 'maior', False, True, False),
    'perfuracao_intestinal': (A, True, ABD, 'maior', False, False, False),
    'cistectomia': (A, True, PER, 'maior', False, False, True),
}
if 'transplante_pulmonar' in po.CIRURGIAS:
    SURG['transplante_pulmonar'] = (A, True, TOR, 'maior', False, False, False)
# ARISCAT não se aplica: só anestesia local/bloqueio periférico ou transplante (Canet 2010, critérios de exclusão)
ARISCAT_NA = {'catarata', 'odontologica', 'endoscopia', 'pele', 'transplante_renal', TX_HEP, 'transplante_pulmonar'}
CAROTIDA_SINTOMATICA = {'endarterectomia_sintomatica', 'stent_carotida_sintomatica'}

DASI_PESOS = {'cuidar_de_si': 2.75, 'andar_em_casa': 1.75, 'andar_quarteiroes': 2.75, 'subir_lance': 5.50,
              'correr': 8.00, 'domestico_leve': 2.70, 'domestico_moderado': 3.50, 'domestico_pesado': 8.00,
              'jardinagem': 4.50, 'relacoes_sexuais': 5.25, 'recreacao_moderada': 6.00,
              'esporte_extenuante': 7.50}                                  # Hlatky 1989
BETABLOQ = {'atenolol', 'metoprolol', 'nebivolol', 'carvedilol', 'bisoprolol', 'propranolol', 'atenolol_clortalidona'}
DOAC = {'rivaroxabana', 'apixabana', 'dabigatrana', 'edoxabana'}
DCV = {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'avc_ait', 'fa', 'valvopatia',
       'protese_mecanica', 'doenca_arterial_periferica', 'hipertensao_pulmonar', 'marcapasso_cdi'}
INSTAVEL_ROTULO = dict(po.INSTAVEIS)
IC_RECENTE = 'Insuficiência cardíaca recente, tratamento ainda não otimizado'

# Conjuntos de itens do DASI
DASI_TUDO = list(DASI_PESOS)                                                          # 58,2
DASI_POUCO = ['cuidar_de_si', 'andar_em_casa', 'andar_quarteiroes', 'domestico_leve']  # 9,95
DASI_34 = ['correr', 'domestico_pesado', 'recreacao_moderada', 'esporte_extenuante', 'jardinagem']  # 34,0
DASI_3475 = ['correr', 'domestico_pesado', 'recreacao_moderada', 'esporte_extenuante', 'relacoes_sexuais']  # 34,75


def _dias(texto):
    a, m, d = (int(x) for x in texto.split('-'))
    return (HOJE - date(a, m, d)).days


class Paciente:
    """Leitura independente do caso (não usa po.ler)."""

    def __init__(self, c):
        self.c = c
        self.idade = c['idade']
        self.sexo = c['sexo']
        self.cir = c['cirurgia']
        self.urg = c.get('urgencia', 'eletiva')
        self.risco, self.rcri_cir, self.incisao, self.porte, self.vascular, self.tx_hep, self.urologica = SURG[self.cir]
        cond = set(c.get('condicoes', []))
        meds = set(c.get('medicacoes', []))
        if any(m.startswith('insulina') for m in meds):
            cond.add('diabetes_insulina')
        if any(m.endswith('statina') for m in meds):
            cond.add('dislipidemia')             # colesterol alto em tratamento segue fator de risco (AHA Figura 1)
        if 'diabetes_insulina' in cond:
            cond.add('diabetes')
        if cond & {'ic_fe_reduzida', 'ic_recente'}:
            cond.add('ic')                       # IC de início recente também é história de IC (Lee; Dakik)
        if 'avc_ait_recente' in cond:
            cond.add('avc_ait')
        if 'protese_mecanica_mitral' in cond:
            cond.add('protese_mecanica')
        self.sint = set(c.get('sintomas', []))
        self.inst = set(c.get('instaveis', []))
        # A condição grave já diz o antecedente: SCA e angina CCS III/IV são dor isquêmica atual (doença coronária em
        # Lee 1999); IC descompensada e edema agudo são IC; estenose importante sintomática é valvopatia; HAP
        # sintomática é hipertensão pulmonar; FA com FC > 120 é FA.
        for instavel, antecedente in (('sca', 'dac'), ('angina_grave', 'dac'), ('ic_descompensada', 'ic'),
                                      ('edema_choque', 'ic'), ('valvopatia_grave_sintomatica', 'valvopatia'),
                                      ('hap_sintomatica', 'hipertensao_pulmonar'), ('fa_alta_resposta', 'fa')):
            if instavel in self.inst:
                cond.add(antecedente)
        self.cond, self.meds = cond, meds
        self.pas, self.pad = c.get('pas'), c.get('pad')
        self.spo2, self.dur, self.infec = c.get('spo2'), c.get('duracao'), bool(c.get('infeccao_respiratoria'))
        self.asa, self.peso, self.cfs = c.get('asa'), c.get('peso'), c.get('cfs')
        self.escadas = c.get('escadas')
        self.dasi_itens = c.get('dasi') or []
        self.dasi_resp = bool(c.get('dasi_respondido'))
        self.sb = set(c.get('stop_bang', []))
        self.stent = c.get('stent') if 'stent' in cond else None
        # Exames anteriores: o mais recente de cada título; resultados preenchem creatinina e hemoglobina
        self.feitos = {}
        cr, hb = c.get('creatinina'), c.get('hemoglobina')
        cr_prev = hb_prev = self.hba1c = None
        for ex in sorted(c.get('anteriores', []), key=lambda e: e['data']):
            self.feitos[ex['exame']] = _dias(ex['data'])
            res = ex.get('resultados') or {}
            if 'creatinina' in res:
                cr_prev = float(res['creatinina'].replace(',', '.'))
            if 'hemoglobina' in res:
                hb_prev = float(res['hemoglobina'].replace(',', '.'))
            if 'hba1c' in res:
                self.hba1c = float(res['hba1c'].replace(',', '.'))
        self.cr = cr if cr is not None else cr_prev
        self.hb = hb if hb is not None else hb_prev

    # ── atalhos clínicos
    @property
    def dcv(self):
        return bool(self.cond & DCV)

    @property
    def cir_ia(self):
        return self.risco in (M, A)

    @property
    def aha_elev(self):
        # AHA 2026 Tabela 2: "Elevated risk ... encompasses patients at intermediate or high surgical risk".
        # Recomendações de exame: "low-risk procedures" (catarata, dentária, endoscopia, pele) não pedem exames.
        return self.cir_ia

    @property
    def eletiva(self):
        return self.urg in ('eletiva', 'tempo_sensivel')

    @property
    def pa_descontrolada(self):
        return (self.pas or 0) >= 180 or (self.pad or 0) >= 110

    # ── escores
    def rcri(self):
        # Lee/SBC Tabela 4 (nota): IAM, prova funcional positiva, ANGINA, nitrato ou onda Q; revascularização isolada
        # não conta
        itens = [bool(self.cond & {'dac', 'iam_previo'}) or 'angina' in self.sint,
                 'ic' in self.cond or 'sinais_ic' in self.sint,          # Lee: estertores/B3 contam como IC
                 'avc_ait' in self.cond,
                 'diabetes_insulina' in self.cond,
                 self.cr is not None and self.cr >= 2.0,          # AHA Tabela 4 (≥ 2,0)
                 self.rcri_cir]
        pts = sum(itens)
        classe = ('I', 'II', 'III', 'IV')[min(pts, 3)]
        nivel = B if pts <= 1 else M if pts == 2 else A                  # SBC 2024 (semiquantitativa)
        return pts, classe, nivel

    def aub(self):
        hist = bool(self.cond & {'iam_previo', 'stent', 'revascularizacao_cirurgica', 'ic', 'fa', 'valvopatia',
                                 'protese_mecanica'}) or 'sinais_ic' in self.sint
        # Dakik 2020: inclui cirurgia cardíaca; sinais de IC ao exame = IC presente
        itens = [hist, bool(self.sint & {'angina', 'dispneia', 'dispneia_nova'}), self.idade >= 75,
                 self.hb is not None and self.hb < 12, self.vascular, self.urg == 'emergencia']
        pts = sum(itens)
        return pts, (B if pts <= 1 else M if pts <= 3 else A)

    def vsg(self):
        if not self.vascular:
            return None
        pts = 4 if self.idade >= 80 else 3 if self.idade >= 70 else 2 if self.idade >= 60 else 0
        pts += 2 * bool(self.cond & {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica'})
        pts += 2 * ('ic' in self.cond) + 2 * ('dpoc' in self.cond) + 2 * ((self.cr or 0) > 1.8)
        pts += ('tabagismo' in self.cond) + ('diabetes_insulina' in self.cond) + bool(self.meds & BETABLOQ)
        pts -= bool(self.cond & {'stent', 'revascularizacao_cirurgica'})
        return pts, (B if pts <= 4 else M if pts <= 6 else A)

    def pac_ia(self):
        v = self.vsg()
        return self.rcri()[0] >= 2 or self.aub()[0] >= 2 or (v is not None and v[0] >= 5)

    def faltam(self):
        """Dado ausente que pode levar o escore ao risco elevado: não se assume normal (auditoria PREOP-04)."""
        f, v = set(), self.vsg()
        if self.cr is None and (self.rcri()[0] == 1 or (v is not None and 3 <= v[0] <= 4)):
            f.add('creatinina')
        if self.hb is None and self.aub()[0] == 1:
            f.add('hemoglobina')
        return f

    def nivel_algoritmo(self):
        """Nível mais alto entre os escores (para a UTI, SBC Quadro 30)."""
        ordem = {B: 0, M: 1, A: 2}
        niveis = [self.rcri()[2], self.aub()[1]] + ([self.vsg()[1]] if self.vsg() else [])
        return max(niveis, key=ordem.get)

    def dasi(self):
        if not self.dasi_itens and not self.dasi_resp:
            return None
        return round(sum(DASI_PESOS[i] for i in self.dasi_itens), 2)

    def capacidade(self):
        d = self.dasi()
        if d is None and self.escadas in (None, 'nao_sabe'):
            return 'desconhecida'
        if (d is not None and d <= 34) or self.escadas == 'nao':
            return 'baixa'
        return 'boa'

    def ariscat(self):
        pts = 16 if self.idade > 80 else 3 if self.idade > 50 else 0
        if self.spo2 is not None:
            pts += 24 if self.spo2 <= 90 else 8 if self.spo2 <= 95 else 0
        pts += 17 * self.infec
        pts += 11 * (self.hb is not None and self.hb <= 10)
        pts += {PER: 0, ABD: 15, TOR: 24}[self.incisao]
        pts += {None: 0, 'menos_2h': 0, '2_3h': 16, 'mais_3h': 23}[self.dur]
        pts += 8 * (self.urg == 'emergencia')
        return pts, (B if pts < 26 else M if pts < 45 else A)

    def stop_bang(self):
        stop = len(self.sb & {'ronco', 'cansaco', 'apneia_observada'}) + ('hipertensao' in self.cond)
        pts = stop + len(self.sb & {'imc_35', 'pescoco_40'}) + (self.idade > 50) + (self.sexo == 'masculino')
        alto = pts >= 5 or (stop >= 2 and (self.sexo == 'masculino' or bool(self.sb & {'imc_35', 'pescoco_40'})))
        return pts, (A if alto else M if pts >= 3 else B)

    def clcr(self):
        if not self.cr or not self.peso:
            return None
        v = (140 - self.idade) * self.peso / (72 * self.cr)
        return round(v * (0.85 if self.sexo == 'feminino' else 1), 1)

    # ── fluxo de indicação (AHA 2026 Figura 1; SBC 2024 seção 2.1 e Figura Central)
    def saudavel(self):
        """AHA Figura 1, primeira pergunta: sem fator de risco (nota *), doença ou sintoma cardiovascular → opera.
        O módulo só libera aqui se o escore também não estiver elevado e não houver doença renal (item do RCRI)."""
        fator = bool(self.cond & {'hipertensao', 'tabagismo', 'dislipidemia', 'diabetes', 'obesidade',
                                  'historia_familiar_dac'}) \
            or (self.sexo == 'feminino' and self.idade > 65) or (self.sexo == 'masculino' and self.idade > 55)
        return not (fator or self.dcv or self.sint or self.inst or self.pa_descontrolada or self.pac_ia()
                    or 'doenca_renal' in self.cond)

    def modificadores(self):
        """AHA Figura 1: valvopatia grave, hipertensão pulmonar grave, cardiopatia congênita de risco elevado, stent
        coronário ou revascularização cirúrgica, AVC recente, dispositivo implantado, fragilidade."""
        return bool(self.cond & {'valvopatia', 'hipertensao_pulmonar', 'cardiopatia_congenita', 'stent',
                                 'revascularizacao_cirurgica', 'avc_ait_recente', 'marcapasso_cdi'}) \
            or (self.cfs is not None and 5 <= self.cfs <= 8)

    def liberado(self):
        """O fluxo libera sem exames cardíacos: sem fatores, cirurgia de baixo risco ou risco calculado baixo sem
        modificador (inclusive quando falta dado e a boa capacidade funcional libera). Quem passa pelo risco elevado
        ou por um modificador e é liberado pela capacidade não entra."""
        if self.tipo() != 'nao_indicada':
            return False
        if self.saudavel() or self.risco == B:
            return True
        return not self.pac_ia() and not self.modificadores()

    def tipo(self):
        if self.urg == 'emergencia':
            return 'emergencia'
        if self.eletiva and (self.inst or self.pa_descontrolada):    # SBC Tabela 2 inclui PA > 180 × 110
            return 'adiar'
        if self.urg == 'urgencia' and (self.inst or self.pa_descontrolada):
            return 'indicada'         # urgência: estabilizar dentro da janela, sem adiar (AHA Tabela 2; SBC 2.1.2)
        if self.sint & {'dispneia_nova', 'sinais_ic', 'sopro'}:
            # AHA função do VE rec. 1 (1 B-NR) e valvas (1 C-EO): avaliar VE/valva antes da cirurgia, qualquer risco
            return 'indicada'
        if self.saudavel() or self.risco == B:
            return 'nao_indicada'
        if not self.pac_ia() and not self.modificadores():
            # Sem o dado, o risco não é "baixo": com boa capacidade libera de qualquer jeito; sem ela, falta o exame.
            return 'incompleto' if self.faltam() and self.capacidade() != 'boa' else 'nao_indicada'
        # AHA: boa capacidade dispensa prova funcional (recomendações de estresse e CCTA, 3: sem benefício). Sintoma
        # novo é avaliado à parte (eco classe 1); a conclusão não pode negar esse exame (checado abaixo).
        if self.capacidade() == 'boa':
            return 'nao_indicada'
        return 'indicada'


def _caso(id_, idade, sexo, cirurgia, **kw):
    kw.update(id=id_, idade=idade, sexo=sexo, cirurgia=cirurgia)
    kw.setdefault('urgencia', 'eletiva')
    return kw


def _ecg(dias):
    return {'exame': 'Eletrocardiograma de repouso', 'data': dias}


def _eco(dias):
    return {'exame': 'Ecocardiograma transtorácico', 'data': dias}


def _hba1c(dias):
    return {'exame': 'Hemoglobina glicada (HbA1c), soro', 'data': dias}


LAB_OK = dict(creatinina=0.9, hemoglobina=13.8, spo2=98, duracao='menos_2h', peso=72)

# ════════════════════════════════════════════════════════════════════════════
# CASOS (pacientes fictícios)
# ════════════════════════════════════════════════════════════════════════════
CASOS = [
    # A. Jovens sem comorbidade em cirurgia de baixo risco
    _caso('a01_f22_catarata_jovem_saudavel', 22, 'feminino', 'catarata', asa=1, escadas='sim', **LAB_OK),
    _caso('a02_m19_odontologica', 19, 'masculino', 'odontologica', asa=1, **LAB_OK),
    _caso('a03_f30_endoscopia', 30, 'feminino', 'endoscopia', asa=1, **LAB_OK),
    _caso('a04_m25_pele', 25, 'masculino', 'pele', asa=1, **LAB_OK),
    _caso('a05_f35_mama', 35, 'feminino', 'mama', asa=1, **LAB_OK),
    _caso('a06_m38_hernia', 38, 'masculino', 'hernia', asa=1, **LAB_OK),
    _caso('a07_f27_artroscopia', 27, 'feminino', 'ortopedica_menor', asa=1, **LAB_OK),
    _caso('a08_m33_plastica', 33, 'masculino', 'plastica', asa=1, **LAB_OK),
    _caso('a09_f40_ginecologica_menor', 40, 'feminino', 'ginecologica_menor', asa=1, **LAB_OK),
    _caso('a10_m18_tireoide', 18, 'masculino', 'tireoide', asa=1, **LAB_OK),
    _caso('a11_m36_rtu_bexiga', 36, 'masculino', 'rtu', asa=1, **LAB_OK),
    _caso('a12_f29_vats_2a3h_ariscat_intermediario', 29, 'feminino', 'vats_menor', asa=1,
          **dict(LAB_OK, duracao='2_3h')),
    _caso('a13_m24_catarata_dasi_completo', 24, 'masculino', 'catarata', escadas='sim', dasi=DASI_TUDO, **LAB_OK),
    # B. Mais velhos sem comorbidade em cirurgia de baixo risco
    _caso('b01_f55_catarata', 55, 'feminino', 'catarata', asa=1, **LAB_OK),
    _caso('b02_m68_endoscopia', 68, 'masculino', 'endoscopia', asa=2, **LAB_OK),
    _caso('b03_f82_catarata_hb125', 82, 'feminino', 'catarata', asa=2, **dict(LAB_OK, hemoglobina=12.5)),
    _caso('b04_m95_pele_spo2_94', 95, 'masculino', 'pele', asa=2, **dict(LAB_OK, spo2=94)),
    _caso('b05_f47_mama', 47, 'feminino', 'mama', asa=1, **LAB_OK),
    _caso('b06_m75_odontologica_anemia_aub2', 75, 'masculino', 'odontologica', asa=2, **dict(LAB_OK, hemoglobina=11)),
    _caso('b07_f88_catarata_spo2_90', 88, 'feminino', 'catarata', asa=2, **dict(LAB_OK, spo2=90)),
    # C. Baixo risco com comorbidade não cardíaca
    _caso('c01_m45_catarata_diabetes', 45, 'masculino', 'catarata', condicoes=['diabetes'], asa=2, **LAB_OK),
    _caso('c02_f52_catarata_has', 52, 'feminino', 'catarata', condicoes=['hipertensao'], asa=2, **LAB_OK),
    _caso('c03_m60_endoscopia_dpoc_fumante', 60, 'masculino', 'endoscopia', condicoes=['dpoc', 'tabagismo'], asa=2,
          **dict(LAB_OK, spo2=94)),
    _caso('c04_f39_pele_obesidade', 39, 'feminino', 'pele', condicoes=['obesidade'], asa=2, **LAB_OK),
    _caso('c05_m50_hernia_drc_asa3', 50, 'masculino', 'hernia', condicoes=['doenca_renal'], asa=3,
          **dict(LAB_OK, creatinina=1.8)),
    _caso('c06_f63_hernia_hepatopatia_asa3', 63, 'feminino', 'hernia', condicoes=['hepatopatia'], asa=3, **LAB_OK),
    _caso('c07_m70_catarata_fa_varfarina', 70, 'masculino', 'catarata', condicoes=['fa'], medicacoes=['varfarina'],
          asa=2, **LAB_OK),
    _caso('c08_f58_endoscopia_insulina', 58, 'feminino', 'endoscopia', medicacoes=['insulina_nph'], asa=2, **LAB_OK),
    # D. Baixo risco com doença cardiovascular conhecida
    _caso('d01_m72_catarata_iam_ic_rcri2', 72, 'masculino', 'catarata', condicoes=['iam_previo', 'ic'], asa=3,
          **LAB_OK),
    _caso('d02_f66_endoscopia_fa', 66, 'feminino', 'endoscopia', condicoes=['fa'], asa=2, **LAB_OK),
    _caso('d03_m58_pele_marcapasso', 58, 'masculino', 'pele', condicoes=['marcapasso_cdi'], asa=2, **LAB_OK),
    _caso('d04_m80_odontologica_avc_antigo', 80, 'masculino', 'odontologica', condicoes=['avc_ait'], asa=2, **LAB_OK),
    # E. Baixo risco com sintomas
    _caso('e01_f42_endoscopia_dispneia_nova', 42, 'feminino', 'endoscopia', sintomas=['dispneia_nova'], asa=2,
          **LAB_OK),
    _caso('e02_m30_odontologica_sopro', 30, 'masculino', 'odontologica', sintomas=['sopro'], asa=1, **LAB_OK),
    _caso('e03_f26_pele_sincope', 26, 'feminino', 'pele', sintomas=['sincope'], asa=1, **LAB_OK),
    _caso('e04_m61_hernia_palpitacoes', 61, 'masculino', 'hernia', sintomas=['palpitacoes'], asa=2, **LAB_OK),
    _caso('e05_f70_catarata_sinais_ic', 70, 'feminino', 'catarata', sintomas=['sinais_ic'], asa=2, **LAB_OK),
    # F. Emergência
    _caso('f01_m80_perfuracao_emergencia_sem_dcv', 80, 'masculino', 'perfuracao_intestinal', urgencia='emergencia',
          asa=4, **dict(LAB_OK, hemoglobina=9.5, spo2=93, duracao='mais_3h')),
    _caso('f02_f45_colecistectomia_emergencia', 45, 'feminino', 'colecistectomia', urgencia='emergencia', **LAB_OK),
    _caso('f03_m67_aaa_roto_dac', 67, 'masculino', 'aorta_aberta', urgencia='emergencia',
          condicoes=['dac', 'hipertensao', 'tabagismo'], **dict(LAB_OK, creatinina=1.5, hemoglobina=11,
                                                                duracao='mais_3h')),
    _caso('f04_m55_isquemia_aguda_mmii_fa', 55, 'masculino', 'revascularizacao_mmii', urgencia='emergencia',
          condicoes=['fa'], **dict(LAB_OK, duracao='2_3h')),
    _caso('f05_m19_trauma_perfuracao', 19, 'masculino', 'perfuracao_intestinal', urgencia='emergencia',
          **dict(LAB_OK, duracao='2_3h')),
    # G. Urgência
    _caso('g01_f88_fratura_quadril_urgencia', 88, 'feminino', 'quadril', urgencia='urgencia',
          condicoes=['hipertensao'], **dict(LAB_OK, hemoglobina=10.5, creatinina=1.3, peso=55)),
    _caso('g02_m70_colectomia_urgencia_pa190', 70, 'masculino', 'colectomia', urgencia='urgencia',
          condicoes=['iam_previo', 'diabetes'], pas=190, pad=100, escadas='nao', **LAB_OK),
    _caso('g03_f60_urgencia_com_sca', 60, 'feminino', 'colecistectomia', urgencia='urgencia', instaveis=['sca'],
          **LAB_OK),
    _caso('g04_m75_urgencia_ic_descompensada', 75, 'masculino', 'perfuracao_intestinal', urgencia='urgencia',
          instaveis=['ic_descompensada'], condicoes=['ic'], **LAB_OK),
    _caso('g05_m50_urgencia_stent_3sem', 50, 'masculino', 'colecistectomia', urgencia='urgencia',
          condicoes=['stent', 'iam_previo'], stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-10-26'},
          **LAB_OK),
    # H. Condições instáveis em cirurgia eletiva (SBC Tabela 2)
    _caso('h01_m64_sca', 64, 'masculino', 'colectomia', instaveis=['sca'], condicoes=['dac'], **LAB_OK),
    _caso('h02_f78_ic_descompensada', 78, 'feminino', 'quadril', instaveis=['ic_descompensada'], condicoes=['ic'],
          **LAB_OK),
    _caso('h03_m59_angina_ccs3_hernia', 59, 'masculino', 'hernia', instaveis=['angina_grave'], condicoes=['dac'],
          **LAB_OK),
    _caso('h04_f81_ea_grave_sintomatica', 81, 'feminino', 'quadril', instaveis=['valvopatia_grave_sintomatica'],
          condicoes=['valvopatia'], **LAB_OK),
    _caso('h05_m70_bavt', 70, 'masculino', 'coluna', instaveis=['arritmia_grave'], **LAB_OK),
    _caso('h06_f68_fa_alta_resposta', 68, 'feminino', 'colecistectomia', instaveis=['fa_alta_resposta'],
          condicoes=['fa'], **LAB_OK),
    _caso('h07_f50_hap_sintomatica', 50, 'feminino', 'ginecologica_maior', instaveis=['hap_sintomatica'], **LAB_OK),
    _caso('h08_m72_aorta_toracica_instavel', 72, 'masculino', 'cabeca_pescoco', instaveis=['aorta_instavel'],
          **LAB_OK),
    _caso('h09_m83_eap_tempo_sensivel', 83, 'masculino', 'colectomia', urgencia='tempo_sensivel',
          instaveis=['edema_choque'], condicoes=['ic'], **LAB_OK),
    _caso('h10_m77_sca_e_ic_descompensada', 77, 'masculino', 'quadril', instaveis=['sca', 'ic_descompensada'],
          condicoes=['dac', 'ic'], **LAB_OK),
    # I. Pressão arterial
    _caso('i01_m58_hernia_pa185x100', 58, 'masculino', 'hernia', pas=185, pad=100, condicoes=['hipertensao'],
          **LAB_OK),
    _caso('i02_f66_colectomia_pa170x112', 66, 'feminino', 'colectomia', pas=170, pad=112,
          condicoes=['hipertensao', 'dac'], escadas='sim', **LAB_OK),
    _caso('i03_m49_quadril_pa179x109', 49, 'masculino', 'quadril', pas=179, pad=109, condicoes=['hipertensao'],
          **LAB_OK),
    _caso('i04_f72_catarata_pa200x120', 72, 'feminino', 'catarata', pas=200, pad=120, condicoes=['hipertensao'],
          **LAB_OK),
    _caso('i05_m60_colectomia_pa182_tempo_sensivel', 60, 'masculino', 'colectomia', urgencia='tempo_sensivel',
          pas=182, pad=90, condicoes=['hipertensao'], **LAB_OK),
    # J. AVC/AIT recente
    _caso('j01_m69_quadril_avc_recente', 69, 'masculino', 'quadril', condicoes=['avc_ait_recente'], escadas='sim',
          **LAB_OK),
    _caso('j02_f74_endarterectomia_sintomatica_ait_recente', 74, 'feminino', 'endarterectomia_sintomatica',
          urgencia='tempo_sensivel', condicoes=['avc_ait_recente', 'hipertensao'], escadas='sim', **LAB_OK),
    # K. Angioplastia: tempo até a cirurgia
    _caso('k01_m62_des_sca_2sem', 62, 'masculino', 'colectomia', condicoes=['stent', 'iam_previo'],
          stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-11-02'}, escadas='sim', **LAB_OK),
    _caso('k02_m62_des_sca_4m', 62, 'masculino', 'colectomia', condicoes=['stent', 'iam_previo'],
          stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-07-10'}, escadas='sim', **LAB_OK),
    _caso('k03_f67_des_sca_8m', 67, 'feminino', 'quadril', condicoes=['stent', 'iam_previo'],
          stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2026-03-12'}, escadas='sim', **LAB_OK),
    _caso('k04_m71_des_sca_14m', 71, 'masculino', 'quadril', condicoes=['stent', 'iam_previo'],
          stent={'tipo': 'farmacologico', 'indicacao': 'sca', 'data': '2025-09-10'}, escadas='sim', **LAB_OK),
    _caso('k05_m59_des_cronica_2m', 59, 'masculino', 'coluna', condicoes=['stent', 'dac'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2026-09-10'}, escadas='sim', **LAB_OK),
    _caso('k06_f63_des_cronica_4m', 63, 'feminino', 'coluna', condicoes=['stent', 'dac'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2026-07-10'}, escadas='sim', **LAB_OK),
    _caso('k07_m66_des_cronica_8m', 66, 'masculino', 'coluna', condicoes=['stent', 'dac'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2026-03-10'}, escadas='sim', **LAB_OK),
    _caso('k08_m57_bms_3sem', 57, 'masculino', 'quadril', condicoes=['stent', 'dac'],
          stent={'tipo': 'convencional', 'indicacao': 'dac_cronica', 'data': '2026-10-26'}, escadas='sim', **LAB_OK),
    _caso('k09_f61_bms_sca_3m', 61, 'feminino', 'quadril', condicoes=['stent', 'iam_previo'],
          stent={'tipo': 'convencional', 'indicacao': 'sca', 'data': '2026-08-10'}, escadas='sim', **LAB_OK),
    _caso('k10_m64_balao_7d', 64, 'masculino', 'hernia', condicoes=['stent', 'dac'],
          stent={'tipo': 'balao', 'indicacao': 'dac_cronica', 'data': '2026-11-09'}, **LAB_OK),
    _caso('k11_m64_balao_27d', 64, 'masculino', 'hernia', condicoes=['stent', 'dac'],
          stent={'tipo': 'balao', 'indicacao': 'dac_cronica', 'data': '2026-10-20'}, **LAB_OK),
    _caso('k12_f70_stent_sem_data', 70, 'feminino', 'quadril', condicoes=['stent', 'dac'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica'}, escadas='sim', **LAB_OK),
    _caso('k13_m68_des_cronica_4m_tempo_sensivel', 68, 'masculino', 'colectomia', urgencia='tempo_sensivel',
          condicoes=['stent', 'dac'], stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica',
                                              'data': '2026-07-10'}, escadas='sim', **LAB_OK),
    _caso('k14_m66_so_stent_sem_criterio_de_lee', 66, 'masculino', 'colectomia', condicoes=['stent'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2024-10-10'}, escadas='nao', **LAB_OK),
    # L. Cirurgia de risco intermediário/alto com escore baixo
    _caso('l01_m30_colectomia_saudavel', 30, 'masculino', 'colectomia', asa=1, **LAB_OK),
    _caso('l02_f44_artroplastia_quadril_saudavel', 44, 'feminino', 'quadril', asa=1, **LAB_OK),
    _caso('l03_m52_coluna_has', 52, 'masculino', 'coluna', condicoes=['hipertensao'], escadas='sim', asa=2, **LAB_OK),
    _caso('l04_f60_cabeca_pescoco_fumante', 60, 'feminino', 'cabeca_pescoco', condicoes=['tabagismo'], asa=2,
          **dict(LAB_OK, spo2=95, duracao='mais_3h')),
    _caso('l05_m40_transplante_renal', 40, 'masculino', 'transplante_renal', condicoes=['doenca_renal'], asa=3,
          **dict(LAB_OK, creatinina=6.5, hemoglobina=10.5, duracao='2_3h')),
    _caso('l06_f35_pancreas_saudavel', 35, 'feminino', 'pancreas', asa=2, **dict(LAB_OK, duracao='mais_3h')),
    _caso('l07_m28_pneumectomia_saudavel', 28, 'masculino', 'pneumectomia', asa=2,
          **dict(LAB_OK, spo2=97, duracao='mais_3h')),
    _caso('l08_m68_colectomia_sinais_ic_sem_historia', 68, 'masculino', 'colectomia', sintomas=['sinais_ic'], asa=3,
          **LAB_OK),
    # M. Escore elevado com boa capacidade funcional
    _caso('m01_m64_colectomia_iam_boa_capacidade', 64, 'masculino', 'colectomia', condicoes=['iam_previo'],
          escadas='sim', dasi=DASI_TUDO, asa=3, **LAB_OK),
    _caso('m02_f71_quadril_ic_insulina_boa', 71, 'feminino', 'quadril', condicoes=['ic', 'diabetes_insulina'],
          escadas='sim', asa=3, **LAB_OK),
    _caso('m03_m55_esofagectomia_dac_dasi3475', 55, 'masculino', 'esofagectomia', condicoes=['dac'], dasi=DASI_3475,
          asa=3, **dict(LAB_OK, duracao='mais_3h')),
    # N. Escore elevado com capacidade baixa
    _caso('n01_m72_colectomia_multiplo_dasi_baixo', 72, 'masculino', 'colectomia', peso=78,
          condicoes=['iam_previo', 'diabetes_insulina', 'hipertensao'], escadas='nao', dasi=DASI_POUCO, asa=3,
          creatinina=1.6, hemoglobina=11.5, spo2=97, duracao='2_3h'),
    _caso('n02_f69_hepatectomia_icfer_avc', 69, 'feminino', 'figado', condicoes=['ic_fe_reduzida', 'avc_ait'],
          dasi=DASI_POUCO, asa=3, peso=60, creatinina=1.4, hemoglobina=11.5, spo2=96, duracao='mais_3h'),
    _caso('n03_m80_pancreas_rcri4_aub4', 80, 'masculino', 'pancreas', condicoes=['iam_previo', 'diabetes_insulina'],
          sintomas=['dispneia'], escadas='nao', asa=3, peso=70, creatinina=2.3, hemoglobina=10, spo2=93,
          duracao='mais_3h'),
    _caso('n04_m66_quadril_dasi_34_limite', 66, 'masculino', 'quadril', condicoes=['iam_previo', 'ic'], dasi=DASI_34,
          asa=3, **LAB_OK),
    _caso('n05_f67_quadril_dasi_3475_boa', 67, 'feminino', 'quadril', condicoes=['iam_previo', 'ic'], dasi=DASI_3475,
          asa=3, **LAB_OK),
    # O. Capacidade desconhecida
    _caso('o01_m78_colectomia_iam_diabetes_desconhecida', 78, 'masculino', 'colectomia',
          condicoes=['iam_previo', 'diabetes'], asa=3, **LAB_OK),
    _caso('o02_f76_histerectomia_ic_nao_sabe', 76, 'feminino', 'ginecologica_maior', condicoes=['ic'],
          escadas='nao_sabe', asa=3, **LAB_OK),
    # P. Escadas × DASI
    _caso('p01_m70_colecistectomia_escadas_sim_dasi10', 70, 'masculino', 'colecistectomia', condicoes=['iam_previo'],
          escadas='sim', dasi=['cuidar_de_si', 'andar_em_casa', 'subir_lance'], asa=3, **LAB_OK),
    _caso('p02_f68_colectomia_escadas_nao_dasi_alto', 68, 'feminino', 'colectomia', condicoes=['ic'],
          escadas='nao', dasi=DASI_TUDO, asa=3, **LAB_OK),
    _caso('p03_m73_colectomia_dasi_respondido_zero', 73, 'masculino', 'colectomia', condicoes=['iam_previo'],
          dasi_respondido=True, asa=3, **LAB_OK),
    # Q. Cirurgia vascular (VSG-CRI)
    _caso('q01_m82_aorta_vsg14', 82, 'masculino', 'aorta_aberta', peso=80,
          condicoes=['dac', 'ic', 'dpoc', 'tabagismo', 'diabetes_insulina', 'revascularizacao_cirurgica'],
          medicacoes=['atenolol'], creatinina=2.0, hemoglobina=12.4, spo2=94, duracao='mais_3h', escadas='nao', asa=4),
    _caso('q02_m63_evar_saudavel', 63, 'masculino', 'evar', escadas='sim', asa=2, **LAB_OK),
    _caso('q03_f74_carotida_assintomatica_iam', 74, 'feminino', 'carotida_assintomatica',
          condicoes=['iam_previo', 'tabagismo', 'hipertensao'], escadas='nao', asa=3, **LAB_OK),
    _caso('q04_m61_angioplastia_periferica_vsg6', 61, 'masculino', 'angioplastia_periferica',
          condicoes=['doenca_arterial_periferica', 'diabetes_insulina'], medicacoes=['metoprolol'], dasi=DASI_POUCO,
          asa=3, **dict(LAB_OK, creatinina=1.9)),
    _caso('q05_f79_revasc_mmii_dpoc_ic_vsg7', 79, 'feminino', 'revascularizacao_mmii', condicoes=['dpoc', 'ic'],
          escadas='nao', asa=3, **dict(LAB_OK, creatinina=1.2, spo2=93, duracao='mais_3h')),
    _caso('q06_m58_stent_carotida_sintomatica_fumante', 58, 'masculino', 'stent_carotida_sintomatica',
          condicoes=['tabagismo'], escadas='sim', asa=2, **LAB_OK),
    _caso('q07_m70_endarterectomia_avc_antigo_dac', 70, 'masculino', 'endarterectomia_sintomatica',
          condicoes=['avc_ait', 'tabagismo', 'dac'], escadas='nao', asa=3, **LAB_OK),
    _caso('q08_m71_revasc_mmii_dpoc_vsg5_so', 71, 'masculino', 'revascularizacao_mmii', condicoes=['dpoc'],
          escadas='nao', asa=3, **LAB_OK),
    _caso('q09_m69_revasc_mmii_dpoc_vsg4', 69, 'masculino', 'revascularizacao_mmii', condicoes=['dpoc'],
          escadas='nao', asa=3, **LAB_OK),
    _caso('q10_m66_angioplastia_cr18_limite', 66, 'masculino', 'angioplastia_periferica',
          condicoes=['doenca_arterial_periferica'], escadas='sim', asa=2, **dict(LAB_OK, creatinina=1.8)),
    _caso('q11_f62_evar_dac_vsg4_rcri2', 62, 'feminino', 'evar', condicoes=['dac'], escadas='sim', asa=3, **LAB_OK),
    # R. Idosos com múltiplas doenças, cirurgia de risco alto
    _caso('r01_f85_colectomia_multimorbida', 85, 'feminino', 'colectomia', peso=52,
          condicoes=['iam_previo', 'stent', 'ic', 'fa', 'diabetes_insulina', 'hipertensao', 'doenca_renal'],
          stent={'tipo': 'farmacologico', 'indicacao': 'dac_cronica', 'data': '2023-05-10'},
          medicacoes=['varfarina'], dasi=DASI_POUCO, cfs=6, asa=4, creatinina=2.4, hemoglobina=9.8, spo2=92,
          duracao='mais_3h'),
    _caso('r02_m92_quadril_ic_avc_dpoc_fragil', 92, 'masculino', 'quadril', peso=60,
          condicoes=['ic', 'avc_ait', 'dpoc', 'hipertensao'], escadas='nao', cfs=7, asa=4, creatinina=1.5,
          hemoglobina=11, spo2=91, duracao='2_3h'),
    _caso('r03_f79_esofagectomia_valvopatia_fa_dispneia', 79, 'feminino', 'esofagectomia',
          condicoes=['valvopatia', 'fa'], sintomas=['dispneia_nova'], asa=3, **dict(LAB_OK, hemoglobina=11.8,
                                                                              duracao='mais_3h')),
    _caso('r04_m87_cistectomia_protese_mitral_icfer', 87, 'masculino', 'cistectomia',
          condicoes=['ic_fe_reduzida', 'protese_mecanica_mitral', 'hipertensao_pulmonar'], medicacoes=['varfarina'],
          escadas='nao', asa=4, **dict(LAB_OK, duracao='mais_3h')),
    _caso('r05_m76_pneumectomia_dpoc_fumante_iam', 76, 'masculino', 'pneumectomia',
          condicoes=['dpoc', 'tabagismo', 'iam_previo'], escadas='nao', asa=3, peso=68, creatinina=1.1,
          hemoglobina=13, spo2=92, duracao='mais_3h', infeccao_respiratoria=True),
    # S. Exames anteriores
    _caso('s01_m70_quadril_iam_ecg_6m', 70, 'masculino', 'quadril', condicoes=['iam_previo'], escadas='sim', asa=2,
          anteriores=[_ecg('2026-05-16')], **LAB_OK),
    _caso('s02_f66_colecistectomia_has_ecg_15m', 66, 'feminino', 'colecistectomia', condicoes=['hipertensao'],
          escadas='sim', asa=2, anteriores=[_ecg('2025-08-01')], **LAB_OK),
    _caso('s03_f73_quadril_valvopatia_eco_3m', 73, 'feminino', 'quadril', condicoes=['valvopatia'], escadas='sim',
          asa=2, anteriores=[_eco('2026-08-10')], **LAB_OK),
    _caso('s04_m60_colectomia_diabetes_hba1c_57d', 60, 'masculino', 'colectomia', condicoes=['diabetes'], asa=2,
          anteriores=[_hba1c('2026-09-20')], **LAB_OK),
    _caso('s05_f58_hernia_diabetes_hba1c_5m', 58, 'feminino', 'hernia', condicoes=['diabetes'], asa=2,
          anteriores=[_hba1c('2026-06-01')], **LAB_OK),
    _caso('s06_m74_colectomia_dac_lab_anterior', 74, 'masculino', 'colectomia', condicoes=['dac'], asa=3, peso=70,
          spo2=97, duracao='2_3h',
          anteriores=[{'exame': 'Creatinina, soro', 'data': '2026-10-15', 'resultados': {'creatinina': '2,3'}},
                      {'exame': 'Hemograma completo com plaquetas', 'data': '2026-10-15',
                       'resultados': {'hemoglobina': '10,5'}}]),
    _caso('s07_f67_colectomia_ic_eco_9m', 67, 'feminino', 'colectomia', condicoes=['ic'], escadas='sim', asa=3,
          anteriores=[_eco('2026-02-10')], **LAB_OK),
    _caso('s08_m62_quadril_ic_sem_eco', 62, 'masculino', 'quadril', condicoes=['ic'], escadas='sim', asa=3, **LAB_OK),
    _caso('s09_f69_colectomia_valvopatia_sem_eco', 69, 'feminino', 'colectomia', condicoes=['valvopatia'],
          escadas='sim', asa=3, **LAB_OK),
    # T. Fragilidade
    _caso('t01_f70_quadril_cfs3', 70, 'feminino', 'quadril', cfs=3, escadas='sim', asa=2, **LAB_OK),
    _caso('t02_m78_colectomia_cfs4', 78, 'masculino', 'colectomia', cfs=4, escadas='sim', asa=2, **LAB_OK),
    _caso('t03_f83_coluna_cfs5', 83, 'feminino', 'coluna', cfs=5, escadas='nao', asa=3, **LAB_OK),
    _caso('t04_m68_quadril_sem_cfs', 68, 'masculino', 'quadril', escadas='sim', asa=2, **LAB_OK),
    _caso('t05_m64_quadril_sem_cfs', 64, 'masculino', 'quadril', escadas='sim', asa=2, **LAB_OK),
    # U. SpO₂, hemoglobina, duração e infecção (ARISCAT)
    _caso('u01_m55_colecistectomia_infeccao_hb10', 55, 'masculino', 'colecistectomia', infeccao_respiratoria=True,
          asa=2, **dict(LAB_OK, spo2=96, hemoglobina=9.8, duracao='2_3h')),
    _caso('u02_f50_colecistectomia_spo2_91', 50, 'feminino', 'colecistectomia', asa=2,
          **dict(LAB_OK, spo2=91, hemoglobina=12)),
    _caso('u03_f51_colecistectomia_ariscat_26', 51, 'feminino', 'colecistectomia', asa=2, **dict(LAB_OK, spo2=95)),
    _caso('u04_m81_hernia_2a3h', 81, 'masculino', 'hernia', asa=2, **dict(LAB_OK, duracao='2_3h')),
    _caso('u05_m80_hernia_2a3h', 80, 'masculino', 'hernia', asa=2, **dict(LAB_OK, duracao='2_3h')),
    _caso('u06_f62_intratoracica_spo2_90', 62, 'feminino', 'intratoracica', asa=3,
          **dict(LAB_OK, spo2=90, duracao='mais_3h')),
    _caso('u07_m45_colectomia_sem_spo2_sem_hb', 45, 'masculino', 'colectomia', asa=1, creatinina=0.9, peso=80),
    # V. STOP-Bang
    _caso('v01_m45_hernia_ronco_cansaco', 45, 'masculino', 'hernia', stop_bang=['ronco', 'cansaco'], asa=1, **LAB_OK),
    _caso('v02_f45_hernia_ronco_cansaco', 45, 'feminino', 'hernia', stop_bang=['ronco', 'cansaco'], asa=1, **LAB_OK),
    _caso('v03_f55_hernia_stopbang5', 55, 'feminino', 'hernia', condicoes=['hipertensao'],
          stop_bang=['ronco', 'cansaco', 'imc_35'], asa=2, **LAB_OK),
    _caso('v04_f52_hernia_stopbang3_intermediario', 52, 'feminino', 'hernia', condicoes=['hipertensao'],
          stop_bang=['ronco'], asa=2, **LAB_OK),
    _caso('v05_m60_catarata_aos_provavel', 60, 'masculino', 'catarata',
          stop_bang=['ronco', 'cansaco', 'apneia_observada'], asa=1, **LAB_OK),
    # W. Situações especiais
    _caso('w01_f58_transplante_hepatico', 58, 'feminino', TX_HEP, condicoes=['hepatopatia'], asa=4,
          **dict(LAB_OK, hemoglobina=10.8, duracao='mais_3h')),
    _caso('w02_m62_quadril_protese_aortica_varfarina', 62, 'masculino', 'quadril', condicoes=['protese_mecanica'],
          medicacoes=['varfarina'], escadas='sim', asa=3, **LAB_OK),
    _caso('w03_f48_colecistectomia_hp_estavel', 48, 'feminino', 'colecistectomia', condicoes=['hipertensao_pulmonar'],
          escadas='sim', asa=3, **LAB_OK),
    _caso('w04_m66_quadril_fa_rivaroxabana_sem_cr', 66, 'masculino', 'quadril', condicoes=['fa'],
          medicacoes=['rivaroxabana'], escadas='sim', asa=3, hemoglobina=13.5, spo2=97, duracao='2_3h'),
    _caso('w05_f31_quadril_jovem', 31, 'feminino', 'quadril', asa=1, **LAB_OK),
    _caso('w06_m77_adrenal_has_dac', 77, 'masculino', 'adrenal', condicoes=['hipertensao', 'dac'], escadas='nao',
          asa=3, **dict(LAB_OK, duracao='2_3h')),
    _caso('w07_f84_urologica_maior_aub3', 84, 'feminino', 'urologica_maior', condicoes=['fa'], escadas='nao_sabe',
          asa=3, **dict(LAB_OK, hemoglobina=11.2)),
    _caso('w08_m53_intratoracica_obeso_diabetico', 53, 'masculino', 'intratoracica',
          condicoes=['obesidade', 'diabetes'], escadas='sim', asa=2, **dict(LAB_OK, duracao='2_3h')),
    _caso('w09_f46_tireoide_has_obesa', 46, 'feminino', 'tireoide', condicoes=['hipertensao', 'obesidade'], asa=2,
          **LAB_OK),
    _caso('w10_m90_coluna_robusto', 90, 'masculino', 'coluna', escadas='sim', cfs=3, asa=2, **LAB_OK),
    _caso('w11_f57_colectomia_angina', 57, 'feminino', 'colectomia', sintomas=['angina'], escadas='sim', asa=2,
          **LAB_OK),
    _caso('w12_m75_colectomia_angina_boa', 75, 'masculino', 'colectomia', sintomas=['angina'], escadas='sim', asa=2,
          **LAB_OK),
    _caso('w13_f45_figado_tev_cancer', 45, 'feminino', 'figado', condicoes=['cancer_ativo', 'tev_3_12m'],
          urgencia='tempo_sensivel', asa=2, **dict(LAB_OK, duracao='mais_3h')),
    _caso('w14_m38_ortopedica_menor_tabagista', 38, 'masculino', 'ortopedica_menor', condicoes=['tabagismo'], asa=2,
          **LAB_OK),
    _caso('w15_f93_catarata_robusta', 93, 'feminino', 'catarata', asa=2, **LAB_OK),
    _caso('x01_f64_colectomia_ic_recente_so', 64, 'feminino', 'colectomia', condicoes=['ic_recente'],
          escadas='sim', asa=3, **LAB_OK),
    _caso('x02_m70_quadril_iam_dispneia_nova_boa_capacidade', 70, 'masculino', 'quadril', condicoes=['iam_previo'],
          sintomas=['dispneia_nova'], escadas='sim', asa=3, **LAB_OK),
    _caso('x03_f78_colecistectomia_dispneia_habitual', 78, 'feminino', 'colecistectomia', sintomas=['dispneia'],
          escadas='nao', asa=3, **dict(LAB_OK, hemoglobina=11.4)),
    _caso('y01_m62_colectomia_diabetes_hba1c_91', 62, 'masculino', 'colectomia', condicoes=['diabetes'], asa=2,
          anteriores=[{'exame': 'Hemoglobina glicada (HbA1c), soro', 'data': '2026-10-20',
                       'resultados': {'hba1c': '9,1'}}], **LAB_OK),
    _caso('y02_f50_colecistectomia_dispneia_nova_escore_baixo', 50, 'feminino', 'colecistectomia',
          sintomas=['dispneia_nova'], escadas='sim', asa=2, **LAB_OK),
    _caso('y03_m66_colectomia_iam_ecg_3m_linha_de_base', 66, 'masculino', 'colectomia', condicoes=['iam_previo'],
          escadas='sim', asa=3, anteriores=[_ecg('2026-08-16')], **LAB_OK),
    _caso('y04_f72_quadril_dac_capacidade_desconhecida', 72, 'feminino', 'quadril', condicoes=['dac'], asa=3,
          **LAB_OK),
    # Z. Dados ausentes e fronteira da creatinina (auditoria pós-merge: PREOP-03 e PREOP-04)
    _caso('z01_m60_colectomia_sem_creatinina_escadas_nao', 60, 'masculino', 'colectomia', escadas='nao', asa=2),
    _caso('z02_m60_colectomia_sem_creatinina_escadas_sim', 60, 'masculino', 'colectomia', escadas='sim', asa=2),
    _caso('z03_f78_quadril_sem_hemoglobina', 78, 'feminino', 'quadril', escadas='nao_sabe', asa=2,
          creatinina=0.8, peso=60),
    _caso('z04_m70_colectomia_dac_sem_laboratorio', 70, 'masculino', 'colectomia', condicoes=['dac'], escadas='nao',
          asa=3),
    _caso('z05_m66_hernia_sem_laboratorio', 66, 'masculino', 'hernia', escadas='nao', asa=2),
    _caso('z06_m60_colectomia_creatinina_2_0', 60, 'masculino', 'colectomia', escadas='nao', asa=2,
          **dict(LAB_OK, creatinina=2.0)),
    _caso('z07_m60_colectomia_creatinina_1_99', 60, 'masculino', 'colectomia', escadas='nao', asa=2,
          **dict(LAB_OK, creatinina=1.99)),
    _caso('z08_m72_aorta_vsg3_sem_creatinina', 72, 'masculino', 'evar', escadas='nao', asa=3, hemoglobina=13.5),
    _caso('z09_f60_colectomia_sem_creatinina_dispneia_nova', 60, 'feminino', 'colectomia', sintomas=['dispneia_nova'],
          escadas='nao', asa=2),
    # A linha intraperitoneal da SBC/ESC em três cirurgias (mesmo risco cardíaco; sangramento e duração diferentes)
    _caso('za1_f55_esplenectomia_saudavel', 55, 'feminino', 'esplenectomia', escadas='sim', asa=1,
          sangramento='minimo', **LAB_OK),
    _caso('za2_m58_hernia_hiatal_has_dm', 58, 'masculino', 'hernia_hiatal', condicoes=['hipertensao', 'diabetes'],
          escadas='sim', asa=2, **LAB_OK),
    _caso('y05_m58_perfuracao_emergencia_choque', 58, 'masculino', 'perfuracao_intestinal', urgencia='emergencia',
          instaveis=['edema_choque'], condicoes=['ic'], **dict(LAB_OK, duracao='2_3h')),
    _caso('y06_f45_hernia_urgencia_pa200', 45, 'feminino', 'hernia', urgencia='urgencia', pas=200, pad=115,
          **LAB_OK),
    _caso('y07_m70_quadril_sopro_boa_capacidade', 70, 'masculino', 'quadril', sintomas=['sopro'], escadas='sim',
          asa=2, **LAB_OK),
    _caso('w17_f61_neurocirurgia_has_dasi_baixo', 61, 'feminino', 'neurocirurgia', condicoes=['hipertensao', 'avc_ait'],
          dasi=DASI_POUCO, asa=3, **dict(LAB_OK, duracao='mais_3h')),
]
if 'transplante_pulmonar' in po.CIRURGIAS:
    CASOS.append(_caso('w16_m55_transplante_pulmonar_dpoc', 55, 'masculino', 'transplante_pulmonar',
                       condicoes=['dpoc'], escadas='nao', asa=4, **dict(LAB_OK, spo2=88, duracao='mais_3h')))
assert len({c['id'] for c in CASOS}) == len(CASOS) >= 120

# ════════════════════════════════════════════════════════════════════════════
# Divergências conhecidas (módulo × oráculo). Preenchido depois de rodar contra o código atual.
# ════════════════════════════════════════════════════════════════════════════
_LEE_IC = ('Lee 1999 (doi:10.1161/01.cir.100.10.1043): no RCRI, "insuficiência cardíaca" inclui exame com estertores '
           'bilaterais ou B3; o módulo só conta a história de IC, não os sinais marcados')
_IC_RECENTE = ('"IC recente" marcada sozinha não conta como insuficiência cardíaca no RCRI (Lee 1999) nem no AUB-HAS2 '
               '(Dakik 2020, doi:10.1161/JAHA.119.016228), nem como doença cardiovascular para ECG/BNP/troponina')
_URG_PA = ('Urgência (2–24 h) não se adia por PA: a SBC Tabela 2/Quadro 9 e a AHA (PA rec. 2) tratam de cirurgia '
           'ELETIVA; o módulo conclui "adiar a cirurgia eletiva" numa cirurgia de urgência')
_URG_INST = ('Urgência (AHA Tabela 2: ameaça à vida ou ao membro, 2–24 h; SBC 2.1.2): estabilizar dentro da janela, '
             'não "adiar a cirurgia eletiva"; a SBC Tabela 2 vale para operações eletivas')
_SCA_CATE = ('SCA: cineangiocoronariografia indicada (SBC 2024 Quadro 7, I-A; AHA revascularização rec. 1, 1 C-LD); o '
             'módulo mostra "cateterismo de rotina: não indicado"')
_CAROTIDA = ('Carótida sintomática: o AVC/AIT recente é a indicação, e a revascularização deve ser precoce (AHA/ASA 2021 '
             'prevenção secundária, doi:10.1161/STR.0000000000000375: até 2 semanas; ESVS 2023, '
             'doi:10.1016/j.ejvs.2022.04.011); a regra de adiar 3 meses (AHA 2a) é para outras cirurgias')
_TX_RENAL = ('SBC 2024 Quadro 17 (doi:10.36660/abc.20240590): troponina ultrassensível antes e 24/48 h após o '
             'transplante renal, I-B, independente do escore')
_DISPNEIA = ('SBC 2024 Quadro 4: IC ou "sintomas sugestivos" (dispneia aos esforços) em cirurgia de risco '
             'intermediário/alto sem eco no último ano → ecocardiograma I-B; o III da SBC é só para assintomáticos')
_RES_CIR = ('Resumo curto em cirurgia de risco intermediário/alto: a SBC 2024 Quadro 3 indica ECG (I-C) e o NICE NG45 '
            'exames pelo porte, e o resumo diz que exames cardíacos não mudam a conduta; o resumo foi definido para '
            'cirurgia de baixo risco sem comorbidade (fragilidade, ARISCAT e pós-operatório ficam recolhidos)')
_RES_COMORB = ('Resumo curto com comorbidade (diabetes, HAS, DPOC, obesidade, DRC, hepatopatia, tabagismo): recolhe '
               'recomendações classe I/2a (anti-hipertensivo AHA 1/SBC I; HbA1c AHA 2a; ECG SBC I no diabetes; '
               'cessação do tabagismo; medidas pulmonares ACP)')
_RES_PULM = ('Resumo curto com ARISCAT ≥ 26 (Canet 2010, risco pulmonar intermediário/alto): as medidas de expansão '
             'pulmonar (ACP 2006) ficam recolhidas')
_RES_AOS = ('Resumo curto com STOP-Bang de risco alto (Chung 2016, doi:10.1378/chest.15-0903): o rastreio de AOS (AHA '
            '2a) e as precauções ficam recolhidos')

_VE = ('AHA 2026, função do VE rec. 1 (1 B-NR): dispneia nova, sinais de IC ou suspeita de disfunção nova → avaliar a '
       'função do VE ANTES da cirurgia, em qualquer cirurgia; a conclusão chama o paciente de "estável" e diz "Pode operar"')
_ANGINA = ('SBC 2024 Tabela 4 (nota) e Lee 1999: angina (dor torácica isquêmica atual) é critério de doença coronária no '
           'RCRI; o módulo só conta a angina no AUB-HAS2')

_SINTOMA_NOVO = ('AHA 2026, função do VE rec. 1 (1 B-NR: dispneia nova ou sinais de IC → avaliar o VE antes de QUALQUER '
                 'cirurgia) e valvas (1 C-EO: suspeita de EAo moderada/grave em cirurgia de risco elevado; regurgitação '
                 'antes de eletiva). O módulo só indica avaliação na cirurgia de baixo risco; na intermediária/alta '
                 'conclui "liberar" com o mesmo sintoma')
_SCA_ESTRESSE = ('SCA: estratégia invasiva (SBC Quadro 7, I-A); o IIb do SBC Quadro 6 é para pacientes ASSINTOMÁTICOS, e '
                 'a prova de estresse é contraindicada na angina instável de alto risco/IAM agudo (ACC/AHA 2002, '
                 'doi:10.1161/01.cir.0000034670.06526.15); o módulo sugere cintilografia ao lado do cateterismo')

# Rodada 3: transplante renal, SCA sem prova de estresse e sintoma novo em qualquer cirurgia, corrigidos no motor.
XFAIL = {}

ASPECTOS = ('escores', 'indicacao', 'exames', 'adiar', 'pulmonar', 'pos', 'resumido')

# ════════════════════════════════════════════════════════════════════════════
# Execução e comparação
# ════════════════════════════════════════════════════════════════════════════
_CACHE = {}


def _rodar(c):
    if c['id'] not in _CACHE:
        dados = {k: v for k, v in c.items() if k not in ('id', 'anteriores')}
        p = po.ler(dados, hoje=HOJE)
        if c.get('anteriores'):
            lidos, erros = periodicidade.ler_exames_anteriores(
                [{'exame': e['exame'], 'data': e['data'], 'resultados': e.get('resultados')} for e in c['anteriores']],
                hoje_=HOJE)
            assert not erros, erros
            po.aplicar_exames_anteriores(p, lidos, hoje=HOJE)
        _CACHE[c['id']] = po.avaliar(p)
    return _CACHE[c['id']]


def _escore(r, nome):
    return next((e for e in r['escores'] if e['nome'] == nome), None)


def _exame(r, titulo):
    return next((e for e in r['exames'] if e['titulo'] == titulo), None)


def _sem_nivel(classe):
    """'SBC IIa-C' → 'SBC IIa'; 'AHA 2b-B-NR' → 'AHA 2b' (o nível de evidência não entra na comparação)."""
    return classe.strip().split('-')[0].strip()


def _tokens(classe):
    return {_sem_nivel(t) for t in classe.split('·')}


def _check_escores(c, r, pac, erros):
    pts, classe, nivel = pac.rcri()
    e = _escore(r, 'RCRI (Lee)')
    if (e['valor'], e['classe'], e['nivel']) != (pts, classe, nivel):
        erros.append(f'RCRI: esperado {pts}/{classe}/{nivel}, veio {e["valor"]}/{e["classe"]}/{e["nivel"]}')
    if e['elevado_aha'] != (pts > 1):
        erros.append('RCRI: limiar AHA (> 1) errado')
    pts, nivel = pac.aub()
    e = _escore(r, 'AUB-HAS2')
    if (e['valor'], e['nivel']) != (pts, nivel):
        erros.append(f'AUB-HAS2: esperado {pts}/{nivel}, veio {e["valor"]}/{e["nivel"]}')
    v, e = pac.vsg(), _escore(r, 'VSG-CRI')
    if v is None and e is not None:
        erros.append('VSG-CRI calculado fora de cirurgia vascular arterial')
    if v is not None and (e is None or (e['valor'], e['nivel']) != v):
        erros.append(f'VSG-CRI: esperado {v}, veio {e and (e["valor"], e["nivel"])}')
    cap = _escore(r, 'Capacidade funcional')
    if cap['estado'] != pac.capacidade():
        erros.append(f'Capacidade: esperado {pac.capacidade()}, veio {cap["estado"]}')
    d = pac.dasi()
    if cap['dasi'] != d:
        erros.append(f'DASI: esperado {d}, veio {cap["dasi"]}')
    if d is not None and cap['mets'] != round((0.43 * d + 9.6) / 3.5, 1):
        erros.append(f'METs do DASI: veio {cap["mets"]}')
    if r['clcr'] != pac.clcr():
        erros.append(f'Cockcroft-Gault: esperado {pac.clcr()}, veio {r["clcr"]}')
    f = _escore(r, 'Fragilidade (CFS)')
    if pac.cfs is None:
        if f is not None:
            erros.append('CFS mostrado sem ter sido informado')
    else:
        esperado = 'Robusto' if pac.cfs <= 3 else 'Pré-frágil' if pac.cfs == 4 else 'Frágil'
        if f is None or f['faixa'] != esperado:
            erros.append(f'CFS {pac.cfs}: esperado {esperado}, veio {f and f["faixa"]}')


def _check_indicacao(c, r, pac, erros):
    ind = r['indicacao']
    esperado = pac.tipo()
    if ind['tipo'] != esperado:
        erros.append(f'Indicação: esperado {esperado}, veio {ind["tipo"]} ({ind["conclusao"]})')
    passo_inst = next((p for p in ind['passos'] if p['pergunta'].startswith('Condição cardiovascular grave')), None)
    if esperado == 'adiar' and passo_inst and passo_inst['resposta'] != 'Sim':
        erros.append('Passo "condição grave ou instável" respondido "Não" com PA ≥ 180/110 ou condição instável')
    # Coerência: a conclusão não pode dizer que exames cardíacos não estão indicados quando o eco é classe 1 (AHA)
    if esperado == 'nao_indicada' and pac.sint & {'dispneia_nova', 'sinais_ic'}:
        if ('exames cardíacos não indicados' in ind['conclusao'] or 'sem investigação' in ind['conclusao']
                or 'Pode operar' in ind['conclusao']):
            erros.append('Dispneia nova ou sinais de IC: a AHA recomenda avaliar a função do VE ANTES da cirurgia '
                         f'(classe 1); a conclusão diz: {ind["conclusao"]}')
    if esperado != 'emergencia' and ind['tipo'] == esperado and not ind['referencias']:
        erros.append('Indicação sem referência')


def _esperado_exames(pac):
    """{titulo: {'estado': set(...)|None, 'aha': str|None, 'sbc': str|None, 'ausente_ok': bool, 'div': bool}}"""
    x = {}
    sint, cond, idade = pac.sint, pac.cond, pac.idade
    dcv, cir_ia, pac_ia = pac.dcv, pac.cir_ia, pac.pac_ia()

    def poe(titulo, estado, aha=None, sbc=None, ausente_ok=False, div=False):
        x[titulo] = {'estado': estado if isinstance(estado, set) else {estado}, 'aha': aha, 'sbc': sbc,
                     'ausente_ok': ausente_ok, 'div': div}

    # ECG (AHA recomendações de ECG 1–4; SBC Quadro 3)
    if pac.aha_elev:
        aha = '2a' if (dcv or sint) else '2b'
    else:
        aha = '3: sem benefício' if not sint else None
    sbc_i = dcv or bool(sint) or cir_ia or pac_ia or 'diabetes' in cond
    sbc = 'I' if sbc_i else 'IIa' if ('obesidade' in cond or idade > 40) else '—'   # Quadro 3 não tem classe III
    indicado = aha in ('2a', '2b') or sbc in ('I', 'IIa')
    estado = 'indicado' if indicado else 'nao_indicado'
    ecg_dias = pac.feitos.get('Eletrocardiograma de repouso')
    if indicado and ecg_dias is not None and ecg_dias <= 365 and not sint and not (pac_ia and cir_ia):
        # com risco intermediário/alto em cirurgia intermediária/alta, o ECG pré-operatório é a linha de base do
        # 1º e 2º dia (SBC Quadro 30), então não vale o antigo
        estado = 'ja_feito'
    poe('Eletrocardiograma de repouso', estado, aha=aha, sbc=sbc,
        div=bool(aha and aha.startswith('3') and sbc in ('I', 'IIa')))

    # Ecocardiograma (AHA função de VE e valvas; SBC Quadros 4 e 16)
    eco_dias = pac.feitos.get('Ecocardiograma transtorácico')
    if sint & {'dispneia_nova', 'sinais_ic'}:
        poe('Ecocardiograma transtorácico', 'indicado', aha='1', sbc='I' if cir_ia else None)
    elif 'sopro' in sint:
        poe('Ecocardiograma transtorácico', 'indicado', aha='1', sbc='I' if cir_ia else None)
    elif 'dispneia' in sint and cir_ia and (eco_dias is None or eco_dias > 365):
        poe('Ecocardiograma transtorácico', 'indicado', sbc='I')     # SBC Q4: "sintomas sugestivos" de IC
    elif 'dispneia' in sint:
        pass
    elif 'valvopatia' in cond and cir_ia:
        recente = eco_dias is not None and eco_dias <= 183
        poe('Ecocardiograma transtorácico', {'ja_feito', 'nao_indicado'} if recente else 'indicado',
            sbc=None if recente else 'I')
    elif 'valvopatia' in cond:
        pass                                     # baixo risco com valvopatia conhecida: fontes não definem
    elif 'ic' in cond and cir_ia:
        recente = eco_dias is not None and eco_dias <= 365
        poe('Ecocardiograma transtorácico', {'ja_feito', 'nao_indicado'} if recente else 'indicado',
            sbc=None if recente else 'I')
    elif 'protese_mecanica' in cond and cir_ia and (eco_dias is None or eco_dias > 365):
        poe('Ecocardiograma transtorácico', 'indicado', sbc='IIa')
    elif pac.tx_hep:
        poe('Ecocardiograma transtorácico', 'indicado', sbc='I')
    elif pac.risco == A:
        poe('Ecocardiograma transtorácico', 'considerar', aha='3: sem benefício', sbc='IIb', div=True)
    elif 'ic' not in cond:
        poe('Ecocardiograma transtorácico', 'nao_indicado', aha='3: sem benefício', sbc='III')

    # BNP / NT-proBNP (AHA 2a; SBC Quadro 29, restrito a risco intermediário/alto pela Figura 1)
    aha = '2a' if pac.aha_elev and (dcv or idade >= 65 or (idade >= 45 and sint)) else None
    fr = bool(cond & {'diabetes', 'hipertensao', 'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica',
                      'obesidade', 'fa'})
    sbc = 'I' if cir_ia and (idade >= 66 or (45 <= idade <= 64 and (dcv or fr))) else None
    if aha or sbc:
        poe('Peptídeo natriurético BNP/PROBNP', 'indicado', aha=aha or '—', sbc=sbc or '—')
    else:
        poe('Peptídeo natriurético BNP/PROBNP', 'nao_indicado', ausente_ok=True)

    # Troponina pré-operatória (AHA 2b; SBC Quadros 17 e 30)
    if not cir_ia:
        poe('Troponina, soro', 'nao_indicado')
    else:
        sbc = 'I' if (pac_ia or pac.cir == 'transplante_renal') else None
        aha = '2b' if (dcv or idade >= 65 or (idade >= 45 and sint)) else None
        if sbc:
            poe('Troponina, soro', 'indicado', sbc='I', aha=aha or '—')
        elif aha:
            poe('Troponina, soro', 'considerar', aha='2b', sbc='—')
        else:
            poe('Troponina, soro', 'nao_indicado', ausente_ok=True)

    # Cateterismo (AHA ICA 3; SBC Quadro 7)
    if 'sca' in pac.inst:
        poe('Cineangiocoronariografia', 'indicado', sbc='I')                  # SBC Quadro 7, I-A
        poe('Cateterismo cardíaco de rotina', set(), ausente_ok=True)
    elif cir_ia:
        poe('Cateterismo cardíaco de rotina', 'nao_indicado', aha='3: sem benefício')  # SBC III só p/ baixo risco

    # HbA1c (AHA 2a; NICE 1.5)
    dias = pac.feitos.get('Hemoglobina glicada (HbA1c), soro')
    if 'diabetes' in cond and pac.eletiva:
        poe('Hemoglobina glicada (HbA1c), soro', 'ja_feito' if dias is not None and dias <= 92 else 'indicado',
            aha='2a')
    elif pac.eletiva and (idade >= 35 or cond & {'hipertensao', 'obesidade', 'dac', 'iam_previo', 'avc_ait',
                                                  'doenca_arterial_periferica'}):
        # Rastreio: AHA 2a ("at risk for diabetes"); SBD/SBA/ABESO 2026 R1, I-B (doi:10.1186/s13098-025-02060-5).
        # É oportunístico: com o paciente liberado pelo fluxo, não é marcado sozinho.
        rastreio = 'considerar' if pac.liberado() else 'indicado'
        poe('Hemoglobina glicada (HbA1c), soro', {rastreio, 'ja_feito'})
        poe('Glicose, soro', {rastreio, 'ja_feito'})

    # NICE NG45 (porte × ASA)
    asa = pac.asa
    if pac.porte == 'maior':
        poe('Hemograma completo com plaquetas', 'indicado')
    elif pac.porte == 'intermediaria' and asa and asa >= 3 and (dcv or 'doenca_renal' in cond):
        poe('Hemograma completo com plaquetas', 'considerar')
    if asa and ((pac.porte == 'maior' and asa >= 2) or (pac.porte == 'intermediaria' and asa >= 3)):
        poe('Creatinina, soro', 'indicado')
    elif pac.meds & DOAC:
        poe('Creatinina, soro', 'indicado')      # SBC Quadro 26: suspensão do DOAC depende da depuração
    if pac.tipo() == 'incompleto':
        if 'creatinina' in pac.faltam():
            poe('Creatinina, soro', 'indicado')
        if 'hemoglobina' in pac.faltam():
            poe('Hemograma completo com plaquetas', 'indicado')
    # AHA Figura 1: liberado para a cirurgia → nenhum exame cardíaco marcado sozinho (classe 1 da AHA e as
    # recomendações próprias dos transplantes ficam)
    if pac.liberado() and not pac.cir.startswith('transplante'):
        for titulo in ('Eletrocardiograma de repouso', 'Ecocardiograma transtorácico',
                       'Peptídeo natriurético BNP/PROBNP', 'Troponina, soro'):
            esp = x.get(titulo)
            if esp and 'indicado' in esp['estado'] and esp['aha'] != '1':
                esp['estado'] = (esp['estado'] - {'indicado'}) | {'considerar'}
                esp['div'] = True
    if 'varfarina' in pac.meds:
        poe('Tempo de protrombina (TP/INR), plasma', 'indicado')
    elif 'hepatopatia' in cond and asa and asa >= 3 and pac.porte in ('intermediaria', 'maior'):
        poe('Coagulograma (TP/INR e TTPa)', 'considerar')
    elif not pac.meds & DOAC and 'hepatopatia' not in cond:
        poe('Coagulograma (TP/INR e TTPa)', 'nao_indicado')
    poe('Radiografia de tórax', 'indicado' if pac.tx_hep else 'nao_indicado')
    if pac.sexo == 'feminino' and idade <= 45:
        poe('Beta-hCG, soro', 'considerar')
    elif pac.sexo == 'feminino' and idade >= 60:
        poe('Beta-hCG, soro', set(), ausente_ok=True)
    return x


def _check_exames(c, r, pac, erros):
    if pac.urg == 'emergencia':
        if any(e['estado'] != 'nao_indicado' for e in r['exames']):
            erros.append('Emergência: nenhum exame que atrase a cirurgia (AHA Tabela 2; SBC 2.1.2)')
        return
    for titulo, esp in _esperado_exames(pac).items():
        e = _exame(r, titulo)
        if e is None:
            if not esp['ausente_ok']:
                erros.append(f'{titulo}: ausente; esperado {sorted(esp["estado"])}')
            continue
        if esp['estado'] and e['estado'] not in esp['estado']:
            erros.append(f'{titulo}: esperado {sorted(esp["estado"])}, veio {e["estado"]} '
                         f'(AHA {e["aha"]}, SBC {e["sbc"]})')
        if not esp['estado'] and esp['ausente_ok'] and e['estado'] != 'nao_indicado':
            erros.append(f'{titulo}: não deveria aparecer como {e["estado"]}')
        if esp['aha'] and e['aha'] != esp['aha']:
            erros.append(f'{titulo}: classe AHA esperada {esp["aha"]}, veio {e["aha"]}')
        if esp['sbc'] and e['sbc'] != esp['sbc']:
            erros.append(f'{titulo}: classe SBC esperada {esp["sbc"]}, veio {e["sbc"]}')
        if esp['div'] and not e['divergencia']:
            erros.append(f'{titulo}: divergência AHA × SBC não sinalizada')
    # Provas de isquemia: só risco elevado + capacidade baixa/desconhecida + cirurgia que pode esperar
    isq = [e for e in r['exames'] if e.get('grupo') == 'isquemia' and e['estado'] != 'nao_indicado']
    quer = pac.tipo() == 'indicada' and pac.pac_ia() and pac.capacidade() != 'boa' and pac.eletiva and pac.cir_ia
    if quer:
        titulos = {e['titulo']: e for e in isq}
        for t, aha, sbc in (('Cintilografia de perfusão miocárdica (estresse e repouso)', '2b', 'IIa'),
                            ('Ecocardiograma de estresse com dobutamina', '2b', 'IIa'),
                            ('Angiotomografia de coronárias', '2b', '—')):
            e = titulos.get(t)
            if e is None or e['estado'] != 'considerar' or e['aha'] != aha or e['sbc'] != sbc:
                erros.append(f'{t}: esperado considerar (AHA {aha}, SBC {sbc}), veio {e and (e["estado"], e["aha"], e["sbc"])}')
    elif (pac.tipo() in ('nao_indicada', 'indicada') and not pac.pac_ia() and pac.cir_ia
          and pac.capacidade() != 'boa' and pac.urg == 'eletiva'
          and pac.cond & {'dac', 'iam_previo', 'stent', 'revascularizacao_cirurgica'}):
        # SBC Quadro 6 (IIb-B): capacidade baixa, assintomático, DAC conhecida; AHA: risco < 1% → sem teste
        if not pac.sint & {'angina', 'dispneia', 'dispneia_nova'}:
            e = _exame(r, 'Cintilografia de perfusão miocárdica (estresse e repouso)')
            if e is None or e['estado'] != 'considerar' or e['sbc'] != 'IIb':
                erros.append(f'Cintilografia: esperado considerar (SBC IIb, Quadro 6), veio {e and (e["estado"], e["sbc"])}')
    elif isq:
        erros.append(f'Prova de isquemia sugerida sem critério: {[e["titulo"] for e in isq]}')
    if pac.urologica:
        e = next((e for e in r['exames'] if 'Urina' in e['titulo'] or 'Urocultura' in e['titulo']), None)
        if e is None or e['estado'] == 'nao_indicado':
            erros.append('Cirurgia urológica: urina/urocultura deveria ser sugerida (NICE NG45)')


def _eh_stent(titulo):
    return 'tent' in titulo or 'ngioplastia' in titulo


def _check_adiar(c, r, pac, erros):
    pend = {a['titulo'] for a in r['adiar'] if not a.get('ok')}
    ok = {a['titulo'] for a in r['adiar'] if a.get('ok')}
    esperados, proibidos = set(), set()
    if pac.eletiva:
        esperados |= {INSTAVEL_ROTULO[k] for k in pac.inst}
    if pac.eletiva and pac.pa_descontrolada:
        esperados.add('PA')
    if 'avc_ait_recente' in pac.cond and pac.eletiva:
        if pac.cir in CAROTIDA_SINTOMATICA:
            proibidos.add('AVC ou AIT há menos de 3 meses')     # o AVC/AIT é a indicação da cirurgia
        else:
            esperados.add('AVC ou AIT há menos de 3 meses')
    if 'diabetes' in pac.cond and pac.eletiva and (pac.hba1c or 0) > 8:
        if not any(t.startswith('HbA1c') for t in pend):
            erros.append(f'HbA1c {pac.hba1c}% em eletiva: esperado otimizar/adiar até < 8% (SBD/SBA/ABESO 2026 R2)')
    if 'ic_recente' in pac.cond and pac.eletiva and IC_RECENTE not in pend:
        erros.append('IC de início recente sem tratamento otimizado: adiar eletiva ≥ 3 meses (SBC Quadro 8, I-C)')
    for e in esperados:
        if e == 'PA':
            if not any(t.startswith('PA ') for t in pend):
                erros.append('PA ≥ 180/110 em cirurgia eletiva sem adiamento (SBC Tabela 2 / Quadro 9; AHA 2b)')
        elif e not in pend:
            erros.append(f'Adiamento esperado ausente: {e}')
    for e in proibidos:
        if e in pend:
            erros.append(f'Adiamento indevido: {e} (endarterectomia/stent de carótida sintomática deve ser feita '
                         'precocemente, idealmente em até 14 dias do evento)')
    textos = {a['titulo']: a['texto'].lower() for a in r['adiar']}
    if not pac.eletiva:
        sobra = [t for t in pend if t.startswith('PA ') or t.startswith('AVC')
                 or ((_eh_stent(t) or t in INSTAVEL_ROTULO.values()) and ('adiar' in textos[t] or 'esperar' in textos[t]))]
        if sobra:
            erros.append(f'Urgência/emergência não se adia por {sobra} (AHA ICP rec. 8; Tabela 2)')
    st = pac.stent
    if st and pac.eletiva:
        pend_st = [t for t in pend if _eh_stent(t)]
        ok_st = [t for t in ok if _eh_stent(t)]
        if not st.get('data'):
            if not any('não informada' in t for t in pend):
                erros.append('Angioplastia sem data: deveria pedir a data')
        elif pac.urg == 'tempo_sensivel':
            if not (pend_st or ok_st):
                erros.append('Stent em cirurgia tempo-sensível sem orientação de intervalo')
        else:
            dias = _dias(st['data']) if st['data'].count('-') == 2 else None
            if st['tipo'] == 'balao':
                janela = 14                                   # AHA 1 C-LD
            elif dias is not None and dias < 30:
                janela = 30                                   # AHA 3: dano; SBC III
            elif st['indicacao'] == 'sca':
                janela = 365                                  # AHA 1 (DES); SBC Quadro 23 (qualquer stent)
            else:
                janela = 183                                  # AHA 2a (DES); SBC Quadro 22 I-A
            if dias < janela and not pend_st:
                erros.append(f'Angioplastia há {dias} dias ({st["tipo"]}, {st["indicacao"]}): esperado adiamento '
                             f'(janela {janela} dias)')
            if dias >= janela and pend_st:
                erros.append(f'Angioplastia há {dias} dias fora da janela, mas pede adiamento: {pend_st}')
    if not pac.eletiva:      # instável em urgência/emergência: só "estabilizar sem atrasar" (SBC 2.1.2)
        esperados |= {INSTAVEL_ROTULO[k] for k in pac.inst}
    inesperados = [t for t in pend if not (t in esperados or (t.startswith('PA ') and 'PA' in esperados)
                                          or _eh_stent(t) or ('não informada' in t) or t == IC_RECENTE
                                          or t.startswith('HbA1c'))]
    if inesperados:
        erros.append(f'Adiamento inesperado: {inesperados}')


def _check_pulmonar(c, r, pac, erros):
    pul = r['pulmonar']
    pts, nivel = pac.ariscat()
    if pac.cir in ARISCAT_NA:
        if pul['escore'].get('aplicavel', True):
            erros.append('ARISCAT apresentado como aplicável em procedimento excluído da derivação (Canet 2010)')
    elif (pul['escore']['valor'], pul['escore']['nivel']) != (pts, nivel):
        erros.append(f'ARISCAT: esperado {pts}/{nivel}, veio {pul["escore"]["valor"]}/{pul["escore"]["nivel"]}')
    pts, nivel = pac.stop_bang()
    if (pul['stop_bang']['valor'], pul['stop_bang']['nivel']) != (pts, nivel):
        erros.append(f'STOP-Bang: esperado {pts}/{nivel}, veio {pul["stop_bang"]["valor"]}/{pul["stop_bang"]["nivel"]}')
    expansao = any(m['titulo'] == 'Expansão pulmonar no pós-operatório' for m in pul['medidas'])
    if ((pac.ariscat()[1] != B and pac.cir not in ARISCAT_NA) or 'dpoc' in pac.cond) and not expansao:
        erros.append('Expansão pulmonar não sugerida com ARISCAT ≥ 26 ou DPOC (ACP 2006)')
    titulos = {o['titulo'] for o in r['orientacoes']}
    quer_fumo = 'tabagismo' in pac.cond and pac.eletiva
    if quer_fumo != ('Parar de fumar' in titulos):
        erros.append(f'Orientação "parar de fumar": esperado {quer_fumo}')
    quer_frag = pac.idade >= 65 and pac.cir_ia and pac.cfs is None
    if quer_frag != ('Avaliar fragilidade' in titulos):
        erros.append(f'Orientação "avaliar fragilidade" (AHA 2a; SBC IIa): esperado {quer_frag}')


def _check_pos(c, r, pac, erros):
    pos = {x['titulo']: x for x in r['pos_operatorio']}
    aha_tn = sbc_tn = None
    if pac.cir_ia:
        if pac.dcv or pac.sint or pac.idade >= 66:
            aha_tn = 'AHA 2b'                                 # AHA MINS 1; Figura 1 (idade é fator de risco)
        if pac.pac_ia() or pac.cir == 'transplante_renal':
            sbc_tn = 'SBC I'                                  # SBC Quadros 17 e 30
    tn = pos.get('Troponina com 24 e 48 h')
    if aha_tn or sbc_tn:
        if tn is None:
            erros.append(f'Troponina 24/48 h ausente; esperado {aha_tn or ""} {sbc_tn or ""}'.strip())
        else:
            tk = _tokens(tn['classe'])
            for esperado in (aha_tn, sbc_tn):
                if esperado and esperado not in tk:
                    erros.append(f'Troponina 24/48 h: classe {esperado} ausente ({tn["classe"]})')
    elif tn is not None:
        erros.append(f'Troponina 24/48 h sem indicação (AHA 3 em baixo risco; SBC III): {tn["classe"]}')
    quer_ecg_uti = pac.pac_ia() and pac.cir_ia
    if quer_ecg_uti != ('ECG no 1º e no 2º dia' in pos):
        erros.append(f'ECG no 1º e 2º dia (SBC Quadro 30): esperado {quer_ecg_uti}')
    uti = pos.get('Unidade de terapia intensiva por 48 h')
    if quer_ecg_uti:
        classe = 'SBC I' if pac.nivel_algoritmo() == A else 'SBC IIa'
        if uti is None or _sem_nivel(uti['classe']) != classe:
            erros.append(f'UTI 48 h: esperado {classe} (nível {pac.nivel_algoritmo()}), veio {uti and uti["classe"]}')
    elif uti is not None:
        erros.append('UTI 48 h sem risco intermediário/alto pelo algoritmo em cirurgia de risco intermediário/alto')
    if ('hipertensao' in pac.cond) != ('Reintroduzir os anti-hipertensivos' in pos):
        erros.append('Reintrodução dos anti-hipertensivos (AHA 1; SBC I) não corresponde à hipertensão')
    if 'Evitar hipotensão' not in pos:
        erros.append('Evitar hipotensão (AHA 1; SBC I) ausente')


def _check_resumido(c, r, pac, erros):
    tem_adiar = any(not a.get('ok') for a in r['adiar'])
    quer = (pac.tipo() == 'nao_indicada' and pac.risco == B and pac.idade < 65 and (pac.cfs is None or pac.cfs < 5)
            and not pac.cond and not pac.sint and not pac.inst
            and not tem_adiar and not pac.pac_ia() and (pac.ariscat()[1] == B or pac.cir in ARISCAT_NA)
            and pac.stop_bang()[1] != A)
    if r['resumido'] != quer:
        erros.append(f'Resumido: esperado {quer}, veio {r["resumido"]}')
    if quer and r['resumido']:
        if not r['resumo'] or not r['resumo']['referencias']:
            erros.append('Resumo curto sem texto ou referência')
        if pac.idade <= 40:
            for t in ('Eletrocardiograma de repouso', 'Ecocardiograma transtorácico',
                      'Peptídeo natriurético BNP/PROBNP', 'Troponina, soro'):
                e = _exame(r, t)
                if e and e['estado'] == 'indicado':
                    erros.append(f'Jovem sem comorbidade em baixo risco com {t} indicado')


VERIFICA = {'escores': _check_escores, 'indicacao': _check_indicacao, 'exames': _check_exames,
            'adiar': _check_adiar, 'pulmonar': _check_pulmonar, 'pos': _check_pos, 'resumido': _check_resumido}


def _params():
    for c in CASOS:
        for aspecto in ASPECTOS:
            marcas = []
            motivo = XFAIL.get((c['id'], aspecto))
            if motivo:
                marcas.append(pytest.mark.xfail(strict=True, reason=motivo))
            yield pytest.param(c, aspecto, id=f'{c["id"]}-{aspecto}', marks=marcas)


@pytest.mark.parametrize('caso, aspecto', list(_params()))
def test_paciente(caso, aspecto):
    r = _rodar(caso)
    pac = Paciente(caso)
    erros = []
    VERIFICA[aspecto](caso, r, pac, erros)
    assert not erros, '\n'.join(erros)


def test_quantidade_de_casos_e_cobertura():
    """≥ 120 pacientes, todas as cirurgias, urgências, condições instáveis e faixas de idade."""
    assert len(CASOS) >= 120
    assert {c['cirurgia'] for c in CASOS} == set(SURG) == set(po.CIRURGIAS)
    assert {c.get('urgencia', 'eletiva') for c in CASOS} == set(po.URGENCIAS)
    assert set().union(*(set(c.get('instaveis', [])) for c in CASOS)) == set(po.INSTAVEIS)
    idades = [c['idade'] for c in CASOS]
    assert min(idades) <= 18 and max(idades) >= 95
    assert {c['sexo'] for c in CASOS} == {'masculino', 'feminino'}


def test_ecg_sem_criterio_da_sbc_nao_recebe_classe_iii():
    """SBC 2024 Quadro 3 só tem indicações I e IIa para o ECG; sem critério, a classe da SBC fica em branco."""
    c = next(x for x in CASOS if x['id'] == 'a01_f22_catarata_jovem_saudavel')
    ecg = _exame(_rodar(c), 'Eletrocardiograma de repouso')
    assert ecg['estado'] == 'nao_indicado' and ecg['aha'] == '3: sem benefício'
    assert ecg['sbc'] in ('—', '')


@pytest.mark.xfail(strict=True, reason='Lacuna documentada, sem fonte primária: nenhuma diretriz (AHA 2026, SBC 2024, '
                                       'ACP 2006) fixa prazo para adiar a eletiva após infecção respiratória; o ARISCAT '
                                       '(Canet 2010, doi:10.1097/ALN.0b013e3181fc6e0a) só a pontua (+17, OR 5,5). O motor '
                                       'não orienta adiar.')
def test_lacuna_infeccao_respiratoria_recente_sem_orientacao_de_adiar():
    c = _caso('lacuna_m55_colecistectomia_infeccao', 55, 'masculino', 'colecistectomia', infeccao_respiratoria=True,
              asa=2, **LAB_OK)
    r = _rodar(c)
    assert any('nfec' in a['titulo'] or 'nfec' in a['texto'] for a in r['adiar'] if not a.get('ok'))
