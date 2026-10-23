import os,smtplib,ssl
from email.message import EmailMessage

def configured():return bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM') and os.getenv('PUBLIC_BASE_URL'))
def send_token(email,token,purpose):
    base=os.environ['PUBLIC_BASE_URL'].rstrip('/')
    page='redefinir.html' if purpose=='reset' else 'verificar.html'
    msg=EmailMessage();msg['From']=os.environ['SMTP_FROM'];msg['To']=email
    msg['Subject']='GoodWare — '+('recuperação de senha' if purpose=='reset' else 'verifique seu e-mail')
    msg.set_content(f'Use este link em até 30 minutos:\n{base}/{page}#token={token}\n\nSe não solicitou, ignore esta mensagem.')
    context=ssl.create_default_context()
    with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
        smtp.starttls(context=context)
        if os.getenv('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
        smtp.send_message(msg)
