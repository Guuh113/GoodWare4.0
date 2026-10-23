"""Diagnostico seguro da conexao Aegis AI (GoodWare) com Ollama/Groq.
Coloque este arquivo ao lado de app.py e .env; execute com o Python do GoodWare.
Nao imprime segredos nem altera o projeto.
"""
import json
import re
import socket
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DOTENV = ROOT / '.env'

try:
    from dotenv import dotenv_values
except ImportError:
    print('ERRO: python-dotenv nao instalado no Python usado.')
    print('Execute pelo Python da pasta .venv\\Scripts\\python.exe do GoodWare.')
    sys.exit(2)

print('=== Diagnostico Aegis AI (sem exibir credenciais) ===')
print('Pasta:', ROOT)
if not DOTENV.is_file():
    print('ERRO: arquivo .env nao encontrado nesta pasta.')
    sys.exit(2)

raw = DOTENV.read_text(encoding='utf-8-sig', errors='replace')
keys = re.findall(r'^\s*(LLM_BASE_URL|LLM_MODEL|LLM_API_KEY)\s*=', raw, flags=re.MULTILINE)
repeated = [k for k, n in Counter(keys).items() if n > 1]
if repeated:
    print('ATENCAO: linhas duplicadas:', ', '.join(repeated), '(a ultima costuma prevalecer).')

config = dotenv_values(DOTENV)
url = (config.get('LLM_BASE_URL') or '').strip().rstrip('/')
model = (config.get('LLM_MODEL') or '').strip()
api_key = (config.get('LLM_API_KEY') or '').strip()
print('LLM_BASE_URL:', url or '[VAZIO]')
print('LLM_MODEL:', model or '[VAZIO]')
print('LLM_API_KEY:', 'CONFIGURADA (valor oculto)' if api_key else '[VAZIA]')

if not url or not model:
    print('ERRO: preencha LLM_BASE_URL e LLM_MODEL no .env.')
    sys.exit(2)

parsed = urlparse(url)
if (parsed.scheme not in ('http', 'https')
        or (parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'))):
    print('ERRO: URL de IA deve usar HTTPS remoto ou HTTP somente local.')
    sys.exit(2)

if 'api.groq.com' in (parsed.hostname or '').lower() and not api_key:
    print('ERRO: a chave LLM_API_KEY e obrigatoria para o Groq.')
    sys.exit(2)

headers = {'Content-Type': 'application/json'}
if api_key:
    headers['Authorization'] = 'Bearer ' + api_key

# Uma requisicao minima reproduz o formato esperado pelo assistant_service.py.
payload = {
    'model': model,
    'messages': [{'role': 'user', 'content': 'Responda somente: Aegis OK'}],
    'max_tokens': 256,
    'stream': False,
}
if model.startswith('openai/gpt-oss-'):
    payload['reasoning_effort'] = 'low'

print('Teste: POST /chat/completions ...')
req = Request(url + '/chat/completions', data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
try:
    with urlopen(req, timeout=90) as response:
        result = json.loads(response.read(200_000).decode('utf-8'))
    content = result.get('choices', [{}])[0].get('message', {}).get('content')
    if content:
        print('SUCESSO: modelo respondeu. A conexao com a API esta funcionando.')
        print('Resposta recebida:', repr(str(content)[:150]))
    else:
        print('ATENCAO: HTTP 200, mas nenhum texto foi retornado. Verifique max_tokens/reasoning.')
except HTTPError as exc:
    print('ERRO HTTP:', exc.code)
    try:
        obj = json.loads(exc.read(8192).decode('utf-8', errors='replace'))
        detail = str(obj.get('error', {}).get('message', 'Resposta de erro nao detalhada.'))
        for secret in (api_key, config.get('SECRET_KEY') or ''):
            if secret:
                detail = detail.replace(secret, '[OCULTO]')
        print('Motivo informado pelo provedor:', detail[:450])
    except Exception:
        print('Nao foi possivel interpretar o detalhe do erro.')
    if exc.code == 401:
        print('Verifique se a chave de API esta correta e ativa.')
    elif exc.code == 429:
        print('Limite de uso/requisicoes atingido. Consulte o painel do provedor.')
    elif exc.code == 404:
        print('Confira a URL e o nome exato do modelo.')
except (URLError, TimeoutError, socket.timeout) as exc:
    print('ERRO DE CONEXAO:', type(exc).__name__)
    print('Verifique rede, firewall e se o servico esta em execucao.')
except Exception as exc:
    print('ERRO INESPERADO:', type(exc).__name__)
    print('Verifique compatibilidade de formato da resposta com Chat Completions.')
