"""Assinatura digital ICP-Brasil dos pedidos (exames e receita de vacinas), com certificado em nuvem.

O médico autoriza uma sessão no provedor do certificado (hoje o BirdID, da Soluti) e, enquanto ela
vale, cada PDF sai assinado. O certificado e a chave nunca passam por aqui: o Evidēns manda ao provedor
só o resumo (SHA-256) do que vai ser assinado e recebe a assinatura de volta.

Referências seguidas:
- API dos provedores de certificado em nuvem (PSC): DOC-ICP-17.01 do ITI (OAuth 2.0 com PKCE,
  /oauth/authorize, /oauth/token, /oauth/certificate-discovery, /oauth/signature).
- Validar (ITI), Guia do Desenvolvedor — https://validar.iti.gov.br/guia-desenvolvedor.html :
  PDF assinado no padrão PAdES; DocMDP no dicionário de referência da assinatura (P = 2, V = 1.2),
  sem a entrada /Perms do catálogo; metadados com o OID do registro profissional, da UF e do tipo
  de documento de saúde (2.16.76.1.12.1.x).

Credenciais do aplicativo no provedor: variáveis de ambiente (nunca no código nem no banco).
Sem elas o provedor não aparece para ninguém e os pedidos seguem saindo como minuta.
"""

import base64
import hashlib
import io
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

# Provedores com integração pronta. Todos os PSC em nuvem seguem a mesma API do ITI; cada um entra aqui
# depois de testado na homologação dele.
PROVEDORES = {
    'birdid': {
        'nome': 'BirdID',
        'url': ('BIRDID_URL', 'https://api.birdid.com.br'),
        'prefixo': '/v0/oauth',
        'cliente': 'BIRDID_CLIENT_ID',
        'segredo': 'BIRDID_CLIENT_SECRET',
    },
}
# Aparecem na lista como "em breve" (mesma API; falta credenciar e testar cada um).
EM_BREVE = ('VIDaaS', 'VaultID', 'SafeID', 'RemoteID', 'NeoID', 'DSCloud', 'SYN')

DURACOES = (1, 4, 12)          # horas de sessão oferecidas ao médico
DURACAO_PADRAO = 4
ESCOPO = 'signature_session'   # várias assinaturas enquanto a sessão valer
OID_SHA256 = '2.16.840.1.101.3.4.2.1'

# OIDs do ITI para documentos digitais em saúde (metadados do PDF).
OID_CRM_NUMERO = '2.16.76.1.4.2.2.1'
OID_CRM_UF = '2.16.76.1.4.2.2.2'
OID_DOCUMENTO = {
    'laboratorio': '2.16.76.1.12.1.3',   # solicitação de exame
    'imagem': '2.16.76.1.12.1.3',
    'vacina': '2.16.76.1.12.1.1',        # prescrição
}

TEMPO_LIMITE = 15   # segundos por chamada ao provedor


class FalhaNaAssinatura(Exception):
    """A assinatura não saiu; `codigo` diz por quê (a mensagem ao usuário é montada na rota)."""

    def __init__(self, codigo, detalhe=''):
        super().__init__(f'{codigo}: {detalhe}' if detalhe else codigo)
        self.codigo = codigo


class SessaoExpirada(FalhaNaAssinatura):
    def __init__(self, detalhe=''):
        super().__init__('sessao_expirada', detalhe)


# ── Provedores ────────────────────────────────────────────────────────────────

def _config(provedor):
    p = PROVEDORES.get(provedor)
    if not p:
        return None
    cliente = (os.environ.get(p['cliente']) or '').strip()
    segredo = (os.environ.get(p['segredo']) or '').strip()
    if not cliente or not segredo:
        return None
    variavel, padrao = p['url']
    base = (os.environ.get(variavel) or padrao).strip().rstrip('/')
    return {'nome': p['nome'], 'base': base + p['prefixo'], 'cliente': cliente, 'segredo': segredo}


