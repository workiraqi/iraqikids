import html
import re
import socket
import ipaddress
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from html.parser import HTMLParser

import feedparser
import requests

from app.extensions import db
from app.models import Candidate, FetchRun, Source


class FetchError(Exception):
    pass


class WebPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.h1_parts = []
        self.body_parts = []
        self.fallback_parts = []
        self.description = None
        self.og_title = None
        self.image_url = None
        self.author = None
        self.published_time = None
        self.links = []
        self._in_title = False
        self._in_h1 = False
        self._content_depth = 0
        self._ignored_depth = 0
        self._in_body = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)

        if tag == "a":
            href = (attrs.get("href") or "").strip()
            if href:
                self.links.append(href)

        if tag in ("script", "style", "nav", "footer", "noscript"):
            self._ignored_depth += 1
            return

        if tag == "body":
            self._in_body = True
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag in ("article", "main"):
            self._content_depth += 1
        elif tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            value = (attrs.get("content") or "").strip()

            if name in ("description", "og:description") and value and not self.description:
                self.description = value
            elif name == "og:title" and value and not self.og_title:
                self.og_title = value
            elif name in ("og:image", "twitter:image") and value and not self.image_url:
                self.image_url = value
            elif name in ("author", "article:author") and value and not self.author:
                if not value.lower().startswith(("http://", "https://")):
                    self.author = value
            elif name in ("article:published_time", "date", "datepublished") and value and not self.published_time:
                self.published_time = value

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "nav", "footer", "noscript"):
            if self._ignored_depth:
                self._ignored_depth -= 1
            return

        if tag == "body":
            self._in_body = False
        elif tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag in ("article", "main"):
            if self._content_depth:
                self._content_depth -= 1

    def handle_data(self, data):
        if self._ignored_depth:
            return

        text = re.sub(r"\\s+", " ", data).strip()
        if not text:
            return

        if self._in_title:
            self.title_parts.append(text)
        if self._in_h1:
            self.h1_parts.append(text)
        if self._content_depth:
            self.body_parts.append(text)
        elif self._in_body:
            self.fallback_parts.append(text)


