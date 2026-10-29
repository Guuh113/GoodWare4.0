"""Persistência SQLAlchemy: PostgreSQL em produção, SQLite para desenvolvimento.
Migração aditiva v2 preserva os dados da versão anterior.
"""
import time
from pathlib import Path
from sqlalchemy import (create_engine, MetaData, Table, Column, Text, Integer, Float, ForeignKey, inspect, text, event)

meta=MetaData()
users=Table('users',meta,Column('id',Text,primary_key=True),Column('email',Text,unique=True),Column('password',Text),Column('full_name',Text,server_default=''),Column('username',Text,server_default=''),Column('memory_enabled',Integer,server_default='0'),Column('verified',Integer,server_default='0'),Column('is_admin',Integer,server_default='0'),Column('mfa_secret',Text,server_default=''),Column('mfa_pending',Text,server_default=''),Column('mfa_pending_until',Float,server_default='0'),Column('mfa_counter',Integer,server_default='-1'),Column('mfa_backups',Text,server_default='[]'))
Table('conversations',meta,Column('id',Text,primary_key=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('created',Float),Column('title',Text,server_default='Nova conversa'),Column('busy_until',Float,server_default='0'))
Table('messages',meta,Column('id',Integer,primary_key=True,autoincrement=True),Column('conversation',Text,ForeignKey('conversations.id',ondelete='CASCADE'),index=True),Column('role',Text),Column('content',Text))
Table('reports',meta,Column('id',Text,primary_key=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('conversation',Text,ForeignKey('conversations.id',ondelete='SET NULL'),index=True),Column('day',Text),Column('body',Text),Column('created_at',Float,server_default='0'))
Table('report_links',meta,Column('conversation',Text,ForeignKey('conversations.id',ondelete='CASCADE'),primary_key=True),Column('report',Text,ForeignKey('reports.id',ondelete='CASCADE'),primary_key=True))
Table('attempts',meta,Column('key',Text,primary_key=True),Column('count',Integer),Column('started',Float))
Table('auth_sessions',meta,Column('id',Text,primary_key=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('expires',Float))
Table('auth_tokens',meta,Column('id',Text,primary_key=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('purpose',Text),Column('expires',Float))
Table('feedback',meta,Column('id',Text,primary_key=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('content',Text),Column('created',Float))
Table('audit',meta,Column('id',Integer,primary_key=True,autoincrement=True),Column('owner',Text,ForeignKey('users.id',ondelete='CASCADE'),index=True),Column('event',Text),Column('created',Float))
Table('knowledge',meta,Column('id',Text,primary_key=True),Column('title',Text),Column('content',Text),Column('source',Text),Column('reviewed_at',Text),Column('tags',Text))
Table('schema_versions',meta,Column('version',Integer,primary_key=True),Column('applied_at',Float))

ADDITIONS={'users':{'full_name':"TEXT DEFAULT ''",'username':"TEXT DEFAULT ''",'memory_enabled':'INTEGER DEFAULT 0','verified':'INTEGER DEFAULT 0','is_admin':'INTEGER DEFAULT 0','mfa_secret':"TEXT DEFAULT ''",'mfa_pending':"TEXT DEFAULT ''",'mfa_pending_until':'FLOAT DEFAULT 0','mfa_counter':'INTEGER DEFAULT -1','mfa_backups':"TEXT DEFAULT '[]'"},'conversations':{'title':"TEXT DEFAULT 'Nova conversa'",'busy_until':'FLOAT DEFAULT 0'},'reports':{'created_at':'FLOAT DEFAULT 0'}}

def make_engine(url):
    if url.startswith('postgres://'):url=url.replace('postgres://','postgresql+psycopg://',1)
    elif url.startswith('postgresql://'):url=url.replace('postgresql://','postgresql+psycopg://',1)
    if url.startswith('sqlite:///'):
        Path(url.removeprefix('sqlite:///')).parent.mkdir(parents=True,exist_ok=True)
    engine=create_engine(url,pool_pre_ping=True,hide_parameters=True,connect_args={'timeout':20} if url.startswith('sqlite:') else {})
    if url.startswith('sqlite:'):
        @event.listens_for(engine,'connect')
        def foreign_keys(connection,record):connection.execute('PRAGMA foreign_keys=ON')
    return engine

def migrate(engine):
    with engine.begin() as conn:
        if engine.dialect.name=='postgresql':conn.execute(text('SELECT pg_advisory_xact_lock(309031)'))
        meta.create_all(conn)
        for table,columns in ADDITIONS.items():
            existing={c['name'] for c in inspect(conn).get_columns(table)}
            for name,ddl in columns.items():
                if name not in existing:conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS users_username_unique ON users(username) WHERE username <> ''"))
        conn.execute(text('INSERT INTO schema_versions(version,applied_at) VALUES (2,:now) ON CONFLICT(version) DO NOTHING'),{'now':time.time()})
        conn.execute(text('INSERT INTO schema_versions(version,applied_at) VALUES (4,:now) ON CONFLICT(version) DO NOTHING'),{'now':time.time()})

class Row:
    def __init__(self,row):self.row=row
    def __getitem__(self,key):return self.row[key] if isinstance(key,int) else self.row._mapping[key]
    def keys(self):return self.row._mapping.keys()
class Result:
    def __init__(self,result):self.result=result;self.rowcount=result.rowcount
    def fetchone(self):
        r=self.result.fetchone();return Row(r) if r is not None else None
    def fetchall(self):return [Row(r) for r in self.result.fetchall()]
    def __iter__(self):return iter(self.fetchall())
class Database:
    def __init__(self,engine):self.conn=engine.connect();self.dialect=engine.dialect.name
    def execute(self,sql,args=()):
        if sql=='BEGIN IMMEDIATE':
            self.conn.commit()
            if self.dialect=='sqlite':self.conn.exec_driver_sql('BEGIN IMMEDIATE')
            else:self.conn.begin()
            return None
        parts=sql.split('?')
        if len(parts)-1 != len(args):raise ValueError('Quantidade de parâmetros SQL inválida.')
        query=''.join(part+(f':p{i}' if i<len(args) else '') for i,part in enumerate(parts))
        return Result(self.conn.execute(text(query),{f'p{i}':v for i,v in enumerate(args)}))
    def executemany(self,sql,rows):
        for row in rows:self.execute(sql,row)
    def lock_user(self,uid):
        if self.dialect=='postgresql':self.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(uid,))
    def commit(self):self.conn.commit()
    def rollback(self):self.conn.rollback()
    def close(self):self.conn.close()
