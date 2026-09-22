"""Caso de uso atomico de vinculacao do resultado da IA (RF16.1 consolidado)."""

import sqlite3
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.enums import ArtifactOrigin
from app.models import Artifact, ArtifactSource, ArtifactVersion, Demand
from app.repositories.artifact_repository import ArtifactRepository
from app.schemas.artifact import (
    ArtifactRead,
    ArtifactResultCreate,
    ArtifactSourceRead,
    ArtifactVersionRead,
)


class ArtifactService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ArtifactRepository(session)

    def create_result(self, demand_id: UUID, data: ArtifactResultCreate) -> ArtifactRead:
        if self.session.get(Demand, demand_id) is None:
            raise NotFoundError(
                code="DEMAND_NOT_FOUND",
                message="Demanda nao encontrada.",
                details={"demand_id": str(demand_id)},
            )

        sources = self.repository.get_sources(data.raw_input_ids)
        found_by_id = {source.id: source for source in sources}
        missing = [source_id for source_id in data.raw_input_ids if source_id not in found_by_id]
        if missing:
            raise NotFoundError(
                code="RAW_INPUT_NOT_FOUND",
                message="Uma ou mais fontes nao foram encontradas.",
                details={"raw_input_ids": ",".join(map(str, missing))},
            )
        foreign = [source.id for source in sources if source.demand_id != demand_id]
        if foreign:
            raise ConflictError(
                code="ARTIFACT_SOURCE_DEMAND_MISMATCH",
                message="Todas as fontes devem pertencer a demanda do artefato.",
                details={"raw_input_ids": ",".join(map(str, foreign))},
            )

        artifact = Artifact(
            id=uuid4(),
            demand_id=demand_id,
            type=data.type.value,
            title=data.title,
            raw_input_id=data.raw_input_ids[0],
        )
        version = ArtifactVersion(
            number=1,
            raw_content=data.raw_output,
            content=data.structured_content,
            origin=ArtifactOrigin.IA.value,
            ai_metadata=data.ai_metadata,
        )
        links = [
            ArtifactSource(
                artifact_id=artifact.id,
                raw_input_id=source_id,
                demand_id=demand_id,
            )
            for source_id in data.raw_input_ids
        ]
        try:
            created = self.repository.create_result(artifact, version, links)
        except IntegrityError as exc:
            self.repository.rollback()
            is_constraint_error = getattr(exc.orig, "sqlstate", None) in {
                "23503",
                "23505",
                "23514",
            } or getattr(exc.orig, "sqlite_errorcode", None) in {
                sqlite3.SQLITE_CONSTRAINT_CHECK,
                sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            }
            if not is_constraint_error:
                raise
            raise ConflictError(
                code="ARTIFACT_PERSISTENCE_CONFLICT",
                message="Nao foi possivel vincular atomicamente o resultado e suas fontes.",
                details={"demand_id": str(demand_id)},
            ) from exc
        return self._to_read(created)

    def list_by_demand(self, demand_id: UUID) -> list[ArtifactRead]:
        if self.session.get(Demand, demand_id) is None:
            raise NotFoundError(
                code="DEMAND_NOT_FOUND",
                message="Demanda nao encontrada.",
                details={"demand_id": str(demand_id)},
            )
        return [self._to_read(artifact) for artifact in self.repository.list_by_demand(demand_id)]

    @staticmethod
    def _to_read(artifact: Artifact) -> ArtifactRead:
        return ArtifactRead(
            id=artifact.id,
            demand_id=artifact.demand_id,
            type=artifact.type,
            title=artifact.title,
            created_at=artifact.created_at,
            sources=[
                ArtifactSourceRead.model_validate(link.raw_input) for link in artifact.source_links
            ],
            versions=[ArtifactVersionRead.model_validate(version) for version in artifact.versions],
        )
