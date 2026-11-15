"""Assinatura digital dos pedidos (src/utils/assinatura.py, rotas /api/auth/assinatura e os PDFs assinados).

O provedor do certificado é simulado: um certificado e uma chave fictícios, criados a cada execução,
respondem no lugar da API do BirdID. Nenhum dado de pessoa real entra aqui.
"""
import base64
import datetime
import hashlib
import io
import itertools
from urllib.parse import parse_qs, urlsplit

import pytest
from asn1crypto import pem as leitor_pem, x509 as ax509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils
from cryptography.x509.oid import NameOID
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from pypdf import PdfReader

from conftest import SENHA_DE_TESTE, aceitar_termos
from src.utils import assinatura, pdf_minutas

_seq = itertools.count(1)
PACIENTE = {'nome': 'Maria de Teste', 'idade': '65', 'sexo': 'feminino'}
EXAMES = [{'titulo': t, 'categoria': 'laboratorio'} for t in ('Hemograma completo', 'Creatinina, soro')]
VACINAS = [{'titulo': 'Vacina influenza', 'categoria': 'vacina'}]
TITULAR = 'MEDICA FICTICIA DE TESTE'


def _certificado(nome=TITULAR + ':00000000191', dias=365):
    """(PEM, função que assina um resumo SHA-256) de um certificado autoassinado de teste."""
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sujeito = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
                         x509.NameAttribute(NameOID.COMMON_NAME, nome)])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(sujeito).issuer_name(sujeito).public_key(chave.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(agora - datetime.timedelta(days=1))
            .not_valid_after(agora + datetime.timedelta(days=dias))
            .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
            .sign(chave, hashes.SHA256()))
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return pem, lambda resumo: chave.sign(resumo, padding.PKCS1v15(), utils.Prehashed(hashes.SHA256()))


PEM, ASSINAR = _certificado()


class Provedor:
    """Faz o papel da API do provedor: confere o PKCE, entrega o certificado e assina resumos."""

    def __init__(self, monkeypatch):
        self.desafio = None
        self.pedidos = []
        self.token_valido = True
        self.certificados = [{'alias': 'cert-1', 'certificate': PEM}]
        self.assinar = ASSINAR
        monkeypatch.setenv('BIRDID_CLIENT_ID', 'cliente-de-teste')
        monkeypatch.setenv('BIRDID_CLIENT_SECRET', 'segredo-de-teste')
        monkeypatch.setattr(assinatura, '_pedir', self.pedir)

    def pedir(self, metodo, url, corpo=None, token=None):
        caminho = urlsplit(url).path
        self.pedidos.append((metodo, caminho, corpo, token))
        if caminho.endswith('/token'):
            feito = base64.urlsafe_b64encode(hashlib.sha256(corpo['code_verifier'].encode()).digest()).rstrip(b'=').decode()
            if corpo['code'] != 'codigo-ok' or feito != self.desafio or corpo['client_secret'] != 'segredo-de-teste':
                raise assinatura.FalhaNaAssinatura('provedor_recusou', 'HTTP 400')
            return {'access_token': 'token-da-sessao', 'expires_in': corpo['lifetime']}
        if token != 'token-da-sessao' or not self.token_valido:
            raise assinatura.SessaoExpirada('HTTP 401')
        if caminho.endswith('/certificate-discovery'):
            return {'status': 'S', 'certificates': self.certificados}
        if caminho.endswith('/signature'):
            item = corpo['hashes'][0]
            assert item['hash_algorithm'] == '2.16.840.1.101.3.4.2.1' and item['signature_format'] == 'RAW'
            assert corpo['certificate_alias'] == 'cert-1'
            return {'signatures': [{'id': item['id'],
                                    'raw_signature': base64.b64encode(self.assinar(bytes.fromhex(item['hash']))).decode()}]}
        if caminho.endswith('/revoke'):
            self.token_valido = False
            return {}
        raise AssertionError(caminho)

    def chamadas(self, final):
        return [p for p in self.pedidos if p[1].endswith(final)]


