from __future__ import annotations

import json

from local_seo_audit.models import Report, Status
from local_seo_audit.render.json_renderer import render_json, report_to_dict


def test_report_to_dict_shape(sample_report: Report) -> None:
    data = report_to_dict(sample_report)
    assert data["url"] == "https://example.com"
    assert data["score"] == sample_report.score
    assert data["grade"] == sample_report.grade
    assert data["business"]["name"] == "Joe's Plumbing"
    assert len(data["results"]) == 4
    assert data["counts"][Status.FAIL.value] == 1


def test_render_json_is_valid_json(sample_report: Report) -> None:
    output = render_json(sample_report)
    parsed = json.loads(output)
    assert parsed["url"] == "https://example.com"
    assert isinstance(parsed["results"], list)


def test_results_are_worst_first(sample_report: Report) -> None:
    data = report_to_dict(sample_report)
    assert data["results"][0]["status"] == "fail"
