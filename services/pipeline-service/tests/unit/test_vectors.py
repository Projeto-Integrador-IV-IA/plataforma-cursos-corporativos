"""Similaridade de cosseno: casos de borda isolados da camada HTTP (card #159)."""

import pytest

from app.domain.vectors import cosseno


def test_identical_vectors_have_similarity_one() -> None:
    assert cosseno([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_zero() -> None:
    assert cosseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_opposite_vectors_have_similarity_minus_one() -> None:
    assert cosseno([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_magnitude_does_not_affect_similarity() -> None:
    assert cosseno([1.0, 0.0], [5.0, 0.0]) == pytest.approx(1.0)


def test_zero_vector_returns_zero_instead_of_dividing_by_zero() -> None:
    assert cosseno([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosseno([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_different_dimensions_raise_value_error() -> None:
    with pytest.raises(ValueError, match="dimensoes diferentes"):
        cosseno([1.0, 2.0], [1.0, 2.0, 3.0])
