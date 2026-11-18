"""Procedimentos do SUS (Tabela SIGTAP) dos exames do catálogo e quais pedem laudo de APAC.

Quem decide se o exame sai em APAC é a regulação. Seguimos o protocolo de regulação ambulatorial eletiva da
SES-GO (Policlínica Estadual da Região Nordeste, tabela de SADT, coluna OBS): tomografia, ressonância,
endoscopia digestiva alta, colonoscopia e densitometria óssea vão em APAC; radiografia, ultrassonografia,
ecocardiograma, mamografia, teste ergométrico, Holter e MAPA, não.
https://goias.gov.br/saude/wp-content/uploads/sites/34/regulacao_estadual/protocolos-regulacao-acesso-ambulatorial-eletivo/Policl%C3%ADnica%20Estadual%20da%20Regi%C3%A3o%20Nordeste%20%E2%80%93%20Posse.pdf

Além desses, todo exame da Tabela de Procedimentos de Alta Complexidade (PAC) sai com laudo de APAC, de laboratório
inclusive (carga viral e CD4 do HIV, teste de DNA-HPV): decisão do responsável clínico, 18/11/2026. A tabela é a que
ele enviou (TRFMED, publicada em 21/02/2022), guardada em src/data/tabela_pac.json por código TUSS; o exame entra
quando um dos códigos TUSS dele (src/utils/tuss.py) está na tabela.

Código só entra quando conferido em documento público (protocolo da SES-GO acima, tabelas SUS de consórcios
públicos, parâmetros técnicos do INCA para mama). Exame em APAC sem código conferido sai com o campo em branco,
para a regulação preencher: nunca um código adivinhado.
"""

import json
from functools import lru_cache
from pathlib import Path

# título do catálogo → (código SIGTAP ou '', vai em APAC?)
PROCEDIMENTOS = {
    # Tomografia (SES-GO: APAC)
    'Tomografia computadorizada de tórax de alta resolução': ('0206020031', True),
    'Tomografia computadorizada de tórax de baixa dose (LDCT)': ('0206020031', True),
    'Tomografia de tórax de baixa dose': ('0206020031', True),
    'Angiotomografia de coronárias': ('', True),          # SES-GO: APAC, sem código no protocolo
    'Escore de cálcio coronariano (TC)': ('', True),
    # Ressonância (SES-GO: APAC)
    'Ressonância magnética de crânio': ('0207010064', True),
    'Angiorressonância de crânio': ('', True),
    'Ressonância magnética de mamas': ('', True),
    'Ressonância magnética de corpo inteiro': ('', True),
    # Endoscopia, colonoscopia e densitometria (SES-GO: APAC)
    'Endoscopia digestiva alta': ('0209010037', True),
    'Colonoscopia': ('0209010029', True),
    'Colonoscopia de Rastreio com ou sem biópsia': ('0209010029', True),
    'Densitometria óssea (DEXA)': ('0204060028', True),
    'Densitometria óssea (coluna lombar e fêmur)': ('0204060028', True),
    # Sem APAC (SES-GO): o código serve ao pedido comum
    'Radiografia de tórax (PA e perfil)': ('0204030153', False),
    'Radiografia de tórax': ('0204030170', False),
    'Mamografia Digital - Bilateral': ('0204030188', False),
    'Mamografia bilateral': ('0204030188', False),
    'Ultrassonografia de abdome total': ('0205020046', False),
    'Ultrassonografia de abdome superior': ('0205020038', False),
    'Ultrassonografia de rins e vias urinárias': ('0205020054', False),
    'Ultrassonografia de vias urinárias': ('0205020054', False),
    'Ultrassonografia de mamas': ('0205020097', False),
    'Ultrassonografia de próstata (via abdominal)': ('0205020100', False),
    'Ultrassonografia de tireoide': ('0205020127', False),
    'Ultrassonografia obstétrica': ('0205020143', False),
    'Ultrassonografia pélvica transvaginal': ('0205020186', False),
    'Ecocardiograma transtorácico': ('0205010032', False),
    'Teste ergométrico': ('0211020060', False),
    'Holter de 24 horas': ('0211020044', False),
    'MAPA - Monitorização Ambulatorial da Pressão Arterial (24h)': ('0211020052', False),
    'MAPA de 24 horas': ('0211020052', False),
}

FONTE_APAC = 'SES-GO, protocolo de regulação ambulatorial (SADT)'


def codigo(titulo):
    return PROCEDIMENTOS.get(titulo, ('', False))[0]


_ARQUIVO_DA_PAC = Path(__file__).resolve().parent.parent / 'data' / 'tabela_pac.json'


@lru_cache(maxsize=1)
def tabela_de_pac():
    """{'fonte': ..., 'codigos': {código TUSS: nome do procedimento}} da tabela de alta complexidade."""
    return json.loads(_ARQUIVO_DA_PAC.read_text(encoding='utf-8'))


def na_tabela_de_pac(titulo):
    """O exame tem código TUSS na Tabela de Procedimentos de Alta Complexidade (PAC)?"""
    from src.utils import tuss
    pac = tabela_de_pac()['codigos']
    return any(linha['codigo'] in pac for sexo in ('feminino', 'masculino') for linha in tuss.linhas_da_guia(titulo, sexo))


