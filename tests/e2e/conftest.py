"""Fixtures do teste de ponta a ponta: fala com o gateway real, nenhum mock.

Pre-requisito (ver README.md desta pasta): a stack precisa estar de pe
(``make up`` ou ``docker compose up -d``) e um usuario operador precisa
existir no banco do pipeline-service - o MVP nao tem cadastro de usuario por
API ainda (so RF01-RF31 cobrem cliente/demanda/artefato), entao o primeiro
operador e sempre criado fora da aplicacao.
"""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000/api/v1")
OPERATOR_EMAIL = os.environ.get("E2E_OPERATOR_EMAIL", "operador@teste.com")
OPERATOR_PASSWORD = os.environ.get("E2E_OPERATOR_PASSWORD", "Senha123!")


@dataclass(frozen=True)
class ApiClient:
    """Cliente minimo sobre ``urllib`` - sem dependencia alem da biblioteca padrao."""

    base_url: str
    token: str | None = None

    def call(
        self,
        method: str,
        path: str,
        body: object = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, object]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode() or "null")
        except urllib.error.HTTPError as erro:
            raw = erro.read().decode()
            try:
                return erro.code, json.loads(raw)
            except json.JSONDecodeError:
                return erro.code, raw

    def authenticated(self, token: str) -> "ApiClient":
        return ApiClient(self.base_url, token)


@pytest.fixture(scope="session")
def api() -> ApiClient:
    return ApiClient(BASE_URL)


@pytest.fixture(scope="session")
def operator_token(api: ApiClient) -> Iterator[str]:
    """Faz login do operador de teste; pula a suite inteira se a stack nao respondeu.

    Nao cria o operador: ver o README desta pasta para o passo manual (insercao
    direta no banco). O objetivo aqui e falhar com uma mensagem util, nao um
    traceback de rede, quando o pre-requisito nao foi cumprido.
    """

    try:
        status, body = api.call(
            "POST", "/auth/login", {"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
        )
    except urllib.error.URLError as erro:
        pytest.skip(
            f"Stack nao respondeu em {BASE_URL} ({erro}). Suba com `make up` ou "
            "`docker compose up -d` antes de rodar tests/e2e."
        )

    if status != 200:
        pytest.skip(
            f"Login do operador de teste falhou (status={status}, body={body}). "
            f"Cadastre {OPERATOR_EMAIL!r} no pipeline-service antes de rodar tests/e2e "
            "(ver README.md desta pasta) ou informe E2E_OPERATOR_EMAIL/E2E_OPERATOR_PASSWORD."
        )

    yield body["access_token"]


@pytest.fixture
def authed_api(api: ApiClient, operator_token: str) -> ApiClient:
    return api.authenticated(operator_token)
