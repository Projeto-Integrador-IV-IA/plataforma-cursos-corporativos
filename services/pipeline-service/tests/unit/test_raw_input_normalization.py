"""Persistencia separada do conteudo normalizado (RF11 consolidado)."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.models import RawInput
from app.schemas.raw_input import RawInputNormalization
from app.services.raw_input_service import RawInputService


def test_normalization_updates_only_normalized_content() -> None:
    raw_input_id = uuid4()
    raw_input = RawInput(
        id=raw_input_id,
        demand_id=uuid4(),
        author_id=uuid4(),
        source="EMAIL",
        original_content="From: cliente@example.com\n\nConteudo original",
    )
    session = Mock()
    session.get.return_value = raw_input
    session.refresh.side_effect = lambda value: None

    result = RawInputService(session).normalize(
        raw_input_id,
        RawInputNormalization(normalized_content="Conteudo original"),
    )

    assert result.original_content == "From: cliente@example.com\n\nConteudo original"
    assert result.normalized_content == "Conteudo original"
    session.flush.assert_called_once_with()


def test_normalization_refuses_unknown_raw_input() -> None:
    session = Mock()
    session.get.return_value = None

    with pytest.raises(NotFoundError) as error:
        RawInputService(session).normalize(
            uuid4(),
            RawInputNormalization(normalized_content="Texto"),
        )

    assert error.value.code == "RAW_INPUT_NOT_FOUND"
