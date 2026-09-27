"""Alt text on images: accessibility, plus context Google can index."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

WARN_THRESHOLD = 0.5
PASS_THRESHOLD = 0.9


class ImageAltCheck(Check):
    id = "image_alt"
    title = "Images have descriptive alt text"
    weight = 6
    severity = Severity.MEDIUM

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        images = ctx.soup.find_all("img")
        fix = (
            "Add descriptive alt text to every meaningful image, e.g. alt=\"Exterior of Joe's "
            'Plumbing storefront in Princeton, NJ". Purely decorative images can use alt="". This '
            "helps screen-reader users and gives Google extra local-relevance context."
        )

        if not images:
            return self.skip("Skipped: no <img> tags found on the page.")

        with_alt = 0
        for img in images:
            alt = img.get("alt")
            if isinstance(alt, str) and alt.strip():
                with_alt += 1

        total = len(images)
        coverage = with_alt / total
        evidence = f"{with_alt}/{total} images ({coverage:.0%}) have non-empty alt text."

        if coverage >= PASS_THRESHOLD:
            status = Status.PASS
        elif coverage >= WARN_THRESHOLD:
            status = Status.WARN
        else:
            status = Status.FAIL
        return self.make(status, evidence, fix)
