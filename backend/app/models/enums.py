from enum import StrEnum


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"


class RemotePolicy(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class RemotePreference(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    ANY = "any"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class ExperienceLevel(StrEnum):
    JUNIOR = "junior"
    MEDIOR = "medior"
    SENIOR = "senior"
    LEAD = "lead"


class EducationLevel(StrEnum):
    NONE = "none"
    SECONDARY = "secondary"
    PROFESSIONAL_BACHELOR = "professional_bachelor"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


class SalaryPeriod(StrEnum):
    YEAR = "year"
    MONTH = "month"
    HOUR = "hour"


class JobStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class JobSource(StrEnum):
    EMPLOYER = "employer"
    DEMO = "demo"
    FEED = "feed"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    NEEDS_OCR = "needs_ocr"
    FAILED = "failed"


class CVVersionKind(StrEnum):
    ORIGINAL = "original"
    OPTIMIZED = "optimized"
    MANUAL = "manual"


class CVVersionStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    IN_REVIEW = "in_review"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationChannel(StrEnum):
    PLATFORM = "platform"
    EXTERNAL = "external"


class CompanyRole(StrEnum):
    OWNER = "owner"
    RECRUITER = "recruiter"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"
