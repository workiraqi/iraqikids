from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class ImageValidationError(ValueError):
    pass


class ArticleImageService:
    @staticmethod
    def upload_folder() -> Path:
        configured = current_app.config.get("ARTICLE_UPLOAD_FOLDER")
        folder = Path(configured) if configured else Path(current_app.static_folder) / "uploads" / "articles"
        folder.mkdir(parents=True, exist_ok=True)
        return folder.resolve()

    @classmethod
    def save(cls, upload: FileStorage) -> str:
        if not upload or not upload.filename:
            raise ImageValidationError("No image was provided.")
        extension = Path(upload.filename).suffix.lower().lstrip(".")
        if extension not in ALLOWED_EXTENSIONS:
            raise ImageValidationError("Only JPG, PNG, and WebP images are allowed.")
        if upload.mimetype not in {"image/jpeg", "image/png", "image/webp"}:
            raise ImageValidationError("The uploaded file MIME type is not allowed.")
        try:
            upload.stream.seek(0)
            with Image.open(upload.stream) as image:
                image.verify()
                detected = image.format
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise ImageValidationError("The uploaded file is not a valid safe image.") from exc
        finally:
            upload.stream.seek(0)
        normalized_extension = ALLOWED_FORMATS.get(detected)
        if normalized_extension is None:
            raise ImageValidationError("The detected image format is not allowed.")
        extension = "jpg" if extension == "jpeg" else extension
        if extension != normalized_extension:
            raise ImageValidationError("The file extension does not match its image content.")
        filename = f"{uuid4().hex}.{normalized_extension}"
        upload.save(cls.upload_folder() / filename)
        return f"uploads/articles/{filename}"

    @classmethod
    def delete(cls, relative_path: str | None) -> None:
        if not relative_path:
            return
        normalized = relative_path.replace("\\", "/")
        if not normalized.startswith("uploads/articles/"):
            return
        filename = Path(normalized).name
        candidate = (cls.upload_folder() / filename).resolve()
        if candidate.parent == cls.upload_folder() and candidate.is_file():
            candidate.unlink()