@pytest.fixture
def provedor(monkeypatch):
    return Provedor(monkeypatch)


def _conta(app, contas, perfil='medico'):
    n = next(_seq)
    registro = f'CRM-GO 7{n:04d}' if perfil != 'estudante' else '2023001 · UFG'
    u = contas.criar(f'assina{n}@exemplo.test', f'Dra. Assinatura {n}', registro, perfil, SENHA_DE_TESTE)
    contas.definir_situacao(u['id'], 'aprovado')
    aceitar_termos(contas, u)
    cliente = app.test_client()
    assert cliente.post('/api/auth/login', json={'email': u['email'], 'senha': SENHA_DE_TESTE}).status_code == 200
    return cliente, u


def _abrir_sessao(cliente, provedor, horas=4):
    r = cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': horas})
    assert r.status_code == 200, r.get_json()
    consulta = parse_qs(urlsplit(r.get_json()['url']).query)
    provedor.desafio = consulta['code_challenge'][0]
    return consulta, cliente.get(f"/api/auth/assinatura/retorno?code=codigo-ok&state={consulta['state'][0]}")


def _pedir_pdf(cliente, assinar=True, rota='/api/gerar-pdf-exames-laboratoriais', itens=EXAMES, **extra):
    return cliente.post(rota, json={'dados_paciente': PACIENTE, 'recomendacoes': itens, 'assinar': assinar, **extra})


def _assinatura_do_pdf(conteudo):
    leitor = PdfFileReader(io.BytesIO(conteudo))
    assert len(leitor.embedded_signatures) == 1
    embutida = leitor.embedded_signatures[0]
    raiz = ax509.Certificate.load(leitor_pem.unarmor(PEM.encode())[2])
    return leitor, embutida, validate_pdf_signature(embutida, ValidationContext(trust_roots=[raiz]))


# ── O PDF assinado ────────────────────────────────────────────────────────────

def test_pdf_assinado_e_integro_cobre_o_arquivo_inteiro_e_segue_o_validar():
    pdf = pdf_minutas.gerar_pdf_exames_laboratoriais(PACIENTE, EXAMES, assinatura={'titular': TITULAR})
    chamadas = []
    assinado = assinatura.assinar_pdf(pdf, PEM, lambda r: chamadas.append(r) or ASSINAR(r),
                                      assinatura.metadados_iti('CRM-GO 12345', 'laboratorio'), TITULAR)
    leitor, embutida, estado = _assinatura_do_pdf(assinado)
    assert estado.intact and estado.valid and estado.coverage.name == 'ENTIRE_FILE'
    assert len(chamadas) == 1 and len(chamadas[0]) == 32          # uma só ida ao provedor, com o resumo SHA-256
    objeto = embutida.sig_object
    assert objeto['/SubFilter'] == '/ETSI.CAdES.detached'          # PAdES
    # Guia do Desenvolvedor do Validar: DocMDP na referência da assinatura (P = 2, V = 1.2) e sem /Perms.
    referencia = objeto['/Reference'][0]
    assert referencia['/TransformMethod'] == '/DocMDP'
    assert referencia['/TransformParams']['/P'] == 2 and referencia['/TransformParams']['/V'] == '/1.2'
    assert '/Perms' not in leitor.root
    info = leitor.trailer['/Info']
    assert info['/2.16.76.1.12.1.3'] == '' and info['/2.16.76.1.4.2.2.1'] == '12345' and info['/2.16.76.1.4.2.2.2'] == 'GO'


def test_pdf_alterado_depois_de_assinado_deixa_de_validar():
    assinado = assinatura.assinar_pdf(pdf_minutas.gerar_pdf_vacinas(PACIENTE, VACINAS), PEM, ASSINAR)
    posicao = assinado.index(b'/Type /Page')
    adulterado = assinado[:posicao] + b'/Type /Pagf' + assinado[posicao + 11:]
    try:
        _, _, estado = _assinatura_do_pdf(adulterado)
        assert not (estado.intact and estado.valid)
    except Exception:
        pass        # arquivo que nem abre mais também não passa por assinado


