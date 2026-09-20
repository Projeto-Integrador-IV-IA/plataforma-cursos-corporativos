"""DTOs da fronteira HTTP da estruturacao (RF11, RF12).

Entrada: identificador da demanda, texto ja normalizado pelo ingestion-service
(RF10) e a versao do prompt a usar. Saida: o curso na forma canonica de
``app.domain.course`` mais os metadados de execucao.

Por que os metadados vem junto e nao so o curso: sem saber qual provedor, qual
modelo e qual versao de prompt produziram aquele resultado, nao da para
comparar duas medicoes de qualidade (RNF04) nem para reproduzir o artefato
depois que ele for gravado na negociacao (RNF09). Eles nao carregam credencial
(RNF11) nem trecho do texto do cliente (RNF10).

O curso em si nao e redeclarado aqui: ``StructuredCourse`` e o contrato, e
duplica-lo em um DTO paralelo seria criar uma segunda fonte de verdade que sai
de sincronia no primeiro campo novo (RNF03, ADR-0006).
"""

from typing import Any, Final, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.course import StructuredCourse
from app.prompts import listar_prompts
from app.services.structuring_service import (
    DEFAULT_PROMPT_VERSION,
    EXTRACTION_PROMPT_NAME,
    StructuringOutcome,
)

#: Teto do texto aceito em uma demanda, em caracteres. Nao e regra de negocio:
#: e o limite que mantem uma chamada dentro do tempo interativo (RNF06) e da
#: camada gratuita do provedor (RNF12). Texto maior e recusado na entrada, com
#: 422, em vez de estourar o teto de tokens no meio da chamada.
TEXTO_MAXIMO: Final[int] = 50_000

#: Demanda de exemplo exibida no Swagger. Dado ficticio - nenhum cliente real (RNF10).
EXEMPLO_DE_REQUISICAO: Final[dict[str, Any]] = {
    "demand_id": "dem-2026-0042",
    "text": (
        "Boa tarde! Conforme conversamos, precisamos de um treinamento de NR-12 para o "
        "pessoal da manutencao da planta 2, uns 25 tecnicos. A ideia e fazer em dois dias "
        "de 8 horas, no proprio site. Fico no aguardo da proposta."
    ),
    "prompt_version": "v2",
}

#: Resposta de exemplo exibida no Swagger, na ordem canonica dos campos.
EXEMPLO_DE_RESPOSTA: Final[dict[str, Any]] = {
    "demand_id": "dem-2026-0042",
    "course": {
        "tema": "NR-12 (seguranca em maquinas e equipamentos)",
        "nicho": None,
        "publico_alvo": "Tecnicos de manutencao da planta 2",
        "numero_participantes": 25,
        "carga_horaria": 16,
        "formato": "presencial",
        "objetivos_aprendizagem": [],
        "ementa": [],
        "campos_ausentes": ["ementa", "objetivos_aprendizagem"],
        "observacoes": [
            "O cliente nao descreveu o conteudo nem os objetivos do treinamento.",
        ],
    },
    "execution": {
        "provider": "mock",
        "model": "mock",
        "prompt": "extract-requirements.v1",
        "attempts": 1,
        "prompt_tokens": 940,
        "completion_tokens": 210,
        "total_tokens": 1150,
        "provider_latency_ms": 820.4,
        "elapsed_ms": 861.7,
    },
}


class StructuringRequest(BaseModel):
    """Texto normalizado que entra na estruturacao (RF11).

    ``extra="forbid"`` recusa campo desconhecido na entrada: chamador fora de
    sincronia com o contrato recebe 422 em vez de ter o campo ignorado em
    silencio (RNF02).
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [EXEMPLO_DE_REQUISICAO]},
    )

    demand_id: str = Field(
        min_length=1,
        max_length=64,
        description="Identificador da demanda na negociacao, usado para correlacionar "
        "log, metrica e reprocessamento.",
    )
    text: str = Field(
        min_length=1,
        max_length=TEXTO_MAXIMO,
        description="Texto da demanda ja normalizado pelo ingestion-service (RF10).",
    )
    prompt_version: str = Field(
        default=DEFAULT_PROMPT_VERSION,
        description="Versao do prompt de extracao a usar, no formato 'v1'. "
        "Acompanha o resultado para que a execucao seja reproduzivel (RNF04).",
    )

    @field_validator("prompt_version")
    @classmethod
    def versao_existe_no_catalogo(cls, valor: str) -> str:
        """Recusa versao inexistente na entrada, e nao no meio da execucao.

        Sem isso, pedir uma versao que ninguem escreveu viraria erro interno
        depois que a demanda ja entrou no fluxo; aqui vira 422 com a lista do
        que existe.
        """

        disponiveis = [v for nome, v in listar_prompts() if nome == EXTRACTION_PROMPT_NAME]
        if valor not in disponiveis:
            raise ValueError(
                f"Versao de prompt desconhecida: {valor!r}. "
                f"Disponiveis: {', '.join(disponiveis) or 'nenhuma'}."
            )
        return valor


class ExecutionMetadata(BaseModel):
    """Proveniencia da execucao que produziu o curso (RNF04, RNF09, RNF12).

    Attributes:
        provider: provedor que atendeu a chamada (``LLM_PROVIDER``).
        model: modelo que efetivamente respondeu.
        prompt: prompt versionado usado, ex.: ``extract-requirements.v1``.
        attempts: tentativas gastas, contando a primeira (RNF05).
        prompt_tokens: tokens de entrada consumidos.
        completion_tokens: tokens gerados.
        total_tokens: soma dos dois, insumo do custo de operacao (RNF12).
        provider_latency_ms: tempo da chamada que respondeu.
        elapsed_ms: tempo do caso de uso inteiro, incluindo as esperas entre
            tentativas - e este que se compara ao alvo de 15 s (RNF06).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    prompt: str
    attempts: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider_latency_ms: float
    elapsed_ms: float


class StructuringResponse(BaseModel):
    """Curso estruturado devolvido pela estruturacao (RF11, RF12).

    O curso vai aninhado em ``course`` de proposito: e exatamente a forma que o
    pipeline-service vai gravar como artefato da negociacao (RF13), sem que a
    proveniencia da execucao se misture aos campos pedagogicos.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [EXEMPLO_DE_RESPOSTA]},
    )

    demand_id: str
    course: StructuredCourse
    execution: ExecutionMetadata

    @classmethod
    def from_outcome(cls, outcome: StructuringOutcome) -> Self:
        """Monta a resposta a partir do desfecho do caso de uso.

        Args:
            outcome: desfecho de ``StructuringService.structure_course``.

        Returns:
            A resposta correspondente, com curso e proveniencia.

        Raises:
            LLMProviderError: o desfecho carrega falha em vez de curso - a
                traducao para resposta HTTP fica com o handler de ``app.main``.
        """

        curso = outcome.raise_for_course()
        completion = outcome.raise_for_error()
        return cls(
            demand_id=outcome.demand.demand_id,
            course=curso,
            execution=ExecutionMetadata(
                provider=completion.provider,
                model=completion.model,
                prompt=outcome.prompt_id or "",
                attempts=outcome.attempts,
                prompt_tokens=completion.usage.prompt_tokens,
                completion_tokens=completion.usage.completion_tokens,
                total_tokens=completion.usage.total_tokens,
                provider_latency_ms=completion.latency_ms,
                elapsed_ms=outcome.elapsed_ms,
            ),
        )
