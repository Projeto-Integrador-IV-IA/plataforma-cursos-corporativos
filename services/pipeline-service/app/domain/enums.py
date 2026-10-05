"""Fonte unica dos vocabularios fechados do dominio (RNF02)."""

from enum import StrEnum


class PipelineStage(StrEnum):
    """Etapas percorridas por uma demanda no pipeline (RF05)."""

    CAPTACAO = "CAPTACAO"
    ESTRUTURACAO = "ESTRUTURACAO"
    PRODUTO = "PRODUTO"
    PROPOSTA = "PROPOSTA"
    ACOMPANHAMENTO = "ACOMPANHAMENTO"


class DemandStatus(StrEnum):
    """Situacoes da demanda, ortogonais a etapa corrente."""

    ABERTA = "ABERTA"
    GANHA = "GANHA"
    PERDIDA = "PERDIDA"
    CANCELADA = "CANCELADA"


class RawInputSource(StrEnum):
    """Origens aceitas para uma fonte bruta."""

    EMAIL = "EMAIL"
    TRANSCRICAO = "TRANSCRICAO"
    MENSAGENS = "MENSAGENS"
    ANOTACAO = "ANOTACAO"
    OUTRO = "OUTRO"


class ArtifactType(StrEnum):
    """Naturezas aceitas para um artefato consolidado (RF15)."""

    DEMANDA_BRUTA = "DEMANDA_BRUTA"
    REQUISITOS_EXTRAIDOS = "REQUISITOS_EXTRAIDOS"
    EMENTA = "EMENTA"
    PROPOSTA = "PROPOSTA"
    OUTRO = "OUTRO"


class ArtifactOrigin(StrEnum):
    """Autores logicos possiveis para uma versao de artefato."""

    IA = "IA"
    HUMANO = "HUMANO"


def enum_values(enum_type: type[StrEnum]) -> tuple[str, ...]:
    """Retorna os valores persistidos de uma enumeracao de contrato."""

    return tuple(item.value for item in enum_type)


def sql_enum_values(enum_type: type[StrEnum]) -> str:
    """Formata valores controlados para uso em um ``CheckConstraint``."""

    return ", ".join(f"'{value}'" for value in enum_values(enum_type))
