# Sistemas Distribuidos: Dois Servidores de Temperatura

Este repositório contém dois serviços independentes para instalação em máquinas diferentes:

- `source_service`: servidor de origem que consulta a temperatura atual de uma cidade.
- `delayed_service`: servidor réplica que consulta o servidor de origem a cada 1 minuto e publica o dado com 1 minuto de atraso.

## Estrutura

- `source_service/`
- `delayed_service/`
- `INSTALACAO_EM_DUAS_MAQUINAS.md`
- `ESTUDO_APRESENTACAO.md`

## Endpoint para clients

O endpoint recomendado para qualquer client consumir o dado atrasado é:

```text
GET /payload
```

Exemplo:

```text
http://IP_DA_MAQUINA_2:8001/payload
```
