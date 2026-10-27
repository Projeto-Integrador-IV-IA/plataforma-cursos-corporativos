"""Deteccao heuristica da origem do texto (apoio ao RF10).

O operador pode declarar a origem; esta camada sugere, quando ela nao e
informada, com base em marcas evidentes do texto (cabecalhos de e-mail,
carimbos de tempo de transcricao e mensagens exportadas com data e autor).

A sugestao nunca sobrescreve a declaracao do operador.
"""

import re

from app.domain.raw_demand import SourceKind

_EMAIL_HEADERS = re.compile(
    r"^\s*(from|de|to|para|subject|assunto|sent|enviado em|date|data):\s*\S",
    re.IGNORECASE | re.MULTILINE,
)
_MESSAGE = re.compile(
    r"^\s*\[?\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+"
    r"\d{1,2}:\d{2}(?::\d{2})?\]?\s*(?:[-\u2013\u2014]\s*)?[^:\n]{1,80}:\s*\S",
    re.MULTILINE,
)
_TRANSCRIPT = re.compile(
    r"^\s*(?:WEBVTT\s*$|"
    r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,.]\d{3}|"
    r"\[?\d{1,2}:\d{2}:\d{2}\]?\s+(?:[-\u2013\u2014]\s*)?[^:\n]{1,80}:\s*\S)",
    re.IGNORECASE | re.MULTILINE,
)
_NOTES = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:anota[cç][oõ]es|notas de reuni[aã]o|meeting notes)\s*(?::|$)",
    re.IGNORECASE | re.MULTILINE,
)


def detect_source_type(text: str) -> SourceKind:
    """Sugere o canal a partir de marcas explicitas, sem alterar o original.

    Cabecalhos de e-mail prevalecem sobre trechos citados de outros canais.
    Um unico rotulo (por exemplo, 'Assunto:') nao basta para reconhecer e-mail.
    Sem marcas suficientes, retorna OUTRO; a escolha do operador e feita pelo
    chamador e sempre tem prioridade sobre esta heuristica.
    """

    headers = {match.casefold() for match in _EMAIL_HEADERS.findall(text)}
    if headers & {"from", "de", "to", "para"} and headers & {
        "subject",
        "assunto",
        "sent",
        "enviado em",
        "date",
        "data",
    }:
        return SourceKind.EMAIL
    if _TRANSCRIPT.search(text):
        return SourceKind.TRANSCRICAO
    if _MESSAGE.search(text):
        return SourceKind.MENSAGENS
    if _NOTES.search(text):
        return SourceKind.ANOTACAO
    return SourceKind.OUTRO
