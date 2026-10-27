"""Persistencia das versoes de um artefato: leitura e insercao, nunca alteracao (RF08).

Versao de artefato nunca e sobrescrita: cada alteracao cria um registro novo.
Por isso este repositorio so tem leituras e ``append`` - nao ha update nem
delete, e nao deve haver. O ORM e o banco tambem recusam alterar ou apagar uma
versao ja gravada. Como os demais, nao encerra a transacao: so faz ``flush``.
"""

from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.artifact import Artifact, ArtifactVersion


class ArtifactVersionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_artifact_for_update(self, artifact_id: UUID) -> Artifact | None:
        """Le o artefato travando a linha ate o fim da transacao.

        Quem vai chamar ``append`` deve travar antes: duas escritas simultaneas
        calculariam o mesmo proximo numero, e o lock as serializa. O SQLite dos
        testes ignora ``FOR UPDATE``; ali a unicidade de (artefato, numero) barra
        a segunda.
        """

        statement = sa.select(Artifact).where(Artifact.id == artifact_id).with_for_update()
        return self.session.scalar(statement)

    def get(self, artifact_id: UUID, number: int) -> ArtifactVersion | None:
        statement = sa.select(ArtifactVersion).where(
            ArtifactVersion.artifact_id == artifact_id,
            ArtifactVersion.number == number,
        )
        return self.session.scalar(statement)

    def list_for_artifact(self, artifact_id: UUID) -> list[ArtifactVersion]:
        """Todas as versoes do artefato, da primeira a vigente (a de maior numero)."""

        statement = (
            sa.select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.number.asc())
        )
        return list(self.session.scalars(statement).all())

    def latest_number(self, artifact_id: UUID) -> int:
        """Numero da versao vigente (a maior); zero se o artefato nao tem versao."""

        statement = sa.select(sa.func.max(ArtifactVersion.number)).where(
            ArtifactVersion.artifact_id == artifact_id
        )
        return self.session.scalar(statement) or 0

    def append(
        self,
        artifact_id: UUID,
        *,
        content: dict[str, Any],
        origin: str,
        author_id: UUID | None = None,
        raw_content: str | None = None,
        ai_metadata: dict[str, Any] | None = None,
        restored_from_number: int | None = None,
    ) -> ArtifactVersion:
        """Insere a proxima versao, ligada a anterior; nunca toca nas existentes.

        O numero e o vinculo com a antecessora saem daqui, e so daqui, para que
        nenhum chamador monte uma cadeia inconsistente. Os CHECKs e as chaves
        estrangeiras do banco validam antes de devolver.
        """

        current = self.latest_number(artifact_id)
        version = ArtifactVersion(
            artifact_id=artifact_id,
            number=current + 1,
            previous_number=current or None,
            content=content,
            origin=origin,
            author_id=author_id,
            raw_content=raw_content,
            ai_metadata=ai_metadata,
            restored_from_number=restored_from_number,
        )
        self.session.add(version)
        self.session.flush()
        self.session.refresh(version)
        return version
