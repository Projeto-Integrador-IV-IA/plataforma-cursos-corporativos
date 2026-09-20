"""Persistencia atomica e consulta dos resultados vinculados a demanda."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session, selectinload

from app.models import Artifact, ArtifactSource, ArtifactVersion, RawInput


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_result(
        self,
        artifact: Artifact,
        version: ArtifactVersion,
        source_links: list[ArtifactSource],
    ) -> Artifact:
        """Insere agregado completo; um unico flush valida todas as restricoes."""

        artifact.versions.append(version)
        artifact.source_links.extend(source_links)
        self.session.add(artifact)
        self.session.flush()
        return self.get_by_id(artifact.id) or artifact

    def get_sources(self, source_ids: list[UUID]) -> list[RawInput]:
        statement = sa.select(RawInput).where(RawInput.id.in_(source_ids))
        return list(self.session.scalars(statement).all())

    def get_by_id(self, artifact_id: UUID) -> Artifact | None:
        statement = (
            sa.select(Artifact)
            .where(Artifact.id == artifact_id)
            .options(
                selectinload(Artifact.versions),
                selectinload(Artifact.source_links).selectinload(ArtifactSource.raw_input),
            )
        )
        return self.session.scalar(statement)

    def list_by_demand(self, demand_id: UUID) -> list[Artifact]:
        statement = (
            sa.select(Artifact)
            .where(Artifact.demand_id == demand_id)
            .options(
                selectinload(Artifact.versions),
                selectinload(Artifact.source_links).selectinload(ArtifactSource.raw_input),
            )
            .order_by(Artifact.created_at.desc(), Artifact.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def rollback(self) -> None:
        self.session.rollback()
