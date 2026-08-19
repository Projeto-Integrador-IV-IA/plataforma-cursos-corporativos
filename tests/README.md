# Testes end-to-end

Testes que atravessam **mais de um microsserviço**. Teste de um serviço isolado mora em
`services/<serviço>/tests`.

## O que validar aqui

O fluxo completo do MVP, que é exatamente a entrega da 4ª parcial (17/11):

1. autenticar (RF16);
2. cadastrar cliente (RF01) e demanda (RF02);
3. registrar demanda bruta em texto livre (RF09);
4. verificar que o bruto foi persistido **antes** da chamada ao LLM (RNF05);
5. obter o curso estruturado e conferir que ele foi anexado à negociação (RF11, RF12, RF13);
6. editar a saída da IA como operador (RF14);
7. avançar e **retroceder** etapas do pipeline (RF05, RF06);
8. conferir que o histórico registrou todas as transições, sem lacuna (RF07, RNF09);
9. recuperar uma versão anterior do artefato (RF08, RF15).

## Cenários de falha obrigatórios

- LLM indisponível ou em timeout: a demanda bruta permanece registrada e recuperável (RNF05).
- Transição inválida de etapa: recusada com erro padronizado, sem alterar o histórico.
- Requisição sem token: recusada em toda rota, exceto login e health (RNF10).

## Como rodar

O LLM é substituído pelo provedor falso (`LLM_PROVIDER=mock`): a suíte não gasta chamada paga
(RNF12) e o resultado é determinístico.

```bash
make up
pytest tests/e2e
```

> Estado: **scaffolding**. Implementar a partir da Fase 3, quando os serviços responderem.
