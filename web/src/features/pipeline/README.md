Lógica de interface do pipeline (RF05): o quadro das demandas por etapa.

- `PipelineBoardView.tsx` — consulta `GET /api/v1/pipeline` e monta as colunas na
  ordem devolvida pelo serviço, com a rolagem horizontal contida no próprio quadro.
- `PipelineRecentUpdates.tsx` — reúne as trilhas das demandas carregadas pelo
  quadro, mostra as cinco movimentações mais recentes e leva cada item ao detalhe.
- `PipelineStageColumn.tsx` — uma coluna: título da etapa, total e os cartões;
  etapa sem demanda tem apresentação própria.
- `PipelineCard.tsx` — o cartão: cliente, título, responsável e situação, clicável
  por inteiro até o detalhe da demanda. Demanda sem responsável é sinalizada por
  texto, borda e cor, nunca só por cor.
- `PipelineBoardLabels.ts` — contagens da coluna. Os nomes de etapa e situação vêm
  de `features/demands/DemandListLabels`, para quadro e listagem dizerem o mesmo.

A ordem das etapas e as transições válidas vivem no `pipeline-service`; esta pasta
não guarda cópia dessas regras. A atualização recente usa a trilha completa de
cada demanda devolvida pelo quadro; o detalhe da demanda oferece acesso a todo o
histórico, sem o limite de cinco itens do painel.

Componentes genéricos (botão, tabela, modal) ficam em `src/components`.
