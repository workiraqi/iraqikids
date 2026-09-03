from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.extensions import db
from app.models.base import TimestampMixin


SOURCE_TYPES = ("rss", "web")
FETCH_STATUSES = ("running", "success", "failed")
CANDIDATE_STATUSES = ("new", "review", "rejected", "converted")
TRANSLATION_STATUSES = ("pending", "translated", "edited")


class Source(TimestampMixin, db.Model):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('rss', 'web')",
            name="ck_sources_source_type",
        ),
        CheckConstraint(
            "quality_score BETWEEN 0 AND 10",
            name="ck_sources_quality_score",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(240))
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)

    source_type: Mapped[str] = mapped_column(
        String(20),
        default="rss",
        index=True,
    )

    language: Mapped[str | None] = mapped_column(String(80), nullable=True)

    quality_score: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default="5",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_fetched_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    fetch_runs = relationship(
        "FetchRun",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    candidates = relationship(
        "Candidate",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    @validates("source_type")
    def validate_source_type(self, key: str, value: str) -> str:
        if value not in SOURCE_TYPES:
            raise ValueError(f"Unknown source type: {value}")
        return value


class FetchRun(TimestampMixin, db.Model):
    __tablename__ = "fetch_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_fetch_runs_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="running",
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_created: Mapped[int] = mapped_column(Integer, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source = relationship(
        "Source",
        back_populates="fetch_runs",
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in FETCH_STATUSES:
            raise ValueError(f"Unknown fetch status: {value}")
        return value


class Candidate(TimestampMixin, db.Model):
    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'review', 'rejected', 'converted')",
            name="ck_candidates_status",
        ),
        CheckConstraint(
            "translation_status IN ('pending', 'translated', 'edited')",
            name="ck_candidates_translation_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500))

    original_url: Mapped[str] = mapped_column(
        String(1000),
        unique=True,
        index=True,
    )

    original_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    original_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    original_author: Mapped[str | None] = mapped_column(
        String(240),
        nullable=True,
    )

    published_at_source: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="new",
        index=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    relevance_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    practical_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    knowledge_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    adaptability_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_quality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    originality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    overall_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    score_recommendation: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    scoring_reasons: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    scored_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
    )

    arabic_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    arabic_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    arabic_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    translation_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
    )

    converted_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source = relationship(
        "Source",
        back_populates="candidates",
    )

    converted_article = relationship(
        "Article",
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in CANDIDATE_STATUSES:
            raise ValueError(f"Unknown candidate status: {value}")
        return value

    @validates("translation_status")
    def validate_translation_status(self, key: str, value: str) -> str:
        if value not in TRANSLATION_STATUSES:
            raise ValueError(f"Unknown translation status: {value}")
        return value