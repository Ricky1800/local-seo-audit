"""Shared pytest fixtures: fixture-file loading and AuditContext construction.

``make_fetch_result`` and ``make_ctx`` are factory fixtures (a fixture that
returns a callable) so every test file can build ad-hoc :class:`FetchResult`
and :class:`AuditContext` objects without touching the network.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

from local_seo_audit.business import Business
from local_seo_audit.checks.base import AuditContext, CrawlResult
from local_seo_audit.fetcher import FetchResult
from local_seo_audit.models import CheckResult, Report, Severity, Status

FIXTURES_DIR = Path(__file__).parent / "fixtures"

MakeFetchResult = Callable[..., FetchResult]
MakeCtx = Callable[..., AuditContext]


def load_fixture(*parts: str) -> str:
    """Read a fixture file's text content, e.g. ``load_fixture("good_site", "index.html")``."""
    return (FIXTURES_DIR / Path(*parts)).read_text(encoding="utf-8")


@pytest.fixture
def make_fetch_result() -> MakeFetchResult:
    def _make(
        url: str,
        text: str = "",
        *,
        status_code: int = 200,
        error: str | None = None,
        final_url: str | None = None,
        redirected: bool = False,
        history_urls: list[str] | None = None,
    ) -> FetchResult:
        return FetchResult(
            request_url=url,
            final_url=final_url or url,
            status_code=status_code,
            headers=httpx.Headers(),
            text=text,
            elapsed_ms=1.0,
            redirected=redirected,
            history_urls=history_urls or [],
            error=error,
        )

    return _make


@pytest.fixture
def make_ctx(make_fetch_result: MakeFetchResult) -> MakeCtx:
    def _make(
        html: str,
        *,
        url: str = "https://example.com/",
        business: Business | None = None,
        primary: FetchResult | None = None,
        http_probe: FetchResult | None = None,
        robots: FetchResult | None = None,
        sitemap: FetchResult | None = None,
        favicon: FetchResult | None = None,
        crawl: CrawlResult | None = None,
        crawl_requested: int = 0,
    ) -> AuditContext:
        resolved_primary = primary or make_fetch_result(url, html)
        soup = BeautifulSoup(resolved_primary.text, "html.parser")
        return AuditContext(
            input_url=url,
            business=business or Business(),
            primary=resolved_primary,
            soup=soup,
            http_probe=http_probe,
            robots=robots or make_fetch_result(url + "robots.txt", "", status_code=404),
            sitemap=sitemap or make_fetch_result(url + "sitemap.xml", "", status_code=404),
            favicon=favicon or make_fetch_result(url + "favicon.ico", "", status_code=404),
            crawl=crawl,
            crawl_requested=crawl_requested,
            fetched_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        )

    return _make


@pytest.fixture
def good_site_html() -> str:
    return load_fixture("good_site", "index.html")


@pytest.fixture
def bad_site_html() -> str:
    return load_fixture("bad_site", "index.html")


@pytest.fixture
def partial_site_html() -> str:
    return load_fixture("partial_site", "index.html")


@pytest.fixture
def good_business() -> Business:
    return Business(
        name="Joe's Plumbing",
        phone="609-555-0100",
        city="Princeton",
        address="123 Main St, Princeton, NJ 08540",
    )


@pytest.fixture
def sample_report() -> Report:
    """A small, hand-built report covering pass/warn/fail/skip for renderer tests."""
    results = [
        CheckResult(
            id="https_redirect",
            title="HTTPS is enabled, and HTTP redirects to HTTPS",
            weight=12,
            severity=Severity.CRITICAL,
            status=Status.PASS,
            evidence="Final URL loads as https://example.com/ (scheme: https).",
            fix="Install an SSL certificate.",
        ),
        CheckResult(
            id="title",
            title="Title tag is present, well-sized, and locally relevant",
            weight=8,
            severity=Severity.HIGH,
            status=Status.WARN,
            evidence='Title: "Example" (7 characters).',
            fix="Keep the title between 10 and 60 characters.",
        ),
        CheckResult(
            id="h1",
            title="Exactly one H1 heading",
            weight=6,
            severity=Severity.MEDIUM,
            status=Status.FAIL,
            evidence="No H1 heading found on the page.",
            fix="Use exactly one <h1> per page.",
        ),
        CheckResult(
            id="favicon",
            title="Favicon is present",
            weight=3,
            severity=Severity.INFO,
            status=Status.SKIP,
            evidence="Skipped: homepage could not be fetched.",
            fix="",
        ),
    ]
    return Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(name="Joe's Plumbing"),
        results=results,
        generated_at=dt.datetime(2026, 1, 1, 12, 0, 0),
    )
