from app.schemas.cv import CVBullet, CVContent, CVExperience
from app.schemas.profile import ContactDetails
from app.services.documents.docx_export import render_docx
from app.services.documents.pdf import render_pdf

SAMPLE_CV = CVContent(
    contact=ContactDetails(full_name="Sanne Jacobs", email="sanne@example.com", city="Leuven"),
    headline="Data analist",
    summary="Data analist met ervaring in SQL en Power BI. Ik maak rapportering begrijpelijk voor managers.",
    experiences=[
        CVExperience(
            title="Data Analist",
            employer="Initech",
            start="2021-03",
            is_current=True,
            bullets=[
                CVBullet(text="Bouwde Power BI-dashboards voor de verkoopafdeling"),
                CVBullet(text="Schreef SQL-queries voor maandelijkse rapporten"),
            ],
        )
    ],
    skills=["SQL", "Power BI", "Excel"],
)


def sample_pdf() -> bytes:
    return render_pdf(SAMPLE_CV, template="minimal")


def sample_docx() -> bytes:
    return render_docx(SAMPLE_CV, template="minimal")
