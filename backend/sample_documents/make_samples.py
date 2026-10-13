"""Generates the fictional sample CV used for manual testing and the end-to-end test.

Run inside the API container:  python sample_documents/make_samples.py
"""

from pathlib import Path

from app.schemas.cv import CVBullet, CVContent, CVEducation, CVExperience
from app.schemas.profile import ContactDetails, LanguageSkill
from app.services.documents.docx_export import render_docx
from app.services.documents.pdf import render_pdf

cv = CVContent(
    contact=ContactDetails(full_name="Noor Vermeulen", email="noor.vermeulen@example.com", phone="+32 470 12 34 56", city="Gent"),
    headline="Backend developer",
    summary="Backend developer met drie jaar ervaring in Python, SQL en PostgreSQL. Ik bouw API's en datapijplijnen en werk graag in een Scrum-team.",
    experiences=[
        CVExperience(title="Backend Developer", employer="Voorbeeld BV", location="Gent", start="2022-09", is_current=True, bullets=[
            CVBullet(text="Bouwde REST API's in Python en FastAPI voor een boekingsplatform"),
            CVBullet(text="Ontwierp datamodellen en queries in PostgreSQL"),
            CVBullet(text="Zette CI/CD op met Docker en GitHub Actions"),
        ]),
        CVExperience(title="Junior Developer", employer="Testbedrijf NV", location="Brugge", start="2021-07", end="2022-08", bullets=[
            CVBullet(text="Schreef rapporteringsqueries in SQL"),
            CVBullet(text="Werkte mee aan een interne webapplicatie in React"),
        ]),
    ],
    education=[CVEducation(degree="Professionele bachelor Toegepaste Informatica", institution="HOGENT", start="2018", end="2021")],
    skills=["Python", "FastAPI", "SQL", "PostgreSQL", "Docker", "Git", "React", "Scrum"],
    languages=[LanguageSkill(code="nl", level="native"), LanguageSkill(code="en", level="fluent"), LanguageSkill(code="fr", level="basic")],
)
HERE = Path(__file__).parent
(HERE / "sample-cv-noor-vermeulen.pdf").write_bytes(render_pdf(cv, template="minimal", title="CV Noor Vermeulen"))
(HERE / "sample-cv-noor-vermeulen.docx").write_bytes(render_docx(cv, template="minimal", title="CV Noor Vermeulen"))
print("ok")
