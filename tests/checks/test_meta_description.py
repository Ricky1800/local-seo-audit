from __future__ import annotations

from local_seo_audit.checks.meta_description import MetaDescriptionCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_good_length(make_ctx: MakeCtx) -> None:
    description = (
        "Joe's Plumbing offers 24/7 emergency plumbing repair and drain cleaning in Princeton, NJ."
    )
    ctx = make_ctx(f'<meta name="description" content="{description}">')
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_missing(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>")
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_empty_content(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<meta name="description" content="">')
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_too_short(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<meta name="description" content="Plumber in NJ.">')
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.WARN


def test_warn_too_long(make_ctx: MakeCtx) -> None:
    long_desc = "Plumbing services. " * 20
    ctx = make_ctx(f'<meta name="description" content="{long_desc}">')
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = MetaDescriptionCheck().run(ctx)
    assert result.status is Status.SKIP
