from sqlalchemy import String, Text, DateTime, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    linkedin_urn: Mapped[str | None] = mapped_column(String(128))
    linkedin_access_token: Mapped[str | None] = mapped_column(Text)
    linkedin_refresh_token: Mapped[str | None] = mapped_column(Text)
    linkedin_token_expires_at: Mapped[DateTime | None] = mapped_column(DateTime)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    drafts: Mapped[list["Draft"]] = relationship("Draft", back_populates="user")
    published_posts: Mapped[list["PublishedPost"]] = relationship(
        "PublishedPost", back_populates="user"
    )


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    topic: Mapped[str] = mapped_column(String(512))
    tone: Mapped[str] = mapped_column(String(64), default="professional")
    target_audience: Mapped[str | None] = mapped_column(String(256))
    post_text: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_notes: Mapped[str | None] = mapped_column(Text)
    character_count: Mapped[int | None] = mapped_column(Integer)
    selected_image_url: Mapped[str | None] = mapped_column(Text)
    pexels_queries: Mapped[str | None] = mapped_column(Text)  # JSON list of {query, style} dicts
    status: Mapped[str] = mapped_column(String(32), default="generating")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="drafts")
    published_post: Mapped["PublishedPost | None"] = relationship(
        "PublishedPost", back_populates="draft"
    )


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    draft_id: Mapped[int] = mapped_column(Integer, ForeignKey("drafts.id"))
    linkedin_post_id: Mapped[str | None] = mapped_column(String(256))
    linkedin_post_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="published_posts")
    draft: Mapped["Draft"] = relationship("Draft", back_populates="published_post")
