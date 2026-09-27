"""The pluggable check registry.

Every check is a small class implementing :class:`~local_seo_audit.checks.base.Check`.
Adding a new one is: write the class, import it here, and append an instance to
``ALL_CHECKS`` — nothing else in the codebase needs to change.
"""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check, CrawlLinkStatus, CrawlResult
from local_seo_audit.checks.canonical import CanonicalCheck
from local_seo_audit.checks.favicon import FaviconCheck
from local_seo_audit.checks.h1 import H1Check
from local_seo_audit.checks.image_alt import ImageAltCheck
from local_seo_audit.checks.meta_description import MetaDescriptionCheck
from local_seo_audit.checks.open_graph import OpenGraphCheck
from local_seo_audit.checks.page_weight import PageWeightCheck
from local_seo_audit.checks.title import TitleCheck
from local_seo_audit.checks.viewport import ViewportCheck

ALL_CHECKS: list[Check] = [
    TitleCheck(),
    MetaDescriptionCheck(),
    H1Check(),
    ViewportCheck(),
    CanonicalCheck(),
    ImageAltCheck(),
    PageWeightCheck(),
    OpenGraphCheck(),
    FaviconCheck(),
]

__all__ = [
    "ALL_CHECKS",
    "AuditContext",
    "CanonicalCheck",
    "Check",
    "CrawlLinkStatus",
    "CrawlResult",
    "FaviconCheck",
    "H1Check",
    "ImageAltCheck",
    "MetaDescriptionCheck",
    "OpenGraphCheck",
    "PageWeightCheck",
    "TitleCheck",
    "ViewportCheck",
]
