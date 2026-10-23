import json,sqlite3,time,hashlib
import pytest
from app import create_app
from database import Database
from test_goodware import account,conv,upload

@pytest.fixture
def app(tmp_path):return create_app({'TESTING':True,'SECRET_KEY':'test-secret','DATABASE':str(tmp_path/'db.sqlite')})

def test_registration_separate_from_login(app):
    c=app.test_client();h={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    data={'email':'new@example.com','password':'long-password-123','password_confirmation':'long-password-123','full_name':'New User','username':'new_user'}
    assert c.post('/api/auth/register',json=data,headers=h).status_code==200
    assert not c.get('/api/auth/session').json['authenticated']
    assert c.get('/painel.html').status_code==302
    assert c.get('/cadastro.html').status_code==200
    data['email']='other@example.com'
    assert c.post('/api/auth/register',json=data,headers=h).status_code==409

def test_real_profile_dashboard_feedback_delete(app):
    c,h=account(app);cid=conv(c,h);rid=upload(c,h,cid).json['resultado']['id']
    assert c.get('/api/dashboard').json['analyses']==1
    assert c.get('/api/account').json['memory_enabled'] is False
    assert c.patch('/api/account',json={'full_name':'New name','memory_enabled':True},headers=h).status_code==200
    assert c.get('/api/account').json['memory_enabled'] is True
    assert c.post('/api/feedback',json={'content':'Good report'},headers=h).status_code==200
    assert c.delete('/api/account',json={'password':'wrong'},headers=h).status_code==400
    assert c.delete('/api/account',json={'password':'long-test-password'},headers=h).status_code==200
    d=Database(app.extensions['goodware_db'])
    for table in ('users','reports','conversations','messages','auth_sessions','feedback','audit'):assert d.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
    d.close()
    assert c.get('/api/reports/'+rid).status_code==401

def test_deletion_ownership_and_reports_preserved(app):
    a,h=account(app);b,hb=account(app,'b@example.com');cid=conv(a,h);rid=upload(a,h,cid).json['resultado']['id']
    assert b.delete('/api/conversations/'+cid,json={},headers=hb).status_code==404
    assert b.delete('/api/reports/'+rid,json={},headers=hb).status_code==404
    assert a.delete('/api/conversations/'+cid,json={},headers=h).status_code==200
    assert a.get('/api/reports/'+rid).status_code==200
    assert a.delete('/api/reports/'+rid,json={},headers=h).status_code==200
    assert a.get('/api/dashboard').json['analyses']==0

def test_memory_opt_in_and_isolation(app,monkeypatch):
    a,h=account(app);b,hb=account(app,'b@example.com');old=conv(a,h);rid=upload(a,h,old).json['resultado']['id'];upload(b,hb,conv(b,hb),name='PRIVATE.py')
    calls=[]
    def fake(hist,reports,msg,**kwargs):calls.append((reports,kwargs));return 'Resposta controlada'
    monkeypatch.setattr('app.generate',fake)
    cid=conv(a,h)
    def send():return a.post('/api/chat',json={'conversation_id':cid,'mensagem':'ransomware ontem'},headers=h)
    assert send().status_code==200 and calls[-1][0]==[]
    a.patch('/api/account',json={'memory_enabled':True},headers=h)
    assert send().status_code==200
    assert [r['id'] for r in calls[-1][0]]==[rid]
    assert calls[-1][1]['knowledge_docs'][0]['source'].startswith('https://www.cisa.gov/')
    a.patch('/api/account',json={'memory_enabled':False},headers=h)
    assert send().status_code==200 and calls[-1][0]==[]

def test_password_reset_single_use_and_revocation(app,monkeypatch):
    c,h=account(app);sent=[]
    monkeypatch.setattr('mailer.configured',lambda:True)
    monkeypatch.setattr('mailer.send_token',lambda email,token,purpose:sent.append((token,purpose)))
    assert c.post('/api/password/request',json={'email':'a@example.com'},headers=h).status_code==200
    raw=sent[0][0];d=Database(app.extensions['goodware_db']);stored=d.execute('SELECT id FROM auth_tokens').fetchone()[0];d.close();assert stored!=raw and stored==hashlib.sha256(raw.encode()).hexdigest()
    data={'token':raw,'password':'replacement-password','password_confirmation':'replacement-password'}
    assert c.post('/api/token/reset',json=data,headers=h).status_code==200
    assert c.post('/api/token/reset',json=data,headers=h).status_code==400
    assert c.get('/api/account').status_code==401

def test_email_verification(app,monkeypatch):
    monkeypatch.setenv('EMAIL_VERIFICATION_REQUIRED','1');monkeypatch.setattr('mailer.configured',lambda:True);sent=[]
    monkeypatch.setattr('mailer.send_token',lambda email,token,purpose:sent.append(token))
    c=app.test_client();h={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    data={'full_name':'Verified User','username':'verified','email':'verify@example.com','password':'long-password-123','password_confirmation':'long-password-123'}
    assert c.post('/api/auth/register',json=data,headers=h).status_code==200
    assert c.post('/api/auth/login',json=data,headers=h).status_code==403
    assert c.post('/api/token/verify',json={'token':sent[0]},headers=h).status_code==200
    assert c.post('/api/auth/login',json=data,headers=h).status_code==200

def test_expired_tokens_and_session(app,monkeypatch):
    c,h=account(app);d=Database(app.extensions['goodware_db']);uid=d.execute('SELECT id FROM users').fetchone()[0]
    raw='long-expired-token';d.execute('INSERT INTO auth_tokens VALUES(?,?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),uid,'verify',time.time()-1));d.execute('UPDATE auth_sessions SET expires=0');d.commit();d.close()
    assert c.post('/api/token/verify',json={'token':raw},headers=h).status_code==400
    assert not c.get('/api/auth/session').json['authenticated']

def test_admin_cannot_read_private_messages(app):
    c,h=account(app);assert c.get('/api/admin').status_code==403
    d=Database(app.extensions['goodware_db']);d.execute('UPDATE users SET is_admin=1');d.commit();d.close()
    payload=c.get('/api/admin').json
    assert 'events' in payload and 'messages' not in payload and 'password' not in str(payload)

def test_sqlite_v1_migration_preserves_data(tmp_path):
    path=tmp_path/'old.sqlite'
    with sqlite3.connect(path) as d:
        d.executescript("CREATE TABLE users(id TEXT PRIMARY KEY,email TEXT UNIQUE,password TEXT);INSERT INTO users VALUES('old','old@example.com','existing-hash');CREATE TABLE conversations(id TEXT PRIMARY KEY,owner TEXT,created REAL);CREATE TABLE messages(id INTEGER PRIMARY KEY,conversation TEXT,role TEXT,content TEXT);CREATE TABLE reports(id TEXT PRIMARY KEY,owner TEXT,conversation TEXT,day TEXT,body TEXT);")
    app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(path)})
    d=Database(app.extensions['goodware_db']);r=d.execute('SELECT * FROM users').fetchone();assert r['password']=='existing-hash' and r['memory_enabled']==0
    assert d.execute('SELECT version FROM schema_versions').fetchone()[0]==2;d.close()

def test_health_security_headers_and_rate_limit(app):
    c=app.test_client();assert c.get('/healthz').json['status']=='ok'
    assert "script-src 'self'" in c.get('/login.html').headers['Content-Security-Policy']
    h={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    for _ in range(20):c.post('/api/auth/login',json={},headers=h)
    assert c.post('/api/auth/login',json={},headers=h).status_code==429

def test_concurrent_chat_lease(app):
    c,h=account(app);cid=conv(c,h);d=Database(app.extensions['goodware_db']);d.execute('UPDATE conversations SET busy_until=? WHERE id=?',(time.time()+60,cid));d.commit();d.close()
    assert c.post('/api/chat',json={'conversation_id':cid,'mensagem':'Olá'},headers=h).status_code==409
