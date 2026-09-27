"""Full-site crawl (``--site``/``--max-pages``): sitemap + link discovery, BFS, site-level checks.

Unlike the single-page :func:`~local_seo_audit.core.audit`, this walks the
whole site (bounded by ``max_pages``), discovering pages from
``sitemap.xml`` (including sitemap indexes) plus internal links found on
each page, breadth-first, same host only. It respects ``robots.txt`` and is
polite: a configurable concurrency cap and an optional delay between
requests. Site-level problems (duplicate titles, orphan pages, broken
canonicals, ...) only make sense once you can see the whole site at once,
so they live here rather than in the single-page :mod:`~local_seo_audit.checks`.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup, Tag

from local_seo_audit.fetcher import FetchResult, fetch
from local_seo_audit.utils import same_host

#: Matches the CLI default and keeps a run bounded even for a large site.
DEFAULT_MAX_PAGES = 50
#: Absolute ceiling regardless of what a caller passes in.
HARD_MAX_PAGES = 500
#: A page below this word count is flagged as "thin" - a common industry rule of thumb.
THIN_CONTENT_WORDS = 200
#: How deep (clicks from the homepage) is considered "too deep" for local-business SEO.
MAX_HEALTHY_DEPTH = 3

_HEADING_RE = re.compile(r"^h[1-6]$")
_SKIP_LINK_PREFIXES = ("#", "mailto:", "tel:", "javascript:")


@dataclass(frozen=True, slots=True)
class Heading:
    """One heading tag, in document order."""

    level: int
    text: str


@dataclass(frozen=True, slots=True)
class CrawledPage:
    """Everything extracted from one crawled page."""

    url: str
    status_code: int
    ok: bool
    error: str | None
    redirected: bool
    history_urls: tuple[str, ...]
    title: str | None
    meta_description: str | None
    h1_count: int
    headings: tuple[Heading, ...]
    word_count: int
    canonical: str | None
    noindex: bool
    internal_links: frozenset[str]
    depth: int
    in_sitemap: bool
    has_tel_link: bool
    has_json_ld: bool


@dataclass(frozen=True, slots=True)
class SiteCrawlReport:
    """Site-wide crawl results plus the derived site-level checks."""

    start_url: str
    pages: tuple[CrawledPage, ...] = ()
    max_pages: int = 0
    sitemap_urls: frozenset[str] = frozenset()
    robots_disallowed: tuple[str, ...] = ()
    duplicate_titles: tuple[tuple[str, tuple[str, ...]], ...] = ()
    duplicate_descriptions: tuple[tuple[str, tuple[str, ...]], ...] = ()
    missing_h1: tuple[str, ...] = ()
    duplicate_h1_pages: tuple[str, ...] = ()
    heading_order_issues: tuple[str, ...] = ()
    thin_content: tuple[tuple[str, int], ...] = ()
    canonical_issues: tuple[str, ...] = ()
    redirect_chains: tuple[str, ...] = ()
    error_pages: tuple[tuple[str, int], ...] = ()
    orphan_pages: tuple[str, ...] = ()
    deep_pages: tuple[tuple[str, int], ...] = ()
    missing_from_sitemap: tuple[str, ...] = ()
    noindex_pages: tuple[str, ...] = ()

    @property
    def pages_crawled(self) -> int:
        return len(self.pages)

    @property
    def ok_pages(self) -> list[CrawledPage]:
        return [p for p in self.pages if p.ok]

    def issue_count(self) -> int:
        """A single number for "how many site-level problems were found"."""
        return sum(
            (
                len(self.duplicate_titles),
                len(self.duplicate_descriptions),
                len(self.missing_h1),
                len(self.duplicate_h1_pages),
                len(self.heading_order_issues),
                len(self.thin_content),
                len(self.canonical_issues),
                len(self.redirect_chains),
                len(self.error_pages),
                len(self.orphan_pages),
                len(self.deep_pages),
                len(self.missing_from_sitemap),
            )
        )


def _local_tag(tag: str) -> str:
    """Strip an XML namespace (``{...}tag`` -> ``tag``)."""
    return tag.rsplit("}", 1)[-1]


def _parse_sitemap_xml(text: str) -> tuple[str, list[str]]:
    """Return ``(kind, urls)``; ``kind`` is ``"sitemapindex"``, ``"urlset"``, or ``"unknown"``."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return "unknown", []
    kind = _local_tag(root.tag)
    urls: list[str] = []
    for child in root:
        if _local_tag(child.tag) not in ("url", "sitemap"):
            continue
        for grandchild in child:
            if _local_tag(grandchild.tag) == "loc" and grandchild.text:
                urls.append(grandchild.text.strip())
                break
    return kind, urls


