from __future__ import annotations

from local_seo_audit.models import Report
from local_seo_audit.render.text import render_text


def test_plain_text_has_no_ansi_codes(sample_report: Report) -> None:
    output = render_text(sample_report, color=False)
    assert "\x1b[" not in output
    assert "example.com" in output
    assert "Joe's Plumbing" in output


def test_colored_text_has_ansi_codes(sample_report: Report) -> None:
    output = render_text(sample_report, color=True)
    assert "\x1b[" in output


def test_contains_score_and_grade(sample_report: Report) -> None:
    output = render_text(sample_report, color=False)
    assert f"{sample_report.score}/100" in output
    assert sample_report.grade in output


def test_fix_shown_for_fail_but_not_for_pass(sample_report: Report) -> None:
    output = render_text(sample_report, color=False)
    assert "Use exactly one <h1> per page." in output
    assert "Install an SSL certificate." not in output


def test_worst_first_ordering(sample_report: Report) -> None:
    output = render_text(sample_report, color=False)
    fail_pos = output.index("Exactly one H1 heading")
    pass_pos = output.index("HTTPS is enabled")
    assert fail_pos < pass_pos
