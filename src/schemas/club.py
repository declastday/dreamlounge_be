from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date


class ClubTagCreate(BaseModel):
    tag_key: str = Field(..., max_length=50)
    tag_value: str = Field(..., max_length=100)


class ClubTagResponse(BaseModel):
    tag_key: str
    tag_value: str

    model_config = {"from_attributes": True}


class ClubCreate(BaseModel):
    name: str = Field(..., max_length=100)
    club_type: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    open_chat_url: Optional[str] = None
    image_url: Optional[str] = None
    activity_images: List[str] = []
    division: Optional[str] = None
    field: Optional[str] = None
    atmosphere: Optional[str] = None
    activity_purpose: Optional[str] = None
    activity_period: Optional[str] = None
    recruit_start: Optional[date] = None
    recruit_end: Optional[date] = None
    is_recruiting: bool = False
    tags: List[ClubTagCreate] = []


class ClubUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    club_type: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    open_chat_url: Optional[str] = None
    image_url: Optional[str] = None
    activity_images: Optional[List[str]] = None
    division: Optional[str] = None
    field: Optional[str] = None
    atmosphere: Optional[str] = None
    activity_purpose: Optional[str] = None
    activity_period: Optional[str] = None
    recruit_start: Optional[date] = None
    recruit_end: Optional[date] = None
    is_recruiting: Optional[bool] = None
    tags: Optional[List[ClubTagCreate]] = None


class ClubResponse(BaseModel):
    id: str
    name: str
    club_type: Optional[str]
    description: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    open_chat_url: Optional[str]
    image_url: Optional[str]
    activity_images: List[str] = []
    division: Optional[str]
    field: Optional[str]
    atmosphere: Optional[str]
    activity_purpose: Optional[str]
    activity_period: Optional[str]
    recruit_start: Optional[date]
    recruit_end: Optional[date]
    is_recruiting: bool
    member_count: int = 0
    tags: List[ClubTagResponse] = []

    @field_validator("activity_images", mode="before")
    @classmethod
    def coerce_activity_images(cls, v):
        return v if isinstance(v, list) else []

    model_config = {"from_attributes": True}


class FormQuestionResponse(BaseModel):
    id: str
    question_text: str
    question_type: str
    is_required: bool
    order_index: int
    options: Optional[list] = None

    model_config = {"from_attributes": True}


class ApplicationFormResponse(BaseModel):
    id: str
    club_id: str
    title: str
    is_active: bool
    questions: List[FormQuestionResponse] = []

    model_config = {"from_attributes": True}


class FormCreate(BaseModel):
    title: str = Field(..., max_length=200)


class FormUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str = "text"
    is_required: bool = True
    order_index: int = 0
    options: Optional[list] = None


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    is_required: Optional[bool] = None
    order_index: Optional[int] = None
    options: Optional[list] = None


class QuestionReorderRequest(BaseModel):
    question_ids: List[str]
