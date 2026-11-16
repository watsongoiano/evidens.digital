"""Comunicados aos usuários (e-mail único por conta e por comunicado), enviados a partir de uma data.

O envio sai pelo cron da Vercel (vercel.json → /api/cron/comunicados, protegido por CRON_SECRET) ou pelo botão
do painel do administrador. Cada conta recebe cada comunicado uma vez só: a marca é feita antes do envio e
desfeita só quando a Resend recusa o lote. Se o resultado é incerto (rede caiu, tempo esgotado, erro 5xx), a marca
fica: é melhor alguém não receber o comunicado do que receber duas vezes (src/utils/contas.py: comunicados_enviados).
"""
from datetime import datetime, timezone

from src.utils import notificacoes

# Chave → (a partir de quando pode sair, em UTC; função que monta (assunto, texto) para um usuário)
COMUNICADOS = {
    # 17/11/2026, 07:00 em Brasília (UTC-3)
    'novidades-2026-11': (datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc), notificacoes.mensagem_de_novidades),
}
LOTE = 100   # limite do envio em lote da Resend


def devidos(agora=None):
    """Chaves dos comunicados cuja hora já chegou."""
    agora = agora or datetime.now(timezone.utc)
    return [chave for chave, (quando, _) in COMUNICADOS.items() if agora >= quando]


def enviar(chave, url_site, contas):
    """Envia o comunicado a um lote de contas que ainda não o receberam. Devolve (enviados, falha, restantes)."""
    _, montar = COMUNICADOS[chave]
    pendentes = contas.sem_comunicado(chave, LOTE)
    reservadas = [c for c in pendentes if contas.reservar_comunicado(c['id'], chave)]
    if not reservadas:
        return 0, None, len(contas.sem_comunicado(chave))
    mensagens = [(c['email'],) + montar(c, url_site) for c in reservadas]
    ok, detalhe, incerto = notificacoes.enviar_lote(mensagens)
    if not ok and incerto:
        return 0, f'{detalhe}: resultado incerto; as {len(reservadas)} contas do lote ficam marcadas para não receber duas vezes', \
            len(contas.sem_comunicado(chave))
    if not ok:
        for c in reservadas:
            contas.liberar_comunicado(c['id'], chave)
        return 0, detalhe, len(contas.sem_comunicado(chave))
    return len(reservadas), None, len(contas.sem_comunicado(chave))
