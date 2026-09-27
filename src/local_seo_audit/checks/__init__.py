"""The pluggable check registry.

Every check is a small class implementing :class:`~local_seo_audit.checks.base.Check`.
Adding a new one is: write the class, import it here, and append an instance to
``ALL_CHECKS`` — nothing else in the codebase needs to change.
"""

from __future__ import annotations

from local_seo_audit.checks.base import AuditContext, Check, CrawlLinkStatus, CrawlResult
from local_seo_audit.checks.canonical import CanonicalCheck
from local_seo_audit.checks.click_to_call import ClickToCallCheck
from local_seo_audit.checks.crawl_links import CrawlBrokenLinksCheck
from local_seo_audit.checks.favicon import FaviconCheck
from local_seo_audit.checks.h1 import H1Check
from local_seo_audit.checks.https_redirect import HttpsRedirectCheck
from local_seo_audit.checks.image_alt import ImageAltCheck
from local_seo_audit.checks.json_ld import JsonLdLocalBusinessCheck
from local_seo_audit.checks.maps import MapsEmbedCheck
from local_seo_audit.checks.meta_description import MetaDescriptionCheck
from local_seo_audit.checks.nap_visible import NapVisibleCheck
from local_seo_audit.checks.open_graph import OpenGraphCheck
from local_seo_audit.checks.page_weight import PageWeightCheck
from local_seo_audit.checks.robots_sitemap import RobotsSitemapCheck
from local_seo_audit.checks.title import TitleCheck
from local_seo_audit.checks.viewport import ViewportCheck

ALL_CHECKS: list[Check] = [
    HttpsRedirectCheck(),
    TitleCheck(),
    MetaDescriptionCheck(),
    H1Check(),
    ViewportCheck(),
    JsonLdLocalBusinessCheck(),
    NapVisibleCheck(),
    ClickToCallCheck(),
    MapsEmbedCheck(),
    RobotsSitemapCheck(),
    CanonicalCheck(),
    ImageAltCheck(),
    PageWeightCheck(),
    OpenGraphCheck(),
    FaviconCheck(),
    CrawlBrokenLinksCheck(),
]

__all__ = [
    "ALL_CHECKS",
    "AuditContext",
    "CanonicalCheck",
    "Check",
    "ClickToCallCheck",
    "CrawlBrokenLinksCheck",
    "CrawlLinkStatus",
    "CrawlResult",
    "FaviconCheck",
    "H1Check",
    "HttpsRedirectCheck",
    "ImageAltCheck",
    "JsonLdLocalBusinessCheck",
    "MapsEmbedCheck",
    "MetaDescriptionCheck",
    "NapVisibleCheck",
    "OpenGraphCheck",
    "PageWeightCheck",
    "RobotsSitemapCheck",
    "TitleCheck",
    "ViewportCheck",
]
