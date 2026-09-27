from __future__ import annotations

from local_seo_audit.checks.https_redirect import HttpsRedirectCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult


def test_pass_when_https_and_redirect_ok(
    make_ctx: MakeCtx, make_fetch_result: MakeFetchResult
) -> None:
    ctx = make_ctx(
        "<html></html>",
        url="https://example.com/",
        http_probe=make_fetch_result(
            "http://example.com/", final_url="https://example.com/", redirected=True
        ),
    )
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_when_https_but_no_redirect(
    make_ctx: MakeCtx, make_fetch_result: MakeFetchResult
) -> None:
    ctx = make_ctx(
        "<html></html>",
        url="https://example.com/",
        http_probe=make_fetch_result("http://example.com/", final_url="http://example.com/"),
    )
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.WARN


def test_fail_when_no_https(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "<html></html>",
        url="http://example.com/",
        primary=make_fetch_result(
            "http://example.com/", "<html></html>", final_url="http://example.com/"
        ),
    )
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_when_page_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx(
        "",
        primary=make_fetch_result(
            "https://example.com/", "", status_code=0, error="ConnectError: boom"
        ),
    )
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.FAIL
    assert "boom" in result.evidence


def test_pass_when_probe_unavailable_but_https_ok(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>", url="https://example.com/", http_probe=None)
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_when_probe_itself_fails(
    make_ctx: MakeCtx, make_fetch_result: MakeFetchResult
) -> None:
    ctx = make_ctx(
        "<html></html>",
        url="https://example.com/",
        http_probe=make_fetch_result(
            "http://example.com/", status_code=0, error="ConnectError: timed out"
        ),
    )
    result = HttpsRedirectCheck().run(ctx)
    assert result.status is Status.PASS
    assert "Could not test" in result.evidence
