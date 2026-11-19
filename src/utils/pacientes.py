"""Cadastro de pacientes: armazenamento cifrado, validação, posse e trilha de acessos.

É a exceção controlada à regra "nenhum dado de paciente é gravado" (docs/pacientes.md; P-10 e P-26 em
docs/registro-de-perigos.md). O check-up, o pré-operatório, os PDFs e as operadoras continuam sem gravar nada:
só as rotas de src/routes/pacientes.py chegam aqui e, por enquanto, só o administrador as usa (`habilitado_para`).

O que fica no banco (tabelas em src/utils/contas.py):

- ``pacientes.dados``: um JSON com todos os campos, cifrado (Fernet, a mesma primitiva do token da assinatura
  digital) com chave derivada de PACIENTES_CHAVE, a chave própria do cadastro (não é a SECRET_KEY, que assina a
  sessão). Nada do paciente fica em claro, nem o nome. O dono e o número do registro vão dentro do texto cifrado.
- ``pacientes.indice_cns`` e ``indice_cpf``: HMAC-SHA256 do número, com outra chave derivada de PACIENTES_CHAVE,
  só para achar duplicado na mesma conta sem guardar o número.
- ``pacientes_acessos``: quem fez o quê e quando (criar, ver, listar, editar, excluir, exportar). Sem dado de
  paciente: nem o termo da busca entra.

Toda função recebe o ``usuario_id`` do dono. O registro de outra conta se comporta como se não existisse, também
para o administrador. Nada daqui escreve em ``eventos_uso`` nem em log.
"""
import base64
import hashlib
import hmac
import json
import math
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone

from src.utils import contas
from src.utils.uso import FUSO
from src.utils.validacao import SEXOS

ACOES = ('criar', 'ver', 'listar', 'editar', 'excluir', 'exportar')

LIMITE_DA_LISTA = 500          # pacientes devolvidos por listagem ou busca
LOTE_DA_LISTA = 200            # linhas decifradas por consulta ao banco
MAX_PLANOS = 5
MAX_FICHA = 64 * 1024          # bytes da ficha clínica em JSON
MAX_PACIENTES_POR_CONTA = 5000 # a listagem decifra todos os registros da conta em memória

# Nomes que a ficha não aceita como chave: num objeto JavaScript eles alcançam o protótipo. A tela mostra os
# dados só com textContent (docs/pacientes.md).
CHAVES_RESERVADAS = frozenset({'__proto__', 'constructor', 'prototype'})

# Raça/cor: as categorias do IBGE usadas nos formulários do SUS (campo "raça/cor" do laudo de APAC).
# Guarda-se a chave; o rótulo é o que vai impresso.
RACAS = {'branca': 'Branca', 'preta': 'Preta', 'parda': 'Parda', 'amarela': 'Amarela', 'indigena': 'Indígena'}

# Tetos dos textos livres. Os que o laudo de APAC e a guia do plano também pedem têm o mesmo teto de lá
# (src/routes/checkup_intelligent.py); tests/test_pacientes.py confere que continuam iguais.
LIMITES = {'nome': 150, 'nome_social': 150, 'mae': 120, 'prontuario': 20, 'responsavel': 120, 'telefone': 20,
           'email': 254, 'endereco': 150, 'municipio': 60, 'operadora': 80, 'carteira': 30}

CAMPOS = ('nome', 'nome_social', 'nascimento', 'sexo', 'cpf', 'cns', 'mae', 'raca', 'prontuario', 'responsavel',
          'telefone', 'email', 'cep', 'endereco', 'municipio', 'ibge', 'uf', 'planos', 'ficha')
CAMPOS_DO_PLANO = ('operadora', 'carteira', 'validade')

# A chave do cadastro é uma variável de ambiente só dele, separada da SECRET_KEY (que assina o cookie de sessão):
# quem obtém a chave de sessão não abre os pacientes, e trocar a de sessão não os torna ilegíveis. Sem ela, ou com
# menos de MIN_DA_CHAVE caracteres, o cadastro fica indisponível; a SECRET_KEY nunca entra no lugar.
VARIAVEL_DA_CHAVE = 'PACIENTES_CHAVE'
MIN_DA_CHAVE = 32

