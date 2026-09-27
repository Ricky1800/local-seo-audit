"""Colored terminal output, built with `rich`."""

from __future__ import annotations

import io

from rich.console import Console

from local_seo_audit.models import Report, Status
from local_seo_audit.vitals import LabData, Metric, Rating, StrategyResult, VitalsResult

_STATUS_STYLE = {
    Status.PASS: "bold green",
    Status.WARN: "bold yellow",
    Status.FAIL: "bold red",
    Status.SKIP: "dim",
}
_STATUS_LABEL = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}

_RATING_STYLE: dict[Rating, str] = {
    "good": "bold green",
    "needs-improvement": "bold yellow",
    "poor": "bold red",
}


def _grade_style(grade: str) -> str:
    if grade in ("A", "B"):
        return "bold green"
    if grade == "C":
        return "bold yellow"
    return "bold red"


def _metric_line(metric: Metric) -> str:
    style = _RATING_STYLE[metric.rating]
    value = f"{metric.value:.2f}" if metric.unit == "" else f"{metric.value:.0f}{metric.unit}"
    return f"{metric.name}: {value} [{style}]{metric.rating}[/{style}]"


def _print_strategy(console: Console, result: StrategyResult) -> None:
    console.print(f"  [bold]{result.strategy.capitalize()}[/bold]")
    if result.error:
        console.print(f"    [bold red]Error:[/bold red] {result.error}")
        return
    if result.field_data and result.field_data.has_any():
        parts = [
            _metric_line(m)
            for m in (result.field_data.lcp, result.field_data.inp, result.field_data.cls)
            if m is not None
        ]
        console.print("    Field data (real users): " + "  ".join(parts))
    else:
        console.print("    Field data (real users): not enough Chrome traffic data available.")
    lab: LabData | None = result.lab_data
    if lab is not None:
        score = f"{lab.performance_score:.0f}/100" if lab.performance_score is not None else "n/a"
        parts = [_metric_line(m) for m in (lab.lcp, lab.tbt, lab.cls) if m is not None]
        console.print(f"    Lab data (Lighthouse): performance {score}  " + "  ".join(parts))
        if lab.opportunities:
            console.print("    Top opportunities:")
            for opportunity in lab.opportunities:
                console.print(f"      - {opportunity}")


def _print_vitals(console: Console, vitals: VitalsResult) -> None:
    console.print("")
    console.print("[bold]Core Web Vitals[/bold] (Google PageSpeed Insights)")
    for result in vitals.by_strategy():
        _print_strategy(console, result)


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

    if report.vitals is not None:
        _print_vitals(console, report.vitals)

    return buffer.getvalue()
