from app import create_app
from test_goodware import account,conv,upload

def test_overview_auth_isolation_and_latest(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(tmp_path/'overview.db')})
    assert app.test_client().get('/api/dashboard/overview').status_code==401
    a,h=account(app);cid=conv(a,h)
    empty=a.get('/api/dashboard/overview').json
    assert empty['latest'] is None and empty['recent']==[] and empty['stats']['analyses']==0
    result=upload(a,h,cid).json['resultado']
    response=a.get('/api/dashboard/overview');data=response.json
    assert 'no-store' in response.headers['Cache-Control']
    assert data['csrf']==h['X-CSRF-Token'] and data['authenticated'] is True
    assert data['latest']['id']==result['id'] and data['latest']['medidor']==result['medidor']
    assert data['stats']==a.get('/api/dashboard').json
    assert len(data['recent'])==1 and 'evidencias' not in data['recent'][0]
    b,hb=account(app,'second@example.com')
    assert b.get('/api/dashboard/overview').json['latest'] is None
