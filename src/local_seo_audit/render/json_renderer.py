"""JSON output for piping into other tools/dashboards."""

from __future__ import annotations

import json
from typing import Any

from local_seo_audit.models import Report
from local_seo_audit.vitals import LabData, Metric, StrategyResult, VitalsResult


def _metric_to_dict(metric: Metric | None) -> dict[str, Any] | None:
    if metric is None:
        return None
    return {
        "name": metric.name,
        "value": metric.value,
        "unit": metric.unit,
        "rating": metric.rating,
    }


def _lab_to_dict(lab: LabData | None) -> dict[str, Any] | None:
    if lab is None:
        return None
    return {
        "performance_score": lab.performance_score,
        "lcp": _metric_to_dict(lab.lcp),
        "tbt": _metric_to_dict(lab.tbt),
        "cls": _metric_to_dict(lab.cls),
        "opportunities": lab.opportunities,
    }


def _strategy_to_dict(result: StrategyResult) -> dict[str, Any]:
    field_data = result.field_data
    return {
        "strategy": result.strategy,
        "error": result.error,
        "field_data": (
            {
                "lcp": _metric_to_dict(field_data.lcp),
                "inp": _metric_to_dict(field_data.inp),
                "cls": _metric_to_dict(field_data.cls),
                "overall_category": field_data.overall_category,
            }
            if field_data is not None
            else None
        ),
        "lab_data": _lab_to_dict(result.lab_data),
    }


def _vitals_to_dict(vitals: VitalsResult | None) -> dict[str, Any] | None:
    if vitals is None:
        return None
    return {
        "mobile": _strategy_to_dict(vitals.mobile) if vitals.mobile is not None else None,
        "desktop": _strategy_to_dict(vitals.desktop) if vitals.desktop is not None else None,
    }


def report_to_dict(report: Report) -> dict[str, Any]:
    """A plain, JSON-serializable representation of ``report``."""
    return {
        "url": report.url,
        "final_url": report.final_url,
        "business": {
            "name": report.business.name,
            "phone": report.business.phone,
            "city": report.business.city,
            "address": report.business.address,
        },
        "generated_at": report.generated_at.isoformat(),
        "tool_version": report.tool_version,
        "score": report.score,
        "grade": report.grade,
        "counts": {status.value: count for status, count in report.counts().items()},
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "weight": r.weight,
                "severity": r.severity.value,
                "status": r.status.value,
                "evidence": r.evidence,
                "fix": r.fix,
            }
            for r in report.sorted_results
        ],
        "vitals": _vitals_to_dict(report.vitals),
    }


def render_json(report: Report, *, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent) + "\n"
