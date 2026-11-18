"""Verifica que segredos locais não aparecem em arquivos nem nos logs."""
import re
import subprocess
import sys

from testing import ROOT, local_env

IGNORAR = {'.env', 'node_modules', '.venv', '.git', '__pycache__', '.pytest_cache',
           'evidencias-locais', 'postgres_data', 'rabbitmq_data'}
CHAVES = ('DB_PASSWORD', 'RABBITMQ_PASSWORD', 'JWT_SECRET', 'STAFF_PASSWORD')
PADROES = {
    'chave AWS': re.compile(r'AKIA[0-9A-Z]{16}'),
    'segredo AWS': re.compile(r'aws_secret_access_key\s*=', re.I),
    'JWT': re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'),
}


def arquivos_texto():
    for p in ROOT.rglob('*'):
        if not p.is_file():
            continue
        if any(part in IGNORAR for part in p.parts):
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
            yield p, p.read_text(encoding='utf8', errors='ignore')
        except OSError:
            continue


def main():
    env = local_env()
    segredos = {k: env[k] for k in CHAVES if len(env.get(k, '')) >= 8}
    assert len(segredos) == len(CHAVES), 'chaves esperadas ausentes no .env'

    total = 0
    achados = []
    padroes = []
    for p, texto in arquivos_texto():
        total += 1
        for chave, valor in segredos.items():
            if valor in texto:
                achados.append((str(p.relative_to(ROOT)), chave))
        for nome, regex in PADROES.items():
            if regex.search(texto):
                padroes.append((str(p.relative_to(ROOT)), nome))
    assert not achados, f'segredos locais encontrados em arquivos: {achados}'
    assert not padroes, f'padrões de segredo encontrados: {padroes}'
    print(f'PASS: {len(segredos)} segredos e padrões AWS/JWT ausentes em {total} arquivos do projeto.')

    logs = subprocess.run(['docker', 'compose', 'logs', '--no-color'],
                          capture_output=True, text=True).stdout
    vazados = [k for k, v in segredos.items() if v in logs]
    assert not vazados, f'segredos presentes nos logs: {vazados}'
    print(f'PASS: segredos ausentes em {len(logs.splitlines())} linhas de log dos containers.')

    gitignore = (ROOT / '.gitignore').read_text(encoding='utf8')
    for item in ('.env', '.venv/', 'node_modules/'):
        assert item in gitignore, f'.gitignore sem {item}'
    assert not list((ROOT / 'infra' / 'terraform').glob('*.tfvars')), 'tfvars presente'
    print('PASS: .gitignore cobre .env/.venv/node_modules e não há tfvars locais.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FAIL:', e, file=sys.stderr)
        sys.exit(1)
