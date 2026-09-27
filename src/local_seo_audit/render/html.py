"""Standalone, printable HTML report - inline CSS, no external requests.

This is the format meant to be handed directly to a non-technical business
owner: a clean, modern one-page report with a score gauge, an executive
summary up top, severity-colored findings, and print styles - opens in any
browser, prints cleanly on a single reasonable page count, and needs nothing
else (no external fonts, scripts, or stylesheets).
"""

from __future__ import annotations

import math
from html import escape

from local_seo_audit.compare import CompetitorComparison
from local_seo_audit.content_gaps import ContentGapPlan, PageMatchStatus
from local_seo_audit.crawler import SiteCrawlReport
from local_seo_audit.models import CheckResult, Report, Severity, Status
from local_seo_audit.vitals import LabData, Metric, StrategyResult, VitalsResult

_STATUS_LABEL = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}
_GRADE_LABEL = {
    "A": "Excellent",
    "B": "Good",
    "C": "Needs work",
    "D": "Struggling",
    "F": "Critical",
}
_PRIORITY_LABEL = {"high": "High priority", "medium": "Medium priority", "low": "Low priority"}

_CSS = """
:root {
  color-scheme: light;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --bg: #f1f3f7;
  --surface: #ffffff;
  --surface-muted: #f6f8fb;
  --border: #e1e4eb;
  --text: #171a21;
  --text-muted: #5b6472;
  --primary: #2452eb;
  --primary-dark: #1a3bc4;
  --pass: #157a3d;
  --pass-bg: #eafaf0;
  --warn: #9a6a05;
  --warn-bg: #fdf6e6;
  --fail: #c0233c;
  --fail-bg: #fdedf0;
  --skip: #6b7280;
  --skip-bg: #f1f2f4;
  --grade-a: #157a3d;
  --grade-b: #3f8f35;
  --grade-c: #b7791f;
  --grade-d: #c1560c;
  --grade-f: #c0233c;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --shadow-1: 0 1px 2px rgba(16, 24, 40, 0.06);
  --shadow-2: 0 6px 16px rgba(16, 24, 40, 0.08);
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
  --sp-6: 24px; --sp-8: 32px; --sp-10: 40px; --sp-12: 48px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161b; --surface: #1c1f26; --surface-muted: #23262e; --border: #2e323c;
    --text: #eef0f4; --text-muted: #9aa2b1;
    --pass-bg: #10301f; --warn-bg: #332506; --fail-bg: #3a1220; --skip-bg: #262932;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 16px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.page { max-width: 900px; margin: 0 auto; padding: var(--sp-8) var(--sp-4) var(--sp-12); }
a { color: var(--primary); }
h1, h2, h3, h4 { line-height: 1.25; font-weight: 700; }
h1 { margin: 0; font-size: clamp(1.5rem, 1.2rem + 1.2vw, 2rem); }
h2 { margin: 0 0 var(--sp-1); font-size: 1.3rem; }
h3 { margin: var(--sp-4) 0 var(--sp-2); font-size: 1.05rem; }
p { margin: var(--sp-1) 0; }

.hero {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: var(--sp-6); box-shadow: var(--shadow-2);
}
.hero-top {
  display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;
  gap: var(--sp-2); color: var(--text-muted); font-size: 0.85rem; margin-bottom: var(--sp-2);
}
.brand { font-weight: 700; letter-spacing: 0.02em; text-transform: uppercase; font-size: 0.75rem; }
.target-url { color: var(--text-muted); word-break: break-all; margin-bottom: var(--sp-1); }
.target-url a { color: var(--primary); }
.business-name { font-size: 1.05rem; font-weight: 600; }

.score-row {
  display: flex; align-items: center; gap: var(--sp-6); flex-wrap: wrap; margin-top: var(--sp-6);
}
.gauge { width: 128px; height: 128px; flex: none; }
.gauge-track { fill: none; stroke: var(--border); stroke-width: 12; }
.gauge-value { fill: none; stroke-width: 12; stroke-linecap: round; }
.gauge-score {
  font-size: 32px; font-weight: 800; text-anchor: middle; font-family: var(--font-sans);
}
.gauge-outof {
  font-size: 12px; fill: var(--text-muted); text-anchor: middle; font-family: var(--font-sans);
}

.score-meta { flex: 1; min-width: 220px; }
.grade-chip {
  display: inline-flex; align-items: center; gap: var(--sp-2); font-weight: 700;
  padding: var(--sp-1) var(--sp-3); border-radius: 999px; font-size: 0.9rem;
}
.counts-row { display: flex; gap: var(--sp-4); flex-wrap: wrap; margin-top: var(--sp-3); }
.count-pill {
  display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--text-muted);
}
.count-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }

.exec-summary {
  margin-top: var(--sp-6); padding-top: var(--sp-6); border-top: 1px solid var(--border);
}
.exec-summary p { color: var(--text); }
.top-issues { margin: var(--sp-2) 0 0; padding: 0; list-style: none; }
.top-issues li {
  display: flex; gap: var(--sp-2); align-items: flex-start; padding: var(--sp-2) 0;
  border-bottom: 1px dashed var(--border);
}
.top-issues li:last-child { border-bottom: none; }
.sev-dot {
  width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex: none;
}

.report-section { margin-top: var(--sp-8); }
.section-sub { color: var(--text-muted); font-size: 0.88rem; margin: 0 0 var(--sp-3); }
.section-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: var(--sp-6); box-shadow: var(--shadow-1);
}

.checks { margin-top: var(--sp-6); display: flex; flex-direction: column; gap: var(--sp-3); }
.check {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 4px solid var(--border); border-radius: var(--radius-md);
  padding: var(--sp-4) 20px; box-shadow: var(--shadow-1);
}
.check.status-pass { border-left-color: var(--pass); }
.check.status-warn { border-left-color: var(--warn); }
.check.status-fail { border-left-color: var(--fail); }
.check.status-skip { border-left-color: var(--skip); }
.check h3 {
  margin: 0 0 var(--sp-2); font-size: 1rem;
  display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2);
}
.badge {
  color: #fff; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em;
  padding: 3px 9px; border-radius: 999px; text-transform: uppercase;
}
.meta { color: var(--text-muted); font-weight: 400; font-size: 0.82rem; }
.evidence { color: var(--text); font-size: 0.95rem; }
.fix {
  background: var(--surface-muted); border-left: 3px solid var(--primary);
  padding: var(--sp-2) var(--sp-3); border-radius: var(--radius-sm);
  margin-top: var(--sp-2); font-size: 0.92rem;
}

.vitals-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--sp-3);
}
.vitals-card {
  background: var(--surface-muted); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: var(--sp-4);
}
.vitals-card h4 { margin: 0 0 var(--sp-2); }
.vitals-note { color: var(--text-muted); font-size: 0.85rem; margin: var(--sp-2) 0 var(--sp-1); }
.vitals-error { color: var(--fail); }
.metric-row { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin: var(--sp-1) 0; }
.metric-chip {
  border: 1.5px solid var(--border); border-radius: 999px; padding: 2px 10px; font-size: 0.8rem;
  font-weight: 700; background: var(--surface);
}
.metric-missing { color: var(--text-muted); font-weight: 400; }

table.data-table {
  width: 100%; border-collapse: collapse; margin-top: var(--sp-3); font-size: 0.85rem;
  background: var(--surface);
}
table.data-table th, table.data-table td {
  border: 1px solid var(--border); padding: 6px 10px; text-align: left; word-break: break-word;
}
table.data-table th { background: var(--surface-muted); }

.issue-list, .plan-list, .match-list, .gap-list, .metrics-list {
  margin: var(--sp-2) 0 0; padding-left: 1.1rem;
}
.issue-list li, .metrics-list li { margin: 4px 0; }
.plan-list {
  list-style: none; padding-left: 0; display: flex; flex-direction: column; gap: var(--sp-3);
}
.plan-item {
  background: var(--surface-muted); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: var(--sp-3) var(--sp-4);
}
.plan-item .why { color: var(--text-muted); font-size: 0.88rem; margin-top: 4px; }
.match-list { list-style: none; padding-left: 0; display: flex; flex-direction: column; gap: 4px; }
.match-list li { display: flex; align-items: center; gap: var(--sp-2); }

footer {
  margin-top: var(--sp-10); color: var(--text-muted); font-size: 0.85rem; text-align: center;
}
footer a { color: var(--primary); }

@media print {
  body { background: #fff; }
  .page { max-width: none; padding: 0.4in; }
  .hero, .section-card, .check, .vitals-card, .plan-item { box-shadow: none; }
  .hero, .check, .vitals-card, .plan-item { border: 1px solid #ccc; }
  .report-section, .check { break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
@media (max-width: 560px) {
  .score-row { gap: var(--sp-4); }
  .gauge { width: 104px; height: 104px; }
}
"""


