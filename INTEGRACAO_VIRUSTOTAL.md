# VirusTotal v3

Configure VIRUSTOTAL_API_KEY nos segredos do servidor. Nunca publique a chave.

Na tela Analisar arquivos, autorize separadamente a consulta de URLs ou de arquivos.
A integração consulta GET /api/v3/urls/{base64url} ou GET /api/v3/files/{sha256}.
Não faz upload de arquivos nem solicita novas varreduras. Arquivos desconhecidos
continuam com a análise estática local; HTTP 404 não significa segurança.
URLs completas são transmitidas ao VirusTotal; não envie links privados ou tokens.
Para arquivos, somente o SHA-256 é transmitido, não o nome ou conteúdo.

A interface exibe data original quando disponível e contadores. O denominador
conta malicious, suspicious, harmless e undetected; exclui motores sem resultado
(timeout, failure, type-unsupported). O percentual não é probabilidade de infecção.
A evidência externa acrescenta a categoria reputacao_externa ao medidor heurístico,
sem substituir achados locais. Resultados são salvos no histórico privado.

A API gratuita possui limites de 4 consultas/minuto e 500/dia e restrições de uso
comercial. HTTP 429 é mostrado ao usuário sem descartar a análise local. Consultas
em lote podem exceder essa cota. Credenciais recusadas, indisponibilidade e ausência
de resultados são exibidas como estados distintos, nunca como resultados seguros.

Referências: https://docs.virustotal.com/reference/url-info e
https://docs.virustotal.com/reference/file-info
