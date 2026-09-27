"""A Google Maps link or embed makes "how do I get there" a one-click answer."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

MAPS_MARKERS = ("google.com/maps", "maps.google.", "goo.gl/maps", "maps.app.goo.gl")


def _has_maps_reference(url: str) -> bool:
    lowered = url.lower()
    return any(marker in lowered for marker in MAPS_MARKERS)


class MapsEmbedCheck(Check):
    id = "maps_embed"
    title = "Google Maps link or embed"
    weight = 6
    severity = Severity.MEDIUM

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        links = [a.get("href", "") for a in ctx.soup.find_all("a", href=True)]
        iframes = [f.get("src", "") for f in ctx.soup.find_all("iframe", src=True)]

        matching_links = [link for link in links if _has_maps_reference(link)]
        matching_iframes = [src for src in iframes if _has_maps_reference(src)]

        fix = (
            "Add a link or embedded iframe pointing to the business's Google Maps listing, e.g. "
            'a "Get Directions" button. This is one of the first things a local visitor looks for.'
        )

        if matching_iframes:
            return self.make(
                Status.PASS, f"Found an embedded Google Maps iframe: {matching_iframes[0]}.", fix
            )
        if matching_links:
            return self.make(Status.PASS, f"Found a Google Maps link: {matching_links[0]}.", fix)
        return self.make(Status.FAIL, "No Google Maps link or embed found on the page.", fix)
