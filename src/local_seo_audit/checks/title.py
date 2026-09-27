"""The <title> tag: present, a sensible length, and locally relevant."""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status

MIN_LEN = 10
MAX_LEN = 60


class TitleCheck(Check):
    id = "title"
    title = "Title tag is present, well-sized, and locally relevant"
    weight = 8
    severity = Severity.HIGH

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        tag = ctx.soup.title
        text = tag.get_text(strip=True) if tag is not None else ""

        if not text:
            return self.make(
                Status.FAIL,
                "No <title> tag (or it is empty).",
                "Add a <title> naming the business and its city, e.g. "
                "'Joe's Plumbing | Princeton, NJ Plumber'. It is the headline Google shows in "
                "search results and the browser tab label.",
            )

        length_ok = MIN_LEN <= len(text) <= MAX_LEN
        city = (ctx.business.city or "").strip().lower()
        name = (ctx.business.name or "").strip().lower()
        lowered = text.lower()
        mentions_city = bool(city) and city in lowered
        mentions_name = bool(name) and name in lowered

        notes = [f'Title: "{text}" ({len(text)} characters).']
        if ctx.business.city:
            notes.append("Mentions the city." if mentions_city else "Does not mention the city.")
        if ctx.business.name:
            notes.append(
                "Mentions the business name."
                if mentions_name
                else "Does not mention the business name."
            )

        relevance_known = bool(city or name)
        relevance_ok = (mentions_city or mentions_name) if relevance_known else True

        if length_ok and relevance_ok:
            status = Status.PASS
        elif length_ok or relevance_ok:
            status = Status.WARN
        else:
            status = Status.FAIL

        fix = (
            f"Keep the title between {MIN_LEN} and {MAX_LEN} characters and include what the "
            "business does plus its city or service area, e.g. 'Joe's Plumbing | Emergency "
            "Plumber in Princeton, NJ'. That combination is what shows up (and gets clicked) in "
            "local Google searches."
        )
        return self.make(status, " ".join(notes), fix)
