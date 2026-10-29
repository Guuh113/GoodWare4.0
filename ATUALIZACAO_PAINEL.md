# Atualização do painel

O painel apresenta imediatamente o medidor, com estado neutro antes de obter um relatório. O último relatório real determina a pontuação e a descrição colorida. Não é uma varredura do computador e não representa probabilidade de infecção.

Carregamentos independentes evitam que a falha de uma consulta apague os demais blocos. Animações respeitam a preferência de movimento reduzido. A interface usa português brasileiro.

Minha conta permite listar e revogar sessões e ativar TOTP com aplicativo autenticador. Chaves TOTP são cifradas com chave derivada da SECRET_KEY do servidor; preserve essa chave em migrações. Códigos de recuperação são armazenados como hashes, consumidos sob bloqueio transacional e exibidos apenas na ativação. Ativar ou desativar TOTP encerra as demais sessões. A migração aditiva preserva contas e relatórios.

A Aegis pode pesquisar na internet mediante opção explícita. O recurso usa browser_search do Groq com GPT OSS; transmite apenas a pergunta atual, sem incluir perfil, histórico ou relatórios. O uso está sujeito à disponibilidade e cota do provedor existente. Não foi contratado plano adicional. Fontes são entregues na resposta do provedor.

Pendências externas: SMTP e remetente para e-mails; infraestrutura com memória adequada para ClamAV; registro de domínio próprio. Nenhum desses serviços foi simulado ou contratado nesta atualização.

Validação: testes de sessões independentes, revogação, CSRF, TOTP, rejeição de repetição de código, recuperação de uso único, persistência, medidor, contexto temporal e isolamento da pesquisa. CI inclui PostgreSQL e build Docker.
