# Visão geral da arquitetura

Atende **RNF01** (microsserviços independentes comunicando-se por API) e **RNF13** (serviços
desacoplados, evolução independente sem reescrita do núcleo).

## Contexto

```mermaid
flowchart LR
    Op([Operador]) --> Plat[Plataforma]
    Plat --> LLM[("API de linguagem<br/>externa")]
    Plat --> DB[("PostgreSQL")]
```

O sistema tem **um tipo de usuário** — o operador que conduz relacionamento, produto e proposta — e
**uma dependência externa**: a API de linguagem, única despesa recorrente do projeto (RNF12).

## Serviços

```mermaid
flowchart TB
    W["web<br/><small>React + TypeScript · :5173</small>"]

    subgraph Backend
        G["gateway-service<br/><small>:8000</small><br/>autenticação, roteamento"]
        I["ingestion-service<br/><small>:8002</small><br/>captura, normalização"]
        A["ai-structuring-service<br/><small>:8003</small><br/>estruturação por LLM"]
        P["pipeline-service<br/><small>:8001</small><br/>CRM, etapas, artefatos"]
    end

    DB[("PostgreSQL")]
    LLM[("API de linguagem")]

    W -->|HTTPS| G
    G --> I
    G --> P
    G --> A
    I --> P
    I --> A
    A --> P
    P --> DB
    A -.-> LLM
```

| Serviço | Responsabilidade | Não é responsabilidade dele |
|---|---|---|
| **gateway-service** | Porta de entrada única. Autentica, roteia e propaga a identidade do usuário. | Regra de negócio. O gateway não decide nada sobre o domínio. |
| **ingestion-service** | Recebe a demanda bruta, **persiste antes de qualquer processamento**, normaliza e orquestra a estruturação. | Interpretar conteúdo — isso é do LLM. |
| **ai-structuring-service** | Monta prompts versionados, chama o LLM, valida a saída contra o schema e mede qualidade. | Persistir. Não tem banco próprio. |
| **pipeline-service** | Dono do domínio e do banco: clientes, demandas, etapas, histórico, artefatos e versões. | Falar com o LLM. |
| **web** | Interface do operador, incluindo a revisão humana da saída da IA. | Regra de negócio duplicada do backend. |

## Princípios

1. **Um serviço, um banco.** Só o `pipeline-service` acessa o PostgreSQL. Os outros pedem por API.
   Isso é o que permite evoluir um serviço sem quebrar os demais (RNF13).
2. **O bruto vem antes.** A demanda bruta é persistida **antes** da chamada ao LLM. Falha ou timeout
   do modelo não pode custar o texto que o operador colou (RNF05).
3. **Histórico é append-only.** Transições de etapa e versões de artefato só aceitam inserção.
   Não há UPDATE nem DELETE nessas tabelas (RNF09).
4. **Contrato antes de código.** Mudança de API começa em `packages/contracts` (RNF02).
5. **A IA propõe, o humano decide.** Nenhuma saída do LLM vai para uso externo sem revisão (RF14).
6. **Sem inventar infraestrutura.** Nada de fila, cache ou service mesh no MVP — custo e operação
   sem problema correspondente (RNF12).

## Fluxo end-to-end da estruturação

```mermaid
sequenceDiagram
    actor Op as Operador
    participant W as web
    participant G as gateway
    participant I as ingestion
    participant P as pipeline
    participant A as ai-structuring
    participant L as LLM

    Op->>W: cola o texto da demanda
    W->>G: POST /api/v1/ingestion/raw-demands
    G->>I: encaminha (com identidade do usuário)

    I->>P: persiste demanda bruta
    Note over I,P: RNF05 - a partir daqui nada se perde
    P-->>I: raw_input_id

    I->>I: normaliza o texto (RF10)
    I->>A: solicita estruturação
    A->>L: prompt versionado + schema
    L-->>A: resposta
    A->>A: valida contra o JSON Schema (RNF03)

    alt saída válida
        A->>P: anexa artefato v1 (RF13)
        A-->>I: curso estruturado
        I-->>W: concluída
        Op->>W: revisa e edita (RF14)
        W->>G: POST nova versão do artefato (RF08)
    else timeout ou saída inválida
        A-->>I: falha recuperável
        I-->>W: FALHA_ESTRUTURACAO
        Note over W: a demanda bruta continua registrada;<br/>o operador pode repetir sem recolar o texto
    end
```

## Decisões de arquitetura

