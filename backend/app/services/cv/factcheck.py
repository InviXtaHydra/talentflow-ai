"""Assembles a tailored CV from the optimizer's output and checks it against the source profile.

The model may only rephrase, select and reorder. This module:
- copies every hard fact (names, employers, titles, dates, education, certifications, languages, contact
  details) from the source profile, never from the model output;
- keeps a bullet only when it is traceable to a source item and introduces no numbers or skills that the
  source doesn't contain; anything else becomes a review item the candidate can accept or ignore;
- restricts the skills list to skills that are in the profile.

This is a strong safeguard, not a guarantee: it can't judge every nuance of wording, which is why the
candidate always reviews and edits the CV before exporting it.
"""

from dataclasses import dataclass

from app.schemas.cv import (
    ChangeNote,
    CVBullet,
    CVContent,
    OptimizerOutput,
    ReviewItem,
)
from app.utils.skills import _SYNONYMS, normalize_skill, split_skills, text_mentions_skill
from app.utils.text import numbers_in


@dataclass
class SourceIndex:
    cv: CVContent
    texts: dict[str, str]  # source id -> all text of that item
    all_text: str
    skill_keys: set[str]  # normalized skills that the profile supports


def build_index(source: CVContent) -> SourceIndex:
    texts: dict[str, str] = {}
    for e in source.experiences:
        if e.source_id:
            texts[e.source_id] = " ".join([e.title, e.employer, e.location or "", e.start or "", e.end or "", *(b.text for b in e.bullets)])
    for p in source.projects:
        if p.source_id:
            texts[p.source_id] = " ".join([p.name, p.description or "", *p.technologies])
    for ed in source.education:
        if ed.source_id:
            texts[ed.source_id] = " ".join([ed.degree, ed.institution, ed.field or "", ed.start or "", ed.end or "", ed.description or ""])
    for c in source.certifications:
        if c.source_id:
            texts[c.source_id] = " ".join([c.name, c.issuer or "", str(c.year or "")])
    all_text = " ".join([source.headline or "", source.summary or "", *texts.values(), *source.skills])
    skill_keys = {normalize_skill(s) for s in split_skills(source.skills)}
    skill_keys |= {normalize_skill(t) for p in source.projects for t in p.technologies}
    return SourceIndex(cv=source, texts=texts, all_text=all_text, skill_keys=skill_keys)


def _skill_vocabulary(extra: list[str]) -> set[str]:
    return set(_SYNONYMS) | {normalize_skill(s) for s in extra}


def unsupported_skills(text: str, index: SourceIndex, vocabulary: set[str]) -> list[str]:
    found = []
    for key in vocabulary:
        if key in index.skill_keys:
            continue
        if text_mentions_skill(text, key) and not text_mentions_skill(index.all_text, key):
            found.append(key)
    return sorted(found)


def unsupported_numbers(text: str, reference: str) -> list[str]:
    return sorted(numbers_in(text) - numbers_in(reference))


