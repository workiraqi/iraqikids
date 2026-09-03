from flask import Blueprint, abort, current_app, render_template, request, url_for
from sqlalchemy import or_

from app.extensions import db
from app.models import Article, Category


bp = Blueprint("content", __name__)


def canonical(endpoint: str, **values) -> str:
    path = url_for(endpoint, **values)
    base = current_app.config.get("SITE_BASE_URL", "").rstrip("/")
    return f"{base}{path}" if base else url_for(endpoint, _external=True, **values)


def published_articles():
    return db.select(Article).where(Article.status == "published")


@bp.get("/articles")
def articles():
    selected_category = None
    query = published_articles().order_by(Article.published_at.desc(), Article.id.desc())
    category_slug = request.args.get("category", "").strip()
    if category_slug:
        selected_category = db.session.scalar(
            db.select(Category).where(Category.slug == category_slug, Category.visible.is_(True))
        )
        if selected_category is None:
            abort(404)
        query = query.where(Article.category_id == selected_category.id)
    page = db.paginate(
        query, page=request.args.get("page", 1, type=int), per_page=12, error_out=False
    )
    return render_template(
        "articles/index.html",
        page=page,
        selected_category=selected_category,
        canonical_url=canonical("content.articles"),
    )


@bp.get("/articles/<slug>")
def article_detail(slug: str):
    article = db.session.scalar(
        published_articles().where(Article.slug == slug)
    )
    if article is None:
        abort(404)
    related = db.session.scalars(
        published_articles()
        .where(Article.category_id == article.category_id, Article.id != article.id)
        .order_by(Article.published_at.desc(), Article.id.desc())
        .limit(3)
    ).all()
    return render_template(
        "articles/detail.html",
        article=article,
        related=related,
        is_preview=False,
        canonical_url=canonical("content.article_detail", slug=article.slug),
    )


@bp.get("/category/<slug>")
def category(slug: str):
    selected = db.session.scalar(
        db.select(Category).where(Category.slug == slug, Category.visible.is_(True))
    )
    if selected is None:
        abort(404)
    query = (
        published_articles()
        .where(Article.category_id == selected.id)
        .order_by(Article.published_at.desc(), Article.id.desc())
    )
    page = db.paginate(
        query, page=request.args.get("page", 1, type=int), per_page=12, error_out=False
    )
    return render_template(
        "articles/category.html",
        category=selected,
        page=page,
        canonical_url=canonical("content.category", slug=selected.slug),
    )


@bp.get("/search")
def search():
    term = request.args.get("q", "").strip()[:120]
    selected_category = None
    category_slug = request.args.get("category", "").strip()
    query = published_articles()
    if term:
        query = query.where(
            or_(Article.title.ilike(f"%{term}%"), Article.summary.ilike(f"%{term}%"))
        )
    else:
        query = query.where(db.false())
    if category_slug:
        selected_category = db.session.scalar(
            db.select(Category).where(Category.slug == category_slug, Category.visible.is_(True))
        )
        if selected_category is None:
            abort(404)
        query = query.where(Article.category_id == selected_category.id)
    page = db.paginate(
        query.order_by(Article.published_at.desc(), Article.id.desc()),
        page=request.args.get("page", 1, type=int),
        per_page=12,
        error_out=False,
    )
    return render_template(
        "search/index.html",
        term=term,
        page=page,
        selected_category=selected_category,
        canonical_url=canonical("content.search"),
    )
