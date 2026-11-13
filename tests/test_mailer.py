import json
import pytest
import mailer


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv('MAIL_PROVIDER','resend')
    monkeypatch.setenv('RESEND_API_KEY','test-private-key')
    monkeypatch.setenv('MAIL_FROM','GoodWare <mail@example.com>')
    monkeypatch.setenv('PUBLIC_BASE_URL','https://example.com')
    monkeypatch.setenv('APP_ENV','production')


@pytest.mark.parametrize('purpose,page',[('reset','redefinir.html'),('verify','verificar.html')])
def test_https_payload(settings,monkeypatch,purpose,page):
    captured=[]
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'{"id":"message-id"}'
    class Opener:
        def open(self,request,timeout):
            captured.append(request)
            assert timeout==15
            return Response()
    monkeypatch.setattr(mailer,'build_opener',lambda handler:Opener())
    assert mailer.configured()
    mailer.send_token('user@example.com','private-token',purpose)
    req=captured[0];payload=json.loads(req.data)
    assert req.full_url=='https://api.resend.com/emails'
    assert req.get_header('Authorization')=='Bearer test-private-key'
    assert payload['to']==['user@example.com']
    assert 'https://example.com/'+page+'#token=private-token' in payload['text']
    assert 'private-token' not in payload['subject']
    assert mailer.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.invalid') is None


@pytest.mark.parametrize('variable,value',[('RESEND_API_KEY',''),('MAIL_FROM',''),('MAIL_PROVIDER','unknown'),('PUBLIC_BASE_URL','http://example.com'),('PUBLIC_BASE_URL','https://user:password@example.com'),('PUBLIC_BASE_URL','https://example.com?url=evil')])
def test_incomplete_config(settings,monkeypatch,variable,value):
    monkeypatch.setenv(variable,value)
    assert not mailer.configured()
    with pytest.raises(RuntimeError):mailer.send_token('user@example.com','secret','reset')


def test_provider_failure_is_sanitized(settings,monkeypatch):
    class Opener:
        def open(self,*args,**kwargs):raise ValueError('secret-token and recipient')
    monkeypatch.setattr(mailer,'build_opener',lambda handler:Opener())
    with pytest.raises(RuntimeError) as exc:mailer.send_token('user@example.com','secret-token','reset')
    assert 'secret-token' not in str(exc.value)


def test_smtp_compatibility(settings,monkeypatch):
    monkeypatch.setenv('MAIL_PROVIDER','smtp')
    monkeypatch.setenv('SMTP_HOST','smtp.example.com')
    monkeypatch.setenv('SMTP_FROM','mail@example.com')
    assert mailer.configured()
