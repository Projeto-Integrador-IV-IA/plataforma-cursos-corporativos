Lógica de interface do pipeline (RF05): o quadro das demandas por etapa.

- `PipelineBoardView.tsx` — consulta `GET /api/v1/pipeline` e monta as colunas na
  ordem devolvida pelo serviço, com a rolagem horizontal contida no próprio quadro.
- `PipelineStageColumn.tsx` — uma coluna: título da etapa, total e os cartões;
  etapa sem demanda tem apresentação própria.
- `PipelineBoardLabels.ts` — contagens da coluna. Os nomes de etapa e situação vêm
  de `features/demands/DemandListLabels`, para quadro e listagem dizerem o mesmo.

A ordem das etapas e as transições válidas vivem no `pipeline-service`; esta pasta
não guarda cópia dessas regras. A movimentação entre etapas (arrastar o cartão e
avançar/retroceder com justificativa) depende das operações de transição (RF06,
RF07), ainda não publicadas no contrato.

Componentes genéricos (botão, tabela, modal) ficam em `src/components`.
