from app.extensions import db
from app.models import SiteSettings


class SettingsService:
    @staticmethod
    def get() -> SiteSettings | None:
        return db.session.get(SiteSettings, 1)

