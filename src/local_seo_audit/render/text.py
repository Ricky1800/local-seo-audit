"""Colored terminal output, built with `rich`."""

from __future__ import annotations

import io
from collections.abc import Sequence

from rich.console import Console

from local_seo_audit.compare import CompetitorComparison
from local_seo_audit.content_gaps import ContentGapPlan
from local_seo_audit.crawler import SiteCrawlReport
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


def _print_site_crawl(console: Console, crawl: SiteCrawlReport) -> None:
    console.print("")
    console.print(
        f"[bold]Site crawl[/bold]: {crawl.pages_crawled} page(s) visited "
        f"(cap {crawl.max_pages}), {len(crawl.sitemap_urls)} in sitemap, "
        f"{crawl.issue_count()} site-level issue(s) found."
    )
    console.print("  Pages:")
    for page in sorted(crawl.pages, key=lambda p: p.url):
        status = "OK" if page.ok else f"ERROR {page.status_code}"
        console.print(
            f"    [{status}] depth {page.depth}  {page.url}  {page.title or '(no title)'}"
        )

    def _list(label: str, items: Sequence[object]) -> None:
        if items:
            console.print(f"  {label}: {len(items)}")

    _list("Duplicate titles", crawl.duplicate_titles)
    _list("Duplicate meta descriptions", crawl.duplicate_descriptions)
    _list("Missing H1", crawl.missing_h1)
    _list("Duplicate H1", crawl.duplicate_h1_pages)
    _list("Heading order issues", crawl.heading_order_issues)
    _list("Thin content pages", crawl.thin_content)
    _list("Canonical issues", crawl.canonical_issues)
    _list("Redirect chains", crawl.redirect_chains)
    _list("Error pages (4xx/5xx)", crawl.error_pages)
    _list("Orphan pages (in sitemap, not linked)", crawl.orphan_pages)
    _list("Pages deeper than 3 clicks", crawl.deep_pages)
    _list("Crawled pages missing from sitemap", crawl.missing_from_sitemap)


def _print_compare(console: Console, comparison: CompetitorComparison) -> None:
    console.print("")
    console.print("[bold]Competitor compare[/bold]")
    header = "  Check".ljust(46) + "You".ljust(10)
    header += "".join(entry.url.ljust(24) for entry in comparison.competitors)
    console.print(header)
    for row in comparison.matrix:
        line = f"  {row.title[:44]}".ljust(46)
        line += (row.your_status or "-").ljust(10)
        line += "".join((status or "-").ljust(24) for status in row.competitor_statuses)
        console.print(line)

    console.print("")
    console.print("[bold]Gaps[/bold] (they have it, you don't - ranked by impact):")
    if not comparison.gaps:
        console.print("  None found.")
    for gap in comparison.gaps:
        who = ", ".join(gap.ahead_competitors)
        console.print(f"  - {gap.title} (weight {gap.weight}) - ahead: {who}")


def _print_content_plan(console: Console, plan: ContentGapPlan) -> None:
    console.print("")
    console.print("[bold]Local content gaps[/bold]")
    label = "inferred from nav/headings" if plan.inferred_services else "as requested"
    console.print(f"  Services checked ({label}):")
    for status in plan.services:
        mark = "[bold green]found[/bold green]" if status.found else "[bold red]missing[/bold red]"
        suffix = f"  ({status.matched_url})" if status.matched_url else ""
        console.print(f"    {mark}  {status.query}{suffix}")
    if plan.areas:
        console.print("  Areas checked:")
        for status in plan.areas:
            mark = (
                "[bold green]found[/bold green]" if status.found else "[bold red]missing[/bold red]"
            )
            console.print(f"    {mark}  {status.query}")
    console.print(
        f"  NAP: {len(plan.nap.distinct_phone_numbers)} distinct phone number(s) across "
        f"{plan.nap.pages_checked} page(s); consistent: {plan.nap.phone_consistent}."
    )
    covered = plan.click_to_call.pages_checked - len(plan.click_to_call.pages_missing)
    console.print(
        f"  Click-to-call: {covered}/{plan.click_to_call.pages_checked} page(s) have a tel: link."
    )
    console.print(
        f"  Review/AggregateRating schema: {plan.schema.has_review_schema_anywhere}. "
        f"FAQPage schema: {plan.schema.has_faq_schema_anywhere}."
    )
    console.print(
        f"  Google Business Profile link: {plan.has_gbp_link}. "
        f"Contact page map: {plan.has_contact_page_map}."
    )
    console.print("")
    console.print("[bold]Content to create[/bold] (prioritized):")
    if not plan.plan:
        console.print("  Nothing found - great coverage.")
    for item in plan.plan:
        console.print(f"  [{item.priority.upper()}] {item.title}")
        console.print(f"    {item.why}")


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

    if report.site_crawl is not None:
        _print_site_crawl(console, report.site_crawl)

    if report.competitors is not None:
        _print_compare(console, report.competitors)

    if report.content_plan is not None:
        _print_content_plan(console, report.content_plan)

    return buffer.getvalue()
