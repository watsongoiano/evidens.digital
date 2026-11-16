"""Triagem de segurança para vacinas de vírus vivos atenuados e HPV.

Esta camada é independente das regras que indicam cada vacina. Ela recebe a
lista já montada e retira dela o que não pode ser sugerido automaticamente,
explicando o motivo. O que é retirado não desaparece: volta em uma lista à
parte (`nao_incluidas`), para que o médico saiba o que ficou de fora e por quê.

Estados possíveis de um item retirado:

* ``contraindicada``       – há contraindicação formal na situação informada;
* ``precaucao``            – a indicação exige avaliação individual de
                             risco-benefício pelo médico;
* ``dados_insuficientes``  – falta uma resposta da triagem; "desconhecido"
                             nunca é tratado como "não".

Fontes dos critérios (conferir a cada revisão do calendário):

* Calendários de vacinação SBIm 2026/2027 (adulto, idoso, gestante);
* Ministério da Saúde/PNI – febre amarela em gestantes, nutrizes e idosos;
* Manual dos Centros de Referência para Imunobiológicos Especiais (CRIE),
  6ª ed., 2023 – pessoas vivendo com HIV e imunossuprimidos.

As regras são deliberadamente conservadoras: na dúvida, o item sai da lista
automática e a decisão volta para o médico.
"""
from __future__ import annotations

import re

from src.utils.validacao import (
    DESCONHECIDO,
    LACTANTE_6M_OU_MAIS,
    LACTANTE_MENOR_6M,
    SIM,
)

CONTRAINDICADA = 'contraindicada'
PRECAUCAO = 'precaucao'
DADOS_INSUFICIENTES = 'dados_insuficientes'

TRIPLICE_VIRAL = 'triplice_viral'
VARICELA = 'varicela'
FEBRE_AMARELA = 'febre_amarela'
DENGUE = 'dengue'
ATENUADA_NAO_CLASSIFICADA = 'atenuada_nao_classificada'
HPV = 'hpv'

ATENUADAS = (TRIPLICE_VIRAL, VARICELA, FEBRE_AMARELA, DENGUE, ATENUADA_NAO_CLASSIFICADA)

CD4_MINIMO_ATENUADAS = 200
CD4_IMUNOSSUPRESSAO_LEVE = 350
IDADE_PRECAUCAO_FEBRE_AMARELA = 60

# Classes internas de medicação (src/utils/doses.py e condicoes.MEDICACOES) que mudam a triagem das
# vacinas de vírus vivo sem implicar, sozinhas, "Imunossupressão: Sim".
CORTICOIDE_DOSE_DESCONHECIDA = 'corticoide_dose_desconhecida'
IMUNOSSUPRESSAO_BAIXO_GRAU = 'imunossupressao_baixo_grau'
TRATAMENTO_ONCOLOGICO = 'oncologico'

REF_SBIM = 'SBIm 2026/2027'
REF_MS_FA = 'Ministério da Saúde/PNI; SBIm 2026/2027'
REF_CRIE = 'Manual dos CRIE (MS, 2023)'
REF_ESPECIAIS = 'SBIm Pacientes Especiais 2026/2027'
REF_DENGUE_IMUNO = 'SBIm Pacientes Especiais 2026/2027 / IN CNV 2026 (MS)'

# Reconhecimento pelo título. É usado quando o item não traz o atributo
# `viva_atenuada` — por exemplo, a lista que o navegador devolve ao pedir o PDF.
_PADROES = (
    (TRIPLICE_VIRAL, re.compile(r'tr[ií]plice\s+viral|tetra\s*viral|\bscrv?\b|sarampo|priorix|m-m-r', re.I)),
    (VARICELA, re.compile(r'varicela|varilrix|varivax', re.I)),
    (FEBRE_AMARELA, re.compile(r'febre\s+amarela|stamaril', re.I)),
    (DENGUE, re.compile(r'dengue|qdenga|butantan-dv', re.I)),
    (HPV, re.compile(r'\bhpv\b|gardasil|papilomav[ií]rus', re.I)),
)


def classificar_vacina(titulo, viva_atenuada=None):
    """Devolve o tipo de vacina sujeito à triagem, ou None se não houver restrição."""
    titulo = titulo or ''
    for tipo, padrao in _PADROES:
        if padrao.search(titulo):
            return tipo
    if viva_atenuada:
        return ATENUADA_NAO_CLASSIFICADA
    return None