def _grade_color_var(grade: str) -> str:
    return {
        "A": "var(--grade-a)",
        "B": "var(--grade-b)",
        "C": "var(--grade-c)",
        "D": "var(--grade-d)",
        "F": "var(--grade-f)",
    }.get(grade, "var(--text-muted)")


def _status_color_var(status: Status) -> str:
    return {
        Status.PASS: "var(--pass)",
        Status.WARN: "var(--warn)",
        Status.FAIL: "var(--fail)",
        Status.SKIP: "var(--skip)",
    }[status]


def _severity_color_var(severity: Severity) -> str:
    return {
        Severity.CRITICAL: "var(--fail)",
        Severity.HIGH: "var(--fail)",
        Severity.MEDIUM: "var(--warn)",
        Severity.LOW: "var(--skip)",
        Severity.INFO: "var(--skip)",
    }[severity]


def _score_gauge_svg(score: float, grade: str) -> str:
    """A circular progress ring - the score at a glance, no external assets."""
    radius = 54
    circumference = 2 * math.pi * radius
    fraction = min(max(score, 0.0), 100.0) / 100.0
    offset = circumference * (1 - fraction)
    color = _grade_color_var(grade)
    score_text = f"{score:g}"
    return (
        f'<svg viewBox="0 0 140 140" class="gauge" role="img" '
        f'aria-label="Score {escape(score_text)} out of 100, grade {escape(grade)}">'
        f'<circle cx="70" cy="70" r="{radius}" class="gauge-track"></circle>'
        f'<circle cx="70" cy="70" r="{radius}" class="gauge-value" style="stroke:{color}" '
        f'stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}" '
        f'transform="rotate(-90 70 70)"></circle>'
        f'<text x="70" y="66" class="gauge-score" style="fill:{color}">{escape(score_text)}</text>'
        f'<text x="70" y="88" class="gauge-outof">/ 100</text>'
        f"</svg>"
    )


