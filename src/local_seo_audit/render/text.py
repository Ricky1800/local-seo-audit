"""Colored terminal output, built with `rich`."""

from __future__ import annotations

import io

from rich.console import Console

from local_seo_audit.models import Report, Status

_STATUS_STYLE = {
    Status.PASS: "bold green",
    Status.WARN: "bold yellow",
    Status.FAIL: "bold red",
    Status.SKIP: "dim",
}
_STATUS_LABEL = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}


def _grade_style(grade: str) -> str:
    if grade in ("A", "B"):
        return "bold green"
    if grade == "C":
        return "bold yellow"
    return "bold red"


def render_text(report: Report, *, color: bool = True, width: int = 100) -> str:
    """Render ``report`` as terminal text; ``color=False`` yields plain text (e.g. for a file)."""
    buffer = io.StringIO()
    console = Console(
        file=buffer, force_terminal=color, no_color=not color, width=width, highlight=False
    )

    console.print("[bold]Local SEO Audit[/bold]")
    console.print(f"URL: {report.url}")
    if report.business.name:
        console.print(f"Business: {report.business.name}")
    console.print(f"Generated: {report.generated_at:%Y-%m-%d %H:%M}")
    console.print(
        f"Score: [bold]{report.score}/100[/bold]   "
        f"Grade: [{_grade_style(report.grade)}]{report.grade}[/{_grade_style(report.grade)}]"
    )

    counts = report.counts()
    console.print(
        f"Pass: [bold green]{counts[Status.PASS]}[/]  "
        f"Warn: [bold yellow]{counts[Status.WARN]}[/]  "
        f"Fail: [bold red]{counts[Status.FAIL]}[/]  "
        f"Skipped: [dim]{counts[Status.SKIP]}[/]"
    )
    console.print("")
    console.print("[bold]Prioritized fix list[/bold] (worst first):")
    for result in report.sorted_results:
        style = _STATUS_STYLE[result.status]
        label = _STATUS_LABEL[result.status]
        console.print(
            f"[{style}][{label}][/{style}] {result.title}"
            f"  (weight {result.weight}, {result.severity.value})"
        )
        console.print(f"    {result.evidence}")
        if result.status in (Status.WARN, Status.FAIL) and result.fix:
            console.print(f"    [italic]Fix:[/italic] {result.fix}")
    return buffer.getvalue()
