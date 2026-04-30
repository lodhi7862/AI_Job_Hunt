from enum import Enum

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2)
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company: str = Field(default="", max_length=255)
    description: str = Field(min_length=50, max_length=20000)


class LinkedInIn(BaseModel):
    profile_url: HttpUrl | None = None
    profile_text: str = Field(default="", max_length=15000)


class ApplicationStatus(str, Enum):
    APPLIED = "Applied"
    SCREENING = "Screening"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


class ApplicationIn(BaseModel):
    company: str = Field(min_length=2, max_length=255)
    role: str = Field(min_length=2, max_length=255)
    date_applied: str = Field(min_length=8, max_length=30)
    status: ApplicationStatus = ApplicationStatus.APPLIED
    notes: str = Field(default="", max_length=5000)
