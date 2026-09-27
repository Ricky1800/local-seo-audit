from __future__ import annotations

import json

import pytest

from local_seo_audit.models import Report
from local_seo_audit.render import render


@pytest.mark.parametrize("fmt", ["text", "md", "html", "json"])
def test_render_dispatches_to_each_format(sample_report: Report, fmt: str) -> None:
    output = render(sample_report, fmt)  # type: ignore[arg-type]
    assert isinstance(output, str)
    assert len(output) > 0


def test_json_format_is_parseable(sample_report: Report) -> None:
    output = render(sample_report, "json")
    json.loads(output)


def test_unknown_format_raises(sample_report: Report) -> None:
    with pytest.raises(ValueError, match="Unknown format"):
        render(sample_report, "pdf")  # type: ignore[arg-type]
