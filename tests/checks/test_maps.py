from __future__ import annotations

from local_seo_audit.checks.maps import MapsEmbedCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_with_iframe(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<iframe src="https://www.google.com/maps/embed?pb=x"></iframe>')
    result = MapsEmbedCheck().run(ctx)
    assert result.status is Status.PASS


def test_pass_with_link(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<a href="https://goo.gl/maps/abc123">Directions</a>')
    result = MapsEmbedCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_no_maps_reference(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<a href="https://example.com/contact">Contact</a>')
    result = MapsEmbedCheck().run(ctx)
    assert result.status is Status.FAIL


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = MapsEmbedCheck().run(ctx)
    assert result.status is Status.SKIP
