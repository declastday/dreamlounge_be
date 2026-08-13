from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ApplicationAnswerCreate(BaseModel):
    question_id: str
    answer_text: str


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|passed|failed)$")


class ApplicationCreate(BaseModel):
    form_id: str
    is_draft: bool = True
    answers: List[ApplicationAnswerCreate] = []


class ApplicationUpdate(BaseModel):
    is_draft: Optional[bool] = None
    answers: Optional[List[ApplicationAnswerCreate]] = None


class ApplicationAnswerResponse(BaseModel):
    question_id: str
    answer_text: Optional[str]

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    id: str
    form_id: str
    club_id: Optional[str] = None
    club_name: Optional[str] = None
    status: str
    is_draft: bool
    submitted_at: Optional[datetime]
    updated_at: datetime
    answers: List[ApplicationAnswerResponse] = []

    model_config = {"from_attributes": True}


class ApplicationListItem(BaseModel):
    id: str
    form_id: str
    club_id: Optional[str] = None
    club_name: Optional[str] = None
    status: str
    is_draft: bool
    submitted_at: Optional[datetime]
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActiveClubItem(BaseModel):
    club_id: str
    club_name: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class AdminApplicationListItem(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_student_id: str
    status: str
    submitted_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AdminApplicationResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_student_id: str
    status: str
    submitted_at: Optional[datetime]
    answers: List[ApplicationAnswerResponse] = []

    model_config = {"from_attributes": True}
