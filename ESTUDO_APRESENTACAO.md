# Estudo e Apresentacao: Dois Servidores com Polling e Atraso

## Objetivo

Este projeto demonstra dois servidores HTTP:

1. Um servidor de origem busca a temperatura atual de uma cidade em uma API externa.
2. Um servidor réplica consulta o primeiro servidor a cada 1 minuto.
3. O servidor réplica publica o dado com 1 minuto de atraso.

Isso permite explicar polling, replicação, desacoplamento e consistência eventual.

## Servidor 1: origem

Função:

- consulta a API Open-Meteo
- guarda a última leitura em memória
- expõe o dado em `GET /temperature/latest`

## Servidor 2: réplica atrasada

Função:

- faz polling no servidor de origem a cada 60 segundos
- coloca o snapshot recebido em fila
- publica o snapshot somente 60 segundos depois
- expõe o payload para clients em `GET /payload`

## Conceitos para explicar em aula

- Polling: consulta periódica entre sistemas.
- Replicação: cópia de dados entre serviços.
- Consistência eventual: os dois servidores não ficam iguais no mesmo instante.
- Desacoplamento: a réplica depende só do servidor de origem, não da API externa.

## Fluxo de demonstração

1. Mostre o `GET /temperature/latest` no servidor de origem.
2. Mostre o `GET /payload` no servidor réplica.
3. Compare `replica_pulled_at` e `replica_published_at`.
4. Explique que a diferença é o atraso intencional de 60 segundos.

## Logs

Cada servidor grava logs em sua própria pasta `logs/`.

- `source_service/logs/source.log`
- `delayed_service/logs/delayed.log`
