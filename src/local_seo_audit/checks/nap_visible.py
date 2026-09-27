"""Name, Address, Phone must appear as plain, readable text on the page.

Structured data helps machines; a human landing on the page still needs to
be able to actually read a phone number to call. This check normalizes
common phone formats so "(609) 555-0100" and "609.555.0100" both count.
"""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status
from local_seo_audit.utils import phone_variants_in_text


class NapVisibleCheck(Check):
    id = "nap_visible"
    title = "Name, address, and phone are visible in the page text"
    weight = 10
    severity = Severity.HIGH

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        biz = ctx.business
        if not biz.has_any():
            return self.skip(
                "Skipped: no business name/address/phone was provided to check against "
                "(pass --name/--address/--phone)."
            )

        text = ctx.page_text
        lowered = text.lower()

        checks: dict[str, bool | None] = {}
        if biz.name:
            checks["name"] = biz.name.strip().lower() in lowered
        if biz.phone:
            checks["phone"] = phone_variants_in_text(biz.phone, text)
        if biz.address:
            checks["address"] = biz.address.strip().lower() in lowered

        found = [k for k, v in checks.items() if v]
        missing = [k for k, v in checks.items() if not v]

        evidence = (
            f"Visible on page: {', '.join(found) if found else 'none'}. "
            f"Missing: {', '.join(missing) if missing else 'none'}."
        )
        fix = (
            "Add a visible business name, address, and phone number as real text (not only inside "
            "an image or a contact-form widget) - ideally in the header or footer of every page. "
            "Visitors and Google both need to read this without extra clicks."
        )

        if not missing:
            status = Status.PASS
        elif not found:
            status = Status.FAIL
        else:
            status = Status.WARN
        return self.make(status, evidence, fix)
