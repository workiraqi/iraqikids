from app.extensions import db
from app.models import Category


CATEGORY_DATA = {
    "title": "تصنيف جديد",
    "slug": "new-category",
    "description": "وصف",
    "icon": "spark",
    "accent_color": "#d9ff64",
    "visible": "y",
    "sort_order": 20,
    "parent_id": 0,
}


def test_create_category(app, client, auth):
    auth.login()
    response = client.post("/admin/categories/new", data=CATEGORY_DATA, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(Category).where(Category.slug == "new-category"))


def test_edit_and_toggle_category(app, client, auth):
    auth.login()
    with app.app_context():
        category = db.session.scalar(db.select(Category).where(Category.slug == "videos"))
        category_id = category.id
    edited = {**CATEGORY_DATA, "title": "فيديو آمن", "slug": "videos", "sort_order": 8}
    response = client.post(
        f"/admin/categories/{category_id}/edit", data=edited, follow_redirects=True
    )
    assert "تم تحديث التصنيف" in response.text
    client.post(f"/admin/categories/{category_id}/toggle")
    with app.app_context():
        assert db.session.get(Category, category_id).visible is False


def test_duplicate_slug_prevention(app, client, auth):
    auth.login()
    duplicate = {**CATEGORY_DATA, "slug": "videos"}
    response = client.post("/admin/categories/new", data=duplicate)
    assert response.status_code == 200
    assert "مستخدم مسبقًا" in response.text
    with app.app_context():
        matches = db.session.scalars(db.select(Category).where(Category.slug == "videos")).all()
        assert len(matches) == 1
