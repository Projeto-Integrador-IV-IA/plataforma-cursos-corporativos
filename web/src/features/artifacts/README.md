Lógica de interface deste domínio: componentes de tela, hooks de dados e
formulários. Componentes genéricos (botão, tabela, modal) ficam em `src/components`.

Esta pasta continua vazia de propósito: a UI de artefato já existe, mas vive onde é consumida, não
aqui. Histórico e restauração de versões (RF08) ficam em
`pages/artifact-versions/ArtifactVersionsPage.tsx`; revisão e decisão (RF14, RF19.2) ficam em
`features/demands/DemandStructuringReview.tsx`; o resumo no detalhe da demanda fica em
`features/demands/DemandDetailArtifacts.tsx`. `src/services/artifacts.ts` é o único ponto comum.
