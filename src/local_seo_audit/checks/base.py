"""The plugin interface every check implements, and the context it runs in."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup

from local_seo_audit.business import Business
from local_seo_audit.fetcher import FetchResult
from local_seo_audit.models import CheckResult, Severity, Status


@dataclass(frozen=True, slots=True)
class CrawlLinkStatus:
    """The result of checking one internal link found during ``--crawl``."""

    url: str
    status_code: int
    ok: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CrawlResult:
    """Outcome of the capped, same-host internal-link crawl."""

    checked: list[CrawlLinkStatus] = field(default_factory=list)
    requested: int = 0

    @property
    def broken(self) -> list[CrawlLinkStatus]:
        return [c for c in self.checked if not c.ok]


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Everything a :class:`Check` needs: fetched data plus the known NAP."""

    input_url: str
    business: Business
    primary: FetchResult
    soup: BeautifulSoup
    http_probe: FetchResult | None
    robots: FetchResult
    sitemap: FetchResult
    favicon: FetchResult
    crawl: CrawlResult | None
    crawl_requested: int
    fetched_at: datetime

    @property
    def page_url(self) -> str:
        """The URL the page actually loaded at, after any redirects."""
        return self.primary.final_url or self.input_url

    @property
    def page_text(self) -> str:
        """Visible, whitespace-normalized text content of the page."""
        return " ".join(self.soup.get_text(separator=" ").split())


class Check(ABC):
    """One pluggable local-SEO / conversion check.

    Subclasses set the four class attributes and implement :meth:`run`.
    Registering a new check is just adding an instance to
    ``local_seo_audit.checks.ALL_CHECKS``.
    """

    id: str
    title: str
    weight: int
    severity: Severity

    def make(self, status: Status, evidence: str, fix: str) -> CheckResult:
        """Build this check's :class:`CheckResult`; the one way to construct one."""
        return CheckResult(
            id=self.id,
            title=self.title,
            weight=self.weight,
            severity=self.severity,
            status=status,
            evidence=evidence,
            fix=fix,
        )

    def skip(self, reason: str) -> CheckResult:
        """A result that is excluded from scoring, e.g. because data was unavailable."""
        return self.make(Status.SKIP, reason, "")

    @abstractmethod
    def run(self, ctx: AuditContext) -> CheckResult:
        """Evaluate this check against ``ctx`` and return its result."""
        raise NotImplementedError
