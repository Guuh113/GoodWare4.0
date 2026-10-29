import json
from datetime import datetime, timezone
from app import create_app
from database import Database
from risk import assess_report
import assistant_service as service
from test_goodware import account, conv, upload

def test_same_account_from_second_browser_after_restart(tmp_path):
    config={'TESTING':True,'SECRET_KEY':'test','DATABASE':str(tmp_path/'shared.sqlite')}
    app=create_app(config);a,h=account(app);cid=conv(a,h)
    report=upload(a,h,cid).json['resultado']
    second=create_app(config);b=second.test_client()
    hb={'X-CSRF-Token':b.get('/api/auth/session').json['csrf']}
    assert b.get('/api/historico').status_code==401
    login=b.post('/api/auth/login',json={'email':'a@example.com','password':'long-test-password'},headers=hb)
    assert login.status_code==200
    assert b.get('/api/historico').json[0]['id']==report['id']
    hb={'X-CSRF-Token':login.json['csrf']}
    b.post('/api/auth/logout',json={},headers=hb)
    assert a.get('/api/auth/session').json['authenticated'] is True
    d=Database(second.extensions['goodware_db'])
    stored=d.execute('SELECT password FROM users WHERE email=?',('a@example.com',)).fetchone()[0];d.close()
    assert stored!='long-test-password' and stored.startswith(('scrypt:','pbkdf2:'))

def test_score_ignores_repetition_and_unvalidated_model():
    r=assess_report({'evidencias':[{'categoria':'execucao_dinamica'}]*100,'pontuacao_modelo':99})
    assert r['medidor']['valor']==35 and r['risco']=='médio'
    assert assess_report({'evidencias':[]})['medidor']['valor']==0
    assert assess_report({'evidencias':[{'categoria':str(i)} for i in range(6)]})['medidor']['valor']==85

def test_score_persisted_and_client_cannot_set_it(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'tests','DATABASE':str(tmp_path/'test.sqlite')})
    a,h=account(app);cid=conv(a,h)
    r=a.post('/api/analisar-url',json={'conversation_id':cid,'url':'http://example.com','medidor':{'valor':0}},headers=h).json['resultado']
    assert r['medidor']['valor']==35
    assert a.get('/api/reports/'+r['id']).json['medidor']==r['medidor']

def test_clock_uses_server_not_model_and_handles_invalid_zone(monkeypatch):
    class FixedDate(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,10,29,1,15,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(service,'datetime',FixedDate)
    monkeypatch.setattr(service,'urlopen',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Clock must not call provider')))
    assert '22:15 de 28/10/2026' in service.generate([],[],'Que horas são?',time_zone='America/Sao_Paulo')
    assert '01:15 de 29/10/2026' in service.generate([],[],'Que horas são?',time_zone='UTC')
    assert 'America/Sao_Paulo' in service.generate([],[],'Que dia é hoje?',time_zone='../../etc/passwd')
    assert len(list(service.generate([],[],'Que horas são?',stream=True)))==1

def test_general_question_still_calls_model_with_temporal_context(monkeypatch):
    import io
    monkeypatch.setenv('LLM_BASE_URL','https://provider.example/v1');monkeypatch.setenv('LLM_MODEL','test')
    sent=[]
    def provider(req,**kw):
        sent.append(json.loads(req.data));return io.BytesIO(b'{"choices":[{"message":{"content":"Uma receita de bolo."}}]}')
    monkeypatch.setattr(service,'urlopen',provider)
    assert service.generate([],[],'Como fazer bolo?',user_name='Gustavo',time_zone='UTC')=='Uma receita de bolo.'
    prompt=str(sent[0]['messages'])
    assert 'Contexto temporal verificado' in prompt and 'Gustavo' in prompt

def test_clock_both_chat_modes(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'tests','DATABASE':str(tmp_path/'test.sqlite')})
    a,h=account(app);cid=conv(a,h)
    for stream in (False,True):
        r=a.post('/api/chat',json={'conversation_id':cid,'mensagem':'Que horas são?','time_zone':'UTC','stream':stream},headers=h)
        assert r.status_code==200 and 'UTC' in r.get_data(as_text=True)
    assert len(a.get('/api/conversations/'+cid).json['messages'])==4
