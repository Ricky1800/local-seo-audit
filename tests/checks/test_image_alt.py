from __future__ import annotations

from local_seo_audit.checks.image_alt import ImageAltCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_full_coverage(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<img src="a.jpg" alt="Storefront"><img src="b.jpg" alt="Van">')
    result = ImageAltCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_no_alt_text(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<img src="a.jpg"><img src="b.jpg">')
    result = ImageAltCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_partial_coverage(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<img src="a.jpg" alt="Storefront"><img src="b.jpg">')
    result = ImageAltCheck().run(ctx)
    assert result.status is Status.WARN


def test_skip_no_images(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<p>No images here.</p>")
    result = ImageAltCheck().run(ctx)
    assert result.status is Status.SKIP


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = ImageAltCheck().run(ctx)
    assert result.status is Status.SKIP
