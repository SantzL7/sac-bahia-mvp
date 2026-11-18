"""Cria .env local aleatório. Não sobrescreve segredos existentes."""
from pathlib import Path
import sys
import secrets

root = Path(__file__).resolve().parents[1]
path = root / '.env'
if path.exists():
    raise SystemExit('Arquivo .env já existe; não será sobrescrito.')
values = {
    'DB_PASSWORD': secrets.token_urlsafe(24),
    'RABBITMQ_PASSWORD': secrets.token_urlsafe(24),
    'JWT_SECRET': secrets.token_urlsafe(48),
    'STAFF_PASSWORD': secrets.token_urlsafe(18),
    'STAFF_USERNAME': 'atendente',
    'AWS_SECRET_ID': '',
    'AWS_REGION': 'sa-east-1',
}
path.write_text(''.join(f'{k}={v}\n' for k,v in values.items()),encoding='utf8')
try:
    path.chmod(0o600)
except OSError:
    pass
print(f'.env criado: {path}')
if '--quiet' not in sys.argv:
    print('Credenciais de demonstração — mantenha fora do Git:')
    print(f"  usuário: {values['STAFF_USERNAME']}")
    print(f"  senha:   {values['STAFF_PASSWORD']}")
