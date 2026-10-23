# Validação da entrega — 14/10/2026

## Executado neste ambiente

- **38 testes Python aprovados; 1 teste PostgreSQL ignorado**, pois não há instância de testes configurada.
- **13 testes JavaScript aprovados** com `node --test tests/*.cjs`.
- Python compilado; sintaxe dos scripts ativos `api.js`, `auth.js`, `product.js` e `intelligence.js` validada pelo Node.
- Links locais de todas as páginas conferidos, sem IDs duplicados ou handlers inline.
- Arquivos YAML de deploy/compose/CI carregados sem erro de sintaxe. Isso não equivale à validação remota do Blueprint pelo Render.
- `gunicorn --check-config 'app:create_app()'` concluiu sem erro com banco SQLite de teste e ambiente de desenvolvimento. Nenhum servidor público foi iniciado.

## Cobertura

Autenticação e cadastro separados; unicidade; confirmação de senha; CSRF; rotas privadas; logout e revogação de sessões; autorização de relatórios/conversas entre contas; perfil; consentimento de memória; recuperação por tokens temporários de uso único; e-mail verificado; exclusão de registros; feedback; acesso administrativo; rate limiting; migração SQLite da versão anterior; saúde do backend; contexto e persistência do chat; bloqueio de geração concorrente; fontes técnicas; contrato HTTP do LLM; uploads inválidos; limites de ZIP; travessia; links simbólicos; evidências por linha/offset; ausência de família inventada; inspeção de URL sem acesso remoto; respostas vazias/HTML/JSON inválido na interface e novas tentativas após falha.

LLM, envio SMTP e características PE específicas usam fixtures controladas nos testes. Os testes não comprovam eficácia real como antivírus, eficácia de classificação ou comportamento de um provedor externo.

## Não executado / depende de infraestrutura

- Render: integração funcional, workspace My Workspace confirmado pelo usuário; consultas não encontraram serviços/bancos. Nenhum serviço/banco criado ou deploy disparado.
- GitHub: repositório Guuh113/IA_ANTIVIRUS confirmado e legível. Escrita foi recusada com HTTP 403 Resource not accessible by integration; nenhuma atualização foi publicada. Consulta de instalações posterior retornou vazia.
- PostgreSQL: teste end-to-end está em `tests/test_postgres.py` e configurado na CI; não executado localmente. Migração SQLite → PostgreSQL requer validação em staging.
- Docker/Compose/Caddy: arquivos preparados; não há Docker disponível para build/execução neste ambiente.
- Browser QA: não executado; o ambiente gerenciado não disponibiliza a capacidade de navegador exigida para esse fluxo. Responsividade e layout precisam ser conferidos no navegador antes da divulgação pública.
- `.bat`: revisado, mas não executado em Windows.
- LLM real e SMTP: faltam credenciais; nenhuma chamada de geração real ou e-mail foi enviado.
- Backup/restauração, TLS, domínio, alertas e teste de carga: precisam ser validados na hospedagem.

## Repetir

Na pasta do projeto:

```sh
python -m pytest -q
node --test tests/*.cjs
```

Use apenas banco descartável em `TEST_POSTGRES_URL` para executar o teste PostgreSQL. O teste cria e exclui uma conta de teste. A CI inclui esse banco temporário e o build Docker, mas o workflow não foi executado no GitHub nesta entrega.

## Verificações adicionais 4.0

Isolamento entre contas para PDF, exportação e comparação; export sem senhas/tokens; limpeza com senha e CSRF; pontuação sem dados e com análises reais; persistência dos vínculos de relatórios; limpeza por retenção em modo simulado e aplicado; streaming completo e interrompido; liberação da conversa após falha; parser SSE; Markdown hostil mantido como texto; eventos NDJSON fragmentados e confirmação de conclusão.

O teste de streaming identificou e levou à correção do encerramento prematuro da conexão SQLAlchemy. O PDF de validação foi renderizado e as duas páginas foram inspecionadas visualmente; fontes incorporadas corrigiram espaçamento irregular. O PDF de teste não contém dados de usuários e não integra o ZIP.

## Correção 4.0.1 de login

32 testes Python de login, autenticação, sessão, plataforma e análise passaram após a correção, incluindo 2 regressões novas. Sintaxe de app.py e js/auth.js conferida. As 51 aprovações acima se referem à validação da versão 4.0; não foi repetida toda a suíte nesta correção. O erro específico do usuário ainda requer a mensagem da tela para confirmação.
