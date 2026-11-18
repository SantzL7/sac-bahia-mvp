"""Comprova a agregação de logs do Dozzle (profile observabilidade)."""
import json
import sys

import requests

URL = 'http://127.0.0.1:8081'
SERVICOS = {
    'sac-bahia-api-1', 'sac-bahia-api-2', 'sac-bahia-worker-1',
    'sac-bahia-postgres-1', 'sac-bahia-rabbitmq-1', 'sac-bahia-traefik-1',
}


def containers_do_stream():
    with requests.get(URL + '/api/events/stream', stream=True, timeout=15) as r:
        assert r.status_code == 200, r.status_code
        buf = ''
        for chunk in r.iter_content(chunk_size=4096):
            buf += chunk.decode('utf-8', errors='replace')
            if 'event: containers-changed' in buf:
                secao = buf.split('event: containers-changed', 1)[1]
                for linha in secao.splitlines(keepends=True):
                    if linha.startswith('data: ') and linha.endswith('\n'):
                        return json.loads(linha[6:].strip())
            if len(buf) > 2_000_000:
                break
    raise AssertionError('stream do Dozzle sem evento containers-changed completo')


def main():
    r = requests.get(URL + '/', timeout=10)
    assert r.status_code == 200, r.status_code
    assert '<title>Dozzle</title>' in r.text, 'UI do Dozzle não respondeu como esperado'
    print('PASS: UI agregada do Dozzle responde em', URL)

    containers = containers_do_stream()
    nomes = {c['name'] for c in containers}
    faltando = SERVICOS - nomes
    assert not faltando, f'Dozzle não lista: {sorted(faltando)}'
    rodando = sorted(c['name'] for c in containers if c.get('state') == 'running' and c['name'] in SERVICOS)
    print('PASS: Dozzle lista os 6 serviços do projeto; em execução:', ', '.join(rodando))
    print('TELEMETRY_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
