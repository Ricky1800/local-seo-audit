"""local_seo_audit: audit a local business website for local-SEO and conversion basics.

Public API:
    >>> from local_seo_audit import audit, Business
    >>> report = audit("https://example.com", business=Business(name="Joe's Plumbing"))
    >>> report.score
"""

from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.core import audit
from local_seo_audit.models import CheckResult, Report, Severity, Status

__version__ = "0.1.0"

__all__ = [
    "Business",
    "CheckResult",
    "Report",
    "Severity",
    "Status",
    "__version__",
    "audit",
]
