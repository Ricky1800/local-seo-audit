"""Core Web Vitals via Google's free PageSpeed Insights (PSI) API v5.

PSI wraps two very different measurements for a URL:

- **Field data** (``loadingExperience``): real-user Chrome UX Report (CrUX)
  data, aggregated over the last 28 days. Only available once a URL has
  enough real Chrome traffic; small local-business sites often don't have
  it, which is not an error.
- **Lab data** (``lighthouseResult``): a single simulated Lighthouse run,
  always present when the API call succeeds.

The API works keyless with low rate limits; set the ``PSI_API_KEY`` env var
(or pass ``api_key=``) to use a free Google API key for a much higher quota.
Nothing here ever raises for a slow/quota/network failure - it always
returns a :class:`StrategyResult` with ``error`` set instead, so a flaky
PSI response never crashes an otherwise-successful audit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

#: PSI runs can take a long time (a real Lighthouse pass); be generous.
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

Strategy = Literal["mobile", "desktop"]
Rating = Literal["good", "needs-improvement", "poor"]

#: Google's published Core Web Vitals thresholds: (good-upper-bound, needs-improvement-upper-bound).
LCP_THRESHOLDS_MS = (2500.0, 4000.0)
CLS_THRESHOLDS = (0.1, 0.25)
INP_THRESHOLDS_MS = (200.0, 500.0)
#: Total Blocking Time is a lab-only proxy for interactivity (no official field metric); these
#: bounds follow Lighthouse's own scoring curve rather than a CrUX-published threshold.
TBT_THRESHOLDS_MS = (200.0, 600.0)


def rate(value: float, thresholds: tuple[float, float]) -> Rating:
    """Classify ``value`` against a Google-style (good, needs-improvement) threshold pair."""
    good, needs_improvement = thresholds
    if value <= good:
        return "good"
    if value <= needs_improvement:
        return "needs-improvement"
    return "poor"


@dataclass(frozen=True, slots=True)
class Metric:
    """One measured value, already classified against Google's published thresholds."""

    name: str
    value: float
    unit: str
    rating: Rating


@dataclass(frozen=True, slots=True)
class FieldData:
    """Real-user CrUX data for one strategy. Any metric may be absent (not enough traffic)."""

    lcp: Metric | None = None
    inp: Metric | None = None
    cls: Metric | None = None
    overall_category: str | None = None

    def has_any(self) -> bool:
        return self.lcp is not None or self.inp is not None or self.cls is not None


@dataclass(frozen=True, slots=True)
class LabData:
    """A single simulated Lighthouse run."""

    performance_score: float | None = None
    lcp: Metric | None = None
    tbt: Metric | None = None
    cls: Metric | None = None
    opportunities: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StrategyResult:
    """The outcome of one PSI call for one strategy (mobile or desktop)."""

    strategy: Strategy
    field_data: FieldData | None = None
    lab_data: LabData | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True, slots=True)
class VitalsResult:
    """Both strategies PSI was asked to run (whichever were requested)."""

    mobile: StrategyResult | None = None
    desktop: StrategyResult | None = None

    def by_strategy(self) -> list[StrategyResult]:
        return [r for r in (self.mobile, self.desktop) if r is not None]


def _crux_metric(
    metrics: dict[str, Any], key: str, name: str, unit: str, thresholds: tuple[float, float]
) -> Metric | None:
    entry = metrics.get(key)
    if not isinstance(entry, dict):
        return None
    percentile = entry.get("percentile")
    if percentile is None:
        return None
    try:
        value = float(percentile)
    except (TypeError, ValueError):
        return None
    if key == "CUMULATIVE_LAYOUT_SHIFT_SCORE":
        # CrUX reports CLS as an integer percentile scaled by 100 (e.g. 12 -> 0.12).
        value = value / 100.0
    return Metric(name=name, value=value, unit=unit, rating=rate(value, thresholds))


def _parse_field_data(loading_experience: Any) -> FieldData | None:
    if not isinstance(loading_experience, dict):
        return None
    metrics = loading_experience.get("metrics")
    if not isinstance(metrics, dict):
        return None
    lcp = _crux_metric(metrics, "LARGEST_CONTENTFUL_PAINT_MS", "LCP", "ms", LCP_THRESHOLDS_MS)
    inp = _crux_metric(metrics, "INTERACTION_TO_NEXT_PAINT", "INP", "ms", INP_THRESHOLDS_MS)
    cls = _crux_metric(metrics, "CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS", "", CLS_THRESHOLDS)
    if lcp is None and inp is None and cls is None:
        return None
    category = loading_experience.get("overall_category")
    return FieldData(
        lcp=lcp, inp=inp, cls=cls, overall_category=category if isinstance(category, str) else None
    )


