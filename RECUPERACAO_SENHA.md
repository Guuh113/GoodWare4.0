# Recuperação de senha

O formulário recuperar.html gera um link válido por 30 minutos. O banco guarda
somente o hash do token. O token é de uso único e a troca invalida as sessões.
A resposta não informa se o e-mail possui conta.

## Ativação com Resend (HTTPS)

1. Configure uma conta no provedor e verifique seu domínio/remetente. Confira
   os limites e o plano antes de ativar; nenhuma conta ou assinatura é criada pelo código.
2. Nas variáveis privadas do serviço configure:
   - MAIL_PROVIDER=resend
   - RESEND_API_KEY: sua chave privada, nunca no Git ou JavaScript.
   - MAIL_FROM: remetente verificado, como GoodWare <contato@seu-dominio>.
   - PUBLIC_BASE_URL=https://goodware-i8y9.onrender.com (ou seu domínio HTTPS).
3. Faça deploy e confirme mail_configured=true em /api/status. Esse campo
   verifica presença da configuração, não entrega de mensagens.
4. Teste com uma conta sua: solicite recuperação, confira a caixa de entrada,
   redefina a senha, confirme o login e que o link não pode ser reutilizado.
   Repita com token expirado. Só depois considere a entrega validada.

Sem chave e remetente, a recuperação permanece indisponível. Não habilite
EMAIL_VERIFICATION_REQUIRED antes de validar entrega para evitar bloqueio de login.
O remetente de teste do provedor não substitui um remetente verificado para usuários reais.
SMTP continua disponível em hospedagens que permitem suas portas.

Referências: https://resend.com/docs/api-reference/emails/send-email
https://render.com/docs/free (bloqueio SMTP no plano gratuito).


## Enviar pelo Gmail do proprietário (sem domínio próprio)

O GoodWare também aceita MAIL_PROVIDER=gmail_api. Assim o link sai da caixa
Gmail que autorizou a integração. O servidor envia pela Gmail API em HTTPS;
não precisa expor senha da conta nem usar SMTP.

1. No Google Cloud Console, crie um projeto, ative Gmail API e configure a tela
   de consentimento OAuth. Como o app estará em teste, inclua a conta Gmail
   proprietária como usuária de teste. Crie um OAuth Client ID do tipo Web.
2. Gere autorização OAuth para a conta dona com escopo
   https://www.googleapis.com/auth/gmail.send e acesso offline. Troque o código
   autorizado por um refresh token. O refresh token é uma credencial secreta.
3. Em Render > serviço GoodWare > Environment, configure de forma privada:
   MAIL_PROVIDER=gmail_api, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
   GMAIL_REFRESH_TOKEN e PUBLIC_BASE_URL=https://goodware-i8y9.onrender.com.
   Não preencha nem publique o token no Git, JavaScript ou nesta conversa.
4. Implante, confirme mail_configured=true e faça teste para a própria caixa.

O proprietário concede ao GoodWare permissão para enviar e-mails pela conta;
revogue o acesso na conta Google se deixar de usá-lo. Apps OAuth em modo de teste
podem exigir nova autorização; não habilite confirmação obrigatória de e-mail
antes do teste real de recuperação. A conta autenticada no OAuth define o remetente.
O GoodWare não lê a caixa de entrada: o escopo é somente envio.

Referência: https://developers.google.com/workspace/gmail/api/auth/web-server
https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
