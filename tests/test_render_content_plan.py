"""Every renderer must show the content-gap plan when present, and omit it otherwise."""

from __future__ import annotations

import datetime as dt

from local_seo_audit.business import Business
from local_seo_audit.content_gaps import (
    ClickToCallCoverage,
    ContentGapItem,
    ContentGapPlan,
    NapConsistency,
    PageMatchStatus,
    SchemaCoverage,
)
from local_seo_audit.models import Report
from local_seo_audit.render.html import render_html
from local_seo_audit.render.json_renderer import render_json, report_to_dict
from local_seo_audit.render.markdown import render_markdown
from local_seo_audit.render.text import render_text


def _plan() -> ContentGapPlan:
    return ContentGapPlan(
        services=(
            PageMatchStatus(query="drain cleaning", found=False, matched_url=None),
            PageMatchStatus(
                query="water heater", found=True, matched_url="https://example.com/water-heater"
            ),
        ),
        areas=(PageMatchStatus(query="Princeton", found=False, matched_url=None),),
        inferred_services=False,
        nap=NapConsistency(
            pages_checked=2,
            distinct_phone_numbers=("6095550100", "6095559999"),
            phone_consistent=False,
            pages_missing_known_phone=(),
            pages_missing_known_name=(),
            pages_missing_known_address=(),
        ),
        click_to_call=ClickToCallCoverage(
            pages_checked=2, pages_missing=("https://example.com/blog",)
        ),
        schema=SchemaCoverage(pages_with_review_schema=(), pages_with_faq_schema=()),
        has_gbp_link=False,
        has_contact_page=True,
        has_contact_page_map=False,
        plan=(
            ContentGapItem(
                title="Create /drain-cleaning-princeton: drain cleaning in Princeton",
                suggested_path="/drain-cleaning-princeton",
                why="No page targets this service+area combination.",
                priority="high",
            ),
            ContentGapItem(
                title="Add Review/AggregateRating schema",
                suggested_path=None,
                why="No page declares review structured data.",
                priority="medium",
            ),
        ),
    )


def _report_with_plan() -> Report:
    return Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(name="Joe's Plumbing"),
        results=[],
        generated_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        content_plan=_plan(),
    )


def test_text_renders_content_plan_section() -> None:
    output = render_text(_report_with_plan(), color=False)
    assert "Local content gaps" in output
    assert "drain cleaning" in output
    assert "Content to create" in output


def test_markdown_renders_content_plan_section() -> None:
    output = render_markdown(_report_with_plan())
    assert "## Local content gaps" in output
    assert "[MISSING] drain cleaning" in output
    assert "[HIGH]" in output


def test_html_renders_content_plan_section() -> None:
    output = render_html(_report_with_plan())
    assert "Local content gaps" in output
    assert "drain-cleaning-princeton" in output
    assert "MISSING" in output


def test_json_renders_content_plan_section() -> None:
    data = report_to_dict(_report_with_plan())
    assert data["content_plan"]["services"][0]["query"] == "drain cleaning"
    assert data["content_plan"]["plan"][0]["priority"] == "high"
    output = render_json(_report_with_plan())
    assert '"content_plan"' in output


def test_renderers_omit_content_plan_section_when_absent(sample_report: Report) -> None:
    assert "Local content gaps" not in render_text(sample_report, color=False)
    assert "Local content gaps" not in render_markdown(sample_report)
    assert "Local content gaps" not in render_html(sample_report)
    assert report_to_dict(sample_report)["content_plan"] is None
