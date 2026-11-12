"""Configuracao de log estruturado.

Todos os microsservicos emitem log em formato consistente para que o fluxo de
uma demanda possa ser reconstruido de ponta a ponta entre servicos - insumo
direto da trilha de auditoria (RNF09) e do diagnostico de falhas do LLM (RNF05).

Contrato esperado desta camada:
    - saida em JSON com: timestamp, nivel, servico, mensagem, ``request_id``,
      ``demand_id`` (quando houver) e duracao em milissegundos;
    - ``request_id`` propagado entre servicos pelo header ``X-Request-ID``;
    - nivel controlado por ``LOG_LEVEL``;
    - nenhum dado sensivel de cliente ou chave de API no log (RNF10, RNF11).

Este modulo acrescenta o que o card RNF08.1 pede: toda chamada ao provedor de
LLM precisa de um registro recuperavel pelo identificador da execucao
(``execution_id``). ``ExecutionLogHandler`` guarda em memoria, por processo, a
lista de registros de cada execucao - a mesma escolha de ``job_service.py``
para o registro de execucoes (RF17): reiniciar o processo perde o historico,
e com mais de uma replica o identificador so e encontrado na que processou.
Nenhuma das duas limitacoes e resolvida aqui.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

#: Nome fixo do servico, repetido em todo registro para correlacionar entre
#: microsservicos (RNF09).
SERVICO: str = "ai-structuring-service"

#: Atributos nativos de ``logging.LogRecord``. Qualquer outra chave presente
#: em ``record.__dict__`` veio de ``extra=`` do chamador e entra no JSON.
_ATRIBUTOS_PADRAO_DO_LOGRECORD: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Formata cada ``LogRecord`` como uma linha JSON.

    Sempre inclui ``timestamp`` (ISO 8601, UTC), ``nivel``, ``servico`` e
    ``mensagem``. Em seguida, ``request_id``, ``demand_id`` e ``duration_ms``
    quando presentes como ``extra=`` do chamador, e por fim qualquer outro
    campo extra - o mesmo formatador serve tanto o log de requisicao quanto o
    log por chamada de LLM (RNF08.1).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "nivel": record.levelname,
            "servico": SERVICO,
            "mensagem": record.getMessage(),
        }

        for campo in ("request_id", "demand_id", "duration_ms"):
            valor = record.__dict__.get(campo)
            if valor is not None:
                payload[campo] = valor

        for chave, valor in record.__dict__.items():
            if chave in _ATRIBUTOS_PADRAO_DO_LOGRECORD or chave in payload:
                continue
            payload[chave] = valor

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


class ExecutionLogHandler(logging.Handler):
    """Guarda, por identificador de execucao, os registros de log emitidos.

    So guarda o registro quando o ``LogRecord`` carrega um ``execution_id``
    em ``extra=``; sem ele, o registro segue para os demais handlers (ex.: o
    ``StreamHandler`` de saida padrao) e simplesmente nao fica recuperavel por
    identificador. Sem teto nem descarte do mais antigo - mesma escolha de
    ``job_service.py`` para o registro de execucoes deste MVP.
    """

    def __init__(self) -> None:
        super().__init__()
        # Formatador padrao para quem usa esta classe isoladamente (ex.: em
        # teste unitario) sem passar por ``configure_logging``.
        self.setFormatter(JsonFormatter())
        self._registros: dict[str, list[dict[str, Any]]] = {}

    def emit(self, record: logging.LogRecord) -> None:
        execution_id = record.__dict__.get("execution_id")
        if execution_id is None:
            return
        try:
            registro = json.loads(self.format(record))
        except Exception:
            self.handleError(record)
            return
        self._registros.setdefault(str(execution_id), []).append(registro)

    def registros(self, execution_id: UUID | str) -> tuple[dict[str, Any], ...]:
        """Devolve os registros da execucao, ou tupla vazia se desconhecida."""

        return tuple(self._registros.get(str(execution_id), ()))


#: Handlers unicos do processo. Modulo-nivel para que ``configure_logging``
#: seja idempotente: chamar duas vezes nao duplica handler no logger raiz.
_stream_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
_execution_log_handler: ExecutionLogHandler = ExecutionLogHandler()


def configure_logging(level: str = "INFO") -> None:
    """Liga o log estruturado em JSON no logger raiz (RNF08.1).

    Idempotente: pode ser chamada mais de uma vez (reimportacao do pytest,
    mais de uma instancia da aplicacao no mesmo processo) sem duplicar
    handler - cada handler e um singleton deste modulo, adicionado apenas se
    ainda nao estiver no logger raiz.
    """

    raiz = logging.getLogger()
    raiz.setLevel(level)

    formatador = JsonFormatter()
    _stream_handler.setFormatter(formatador)
    _execution_log_handler.setFormatter(formatador)

    if _stream_handler not in raiz.handlers:
        raiz.addHandler(_stream_handler)
    if _execution_log_handler not in raiz.handlers:
        raiz.addHandler(_execution_log_handler)


def get_logger(name: str) -> logging.Logger:
    """Devolve o logger do modulo, sem configuracao propria (RNF08.1)."""

    return logging.getLogger(name)


def consultar_registros_de_execucao(execution_id: UUID | str) -> tuple[dict[str, Any], ...]:
    """Devolve os registros de log da execucao, pelo identificador (RNF08.1).

    Nunca levanta excecao: identificador desconhecido devolve tupla vazia.
    """

    return _execution_log_handler.registros(execution_id)
