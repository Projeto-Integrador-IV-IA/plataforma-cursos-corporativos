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

from pydantic import BaseModel, ConfigDict

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
