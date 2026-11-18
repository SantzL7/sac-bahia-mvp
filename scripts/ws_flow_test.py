"""Testa o fluxo real outbox -> RabbitMQ -> Worker -> fanout -> WebSocket."""
import json
import ssl
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

import urllib3
from websocket import create_connection, WebSocketTimeoutException
from testing import BASE, call, issue, token

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def psql(sql):
    r = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'sac', '-d', 'sac', '-t', '-A', '-F', '|', '-c', sql],
        capture_output=True, text=True, check=True,
    )
    return [line.split('|') for line in r.stdout.splitlines() if line.strip()]


def log_entries(service):
    r = subprocess.run(
        ['docker', 'compose', 'logs', '--no-color', '--tail=2000', service],
        capture_output=True, text=True, check=True,
    )
    for line in r.stdout.splitlines():
        payload = line.split('| ', 1)[1] if '| ' in line else line
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


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


def recv_event(ws, correlation, tipo, timeout=20):
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


def expect_no_event(ws, correlation, seconds=4):
    deadline = time.monotonic() + seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        ws.settimeout(remaining)
        try:
            msg = json.loads(ws.recv())
        except WebSocketTimeoutException:
            return
        if msg.get('correlation_id') == correlation:
            raise AssertionError(f'evento duplicado entregue no WS: {msg}')


def wait_for_instances(event_id, timeout=15):
    deadline = time.monotonic() + timeout
    observed = set()
    while time.monotonic() < deadline:
        observed = {e.get('instance') for e in log_entries('api')
                    if e.get('message') == 'websocket_forwarded' and e.get('event_id') == event_id}
        if len(observed) >= 2:
            return observed
        time.sleep(1)
    raise AssertionError(f'fanout nao chegou as duas APIs para {event_id}: {observed}')


def wait_for_duplicate(event_id, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for e in log_entries('worker'):
            if e.get('message') == 'duplicate_ignored' and e.get('event_id') == event_id:
                return e
        time.sleep(1)
    raise AssertionError(f'worker nao registrou duplicate_ignored para {event_id}')


def publish_duplicate(event_id):
    r = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'worker', 'node', 'worker/src/republish_event.js', event_id],
        capture_output=True, text=True, check=True,
    )
    assert event_id in r.stdout, (r.stdout, r.stderr)


def main():
    staff = token(2)
    auth = {'Authorization': 'Bearer ' + staff}
    ws1, node1 = connect_ws(staff)
    ws2, node2 = connect_ws(staff)
    print(f'Conexoes WS nos nos: {node1} / {node2}')
    try:
        cor_emit = str(uuid.uuid4())
        t = issue(2, 'NORMAL', correlation=cor_emit)
        recv_event(ws1, cor_emit, 'SENHA_EMITIDA')
        recv_event(ws2, cor_emit, 'SENHA_EMITIDA')
        print('PASS: SENHA_EMITIDA chegou nas duas conexoes WebSocket.')

        cor_call = str(uuid.uuid4())
        called = call('POST', '/api/v1/guiches/2/chamar', {**auth, 'X-Correlation-ID': cor_call})
        assert called['id'] == t['senha_id'], (called, t)
        recv_event(ws1, cor_call, 'SENHA_CHAMADA')
        recv_event(ws2, cor_call, 'SENHA_CHAMADA')
        print('PASS: SENHA_CHAMADA chegou nas duas conexoes WebSocket.')

        cor_fin = str(uuid.uuid4())
        done = call('POST', f"/api/v1/senhas/{t['senha_id']}/finalizar", {**auth, 'X-Correlation-ID': cor_fin})
        assert done['status'] == 'FINALIZADA', done
        recv_event(ws1, cor_fin, 'SENHA_FINALIZADA')
        recv_event(ws2, cor_fin, 'SENHA_FINALIZADA')
        print('PASS: SENHA_FINALIZADA chegou nas duas conexoes WebSocket.')

        rows = psql(f"""SELECT e.id,e.tipo,(e.publicado_em IS NOT NULL),(e.tentativas>=1),
            EXISTS(SELECT 1 FROM eventos_processados p WHERE p.evento_id=e.id)
            FROM eventos e WHERE e.senha_id='{t['senha_id']}' ORDER BY e.criado_em""")
        assert len(rows) == 3, rows
        assert all(row[2] == 't' and row[3] == 't' and row[4] == 't' for row in rows), rows
        events = {row[0]: row[1] for row in rows}
        print('PASS: 3 eventos publicados, com tentativa registrada e processados:', events)

        for event_id in events:
            nos = wait_for_instances(event_id)
            print(f'PASS: fanout de {event_id} nas duas APIs: {sorted(nos)}')

        emit_id = next(eid for eid, tipo in events.items() if tipo == 'SENHA_EMITIDA')
        forwarded_before = {e.get('instance') for e in log_entries('api')
                            if e.get('message') == 'websocket_forwarded' and e.get('event_id') == emit_id}
        publish_duplicate(emit_id)
        duplicate = wait_for_duplicate(emit_id)
        assert psql(f"SELECT COUNT(*) FROM eventos_processados WHERE evento_id='{emit_id}'")[0][0] == '1'
        expect_no_event(ws1, cor_emit)
        expect_no_event(ws2, cor_emit)
        forwarded_after = {e.get('instance') for e in log_entries('api')
                           if e.get('message') == 'websocket_forwarded' and e.get('event_id') == emit_id}
        assert forwarded_after == forwarded_before, (forwarded_before, forwarded_after)
        print('PASS: entrega duplicada ignorada, sem novo fanout:', duplicate.get('correlation_id'))
    finally:
        ws1.close()
        ws2.close()
    print('WS_FLOW_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
