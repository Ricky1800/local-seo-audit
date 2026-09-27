"""Open Graph tags control how the page looks when shared on social/messaging apps."""

from __future__ import annotations

from bs4 import Tag

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

REQUIRED_OG = ("og:title", "og:description", "og:image", "og:url")


class OpenGraphCheck(Check):
    id = "open_graph"
    title = "Open Graph tags"
    weight = 4
    severity = Severity.LOW

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        present: set[str] = set()
        for prop in REQUIRED_OG:
            tag = ctx.soup.find("meta", attrs={"property": prop})
            if isinstance(tag, Tag) and str(tag.get("content", "")).strip():
                present.add(prop)

        missing = [p for p in REQUIRED_OG if p not in present]
        evidence = (
            f"Present: {', '.join(sorted(present)) or 'none'}. "
            f"Missing: {', '.join(missing) or 'none'}."
        )
        fix = (
            "Add og:title, og:description, og:image, and og:url meta tags. Without them, links "
            "shared on Facebook, Instagram, or in a text message show a blank or ugly preview "
            "instead of a photo and description of the business."
        )

        if not missing:
            status = Status.PASS
        elif len(missing) <= 2:
            status = Status.WARN
        else:
            status = Status.FAIL
        return self.make(status, evidence, fix)
