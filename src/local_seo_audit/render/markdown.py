"""Markdown output: easy to paste into an email, Slack message, or GitHub issue."""

from __future__ import annotations

from local_seo_audit.models import Report, Status
from local_seo_audit.vitals import LabData, Metric, Rating, StrategyResult, VitalsResult

_STATUS_EMOJI = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌", Status.SKIP: "⏭️"}

_RATING_EMOJI: dict[Rating, str] = {"good": "🟢", "needs-improvement": "🟡", "poor": "🔴"}


def _metric_text(metric: Metric) -> str:
    value = f"{metric.value:.2f}" if metric.unit == "" else f"{metric.value:.0f}{metric.unit}"
    return f"{metric.name} {value} {_RATING_EMOJI[metric.rating]} {metric.rating}"


def _vitals_lines(vitals: VitalsResult) -> list[str]:
    lines = ["## Core Web Vitals", "", "_Source: Google PageSpeed Insights._", ""]
    for result in vitals.by_strategy():
        lines.append(f"### {result.strategy.capitalize()}")
        lines.append("")
        if result.error:
            lines.append(f"- **Error:** {result.error}")
            lines.append("")
            continue
        field: StrategyResult = result
        if field.field_data and field.field_data.has_any():
            parts = ", ".join(
                _metric_text(m)
                for m in (field.field_data.lcp, field.field_data.inp, field.field_data.cls)
                if m is not None
            )
            lines.append(f"- **Field data (real users):** {parts}")
        else:
            lines.append("- **Field data (real users):** not enough Chrome traffic data.")
        lab: LabData | None = result.lab_data
        if lab is not None:
            score = (
                f"{lab.performance_score:.0f}/100" if lab.performance_score is not None else "n/a"
            )
            parts = ", ".join(_metric_text(m) for m in (lab.lcp, lab.tbt, lab.cls) if m is not None)
            lines.append(f"- **Lab data (Lighthouse):** performance {score} — {parts}")
            if lab.opportunities:
                lines.append("- **Top opportunities:**")
                for opportunity in lab.opportunities:
                    lines.append(f"  - {opportunity}")
        lines.append("")
    return lines


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

    if report.vitals is not None:
        lines.extend(_vitals_lines(report.vitals))

    return "\n".join(lines).rstrip() + "\n"
