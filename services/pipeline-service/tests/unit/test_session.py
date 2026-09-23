"""Testes do ciclo transacional da dependencia de sessao."""

import pytest

from app.db import session as session_module


class FakeSession:
    """Sessao minima para observar o encerramento da transacao."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def use_fake_session(
    monkeypatch: pytest.MonkeyPatch,
    fake_session: FakeSession,
) -> None:
    def factory() -> FakeSession:
        return fake_session

    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)


def test_get_session_commits_and_closes_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    use_fake_session(monkeypatch, fake_session)

    dependency = session_module.get_session()
    assert next(dependency) is fake_session
    with pytest.raises(StopIteration):
        next(dependency)

    assert (fake_session.commits, fake_session.rollbacks, fake_session.closes) == (1, 0, 1)


def test_get_session_rolls_back_and_closes_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    use_fake_session(monkeypatch, fake_session)

    dependency = session_module.get_session()
    assert next(dependency) is fake_session
    with pytest.raises(RuntimeError, match="falha"):
        dependency.throw(RuntimeError("falha"))

    assert (fake_session.commits, fake_session.rollbacks, fake_session.closes) == (0, 1, 1)
