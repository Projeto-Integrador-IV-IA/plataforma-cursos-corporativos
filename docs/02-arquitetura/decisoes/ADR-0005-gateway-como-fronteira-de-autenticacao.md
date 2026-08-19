# ADR-0005 — Gateway como fronteira de autenticação

- **Status:** Aceita
- **Data:** 2026-08-19
- **Requisitos:** RF16, RF07, RNF01, RNF10

## Contexto

RF16 exige autenticação para acessar a plataforma e RNF10 exige controle de acesso com dados de
clientes não expostos publicamente. Com quatro serviços de backend, é preciso decidir **onde** a
autenticação acontece.

Há ainda um requisito que depende disso: RF07 exige registrar *quem* mudou a etapa. A identidade do
usuário precisa chegar até o `pipeline-service` de forma confiável.

RNF01 lista quatro frentes e não menciona um gateway. Este ADR justifica o acréscimo.

## Decisão

**Um `gateway-service` como única porta de entrada da plataforma.**

- O gateway autentica (login, emissão e validação de token JWT) e roteia para os serviços internos.
- Os serviços internos **não são expostos publicamente**: no Compose, só o gateway e o frontend
  publicam porta para fora; a comunicação interna ocorre na rede do Docker.
- A identidade do usuário autenticado é propagada aos serviços internos por header, junto do
  `X-Request-ID`. É dela que sai o autor das transições de etapa (RF07) e das versões de artefato.
- O padrão é **negar**: rota nova nasce protegida. As únicas exceções são `login` e `health`.
- O gateway não contém regra de negócio. Ele autentica e encaminha — nada mais.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Cada serviço valida o próprio token** | Quatro implementações de validação para manter e auditar; a chance de uma delas ficar desatualizada e virar brecha é real. Contra RNF10. |
| **Autenticação só no frontend** | Não é controle de acesso: qualquer chamada direta à API passaria. Descartada. |
| **Provedor externo de identidade (OAuth/SSO)** | Mais robusto, porém adiciona dependência externa e configuração para um sistema com um único operador. RNF-F2 trata credenciais de terceiros como evolução futura. |
| **Nenhum gateway; frontend chama cada serviço** | O frontend passaria a conhecer a topologia interna, e todos os serviços precisariam ser expostos publicamente — o oposto de RNF10. |

## Consequências

**Positivas**

- Uma única superfície de autenticação para revisar e auditar (RNF10).
- Serviços internos não ficam expostos à internet.
- O frontend conhece **uma** URL base, e a topologia interna pode mudar sem quebrá-lo (RNF13).
- A autoria da trilha de auditoria vem do token, nunca do corpo da requisição — não é falsificável
  pelo cliente (RF07, RNF09).

**Negativas**

- Um salto de rede a mais em toda requisição, o que pesa contra o alvo de RNF07 (≤ 500 ms). Mitigado
  encaminhando as rotas de CRM direto ao pipeline, sem agregação intermediária.
- O gateway é ponto único de falha do acesso. Aceito no MVP.
- Os serviços internos **confiam** no header de identidade vindo do gateway. Essa confiança só é
  válida enquanto eles não estiverem publicamente acessíveis — condição a revalidar quando o ambiente
  de homologação for definido (ver [Q5](../../01-requisitos/questoes-em-aberto.md)).
