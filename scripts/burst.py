"""Teste de 60 emissões simultâneas e unicidade no banco via API."""
import sys
import uuid
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor,as_completed
from testing import issue
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    n=60
    keys=[str(uuid.uuid4()) for _ in range(n)]
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures=[pool.submit(issue,1,'NORMAL',k) for k in keys]
        results=[f.result() for f in as_completed(futures)]
    numbers=[r['numero'] for r in results];ids=[r['senha_id'] for r in results]
    assert len(set(ids))==n,(len(set(ids)),n)
    assert len(set(numbers))==n,(len(set(numbers)),n)
    print(f'PASS: {n} emissões simultâneas; {n} IDs e números únicos.')

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