def disponiveis():
    """Provedores com credenciais configuradas: [{'id', 'nome'}]."""
    return [{'id': pid, 'nome': p['nome']} for pid, p in PROVEDORES.items() if _config(pid)]


def nome_do_provedor(provedor):
    return PROVEDORES.get(provedor, {}).get('nome', provedor)


def _pedir(metodo, url, corpo=None, token=None):
    """Chamada HTTP ao provedor; devolve o JSON da resposta. Os testes trocam esta função."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    cabecalhos = {'Accept': 'application/json'}
    if dados is not None:
        cabecalhos['Content-Type'] = 'application/json'
    if token:
        cabecalhos['Authorization'] = f'Bearer {token}'
    pedido = urllib.request.Request(url, data=dados, headers=cabecalhos, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
            texto = resposta.read(2_000_000).decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise SessaoExpirada(f'HTTP {exc.code}')
        raise FalhaNaAssinatura('provedor_recusou', f'HTTP {exc.code}')
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FalhaNaAssinatura('provedor_fora', type(exc).__name__)
    try:
        return json.loads(texto) if texto.strip() else {}
    except ValueError:
        raise FalhaNaAssinatura('provedor_recusou', 'resposta ilegível')


def novo_pkce():
    """(verificador, desafio S256) do PKCE (RFC 7636)."""
    verificador = secrets.token_urlsafe(48)
    desafio = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b'=').decode()
    return verificador, desafio


def url_de_autorizacao(provedor, retorno, estado, desafio, horas):
    c = _config(provedor)
    if not c:
        raise FalhaNaAssinatura('provedor_indisponivel')
    parametros = {
        'response_type': 'code', 'client_id': c['cliente'], 'redirect_uri': retorno, 'state': estado,
        'code_challenge': desafio, 'code_challenge_method': 'S256',
        'scope': ESCOPO, 'lifetime': str(int(horas) * 3600),
    }
    return f"{c['base']}/authorize?{urllib.parse.urlencode(parametros)}"


def trocar_codigo(provedor, codigo, verificador, retorno, horas):
    """Troca o código de autorização pelo token da sessão: {'token', 'expira_em'}."""
    c = _config(provedor)
    if not c:
        raise FalhaNaAssinatura('provedor_indisponivel')
    r = _pedir('POST', f"{c['base']}/token", {
        'grant_type': 'authorization_code', 'client_id': c['cliente'], 'client_secret': c['segredo'],
        'code': codigo, 'code_verifier': verificador, 'redirect_uri': retorno,
        'lifetime': int(horas) * 3600,
    })
    token = r.get('access_token')
    if not isinstance(token, str) or not token:
        raise FalhaNaAssinatura('provedor_recusou', 'sem token')
    try:
        validade = int(r.get('expires_in') or 0)
    except (TypeError, ValueError):
        validade = 0
    pedido = int(horas) * 3600
    validade = min(validade, pedido) if validade > 0 else pedido
    return {'token': token, 'expira_em': int(time.time()) + validade}


def certificados(provedor, token):
    """Certificados do titular no provedor: [{'alias', 'pem'}]."""
    c = _config(provedor)
    if not c:
        raise FalhaNaAssinatura('provedor_indisponivel')
    r = _pedir('GET', f"{c['base']}/certificate-discovery", token=token)
    saida = []
    for item in r.get('certificates') or []:
        if isinstance(item, dict) and isinstance(item.get('certificate'), str):
            saida.append({'alias': str(item.get('alias') or ''), 'pem': _como_pem(item['certificate'])})
    return saida


def assinar_resumo(provedor, token, alias, resumo):
    """Assinatura RSA (PKCS#1 v1.5) do resumo SHA-256, feita pelo provedor com a chave do titular."""
    c = _config(provedor)
    if not c:
        raise FalhaNaAssinatura('provedor_indisponivel')
    r = _pedir('POST', f"{c['base']}/signature", {
        'certificate_alias': alias,
        'hashes': [{'id': 'pedido', 'alias': 'pedido', 'hash': resumo.hex(),
                    'hash_algorithm': OID_SHA256, 'signature_format': 'RAW'}],
    }, token=token)
    assinaturas = r.get('signatures') or []
    bruta = assinaturas[0].get('raw_signature') if assinaturas and isinstance(assinaturas[0], dict) else None
    if not isinstance(bruta, str) or not bruta:
        raise FalhaNaAssinatura('provedor_recusou', 'sem assinatura')
    try:
        return base64.b64decode(bruta, validate=False)
    except ValueError:
        raise FalhaNaAssinatura('provedor_recusou', 'assinatura ilegível')


def revogar(provedor, token):
    """Encerra a sessão no provedor (melhor esforço: a sessão local é apagada de qualquer modo)."""
    c = _config(provedor)
    if not c:
        return
    try:
        _pedir('POST', f"{c['base']}/revoke", {'token': token, 'client_id': c['cliente'],
                                              'client_secret': c['segredo']}, token=token)
    except FalhaNaAssinatura:
        pass


# ── Certificado ───────────────────────────────────────────────────────────────

def _como_pem(texto):
    texto = texto.strip()
    if 'BEGIN CERTIFICATE' in texto:
        return texto
    corpo = re.sub(r'\s+', '', texto)
    linhas = '\n'.join(corpo[i:i + 64] for i in range(0, len(corpo), 64))
    return f'-----BEGIN CERTIFICATE-----\n{linhas}\n-----END CERTIFICATE-----'


def _carregar(pem):
    from asn1crypto import pem as leitor_pem, x509
    try:
        _, _, der = leitor_pem.unarmor(pem.encode())
        return x509.Certificate.load(der)
    except (ValueError, TypeError) as exc:
        raise FalhaNaAssinatura('certificado_invalido', type(exc).__name__)


def dados_do_certificado(pem):
    """{'titular', 'valido_ate'} do certificado. O CN da ICP-Brasil é 'NOME:CPF'; o CPF não é guardado."""
    cert = _carregar(pem)
    nome = cert.subject.native.get('common_name') or ''
    if isinstance(nome, list):
        nome = nome[0] if nome else ''
    titular = re.sub(r':\d+$', '', str(nome)).strip()[:150]
    return {'titular': titular, 'valido_ate': int(cert['tbs_certificate']['validity']['not_after'].native.timestamp()),
            'rsa': cert.public_key.algorithm == 'rsa'}


def escolher_certificado(lista, agora=None):
    """O primeiro certificado RSA ainda válido da lista do provedor, com os dados dele."""
    agora = agora or time.time()
    for item in lista:
        try:
            dados = dados_do_certificado(item['pem'])
        except FalhaNaAssinatura:
            continue
        if dados['rsa'] and dados['valido_ate'] > agora and dados['titular']:
            return {**item, **dados}
    raise FalhaNaAssinatura('sem_certificado')


# ── Token guardado ────────────────────────────────────────────────────────────
# O token da sessão fica no banco cifrado (Fernet) com uma chave que só existe no ambiente da aplicação.

def _cofre(chave):
    from cryptography.fernet import Fernet
    segredo = (os.environ.get('ASSINATURA_CHAVE') or chave or '').encode()
    if not segredo:
        raise FalhaNaAssinatura('sem_chave')
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'evidens-assinatura:' + segredo).digest()))


