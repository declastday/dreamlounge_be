from __future__ import annotations
from uuid import uuid4
from sqlalchemy import String, Boolean, Text, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base, TimestampMixin


class Club(TimestampMixin, Base):
    __tablename__ = "clubs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    president_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # 'department': 학과 동아리 / 'central': 중앙 동아리
    club_type: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    open_chat_url: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(255))
    activity_images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    division: Mapped[str | None] = mapped_column(String(100))
    field: Mapped[str | None] = mapped_column(String(100))
    atmosphere: Mapped[str | None] = mapped_column(String(100))
    activity_purpose: Mapped[str | None] = mapped_column(String(100))
    activity_period: Mapped[str | None] = mapped_column(String(100))
    recruit_start: Mapped[str | None] = mapped_column(Date)
    recruit_end: Mapped[str | None] = mapped_column(Date)
    is_recruiting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tags = relationship("ClubTag", back_populates="club", cascade="all, delete-orphan")
    members = relationship("ClubMember", back_populates="club")
    application_forms = relationship("ApplicationForm", back_populates="club")
    posts = relationship("Post", back_populates="club")

    @property
    def member_count(self) -> int:
        return sum(1 for m in self.members if m.status == "active")


class ClubTag(Base):
    __tablename__ = "club_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("clubs.id"), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(100), nullable=False)

    club = relationship("Club", back_populates="tags")