def _resultado(estado, motivo, referencia):
    return {'estado': estado, 'motivo': motivo, 'referencia': referencia}


def avaliar_vacina(tipo, triagem, contexto):
    """Avalia um tipo de vacina contra a triagem do paciente.

    `triagem`: {'gestante', 'lactante', 'imunossupressao'} com os valores de
    `src.utils.validacao`. Chave ausente vale como "desconhecido".
    `contexto`: {'idade', 'hiv' (bool), 'cd4' (float ou None), 'classes' (classes de medicação em uso)}.

    Devolve None quando a vacina pode seguir na lista de recomendações; caso
    contrário, um dicionário com `estado`, `motivo` e `referencia`.
    """
    gestante = triagem.get('gestante', DESCONHECIDO)
    lactante = triagem.get('lactante', DESCONHECIDO)
    imunossupressao = triagem.get('imunossupressao', DESCONHECIDO)

    if tipo == HPV:
        if gestante == SIM:
            return _resultado(
                CONTRAINDICADA,
                'HPV: contraindicada na gestação. Iniciar ou completar o esquema após o parto.',
                REF_SBIM,
            )
        if gestante == DESCONHECIDO:
            return _resultado(
                DADOS_INSUFICIENTES,
                'HPV: informe se a paciente é gestante para avaliar a indicação.',
                REF_SBIM,
            )
        return None

    if tipo not in ATENUADAS:
        return None

    # 1. Gestação
    if gestante == SIM:
        if tipo == FEBRE_AMARELA:
            return _resultado(
                CONTRAINDICADA,
                'Febre amarela: contraindicada na gestação. Se não for possível adiar (surto ou '
                'emergência epidemiológica), o serviço de saúde deve avaliar risco-benefício.',
                REF_MS_FA,
            )
        return _resultado(
            CONTRAINDICADA,
            'Vacina de vírus vivo atenuado: contraindicada na gestação.',
            REF_SBIM,
        )

    # 2. Pessoa vivendo com HIV: depende do CD4
    if contexto.get('hiv'):
        cd4 = contexto.get('cd4')
        if cd4 is None:
            return _resultado(
                DADOS_INSUFICIENTES,
                'Vacina de vírus vivo atenuado em pessoa vivendo com HIV: informe a contagem '
                'recente de LT-CD4+ para avaliar a indicação.',
                REF_CRIE,
            )
        if cd4 < CD4_MINIMO_ATENUADAS:
            return _resultado(
                CONTRAINDICADA,
                f'Vacina de vírus vivo atenuado: contraindicada em pessoa vivendo com HIV com '
                f'LT-CD4+ abaixo de {CD4_MINIMO_ATENUADAS} células/mm³.',
                REF_CRIE,
            )
        if cd4 >= CD4_IMUNOSSUPRESSAO_LEVE:
            return _resultado(
                PRECAUCAO,
                f'Vacina de vírus vivo atenuado em pessoa vivendo com HIV com LT-CD4+ a partir de '
                f'{CD4_IMUNOSSUPRESSAO_LEVE} células/mm³: a SBIm considera imunossupressão leve ou ausente e a '
                f'vacina pode ser feita; fica fora da lista automática para o médico confirmar.',
                REF_ESPECIAIS + ' / ' + REF_CRIE,
            )
        return _resultado(
            PRECAUCAO,
            f'Vacina de vírus vivo atenuado em pessoa vivendo com HIV com LT-CD4+ a partir de '
            f'{CD4_MINIMO_ATENUADAS} células/mm³: indicação individualizada, conforme a faixa de '
            f'CD4 e a situação clínica.',
            REF_CRIE,
        )

    # 3. Outras causas de imunossupressão
    if imunossupressao == SIM:
        return _resultado(
            CONTRAINDICADA,
            'Vacina de vírus vivo atenuado: contraindicada em imunossupressão. Exceções dependem '
            'do grau de imunossupressão e devem ser avaliadas caso a caso.',
            REF_CRIE,
        )

    # 4. Amamentação
    if tipo == FEBRE_AMARELA and lactante == LACTANTE_MENOR_6M:
        return _resultado(
            CONTRAINDICADA,
            'Febre amarela: contraindicada em nutrizes até a criança completar 6 meses. Se a '
            'vacinação for inevitável, suspender o aleitamento por 10 dias.',
            REF_MS_FA,
        )
    if tipo == DENGUE and lactante in (LACTANTE_MENOR_6M, LACTANTE_6M_OU_MAIS):
        return _resultado(
            CONTRAINDICADA,
            'Dengue: contraindicada durante a amamentação.',
            REF_SBIM,
        )

    # 5. Medicações que a triagem não capta sozinha. Na dúvida, o item sai da lista automática.
    classes = set(contexto.get('classes') or ())
    if CORTICOIDE_DOSE_DESCONHECIDA in classes:
        return _resultado(
            DADOS_INSUFICIENTES,
            'Corticoide sistêmico sem dose e duração: informe as duas para liberar vacinas de vírus vivo '
            '(≥ 20 mg/dia de prednisona por 14 dias ou mais é imunossupressão; só 1 mês depois de suspender).',
            REF_ESPECIAIS + ' / IDSA 2013',
        )
    if IMUNOSSUPRESSAO_BAIXO_GRAU in classes:
        if tipo == DENGUE:
            return _resultado(
                CONTRAINDICADA,
                'Dengue: contraindicada em qualquer terapia imunossupressora, inclusive a de baixo grau.',
                REF_DENGUE_IMUNO,
            )
        return _resultado(
            PRECAUCAO,
            'Imunossupressão de baixo grau (metotrexato ≤ 0,4 mg/kg/semana ou azatioprina ≤ 3 mg/kg/dia): avaliar '
            'caso a caso. A SBIm pede 1 a 3 meses sem metotrexato e 3 meses sem azatioprina antes de vacina viva.',
            REF_ESPECIAIS + ' / IDSA 2013',
        )
    if TRATAMENTO_ONCOLOGICO in classes:
        return _resultado(
            PRECAUCAO,
            'Vacina de vírus vivo atenuado durante o tratamento sistêmico do câncer: decidir com a equipe de oncologia. '
            'O ideal é aplicar 3 a 4 semanas antes de iniciar o tratamento (mínimo de 15 dias).',
            REF_ESPECIAIS + ' / IDSA 2013',
        )

    # 6. Triagem incompleta: desconhecido não é "não"
    faltam = []
    if gestante == DESCONHECIDO:
        faltam.append('gestação')
    if lactante == DESCONHECIDO and tipo in (FEBRE_AMARELA, DENGUE, ATENUADA_NAO_CLASSIFICADA):
        faltam.append('amamentação')
    if imunossupressao == DESCONHECIDO:
        faltam.append('imunossupressão')
    if faltam:
        return _resultado(
            DADOS_INSUFICIENTES,
            'Vacina de vírus vivo atenuado: responda à triagem de segurança ('
            + ', '.join(faltam) + ') para avaliar a indicação.',
            REF_SBIM,
        )

    # 7. Febre amarela a partir dos 60 anos
    idade = contexto.get('idade')
    if tipo == FEBRE_AMARELA and idade is not None and idade >= IDADE_PRECAUCAO_FEBRE_AMARELA:
        return _resultado(
            PRECAUCAO,
            f'Febre amarela a partir de {IDADE_PRECAUCAO_FEBRE_AMARELA} anos em pessoa não '
            f'vacinada: avaliar risco-benefício antes de indicar.',
            REF_MS_FA,
        )

    return None


def aplicar_triagem_vacinas(recomendacoes, triagem, contexto):
    """Separa as recomendações em mantidas e não incluídas.

    Só itens de categoria ``vacina`` são avaliados. Devolve `(mantidas, nao_incluidas)`;
    cada item de `nao_incluidas` tem `titulo`, `categoria`, `estado`, `motivo` e `referencia`.
    """
    mantidas = []
    nao_incluidas = []
    for rec in recomendacoes or []:
        if not isinstance(rec, dict) or (rec.get('categoria') or '').lower() != 'vacina':
            mantidas.append(rec)
            continue
        tipo = classificar_vacina(rec.get('titulo'), rec.get('viva_atenuada'))
        resultado = avaliar_vacina(tipo, triagem, contexto) if tipo else None
        if resultado is None:
            mantidas.append(rec)
        else:
            nao_incluidas.append({
                'titulo': rec.get('titulo') or 'Vacina',
                'categoria': 'vacina',
                **resultado,
            })
    return mantidas, nao_incluidas
