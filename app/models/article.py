from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from app.models.base import TimestampMixin


ARTICLE_STATUSES = ("draft", "review", "approved", "published", "hidden")


class Article(TimestampMixin, db.Model):
    __tablename__ = "articles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'review', 'approved', 'published', 'hidden')",
            name="ck_articles_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    slug: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )

    source_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    original_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(180), nullable=True)

    featured_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_alt: Mapped[str | None] = mapped_column(String(300), nullable=True)
    image_caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_credit: Mapped[str | None] = mapped_column(String(300), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    category = relationship("Category", backref="articles")

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in ARTICLE_STATUSES:
            raise ValueError(f"Unknown article status: {value}")
        return value

