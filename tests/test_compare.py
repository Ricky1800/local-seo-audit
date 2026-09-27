"""Competitor-compare tests: audits reuse the same checks, matrix + gaps are derived correctly."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from local_seo_audit.business import Business
from local_seo_audit.compare import MAX_COMPETITORS, compare_competitors
from local_seo_audit.core import audit
from local_seo_audit.models import Status

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "competitors"


def _strong_html() -> str:
    return (FIXTURES_DIR / "strong.html").read_text(encoding="utf-8")


def _mock_competitor(respx_mock: respx.MockRouter, origin: str, html: str) -> None:
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    http_origin = "http://" + origin.removeprefix("https://")
    respx_mock.get(f"{http_origin}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))


def test_compare_finds_gaps_where_competitor_beats_you(
    respx_mock: respx.MockRouter, bad_site_html: str
) -> None:
    your_origin = "http://yoursite.example"
    respx_mock.get(f"{your_origin}/").mock(return_value=httpx.Response(200, text=bad_site_html))
    respx_mock.get(f"{your_origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/favicon.ico").mock(return_value=httpx.Response(404))

    competitor_origin = "https://www.aceplumbingnj.com"
    _mock_competitor(respx_mock, competitor_origin, _strong_html())

    your_report = audit(f"{your_origin}/", business=Business(name="Bad Co"))
    comparison = compare_competitors(your_report, [f"{competitor_origin}/"])

    assert len(comparison.competitors) == 1
    competitor = comparison.competitors[0]
    assert competitor.ok
    assert competitor.report is not None
    assert competitor.report.score > your_report.score
    assert competitor.metrics is not None
    assert competitor.metrics.page_weight_bytes is not None
    assert "Plumber" in competitor.metrics.schema_types
    assert "AggregateRating" in competitor.metrics.schema_types

    assert comparison.gaps, "expected at least one gap where the competitor beats you"
    click_to_call_gap = next((g for g in comparison.gaps if g.check_id == "click_to_call"), None)
    assert click_to_call_gap is not None
    assert competitor_origin + "/" in click_to_call_gap.ahead_competitors

    # Gaps are ranked by weight, worst-impact first.
    weights = [gap.weight for gap in comparison.gaps]
    assert weights == sorted(weights, reverse=True)

    # The matrix covers every check, always in the same (ALL_CHECKS) order.
    row_ids = [row.check_id for row in comparison.matrix]
    assert "click_to_call" in row_ids
    your_row = next(r for r in comparison.matrix if r.check_id == "click_to_call")
    assert your_row.your_status == Status.FAIL.value
    assert your_row.competitor_statuses == (Status.PASS.value,)


def test_compare_handles_an_unreachable_competitor_gracefully(
    respx_mock: respx.MockRouter, good_site_html: str
) -> None:
    your_origin = "https://healthysite.example"
    respx_mock.get(f"{your_origin}/").mock(return_value=httpx.Response(200, text=good_site_html))
    respx_mock.get(f"http://{your_origin.removeprefix('https://')}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{your_origin}/"})
    )
    respx_mock.get(f"{your_origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/favicon.ico").mock(return_value=httpx.Response(404))

    down_origin = "https://downcompetitor.example"
    error = httpx.ConnectError("no route")
    for path in ("", "robots.txt", "sitemap.xml", "favicon.ico"):
        respx_mock.get(f"{down_origin}/{path}").mock(side_effect=error)
    respx_mock.get(f"http://{down_origin.removeprefix('https://')}/").mock(side_effect=error)

    your_report = audit(f"{your_origin}/")
    comparison = compare_competitors(your_report, [f"{down_origin}/"])

    competitor = comparison.competitors[0]
    # audit() itself never raises (network errors become FAIL results), so the competitor
    # is still "ok" - just with a very low score.
    assert competitor.ok
    assert competitor.report is not None
    assert competitor.report.score < your_report.score


def test_compare_rejects_more_than_max_competitors(respx_mock: respx.MockRouter) -> None:
    your_origin = "https://limit.example"
    html = "<html></html>"
    respx_mock.get(f"{your_origin}/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get(f"http://{your_origin.removeprefix('https://')}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{your_origin}/"})
    )
    respx_mock.get(f"{your_origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{your_origin}/favicon.ico").mock(return_value=httpx.Response(404))

    your_report = audit(f"{your_origin}/")
    too_many = [f"https://c{i}.example/" for i in range(MAX_COMPETITORS + 1)]

    with pytest.raises(ValueError, match="At most 3"):
        compare_competitors(your_report, too_many)
