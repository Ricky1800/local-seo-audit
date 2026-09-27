from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.models import CheckResult, Report, Severity, Status, grade_for_score


def _result(status: Status, weight: int = 10, severity: Severity = Severity.MEDIUM) -> CheckResult:
    return CheckResult(
        id="dummy",
        title="Dummy check",
        weight=weight,
        severity=severity,
        status=status,
        evidence="evidence",
        fix="fix",
    )


class TestCheckResult:
    def test_earned_points_pass(self) -> None:
        assert _result(Status.PASS, weight=10).earned_points == 10.0

    def test_earned_points_warn(self) -> None:
        assert _result(Status.WARN, weight=10).earned_points == 5.0

    def test_earned_points_fail(self) -> None:
        assert _result(Status.FAIL, weight=10).earned_points == 0.0

    def test_earned_points_skip(self) -> None:
        assert _result(Status.SKIP, weight=10).earned_points == 0.0

    def test_counts_toward_score(self) -> None:
        assert _result(Status.PASS).counts_toward_score is True
        assert _result(Status.SKIP).counts_toward_score is False


class TestGradeForScore:
    def test_grade_boundaries(self) -> None:
        assert grade_for_score(95) == "A"
        assert grade_for_score(90) == "A"
        assert grade_for_score(89.9) == "B"
        assert grade_for_score(80) == "B"
        assert grade_for_score(70) == "C"
        assert grade_for_score(60) == "D"
        assert grade_for_score(59.9) == "F"
        assert grade_for_score(0) == "F"


class TestReport:
    def test_score_all_pass_is_100(self) -> None:
        report = Report(
            url="https://example.com",
            final_url="https://example.com",
            business=Business(),
            results=[_result(Status.PASS, weight=10), _result(Status.PASS, weight=20)],
        )
        assert report.score == 100.0
        assert report.grade == "A"

    def test_score_mixed(self) -> None:
        report = Report(
            url="https://example.com",
            final_url="https://example.com",
            business=Business(),
            results=[
                _result(Status.PASS, weight=50),
                _result(Status.FAIL, weight=50),
            ],
        )
        assert report.score == 50.0
        assert report.grade == "F"

    def test_skip_excluded_from_denominator(self) -> None:
        report = Report(
            url="https://example.com",
            final_url="https://example.com",
            business=Business(),
            results=[
                _result(Status.PASS, weight=10),
                _result(Status.SKIP, weight=1000),
            ],
        )
        assert report.score == 100.0

    def test_score_with_no_results_is_zero(self) -> None:
        report = Report(
            url="https://example.com", final_url="https://example.com", business=Business()
        )
        assert report.score == 0.0
        assert report.grade == "F"

    def test_sorted_results_worst_first(self) -> None:
        report = Report(
            url="https://example.com",
            final_url="https://example.com",
            business=Business(),
            results=[
                _result(Status.PASS, severity=Severity.CRITICAL),
                _result(Status.FAIL, severity=Severity.LOW),
                _result(Status.WARN, severity=Severity.HIGH),
            ],
        )
        statuses = [r.status for r in report.sorted_results]
        assert statuses == [Status.FAIL, Status.WARN, Status.PASS]

    def test_counts(self) -> None:
        report = Report(
            url="https://example.com",
            final_url="https://example.com",
            business=Business(),
            results=[_result(Status.PASS), _result(Status.PASS), _result(Status.FAIL)],
        )
        counts = report.counts()
        assert counts[Status.PASS] == 2
        assert counts[Status.FAIL] == 1
        assert counts[Status.WARN] == 0
        assert counts[Status.SKIP] == 0
