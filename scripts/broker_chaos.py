"""Para o RabbitMQ, emite senha, confirma outbox persistido e recupera o fluxo."""
import json
import ssl
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

import requests
import urllib3
from websocket import create_connection, WebSocketTimeoutException
from testing import BASE, issue, token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def psql(sql):
    r = run('docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'sac', '-d', 'sac', '-t', '-A', '-F', '|', '-c', sql)
    return [line.split('|') for line in r.stdout.splitlines() if line.strip()]


def rabbit_ready():
    r = run('docker', 'compose', 'exec', '-T', 'rabbitmq', 'rabbitmq-diagnostics', '-q', 'ping', check=False)
    return r.returncode == 0


def wait_rabbit(timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if rabbit_ready():
            return
        time.sleep(2)
    raise AssertionError('RabbitMQ nao voltou a responder')


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


def recv_event(ws, correlation, tipo, timeout=30):
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


def main():
    staff = token(1)
    ws, node = connect_ws(staff)
    print('WS conectado em:', node)
    try:
        print('Parando RabbitMQ...')
        run('docker', 'compose', 'stop', 'rabbitmq')
        try:
            time.sleep(3)
            r = requests.get(BASE + '/health/ready', verify=False, timeout=10)
            assert r.status_code == 200, (r.status_code, r.text)
            cor = str(uuid.uuid4())
            t = issue(1, 'NORMAL', correlation=cor)
            print('Senha emitida com broker parado:', t['senha_id'])
            assert psql(f"SELECT status FROM senhas WHERE id='{t['senha_id']}'")[0][0] == 'AGUARDANDO'
            assert psql(f"SELECT COUNT(*) FROM eventos WHERE correlation_id='{cor}' AND publicado_em IS NULL")[0][0] == '1'
            print('PASS: senha e evento persistidos no outbox com o broker parado.')
        finally:
            print('Reiniciando RabbitMQ...')
            run('docker', 'compose', 'start', 'rabbitmq', check=False)
        wait_rabbit()
        print('RabbitMQ pronto; aguardando publicacao e processamento...')
        published = processed = False
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            published = psql(f"SELECT COUNT(*) FROM eventos WHERE correlation_id='{cor}' AND publicado_em IS NOT NULL")[0][0] == '1'
            processed = psql(f"SELECT COUNT(*) FROM eventos e JOIN eventos_processados p ON p.evento_id=e.id WHERE e.correlation_id='{cor}'")[0][0] == '1'
            if published and processed:
                break
            time.sleep(2)
        assert published and processed, (published, processed)
        print('PASS: evento publicado e processado apos a recuperacao.')
        # A notificacao do primeiro evento pode ter sido emitida antes de o
        # subscriber da API reconectar. O estado de negocio ja esta no banco;
        # um novo evento comprova que o caminho WS voltou a funcionar.
        time.sleep(5)
        cor2 = str(uuid.uuid4())
        t2 = issue(1, 'NORMAL', correlation=cor2)
        msg = recv_event(ws, cor2, 'SENHA_EMITIDA', timeout=30)
        print('PASS: WS recebeu um novo evento apos a recuperacao:', json.dumps(msg, ensure_ascii=False))
        assert psql(f"SELECT status FROM senhas WHERE id='{t['senha_id']}'")[0][0] == 'AGUARDANDO'
        assert psql(f"SELECT status FROM senhas WHERE id='{t2['senha_id']}'")[0][0] == 'AGUARDANDO'
        print('PASS: nenhuma senha perdida; ambas permanecem AGUARDANDO.')
    finally:
        ws.close()
        run('docker', 'compose', 'start', 'rabbitmq', check=False)
        wait_rabbit()
    print('BROKER_CHAOS_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
