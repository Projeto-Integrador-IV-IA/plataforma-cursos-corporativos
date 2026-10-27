"""Guarda generica contra UPDATE e DELETE pelo ORM em tabelas append-only (RNF09).

A garantia tem duas camadas, e esta e so uma delas. No banco, o gatilho da
migration recusa qualquer UPDATE ou DELETE, inclusive os em massa que o ORM
nao intercepta - essa e a garantia que realmente protege os dados. Aqui, o
evento do SQLAlchemy recusa a mesma operacao antes de chegar ao banco, com um
erro tipado que a aplicacao pode tratar sem depender do texto da excecao do
driver.

``forbid_changes`` existe para as tabelas append-only do servico nao
repetirem o mesmo par de ``event.listens_for`` cada uma com seu proprio
texto de erro.
"""

from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper


class AppendOnlyViolationError(RuntimeError):
    """Tentativa de alterar ou apagar um evento de uma tabela append-only (RNF09)."""


def forbid_changes(model: type[Any], table_name: str) -> None:
    """Registra os eventos que recusam UPDATE e DELETE de ``model`` pelo ORM.

    Chamar uma unica vez, logo depois da definicao da classe do modelo.
    """

    @event.listens_for(model, "before_update")
    @event.listens_for(model, "before_delete")
    def _refuse_change(mapper: Mapper[Any], connection: Connection, target: Any) -> None:
        raise AppendOnlyViolationError(
            f"{table_name} e append-only: eventos nao podem ser alterados nem apagados."
        )
