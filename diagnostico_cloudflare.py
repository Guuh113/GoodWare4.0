"""Teste mínimo se 403 decorre do User-Agent padrão do urllib.
NÃO lê nem mostra credenciais. Execute na pasta do GoodWare com Python do .venv.
"""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
from dotenv import dotenv_values

cfg = dotenv_values(Path.cwd()/'.env')
base = str(cfg.get('LLM_BASE_URL') or '').strip().rstrip('/')
if base != 'https://api.groq.com/openai/v1':
    raise SystemExit('ERRO: configure LLM_BASE_URL=https://api.groq.com/openai/v1 primeiro')

for label, ua in [('Python urllib padrão', None), ('Identificação GoodWare', 'GoodWare-Aegis/4.0')]:
    headers={'Accept': 'application/json'}
    if ua:
        headers['User-Agent']=ua
    req=Request(base+'/models',headers=headers)
    try:
        with urlopen(req,timeout=25) as res:
            print(f'{label}: HTTP {res.status}')
    except HTTPError as e:
        print(f'{label}: HTTP {e.code}, server={e.headers.get("Server", "indefinido")}')
    except (URLError, TimeoutError) as e:
        print(f'{label}: falha de conexão ({type(e).__name__})')
print('Leitura esperada: 403 no urllib padrão e 401 sem chave no GoodWare indicam filtro por identificação do cliente.')
print('Se ambos dão 403, contate suporte Groq; o HTTP 403 não prova bloqueio regional.')
