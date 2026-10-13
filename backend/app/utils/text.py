import hashlib
import json
import re
import unicodedata
from typing import Any

_STOPWORDS = set(
    [
        "de",
        "het",
        "een",
        "en",
        "van",
        "in",
        "op",
        "te",
        "voor",
        "met",
        "is",
        "dat",
        "die",
        "aan",
        "als",
        "zijn",
        "bij",
        "of",
        "om",
        "naar",
        "door",
        "ook",
        "je",
        "jij",
        "wij",
        "we",
        "the",
        "a",
        "an",
        "and",
        "of",
        "in",
        "on",
        "to",
        "for",
        "with",
        "is",
        "that",
        "as",
        "are",
        "by",
        "or",
        "at",
        "from",
        "be",
        "you",
        "we",
        "our",
        "your",
        "this",
        "will",
        "le",
        "la",
        "les",
        "un",
        "une",
        "et",
        "des",
        "du",
        "en",
        "pour",
        "avec",
        "est",
        "que",
        "qui",
        "dans",
        "sur",
        "au",
        "aux",
        "par",
        "vous",
        "nous",
    ]
)


def content_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def tokens(text: str | None) -> list[str]:
    if not text:
        return []
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [t for t in re.findall(r"[a-z0-9#+]+", text) if len(t) > 1 and t not in _STOPWORDS]


def numbers_in(text: str | None) -> set[str]:
    """Numbers that appear in a text (amounts, percentages, counts), normalized for comparison."""
    if not text:
        return set()
    found = re.findall(r"\d+(?:[.,]\d+)?", text)
    return {n.replace(",", ".").rstrip("0").rstrip(".") if "." in n.replace(",", ".") else n for n in found}


def clean_extracted_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
