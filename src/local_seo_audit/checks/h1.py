"""Exactly one <h1> gives both visitors and search engines a clear page topic."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status


class H1Check(Check):
    id = "h1"
    title = "Exactly one H1 heading"
    weight = 6
    severity = Severity.MEDIUM

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        headings = [h.get_text(strip=True) for h in ctx.soup.find_all("h1")]
        count = len(headings)
        fix = (
            "Use exactly one <h1> per page, stating what the business is and does (e.g. "
            "'Princeton's Trusted Local Plumber'). Multiple or missing H1s confuse both readers "
            "and search engines about the page's main topic."
        )

        if count == 1:
            return self.make(Status.PASS, f'Found exactly one H1: "{headings[0]}".', fix)
        if count == 0:
            return self.make(Status.FAIL, "No H1 heading found on the page.", fix)
        preview = "; ".join(f'"{h}"' for h in headings[:5])
        return self.make(Status.WARN, f"Found {count} H1 headings: {preview}.", fix)
