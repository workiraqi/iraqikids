from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import roles_required
from app.extensions import db
from app.models import Article, Candidate, Category, Source
from app.services.translation import ArabicTranslationService, TranslationError
from app.services.content_scoring import ContentScoringService
from app.services.content import sanitize_article_body


bp = Blueprint(
    "candidate_admin",
    __name__,
    url_prefix="/admin/candidates",
)


@bp.get("/")
@login_required
@roles_required("admin", "editor", "reviewer")
def index():
    status = (request.args.get("status") or "").strip()
    source_id = request.args.get("source_id", type=int)

    stmt = (
        db.select(Candidate)
        .join(Source)
        .order_by(Candidate.id.desc())
    )

    if status:
        stmt = stmt.where(Candidate.status == status)

    if source_id:
        stmt = stmt.where(Candidate.source_id == source_id)

    candidates = db.session.scalars(stmt).all()

    sources = db.session.scalars(
        db.select(Source).order_by(Source.name.asc())
    ).all()

    return render_template(
        "admin/candidates/index.html",
        candidates=candidates,
        sources=sources,
        selected_status=status,
        selected_source_id=source_id,
    )
@bp.get("/<int:candidate_id>")
@login_required
@roles_required("admin", "editor", "reviewer")
def detail(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)
    categories = db.session.scalars(db.select(Category).order_by(Category.id)).all()

    return render_template(
        "admin/candidates/detail.html",
        candidate=candidate,
        categories=categories,
    )



@bp.post("/<int:candidate_id>/score")
@login_required
@roles_required("admin", "editor", "reviewer")
def score_candidate(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)

    result = ContentScoringService.score(
        title=candidate.title or "",
        summary=candidate.original_summary or "",
        body=candidate.original_body or "",
        source_quality=(candidate.source.quality_score if candidate.source else 5),
        originality=ContentScoringService.estimate_originality(
            title=candidate.title or "",
            summary=candidate.original_summary or "",
            body=candidate.original_body or "",
        ),
    )

    candidate.relevance_score = result.relevance
    candidate.practical_score = result.practical_value
    candidate.knowledge_score = result.knowledge_value
    candidate.adaptability_score = result.arabic_adaptability
    candidate.source_quality_score = result.source_quality
    candidate.originality_score = result.originality
    candidate.overall_score = result.overall
    candidate.content_type = result.content_type
    candidate.score_recommendation = result.recommendation
    candidate.scoring_reasons = " | ".join(result.reasons)
    candidate.scored_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(
        "تم تقييم المحتوى وحفظ النتيجة للمراجعة البشرية.",
        "success",
    )

    return redirect(
        url_for(
            "candidate_admin.detail",
            candidate_id=candidate.id,
        )
    )


@bp.post("/<int:candidate_id>/review")
@login_required
@roles_required("admin", "editor", "reviewer")
def mark_review(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)

    candidate.status = "review"
    db.session.commit()

    return redirect(
        url_for("candidate_admin.detail", candidate_id=candidate.id)
    )


@bp.post("/<int:candidate_id>/reject")
@login_required
@roles_required("admin", "editor", "reviewer")
def reject(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)

    candidate.status = "rejected"
    db.session.commit()

    return redirect(
        url_for("candidate_admin.detail", candidate_id=candidate.id)
    )

@bp.post("/<int:candidate_id>/convert")
@login_required
@roles_required("admin", "editor")
def convert(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)
    if candidate.status == "converted" and candidate.converted_article_id:
        return redirect(url_for("article_admin.edit", article_id=candidate.converted_article_id))

    arabic_title = (candidate.arabic_title or "").strip()
    arabic_summary = (candidate.arabic_summary or "").strip()
    arabic_body = (candidate.arabic_body or "").strip()

    if not arabic_title or not arabic_body:
        flash("يجب ترجمة المادة أو تحريرها بالعربية قبل تحويلها إلى مقال.", "error")
        return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))

    category_id = request.form.get("category_id", type=int)
    category = db.session.get(Category, category_id) if category_id else None
    if category is None:
        flash("اختر تصنيفًا صالحًا قبل التحويل.", "error")
        return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))

    base_slug = f"candidate-{candidate.id}"
    slug = base_slug
    counter = 2
    while db.session.scalar(db.select(Article.id).where(Article.slug == slug)):
        slug = f"{base_slug}-{counter}"
        counter += 1

    article = Article(
        title=arabic_title[:240],
        slug=slug,
        summary=(arabic_summary or arabic_title)[:2000],
        body=sanitize_article_body(arabic_body),
        category_id=category.id,
        source_name=candidate.source.name,
        source_url=candidate.original_url,
        source_language=candidate.source.language,
        original_title=candidate.title,
        author=candidate.original_author,
        status="draft",
        featured=False,
    )
    db.session.add(article)
    try:
        db.session.flush()
        candidate.status = "converted"
        candidate.converted_article_id = article.id
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("تعذر تحويل المادة إلى مقال بسبب تعارض في البيانات.", "error")
        return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))

    flash("تم تحويل النسخة العربية إلى مسودة مقال.", "success")
    return redirect(url_for("article_admin.edit", article_id=article.id))


@bp.post("/<int:candidate_id>/arabic")
@login_required
@roles_required("admin", "editor", "reviewer")
def save_arabic(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)
    candidate.arabic_title = (request.form.get("arabic_title") or "").strip() or None
    candidate.arabic_summary = (request.form.get("arabic_summary") or "").strip() or None
    candidate.arabic_body = (request.form.get("arabic_body") or "").strip() or None
    candidate.translation_status = "edited" if candidate.arabic_title or candidate.arabic_summary or candidate.arabic_body else "pending"
    db.session.commit()
    flash("تم حفظ النص العربي.", "success")
    return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))


@bp.post("/<int:candidate_id>/translate")
@login_required
@roles_required("admin", "editor", "reviewer")
def translate_arabic(candidate_id: int):
    candidate = db.get_or_404(Candidate, candidate_id)

    if candidate.translation_status == "edited" and (candidate.arabic_title or candidate.arabic_summary or candidate.arabic_body):
        flash("هذه المادة تحتوي على تحرير عربي يدوي. لم تتم إعادة الترجمة حتى لا يتم استبدال تعديلاتك.", "error")
        return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))

    try:
        result = ArabicTranslationService.translate_candidate(candidate)
    except TranslationError as exc:
        flash(f"فشلت الترجمة: {exc}", "error")
        return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))

    candidate.arabic_title = result["arabic_title"]
    candidate.arabic_summary = result["arabic_summary"]
    candidate.arabic_body = result["arabic_body"]
    candidate.translation_status = "translated"
    db.session.commit()
    flash("تمت الترجمة إلى العربية. راجع النص قبل اعتماده.", "success")
    return redirect(url_for("candidate_admin.detail", candidate_id=candidate.id))
