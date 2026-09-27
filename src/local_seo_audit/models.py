"""Data model shared by checks, scoring, and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from local_seo_audit.business import Business
from local_seo_audit.content_gaps import ContentGapPlan
from local_seo_audit.crawler import SiteCrawlReport
from local_seo_audit.vitals import VitalsResult

if TYPE_CHECKING:
    from local_seo_audit.compare import CompetitorComparison


class Status(str, Enum):
    """Outcome of a single check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class Severity(str, Enum):
    """How much a failing check should worry the owner."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    """The outcome of a single :class:`~local_seo_audit.checks.base.Check`.

    Attributes:
        id: Stable, machine-readable identifier (e.g. ``"https_redirect"``).
        title: Short human-readable name of the check.
        weight: Relative importance used for scoring (higher = more points).
        severity: How serious a failure of this check is for the business.
        status: pass / warn / fail / skip.
        evidence: What was actually observed on the page (for transparency).
        fix: Plain-English, non-technical instructions for fixing a fail/warn.
    """

    id: str
    title: str
    weight: int
    severity: Severity
    status: Status
    evidence: str
    fix: str

    @property
    def earned_points(self) -> float:
        """Points earned toward the score, out of :attr:`weight`."""
        if self.status is Status.PASS:
            return float(self.weight)
        if self.status is Status.WARN:
            return self.weight * 0.5
        return 0.0

    @property
    def counts_toward_score(self) -> bool:
        """Whether this result should be included in the score denominator."""
        return self.status is not Status.SKIP

    def sort_key(self) -> tuple[int, int]:
        """Sort key that surfaces the worst, highest-weight problems first."""
        status_rank = {Status.FAIL: 0, Status.WARN: 1, Status.PASS: 2, Status.SKIP: 3}
        return (status_rank[self.status] * 10 + _SEVERITY_ORDER[self.severity], -self.weight)


def grade_for_score(score: float) -> str:
    """Letter grade for a 0-100 score."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


@dataclass(frozen=True, slots=True)
class Report:
    """The full result of auditing one URL."""

    url: str
    final_url: str
    business: Business
    results: list[CheckResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    tool_version: str = "0.1.0"
    #: Populated only when ``--vitals`` (or ``audit(..., vitals=True)``) was requested.
    vitals: VitalsResult | None = None
    #: Populated only when ``--site`` (or ``audit(..., site=True)``) was requested.
    site_crawl: SiteCrawlReport | None = None
    #: Populated only when ``--compare URL`` was given (attached after the fact via
    #: ``dataclasses.replace``, since it depends on a completed ``Report``).
    competitors: CompetitorComparison | None = None
    #: Populated when a site crawl ran (--site) or --services/--areas was given.
    content_plan: ContentGapPlan | None = None

    @property
    def score(self) -> float:
        scored = [r for r in self.results if r.counts_toward_score]
        total_weight = sum(r.weight for r in scored)
        if total_weight == 0:
            return 0.0
        earned = sum(r.earned_points for r in scored)
        return round(100 * earned / total_weight, 1)

    @property
    def grade(self) -> str:
        return grade_for_score(self.score)

    @property
    def sorted_results(self) -> list[CheckResult]:
        """Results ordered worst-first, so the fix list is prioritized."""
        return sorted(self.results, key=CheckResult.sort_key)

    def counts(self) -> dict[Status, int]:
        out: dict[Status, int] = dict.fromkeys(Status, 0)
        for r in self.results:
            out[r.status] += 1
        return out
