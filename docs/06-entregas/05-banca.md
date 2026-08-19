# Banca — 24/11

## Roteiro sugerido

| Bloco | Conteúdo | Tempo |
|---|---|---|
| 1 | **Problema** — processo fragmentado, centralizado em uma pessoa, 2–3 propostas manuais por dia | 2 min |
| 2 | **Solução** — os dois pilares: consolidação (valor) e IA (diferencial) | 2 min |
| 3 | **Arquitetura** — microsserviços, decisões e justificativas | 3 min |
| 4 | **Demonstração ao vivo** — o fluxo end-to-end | 6 min |
| 5 | **Resultados de IA** — métricas de qualidade medidas, não opinadas | 3 min |
| 6 | **Custos e viabilidade** — custo por demanda medido contra tempo do operador liberado | 2 min |
| 7 | **Limitações e evoluções** — o que ficou fora e por quê | 2 min |

## Roteiro da demonstração

1. Login na plataforma
2. Cadastro de um cliente
3. Criação de uma demanda
4. **Colar um e-mail real de demanda** (anonimizado) — o momento que mostra o problema resolvido
5. Estruturação por IA, com o estado de processamento visível
6. Curso estruturado anexado à negociação
7. Revisão e edição pelo operador — mostrar que o humano decide
8. Avanço no pipeline
9. **Retrocesso de etapa** — o cliente mudou de ideia, cenário real do negócio
10. Histórico completo, sem lacuna
11. Recuperação de uma versão anterior do artefato

> Ensaie com dado real anonimizado. Demonstração com cliente fictício e texto inventado não convence
> — a força do projeto é ter cliente real.

## Preparação

- [ ] Ambiente de demonstração no ar e testado no mesmo dia
- [ ] **Plano B**: vídeo gravado da demonstração, caso a rede falhe
- [ ] Dados de demonstração carregados e anonimizados
- [ ] Slides prontos, sem excesso de texto
- [ ] Tempo cronometrado em ensaio
- [ ] Papéis definidos: quem fala cada bloco, quem opera a demonstração

## Perguntas prováveis — prepare as respostas

| Pergunta | Onde está a resposta |
|---|---|
| Por que microsserviços para um sistema com um usuário? | [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) — exigência de RNF01 e trabalho paralelo de 6 pessoas |
| Como sabem que a IA acerta? | [Métricas de qualidade](../04-ia/metricas-qualidade.md) — números medidos sobre conjunto anotado |
| E se a IA errar? | RF14: revisão humana obrigatória antes de qualquer uso externo |
| E se a API do LLM cair? | RNF05: a demanda bruta é persistida antes da chamada; nada se perde |
| Por que não fizeram o custeio? | Não existe base de custo modelável — decisão consciente, registrada em [questões em aberto](../01-requisitos/questoes-em-aberto.md) |
| Quanto custa operar? | [Custos de operação](../04-ia/custos-operacao.md), com valor medido |
| Isso escala? | [ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md) e RNF-F3; serviços desacoplados permitem evoluir sem reescrever o núcleo |
| Qual a contribuição científica? | [Possíveis artigos](../00-produto/escopo-mvp.md#possíveis-artigos-científicos) |

## Postura

Conheça as **limitações** do projeto tão bem quanto as qualidades. Banca valoriza consciência de
risco mais do que promessa. O que ficou fora do MVP ficou por decisão registrada e justificada — e
isso é um resultado do projeto, não uma falha dele.
