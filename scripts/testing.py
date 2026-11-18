"""Utilitários dos testes de integração (somente ambiente local)."""
from pathlib import Path
import os
import requests
import uuid

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('SAC_URL','https://localhost:8443')

def local_env():
    p=ROOT/'.env'
    if not p.exists():raise RuntimeError('Crie .env com python scripts/setup_env.py')
    result={}
    for line in p.read_text(encoding='utf8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k,v=line.split('=',1);result[k]=v
    return result

def call(method,path,headers=None,payload=None,expected=(200,)):
    r=requests.request(method,BASE+path,headers=headers,json=payload,timeout=20,verify=False)
    if r.status_code not in expected:raise AssertionError(f'{method} {path}: {r.status_code} {r.text}')
    return r.json()

def issue(posto=1,cat='NORMAL',key=None,correlation=None):
    key=key or str(uuid.uuid4())
    headers={'Idempotency-Key':key}
    if correlation:headers['X-Correlation-ID']=correlation
    return call('POST',f'/api/v1/postos/{posto}/senhas',headers,{'categoria':cat},(200,201))

def token(posto=1):
    env=local_env()
    result=call('POST','/api/v1/auth/atendente',payload={'usuario':env['STAFF_USERNAME'],'senha':env['STAFF_PASSWORD'],'posto_id':posto})
    return result['token']
