"""Excecoes de dominio e traducao para respostas HTTP.

Erros previsiveis viram excecoes tipadas aqui e sao traduzidos em um corpo de
erro unico para toda a plataforma, de modo que o frontend trate qualquer
servico da mesma forma (RNF02).

Formato de erro acordado entre os servicos:
    {"error": {"code": "DEMAND_NOT_FOUND", "message": "...", "details": {...}}}

Hierarquia prevista:
    PlatformError                 base de todas
    ├── NotFoundError             recurso inexistente            -> 404
    ├── ValidationError           entrada invalida               -> 422
    ├── ConflictError             transicao de etapa invalida    -> 409
    ├── UnauthorizedError         sem autenticacao (RF16)        -> 401
    ├── ForbiddenError            sem permissao (RNF10)          -> 403
    └── UpstreamError             falha de servico dependente    -> 502/504
        └── LLMUnavailableError   timeout/erro do LLM (RNF05)    -> 503

TODO(scaffolding): implementar a hierarquia e os handlers do FastAPI.
"""

# TODO: class PlatformError(Exception): ...
# TODO: def register_exception_handlers(app) -> None: ...
