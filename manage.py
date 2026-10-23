"""Operações locais de manutenção. Nunca imprime senhas, tokens ou conversas."""
import argparse,time,json
from retention import prune
from pathlib import Path
from sqlalchemy import select
from app import create_app
from database import Database,meta
import knowledge

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init-db');sub.add_parser('prune-expired')
    admin=sub.add_parser('set-admin');admin.add_argument('email');admin.add_argument('--revoke',action='store_true')
    kb=sub.add_parser('import-knowledge');kb.add_argument('file');kb.add_argument('--reviewed',action='store_true',required=True)
    migrate=sub.add_parser('import-sqlite');migrate.add_argument('file')
    retention=sub.add_parser('prune-data');retention.add_argument('--days',type=int,required=True);retention.add_argument('--apply',action='store_true')
    args=parser.parse_args();app=create_app();engine=app.extensions['goodware_db'];db=Database(engine)
    try:
        if args.command=='prune-data':print(json.dumps(prune(db,args.days,args.apply),ensure_ascii=False))
        elif args.command=='set-admin':
            r=db.execute('UPDATE users SET is_admin=? WHERE email=?',(0 if args.revoke else 1,args.email.lower()))
            if not r.rowcount:parser.error('Conta não encontrada.')
            db.execute('INSERT INTO audit(owner,event,created) VALUES(NULL,?,?)',('admin.permission.changed',time.time()));db.commit();print('Permissão atualizada.')
        elif args.command=='import-knowledge':knowledge.import_knowledge(db,args.file,replace=True);print('Base revisada importada.')
        elif args.command=='prune-expired':
            for table in ('auth_tokens','auth_sessions'):db.execute(f'DELETE FROM {table} WHERE expires<?',(time.time(),))
            db.execute('DELETE FROM attempts WHERE started<?',(time.time()-86400,));db.commit();print('Registros expirados removidos.')
        elif args.command=='import-sqlite':
            import sqlite3
            source=Path(args.file).resolve()
            if not source.is_file():parser.error('SQLite de origem não encontrado.')
            if engine.dialect.name!='postgresql':parser.error('Destino precisa ser PostgreSQL.')
            with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as old,engine.begin() as conn:
                old.row_factory=sqlite3.Row
                if conn.execute(select(meta.tables['users'].c.id).limit(1)).first():parser.error('Destino deve estar vazio de usuários.')
                available={r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for name in ('users','conversations','messages','reports','report_links','feedback','audit'):
                    if name not in available:continue
                    table=meta.tables[name]
                    for row in old.execute(f'SELECT * FROM {name}'):
                        data={k:row[k] for k in row.keys() if k in table.c}
                        if name in ('messages','audit'):data.pop('id',None)
                        conn.execute(table.insert().values(**data))
            print('Dados importados. Sessões e tokens antigos não são migrados; usuários devem entrar novamente.')
        else:print('Esquema e base técnica inicializados.')
    finally:db.close();engine.dispose()
if __name__=='__main__':main()
