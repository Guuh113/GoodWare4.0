import io
import json
from urllib.error import HTTPError
import pytest
import url_reputation as rep
from app import create_app
from test_goodware import account, conv

URL = 'https://example.com/'


def stub(monkeypatch, threats=5, total=100, **changes):
    monkeypatch.setenv('VIRUSTOTAL_API_KEY', 'test-only-key')
    calls = []
    attrs = {'last_analysis_stats': {'malicious': threats, 'suspicious': 0,
             'harmless': total-threats, 'undetected': 0}, 'last_analysis_date': 1700000000}
    attrs.update(changes)
    data = {'data': {'type': 'url', 'attributes': attrs}}

    class Client:
        def open(self, req, timeout):
            calls.append((req, timeout))
            return io.BytesIO(json.dumps(data).encode())
    monkeypatch.setattr(rep, 'build_opener', lambda *args: Client())
    return calls


def test_contract_and_no_trust_in_upstream_labels(monkeypatch):
    calls = stub(monkeypatch)
    result = rep.lookup(URL)
    assert result['estado'] == 'consultado' and result['motores_sinalizaram'] == 5
    assert 'SEGURO' not in str(result) and '<script>' not in str(result)
    req, timeout = calls[0]
    assert req.full_url == 'https://www.virustotal.com/api/v3/urls/aHR0cHM6Ly9leGFtcGxlLmNvbS8'
    assert req.method == 'GET' and req.data is None
    assert req.get_header('X-apikey') == 'test-only-key'
    assert result['analisado_em'] == '2023-11-14T22:13:20+00:00'
    assert timeout == 8


@pytest.mark.parametrize('changes', [
    {'last_analysis_stats': {'malicious': -1, 'suspicious': 0, 'harmless': 1, 'undetected': 0}},
    {'last_analysis_stats': {'malicious': True, 'suspicious': 0, 'harmless': 1, 'undetected': 0}},
    {'last_analysis_stats': None}, {'last_analysis_stats': {}},
    {'last_analysis_stats': {'malicious': '1', 'suspicious': 0, 'harmless': 1, 'undetected': 0}}])
def test_malformed_provider_is_not_a_clean_result(monkeypatch, changes):
    stub(monkeypatch, **changes)
    assert rep.lookup(URL)['estado'] == 'indisponivel'


def test_zero_engines_is_unknown(monkeypatch):
    stub(monkeypatch, threats=0, total=0)
    assert rep.lookup(URL)['estado'] == 'sem_dados'


@pytest.mark.parametrize('url', ['https://user:password@example.com', 'https://localhost',
    'http://127.0.0.1', 'http://10.0.0.1', 'http://[::1]', 'https://app.internal',
    'https://example.com/#private-token'])
def test_private_targets_not_sent(monkeypatch, url):
    calls = stub(monkeypatch)
    assert rep.lookup(url)['estado'] == 'nao_enviado'
    assert not calls


def test_missing_configuration(monkeypatch):
    monkeypatch.delenv('VIRUSTOTAL_API_KEY', raising=False)
    assert not rep.configured()
    assert rep.lookup(URL)['estado'] == 'nao_configurado'


@pytest.mark.parametrize('error', [TimeoutError(), HTTPError('https://scanner.example',429,'rate limit',{},None),
    HTTPError('https://scanner.example',500,'key=secret',{},None)])
def test_failure_does_not_leak_upstream(monkeypatch, error):
    monkeypatch.setenv('VIRUSTOTAL_API_KEY', 'test-only-key')
    class Client:
        def open(self, *args, **kwargs): raise error
    monkeypatch.setattr(rep, 'build_opener', lambda *args: Client())
    result = rep.lookup(URL)
    assert result['estado'] in ('indisponivel','limite_excedido')
    assert 'secret' not in str(result)


def test_auth_consent_persistence_and_fallback(tmp_path, monkeypatch):
    calls = stub(monkeypatch)
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'DATABASE': str(tmp_path/'test.db')})
    a, h = account(app); cid = conv(a, h)
    payload = {'url': URL, 'conversation_id': cid}
    assert app.test_client().post('/api/analisar-url',json=payload).status_code in (401,403)
    for consent in (None, False, 'true'):
        result = a.post('/api/analisar-url',json=dict(payload,consultar_reputacao=consent),headers=h)
        assert result.status_code == 200 and 'reputacao' not in result.json['resultado']
    assert not calls
    result = a.post('/api/analisar-url',json=dict(payload,consultar_reputacao=True),headers=h).json['resultado']
    assert len(calls) == 1 and result['reputacao']['motores_sinalizaram'] == 5
    assert result['medidor']['valor'] == 35  # Provider percentage is separate.
    assert a.get('/api/reports/'+result['id']).json['reputacao'] == result['reputacao']
    b, hb = account(app,'b@example.com')
    assert b.get('/api/reports/'+result['id']).status_code == 404
    monkeypatch.delenv('VIRUSTOTAL_API_KEY')
    result = a.post('/api/analisar-url',json=dict(payload,consultar_reputacao=True),headers=h).json['resultado']
    assert result['reputacao']['estado'] == 'nao_configurado'
    assert result['classificacao'] == 'Inspeção sintática'

@pytest.mark.parametrize('code,state', [(404,'nao_encontrado'),(401,'credencial_invalida'),(403,'acesso_negado'),(429,'limite_excedido')])
def test_provider_errors(monkeypatch, code, state):
    monkeypatch.setenv('VIRUSTOTAL_API_KEY', 'test-only-key')
    class Client:
        def open(self, *a, **kw): raise HTTPError('https://www.virustotal.com',code,'secret',{},None)
    monkeypatch.setattr(rep, 'build_opener', lambda *a: Client())
    result=rep.lookup(URL)
    assert result['estado']==state and 'secret' not in str(result)


def test_file_consent_hash_only_persistence(tmp_path, monkeypatch):
    import hashlib
    contents=b'print("hello")'
    digest=hashlib.sha256(contents).hexdigest()
    calls=[]
    monkeypatch.setenv('VIRUSTOTAL_API_KEY','test-only-key')
    class Client:
        def open(self, req, timeout):
            calls.append(req)
            return io.BytesIO(json.dumps({'data':{'type':'file','id':digest,'attributes':{
                'last_analysis_stats':{'malicious':1,'suspicious':0,'harmless':0,'undetected':9}}}}).encode())
    monkeypatch.setattr(rep,'build_opener',lambda *a:Client())
    app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':str(tmp_path/'file.db')})
    a,h=account(app);cid=conv(a,h)
    for consent in ('false','true'):
        response=a.post('/api/analisar-ficheiro',data={'file':(io.BytesIO(contents),'hello.py'),
            'conversation_id':cid,'consultar_reputacao':consent},headers=h)
        assert response.status_code==200
        result=response.json['resultado']
        if consent=='false': assert 'reputacao' not in result and not calls
    assert len(calls)==1 and calls[0].full_url.endswith('/files/'+digest)
    assert calls[0].data is None and 'hello' not in calls[0].full_url
    assert result['reputacao']['motores_sinalizaram']==1
    assert result['classificacao']=='Sinalização externa — requer investigação'
    assert not any('não verifica assinatura digital ou reputação externa' in item for item in result['limitacoes'])
    assert a.get('/api/reports/'+result['id']).json['reputacao']==result['reputacao']


def test_redirects_not_followed():
    assert rep.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example') is None
