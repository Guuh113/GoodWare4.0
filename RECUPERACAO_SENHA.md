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
