from flask import Blueprint, render_template


bp = Blueprint("errors", __name__)


def register_error_handlers(app):
    for code in (403, 404, 429, 500):
        app.register_error_handler(
            code,
            lambda error, status=code: (render_template("errors/error.html", status=status), status),
        )
