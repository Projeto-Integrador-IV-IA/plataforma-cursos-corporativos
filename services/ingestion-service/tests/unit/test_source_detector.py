"""RF10: inferencia conservadora pelo formato, sem editar a fonte."""

import pytest

from app.domain.raw_demand import SourceKind
from app.normalizers.source_detector import detect_source_type


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "De: marina@example.com\nAssunto: Treinamento\n\nPrecisamos de 20 vagas.",
            SourceKind.EMAIL,
        ),
        ("FROM: Marina\r\nDATE: 18 Oct 2026\r\nCorpo", SourceKind.EMAIL),
        ("Para: equipe@example.com\nEnviado em: domingo\nCorpo", SourceKind.EMAIL),
        ("[18/10/2026, 10:30:05] Marina: Precisamos de 20 vagas.", SourceKind.MENSAGENS),
        ("18/10/26 10:30 - Marina: Ola!\n18/10/26 10:31 - Joao: Ola!", SourceKind.MENSAGENS),
        ("18-10-2026, 10:30 - Marina: Ola!", SourceKind.MENSAGENS),
        ("[00:01:23] Marina: O objetivo e capacitar a equipe.", SourceKind.TRANSCRICAO),
        ("00:01:23 Joao: Vamos revisar o escopo.", SourceKind.TRANSCRICAO),
        ("1\n00:00:01,000 --> 00:00:03,000\nBom dia", SourceKind.TRANSCRICAO),
        ("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nBom dia", SourceKind.TRANSCRICAO),
        ("Anotações:\nTreinar a equipe de operacoes.", SourceKind.ANOTACAO),
        ("# Meeting notes\nRevisar o programa.", SourceKind.ANOTACAO),
        ("Texto livre sem marcas do canal.", SourceKind.OUTRO),
        ("Assunto: plano de treinamento", SourceKind.OUTRO),
        ("De: lideranca", SourceKind.OUTRO),
        ("O curso inicia em 18/10/2026 as 10:30.", SourceKind.OUTRO),
        ("O exemplo usa [00:01:23] para marcar o tempo.", SourceKind.OUTRO),
        ("", SourceKind.OUTRO),
    ],
)
def test_explicit_markers_identify_the_source(text: str, expected: SourceKind) -> None:
    assert detect_source_type(text) is expected


def test_email_headers_take_precedence_over_a_quoted_chat() -> None:
    text = "From: marina@example.com\nSubject: Encaminhamento\n\n18/10/26 10:30 - Marina: Ola!"
    assert detect_source_type(text) is SourceKind.EMAIL
