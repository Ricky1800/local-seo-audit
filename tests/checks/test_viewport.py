from __future__ import annotations

from local_seo_audit.checks.viewport import ViewportCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<meta name="viewport" content="width=device-width, initial-scale=1">')
    result = ViewportCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_missing(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>")
    result = ViewportCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_unusual_content(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<meta name="viewport" content="initial-scale=1">')
    result = ViewportCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = ViewportCheck().run(ctx)
    assert result.status is Status.SKIP