def discover_sitemap_urls(
    client: httpx.Client, base_url: str, robots_text: str = "", *, max_sitemaps: int = 20
) -> set[str]:
    """Discover every page URL reachable from ``sitemap.xml``, following sitemap indexes.

    Also honors any ``Sitemap:`` lines in ``robots_text`` (a site is not required to put
    its sitemap at the default ``/sitemap.xml`` path).
    """
    to_fetch: list[str] = [urljoin(base_url, "/sitemap.xml")]
    for line in robots_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("sitemap:"):
            to_fetch.append(stripped.split(":", 1)[1].strip())

    seen_sitemaps: set[str] = set()
    page_urls: set[str] = set()
    while to_fetch and len(seen_sitemaps) < max_sitemaps:
        sitemap_url = to_fetch.pop()
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)
        result = fetch(client, sitemap_url)
        if not result.ok or not result.text.strip():
            continue
        kind, urls = _parse_sitemap_xml(result.text)
        if kind == "sitemapindex":
            to_fetch.extend(urls)
        else:
            page_urls.update(urls)
    return page_urls


def _build_robot_parser(robots_text: str, base_url: str) -> RobotFileParser:
    parser = RobotFileParser()
    parser.set_url(urljoin(base_url, "/robots.txt"))
    parser.parse(robots_text.splitlines())
    return parser


def _extract_links(soup: BeautifulSoup, base_url: str, limit: int = 200) -> set[str]:
    out: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not isinstance(href, str):
            continue
        href = href.strip()
        if not href or href.lower().startswith(_SKIP_LINK_PREFIXES):
            continue
        absolute = urljoin(base_url, href).split("#", 1)[0]
        if not absolute or not same_host(absolute, base_url):
            continue
        out.add(absolute)
        if len(out) >= limit:
            break
    return out


def _extract_headings(soup: BeautifulSoup) -> list[Heading]:
    return [
        Heading(level=int(tag.name[1]), text=tag.get_text(strip=True))
        for tag in soup.find_all(_HEADING_RE)
    ]


def _has_heading_order_issue(headings: tuple[Heading, ...]) -> bool:
    """Flag a page that doesn't start at H1, or that skips a level going down."""
    if not headings:
        return False
    if headings[0].level != 1:
        return True
    max_seen = headings[0].level
    for heading in headings[1:]:
        if heading.level > max_seen + 1:
            return True
        max_seen = max(max_seen, heading.level)
    return False


def _tag_content(tag: object) -> str | None:
    if not isinstance(tag, Tag):
        return None
    content = tag.get("content")
    return content.strip() if isinstance(content, str) and content.strip() else None


