from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.admin.forms import BrandingForm, CategoryForm, ThemeForm
from app.auth.permissions import roles_required
from app.extensions import db
from app.models import Category, Theme
from app.models.theme import COLOR_FIELDS
from app.services import DEFAULT_THEME, SettingsService, ThemeService


bp = Blueprint("admin", __name__, url_prefix="/admin")


def set_parent_choices(form: CategoryForm, current: Category | None = None) -> None:
    query = db.select(Category).order_by(Category.sort_order, Category.title)
    categories = list(db.session.scalars(query))
    excluded = {current.id} if current else set()
    if current:
        excluded.update(child.id for child in current.children)
    form.parent_id.choices = [(0, "— بدون تصنيف أب —")] + [
        (category.id, category.title) for category in categories if category.id not in excluded
    ]


@bp.get("")
@login_required
def dashboard():
    settings = SettingsService.get()
    category_count = db.session.scalar(db.select(db.func.count(Category.id))) or 0
    return render_template(
        "admin/dashboard.html",
        settings=settings,
        category_count=category_count,
        active_theme=ThemeService.get_active(),
    )


@bp.get("/categories")
@login_required
def categories():
    items = db.session.scalars(
        db.select(Category).order_by(Category.sort_order, Category.title)
    ).all()
    return render_template("admin/categories/list.html", categories=items)


@bp.route("/categories/new", methods=["GET", "POST"])
@roles_required("admin", "editor")
def category_new():
    form = CategoryForm(visible=True, sort_order=0)
    set_parent_choices(form)
    if form.validate_on_submit():
        category = Category()
        form.populate_obj(category)
        category.parent_id = form.parent_id.data or None
        db.session.add(category)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.slug.errors.append("هذا الـslug مستخدم مسبقًا.")
        else:
            flash("تمت إضافة التصنيف.", "success")
            return redirect(url_for("admin.categories"))
    return render_template("admin/categories/form.html", form=form, page_title="إضافة تصنيف")


@bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "editor")
def category_edit(category_id: int):
    category = db.get_or_404(Category, category_id)
    form = CategoryForm(obj=category)
    set_parent_choices(form, category)
    if form.validate_on_submit():
        form.populate_obj(category)
        category.parent_id = form.parent_id.data or None
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.slug.errors.append("هذا الـslug مستخدم مسبقًا.")
        else:
            flash("تم تحديث التصنيف.", "success")
            return redirect(url_for("admin.categories"))
    elif not form.is_submitted():
        form.parent_id.data = category.parent_id or 0
    return render_template("admin/categories/form.html", form=form, page_title="تعديل تصنيف")


@bp.post("/categories/<int:category_id>/toggle")
@roles_required("admin", "editor")
def category_toggle(category_id: int):
    category = db.get_or_404(Category, category_id)
    category.visible = not category.visible
    db.session.commit()
    flash("تم تحديث حالة الظهور.", "success")
    return redirect(url_for("admin.categories"))


@bp.post("/categories/<int:category_id>/delete")
@roles_required("admin")
def category_delete(category_id: int):
    category = db.get_or_404(Category, category_id)
    if category.children:
        flash("لا يمكن حذف تصنيف يحتوي على تصنيفات فرعية.", "error")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("تم حذف التصنيف.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/appearance/theme", methods=["GET", "POST"])
@roles_required("admin")
def theme_edit():
    theme = ThemeService.get_active()
    if theme is None:
        abort(503, "Theme has not been initialized")
    form = ThemeForm(obj=theme)
    if form.validate_on_submit():
        values = {field: getattr(form, field).data for field in COLOR_FIELDS}
        if not ThemeService.validate_values(values):
            abort(400)
        for field, value in values.items():
            setattr(theme, field, value)
        ThemeService.activate(theme)
        db.session.commit()
        flash("تم حفظ ألوان المظهر.", "success")
        return redirect(url_for("admin.theme_edit"))
    return render_template(
        "admin/appearance/theme.html", form=form, theme=theme, color_fields=COLOR_FIELDS
    )


@bp.post("/appearance/theme/reset")
@roles_required("admin")
def theme_reset():
    theme = ThemeService.get_active()
    if theme is None:
        abort(503)
    ThemeService.reset(theme)
    db.session.commit()
    flash("تمت استعادة الألوان الافتراضية.", "success")
    return redirect(url_for("admin.theme_edit"))


@bp.route("/appearance/branding", methods=["GET", "POST"])
@roles_required("admin", "editor")
def branding_edit():
    settings = SettingsService.get()
    if settings is None:
        abort(503, "Site settings have not been initialized")
    form = BrandingForm(obj=settings)
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash("تم حفظ الهوية والنصوص.", "success")
        return redirect(url_for("admin.branding_edit"))
    return render_template("admin/appearance/branding.html", form=form)

