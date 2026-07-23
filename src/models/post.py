from __future__ import annotations
from uuid import uuid4
from sqlalchemy import String, Boolean, Text, ForeignKey, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from src.db.base import Base, TimestampMixin


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("clubs.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # 'notice': 공지 / 'general': 일반 글
    post_type: Mapped[str] = mapped_column(String(20), nullable=False, default="general")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_notice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    club = relationship("Club", back_populates="posts")
    author = relationship("User", foreign_keys=[author_id])
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    @property
    def author_name(self) -> str:
        return self.author.name if self.author else ""


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("posts.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    post = relationship("Post", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])

    @property
    def author_name(self) -> str:
        return self.author.name if self.author else ""


# ── comment_count 를 SQL 집계로 계산 (성능 최적화) ─────────────
# 기존: post_service.get_posts 에서 selectinload(Post.comments) 로
#       댓글 전체를 로드한 뒤 파이썬에서 sum(1 for c in ...) 으로 셌음
#       → 개수만 필요한데 댓글 객체를 전부 생성/전송 (Club.member_count 와 동일 패턴)
#
# 변경: DB 가 COUNT 로 숫자만 반환 → 댓글 행을 로드하지 않음
#
# 주의: 게시글 "상세"(get_post)는 댓글 내용을 실제로 사용하므로
#       그쪽의 selectinload 는 그대로 유지해야 한다.
Post.comment_count = column_property(
    select(func.count(Comment.id))
    .where(
        Comment.post_id == Post.id,
        Comment.is_deleted == False,  # noqa: E712
    )
    .correlate_except(Comment)
    .scalar_subquery(),
    deferred=False,
)
