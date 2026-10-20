"""Regras da maquina de estados do pipeline (RF05, RF06).

A tabela ``VALID_TRANSITIONS`` e conferida contra a regra escrita em palavras,
nao contra si mesma: avanco so para a etapa seguinte, retrocesso para qualquer
etapa anterior, nada para demanda encerrada.
"""

from itertools import product

import pytest

from app.core.exceptions import ConflictError, InvalidTransitionError
from app.domain.enums import DemandStatus, PipelineStage
from app.domain.rules import (
    advance_target,
    available_transitions,
    can_transition,
    next_stage,
    validate_transition,
)

STAGES = tuple(PipelineStage)
CLOSED = [status for status in DemandStatus if status is not DemandStatus.ABERTA]
REFUSAL_CODES = {
    "DEMAND_NOT_OPEN",
    "DEMAND_AT_FINAL_STAGE",
    "STAGE_UNCHANGED",
    "INVALID_STAGE_TRANSITION",
}


def _rule(current: PipelineStage, target: PipelineStage) -> bool:
    """A regra em palavras: proxima etapa ou qualquer etapa anterior."""

    origin, destination = STAGES.index(current), STAGES.index(target)
    return destination == origin + 1 or destination < origin


def _refusal(*args: object) -> InvalidTransitionError:
    with pytest.raises(InvalidTransitionError) as raised:
        validate_transition(*args)  # type: ignore[arg-type]
    return raised.value


@pytest.mark.parametrize(("current", "target"), list(product(STAGES, STAGES)))
def test_open_demand_follows_the_written_rule(
    current: PipelineStage, target: PipelineStage
) -> None:
    assert can_transition(current, target) is _rule(current, target)


@pytest.mark.parametrize("status", CLOSED)
@pytest.mark.parametrize(("current", "target"), list(product(STAGES, STAGES)))
def test_closed_demand_never_changes_stage(
    current: PipelineStage, target: PipelineStage, status: DemandStatus
) -> None:
    assert can_transition(current, target, status) is False


def test_unknown_values_are_refused_without_raising_in_the_predicate() -> None:
    assert can_transition("XPTO", PipelineStage.CAPTACAO) is False
    assert can_transition(PipelineStage.CAPTACAO, "XPTO") is False
    assert can_transition(PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO, "XPTO") is False


def test_plain_strings_are_accepted() -> None:
    assert can_transition("CAPTACAO", "ESTRUTURACAO", "ABERTA") is True


def test_next_stage_walks_the_order_and_stops_at_the_end() -> None:
    assert [next_stage(stage) for stage in STAGES] == [*STAGES[1:], None]


def test_next_stage_rejects_unknown_stage() -> None:
    with pytest.raises(ValueError):
        next_stage("XPTO")


# --- available_transitions ---------------------------------------------------


def test_available_transitions_from_the_first_stage() -> None:
    assert available_transitions(PipelineStage.CAPTACAO) == (PipelineStage.ESTRUTURACAO,)


def test_available_transitions_from_the_last_stage_can_only_go_back() -> None:
    assert available_transitions(PipelineStage.ACOMPANHAMENTO) == (
        PipelineStage.CAPTACAO,
        PipelineStage.ESTRUTURACAO,
        PipelineStage.PRODUTO,
        PipelineStage.PROPOSTA,
    )


@pytest.mark.parametrize("current", STAGES)
def test_available_transitions_agree_with_can_transition(current: PipelineStage) -> None:
    available = available_transitions(current)

    assert current not in available
    assert list(available) == sorted(available, key=STAGES.index)
    assert set(available) == {stage for stage in STAGES if can_transition(current, stage)}


@pytest.mark.parametrize("status", CLOSED)
def test_closed_demand_has_no_available_transitions(status: DemandStatus) -> None:
    assert all(available_transitions(stage, status) == () for stage in STAGES)


def test_available_transitions_of_unknown_values_is_empty() -> None:
    assert available_transitions("XPTO") == ()
    assert available_transitions(PipelineStage.CAPTACAO, "XPTO") == ()


