from app import create_app
from app.commands import seed_core
from app.extensions import db
from app.models import Candidate, Source, User


def test_csrf_blocks_post_without_token():
    application = create_app("testing", {"WTF_CSRF_ENABLED": True})
    client = application.test_client()
    response = client.post(
        "/admin/login",
        data={"email": "nobody@example.com", "password": "wrong"},
    )
    assert response.status_code == 400


def test_reviewer_cannot_create_article():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seed_core()
        user = User(
            email="reviewer@example.com",
            display_name="Reviewer",
            role="reviewer",
            active=True,
        )
        user.set_password("correct-password")
        db.session.add(user)
        db.session.commit()

        client = application.test_client()
        client.post(
            "/admin/login",
            data={"email": "reviewer@example.com", "password": "correct-password"},
        )
        response = client.get("/admin/articles/new")
        assert response.status_code == 403

        db.session.remove()
        db.drop_all()


def test_candidate_summary_is_escaped_for_admin(auth, client, app):
    auth.login()
    with app.app_context():
        source = Source(
            name="Security Source",
            url="https://security.example",
            source_type="web",
            language="en",
            is_active=True,
        )
        db.session.add(source)
        db.session.flush()
        candidate = Candidate(
            source_id=source.id,
            title="Security candidate",
            original_url="https://security.example/item",
            original_summary='<img src=x onerror="alert(1)"><script>alert(2)</script>',
            status="new",
        )
        db.session.add(candidate)
        db.session.commit()
        candidate_id = candidate.id

    response = client.get(f"/admin/candidates/{candidate_id}")
    assert response.status_code == 200
    assert "<script>alert(2)</script>" not in response.text
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in response.text
    assert "onerror=" not in response.text or "&lt;img" in response.text


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