# Rótulos das chaves derivadas de PACIENTES_CHAVE. O "v1" acompanha o prefixo gravado em cada registro: trocar a
# derivação ou a chave pede rótulo novo e regravação dos registros antigos.
ROTULO_DA_CIFRA = b'evidens-pacientes-v1'
ROTULO_DO_INDICE = b'evidens-pacientes-indice-v1'
VERSAO_DA_CIFRA = 'v1'

# Mesmo valor de src/routes/auth.CHAVE_PADRAO: a chave de desenvolvimento, que está no código, nunca cifra dado de
# paciente (tests/test_pacientes.py confere que os dois valores continuam iguais).
_CHAVE_DE_DESENVOLVIMENTO = 'dev-secret-key-change-in-production'

MSG_SEM_CHAVE = ('O cadastro de pacientes está desligado neste ambiente: falta a PACIENTES_CHAVE, a chave própria '
                 f'do cadastro (ao menos {MIN_DA_CHAVE} caracteres, diferente da chave de sessão). Nada foi gravado.')
MSG_ILEGIVEL = ('Este registro não pôde ser aberto com a chave atual do ambiente (PACIENTES_CHAVE). '
                'Nenhum dado foi alterado.')
MSG_CONFLITO = ('Este paciente foi alterado em outro lugar depois de aberto. Nada foi gravado: '
                'abra o registro de novo e repita a alteração.')


class CadastroIndisponivel(Exception):
    """Não há PACIENTES_CHAVE utilizável no ambiente: sem ela nada é cifrado, gravado nem aberto."""

    def __init__(self):
        super().__init__(MSG_SEM_CHAVE)


class DadosInvalidos(contas.DadosInvalidos):
    """`erros` são frases fixas (nunca repetem o que foi digitado); `campos`, os campos a corrigir."""

    def __init__(self, erros, campos=()):
        super().__init__(erros)
        self.campos = list(campos)


class Duplicado(Exception):
    """A conta já tem um paciente com este CNS ou CPF. `paciente_id` é o registro que já existe."""

    def __init__(self, campo, paciente_id):
        super().__init__(f'{campo} já cadastrado nesta conta')
        self.campo, self.paciente_id = campo, int(paciente_id)


class LimiteDaConta(Exception):
    """A conta já tem `MAX_PACIENTES_POR_CONTA` pacientes: nada foi gravado."""

    def __init__(self, limite):
        super().__init__(f"O limite é de {f'{limite:,}'.replace(',', '.')} pacientes por conta. Nada foi gravado: "
                         'exclua registros que não usa mais para cadastrar outros.')
        self.limite = int(limite)


class EdicaoSimultanea(Exception):
    """O registro mudou entre a leitura e a gravação desta edição: nada foi gravado."""

    def __init__(self):
        super().__init__(MSG_CONFLITO)


class RegistroIlegivel(Exception):
    """O registro não abre com a chave atual, ou não é da conta ou do número gravados na linha."""

    def __init__(self):
        super().__init__(MSG_ILEGIVEL)


def habilitado_para(usuario):
    """Quem pode usar o cadastro de pacientes. É a única regra: as rotas perguntam aqui.

    Hoje, só o administrador. Abrir a outras contas é trocar a linha abaixo, e só depois do que
    docs/pacientes.md lista (nova versão dos Termos, textos da home e do cadastro, política de retenção).
    """
    return bool(usuario) and bool(usuario.get('administrador'))


# ── Chaves, cifra e índice ───────────────────────────────────────────────────

def _chave(rotulo):
    segredo = (os.environ.get(VARIAVEL_DA_CHAVE) or '').strip()
    # A chave de sessão é lida só para recusar o mesmo valor: as duas têm de ser diferentes.
    de_sessao = (os.environ.get('SECRET_KEY') or '').strip()
    if len(segredo) < MIN_DA_CHAVE or segredo in (_CHAVE_DE_DESENVOLVIMENTO, de_sessao):
        raise CadastroIndisponivel()
    return hmac.new(segredo.encode(), rotulo, hashlib.sha256).digest()


