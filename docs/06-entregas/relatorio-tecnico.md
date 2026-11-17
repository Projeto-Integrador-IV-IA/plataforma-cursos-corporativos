# Relatório técnico — 4ª parcial (Marco M4)

Síntese técnica do estado da plataforma na entrega de 17/11. Cobre integração, testes e
tratamento de exceção, desempenho, verificação de requisitos e segurança, conforme pedido em
[`04-quarta-parcial.md`](04-quarta-parcial.md). Este documento **não repete** o que já está
detalhado em outro lugar — aponta para a fonte e resume a conclusão. Decisões de arquitetura
estão nos ADRs ([`docs/02-arquitetura/decisoes/`](../02-arquitetura/decisoes/)); evidência
requisito a requisito está na [matriz de rastreabilidade](../01-requisitos/matriz-rastreabilidade.md),
que é a referência de verdade — os números abaixo foram conferidos contra o código nesta auditoria
(17/11/2026).

## 1. Arquitetura

Quatro serviços de backend (`gateway-service`, `pipeline-service`, `ingestion-service`,
`ai-structuring-service`) e um frontend (`web`), com fronteira traçada pelo motivo de mudança de
cada um ([ADR-0001](../02-arquitetura/decisoes/ADR-0001-arquitetura-microsservicos.md)). Banco
único (PostgreSQL + pgvector), com dono exclusivo — só o `pipeline-service` conecta nele
([ADR-0004](../02-arquitetura/decisoes/ADR-0004-banco-unico-com-dono.md)). REST síncrono entre
serviços, sem fila ([ADR-0003](../02-arquitetura/decisoes/ADR-0003-comunicacao-entre-servicos.md)).
Gateway como única fronteira de autenticação, rede interna não exposta
([ADR-0005](../02-arquitetura/decisoes/ADR-0005-gateway-como-fronteira-de-autenticacao.md)). Saída
da IA com schema fixo e validado ([ADR-0006](../02-arquitetura/decisoes/ADR-0006-saida-da-ia-com-schema-fixo.md)).
Evidência por trecho citável e `pgvector` para recuperação por similaridade
([ADR-0007](../02-arquitetura/decisoes/ADR-0007-estrategia-evidencia-e-recuperacao-vetorial.md)).

Correlação de log entre serviços (`X-Request-ID`) está implementada nos quatro backends: o header é
lido no handler de erro e no logger estruturado de cada serviço (`app/core/exceptions.py`,
`app/core/logging.py` em cada um), propagado pelo chamador.

## 2. Fluxo ponta a ponta

```
web → gateway (autenticação, proxy) → pipeline-service (cliente, demanda, etapa, artefato)
                                     → ingestion-service (captação, normalização)
                                     → ai-structuring-service (extração, schema, evidência)
```

Rotas reais (ver [`web/src/app/routes.tsx`](../../web/src/app/routes.tsx)): `/login` →
`/clientes/novo` → `/demandas/nova` → `/demandas/:demandId/ingestao` →
`/demandas/:demandId/estruturacao` → `/demandas/:demandId` (histórico e artefatos) →
`/artefatos/:artifactId/versoes` → `/pipeline`. Passo a passo com o que apontar em cada tela está no
[roteiro de demonstração](roteiro-demonstracao.md).

**Fechamento da fatia vertical (RF13).** Até esta auditoria, a documentação registrava que
`ai-structuring-service` não tinha cliente para anexar o resultado ao `pipeline-service` — isso já
não procede. `JobService._persistir_resultado`
([`job_service.py`](../../services/ai-structuring-service/app/services/job_service.py)) chama
`PipelineServiceClient.persist_artifact`
([`pipeline_client.py`](../../services/ai-structuring-service/app/clients/pipeline_client.py))
contra `POST /api/v1/demands/{demand_id}/artifacts` ao final de toda execução bem-sucedida;
`pipeline_service_url` é hoje campo obrigatório de `Settings`. O fluxo completo
**ingestão → estruturação → artefato persistido na demanda** está de fato ligado em código.

**O que falta para a revisão fechar o ciclo (RF19.2).** A edição salva cria versão `HUMANO`
(`POST /api/v1/artifacts/{id}/versions`, RF19.1 — entregue), mas não existe ação de aprovar,
rejeitar ou devolver, nem estado de revisão na demanda: os cards #58, #59, #60 e #102 continuam
abertos. "A IA nunca é a palavra final" hoje se apoia só na prática operacional (ninguém usa a saída
sem olhar a tela de revisão), não em uma barreira de servidor que recuse avanço sem revisão
registrada.

