"""Modo sombra da conta de operadora: classifica um arquivo de pedidos de exame, sem barrar nada.

Uso:  python scripts/modo_sombra.py pedidos.csv [resultado.csv]

O arquivo de entrada tem uma linha por exame pedido (colunas em docs/operadoras-modo-sombra.md). O resultado repete
as colunas da entrada e acrescenta a cor, o motivo e a referência. O resumo sai na tela.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import operadora  # noqa: E402

ROTULOS = {'verde': 'Liberaria', 'amarelo': 'Pediria esclarecimento', 'vermelho': 'Barraria',
           'fora_do_escopo': 'Fora do escopo (urgência ou internado)'}


def principal(argumentos):
    if len(argumentos) not in (1, 2):
        print(__doc__)
        return 2
    entrada = Path(argumentos[0])
    saida = Path(argumentos[1]) if len(argumentos) == 2 else entrada.with_name(entrada.stem + '_classificado.csv')
    brutas = operadora.ler_csv(entrada.read_text(encoding='utf-8'))
    resultados, resumo = operadora.classificar_lote(brutas)
    saida.write_text(operadora.escrever_csv(brutas, resultados), encoding='utf-8')

    validas = resumo['linhas'] - resumo['invalidas']
    print(f'Modo sombra do Evidēns, versão {resumo["versao"]}: nada foi barrado; este é o retrato do que seria.')
    print(f'{resumo["linhas"]} linhas lidas, {resumo["invalidas"]} com erro de preenchimento.')
    for cor, rotulo in ROTULOS.items():
        n = resumo['por_cor'].get(cor, 0)
        parte = f' ({100 * n / validas:.1f}%)' if validas else ''
        valor = resumo['valor_por_cor'].get(cor)
        print(f'  {rotulo}: {n}{parte}' + (f' · R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') if valor else ''))
    for cor, grupo in (('amarelo', 'pedidos de esclarecimento'), ('vermelho', 'que seriam barrados')):
        presumidas = resumo['origem_da_finalidade'].get(cor, {}).get('presumida', 0)
        if presumidas:
            print(f'  Dos {grupo}, {presumidas} dependem de presumir rastreio (pedido sem finalidade nem CID).')
    if resumo['mais_barrados']:
        print('Exames mais barrados:')
        for exame, n in resumo['mais_barrados']:
            print(f'  {n:>6}  {exame}')
    print('Motivos:', ', '.join(f'{k} {v}' for k, v in sorted(resumo['por_motivo'].items(), key=lambda par: -par[1])))
    print(f'Resultado em {saida}')
    return 0


if __name__ == '__main__':
    sys.exit(principal(sys.argv[1:]))
