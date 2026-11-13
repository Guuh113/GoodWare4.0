"""Transactional account mail. Secrets and reset tokens stay on the server."""
import json
import base64
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit, quote, urlencode
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
    if provider == 'gmail_api':
        return all(os.getenv(key, '').strip() for key in ('GMAIL_CLIENT_ID','GMAIL_CLIENT_SECRET','GMAIL_REFRESH_TOKEN'))
    return provider == 'smtp' and bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'))


def send_token(email, token, purpose):
    if not configured() or purpose not in ('reset', 'verify'):
        raise RuntimeError('Envio de e-mail não configurado.')
    page = 'redefinir.html' if purpose == 'reset' else 'verificar.html'
    subject = 'GoodWare — ' + ('recuperação de senha' if purpose == 'reset' else 'verifique seu e-mail')
    body = f'Use este link em até 30 minutos:\n{base_url()}/{page}#token={quote(token, safe="")}\n\nSe não solicitou, ignore esta mensagem.'
    provider = os.getenv('MAIL_PROVIDER', 'smtp').strip().lower()
    if provider == 'gmail_api':
        # Gmail is both the verified sender and the mailbox owner authorizing this app.
        # Send only through Google's HTTPS API; do not spoof a From address.
        message = EmailMessage()
        message['To'], message['Subject'] = email, subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip('=')
        try:
            token_request = Request('https://oauth2.googleapis.com/token',
                data=urlencode({'client_id': os.environ['GMAIL_CLIENT_ID'],
                    'client_secret': os.environ['GMAIL_CLIENT_SECRET'],
                    'refresh_token': os.environ['GMAIL_REFRESH_TOKEN'],
                    'grant_type': 'refresh_token'}).encode(),
                headers={'Content-Type':'application/x-www-form-urlencoded'}, method='POST')
            with build_opener(NoRedirect()).open(token_request, timeout=15) as response:
                auth = json.loads(response.read(65537))
            access_token = auth.get('access_token') if isinstance(auth, dict) else None
            if not isinstance(access_token, str) or not access_token:
                raise ValueError('Missing access token')
            send_request = Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                data=json.dumps({'raw':raw}).encode(),
                headers={'Authorization':'Bearer '+access_token,'Content-Type':'application/json'}, method='POST')
            with build_opener(NoRedirect()).open(send_request, timeout=15) as response:
                sent = json.loads(response.read(65537))
            if not isinstance(sent, dict) or not sent.get('id'):
                raise ValueError('Missing message id')
        except Exception:
            raise RuntimeError('Não foi possível enviar pelo Gmail autorizado. Verifique a conexão e as credenciais privadas.') from None
        return
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
