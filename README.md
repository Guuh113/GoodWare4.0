# GoodWare 4.0.1 · Aegis Intelligence

Plataforma Flask de análise estática com contas reais, relatórios persistentes, assistente generativo configurável e base técnica com fontes. Mantém a identidade original: preto `#0B0B0D`, painéis escuros e roxo `#7B61FF`.

**Estado da entrega:** implementação local e arquivos de produção preparados. Não foi publicado um site nem provisionado um banco remoto. Não há link público ativo nesta entrega. O funcionamento 24 horas exige infraestrutura ativa, independente do computador do desenvolvedor. Hospedagem, banco, e-mail e modelo podem gerar custos.

## Correção de login

Leia CORRECAO_LOGIN.md antes de atualizar. Preserve seu .env e a pasta instance para manter as contas existentes.

## Abrir localmente no Windows

1. Clique no ZIP com o botão direito → **Extrair Tudo**.
2. Abra a pasta extraída `goodware-site1`. Confira se `requirements.txt`, `app.py`, `.env.example` e `iniciar.py` estão junto do `.bat`.
3. Execute **INICIAR_GOODWARE.bat** com Python 3.11/3.12 instalado. O iniciador instala dependências, gera um segredo persistente e abre o endereço correto.
4. Clique em **Criar uma conta**. Preencha nome, usuário, e-mail e senhas iguais (12–256 caracteres). Após a confirmação, faça login.

Não abra o HTML diretamente nem use Live Server. Nesta modalidade o terminal precisa continuar aberto; isso não equivale a hospedagem.

Em Linux/macOS: crie e ative um ambiente virtual, instale `requirements.txt` e execute `python iniciar.py`. Não use o servidor local como implantação pública.

## Novidades da versão 4.0

- Mission Control com boas-vindas, ações rápidas, totais reais e pontuação de critérios explícitos.
- Radar com filtros de data/nome/risco, gráficos interativos acessíveis, categorias e linha do tempo das últimas 100 análises. Sem feed externo fictício.
- Comparação autorizada de dois relatórios: hash, indicadores comuns e exclusivos.
- Exportação PDF no servidor com evidências, cobertura, SHA-256, limites e orientações; fontes DejaVu incorporadas e licença incluída.
- Exportação JSON de conta, conversas, vínculos de relatórios e feedback, sem credenciais.
- Exclusão de todo o histórico com confirmação de senha, desativando a recuperação de memória.
- Aegis com streaming real do contrato SSE do provedor para NDJSON na interface. Exige Chat Completions com `stream: true` e marcador `[DONE]`. Uma resposta parcial não é salva como concluída. O modo não streaming permanece disponível na API.
- Markdown seguro limitado a títulos, negrito, código e listas simples; HTML, imagens e links Markdown não são interpretados.
- Upload dentro da conversa, relatório vinculado no banco (migração v3), botões de explicação simples/técnica, Aegis Explain por evidência e feedback da resposta.
- Knowledge com fontes e datas de revisão, e um desafio educativo de phishing com correção fixa claramente identificada. Perguntas abertas usam o modelo configurado.
- Metadados de formato/tamanho e sugestões de revisão dos padrões estáticos de código.
- Logs HTTP estruturados sem conteúdo, caminhos de arquivos, senhas ou mensagens. Identificador de requisição no cabeçalho.

O progresso da investigação informa o arquivo em processamento e resultados efetivamente concluídos. Não há porcentagem simulada ou confirmação de etapas internas antes de terminarem.

## Navegação implementada

- **Painel:** totais reais de análises, arquivos, indicadores e relatórios de risco alto; lista recente.
- **Analisar:** arquivos, pastas, ZIPs, PE e texto; URL com inspeção somente sintática.
- **Histórico:** até 100 relatórios recentes, filtro de nome/hash e exclusão autorizada.
- **Aegis AI:** página exclusiva, histórico lateral, nova conversa, contexto de relatório, respostas longas e exclusão de conversas.
- **Minha conta:** perfil, autorização de memória, verificação de e-mail, feedback e exclusão de conta com senha.
- **Administração:** métricas agregadas, eventos sem conteúdo privado e lista de fontes. A concessão de acesso exige operação administrativa no servidor.

Login/cadastro separados, recuperação de senha e confirmação de e-mail têm backend real. Login social não é anunciado porque não está integrado.

## Configurar a IA generativa

No `.env` local ou nos segredos da hospedagem:

```dotenv
LLM_BASE_URL=https://SEU-PROVEDOR-COMPATIVEL/v1
LLM_MODEL=IDENTIFICADOR-DO-MODELO
LLM_API_KEY=CHAVE-DO-PROVEDOR
```

Substitua os valores de exemplo. Obtenha a chave no painel do provedor escolhido e habilite a cobrança/quota quando necessária. O contrato implementado é **Chat Completions** (`POST /chat/completions`, `messages`, `model`, `max_tokens`). Confirme que seu modelo aceita esse contrato. Uma assinatura de chat não fornece automaticamente uma chave de API para este servidor.

