"""Local content-gap analysis: service/area landing pages, NAP consistency, schema, and a plan.

Needs to see every crawled page at once (a dedicated service page might not
be the homepage), so it operates on a list of
:class:`~local_seo_audit.crawler.CrawledPage` - either a full ``--site``
crawl, or, as a lighter fallback, just the homepage.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from local_seo_audit.business import Business
from local_seo_audit.crawler import CrawledPage
from local_seo_audit.utils import normalize_phone

#: Common nav/heading text that is never itself a service or area name.
_STOPWORD_PHRASES = {
    "home",
    "about",
    "about us",
    "contact",
    "contact us",
    "blog",
    "news",
    "services",
    "our services",
    "reviews",
    "testimonials",
    "gallery",
    "faq",
    "faqs",
    "privacy policy",
    "terms",
    "terms of service",
    "sitemap",
    "careers",
    "menu",
    "shop",
    "cart",
    "login",
    "sign in",
}


@dataclass(frozen=True, slots=True)
class PageMatchStatus:
    """Whether a dedicated page was found for one requested service or area."""

    query: str
    found: bool
    matched_url: str | None


@dataclass(frozen=True, slots=True)
class NapConsistency:
    """Name/Address/Phone consistency across every crawled page."""

    pages_checked: int
    distinct_phone_numbers: tuple[str, ...]
    phone_consistent: bool
    pages_missing_known_phone: tuple[str, ...]
    pages_missing_known_name: tuple[str, ...]
    pages_missing_known_address: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClickToCallCoverage:
    pages_checked: int
    pages_missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.pages_checked > 0 and not self.pages_missing


@dataclass(frozen=True, slots=True)
class SchemaCoverage:
    pages_with_review_schema: tuple[str, ...]
    pages_with_faq_schema: tuple[str, ...]

    @property
    def has_review_schema_anywhere(self) -> bool:
        return bool(self.pages_with_review_schema)

    @property
    def has_faq_schema_anywhere(self) -> bool:
        return bool(self.pages_with_faq_schema)


@dataclass(frozen=True, slots=True)
class ContentGapItem:
    """One actionable, prioritized entry in the "content to create" plan."""

    title: str
    suggested_path: str | None
    why: str
    priority: str  # "high" | "medium" | "low"


@dataclass(frozen=True, slots=True)
class ContentGapPlan:
    services: tuple[PageMatchStatus, ...]
    areas: tuple[PageMatchStatus, ...]
    inferred_services: bool
    nap: NapConsistency
    click_to_call: ClickToCallCoverage
    schema: SchemaCoverage
    has_gbp_link: bool
    has_contact_page: bool
    has_contact_page_map: bool
    plan: tuple[ContentGapItem, ...]


def _page_haystack(page: CrawledPage) -> str:
    parts = [page.title or "", page.url]
    parts.extend(h.text for h in page.headings)
    return " ".join(parts).lower()


def _normalize_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _matches(query: str, page: CrawledPage) -> bool:
    haystack = _page_haystack(page)
    query_l = query.strip().lower()
    if query_l and query_l in haystack:
        return True
    words = _normalize_words(query)
    return bool(words) and all(w in haystack for w in words)


def _find_dedicated_page(query: str, pages: Sequence[CrawledPage]) -> PageMatchStatus:
    for page in pages:
        if page.ok and _matches(query, page):
            return PageMatchStatus(query=query, found=True, matched_url=page.url)
    return PageMatchStatus(query=query, found=False, matched_url=None)


def infer_services(pages: Sequence[CrawledPage], limit: int = 8) -> list[str]:
    """Best-effort service-name candidates from nav links and H2/H3 headings.

    Only used when ``--services`` isn't given; always prefer an explicit list
    when the caller has one; this is a fallback, not a promise of accuracy.
    """
    candidates: dict[str, None] = {}
    for page in pages:
        if not page.ok:
            continue
        for heading in page.headings:
            if heading.level not in (2, 3):
                continue
            text = heading.text.strip()
            if not text or text.lower() in _STOPWORD_PHRASES:
                continue
            if 1 <= len(text.split()) <= 6:
                candidates.setdefault(text, None)
        for text in page.nav_link_texts:
            if text.lower() in _STOPWORD_PHRASES:
                continue
            candidates.setdefault(text, None)
    return list(candidates)[:limit]


def _nap_consistency(pages: Sequence[CrawledPage], business: Business | None) -> NapConsistency:
    ok_pages = [p for p in pages if p.ok]
    counter: Counter[str] = Counter()
    for page in ok_pages:
        counter.update(page.phone_candidates)

    known_phone = normalize_phone(business.phone) if business and business.phone else None
    canonical_phone = known_phone or (counter.most_common(1)[0][0] if counter else None)

    missing_phone: list[str] = []
    if canonical_phone:
        missing_phone = [p.url for p in ok_pages if canonical_phone not in p.phone_candidates]

    missing_name: list[str] = []
    if business and business.name:
        name_l = business.name.strip().lower()
        missing_name = [p.url for p in ok_pages if name_l not in p.page_text.lower()]

    missing_address: list[str] = []
    if business and business.address:
        addr_l = business.address.strip().lower()
        missing_address = [p.url for p in ok_pages if addr_l not in p.page_text.lower()]

    return NapConsistency(
        pages_checked=len(ok_pages),
        distinct_phone_numbers=tuple(sorted(counter)),
        phone_consistent=len(counter) <= 1,
        pages_missing_known_phone=tuple(missing_phone),
        pages_missing_known_name=tuple(missing_name),
        pages_missing_known_address=tuple(missing_address),
    )


def _click_to_call_coverage(pages: Sequence[CrawledPage]) -> ClickToCallCoverage:
    ok_pages = [p for p in pages if p.ok]
    missing = [p.url for p in ok_pages if not p.has_tel_link]
    return ClickToCallCoverage(pages_checked=len(ok_pages), pages_missing=tuple(missing))


def _schema_coverage(pages: Sequence[CrawledPage]) -> SchemaCoverage:
    ok_pages = [p for p in pages if p.ok]
    return SchemaCoverage(
        pages_with_review_schema=tuple(p.url for p in ok_pages if p.has_review_schema),
        pages_with_faq_schema=tuple(p.url for p in ok_pages if p.has_faq_schema),
    )


def _find_contact_page(pages: Sequence[CrawledPage]) -> CrawledPage | None:
    for page in pages:
        if page.ok and "contact" in _page_haystack(page):
            return page
    return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "page"


def _build_plan(
    service_statuses: tuple[PageMatchStatus, ...],
    area_statuses: tuple[PageMatchStatus, ...],
    nap: NapConsistency,
    click_to_call: ClickToCallCoverage,
    schema: SchemaCoverage,
    has_gbp_link: bool,
    contact_page: CrawledPage | None,
    has_contact_page_map: bool,
) -> tuple[ContentGapItem, ...]:
    items: list[ContentGapItem] = []
    missing_services = [s for s in service_statuses if not s.found]
    missing_areas = [a for a in area_statuses if not a.found]

    if missing_services and missing_areas:
        for service in missing_services[:5]:
            for area in missing_areas[:3]:
                slug = f"{_slugify(service.query)}-{_slugify(area.query)}"
                items.append(
                    ContentGapItem(
                        title=f"Create /{slug}: {service.query} in {area.query}",
                        suggested_path=f"/{slug}",
                        why=(
                            f"No page targets '{service.query}' for {area.query}. A combined "
                            "service+area page is what local searchers actually click on for "
                            f"'{service.query} near {area.query}' / '{service.query} {area.query}'."
                        ),
                        priority="high",
                    )
                )
    for service in missing_services:
        slug = _slugify(service.query)
        items.append(
            ContentGapItem(
                title=f"Create /{slug}: dedicated {service.query} page",
                suggested_path=f"/{slug}",
                why=(
                    f"'{service.query}' has no dedicated landing page - it's likely buried in a "
                    "generic services list, which ranks worse than a focused page for that "
                    "specific search term."
                ),
                priority="high",
            )
        )
    for area in missing_areas:
        slug = _slugify(area.query)
        items.append(
            ContentGapItem(
                title=f"Create /{slug}: service-area page for {area.query}",
                suggested_path=f"/{slug}",
                why=(
                    f"No page names {area.query}, so the business is invisible for "
                    f"'[service] in {area.query}' searches even if it actually serves that area."
                ),
                priority="medium",
            )
        )

    if not nap.phone_consistent:
        items.append(
            ContentGapItem(
                title="Fix inconsistent phone numbers across the site",
                suggested_path=None,
                why=(
                    f"Found {len(nap.distinct_phone_numbers)} different phone numbers across "
                    "crawled pages. Inconsistent NAP confuses Google's local-ranking signals and "
                    "callers who see a different number than the one they searched for."
                ),
                priority="high",
            )
        )
    if nap.pages_missing_known_phone:
        items.append(
            ContentGapItem(
                title="Add the business phone number to every page",
                suggested_path=None,
                why=(
                    f"{len(nap.pages_missing_known_phone)} crawled page(s) don't show the known "
                    "phone number anywhere in the visible text."
                ),
                priority="medium",
            )
        )
    if not click_to_call.complete and click_to_call.pages_checked:
        items.append(
            ContentGapItem(
                title="Add a click-to-call link on every page",
                suggested_path=None,
                why=(
                    f"{len(click_to_call.pages_missing)} of {click_to_call.pages_checked} crawled "
                    "page(s) have no tel: link - most local searches happen on a phone, and every "
                    "page is a potential landing page."
                ),
                priority="high",
            )
        )
    if not schema.has_review_schema_anywhere:
        items.append(
            ContentGapItem(
                title="Add Review/AggregateRating schema",
                suggested_path=None,
                why=(
                    "No page declares Review or AggregateRating structured data, so star ratings "
                    "can't show up directly in Google search results even if real reviews exist."
                ),
                priority="medium",
            )
        )
    if not schema.has_faq_schema_anywhere:
        items.append(
            ContentGapItem(
                title="Add FAQPage schema to a services or FAQ page",
                suggested_path=None,
                why=(
                    "No page declares FAQPage structured data - an easy way to win extra space "
                    "in search results with expandable question-and-answer snippets."
                ),
                priority="low",
            )
        )
    if not has_gbp_link:
        items.append(
            ContentGapItem(
                title="Link to the Google Business Profile",
                suggested_path=None,
                why=(
                    "No page links to a Google Business Profile (g.page/business.google.com). "
                    "This is free, high-trust real estate connecting the site to reviews, hours, "
                    "and the map pin in search."
                ),
                priority="medium",
            )
        )
    if contact_page is not None and not has_contact_page_map:
        items.append(
            ContentGapItem(
                title=f"Embed a map on {contact_page.url}",
                suggested_path=None,
                why=(
                    'The contact page has no embedded map - "how do I get there" is one of the '
                    "first things a local visitor looks for."
                ),
                priority="medium",
            )
        )
    elif contact_page is None:
        items.append(
            ContentGapItem(
                title="Create a dedicated /contact page",
                suggested_path="/contact",
                why="No page could be identified as a contact page during the crawl.",
                priority="medium",
            )
        )

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda item: priority_rank[item.priority])
    return tuple(items)


def analyze_content_gaps(
    pages: Sequence[CrawledPage],
    *,
    business: Business | None = None,
    services: list[str] | None = None,
    areas: list[str] | None = None,
) -> ContentGapPlan:
    """Build a prioritized local-content plan from a set of crawled pages.

    Args:
        pages: Every page to consider - ideally a full ``--site`` crawl;
            a single homepage snapshot also works, just with less signal.
        business: Known-good NAP facts, used for the NAP-consistency check.
        services: Service names to check for a dedicated page. When omitted,
            candidates are inferred from nav links and H2/H3 headings.
        areas: City/service-area names to check for a dedicated page.
    """
    inferred = False
    service_queries = list(services) if services else []
    if not service_queries:
        service_queries = infer_services(pages)
        inferred = True

    service_statuses = tuple(_find_dedicated_page(s, pages) for s in service_queries)
    area_statuses = tuple(_find_dedicated_page(a, pages) for a in (areas or []))

    nap = _nap_consistency(pages, business)
    click_to_call = _click_to_call_coverage(pages)
    schema = _schema_coverage(pages)
    has_gbp_link = any(p.has_gbp_link for p in pages if p.ok)
    contact_page = _find_contact_page(pages)
    has_contact_page_map = bool(contact_page and contact_page.has_map_embed)

    plan = _build_plan(
        service_statuses,
        area_statuses,
        nap,
        click_to_call,
        schema,
        has_gbp_link,
        contact_page,
        has_contact_page_map,
    )

    return ContentGapPlan(
        services=service_statuses,
        areas=area_statuses,
        inferred_services=inferred,
        nap=nap,
        click_to_call=click_to_call,
        schema=schema,
        has_gbp_link=has_gbp_link,
        has_contact_page=contact_page is not None,
        has_contact_page_map=has_contact_page_map,
        plan=plan,
    )
