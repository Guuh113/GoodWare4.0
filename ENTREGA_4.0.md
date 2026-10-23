# GoodWare 4.0 — Aegis Intelligence

## Entregue e integrado

A base 3.0 foi preservada e ampliada. Paleta: #0B0B0D / #7B61FF; mesmas páginas e marca. Cadastro separado, sessão revogável, banco SQLAlchemy, relatórios reais e memória autorizada continuam integrados.

| Área | Implementação |
|---|---|
| Mission Control | Nome do usuário, contadores reais, análises recentes, atalhos e pontuação explicável |
| Radar | Filtros nome/hash, data e risco; gráficos de risco, evolução e categorias; timeline |
| Aegis | Markdown seguro, streaming, upload vinculado, histórico, prompts simples/técnicos, feedback |
| Relatórios | PDF, localização/linha/offset existente, recomendações, hash, cobertura e limites |
| Compare | Comparação de hashes e indicadores de dois relatórios autorizados |
| Privacidade | Export JSON, consulta do histórico, exclusão com senha, revogação da memória |
| Knowledge/Coach | Três documentos referenciados e um desafio fixo de phishing, sem fingir IA |
| Infraestrutura | Docker/Render/Compose/CI existentes; fontes PDF incluídas; migração v3 de vínculos |
| Operação | Logs por requisição sem conteúdo privado e comando explícito de retenção |

## Resultado verificado

38 testes Python e 13 JavaScript aprovados; 1 teste PostgreSQL ignorado. PDF renderizado e revisado visualmente. Referências HTML, IDs, sintaxe Python/JS e YAML conferidos. Veja TESTES.md para escopo e limitações.

## O que impede afirmar que está pronto em produção

- IA generativa integrada no código, mas não configurada/testada com modelo real. Exige LLM_BASE_URL, LLM_MODEL e possivelmente LLM_API_KEY.
- SMTP não configurado/testado. Cadastros/logins locais funcionam; envio de e-mail exige provedor.
- PostgreSQL real, Docker, navegador, TLS e restauração de backups ainda não validados neste ambiente.
- GitHub recusou envio (HTTP 403). Render respondeu às consultas, mas nenhum deploy foi realizado. Não há URL pública verificada.
- Serviço gratuito não atende funcionamento continuamente ativo; plano pago precisa de escolha de orçamento.

## Escopo deliberadamente não anunciado

Não há proteção do computador em tempo real, detecção confirmada de famílias, execução de malware, feed de ameaças atual, reputação externa, agente desktop, workers isolados, memória semântica ou notificações push. O progresso mostrado é real por arquivo, sem etapas internas fictícias. Scanners estáticos continuam no processo web e exigem isolamento adicional antes de escala pública.

## Uso

Extraia o ZIP e abra INICIAR_GOODWARE.bat no Windows; consulte README.md para ambiente Python e DEPLOY.md para publicação por GitHub/Render. Nunca abra o HTML diretamente nem execute amostras desconhecidas. Nenhum segredo deve ser enviado ao repositório.
