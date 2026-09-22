"""Validacoes de parametros de consulta compartilhadas entre rotas da v1.

Vive fora dos modulos de rota porque mais de um caminho aceita o mesmo filtro:
a listagem de demandas (RF03) e a visao de pipeline (RF05) precisam recusar um
periodo incoerente da mesma forma, e duplicar a regra faria as duas divergirem
em silencio.
"""

from datetime import datetime

from app.core.exceptions import ValidationError, issue_de_validacao


def validate_period(created_from: datetime | None, created_to: datetime | None) -> None:
    """Exige fuso e uma faixa cronologica coerente para o filtro de periodo.

    Levanta ``ValidationError`` para que a resposta saia pelo mesmo handler do
    restante do servico, com o ``details.issues`` de sempre (RNF02).
    """

    issues: list[dict[str, object]] = []
    if created_from is not None and created_from.utcoffset() is None:
        issues.append(
            issue_de_validacao(
                localizacao=["query", "from"],
                mensagem="A data inicial deve informar o fuso horario.",
                tipo="value_error.timezone",
            )
        )
    if created_to is not None and created_to.utcoffset() is None:
        issues.append(
            issue_de_validacao(
                localizacao=["query", "to"],
                mensagem="A data final deve informar o fuso horario.",
                tipo="value_error.timezone",
            )
        )
    if (
        not issues
        and created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        issues.append(
            issue_de_validacao(
                localizacao=["query", "to"],
                mensagem="A data final deve ser maior ou igual a data inicial.",
                tipo="value_error.period",
            )
        )

    if issues:
        raise ValidationError(
            code="VALIDATION_ERROR",
            message="Os dados informados sao invalidos.",
            details={"issues": issues},
        )
