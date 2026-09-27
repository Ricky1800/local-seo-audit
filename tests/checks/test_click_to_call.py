from __future__ import annotations

from local_seo_audit.checks.click_to_call import ClickToCallCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<a href="tel:+16095550100">Call</a>')
    result = ClickToCallCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_no_tel_link(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<p>609-555-0100</p>")
    result = ClickToCallCheck().run(ctx)
    assert result.status is Status.FAIL


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = ClickToCallCheck().run(ctx)
    assert result.status is Status.SKIP
