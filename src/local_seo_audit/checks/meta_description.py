"""The meta description: present and a length Google won't truncate/pad."""

from __future__ import annotations

from bs4 import Tag

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

MIN_LEN = 50
MAX_LEN = 160


class MetaDescriptionCheck(Check):
    id = "meta_description"
    title = "Meta description is present and well-sized"
    weight = 6
    severity = Severity.MEDIUM

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        meta = ctx.soup.find("meta", attrs={"name": "description"})
        content = ""
        if isinstance(meta, Tag):
            raw = meta.get("content", "")
            content = raw.strip() if isinstance(raw, str) else ""

        fix = (
            f'Add a <meta name="description"> between {MIN_LEN} and {MAX_LEN} characters that '
            "summarizes what the business does and where, with a reason to click. This is the "
            "snippet Google shows under the title in search results."
        )

        if not content:
            return self.make(Status.FAIL, "No meta description found.", fix)

        length_ok = MIN_LEN <= len(content) <= MAX_LEN
        evidence = f'Meta description: "{content}" ({len(content)} characters).'
        status = Status.PASS if length_ok else Status.WARN
        return self.make(status, evidence, fix)
