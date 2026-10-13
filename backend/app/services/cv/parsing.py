"""Text extraction from PDF and DOCX. Documents are treated as data only: no macros, scripts, links or
embedded objects are executed or followed."""

import io
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


def extract_pdf(data: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("encrypted", "Dit PDF-bestand is beveiligd met een wachtwoord. Upload een versie zonder beveiliging.")
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((page.extract_text() or "") for page in pages)
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
