# Atualização em revisão — contas, medidor e Aegis

O proprietário autorizou a publicação desta revisão após a validação dos testes. O Render acompanha main e publica automaticamente após o merge.

## Contas em qualquer computador

O serviço publicado já usa PostgreSQL no Supabase. O login consulta o e-mail normalizado e verifica o hash da senha com Werkzeug; nenhuma senha é guardada em texto puro. Cada navegador recebe sua própria sessão revogável. Use o mesmo endereço oficial e o mesmo cadastro em cada computador. Cadastros de instalações locais antigas não são automaticamente copiados para a nuvem.

Nesta revisão, a tela de login explica esse comportamento e há teste de login em dois clientes com reinicialização do aplicativo, persistência de relatório e logout independente. O teste PostgreSQL da CI também cobre dois clientes.

## Medidor heurístico v1

O servidor calcula e persiste `medidor` junto ao relatório. Não recebe pontuação escolhida pelo cliente. Categorias distintas: 35 pontos pela primeira, +10 por categoria adicional, teto 85. Repetições da mesma categoria não contam. URLs usam cada tipo de alerta sintático como categoria. Faixas: 0–29 baixo, 30–69 atenção, 70–100 alto.

O índice mede prioridade de revisão, não probabilidade de malware. Não é validado como escala clínica/estatística e pode produzir falsos positivos ou negativos. A pontuação do modelo sintético permanece separada. Sem indicadores não significa seguro. Relatórios antigos mantêm sua categoria e mostram “Sem pontuação”; uma nova análise gera o índice com versão e critérios.

A interface usa verde/amarelo/vermelho, marcador não editável, texto e semântica acessível de medidor. Abra PREVIA.html para alternar exemplos de baixo, atenção, alto e legado. Esta prévia usa o mesmo CSS e componente JS, com exemplos identificados e sem chamadas externas.

## Aegis e hora atual

Assistente geral com especialidade em segurança. O servidor adiciona data e hora verificadas a cada geração; o navegador informa apenas o nome do fuso IANA, validado no servidor. Fuso inválido/ausente usa America/Sao_Paulo. Perguntas diretas sobre hora e data são respondidas pelo relógio sem depender do modelo. Funciona no protocolo JSON e NDJSON. O contexto inclui fuso e offset UTC, inclusive em mudança de data.

Não há ferramenta de pesquisa web: notícias, clima e outros fatos ao vivo não são garantidos. O assistente é instruído a explicar essa limitação e não inventar fontes. Nenhuma chave de API está incluída no código ou na prévia.

## Validação

46 testes Python passaram; 1 teste PostgreSQL aguarda execução na CI com banco descartável. 17 testes JavaScript passaram. A fixture antiga de streaming foi alinhada ao contrato em uso: resposta completa do provedor encapsulada em eventos NDJSON, sem salvar falhas como respostas concluídas. A revisão não muda esse contrato.

A publicação deve ser verificada no Render após o merge. SMTP e recuperação por e-mail ainda exigem configuração própria.

## Complemento: descrição por nível e assistente geral

Cada relatório agora inclui um bloco de descrição na cor do nível, com impactos possíveis das categorias encontradas e próximos passos. A lista agrupa repetições e preserva evidências como texto, sem interpretar HTML. Padrões de URL também recebem explicação específica. Verde não equivale a garantia de segurança.

A página e a saudação da Aegis passam a apresentar ajuda geral: estudos, programação, textos, ideias e cotidiano. O prompt responde diretamente ao assunto solicitado, sem inserir alertas de malware em perguntas não relacionadas. Continua sem pesquisa web ao vivo e sem promessa de respostas infalíveis.

Domínio: goodware.com já aponta para um site existente. O proprietário informou não possuir esse domínio. Nenhuma compra ou mudança de DNS foi feita; o endereço onrender.com continua válido. Um domínio próprio depende de registro disponível e aprovação do custo.
