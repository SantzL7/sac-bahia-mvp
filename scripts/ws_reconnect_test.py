"""Derruba a replica que atende o WS e valida reconexao + reconciliacao REST."""
import json
import ssl
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

import requests
import urllib3
from websocket import (WebSocketConnectionClosedException, WebSocketTimeoutException,
                       create_connection)
from testing import BASE, call, issue, token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def connect_ws(token_value):
    parsed = urlsplit(BASE)
    proto = 'wss' if parsed.scheme == 'https' else 'ws'
    url = urlunsplit((proto, parsed.netloc, '/ws', '', ''))
    opts = {'timeout': 15, 'header': [f'Authorization: Bearer {token_value}']}
    if proto == 'wss':
        opts['sslopt'] = {'cert_reqs': ssl.CERT_NONE, 'check_hostname': False}
    ws = create_connection(url, **opts)
    welcome = json.loads(ws.recv())
    assert welcome.get('tipo') == 'CONECTADO', welcome
    return ws, welcome.get('node')


def recv_event(ws, correlation, tipo, timeout=25):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f'{tipo} nao chegou em {timeout}s')
        ws.settimeout(remaining)
        try:
            msg = json.loads(ws.recv())
        except WebSocketTimeoutException:
            raise AssertionError(f'{tipo} nao chegou em {timeout}s')
        if msg.get('tipo') == 'FILA_ATUALIZADA' and msg.get('correlation_id') == correlation and msg.get('evento') == tipo:
            return msg


def api_container_for_node(node):
    ids = run('docker', 'compose', 'ps', '-q', 'api').stdout.split()
    for cid in ids:
        hostname = run('docker', 'inspect', '--format', '{{.Config.Hostname}}', cid).stdout.strip()
        if hostname == node:
            return cid
    raise AssertionError(f'container da API nao encontrado para o no {node}: {ids}')


def wait_api_healthy(cid, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', cid, check=False)
        if r.returncode == 0 and r.stdout.strip() == 'healthy':
            return
        time.sleep(2)
    raise AssertionError(f'replica {cid} nao ficou healthy')


def wait_gateway(timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = requests.get(BASE + '/health/ready', verify=False, timeout=5)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2)
    raise AssertionError('gateway nao respondeu apos a recuperacao')


def main():
    staff = token(1)
    ws, node = connect_ws(staff)
    print('WS conectado no no:', node)
    cid = api_container_for_node(node)
    print('Parando replica:', cid[:12])
    ws2 = None
    try:
        run('docker', 'stop', cid)
        closed = False
        ws.settimeout(20)
        try:
            ws.recv()
        except (WebSocketTimeoutException, WebSocketConnectionClosedException, ConnectionResetError, OSError):
            closed = True
        assert closed, 'a conexao WS nao foi encerrada com a queda da replica'
        print('PASS: conexao WS encerrada apos a queda da replica.')

        deadline = time.monotonic() + 30
        node2 = None
        while time.monotonic() < deadline:
            try:
                ws2, node2 = connect_ws(staff)
                if node2 != node:
                    break
                ws2.close()
                ws2 = None
                time.sleep(2)
            except Exception:
                time.sleep(2)
        assert ws2 is not None and node2 != node, (node, node2)
        print('PASS: reconectado no no sobrevivente:', node2)

        cor = str(uuid.uuid4())
        t = issue(1, 'NORMAL', correlation=cor)
        msg = recv_event(ws2, cor, 'SENHA_EMITIDA')
        print('PASS: evento chegou apos a reconexao:', json.dumps(msg, ensure_ascii=False))

        state = call('GET', f"/api/v1/senhas/{t['senha_id']}", {'Authorization': 'Bearer ' + t['token']})
        assert state['senha_id'] == t['senha_id'] and state['status'] == 'AGUARDANDO', state
        print('PASS: reconciliacao REST retornou o estado AGUARDANDO.')
    finally:
        if ws2 is not None:
            ws2.close()
        ws.close()
        print('Restaurando replica:', cid[:12])
        run('docker', 'start', cid, check=False)
        wait_api_healthy(cid)
        info = wait_gateway()
        print('PASS: replica restaurada e gateway pronto:', info.get('node'))
        ps = run('docker', 'compose', 'ps', '--format', '{{.Name}} {{.Status}}').stdout
        for name in ('sac-bahia-api-1', 'sac-bahia-api-2', 'sac-bahia-postgres-1',
                     'sac-bahia-rabbitmq-1', 'sac-bahia-traefik-1', 'sac-bahia-worker-1'):
            assert name in ps, ps
        # Apenas api, postgres e rabbitmq declaram healthcheck no compose.yaml.
        assert ps.count('healthy') == 4, ps
    print('WS_RECONNECT_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
