"""Markdown output: easy to paste into an email, Slack message, or GitHub issue."""

from __future__ import annotations

from local_seo_audit.models import Report, Status

_STATUS_EMOJI = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌", Status.SKIP: "⏭️"}


def render_markdown(report: Report) -> str:
    lines: list[str] = [f"# Local SEO Audit — {report.url}", ""]
    if report.business.name:
        lines.append(f"**Business:** {report.business.name}  ")
    lines.append(f"**Generated:** {report.generated_at:%Y-%m-%d %H:%M}  ")
    lines.append(f"**Score:** {report.score}/100 — **Grade: {report.grade}**")
    lines.append("")

    counts = report.counts()
    lines.append(
        f"Pass: {counts[Status.PASS]} &nbsp;·&nbsp; Warn: {counts[Status.WARN]} &nbsp;·&nbsp; "
        f"Fail: {counts[Status.FAIL]} &nbsp;·&nbsp; Skipped: {counts[Status.SKIP]}"
    )
    lines.append("")
    lines.append("## Prioritized fix list")
    lines.append("")

    for result in report.sorted_results:
        emoji = _STATUS_EMOJI[result.status]
        lines.append(
            f"### {emoji} {result.title} "
            f"`{result.status.value}` · weight {result.weight} · {result.severity.value}"
        )
        lines.append("")
        lines.append(f"- **Evidence:** {result.evidence}")
        if result.status in (Status.WARN, Status.FAIL) and result.fix:
            lines.append(f"- **Fix:** {result.fix}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
