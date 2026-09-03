from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.admin.article_forms import ArticleForm
from app.auth.permissions import roles_required
from app.extensions import db
from app.media import ArticleImageService, ImageValidationError
from app.models import ARTICLE_STATUSES, Article, Category
from app.services.content import sanitize_article_body
from app.services.publishing import PublishingError, PublishingService


bp = Blueprint("article_admin", __name__, url_prefix="/admin/articles")

EDITABLE_FIELDS = (
    "title",
    "slug",
    "summary",
    "category_id",
    "author",
    "source_name",
    "source_url",
    "source_language",
    "original_title",
    "image_alt",
    "image_caption",
    "image_credit",
    "featured",
)


def set_category_choices(form: ArticleForm) -> None:
    categories = db.session.scalars(
        db.select(Category).order_by(Category.sort_order, Category.title)
    ).all()
    form.category_id.choices = [(category.id, category.title) for category in categories]


def apply_form(article: Article, form: ArticleForm) -> None:
    for field in EDITABLE_FIELDS:
        value = getattr(form, field).data
        if isinstance(value, str):
            value = value.strip() or None
        setattr(article, field, value)
    article.body = sanitize_article_body(form.body.data)


def handle_image(article: Article, form: ArticleForm) -> str | None:
    previous = article.featured_image
    upload = form.image.data
    if upload and upload.filename:
        article.featured_image = ArticleImageService.save(upload)
        return previous
    if form.remove_image.data:
        article.featured_image = None
        return previous
    return None


@bp.get("")
@roles_required("admin", "editor", "reviewer")
def index():
    selected_status = request.args.get("status", "").strip()
    query = db.select(Article).order_by(Article.updated_at.desc())
    if selected_status in ARTICLE_STATUSES:
        query = query.where(Article.status == selected_status)
    page = db.paginate(query, page=request.args.get("page", 1, type=int), per_page=20, error_out=False)
    return render_template(
        "admin/articles/index.html",
        page=page,
        statuses=ARTICLE_STATUSES,
        selected_status=selected_status,
    )


@bp.route("/new", methods=["GET", "POST"])
@roles_required("admin", "editor")
def create():
    form = ArticleForm()
    set_category_choices(form)
    if form.validate_on_submit():
        article = Article(status="draft", title="", slug="", summary="", body="", category_id=0)
        apply_form(article, form)
        db.session.add(article)
        new_image = None
        try:
            handle_image(article, form)
            new_image = article.featured_image
            db.session.commit()
        except ImageValidationError as exc:
            db.session.rollback()
            form.image.errors.append(str(exc))
        except IntegrityError:
            db.session.rollback()
            if new_image:
                ArticleImageService.delete(new_image)
            form.slug.errors.append("هذا الـslug مستخدم مسبقًا.")
        else:
            flash("تم إنشاء مسودة المقال.", "success")
            return redirect(url_for("article_admin.edit", article_id=article.id))
    return render_template("admin/articles/form.html", form=form, article=None, page_title="مقال جديد")


@bp.route("/<int:article_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "editor")
def edit(article_id: int):
    article = db.get_or_404(Article, article_id)
    form = ArticleForm(obj=article)
    set_category_choices(form)
    if form.validate_on_submit():
        apply_form(article, form)
        previous_image = None
        new_image = None
        try:
            previous_image = handle_image(article, form)
            new_image = article.featured_image if article.featured_image != previous_image else None
            db.session.commit()
        except ImageValidationError as exc:
            db.session.rollback()
            form.image.errors.append(str(exc))
        except IntegrityError:
            db.session.rollback()
            if new_image:
                ArticleImageService.delete(new_image)
            form.slug.errors.append("هذا الـslug مستخدم مسبقًا.")
        else:
            if previous_image:
                ArticleImageService.delete(previous_image)
            flash("تم حفظ المقال.", "success")
            return redirect(url_for("article_admin.edit", article_id=article.id))
    return render_template(
        "admin/articles/form.html", form=form, article=article, page_title="تعديل المقال"
    )


@bp.get("/<int:article_id>/preview")
@roles_required("admin", "editor", "reviewer")
def preview(article_id: int):
    article = db.get_or_404(Article, article_id)
    return render_template(
        "articles/detail.html", article=article, related=[], is_preview=True, canonical_url=None
    )


@bp.post("/<int:article_id>/review")
@roles_required("admin", "editor")
def submit_for_review(article_id: int):
    article = db.get_or_404(Article, article_id)
    try:
        PublishingService.submit_for_review(article)
    except PublishingError as exc:
        flash(str(exc), "error")
    else:
        db.session.commit()
        flash("تم إرسال المقال للمراجعة.", "success")
    return redirect(url_for("article_admin.index"))


@bp.post("/<int:article_id>/approve")
@roles_required("admin", "reviewer")
def approve(article_id: int):
    article = db.get_or_404(Article, article_id)
    try:
        PublishingService.approve(article)
    except PublishingError as exc:
        flash(str(exc), "error")
    else:
        db.session.commit()
        flash("تم اعتماد المقال وأصبح جاهزًا للنشر.", "success")
    return redirect(url_for("article_admin.index"))


@bp.post("/<int:article_id>/publish")
@roles_required("admin", "reviewer")
def publish(article_id: int):
    article = db.get_or_404(Article, article_id)
    try:
        PublishingService.publish(article)
    except PublishingError as exc:
        flash(str(exc), "error")
    else:
        db.session.commit()
        flash("تم نشر المقال.", "success")
    return redirect(url_for("article_admin.index"))


@bp.post("/<int:article_id>/hide")
@roles_required("admin", "editor", "reviewer")
def hide(article_id: int):
    article = db.get_or_404(Article, article_id)
    try:
        PublishingService.hide(article)
    except PublishingError as exc:
        flash(str(exc), "error")
    else:
        db.session.commit()
        flash("تم إخفاء المقال.", "success")
    return redirect(url_for("article_admin.index"))


@bp.post("/<int:article_id>/restore")
@roles_required("admin", "editor", "reviewer")
def restore(article_id: int):
    article = db.get_or_404(Article, article_id)
    try:
        PublishingService.restore(article)
    except PublishingError as exc:
        flash(str(exc), "error")
    else:
        db.session.commit()
        flash("تمت استعادة المقال.", "success")
    return redirect(url_for("article_admin.index"))


@bp.post("/<int:article_id>/delete")
@roles_required("admin")
def delete(article_id: int):
    article = db.get_or_404(Article, article_id)
    image = article.featured_image
    db.session.delete(article)
    db.session.commit()
    ArticleImageService.delete(image)
    flash("تم حذف المقال.", "success")
    return redirect(url_for("article_admin.index"))

