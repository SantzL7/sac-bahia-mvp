"""Dispara evento com Correlation ID; verifica traces nos logs agregados."""
import sys,time,subprocess,uuid,json
import urllib3
from testing import issue
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    cor=str(uuid.uuid4())
    t=issue(correlation=cor)
    print('Senha:',t['senha_id'],'Correlation ID:',cor)
    print('Aguardando publicação e processamento do evento (8s)...')
    time.sleep(8)
    r=subprocess.run(['docker','compose','logs','--no-color','api','worker'],capture_output=True,text=True,check=True)
    lines=[line for line in r.stdout.splitlines() if cor in line]
    for line in lines:print(line[:450])
    has_api=any('event_persisted' in line for line in lines)
    has_worker=any('event_processed' in line or 'duplicate_ignored' in line for line in lines)
    assert has_api and has_worker, 'Rastreio incompleto: verifique backlog e logs do broker'
    print('PASS: evento correlacionado entre API e Worker.')

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
