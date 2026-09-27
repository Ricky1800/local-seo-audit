"""Every renderer must show the Core Web Vitals section when present, and omit it otherwise."""

from __future__ import annotations

import datetime as dt

from local_seo_audit.business import Business
from local_seo_audit.models import Report
from local_seo_audit.render.html import render_html
from local_seo_audit.render.json_renderer import render_json, report_to_dict
from local_seo_audit.render.markdown import render_markdown
from local_seo_audit.render.text import render_text
from local_seo_audit.vitals import FieldData, LabData, Metric, StrategyResult, VitalsResult


def _vitals_result() -> VitalsResult:
    mobile = StrategyResult(
        strategy="mobile",
        field_data=FieldData(
            lcp=Metric("LCP", 2100.0, "ms", "good"),
            inp=Metric("INP", 150.0, "ms", "good"),
            cls=Metric("CLS", 0.05, "", "good"),
            overall_category="FAST",
        ),
        lab_data=LabData(
            performance_score=94.0,
            lcp=Metric("LCP", 1900.0, "ms", "good"),
            tbt=Metric("TBT", 80.0, "ms", "good"),
            cls=Metric("CLS", 0.03, "", "good"),
            opportunities=["Eliminate render-blocking resources"],
        ),
    )
    desktop = StrategyResult(strategy="desktop", error="Timed out contacting PageSpeed Insights.")
    return VitalsResult(mobile=mobile, desktop=desktop)


def _report_with_vitals() -> Report:
    return Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(name="Joe's Plumbing"),
        results=[],
        generated_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        vitals=_vitals_result(),
    )


def test_text_renders_vitals_section() -> None:
    output = render_text(_report_with_vitals(), color=False)
    assert "Core Web Vitals" in output
    assert "Mobile" in output
    assert "Eliminate render-blocking resources" in output
    assert "Timed out contacting PageSpeed Insights." in output


def test_markdown_renders_vitals_section() -> None:
    output = render_markdown(_report_with_vitals())
    assert "## Core Web Vitals" in output
    assert "Field data (real users)" in output
    assert "performance 94/100" in output
    assert "**Error:** Timed out contacting PageSpeed Insights." in output


def test_html_renders_vitals_section() -> None:
    output = render_html(_report_with_vitals())
    assert "Core Web Vitals" in output
    assert "LCP" in output
    assert "Timed out contacting PageSpeed Insights." in output


def test_json_renders_vitals_section() -> None:
    data = report_to_dict(_report_with_vitals())
    assert data["vitals"]["mobile"]["field_data"]["lcp"]["value"] == 2100.0
    assert data["vitals"]["mobile"]["lab_data"]["performance_score"] == 94.0
    assert data["vitals"]["desktop"]["error"] == "Timed out contacting PageSpeed Insights."
    output = render_json(_report_with_vitals())
    assert '"vitals"' in output


def test_renderers_omit_vitals_section_when_absent(sample_report: Report) -> None:
    assert "Core Web Vitals" not in render_text(sample_report, color=False)
    assert "Core Web Vitals" not in render_markdown(sample_report)
    assert "Core Web Vitals" not in render_html(sample_report)
    assert report_to_dict(sample_report)["vitals"] is None
