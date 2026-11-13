"""Direct VirusTotal v3 reputation client. Never fetches the submitted URL."""
import base64
import re
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


def configured():
    return bool(os.getenv('VIRUSTOTAL_API_KEY', '').strip())


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


def lookup(value, kind='url'):
    result = {'fonte': 'VirusTotal API v3',
              'consultado_em': datetime.now(timezone.utc).isoformat()}
    if not configured():
        return dict(result, estado='nao_configurado', detalhe='VirusTotal não configurado. A análise local continua disponível.')
    if kind == 'url':
        if not shareable(value):
            return dict(result, estado='nao_enviado', detalhe='Endereços internos, credenciais ou fragmentos não são enviados ao serviço externo.')
        identifier = base64.urlsafe_b64encode(value.encode()).decode().rstrip('=')
        resource = 'urls'
    elif kind == 'file' and re.fullmatch(r'[a-f0-9]{64}', value):
        identifier, resource = value, 'files'
    else:
        return dict(result, estado='nao_enviado', detalhe='Identificador inválido para consulta externa.')
    req = Request('https://www.virustotal.com/api/v3/' + resource + '/' + identifier,
                  headers={'Accept': 'application/json', 'x-apikey': os.getenv('VIRUSTOTAL_API_KEY').strip()}, method='GET')
    try:
        with build_opener(NoRedirect()).open(req, timeout=8) as response:
            raw = response.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('oversized response')
        data = json.loads(raw)['data']
        if data.get('type') != kind:
            raise ValueError('wrong object type')
        if kind == 'file' and data.get('id') != value:
            raise ValueError('wrong file')
        attrs = data['attributes']
        stats = attrs['last_analysis_stats']
        counts = [stats[k] for k in ('malicious', 'suspicious', 'harmless', 'undetected')]
        if any(type(n) is not int or not 0 <= n <= 10000 for n in counts):
            raise ValueError('invalid counters')
        total, threats = sum(counts), sum(counts[:2])
        if total > 10000:
            raise ValueError('invalid total')
        stamp = attrs.get('last_analysis_date')
        analyzed = (datetime.fromtimestamp(stamp, timezone.utc).isoformat()
                    if type(stamp) is int and 0 < stamp <= datetime.now(timezone.utc).timestamp() else None)
        return dict(result, estado='consultado' if total else 'sem_dados',
                    motores_sinalizaram=threats, total_motores=total,
                    percentual_motores=threats * 100 // total if total else 0,
                    analisado_em=analyzed,
                    detalhe=(f'{threats} de {total} motores com resultado sinalizaram o item. Isso não confirma infecção; zero alertas não garante segurança.'
                             if total else 'O provedor não retornou motores com resultados.'))
    except HTTPError as exc:
        state = {404: 'nao_encontrado', 429: 'limite_excedido', 401: 'credencial_invalida', 403: 'acesso_negado'}.get(exc.code, 'indisponivel')
    except (URLError, OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        state = 'indisponivel'
    messages = {
        'nao_encontrado': 'Item ainda não encontrado no VirusTotal. Nenhum arquivo foi enviado e nenhuma nova varredura foi iniciada.',
        'limite_excedido': 'Limite de consultas do VirusTotal atingido. Tente novamente mais tarde.',
        'credencial_invalida': 'A credencial do VirusTotal foi recusada. O administrador precisa verificar a configuração.',
        'acesso_negado': 'O VirusTotal não autorizou esta consulta. Verifique as permissões da conta.',
    }
    return dict(result, estado=state, detalhe=messages.get(state, 'VirusTotal indisponível no momento.') + ' A análise local foi preservada; isso não significa que o item seja seguro.')


def enrich(report):
    is_file = report.get('tipo') == 'FICHEIRO'
    result = lookup(report['sha256'], 'file') if is_file else lookup(report['alvo'])
    report['reputacao'] = result
    if is_file:
        report['limitacoes'] = [item.replace(' ou reputação externa', '') for item in report.get('limitacoes', [])]
    report['explicacao'] += ' ' + result['detalhe']
    report['limitacoes'].append('A consulta externa usa resultados já existentes no VirusTotal; não inicia nova varredura. Os resultados podem estar desatualizados. Arquivos são consultados somente pelo SHA-256, sem envio do conteúdo.')
    if result['estado'] == 'consultado':
        if not is_file:
            report['classificacao'] = 'Inspeção sintática e consulta de reputação'
        # Preserve local analysis and explanation alongside external evidence.
        if result['motores_sinalizaram']:
            report['classificacao'] = 'Sinalização externa — requer investigação'
            report['evidencias'].append({
                'id': 'E' + str(len(report['evidencias']) + 1),
                'categoria': 'reputacao_externa', 'titulo': 'Item sinalizado por motores externos',
                'arquivo': report['alvo'], 'localizacao': {'componente': 'Reputação externa'},
                'justificativa': result['detalhe'], 'natureza': 'Sinalização externa, não confirmação de infecção'})
    return report
