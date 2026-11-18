"""Persistencia das decisoes de revisao de um artefato: leitura e insercao, nunca alteracao."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.artifact_review import ArtifactReview


class ArtifactReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        artifact_id: UUID,
        *,
        version_number: int,
        decision: str,
        author_id: UUID,
        reason: str | None,
    ) -> ArtifactReview:
        review = ArtifactReview(
            artifact_id=artifact_id,
            version_number=version_number,
            decision=decision,
            author_id=author_id,
            reason=reason,
        )
        self.session.add(review)
        self.session.flush()
        self.session.refresh(review)
        return review

    def list_for_artifact(self, artifact_id: UUID) -> list[ArtifactReview]:
        """Todas as decisoes do artefato, da mais antiga a mais recente."""

        statement = (
            sa.select(ArtifactReview)
            .where(ArtifactReview.artifact_id == artifact_id)
            .order_by(ArtifactReview.created_at.asc())
        )
        return list(self.session.scalars(statement).all())
