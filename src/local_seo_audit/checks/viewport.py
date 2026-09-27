"""A mobile viewport meta tag: most local searches happen on a phone."""

from __future__ import annotations

from bs4 import Tag

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status


class ViewportCheck(Check):
    id = "viewport"
    title = "Mobile viewport meta tag"
    weight = 7
    severity = Severity.HIGH

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        meta = ctx.soup.find("meta", attrs={"name": "viewport"})
        fix = (
            'Add <meta name="viewport" content="width=device-width, initial-scale=1"> to the '
            "<head>. Most local searches happen on a phone; without this tag the page renders "
            "zoomed-out and hard to use on mobile."
        )

        if not isinstance(meta, Tag):
            return self.make(Status.FAIL, "No viewport meta tag found.", fix)

        raw = meta.get("content", "")
        content = raw.strip() if isinstance(raw, str) else ""
        if "width=device-width" in content.replace(" ", ""):
            return self.make(Status.PASS, f'Viewport meta tag: "{content}".', fix)
        return self.make(Status.WARN, f'Viewport meta tag present but unusual: "{content}".', fix)
