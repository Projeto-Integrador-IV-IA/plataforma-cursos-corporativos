# gateway-service

Porta de entrada unica da plataforma: autenticacao, roteamento e agregacao para o frontend.

- **Porta:** `8000`
- **Requisitos atendidos:** RF16, RF17, RNF10, RNF02
- **Contrato de API:** [`packages/contracts/openapi/gateway-service.yaml`](../../packages/contracts/openapi/gateway-service.yaml)

## Estrutura

```
app/
├── main.py        Ponto de entrada da aplicacao (FastAPI)
├── core/          Configuracao, logging e excecoes
├── api/v1/        Rotas HTTP versionadas (RNF02)
├── schemas/       DTOs de entrada e saida (Pydantic)
└── services/      Casos de uso / regras de aplicacao
```

## Executar

```bash
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$GATEWAY_PORT"
```

## Autenticacao e sessao

`POST /api/v1/auth/login` recebe e-mail e senha, consulta o usuario pela API
interna do `pipeline-service`, verifica o hash bcrypt e emite um JWT. O tempo de
vida vem de `ACCESS_TOKEN_EXPIRE_MINUTES`; tokens expirados, adulterados ou
assinados com outra chave recebem `401`.

`GET /api/v1/auth/verify` e uma operacao protegida de referencia. Envie
`Authorization: Bearer <token>`. Rotas protegidas futuras devem depender de
`get_current_user`, que devolve a identidade e o perfil autenticados.

O gateway nao acessa o banco. A consulta interna usa `AUTH_SERVICE_KEY`,
compartilhada somente com o `pipeline-service`, e os servicos internos continuam
sem porta publica. `JWT_SECRET_KEY` e `AUTH_SERVICE_KEY` devem ter ao menos 32
caracteres e nunca entram no repositorio.

O cadastro de usuarios ja persiste somente `password_hash`. `hash_password`
gera bcrypt com salt; `verify_password` aceita os hashes bcrypt existentes. O
login devolve a mesma mensagem para e-mail inexistente, senha errada e usuario
inativo, evitando revelar quais contas existem.

## Testes

```bash
pytest
```
