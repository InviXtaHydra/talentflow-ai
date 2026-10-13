"""Text extraction from PDF and DOCX. Documents are treated as data only: no macros, scripts, links or
embedded objects are executed or followed."""

import io
import itertools
import logging
import re

from docx import Document as DocxDocument
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.utils.files import DOCX_MIME, PDF_MIME
from app.utils.text import clean_extracted_text

logger = logging.getLogger("talentflow.cv")

MAX_PAGES = 15
# Below this many characters of text per page, a PDF is most likely a scan (images only).
MIN_CHARS_PER_PAGE = 80


class ExtractionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _positioned_text(page) -> str:
    """Text rebuilt from the position of each fragment: fragments on the same visual row are joined.

    Multi-column CVs often store their text out of reading order (e.g. all dates first, then all job titles),
    which makes a model pair the wrong dates with the wrong jobs. Rows keep "Sep 2024 - May 2025   Developer" together."""
    items: list[tuple[float, float, str]] = []

    def visit(text: str, cm: list[float], tm: list[float], font: object, size: float) -> None:
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            items.append((y, x, " ".join(text.split())))

    page.extract_text(visitor_text=visit)
    if not items:
        return ""
    # Reading direction: text mostly flows downwards, so the dominant direction of y between consecutive
    # fragments in the content stream tells whether y grows up (normal PDF) or down (flipped coordinates).
    steps = [b[0] - a[0] for a, b in itertools.pairwise(items) if abs(b[0] - a[0]) > 2]
    downward_is_negative = sum(1 for d in steps if d < 0) >= sum(1 for d in steps if d > 0)
    items.sort(key=lambda i: ((-i[0] if downward_is_negative else i[0]), i[1]))
    lines: list[list[tuple[float, str]]] = []
    current_y: float | None = None
    for y, x, text in items:
        if current_y is None or abs(y - current_y) > 3:
            lines.append([])
            current_y = y
        lines[-1].append((x, text))
    return "\n".join("   ".join(t for _, t in sorted(line)) for line in lines)


def extract_pdf(data: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("encrypted", "Dit PDF-bestand is beveiligd met een wachtwoord. Upload een versie zonder beveiliging.")
        pages = reader.pages[:MAX_PAGES]
        plain = "\n".join((page.extract_text() or "") for page in pages)
        try:
            positioned = "\n".join(_positioned_text(page) for page in pages)
        except Exception:  # positional extraction is a best-effort improvement
            positioned = ""
        # Use the row-based text when it captured (nearly) all the text.
        text = positioned if len(positioned.replace(" ", "")) >= 0.9 * len(plain.replace(" ", "")) else plain
        return clean_extracted_text(text), len(pages)
    except ExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        logger.info("PDF could not be read: %s", type(exc).__name__)
        raise ExtractionError("unreadable", "Dit PDF-bestand kon niet gelezen worden. Is het beschadigd?") from exc


def extract_docx(data: bytes) -> str:
    try:
        document = DocxDocument(io.BytesIO(data))
    except Exception as exc:  # python-docx raises several unrelated exception types for broken files
        raise ExtractionError("unreadable", "Dit Word-bestand kon niet gelezen worden. Is het beschadigd?") from exc
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                lines.append(" | ".join(dict.fromkeys(cells)))
    return clean_extracted_text("\n".join(lines))


def extract_text(data: bytes, mime: str) -> tuple[str, bool]:
    """Returns (text, needs_ocr)."""
    if mime == PDF_MIME:
        text, pages = extract_pdf(data)
        return text, len(text) < MIN_CHARS_PER_PAGE * max(1, min(pages, 2))
    if mime == DOCX_MIME:
        text = extract_docx(data)
        if len(text) < 40:
            raise ExtractionError("empty", "Dit document bevat (bijna) geen tekst.")
        return text, False
    raise ExtractionError("unsupported", "Dit bestandstype wordt niet ondersteund.")


_LANG_MARKERS = {
    "nl": {"de", "het", "een", "en", "van", "ervaring", "werkervaring", "opleiding", "vaardigheden", "talen", "bij", "voor", "met"},
    "fr": {"le", "la", "les", "et", "des", "du", "expérience", "formation", "compétences", "langues", "pour", "avec", "chez"},
    "en": {"the", "and", "of", "experience", "education", "skills", "languages", "for", "with", "at", "work"},
}


def detect_language(text: str) -> str | None:
    words = re.findall(r"[a-zàâçéèêëîïôûùüÿœ]+", text.lower())[:3000]
    if not words:
        return None
    scores = {lang: sum(1 for w in words if w in markers) for lang, markers in _LANG_MARKERS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 5 else None
