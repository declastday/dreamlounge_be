from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    title: str
    content: str


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class PostListItem(BaseModel):
    id: str
    author_id: str
    author_name: str = ""
    post_type: str
    title: str
    is_notice: bool
    created_at: datetime
    comment_count: int = 0
    is_author_president: bool = False

    model_config = {"from_attributes": True}


class PostResponse(BaseModel):
    id: str
    club_id: str
    author_id: str
    post_type: str
    title: str
    content: str
    is_notice: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_id: str
    author_name: str = ""
    content: str
    created_at: datetime
    is_author_president: bool = False

    model_config = {"from_attributes": True}


class PostDetailResponse(BaseModel):
    id: str
    club_id: str
    author_id: str
    author_name: str = ""
    post_type: str
    title: str
    content: str
    is_notice: bool
    created_at: datetime
    is_author_president: bool = False
    comments: List[CommentResponse] = []

    model_config = {"from_attributes": True}
