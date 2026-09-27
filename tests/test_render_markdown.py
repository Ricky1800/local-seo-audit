from __future__ import annotations

from local_seo_audit.models import Report
from local_seo_audit.render.markdown import render_markdown


def test_has_markdown_headings(sample_report: Report) -> None:
    output = render_markdown(sample_report)
    assert output.startswith("# Local SEO Audit")
    assert "## Prioritized fix list" in output


def test_contains_score_and_grade(sample_report: Report) -> None:
    output = render_markdown(sample_report)
    assert f"{sample_report.score}/100" in output
    assert sample_report.grade in output


def test_fix_only_shown_for_warn_and_fail(sample_report: Report) -> None:
    output = render_markdown(sample_report)
    assert "**Fix:** Use exactly one <h1> per page." in output
    assert "**Fix:** Install an SSL certificate." not in output


def test_ends_with_single_trailing_newline(sample_report: Report) -> None:
    output = render_markdown(sample_report)
    assert output.endswith("\n")
    assert not output.endswith("\n\n")
