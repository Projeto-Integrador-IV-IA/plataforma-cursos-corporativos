"""Log estruturado e registro de execucao recuperavel (RNF08.1).

O que estes testes protegem: todo registro emitido vira uma linha JSON com a
forma basica do contrato (``timestamp``, ``nivel``, ``servico``, ``mensagem``),
um registro que carrega ``execution_id`` fica recuperavel por
``consultar_registros_de_execucao`` e um que nao carrega simplesmente nao
aparece ali - sem erro, sem excecao. ``configure_logging`` e idempotente: a
suite inteira chama ``create_app()`` (e portanto esta funcao) repetidas vezes
no mesmo processo, e isso nunca pode duplicar handler no logger raiz.
"""

import json
import logging

from app.core.logging import (
    ExecutionLogHandler,
    JsonFormatter,
    configure_logging,
    consultar_registros_de_execucao,
    get_logger,
)


def _registro(
    *,
    msg: str = "mensagem de teste",
    level: int = logging.INFO,
    extra: dict[str, object] | None = None,
    exc_info: tuple | None = None,
) -> logging.LogRecord:
    """Monta um ``LogRecord`` isolado, sem depender de um logger configurado."""

    registro = logging.LogRecord(
        name="app.teste",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )
    for chave, valor in (extra or {}).items():
        setattr(registro, chave, valor)
    return registro


# ----------------------------------------------------------------------
# JsonFormatter: forma basica do contrato
# ----------------------------------------------------------------------


def test_formatter_produz_json_valido_com_as_chaves_base() -> None:
    linha = JsonFormatter().format(_registro(msg="ola"))

    corpo = json.loads(linha)
    assert corpo["nivel"] == "INFO"
    assert corpo["servico"] == "ai-structuring-service"
    assert corpo["mensagem"] == "ola"
    assert "timestamp" in corpo


def test_formatter_inclui_request_id_demand_id_e_duration_ms_quando_presentes() -> None:
    linha = JsonFormatter().format(
        _registro(extra={"request_id": "req-1", "demand_id": "dem-1", "duration_ms": 12.5})
    )

    corpo = json.loads(linha)
    assert corpo["request_id"] == "req-1"
    assert corpo["demand_id"] == "dem-1"
    assert corpo["duration_ms"] == 12.5


def test_formatter_omite_request_id_quando_ausente() -> None:
    linha = JsonFormatter().format(_registro())

    corpo = json.loads(linha)
    assert "request_id" not in corpo
    assert "demand_id" not in corpo
    assert "duration_ms" not in corpo


def test_formatter_mescla_campos_extras_quaisquer() -> None:
    linha = JsonFormatter().format(_registro(extra={"execution_id": "exec-1", "tentativas": 2}))

    corpo = json.loads(linha)
    assert corpo["execution_id"] == "exec-1"
    assert corpo["tentativas"] == 2


def test_formatter_inclui_exc_info_formatado_quando_presente() -> None:
    try:
        raise ValueError("falha de teste")
    except ValueError:
        import sys

        linha = JsonFormatter().format(_registro(exc_info=sys.exc_info()))

    corpo = json.loads(linha)
    assert "ValueError" in corpo["exc_info"]
    assert "falha de teste" in corpo["exc_info"]


# ----------------------------------------------------------------------
# ExecutionLogHandler: recuperavel por identificador
# ----------------------------------------------------------------------


def test_registro_com_execution_id_fica_recuperavel() -> None:
    handler = ExecutionLogHandler()

    handler.emit(_registro(msg="chamada concluida", extra={"execution_id": "exec-42"}))

    (registro,) = handler.registros("exec-42")
    assert registro["mensagem"] == "chamada concluida"


def test_registro_sem_execution_id_nao_fica_recuperavel() -> None:
    handler = ExecutionLogHandler()

    handler.emit(_registro(msg="sem identificador"))

    assert handler.registros("qualquer-id") == ()


def test_identificador_desconhecido_devolve_tupla_vazia_sem_levantar() -> None:
    handler = ExecutionLogHandler()

    assert handler.registros("nunca-existiu") == ()


def test_execution_id_aceita_uuid_e_string_equivalentes() -> None:
    from uuid import uuid4

    handler = ExecutionLogHandler()
    identificador = uuid4()

    handler.emit(_registro(extra={"execution_id": identificador}))

    assert handler.registros(identificador) == handler.registros(str(identificador))
    assert len(handler.registros(identificador)) == 1


def test_falha_ao_formatar_nao_propaga_excecao() -> None:
    """Registro que nao formata (ex.: args insuficientes) nao derruba o handler."""

    handler = ExecutionLogHandler()
    registro = logging.LogRecord(
        name="app.teste",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="%s e %s",
        args=("so um",),
        exc_info=None,
    )
    registro.execution_id = "exec-quebrado"

    handler.emit(registro)  # nao deve levantar

    assert handler.registros("exec-quebrado") == ()


# ----------------------------------------------------------------------
# configure_logging: idempotente
# ----------------------------------------------------------------------


def test_configure_logging_duas_vezes_nao_duplica_handler() -> None:
    configure_logging("INFO")
    quantidade_apos_primeira = len(logging.getLogger().handlers)

    configure_logging("INFO")

    assert len(logging.getLogger().handlers) == quantidade_apos_primeira


def test_configure_logging_aplica_o_nivel_informado() -> None:
    configure_logging("DEBUG")

    assert logging.getLogger().level == logging.DEBUG

    configure_logging("INFO")  # devolve ao nivel padrao dos demais testes


# ----------------------------------------------------------------------
# get_logger / consultar_registros_de_execucao: API publica
# ----------------------------------------------------------------------


def test_get_logger_devolve_logging_logger() -> None:
    logger = get_logger("app.teste.alguma_coisa")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.teste.alguma_coisa"


def test_consultar_registros_de_execucao_recupera_registro_emitido_pelo_logger() -> None:
    from uuid import uuid4

    configure_logging("INFO")
    identificador = uuid4()
    logger = get_logger("app.teste.consulta")

    logger.info("chamada registrada", extra={"execution_id": identificador, "tokens": 10})

    (registro,) = consultar_registros_de_execucao(identificador)
    assert registro["tokens"] == 10
    assert registro["execution_id"] == str(identificador)


def test_consultar_registros_de_execucao_para_id_desconhecido_e_vazio() -> None:
    assert consultar_registros_de_execucao("nunca-logado-antes") == ()