## 3. Testes e tratamento de exceção

Cobertura de linha medida nesta auditoria (`pytest --cov`, suíte completa de cada serviço):

| Serviço | Cobertura | Observação |
|---|---|---|
| `ai-structuring-service` | 94% | Piso de CI em 85% (`fail_under`, card #222). Módulos de domínio e de serviço (`domain/course.py`, `services/structuring_service.py`) em 100%. `providers/fastembed_provider.py` (recém-chegado, RF29) em 46% — assim como `providers/http_llm_provider.py` (90%), o caminho que fala com um provedor real fora do `mock` é o menos exercitado pela suíte. |
| `pipeline-service` | 97% | 297 testes, todos passando. |
| `ingestion-service` | 94% | — |
| `gateway-service` | 90% | `app/proxy/forwarder.py` em 25% — o encaminhamento de rotas de negócio é a parte menos exercitada da suíte, e é exatamente onde falta aplicar autorização por perfil (seção 5). |

Só `ai-structuring-service` tem piso de cobertura reprovando o CI (`pyproject.toml`); os outros três
medem mas não impõem piso.

**Tratamento de exceção verificado em código:**
- Falha/timeout do LLM não perde a demanda bruta: o texto é persistido pelo `ingestion-service`
  antes de qualquer chamada à IA (RNF05); retentativa com `tenacity` e teto configurável,
  resposta fora do schema também retentada com teto próprio
  (`services/ai-structuring-service/app/services/structuring_service.py`).
- Transição de etapa inválida é recusada pela máquina de estados
  (`app/domain/rules.py`, `pipeline-service`) sem alterar o histórico — append-only garantido por
  `stage_transitions` e `artifact_versions`.
- Rota protegida sem token recusa com `401` (`gateway-service`, `test_auth.py`).
- Entrada inválida tem mensagem por campo (`details.issues`) em todos os formulários cobertos por
  teste (`test_clients.py`, `test_demands.py`, `ClientForm.test.tsx`, `DemandForm.test.tsx`).

**Lacuna real:** nenhum teste do `ai-structuring-service` exercita a persistência do artefato
descrita na seção 2 — `pipeline_service_url` só aparece como valor de fixture em
`tests/conftest.py`, e `test_structuring_jobs.py` não verifica chamada, payload nem o desfecho de
falha (`ARTIFACT_PERSISTENCE_FAILED`). `tests/e2e/` no repositório raiz contém só um `.gitkeep` —
**não há teste automatizado, de nenhum nível, provando o fluxo completo entre serviços.** A suíte de
cada serviço prova o serviço isoladamente; a integração real entre eles depende hoje de teste manual
(ver [tests/fluxos](../../tests/fluxos), que documenta o roteiro de teste manual, não testes
automatizados).

## 4. Desempenho

- **RNF06** (estruturação ≤ 15 s): execução assíncrona com estado consultável (RF17); o endpoint
  devolve `total_elapsed_ms` do aceite ao desfecho. Medido contra o provedor mock na CI — não mede o
  modelo real. Latência real por modelo foi medida à parte, contra o OpenRouter, três candidatos da
  família DeepSeek (ver [relatório comparativo](../04-ia/avaliacoes/relatorio-comparativo-modelos.md));
  a verificação do alvo de 15 s em condição de produção ainda não ocorreu.
- **RNF07** (CRUD ≤ 500 ms): sem medição registrada. Alvo é estimativa desde a definição do
  requisito — [Q2 em questões em aberto](../01-requisitos/questoes-em-aberto.md#q2--metas-de-desempenho)
  segue aberta.
- **Custo de LLM**: medido, não estimado, para os três candidatos avaliados — projeção mensal (2–3
  demandas/dia) abaixo de US$ 0,55 para qualquer um dos três
  ([custos de operação](../04-ia/custos-operacao.md)).

**Desvio em relação à meta, justificado:** os dois alvos de latência (RNF06, RNF07) foram fixados
antes de qualquer medição e seguem sem verificação contra ambiente real — dívida registrada, não
escondida, nas questões em aberto Q2.

## 5. Verificação dos requisitos

Resumo; detalhe requisito a requisito está na matriz. Essenciais do MVP com gap real conhecido:

- **RF19.2** (aprovar/rejeitar/devolver na revisão) — não iniciado, cards #58/#59/#60/#102 abertos.
- **RF21/RF15** (repositório único de artefatos) — parcialmente coberto por `GET /api/v1/demands/{id}`
  (devolve insumos, artefatos e versões numa única consulta), mas os cards dedicados (#38 endpoint,
  #108 tela consolidada) continuam abertos.
- **RNF18 do Documento Consolidado** (autorização por perfil, menor privilégio) — primitivas de
  permissão existem e são testadas no `gateway-service` (`role_has_permission`,
  `test_unknown_role_uses_least_privilege`) e a interface já restringe por perfil (RF26), mas
  **as rotas de negócio do proxy do gateway não aplicam a verificação de permissão** — só exigem
  sessão autenticada. Ver seção 6.

Essenciais e Altos **sem** gap conhecido nesta auditoria: RF01–RF03 (CRUD/listagem, exceto
inativação de cliente), RF04 (detalhe com histórico e artefatos), RF05–RF09 (pipeline, captação),
RF11–RF14 (extração, ementa a partir do texto do cliente, anexação, revisão/edição com nova
versão), RF16–RF17 (autenticação, estado de processamento), RF23, RF26.

Fora do MVP corrente, por decisão ou por dependência não satisfeita: transcrição de áudio real
(STT) — captação, validação e armazenamento do binário estão prontos, mas a conversão em texto
depende da integração ElevenLabs (card #165, aberto); diarização de fala do cliente (RF31
consolidado, card #168, aberto).

Geração e consumo de embeddings para recuperação por similaridade (RF29 consolidado, cards
#160–#162) **chegaram a `dev` durante a redação deste relatório** (17/11): `POST
/api/v1/demands/{demand_id}/embeddings` gera os vetores dos trechos de uma demanda, e
`structuring_service.py` já sabe usar os mais similares no lugar do texto completo quando
`RETRIEVAL_ENABLED=true`. A flag é `false` por padrão — o caminho existe e está testado, mas não
está ligado nem acionado automaticamente após a captação.

## 6. Segurança

- Segredos fora do código: `Settings` por ambiente + `SecretStr`, sem fallback hard-coded; varredura
  de segredos na CI (`job seguranca`, [`ci.yml`](../../.github/workflows/ci.yml)).
- Senhas só como hash bcrypt (`auth/password.py`, `gateway-service`); nunca persistidas em texto.
- Rede interna não exposta: só o gateway publica porta no `docker-compose.yml`.
- Autenticação por JWT obrigatória em toda rota exceto `/login` e health (RNF10).
- **Gap de autorização (não de autenticação):** `routes/proxy.py` do `gateway-service` exige
  `CurrentUser`, mas não chama `require_permission`/`require_any_permission` ao encaminhar para os
  serviços de domínio, e `forwarder.py` não repassa o perfil do usuário na chamada a jusante.
  Cobertura de `forwarder.py` medida em 25% nesta auditoria é consistente com esse caminho pouco
  exercitado. Hoje, qualquer operador autenticado pode chamar a API de negócio diretamente, mesmo
  sem a tela correspondente liberada para o seu perfil — a restrição por perfil (RF26) é só de
  interface.
- Fronteira do Bloco B verificada no CI (`job fronteira-bloco-b`): nenhuma ocorrência de
  custeio/orçamento/instrutor fora das exceções documentadas.

## 7. Limitações conhecidas (resumo)

1. Sem teste automatizado de ponta a ponta entre serviços (`tests/e2e/` vazio).
2. Persistência do artefato gerado pela IA no pipeline (RF13) não tem teste dedicado.
3. Autorização por perfil aplicada só na interface, não no gateway.
4. Fluxo de revisão sem estado formal de aprovação/rejeição (RF19.2).
5. Repositório único de artefatos (RF21/RF15) coberto de forma indireta, sem endpoint/tela
   dedicados.
6. Transcrição de áudio (STT) ainda não existe — só captação e validação do arquivo.
7. Metas de latência (RNF06, RNF07) não verificadas contra ambiente de produção/homologação.
8. Ambiente de homologação acessível (RNF15) ainda não definido — Q5 em aberto.
9. Registro de execuções de IA e de consumo de tokens em memória, por processo — não sobrevive a
   reinício nem é compartilhado entre réplicas (RF17, RNF12).