def test_assinatura_que_nao_confere_com_o_certificado_e_recusada():
    _, outra_chave = _certificado()
    with pytest.raises(assinatura.FalhaNaAssinatura) as erro:
        assinatura.assinar_pdf(pdf_minutas.gerar_pdf_vacinas(PACIENTE, VACINAS), PEM, outra_chave)
    assert erro.value.codigo == 'assinatura_nao_confere'


def test_metadados_do_iti_por_tipo_de_documento():
    assert assinatura.metadados_iti('CRM-SP 987', 'vacina') == {
        '2.16.76.1.12.1.1': '', '2.16.76.1.4.2.2.1': '987', '2.16.76.1.4.2.2.2': 'SP'}
    assert assinatura.metadados_iti('CRM-SP 987', 'imagem')['2.16.76.1.12.1.3'] == ''
    assert assinatura.metadados_iti(None, 'laboratorio') == {'2.16.76.1.12.1.3': ''}     # sem CRM reconhecido


def test_titular_sai_do_certificado_sem_o_cpf():
    dados = assinatura.dados_do_certificado(PEM)
    assert dados['titular'] == TITULAR and dados['rsa']
    assert dados['valido_ate'] > datetime.datetime.now().timestamp()


def test_certificado_vencido_nao_e_escolhido():
    vencido, _ = _certificado(dias=0)
    with pytest.raises(assinatura.FalhaNaAssinatura) as erro:
        assinatura.escolher_certificado([{'alias': 'a', 'pem': vencido}],
                                        agora=datetime.datetime.now().timestamp() + 86400)
    assert erro.value.codigo == 'sem_certificado'
    assert assinatura.escolher_certificado([{'alias': 'a', 'pem': vencido}, {'alias': 'b', 'pem': PEM}],
                                           agora=datetime.datetime.now().timestamp() + 86400)['alias'] == 'b'


def test_token_guardado_fica_cifrado_e_nao_abre_com_outra_chave():
    cifrado = assinatura.cifrar('token-da-sessao', 'chave-do-ambiente')
    assert 'token-da-sessao' not in cifrado
    assert assinatura.decifrar(cifrado, 'chave-do-ambiente') == 'token-da-sessao'
    with pytest.raises(assinatura.SessaoExpirada):
        assinatura.decifrar(cifrado, 'outra-chave')


def test_minuta_assinada_troca_a_linha_de_caneta_pelo_aviso_de_assinatura_digital():
    def texto(**extra):
        pdf = pdf_minutas.gerar_pdf_exames_laboratoriais(
            PACIENTE, EXAMES, responsavel={'nome': 'Dra. Teste', 'crm': 'CRM-GO 12345', 'estudante': False}, **extra)
        return ' '.join(PdfReader(io.BytesIO(pdf)).pages[0].extract_text().split())
    com, sem = texto(assinatura={'titular': TITULAR}), texto()
    assert f'Assinado digitalmente por {TITULAR}' in com and 'validar.iti.gov.br' in com
    assert 'CRM-GO 12345' in com
    assert 'sem assinatura digital' not in com and 'Assinatura e Carimbo' not in com
    assert 'sem assinatura digital' in sem and 'Assinado digitalmente' not in sem


# ── Sessão no provedor ────────────────────────────────────────────────────────

def test_sem_credenciais_do_provedor_a_assinatura_nao_aparece(app, contas, monkeypatch):
    monkeypatch.delenv('BIRDID_CLIENT_ID', raising=False)
    monkeypatch.delenv('BIRDID_CLIENT_SECRET', raising=False)
    cliente, _ = _conta(app, contas)
    assert cliente.get('/api/auth/assinatura').get_json() == {'disponivel': False}
    assert cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 4}).status_code == 403
    r = _pedir_pdf(cliente)
    assert r.status_code == 400 and r.get_json()['codigo'] == 'assinatura_indisponivel'