def _executive_summary(report: Report) -> str:
    counts = report.counts()
    scored = counts[Status.PASS] + counts[Status.WARN] + counts[Status.FAIL]
    top_issues = [
        r
        for r in report.sorted_results
        if r.status in (Status.FAIL, Status.WARN)
        and r.severity in (Severity.CRITICAL, Severity.HIGH)
    ][:5]

    if report.score >= 90:
        headline = "This site is in strong shape for local SEO and conversion basics."
    elif report.score >= 70:
        headline = "This site has a solid foundation, with a handful of fixable gaps."
    elif report.score >= 50:
        headline = "This site is losing customers to fixable local-SEO and conversion problems."
    else:
        headline = "This site has serious local-SEO and conversion gaps costing it customers now."

    summary = (
        f"<p>{escape(headline)} Out of {scored} scored check(s), "
        f"<strong>{counts[Status.PASS]} pass</strong>, "
        f"<strong>{counts[Status.WARN]} need attention</strong>, and "
        f"<strong>{counts[Status.FAIL]} fail outright</strong>.</p>"
    )

    if top_issues:
        items = "".join(_top_issue_row(r) for r in top_issues)
        summary += f'<p><strong>Fix these first:</strong></p><ul class="top-issues">{items}</ul>'
    else:
        summary += "<p>No critical or high-severity issues were found. Nice work.</p>"

    return f'<div class="exec-summary"><h2>Executive summary</h2>{summary}</div>'


def _top_issue_row(result: CheckResult) -> str:
    dot_color = _severity_color_var(result.severity)
    title_html = f"<strong>{escape(result.title)}</strong> &mdash; {escape(result.evidence)}"
    return (
        f'<li><span class="sev-dot" style="background:{dot_color}"></span>'
        f"<span>{title_html}</span></li>"
    )


