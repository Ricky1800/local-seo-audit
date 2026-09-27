"""Standalone, printable HTML report — inline CSS, no external requests.

This is the format meant to be handed directly to a non-technical business
owner: it opens in any browser, prints cleanly, and needs nothing else.
"""

from __future__ import annotations

from html import escape

from local_seo_audit.compare import CompetitorComparison
from local_seo_audit.crawler import SiteCrawlReport
from local_seo_audit.models import Report, Status
from local_seo_audit.vitals import LabData, Metric, Rating, StrategyResult, VitalsResult

_RATING_COLOR: dict[Rating, str] = {
    "good": "#1a7f37",
    "needs-improvement": "#9a6700",
    "poor": "#cf222e",
}

_STATUS_COLOR = {
    Status.PASS: "#1a7f37",
    Status.WARN: "#9a6700",
    Status.FAIL: "#cf222e",
    Status.SKIP: "#6e7781",
}
_STATUS_LABEL = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}
_GRADE_COLOR = {"A": "#1a7f37", "B": "#2da44e", "C": "#9a6700", "D": "#bc4c00", "F": "#cf222e"}

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0;
  background: #f6f8fa;
  color: #1f2328;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.5;
}
main { max-width: 860px; margin: 0 auto; padding: 32px 20px 64px; }
header { background: #fff; border: 1px solid #d0d7de; border-radius: 12px; padding: 24px; }
h1 { margin: 0 0 4px; font-size: 1.6rem; }
p { margin: 4px 0; }
.url a { color: #0969da; word-break: break-all; }
.business { font-size: 1.05rem; }
.generated { color: #57606a; font-size: 0.9rem; }
.score-card { display: flex; align-items: center; gap: 16px; margin: 16px 0; }
.score { font-size: 2.6rem; font-weight: 700; }
.score span { font-size: 1.2rem; font-weight: 400; color: #57606a; }
.grade {
  color: #fff; font-weight: 700; font-size: 1.4rem;
  width: 56px; height: 56px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.counts { color: #57606a; }
.checks { margin-top: 24px; display: flex; flex-direction: column; gap: 12px; }
.check {
  background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
  padding: 16px 20px;
}
.check h3 {
  margin: 0 0 8px; font-size: 1.05rem;
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
}
.badge {
  color: #fff; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.03em;
  padding: 2px 8px; border-radius: 999px;
}
.meta { color: #57606a; font-weight: 400; font-size: 0.85rem; }
.evidence { color: #32383f; }
.fix { background: #f6f8fa; border-left: 3px solid #0969da; padding: 8px 12px; border-radius: 4px; }
footer { margin-top: 32px; color: #57606a; font-size: 0.85rem; text-align: center; }
footer a { color: #0969da; }
.report-section { margin-top: 28px; }
.report-section h2 { font-size: 1.25rem; margin: 0 0 4px; }
.section-sub { color: #57606a; font-size: 0.85rem; margin: 0 0 12px; }
.vitals-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px;
}
.vitals-card {
  background: #fff; border: 1px solid #d0d7de; border-radius: 10px; padding: 14px 16px;
}
.vitals-card h4 { margin: 0 0 8px; }
.vitals-note { color: #57606a; font-size: 0.85rem; margin: 6px 0 4px; }
.vitals-error { color: #cf222e; }
.metric-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0; }
.metric-chip {
  border: 1px solid #d0d7de; border-radius: 999px; padding: 2px 10px; font-size: 0.8rem;
  font-weight: 600;
}
.metric-missing { color: #57606a; }
.crawl-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.85rem; }
.crawl-table th, .crawl-table td {
  border: 1px solid #d0d7de; padding: 6px 8px; text-align: left; word-break: break-word;
}
.crawl-table th { background: #f6f8fa; }
@media print {
  body { background: #fff; }
  header, .check, .vitals-card { border: 1px solid #ccc; break-inside: avoid; }
}
"""


def _check_section(
    status: Status, title: str, weight: int, severity: str, evidence: str, fix: str
) -> str:
    color = _STATUS_COLOR[status]
    label = _STATUS_LABEL[status]
    fix_html = ""
    if status in (Status.WARN, Status.FAIL) and fix:
        fix_html = f'<p class="fix"><strong>Fix:</strong> {escape(fix)}</p>'
    return (
        f'<section class="check status-{status.value}">'
        f'<h3><span class="badge" style="background:{color}">{label}</span> '
        f'{escape(title)}<span class="meta">weight {weight} · {escape(severity)}</span></h3>'
        f'<p class="evidence">{escape(evidence)}</p>'
        f"{fix_html}"
        f"</section>"
    )


def _metric_chip(metric: Metric | None) -> str:
    if metric is None:
        return '<span class="metric-chip metric-missing">n/a</span>'
    color = _RATING_COLOR[metric.rating]
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
            opp_html = f'<p class="vitals-note">Top opportunities:</p><ul>{items}</ul>'
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
        '<section class="report-section vitals">'
        "<h2>Core Web Vitals</h2>"
        '<p class="section-sub">Source: Google PageSpeed Insights.</p>'
        f'<div class="vitals-grid">{cards}</div>'
        "</section>"
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
    return (
        '<section class="report-section site-crawl">'
        "<h2>Site crawl</h2>"
        f'<p class="section-sub">Visited {crawl.pages_crawled} page(s) '
        f"(cap {crawl.max_pages}); {len(crawl.sitemap_urls)} URL(s) in the sitemap; "
        f"{crawl.issue_count()} site-level issue(s) found.</p>"
        f"<ul>{issues}</ul>"
        '<table class="crawl-table"><thead><tr><th>URL</th><th>Status</th><th>Depth</th>'
        f"<th>Title</th><th>Words</th></tr></thead><tbody>{page_rows}</tbody></table>"
        "</section>"
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
    gaps_html = f"<ul>{gap_items}</ul>" if gap_items else "<p>None found.</p>"

    metrics_items = "".join(
        f"<li>{escape(entry.url)}: "
        f"{escape(str(entry.metrics.page_weight_bytes) + ' bytes') if entry.metrics else 'n/a'}, "
        f"schema: {escape(', '.join(entry.metrics.schema_types) if entry.metrics else 'n/a')}"
        f"{' &mdash; ' + escape(entry.error) if entry.error else ''}</li>"
        for entry in comparison.competitors
    )

    return (
        '<section class="report-section compare">'
        "<h2>Competitor compare</h2>"
        f'<table class="crawl-table"><thead><tr>{header_cells}</tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Key metrics</h3><ul>{metrics_items}</ul>"
        "<h3>Gaps (they have it, you don't)</h3>"
        f"{gaps_html}"
        "</section>"
    )


def render_html(report: Report) -> str:
    counts = report.counts()
    rows = "".join(
        _check_section(r.status, r.title, r.weight, r.severity.value, r.evidence, r.fix)
        for r in report.sorted_results
    )

    business_line = ""
    if report.business.name:
        business_name = escape(report.business.name)
        business_line = f'<p class="business">Business: <strong>{business_name}</strong></p>'

    grade_color = _GRADE_COLOR.get(report.grade, "#57606a")
    safe_url = escape(report.url)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local SEO Audit Report</title>
<style>{_CSS}</style>
</head>
<body>
<main>
  <header>
    <h1>Local SEO Audit</h1>
    <p class="url"><a href="{safe_url}">{safe_url}</a></p>
    {business_line}
    <p class="generated">Generated {report.generated_at:%Y-%m-%d %H:%M}</p>
    <div class="score-card">
      <div class="score" style="color:{grade_color}">{report.score}<span>/100</span></div>
      <div class="grade" style="background:{grade_color}">{escape(report.grade)}</div>
    </div>
    <p class="counts">
      Pass: {counts[Status.PASS]} &nbsp; Warn: {counts[Status.WARN]} &nbsp;
      Fail: {counts[Status.FAIL]} &nbsp; Skipped: {counts[Status.SKIP]}
    </p>
  </header>
  <section class="checks">
    {rows}
  </section>
  {_vitals_section(report.vitals)}
  {_site_crawl_section(report.site_crawl)}
  {_compare_section(report.competitors)}
  <footer>
    <p>Generated by
      <a href="https://github.com/Ricky1800/local-seo-audit">local-seo-audit</a>
      v{escape(report.tool_version)} &mdash; free and open source.</p>
  </footer>
</main>
</body>
</html>
"""