Também aceita servidor local compatível em `http://127.0.0.1:11434/v1`; o modelo deve estar previamente instalado no serviço. Em nuvem, `127.0.0.1` refere-se ao contêiner, não ao seu computador. Provedores remotos exigem HTTPS. A chave nunca vai para o navegador.

Sem configuração, o chat informa indisponibilidade; não usa respostas por palavras-chave como substituto. A conectividade com um modelo real não foi validada nesta entrega por ausência de credenciais/modelo ativo.

As mensagens e trechos recuperados serão enviados ao provedor. O operador deve informar sua política de privacidade e retenção e escolher um serviço apropriado aos dados que trata.

### Memória e conhecimento são separados

- Histórico da conversa atual persiste no banco e é recuperado por proprietário.
- Memória entre conversas vem **desligada**. O usuário autoriza em Minha conta e pode revogar.
- Com autorização, recupera até 5 relatórios entre os 50 recentes e até 20 mensagens anteriores de outras conversas da mesma conta. A busca é lexical/recência, não memória ilimitada ou treinamento automático.
- O contexto do modelo limita-se a 20 mensagens da conversa atual, 5 relatórios e 40 indicadores por relatório. Relatórios completos continuam acessíveis.
- A base inicial contém três resumos curtos e referenciados: CISA (ransomware), MITRE ATT&CK T1055 e Microsoft PE. É um ponto de partida, não catálogo exaustivo de malware.
- Recuperação lexical de até três fontes revisadas funciona sem embeddings. Não foi instalado pgvector; para esta base pequena ele não é necessário. Uma expansão futura pode substituir o recuperador mantendo autorização e proveniência.
- Mensagens de usuários nunca atualizam automaticamente a base. O operador importa documentos revisados com `python manage.py import-knowledge arquivo.json --reviewed`, no formato de `data/knowledge.json`.

O prompt separa dados não confiáveis de instruções e exige evidências e limites. Isso reduz riscos, mas não garante imunidade a prompt injection/alucinações. Confirme informações importantes nas fontes e nos relatórios.

## Banco e migrações

`DATABASE_URL=postgresql+psycopg://...` habilita PostgreSQL. Em produção (`APP_ENV=production`) o aplicativo exige PostgreSQL, cookie seguro e segredo forte. Desenvolvimento usa SQLite em `instance/goodware.db` ou `DATABASE`.

SQLAlchemy gerencia as conexões e parâmetros; `database.py` mantém a migrações aditivas v2/v3 em `schema_versions`. A inicialização cria tabelas, adiciona colunas novas e preserva o SQLite da versão anterior. PostgreSQL usa um lock de migração. Não existe downgrade destrutivo automático.

Persistem: contas/perfis, sessões revogáveis, tokens temporários em hash, conversas, mensagens, relatórios/metadados/evidências em JSON, feedback, auditoria e documentos técnicos. As amostras enviadas ficam apenas em memória durante a inspeção; não são armazenadas ou servidas para download. Relatórios ficam no banco privado e exigem autorização.

Para migrar um SQLite existente para PostgreSQL **vazio de usuários**, faça backup da origem, configure o destino e execute:

```sh
python manage.py import-sqlite /caminho/goodware.db
```

Sessões e tokens da origem não são importados. Teste a migração em staging antes de trocar a aplicação principal. O comando de importação está preparado, mas ainda exige validação contra PostgreSQL em staging; o teste de integração existente verifica o fluxo da aplicação em PostgreSQL, não a importação completa.

## E-mail e recuperação de senha

Defina `SMTP_HOST`, `SMTP_PORT` (587 por padrão), `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD` e `PUBLIC_BASE_URL` (URL pública HTTPS, sem barra final). O cliente usa STARTTLS obrigatório. Se o provedor só aceitar SMTP SSL na porta 465, selecione uma configuração STARTTLS compatível ou adapte o transporte antes de usar.

`EMAIL_VERIFICATION_REQUIRED=1` exige confirmação antes do login. Habilite após configurar SMTP. Com `0`, usuários podem entrar sem confirmação, mas o perfil continua mostrando o e-mail como não verificado. O perfil permite solicitar verificação. Se o envio obrigatório não estiver disponível, o cadastro retorna erro claro.

Tokens duram 30 minutos, são armazenados em hash e consumidos uma vez. Redefinir a senha revoga todas as sessões. Links levam o token no fragmento; o navegador o remove da barra ao abrir a página. Tokens, senhas e chaves não são gravados em auditoria.

## Segurança e limites

Sessões em banco expiram em 24 horas; logout revoga a sessão atual. Senhas usam o hash seguro padrão do Werkzeug. Operações de escrita exigem CSRF; autorização é conferida em relatórios, conversas e conta. A interface usa `textContent`, sem HTML vindo de usuários/LLM. CSP restringe scripts à própria origem. Há limites persistentes por endpoint/conta ou IP e bloqueio de geração simultânea na mesma conversa.