def _audit_numeric_value(audits: dict[str, Any], audit_id: str) -> float | None:
    audit = audits.get(audit_id)
    if not isinstance(audit, dict):
        return None
    value = audit.get("numericValue")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _top_opportunities(audits: dict[str, Any], limit: int = 5) -> list[str]:
    candidates: list[tuple[float, str]] = []
    for audit in audits.values():
        if not isinstance(audit, dict):
            continue
        details = audit.get("details")
        if not isinstance(details, dict) or details.get("type") != "opportunity":
            continue
        score = audit.get("score")
        if score is not None and score >= 0.9:
            continue
        savings_ms = details.get("overallSavingsMs") or 0
        title = audit.get("title")
        if not isinstance(title, str) or not title:
            continue
        try:
            savings = float(savings_ms)
        except (TypeError, ValueError):
            savings = 0.0
        candidates.append((savings, title))
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [title for _, title in candidates[:limit]]


def _parse_lab_data(lighthouse_result: Any) -> LabData | None:
    if not isinstance(lighthouse_result, dict):
        return None
    audits = lighthouse_result.get("audits")
    audits = audits if isinstance(audits, dict) else {}

    performance_score: float | None = None
    categories = lighthouse_result.get("categories")
    if isinstance(categories, dict):
        performance = categories.get("performance")
        if isinstance(performance, dict) and performance.get("score") is not None:
            try:
                performance_score = round(float(performance["score"]) * 100, 1)
            except (TypeError, ValueError):
                performance_score = None

    lcp_value = _audit_numeric_value(audits, "largest-contentful-paint")
    tbt_value = _audit_numeric_value(audits, "total-blocking-time")
    cls_value = _audit_numeric_value(audits, "cumulative-layout-shift")

    lcp = (
        Metric("LCP", lcp_value, "ms", rate(lcp_value, LCP_THRESHOLDS_MS))
        if lcp_value is not None
        else None
    )
    tbt = (
        Metric("TBT", tbt_value, "ms", rate(tbt_value, TBT_THRESHOLDS_MS))
        if tbt_value is not None
        else None
    )
    cls = (
        Metric("CLS", cls_value, "", rate(cls_value, CLS_THRESHOLDS))
        if cls_value is not None
        else None
    )

    if performance_score is None and lcp is None and tbt is None and cls is None:
        return None

    return LabData(
        performance_score=performance_score,
        lcp=lcp,
        tbt=tbt,
        cls=cls,
        opportunities=_top_opportunities(audits),
    )


def _error_message_from_response(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200] if response.text else "no details"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message:
                return message
    return "no details"


def _fetch_one(
    client: httpx.Client, url: str, strategy: Strategy, api_key: str | None
) -> StrategyResult:
    params: dict[str, str] = {"url": url, "strategy": strategy, "category": "performance"}
    if api_key:
        params["key"] = api_key

    try:
        response = client.get(PSI_ENDPOINT, params=params)
    except httpx.TimeoutException:
        return StrategyResult(
            strategy=strategy,
            error="Timed out contacting PageSpeed Insights. Try again, or run without --vitals.",
        )
    except httpx.HTTPError as exc:
        return StrategyResult(strategy=strategy, error=f"{type(exc).__name__}: {exc}")

    if response.status_code == 429:
        return StrategyResult(
            strategy=strategy,
            error=(
                "PageSpeed Insights quota exceeded (HTTP 429). Set the PSI_API_KEY environment "
                "variable with a free Google API key for a much higher quota, or try again later."
            ),
        )
    if response.status_code != 200:
        detail = _error_message_from_response(response)
        return StrategyResult(
            strategy=strategy,
            error=f"PageSpeed Insights returned HTTP {response.status_code}: {detail}",
        )

    try:
        payload = response.json()
    except ValueError:
        return StrategyResult(
            strategy=strategy, error="PageSpeed Insights returned an unparseable response."
        )
    if not isinstance(payload, dict):
        return StrategyResult(
            strategy=strategy, error="PageSpeed Insights returned an unexpected response shape."
        )

    field_data = _parse_field_data(
        payload.get("loadingExperience") or payload.get("originLoadingExperience")
    )
    lab_data = _parse_lab_data(payload.get("lighthouseResult"))
    if field_data is None and lab_data is None:
        return StrategyResult(
            strategy=strategy, error="PageSpeed Insights returned no usable field or lab data."
        )
    return StrategyResult(strategy=strategy, field_data=field_data, lab_data=lab_data)


def fetch_core_web_vitals(
    url: str,
    *,
    api_key: str | None = None,
    client: httpx.Client | None = None,
    strategies: tuple[Strategy, ...] = ("mobile", "desktop"),
) -> VitalsResult:
    """Fetch Core Web Vitals for ``url`` from PageSpeed Insights, mobile and desktop.

    Never raises: a timeout, quota error, or malformed response becomes a
    per-strategy :attr:`StrategyResult.error` instead of an exception, so a
    flaky third-party API can never crash the rest of an audit.
    """
    key = api_key if api_key is not None else os.environ.get("PSI_API_KEY") or None
    owns_client = client is None
    http_client = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    results: dict[Strategy, StrategyResult] = {}
    try:
        for strategy in strategies:
            results[strategy] = _fetch_one(http_client, url, strategy, key)
    finally:
        if owns_client:
            http_client.close()
    return VitalsResult(mobile=results.get("mobile"), desktop=results.get("desktop"))
