from __future__ import annotations

from local_seo_audit.checks.base import CrawlLinkStatus, CrawlResult
from local_seo_audit.checks.crawl_links import CrawlBrokenLinksCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx


def test_skip_when_not_requested(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>", crawl_requested=0, crawl=None)
    result = CrawlBrokenLinksCheck().run(ctx)
    assert result.status is Status.SKIP


def test_skip_when_no_links_found(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>", crawl_requested=5, crawl=CrawlResult(checked=[], requested=5))
    result = CrawlBrokenLinksCheck().run(ctx)
    assert result.status is Status.SKIP


def test_pass_no_broken_links(make_ctx: MakeCtx) -> None:
    crawl = CrawlResult(
        checked=[CrawlLinkStatus(url="https://example.com/about", status_code=200, ok=True)],
        requested=5,
    )
    ctx = make_ctx("<html></html>", crawl_requested=5, crawl=crawl)
    result = CrawlBrokenLinksCheck().run(ctx)
    assert result.status is Status.PASS


def test_warn_some_broken(make_ctx: MakeCtx) -> None:
    crawl = CrawlResult(
        checked=[
            CrawlLinkStatus(url="https://example.com/a", status_code=200, ok=True),
            CrawlLinkStatus(url="https://example.com/b", status_code=200, ok=True),
            CrawlLinkStatus(url="https://example.com/c", status_code=404, ok=False),
        ],
        requested=5,
    )
    ctx = make_ctx("<html></html>", crawl_requested=5, crawl=crawl)
    result = CrawlBrokenLinksCheck().run(ctx)
    assert result.status is Status.WARN


def test_fail_majority_broken(make_ctx: MakeCtx) -> None:
    crawl = CrawlResult(
        checked=[
            CrawlLinkStatus(url="https://example.com/a", status_code=404, ok=False),
            CrawlLinkStatus(url="https://example.com/b", status_code=500, ok=False),
            CrawlLinkStatus(url="https://example.com/c", status_code=200, ok=True),
        ],
        requested=5,
    )
    ctx = make_ctx("<html></html>", crawl_requested=5, crawl=crawl)
    result = CrawlBrokenLinksCheck().run(ctx)
    assert result.status is Status.FAIL
