from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import Article, Category
from app.services.content import sanitize_article_body
from app.services.publishing import PublishingService


def article_form_data(category_id, **overrides):
    data = {
        "title": "مسودة جديدة",
        "slug": "new-draft",
        "summary": "ملخص عربي قصير للمقال.",
        "body": "<p>نص آمن</p>",
        "category_id": category_id,
        "author": "محرر",
        "source_name": "",
        "source_url": "",
        "source_language": "",
        "original_title": "",
        "image_alt": "",
        "image_caption": "",
        "image_credit": "",
    }
    data.update(overrides)
    return data


def first_category_id(app):
    with app.app_context():
        return db.session.scalar(db.select(Category.id).order_by(Category.id))


def test_article_rejects_unknown_status(app):
    with app.app_context(), pytest.raises(ValueError):
        Article(title="x", slug="x", summary="x", body="x", category_id=1, status="unknown")


def test_create_draft_requires_admin(client, app):
    response = client.get("/admin/articles/new")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_create_edit_and_duplicate_slug(client, app, auth):
    auth.login()
    category_id = first_category_id(app)
    response = client.post(
        "/admin/articles/new", data=article_form_data(category_id), follow_redirects=True
    )
    assert "تم إنشاء مسودة المقال" in response.text
    with app.app_context():
        article = db.session.scalar(db.select(Article).where(Article.slug == "new-draft"))
        assert article.status == "draft"
        article_id = article.id
    edited = article_form_data(
        category_id,
        title="عنوان محرر",
        body="<p>آمن</p><script>alert(1)</script><iframe src='x'></iframe>",
    )
    response = client.post(
        f"/admin/articles/{article_id}/edit", data=edited, follow_redirects=True
    )
    assert "تم حفظ المقال" in response.text
    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.title == "عنوان محرر"
        assert "script" not in article.body
        assert "iframe" not in article.body
    duplicate = article_form_data(category_id, title="مكرر")
    response = client.post("/admin/articles/new", data=duplicate)
    assert "مستخدم مسبقًا" in response.text


def test_publish_hide_and_public_visibility(client, app, auth):
    category_id = first_category_id(app)
    with app.app_context():
        article = Article(
            title="سري قبل النشر",
            slug="private-draft",
            summary="ملخص",
            body="<p>نص</p>",
            category_id=category_id,
            status="draft",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id
    assert client.get("/articles/private-draft").status_code == 404
    auth.login()
    client.post(f"/admin/articles/{article_id}/review")
    client.post(f"/admin/articles/{article_id}/approve")
    client.post(f"/admin/articles/{article_id}/publish")
    assert client.get("/articles/private-draft").status_code == 200
    client.post(f"/admin/articles/{article_id}/hide")
    assert client.get("/articles/private-draft").status_code == 404


def test_publishing_service_restore(app):
    with app.app_context():
        category_id = db.session.scalar(db.select(Category.id).order_by(Category.id))
        article = Article(title="Flow", slug="flow", summary="x", body="<p>x</p>", category_id=category_id, status="draft")
        PublishingService.submit_for_review(article)
        PublishingService.approve(article)
        PublishingService.publish(article)
        assert article.status == "published"
        assert article.published_at is not None
        PublishingService.hide(article)
        assert article.status == "hidden"
        PublishingService.restore(article)
        assert article.status == "published"


def test_sanitizer_strips_unsafe_html_and_protocols():
    cleaned = sanitize_article_body(
        '<p>safe</p><script>alert(1)</script><iframe src="x"></iframe><a href="javascript:bad">bad</a>'
    )
    assert "script" not in cleaned
    assert "iframe" not in cleaned
    assert "javascript:" not in cleaned
    assert "<p>safe</p>" in cleaned



def test_draft_cannot_publish_without_review_and_approval(client, app, auth):
    category_id = first_category_id(app)
    with app.app_context():
        article = Article(
            title="Manual workflow",
            slug="manual-workflow",
            summary="x",
            body="<p>x</p>",
            category_id=category_id,
            status="draft",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id

    auth.login()
    response = client.post(
        f"/admin/articles/{article_id}/publish",
        follow_redirects=True,
    )
    assert "Only an approved article can be published." in response.text

    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "draft"
        assert article.published_at is None


def test_full_manual_article_workflow(client, app, auth):
    category_id = first_category_id(app)
    with app.app_context():
        article = Article(
            title="Workflow",
            slug="workflow-gated",
            summary="x",
            body="<p>x</p>",
            category_id=category_id,
            status="draft",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id

    auth.login()
    client.post(f"/admin/articles/{article_id}/review")
    with app.app_context():
        assert db.session.get(Article, article_id).status == "review"

    client.post(f"/admin/articles/{article_id}/approve")
    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "approved"
        assert article.approved_at is not None
        assert article.published_at is None

    assert client.get("/articles/workflow-gated").status_code == 404

    client.post(f"/admin/articles/{article_id}/publish")
    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "published"
        assert article.published_at is not None

    assert client.get("/articles/workflow-gated").status_code == 200
