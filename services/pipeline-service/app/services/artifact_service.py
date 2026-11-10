"""Caso de uso atomico de vinculacao do resultado da IA (RF16.1 consolidado)."""

import sqlite3
from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.enums import ArtifactOrigin
from app.models import Artifact, ArtifactSource, ArtifactVersion, Demand
from app.models.user import User
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.artifact_version_repository import ArtifactVersionRepository
from app.schemas.artifact import (
    ArtifactRead,
    ArtifactResultCreate,
    ArtifactSourceRead,
    ArtifactVersionCreate,
    ArtifactVersionRead,
)


class ArtifactService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ArtifactRepository(session)
        self.versions = ArtifactVersionRepository(session)

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

    def restore_version(
        self,
        artifact_id: UUID,
        number: int,
        author_id: UUID,
    ) -> ArtifactVersionRead:
        """Restaura a versao ``number`` criando uma versao nova com o conteudo dela (RF08).

        Nao desfaz nada: nenhuma versao existente e alterada, e o caminho
        percorrido no meio continua consultavel. A versao nova e a vigente, tem
        origem humana, e guarda em ``restored_from_number`` qual voltou - ela e o
        evento de restauracao, com autor e instante. So faz ``flush``: o commit e
        da sessao da requisicao.
        """

        artifact = self.versions.get_artifact_for_update(artifact_id)
        if artifact is None:
            raise NotFoundError(
                code="ARTIFACT_NOT_FOUND",
                message="Artefato nao encontrado.",
                details={"artifact_id": str(artifact_id)},
            )
        if self.session.get(User, author_id) is None:
            raise NotFoundError(code="USER_NOT_FOUND", message="Operador nao encontrado.")

        chosen = self.versions.get(artifact_id, number)
        if chosen is None:
            raise NotFoundError(
                code="ARTIFACT_VERSION_NOT_FOUND",
                message=f"O artefato nao tem a versao {number}.",
                details={"artifact_id": str(artifact_id), "number": str(number)},
            )

        current = self.versions.latest_number(artifact_id)
        if number == current:
            raise ConflictError(
                code="ARTIFACT_VERSION_ALREADY_CURRENT",
                message=f"A versao {number} ja e a vigente; nao ha o que restaurar.",
                details={"artifact_id": str(artifact_id), "number": str(number)},
            )

        restored = self.versions.append(
            artifact_id,
            # Copia, nao referencia: a versao nova nao pode compartilhar o dict
            # com a restaurada. Sem bruto nem metadados de IA - quem restaurou e
            # uma pessoa; a origem na versao restaurada segue la.
            content=deepcopy(chosen.content),
            origin=ArtifactOrigin.HUMANO.value,
            author_id=author_id,
            restored_from_number=number,
            ai_origin_number=self.versions.ai_origin_of(chosen),
        )
        return ArtifactVersionRead.model_validate(restored)

    def edit_version(
        self,
        artifact_id: UUID,
        data: ArtifactVersionCreate,
        author_id: UUID,
    ) -> ArtifactVersionRead:
        """Salva a edicao humana como versao nova, vigente, e nunca sobrescreve (Q1, RF14).

        A versao nova tem origem humana, aponta para a versao de que partiu
        (``previous_number``) e para a versao da IA que originou a cadeia
        (``ai_origin_number``). A edicao so e aceita sobre a vigente: se alguem
        salvou no meio, devolve conflito em vez de apagar a edicao dele. So faz
        ``flush``: o commit e da sessao da requisicao.
        """

        artifact = self.versions.get_artifact_for_update(artifact_id)
        if artifact is None:
            raise NotFoundError(
                code="ARTIFACT_NOT_FOUND",
                message="Artefato nao encontrado.",
                details={"artifact_id": str(artifact_id)},
            )
        if self.session.get(User, author_id) is None:
            raise NotFoundError(code="USER_NOT_FOUND", message="Operador nao encontrado.")

        base = self.versions.get(artifact_id, data.base_number)
        if base is None:
            raise NotFoundError(
                code="ARTIFACT_VERSION_NOT_FOUND",
                message=f"O artefato nao tem a versao {data.base_number}.",
                details={"artifact_id": str(artifact_id), "number": str(data.base_number)},
            )

        current = self.versions.latest_number(artifact_id)
        if data.base_number != current:
            raise ConflictError(
                code="ARTIFACT_VERSION_NOT_CURRENT",
                message=(
                    f"A edicao partiu da versao {data.base_number}, mas a vigente e a "
                    f"{current}. Recarregue o artefato e refaca a edicao."
                ),
                details={
                    "artifact_id": str(artifact_id),
                    "base_number": str(data.base_number),
                    "current_number": str(current),
                },
            )

        if data.structured_content == base.content:
            raise ConflictError(
                code="ARTIFACT_CONTENT_UNCHANGED",
                message="O conteudo editado e igual ao da versao vigente; nada a salvar.",
                details={"artifact_id": str(artifact_id), "number": str(current)},
            )

        edited = self.versions.append(
            artifact_id,
            content=data.structured_content,
            origin=ArtifactOrigin.HUMANO.value,
            author_id=author_id,
            ai_origin_number=self.versions.ai_origin_of(base),
        )
        return ArtifactVersionRead.model_validate(edited)

    def list_versions(self, artifact_id: UUID) -> list[ArtifactVersionRead]:
        """Todas as versoes do artefato, da primeira a vigente (RF08)."""

        if self.session.get(Artifact, artifact_id) is None:
            raise NotFoundError(
                code="ARTIFACT_NOT_FOUND",
                message="Artefato nao encontrado.",
                details={"artifact_id": str(artifact_id)},
            )
        return [
            ArtifactVersionRead.model_validate(version)
            for version in self.versions.list_for_artifact(artifact_id)
        ]

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
