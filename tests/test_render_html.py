from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.models import CheckResult, Report, Severity, Status
from local_seo_audit.render.html import render_html


def test_is_a_standalone_html_document(sample_report: Report) -> None:
    output = render_html(sample_report)
    assert output.strip().startswith("<!DOCTYPE html>")
    assert "<style>" in output
    assert "<script " not in output  # no external scripts, no external stylesheet fetches
    assert 'rel="stylesheet" href="http' not in output


def test_contains_business_and_score(sample_report: Report) -> None:
    output = render_html(sample_report)
    assert "Joe" in output and "Plumbing" in output
    assert str(sample_report.score) in output
    assert sample_report.grade in output


def test_escapes_html_in_evidence() -> None:
    malicious = CheckResult(
        id="title",
        title="Title tag",
        weight=8,
        severity=Severity.HIGH,
        status=Status.FAIL,
        evidence='<script>alert("xss")</script>',
        fix="fix it",
    )
    report = Report(
        url="https://example.com",
        final_url="https://example.com/",
        business=Business(),
        results=[malicious],
    )
    output = render_html(report)
    assert "<script>alert" not in output
    assert "&lt;script&gt;" in output


def test_fix_only_rendered_for_warn_and_fail(sample_report: Report) -> None:
    output = render_html(sample_report)
    assert "Use exactly one" in output
    assert "Install an SSL certificate." not in output


def test_has_score_gauge_and_executive_summary(sample_report: Report) -> None:
    output = render_html(sample_report)
    assert 'class="gauge"' in output
    assert "gauge-value" in output
    assert "Executive summary" in output
    # sample_report has a FAIL (h1, medium) and a WARN (title, high) - only the
    # high/critical-severity WARN/FAIL should surface in "fix these first".
    assert "Title tag is present" in output


def test_is_print_friendly() -> None:
    report = Report(
        url="https://example.com", final_url="https://example.com/", business=Business()
    )
    output = render_html(report)
    assert "@media print" in output
    assert "<script " not in output


def test_has_no_external_assets(sample_report: Report) -> None:
    output = render_html(sample_report)
    assert "http://fonts" not in output
    assert "https://fonts" not in output
    assert '<link rel="stylesheet"' not in output
