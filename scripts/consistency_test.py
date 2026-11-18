"""Testes F2: idempotencia concorrente e atomicidade senha + evento."""
import sys
import uuid
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor
from testing import BASE
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def post_issue(key, cat='NORMAL', posto=1):
    return requests.post(
        f'{BASE}/api/v1/postos/{posto}/senhas',
        headers={'Idempotency-Key': key},
        json={'categoria': cat},
        timeout=20,
        verify=False,
    )


def test_same_key_same_payload():
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as ex:
        rs = [f.result() for f in [ex.submit(post_issue, key) for _ in range(2)]]
    assert all(r.status_code in (200, 201) for r in rs), [(r.status_code, r.text) for r in rs]
    ids = {r.json()['senha_id'] for r in rs}
    assert len(ids) == 1, ids
    reused = sorted(r.json()['reutilizada'] for r in rs)
    assert reused == [False, True], reused
    assert sum(r.status_code == 201 for r in rs) == 1, [r.status_code for r in rs]
    print(f'PASS: mesma chave e mesmo payload -> 1 senha ({list(ids)[0]}), reutilizada={reused}')


def test_same_key_divergent_payload():
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(post_issue, key, 'NORMAL'), ex.submit(post_issue, key, 'PRIORITARIA')]
        rs = [f.result() for f in fs]
    codes = sorted(r.status_code for r in rs)
    assert codes == [201, 409], [(r.status_code, r.text) for r in rs]
    winner = next(r for r in rs if r.status_code == 201).json()
    # Garante tambem o caminho deterministico de reuso com payload divergente.
    other = 'PRIORITARIA' if winner['categoria'] == 'NORMAL' else 'NORMAL'
    again = post_issue(key, other)
    assert again.status_code == 409, (again.status_code, again.text)
    print(f"PASS: mesma chave com payload divergente -> 201/409; senha {winner['senha_id']}; reuso posterior 409")


def main():
    test_same_key_same_payload()
    test_same_key_divergent_payload()
    print('CONSISTENCY_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
