import pyotp
from app import create_app
from database import Database
from test_goodware import account

def test_mfa_activation_replay_recovery_and_revoke(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(tmp_path/'mfa.sqlite')})
    a,h=account(app)
    b=app.test_client();bh={'X-CSRF-Token':b.get('/api/auth/session').json['csrf']}
    credentials={'email':'a@example.com','password':'long-test-password'}
    assert b.post('/api/auth/login',json=credentials,headers=bh).status_code==200
    url='/api/account/mfa';password={'password':'long-test-password'}
    assert a.post(url,json={'action':'setup','password':'wrong'},headers=h).status_code==403
    setup=a.post(url,json={**password,'action':'setup'},headers=h).json
    secret=setup['secret'];code=pyotp.TOTP(secret).now()
    assert a.get(url).json=={'enabled':False}
    result=a.post(url,json={**password,'action':'confirm','code':code},headers=h)
    assert result.status_code==200 and len(result.json['backup_codes'])==8
    assert a.get(url).json=={'enabled':True}
    assert b.get('/api/historico').status_code==401
    bh={'X-CSRF-Token':b.get('/api/auth/session').json['csrf']}
    assert b.post('/api/auth/login',json=credentials,headers=bh).status_code==401
    assert b.post('/api/auth/login',json={**credentials,'code':code},headers=bh).status_code==401
    backup=result.json['backup_codes'][0]
    login=b.post('/api/auth/login',json={**credentials,'code':backup},headers=bh)
    assert login.status_code==200
    c=app.test_client();ch={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    assert c.post('/api/auth/login',json={**credentials,'code':backup},headers=ch).status_code==401
    d=Database(app.extensions['goodware_db']);row=d.execute('SELECT mfa_secret,mfa_backups FROM users').fetchone();d.close()
    assert secret not in row[0] and backup not in row[1]
    assert a.delete(url,json={**password,'code':result.json['backup_codes'][1]},headers=h).status_code==200
    assert b.get('/api/historico').status_code==401
    assert a.get(url).json=={'enabled':False}
    assert c.post('/api/auth/login',json=credentials,headers=ch).status_code==200
