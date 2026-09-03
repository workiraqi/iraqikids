from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import TimestampMixin


class SiteSettings(TimestampMixin, db.Model):
    __tablename__ = "site_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_site_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    site_name: Mapped[str] = mapped_column(String(160))
    arabic_site_name: Mapped[str] = mapped_column(String(160))
    short_description: Mapped[str] = mapped_column(Text)
    hero_title: Mapped[str] = mapped_column(String(300))
    hero_subtitle: Mapped[str] = mapped_column(Text)
    footer_text: Mapped[str] = mapped_column(String(300))
    logo_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    favicon_path: Mapped[str | None] = mapped_column(String(300), nullable=True)

