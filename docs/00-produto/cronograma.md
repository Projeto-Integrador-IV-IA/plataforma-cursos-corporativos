# Cronograma e marcos

```mermaid
gantt
    title Projeto Integrador de Extensao IV - 2026
    dateFormat YYYY-MM-DD
    axisFormat %d/%m

    section Fase 1 - Concepcao
    Escopo, requisitos e plano        :f1, 2026-08-18, 2026-08-25
    M1 - 1a parcial                   :milestone, 2026-08-25, 0d

    section Fase 2 - Modelagem e PoC
    Requisitos detalhados             :f2a, 2026-08-26, 2026-09-05
    Modelagem de dados                :f2b, 2026-08-26, 2026-09-08
    Arquitetura de microsservicos     :f2c, 2026-09-01, 2026-09-10
    PoC da estruturacao por IA        :f2d, 2026-09-05, 2026-09-15
    M2 - 2a parcial                   :milestone, 2026-09-15, 0d
    Pre-banca                         :milestone, 2026-09-22, 0d

    section Fase 3 - Desenvolvimento
    Backend base                      :f3a, 2026-09-16, 2026-10-03
    Cadastros no frontend             :f3b, 2026-09-16, 2026-10-03
    Pipeline e rastreabilidade        :f3c, 2026-09-22, 2026-10-17
    Integracao da IA                  :f3d, 2026-09-16, 2026-10-17
    Metricas e custos                 :f3e, 2026-10-06, 2026-10-17
    M3 - 3a parcial                   :milestone, 2026-10-20, 0d

    section Fase 4 - Integracao final
    Integracao end-to-end             :f4a, 2026-10-21, 2026-11-07
    Testes e correcoes                :f4b, 2026-10-28, 2026-11-14
    Relatorio e apresentacao          :f4c, 2026-11-03, 2026-11-21
    M4 - MVP funcional                :milestone, 2026-11-17, 0d
    Banca                             :milestone, 2026-11-24, 0d
```

## Marcos

| Marco | Data | Critério de conclusão |
|---|---|---|
| **M1** | 25/08 | Problema, público, escopo, requisitos e plano de ação (5W2H) submetidos. |
| **M2** | 15/09 | Requisitos detalhados, modelagem de dados, arquitetura de microsserviços e PoC da estruturação por IA. |
| **Pré-banca** | 22/09 | Validação intermediária com a banca. |
| **M3** | 20/10 | Backend e pipeline funcionais, módulo de estruturação integrado, métricas de qualidade e levantamento de custos. |
| **M4** | 17/11 | Microsserviços integrados e MVP funcional end-to-end. |
| **Banca** | 24/11 | Apresentação final. |

## Método

Scrum com entregas semanais. Controle via GitHub Projects e Insights; fluxo
**Card → Branch → Commits → Pull Request → Review → Merge**.

Checklists por entrega em [06-entregas](../06-entregas).