def _check_section(result: CheckResult) -> str:
    color = _status_color_var(result.status)
    label = _STATUS_LABEL[result.status]
    fix_html = ""
    if result.status in (Status.WARN, Status.FAIL) and result.fix:
        fix_html = f'<p class="fix"><strong>Fix:</strong> {escape(result.fix)}</p>'
    return (
        f'<section class="check status-{result.status.value}">'
        f'<h3><span class="badge" style="background:{color}">{label}</span> '
        f"{escape(result.title)}"
        f'<span class="meta">weight {result.weight} &middot; {escape(result.severity.value)}</span>'
        f"</h3>"
        f'<p class="evidence">{escape(result.evidence)}</p>'
        f"{fix_html}"
        f"</section>"
    )


def _metric_chip(metric: Metric | None) -> str:
    if metric is None:
        return '<span class="metric-chip metric-missing">n/a</span>'
    color = {
        "good": "var(--pass)",
        "needs-improvement": "var(--warn)",
        "poor": "var(--fail)",
    }[metric.rating]
    value = f"{metric.value:.2f}" if metric.unit == "" else f"{metric.value:.0f}{metric.unit}"
    return (
        f'<span class="metric-chip" style="border-color:{color};color:{color}">'
        f"{escape(metric.name)} {escape(value)} &middot; {escape(metric.rating)}</span>"
    )


def _strategy_card(result: StrategyResult) -> str:
    if result.error:
        return (
            f'<div class="vitals-card"><h4>{escape(result.strategy.capitalize())}</h4>'
            f'<p class="vitals-error">{escape(result.error)}</p></div>'
        )
    field = result.field_data
    field_html = '<p class="vitals-note">Not enough real-user Chrome traffic data.</p>'
    if field is not None and field.has_any():
        field_html = (
            '<div class="metric-row">'
            + _metric_chip(field.lcp)
            + _metric_chip(field.inp)
            + _metric_chip(field.cls)
            + "</div>"
        )
    lab: LabData | None = result.lab_data
    lab_html = ""
    if lab is not None:
        score = f"{lab.performance_score:.0f}/100" if lab.performance_score is not None else "n/a"
        opp_html = ""
        if lab.opportunities:
            items = "".join(f"<li>{escape(o)}</li>" for o in lab.opportunities)
            opp_html = (
                f'<p class="vitals-note">Top opportunities:</p><ul class="issue-list">{items}</ul>'
            )
        lab_note = f"Lab (Lighthouse) performance: <strong>{escape(score)}</strong>"
        lab_html = (
            f'<p class="vitals-note">{lab_note}</p>'
            '<div class="metric-row">'
            + _metric_chip(lab.lcp)
            + _metric_chip(lab.tbt)
            + _metric_chip(lab.cls)
            + "</div>"
            + opp_html
        )
    return (
        f'<div class="vitals-card"><h4>{escape(result.strategy.capitalize())}</h4>'
        f'<p class="vitals-note">Field data (real users):</p>{field_html}{lab_html}</div>'
    )


def _vitals_section(vitals: VitalsResult | None) -> str:
    if vitals is None:
        return ""
    cards = "".join(_strategy_card(r) for r in vitals.by_strategy())
    return (
        '<section class="report-section vitals"><div class="section-card">'
        "<h2>Core Web Vitals</h2>"
        '<p class="section-sub">Source: Google PageSpeed Insights.</p>'
        f'<div class="vitals-grid">{cards}</div>'
        "</div></section>"
    )


def _issue_row(label: str, count: int) -> str:
    if not count:
        return ""
    return f"<li><strong>{count}</strong> {escape(label)}</li>"


