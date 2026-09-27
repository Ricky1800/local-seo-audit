"""Output renderers: pick one with :func:`render`, or import a specific one."""

from __future__ import annotations

from typing import Literal

from local_seo_audit.models import Report
from local_seo_audit.render.html import render_html
from local_seo_audit.render.json_renderer import render_json
from local_seo_audit.render.markdown import render_markdown
from local_seo_audit.render.text import render_text

Format = Literal["text", "md", "html", "json"]

__all__ = ["Format", "render", "render_html", "render_json", "render_markdown", "render_text"]


def render(report: Report, fmt: Format, *, color: bool = True) -> str:
    """Render ``report`` in the given output format."""
    if fmt == "text":
        return render_text(report, color=color)
    if fmt == "md":
        return render_markdown(report)
    if fmt == "html":
        return render_html(report)
    if fmt == "json":
        return render_json(report)
    raise ValueError(f"Unknown format: {fmt!r}")
