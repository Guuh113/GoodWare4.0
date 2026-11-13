# Operação e pendências

- /healthz verifica aplicação e conexão com o banco; o serviço Render usa essa rota.
- Logs HTTP incluem duração, rota parametrizada, status e identificador da requisição.
  Não incluem URLs submetidas, conteúdo de arquivos, tokens, mensagens ou senhas.
- Histórico, análise e perfil carregam sessão e consultas independentes em paralelo.
  Dados privados continuam sem cache no navegador e só são renderizados após autenticação.
- O cache de reputação é temporário; consulte INTEGRACAO_VIRUSTOTAL.md.
- Recuperação: código HTTPS disponível; ativação e teste de entrega ainda exigem
  credencial privada do provedor e remetente verificado. Veja RECUPERACAO_SENHA.md.

## Backup

O script ops/backup.sh pertence à instalação Docker Compose/VPS. Ele NÃO está
rodando automaticamente no serviço gratuito Render. Persistência no PostgreSQL
não substitui backup. Não considerar backup ativo sem confirmar uma cópia
externa e testar restauração em banco isolado.

Para concluir backups externos: definir armazenamento privado durável, fornecer
credencial de banco ao executor de backup por segredo (sem publicar no Git),
executar pg_dump com versão compatível com o servidor, verificar o arquivo com
pg_restore --list e testar restauração em banco separado. Guardar a cópia cifrada,
com acesso restrito e política de retenção. Não usar o disco efêmero do Render
como único destino e nunca restaurar um teste sobre produção.

## Limitações restantes

A hospedagem gratuita pode hibernar; cache e paralelismo não eliminam a espera
de inicialização. Health checks não significam monitoramento externo contínuo
com alertas configurados. Nenhum serviço pago foi criado por esta atualização.
