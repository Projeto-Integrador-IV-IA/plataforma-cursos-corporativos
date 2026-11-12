# web

Interface do operador: onde clientes, demandas e o pipeline são consultados e onde a saída da IA é
revisada antes de qualquer uso externo (RF14). Atende **RNF25** (Documento Consolidado de Requisitos v1.0).

- **Porta:** `5173`
- **Requisitos atendidos:** RF03, RF04, RF05, RF06, RF07, RF14, RF17, RF23, RF26, RNF10, RNF25

---

## 1. Telas Previstas

| Tela | Requisitos |
|---|---|
| Login | RF26 |
| Lista de clientes / cadastro | RF01, RF03 |
| Lista de demandas com filtro por status, cliente e período | RF02, RF03 |
| Painel do pipeline e atualizações recentes | RF05, RF23 |
| Detalhe da negociação: pipeline, histórico e artefatos | RF04, RF05, RF06, RF07, RF15 |
| Ingestão de demanda bruta (texto livre) | RF09 |
| Revisão e edição do curso estruturado pela IA | RF12, RF14 |
| Histórico de versões de artefato | RF08 |

O estado de processamento da estruturação (RF17) é feedback global: enquanto a IA trabalha, a
interface mostra progresso e não bloqueia a navegação.

---

## 2. Estrutura e Convenção de Pastas

A organização de código do frontend segue uma separação rigorosa por responsabilidade:

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

---

## 3. Rotas

Declaradas em [`src/app/routes.tsx`](src/app/routes.tsx); os caminhos vivem em
[`src/app/paths.ts`](src/app/paths.ts) e nenhum componente escreve URL literal.

| Caminho | Tela | Requisitos |
|---|---|---|
| `/login` | Entrar | RF26 |
| `/clientes` | Clientes | RF01, RF03 |
| `/clientes/:clientId` | Detalhe do cliente | RF01 |
| `/pipeline` | Painel por etapas e atualizações recentes | RF05, RF23 |
| `/demandas` | Demandas | RF02, RF03 |
| `/demandas/:demandId` | Detalhe da demanda | RF04–RF07, RF15 |
| `/demandas/:demandId/ingestao` | Ingestão da demanda | RF09, RNF05 |
| `/demandas/:demandId/estruturacao` | Estruturação por IA | RF12, RF14 |
| `/artefatos/:artifactId/versoes` | Versões do artefato | RF08 |

`/` redireciona para `/clientes`; qualquer outro caminho cai na tela de rota inexistente.

`/login` é rota irmã do layout: todas as demais são filhas de `App`, recebem a navegação
lateral e passam pelo guarda de sessão. Sem sessão, o destino pretendido fica preservado no
estado do roteador e é retomado depois da autenticação.

---

## 4. Acesso ao Gateway e Variáveis de Ambiente

Toda chamada de rede passa por [`src/services/api.ts`](src/services/api.ts) — nenhum componente usa
`fetch` diretamente. O cliente HTTP lê a URL base de `VITE_API_BASE_URL` (RNF11), anexa o token da sessão (RF26), aplica o timeout da operação (RNF06, RNF07) e traduz falhas em `ApiError`.

### Variáveis de Ambiente (.env)

O frontend consome as seguintes variáveis definidas a partir do arquivo `.env.example`:

| Variável | Descrição | Exemplo / Padrão |
|---|---|---|
| `VITE_API_BASE_URL` | URL base do gateway da API (RNF11) | `http://localhost:8000` |

A resposta usa o envelope `{ "error": { code, message, details, request_id } }`; falhas de rede, timeout e resposta inválida chegam à tela como `ApiError`.

Os tipos de entrada e saída vivem em [`src/types/api.ts`](src/types/api.ts) e derivam dos contratos
em `packages/contracts` (RNF02).

| Módulo | Domínio |
|---|---|
| [`services/clients.ts`](src/services/clients.ts) | Clientes (RF01, RF03) |
| [`services/demands.ts`](src/services/demands.ts) | Demandas (RF02, RF03, RF04) |
| [`services/ingestion.ts`](src/services/ingestion.ts) | Demanda bruta e normalização (RF09, RF10) |
| [`services/pipeline.ts`](src/services/pipeline.ts) | Etapas e histórico (RF05, RF06, RF07) |
| [`services/artifacts.ts`](src/services/artifacts.ts) | Artefatos e versões (RF08, RF15) |

---

## 5. Como Executar e Testar

```bash
cp .env.example .env
npm install
npm run dev     # http://localhost:5173 (Inicia o servidor de desenvolvimento)
npm run build   # tsc -b && vite build (Gera o build de produção)
npm run test    # vitest (Executa a suíte de testes unitários e de integração)
npm run lint    # eslint (Verifica a qualidade de código)

Estado: estrutura base pronta (RNF01) — rotas, layout e providers navegáveis.
As telas são molduras: nenhum dado é consumido do gateway ainda.