def _site_crawl_section(crawl: SiteCrawlReport | None) -> str:
    if crawl is None:
        return ""
    page_rows = "".join(
        f"<tr><td>{escape(p.url)}</td><td>{'OK' if p.ok else p.status_code}</td>"
        f"<td>{p.depth}</td><td>{escape(p.title or '(no title)')}</td>"
        f"<td>{p.word_count}</td></tr>"
        for p in sorted(crawl.pages, key=lambda page: page.url)
    )
    issues = "".join(
        [
            _issue_row("duplicate title(s)", len(crawl.duplicate_titles)),
            _issue_row("duplicate meta description(s)", len(crawl.duplicate_descriptions)),
            _issue_row("page(s) missing an H1", len(crawl.missing_h1)),
            _issue_row("page(s) with duplicate H1s", len(crawl.duplicate_h1_pages)),
            _issue_row("page(s) with heading-order problems", len(crawl.heading_order_issues)),
            _issue_row("thin-content page(s)", len(crawl.thin_content)),
            _issue_row("canonical issue(s)", len(crawl.canonical_issues)),
            _issue_row("redirect chain(s)", len(crawl.redirect_chains)),
            _issue_row("error page(s) (4xx/5xx)", len(crawl.error_pages)),
            _issue_row("orphan page(s) (in sitemap, not linked)", len(crawl.orphan_pages)),
            _issue_row("page(s) deeper than 3 clicks", len(crawl.deep_pages)),
            _issue_row("crawled page(s) missing from the sitemap", len(crawl.missing_from_sitemap)),
        ]
    )
    no_issues = "<p>No site-level issues found.</p>"
    issues_html = f'<ul class="issue-list">{issues}</ul>' if issues else no_issues
    return (
        '<section class="report-section site-crawl"><div class="section-card">'
        "<h2>Site crawl</h2>"
        f'<p class="section-sub">Visited {crawl.pages_crawled} page(s) '
        f"(cap {crawl.max_pages}); {len(crawl.sitemap_urls)} URL(s) in the sitemap; "
        f"{crawl.issue_count()} site-level issue(s) found.</p>"
        f"{issues_html}"
        '<table class="data-table"><thead><tr><th>URL</th><th>Status</th><th>Depth</th>'
        f"<th>Title</th><th>Words</th></tr></thead><tbody>{page_rows}</tbody></table>"
        "</div></section>"
    )


def _compare_section(comparison: CompetitorComparison | None) -> str:
    if comparison is None:
        return ""
    header_cells = "<th>Check</th><th>You</th>" + "".join(
        f"<th>{escape(entry.url)}</th>" for entry in comparison.competitors
    )
    rows = ""
    for row in comparison.matrix:
        cells = f"<td>{escape(row.title)}</td><td>{escape(row.your_status or '-')}</td>"
        cells += "".join(f"<td>{escape(status or '-')}</td>" for status in row.competitor_statuses)
        rows += f"<tr>{cells}</tr>"

    gap_items = "".join(
        f"<li><strong>{escape(gap.title)}</strong> (weight {gap.weight}) &mdash; ahead: "
        f"{escape(', '.join(gap.ahead_competitors))}</li>"
        for gap in comparison.gaps
    )
    gaps_html = f'<ul class="gap-list">{gap_items}</ul>' if gap_items else "<p>None found.</p>"

    metrics_items = "".join(
        f"<li>{escape(entry.url)}: "
        f"{escape(str(entry.metrics.page_weight_bytes) + ' bytes') if entry.metrics else 'n/a'}, "
        f"schema: {escape(', '.join(entry.metrics.schema_types) if entry.metrics else 'n/a')}"
        f"{' &mdash; ' + escape(entry.error) if entry.error else ''}</li>"
        for entry in comparison.competitors
    )

    return (
        '<section class="report-section compare"><div class="section-card">'
        "<h2>Competitor compare</h2>"
        '<p class="section-sub">Same checks, side by side.</p>'
        f'<table class="data-table"><thead><tr>{header_cells}</tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        f'<h3>Key metrics</h3><ul class="metrics-list">{metrics_items}</ul>'
        "<h3>Gaps (they have it, you don't)</h3>"
        f"{gaps_html}"
        "</div></section>"
    )


def _match_list(statuses: tuple[PageMatchStatus, ...]) -> str:
    items = []
    for status in statuses:
        badge = (
            '<span class="badge" style="background:var(--pass)">FOUND</span>'
            if status.found
            else '<span class="badge" style="background:var(--fail)">MISSING</span>'
        )
        suffix = f" &mdash; {escape(status.matched_url)}" if status.matched_url else ""
        items.append(f"<li>{badge} {escape(status.query)}{suffix}</li>")
    return f'<ul class="match-list">{"".join(items)}</ul>' if items else "<p>None specified.</p>"


