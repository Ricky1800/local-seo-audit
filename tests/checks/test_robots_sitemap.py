from __future__ import annotations

from local_seo_audit.checks.robots_sitemap import RobotsSitemapCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_both_present(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "<html></html>",
        robots=make_fetch_result(
            "https://example.com/robots.txt",
            "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml",
        ),
        sitemap=make_fetch_result("https://example.com/sitemap.xml", "<urlset></urlset>"),
    )
    result = RobotsSitemapCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_both_missing(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "<html></html>",
        robots=make_fetch_result("https://example.com/robots.txt", "", status_code=404),
        sitemap=make_fetch_result("https://example.com/sitemap.xml", "", status_code=404),
    )
    result = RobotsSitemapCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_only_robots_present(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "<html></html>",
        robots=make_fetch_result("https://example.com/robots.txt", "User-agent: *\nAllow: /"),
        sitemap=make_fetch_result("https://example.com/sitemap.xml", "", status_code=404),
    )
    result = RobotsSitemapCheck().run(ctx)
    assert result.status is Status.WARN


def test_pass_but_notes_sitemap_not_referenced(
    make_ctx: MakeCtx, make_fetch_result: MakeFetchResult
) -> None:
    ctx = make_ctx(
        "<html></html>",
        robots=make_fetch_result("https://example.com/robots.txt", "User-agent: *\nAllow: /"),
        sitemap=make_fetch_result("https://example.com/sitemap.xml", "<urlset></urlset>"),
    )
    result = RobotsSitemapCheck().run(ctx)
    assert result.status is Status.PASS
    assert "not referenced" in result.evidence


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = RobotsSitemapCheck().run(ctx)
    assert result.status is Status.SKIP
