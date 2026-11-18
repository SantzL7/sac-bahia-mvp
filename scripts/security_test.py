"""Exercita ticket/role/posto, JWT, WSS e TLS (teste acadêmico local)."""
import base64
import hashlib
import hmac
import json
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import requests
import urllib3
from websocket import WebSocketBadStatusException, create_connection

from testing import BASE, issue, local_env, token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ISS = 'sac-bahia-mvp'


def assert_http(method, path, expected, auth=None, payload=None):
    headers = {'Authorization': 'Bearer ' + auth} if auth else {}
    r = requests.request(method, BASE + path, headers=headers, json=payload, verify=False, timeout=10)
    if r.status_code != expected:
        raise AssertionError(f'{path}: esperado {expected}, recebido {r.status_code}: {r.text[:300]}')
    return r


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def make_token(payload, secret, alg='HS256'):
    header = {'alg': alg, 'typ': 'JWT'}
    msg = (b64url(json.dumps(header, separators=(',', ':')).encode()) + '.' +
           b64url(json.dumps(payload, separators=(',', ':')).encode()))
    if alg == 'none':
        return msg + '.'
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest()
    return msg + '.' + b64url(sig)


def claims(posto=1, minutes=60, **extra):
    agora = int(time.time())
    base = {'role': 'ATENDENTE', 'posto_id': posto, 'iss': ISS, 'aud': ISS,
            'iat': agora, 'exp': agora + minutes * 60}
    base.update(extra)
    return base


def ws_url():
    p = urlsplit(BASE)
    proto = 'wss' if p.scheme == 'https' else 'ws'
    return urlunsplit((proto, p.netloc, '/ws', '', ''))


def ws_connect(tok):
    opts = {'timeout': 10, 'header': [f'Authorization: Bearer {tok}']}
    if ws_url().startswith('wss'):
        opts['sslopt'] = {'cert_reqs': ssl.CERT_NONE, 'check_hostname': False}
    return create_connection(ws_url(), **opts)


def tls_details():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection(('localhost', 8443), timeout=10) as raw:
        with ctx.wrap_socket(raw, server_hostname='localhost') as s:
            return s.version(), s.cipher()[0]


def main():
    a = issue(1)
    b = issue(1)
    assert_http('GET', f"/api/v1/senhas/{b['senha_id']}", 403, a['token'])
    assert_http('POST', '/api/v1/guiches/1/chamar', 403, a['token'])
    staff = token(1)
    assert_http('POST', '/api/v1/guiches/2/chamar', 403, staff)
    assert_http('GET', f"/api/v1/senhas/{b['senha_id']}", 401)
    print('PASS: roles e isolamento por senha/guichê/posto corretos.')

    env = local_env()
    segredo = env['JWT_SECRET']
    alvo = f"/api/v1/senhas/{b['senha_id']}"

    adulterado = staff[:-1] + ('A' if staff[-1] != 'A' else 'B')
    assert_http('GET', alvo, 401, adulterado)
    print('PASS: JWT com assinatura adulterada retorna 401.')

    assert_http('GET', alvo, 401, make_token(claims(), 'segredo-errado'))
    print('PASS: JWT assinado com outro segredo retorna 401.')

    assert_http('GET', alvo, 401, make_token(claims(minutes=-2), segredo))
    print('PASS: JWT expirado retorna 401.')

    assert_http('GET', alvo, 401, make_token(claims(), '', alg='none'))
    print('PASS: JWT com alg=none retorna 401.')

    errado = claims()
    errado['aud'] = 'outro-servico'
    assert_http('GET', alvo, 401, make_token(errado, segredo))
    errado = claims()
    errado['iss'] = 'outro-emissor'
    assert_http('GET', alvo, 401, make_token(errado, segredo))
    print('PASS: JWT com audiência/emissor divergentes retorna 401.')

    # Token válido (assinado com o segredo real) de ATENDENTE do posto 2 não
    # pode operar guichê do posto 1: prova que o escopo é checado, não só a assinatura.
    assert_http('POST', '/api/v1/guiches/1/chamar', 403, make_token(claims(posto=2), segredo))
    print('PASS: token válido de outro posto retorna 403 no guichê.')

    ws = ws_connect(staff)
    try:
        boas_vindas = json.loads(ws.recv())
        assert boas_vindas.get('tipo') == 'CONECTADO', boas_vindas
    finally:
        ws.close()
    print('PASS: WSS autenticado aceito com mensagem CONECTADO.')

    try:
        ws_connect('token-invalido')
        raise AssertionError('WSS aceitou token inválido')
    except WebSocketBadStatusException as e:
        assert e.status_code == 401, e.status_code
    print('PASS: handshake WSS com token inválido retorna 401.')

    versao, cifra = tls_details()
    assert versao in ('TLSv1.2', 'TLSv1.3'), versao
    print(f'PASS: TLS negociado ({versao}, {cifra}); certificado de desenvolvimento.')

    try:
        ssl.create_default_context().wrap_socket(
            socket.create_connection(('localhost', 8443), timeout=10), server_hostname='localhost')
        raise AssertionError('certificado local foi aceito por CA pública')
    except ssl.SSLCertVerificationError:
        print('PASS: certificado local não é confiável por CA pública (esperado no dev).')

    # A porta 80 do host pode estar ocupada por outro serviço local (neste
    # ambiente, um nginx do WSL). O que importa é que o Compose não publique
    # HTTP puro e que a API não responda por lá.
    portas = subprocess.check_output(
        ['docker', 'compose', 'ps', '--format', '{{.Name}} {{.Ports}}'], text=True)
    assert ':80->' not in portas, portas
    try:
        r = requests.get('http://localhost/api/v1/postos', timeout=3)
        exposto = r.status_code == 200 and '"postos"' in r.text
    except requests.ConnectionError:
        exposto = False
    assert not exposto, 'API respondeu em HTTP puro na porta 80'
    print('PASS: Compose não publica a porta 80; a API só responde via HTTPS/WSS (8443).')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
