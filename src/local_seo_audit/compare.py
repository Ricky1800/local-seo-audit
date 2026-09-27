"""Competitor compare (``--compare URL``, up to 3): same checks, side-by-side.

Each competitor is audited with the exact same pluggable checks as the
primary site, so the comparison is apples-to-apples. The result is a
per-check matrix (your status vs. each competitor's) plus a ranked list of
"they have it, you don't" gaps, sorted by the weight of the check they beat
you on (a proxy for how much it matters).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup

from local_seo_audit.business import Business
from local_seo_audit.checks import ALL_CHECKS
from local_seo_audit.core import audit
from local_seo_audit.fetcher import fetch, new_client
from local_seo_audit.models import Status
from local_seo_audit.structured_data import extract_schema_types

if TYPE_CHECKING:
    from local_seo_audit.models import Report

#: A meaningful comparison needs a small, readable set - beyond this it stops being
#: a quick side-by-side and starts being a spreadsheet.
MAX_COMPETITORS = 3


@dataclass(frozen=True, slots=True)
class KeyMetrics:
    """A few at-a-glance numbers, shown alongside the full check matrix."""

    page_weight_bytes: int | None
    schema_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompetitorEntry:
    """One competitor's audit outcome (or why it couldn't be audited)."""

    url: str
    report: Report | None
    metrics: KeyMetrics | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.report is not None


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    """One check's status for you vs. every competitor."""

    check_id: str
    title: str
    weight: int
    your_status: str | None
    competitor_statuses: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class GapItem:
    """A check where at least one competitor passes and you do not."""

    check_id: str
    title: str
    weight: int
    ahead_competitors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompetitorComparison:
    """The full side-by-side result, ready for every renderer to show."""

    your_url: str
    competitors: tuple[CompetitorEntry, ...]
    matrix: tuple[ComparisonRow, ...]
    gaps: tuple[GapItem, ...]


def _key_metrics(client: httpx.Client, url: str) -> KeyMetrics | None:
    result = fetch(client, url)
    if not result.ok:
        return None
    soup = (
        BeautifulSoup(result.text, "html.parser")
        if result.text
        else BeautifulSoup("", "html.parser")
    )
    return KeyMetrics(
        page_weight_bytes=result.byte_size,
        schema_types=tuple(sorted(extract_schema_types(soup))),
    )


def compare_competitors(
    your_report: Report,
    competitor_urls: list[str],
    *,
    business: Business | None = None,
    vitals: bool = False,
    psi_api_key: str | None = None,
    client: httpx.Client | None = None,
) -> CompetitorComparison:
    """Audit up to :data:`MAX_COMPETITORS` competitor URLs and compare them to ``your_report``.

    Raises:
        ValueError: if more than :data:`MAX_COMPETITORS` URLs are given.
    """
    if len(competitor_urls) > MAX_COMPETITORS:
        raise ValueError(
            f"At most {MAX_COMPETITORS} competitor URLs are supported "
            f"(got {len(competitor_urls)}). Pick your top {MAX_COMPETITORS}."
        )

    owns_client = client is None
    http_client = client or new_client()
    entries: list[CompetitorEntry] = []
    try:
        for url in competitor_urls:
            try:
                competitor_report = audit(
                    url,
                    business=business,
                    vitals=vitals,
                    psi_api_key=psi_api_key,
                    client=http_client,
                )
            except Exception as exc:  # pragma: no cover - audit() itself does not raise
                entries.append(CompetitorEntry(url=url, report=None, metrics=None, error=str(exc)))
                continue
            metrics = _key_metrics(http_client, competitor_report.final_url)
            entries.append(CompetitorEntry(url=url, report=competitor_report, metrics=metrics))
    finally:
        if owns_client:
            http_client.close()

    your_results = {r.id: r for r in your_report.results}
    rows: list[ComparisonRow] = []
    gaps: list[GapItem] = []
    for check in ALL_CHECKS:
        your_result = your_results.get(check.id)
        your_status = your_result.status.value if your_result else None
        competitor_statuses: list[str | None] = []
        ahead: list[str] = []
        for entry in entries:
            status_value: str | None = None
            if entry.report is not None:
                competitor_result = next(
                    (r for r in entry.report.results if r.id == check.id), None
                )
                if competitor_result is not None:
                    status_value = competitor_result.status.value
                    if (
                        competitor_result.status is Status.PASS
                        and your_result is not None
                        and your_result.status in (Status.FAIL, Status.WARN)
                    ):
                        ahead.append(entry.url)
            competitor_statuses.append(status_value)
        rows.append(
            ComparisonRow(
                check_id=check.id,
                title=check.title,
                weight=check.weight,
                your_status=your_status,
                competitor_statuses=tuple(competitor_statuses),
            )
        )
        if ahead:
            gaps.append(
                GapItem(
                    check_id=check.id,
                    title=check.title,
                    weight=check.weight,
                    ahead_competitors=tuple(ahead),
                )
            )

    gaps.sort(key=lambda g: g.weight, reverse=True)

    return CompetitorComparison(
        your_url=your_report.final_url,
        competitors=tuple(entries),
        matrix=tuple(rows),
        gaps=tuple(gaps),
    )
