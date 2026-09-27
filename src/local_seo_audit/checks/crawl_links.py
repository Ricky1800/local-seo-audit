"""Optional (--crawl N): a capped, same-host crawl looking for broken internal links."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status


class CrawlBrokenLinksCheck(Check):
    id = "crawl_broken_links"
    title = "Internal links are not broken (--crawl)"
    weight = 5
    severity = Severity.MEDIUM

    def run(self, ctx: AuditContext) -> CheckResult:
        if ctx.crawl_requested <= 0:
            return self.skip("Skipped: pass --crawl N to check internal links for 404s/errors.")
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")
        if ctx.crawl is None or not ctx.crawl.checked:
            return self.skip("Skipped: no same-host internal links were found to crawl.")

        fix = (
            "Fix or remove links pointing at pages that no longer exist (404) or error out. "
            "Broken internal links waste the crawl budget search engines give the site and leave "
            "visitors on a dead end."
        )
        broken = ctx.crawl.broken
        checked_n = len(ctx.crawl.checked)
        evidence = f"Checked {checked_n} internal link(s) (capped at {ctx.crawl.requested})."
        if broken:
            detail = "; ".join(f"{b.url} -> {b.error or b.status_code}" for b in broken[:5])
            evidence += f" Broken: {len(broken)}: {detail}."
            status = Status.FAIL if len(broken) > checked_n / 2 else Status.WARN
        else:
            evidence += " No broken links found."
            status = Status.PASS
        return self.make(status, evidence, fix)
