"""A tel: link turns a phone number into a one-tap call on mobile."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status


class ClickToCallCheck(Check):
    id = "click_to_call"
    title = "Click-to-call (tel:) link"
    weight = 8
    severity = Severity.HIGH

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        tel_links = [
            a.get("href", "")
            for a in ctx.soup.find_all("a", href=True)
            if a["href"].startswith("tel:")
        ]
        fix = (
            'Wrap the phone number in a click-to-call link: <a href="tel:+16095550100">609-555-0100'
            "</a>. Most local-business searches happen on a phone; this turns the number into a "
            "one-tap call instead of forcing the visitor to dial manually."
        )

        if not tel_links:
            return self.make(Status.FAIL, "No tel: link found on the page.", fix)

        evidence = f"Found {len(tel_links)} tel: link(s): {', '.join(tel_links[:3])}."
        return self.make(Status.PASS, evidence, fix)