ZIP: 10 MiB por upload/entrada, 30 MiB descompactados, 200 entradas, razão 100:1, sem extração, links, caminhos absolutos/travessia ou arquivos criptografados. ZIP aninhado não é expandido. Até 100 indicadores por arquivo. Formatos ignorados aparecem no relatório.

Textos UTF-8 suportados: Python, JS/TS, HTML, PowerShell, shell, batch, PHP, VBS, TXT e JSON. A inspeção é heurística: não faz análise de fluxo de dados. Imports, padrões, entropia e permissões não confirmam execução, roubo de credenciais ou família de malware. Sem indicadores não significa seguro. URLs não são acessadas.

O modelo `.pkl` foi preservado sem desserialização nesta entrega. Está desativado por padrão (`TRUST_MODEL_PICKLE=0`): pickle pode executar código ao carregar. O `train.py` fornecido usa dados sintéticos, sem validação externa demonstrada; sua saída opcional é pontuação não calibrada, nunca certeza ou família. Não execute o script de treinamento sem intenção de sobrescrever o modelo.

## Administração e dados pessoais

```sh
python manage.py set-admin administrador@exemplo.com
python manage.py set-admin administrador@exemplo.com --revoke
python manage.py prune-expired
```

O painel administrativo não mostra conversas ou relatórios privados. Operadores com acesso direto ao banco têm privilégios de infraestrutura e devem ser controlados/auditados separadamente. Excluir uma conversa preserva relatórios; excluir um relatório não reescreve mensagens anteriores. Excluir a conta remove seus registros do banco ativo. Backups podem reter cópias durante o período de retenção; considere isso no atendimento a solicitações de titulares.

Esses controles apoiam privacidade, mas não representam certificação de conformidade com a LGPD. O operador ainda precisa definir finalidade, base legal, contato de privacidade, contratos dos provedores e retenção.

## Hospedagem

Consulte **DEPLOY.md**. Inclui:

- Docker com usuário sem privilégios e Gunicorn.
- Render Blueprint com aplicação, PostgreSQL privado e `/healthz`.
- Docker Compose para VPS, PostgreSQL persistente, Caddy HTTPS e backups locais diários.
- CI para testes, integração PostgreSQL e build Docker; deploy manual com ambiente protegido.
- Procedimentos de backup, restauração e rollback.

O workspace Render **My Workspace** e o repositório **Guuh113/IA_ANTIVIRUS** foram autorizados pelo usuário. A leitura do Render funcionou e não encontrou recursos; a leitura do GitHub funcionou, mas a tentativa de envio retornou HTTP 403 `Resource not accessible by integration`. A consulta posterior de instalações acessíveis retornou lista vazia. Isso não é falha de login do GoodWare nem prova de problema na conexão Render. Nenhuma publicação foi concluída. Veja a alternativa pelo painel em DEPLOY.md. O `.bat` continua sendo só uma opção local.

## Testes e limites da validação

```sh
python -m pytest -q
node --test tests/*.cjs
```

Veja **TESTES.md** para resultados e verificações que dependem do ambiente externo. Nenhuma amostra de malware foi executada. Respostas controladas de LLM e SMTP existem apenas nos testes, nunca como funcionalidade do produto.

## Retenção e operação

O banco ativo preserva conversas até exclusão do usuário. Relatórios e feedback podem ter retenção definida pelo operador:

```sh
python manage.py prune-data --days 90
python manage.py prune-data --days 90 --apply
```

O primeiro comando apenas conta. O segundo remove relatórios datados, feedback e auditoria anteriores ao prazo; não remove conversas (mensagens ainda não têm data individual). Registros legados de relatório sem data válida são preservados. Agende explicitamente apenas após definir e comunicar a política. Isso não executa nem limpa backups externos.

## Recursos que ainda exigem trabalho ou configuração

A implementação não deve ser apresentada como produto de proteção contínua validado. Faltam: modelo de IA e SMTP reais configurados/testados, PostgreSQL remoto, build Docker e deploy com URL verificada, QA visual desktop/mobile, teste de carga e restauração. O streaming foi testado com fixtures; precisa de teste com o provedor escolhido. O status de IA significa configuração presente, não teste de saúde.

Não implementados: feed externo/reputação, análise dinâmica, agente desktop, scanner do computador em tempo real, classificação de famílias comprovada, sandbox de análise isolada por job, fila/worker, recuperação semântica/embeddings, notificações push e chat simultâneo durante etapas internas do mesmo upload. A inspeção estática é limitada e executada no processo web; não executa o arquivo enviado, mas parsers ainda processam dados não confiáveis. Antes de uso público de maior escala, separe scanners em workers com limites de recursos e rede.

Arquitetura futura do agente desktop: instalação com consentimento, identidade por dispositivo, tokens revogáveis de escopo mínimo, canal TLS de saída, seleção local explícita de arquivos e auditoria. Nenhum comando remoto genérico nem agente foi instalado nesta entrega.
