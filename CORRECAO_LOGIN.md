# Correção de login — GoodWare 4.0.1

A mensagem exata do erro do usuário ainda não foi fornecida. Foram corrigidos problemas identificáveis no código; isso não comprova que todos os possíveis erros de instalação foram resolvidos.

- O login verifica senhas existentes de 1 a 256 caracteres. A exigência de 12 caracteres continua no cadastro e na redefinição, sem bloquear contas antigas com senha menor.
- Espaços externos do e-mail são removidos antes da validação. A senha não é alterada.
- O banco SQLite relativo passa a ser resolvido a partir da pasta do projeto, independentemente da pasta usada para iniciar Python.
- O cookie chama-se goodware_session para reduzir conflito com outros aplicativos Flask locais. É necessário entrar novamente após a atualização.
- Após autenticar, a interface confirma que a sessão foi mantida antes de abrir o painel e informa falhas de cookie.

## Atualizar sem perder sua conta

1. Feche o terminal do GoodWare.
2. Faça uma cópia da pasta atual como backup.
3. Extraia este ZIP e copie o conteúdo de goodware-site1 sobre a pasta atual do projeto, substituindo os arquivos de código.
4. Preserve o arquivo .env e a pasta instance originais. Este ZIP não contém seus usuários ou senhas. Não apague o banco para tentar corrigir o login.
5. Inicie INICIAR_GOODWARE.bat e use o endereço que ele abrir.

Se você extraiu cada versão em uma pasta diferente, cada pasta pode ter um banco separado. A conta só estará disponível na instalação que usa o banco onde ela foi criada. Não copie um banco sobre outro sem backup.

Se o erro continuar, envie a mensagem exata da tela (ou print) e o endereço aberto no navegador. Não envie sua senha nem o conteúdo do .env.
