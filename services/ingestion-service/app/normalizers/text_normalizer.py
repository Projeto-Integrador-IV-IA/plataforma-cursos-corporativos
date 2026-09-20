"""Sanitizacao conservadora de texto bruto para envio a IA (RF11 consolidado)."""

import html
import re
import unicodedata
from html.parser import HTMLParser

from app.domain.raw_demand import SourceKind

_EMAIL_HEADER = re.compile(
    r"^(?:from|de|sent|enviado em|date|data|to|para|cc|bcc|subject|assunto|reply-to):\s*",
    re.IGNORECASE,
)
_EMAIL_REPLY_MARKER = re.compile(
    r"^-{2,}\s*(?:original message|mensagem original|forwarded message|"
    r"mensagem encaminhada)\s*-{2,}$",
    re.IGNORECASE,
)
_EMAIL_WROTE_LINE = re.compile(r"^.+(?:escreveu|wrote):\s*$", re.IGNORECASE)
_SIGNATURE_START = re.compile(
    r"^(?:--\s*|atenciosamente[,.!]?|att[,.!]?|cordialmente[,.!]?|"
    r"grato(?:\(a\))?[,.!]?|obrigad[oa][,.!]?|best regards[,.!]?|regards[,.!]?)$",
    re.IGNORECASE,
)
_WHATSAPP_PREFIXES = (
    re.compile(
        r"^\[?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?[, ]+\d{1,2}:\d{2}"
        r"(?::\d{2})?\]?\s*(?:[-–—]\s*)?(?:[^:]{1,80}:\s*)?"
    ),
    re.compile(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*(?:[-–—]\s*)?(?:[^:]{1,80}:\s*)?"),
)
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]+)]\(([^)]+)\)")
_MARKDOWN_DECORATION = re.compile(r"(?<!\w)(?:\*\*|__|~~|`)(.+?)(?:\*\*|__|~~|`)(?!\w)")
_LINE_MARKER = re.compile(r"^\s*(?:>{1,3}\s*|#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)")
_ZERO_WIDTH = re.compile("[\u200b-\u200f\u2060\ufeff]")
_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
_BLANK_LINES = re.compile(r"\n{3,}")


class _TextExtractor(HTMLParser):
    """Extrai texto visivel e conserva separacao entre blocos HTML."""

    _BLOCK_TAGS = {"br", "div", "p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0
        self._links: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag == "a":
            self._links.append(next((value for key, value in attrs if key == "href"), None))
        elif tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "a" and self._links:
            if href := self._links.pop():
                self.parts.append(f" ({href})")
        elif tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def normalize_text(text: str, source_type: SourceKind) -> str:
    """Produz uma copia sanitizada sem modificar, resumir ou reescrever a entrada."""

    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = _ZERO_WIDTH.sub("", normalized).replace("\u00a0", " ")
    normalized = _strip_html(normalized)
    lines = normalized.splitlines()

    if source_type is SourceKind.EMAIL:
        lines = _remove_email_noise(lines)
    elif source_type is SourceKind.MENSAGENS:
        lines = [_remove_whatsapp_prefix(line) for line in lines]

    lines = [_strip_markup(line) for line in lines]
    normalized = "\n".join(line.rstrip() for line in lines)
    normalized = _HORIZONTAL_SPACE.sub(" ", normalized)
    normalized = _BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()


def _strip_html(text: str) -> str:
    if not re.search(r"<[a-zA-Z][^>]*>", text):
        return html.unescape(text)
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def _remove_email_noise(lines: list[str]) -> list[str]:
    """Remove metadados e assinatura, preservando corpos atual e encadeados."""

    result: list[str] = []
    in_leading_headers = True
    for line in lines:
        stripped = line.strip()
        if in_leading_headers and (_EMAIL_HEADER.match(stripped) or not stripped):
            continue
        in_leading_headers = False
        if _EMAIL_REPLY_MARKER.match(stripped) or _EMAIL_WROTE_LINE.match(stripped):
            in_leading_headers = True
            continue
        result.append(line)

    nonempty_indexes = [index for index, line in enumerate(result) if line.strip()]
    for index in reversed(nonempty_indexes[-10:]):
        if _SIGNATURE_START.match(result[index].strip()) and index > 0:
            return result[:index]
    return result


def _remove_whatsapp_prefix(line: str) -> str:
    for pattern in _WHATSAPP_PREFIXES:
        cleaned = pattern.sub("", line, count=1)
        if cleaned != line:
            return cleaned
    return line


def _strip_markup(line: str) -> str:
    line = _LINE_MARKER.sub("", line)
    line = _MARKDOWN_LINK.sub(lambda match: f"{match.group(1)} ({match.group(2)})", line)
    previous = None
    while previous != line:
        previous = line
        line = _MARKDOWN_DECORATION.sub(r"\1", line)
    return line
