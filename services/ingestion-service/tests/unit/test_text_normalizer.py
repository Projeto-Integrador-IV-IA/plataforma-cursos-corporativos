"""Aceite da sanitizacao sem reescrita do conteudo semantico."""

from app.domain.raw_demand import SourceKind
from app.normalizers.text_normalizer import normalize_text


def test_removes_email_headers_signature_html_and_redundant_spacing() -> None:
    original = (
        "From: cliente@example.com\r\n"
        "Sent: domingo, 20 de setembro de 2026 09:30\r\n"
        "To: comercial@example.com\r\n"
        "Subject: Curso de lideranca\r\n\r\n"
        "<p>Precisamos de um curso de <strong>liderança</strong> para 20 gestores.</p>\r\n"
        "<p>Carga horária desejada: 8 horas.</p>\r\n\r\n\r\n"
        "Atenciosamente,\r\nMaria Silva\r\nGerente de RH\r\n(11) 99999-9999"
    )

    result = normalize_text(original, SourceKind.EMAIL)

    assert result == (
        "Precisamos de um curso de liderança para 20 gestores.\n\n"
        "Carga horária desejada: 8 horas."
    )
    assert original.startswith("From: cliente@example.com\r\n")


def test_removes_whatsapp_metadata_but_preserves_every_message() -> None:
    original = (
        "[20/09/2026 10:31] Ana: Precisamos treinar a equipe comercial.\n"
        "20/09/2026, 10:32 - Bruno: O público será de 35 vendedores.\n"
        "[10:33] Ana: Formato presencial, em São Paulo."
    )

    result = normalize_text(original, SourceKind.MENSAGENS)

    assert result.splitlines() == [
        "Precisamos treinar a equipe comercial.",
        "O público será de 35 vendedores.",
        "Formato presencial, em São Paulo.",
    ]


def test_removes_markup_without_summarizing_or_losing_link_destination() -> None:
    original = (
        "# Briefing\n"
        "- **Tema:** Segurança de dados\n"
        "- Material: [política interna](https://example.com/politica)\n"
        "> Não remover esta observação do cliente."
    )

    result = normalize_text(original, SourceKind.ANOTACAO)

    assert result == (
        "Briefing\n"
        "Tema: Segurança de dados\n"
        "Material: política interna (https://example.com/politica)\n"
        "Não remover esta observação do cliente."
    )


def test_keeps_plain_semantic_content_unchanged() -> None:
    original = "Tema: LGPD\nPúblico: gestores\nCarga horária: 4 horas"

    assert normalize_text(original, SourceKind.OUTRO) == original
