"""Valida o circuit breaker do worker durante queda e retorno do RabbitMQ."""
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from testing import issue


def run(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def logs_since(since):
    r = run('docker', 'compose', 'logs', '--no-color', '--since', since, 'worker')
    for line in r.stdout.splitlines():
        payload = line.split('| ', 1)[1] if '| ' in line else line
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def psql(sql):
    r = run('docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'sac', '-d', 'sac', '-t', '-A', '-c', sql)
    return r.stdout.strip()


def rabbit_ready():
    r = run('docker', 'compose', 'exec', '-T', 'rabbitmq', 'rabbitmq-diagnostics', '-q', 'ping', check=False)
    return r.returncode == 0


def wait_rabbit(timeout=120):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if rabbit_ready():
            return
        time.sleep(2)
    raise AssertionError('RabbitMQ não voltou a responder')


def esperar_log(since, mensagem, timeout, campo=None, valor=None):
    limite = time.monotonic() + timeout
    vistos = []
    while time.monotonic() < limite:
        vistos = [e for e in logs_since(since) if e.get('message') == mensagem]
        if campo:
            vistos = [e for e in vistos if e.get(campo) == valor]
        if vistos:
            return vistos[0]
        time.sleep(2)
    raise AssertionError(f'log {mensagem} não apareceu em {timeout}s')


def main():
    assert rabbit_ready(), 'RabbitMQ precisa estar saudável para iniciar o teste'
    since = (datetime.now(timezone.utc) - timedelta(seconds=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
    print('Parando RabbitMQ para forçar falhas do relay...')
    run('docker', 'compose', 'stop', 'rabbitmq')
    try:
        aberto = esperar_log(since, 'circuit_opened', 90)
        print('PASS: circuito aberto após falhas consecutivas:', aberto.get('failures'))

        falhas = esperar_log(since, 'outbox_relay_retry', 90, 'breaker', 'OPEN')
        print('PASS: relay registrou breaker OPEN:', falhas.get('error'))
    finally:
        print('Reiniciando RabbitMQ...')
        run('docker', 'compose', 'start', 'rabbitmq', check=False)
        wait_rabbit()

    meio = esperar_log(since, 'circuit_half_open', 90)
    print('PASS: circuito passou a HALF_OPEN para testar recuperação:', meio.get('message'))

    fechado = esperar_log(since, 'circuit_closed', 90)
    print('PASS: circuito fechado após o broker voltar:', fechado.get('message'))

    cor = str(uuid.uuid4())
    t = issue(1, 'NORMAL', correlation=cor)
    publicado = processado = False
    limite = time.monotonic() + 45
    while time.monotonic() < limite:
        publicado = psql(f"SELECT COUNT(*) FROM eventos WHERE correlation_id='{cor}' AND publicado_em IS NOT NULL") == '1'
        processado = psql(f"SELECT COUNT(*) FROM eventos e JOIN eventos_processados p ON p.evento_id=e.id WHERE e.correlation_id='{cor}'") == '1'
        if publicado and processado:
            break
        time.sleep(2)
    assert publicado and processado, (publicado, processado)
    print(f"PASS: senha {t['numero']} publicada e processada após a recuperação.")
    print('CIRCUIT_BREAKER_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
