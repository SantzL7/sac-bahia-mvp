"""Testa a notificação do RabbitMQ entre API e cliente WebSocket."""
import sys,uuid,json,ssl,time,requests,urllib3
from websocket import create_connection
from testing import BASE,issue,call
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    ticket=issue(1,'NORMAL')
    url=BASE.replace('https://','wss://').replace('http://','ws://')+'/ws'
    opts={'timeout':15,'header':[f"Authorization: Bearer {ticket['token']}"]}
    if url.startswith('wss'):opts['sslopt']={'cert_reqs':ssl.CERT_NONE,'check_hostname':False}
    ws=create_connection(url,**opts)
    try:
        welcome=json.loads(ws.recv());assert welcome['tipo']=='CONECTADO'
        issue(1,'NORMAL')
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            e=json.loads(ws.recv())
            if e.get('tipo')=='FILA_ATUALIZADA' and e.get('posto_id')==1:
                print('PASS: evento entregue por WebSocket:',json.dumps(e,ensure_ascii=False));return
        raise AssertionError('Nenhum evento WebSocket chegou em 15 segundos')
    finally:ws.close()

if __name__=='__main__':
    try:main()
    except Exception as e:print('FAIL:',e,file=sys.stderr);sys.exit(1)
