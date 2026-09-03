from app.extensions import db
from app.models import Theme
from app.models.theme import COLOR_FIELDS, HEX_PATTERN


DEFAULT_THEME = {
    "name": "Iraqi Kids Warm Creative",
    "bg": "#fff7e8",
    "bg_secondary": "#f2ebff",
    "panel": "#fffdf7",
    "text": "#14213d",
    "text_muted": "#5f6472",
    "primary": "#ff6257",
    "secondary": "#7467f0",
    "lime": "#f5c84c",
    "cyan": "#77cbea",
    "pink": "#ff9ab5",
    "border": "#d9d0c2",
    "button": "#f05249",
    "hover": "#c83f39",
}


class ThemeService:
    CSS_NAMES = {field: f"--color-{field.replace('_', '-')}" for field in COLOR_FIELDS}

    @staticmethod
    def get_active() -> Theme | None:
        return db.session.scalar(db.select(Theme).where(Theme.is_active.is_(True)))

    @staticmethod
    def activate(theme: Theme) -> None:
        for active in db.session.scalars(
            db.select(Theme).where(Theme.is_active.is_(True), Theme.id != theme.id)
        ):
            active.is_active = False
        theme.is_active = True

    @staticmethod
    def reset(theme: Theme) -> None:
        for field in COLOR_FIELDS:
            setattr(theme, field, DEFAULT_THEME[field])

    @staticmethod
    def validate_values(values: dict[str, str]) -> bool:
        return all(HEX_PATTERN.fullmatch(values.get(field, "")) for field in COLOR_FIELDS)

    @classmethod
    def to_css(cls, theme: Theme) -> str:
        declarations = "\n".join(
            f"  {cls.CSS_NAMES[field]}: {getattr(theme, field)};" for field in COLOR_FIELDS
        )
        return f":root {{\n{declarations}\n}}\n"
