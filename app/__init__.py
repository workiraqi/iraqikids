import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from pathlib import Path
from flask import Flask, g

from app.commands import register_commands
from app.config import CONFIGS
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name: str | None = None, config_overrides: dict | None = None) -> Flask:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
    selected = config_name or os.getenv("FLASK_ENV", "development")
    if selected not in CONFIGS:
        raise ValueError(f"Unknown configuration: {selected}")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS[selected])
    if config_overrides:
        app.config.update(config_overrides)

    if selected == "production":
        if not app.config.get("SECRET_KEY") or not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("Production requires SECRET_KEY and DATABASE_URL.")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى لوحة الإدارة."
    login_manager.login_message_category = "error"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id)) if user_id.isdigit() else None

    from app.admin import bp as admin_bp
    from app.admin.articles import bp as article_admin_bp
    from app.admin.candidates import bp as candidate_admin_bp
    from app.admin.sources import bp as source_admin_bp
    from app.auth import bp as auth_bp
    from app.errors import register_error_handlers
    from app.public import bp as public_bp
    from app.public.content import bp as content_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(article_admin_bp)
    app.register_blueprint(candidate_admin_bp)
    app.register_blueprint(source_admin_bp)
    register_error_handlers(app)
    register_commands(app)

    @app.before_request
    def create_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(18)

    @app.context_processor
    def inject_site_context():
        from app.models import Category
        from app.services import SettingsService

        nav_categories = db.session.scalars(
            db.select(Category)
            .where(Category.visible.is_(True))
            .order_by(Category.sort_order, Category.title)
        ).all()
        return {
            "site_settings": SettingsService.get(),
            "nav_categories": nav_categories,
            "csp_nonce": g.get("csp_nonce", ""),
        }

    @app.after_request
    def add_security_headers(response):
        nonce = g.get("csp_nonce", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        return response

    return app