def cifrar(token, chave):
    return _cofre(chave).encrypt(token.encode()).decode()


def decifrar(cifrado, chave):
    from cryptography.fernet import InvalidToken
    try:
        return _cofre(chave).decrypt(cifrado.encode()).decode()
    except (InvalidToken, ValueError):
        raise SessaoExpirada('token ilegível')


# ── PDF ───────────────────────────────────────────────────────────────────────

def metadados_iti(crm, categoria):
    """Metadados do Validar para o documento: tipo e, quando há CRM reconhecido, número e UF."""
    dados = {}
    oid = OID_DOCUMENTO.get(categoria)
    if oid:
        dados[oid] = ''
    m = re.match(r'^CRM-([A-Z]{2}) (\d+)$', crm or '')
    if m:
        dados[OID_CRM_NUMERO] = m.group(2)
        dados[OID_CRM_UF] = m.group(1)
    return dados


def _com_metadados(pdf, metadados):
    if not metadados:
        return pdf
    from pypdf import PdfReader, PdfWriter
    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    escritor.add_metadata({f'/{oid}': valor for oid, valor in metadados.items()})
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()


def assinar_pdf(pdf, certificado_pem, assinar, metadados=None, titular=None):
    """O PDF assinado (PAdES, SHA-256 com RSA).

    `assinar(resumo)` recebe os 32 bytes do SHA-256 dos atributos assinados e devolve a assinatura RSA
    PKCS#1 v1.5 (é a chamada ao provedor). A assinatura é conferida com a chave pública do certificado
    antes de entrar no documento: resposta que não confere vira erro, nunca um PDF com assinatura inválida.
    """
    from asn1crypto import algos
    from cryptography import x509 as cx509
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, utils
    from pyhanko.pdf_utils import generic
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import fields, signers
    from pyhanko.sign.fields import MDPPerm
    from pyhanko.sign.signers.cms_embedder import SigMDPSetup, docmdp_reference_dictionary

    certificado = _carregar(certificado_pem)
    if certificado.public_key.algorithm != 'rsa':
        raise FalhaNaAssinatura('certificado_invalido', 'chave não RSA')
    chave_publica = cx509.load_der_x509_certificate(certificado.dump()).public_key()

    class Remoto(signers.Signer):
        def __init__(self):
            super().__init__(signing_cert=certificado,
                             signature_mechanism=algos.SignedDigestAlgorithm({'algorithm': 'sha256_rsa'}))

        async def async_sign_raw(self, data, digest_algorithm, dry_run=False):
            if dry_run:     # só para medir o espaço da assinatura: não chama o provedor
                return bytes(chave_publica.key_size // 8)
            resumo = hashlib.sha256(data).digest()
            assinatura = assinar(resumo)
            try:
                chave_publica.verify(assinatura, resumo, padding.PKCS1v15(), utils.Prehashed(hashes.SHA256()))
            except InvalidSignature:
                raise FalhaNaAssinatura('assinatura_nao_confere')
            return assinatura

    class SoReferencia(SigMDPSetup):
        """DocMDP só no dicionário de referência da assinatura, sem /Perms no catálogo (orientação do Validar)."""

        def apply(self, sig_obj_ref, writer):
            sig_obj_ref.get_object()['/Reference'] = generic.ArrayObject(
                [docmdp_reference_dictionary(MDPPerm.FILL_FORMS)])

    class Assinador(signers.PdfSigner):
        def init_signing_session(self, *args, **kwargs):
            sessao = super().init_signing_session(*args, **kwargs)
            regras = sessao._apply_locking_rules
            sessao._apply_locking_rules = lambda: SoReferencia(md_algorithm=regras().md_algorithm)
            return sessao

    escritor = IncrementalPdfFileWriter(io.BytesIO(_com_metadados(pdf, metadados)), strict=False)
    dados = signers.PdfSignatureMetadata(
        field_name='AssinaturaDoMedico', md_algorithm='sha256',
        subfilter=fields.SigSeedSubFilter.PADES, name=titular or None)
    saida = io.BytesIO()
    try:
        Assinador(dados, signer=Remoto()).sign_pdf(escritor, output=saida)
    except FalhaNaAssinatura:
        raise
    except Exception as exc:
        raise FalhaNaAssinatura('pdf_nao_assinou', f'{type(exc).__name__}: {exc}')
    return saida.getvalue()
