# Testes end-to-end

Testes que atravessam **mais de um microsserviço**. Teste de um serviço isolado mora em
`services/<serviço>/tests`.

## O que validar aqui

O fluxo completo do MVP, que é exatamente a entrega da 4ª parcial (17/11):

1. autenticar (RF16);
2. cadastrar cliente (RF01) e demanda (RF02);
3. registrar demanda bruta em texto livre (RF09);
4. verificar que o bruto foi persistido **antes** da chamada ao LLM (RNF05);
5. obter o curso estruturado e conferir que ele foi anexado à negociação (RF11, RF12, RF13);
6. editar a saída da IA como operador (RF14);
7. avançar e **retroceder** etapas do pipeline (RF05, RF06);
8. conferir que o histórico registrou todas as transições, sem lacuna (RF07, RNF09);
9. recuperar uma versão anterior do artefato (RF08, RF15).

## Cenários de falha obrigatórios

- LLM indisponível ou em timeout: a demanda bruta permanece registrada e recuperável (RNF05).
- Transição inválida de etapa: recusada com erro padronizado, sem alterar o histórico.
- Requisição sem token: recusada em toda rota, exceto login e health (RNF10).

## Como rodar

O LLM é substituído pelo provedor falso (`LLM_PROVIDER=mock`): a suíte não gasta chamada paga
(RNF12) e o resultado é determinístico. Sem dependência além de `pytest` — as chamadas HTTP usam
só a biblioteca padrão do Python.

```bash
make up                         # ou: docker compose up -d
pip install -r tests/requirements.txt
pytest tests/e2e
```

**Pré-requisito que a suíte não resolve por si:** um usuário operador cadastrado no
`pipeline-service` — o MVP ainda não tem cadastro de usuário por API (ver
[docs/01-requisitos/questoes-em-aberto.md](../docs/01-requisitos/questoes-em-aberto.md)). Sem ele,
a suíte pula com uma mensagem explicando o que falta, em vez de falhar com erro de rede. Para
criar um operador de teste:

```bash
docker compose exec gateway-service python -c \
  "import bcrypt; print(bcrypt.hashpw(b'Senha123!', bcrypt.gensalt()).decode())"
docker compose exec db psql -U cursos -d cursos_corporativos -c \
  "INSERT INTO users (name, email, password_hash, role) VALUES \
   ('Operador de Teste', 'operador@teste.com', '<hash gerado acima>', 'OPERADOR');"
```

Credenciais diferentes das acima: configure `E2E_OPERATOR_EMAIL` e `E2E_OPERATOR_PASSWORD`.
Gateway em endereço diferente de `http://localhost:8000`: configure `E2E_BASE_URL`
(`<base>/api/v1` é montado por `tests/e2e/conftest.py`).

> Verificado ao vivo em 17/11/2026 contra a stack completa: os nove passos do fluxo principal e os
> dois cenários de falha abaixo (sem token, transição inválida) passam. O cenário de LLM
> indisponível/timeout já é verificado em
> [`services/ai-structuring-service/tests/integration/test_structuring_jobs.py`](../services/ai-structuring-service/tests/integration/test_structuring_jobs.py)
> (`_ProvedorQueFalha`) — reproduzi-lo aqui exigiria reconfigurar o provedor da stack em execução,
> o que o tornaria um teste de outra natureza; o que esta pasta prova é a integração entre
> serviços, não o comportamento de cada um isolado.
