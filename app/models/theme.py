import re

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.extensions import db
from app.models.base import TimestampMixin


HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
COLOR_FIELDS = (
    "bg",
    "bg_secondary",
    "panel",
    "text",
    "text_muted",
    "primary",
    "secondary",
    "lime",
    "cyan",
    "pink",
    "border",
    "button",
    "hover",
)


class Theme(TimestampMixin, db.Model):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    bg: Mapped[str] = mapped_column(String(7))
    bg_secondary: Mapped[str] = mapped_column(String(7))
    panel: Mapped[str] = mapped_column(String(7))
    text: Mapped[str] = mapped_column(String(7))
    text_muted: Mapped[str] = mapped_column(String(7))
    primary: Mapped[str] = mapped_column(String(7))
    secondary: Mapped[str] = mapped_column(String(7))
    lime: Mapped[str] = mapped_column(String(7))
    cyan: Mapped[str] = mapped_column(String(7))
    pink: Mapped[str] = mapped_column(String(7))
    border: Mapped[str] = mapped_column(String(7))
    button: Mapped[str] = mapped_column(String(7))
    hover: Mapped[str] = mapped_column(String(7))

    @validates(*COLOR_FIELDS)
    def validate_color(self, key: str, value: str) -> str:
        if not value or not HEX_PATTERN.fullmatch(value):
            raise ValueError(f"{key} must be a six-digit hexadecimal color")
        return value.lower()

