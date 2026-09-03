from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app.auth.forms import LoginForm
from app.extensions import db, limiter
from app.models import User


bp = Blueprint("auth", __name__, url_prefix="/admin")


def is_safe_next_url(target: str | None) -> bool:
    if not target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc and target.startswith("/")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user and user.active and user.check_password(form.password.data):
            next_url = request.args.get("next")
            session.clear()
            login_user(user)
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            flash("تم تسجيل الدخول بنجاح.", "success")
            return redirect(next_url if is_safe_next_url(next_url) else url_for("admin.dashboard"))
        flash("بيانات تسجيل الدخول غير صحيحة.", "error")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        session.clear()
    flash("تم تسجيل الخروج.", "success")
    return redirect(url_for("auth.login"))

