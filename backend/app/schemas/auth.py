import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.schemas.common import ApiModel


def _check_password(value: str) -> str:
    if len(value) < 10:
        raise ValueError("Het wachtwoord moet minstens 10 tekens lang zijn.")
    if len(set(value)) < 4:
        raise ValueError("Kies een minder voorspelbaar wachtwoord.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    # Only these two roles can be chosen at sign-up. Admins are created with the CLI.
    account_type: Literal["candidate", "employer"] = "candidate"
    company_name: str | None = Field(default=None, max_length=200)
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _check_password(value)

    @field_validator("full_name", "company_name")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("accept_terms")
    @classmethod
    def must_accept(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Je moet de voorwaarden en de privacyverklaring aanvaarden.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _check_password(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _check_password(value)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class UpdateAccountRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    locale: Literal["nl", "fr", "en"] | None = None
    ai_processing_consent: bool | None = None


class CompanyRef(ApiModel):
    id: uuid.UUID
    name: str
    slug: str
    role: str


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    locale: str
    email_verified: bool
    onboarding_completed: bool = False
    ai_processing_consent: bool = False
    is_demo: bool = False
    companies: list[CompanyRef] = Field(default_factory=list)
    created_at: datetime


class SessionOut(ApiModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    user_agent: str | None
    current: bool = False