def assemble(source: CVContent, output: OptimizerOutput, job_skills: list[str]) -> tuple[CVContent, list[ReviewItem]]:
    index = build_index(source)
    vocabulary = _skill_vocabulary(job_skills)
    review: list[ReviewItem] = []
    valid_ids = set(index.texts)

    def check_text(text: str, reference: str) -> str | None:
        numbers = unsupported_numbers(text, reference)
        if numbers:
            return f"Bevat cijfers die niet in je profiel staan: {', '.join(numbers)}"
        skills = unsupported_skills(text, index, vocabulary)
        if skills:
            return f"Vermeldt vaardigheden die niet in je profiel staan: {', '.join(skills)}"
        return None

    # Experiences: order from the model (unknown ids ignored), every source experience kept.
    by_id = {e.source_id: e for e in source.experiences if e.source_id}
    order = [i for i in dict.fromkeys(output.experience_order) if i in by_id]
    order += [e.source_id for e in source.experiences if e.source_id and e.source_id not in order]
    rewritten = {e.source_id: e for e in output.experiences}
    experiences = []
    for exp_id in order:
        original = by_id[exp_id]
        proposal = rewritten.get(exp_id)
        bullets: list[CVBullet] = []
        if proposal:
            for bullet in proposal.bullets:
                refs = [r for r in bullet.source_refs if r in valid_ids] or [exp_id]
                reference = " ".join(index.texts[r] for r in refs)
                problem = check_text(bullet.text, reference)
                if problem:
                    review.append(ReviewItem(kind="bullet", section="experience", text=bullet.text, reason=problem, source_id=exp_id))
                else:
                    bullets.append(CVBullet(text=bullet.text.strip(), source_refs=refs))
        if not bullets:
            bullets = list(original.bullets)
        experiences.append(original.model_copy(update={"bullets": bullets}))

    # Skills: only what the profile supports, model's order first.
    skills: list[str] = []
    seen: set[str] = set()
    source_skills = split_skills(source.skills)
    display = {normalize_skill(s): s for s in source_skills}
    for p in source.projects:
        for t in p.technologies:
            display.setdefault(normalize_skill(t), t)
    for name in output.skills:
        key = normalize_skill(name)
        if key in seen:
            continue
        if key in index.skill_keys:
            skills.append(display.get(key, name))
            seen.add(key)
        else:
            review.append(ReviewItem(kind="skill", section="skills", text=name, reason="Deze vaardigheid staat niet in je profiel."))
    skills += [s for s in source_skills if normalize_skill(s) not in seen]

    # Summary and headline: kept only when they add no unsupported facts.
    summary = output.summary.strip() if output.summary else source.summary
    if summary and summary != source.summary:
        problem = check_text(summary, index.all_text)
        if problem:
            review.append(ReviewItem(kind="summary", section="summary", text=summary, reason=problem))
            summary = source.summary
    headline = (output.headline or "").strip() or source.headline
    if headline and headline != source.headline and check_text(headline, index.all_text):
        review.append(
            ReviewItem(kind="summary", section="headline", text=headline, reason="De titel bevat gegevens die niet in je profiel staan.")
        )
        headline = source.headline

    # Projects: reorder, descriptions checked like bullets.
    projects_by_id = {p.source_id: p for p in source.projects if p.source_id}
    project_order = [i for i in dict.fromkeys(output.project_order) if i in projects_by_id]
    project_order += [p.source_id for p in source.projects if p.source_id and p.source_id not in project_order]
    project_text = {p.source_id: p.description for p in output.projects if p.description}
    projects = []
    for pid in project_order:
        original_project = projects_by_id[pid]
        description = project_text.get(pid)
        if description and description != original_project.description:
            problem = check_text(description, index.texts.get(pid, ""))
            if problem:
                review.append(ReviewItem(kind="bullet", section="projects", text=description, reason=problem, source_id=pid))
                description = original_project.description
        projects.append(original_project.model_copy(update={"description": description or original_project.description}))

    tailored = CVContent(
        contact=source.contact,
        headline=headline,
        summary=summary,
        experiences=experiences,
        education=source.education,
        skills=skills,
        certifications=source.certifications,
        languages=source.languages,
        projects=projects,
    )
    return tailored, review


_SECTION_KEYWORDS = {
    "summary": ("samenvatting", "summary", "profiel", "profil", "résumé", "headline", "titel"),
    "experience": ("ervaring", "experience", "expérience", "werk", "bullet"),
    "skills": ("vaardig", "skill", "compét", "competen"),
    "projects": ("project", "projet"),
}


def describe_changes(source: CVContent, tailored: CVContent, model_notes: list[ChangeNote], language: str) -> list[ChangeNote]:
    """Change notes based on what actually differs between the source and the final CV. The model's own notes
    are kept only for sections that really changed, so the list never claims edits that didn't survive the fact check."""
    nl = language != "en" and language != "fr"
    changed: dict[str, bool] = {
        "summary": (tailored.summary or "") != (source.summary or "") or (tailored.headline or "") != (source.headline or ""),
        "experience": False,
        "skills": tailored.skills != source.skills,
        "projects": [p.source_id for p in tailored.projects] != [p.source_id for p in source.projects]
        or any(a.description != b.description for a, b in zip(tailored.projects, source.projects, strict=False)),
    }
    notes: list[ChangeNote] = []
    order_changed = [e.source_id for e in tailored.experiences] != [e.source_id for e in source.experiences]
    originals = {e.source_id: [b.text for b in e.bullets] for e in source.experiences}
    rewritten = sum(1 for e in tailored.experiences for b in e.bullets if b.text not in originals.get(e.source_id, []))
    changed["experience"] = order_changed or rewritten > 0
    if order_changed:
        notes.append(
            ChangeNote(
                section="experience",
                description="Werkervaring geordend op relevantie voor deze vacature." if nl else "Work experience reordered by relevance.",
            )
        )
    if rewritten:
        notes.append(
            ChangeNote(
                section="experience",
                description=f"{rewritten} opsommingspunt(en) herschreven." if nl else f"{rewritten} bullet point(s) rewritten.",
            )
        )
    if changed["skills"]:
        notes.append(
            ChangeNote(
                section="skills",
                description="Vaardigheden geordend: wat de vacature vraagt staat bovenaan." if nl else "Skills reordered for the vacancy.",
            )
        )
    if changed["summary"]:
        notes.append(
            ChangeNote(
                section="summary",
                description="Samenvatting en/of titel afgestemd op de vacature." if nl else "Summary and/or headline tailored.",
            )
        )
    for note in model_notes:
        section = note.section.lower()
        key = next((k for k, words in _SECTION_KEYWORDS.items() if any(w in section for w in words)), None)
        if key and changed[key] and key != "experience":
            notes.append(note)
    return notes