def _cofre():
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(_chave(ROTULO_DA_CIFRA)))


def _cifrar(cofre, usuario_id, paciente_id, campos):
    # O dono e o número do registro vão dentro do texto cifrado: uma linha copiada para outra conta, ou um texto
    # cifrado trocado de linha, direto no banco, não abre.
    claro = json.dumps({'dono': int(usuario_id), 'id': int(paciente_id), 'campos': campos}, ensure_ascii=False,
                       separators=(',', ':'), allow_nan=False)
    return VERSAO_DA_CIFRA + ':' + cofre.encrypt(claro.encode()).decode()


def _decifrar(cofre, usuario_id, paciente_id, cifrado):
    from cryptography.fernet import InvalidToken
    versao, _, corpo = str(cifrado or '').partition(':')
    if versao != VERSAO_DA_CIFRA:
        raise RegistroIlegivel()
    try:
        envelope = json.loads(cofre.decrypt(corpo.encode()))
    except (InvalidToken, ValueError):
        raise RegistroIlegivel() from None
    if not isinstance(envelope, dict) or envelope.get('dono') != int(usuario_id) \
            or envelope.get('id') != int(paciente_id) or not isinstance(envelope.get('campos'), dict):
        raise RegistroIlegivel()
    return envelope['campos']


def _indice(usuario_id, campo, numero):
    """HMAC do número (já só com dígitos), por conta: o mesmo CNS em duas contas dá índices diferentes."""
    if not numero:
        return None
    return hmac.new(_chave(ROTULO_DO_INDICE), f'{int(usuario_id)}:{campo}:{numero}'.encode(), hashlib.sha256).hexdigest()


# ── Validação ────────────────────────────────────────────────────────────────

class _Recusa(Exception):
    pass


def cpf_valido(cpf):
    """CPF: 11 dígitos, não todos iguais, com os dois dígitos verificadores (módulo 11) corretos."""
    d = re.sub(r'[^0-9]', '', cpf if isinstance(cpf, str) else '')
    if len(d) != 11 or d == d[0] * 11:
        return False
    return all(sum(int(d[i]) * (n + 1 - i) for i in range(n)) * 10 % 11 % 10 == int(d[n]) for n in (9, 10))


def _em_branco(valor):
    return valor is None or valor == [] or valor == {} or (isinstance(valor, str) and not valor.strip())


def _sem_acento(texto):
    decomposto = unicodedata.normalize('NFKD', str(texto or ''))
    return ''.join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def _linha(valor, maximo, rotulo):
    if not isinstance(valor, str):
        raise _Recusa(f'{rotulo}: envie como texto.')
    texto = contas._limpo(valor, maximo + 1)
    if len(texto) > maximo:
        raise _Recusa(f'{rotulo}: no máximo {maximo} caracteres.')
    return texto


def _digitos(valor):
    """Só os algarismos de um número digitado com ou sem pontuação; '' se não for texto curto."""
    if not isinstance(valor, str) or len(valor) > 40:
        return ''
    return re.sub(r'[^0-9]', '', valor)


def _hoje():
    # O dia de hoje no horário de Brasília, como no resto do sistema (uso.FUSO, periodicidade.FUSO_BRASILIA).
    return datetime.now(FUSO).date()


def _ler_nome(valor):
    texto = _linha(valor, LIMITES['nome'], 'Nome')
    if len(texto) < 2:
        raise _Recusa('Informe o nome do paciente.')
    return texto


