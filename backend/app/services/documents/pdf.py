"""PDF rendering of a structured CV (ReportLab). Single-column, real text (selectable and ATS-readable)."""

import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from app.schemas.cv import CVContent
from app.services.documents.labels import contact_items, labels, language_line, period

_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_FONTS_READY: dict[str, str] | None = None


def _fonts() -> dict[str, str]:
    """DejaVu (full Unicode: é, ç, ş, ğ, €) when installed, otherwise ReportLab's built-in Helvetica/Courier."""
    global _FONTS_READY
    if _FONTS_READY is not None:
        return _FONTS_READY
    files = {"sans": "DejaVuSans.ttf", "sans-bold": "DejaVuSans-Bold.ttf", "mono": "DejaVuSansMono.ttf"}
    if all(os.path.exists(os.path.join(_FONT_DIR, f)) for f in files.values()):
        for name, file in files.items():
            pdfmetrics.registerFont(TTFont(f"TF-{name}", os.path.join(_FONT_DIR, file)))
        _FONTS_READY = {"sans": "TF-sans", "bold": "TF-sans-bold", "mono": "TF-mono"}
    else:
        _FONTS_READY = {"sans": "Helvetica", "bold": "Helvetica-Bold", "mono": "Courier"}
    return _FONTS_READY


THEMES = {
    "modern": {
        "accent": colors.HexColor("#3730A3"),
        "muted": colors.HexColor("#475569"),
        "rule": True,
        "upper": False,
        "skills_first": False,
    },
    "minimal": {"accent": colors.black, "muted": colors.HexColor("#333333"), "rule": False, "upper": True, "skills_first": False},
    "technical": {
        "accent": colors.HexColor("#0F766E"),
        "muted": colors.HexColor("#475569"),
        "rule": True,
        "upper": False,
        "skills_first": True,
    },
}


def _p(text: str | None) -> str:
    return escape(text or "")


def render_pdf(cv: CVContent, *, template: str = "modern", language: str = "nl", title: str = "CV") -> bytes:
    fonts = _fonts()
    theme = THEMES.get(template, THEMES["modern"])
    lab = labels(language)
    base = ParagraphStyle(
        "base", fontName=fonts["sans"], fontSize=9.6, leading=13.2, textColor=colors.HexColor("#111827"), alignment=TA_LEFT
    )
    styles = {
        "name": ParagraphStyle(
            "name",
            parent=base,
            fontName=fonts["bold"],
            fontSize=21,
            leading=25,
            textColor=theme["accent"] if template != "minimal" else colors.black,
        ),
        "headline": ParagraphStyle("headline", parent=base, fontSize=11.5, leading=15, textColor=theme["muted"]),
        "contact": ParagraphStyle("contact", parent=base, fontSize=8.8, textColor=theme["muted"]),
        "section": ParagraphStyle(
            "section",
            parent=base,
            fontName=fonts["bold"],
            fontSize=10.5 if template == "minimal" else 11.5,
            leading=14,
            textColor=theme["accent"],
            spaceBefore=9,
            spaceAfter=3,
        ),
        "role": ParagraphStyle("role", parent=base, fontName=fonts["bold"], fontSize=10.2),
        "meta": ParagraphStyle("meta", parent=base, fontSize=8.8, textColor=theme["muted"]),
        "body": base,
        "skills": ParagraphStyle("skills", parent=base, fontName=fonts["mono"] if template == "technical" else fonts["sans"], fontSize=9),
    }
    link_color = "#3730A3" if template == "modern" else ("#0F766E" if template == "technical" else "#111111")

    def section(name: str) -> list:
        heading = lab[name].upper() if theme["upper"] else lab[name]
        out: list = [Paragraph(_p(heading), styles["section"])]
        if theme["rule"]:
            out.append(HRFlowable(width="100%", thickness=0.6, color=theme["accent"], spaceBefore=0, spaceAfter=4))
        return out

    story: list = [Paragraph(_p(cv.contact.full_name or ""), styles["name"])]
    if cv.headline:
        story.append(Paragraph(_p(cv.headline), styles["headline"]))
    contact = contact_items(cv)
    if contact:
        parts = [f'<a href="{_p(href)}" color="{link_color}">{_p(text)}</a>' if href else _p(text) for text, href in contact]
        story += [Spacer(1, 3), Paragraph("  ·  ".join(parts), styles["contact"])]
    story.append(Spacer(1, 4))

    def skills_block() -> list:
        if not cv.skills:
            return []
        return [*section("skills"), Paragraph(_p(" · ".join(cv.skills)), styles["skills"])]

    if cv.summary:
        story += [*section("profile"), Paragraph(_p(cv.summary), styles["body"])]
    if theme["skills_first"]:
        story += skills_block()

    if cv.experiences:
        story += section("experience")
        for exp in cv.experiences:
            header = [
                Paragraph(f"{_p(exp.title)} <font name='{fonts['sans']}' color='#475569'>— {_p(exp.employer)}</font>", styles["role"]),
                Paragraph(
                    _p(" · ".join(x for x in [period(exp.start, exp.end, exp.is_current, language), exp.location or ""] if x)),
                    styles["meta"],
                ),
            ]
            bullets = (
                ListFlowable(
                    [ListItem(Paragraph(_p(b.text), styles["body"]), leftIndent=10, value="•") for b in exp.bullets],
                    bulletType="bullet",
                    start="•",
                    leftIndent=10,
                    bulletFontSize=8,
                    bulletOffsetY=-1,
                )
                if exp.bullets
                else None
            )
            block = [*header, Spacer(1, 2)] + ([bullets] if bullets else []) + [Spacer(1, 6)]
            # Keep a role's header together with its first lines; long roles may still break across pages.
            story.append(KeepTogether(block) if len(exp.bullets) <= 6 else KeepTogether(block[:3]))
            if len(exp.bullets) > 6:
                story += block[3:]

    if cv.projects:
        story += section("projects")
        for project in cv.projects:
            items = [
                Paragraph(
                    _p(project.name) + (f" <font color='#475569' size='8.5'>({_p(project.url)})</font>" if project.url else ""),
                    styles["role"],
                )
            ]
            if project.description:
                items.append(Paragraph(_p(project.description), styles["body"]))
            if project.technologies:
                items.append(Paragraph(_p(", ".join(project.technologies)), styles["meta"]))
            story.append(KeepTogether([*items, Spacer(1, 5)]))

    if cv.education:
        story += section("education")
        for edu in cv.education:
            degree = edu.degree + (f", {edu.field}" if edu.field else "")
            items = [Paragraph(f"{_p(degree)} <font name='{fonts['sans']}' color='#475569'>— {_p(edu.institution)}</font>", styles["role"])]
            when = period(edu.start, edu.end, False, language)
            if when:
                items.append(Paragraph(_p(when), styles["meta"]))
            if edu.description:
                items.append(Paragraph(_p(edu.description), styles["body"]))
            story.append(KeepTogether([*items, Spacer(1, 5)]))

    if cv.certifications:
        story += section("certifications")
        for cert in cv.certifications:
            line = cert.name + (f" — {cert.issuer}" if cert.issuer else "") + (f" ({cert.year})" if cert.year else "")
            story.append(Paragraph(_p(line), styles["body"]))

    if not theme["skills_first"]:
        story += skills_block()
    if cv.languages:
        story += [*section("languages"), Paragraph(_p(language_line(cv, language)), styles["body"])]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
        author=cv.contact.full_name or "",
        creator="TalentFlow AI",
    )
    doc.build(story)
    return buffer.getvalue()