| ADR | Decisão |
|---|---|
| [ADR-0001](decisoes/ADR-0001-arquitetura-microsservicos.md) | Arquitetura em microsserviços e divisão das fronteiras. |
| [ADR-0002](decisoes/ADR-0002-stack-tecnologica.md) | Stack: Python/FastAPI, PostgreSQL, React/TypeScript. |
| [ADR-0003](decisoes/ADR-0003-comunicacao-entre-servicos.md) | Comunicação síncrona por HTTP/REST no MVP. |
| [ADR-0004](decisoes/ADR-0004-banco-unico-com-dono.md) | Banco único, com o `pipeline-service` como dono exclusivo. |
| [ADR-0005](decisoes/ADR-0005-gateway-como-fronteira-de-autenticacao.md) | Autenticação concentrada no gateway. |
| [ADR-0006](decisoes/ADR-0006-saida-da-ia-com-schema-fixo.md) | Saída da IA validada contra JSON Schema versionado. |
| [ADR-0008](decisoes/ADR-0008-fronteira-nucleo-bloco-b.md) | Fronteira entre o núcleo do MVP e o Bloco B, verificada no CI. |

## O que a arquitetura precisa suportar depois

O MVP não implementa custeio, busca de instrutores, geração de slides nem integrações externas.
A arquitetura foi desenhada para que cada um deles entre como **serviço novo**, consumindo o
`pipeline-service` por API — sem reescrever o núcleo (RNF13, RF-F1 a RF-F5).

### Ponto de extensão

Um módulo do Bloco B entra **ao lado** do núcleo, nunca dentro dele. A dependência tem uma só
direção: o módulo chama o `pipeline-service`; o núcleo não chama, não importa e não nomeia o módulo
([ADR-0008](decisoes/ADR-0008-fronteira-nucleo-bloco-b.md)).

```mermaid
flowchart LR
    W["web"] --> G["gateway-service"]
    G --> N["núcleo<br/><small>ingestion · ai-structuring · pipeline</small>"]
    G -.-> M["módulo novo<br/><small>ex.: custeio-service</small>"]
    M -->|"HTTP, contrato do pipeline"| P["pipeline-service"]
```

Para acoplar um módulo novo (por exemplo, `custeio-service`) sem alterar o núcleo:

1. **Serviço próprio** em `services/<modulo>-service`, com contrato em
   `packages/contracts/openapi/<modulo>-service.yaml` (contrato antes de código, RNF02).
2. **Domínio pelo contrato do `pipeline-service`**, com um cliente HTTP — o mesmo padrão que o
   `ingestion-service` já usa em `app/clients/pipeline_client.py`. O módulo não acessa o PostgreSQL
   ([ADR-0004](decisoes/ADR-0004-banco-unico-com-dono.md)).
3. **Resultado como artefato da demanda** (`POST /api/v1/demands/{id}/artifacts`) quando for um
   documento: já nasce versionado, atrelado à demanda e recuperável (RF08, RF15). Um tipo de
   artefato novo é mudança **aditiva** no contrato do pipeline — a [ADR-0001](decisoes/ADR-0001-arquitetura-microsservicos.md)
   já prevê que o pipeline muda quando surge um tipo novo —, não reescrita.
4. **Rota no `gateway-service`**, que segue como único ponto de autenticação
   ([ADR-0005](decisoes/ADR-0005-gateway-como-fronteira-de-autenticacao.md)) e propaga o
   `X-User-ID`.
5. **Entrada no `docker-compose.yml`** e feature própria em `web/src/features/<modulo>/`.
6. **Diretórios do módulo na lista de permitidos** da verificação de fronteira (abaixo), no mesmo
   PR que o cria.

O núcleo não oferece eventos, fila nem ganchos de plugin, de propósito (princípio 6): o módulo é
acionado pelo operador, pela web, via gateway. Persistência própria de módulo, quando o dado não
couber em artefato, é decisão da ADR que escopar o primeiro módulo.

### Verificação da fronteira

O job `fronteira-bloco-b` do [CI](../../.github/workflows/ci.yml) procura `custeio`, `orçamento`,
`instrutor`, `proposta comercial` e `slide` em `services/`, `packages/` e `web/` e reprova o PR se
achar fora da lista [`fronteira-bloco-b-permitidos.txt`](../../.github/fronteira-bloco-b-permitidos.txt).
A fala do cliente "depende do orçamento", usada em exemplos de prompt e em fixtures, é permitida.
A etapa e o tipo de artefato `PROPOSTA` são vocabulário do núcleo (RF05); o que é Bloco B é
*gerar* a proposta (RF-F2). O critério completo para classificar uma ocorrência está na ADR-0008.
