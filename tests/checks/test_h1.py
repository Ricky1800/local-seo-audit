from __future__ import annotations

from local_seo_audit.checks.h1 import H1Check
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_exactly_one(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<h1>Princeton's Trusted Plumber</h1>")
    result = H1Check().run(ctx)
    assert result.status is Status.PASS


def test_fail_zero(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<h2>Not an H1</h2>")
    result = H1Check().run(ctx)
    assert result.status is Status.FAIL


def test_warn_multiple(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<h1>First</h1><h1>Second</h1>")
    result = H1Check().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = H1Check().run(ctx)
    assert result.status is Status.SKIP
