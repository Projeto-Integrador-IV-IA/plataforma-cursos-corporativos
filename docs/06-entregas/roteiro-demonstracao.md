# Roteiro de demonstração — MVP ponta a ponta

Script passo a passo para demonstrar o fluxo principal: login → cliente → demanda → captação de
texto bruto → estruturação por IA → revisão com evidência por campo → histórico de etapas e de
versões do artefato. Baseado nas rotas reais de
[`web/src/app/routes.tsx`](../../web/src/app/routes.tsx) e
[`paths.ts`](../../web/src/app/paths.ts) — toda tela e todo texto citados abaixo existem no código
nesta data (17/11/2026). Onde uma ação do roteiro de teste de fluxo
([`tests/fluxos/`](../../tests/fluxos)) ainda não tem botão na interface, isso está marcado
explicitamente — não inventamos tela para cobrir a lacuna.

## Preparação

1. Subir a stack (`make dev` ou `docker compose up`, ver
   [ambiente de desenvolvimento](../05-processo/ambiente-desenvolvimento.md)). `LLM_PROVIDER=mock`
   funciona sem chave de API para o ensaio da demonstração; para a banca, usar um provedor real
   configurado com antecedência, para não depender de latência de rede ao vivo.
2. Ter um usuário operador já cadastrado no `pipeline-service` (login e senha). O MVP hoje emite um
   único perfil (`OPERADOR`, com todas as permissões) — não há um segundo usuário com perfil restrito
   para demonstrar a diferença visual entre perfis; mencionar isso se a banca perguntar sobre RF26.
3. Abrir `http://localhost:5173` (ou a URL de homologação, quando definida — RNF15 segue em aberto).

## 1. Login — `/login`

- Preencher e-mail e senha do operador e confirmar.
- Apontar: campo de senha com alternância de visibilidade; mensagem de erro única por campo quando
  as credenciais são inválidas; depois de logado, qualquer rota digitada diretamente na URL exige a
  sessão (RNF10) — tentar abrir `/pipeline` em aba anônima para mostrar o redirecionamento a
  `/login`.
- Resultado: redirecionamento para `/inicio`.

## 2. Cadastrar cliente — `/clientes/novo`

- A partir do menu, abrir "Clientes" (`/clientes`) e o botão de cadastro.
- Preencher **Razão social** (obrigatório), CNPJ, Segmento, Contato, E-mail, Telefone, Observações
  (opcionais).
- Apontar: só a razão social é obrigatória; CNPJ e e-mail são validados no formato quando
  preenchidos; ao salvar, redireciona para a listagem.
- Abrir o cliente recém-criado (`/clientes/:clientId`) e apontar a tela de detalhe: dados do
  cadastro, edição parcial (só os campos alterados vão no `PATCH`) e a lista de demandas do cliente.

## 3. Abrir demanda — `/demandas/nova`

- A partir de "Demandas" (`/demandas`), abrir o formulário de nova demanda.
- Selecionar o cliente cadastrado no passo 2, preencher Título e Contexto.
- Resultado: redireciona para o detalhe da demanda (`/demandas/:demandId`), etapa inicial
  **Captação**.
- Apontar na tela de detalhe: seções "Etapa e situação", "Histórico de etapas" (vazio por ora, só a
  entrada no pipeline), "Curso com IA", "Fontes captadas" (vazia) e "Artefatos" (vazio) — a tela
  reúne tudo sobre a negociação num lugar só (RF04).

## 4. Captar texto bruto — `/demandas/:demandId/ingestao`

- Na seção "Fontes captadas", clicar em **"Registrar a primeira fonte da demanda"**.
- Em "De onde veio o texto?", escolher uma origem (E-mail, Transcrição de reunião, Mensagens,
  Anotação, Outro) ou deixar "Identificar automaticamente".
- Colar um texto de demanda real (anonimizado) em "Texto recebido do cliente" — mínimo 10
  caracteres, máximo 50.000.
- Clicar em **"Salvar texto e fazer o curso com IA"**.
- Apontar: o texto original é persistido **antes** de qualquer chamada à IA (RNF05) — se a IA cair
  depois deste clique, o texto já está salvo e nada se perde; a geração começa automaticamente ao
  salvar, sem precisar de uma segunda ação.
- Resultado: redireciona para a tela de estruturação, já acompanhando a execução.

## 5. Acompanhar o processamento — `/demandas/:demandId/estruturacao`

- Apontar a seção "Processamento": estado da execução (`PENDENTE` → `PROCESSANDO` → `CONCLUIDA` ou
  `ERRO`), distinguido por texto, forma e borda — não só por cor (acessibilidade) — e atualizado em
  região `aria-live` para leitor de tela.
- O identificador da execução fica na URL (`?execucao=`): recarregar a página mantém o
  acompanhamento.
- Esperar a conclusão (rápida com `LLM_PROVIDER=mock`).

