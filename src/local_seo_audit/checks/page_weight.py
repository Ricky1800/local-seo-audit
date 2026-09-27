"""A bloated homepage (huge HTML, dozens of scripts) loses impatient mobile visitors."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status
from local_seo_audit.utils import human_bytes

HTML_WARN_BYTES = 300_000
HTML_FAIL_BYTES = 700_000
SCRIPT_WARN_COUNT = 20
SCRIPT_FAIL_COUNT = 40


class PageWeightCheck(Check):
    id = "page_weight"
    title = "Page weight (HTML size and script/style count)"
    weight = 5
    severity = Severity.LOW

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        html_bytes = ctx.primary.byte_size
        script_count = len(ctx.soup.find_all("script"))
        style_count = len(ctx.soup.find_all("style")) + len(
            ctx.soup.find_all("link", attrs={"rel": "stylesheet"})
        )

        evidence = (
            f"HTML size: {human_bytes(html_bytes)}. Scripts: {script_count}. "
            f"Stylesheets/style blocks: {style_count}."
        )
        fix = (
            "Trim unused scripts/plugins, compress images, and avoid heavy page builders where "
            "possible. A lighter homepage loads faster on mobile data, and page speed is a "
            "confirmed Google ranking factor."
        )

        if html_bytes >= HTML_FAIL_BYTES or script_count >= SCRIPT_FAIL_COUNT:
            status = Status.FAIL
        elif html_bytes >= HTML_WARN_BYTES or script_count >= SCRIPT_WARN_COUNT:
            status = Status.WARN
        else:
            status = Status.PASS
        return self.make(status, evidence, fix)
