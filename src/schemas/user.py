from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class EmailVerifySendRequest(BaseModel):
    email: EmailStr


class EmailVerifyConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PrivacyConsentCreate(BaseModel):
    required_agreed: bool
    optional_agreed: bool = False


class UserCreate(BaseModel):
    student_id: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    verification_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    privacy_consent: PrivacyConsentCreate


class LoginRequest(BaseModel):
    student_id: str
    password: str


class UserInfo(BaseModel):
    id: str
    student_id: str
    name: str
    email: str
    phone: Optional[str]
    department: Optional[str]

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class UserResponse(BaseModel):
    id: str
    student_id: str
    name: str
    email: str
    phone: Optional[str]
    department: Optional[str]
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
