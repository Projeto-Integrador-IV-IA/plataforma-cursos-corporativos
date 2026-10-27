"""Aceite da sanitizacao e da segmentacao estavel da fonte."""

from uuid import UUID, uuid4

from app.domain.raw_demand import SourceKind
from app.normalizers.text_normalizer import normalize_text, segment_text


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
        "Precisamos de um curso de liderança para 20 gestores.\n\nCarga horária desejada: 8 horas."
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


def test_segments_each_nonblank_logical_line_in_original_order() -> None:
    source_id = UUID("b46f05f7-2394-43a5-a864-38f62ce2e8f4")
    original = (
        "# Briefing\n\n- Tema: Seguranca de dados\n- Publico: gestores\n\n> Formato presencial"
    )

    segments = segment_text(original, SourceKind.ANOTACAO, source_id=source_id)

    assert [(segment.position, segment.text) for segment in segments] == [
        (1, "Briefing"),
        (2, "Tema: Seguranca de dados"),
        (3, "Publico: gestores"),
        (4, "Formato presencial"),
    ]
    assert all(segment.source_id == source_id for segment in segments)


def test_reprocessing_the_same_source_produces_the_same_segment_ids() -> None:
    source_id = UUID("57754d48-b635-45d3-8449-a531ec02268f")
    original = "Tema: LGPD\r\n\r\nPublico: gestores\r\nCarga horaria: 4 horas"

    first = segment_text(original, SourceKind.OUTRO, source_id=source_id)
    second = segment_text(original, SourceKind.OUTRO, source_id=source_id)

    assert [segment.id for segment in first] == [segment.id for segment in second]
    assert [str(segment.id) for segment in first] == [
        "4d6bbfc3-58db-5828-a4e3-e777774b10e8",
        "2cf6fe08-8db2-5194-afb1-7f9d85e855d0",
        "ce6a5f99-afbd-5311-95ec-923d6b350905",
    ]


def test_equal_text_from_different_sources_does_not_share_segment_ids() -> None:
    text = "Tema: LGPD\nPublico: gestores"

    first = segment_text(text, SourceKind.OUTRO, source_id=uuid4())
    second = segment_text(text, SourceKind.OUTRO, source_id=uuid4())

    assert [segment.id for segment in first] != [segment.id for segment in second]


def test_inserting_a_line_shifts_the_id_of_untouched_segments_below_it() -> None:
    """Documenta uma limitacao conhecida: a posicao entra no hash do trecho.

    Reprocessar a mesma fonte sem alteracoes preserva os IDs (ver teste acima),
    mas inserir uma linha no topo da fonte realinha a posicao de todos os
    trechos seguintes e, como a posicao compoe o UUIDv5, o identificador deles
    muda mesmo que o texto do trecho nao tenha sido alterado. Se os IDs forem
    usados como referencia persistente para citacoes, uma pequena edicao no
    inicio da fonte pode invalidar silenciosamente citacoes de trechos que nao
    mudaram.
    """
    source_id = uuid4()
    original = "Tema: LGPD\nPublico: gestores\nCarga horaria: 4 horas"
    edited = "Observacao adicionada\n" + original

    before = segment_text(original, SourceKind.OUTRO, source_id=source_id)
    after = segment_text(edited, SourceKind.OUTRO, source_id=source_id)

    unchanged_segment_after = next(s for s in after if s.text == "Tema: LGPD")
    unchanged_segment_before = next(s for s in before if s.text == "Tema: LGPD")

    assert unchanged_segment_after.id != unchanged_segment_before.id
