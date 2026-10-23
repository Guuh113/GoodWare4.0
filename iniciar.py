"""Inicialização local: configura segredo persistente e abre o backend correto."""
import os
import secrets
import webbrowser
from pathlib import Path
from threading import Timer
from dotenv import dotenv_values, set_key
from werkzeug.serving import make_server

ROOT=Path(__file__).resolve().parent

def prepare_env(root=ROOT):
    path=root/'.env'
    if not path.exists():path.write_text((root/'.env.example').read_text(encoding='utf-8'),encoding='utf-8')
    if not os.getenv('SECRET_KEY') and not dotenv_values(path).get('SECRET_KEY'):
        set_key(str(path),'SECRET_KEY',secrets.token_hex(32))
    return path

def main():
    os.chdir(ROOT)
    prepare_env()
    from app import create_app
    app=create_app()
    # Bind first: never open another service accidentally using the same port.
    port=int(os.getenv('PORT','5000'))
    server=make_server('127.0.0.1',port,app,threaded=True)
    address=f'http://127.0.0.1:{server.server_port}/login.html'
    print(f'GoodWare iniciado: {address}',flush=True)
    print('Mantenha este terminal aberto. Use Ctrl+C para encerrar.',flush=True)
    timer=Timer(1,lambda:webbrowser.open(address));timer.daemon=True;timer.start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
