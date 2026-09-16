"""Contrato da maquina de estados do pipeline (RF05 e RF06)."""

import pytest

from app.domain.enums import DemandStatus, PipelineStage, enum_values
from app.domain.rules import VALID_TRANSITIONS, can_transition, next_stage

EXPECTED_STAGE_VALUES = (
    "CAPTACAO",
    "ESTRUTURACAO",
    "PRODUTO",
    "PROPOSTA",
    "ACOMPANHAMENTO",
)

EXPECTED_TRANSITIONS = {
    PipelineStage.CAPTACAO: {PipelineStage.ESTRUTURACAO},
    PipelineStage.ESTRUTURACAO: {
        PipelineStage.CAPTACAO,
        PipelineStage.PRODUTO,
    },
    PipelineStage.PRODUTO: {
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        PipelineStage.PROPOSTA,
    },
    PipelineStage.PROPOSTA: {
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        PipelineStage.PRODUTO,
        PipelineStage.ACOMPANHAMENTO,
    },
    PipelineStage.ACOMPANHAMENTO: {
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        PipelineStage.PRODUTO,
        PipelineStage.PROPOSTA,
    },
}


def test_pipeline_stages_are_persisted_in_business_order() -> None:
    assert enum_values(PipelineStage) == EXPECTED_STAGE_VALUES


def test_all_transition_rules_are_declared_in_one_mapping() -> None:
    assert {stage: set(targets) for stage, targets in VALID_TRANSITIONS.items()} == (
        EXPECTED_TRANSITIONS
    )


@pytest.mark.parametrize(
    ("current", "target"),
    [(current, target) for current, targets in EXPECTED_TRANSITIONS.items() for target in targets],
)
def test_declared_transitions_are_allowed(
    current: PipelineStage,
    target: PipelineStage,
) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (PipelineStage.CAPTACAO, PipelineStage.CAPTACAO),
        (PipelineStage.CAPTACAO, PipelineStage.PRODUTO),
        (PipelineStage.ESTRUTURACAO, PipelineStage.PROPOSTA),
        (PipelineStage.PRODUTO, PipelineStage.ACOMPANHAMENTO),
        (PipelineStage.ACOMPANHAMENTO, PipelineStage.ACOMPANHAMENTO),
    ],
)
def test_same_stage_and_skipped_forward_transitions_are_rejected(
    current: PipelineStage,
    target: PipelineStage,
) -> None:
    assert not can_transition(current, target)


@pytest.mark.parametrize(
    "status",
    [DemandStatus.GANHA, DemandStatus.PERDIDA, DemandStatus.CANCELADA],
)
def test_closed_demands_cannot_change_stage(status: DemandStatus) -> None:
    assert not can_transition(
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        status,
    )


def test_unknown_domain_values_are_rejected() -> None:
    assert not can_transition("ETAPA_INEXISTENTE", PipelineStage.CAPTACAO)
    assert not can_transition(PipelineStage.CAPTACAO, "ETAPA_INEXISTENTE")
    assert not can_transition(
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        "STATUS_INEXISTENTE",
    )


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        (PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO),
        (PipelineStage.ESTRUTURACAO, PipelineStage.PRODUTO),
        (PipelineStage.PRODUTO, PipelineStage.PROPOSTA),
        (PipelineStage.PROPOSTA, PipelineStage.ACOMPANHAMENTO),
        (PipelineStage.ACOMPANHAMENTO, None),
    ],
)
def test_next_stage_follows_declared_order(
    current: PipelineStage,
    expected: PipelineStage | None,
) -> None:
    assert next_stage(current) is expected
