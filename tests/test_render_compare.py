"""Every renderer must show the competitor-compare section when present, and omit it otherwise."""

from __future__ import annotations

import datetime as dt

from local_seo_audit.business import Business
from local_seo_audit.compare import (
    ComparisonRow,
    CompetitorComparison,
    CompetitorEntry,
    GapItem,
    KeyMetrics,
)
from local_seo_audit.models import Report
from local_seo_audit.render.html import render_html
from local_seo_audit.render.json_renderer import render_json, report_to_dict
from local_seo_audit.render.markdown import render_markdown
from local_seo_audit.render.text import render_text


def _comparison() -> CompetitorComparison:
    competitor = CompetitorEntry(
        url="https://competitor.example/",
        report=None,
        metrics=KeyMetrics(page_weight_bytes=12000, schema_types=("Plumber", "AggregateRating")),
    )
    return CompetitorComparison(
        your_url="https://example.com/",
        competitors=(competitor,),
        matrix=(
            ComparisonRow(
                check_id="click_to_call",
                title="Click-to-call (tel:) link",
                weight=8,
                your_status="fail",
                competitor_statuses=("pass",),
            ),
        ),
        gaps=(
            GapItem(
                check_id="click_to_call",
                title="Click-to-call (tel:) link",
                weight=8,
                ahead_competitors=("https://competitor.example/",),
            ),
        ),
    )


def _report_with_compare() -> Report:
    return Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(name="Joe's Plumbing"),
        results=[],
        generated_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        competitors=_comparison(),
    )


def test_text_renders_compare_section() -> None:
    output = render_text(_report_with_compare(), color=False)
    assert "Competitor compare" in output
    assert "competitor.example" in output
    assert "Gaps" in output


def test_markdown_renders_compare_section() -> None:
    output = render_markdown(_report_with_compare())
    assert "## Competitor compare" in output
    assert "| Check | You | https://competitor.example/ |" in output
    assert "**Click-to-call (tel:) link**" in output


def test_html_renders_compare_section() -> None:
    output = render_html(_report_with_compare())
    assert "Competitor compare" in output
    assert "competitor.example" in output
    assert "Plumber, AggregateRating" in output or "AggregateRating" in output


def test_json_renders_compare_section() -> None:
    data = report_to_dict(_report_with_compare())
    assert data["competitors"]["competitors"][0]["url"] == "https://competitor.example/"
    assert data["competitors"]["gaps"][0]["check_id"] == "click_to_call"
    output = render_json(_report_with_compare())
    assert '"competitors"' in output


def test_renderers_omit_compare_section_when_absent(sample_report: Report) -> None:
    assert "Competitor compare" not in render_text(sample_report, color=False)
    assert "Competitor compare" not in render_markdown(sample_report)
    assert "Competitor compare" not in render_html(sample_report)
    assert report_to_dict(sample_report)["competitors"] is None
