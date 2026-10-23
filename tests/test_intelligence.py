import json,io
import pytest
from app import create_app
from test_goodware import account,conv,upload
from assistant_service import AssistantUnavailable
from database import Database

@pytest.fixture
def app(tmp_path):return create_app({'TESTING':True,'SECRET_KEY':'tests','DATABASE':str(tmp_path/'v4.sqlite')})

def test_export_comparison_pdf_isolated(app):
    a,h=account(app);b,hb=account(app,'b@example.com');cid=conv(a,h)
    left=upload(a,h,cid).json['resultado'];right=upload(a,h,cid,b'print("hello")','clean.py').json['resultado']
    assert a.get('/api/reports/compare?left='+left['id']+'&right='+right['id']).json['only_left']
    for suffix in ['/api/reports/'+left['id']+'/pdf','/api/reports/compare?left='+left['id']+'&right='+right['id']]:assert b.get(suffix).status_code==404
    pdf=a.get('/api/reports/'+left['id']+'/pdf');assert pdf.status_code==200 and pdf.data.startswith(b'%PDF-') and 'attachment' in pdf.headers['Content-Disposition']
    data=a.get('/api/account/export').json;assert len(data['reports'])==2 and 'password' not in data['account'] and 'auth_sessions' not in data
    assert b.get('/api/account/export').json['reports']==[]
    assert a.get('/api/historico').json[0]['conversation_id']==cid

def test_score_empty_and_real_counts(app):
    a,h=account(app);d=a.get('/api/intelligence').json;assert d['score']['value']==0 and d['radar']['total']==0
    upload(a,h,conv(a,h));d=a.get('/api/intelligence').json
    assert d['radar']['total']==1 and d['radar']['risks']=={'médio':1} and d['radar']['categories']['execucao_dinamica']==1
    assert d['score']['value']==sum(c['earned'] for c in d['score']['criteria'])

def test_clear_history_requires_password_and_csrf(app):
    a,h=account(app);b,hb=account(app,'b@example.com');upload(a,h,conv(a,h));upload(b,hb,conv(b,hb))
    assert a.delete('/api/account/history',json={'password':'long-test-password'}).status_code==403
    assert a.delete('/api/account/history',json={'password':'wrong'},headers=h).status_code==400
    a.patch('/api/account',json={'memory_enabled':True},headers=h)
    assert a.delete('/api/account/history',json={'password':'long-test-password'},headers=h).status_code==200
    assert a.get('/api/historico').json==[] and a.get('/api/conversations').json==[]
    assert not a.get('/api/account').json['memory_enabled'] and len(b.get('/api/historico').json)==1

def test_stream_persists_only_complete_responses(app,monkeypatch):
    c,h=account(app);cid=conv(c,h)
    monkeypatch.setattr('app.generate',lambda *a,**kw:iter(['Olá, ','veja E1.']))
    r=c.post('/api/chat',json={'conversation_id':cid,'mensagem':'Explique','stream':True},headers=h)
    events=[json.loads(line) for line in r.data.splitlines()]
    assert [e['type'] for e in events]==['delta','delta','done']
    assert c.get('/api/conversations/'+cid).json['messages'][-1]['content']=='Olá, veja E1.'
    def failure(*a,**kw):
        yield 'Parcial'
        raise AssistantUnavailable('Falha controlada')
    monkeypatch.setattr('app.generate',failure)
    r=c.post('/api/chat',json={'conversation_id':cid,'mensagem':'Outra','stream':True},headers=h)
    assert json.loads(r.data.splitlines()[-1])['type']=='error'
    assert len(c.get('/api/conversations/'+cid).json['messages'])==2
    d=Database(app.extensions['goodware_db']);assert d.execute('SELECT busy_until FROM conversations WHERE id=?',(cid,)).fetchone()[0]==0;d.close()

def test_provider_stream_parser(monkeypatch):
    import assistant_service as service
    monkeypatch.setenv('LLM_BASE_URL','https://provider.example/v1');monkeypatch.setenv('LLM_MODEL','test')
    class Response(io.BytesIO):pass
    monkeypatch.setattr(service,'urlopen',lambda *a,**kw:Response(b'data: {"choices":[{"delta":{"content":"Oi"}}]}\n\ndata: [DONE]\n'))
    assert list(service.generate([],[],'Oi',stream=True))==['Oi']
    monkeypatch.setattr(service,'urlopen',lambda *a,**kw:Response(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n'))
    with pytest.raises(AssistantUnavailable):list(service.generate([],[],'Oi',stream=True))

def test_new_pages_protected_and_knowledge_sources(app):
    c=app.test_client()
    for path in ('radar.html','knowledge.html'):assert c.get('/'+path).status_code==302
    c,h=account(app)
    for path in ('radar.html','knowledge.html'):assert c.get('/'+path).status_code==200
    assert all(d['source'].startswith('https://') and d['reviewed_at'] for d in c.get('/api/knowledge').json)

def test_report_link_persists_and_cannot_cross_accounts(app,monkeypatch):
    a,h=account(app);b,hb=account(app,'b@example.com');rid=upload(a,h,conv(a,h)).json['resultado']['id']
    assert b.post('/api/conversations',json={'report_id':rid},headers=hb).status_code==404
    cid=a.post('/api/conversations',json={'report_id':rid},headers=h).json['id']
    assert a.get('/api/conversations/'+cid).json['reports'][0]['id']==rid
    assert rid in next(c for c in a.get('/api/account/export').json['conversations'] if c['id']==cid)['report_ids']
    assert a.delete('/api/reports/'+rid,json={},headers=h).status_code==200
    assert a.get('/api/conversations/'+cid).json['reports']==[]

def test_retention_dry_run_and_apply(app):
    from retention import prune
    a,h=account(app);cid=conv(a,h);upload(a,h,cid)
    d=Database(app.extensions['goodware_db']);d.execute('UPDATE reports SET created_at=1');d.commit()
    assert prune(d,30)['reports']==1 and a.get('/api/historico').json
    assert prune(d,30,True)['applied'] and a.get('/api/historico').json==[]
    assert a.get('/api/conversations/'+cid).status_code==200;d.close()
