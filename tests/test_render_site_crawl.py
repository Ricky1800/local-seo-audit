"""Every renderer must show the site-crawl section when present, and omit it otherwise."""

from __future__ import annotations

import datetime as dt

from local_seo_audit.business import Business
from local_seo_audit.crawler import CrawledPage, SiteCrawlReport
from local_seo_audit.models import Report
from local_seo_audit.render.html import render_html
from local_seo_audit.render.json_renderer import render_json, report_to_dict
from local_seo_audit.render.markdown import render_markdown
from local_seo_audit.render.text import render_text


def _page(url: str, *, title: str | None = "A title", ok: bool = True) -> CrawledPage:
    return CrawledPage(
        url=url,
        status_code=200 if ok else 404,
        ok=ok,
        error=None,
        redirected=False,
        history_urls=(),
        title=title,
        meta_description="A description",
        h1_count=1,
        headings=(),
        word_count=250,
        canonical=None,
        noindex=False,
        internal_links=frozenset(),
        depth=1,
        in_sitemap=True,
        has_tel_link=True,
        has_json_ld=True,
    )


def _crawl() -> SiteCrawlReport:
    pages = (
        _page("https://example.com/"),
        _page("https://example.com/services", title="Same Title"),
        _page("https://example.com/about", title="Same Title"),
        _page("https://example.com/missing", ok=False),
    )
    return SiteCrawlReport(
        start_url="https://example.com/",
        pages=pages,
        max_pages=50,
        sitemap_urls=frozenset({"https://example.com/", "https://example.com/services"}),
        duplicate_titles=(
            ("Same Title", ("https://example.com/services", "https://example.com/about")),
        ),
        missing_h1=("https://example.com/about",),
        error_pages=(("https://example.com/missing", 404),),
    )


def _report_with_crawl() -> Report:
    return Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(name="Joe's Plumbing"),
        results=[],
        generated_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        site_crawl=_crawl(),
    )


def test_text_renders_site_crawl_section() -> None:
    output = render_text(_report_with_crawl(), color=False)
    assert "Site crawl" in output
    assert "https://example.com/services" in output
    assert "Duplicate titles: 1" in output


def test_markdown_renders_site_crawl_section() -> None:
    output = render_markdown(_report_with_crawl())
    assert "## Site crawl" in output
    assert "| URL | Status | Depth | Title | Words |" in output
    assert "**Duplicate titles:** 1" in output


def test_html_renders_site_crawl_section() -> None:
    output = render_html(_report_with_crawl())
    assert "Site crawl" in output
    assert "<table" in output
    assert "duplicate title(s)" in output


def test_json_renders_site_crawl_section() -> None:
    data = report_to_dict(_report_with_crawl())
    assert data["site_crawl"]["pages_crawled"] == 4
    assert data["site_crawl"]["issues"]["duplicate_titles"][0]["value"] == "Same Title"
    output = render_json(_report_with_crawl())
    assert '"site_crawl"' in output


def test_renderers_omit_site_crawl_section_when_absent(sample_report: Report) -> None:
    assert "Site crawl" not in render_text(sample_report, color=False)
    assert "Site crawl" not in render_markdown(sample_report)
    assert "Site crawl" not in render_html(sample_report)
    assert report_to_dict(sample_report)["site_crawl"] is None
