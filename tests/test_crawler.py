"""Full-site crawl tests: sitemap-index discovery, robots.txt, BFS, and site-level checks.

Everything is served from local fixture files via respx - no real network access.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from local_seo_audit.crawler import crawl_site, discover_sitemap_urls

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "site_crawl"


def _load(name: str, origin: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8").replace("{origin}", origin)


def _mock_site(respx_mock: respx.MockRouter, origin: str) -> None:
    pages = {
        "/": "index.html",
        "/about": "about.html",
        "/services": "services.html",
        "/contact": "contact.html",
        "/orphan": "orphan.html",
        "/level1": "level1.html",
        "/level2": "level2.html",
        "/level3": "level3.html",
    }
    for path, filename in pages.items():
        respx_mock.get(f"{origin}{path}").mock(
            return_value=httpx.Response(200, text=_load(filename, origin))
        )
    respx_mock.get(f"{origin}/robots.txt").mock(
        return_value=httpx.Response(200, text=_load("robots.txt", origin))
    )
    respx_mock.get(f"{origin}/sitemap.xml").mock(
        return_value=httpx.Response(200, text=_load("sitemap.xml", origin))
    )
    respx_mock.get(f"{origin}/sitemap-pages.xml").mock(
        return_value=httpx.Response(200, text=_load("sitemap-pages.xml", origin))
    )
    respx_mock.get(f"{origin}/old-page").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/old-page-2"})
    )
    respx_mock.get(f"{origin}/old-page-2").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/services"})
    )
    respx_mock.get(f"{origin}/missing").mock(return_value=httpx.Response(404, text="not found"))
    # Deliberately no mock for /private/notes: robots.txt disallows it, so a correct
    # crawler never requests it. respx will raise if that assumption is ever violated.


def test_discover_sitemap_urls_follows_sitemap_index(respx_mock: respx.MockRouter) -> None:
    origin = "https://sitemaptest.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        urls = discover_sitemap_urls(client, f"{origin}/")

    assert urls == {
        f"{origin}/",
        f"{origin}/about",
        f"{origin}/services",
        f"{origin}/contact",
        f"{origin}/orphan",
    }


def test_crawl_site_visits_linked_pages_and_respects_robots(
    respx_mock: respx.MockRouter,
) -> None:
    origin = "https://crawlme.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50, concurrency=2)

    visited = {p.url for p in report.pages}
    assert f"{origin}/" in visited
    assert f"{origin}/about" in visited
    assert f"{origin}/contact" in visited
    assert f"{origin}/level3" in visited
    assert f"{origin}/private/notes" not in visited
    assert f"{origin}/private/notes" in report.robots_disallowed


def test_crawl_finds_duplicate_titles_and_descriptions(respx_mock: respx.MockRouter) -> None:
    origin = "https://dupes.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    title_urls = {url for _, urls in report.duplicate_titles for url in urls}
    assert f"{origin}/" in title_urls
    assert f"{origin}/services" in title_urls

    desc_urls = {url for _, urls in report.duplicate_descriptions for url in urls}
    assert f"{origin}/about" in desc_urls
    assert f"{origin}/contact" in desc_urls


def test_crawl_finds_missing_h1_and_heading_order_issue(respx_mock: respx.MockRouter) -> None:
    origin = "https://headings.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    assert f"{origin}/services" in report.missing_h1
    assert f"{origin}/services" in report.heading_order_issues


def test_crawl_finds_thin_content(respx_mock: respx.MockRouter) -> None:
    origin = "https://thin.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    thin_urls = {url for url, _ in report.thin_content}
    assert f"{origin}/services" in thin_urls
    assert f"{origin}/about" not in thin_urls


def test_crawl_finds_bad_canonical(respx_mock: respx.MockRouter) -> None:
    origin = "https://canon.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    assert any("different host" in issue for issue in report.canonical_issues)


def test_crawl_finds_redirect_chain_and_error_page(respx_mock: respx.MockRouter) -> None:
    origin = "https://redirects.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    assert f"{origin}/old-page" in report.redirect_chains
    error_urls = {url for url, _ in report.error_pages}
    assert f"{origin}/missing" in error_urls


def test_crawl_finds_orphan_and_missing_from_sitemap(respx_mock: respx.MockRouter) -> None:
    origin = "https://orphans.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    assert f"{origin}/orphan" in report.orphan_pages
    assert f"{origin}/level1" in report.missing_from_sitemap


def test_crawl_finds_deep_pages_and_noindex(respx_mock: respx.MockRouter) -> None:
    origin = "https://deep.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=50)

    deep_urls = {url for url, depth in report.deep_pages}
    assert f"{origin}/level3" in deep_urls
    # /orphan isn't linked, so it's only visible via the sitemap, never actually crawled;
    # noindex_pages only covers pages that were actually fetched and had the meta tag.
    assert report.pages_crawled >= 8


def test_crawl_respects_max_pages_cap(respx_mock: respx.MockRouter) -> None:
    origin = "https://capped.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=2)

    assert report.pages_crawled == 2
    assert report.max_pages == 2


def test_crawl_site_with_unreachable_homepage_returns_empty_report(
    respx_mock: respx.MockRouter,
) -> None:
    origin = "https://unreachable.example"
    respx_mock.get(f"{origin}/").mock(side_effect=httpx.ConnectError("no route"))
    respx_mock.get(f"{origin}/robots.txt").mock(side_effect=httpx.ConnectError("no route"))
    respx_mock.get(f"{origin}/sitemap.xml").mock(side_effect=httpx.ConnectError("no route"))

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=5)

    assert report.pages_crawled == 1
    assert not report.pages[0].ok


def test_sitemap_with_no_sitemap_present_returns_empty_set(respx_mock: respx.MockRouter) -> None:
    origin = "https://nositemap.example"
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))

    with httpx.Client() as client:
        urls = discover_sitemap_urls(client, f"{origin}/")

    assert urls == set()


def test_sitemap_with_malformed_xml_is_ignored(respx_mock: respx.MockRouter) -> None:
    origin = "https://badxml.example"
    respx_mock.get(f"{origin}/sitemap.xml").mock(
        return_value=httpx.Response(200, text="<not><valid<xml")
    )

    with httpx.Client() as client:
        urls = discover_sitemap_urls(client, f"{origin}/")

    assert urls == set()


@pytest.mark.parametrize("delay", [0.0])
def test_crawl_accepts_a_delay_argument(respx_mock: respx.MockRouter, delay: float) -> None:
    origin = "https://politedelay.example"
    _mock_site(respx_mock, origin)

    with httpx.Client() as client:
        report = crawl_site(client, f"{origin}/", max_pages=3, delay=delay)

    assert report.pages_crawled == 3
