"""Comprova que o Traefik distribui requisições entre as duas réplicas da API."""
import collections
import json
import subprocess
import sys

import requests
import urllib3

from testing import BASE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AMOSTRAS = 20


def hostnames():
    ids = subprocess.check_output(['docker', 'compose', 'ps', '-q', 'api'], text=True).split()
    nomes = {}
    for cid in ids:
        nome = subprocess.check_output(
            ['docker', 'inspect', '--format', '{{.Config.Hostname}}', cid], text=True).strip()
        nomes[cid] = nome
    return nomes


def dns_no_api():
    container = subprocess.check_output(
        ['docker', 'compose', 'ps', '-q', 'api'], text=True).split()[0]
    script = ("const dns=require('node:dns').promises;"
              "Promise.all(['postgres','rabbitmq'].map(n=>dns.lookup(n)))"
              ".then(r=>console.log(JSON.stringify(r.map(x=>x.address))))")
    out = subprocess.check_output(['docker', 'exec', container, 'node', '-e', script], text=True).strip()
    enderecos = json.loads(out)
    assert len(enderecos) == 2 and all(enderecos), out
    return enderecos


def main():
    nomes = hostnames()
    if len(nomes) < 2:
        raise RuntimeError('É necessário iniciar com --scale api=2')
    print('Réplicas:', ', '.join(f'{cid[:12]}={nome}' for cid, nome in nomes.items()))

    enderecos = dns_no_api()
    print('PASS: API resolve postgres e rabbitmq por nome Docker:', enderecos)

    vistos = collections.Counter()
    erros = 0
    for _ in range(AMOSTRAS):
        try:
            r = requests.get(BASE + '/health/ready', verify=False, timeout=8)
            if r.status_code != 200:
                erros += 1
                continue
            vistos[r.json()['node']] += 1
        except requests.RequestException:
            erros += 1

    print(f'Distribuição de {AMOSTRAS} requisições:', dict(vistos), 'erros:', erros)
    assert erros == 0, f'{erros} requisições falharam'
    assert set(vistos) == set(nomes.values()), f'{AMOSTRAS} requisições não chegaram às duas réplicas: {dict(vistos)}'

    logs = subprocess.check_output(
        ['docker', 'compose', 'logs', '--no-color', '--tail=400', 'api'], text=True)
    for nome in nomes.values():
        assert f'"instance":"{nome}"' in logs, f'logs da API não mostram a instância {nome}'
    print('PASS: as duas réplicas atenderam e aparecem nos logs JSON.')
    print('PASS: balanceamento entre réplicas comprovado por respostas e logs.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
