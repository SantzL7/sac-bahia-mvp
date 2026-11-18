"""Prova que o CLI mantem o WebSocket ocioso aberto (>8s) sem reconectar."""
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from testing import issue, token

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]


def ler(caminho):
    try:
        return Path(caminho).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def esperar(proc, caminho, texto, timeout, contexto):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if texto in ler(caminho):
            return
        if proc.poll() is not None:
            raise AssertionError(f'CLI terminou antes de {contexto}: {ler(caminho)[-800:]}')
        time.sleep(0.5)
    raise AssertionError(f'{contexto} nao ocorreu em {timeout}s: {ler(caminho)[-800:]}')


def main():
    tok = token(1)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', SAC_TOKEN=tok)
    saida = tempfile.NamedTemporaryFile('w', delete=False, suffix='.out.log').name
    erros = tempfile.NamedTemporaryFile('w', delete=False, suffix='.err.log').name
    with open(saida, 'w', encoding='utf-8') as out, open(erros, 'w', encoding='utf-8') as err:
        proc = subprocess.Popen(
            [sys.executable, '-u', str(ROOT / 'cliente-python' / 'main.py'),
             '--inseguro', 'acompanhar', '--posto', '1'],
            stdout=out, stderr=err, env=env, cwd=str(ROOT),
        )
    try:
        esperar(proc, saida, 'Conectando ao canal de eventos', 20, 'conexao do CLI')
        print('PASS: CLI conectado ao WebSocket.')

        cor1 = str(uuid.uuid4())
        issue(1, 'NORMAL', correlation=cor1)
        esperar(proc, saida, cor1, 20, 'primeiro evento')
        print('PASS: evento recebido pelo CLI.')

        print('Aguardando 15s de ociosidade (acima do timeout de 8s do handshake)...')
        time.sleep(15)
        log = ler(saida) + ler(erros)
        assert 'Conexao indisponivel' not in log and 'Conexão indisponível' not in log, log[-800:]
        assert 'reconectando em 3 segundos' not in log, log[-800:]
        assert proc.poll() is None, 'CLI encerrou durante a ociosidade'
        print('PASS: nenhuma reconexao durante a ociosidade; processo segue ativo.')

        cor2 = str(uuid.uuid4())
        issue(1, 'NORMAL', correlation=cor2)
        esperar(proc, saida, cor2, 20, 'segundo evento apos ociosidade')
        print('PASS: evento apos a ociosidade entregue na mesma conexao.')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    print('CLI_IDLE_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
