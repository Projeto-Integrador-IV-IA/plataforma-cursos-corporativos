"""Modelos ORM do dominio relacional exigido pelo RNF08."""

from app.models.artifact import Artifact, ArtifactSource, ArtifactVersion
from app.models.client import Client
from app.models.demand import Demand
from app.models.raw_input import RawInput, SourceSegment
from app.models.segment_embedding import SegmentEmbedding
from app.models.stage_transition import StageTransition
from app.models.user import User

__all__ = [
    "Artifact",
    "ArtifactSource",
    "ArtifactVersion",
    "Client",
    "Demand",
    "RawInput",
    "SegmentEmbedding",
    "SourceSegment",
    "StageTransition",
    "User",
]
