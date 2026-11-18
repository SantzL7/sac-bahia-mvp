"""Teste de 2 chamadas simultâneas em guichês distintos do mesmo posto."""
import sys,uuid,requests,urllib3
from concurrent.futures import ThreadPoolExecutor
from testing import issue,token,call
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    # Garante pelo menos duas senhas normais, mas filas já existentes podem entrar antes.
    issue(1,'NORMAL');issue(1,'NORMAL');auth=token(1)
    headers={'Authorization':'Bearer '+auth}
    # Guichês 1 e 3 pertencem ao posto 1 no seed (o 2 e o 4 pertencem ao posto 2).
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(call,'POST',f'/api/v1/guiches/{id}/chamar',headers) for id in (1,3)]
        a,b=[f.result() for f in futures]
    assert a['id']!=b['id'],(a,b)
    print('PASS: dois guichês chamaram senhas diferentes:',a['numero'],b['numero'])

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
