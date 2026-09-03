from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.admin.source_forms import SourceForm
from app.auth.permissions import roles_required
from app.extensions import db
from app.models import Source
from app.services.fetching import FetchError, SourceFetchService


bp = Blueprint(
    "source_admin",
    __name__,
    url_prefix="/admin/sources",
)


@bp.get("")
@roles_required("admin", "editor", "reviewer")
def index():
    selected_status = request.args.get("status", "").strip()

    query = db.select(Source).order_by(
        Source.is_active.desc(),
        Source.name,
    )

    if selected_status == "active":
        query = query.where(Source.is_active.is_(True))
    elif selected_status == "inactive":
        query = query.where(Source.is_active.is_(False))

    sources = db.session.scalars(query).all()

    return render_template(
        "admin/sources/index.html",
        sources=sources,
        selected_status=selected_status,
    )


@bp.route("/new", methods=["GET", "POST"])
@roles_required("admin", "editor")
def create():
    form = SourceForm()

    if form.validate_on_submit():
        source = Source(
            name=form.name.data.strip(),
            url=form.url.data.strip(),
            source_type=form.source_type.data,
            language=(form.language.data or "").strip() or None,
            quality_score=form.quality_score.data,
            notes=(form.notes.data or "").strip() or None,
            is_active=form.is_active.data,
        )

        db.session.add(source)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.url.errors.append(
                "هذا المصدر موجود مسبقًا."
            )
        else:
            flash("تمت إضافة المصدر.", "success")
            return redirect(url_for("source_admin.index"))

    return render_template(
        "admin/sources/form.html",
        form=form,
        source=None,
        page_title="إضافة مصدر",
    )


@bp.route("/<int:source_id>/edit", methods=["GET", "POST"])
@roles_required("admin", "editor")
def edit(source_id: int):
    source = db.get_or_404(Source, source_id)
    form = SourceForm(obj=source)

    if form.validate_on_submit():
        source.name = form.name.data.strip()
        source.url = form.url.data.strip()
        source.source_type = form.source_type.data
        source.language = (form.language.data or "").strip() or None
        source.quality_score = form.quality_score.data
        source.notes = (form.notes.data or "").strip() or None
        source.is_active = form.is_active.data

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.url.errors.append(
                "هذا الرابط مستخدم لمصدر آخر."
            )
        else:
            flash("تم تحديث المصدر.", "success")
            return redirect(url_for("source_admin.index"))

    return render_template(
        "admin/sources/form.html",
        form=form,
        source=source,
        page_title="تعديل المصدر",
    )


@bp.post("/<int:source_id>/toggle")
@roles_required("admin", "editor")
def toggle(source_id: int):
    source = db.get_or_404(Source, source_id)

    source.is_active = not source.is_active
    db.session.commit()

    if source.is_active:
        flash("تم تفعيل المصدر.", "success")
    else:
        flash("تم تعطيل المصدر.", "success")

    return redirect(url_for("source_admin.index"))


@bp.post("/<int:source_id>/delete")
@roles_required("admin")
def delete(source_id: int):
    source = db.get_or_404(Source, source_id)

    if source.candidates or source.fetch_runs:
        flash(
            "لا يمكن حذف هذا المصدر لأنه مرتبط بسجل جلب أو بمواد مرشحة. يمكنك تعطيله بدلًا من حذفه.",
            "error",
        )
        return redirect(url_for("source_admin.index"))

    db.session.delete(source)
    db.session.commit()

    flash("تم حذف المصدر.", "success")
    return redirect(url_for("source_admin.index"))

@bp.post("/<int:source_id>/fetch")
@roles_required("admin", "editor", "reviewer")
def fetch_now(source_id: int):
    source = db.get_or_404(Source, source_id)
    try:
        run = SourceFetchService.fetch(source)
    except FetchError as exc:
        flash(f"فشل الجلب: {exc}", "error")
    else:
        flash(f"اكتمل الجلب: تم العثور على {run.items_found}، أضيف {run.items_created}، وتم تخطي {run.items_skipped}.", "success")
    return redirect(url_for("source_admin.index"))
