from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.checks.nap_visible import NapVisibleCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_all_present(make_ctx: MakeCtx) -> None:
    html = "<p>Joe's Plumbing, 123 Main St, Princeton. Call (609) 555-0100.</p>"
    ctx = make_ctx(
        html,
        business=Business(name="Joe's Plumbing", phone="609-555-0100", address="123 main st"),
    )
    result = NapVisibleCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_none_present(make_ctx: MakeCtx) -> None:
    html = "<p>Welcome to our site.</p>"
    ctx = make_ctx(html, business=Business(name="Joe's Plumbing", phone="609-555-0100"))
    result = NapVisibleCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_partial(make_ctx: MakeCtx) -> None:
    html = "<p>Call us at (609) 555-0100 today!</p>"
    ctx = make_ctx(html, business=Business(name="Joe's Plumbing", phone="609-555-0100"))
    result = NapVisibleCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_no_business_info(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<p>hello</p>", business=Business())
    result = NapVisibleCheck().run(ctx)
    assert result.status is Status.SKIP


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "",
        business=Business(name="Joe's Plumbing"),
        primary=make_fetch_result("https://example.com/", "", status_code=500),
    )
    result = NapVisibleCheck().run(ctx)
    assert result.status is Status.SKIP
