from __future__ import annotations

from local_seo_audit.checks.canonical import CanonicalCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<link rel="canonical" href="https://example.com/">', url="https://example.com/")
    result = CanonicalCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_missing(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>")
    result = CanonicalCheck().run(ctx)
    assert result.status is Status.WARN


def test_warn_empty_href(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<link rel="canonical" href="">')
    result = CanonicalCheck().run(ctx)
    assert result.status is Status.WARN


def test_warn_different_host(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<link rel="canonical" href="https://other.com/">', url="https://example.com/")
    result = CanonicalCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = CanonicalCheck().run(ctx)
    assert result.status is Status.SKIP
