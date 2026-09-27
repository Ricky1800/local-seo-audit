"""A favicon is a small trust signal: its absence reads as unfinished/abandoned."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

ICON_RELS = {"icon", "shortcut icon", "apple-touch-icon"}


class FaviconCheck(Check):
    id = "favicon"
    title = "Favicon is present"
    weight = 3
    severity = Severity.INFO

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        linked = False
        for link in ctx.soup.find_all("link", rel=True):
            rel = link.get("rel")
            rel_values = {r.lower() for r in rel} if isinstance(rel, list) else {str(rel).lower()}
            if rel_values & ICON_RELS:
                linked = True
                break

        default_ok = ctx.favicon.ok
        fix = (
            'Add a favicon: either a favicon.ico at the site root, or a <link rel="icon" '
            'href="/favicon.png"> tag in the <head>. It is a small polish detail that makes the '
            "site feel maintained in browser tabs and bookmarks."
        )

        if linked or default_ok:
            evidence = f"Favicon found via {'<link> tag' if linked else '/favicon.ico'}."
            return self.make(Status.PASS, evidence, fix)
        return self.make(
            Status.WARN, "No favicon <link> tag and /favicon.ico is not reachable.", fix
        )
