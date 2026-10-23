import io, json, zipfile, stat
import pytest
from app import create_app
from scanner import analyze

@pytest.fixture
def app(tmp_path):return create_app({'TESTING':True,'SECRET_KEY':'test-only','DATABASE':str(tmp_path/'test.db')})

def account(app,email='a@example.com'):
    c=app.test_client();csrf=c.get('/api/auth/session').json['csrf']
    r=c.post('/api/auth/register',json={'email':email,'password':'long-test-password','password_confirmation':'long-test-password','full_name':'Test User','username':email.split('@')[0]+'_user'},headers={'X-CSRF-Token':csrf})
    assert r.status_code==200
    r=c.post('/api/auth/login',json={'email':email,'password':'long-test-password'},headers={'X-CSRF-Token':csrf})
    assert r.status_code==200
    return c,{'X-CSRF-Token':r.json['csrf']}

def conv(c,h):return c.post('/api/conversations',json={},headers=h).json['id']
def upload(c,h,cid,data=b'exec(user_input)\n',name='src.py'):
    return c.post('/api/analisar-ficheiro',data={'conversation_id':cid,'file':(io.BytesIO(data),name)},headers=h)
def archive(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in entries:z.writestr(name,data)
    return b.getvalue()

def test_auth_csrf_and_private_files(app):
    c=app.test_client()
    assert c.get('/api/historico').status_code==401
    assert c.post('/api/auth/register',json={}).status_code==403
    for p in ['/app.py','/.env','/modelo_malware.pkl','/instance/goodware.db','/teste_alta_entropia.exe']:
        assert c.get(p).status_code==404

def test_ownership(app):
    a,ha=account(app);b,hb=account(app,'b@example.com');cid=conv(a,ha)
    r=upload(a,ha,cid).json['resultado']
    assert b.get('/api/historico').json==[]
    assert b.get('/api/conversations/'+cid).status_code==404
    assert b.get('/api/reports/'+r['id']).status_code==404
    assert upload(b,hb,cid).status_code==404
    assert b.post('/api/chat',json={'conversation_id':conv(b,hb),'mensagem':'Oi','report_id':r['id']},headers=hb).status_code==404

def test_chat_context_and_new_conversation(app,monkeypatch):
    c,h=account(app);cid=conv(c,h);r=upload(c,h,cid).json['resultado'];calls=[]
    def generate(history,reports,msg,**kwargs):calls.append((history,reports,msg));return 'Veja E1: suspeita, não confirmação.'
    monkeypatch.setattr('app.generate',generate)
    for msg in ['Explique o primeiro','Isso rouba dados?']:
        assert c.post('/api/chat',json={'conversation_id':cid,'mensagem':msg},headers=h).status_code==200
    assert calls[1][0][0]['content']=='Explique o primeiro'
    assert calls[1][1][0]['id']==r['id']
    other=conv(c,h)
    assert c.get('/api/conversations/'+other).json=={'messages':[],'reports':[]}
    assert len(c.get('/api/conversations/'+cid).json['messages'])==4

def test_unconfigured_llm(app,monkeypatch):
    monkeypatch.delenv('LLM_MODEL',raising=False)
    c,h=account(app);cid=conv(c,h)
    assert c.post('/api/chat',json={'conversation_id':cid,'mensagem':'Oi'},headers=h).status_code==503
    assert c.get('/api/conversations/'+cid).json['messages']==[]

def test_lines_and_no_unsupported_diagnosis():
    r=analyze(archive([('src/main.py',b'# comment\nexec(user_input)\n'),('assets/a.bin',b'other')]),'project.zip')
    assert r['evidencias'][0]['arquivo']=='src/main.py'
    assert r['evidencias'][0]['localizacao']=={'linha':2}
    assert r['tipo_ameaca']=='Tipo de ameaça ainda não determinado'
    assert r['pontuacao_modelo'] is None
    assert r['arquivos'][1]['detalhes']['ignorado']
    clean=analyze(b'print("Hello")','hello.py')
    assert clean['evidencias']==[] and clean['classificacao']!='Seguro'

@pytest.mark.parametrize('name',['../outside.py','/abs.py','C:/windows/a.py','..\\bad.py'])
def test_traversal(name):
    with pytest.raises(ValueError):analyze(archive([(name,b'print(1)')]),'a.zip')

def test_limits_and_symlink():
    with pytest.raises(ValueError):analyze(archive([('bomb.py',b'x'*200000)]),'a.zip')
    with pytest.raises(ValueError):analyze(archive([(str(i)+'.py',b'') for i in range(201)]),'a.zip')
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        i=zipfile.ZipInfo('link.py');i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,'/etc/passwd')
    with pytest.raises(ValueError):analyze(b.getvalue(),'a.zip')

