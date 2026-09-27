"""HTTPS must be enabled, and plain http:// must redirect to it."""

from __future__ import annotations

from urllib.parse import urlparse

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

_FIX = (
    "Install an SSL certificate (most modern hosts, including Vercel and Netlify, issue one for "
    "free) and configure the server to redirect every http:// request to https://. Without this, "
    "browsers mark the site 'Not Secure', which scares off visitors, and Google ranks insecure "
    "sites lower."
)


class HttpsRedirectCheck(Check):
    id = "https_redirect"
    title = "HTTPS is enabled, and HTTP redirects to HTTPS"
    weight = 12
    severity = Severity.CRITICAL

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            reason = ctx.primary.error or f"HTTP {ctx.primary.status_code}"
            return self.make(
                Status.FAIL,
                f"Could not load {ctx.input_url}: {reason}.",
                "Make sure the website is online and reachable at this address. A site that will "
                "not load loses every visitor, and every check below depends on it working.",
            )

        scheme = urlparse(ctx.primary.final_url).scheme
        https_ok = scheme == "https"

        redirect_ok: bool | None = None
        redirect_note = ""
        if ctx.http_probe is not None:
            if ctx.http_probe.ok:
                probe_scheme = urlparse(ctx.http_probe.final_url).scheme
                redirect_ok = probe_scheme == "https"
                if redirect_ok:
                    redirect_note = f" http:// correctly redirects to {ctx.http_probe.final_url}."
                else:
                    redirect_note = (
                        f" http:// does NOT redirect to https:// (landed on "
                        f"{ctx.http_probe.final_url})."
                    )
            else:
                redirect_note = " Could not test whether the plain http:// version redirects."

        if https_ok and redirect_ok is not False:
            status = Status.PASS
        elif https_ok:
            status = Status.WARN
        else:
            status = Status.FAIL

        evidence = f"Final URL loads as {ctx.primary.final_url} (scheme: {scheme})." + redirect_note
        return self.make(status, evidence, _FIX)
