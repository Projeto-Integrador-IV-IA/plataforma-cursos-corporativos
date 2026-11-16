"""Guarda de arquitetura: SDK de provedor so existe dentro de ``app/providers``.

Se um modulo de caso de uso, rota ou dominio importar o SDK de um fornecedor, a
troca de provedor deixa de ser configuracao e vira refatoracao - exatamente o
que RNF03 e a ADR-0006 evitam. Este teste falha antes disso acontecer.

``app/clients`` tem uma isencao mais estreita que ``app/providers``: pode usar
cliente HTTP generico para falar com os outros microsservicos da propria
plataforma (RNF01, ex.: `pipeline-service`), mas nao pode importar SDK de
fornecedor de LLM - essa troca continua exclusiva de ``app/providers``.
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"
PROVIDERS_DIR = APP_DIR / "providers"
CLIENTS_DIR = APP_DIR / "clients"

# Raiz do modulo de cada SDK/cliente de fornecedor conhecido.
SDKS_DE_PROVEDOR = frozenset(
    {
        "anthropic",
        "boto3",
        "cohere",
        "google",
        "groq",
        "huggingface_hub",
        "langchain",
        "litellm",
        "mistralai",
        "ollama",
        "openai",
        "transformers",
        "vertexai",
    }
)

# Cliente HTTP generico: legitimo em qualquer lugar, exceto para falar com o
# fornecedor - por isso tambem fica restrito ao pacote de provedores. Em
# ``app/clients`` e o que fala com os outros microsservicos da plataforma, por
# isso essa pasta fica de fora so desta lista, nunca da de SDK de fornecedor.
CLIENTES_HTTP = frozenset({"httpx", "requests", "aiohttp", "urllib3"})

RESTRITOS = SDKS_DE_PROVEDOR | CLIENTES_HTTP


def _modulos_raiz_importados(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    raizes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            raizes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            raizes.add(no.module.split(".")[0])
    return raizes


def _modulos_fora_de_providers() -> list[Path]:
    return [
        arquivo for arquivo in sorted(APP_DIR.rglob("*.py")) if PROVIDERS_DIR not in arquivo.parents
    ]


def test_nenhum_modulo_fora_de_providers_importa_sdk_de_provedor() -> None:
    infratores: dict[str, list[str]] = {}
    for arquivo in _modulos_fora_de_providers():
        restritos_do_arquivo = RESTRITOS
        if CLIENTS_DIR in arquivo.parents:
            restritos_do_arquivo = SDKS_DE_PROVEDOR

        restritos = sorted(_modulos_raiz_importados(arquivo) & restritos_do_arquivo)
        if restritos:
            infratores[arquivo.relative_to(APP_DIR).as_posix()] = restritos

    assert infratores == {}, (
        "SDK de provedor importado fora de app/providers - o servico deve falar "
        f"apenas com a abstracao LLMProvider: {infratores}"
    )


def test_a_varredura_cobre_modulos_de_verdade() -> None:
    """Protege o teste acima de passar por varrer uma lista vazia."""

    arquivos = _modulos_fora_de_providers()

    assert len(arquivos) > 5
    assert APP_DIR / "core" / "exceptions.py" in arquivos


def test_contrato_do_provedor_nao_depende_de_fornecedor_concreto() -> None:
    assert not _modulos_raiz_importados(PROVIDERS_DIR / "base.py") & RESTRITOS


def test_clientes_de_microsservico_nao_importam_sdk_de_fornecedor() -> None:
    """``app/clients`` ganhou isencao de cliente HTTP, nunca de SDK de LLM."""

    infratores: dict[str, list[str]] = {}
    for arquivo in sorted(CLIENTS_DIR.rglob("*.py")):
        restritos = sorted(_modulos_raiz_importados(arquivo) & SDKS_DE_PROVEDOR)
        if restritos:
            infratores[arquivo.relative_to(APP_DIR).as_posix()] = restritos

    assert infratores == {}
