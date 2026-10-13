"""Basic CV extraction without a language model.

Only finds what can be recognized reliably with patterns: contact details, the skills and languages
sections. Work experience and education are left for the candidate to fill in. The result is labelled
as a basic extraction in the UI; nothing is guessed."""

import re

from app.schemas.profile import ContactDetails, ExtractedCV, LanguageSkill, ProfileContent

_SECTION_HEADINGS = {
    "skills": ["vaardigheden", "competenties", "skills", "compétences", "competences", "technische vaardigheden", "kennis", "tools"],
    "languages": ["talen", "talenkennis", "languages", "langues"],
    "summary": ["profiel", "over mij", "samenvatting", "profile", "summary", "about me", "profil", "à propos"],
    "experience": ["werkervaring", "ervaring", "experience", "work experience", "expérience", "expérience professionnelle"],
    "education": ["opleiding", "opleidingen", "education", "formation", "studies"],
}
_ALL_HEADINGS = {h: key for key, values in _SECTION_HEADINGS.items() for h in values}

_LANGUAGE_NAMES = {
    "nederlands": "nl",
    "dutch": "nl",
    "néerlandais": "nl",
    "vlaams": "nl",
    "frans": "fr",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "engels": "en",
    "english": "en",
    "anglais": "en",
    "duits": "de",
    "german": "de",
    "allemand": "de",
    "spaans": "es",
    "spanish": "es",
    "espagnol": "es",
    "turks": "tr",
    "turkish": "tr",
    "turc": "tr",
    "italiaans": "it",
    "italian": "it",
    "italien": "it",
    "arabisch": "ar",
    "arabic": "ar",
    "arabe": "ar",
}
_LEVEL_WORDS = {
    "native": ["moedertaal", "native", "langue maternelle", "maternelle"],
    "fluent": ["vloeiend", "fluent", "courant", "uitstekend", "excellent", "c1", "c2"],
    "professional": ["goed", "good", "professioneel", "professional", "bon", "b2", "b1"],
    "basic": ["basis", "basic", "notions", "elementair", "a1", "a2", "beperkt"],
}


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        key = _ALL_HEADINGS.get(line.lower().rstrip(":").strip())
        if key:
            current = key
            sections.setdefault(key, [])
            continue
        if current and line:
            sections[current].append(line)
    return sections


def extract(text: str, language: str | None) -> ExtractedCV:
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?:\+32|0032|0)\s?\d{1,3}(?:[\s./-]?\d{2,3}){2,4}", text)
    linkedin = re.search(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", text, re.I)
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    name = first_line if 2 <= len(first_line.split()) <= 4 and not re.search(r"[@\d]", first_line) else None

    sections = _sections(text)
    skills: list[str] = []
    for line in sections.get("skills", [])[:40]:
        for part in re.split(r"[,;•·|/]| - ", line):
            part = part.strip(" -–•*\t")
            if 1 < len(part) <= 40 and len(part.split()) <= 4:
                skills.append(part)

    languages: list[LanguageSkill] = []
    lang_lines = sections.get("languages", []) or text.splitlines()
    seen: set[str] = set()
    for line in lang_lines:
        lower = line.lower()
        for word, code in _LANGUAGE_NAMES.items():
            if re.search(rf"\b{re.escape(word)}\b", lower) and code not in seen:
                level = next((lvl for lvl, words in _LEVEL_WORDS.items() if any(w in lower for w in words)), "professional")
                languages.append(LanguageSkill(code=code, level=level))
                seen.add(code)

    summary_lines = sections.get("summary", [])[:8]
    return ExtractedCV(
        language=language,
        contact=ContactDetails(
            full_name=name,
            email=email.group(0) if email else None,
            phone=phone.group(0).strip() if phone else None,
            linkedin_url=linkedin.group(0) if linkedin else None,
        ),
        summary=" ".join(summary_lines) or None,
        profile=ProfileContent(skills=skills[:60], languages=languages),
    )
