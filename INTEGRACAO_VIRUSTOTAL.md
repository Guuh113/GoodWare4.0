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

## Medidor prioridade-v2

Novas análises usam a maior nota entre heurística local e reputação, sem somar
ou contar a mesma sinalização duas vezes. As faixas são uma política de triagem
do GoodWare, não probabilidades nem uma classificação oficial do VirusTotal:

| Motores sinalizando (malicious + suspicious) | Nota |
| --- | --- |
| 0 | 0 |
| 1–2 | 35 |
| 3–9 | 55 |
| 10 ou mais | 70 |
| 10 ou mais e pelo menos 20% dos motores válidos | 85 |
| 20 ou mais e pelo menos 50% dos motores válidos | 95 |

Vale a maior faixa aplicável. A heurística local permanece: 35 pela primeira
categoria, +10 por categoria distinta, teto 85. Reputação indisponível/contagens
inválidas não reduzem a nota local. Ausência de dados não indica segurança.
O relatório mantém contagens, datas, critérios e versão. Relatórios anteriores
preservam o cálculo original; faça nova análise para usar a versão atual.
