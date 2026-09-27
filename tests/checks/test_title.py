from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.checks.title import TitleCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_good_title_with_city(make_ctx: MakeCtx) -> None:
    ctx = make_ctx(
        "<title>Joe's Plumbing | Princeton, NJ Plumber</title>",
        business=Business(city="Princeton"),
    )
    result = TitleCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_missing_title(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<title></title>")
    result = TitleCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_no_title_tag_at_all(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<p>no title here</p>")
    result = TitleCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_too_short_but_relevant(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<title>Joe NJ</title>", business=Business(city="NJ"))
    result = TitleCheck().run(ctx)
    assert result.status is Status.WARN


def test_warn_good_length_but_missing_city(make_ctx: MakeCtx) -> None:
    ctx = make_ctx(
        "<title>Best Plumbing Services Around</title>", business=Business(city="Princeton")
    )
    result = TitleCheck().run(ctx)
    assert result.status is Status.WARN


def test_pass_when_no_business_info_given(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<title>A Perfectly Fine Title</title>")
    result = TitleCheck().run(ctx)
    assert result.status is Status.PASS


def test_skip_when_page_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = TitleCheck().run(ctx)
    assert result.status is Status.SKIP
