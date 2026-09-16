"""Persistencia de demandas, sem encerrar a transacao da requisicao (RF02)."""

from sqlalchemy.orm import Session

from app.models.demand import Demand


class DemandRepository:
    """Isola a escrita e recupera os valores gerados pelo banco."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, demand: Demand) -> Demand:
        """Insere e valida as restricoes antes de produzir a resposta HTTP."""

        self.session.add(demand)
        self.session.flush()
        self.session.refresh(demand)
        return demand