def _content_plan_section(plan: ContentGapPlan | None) -> str:
    if plan is None:
        return ""
    priority_color = {"high": "var(--fail)", "medium": "var(--warn)", "low": "var(--skip)"}
    label = "inferred from nav/headings" if plan.inferred_services else "as requested"
    plan_items = "".join(
        '<li class="plan-item">'
        f'<span class="badge" style="background:{priority_color[item.priority]}">'
        f"{escape(_PRIORITY_LABEL[item.priority])}</span> "
        f"<strong>{escape(item.title)}</strong>"
        f'<div class="why">{escape(item.why)}</div></li>'
        for item in plan.plan
    )
    plan_html = (
        f'<ul class="plan-list">{plan_items}</ul>'
        if plan_items
        else "<p>Nothing found - great coverage.</p>"
    )

    areas_html = f"<h3>Areas checked</h3>{_match_list(plan.areas)}" if plan.areas else ""

    return (
        '<section class="report-section content-gaps"><div class="section-card">'
        "<h2>Local content gaps</h2>"
        f"<h3>Services checked ({escape(label)})</h3>"
        f"{_match_list(plan.services)}"
        f"{areas_html}"
        "<h3>NAP, schema &amp; coverage</h3>"
        '<ul class="issue-list">'
        f"<li>{len(plan.nap.distinct_phone_numbers)} distinct phone number(s) across "
        f"{plan.nap.pages_checked} page(s); consistent: {plan.nap.phone_consistent}.</li>"
        "<li>Click-to-call present on "
        f"{plan.click_to_call.pages_checked - len(plan.click_to_call.pages_missing)}/"
        f"{plan.click_to_call.pages_checked} page(s).</li>"
        f"<li>Review/AggregateRating schema: {plan.schema.has_review_schema_anywhere}. "
        f"FAQPage schema: {plan.schema.has_faq_schema_anywhere}.</li>"
        f"<li>Google Business Profile link: {plan.has_gbp_link}. "
        f"Contact page map: {plan.has_contact_page_map}.</li>"
        "</ul>"
        "<h3>Content to create (prioritized)</h3>"
        f"{plan_html}"
        "</div></section>"
    )


def render_html(report: Report) -> str:
    counts = report.counts()
    rows = "".join(_check_section(r) for r in report.sorted_results)

    business_line = ""
    if report.business.name:
        business_line = f'<p class="business-name">{escape(report.business.name)}</p>'

    grade_color = _grade_color_var(report.grade)
    grade_desc = _GRADE_LABEL.get(report.grade, "")
    safe_url = escape(report.url)

    count_pills = "".join(
        f'<span class="count-pill"><span class="count-dot" style="background:{color}"></span>'
        f"{count} {label}</span>"
        for label, count, color in (
            ("passed", counts[Status.PASS], "var(--pass)"),
            ("need attention", counts[Status.WARN], "var(--warn)"),
            ("failed", counts[Status.FAIL], "var(--fail)"),
            ("skipped", counts[Status.SKIP], "var(--skip)"),
        )
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local SEO Audit Report</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="hero">
    <div class="hero-top">
      <span class="brand">Local SEO Audit</span>
      <span class="generated">Generated {report.generated_at:%Y-%m-%d %H:%M}</span>
    </div>
    <h1>{escape(report.business.name or report.url)}</h1>
    {business_line}
    <p class="target-url"><a href="{safe_url}">{safe_url}</a></p>
    <div class="score-row">
      {_score_gauge_svg(report.score, report.grade)}
      <div class="score-meta">
        <span class="grade-chip" style="color:{grade_color};background:{grade_color}22">
          Grade {escape(report.grade)} &middot; {escape(grade_desc)}
        </span>
        <div class="counts-row">{count_pills}</div>
      </div>
    </div>
    {_executive_summary(report)}
  </header>

  <section class="checks">
    {rows}
  </section>
  {_vitals_section(report.vitals)}
  {_site_crawl_section(report.site_crawl)}
  {_compare_section(report.competitors)}
  {_content_plan_section(report.content_plan)}
  <footer>
    <p>Generated by
      <a href="https://github.com/Ricky1800/local-seo-audit">local-seo-audit</a>
      v{escape(report.tool_version)} &mdash; free and open source.</p>
  </footer>
</div>
</body>
</html>
"""
