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


# ============================================================
# [최적화] comment_count → SQL 집계 (column_property)
#   기존: post_service.get_posts 에서 댓글을 전부 로드한 뒤
#         파이썬 sum() 으로 개수 계산 → 댓글 객체 전부 생성/전송
#   변경: DB 가 COUNT 로 숫자만 반환 → 댓글 행을 로드하지 않음
#         (get_posts 의 selectinload(Post.comments) 도 함께 제거)
#
#   주의: 게시글 "상세"(get_post)는 댓글 내용을 실제로 사용하므로
#         그쪽 selectinload 는 그대로 유지
# ============================================================
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
