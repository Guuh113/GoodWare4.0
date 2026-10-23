from pathlib import Path
import pytest
from werkzeug.security import generate_password_hash
from database import Database
from app import create_app

def test_existing_short_password_can_login_but_new_short_password_rejected(tmp_path):
    app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(tmp_path/'db.sqlite')})
    d=Database(app.extensions['goodware_db'])
    d.execute('INSERT INTO users(id,email,password,full_name,username) VALUES(?,?,?,?,?)',('legacy','old@example.com',generate_password_hash('old123'),'Legacy User','legacy'));d.commit();d.close()
    c=app.test_client();h={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    assert c.post('/api/auth/login',json={'email':'  OLD@example.com  ','password':'old123'},headers=h).status_code==200
    assert c.get('/api/auth/session').json['authenticated']
    assert c.get('/painel.html').status_code==200
    assert app.config['SESSION_COOKIE_NAME']=='goodware_session'
    h={'X-CSRF-Token':c.get('/api/auth/session').json['csrf']}
    assert c.post('/api/auth/register',json={'email':'new@example.com','password':'short'},headers=h).status_code==400
    assert c.post('/api/auth/login',json={'email':'old@example.com','password':'wrong'},headers=h).status_code==401

def test_relative_database_path_is_independent_of_launch_directory(tmp_path,monkeypatch):
    import app as module
    project=tmp_path/'project';project.mkdir();(project/'data').mkdir()
    (project/'data/knowledge.json').write_text('[]')
    monkeypatch.setattr(module,'ROOT',project)
    other=tmp_path/'other';other.mkdir();monkeypatch.chdir(other)
    app=module.create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':'instance/goodware.db'})
    assert Path(app.extensions['goodware_db'].url.database)==project/'instance/goodware.db'
    assert not (other/'instance/goodware.db').exists()