def _ler_nascimento(valor):
    mensagem = 'Confira a data de nascimento (AAAA-MM-DD): não pode ser futura.'
    if not isinstance(valor, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', valor.strip()):
        raise _Recusa(mensagem)
    try:
        nascimento = date.fromisoformat(valor.strip())
    except ValueError:
        raise _Recusa(mensagem) from None
    if nascimento.year < 1900 or nascimento > _hoje():
        raise _Recusa(mensagem)
    return nascimento.isoformat()


def _ler_sexo(valor):
    sexo = valor.strip().lower() if isinstance(valor, str) else None
    if sexo not in SEXOS:
        raise _Recusa('Sexo: masculino ou feminino.')
    return sexo


def _ler_cpf(valor):
    cpf = _digitos(valor)
    if not cpf_valido(cpf):
        raise _Recusa('Confira o CPF: 11 dígitos válidos.')
    return cpf


def _ler_cns(valor):
    cns = _digitos(valor)
    if not contas.cns_valido(cns):
        raise _Recusa('Confira o CNS do paciente: 15 dígitos válidos.')
    return cns


def _ler_raca(valor):
    raca = _sem_acento(valor).strip() if isinstance(valor, str) else None
    if raca not in RACAS:
        raise _Recusa('Raça/cor: branca, preta, parda, amarela ou indígena.')
    return raca


def _ler_email(valor):
    email = contas.normalizar_email(valor if isinstance(valor, str) else '')
    # O tamanho vem antes da expressão regular (custo quadrático em texto longo). Caractere de controle, invisível
    # ou substituto solto é recusado: `_limpo` os troca por espaço, e aí o texto deixa de ser igual ao enviado.
    if len(email) > LIMITES['email'] or contas._limpo(email, LIMITES['email']) != email or not contas._EMAIL.match(email):
        raise _Recusa('Informe um e-mail válido.')
    return email


def _ler_cep(valor):
    cep = _digitos(valor)
    if len(cep) != 8:
        raise _Recusa('O CEP tem 8 dígitos.')
    return cep


def _ler_ibge(valor):
    ibge = _digitos(valor)
    if len(ibge) != 7:
        raise _Recusa('O código IBGE do município tem 7 dígitos.')
    return ibge


def _ler_uf(valor):
    uf = valor.strip().upper() if isinstance(valor, str) else None
    if uf not in contas.UFS:
        raise _Recusa('Confira a UF: a sigla do estado, com duas letras.')
    return uf


def _ler_validade(valor):
    mensagem = 'Validade do plano: AAAA-MM ou AAAA-MM-DD.'
    if not isinstance(valor, str):
        raise _Recusa(mensagem)
    texto = valor.strip()
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}(-[0-9]{2})?', texto):
        raise _Recusa(mensagem)
    try:
        dia = date.fromisoformat(texto if len(texto) == 10 else texto + '-01')
    except ValueError:
        raise _Recusa(mensagem) from None
    if not 1900 <= dia.year <= 2100:
        raise _Recusa(mensagem)
    return texto


def _ler_planos(valor):
    if not isinstance(valor, list):
        raise _Recusa('Planos de saúde: envie uma lista.')
    if len(valor) > MAX_PLANOS:
        raise _Recusa(f'Cada paciente pode ter até {MAX_PLANOS} planos de saúde.')
    planos = []
    for item in valor:
        if not isinstance(item, dict) or any(chave not in CAMPOS_DO_PLANO for chave in item):
            raise _Recusa('Plano de saúde em formato inválido: use operadora, carteira e validade.')
        operadora = '' if _em_branco(item.get('operadora')) else _linha(item['operadora'], LIMITES['operadora'], 'Operadora do plano')
        if len(operadora) < 2:
            raise _Recusa('Em cada plano de saúde, informe a operadora.')
        carteira = '' if _em_branco(item.get('carteira')) else _linha(item['carteira'], LIMITES['carteira'], 'Número da carteira')
        validade = '' if _em_branco(item.get('validade')) else _ler_validade(item['validade'])
        planos.append({'operadora': operadora, 'carteira': carteira, 'validade': validade})
    return planos


def _valor_simples(valor):
    if valor is None or isinstance(valor, (bool, str)):
        return True
    if isinstance(valor, int):
        return True
    return isinstance(valor, float) and math.isfinite(valor)


