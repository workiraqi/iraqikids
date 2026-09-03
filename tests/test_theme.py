from app.extensions import db
from app.models import Theme
from app.services import DEFAULT_THEME, ThemeService


def test_activate_theme_leaves_one_active(app):
    with app.app_context():
        second = Theme(**{**DEFAULT_THEME, "name": "Second"}, is_active=False, is_default=False)
        db.session.add(second)
        db.session.flush()
        ThemeService.activate(second)
        db.session.commit()
        active = db.session.scalars(db.select(Theme).where(Theme.is_active.is_(True))).all()
        assert active == [second]


def test_reset_restores_defaults(app):
    with app.app_context():
        theme = ThemeService.get_active()
        theme.bg = "#ffffff"
        ThemeService.reset(theme)
        assert theme.bg == DEFAULT_THEME["bg"]
        assert theme.pink == DEFAULT_THEME["pink"]


def test_public_page_and_styles_use_active_theme(client):
    page = client.get("/")
    css = client.get("/theme.css")
    assert page.status_code == 200
    assert "مِخيال" in page.text
    assert css.status_code == 200
    assert "--color-bg: #fff7e8" in css.text
    assert "--color-pink: #ff9ab5" in css.text


def test_theme_headers_are_secure(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]

