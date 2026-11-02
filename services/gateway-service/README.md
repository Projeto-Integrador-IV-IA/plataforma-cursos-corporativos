# gateway-service

Porta de entrada unica da plataforma: autenticacao, roteamento e agregacao para o frontend. Atende **RNF25** (Documento Consolidado de Requisitos v1.0).

- **Porta:** `8000`
- **Requisitos atendidos:** RF16, RF17, RNF02, RNF10, RNF25
- **Contrato de API:** [`packages/contracts/openapi/gateway-service.yaml`](../../packages/contracts/openapi/gateway-service.yaml)

---

## 1. Responsabilidade e Fronteira

O **Gateway Service** atua como o único ponto de entrada para o cliente/frontend da plataforma.
- **O que ele faz:** Concentra a autenticação de usuários, emite tokens JWT, realiza o roteamento reverso e o encaminhamento seguro de requisições para os microsserviços internos, mantendo-os isolados da rede pública.
- **O que ele NÃO faz:** Não armazena dados de negócios, não gerencia o banco relacional diretamente (delega a consulta interna ao `pipeline-service`) e não executa regras de IA ou ingestão.

---

## 2. Estrutura

```
app/
├── main.py        Ponto de entrada da aplicacao (FastAPI)
├── core/          Configuracao, logging e excecoes
├── api/v1/        Rotas HTTP versionadas (RNF02)
├── schemas/       DTOs de entrada e saida (Pydantic)
└── services/      Casos de uso / regras de aplicacao
```

---

## 3. Endpoints Expostos e Mapa de Encaminhamento

O gateway intercepta e encaminha as requisições para os serviços correspondentes na rede interna:

| Método | Endpoint do Gateway | Encaminha para / Descrição |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Autentica via `pipeline-service` e emite o JWT |
| `GET` | `/api/v1/auth/verify` | Valida o token e retorna o perfil atual |
| `POST` | `/api/v1/demands` | Encaminha para o `pipeline-service` (`/api/v1/demands`) |
| `GET` | `/api/v1/demands/{id}` | Encaminha para o `pipeline-service` |
| `POST` | `/api/v1/ingestion/...` | Encaminha para o `ingestion-service` |
| `POST` | `/api/v1/ai/structure` | Encaminha para o `ai-structuring-service` |

---

## 4. Como Executar

```bash
# Exporte no shell as variaveis de .env.example e preencha os campos vazios.
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$GATEWAY_PORT"

---

## 5. Autenticação, Sessão e Como Obter o Token para Testes

Para exercitar as rotas protegidas de qualquer microsserviço através do gateway, você precisa primeiro autenticar-se e obter um token JWT válido:

1. **Faça a chamada de login:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email": "seu-email@exemplo.com", "password": "sua-senha"}'

2. **Copie o token retornado no payload JSON.

3. **Utilize o token nas requisições subsequentes para rotas protegidas enviando o header de autorização:

Authorization: Bearer <seu-token-jwt>

`POST /api/v1/auth/login` recebe e-mail e senha, consulta o usuário pela API
interna do pipeline-service, verifica o hash bcrypt e emite um JWT. O tempo de
vida vem de `ACCESS_TOKEN_EXPIRE_MINUTES`; tokens expirados, adulterados ou
assinados com outra chave recebem 401.

`GET /api/v1/auth/verify` é uma operação protegida de referência. Rotas protegidas futuras devem depender de `get_current_user`, que devolve a identidade e o perfil autenticados.

O gateway não acessa o banco. A consulta interna usa `AUTH_SERVICE_KEY`,
compartilhada somente com o pipeline-service, e os serviços internos continuam
sem porta pública. `JWT_SECRET_KEY` e `AUTH_SERVICE_KEY` devem ter ao menos 32
caracteres e nunca entram no repositório.

O cadastro de usuários já persiste somente `password_hash`. `hash_password`
gera bcrypt com salt; `verify_password` aceita os hashes bcrypt existentes. O
login devolve a mesma mensagem para e-mail inexistente, senha errada e usuário
inativo, evitando revelar quais contas existem.

## 6. Testes

```bash
pytest

