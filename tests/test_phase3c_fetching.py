import socket
from unittest.mock import patch

import pytest

from app.services.fetching import FetchError, SourceFetchService


def _public_dns(*args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("93.184.216.34", 443),
        )
    ]


def _private_dns(*args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("127.0.0.1", 80),
        )
    ]


def test_validate_public_url_rejects_non_http():
    with pytest.raises(FetchError):
        SourceFetchService._validate_public_url("file:///etc/passwd")


def test_validate_public_url_rejects_localhost():
    with pytest.raises(FetchError):
        SourceFetchService._validate_public_url("http://localhost/test")


def test_validate_public_url_rejects_private_ip():
    with patch(
        "app.services.fetching.socket.getaddrinfo",
        side_effect=_private_dns,
    ):
        with pytest.raises(FetchError):
            SourceFetchService._validate_public_url(
                "http://example.test/article"
            )


def test_validate_public_url_accepts_public_host():
    with patch(
        "app.services.fetching.socket.getaddrinfo",
        side_effect=_public_dns,
    ):
        result = SourceFetchService._validate_public_url(
            "https://example.com/article"
        )

    assert result == "https://example.com/article"


def test_extract_web_page_reads_article_metadata_and_body():
    lt = chr(60)
    gt = chr(62)

    html = (
        f"{lt}html{gt}"
        f"{lt}head{gt}"
        f'{lt}title{gt}Fallback title{lt}/title{gt}'
        f'{lt}meta name="description" '
        f'content="A useful activity for children"{gt}'
        f'{lt}meta property="og:image" content="/image.jpg"{gt}'
        f'{lt}meta name="author" content="Jane Doe"{gt}'
        f"{lt}/head{gt}"
        f"{lt}body{gt}"
        f"{lt}article{gt}"
        f"{lt}h1{gt}Creative Art for Kids{lt}/h1{gt}"
        f"{lt}p{gt}"
        "Children can paint, build, and experiment with simple materials."
        f"{lt}/p{gt}"
        f"{lt}/article{gt}"
        f"{lt}/body{gt}"
        f"{lt}/html{gt}"
    )

    page = SourceFetchService._extract_web_page(html)

    assert page["title"] == "Creative Art for Kids"
    assert page["summary"] == "A useful activity for children"
    assert "Children can paint" in page["body"]
    assert page["image_url"] == "/image.jpg"
    assert page["author"] == "Jane Doe"


def test_filter_discovered_links_keeps_same_host_content_only():
    links = [
        "/about",
        "/blog/creative-kids-art",
        "https://other.example/story",
        "/blog/creative-kids-art#top",
    ]

    result = SourceFetchService._filter_discovered_links(
        "https://example.com/",
        links,
    )

    assert result == [
        "https://example.com/blog/creative-kids-art"
    ]


def test_select_probable_content_links():
    links = [
        "https://example.com/about/team",
        "https://example.com/blog/creative-art-for-kids",
        "https://example.com/simple",
    ]

    result = SourceFetchService._select_probable_content_links(links)

    assert result == [
        "https://example.com/blog/creative-art-for-kids"
    ]


def test_relevance_classifier_recognizes_children_creativity():
    label, score = SourceFetchService._classify_content_relevance(
        "Creative art activities for children",
        "Hands-on learning activities for kids",
        "",
    )

    assert label == "relevant"
    assert score >= 6


def test_relevance_classifier_rejects_adult_career_content():
    label, score = SourceFetchService._classify_content_relevance(
        "Professional success at work",
        "Career advice for the workplace",
        "",
    )

    assert label == "irrelevant"
    assert score < 0

from app.extensions import db
from app.models import Candidate, FetchRun, Source


def test_fetch_web_source_creates_candidate_and_stores_body(app):
    with app.app_context():
        source = Source(name="Phase 3C Web", url="https://example.com", source_type="web", language="en", is_active=True)
        db.session.add(source)
        db.session.flush()
        run = FetchRun(source_id=source.id, status="running")
        db.session.add(run)
        db.session.flush()

        homepage = "HOME"
        article_html = "ARTICLE"
        article_url = "https://example.com/blog/creative-art-for-kids"

        def fake_fetch(url):
            if url == source.url:
                return source.url, homepage
            return article_url, article_html

        page_data = {
            "title": "Creative Art for Kids",
            "summary": "A hands-on learning activity for children",
            "body": "Children can paint, build, experiment, and explore creativity together.",
            "image_url": "/images/art.jpg",
            "author": "Jane Doe",
            "published_time": "2026-08-20T10:00:00Z",
        }

        with patch.object(SourceFetchService, "_fetch_web_response", side_effect=fake_fetch), patch("app.services.fetching.WebPageParser") as parser_class, patch.object(SourceFetchService, "_filter_discovered_links", return_value=[article_url]), patch.object(SourceFetchService, "_select_probable_content_links", return_value=[article_url]), patch.object(SourceFetchService, "_extract_web_page", return_value=page_data), patch.object(SourceFetchService, "_classify_content_relevance", return_value=("relevant", 10)):
            parser_class.return_value.links = [article_url]
            result = SourceFetchService._fetch_web_source(source, run)

        candidate = db.session.scalar(db.select(Candidate).where(Candidate.original_url == article_url))
        assert candidate is not None
        assert candidate.original_body == page_data["body"]
        assert candidate.original_summary == page_data["summary"]
        assert candidate.original_author == "Jane Doe"
        assert candidate.image_url == "https://example.com/images/art.jpg"
        assert candidate.status == "new"
        assert result.items_found == 1
        assert result.items_created == 1
        assert result.items_skipped == 0
        assert result.status == "success"
        assert source.last_fetched_at is not None


def test_fetch_web_source_does_not_duplicate_existing_candidate(app):
    with app.app_context():
        source = Source(name="Phase 3C Duplicate", url="https://duplicate.example", source_type="web", language="en", is_active=True)
        db.session.add(source)
        db.session.flush()
        article_url = "https://duplicate.example/blog/creative-kids-project"
        existing = Candidate(source_id=source.id, title="Existing", original_url=article_url, original_body="Existing body", status="new")
        db.session.add(existing)
        db.session.flush()
        run = FetchRun(source_id=source.id, status="running")
        db.session.add(run)
        db.session.flush()

        with patch.object(SourceFetchService, "_fetch_web_response", return_value=(source.url, "HOME")), patch("app.services.fetching.WebPageParser") as parser_class, patch.object(SourceFetchService, "_filter_discovered_links", return_value=[article_url]), patch.object(SourceFetchService, "_select_probable_content_links", return_value=[article_url]):
            parser_class.return_value.links = [article_url]
            result = SourceFetchService._fetch_web_source(source, run)

        matches = db.session.scalars(db.select(Candidate).where(Candidate.original_url == article_url)).all()
        assert len(matches) == 1
        assert result.items_found == 0
        assert result.items_created == 0
        assert result.items_skipped == 0
        assert result.status == "success"
