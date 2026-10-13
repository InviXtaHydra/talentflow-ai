"""Section labels and date formatting for generated CVs, per document language."""

from app.schemas.cv import CVContent

LABELS = {
    "nl": {
        "profile": "Profiel",
        "experience": "Werkervaring",
        "education": "Opleiding",
        "skills": "Vaardigheden",
        "projects": "Projecten",
        "certifications": "Certificaten",
        "languages": "Talen",
        "present": "heden",
    },
    "fr": {
        "profile": "Profil",
        "experience": "Expérience professionnelle",
        "education": "Formation",
        "skills": "Compétences",
        "projects": "Projets",
        "certifications": "Certifications",
        "languages": "Langues",
        "present": "présent",
    },
    "en": {
        "profile": "Profile",
        "experience": "Work experience",
        "education": "Education",
        "skills": "Skills",
        "projects": "Projects",
        "certifications": "Certifications",
        "languages": "Languages",
        "present": "present",
    },
}

MONTHS = {
    "nl": ["jan.", "feb.", "mrt.", "apr.", "mei", "jun.", "jul.", "aug.", "sep.", "okt.", "nov.", "dec."],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

LANGUAGE_NAMES = {
    "nl": {
        "nl": "Nederlands",
        "fr": "Frans",
        "en": "Engels",
        "de": "Duits",
        "tr": "Turks",
        "es": "Spaans",
        "it": "Italiaans",
        "ar": "Arabisch",
    },
    "fr": {
        "nl": "Néerlandais",
        "fr": "Français",
        "en": "Anglais",
        "de": "Allemand",
        "tr": "Turc",
        "es": "Espagnol",
        "it": "Italien",
        "ar": "Arabe",
    },
    "en": {
        "nl": "Dutch",
        "fr": "French",
        "en": "English",
        "de": "German",
        "tr": "Turkish",
        "es": "Spanish",
        "it": "Italian",
        "ar": "Arabic",
    },
}

LEVELS = {
    "nl": {"native": "moedertaal", "fluent": "vloeiend", "professional": "goed", "basic": "basis"},
    "fr": {"native": "langue maternelle", "fluent": "courant", "professional": "bon niveau", "basic": "notions"},
    "en": {"native": "native", "fluent": "fluent", "professional": "professional", "basic": "basic"},
}


def labels(language: str) -> dict[str, str]:
    return LABELS.get(language, LABELS["nl"])


def format_month(value: str | None, language: str) -> str:
    if not value:
        return ""
    parts = value.split("-")
    if len(parts) == 1:
        return parts[0]
    return f"{MONTHS.get(language, MONTHS['nl'])[int(parts[1]) - 1]} {parts[0]}"


def period(start: str | None, end: str | None, is_current: bool, language: str) -> str:
    begin = format_month(start, language)
    finish = labels(language)["present"] if is_current else format_month(end, language)
    if begin and finish:
        return f"{begin} – {finish}"
    return begin or finish


def language_line(cv: CVContent, language: str) -> str:
    names = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["nl"])
    levels = LEVELS.get(language, LEVELS["nl"])
    return ", ".join(f"{names.get(lang.code, lang.code.upper())} ({levels.get(lang.level, lang.level)})" for lang in cv.languages)


def contact_items(cv: CVContent) -> list[tuple[str, str | None]]:
    """(text, link) pairs for the contact line. Only details the candidate entered; nothing is added."""
    c = cv.contact
    items: list[tuple[str, str | None]] = []
    if c.city:
        items.append((c.city, None))
    if c.phone:
        items.append((c.phone, f"tel:{c.phone.replace(' ', '')}"))
    if c.email:
        items.append((c.email, f"mailto:{c.email}"))
    for url in (c.linkedin_url, c.website_url):
        if url:
            href = url if url.startswith("http") else f"https://{url}"
            items.append((url.replace("https://", "").replace("http://", "").rstrip("/"), href))
    return items
