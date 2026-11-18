"""Smoke test reproduzível com saída PASS/FAIL e código de erro."""
import sys
import requests
import uuid
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from testing import call,issue,token,BASE

def main():
    postos=call('GET','/api/v1/postos')['postos'];assert len(postos)>=2
    fila=call('GET','/api/v1/postos/1/fila');assert 'tempo_espera_minutos' in fila
    key=str(uuid.uuid4())
    t=issue(key=key)
    same=issue(key=key)
    assert t['senha_id']==same['senha_id'] and same['reutilizada']
    try:
        call('POST','/api/v1/postos/1/senhas',{'Idempotency-Key':key},{'categoria':'PRIORITARIA'})
        raise AssertionError('Esperava HTTP 409 em payload divergente')
    except AssertionError as e:
        if '409' not in str(e):raise
    mine=call('GET',f"/api/v1/senhas/{t['senha_id']}",{'Authorization':'Bearer '+t['token']})
    assert mine['status']=='AGUARDANDO'
    staff=token(1)
    called_ids=[]
    # O limite acompanha a fila para nao gerar falso negativo com backlog grande.
    limit=fila['quantidade_aguardando']+10
    for _ in range(limit):
        called=call('POST','/api/v1/guiches/1/chamar',{'Authorization':'Bearer '+staff})
        called_ids.append(called['id'])
        if called['id']==t['senha_id']:break
    else:raise AssertionError(f'Senha nao chamada no limite do teste ({limit})')
    done=call('POST',f"/api/v1/senhas/{t['senha_id']}/finalizar",{'Authorization':'Bearer '+staff})
    assert done['status']=='FINALIZADA'
    print('PASS: REST/contrato, idempotência, RBAC, consulta, chamada, finalização.')

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
