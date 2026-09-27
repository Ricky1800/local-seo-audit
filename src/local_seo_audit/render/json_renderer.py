"""JSON output for piping into other tools/dashboards."""

from __future__ import annotations

import json
from typing import Any

from local_seo_audit.models import Report


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
    }


def render_json(report: Report, *, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent) + "\n"
