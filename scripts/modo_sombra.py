"""Modo sombra da conta de operadora: classifica pedidos de exame, sem barrar nada.

Uso:
  python scripts/modo_sombra.py pedidos.csv [resultado.csv]
  python scripts/modo_sombra.py --laudos laudo1.pdf laudo2.pdf [--saida resultado.csv] [--regime internado]
                                [--carater eletivo] [--finalidade rastreio] [--cid Z00.0] [--idade 52 --sexo M]

O arquivo CSV tem uma linha por exame pedido (colunas em docs/operadoras-modo-sombra.md). Com --laudos, cada exame
identificado no laudo em PDF vira um pedido: o nome do arquivo é o identificador do beneficiário (não use o nome do
paciente), a data da coleta é a data do pedido, e o sexo, a idade e o regime (setor de internação ou de
pronto-socorro) saem do cabeçalho do laudo. O resultado repete as colunas da entrada e acrescenta a cor, o motivo e a
referência. O resumo sai na tela.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import laudos, operadora  # noqa: E402

ROTULOS = {'verde': 'Liberaria', 'amarelo': 'Pediria esclarecimento', 'vermelho': 'Barraria',
           'fora_do_escopo': 'Fora do escopo (urgência, internado ou exame que não é de laboratório)'}


def _reais(valor):
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _ler(arquivo):
    """Texto do arquivo: UTF-8 ou, se não for, Windows-1252 (o que o Excel grava no Brasil)."""
    dados = arquivo.read_bytes()
    try:
        return dados.decode('utf-8-sig')
    except UnicodeDecodeError:
        return dados.decode('cp1252')


def _dos_laudos(opcoes):
    """Pedidos tirados dos laudos em PDF. Devolve (linhas, falhas); falha de leitura não derruba os demais."""
    linhas, falhas = [], 0
    for caminho in opcoes.laudos:
        arquivo = Path(caminho)
        try:
            pedidos, soltos = operadora.pedidos_do_laudo(
                arquivo.read_bytes(), arquivo.stem, idade=opcoes.idade, sexo=opcoes.sexo, carater=opcoes.carater,
                regime=opcoes.regime, finalidade=opcoes.finalidade, cid=opcoes.cid)
        except (OSError, ValueError, laudos.LaudoIlegivel) as erro:
            print(f'  {arquivo.name}: não lido ({erro}).')
            falhas += 1
            continue
        linhas += pedidos
        regime = pedidos[0]['regime'] if pedidos else ''
        print(f'  {arquivo.name}: {len(pedidos)} exames identificados' + (f', regime {regime}' if regime else '')
              + (f'; não identificados: {", ".join(soltos)}' if soltos else '') + '.')
    return linhas, falhas


def principal(argumentos):
    leitor = argparse.ArgumentParser(description='Modo sombra do Evidēns: classifica pedidos de exame, sem barrar nada.')
    leitor.add_argument('arquivos', nargs='*', help='pedidos.csv [resultado.csv]')
    leitor.add_argument('--laudos', nargs='+', metavar='PDF', help='laudos em PDF, no lugar do arquivo de pedidos')
    leitor.add_argument('--saida', help='arquivo de resultado (com --laudos)')
    leitor.add_argument('--carater', default='eletivo')
    leitor.add_argument('--regime', help='sem ele, vale o setor do laudo (internação, pronto-socorro) ou ambulatorial')
    leitor.add_argument('--finalidade', default='')
    leitor.add_argument('--cid', default='')
    leitor.add_argument('--idade', type=int)
    leitor.add_argument('--sexo')
    try:
        opcoes = leitor.parse_args(argumentos)
    except SystemExit:
        return 2
    if opcoes.laudos:
        if opcoes.arquivos:
            print('Use o arquivo de pedidos ou --laudos, não os dois.')
            return 2
        saida = Path(opcoes.saida) if opcoes.saida else Path(opcoes.laudos[0]).with_name('laudos_classificado.csv')
        print('Laudos lidos:')
        brutas, falhas = _dos_laudos(opcoes)
        if falhas and not brutas:
            return 2
    else:
        if len(opcoes.arquivos) not in (1, 2):
            print(__doc__)
            return 2
        entrada = Path(opcoes.arquivos[0])
        saida = Path(opcoes.arquivos[1]) if len(opcoes.arquivos) == 2 else entrada.with_name(entrada.stem + '_classificado.csv')
        if not entrada.is_file():
            print(f'Arquivo não encontrado: {entrada}')
            return 2
        if saida.resolve() == entrada.resolve():
            print('O arquivo de resultado não pode ser o próprio arquivo de entrada.')
            return 2
        brutas = operadora.ler_csv(_ler(entrada))
    resultados, resumo = operadora.classificar_lote(brutas)
    saida.write_text(operadora.escrever_csv(brutas, resultados), encoding='utf-8')

    validas = resumo['linhas'] - resumo['invalidas']
    print(f'Modo sombra do Evidēns, versão {resumo["versao"]}: nada foi barrado; este é o retrato do que seria.')
    print(f'Linhas lidas: {resumo["linhas"]}. Com erro de preenchimento: {resumo["invalidas"]}.')
    for cor, rotulo in ROTULOS.items():
        n = resumo['por_cor'].get(cor, 0)
        parte = f' ({100 * n / validas:.1f}%)'.replace('.', ',') if validas else ''
        valor = resumo['valor_por_cor'].get(cor)
        print(f'  {rotulo}: {n}{parte}' + (f' · {_reais(valor)}' if valor else ''))
    for cor, grupo in (('amarelo', 'Pedidos de esclarecimento'), ('vermelho', 'Pedidos que seriam barrados')):
        presumidas = resumo['origem_da_finalidade'].get(cor, {}).get('presumida', 0)
        if presumidas:
            print(f'  {grupo} que dependem de presumir rastreio (pedido sem finalidade nem CID): {presumidas}.')
    if resumo['mais_barrados']:
        print('Exames mais barrados:')
        for exame, n in resumo['mais_barrados']:
            print(f'  {n:>6}  {exame}')
    print('Motivos:', ', '.join(f'{k} {v}' for k, v in sorted(resumo['por_motivo'].items(), key=lambda par: (-par[1], par[0]))))
    print(f'Resultado em {saida}')
    if not validas:
        print('Nenhuma linha válida: confira o cabeçalho, o separador e a codificação do arquivo.')
        return 1
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')      # terminal sem UTF-8 não derruba o resumo
    sys.exit(principal(sys.argv[1:]))
