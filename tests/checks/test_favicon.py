from __future__ import annotations

from local_seo_audit.checks.favicon import FaviconCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_with_link_tag(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        '<link rel="icon" href="/favicon.png">',
        favicon=make_fetch_result("https://example.com/favicon.ico", "", status_code=404),
    )
    result = FaviconCheck().run(ctx)
    assert result.status is Status.PASS


def test_pass_with_default_favicon_ico(
    make_ctx: MakeCtx, make_fetch_result: MakeFetchResult
) -> None:
    ctx = make_ctx(
        "<html></html>",
        favicon=make_fetch_result("https://example.com/favicon.ico", "binary-ish", status_code=200),
    )
    result = FaviconCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_neither_present(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "<html></html>",
        favicon=make_fetch_result("https://example.com/favicon.ico", "", status_code=404),
    )
    result = FaviconCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = FaviconCheck().run(ctx)
    assert result.status is Status.SKIP
