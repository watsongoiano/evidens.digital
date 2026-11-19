"""Rotas do cadastro de pacientes (src/utils/pacientes.py; docs/pacientes.md).

Por enquanto só o administrador usa, e não há tela: o cadastro está no ar para ser testado antes de abrir.
Cada paciente pertence à conta que o cadastrou; o registro de outra conta responde 404, também para o
administrador. As respostas de erro trazem só frases fixas, nunca o que foi enviado.
"""
from functools import wraps

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from src.routes.auth import disponivel, exigir_administrador, exigir_login, origem_confiavel, usuario_atual
from src.utils import pacientes

pacientes_bp = Blueprint('pacientes', __name__)

# A ficha clínica vai até 64 KB; o resto do cadastro é pequeno.
TAMANHO_MAXIMO_DO_ENVIO = 128 * 1024

MSG_NAO_ENCONTRADO = 'Paciente não encontrado.'


def exigir_cadastro(funcao):
    """Porta única das rotas do cadastro de pacientes.

    Quem pode usar é decidido em `pacientes.habilitado_para`. Hoje essa regra só aceita o administrador, então todo
    pedido passa por `exigir_administrador`. No dia em que a regra aceitar outras contas, elas entram por
    `exigir_login` (as mesmas conferências, menos a de administrador), sem mexer nas rotas.
    """
    @wraps(funcao)
    def conferida(*args, **kwargs):
        if not pacientes.habilitado_para(usuario_atual()):
            return jsonify({'error': 'O cadastro de pacientes não está disponível para esta conta.'}), 403
        return funcao(*args, **kwargs)

    so_administrador, com_login = exigir_administrador(conferida), exigir_login(conferida)

    @wraps(funcao)
    def protegida(*args, **kwargs):
        u = usuario_atual() if disponivel() else None
        aberto_para_a_conta = u is not None and not u['administrador'] and pacientes.habilitado_para(u)
        return (com_login if aberto_para_a_conta else so_administrador)(*args, **kwargs)
    return protegida


@pacientes_bp.before_request
def _so_do_proprio_site():
    """Nenhum pedido vindo de outro site, nem de leitura: a resposta leva dado de paciente e cada leitura entra na
    trilha de acessos."""
    if not origem_confiavel():
        return jsonify({'error': 'Requisição recusada: origem não reconhecida.'}), 403


@pacientes_bp.after_request
def _sem_cache(resposta):
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@pacientes_bp.errorhandler(pacientes.DadosInvalidos)
def _dados_invalidos(erro):
    return jsonify({'error': 'Confira os dados informados.', 'erros': erro.erros, 'campos': erro.campos}), 400


@pacientes_bp.errorhandler(pacientes.Duplicado)
def _duplicado(erro):
    nome = {'cns': 'CNS', 'cpf': 'CPF'}[erro.campo]
    return jsonify({'error': f'Já existe um paciente com este {nome} no seu cadastro.', 'codigo': 'duplicado',
                    'campo': erro.campo, 'paciente_id': erro.paciente_id}), 409


@pacientes_bp.errorhandler(pacientes.CadastroIndisponivel)
def _sem_chave(erro):
    return jsonify({'error': pacientes.MSG_SEM_CHAVE, 'codigo': 'sem_chave'}), 503


@pacientes_bp.errorhandler(pacientes.RegistroIlegivel)
def _ilegivel(erro):
    return jsonify({'error': pacientes.MSG_ILEGIVEL, 'codigo': 'ilegivel'}), 500


@pacientes_bp.errorhandler(RequestEntityTooLarge)
def _envio_grande(erro):
    return jsonify({'error': f'O envio passa de {TAMANHO_MAXIMO_DO_ENVIO // 1024} KB.'}), 413


def _corpo():
    """O JSON enviado, ou None (a validação responde o que falta)."""
    request.max_content_length = TAMANHO_MAXIMO_DO_ENVIO
    return request.get_json(silent=True)


def _dono():
    return usuario_atual()['id']


@pacientes_bp.route('/pacientes')
@exigir_cadastro
def pacientes_listar():
    """Lista da conta; `?busca=` filtra por parte do nome ou pelo final do CNS.

    O termo na URL fica nos registros de acesso da hospedagem: a tela deve preferir `POST /api/pacientes/buscar`."""
    return jsonify(pacientes.listar(_dono(), request.args.get('busca', '')))


@pacientes_bp.route('/pacientes/buscar', methods=['POST'])
@exigir_cadastro
def pacientes_buscar():
    """A mesma lista, com o termo no corpo ({busca}) para ele não aparecer na URL."""
    corpo = _corpo()
    busca = corpo.get('busca') if isinstance(corpo, dict) else ''
    return jsonify(pacientes.listar(_dono(), busca if isinstance(busca, str) else ''))


@pacientes_bp.route('/pacientes', methods=['POST'])
@exigir_cadastro
def pacientes_criar():
    novo = pacientes.criar(_dono(), _corpo())
    return jsonify({'ok': True, 'paciente': novo, 'mensagem': 'Paciente salvo.'}), 201


@pacientes_bp.route('/pacientes/<int:pid>')
@exigir_cadastro
def pacientes_ver(pid):
    paciente = pacientes.ler(_dono(), pid)
    if paciente is None:
        return jsonify({'error': MSG_NAO_ENCONTRADO}), 404
    return jsonify({'paciente': paciente})


@pacientes_bp.route('/pacientes/<int:pid>', methods=['POST'])
@exigir_cadastro
def pacientes_atualizar(pid):
    """Troca os campos enviados e mantém os demais; '' ou null apaga o campo."""
    paciente = pacientes.atualizar(_dono(), pid, _corpo())
    if paciente is None:
        return jsonify({'error': MSG_NAO_ENCONTRADO}), 404
    return jsonify({'ok': True, 'paciente': paciente, 'mensagem': 'Paciente salvo.'})


@pacientes_bp.route('/pacientes/<int:pid>/excluir', methods=['POST'])
@exigir_cadastro
def pacientes_excluir(pid):
    if not pacientes.excluir(_dono(), pid):
        return jsonify({'error': MSG_NAO_ENCONTRADO}), 404
    return jsonify({'ok': True})


@pacientes_bp.route('/pacientes/<int:pid>/exportar')
@exigir_cadastro
def pacientes_exportar(pid):
    """Tudo o que há guardado do paciente, em JSON para baixar. O nome do arquivo não leva o nome do paciente."""
    dados = pacientes.exportar(_dono(), pid)
    if dados is None:
        return jsonify({'error': MSG_NAO_ENCONTRADO}), 404
    resposta = jsonify(dados)
    resposta.headers['Content-Disposition'] = f'attachment; filename="paciente-{pid}.json"'
    return resposta
