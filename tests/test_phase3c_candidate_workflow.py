from unittest.mock import patch

from app.extensions import db
from app.models import Article, Candidate, Category, Source


def _make_source_and_candidate(
    app,
    *,
    translated=False,
    edited=False,
):
    with app.app_context():
        source = Source(
            name="Phase 3C Workflow Source",
            url="https://workflow.example",
            source_type="web",
            language="en",
            is_active=True,
        )
        db.session.add(source)
        db.session.flush()

        candidate = Candidate(
            source_id=source.id,
            title="Creative Science for Children",
            original_url="https://workflow.example/blog/creative-science-children",
            original_summary="A useful science activity for children.",
            original_body="Children experiment with simple materials.",
            original_author="Source Author",
            status="new",
        )

        if translated or edited:
            candidate.arabic_title = "تجربة علمية إبداعية للأطفال"
            candidate.arabic_summary = "نشاط علمي بسيط يشجع الأطفال على التجريب."
            candidate.arabic_body = (
                "يستطيع الأطفال تنفيذ تجربة بسيطة باستخدام مواد متاحة، "
                "مع الملاحظة وطرح الأسئلة ومناقشة النتائج."
            )

        if edited:
            candidate.translation_status = "edited"
        elif translated:
            candidate.translation_status = "translated"

        db.session.add(candidate)
        db.session.commit()

        return candidate.id


def test_save_arabic_marks_candidate_as_edited(app, client, auth):
    candidate_id = _make_source_and_candidate(app)

    auth.login()

    response = client.post(
        f"/admin/candidates/{candidate_id}/arabic",
        data={
            "arabic_title": "عنوان محرر يدويًا",
            "arabic_summary": "ملخص محرر",
            "arabic_body": "هذا متن عربي حرره المستخدم يدويًا.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.translation_status == "edited"
        assert candidate.arabic_title == "عنوان محرر يدويًا"
        assert candidate.arabic_body == "هذا متن عربي حرره المستخدم يدويًا."


def test_translate_does_not_overwrite_manually_edited_text(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(
        app,
        edited=True,
    )

    auth.login()

    with patch(
        "app.admin.candidates.ArabicTranslationService.translate_candidate"
    ) as translate:
        response = client.post(
            f"/admin/candidates/{candidate_id}/translate",
            follow_redirects=False,
        )

    assert response.status_code == 302
    translate.assert_not_called()

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.translation_status == "edited"
        assert candidate.arabic_title == "تجربة علمية إبداعية للأطفال"


def test_convert_rejects_candidate_without_arabic_content(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(app)

    auth.login()

    with app.app_context():
        category = db.session.scalar(
            db.select(Category).order_by(Category.id)
        )
        category_id = category.id

    response = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": category_id},
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)
        articles = db.session.scalars(
            db.select(Article).where(
                Article.original_title
                == "Creative Science for Children"
            )
        ).all()

        assert candidate.status == "new"
        assert candidate.converted_article_id is None
        assert articles == []


def test_convert_rejects_invalid_category(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(
        app,
        translated=True,
    )

    auth.login()

    response = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": 999999},
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.status == "new"
        assert candidate.converted_article_id is None


def test_convert_creates_draft_article_and_links_candidate(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(
        app,
        translated=True,
    )

    auth.login()

    with app.app_context():
        category = db.session.scalar(
            db.select(Category).order_by(Category.id)
        )
        category_id = category.id

    response = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": category_id},
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        assert candidate.status == "converted"
        assert candidate.converted_article_id is not None

        article = db.session.get(
            Article,
            candidate.converted_article_id,
        )

        assert article is not None
        assert article.status == "draft"
        assert article.title == "تجربة علمية إبداعية للأطفال"
        assert article.category_id == category_id
        assert article.source_name == "Phase 3C Workflow Source"
        assert article.source_url == (
            "https://workflow.example/blog/creative-science-children"
        )
        assert article.source_language == "en"
        assert article.original_title == "Creative Science for Children"
        assert article.author == "Source Author"
        assert article.featured is False


def test_second_conversion_does_not_create_duplicate_article(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(
        app,
        translated=True,
    )

    auth.login()

    with app.app_context():
        category = db.session.scalar(
            db.select(Category).order_by(Category.id)
        )
        category_id = category.id

    first = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": category_id},
        follow_redirects=False,
    )

    assert first.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)
        first_article_id = candidate.converted_article_id

    second = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": category_id},
        follow_redirects=False,
    )

    assert second.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)

        articles = db.session.scalars(
            db.select(Article).where(
                Article.original_title
                == "Creative Science for Children"
            )
        ).all()

        assert candidate.converted_article_id == first_article_id
        assert len(articles) == 1

def test_candidate_to_published_article_requires_manual_article_gates(
    app,
    client,
    auth,
):
    candidate_id = _make_source_and_candidate(app, translated=True)
    auth.login()

    with app.app_context():
        category_id = db.session.scalar(
            db.select(Category.id).order_by(Category.id)
        )

    response = client.post(
        f"/admin/candidates/{candidate_id}/convert",
        data={"category_id": category_id},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        candidate = db.session.get(Candidate, candidate_id)
        article_id = candidate.converted_article_id
        article = db.session.get(Article, article_id)
        assert candidate.status == "converted"
        assert article.status == "draft"
        assert article.published_at is None
        assert article.source_name == "Phase 3C Workflow Source"
        assert article.source_url == (
            "https://workflow.example/blog/creative-science-children"
        )

    direct_publish = client.post(
        f"/admin/articles/{article_id}/publish",
        follow_redirects=True,
    )
    assert "Only an approved article can be published." in direct_publish.text

    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "draft"
        assert article.published_at is None

    client.post(f"/admin/articles/{article_id}/review")
    client.post(f"/admin/articles/{article_id}/approve")

    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "approved"
        assert article.approved_at is not None
        assert article.published_at is None

    client.post(f"/admin/articles/{article_id}/publish")

    with app.app_context():
        article = db.session.get(Article, article_id)
        assert article.status == "published"
        assert article.published_at is not None
