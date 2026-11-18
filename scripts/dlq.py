"""Injeta mensagem malformada e confere incremento de DLQ via rabbitmqctl."""
import subprocess
import sys
import time


def count():
    r = subprocess.run(
        ['docker', 'compose', 'exec', '-T', 'rabbitmq', 'rabbitmqctl', '-q', 'list_queues',
         'name', 'messages', 'messages_unacknowledged'],
        capture_output=True, text=True, check=True,
    )
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == 'sac.events.dlq':
            return int(parts[1]) + int(parts[2])
    return 0


def main():
    before = count()
    subprocess.run(['docker', 'compose', 'exec', '-T', 'worker', 'node', 'worker/src/inject_poison.js'], check=True)
    for _ in range(18):
        time.sleep(1)
        after = count()
        if after > before:
            print(f'PASS: DLQ aumentou de {before} para {after} mensagem(ns) apos retries.')
            return
    raise AssertionError('DLQ nao recebeu a mensagem; verifique logs do worker')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
