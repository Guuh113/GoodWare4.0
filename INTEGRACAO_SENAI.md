# Reputação de URLs — API SENAI

Integração pelo contrato público de
https://github.com/Murilo-s-santos/TCC-SENAI-API-ciberseguranca
(endpoint `POST /api/v1/scans/url`). O cliente GoodWare é independente; o código
Java e as credenciais do repositório de origem não são incorporados.

## Ativar

1. Obtenha com o responsável o endereço HTTPS da API Java hospedada.
   O link do GitHub é código-fonte, não um serviço HTTP de análise.
2. No servidor do GoodWare, configure `SENAI_API_URL=https://HOST-DA-API`.
   Use a URL base, sem `/api/v1/scans/url`, query ou fragmento. Uma eventual
   subpasta base é permitida. A conexão tem timeout de 8 segundos e não segue redirecionamentos.
3. Se houver um gateway com autenticação Bearer, configure `SENAI_API_TOKEN`
   somente nos segredos do servidor. A versão Java consultada não implementa
   autenticação própria; não envie a chave do VirusTotal como esse token.
4. Reinicie/republique o GoodWare. Em Analisar arquivos → Inspecione uma URL,
   marque a autorização de consulta externa e envie uma URL pública de teste.

A chave do VirusTotal pertence à configuração privada da API Java, não ao
navegador nem ao GitHub. A versão consultada contém um valor literal nesse campo:
o responsável deve revogá-lo/rotacioná-lo se for uma chave real e usar um segredo
de ambiente antes de publicar o serviço. Não reutilize uma chave exposta.

## Comportamento

- Sem a opção marcada, nenhuma URL é transmitida ao provedor.
- Com autorização explícita (`consultar_reputacao: true` booleano), apenas a URL
  é enviada: nenhum arquivo, mensagem, conta ou relatório acompanha a consulta.
- Não envie URLs privadas, assinadas ou com informações pessoais. URLs com
  credenciais, fragmentos ou endereços locais identificáveis são bloqueadas para
  consulta externa; isso não identifica todos os links privados.
- A API Java consulta resultados existentes no VirusTotal, sem solicitar uma
  nova varredura. Não informa a data da análise original. Um HTTP 500 pode também
  representar URL ausente na base, pois a versão atual não distingue esse caso.
- Timeout, HTTP 429/500, resposta inválida e ausência de configuração são
  identificados no relatório. A inspeção sintática continua funcionando.
- O percentual de motores é exibido separadamente do medidor heurístico.
  Sinalização externa adiciona uma categoria de evidência (35 pontos se isolada),
  conforme o critério existente. Zero alertas não garante segurança.
- Os resultados persistem no histórico privado e no contexto dos relatórios
  usados pela Aegis. O PDF inclui o resumo externo e suas limitações.

## Validação

`python -m pytest tests/test_url_reputation.py`

Os testes usam respostas simuladas do contrato, incluindo indisponibilidade,
consentimento, isolamento de contas, validação de contadores e persistência.
Um teste real depende da API Java publicada e da chave válida no servidor dela.
