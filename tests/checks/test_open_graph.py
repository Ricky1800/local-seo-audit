from __future__ import annotations

from local_seo_audit.checks.open_graph import OpenGraphCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult

ALL_OG_TAGS = """
<meta property="og:title" content="Joe's Plumbing">
<meta property="og:description" content="Plumbing in Princeton, NJ.">
<meta property="og:image" content="https://example.com/photo.jpg">
<meta property="og:url" content="https://example.com/">
"""


def test_pass_all_present(make_ctx: MakeCtx) -> None:
    ctx = make_ctx(ALL_OG_TAGS)
    result = OpenGraphCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_all_missing(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>")
    result = OpenGraphCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_partial(make_ctx: MakeCtx) -> None:
    html = (
        '<meta property="og:title" content="Joe\'s Plumbing">'
        '<meta property="og:url" content="https://example.com/">'
    )
    ctx = make_ctx(html)
    result = OpenGraphCheck().run(ctx)
    assert result.status is Status.WARN


def test_fail_only_one_present(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<meta property="og:title" content="Joe\'s Plumbing">')
    result = OpenGraphCheck().run(ctx)
    assert result.status is Status.FAIL


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = OpenGraphCheck().run(ctx)
    assert result.status is Status.SKIP
