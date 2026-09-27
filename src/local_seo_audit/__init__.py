"""local_seo_audit: audit a local business website for local-SEO and conversion basics."""

from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.models import CheckResult, Report, Severity, Status, grade_for_score

__version__ = "0.1.0"

__all__ = [
    "Business",
    "CheckResult",
    "Report",
    "Severity",
    "Status",
    "__version__",
    "grade_for_score",
]
