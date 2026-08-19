# Contratos de eventos

**Reservado.** O MVP usa comunicação **síncrona via HTTP/REST** entre os microsserviços — decisão
registrada em [ADR-0003](../../../docs/02-arquitetura/decisoes/ADR-0003-comunicacao-entre-servicos.md).

Esta pasta existe porque a arquitetura precisa permitir evolução independente dos serviços (RNF13).
Se, na fase pós-MVP, a estruturação por IA passar a rodar de forma assíncrona (fila de trabalho) ou
surgirem integrações externas (RF-F5), os contratos de evento entram aqui — sem alterar a decisão do MVP.

Não crie fila nem broker no MVP: acrescenta operação e custo (RNF12) sem resolver problema que exista hoje.
