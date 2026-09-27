"""Markdown output: easy to paste into an email, Slack message, or GitHub issue."""

from __future__ import annotations

from collections.abc import Sequence

from local_seo_audit.compare import CompetitorComparison
from local_seo_audit.content_gaps import ContentGapPlan
from local_seo_audit.crawler import SiteCrawlReport
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


def _compare_lines(comparison: CompetitorComparison) -> list[str]:
    lines = ["## Competitor compare", ""]
    header = ["Check", "You"] + [entry.url for entry in comparison.competitors]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for row in comparison.matrix:
        cells = [row.title, row.your_status or "-"]
        cells.extend(status or "-" for status in row.competitor_statuses)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("### Gaps (they have it, you don't - ranked by impact)")
    lines.append("")
    if not comparison.gaps:
        lines.append("None found.")
    for gap in comparison.gaps:
        who = ", ".join(gap.ahead_competitors)
        lines.append(f"- **{gap.title}** (weight {gap.weight}) - ahead: {who}")
    lines.append("")
    return lines


def _content_plan_lines(plan: ContentGapPlan) -> list[str]:
    lines = ["## Local content gaps", ""]
    label = "inferred from nav/headings" if plan.inferred_services else "as requested"
    lines.append(f"**Services checked** ({label}):")
    for status in plan.services:
        mark = "found" if status.found else "MISSING"
        suffix = f" ({status.matched_url})" if status.matched_url else ""
        lines.append(f"- [{mark}] {status.query}{suffix}")
    lines.append("")
    if plan.areas:
        lines.append("**Areas checked:**")
        for status in plan.areas:
            mark = "found" if status.found else "MISSING"
            lines.append(f"- [{mark}] {status.query}")
        lines.append("")
    lines.append(
        f"- **NAP:** {len(plan.nap.distinct_phone_numbers)} distinct phone number(s) across "
        f"{plan.nap.pages_checked} page(s); consistent: {plan.nap.phone_consistent}."
    )
    covered = plan.click_to_call.pages_checked - len(plan.click_to_call.pages_missing)
    lines.append(
        f"- **Click-to-call:** {covered}/{plan.click_to_call.pages_checked} page(s) have a "
        "tel: link."
    )
    lines.append(
        f"- **Review/AggregateRating schema:** {plan.schema.has_review_schema_anywhere}. "
        f"**FAQPage schema:** {plan.schema.has_faq_schema_anywhere}."
    )
    lines.append(
        f"- **Google Business Profile link:** {plan.has_gbp_link}. "
        f"**Contact page map:** {plan.has_contact_page_map}."
    )
    lines.append("")
    lines.append("### Content to create (prioritized)")
    lines.append("")
    if not plan.plan:
        lines.append("Nothing found - great coverage.")
    for item in plan.plan:
        lines.append(f"- **[{item.priority.upper()}] {item.title}** - {item.why}")
    lines.append("")
    return lines


def _site_crawl_lines(crawl: SiteCrawlReport) -> list[str]:
    lines = [
        "## Site crawl",
        "",
        f"Visited {crawl.pages_crawled} page(s) (cap {crawl.max_pages}); "
        f"{len(crawl.sitemap_urls)} URL(s) in the sitemap; "
        f"**{crawl.issue_count()} site-level issue(s)** found.",
        "",
        "| URL | Status | Depth | Title | Words |",
        "|---|---|---|---|---|",
    ]
    for page in sorted(crawl.pages, key=lambda p: p.url):
        status = "OK" if page.ok else f"HTTP {page.status_code}"
        title = page.title or "(no title)"
        lines.append(f"| {page.url} | {status} | {page.depth} | {title} | {page.word_count} |")
    lines.append("")

    def _list(label: str, items: Sequence[object]) -> None:
        if items:
            lines.append(f"- **{label}:** {len(items)}")

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

    if report.site_crawl is not None:
        lines.extend(_site_crawl_lines(report.site_crawl))

    if report.competitors is not None:
        lines.extend(_compare_lines(report.competitors))

    if report.content_plan is not None:
        lines.extend(_content_plan_lines(report.content_plan))

    return "\n".join(lines).rstrip() + "\n"
