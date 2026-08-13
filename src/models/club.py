from __future__ import annotations
from uuid import uuid4
from sqlalchemy import String, Boolean, Text, Date, ForeignKey, JSON, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
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

    # [최적화] member_count 는 파일 하단에서 column_property(SQL COUNT)로 정의
    #          기존의 @property(파이썬 계산)는 회원 행을 전부 로드해야 해서
    #          목록 조회 시 N+1 을 유발하므로 제거


class ClubTag(Base):
    __tablename__ = "club_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("clubs.id"), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(100), nullable=False)

    club = relationship("Club", back_populates="tags")


# ============================================================
# [최적화] member_count → SQL 집계 (column_property)
#   기존: @property 로 self.members 를 순회 → 회원 행 전부 로드(N+1)
#   변경: DB 가 COUNT 로 숫자만 반환 → 회원 행을 로드하지 않음
#         (club_service.get_clubs 의 selectinload(Club.members) 도 함께 제거됨)
#
#   ClubMember 가 별도 모듈이라 순환 import 를 피하려고
#   클래스 정의 이후에 부착
# ============================================================
from src.models.club_member import ClubMember  # noqa: E402

Club.member_count = column_property(
    select(func.count(ClubMember.id))
    .where(
        ClubMember.club_id == Club.id,
        ClubMember.status == "active",
    )
    .correlate_except(ClubMember)
    .scalar_subquery(),
    deferred=False,
)
