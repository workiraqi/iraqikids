from datetime import datetime, timezone

from app.extensions import db
from app.models import Article, Category


def test_homepage_and_theme_are_dynamic(client, app):
    response = client.get("/")
    assert response.status_code == 200
    assert "المكان الذي تتحول فيه الأسئلة إلى تجارب" in response.text
    assert "shadow-as-a-drawing-tool" in response.text
    css = client.get("/theme.css")
    assert "--color-bg: #fff7e8" in css.text


def test_article_detail_category_and_search(client):
    detail = client.get("/articles/shadow-as-a-drawing-tool")
    category = client.get("/category/creativity-arts")
    search = client.get("/search?q=الورق")
    assert detail.status_code == 200
    assert "حين يصبح الظل أداة للرسم" in detail.text
    assert "الإبداع والفنون" in category.text
    assert search.status_code == 200
    assert "جسر من ورقة واحدة" in search.text


def test_hidden_article_is_not_public(client, app):
    with app.app_context():
        article = db.session.scalar(db.select(Article).where(Article.slug == "shadow-as-a-drawing-tool"))
        article.status = "hidden"
        db.session.commit()
    assert client.get("/articles/shadow-as-a-drawing-tool").status_code == 404


def test_article_pagination(client, app):
    with app.app_context():
        category_id = db.session.scalar(db.select(Category.id).order_by(Category.id))
        for index in range(4):
            db.session.add(Article(title=f"Extra {index}", slug=f"extra-{index}", summary="summary", body="<p>body</p>", category_id=category_id, status="published", published_at=datetime.now(timezone.utc)))
        db.session.commit()
    response = client.get("/articles?page=2")
    assert response.status_code == 200
    assert 'aria-current="page">2' in response.text


def test_search_category_filter_and_empty_state(client):
    filtered = client.get("/search?q=الظل&category=creativity-arts")
    empty = client.get("/search?q=عبارة-غير-موجودة")
    assert filtered.status_code == 200
    assert "حين يصبح الظل أداة للرسم" in filtered.text
    assert "لم نعثر على نتيجة" in empty.text


def test_sitemap_and_error_pages(client):
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "shadow-as-a-drawing-tool" in sitemap.text
    assert client.get("/not-found").status_code == 404
