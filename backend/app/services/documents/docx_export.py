"""Word (.docx) rendering of a structured CV with python-docx. Uses real headings, paragraphs and list
bullets (no text boxes or tables), which ATS systems parse reliably."""

import io
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from app.schemas.cv import CVContent
from app.services.documents.labels import contact_items, labels, language_line, period

THEMES: dict[str, dict[str, Any]] = {
    "modern": {"font": "Calibri", "accent": RGBColor(0x37, 0x30, 0xA3), "upper": False, "skills_first": False, "mono": None},
    "minimal": {"font": "Arial", "accent": RGBColor(0, 0, 0), "upper": True, "skills_first": False, "mono": None},
    "technical": {"font": "Calibri", "accent": RGBColor(0x0F, 0x76, 0x6E), "upper": False, "skills_first": True, "mono": "Consolas"},
}
MUTED = RGBColor(0x47, 0x55, 0x69)


def _add_hyperlink(paragraph, text: str, url: str, color: RGBColor) -> None:
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color_el = OxmlElement("w:color")
    color_el.set(qn("w:val"), str(color))
    props.append(color_el)
    run.append(props)
    text_el = OxmlElement("w:t")
    text_el.text = text
    run.append(text_el)
    link.append(run)
    paragraph._p.append(link)


def _bottom_border(paragraph, color: RGBColor) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", str(color))):
        bottom.set(qn(key), value)
    borders.append(bottom)
    p_pr.append(borders)


def render_docx(cv: CVContent, *, template: str = "modern", language: str = "nl", title: str = "CV") -> bytes:
    theme = THEMES.get(template, THEMES["modern"])
    lab = labels(language)
    doc = Document()
    doc.core_properties.title = title
    doc.core_properties.author = cv.contact.full_name or ""
    for s in doc.sections:
        s.left_margin = s.right_margin = Mm(18)
        s.top_margin = s.bottom_margin = Mm(16)
    normal = doc.styles["Normal"]
    normal.font.name = theme["font"]
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(2)

    def para(
        text: str = "",
        *,
        size: float | None = None,
        bold: bool = False,
        color: RGBColor | None = None,
        after: float = 2,
        font: str | None = None,
    ):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(after)
        if text:
            run = p.add_run(text)
            run.bold = bold
            if size:
                run.font.size = Pt(size)
            if color is not None:
                run.font.color.rgb = color
            if font:
                run.font.name = font
        return p

    def section(name: str) -> None:
        heading = lab[name].upper() if theme["upper"] else lab[name]
        p = para(heading, size=11.5, bold=True, color=theme["accent"], after=3)
        p.paragraph_format.space_before = Pt(9)
        if template != "minimal":
            _bottom_border(p, theme["accent"])

    name = para(cv.contact.full_name or "", size=21, bold=True, color=theme["accent"] if template != "minimal" else None, after=1)
    name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if cv.headline:
        para(cv.headline, size=12, color=MUTED, after=2)
    contact = contact_items(cv)
    if contact:
        p = para(after=6)
        for i, (text, href) in enumerate(contact):
            if i:
                p.add_run("  ·  ").font.color.rgb = MUTED
            if href and not href.startswith("tel:"):
                _add_hyperlink(p, text, href, theme["accent"])
            else:
                run = p.add_run(text)
                run.font.color.rgb = MUTED

    def skills_block() -> None:
        if cv.skills:
            section("skills")
            para(" · ".join(cv.skills), font=theme["mono"])

    if cv.summary:
        section("profile")
        para(cv.summary)
    if theme["skills_first"]:
        skills_block()

    if cv.experiences:
        section("experience")
        for exp in cv.experiences:
            p = para(after=0)
            run = p.add_run(exp.title)
            run.bold = True
            employer = p.add_run(f" — {exp.employer}")
            employer.font.color.rgb = MUTED
            p.paragraph_format.keep_with_next = True
            meta = " · ".join(x for x in [period(exp.start, exp.end, exp.is_current, language), exp.location or ""] if x)
            if meta:
                m = para(meta, size=9, color=MUTED, after=2)
                m.paragraph_format.keep_with_next = True
            for bullet in exp.bullets:
                b = doc.add_paragraph(bullet.text, style="List Bullet")
                b.paragraph_format.space_after = Pt(1)
            para(after=3)

    if cv.projects:
        section("projects")
        for project in cv.projects:
            p = para(project.name, bold=True, after=0)
            p.paragraph_format.keep_with_next = True
            if project.description:
                para(project.description, after=0)
            if project.technologies:
                para(", ".join(project.technologies), size=9, color=MUTED, after=4)

    if cv.education:
        section("education")
        for edu in cv.education:
            p = para(after=0)
            p.add_run(edu.degree + (f", {edu.field}" if edu.field else "")).bold = True
            p.add_run(f" — {edu.institution}").font.color.rgb = MUTED
            when = period(edu.start, edu.end, False, language)
            if when:
                para(when, size=9, color=MUTED, after=0)
            if edu.description:
                para(edu.description, after=0)
            para(after=2)

    if cv.certifications:
        section("certifications")
        for cert in cv.certifications:
            para(cert.name + (f" — {cert.issuer}" if cert.issuer else "") + (f" ({cert.year})" if cert.year else ""))

    if not theme["skills_first"]:
        skills_block()
    if cv.languages:
        section("languages")
        para(language_line(cv, language))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
