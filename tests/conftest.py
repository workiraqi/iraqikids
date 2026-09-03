import pytest

from app import create_app
from app.commands import seed_core
from app.extensions import db
from app.models import User


@pytest.fixture()
def app(tmp_path):
    application = create_app("testing", {"ARTICLE_UPLOAD_FOLDER": str(tmp_path / "uploads")})
    with application.app_context():
        db.create_all()
        seed_core()
        user = User(email="admin@example.com", display_name="Test Admin", role="admin", active=True)
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def auth(client):
    class AuthActions:
        @staticmethod
        def login(email="admin@example.com", password="correct-password"):
            return client.post("/admin/login", data={"email": email, "password": password}, follow_redirects=True)

        @staticmethod
        def logout():
            return client.post("/admin/logout", follow_redirects=True)

    return AuthActions()
