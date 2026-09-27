from __future__ import annotations

from local_seo_audit.checks.page_weight import PageWeightCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_small_page(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html><body><p>Small page</p></body></html>")
    result = PageWeightCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_medium_page(make_ctx: MakeCtx) -> None:
    html = "<html><body>" + "<script>1;</script>" * 25 + "</body></html>"
    ctx = make_ctx(html)
    result = PageWeightCheck().run(ctx)
    assert result.status is Status.WARN


def test_fail_heavy_page(make_ctx: MakeCtx) -> None:
    html = "<html><body>" + "<script>1;</script>" * 45 + "</body></html>"
    ctx = make_ctx(html)
    result = PageWeightCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_large_html(make_ctx: MakeCtx) -> None:
    html = "<html><body><p>" + ("x" * 800_000) + "</p></body></html>"
    ctx = make_ctx(html)
    result = PageWeightCheck().run(ctx)
    assert result.status is Status.FAIL


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = PageWeightCheck().run(ctx)
    assert result.status is Status.SKIP