def vai_em_apac(titulo):
    """O exame sai com laudo de APAC: a regulação pede (SES-GO) ou ele está na tabela de alta complexidade (PAC)."""
    return PROCEDIMENTOS.get(titulo, ('', False))[1] or na_tabela_de_pac(titulo)


def titulos_em_apac(titulos):
    """Dos títulos dados, os que saem com laudo de APAC (para a tela saber quando pedir os dados do laudo)."""
    return sorted({t for t in titulos if vai_em_apac(t)}, key=str.lower)


def formatado(cod):
    """0206020031 → 02.06.02.003-1 (como na Tabela SIGTAP)."""
    if len(cod or '') != 10:
        return ''
    return f'{cod[0:2]}.{cod[2:4]}.{cod[4:6]}.{cod[6:9]}-{cod[9]}'


# CID-10 automático do laudo de APAC. Ordem: o CID que o médico digitou; a comorbidade marcada que motivou
# aquele exame (ex.: colonoscopia na doença de Crohn); o código de rastreamento do exame (capítulo Z da CID-10,
# OMS); a primeira comorbidade marcada; e, por fim, Z00.0 (exame médico geral). O secundário é a primeira
# comorbidade marcada que não virou o principal. É sugestão de codificação: o médico pode reescrever.
CID_DA_COMORBIDADE = {
    'diabetes': 'E11.9', 'diabetes_tipo_1': 'E10.9', 'hipertensao': 'I10', 'has_resistente': 'I10',
    'dislipidemia': 'E78.5', 'obesidade': 'E66.9', 'dpoc': 'J44.9', 'doenca_renal': 'N18.9',
    'insuficiencia_cardiaca': 'I50.9', 'hiv': 'B24', 'hbv_risco_chc': 'B18.1',
    'crohn_colon': 'K50.1', 'crohn_8_anos': 'K50.9', 'crohn_cep': 'K50.9', 'crohn_delgado': 'K50.0',
    'rcu_8_anos': 'K51.9', 'rcu_alem_reto': 'K51.9', 'rcu_cep': 'K51.9',
    'les_nefrite': 'M32.1', 'osteoporose_diagnostico': 'M81.9', 'psoriase_extensa': 'L40.0',
}
# Exame → comorbidades que o motivam no motor (a primeira marcada vira o CID principal).
_COMORBIDADES_DO_EXAME = {
    'Colonoscopia': ('crohn_colon', 'crohn_8_anos', 'crohn_cep', 'rcu_8_anos', 'rcu_alem_reto', 'rcu_cep'),
    'Colonoscopia de Rastreio com ou sem biópsia': ('crohn_colon', 'crohn_8_anos', 'crohn_cep', 'rcu_8_anos',
                                                    'rcu_alem_reto', 'rcu_cep'),
    'Densitometria óssea (DEXA)': ('osteoporose_diagnostico',),
    'Densitometria óssea (coluna lombar e fêmur)': ('osteoporose_diagnostico',),
    'Carga Viral do HIV (HIV RNA)': ('hiv',), 'Contagem de linfócitos T CD4+': ('hiv',),
    'Genotipagem do HIV (Teste de Resistência)': ('hiv',),
}
# Exame de rastreamento → CID-10 de "exame especial de rastreamento" (Z12.1 intestino, Z12.2 aparelho respiratório,
# Z12.3 mama, Z12.8 outras localizações, Z13.6 doenças cardiovasculares, Z13.8 outras doenças especificadas).
_CID_DO_RASTREIO = {
    'Tomografia computadorizada de tórax de baixa dose (LDCT)': 'Z12.2',
    'Tomografia de tórax de baixa dose': 'Z12.2',
    'Colonoscopia': 'Z12.1', 'Colonoscopia de Rastreio com ou sem biópsia': 'Z12.1',
    'Ressonância magnética de mamas': 'Z12.3', 'Ressonância magnética de corpo inteiro': 'Z12.8',
    'Angiotomografia de coronárias': 'Z13.6', 'Escore de cálcio coronariano (TC)': 'Z13.6',
    'Densitometria óssea (DEXA)': 'Z13.8', 'Densitometria óssea (coluna lombar e fêmur)': 'Z13.8',
    'Ressonância magnética de crânio': 'Z13.8', 'Angiorressonância de crânio': 'Z13.8',
    'Mamografia Digital - Bilateral': 'Z12.3', 'Mamografia bilateral': 'Z12.3',       # tabela de PAC
    'Pesquisa do Papilomavírus Humano (HPV), por técnica molecular': 'Z12.4',
}


def cid_do_exame(titulo, comorbidades=(), digitado=''):
    """(CID principal, CID secundário) do laudo de APAC daquele exame."""
    marcadas = [CID_DA_COMORBIDADE[c] for c in comorbidades if c in CID_DA_COMORBIDADE]
    if digitado:
        principal = digitado
    else:
        do_exame = [CID_DA_COMORBIDADE[c] for c in _COMORBIDADES_DO_EXAME.get(titulo, ()) if c in comorbidades]
        principal = (do_exame or [_CID_DO_RASTREIO.get(titulo)] or [None])[0] or (marcadas[0] if marcadas else 'Z00.0')
    secundario = next((c for c in marcadas if c != principal), '')
    return principal, secundario