def _build_crawled_page(
    result: FetchResult, url: str, depth: int, sitemap_urls: set[str]
) -> CrawledPage:
    in_sitemap = url in sitemap_urls or (result.final_url in sitemap_urls)
    if result.error is not None or result.status_code == 0:
        return CrawledPage(
            url=url,
            status_code=result.status_code,
            ok=False,
            error=result.error,
            redirected=result.redirected,
            history_urls=tuple(result.history_urls),
            title=None,
            meta_description=None,
            h1_count=0,
            headings=(),
            word_count=0,
            canonical=None,
            noindex=False,
            internal_links=frozenset(),
            depth=depth,
            in_sitemap=in_sitemap,
            has_tel_link=False,
            has_json_ld=False,
        )

    ok = 200 <= result.status_code < 400
    soup = (
        BeautifulSoup(result.text, "html.parser")
        if result.text
        else BeautifulSoup("", "html.parser")
    )

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_description = _tag_content(description_tag)

    headings = _extract_headings(soup)
    h1_count = sum(1 for h in headings if h.level == 1)

    canonical_tag = soup.find("link", rel="canonical")
    canonical: str | None = None
    if isinstance(canonical_tag, Tag):
        href = canonical_tag.get("href")
        if isinstance(href, str) and href.strip():
            canonical = urljoin(result.final_url or url, href.strip())

    robots_meta = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    noindex = False
    if isinstance(robots_meta, Tag):
        content = robots_meta.get("content")
        noindex = isinstance(content, str) and "noindex" in content.lower()

    page_text = " ".join(soup.get_text(separator=" ").split())
    word_count = len(page_text.split())

    has_tel_link = any(
        isinstance(a.get("href"), str) and a["href"].strip().lower().startswith("tel:")
        for a in soup.find_all("a", href=True)
    )
    has_json_ld = bool(soup.find_all("script", attrs={"type": "application/ld+json"}))

    base_for_links = result.final_url or url
    internal_links = frozenset(_extract_links(soup, base_for_links))

    return CrawledPage(
        url=url,
        status_code=result.status_code,
        ok=ok,
        error=None,
        redirected=result.redirected,
        history_urls=tuple(result.history_urls),
        title=title,
        meta_description=meta_description,
        h1_count=h1_count,
        headings=tuple(headings),
        word_count=word_count,
        canonical=canonical,
        noindex=noindex,
        internal_links=internal_links,
        depth=depth,
        in_sitemap=in_sitemap,
        has_tel_link=has_tel_link,
        has_json_ld=has_json_ld,
    )


def _build_report(
    start_url: str,
    pages: list[CrawledPage],
    max_pages: int,
    sitemap_urls: set[str],
    disallowed: list[str],
    linked_urls: set[str],
) -> SiteCrawlReport:
    ok_pages = [p for p in pages if p.ok]
    by_url = {p.url: p for p in pages}

    title_groups: dict[str, list[str]] = {}
    description_groups: dict[str, list[str]] = {}
    for page in ok_pages:
        if page.title:
            title_groups.setdefault(page.title, []).append(page.url)
        if page.meta_description:
            description_groups.setdefault(page.meta_description, []).append(page.url)

    duplicate_titles = tuple(
        (title, tuple(urls)) for title, urls in title_groups.items() if len(urls) > 1
    )
    duplicate_descriptions = tuple(
        (desc, tuple(urls)) for desc, urls in description_groups.items() if len(urls) > 1
    )
    missing_h1 = tuple(p.url for p in ok_pages if p.h1_count == 0)
    duplicate_h1_pages = tuple(p.url for p in ok_pages if p.h1_count > 1)
    heading_order_issues = tuple(p.url for p in ok_pages if _has_heading_order_issue(p.headings))
    thin_content = tuple(
        (p.url, p.word_count) for p in ok_pages if p.word_count < THIN_CONTENT_WORDS
    )
    noindex_pages = tuple(p.url for p in ok_pages if p.noindex)

    canonical_issues: list[str] = []
    for page in ok_pages:
        if page.canonical is None:
            continue
        if not same_host(page.canonical, start_url):
            canonical_issues.append(
                f"{page.url}: canonical points to a different host ({page.canonical})."
            )
            continue
        target = by_url.get(page.canonical)
        if target is not None and not target.ok:
            canonical_issues.append(
                f"{page.url}: canonical points to a page that errors ({page.canonical}, "
                f"HTTP {target.status_code})."
            )

    redirect_chains = tuple(p.url for p in pages if len(p.history_urls) > 1)
    error_pages = tuple((p.url, p.status_code) for p in pages if not p.ok)
    deep_pages = tuple((p.url, p.depth) for p in ok_pages if p.depth > MAX_HEALTHY_DEPTH)

    orphan_pages = tuple(sorted(u for u in sitemap_urls if u not in linked_urls and u != start_url))
    crawled_urls = {p.url for p in ok_pages}
    missing_from_sitemap = (
        tuple(sorted(u for u in crawled_urls if u not in sitemap_urls)) if sitemap_urls else ()
    )

    return SiteCrawlReport(
        start_url=start_url,
        pages=tuple(pages),
        max_pages=max_pages,
        sitemap_urls=frozenset(sitemap_urls),
        robots_disallowed=tuple(disallowed),
        duplicate_titles=duplicate_titles,
        duplicate_descriptions=duplicate_descriptions,
        missing_h1=missing_h1,
        duplicate_h1_pages=duplicate_h1_pages,
        heading_order_issues=heading_order_issues,
        thin_content=thin_content,
        canonical_issues=tuple(canonical_issues),
        redirect_chains=redirect_chains,
        error_pages=error_pages,
        orphan_pages=orphan_pages,
        deep_pages=deep_pages,
        missing_from_sitemap=missing_from_sitemap,
        noindex_pages=noindex_pages,
    )


