# Massa de teste

Exemplos de demanda bruta usados nos testes e na avaliação da qualidade da estruturação (RNF04).

## Regras

- Todo dado de cliente real entra **anonimizado**: nomes de empresa, pessoas, valores e contatos
  substituídos (RNF10).
- Cada caso do conjunto de avaliação vem em par: o texto de entrada e o gabarito anotado por humano.
- O conjunto é versionado com o código — mudança de prompt é reavaliada sobre a mesma massa, senão
  os números não são comparáveis entre si.

## Organização prevista

```
fixtures/
├── emails/            corpo de e-mail colado
├── transcricoes/      transcrição de reunião
├── mensagens/         conversas de WhatsApp
└── gabaritos/         saída esperada de cada caso (JSON)
```

Meta: 20 casos anotados até a 3ª parcial (20/10).