def test_estudante_nao_assina(app, contas, provedor):
    cliente, _ = _conta(app, contas, 'estudante')
    assert cliente.get('/api/auth/assinatura').get_json() == {'disponivel': False}
    assert cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 4}).status_code == 403
    assert _pedir_pdf(cliente).get_json()['codigo'] == 'assinatura_indisponivel'


def test_estado_inicial_lista_provedor_duracoes_e_os_que_vem_depois(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    estado = cliente.get('/api/auth/assinatura').get_json()
    assert estado['disponivel'] and estado['provedores'] == [{'id': 'birdid', 'nome': 'BirdID'}]
    assert estado['duracoes'] == [1, 4, 12] and 'VIDaaS' in estado['em_breve']
    assert estado['preferencias'] == {'provedor': 'birdid', 'horas': 4, 'assinar': False}
    assert estado['sessao'] is None


def test_iniciar_monta_o_pedido_de_autorizacao_com_pkce(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    r = cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 12})
    partes = urlsplit(r.get_json()['url'])
    consulta = {k: v[0] for k, v in parse_qs(partes.query).items()}
    assert f'{partes.scheme}://{partes.netloc}{partes.path}' == 'https://api.birdid.com.br/v0/oauth/authorize'
    assert consulta['response_type'] == 'code' and consulta['client_id'] == 'cliente-de-teste'
    assert consulta['code_challenge_method'] == 'S256' and len(consulta['code_challenge']) == 43
    assert consulta['scope'] == 'signature_session' and consulta['lifetime'] == str(12 * 3600)
    assert consulta['redirect_uri'].endswith('/api/auth/assinatura/retorno')
    assert 'segredo-de-teste' not in r.get_json()['url']           # o segredo do aplicativo nunca vai ao navegador
    assert cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'outro', 'horas': 4}).status_code == 400
    assert cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 24}).status_code == 400


def test_retorno_abre_a_sessao_e_o_estado_mostra_titular_e_validade(app, contas, provedor):
    cliente, u = _conta(app, contas)
    _, volta = _abrir_sessao(cliente, provedor, horas=1)
    assert volta.status_code == 200 and 'Assinatura digital ativada' in volta.get_data(as_text=True)
    assert volta.headers['Cache-Control'] == 'no-store'
    sessao = cliente.get('/api/auth/assinatura').get_json()['sessao']
    assert sessao['provedor'] == 'birdid' and sessao['nome'] == 'BirdID' and sessao['titular'] == TITULAR
    agora = datetime.datetime.now().timestamp()
    assert agora + 3500 < sessao['expira_em'] <= agora + 3601
    guardada = contas.sessao_de_assinatura(u['id'])
    assert 'token-da-sessao' not in guardada['token']             # no banco, só cifrado
    assert set(sessao) == {'provedor', 'nome', 'titular', 'expira_em'}   # token e certificado não vão ao navegador


def test_retorno_com_estado_errado_ou_repetido_nao_abre_sessao(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    r = cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 4})
    consulta = parse_qs(urlsplit(r.get_json()['url']).query)
    provedor.desafio = consulta['code_challenge'][0]
    assert cliente.get('/api/auth/assinatura/retorno?code=codigo-ok&state=forjado').status_code == 400
    # o pedido de sessão vale uma vez: depois de uma volta recusada, nem o estado certo serve
    assert cliente.get(f"/api/auth/assinatura/retorno?code=codigo-ok&state={consulta['state'][0]}").status_code == 400
    assert cliente.get('/api/auth/assinatura').get_json()['sessao'] is None
    assert not provedor.chamadas('/token')


