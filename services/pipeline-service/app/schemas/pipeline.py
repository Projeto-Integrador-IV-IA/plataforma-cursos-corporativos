"""Contrato da visao de pipeline: demandas agrupadas por etapa (RF05).

Separados dos modelos ORM de proposito: o que a API expoe e contrato publico
(RNF02) e nao deve mudar so porque o schema do banco mudou.

O cartao carrega o minimo que a coluna precisa desenhar - cliente, titulo,
responsavel e situacao. Contexto, fontes e artefatos ficam no detalhe (RF02):
trazer o agregado inteiro de cada demanda encheria a resposta do quadro com
dados que nenhuma coluna mostra.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import DemandStatus, PipelineStage


class PipelineCardPersonRead(BaseModel):
    """Cliente ou responsavel exibido no cartao, reduzido a nome e identificador."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class PipelineCardRead(BaseModel):
    """Demanda como ela aparece na coluna de uma etapa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: DemandStatus
    client: PipelineCardPersonRead
    owner: PipelineCardPersonRead | None
    created_at: datetime
    updated_at: datetime


class PipelineStageGroup(BaseModel):
    """Uma coluna do quadro.

    ``total`` conta todas as demandas da etapa que passam pelos filtros, nao
    apenas as que vieram em ``items``: a coluna precisa mostrar quantas existem
    mesmo quando o recorte nao trouxe todas.
    """

    stage: PipelineStage
    total: int
    items: list[PipelineCardRead]


class PipelineBoard(BaseModel):
    """Quadro completo.

    As cinco etapas vem sempre, inclusive as vazias: o quadro tem colunas
    fixas, e omitir a etapa sem demanda faria a interface ter de inventar quais
    colunas desenhar.
    """

    stages: list[PipelineStageGroup]
    total: int


class StageChangeRequest(BaseModel):
    """Corpo opcional do avanco: so a justificativa; o destino vem da maquina de estados.

    O autor nao entra aqui de proposito: vem do cabecalho ``X-User-ID`` (RNF10).
    """

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Justificativa opcional do avanco; texto em branco equivale a ausente.",
    )

    @field_validator("reason")
    @classmethod
    def _blank_reason_is_absent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class StageChangeRead(BaseModel):
    """Resultado de uma mudanca de etapa: o evento gravado e a etapa resultante."""

    transition_id: UUID
    demand_id: UUID
    from_stage: PipelineStage
    current_stage: PipelineStage
    reason: str | None
    author_id: UUID
    occurred_at: datetime


class StageTransitionRead(BaseModel):
    """Um evento da trilha: de onde, para onde, quem moveu e quando.

    ``from_stage`` e nulo so no evento inicial de uma demanda, se existir.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    demand_id: UUID
    from_stage: PipelineStage | None
    to_stage: PipelineStage
    reason: str | None
    author: PipelineCardPersonRead
    occurred_at: datetime


class StageTransitionTimeline(BaseModel):
    """Linha do tempo de uma demanda, do mais antigo ao mais recente."""

    items: list[StageTransitionRead]
    total: int
