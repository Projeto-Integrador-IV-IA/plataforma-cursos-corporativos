"""Captacao que persiste o bruto antes de qualquer etapa posterior (RF09, RF10)."""

import logging
from uuid import UUID

from app.clients.pipeline_client import PipelineClient
from app.core.exceptions import UpstreamError
from app.domain.raw_demand import PersistedRawDemand, RawDemand
from app.normalizers.text_normalizer import normalize_text

_logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, pipeline_client: PipelineClient) -> None:
        self.pipeline_client = pipeline_client

    def capture(
        self,
        raw_demand: RawDemand,
        *,
        author_id: UUID,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        """Persiste o original, sanitiza uma copia e grava o resultado separadamente.

        A ordem nao e detalhe de implementacao: o original e confirmado primeiro,
        e so entao a copia sanitizada e derivada dele (RF09, RNF05).

        Falha ao gravar a sanitizacao **nao derruba a captacao**. O texto que o
        operador colou ja esta salvo, e e ele que o requisito manda preservar;
        anunciar erro aqui faria o operador colar tudo de novo e duplicar a
        fonte. A demanda fica com ``normalized_content`` nulo, que e exatamente
        o estado que o reprocessamento sabe reconhecer.
        """

        persisted = self.pipeline_client.persist_raw_demand(
            raw_demand,
            author_id=author_id,
            request_id=request_id,
        )
        normalized_content = normalize_text(raw_demand.text, raw_demand.source_type)
        try:
            self.pipeline_client.persist_normalization(
                persisted.raw_input_id,
                normalized_content,
                request_id=request_id,
            )
        except UpstreamError as erro:
            _registrar_sanitizacao_nao_gravada(persisted, erro, request_id=request_id)
        return persisted


def _registrar_sanitizacao_nao_gravada(
    persisted: PersistedRawDemand,
    erro: UpstreamError,
    *,
    request_id: str | None,
) -> None:
    """Alerta sem vazar conteudo do cliente para o log (RNF10, RNF11).

    Identificadores bastam para o reprocessamento achar o registro; o texto
    captado nunca entra na mensagem.
    """

    _logger.warning(
        "Sanitizacao nao gravada; o texto original esta preservado "
        "(raw_input_id=%s, demand_id=%s, request_id=%s, causa=%s, status=%d).",
        persisted.raw_input_id,
        persisted.demand_id,
        request_id or "nao informado",
        erro.code,
        erro.status_code,
    )
