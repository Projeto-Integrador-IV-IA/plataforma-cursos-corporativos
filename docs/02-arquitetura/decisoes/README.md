# Decisões de arquitetura (ADR)

Um **ADR** (*Architecture Decision Record*) registra uma decisão relevante, o contexto em que foi
tomada e o que ela custa. Serve para que, meses depois — ou na banca — a pergunta "por que fizeram
assim?" tenha resposta escrita.

## Quando escrever

Escreva um ADR quando a decisão:

- é difícil de reverter depois (banco, protocolo de comunicação, fronteira de serviço);
- afeta mais de uma frente da equipe;
- foi tomada entre alternativas reais e alguém vai perguntar por quê.

Não escreva ADR para escolha de nome de variável ou de biblioteca trivial.

## Formato

```
ADR-XXXX-titulo-em-kebab-case.md
```

Seções: **Contexto** · **Decisão** · **Alternativas consideradas** · **Consequências** (boas e ruins).

## Status

`Proposta` → `Aceita` → (`Substituída por ADR-YYYY` | `Obsoleta`)

ADR aceito **não é editado** quando muda de ideia: escreve-se um novo, que substitui o anterior.
O histórico da decisão é tão importante quanto a decisão.

## Índice

| ADR | Título | Status | Data |
|---|---|---|---|
| [0001](ADR-0001-arquitetura-microsservicos.md) | Arquitetura em microsserviços | Aceita | 2026-08-19 |
| [0002](ADR-0002-stack-tecnologica.md) | Stack tecnológica | Aceita | 2026-08-19 |
| [0003](ADR-0003-comunicacao-entre-servicos.md) | Comunicação síncrona por HTTP/REST | Aceita | 2026-08-19 |
| [0004](ADR-0004-banco-unico-com-dono.md) | Banco único com dono exclusivo | Aceita | 2026-08-19 |
| [0005](ADR-0005-gateway-como-fronteira-de-autenticacao.md) | Gateway como fronteira de autenticação | Aceita | 2026-08-19 |
| [0006](ADR-0006-saida-da-ia-com-schema-fixo.md) | Saída da IA com schema fixo | Aceita | 2026-08-19 |