class SourceFetchService:
    @staticmethod
    def _validate_public_url(url: str) -> str:
        parsed = urlparse((url or "").strip())
        if parsed.scheme not in ("http", "https"):
            raise FetchError("يُسمح فقط بروابط HTTP وHTTPS.")
        if not parsed.hostname:
            raise FetchError("الرابط لا يحتوي على اسم مضيف صالح.")

        host = parsed.hostname.lower()
        if host in ("localhost",) or host.endswith(".localhost"):
            raise FetchError("عناوين localhost غير مسموح بها.")

        try:
            infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError as exc:
            raise FetchError("تعذر حل اسم المضيف.") from exc

        if not infos:
            raise FetchError("تعذر حل اسم المضيف.")

        for info in infos:
            ip_text = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                continue

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise FetchError("الرابط يشير إلى عنوان شبكة غير عام وغير مسموح به.")

        return url

    @staticmethod
    def fetch(source: Source) -> FetchRun:
        if not source.is_active:
            raise FetchError("المصدر معطّل.")

        if source.source_type not in ("rss", "web"):
            raise FetchError("نوع المصدر غير مدعوم.")

        run = FetchRun(
            source_id=source.id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.session.add(run)
        db.session.flush()

        try:
            if source.source_type == "web":
                return SourceFetchService._fetch_web_source(source, run)

            _, rss_bytes = SourceFetchService._fetch_rss_response(source.url)
            feed = feedparser.parse(rss_bytes)

            if getattr(feed, "bozo", False) and not feed.entries:
                raise FetchError("تعذر قراءة RSS من هذا المصدر.")

            run.items_found = len(feed.entries)

            created = 0
            skipped = 0

            for entry in feed.entries:
                url = (
                    entry.get("link")
                    or entry.get("id")
                    or ""
                ).strip()

                title = (entry.get("title") or "").strip()

                if not url or not title:
                    skipped += 1
                    continue

                existing = db.session.scalar(
                    db.select(Candidate).where(
                        Candidate.original_url == url
                    )
                )

                if existing:
                    skipped += 1
                    continue

                summary = SourceFetchService._clean_text(
                    entry.get("summary")
                    or entry.get("description")
                    or None
                )

                author = entry.get("author") or None

                published_at = SourceFetchService._extract_date(entry)

                image_url = SourceFetchService._extract_image(entry)

                candidate = Candidate(
                    source_id=source.id,
                    title=title[:500],
                    original_url=url[:1000],
                    original_summary=summary,
                    original_author=author[:240] if author else None,
                    published_at_source=published_at,
                    image_url=image_url[:1000] if image_url else None,
                    status="new",
                )

                db.session.add(candidate)
                created += 1

            run.items_created = created
            run.items_skipped = skipped
            run.status = "success"
            run.finished_at = datetime.now(timezone.utc)

            source.last_fetched_at = datetime.now(timezone.utc)

            db.session.commit()
            return run

        except Exception as exc:
            db.session.rollback()

            failed_run = FetchRun(
                source_id=source.id,
                status="failed",
                started_at=run.started_at,
                finished_at=datetime.now(timezone.utc),
                error_message=str(exc)[:5000],
            )

            db.session.add(failed_run)
            db.session.commit()

            if isinstance(exc, FetchError):
                raise

            raise FetchError(str(exc)) from exc

    MAX_WEB_BYTES = 2 * 1024 * 1024
    REQUEST_TIMEOUT = 10
    MAX_REDIRECTS = 5
    MAX_WEB_ARTICLES = 20

    @staticmethod
    def _fetch_web_source(source: Source, run: FetchRun) -> FetchRun:
        final_url, html_text = SourceFetchService._fetch_web_response(source.url)

        parser = WebPageParser()
        parser.feed(html_text)
        discovered = SourceFetchService._filter_discovered_links(final_url, parser.links)
        content_links = SourceFetchService._select_probable_content_links(discovered)

        if not content_links:
            content_links = [final_url]

        run.items_found = min(len(content_links), SourceFetchService.MAX_WEB_ARTICLES)
        created = 0
        skipped = 0
        checked = 0

        for article_url in content_links:
            if checked >= SourceFetchService.MAX_WEB_ARTICLES:
                break

            existing = db.session.scalar(
                db.select(Candidate).where(Candidate.original_url == article_url)
            )
            if existing:
                continue

            checked += 1

            try:
                resolved_url, article_html = SourceFetchService._fetch_web_response(article_url)
                page = SourceFetchService._extract_web_page(article_html)
            except FetchError:
                skipped += 1
                continue

            title = (page.get("title") or "").strip()
            summary = (page.get("summary") or "").strip() or None
            body = (page.get("body") or "").strip() or None

            if not title or not body:
                skipped += 1
                continue

            relevance, relevance_score = SourceFetchService._classify_content_relevance(
                title,
                summary,
                body,
            )

            if relevance == "irrelevant":
                skipped += 1
                continue

            duplicate = db.session.scalar(
                db.select(Candidate).where(Candidate.original_url == resolved_url)
            )
            if duplicate:
                skipped += 1
                continue

            published_at = None
            if page.get("published_time"):
                try:
                    published_at = datetime.fromisoformat(page["published_time"].replace("Z", "+00:00"))
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                except Exception:
                    published_at = None

            image_url = page.get("image_url")
            if image_url:
                from urllib.parse import urljoin
                image_url = urljoin(resolved_url, image_url)

            candidate = Candidate(
                source_id=source.id,
                title=title[:500],
                original_url=resolved_url[:1000],
                original_summary=summary,
                original_body=body,
                original_author=(page.get("author") or "")[:240] or None,
                published_at_source=published_at,
                image_url=image_url[:1000] if image_url else None,
                status="new",
            )
            db.session.add(candidate)
            created += 1

        run.items_found = checked
        run.items_created = created
        run.items_skipped = skipped
        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        source.last_fetched_at = datetime.now(timezone.utc)
        db.session.commit()
        return run

    MAX_RSS_BYTES = 2 * 1024 * 1024

    @staticmethod
    def _fetch_rss_response(url: str):
        current_url = SourceFetchService._validate_public_url(url)

        session = requests.Session()
        session.trust_env = False
        session.headers.update({
            "User-Agent": "IraqiKidsBot/0.1 (+editorial-fetcher)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        })

        for _ in range(SourceFetchService.MAX_REDIRECTS + 1):
            try:
                response = session.get(
                    current_url,
                    timeout=SourceFetchService.REQUEST_TIMEOUT,
                    stream=True,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                raise FetchError("تعذر الاتصال بمصدر RSS.") from exc

            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchError("إعادة توجيه RSS بدون رابط صالح.")

                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                SourceFetchService._validate_public_url(current_url)
                continue

            if response.status_code >= 400:
                code = response.status_code
                response.close()
                raise FetchError(f"مصدر RSS أعاد HTTP {code}.")

            content_type = (response.headers.get("Content-Type") or "").lower()
            allowed_types = (
                "application/rss+xml",
                "application/atom+xml",
                "application/xml",
                "text/xml",
                "application/rdf+xml",
            )
            if content_type and not any(item in content_type for item in allowed_types):
                response.close()
                raise FetchError("نوع محتوى RSS غير مدعوم.")

            length = response.headers.get("Content-Length")
            if length:
                try:
                    if int(length) > SourceFetchService.MAX_RSS_BYTES:
                        response.close()
                        raise FetchError("حجم RSS أكبر من الحد المسموح.")
                except ValueError:
                    pass

            chunks = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > SourceFetchService.MAX_RSS_BYTES:
                        raise FetchError("حجم RSS أكبر من الحد المسموح.")
                    chunks.append(chunk)
            finally:
                response.close()

            return current_url, b"".join(chunks)

        raise FetchError("عدد عمليات إعادة توجيه RSS تجاوز الحد المسموح.")

    @staticmethod
    def _fetch_web_response(url: str):
        current_url = SourceFetchService._validate_public_url(url)

        session = requests.Session()
        session.trust_env = False
        session.headers.update({
            "User-Agent": "IraqiKidsBot/0.1 (+editorial-fetcher)"
        })

        for _ in range(SourceFetchService.MAX_REDIRECTS + 1):
            try:
                response = session.get(
                    current_url,
                    timeout=SourceFetchService.REQUEST_TIMEOUT,
                    stream=True,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                raise FetchError("تعذر الاتصال بالمصدر.") from exc

            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchError("إعادة توجيه بدون رابط صالح.")

                from urllib.parse import urljoin
                current_url = urljoin(current_url, location)
                SourceFetchService._validate_public_url(current_url)
                continue

            if response.status_code >= 400:
                code = response.status_code
                response.close()
                raise FetchError(f"المصدر أعاد HTTP {code}.")

            content_type = (response.headers.get("Content-Type") or "").lower()
            if not ("text/html" in content_type or "text/plain" in content_type):
                response.close()
                raise FetchError("نوع المحتوى غير مدعوم للجلب كصفحة ويب.")

            length = response.headers.get("Content-Length")
            if length:
                try:
                    if int(length) > SourceFetchService.MAX_WEB_BYTES:
                        response.close()
                        raise FetchError("حجم الصفحة أكبر من الحد المسموح.")
                except ValueError:
                    pass

            chunks = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > SourceFetchService.MAX_WEB_BYTES:
                        raise FetchError("حجم الصفحة أكبر من الحد المسموح.")
                    chunks.append(chunk)
            finally:
                response.close()

            raw = b"".join(chunks)
            encoding = response.encoding or "utf-8"
            try:
                text = raw.decode(encoding, errors="replace")
            except LookupError:
                text = raw.decode("utf-8", errors="replace")

            return current_url, text

        raise FetchError("عدد عمليات إعادة التوجيه تجاوز الحد المسموح.")

    @staticmethod
    def _filter_discovered_links(base_url: str, links):
        from urllib.parse import urljoin, urlparse

        base = urlparse(base_url)
        blocked_paths = {
            "", "/", "/contact", "/about", "/leaders", "/careers",
            "/cambridge", "/chicago", "/london", "/sanfrancisco", "/china",
            "/design-services", "/work", "/health", "/ai", "/playlab",
            "/subscribe"
        }

        results = []
        seen = set()

        for href in links:
            href = (href or "").strip()
            if not href or href.startswith("#"):
                continue

            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.hostname != base.hostname:
                continue

            path = parsed.path.rstrip("/") or "/"
            if path in blocked_paths:
                continue

            clean = parsed._replace(fragment="").geturl()
            if clean in seen:
                continue

            seen.add(clean)
            results.append(clean)

        return results

    @staticmethod
    def _classify_content_relevance(title, summary, body):
        primary = " ".join(filter(None, [title, summary])).strip()
        if len(primary) < 80:
            primary = " ".join(filter(None, [primary, (body or "")[:800]]))
        text = primary.lower()

        direct_child_terms = (
            "child", "children", "kid", "kids", "toddler", "preschool",
            "young learner", "young learners", "school-age"
        )

        direct_activity_terms = (
            "arts and crafts", "art activity", "craft activity", "playdough",
            "open-ended play", "sensory play", "pretend play",
            "learning activity", "hands-on activity", "stem activity",
            "steam activity", "classroom activity", "kids activity",
            "children activity", "make your own", "screen-free activity"
        )

        creative_terms = (
            "creative", "creativity", "imagination", "imaginative",
            "creative thinking", "art", "craft", "play", "draw", "paint",
            "experiment", "invent", "build", "curiosity"
        )

        education_terms = (
            "teacher", "school", "classroom", "parenting", "learning",
            "education", "student", "students"
        )

        adult_context = (
            "work", "workplace", "career", "retirement", "dating",
            "romantic relationship", "aging", "over 60", "over 70",
            "over 80", "menopause", "job", "office", "professional success",
            "marriage", "relationship", "toxic people", "fitness",
            "running", "diet", "brain foods"
        )

        child = sum(1 for term in direct_child_terms if term in text)
        activity = sum(1 for term in direct_activity_terms if term in text)
        creative = sum(1 for term in creative_terms if term in text)
        education = sum(1 for term in education_terms if term in text)
        adult = sum(1 for term in adult_context if term in text)

        score = child * 5 + activity * 5 + creative * 2 + education * 2 - adult * 6

        if adult >= 1 and child == 0 and activity == 0:
            return "irrelevant", score

        if child >= 1 and (activity >= 1 or creative >= 1 or education >= 1) and score >= 6:
            return "relevant", score

        if activity >= 2 and score >= 8:
            return "relevant", score

        if (child >= 1 or activity >= 1) and score >= 1:
            return "uncertain", score

        if adult == 0 and (creative >= 1 or education >= 1) and score >= 4:
            return "uncertain", score

        return "irrelevant", score

    @staticmethod
    def _select_probable_content_links(links):
        from urllib.parse import urlparse

        blocked = {
            "privacy-policy", "terms-conditions", "terms", "privacy",
            "contact", "about", "about-us", "careers", "subscribe",
            "leaders", "masthead", "editorial-policy", "corrections",
            "feed", "latest-articles", "video-library", "iq", "thinking",
            "work", "health", "ai", "playlab", "design-services", "deib"
        }

        content_sections = {
            "article", "articles", "blog", "blogs", "story", "stories",
            "news", "post", "posts", "case-study", "case-studies"
        }

        results = []
        seen = set()

        for url in links:
            parsed = urlparse(url)
            parts = [part.lower() for part in parsed.path.split("/") if part]

            if not parts:
                continue

            if any(part in blocked for part in parts):
                continue

            last = parts[-1]
            probable = False

            if len(parts) >= 2 and parts[0] in content_sections:
                probable = True
            elif len(parts) == 1 and last.count("-") >= 2:
                probable = True
            elif len(parts) >= 2 and last.count("-") >= 2:
                probable = True

            if not probable:
                continue

            if url in seen:
                continue

            seen.add(url)
            results.append(url)

        return results

    @staticmethod
    def _extract_web_page(html_text: str):
        parser = WebPageParser()
        try:
            parser.feed(html_text)
        except Exception as exc:
            raise FetchError("تعذر تحليل صفحة الويب.") from exc

        title = " ".join(parser.h1_parts).strip() or parser.og_title or " ".join(parser.title_parts).strip()
        description = SourceFetchService._clean_text(parser.description)
        body_source = parser.body_parts if parser.body_parts else parser.fallback_parts
        body = SourceFetchService._clean_text(" ".join(body_source))

        return {
            "title": title or None,
            "summary": description,
            "body": body,
            "image_url": parser.image_url,
            "author": parser.author,
            "published_time": parser.published_time,
        }

    @staticmethod
    def _clean_text(value):
        if not value:
            return None
        text = html.unescape(str(value))
        pattern = chr(60) + "(?:(?!" + chr(62) + ").)+" + chr(62)
        text = re.sub(pattern, " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    @staticmethod
    def _extract_date(entry):
        for field in ("published", "updated"):
            value = entry.get(field)
            if not value:
                continue

            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed
            except Exception:
                pass

        return None

    @staticmethod
    def _extract_image(entry):
        media = entry.get("media_content")
        if media:
            first = media[0]
            if isinstance(first, dict):
                url = first.get("url")
                if url:
                    return url

        thumbnail = entry.get("media_thumbnail")
        if thumbnail:
            first = thumbnail[0]
            if isinstance(first, dict):
                url = first.get("url")
                if url:
                    return url

        links = entry.get("links") or []

        for link in links:
            if not isinstance(link, dict):
                continue

            href = link.get("href")
            media_type = link.get("type", "")

            if href and media_type.startswith("image/"):
                return href

        return None
