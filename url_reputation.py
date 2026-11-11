"""Client for the SENAI URL reputation API. Never fetches the submitted URL."""
import ipaddress
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint():
    value = os.getenv('SENAI_API_URL', '').strip().rstrip('/')
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            return None
        parsed.port  # Reject malformed ports.
    except ValueError:
        return None
    return value + '/api/v1/scans/url'


def configured():
    return endpoint() is not None


def shareable(value):
    """Do not disclose credentials, fragments or internal addresses to a third party."""
    try:
        p = urlsplit(value)
        host = (p.hostname or '').lower().rstrip('.')
        if p.username is not None or p.password is not None or p.fragment:
            return False
        if not host or '.' not in host or host.endswith(('.localhost', '.local', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            # Domain names are data for the provider, not destinations we connect to.
            return ':' not in host and not host.replace('.', '').isdigit()
    except ValueError:
        return False


def lookup(value):
    result = {'fonte': 'API SENAI / VirusTotal',
              'consultado_em': datetime.now(timezone.utc).isoformat()}
    target = endpoint()
    if not target:
        return dict(result, estado='nao_configurado', detalhe='Consulta externa não configurada. Apenas a inspeção sintática foi realizada.')
    if not shareable(value):
        return dict(result, estado='nao_enviado', detalhe='Endereços internos, credenciais ou fragmentos não são enviados ao serviço externo.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    token = os.getenv('SENAI_API_TOKEN', '').strip()
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(target, data=json.dumps({'url': value}).encode(), headers=headers, method='POST')
    try:
        with build_opener(NoRedirect()).open(req, timeout=8) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('oversized response')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('urlAnalisada') != value:
            raise ValueError('mismatched target')
        total, threats, score = (data.get(k) for k in ('totalMotores', 'motoresAmeaca', 'pontuacaoRisco'))
        if (any(type(n) is not int for n in (total, threats, score))
                or not 0 <= threats <= total <= 10000 or not 0 <= score <= 100):
            raise ValueError('invalid counters')
        expected = threats * 100 // total if total else 0
        if score != expected:
            raise ValueError('inconsistent score')
        # Do not repeat the API's "SEGURO" label or treat its percentage as probability.
        return dict(result, estado='consultado' if total else 'sem_dados',
                    motores_sinalizaram=threats, total_motores=total, percentual_motores=score,
                    detalhe=(f'{threats} de {total} motores sinalizaram a URL. Isso não confirma infecção.'
                             if total else 'O provedor não retornou motores com resultados.'))
    except HTTPError as exc:
        state = 'limite_excedido' if exc.code == 429 else 'indisponivel'
    except (URLError, OSError, ValueError, TypeError, RecursionError):
        state = 'indisponivel'
    return dict(result, estado=state, detalhe='Não foi possível obter a reputação externa. Apenas a inspeção sintática foi realizada; isso não significa que a URL seja segura.')


def enrich(report):
    result = lookup(report['alvo'])
    report['reputacao'] = result
    report['explicacao'] += ' ' + result['detalhe']
    report['limitacoes'].append('A consulta externa usa resultados já existentes no VirusTotal; não inicia nova varredura. A API não informa a data da análise original e pode retornar dados desatualizados.')
    if result['estado'] == 'consultado':
        report['classificacao'] = 'Inspeção sintática e consulta de reputação'
        report['explicacao'] = 'O GoodWare não abriu a URL. ' + result['detalhe']
        if result['motores_sinalizaram']:
            report['evidencias'].append({
                'id': 'E' + str(len(report['evidencias']) + 1),
                'categoria': 'reputacao_externa', 'titulo': 'URL sinalizada por motores externos',
                'arquivo': report['alvo'], 'localizacao': {'componente': 'Reputação externa'},
                'justificativa': result['detalhe'], 'natureza': 'Sinalização externa, não confirmação de infecção'})
    return report
