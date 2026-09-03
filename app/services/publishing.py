from datetime import datetime, timezone

from app.models import Article


class PublishingError(ValueError):
    pass


class PublishingService:
    @staticmethod
    def submit_for_review(article: Article) -> None:
        if article.status == "review":
            return
        if article.status != "draft":
            raise PublishingError("Only a draft article can be submitted for review.")
        article.status = "review"

    @staticmethod
    def approve(article: Article) -> None:
        if article.status == "approved":
            return
        if article.status != "review":
            raise PublishingError("Only an article in review can be approved.")
        article.status = "approved"
        article.approved_at = article.approved_at or datetime.now(timezone.utc)

    @staticmethod
    def publish(article: Article) -> None:
        if article.status == "published":
            return
        if article.status != "approved":
            raise PublishingError("Only an approved article can be published.")
        now = datetime.now(timezone.utc)
        article.status = "published"
        article.approved_at = article.approved_at or now
        article.published_at = article.published_at or now

    @staticmethod
    def hide(article: Article) -> None:
        if article.status != "published":
            raise PublishingError("Only a published article can be hidden.")
        article.status = "hidden"

    @staticmethod
    def restore(article: Article) -> None:
        if article.status != "hidden":
            raise PublishingError("Only a hidden article can be restored.")
        article.status = "published" if article.published_at else "draft"
