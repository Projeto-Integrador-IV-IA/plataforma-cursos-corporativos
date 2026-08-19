# Questões em aberto

Decisões pendentes que afetam implementação. Cada uma tem **prazo** e **responsável** — questão sem
prazo vira surpresa no fim do projeto.

Ao fechar uma questão: registre a decisão aqui, abra um [ADR](../02-arquitetura/decisoes) se ela
mudar a arquitetura, e atualize os documentos afetados.

---

## Q1 — Revisão × versionamento de artefato

**Contexto.** RF14 permite ao operador editar a saída da IA. RF08 exige versionamento com recuperação
das versões anteriores.

**Pergunta.** Editar a saída da IA **gera uma nova versão** do artefato ou **sobrescreve** a atual?

**Por que importa.** Afeta diretamente a modelagem de dados (`artifact_versions`) e a interface de
revisão. Decidir depois de implementar significa migração de dados.

**Opções.**

| Opção | Consequência |
|---|---|
| Nova versão a cada edição salva | Histórico completo, mas muitas versões triviais por ajuste pequeno. |
| Nova versão apenas ao concluir a revisão | Histórico limpo; exige um estado de rascunho na interface. |
| Sobrescrever | Contraria RF08 e RNF09 — descartada. |

**Recomendação da equipe técnica.** Segunda opção: rascunho editável + versão consolidada ao concluir.
Preserva a distinção entre "o que a IA gerou" e "o que o humano aprovou", que é justamente o insumo
das métricas de RNF04.

- **Responsável:** Backend + IA
- **Prazo:** antes do início da Fase 3 (16/09)
- **Status:** ⬜ em aberto

---

## Q2 — Metas de desempenho

**Contexto.** RNF06 fixa ≤ 15 s para a estruturação por IA; RNF07 fixa ≤ 500 ms para o CRUD do CRM.
Os dois números são **estimativas sem medição**.

**Pergunta.** Os alvos se sustentam depois da PoC?

**Por que importa.** Meta irreal vira dívida na banca; meta frouxa não pressiona a implementação.

- **Responsável:** IA (RNF06) + Backend (RNF07)
- **Prazo:** revisão após a PoC da 2ª parcial (15/09)
- **Status:** ⬜ em aberto

---

## Q3 — Definição da métrica de qualidade da IA

**Contexto.** RNF04 exige métricas de acurácia e consistência mensuráveis e reportáveis — é entregável
da 3ª parcial (20/10).

**Pergunta.** O que exatamente se mede: campos corretos extraídos? Coerência da ementa? Como se coleta
o gabarito?

**Por que importa.** **Sem isso, a 3ª parcial não tem entregável verificável.** É a questão mais crítica
desta lista.

**Encaminhamento.** Definir as métricas em [métricas de qualidade](../04-ia/metricas-qualidade.md) e
montar o conjunto de avaliação com casos reais anonimizados do cliente (meta: 20 casos anotados).

- **Responsável:** IA + Documentação
- **Prazo:** definição até 15/09; primeira medição até 06/10
- **Status:** ⬜ em aberto

---

## Q4 — Fronteira do custeio

**Contexto.** O custeio era núcleo do projeto e foi reposicionado como evolução futura: não existe
base de custo modelável — a estimativa é hoje tácita e humana.

**Decisão tomada.** O custeio permanece **fora do MVP** até existir a fundação de dados (RNF-F1).
**Não prometer faixa orçamentária** ao cliente sem essa base.

- **Responsável:** Gerência
- **Status:** ✅ decidido — mantido como registro para não ser reaberto por engano

---

## Q5 — Ambiente de homologação

**Contexto.** RNF12 restringe a operação a camada gratuita/estudantil; RNF15 exige portabilidade.

**Pergunta.** Onde a aplicação é hospedada para a homologação com o cliente e para a banca?

**Por que importa.** Demonstração na banca rodando só em `localhost` é frágil. A escolha precisa
caber no custo zero e não amarrar o projeto a um provedor específico.

- **Responsável:** Gerência + Backend
- **Prazo:** Fase 3 (até 20/10)
- **Status:** ⬜ em aberto

---

## Q6 — Papéis de usuário

**Contexto.** RF16 pede autenticação; RNF10 pede controle de acesso. Hoje o processo tem **um único
operador**.

**Pergunta.** O MVP precisa de mais de um papel (ex.: administrador × operador) ou basta usuário
autenticado?

**Recomendação.** Um único papel no MVP. Multiusuário e multiempresa são RNF-F3, evolução futura.
Modelar o campo `papel` desde já, sem implementar autorização por papel.

- **Responsável:** Backend
- **Prazo:** antes da modelagem final de dados (08/09)
- **Status:** ⬜ em aberto