## 6. Revisar a estrutura gerada com evidência por campo

- Ainda em `/demandas/:demandId/estruturacao`:
  - Seção **"Campos a confirmar (N)"**: lista as lacunas que a IA declarou — apontar que cada lacuna
    tem **tipo** (`ausente`, `ambígua`, `contraditória`) e **motivo**, nunca um valor inventado no
    lugar.
  - Seção **"Estrutura gerada"**: tema, público-alvo, carga horária, objetivos de aprendizagem,
    ementa — mostrando a versão e a origem (IA) do artefato.
  - Clicar em um link de evidência de um campo preenchido (ex.: "Abrir trecho 1 na fonte original").
    Resultado: navega para `/demandas/:demandId` com o trecho citado destacado na fonte original
    (seção "Fonte original", `#source-evidence`), com o trecho anterior e o seguinte visíveis como
    contexto.
  - Voltar para a revisão pelo link "Voltar para a revisão".
- Seção **"Fontes de origem"**: as fontes brutas que alimentaram esta versão do artefato.
- Seção **"Decisão da revisão"** (RF19.2, cards #58–#60, #102): preencher a justificativa e clicar em
  **Devolver** — mostra que a justificativa é obrigatória (tentar sem preencher recusa com mensagem
  antes de qualquer chamada à API) e que a decisão aparece registrada acima, com autor e data.
  Aprovar não exige justificativa. Se a estrutura for editada por outra pessoa entre a tela abrir e a
  decisão, o servidor recusa (409) e a tela avisa para recarregar — a decisão nunca vale, em
  silêncio, para uma versão que já não é a vigente.
- **Lacuna honesta a mencionar se perguntado:** editar um campo gerado direto nesta tela (card #101)
  ainda não existe na interface — a única forma de corrigir um campo hoje é por API
  (`POST /api/v1/artifacts/{id}/versions`) ou restaurando uma versão anterior na tela de histórico
  (seção 7). "A IA nunca é a palavra final" hoje é reforçado pelo servidor: aprovar, rejeitar e
  devolver ficam registrados, com autor e justificativa, de forma append-only.

## 7. Ver histórico de versões do artefato — `/artefatos/:artifactId/versoes`

- A partir da revisão, clicar em **"Ver o histórico de versões (N)"**.
- Apontar: lista de versões em ordem decrescente, origem (IA/HUMANO) e autor de cada uma.
- Selecionar uma versão e usar a ação de restaurar: mostra que o conteúdo escolhido entra como
  **versão nova**, sem apagar nem sobrescrever nenhuma versão anterior (append-only, RNF09) — é
  assim que RF08 ("versionar com recuperação") funciona na prática.

## 8. Ver histórico de etapas

- Voltar para `/demandas/:demandId` e apontar a seção **"Histórico de etapas"**: cada transição
  registra origem, destino, autor, data/hora e justificativa (quando houve retrocesso).
- **Lacuna honesta a mencionar se perguntado:** avançar ou retroceder a etapa não tem botão *nesta
  tela* (detalhe da demanda) — só no quadro do pipeline (seção 9). Para mudar a etapa a partir do
  detalhe hoje, é preciso ir ao quadro.

## 9. Ver o quadro do pipeline e mover uma demanda — `/pipeline`

- Apontar as cinco colunas fixas (etapas), sempre presentes mesmo vazias, com o total real de cada
  etapa no cabeçalho (não só o que o recorte trouxe).
- Apontar o cartão da demanda usada na demonstração na coluna correspondente, e, se houver outra
  demanda sem responsável, o destaque "Sem responsável definido" (texto, forma e borda — não só
  cor).
- Arrastar o cartão para a coluna seguinte: avança a etapa (`POST
  /api/v1/demands/{id}/advance`) e atualiza o quadro. Arrastar para uma coluna anterior pede
  justificativa (retrocesso, `.../rollback`) antes de confirmar — card #95/#96, RF06/RF07.
- **Lacuna honesta a mencionar se perguntado:** a movimentação só existe por arrastar-e-soltar; não
  há botão equivalente para quem usa teclado ou não percebe que o cartão é arrastável.
- Apontar a seção de **atualizações recentes** do painel (RF23): lista as demandas com movimentação
  mais recente, com link direto para o histórico completo de cada uma.

## Encerramento

- Resumir o que foi mostrado contra o que o requisito pede: captação com preservação do original
  (RNF05), estruturação com schema fixo e evidência por trecho (RNF03, RF27/RF28 consolidados),
  revisão com lacuna classificada, versionamento append-only (RF08, RNF09) e rastreabilidade de
  etapa (RF07).
- Ser direto sobre o que ainda não está na interface, citado nos passos 6 e 8 — consta como gap
  conhecido no [relatório técnico](relatorio-tecnico.md) e na
  [matriz de rastreabilidade](../01-requisitos/matriz-rastreabilidade.md), não é surpresa para quem
  pergunta.