def _ler_ficha(valor):
    """Ficha clínica: retrato do formulário do check-up. O servidor não interpreta; só confere a forma e o tamanho."""
    mensagem = 'Ficha clínica em formato inválido: use um objeto com textos, números ou listas simples.'
    if not isinstance(valor, dict):
        raise _Recusa(mensagem)
    for chave, item in valor.items():
        if not isinstance(chave, str) or not 0 < len(chave) <= 80:
            raise _Recusa(mensagem)
        if chave.strip() in CHAVES_RESERVADAS:
            # A ficha só tem um nível (objeto dentro de objeto é recusado logo abaixo): conferir aqui cobre todos.
            raise _Recusa('Ficha clínica: há um campo com nome reservado, que o cadastro não aceita.')
        if not (_valor_simples(item) or (isinstance(item, list) and all(_valor_simples(v) for v in item))):
            raise _Recusa(mensagem)
    try:
        tamanho = len(json.dumps(valor, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())
    except (ValueError, TypeError):
        raise _Recusa(mensagem) from None
    if tamanho > MAX_FICHA:
        raise _Recusa(f'A ficha clínica passa de {MAX_FICHA // 1024} KB.')
    return valor


def _texto_livre(campo, rotulo):
    return lambda valor: _linha(valor, LIMITES[campo], rotulo)


_LEITORES = {
    'nome': _ler_nome,
    'nome_social': _texto_livre('nome_social', 'Nome social'),
    'nascimento': _ler_nascimento,
    'sexo': _ler_sexo,
    'cpf': _ler_cpf,
    'cns': _ler_cns,
    'mae': _texto_livre('mae', 'Nome da mãe'),
    'raca': _ler_raca,
    'prontuario': _texto_livre('prontuario', 'Prontuário'),
    'responsavel': _texto_livre('responsavel', 'Responsável'),
    'telefone': _texto_livre('telefone', 'Telefone'),
    'email': _ler_email,
    'cep': _ler_cep,
    'endereco': _texto_livre('endereco', 'Endereço'),
    'municipio': _texto_livre('municipio', 'Município'),
    'ibge': _ler_ibge,
    'uf': _ler_uf,
    'planos': _ler_planos,
    'ficha': _ler_ficha,
}
assert tuple(_LEITORES) == CAMPOS


def validar(dados):
    """Devolve só os campos informados, já normalizados; levanta `DadosInvalidos` com o que corrigir.

    Campo vazio (None, '', [] ou {}) vale como não informado. Chave desconhecida é recusada. As mensagens são
    fixas e nunca repetem o que foi enviado, para a resposta de erro não levar dado de paciente.
    """
    if not isinstance(dados, dict):
        raise DadosInvalidos(['Envie os dados do paciente em JSON.'])
    erros, com_erro, limpo = [], [], {}
    if any(chave not in _LEITORES for chave in dados):
        erros.append('Há campos que o cadastro de pacientes não aceita.')
    for campo, ler in _LEITORES.items():
        valor = dados.get(campo)
        if _em_branco(valor):
            continue
        try:
            lido = ler(valor)
        except _Recusa as recusa:
            erros.append(str(recusa))
            com_erro.append(campo)
            continue
        if not _em_branco(lido):
            limpo[campo] = lido
    if 'nome' not in limpo and 'nome' not in com_erro:
        erros.append('Informe o nome do paciente.')
        com_erro.append('nome')
    if erros:
        raise DadosInvalidos(erros, com_erro)
    return limpo


# ── Banco ────────────────────────────────────────────────────────────────────

def _em_postgres():
    return not contas._eh_sqlite(contas._url())


def _id(valor):
    """Identificador que cabe na coluna (BIGINT); fora disso o registro não existe."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if 0 < numero < 2 ** 62 else None


def _registrar(executar, paciente_id, usuario_id, acao, quando=None):
    """Trilha de acessos: na mesma transação da ação. Se a trilha não grava, a ação não acontece."""
    assert acao in ACOES
    executar('INSERT INTO pacientes_acessos (paciente_id, usuario_id, acao, quando) VALUES (?, ?, ?, ?)',
             (paciente_id, int(usuario_id), acao, int(quando if quando is not None else time.time())))


def _recusar_duplicado(executar, usuario_id, indices, exceto=None):
    for campo, indice in indices.items():
        if not indice:
            continue
        linha = executar(f'SELECT id FROM pacientes WHERE usuario_id = ? AND indice_{campo} = ?',
                         (usuario_id, indice)).fetchone()
        if linha and linha[0] != exceto:
            raise Duplicado(campo, linha[0])


def _violou_unicidade(erro):
    return ('unique' in str(erro).lower() or 'IntegrityError' in type(erro).__name__
            or 'UniqueViolation' in type(erro).__name__)


def _indices(usuario_id, campos):
    return {'cns': _indice(usuario_id, 'cns', campos.get('cns')), 'cpf': _indice(usuario_id, 'cpf', campos.get('cpf'))}


def _completo(paciente_id, campos, criado_em, atualizado_em):
    """O registro como sai para o dono: todas as chaves, com '' (ou [] e {}) no que não foi informado."""
    saida = {'id': int(paciente_id), 'criado_em': int(criado_em), 'atualizado_em': int(atualizado_em)}
    for campo in CAMPOS:
        saida[campo] = campos.get(campo, [] if campo == 'planos' else {} if campo == 'ficha' else '')
    return saida


def _resumo(paciente_id, campos, atualizado_em):
    return {'id': int(paciente_id), 'nome': campos.get('nome', ''), 'nascimento': campos.get('nascimento', ''),
            'sexo': campos.get('sexo', ''), 'cns_final': (campos.get('cns') or '')[-4:],
            'atualizado_em': int(atualizado_em)}


def criar(usuario_id, dados):
    """Grava um paciente da conta e devolve o registro. `Duplicado` se a conta já tem o CNS ou o CPF."""
    uid = int(usuario_id)
    campos = validar(dados)
    cofre, indices, agora = _cofre(), _indices(uid, campos), int(time.time())
    try:
        with contas._conexao() as executar:
            total = executar('SELECT COUNT(*) FROM pacientes WHERE usuario_id = ?', (uid,)).fetchall()[0][0]
            if total >= MAX_PACIENTES_POR_CONTA:
                raise LimiteDaConta(MAX_PACIENTES_POR_CONTA)
            _recusar_duplicado(executar, uid, indices)
            # Duas etapas na mesma transação: o número do registro só existe depois do INSERT e vai dentro do
            # texto cifrado. A linha sem dados nunca fica visível a outra conexão.
            pid = executar(
                'INSERT INTO pacientes (usuario_id, dados, indice_cns, indice_cpf, criado_em, atualizado_em) '
                'VALUES (?, ?, ?, ?, ?, ?) RETURNING id',
                (uid, '', indices['cns'], indices['cpf'], agora, agora)).fetchall()[0][0]
            if executar('UPDATE pacientes SET dados = ? WHERE id = ? AND usuario_id = ?',
                        (_cifrar(cofre, uid, pid, campos), pid, uid)).rowcount != 1:
                raise RuntimeError('o registro novo não foi gravado')
            _registrar(executar, pid, uid, 'criar', agora)
    except (Duplicado, LimiteDaConta):
        raise
    except Exception as erro:
        # Outra requisição gravou o mesmo CNS ou CPF no intervalo: o índice único do banco recusou.
        if _violou_unicidade(erro):
            with contas._conexao() as executar:
                _recusar_duplicado(executar, uid, indices)
        raise
    return _completo(pid, campos, agora, agora)


def _busca(texto):
    """(palavras do nome, final do CNS): só algarismos procuram pelo final do CNS; o resto, pelo nome."""
    texto = contas._limpo(texto, 80)
    numero = re.sub(r'[\s.\-]', '', texto)
    if re.fullmatch(r'[0-9]+', numero):
        return [], numero
    return _sem_acento(texto).split(), ''


def listar(usuario_id, busca=''):
    """Pacientes da conta, em ordem alfabética: {'pacientes', 'total', 'truncado', 'ilegiveis'}.

    Cada item traz só id, nome, nascimento, sexo, os 4 últimos dígitos do CNS e atualizado_em. A busca (parte do
    nome, sem diferenciar acento ou maiúscula, ou o final do CNS) é feita aqui, depois de decifrar: o banco não
    tem como procurar em texto cifrado. Saem no máximo `LIMITE_DA_LISTA`; `total` conta todos os que combinam.
    O termo da busca não é gravado em lugar nenhum.
    """
    uid = int(usuario_id)
    palavras, final_do_cns = _busca(busca)
    cofre = _cofre()
    achados, ilegiveis, ultimo = [], 0, None
    with contas._conexao() as executar:
        while True:
            if ultimo is None:
                linhas = executar('SELECT id, dados, atualizado_em FROM pacientes WHERE usuario_id = ? '
                                  'ORDER BY id DESC LIMIT ?', (uid, LOTE_DA_LISTA)).fetchall()
            else:
                linhas = executar('SELECT id, dados, atualizado_em FROM pacientes WHERE usuario_id = ? AND id < ? '
                                  'ORDER BY id DESC LIMIT ?', (uid, ultimo, LOTE_DA_LISTA)).fetchall()
            for pid, cifrado, atualizado_em in linhas:
                try:
                    campos = _decifrar(cofre, uid, pid, cifrado)
                except RegistroIlegivel:
                    ilegiveis += 1
                    continue
                if final_do_cns:
                    combina = (campos.get('cns') or '').endswith(final_do_cns)
                else:
                    nomes = _sem_acento(f"{campos.get('nome', '')} {campos.get('nome_social', '')}")
                    combina = all(palavra in nomes for palavra in palavras)
                if combina:
                    achados.append(_resumo(pid, campos, atualizado_em))
            if len(linhas) < LOTE_DA_LISTA:
                break
            ultimo = linhas[-1][0]
        _registrar(executar, None, uid, 'listar')
    achados.sort(key=lambda p: (_sem_acento(p['nome']), p['id']))
    return {'pacientes': achados[:LIMITE_DA_LISTA], 'total': len(achados),
            'truncado': len(achados) > LIMITE_DA_LISTA, 'ilegiveis': ilegiveis}


def _consultar(usuario_id, paciente_id, acao):
    uid, pid = int(usuario_id), _id(paciente_id)
    if pid is None:
        return None
    cofre = _cofre()
    with contas._conexao() as executar:
        linha = executar('SELECT dados, criado_em, atualizado_em FROM pacientes WHERE id = ? AND usuario_id = ?',
                         (pid, uid)).fetchone()
        if not linha:
            return None
        paciente = _completo(pid, _decifrar(cofre, uid, pid, linha[0]), linha[1], linha[2])
        _registrar(executar, pid, uid, acao)
    return paciente


def ler(usuario_id, paciente_id):
    """O paciente `paciente_id`, só se for da conta; senão None."""
    return _consultar(usuario_id, paciente_id, 'ver')


def exportar(usuario_id, paciente_id):
    """Tudo o que há guardado do paciente, para baixar (portabilidade); None se não for da conta."""
    paciente = _consultar(usuario_id, paciente_id, 'exportar')
    if paciente is None:
        return None
    return {'formato': 'evidens-paciente', 'versao': 1, 'exportado_em': int(time.time()), 'paciente': paciente}


def atualizar(usuario_id, paciente_id, dados):
    """Troca os campos enviados e mantém os demais; campo enviado vazio ('' ou null) é apagado.

    `planos` e `ficha`, quando enviados, substituem os anteriores por inteiro. Devolve o registro como ficou,
    ou None se o paciente não for da conta ou tiver sido excluído no meio do caminho.

    `atualizado_em`, quando enviado, é a versão que quem edita tinha em mãos (o `atualizado_em` do registro lido):
    se o registro foi alterado depois disso, a edição é recusada com `EdicaoSimultanea` e nada é gravado, para um
    formulário aberto há tempo não sobrescrever o que mudou em outro lugar. Não é campo do paciente e não é
    gravado; cada edição avança o `atualizado_em` do registro em pelo menos 1 segundo, então duas edições no mesmo
    segundo não se confundem.

    Dois pedidos ao mesmo tempo: em Postgres a leitura trava a linha (SELECT … FOR UPDATE) até a gravação, e o
    segundo pedido espera e parte do que o primeiro gravou. Em sqlite, que não tem a cláusula, o UPDATE só grava
    se o texto cifrado ainda for o que foi lido. Nos dois bancos confere-se quantas linhas o UPDATE alcançou:
    nenhuma, e o registro sumiu (None) ou mudou (`EdicaoSimultanea`); em nenhum dos casos entra "editar" na trilha.
    """
    uid, pid = int(usuario_id), _id(paciente_id)
    if not isinstance(dados, dict):
        raise DadosInvalidos(['Envie os dados do paciente em JSON.'])
    if pid is None:
        return None
    dados = dict(dados)
    versao = dados.pop('atualizado_em', None)
    if versao is not None and (isinstance(versao, bool) or not isinstance(versao, int)):
        raise DadosInvalidos(['A versão do registro (atualizado_em) deve ser o número recebido na leitura.'])
    cofre, agora = _cofre(), int(time.time())
    indices = {}
    try:
        with contas._conexao() as executar:
            trava = ' FOR UPDATE' if _em_postgres() else ''
            # fetchall: a consulta termina aqui e não segura o banco (sqlite) enquanto a edição é preparada.
            linhas = executar('SELECT dados, criado_em, atualizado_em FROM pacientes WHERE id = ? AND usuario_id = ?'
                              + trava, (pid, uid)).fetchall()
            if not linhas:
                return None
            lido, criado_em, atualizado_em = linhas[0]
            if versao is not None and versao != int(atualizado_em):
                raise EdicaoSimultanea()           # mudou desde que quem edita leu o registro
            agora = max(agora, int(atualizado_em) + 1)
            campos = validar({**_decifrar(cofre, uid, pid, lido), **dados})
            indices = _indices(uid, campos)
            _recusar_duplicado(executar, uid, indices, exceto=pid)
            gravadas = executar('UPDATE pacientes SET dados = ?, indice_cns = ?, indice_cpf = ?, atualizado_em = ? '
                                'WHERE id = ? AND usuario_id = ? AND dados = ?',
                                (_cifrar(cofre, uid, pid, campos), indices['cns'], indices['cpf'], agora, pid, uid,
                                 lido)).rowcount
            if gravadas != 1:
                ainda_existe = executar('SELECT id FROM pacientes WHERE id = ? AND usuario_id = ?', (pid, uid)).fetchall()
                if not ainda_existe:
                    return None                    # excluído entre a leitura e a gravação
                raise EdicaoSimultanea()
            _registrar(executar, pid, uid, 'editar', agora)
    except (Duplicado, DadosInvalidos, RegistroIlegivel, EdicaoSimultanea):
        raise
    except Exception as erro:
        if indices and _violou_unicidade(erro):
            with contas._conexao() as executar:
                _recusar_duplicado(executar, uid, indices, exceto=pid)
        raise
    return _completo(pid, campos, criado_em, agora)


def excluir(usuario_id, paciente_id):
    """Apaga o registro (a linha inteira). A trilha de acessos fica, só com o número do registro.

    Não depende da chave: um registro que não abre mais também pode ser apagado."""
    uid, pid = int(usuario_id), _id(paciente_id)
    if pid is None:
        return False
    with contas._conexao() as executar:
        apagou = executar('DELETE FROM pacientes WHERE id = ? AND usuario_id = ?', (pid, uid)).rowcount > 0
        if apagou:
            _registrar(executar, pid, uid, 'excluir')
    return apagou


def trilha(usuario_id, paciente_id=None, limite=200):
    """Acessos da conta (ou de um paciente dela), do mais recente para o mais antigo. Ler a trilha não a altera."""
    uid = int(usuario_id)
    sql, parametros = 'SELECT paciente_id, acao, quando FROM pacientes_acessos WHERE usuario_id = ?', [uid]
    if paciente_id is not None:
        sql, parametros = sql + ' AND paciente_id = ?', parametros + [_id(paciente_id) or 0]
    with contas._conexao() as executar:
        linhas = executar(sql + ' ORDER BY id DESC LIMIT ?', parametros + [int(limite)]).fetchall()
    return [{'paciente_id': linha[0], 'acao': linha[1], 'quando': int(linha[2])} for linha in linhas]
