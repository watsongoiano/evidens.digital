"""Uso do sistema: o que alimenta o painel /analytics.

Grava um evento por ação (quem, o quê, quando) na mesma base das contas. Nenhum dado de paciente
é gravado: só o id do usuário (ou nada, para a página inicial), o tipo do evento e a hora.

Antes, os contadores ficavam num arquivo JSON na pasta temporária do servidor. Na Vercel cada
instância tem a sua pasta, apagada quando a instância é reciclada: os números zeravam e não havia
nada por usuário.

Registrar nunca derruba a requisição: se o banco falhar, o evento se perde e a página segue.
"""
import time
from datetime import datetime, timedelta, timezone

from src.utils import contas

FUSO = timezone(timedelta(hours=-3))      # Brasília (sem horário de verão desde 2019)

TIPOS = {
    'visita': 'Visitas à página inicial',
    'acesso': 'Acessos ao check-up',
    'login': 'Entradas na conta',
    'checkup': 'Check-ups gerados',
    'pdf_laboratorio': 'Pedidos de laboratório',
    'pdf_imagem': 'Pedidos de imagem',
    'pdf_vacinas': 'Receitas de vacinas',
    'guia_plano': 'Guias do plano de saúde',
}
POR_CATEGORIA_DE_PDF = {'laboratorio': 'pdf_laboratorio', 'imagem': 'pdf_imagem', 'vacina': 'pdf_vacinas'}

_ROBOS = ('bot', 'crawl', 'spider', 'slurp', 'facebookexternalhit', 'whatsapp', 'preview', 'headless',
          'lighthouse', 'monitor', 'vercel', 'curl', 'python-requests', 'wget')


def eh_robo(user_agent):
    ua = (user_agent or '').lower()
    return not ua or any(marca in ua for marca in _ROBOS)


def registrar(tipo, usuario=None, quando=None):
    """Grava um evento. `usuario` é o dict da conta (ou None). Nunca levanta exceção."""
    if tipo not in TIPOS:
        return
    try:
        uid = usuario.get('id') if isinstance(usuario, dict) else None
        with contas._conexao() as executar:
            executar('INSERT INTO eventos_uso (usuario_id, tipo, criado_em) VALUES (?, ?, ?)',
                     (uid, tipo, int(quando if quando is not None else time.time())))
    except Exception as erro:              # noqa: BLE001 — o uso nunca pode quebrar o atendimento
        print(f'[uso] evento {tipo} não registrado: {type(erro).__name__}')


def _inicio_do_dia(agora):
    return int(datetime(agora.year, agora.month, agora.day, tzinfo=FUSO).timestamp())


def resumo(agora=None, dias=30):
    """Números do painel: totais por período, série diária e uma linha por usuário."""
    agora = agora or datetime.now(FUSO)
    hoje = _inicio_do_dia(agora)
    inicio_mes = int(datetime(agora.year, agora.month, 1, tzinfo=FUSO).timestamp())
    inicio_serie = hoje - (dias - 1) * 86400
    vazio = lambda: {t: 0 for t in TIPOS}   # noqa: E731
    periodos = {'hoje': vazio(), 'sete_dias': vazio(), 'mes': vazio(), 'total': vazio()}
    serie = {(datetime.fromtimestamp(inicio_serie + i * 86400, FUSO)).strftime('%Y-%m-%d'): vazio() for i in range(dias)}
    with contas._conexao() as executar:
        for tipo, total in executar('SELECT tipo, COUNT(*) FROM eventos_uso GROUP BY tipo').fetchall():
            if tipo in TIPOS:
                periodos['total'][tipo] = int(total)
        recentes = executar('SELECT tipo, criado_em FROM eventos_uso WHERE criado_em >= ?',
                            (min(inicio_serie, inicio_mes),)).fetchall()
        por_usuario = executar('SELECT usuario_id, tipo, COUNT(*), MAX(criado_em) FROM eventos_uso '
                               'WHERE usuario_id IS NOT NULL GROUP BY usuario_id, tipo').fetchall()
        recentes_por_usuario = executar('SELECT usuario_id, tipo, COUNT(*) FROM eventos_uso '
                                        'WHERE usuario_id IS NOT NULL AND criado_em >= ? GROUP BY usuario_id, tipo',
                                        (inicio_serie,)).fetchall()
    usuarios = {u['id']: u for u in contas.listar()}
    sete = hoje - 6 * 86400
    for tipo, quando in recentes:
        if tipo not in TIPOS:
            continue
        quando = int(quando)
        if quando >= hoje:
            periodos['hoje'][tipo] += 1
        if quando >= sete:
            periodos['sete_dias'][tipo] += 1
        if quando >= inicio_mes:
            periodos['mes'][tipo] += 1
        dia = datetime.fromtimestamp(quando, FUSO).strftime('%Y-%m-%d')
        if dia in serie:
            serie[dia][tipo] += 1

    linhas = {}
    for uid, tipo, total, ultimo in por_usuario:
        if tipo not in TIPOS:
            continue
        u = usuarios.get(uid)
        linha = linhas.setdefault(uid, {
            'id': uid, 'nome': u['nome'] if u else 'Conta removida', 'email': u['email'] if u else '',
            'perfil': u['perfil'] if u else '', 'total': vazio(), 'ultimos_30_dias': vazio(), 'ultima_atividade': 0})
        linha['total'][tipo] = int(total)
        linha['ultima_atividade'] = max(linha['ultima_atividade'], int(ultimo))
    for uid, tipo, total in recentes_por_usuario:
        if uid in linhas and tipo in TIPOS:
            linhas[uid]['ultimos_30_dias'][tipo] = int(total)
    ordem = sorted(linhas.values(), key=lambda l: (-l['ultima_atividade'], l['nome'].lower()))
    for linha in ordem:
        linha['ultima_atividade'] = datetime.fromtimestamp(linha['ultima_atividade'], FUSO).isoformat()
    ativos = {janela: sum(1 for l in ordem if any(l[chave].values()))
              for janela, chave in (('ultimos_30_dias', 'ultimos_30_dias'), ('total', 'total'))}
    return {
        'tipos': TIPOS,
        'periodos': periodos,
        'serie': [{'dia': dia, **valores} for dia, valores in serie.items()],
        'usuarios': ordem,
        'usuarios_ativos': ativos,
        'gerado_em': agora.isoformat(),
    }
