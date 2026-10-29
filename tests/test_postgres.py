"""Integration test only against a disposable CI/test database."""
import os,uuid
import pytest
from sqlalchemy import text
from app import create_app
from database import Database
from test_goodware import account,conv,upload

@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'),reason='PostgreSQL de testes não configurado')
def test_postgres_end_to_end(monkeypatch):
    app=create_app({'TESTING':True,'SECRET_KEY':'postgres-tests','DATABASE_URL':os.environ['TEST_POSTGRES_URL']})
    email='pg'+uuid.uuid4().hex[:12]+'@example.com'
    c,h=account(app,email);cid=conv(c,h)
    assert upload(c,h,cid).status_code==200
    monkeypatch.setattr('app.generate',lambda *a,**kw:'Teste de persistência PostgreSQL')
    assert c.post('/api/chat',json={'conversation_id':cid,'mensagem':'Explique'},headers=h).status_code==200
    assert len(c.get('/api/conversations/'+cid).json['messages'])==2
    second=app.test_client();hs={'X-CSRF-Token':second.get('/api/auth/session').json['csrf']}
    assert second.post('/api/auth/login',json={'email':email,'password':'long-test-password'},headers=hs).status_code==200
    assert second.get('/api/conversations/'+cid).json['messages']==c.get('/api/conversations/'+cid).json['messages']
    assert second.get('/api/historico').json[0]['medidor']['valor']==35
    assert c.delete('/api/account',json={'password':'long-test-password'},headers=h).status_code==200