def test_retorno_recusado_pelo_provedor_ou_sem_certificado(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    r = cliente.post('/api/auth/assinatura/iniciar', json={'provedor': 'birdid', 'horas': 4})
    estado = parse_qs(urlsplit(r.get_json()['url']).query)['state'][0]
    volta = cliente.get(f'/api/auth/assinatura/retorno?error=access_denied&state={estado}')
    assert volta.status_code == 400 and 'não foi concluída' in volta.get_data(as_text=True)
    provedor.certificados = []
    _, volta = _abrir_sessao(cliente, provedor)
    assert volta.status_code == 400 and 'Nenhum certificado' in volta.get_data(as_text=True)
    assert cliente.get('/api/auth/assinatura').get_json()['sessao'] is None


def test_retorno_sem_login_nao_abre_sessao(app, contas, provedor):
    assert app.test_client().get('/api/auth/assinatura/retorno?code=codigo-ok&state=x').status_code == 400


def test_preferencias_sao_guardadas_por_conta(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    r = cliente.post('/api/auth/assinatura/preferencias', json={'horas': 12, 'assinar': True})
    assert r.get_json()['preferencias'] == {'provedor': 'birdid', 'horas': 12, 'assinar': True}
    assert cliente.post('/api/auth/assinatura/preferencias', json={'assinar': False}).get_json()['preferencias']['horas'] == 12
    assert cliente.post('/api/auth/assinatura/preferencias', json={'horas': 3}).status_code == 400
    assert cliente.post('/api/auth/assinatura/preferencias', json={'provedor': 'vidaas'}).status_code == 400
    outro, _ = _conta(app, contas)
    assert outro.get('/api/auth/assinatura').get_json()['preferencias']['assinar'] is False


def test_encerrar_e_sair_da_conta_revogam_o_token_no_provedor(app, contas, provedor):
    cliente, u = _conta(app, contas)
    _abrir_sessao(cliente, provedor)
    assert cliente.post('/api/auth/assinatura/encerrar').status_code == 200
    assert contas.sessao_de_assinatura(u['id']) is None and len(provedor.chamadas('/revoke')) == 1
    provedor.token_valido = True
    _abrir_sessao(cliente, provedor)
    cliente.post('/api/auth/logout')
    assert contas.sessao_de_assinatura(u['id']) is None and len(provedor.chamadas('/revoke')) == 2


def test_sessao_vencida_some_sozinha(app, contas, provedor):
    cliente, u = _conta(app, contas)
    _abrir_sessao(cliente, provedor, horas=1)
    assert contas.sessao_de_assinatura(u['id'], agora=datetime.datetime.now().timestamp() + 3700) is None
    assert cliente.get('/api/auth/assinatura').get_json()['sessao'] is None


# ── Pedidos assinados ─────────────────────────────────────────────────────────

@pytest.mark.parametrize('rota,itens,oid', [
    ('/api/gerar-pdf-exames-laboratoriais', EXAMES, '2.16.76.1.12.1.3'),
    ('/api/gerar-pdf-exames-imagem', [{'titulo': 'Mamografia bilateral', 'categoria': 'imagem'}], '2.16.76.1.12.1.3'),
    ('/api/gerar-pdf-vacinas', VACINAS, '2.16.76.1.12.1.1'),
])
def test_cada_tipo_de_pedido_sai_assinado_com_a_sessao_aberta(app, contas, provedor, rota, itens, oid):
    cliente, u = _conta(app, contas)
    _abrir_sessao(cliente, provedor)
    r = _pedir_pdf(cliente, rota=rota, itens=itens)
    assert r.status_code == 200, r.get_json()
    leitor, _, estado = _assinatura_do_pdf(r.data)
    assert estado.intact and estado.valid and estado.coverage.name == 'ENTIRE_FILE'
    info = leitor.trailer['/Info']
    assert info[f'/{oid}'] == '' and info['/2.16.76.1.4.2.2.2'] == 'GO'
    assert info['/2.16.76.1.4.2.2.1'] == contas.crm_de(u).split()[1]
    texto = ' '.join(PdfReader(io.BytesIO(r.data)).pages[0].extract_text().split())
    assert f'Assinado digitalmente por {TITULAR}' in texto and 'sem assinatura digital' not in texto
    assert len(provedor.chamadas('/signature')) == 1


def test_pedido_de_assinatura_sem_sessao_e_recusado_e_nao_entrega_minuta(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    r = _pedir_pdf(cliente)
    assert r.status_code == 409 and r.get_json()['codigo'] == 'assinatura_sem_sessao'
    assert r.mimetype == 'application/json'


def test_sem_pedir_assinatura_o_pdf_continua_minuta_mesmo_com_sessao(app, contas, provedor):
    cliente, _ = _conta(app, contas)
    _abrir_sessao(cliente, provedor)
    r = _pedir_pdf(cliente, assinar=False)
    assert r.status_code == 200 and not PdfFileReader(io.BytesIO(r.data)).embedded_signatures
    assert 'sem assinatura digital' in ' '.join(PdfReader(io.BytesIO(r.data)).pages[0].extract_text().split())
    assert not provedor.chamadas('/signature')


def test_token_recusado_pelo_provedor_encerra_a_sessao_e_pede_nova(app, contas, provedor):
    cliente, u = _conta(app, contas)
    _abrir_sessao(cliente, provedor)
    provedor.token_valido = False
    r = _pedir_pdf(cliente)
    assert r.status_code == 409 and r.get_json()['codigo'] == 'assinatura_sem_sessao'
    assert contas.sessao_de_assinatura(u['id']) is None


def test_falha_do_provedor_ao_assinar_nao_entrega_pdf_sem_assinatura(app, contas, provedor):
    cliente, u = _conta(app, contas)
    _abrir_sessao(cliente, provedor)
    _, outra_chave = _certificado()
    provedor.assinar = outra_chave                     # o provedor devolve assinatura que não confere
    r = _pedir_pdf(cliente)
    assert r.status_code == 502 and r.get_json()['codigo'] == 'assinatura_falhou'
    assert contas.sessao_de_assinatura(u['id']) is not None       # falha passageira não derruba a sessão


def test_pedido_assinado_com_timbrado_e_guia_do_plano(app, contas, provedor):
    from fpdf import FPDF
    cliente, _ = _conta(app, contas)
    papel = FPDF()
    papel.add_page()
    papel.set_font('Helvetica', 'B', 16)
    papel.cell(0, 8, 'Clinica Exemplo Timbrado')
    assert cliente.post('/api/auth/timbrado', data={'arquivo': (io.BytesIO(bytes(papel.output())), 't.pdf')},
                        content_type='multipart/form-data').status_code == 201
    plano = cliente.post('/api/auth/credenciamentos', json=dict(
        operadora='Unimed Goiânia', registro_ans='123456', codigo_prestador='0012345',
        nome_contratado='Clínica de Teste Ltda.', cbo='225125'))
    cid = plano.get_json()['credenciamento']['id']
    _abrir_sessao(cliente, provedor)
    r = _pedir_pdf(cliente, guia={'credenciamento_id': cid, 'carteira': '123', 'indicacao': 'Check-up'})
    assert r.status_code == 200, r.get_json()
    _, _, estado = _assinatura_do_pdf(r.data)
    assert estado.intact and estado.valid and estado.coverage.name == 'ENTIRE_FILE'
    paginas = PdfReader(io.BytesIO(r.data)).pages
    assert 'Clinica Exemplo Timbrado' in paginas[0].extract_text()
    guia = ' '.join(paginas[-1].extract_text().split())
    assert 'Assinado digitalmente (ICP-Brasil)' in guia and 'assinatura e carimbo do médico solicitante' not in guia


def test_sair_da_conta_limpa_a_sessao_mesmo_se_o_encerramento_da_assinatura_falhar(app, contas, provedor, monkeypatch):
    cliente, _ = _conta(app, contas)
    _abrir_sessao(cliente, provedor)

    def banco_fora(uid, agora=None):
        raise RuntimeError('banco fora do ar')
    monkeypatch.setattr(contas, 'sessao_de_assinatura', banco_fora)
    assert cliente.post('/api/auth/logout').status_code == 200
    monkeypatch.undo()
    assert cliente.get('/api/auth/eu').get_json() == {'usuario': None}
