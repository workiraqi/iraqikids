import bleach


ALLOWED_TAGS = ["p", "h2", "h3", "strong", "em", "ul", "ol", "li", "blockquote", "a"]
ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
ALLOWED_PROTOCOLS = ["http", "https"]


def sanitize_article_body(value: str) -> str:
    return bleach.clean(
        value or "",
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

