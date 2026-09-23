# web

Interface do operador: onde clientes, demandas e o pipeline são consultados e onde a saída da IA é
revisada antes de qualquer uso externo (RF14).

- **Porta:** `5173`
- **Requisitos atendidos:** RF03, RF04, RF05, RF06, RF14, RF17, RNF10

## Telas previstas

| Tela | Requisitos |
|---|---|
| Login | RF16 |
| Lista de clientes / cadastro | RF01, RF03 |
| Lista de demandas com filtro por status, cliente e período | RF02, RF03 |
| Detalhe da negociação: pipeline, histórico e artefatos | RF04, RF05, RF06, RF07, RF15 |
| Ingestão de demanda bruta (texto livre) | RF09 |
| Revisão e edição do curso estruturado pela IA | RF12, RF14 |
| Histórico de versões de artefato | RF08 |

O estado de processamento da estruturação (RF17) é feedback global: enquanto a IA trabalha, a
interface mostra progresso e não bloqueia a navegação.

## Estrutura

```
src/
├── app/          Configuração da aplicação: rotas, providers, layout
├── pages/        Uma pasta por tela
├── features/     Lógica por domínio (clientes, demandas, pipeline, artefatos, ingestão)
├── components/   Componentes reutilizáveis de interface
├── services/     Acesso HTTP ao gateway
├── hooks/        Hooks compartilhados
├── types/        Tipos derivados dos contratos de API
├── lib/          Utilitários
├── test/         Setup e helpers da suíte de testes
└── styles/       Estilos globais
```

## Rotas

Declaradas em [`src/app/routes.tsx`](src/app/routes.tsx); os caminhos vivem em
[`src/app/paths.ts`](src/app/paths.ts) e nenhum componente escreve URL literal.

| Caminho | Tela | Requisitos |
|---|---|---|
| `/login` | Entrar | RF16 |
| `/clientes` | Clientes | RF01, RF03 |
| `/clientes/:clientId` | Detalhe do cliente | RF01 |
| `/demandas` | Demandas | RF02, RF03 |
| `/demandas/:demandId` | Detalhe da demanda | RF04–RF07, RF15 |
| `/demandas/:demandId/ingestao` | Ingestão da demanda | RF09, RNF05 |
| `/demandas/:demandId/estruturacao` | Estruturação por IA | RF12, RF14 |
| `/artefatos/:artifactId/versoes` | Versões do artefato | RF08 |

`/` redireciona para `/clientes`; qualquer outro caminho cai na tela de rota inexistente.

`/login` é rota irmã do layout: todas as demais são filhas de `App` e recebem a navegação
lateral. Essa separação é o lugar do guarda de sessão (RNF10) quando RF16 existir — hoje
não há token para verificar e as rotas ficam abertas.

## Acesso ao gateway

Toda chamada de rede passa por [`src/services/api.ts`](src/services/api.ts) — nenhum componente usa
`fetch` diretamente. Ele lê a URL base de `VITE_API_BASE_URL` (RNF11), anexa o token da sessão
(RF16), aplica o timeout da operação (RNF06, RNF07) e traduz qualquer falha em um único tipo,
`ApiError`: erro da API no envelope `{ "error": { code, message, details, request_id } }`, falha de
rede, timeout ou resposta ilegível chegam à tela da mesma forma.

Os tipos de entrada e saída vivem em [`src/types/api.ts`](src/types/api.ts) e derivam dos contratos
em `packages/contracts` (RNF02) — divergência falha na compilação, não em produção. Os domínios cujo
contrato ainda é esqueleto estão marcados como **PREVISTO** no arquivo e seguem o dicionário de
dados até o contrato ser publicado.

| Módulo | Domínio |
|---|---|
| [`services/clients.ts`](src/services/clients.ts) | Clientes (RF01, RF03) |
| [`services/demands.ts`](src/services/demands.ts) | Demandas (RF02, RF03, RF04) |
| [`services/ingestion.ts`](src/services/ingestion.ts) | Demanda bruta e normalização (RF09, RF10) |
| [`services/pipeline.ts`](src/services/pipeline.ts) | Etapas e histórico (RF05, RF06, RF07) |
| [`services/artifacts.ts`](src/services/artifacts.ts) | Artefatos e versões (RF08, RF15) |

## Executar

```bash
cp .env.example .env
npm install
npm run dev     # http://localhost:5173
npm run build   # tsc -b && vite build
npm run test    # vitest
npm run lint    # eslint
```

> Estado: **estrutura base pronta** (RNF01) — rotas, layout e providers navegáveis.
> As telas são molduras: nenhum dado é consumido do gateway ainda.
