from app.models.entities import CandidateProfile, User
from app.schemas.cv import CVBullet, CVCertification, CVContent, CVEducation, CVExperience, CVProject
from app.schemas.profile import ContactDetails, ProfileContent


def contact_for(user: User, profile: CandidateProfile) -> ContactDetails:
    return ContactDetails(
        full_name=user.full_name,
        email=user.email,
        phone=profile.phone,
        city=profile.city,
        linkedin_url=profile.linkedin_url,
        website_url=profile.website_url,
    )


def profile_to_cv_content(user: User, profile: CandidateProfile) -> CVContent:
    """The candidate's verified profile as a CV document, item ids kept as provenance."""
    content = ProfileContent.model_validate(profile.content or {})
    return CVContent(
        contact=contact_for(user, profile),
        headline=profile.headline,
        summary=profile.summary,
        experiences=[
            CVExperience(
                source_id=e.id,
                title=e.title,
                employer=e.employer,
                location=e.location,
                start=e.start,
                end=e.end,
                is_current=e.is_current,
                bullets=[CVBullet(text=b, source_refs=[e.id]) for b in e.bullets]
                or ([CVBullet(text=e.description, source_refs=[e.id])] if e.description else []),
            )
            for e in content.experiences
        ],
        education=[
            CVEducation(
                source_id=e.id,
                degree=e.degree,
                institution=e.institution,
                field=e.field,
                start=e.start,
                end=e.end,
                description=e.description,
            )
            for e in content.education
        ],
        skills=list(content.skills),
        certifications=[CVCertification(source_id=c.id, name=c.name, issuer=c.issuer, year=c.year) for c in content.certifications],
        languages=list(content.languages),
        projects=[
            CVProject(source_id=p.id, name=p.name, description=p.description, url=p.url, technologies=p.technologies)
            for p in content.projects
        ],
    )
