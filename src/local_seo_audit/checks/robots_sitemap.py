"""robots.txt and sitemap.xml: how search engines are told what to crawl."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status


class RobotsSitemapCheck(Check):
    id = "robots_sitemap"
    title = "robots.txt and sitemap.xml are present"
    weight = 6
    severity = Severity.LOW

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        # A present, fetchable robots.txt is what matters most; content is a bonus signal.
        robots_present = ctx.robots.ok and bool(ctx.robots.text.strip())
        sitemap_present = ctx.sitemap.ok and bool(ctx.sitemap.text.strip())
        sitemap_referenced = sitemap_present and "sitemap:" in ctx.robots.text.lower()

        fix = (
            "Add a robots.txt file at the site root (even a simple 'User-agent: *\\nAllow: /') and "
            "a sitemap.xml listing the site's pages, then reference the sitemap from robots.txt "
            "with a 'Sitemap:' line. This helps Google discover and index every page."
        )

        notes = [
            f"robots.txt: {'found' if robots_present else 'missing/unreachable'}.",
            f"sitemap.xml: {'found' if sitemap_present else 'missing/unreachable'}.",
        ]
        if robots_present and sitemap_present:
            notes.append(
                "sitemap is referenced from robots.txt."
                if sitemap_referenced
                else "sitemap.xml exists but is not referenced from robots.txt."
            )

        if robots_present and sitemap_present:
            status = Status.PASS
        elif robots_present or sitemap_present:
            status = Status.WARN
        else:
            status = Status.FAIL
        return self.make(status, " ".join(notes), fix)