# --- validate_transition -----------------------------------------------------


@pytest.mark.parametrize("status", list(DemandStatus))
@pytest.mark.parametrize(("current", "target"), list(product(STAGES, STAGES)))
def test_validate_transition_refuses_exactly_when_the_predicate_does(
    current: PipelineStage, target: PipelineStage, status: DemandStatus
) -> None:
    if can_transition(current, target, status):
        assert validate_transition(current, target, status) is None
        return

    error = _refusal(current, target, status)

    assert isinstance(error, ConflictError)
    assert error.status_code == 409
    assert error.code in REFUSAL_CODES
    assert error.message
    assert error.details["current_stage"] == current.value
    assert error.details["target_stage"] == target.value


def test_skipping_a_stage_is_refused_and_names_the_next_one() -> None:
    error = _refusal(PipelineStage.CAPTACAO, PipelineStage.PRODUTO)

    assert error.code == "INVALID_STAGE_TRANSITION"
    assert "CAPTACAO" in error.message
    assert "PRODUTO" in error.message
    assert "sequencial" in error.message
    assert PipelineStage.ESTRUTURACAO.value in error.message
    assert error.details["allowed_stages"] == [PipelineStage.ESTRUTURACAO.value]


def test_staying_in_the_same_stage_is_refused_with_its_own_reason() -> None:
    error = _refusal(PipelineStage.PRODUTO, PipelineStage.PRODUTO)

    assert error.code == "STAGE_UNCHANGED"
    assert "PRODUTO" in error.message


@pytest.mark.parametrize("status", CLOSED)
def test_closed_demand_is_refused_with_its_own_reason(status: DemandStatus) -> None:
    error = _refusal(PipelineStage.CAPTACAO, PipelineStage.ESTRUTURACAO, status)

    assert error.code == "DEMAND_NOT_OPEN"
    assert error.details["status"] == status.value
    assert error.details["allowed_stages"] == []


def test_closed_demand_takes_precedence_over_the_same_stage() -> None:
    error = _refusal(PipelineStage.PRODUTO, PipelineStage.PRODUTO, DemandStatus.GANHA)

    assert error.code == "DEMAND_NOT_OPEN"


def test_unknown_values_are_refused_with_a_typed_error_not_a_value_error() -> None:
    error = _refusal("XPTO", PipelineStage.CAPTACAO)

    assert error.code == "INVALID_STAGE_TRANSITION"
    assert error.details["current_stage"] == "XPTO"


# --- advance_target ----------------------------------------------------------


@pytest.mark.parametrize(("current", "expected"), list(zip(STAGES, STAGES[1:], strict=False)))
def test_advance_target_is_the_next_stage(current: PipelineStage, expected: PipelineStage) -> None:
    assert advance_target(current) is expected


def test_advance_from_the_last_stage_is_refused_with_the_stage_in_the_message() -> None:
    with pytest.raises(InvalidTransitionError) as raised:
        advance_target(PipelineStage.ACOMPANHAMENTO)

    assert raised.value.code == "DEMAND_AT_FINAL_STAGE"
    assert PipelineStage.ACOMPANHAMENTO.value in raised.value.message
    assert raised.value.details == {"current_stage": PipelineStage.ACOMPANHAMENTO.value}


def test_final_stage_is_reported_before_the_demand_status() -> None:
    with pytest.raises(InvalidTransitionError) as raised:
        advance_target(PipelineStage.ACOMPANHAMENTO, DemandStatus.GANHA)

    assert raised.value.code == "DEMAND_AT_FINAL_STAGE"


def test_advance_of_a_closed_demand_is_refused() -> None:
    with pytest.raises(InvalidTransitionError) as raised:
        advance_target(PipelineStage.CAPTACAO, DemandStatus.PERDIDA)

    assert raised.value.code == "DEMAND_NOT_OPEN"
    assert raised.value.message == "Demandas encerradas nao mudam de etapa."


def test_advance_with_an_unknown_stage_is_a_programming_error() -> None:
    with pytest.raises(ValueError):
        advance_target("XPTO")
