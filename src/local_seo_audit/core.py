"""Orchestrates a full audit: fetch, parse, run every check, build the Report."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from local_seo_audit.business import Business
from local_seo_audit.checks import ALL_CHECKS, AuditContext, CrawlLinkStatus, CrawlResult
from local_seo_audit.fetcher import FetchResult, fetch, new_client
from local_seo_audit.models import Report
from local_seo_audit.utils import ensure_scheme, same_host
from local_seo_audit.vitals import VitalsResult, fetch_core_web_vitals

#: Internal links are checked one homepage-depth deep; this keeps runs fast and
#: avoids ever making an unbounded number of requests to someone else's server.
_MAX_CRAWL_CAP = 50


def _best_parser() -> str:
    """Prefer lxml (faster, more lenient) but never hard-fail if it's not installed."""
    try:
        import lxml  # noqa: F401
    except ImportError:
        return "html.parser"
    return "lxml"


def _http_probe_url(final_url: str) -> str | None:
    """The http:// origin to test for a redirect, given the https:// page that loaded."""
    parsed = urlparse(final_url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return parsed._replace(scheme="http").geturl()


def _extract_internal_links(soup: BeautifulSoup, base_url: str, limit: int) -> list[str]:
    skip_prefixes = ("#", "mailto:", "tel:", "javascript:")
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.lower().startswith(skip_prefixes):
            continue
        absolute = urljoin(base_url, href).split("#", 1)[0]
        if not absolute or not same_host(absolute, base_url):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
        if len(links) >= limit:
            break
    return links


def _crawl_internal_links(
    client: httpx.Client, base_url: str, soup: BeautifulSoup, limit: int
) -> CrawlResult:
    capped_limit = min(limit, _MAX_CRAWL_CAP)
    links = _extract_internal_links(soup, base_url, capped_limit)
    checked: list[CrawlLinkStatus] = []
    for link in links:
        result = fetch(client, link)
        ok = result.error is None and result.status_code != 0 and result.status_code < 400
        checked.append(
            CrawlLinkStatus(url=link, status_code=result.status_code, ok=ok, error=result.error)
        )
    return CrawlResult(checked=checked, requested=capped_limit)


def audit(
    url: str,
    business: Business | None = None,
    *,
    crawl: int = 0,
    client: httpx.Client | None = None,
    vitals: bool = False,
    psi_api_key: str | None = None,
) -> Report:
    """Audit ``url`` and return a fully-scored :class:`Report`.

    Args:
        url: The site to audit. A bare host (``example.com``) is treated as
            ``https://example.com``.
        business: Known-good NAP facts to check the page against. Omit any
            field you do not know; checks that need it will be skipped.
        crawl: If > 0, also crawl up to this many same-host internal links
            (capped at 50) looking for broken links.
        client: An existing :class:`httpx.Client` to reuse (mainly for tests).
            When omitted, a new client is created and closed automatically.
        vitals: If true, also fetch Core Web Vitals (mobile + desktop) from
            Google's PageSpeed Insights API. Off by default: it is a slow,
            separate network call to a third-party API.
        psi_api_key: Optional PageSpeed Insights API key. Falls back to the
            ``PSI_API_KEY`` environment variable, then to an unauthenticated
            (rate-limited) request.
    """
    business = business or Business()
    target = ensure_scheme(url.strip())

    owns_client = client is None
    http_client = client or new_client()
    try:
        primary = fetch(http_client, target)
        parser = _best_parser()
        soup = BeautifulSoup(primary.text, parser) if primary.text else BeautifulSoup("", parser)

        http_probe: FetchResult | None = None
        probe_url = _http_probe_url(primary.final_url) if primary.ok else None
        if probe_url is not None:
            http_probe = fetch(http_client, probe_url)

        base_for_relative = primary.final_url or target
        robots = fetch(http_client, urljoin(base_for_relative, "/robots.txt"))
        sitemap = fetch(http_client, urljoin(base_for_relative, "/sitemap.xml"))
        favicon = fetch(http_client, urljoin(base_for_relative, "/favicon.ico"))

        crawl_result: CrawlResult | None = None
        if crawl > 0 and primary.ok:
            crawl_result = _crawl_internal_links(http_client, base_for_relative, soup, crawl)

        ctx = AuditContext(
            input_url=target,
            business=business,
            primary=primary,
            soup=soup,
            http_probe=http_probe,
            robots=robots,
            sitemap=sitemap,
            favicon=favicon,
            crawl=crawl_result,
            crawl_requested=crawl,
            fetched_at=datetime.now(),
        )
        results = [check.run(ctx) for check in ALL_CHECKS]

        vitals_result: VitalsResult | None = None
        if vitals:
            vitals_result = fetch_core_web_vitals(ctx.page_url, api_key=psi_api_key)

        return Report(
            url=target,
            final_url=primary.final_url or target,
            business=business,
            results=results,
            generated_at=ctx.fetched_at,
            vitals=vitals_result,
        )
    finally:
        if owns_client:
            http_client.close()
