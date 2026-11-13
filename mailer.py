"""Transactional account mail. Secrets and reset tokens stay on the server."""
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit, quote
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def base_url():
    base = os.getenv('PUBLIC_BASE_URL', '').strip().rstrip('/')
    try:
        parsed = urlsplit(base)
        valid = parsed.scheme in ('https', 'http') and parsed.hostname and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
        if os.getenv('APP_ENV') == 'production' and parsed.scheme != 'https':
            valid = False
        return base if valid else ''
    except ValueError:
        return ''


def configured():
    provider = os.getenv('MAIL_PROVIDER', 'smtp').strip().lower()
    if not base_url():
        return False
    if provider == 'resend':
        return bool(os.getenv('RESEND_API_KEY', '').strip() and os.getenv('MAIL_FROM', '').strip())
    return provider == 'smtp' and bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'))


def send_token(email, token, purpose):
    if not configured() or purpose not in ('reset', 'verify'):
        raise RuntimeError('Envio de e-mail não configurado.')
    page = 'redefinir.html' if purpose == 'reset' else 'verificar.html'
    subject = 'GoodWare — ' + ('recuperação de senha' if purpose == 'reset' else 'verifique seu e-mail')
    body = f'Use este link em até 30 minutos:\n{base_url()}/{page}#token={quote(token, safe="")}\n\nSe não solicitou, ignore esta mensagem.'
    if os.getenv('MAIL_PROVIDER', 'smtp').strip().lower() == 'resend':
        payload = {'from': os.environ['MAIL_FROM'], 'to': [email], 'subject': subject, 'text': body}
        request = Request('https://api.resend.com/emails', data=json.dumps(payload).encode(),
                          headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'], 'Content-Type': 'application/json'}, method='POST')
        try:
            with build_opener(NoRedirect()).open(request, timeout=15) as response:
                if response.status not in (200, 201, 202):
                    raise ValueError('Rejected')
                result = json.loads(response.read(65537))
                if not isinstance(result, dict) or not result.get('id'):
                    raise ValueError('Missing message id')
        except Exception:
            # Provider errors can contain recipient addresses; do not expose/log them.
            raise RuntimeError('Serviço de e-mail temporariamente indisponível.') from None
        return
    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = os.environ['SMTP_FROM'], email, subject
    msg.set_content(body)
    with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', '587')), timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if os.getenv('SMTP_USER'):
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(msg)
