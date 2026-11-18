"""Para uma réplica da API; comprova atendimento no nó sobrevivente e recuperação."""
import subprocess
import sys
import time

import requests
import urllib3

from testing import BASE, call, issue

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def hostnames():
    return {cid: run('docker', 'inspect', '--format', '{{.Config.Hostname}}', cid)
            for cid in run('docker', 'compose', 'ps', '-q', 'api').split()}


def ready():
    r = requests.get(BASE + '/health/ready', timeout=6, verify=False)
    r.raise_for_status()
    return r.json()['node']


def esperar_no(nome, timeout=45):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            no = ready()
            if no == nome:
                return no
        except requests.RequestException:
            pass
        time.sleep(1)
    raise AssertionError(f'o nó {nome} não atendeu em {timeout}s')


def esperar_ambos(nomes, timeout=60):
    vistos = set()
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            vistos.add(ready())
        except requests.RequestException:
            pass
        if nomes <= vistos:
            return vistos
        time.sleep(1)
    raise AssertionError(f'nem todas as réplicas voltaram a atender: {sorted(vistos)}')


def emitir_com_retry(timeout=40):
    limite = time.monotonic() + timeout
    ultimo = None
    while time.monotonic() < limite:
        try:
            return issue(1, 'NORMAL')
        except Exception as e:  # noqa: BLE001 — o gateway pode ainda tentar o nó parado
            ultimo = e
            time.sleep(1)
    raise AssertionError(f'emissão não foi atendida durante a queda: {ultimo}')


def main():
    nomes = hostnames()
    if len(nomes) < 2:
        raise RuntimeError('É necessário iniciar com --scale api=2')
    alvo = next(iter(nomes))
    nome_alvo = nomes[alvo]
    sobrevivente = next(n for cid, n in nomes.items() if cid != alvo)
    print(f'Interrompendo réplica {alvo[:12]} ({nome_alvo}); sobrevivente esperado: {sobrevivente}')

    subprocess.check_call(['docker', 'stop', alvo])
    try:
        no = esperar_no(sobrevivente)
        print('PASS: gateway encaminhou ao nó sobrevivente:', no)

        t = emitir_com_retry()
        estado = call('GET', f"/api/v1/senhas/{t['senha_id']}",
                      {'Authorization': 'Bearer ' + t['token']})
        assert estado['status'] == 'AGUARDANDO', estado
        print(f"PASS: nova emissão (senha {t['numero']}) e consulta REST atendidas durante a queda.")
    finally:
        print('Restaurando réplica...')
        subprocess.run(['docker', 'start', alvo], check=False)

    limite = time.monotonic() + 90
    while time.monotonic() < limite:
        status = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', alvo)
        if status == 'healthy':
            break
        time.sleep(2)
    else:
        raise AssertionError('réplica restaurada não ficou healthy')

    vistos = esperar_ambos({nome_alvo, sobrevivente})
    print('PASS: réplica restaurada; ambos os nós voltaram a atender:', sorted(vistos))
    print('CHAOS_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
