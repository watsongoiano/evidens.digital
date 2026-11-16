"""Procedimentos do SUS (Tabela SIGTAP) dos exames do catálogo e quais pedem laudo de APAC.

Quem decide se o exame sai em APAC é a regulação. Seguimos o protocolo de regulação ambulatorial eletiva da
SES-GO (Policlínica Estadual da Região Nordeste, tabela de SADT, coluna OBS): tomografia, ressonância,
endoscopia digestiva alta, colonoscopia e densitometria óssea vão em APAC; radiografia, ultrassonografia,
ecocardiograma, mamografia, teste ergométrico, Holter e MAPA, não.
https://goias.gov.br/saude/wp-content/uploads/sites/34/regulacao_estadual/protocolos-regulacao-acesso-ambulatorial-eletivo/Policl%C3%ADnica%20Estadual%20da%20Regi%C3%A3o%20Nordeste%20%E2%80%93%20Posse.pdf

Código só entra quando conferido em documento público (protocolo da SES-GO acima, tabelas SUS de consórcios
públicos, parâmetros técnicos do INCA para mama). Exame em APAC sem código conferido sai com o campo em branco,
para a regulação preencher: nunca um código adivinhado.
"""

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


def vai_em_apac(titulo):
    return PROCEDIMENTOS.get(titulo, ('', False))[1]


def formatado(cod):
    """0206020031 → 02.06.02.003-1 (como na Tabela SIGTAP)."""
    if len(cod or '') != 10:
        return ''
    return f'{cod[0:2]}.{cod[2:4]}.{cod[4:6]}.{cod[6:9]}-{cod[9]}'
