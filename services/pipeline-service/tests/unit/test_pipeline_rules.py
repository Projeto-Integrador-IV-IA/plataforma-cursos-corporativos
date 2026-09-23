"""Contrato da maquina de estados do pipeline (RF05 e RF06).

Os casos sao derivados da ordem declarada em ``PipelineStage``, e nao de uma
copia da tabela de transicoes: uma tabela errada precisa falhar aqui, e nao
combinar com um espelho escrito no teste.
"""

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

STAGES = tuple(PipelineStage)
STAGE_PAIRS = [(current, target) for current in STAGES for target in STAGES]
CLOSED_STATUSES = (DemandStatus.GANHA, DemandStatus.PERDIDA, DemandStatus.CANCELADA)


def advances_one_step_or_goes_back(current: PipelineStage, target: PipelineStage) -> bool:
    """Traduz a regra do RF05 e do RF06 sem consultar ``VALID_TRANSITIONS``."""

    origin, destination = STAGES.index(current), STAGES.index(target)
    return destination == origin + 1 or destination < origin


def test_pipeline_stages_are_persisted_in_business_order() -> None:
    assert enum_values(PipelineStage) == EXPECTED_STAGE_VALUES


def test_every_stage_declares_its_transitions() -> None:
    assert set(VALID_TRANSITIONS) == set(STAGES)


@pytest.mark.parametrize(("current", "target"), STAGE_PAIRS)
def test_only_the_next_stage_advances_and_any_previous_is_reachable(
    current: PipelineStage,
    target: PipelineStage,
) -> None:
    assert can_transition(current, target) is advances_one_step_or_goes_back(current, target)


@pytest.mark.parametrize("stage", STAGES)
def test_staying_in_the_same_stage_is_rejected(stage: PipelineStage) -> None:
    assert not can_transition(stage, stage)


@pytest.mark.parametrize("status", CLOSED_STATUSES)
@pytest.mark.parametrize(("current", "target"), STAGE_PAIRS)
def test_closed_demands_cannot_change_stage(
    current: PipelineStage,
    target: PipelineStage,
    status: DemandStatus,
) -> None:
    assert not can_transition(current, target, status)


def test_unknown_domain_values_are_rejected() -> None:
    assert not can_transition("ETAPA_INEXISTENTE", PipelineStage.CAPTACAO)
    assert not can_transition(PipelineStage.CAPTACAO, "ETAPA_INEXISTENTE")
    assert not can_transition(
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        "STATUS_INEXISTENTE",
    )


def test_stage_without_declared_transitions_authorizes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Etapa nova no enum e ausente da tabela nao pode derrubar o chamador."""

    incomplete = {
        stage: targets
        for stage, targets in VALID_TRANSITIONS.items()
        if stage is not PipelineStage.PRODUTO
    }
    monkeypatch.setattr("app.domain.rules.VALID_TRANSITIONS", incomplete)

    assert not can_transition(PipelineStage.PRODUTO, PipelineStage.PROPOSTA)


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


def test_next_stage_rejects_unknown_stage() -> None:
    """Ao contrario de ``can_transition``, aqui valor invalido e erro, nao False."""

    with pytest.raises(ValueError):
        next_stage("ETAPA_INEXISTENTE")


@pytest.mark.parametrize("status", CLOSED_STATUSES)
def test_next_stage_ignores_status_and_does_not_authorize(status: DemandStatus) -> None:
    """``next_stage`` navega a ordem; a autorizacao continua em ``can_transition``."""

    assert next_stage(PipelineStage.CAPTACAO) is PipelineStage.ESTRUTURACAO
    assert not can_transition(PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO, status)
