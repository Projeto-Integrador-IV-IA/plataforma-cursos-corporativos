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
└── styles/       Estilos globais
```

## Executar

```bash
cp .env.example .env
npm install
npm run dev
```

> Estado: **scaffolding**. Nenhum componente implementado ainda.
