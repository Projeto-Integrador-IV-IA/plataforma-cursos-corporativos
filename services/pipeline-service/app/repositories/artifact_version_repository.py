"""Persistencia das versoes de um artefato: leitura e insercao, nunca alteracao (RF08).

Versoes sao append-only: restaurar cria uma versao nova e nao toca nas
existentes, entao este repositorio nao tem update nem delete. Como os demais,
nao encerra a transacao - so faz ``flush``.
"""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.artifact import Artifact, ArtifactVersion


class ArtifactVersionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_artifact_for_update(self, artifact_id: UUID) -> Artifact | None:
        """Le o artefato travando a linha ate o fim da transacao.

        Duas restauracoes simultaneas calculariam o mesmo proximo numero; o
        lock as serializa. O SQLite dos testes ignora ``FOR UPDATE``; ali a
        unicidade de (artefato, numero) barra a segunda.
        """

        statement = sa.select(Artifact).where(Artifact.id == artifact_id).with_for_update()
        return self.session.scalar(statement)

    def get(self, artifact_id: UUID, number: int) -> ArtifactVersion | None:
        statement = sa.select(ArtifactVersion).where(
            ArtifactVersion.artifact_id == artifact_id,
            ArtifactVersion.number == number,
        )
        return self.session.scalar(statement)

    def latest_number(self, artifact_id: UUID) -> int:
        """Numero da versao vigente (a maior); zero se o artefato nao tem versao."""

        statement = sa.select(sa.func.max(ArtifactVersion.number)).where(
            ArtifactVersion.artifact_id == artifact_id
        )
        return self.session.scalar(statement) or 0

    def add(self, version: ArtifactVersion) -> ArtifactVersion:
        """Insere e valida as restricoes antes de devolver."""

        self.session.add(version)
        self.session.flush()
        self.session.refresh(version)
        return version
