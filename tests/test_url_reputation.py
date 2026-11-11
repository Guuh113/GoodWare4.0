import io
import json
from urllib.error import HTTPError
import pytest
import url_reputation as rep
from app import create_app
from test_goodware import account, conv

URL = 'https://example.com/'


def stub(monkeypatch, threats=5, total=100, **changes):
    monkeypatch.setenv('SENAI_API_URL', 'https://scanner.example')
    calls = []
    data = dict(urlAnalisada=URL, motoresAmeaca=threats, totalMotores=total,
                pontuacaoRisco=threats * 100 // total if total else 0,
                status='SEGURO', mensagemResumo='<script>untrusted</script>')
    data.update(changes)

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
    assert req.full_url == 'https://scanner.example/api/v1/scans/url'
    assert req.method == 'POST' and json.loads(req.data) == {'url': URL}
    assert timeout == 8


@pytest.mark.parametrize('changes', [{'totalMotores': -1}, {'motoresAmeaca': True},
    {'pontuacaoRisco': 99}, {'urlAnalisada': 'https://other.example'}, {'totalMotores': '100'}])
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


@pytest.mark.parametrize('endpoint', ['', 'http://scanner.example', 'https://user:pass@scanner.example',
    'https://scanner.example?key=secret', 'https://scanner.example:invalid'])
def test_invalid_configuration(monkeypatch, endpoint):
    monkeypatch.setenv('SENAI_API_URL', endpoint)
    assert not rep.configured()
    assert rep.lookup(URL)['estado'] == 'nao_configurado'


@pytest.mark.parametrize('error', [TimeoutError(), HTTPError('https://scanner.example',429,'rate limit',{},None),
    HTTPError('https://scanner.example',500,'key=secret',{},None)])
def test_failure_does_not_leak_upstream(monkeypatch, error):
    monkeypatch.setenv('SENAI_API_URL', 'https://scanner.example')
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
    monkeypatch.delenv('SENAI_API_URL')
    result = a.post('/api/analisar-url',json=dict(payload,consultar_reputacao=True),headers=h).json['resultado']
    assert result['reputacao']['estado'] == 'nao_configurado'
    assert result['classificacao'] == 'Inspeção sintática'
