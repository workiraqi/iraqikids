import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Category, SiteSettings, Theme, User
from app.services import DEFAULT_THEME


def test_user_password_and_role(app):
    with app.app_context():
        user = User(email="editor@example.test", display_name="Editor", role="editor", active=True)
        user.set_password("a-secure-password")
        assert user.password_hash != "a-secure-password"
        assert user.check_password("a-secure-password")
        assert user.has_role("editor")


def test_category_parent_relationship(app):
    with app.app_context():
        parent = Category(title="Parent", slug="parent", sort_order=1)
        child = Category(title="Child", slug="child", parent=parent, sort_order=2)
        db.session.add_all([parent, child])
        db.session.commit()
        assert child.parent_id == parent.id
        assert parent.children == [child]


def test_theme_rejects_invalid_hex(app):
    with app.app_context(), pytest.raises(ValueError):
        Theme(**{**DEFAULT_THEME, "name": "Broken", "bg": "red"})


def test_site_settings_is_singleton(app):
    with app.app_context():
        db.session.add(
            SiteSettings(
                id=2,
                site_name="Other",
                arabic_site_name="آخر",
                short_description="x",
                hero_title="x",
                hero_subtitle="x",
                footer_text="x",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

