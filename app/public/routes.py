from flask import Blueprint, Response, abort, render_template

from app.extensions import db
from app.models import Article, Category
from app.public.content import canonical
from app.services import SettingsService, ThemeService


bp = Blueprint("public", __name__)

HOME_SECTION_SLUGS = (
    "creativity-arts",
    "science-innovation",
    "parents-teachers",
    "from-the-world",
    "books-stories",
)


def published_query():
    return db.select(Article).where(Article.status == "published")


@bp.get("/")
def home():
    settings = SettingsService.get()
    categories = db.session.scalars(
        db.select(Category)
        .where(Category.visible.is_(True))
        .order_by(Category.sort_order, Category.title)
    ).all()

    featured = list(
        db.session.scalars(
            published_query()
            .where(Article.featured.is_(True))
            .order_by(Article.published_at.desc(), Article.id.desc())
            .limit(3)
        )
    )
    used_ids = {article.id for article in featured}
    if len(featured) < 3:
        fill_query = published_query().order_by(Article.published_at.desc(), Article.id.desc())
        if used_ids:
            fill_query = fill_query.where(Article.id.notin_(used_ids))
        fill = list(db.session.scalars(fill_query.limit(3 - len(featured))))
        featured.extend(fill)
        used_ids.update(article.id for article in fill)

    sections = []
    for slug in HOME_SECTION_SLUGS:
        category = next((item for item in categories if item.slug == slug), None)
        if category is None:
            continue
        query = (
            published_query()
            .where(Article.category_id == category.id)
            .order_by(Article.published_at.desc(), Article.id.desc())
        )
        if used_ids:
            query = query.where(Article.id.notin_(used_ids))
        articles = list(db.session.scalars(query.limit(3)))
        if articles:
            sections.append({"category": category, "articles": articles})
            used_ids.update(article.id for article in articles)

    latest_query = published_query().order_by(Article.published_at.desc(), Article.id.desc())
    if used_ids:
        latest_query = latest_query.where(Article.id.notin_(used_ids))
    latest = list(db.session.scalars(latest_query.limit(6)))

    floating_cards = (
        {"eyebrow": "تحدّي اليوم", "title": "ابنِ جسراً من الورق", "position": "one"},
        {"eyebrow": "من اليابان", "title": "التعلّم بالملاحظة", "position": "two"},
        {"eyebrow": "6–9 سنوات", "title": "ارسم صوت المطر", "position": "three"},
    )
    return render_template(
        "home/index.html",
        settings=settings,
        categories=categories,
        featured_articles=featured,
        content_sections=sections,
        latest_articles=latest,
        floating_cards=floating_cards,
        canonical_url=canonical("public.home"),
    )


@bp.get("/theme.css")
def theme_css():
    theme = ThemeService.get_active()
    if theme is None:
        abort(503)
    response = Response(ThemeService.to_css(theme), mimetype="text/css")
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.get("/sitemap.xml")
def sitemap():
    articles = db.session.scalars(
        published_query().order_by(Article.published_at.desc(), Article.id.desc())
    ).all()
    categories = db.session.scalars(
        db.select(Category).where(Category.visible.is_(True)).order_by(Category.sort_order)
    ).all()
    return Response(
        render_template("seo/sitemap.xml", articles=articles, categories=categories),
        mimetype="application/xml",
    )


@bp.get("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\nDisallow: /admin/\n", mimetype="text/plain")