def crawl_site(
    client: httpx.Client,
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    delay: float = 0.0,
    concurrency: int = 2,
) -> SiteCrawlReport:
    """Breadth-first crawl of ``start_url``'s site, same host only, capped at ``max_pages``.

    Args:
        client: The shared HTTP client to use (reused across every request).
        start_url: Where to start the crawl (usually the homepage).
        max_pages: Stop after visiting this many pages (clamped to
            ``[1, HARD_MAX_PAGES]``).
        delay: Seconds to wait before each request within a BFS layer -
            politeness at the cost of speed. ``0`` (the default) disables it.
        concurrency: Maximum concurrent requests within one BFS layer.
    """
    max_pages = max(1, min(max_pages, HARD_MAX_PAGES))
    parsed_start = urlparse(start_url)
    origin = f"{parsed_start.scheme}://{parsed_start.netloc}/"

    robots_result = fetch(client, urljoin(origin, "/robots.txt"))
    robots_text = robots_result.text if robots_result.ok else ""
    robot_parser = _build_robot_parser(robots_text, origin)
    sitemap_urls = discover_sitemap_urls(client, origin, robots_text)

    visited: dict[str, CrawledPage] = {}
    frontier: list[tuple[str, int]] = [(start_url, 0)]
    seen: set[str] = {start_url}
    linked_urls: set[str] = set()
    disallowed: list[str] = []

    def _fetch_or_skip(item: tuple[str, int]) -> tuple[str, int, FetchResult | None]:
        url, depth = item
        if not robot_parser.can_fetch("*", url):
            return url, depth, None
        if delay > 0:
            time.sleep(delay)
        return url, depth, fetch(client, url)

    while frontier and len(visited) < max_pages:
        budget = max_pages - len(visited)
        layer, frontier = frontier[:budget], frontier[budget:]
        if not layer:
            break

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            fetched = list(executor.map(_fetch_or_skip, layer))

        next_layer: list[tuple[str, int]] = []
        for url, depth, result in fetched:
            if result is None:
                disallowed.append(url)
                continue
            page = _build_crawled_page(result, url, depth, sitemap_urls)
            visited[url] = page
            # Sorted for deterministic BFS order; robots-disallowed candidates are filtered
            # out later (when actually dequeued), not here, so a disallowed link never
            # "steals" a visit slot from a link that would have counted toward max_pages.
            for link in sorted(page.internal_links):
                linked_urls.add(link)
                if link not in seen:
                    seen.add(link)
                    next_layer.append((link, depth + 1))
        frontier.extend(next_layer)

    return _build_report(
        start_url, list(visited.values()), max_pages, sitemap_urls, disallowed, linked_urls
    )