def test_bad_uploads(app):
    c,h=account(app);cid=conv(c,h)
    for data,name in [(b'MZbroken','a.exe'),(b'PKbad','a.zip'),(b'','a.py'),(b'hello','a.bin')]:
        assert upload(c,h,cid,data,name).status_code==400
    assert upload(c,h,cid,b'x'*(10*1024*1024+1),'a.py').status_code==400

def test_pe_evidence_does_not_name_family(monkeypatch):
    monkeypatch.setattr('scanner.extrair_caracteristicas_memoria',lambda _:([1]*10,{'secoes':[{'nome':'.text','offset':512,'entropia':7.9,'gravavel_executavel':True}],'imports_suspeitos':[{'nome':'WriteProcessMemory','iat_rva':8192}]}))
    monkeypatch.setattr('risk.score_model',lambda _:(99,'Não calibrado'))
    r=analyze(b'MZfake','fixture.exe')
    assert r['tipo_ameaca']=='Tipo de ameaça ainda não determinado'
    assert r['evidencias'][0]['localizacao']['offset']==512
    assert 'linha' not in r['evidencias'][0]['localizacao']

def test_llm_wire_format(monkeypatch):
    import assistant_service as s
    monkeypatch.setenv('LLM_BASE_URL','http://localhost:11434/v1');monkeypatch.setenv('LLM_MODEL','test')
    captured=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return json.dumps({'choices':[{'message':{'content':'Resposta de teste'}}]}).encode()
    def fake(req,timeout):captured.append(json.loads(req.data));return Response()
    monkeypatch.setattr(s,'urlopen',fake)
    assert s.generate([{'role':'user','content':'Antes'}],[{'evidencias':[]}],'Agora')=='Resposta de teste'
    assert captured[0]['messages'][-2]['content']=='Antes'
    assert captured[0]['messages'][-1]['content']=='Agora'

def test_url_no_remote_request(app):
    c,h=account(app);cid=conv(c,h)
    r=c.post('/api/analisar-url',json={'url':'http://127.0.0.1/internal','conversation_id':cid},headers=h)
    assert r.status_code==200 and 'não acessada' in r.json['resultado']['explicacao']

def test_logout(app):
    c,h=account(app);assert c.post('/api/auth/logout',json={},headers=h).status_code==200
    assert c.get('/api/historico').status_code==401

def test_quota_and_relative_path(app):
    app.config['DAILY_LIMIT']=1
    c,h=account(app);cid=conv(c,h)
    r=upload(c,h,cid,name='folder/script.py')
    assert r.status_code==200
    assert r.json['resultado']['evidencias'][0]['arquivo']=='folder/script.py'
    assert upload(c,h,cid).status_code==429

def test_real_pe_parser_rejects_truncated_fixture():
    from extractor import extrair_caracteristicas_memoria
    assert extrair_caracteristicas_memoria(b'MZtruncated')==(None,None)

def test_api_routing_errors_are_json(app):
    c=app.test_client()
    r=c.get('/api/does-not-exist')
    assert r.status_code==404 and r.is_json
    token=c.get('/api/auth/session').json['csrf']
    r=c.put('/api/auth/session',headers={'X-CSRF-Token':token})
    assert r.status_code==405 and r.is_json

def test_launcher_generates_persistent_secret(tmp_path,monkeypatch):
    from iniciar import prepare_env
    from dotenv import dotenv_values
    monkeypatch.delenv('SECRET_KEY',raising=False)
    (tmp_path/'.env.example').write_text('SECRET_KEY=\nLLM_MODEL=\n')
    path=prepare_env(tmp_path);first=dotenv_values(path)['SECRET_KEY']
    assert len(first)==64
    prepare_env(tmp_path)
    assert dotenv_values(path)['SECRET_KEY']==first
