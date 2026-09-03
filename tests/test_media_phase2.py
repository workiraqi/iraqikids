from io import BytesIO

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.media import ArticleImageService, ImageValidationError


def png_upload(filename="test.png"):
    data = BytesIO()
    Image.new("RGB", (8, 8), "#d9ff64").save(data, format="PNG")
    data.seek(0)
    return FileStorage(stream=data, filename=filename, content_type="image/png")


def test_valid_image_upload_and_delete(app):
    with app.app_context():
        path = ArticleImageService.save(png_upload())
        stored = ArticleImageService.upload_folder() / path.rsplit("/", 1)[-1]
        assert path.startswith("uploads/articles/")
        assert stored.exists()
        ArticleImageService.delete(path)
        assert not stored.exists()


def test_image_extension_and_content_validation(app):
    with app.app_context(), pytest.raises(ImageValidationError):
        ArticleImageService.save(png_upload("test.jpg"))
    with app.app_context(), pytest.raises(ImageValidationError):
        ArticleImageService.save(
            FileStorage(stream=BytesIO(b"not-an-image"), filename="fake.png", content_type="image/png")
        )
