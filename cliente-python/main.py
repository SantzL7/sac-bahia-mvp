"""Cliente REST + WebSocket para o protótipo acadêmico SAC Bahia.
A opção --inseguro é exclusiva para o certificado de desenvolvimento do Traefik.
"""
import argparse
import json
import os
import ssl
import sys
import time
import uuid
from urllib.parse import urlsplit, urlunsplit
import requests


def parser_builder():
    p=argparse.ArgumentParser(description='Cliente do SAC Bahia (simulação acadêmica)')
    p.add_argument('--url',default=os.getenv('SAC_URL','https://localhost:8443'),help='URL base do gateway')
    p.add_argument('--inseguro',action='store_true',help='Apenas demo local: ignora validação TLS')
    sub=p.add_subparsers(dest='comando',required=True)
    sub.add_parser('postos',help='Listar postos')
    f=sub.add_parser('fila');f.add_argument('--posto',type=int,required=True)
    e=sub.add_parser('emitir');e.add_argument('--posto',type=int,required=True);e.add_argument('--categoria',choices=['NORMAL','PRIORITARIA'],default='NORMAL');e.add_argument('--chave',help='Idempotency-Key opcional')
    l=sub.add_parser('login');l.add_argument('--posto',type=int,required=True);l.add_argument('--usuario',default='atendente');l.add_argument('--senha',help='Se omitida, pede senha sem ecoar')
    c=sub.add_parser('consultar');c.add_argument('--senha-id',required=True);c.add_argument('--token',default=os.getenv('SAC_TOKEN'))
    ch=sub.add_parser('chamar');ch.add_argument('--guiche',type=int,required=True);ch.add_argument('--token',default=os.getenv('SAC_TOKEN'))
    fin=sub.add_parser('finalizar');fin.add_argument('--senha-id',required=True);fin.add_argument('--token',default=os.getenv('SAC_TOKEN'))
    a=sub.add_parser('acompanhar');a.add_argument('--posto',type=int,required=True);a.add_argument('--token',default=os.getenv('SAC_TOKEN'));a.add_argument('--senha-id',help='Se informado, consulta estado após cada evento')
    return p


def call(base,method,path,token=None,payload=None,headers=None,verify=True):
    url=base.rstrip('/')+path
    h=dict(headers or {})
    if token:h['Authorization']=f'Bearer {token}'
    try:
        r=requests.request(method,url,json=payload,headers=h,timeout=6,verify=verify)
    except requests.RequestException as e:
        raise RuntimeError(f'Falha de rede: {e}') from e
    try:data=r.json()
    except ValueError:data={'erro':r.text[:300]}
    if not r.ok:raise RuntimeError(f'HTTP {r.status_code}: {json.dumps(data,ensure_ascii=False)}')
    return data


def follow(args,verify):
    from websocket import create_connection, WebSocketTimeoutException
    if not args.token:raise RuntimeError('Informe --token ou variável SAC_TOKEN')
    parsed=urlsplit(args.url)
    protocol='wss' if parsed.scheme=='https' else 'ws'
    url=urlunsplit((protocol,parsed.netloc,'/ws','',''))
    print('Conectando ao canal de eventos; Ctrl+C encerra. Reconecta após falhas.')
    while True:
        try:
            kwargs={'header':[f'Authorization: Bearer {args.token}'],'timeout':8}
            if protocol=='wss' and not verify:
                kwargs['sslopt']={'cert_reqs':ssl.CERT_NONE,'check_hostname':False}
            ws=create_connection(url,**kwargs)
            try:
                # O timeout acima vale para o handshake; depois disso a espera
                # por eventos pode ficar ociosa sem ser tratada como falha.
                ws.settimeout(60)
                # Não há polling HTTP; a consulta ocorre apenas após evento ou reconexão.
                if args.senha_id:
                    print(json.dumps(call(args.url,'GET',f'/api/v1/senhas/{args.senha_id}',args.token,verify=verify),ensure_ascii=False))
                while True:
                    try:
                        message=ws.recv()
                    except WebSocketTimeoutException:
                        continue
                    if not message:raise RuntimeError('Canal encerrado')
                    event=json.loads(message)
                    if event.get('posto_id')!=args.posto:continue
                    print('Evento:',json.dumps(event,ensure_ascii=False))
                    if args.senha_id and event.get('tipo')=='FILA_ATUALIZADA':
                        print('Estado:',json.dumps(call(args.url,'GET',f'/api/v1/senhas/{args.senha_id}',args.token,verify=verify),ensure_ascii=False))
            finally:ws.close()
        except KeyboardInterrupt:return
        except Exception as e:
            print(f'Conexão indisponível: {e}; reconectando em 3 segundos...',file=sys.stderr)
            time.sleep(3)


def main():
    args=parser_builder().parse_args()
    if args.inseguro:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if not args.inseguro and args.url.startswith('https://localhost'):
        print('Para o certificado local gerado automaticamente pelo Traefik, use --inseguro. Não use em produção.',file=sys.stderr)
    try:
        verify=not args.inseguro
        if args.comando=='acompanhar':return follow(args,verify)
        if args.comando=='postos':out=call(args.url,'GET','/api/v1/postos',verify=verify)
        elif args.comando=='fila':out=call(args.url,'GET',f'/api/v1/postos/{args.posto}/fila',verify=verify)
        elif args.comando=='emitir':
            key=args.chave or str(uuid.uuid4())
            out=call(args.url,'POST',f'/api/v1/postos/{args.posto}/senhas',
                payload={'categoria':args.categoria},headers={'Idempotency-Key':key},verify=verify)
            print('Idempotency-Key:',key)
        elif args.comando=='login':
            import getpass
            password=args.senha or getpass.getpass('Senha de atendente: ')
            out=call(args.url,'POST','/api/v1/auth/atendente',payload={'usuario':args.usuario,'senha':password,'posto_id':args.posto},verify=verify)
        else:
            if not args.token:raise RuntimeError('Informe --token ou variável SAC_TOKEN')
            if args.comando=='consultar':out=call(args.url,'GET',f'/api/v1/senhas/{args.senha_id}',token=args.token,verify=verify)
            elif args.comando=='chamar':out=call(args.url,'POST',f'/api/v1/guiches/{args.guiche}/chamar',token=args.token,verify=verify)
            elif args.comando=='finalizar':out=call(args.url,'POST',f'/api/v1/senhas/{args.senha_id}/finalizar',token=args.token,verify=verify)
        print(json.dumps(out,ensure_ascii=False,indent=2))
    except (RuntimeError,requests.RequestException) as e:
        print(f'Erro: {e}',file=sys.stderr);sys.exit(1)

if __name__=='__main__':main()
