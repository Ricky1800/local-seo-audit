"""A canonical tag tells search engines which URL is the "real" one."""

from __future__ import annotations

from bs4 import Tag

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status
from local_seo_audit.utils import same_host


class CanonicalCheck(Check):
    id = "canonical"
    title = "Canonical tag"
    weight = 5
    severity = Severity.LOW

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        link = ctx.soup.find("link", attrs={"rel": "canonical"})
        fix = (
            'Add <link rel="canonical" href="https://example.com/"> in the <head>, pointing to the '
            "preferred version of the URL. This prevents Google from splitting ranking signals "
            "across http/https or www/non-www duplicates of the same page."
        )

        if not isinstance(link, Tag):
            return self.make(Status.WARN, "No canonical tag found.", fix)

        href = link.get("href", "")
        href = href.strip() if isinstance(href, str) else ""
        if not href:
            return self.make(Status.WARN, "Canonical tag present but has no href.", fix)

        if same_host(href, ctx.page_url):
            return self.make(Status.PASS, f"Canonical tag points to {href}.", fix)
        return self.make(
            Status.WARN,
            f"Canonical tag points to a different host ({href}) than the page itself.",
            fix,
        )
