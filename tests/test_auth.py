from app import create_app
from app.commands import seed_core
from app.extensions import db, limiter
from app.models import User


def test_admin_requires_login(client):
    response = client.get("/admin")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_login_success(auth):
    response = auth.login()
    assert response.status_code == 200
    assert "Test Admin" in response.text


def test_wrong_password_has_generic_error(auth):
    response = auth.login(password="wrong-password")
    assert response.status_code == 200
    assert "بيانات تسجيل الدخول غير صحيحة" in response.text



def test_logout(auth, client):
    auth.login()
    response = auth.logout()
    assert response.status_code == 200
    assert "تسجيل الدخول" in response.text
    assert client.get("/admin").status_code == 302


def test_login_rate_limit():
    application = create_app("testing", {"RATELIMIT_ENABLED": True})
    with application.app_context():
        db.create_all()
        seed_core()
        user = User(email="rate@example.com", display_name="Rate", role="admin", active=True)
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()
        limiter.reset()
        client = application.test_client()
        responses = [
            client.post("/admin/login", data={"email": "rate@example.com", "password": "wrong"})
            for _ in range(6)
        ]
        assert responses[-1].status_code == 429
        db.session.remove()
        db.drop_all()

