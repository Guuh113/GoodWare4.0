# Publicar o GoodWare 4.0

## Opção principal: Render + PostgreSQL

A configuração segue as referências oficiais: [Flask](https://render.com/docs/deploy-flask), [Docker](https://render.com/docs/docker), [Blueprint](https://render.com/docs/blueprint-spec) e [PostgreSQL](https://render.com/docs/postgresql). Consulte preços e retenção de backups no painel antes de criar os serviços; não há orçamento ou garantia de disponibilidade embutidos neste projeto.

1. Coloque **o conteúdo de `goodware-site1` na raiz** do repositório Git autorizado (o repositório atual é público). Não envie `.env`, `instance`, `.venv`, backups ou credenciais.
2. Conecte esse repositório à conta Render. Crie um Blueprint a partir do `render.yaml` e revise o plano e custos da aplicação e do banco antes de aprovar.
3. O Blueprint cria uma aplicação Docker e uma referência ao PostgreSQL. Acesso público ao banco fica bloqueado (`ipAllowList: []`). O segredo de sessão é gerado pelo serviço.
4. Preencha `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` e `PUBLIC_BASE_URL`. Para autenticação por e-mail, adicione as variáveis SMTP descritas no README. Não coloque segredos em arquivos versionados.
5. Após conhecer o domínio do serviço, confirme `PUBLIC_BASE_URL=https://SEU-SUBDOMINIO.onrender.com`. Habilite verificação de e-mail somente após testar SMTP.
6. Inicie o deploy. Aguarde o health check `/healthz`. A inicialização aplica migrações e executa Gunicorn. Configure o domínio próprio pelo painel se desejado.
7. Valide pelo endereço HTTPS: cadastro → login → upload → relatório → Aegis → recarregar conversa → logout. Confirme que dois usuários não acessam IDs um do outro. Valide e-mail e uma resposta real do LLM.
8. Só divulgue o link depois dessas verificações. Sem chave/modelo, o site abre mas o chat informa indisponibilidade.

O `render.yaml` usa planos gratuitos para avaliação, conforme o fluxo inicial do Render; isso não atende à exigência de serviço continuamente ativo. Para operação contínua, revise e use `render.production.yaml`, que prevê aplicação paga e exige selecionar/revisar o plano do PostgreSQL antes de provisionar. Não crie recursos pagos sem definir o orçamento. Os planos são configurações iniciais, não medições de capacidade. Ajuste memória/concurrency após teste de carga. O banco usa o plano padrão do provedor, sujeito a custo; selecione explicitamente a opção desejada ao revisar. Habilite e confirme a política de backups gerenciados compatível com esse plano. Monitore saúde, consumo e falhas de backup; `/healthz` verifica aplicação/banco, não disponibilidade do provedor de IA ou SMTP.

### Atualizações aprovadas / CI

O `render.yaml` deixa deploy automático desligado. `.github/workflows/ci.yml` executa testes, PostgreSQL descartável e build da imagem. Configure o ambiente GitHub **production** com revisores obrigatórios e o segredo `RENDER_DEPLOY_HOOK`, obtido no serviço Render. Acione o workflow manualmente na branch `main`. O job de deploy só roda após testes e aprovação do ambiente, se a proteção foi realmente configurada no GitHub.

O workflow apenas solicita o deploy ao Render; verifique a conclusão no painel e `/healthz`. Um HTTP bem-sucedido no hook não comprova que a nova versão ficou saudável. Proteja `main` e exija revisão para alterações. A configuração não cria automaticamente políticas de revisão na sua conta.

## Alternativa: VPS com Docker Compose e HTTPS

Requisitos: VPS Linux ativo, Docker/Compose, domínio apontando para o IP e portas 80/443 liberadas. Use disco com criptografia e controle de acesso no provedor.

1. Copie `.env.example` para `.env` no servidor.
2. Defina `SECRET_KEY` aleatória de ao menos 32 caracteres, `POSTGRES_PASSWORD` alfanumérica longa, `GOODWARE_DOMAIN`, `PUBLIC_BASE_URL=https://SEU-DOMINIO` e as variáveis do modelo/e-mail.
3. Na raiz do projeto: `docker compose up -d --build`.
4. A aplicação e o banco não expõem portas públicas diretamente. O Caddy termina TLS. Confirme que o DNS está correto e que não existe outro serviço usando 80/443.
5. Verifique `docker compose ps`, `docker compose logs --tail=100 app` e o endpoint HTTPS `/healthz`.

`TRUST_PROXY=1` só deve ser habilitado quando exatamente um proxy confiável estiver à frente da aplicação. Nunca exponha o contêiner diretamente com esse modo, pois cabeçalhos de proxy podem ser falsificados. O compose usa limite de memória/CPU e reinício `unless-stopped`, mas não substitui observabilidade externa.

## Backups e restauração

No compose, o serviço `backup` executa `pg_dump -Fc` diariamente em volume privado e remove cópias com mais de sete dias. Um backup local no mesmo servidor não protege contra perda do servidor: configure cópia criptografada para armazenamento externo privado e monitore falhas. Criptografia em repouso e transporte ao destino externo são responsabilidade da infraestrutura; não há promessa de criptografia do volume pelo aplicativo.

Para restaurar, primeiro interrompa gravações, preserve o banco atual e restaure em uma instância separada para validação. Exemplo com um dump local e um banco **novo/vazio** configurado no ambiente:

```sh
pg_restore --no-owner --dbname="$RESTORE_DATABASE_URL" /caminho/backup.dump
```

Depois valide contas/relatórios e a versão de esquema antes de alterar `DATABASE_URL` da aplicação. Não execute restauração sobre o banco ativo sem plano e backup. Teste periodicamente a restauração. Dados excluídos do banco ativo podem persistir em backups até expirar a retenção.

## Rollback

Guarde o identificador do commit/imagem de cada release. Se a aplicação falhar, selecione a versão anterior no provedor ou volte o repositório a uma release aprovada e reconstrua. A migração atual é aditiva; não remove colunas. Reverter código não reverte dados. Nunca restaure um backup antigo automaticamente, pois isso pode perder gravações recentes. Faça staging e uma estratégia de migração compatível antes de mudanças destrutivas futuras.

## Migrar dados locais

Faça cópia do SQLite, configure o PostgreSQL de destino e execute `python manage.py import-sqlite caminho/goodware.db` em ambiente controlado. O destino deve estar vazio de usuários. Credenciais de conexão ficam em variáveis de ambiente. Sessões e tokens antigos são descartados; será necessário novo login. O administrador deve testar esse procedimento em staging.

## Pendências externas desta entrega

- Corrigir a permissão efetiva de escrita da integração GitHub ou enviar os arquivos pelo painel autenticado.
- Provisionamento PostgreSQL, execução do teste de integração e build Docker no ambiente de destino.
- Chave/modelo LLM e teste real de geração.
- Serviço SMTP e teste de entrega de e-mails.
- Domínio, TLS, backup remoto, alertas e política de retenção.
- Revisão visual em navegador desktop/mobile e teste de carga no ambiente publicado.

Nada foi implantado externamente durante a criação deste pacote. Não existe link público verificado para informar.

## Bloqueio atual e caminho alternativo concreto

O usuário confirmou My Workspace e Guuh113/IA_ANTIVIRUS. Consultas ao Render funcionaram; nenhuma aplicação ou banco foi encontrado. GitHub permitiu leitura, mas recusou criar a árvore de arquivos com HTTP 403 `Resource not accessible by integration`. A causa exata da permissão insuficiente (instalação/escopos) não foi confirmada. Não se tentou contornar essa restrição.

1. No GitHub, revise a instalação do aplicativo conectado: acesso ao repositório IA_ANTIVIRUS e permissões Contents e Workflows de escrita. Não envie tokens ou chaves no chat.
2. Alternativa sem a integração de escrita: extraia o ZIP; usando sua sessão no GitHub, envie o conteúdo de `goodware-site1` à raiz de `Guuh113/IA_ANTIVIRUS` por Git ou **Add file → Upload files**. Preserve o histórico. Confirme que Dockerfile, app.py, assets/fonts e render.yaml aparecem na raiz e que .env.example e .github/workflows/ci.yml foram incluídos. Não envie .env, dados de usuários, caches ou backups. O ZIP como único arquivo não permite ao Render construir o aplicativo.
3. Após confirmar os arquivos no GitHub, abra https://dashboard.render.com/blueprint/new?repo=https://github.com/Guuh113/IA_ANTIVIRUS e conecte o GitHub ao Render caso solicitado. Escolha o workspace já confirmado.
4. Para avaliação, revise `render.yaml`. Para uso continuamente ativo, substitua pelo conteúdo de `render.production.yaml` após selecionar planos/orçamento; configure explicitamente o plano do banco. Nenhum plano pago foi contratado.
5. Preencha os segredos no painel e aplique. Depois verifique `/healthz`, cadastro/login e uma conversa real. Não publique o endereço como funcional apenas porque o build começou.

O plano gratuito de web service suspende por inatividade; PostgreSQL gratuito expira em 30 dias. SMTP nas portas 25/465/587 não está disponível no web service gratuito. Portanto o plano gratuito não satisfaz disponibilidade contínua e recuperação de senha por este transporte. Fonte: https://render.com/docs/free (consultada em 14/10/2026). O operador deve escolher um plano compatível ou adaptar e testar e-mail via API HTTPS.
