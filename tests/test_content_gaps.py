"""Unit tests for local content-gap analysis: service/area pages, NAP, schema, and the plan."""

from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.content_gaps import analyze_content_gaps, infer_services
from local_seo_audit.crawler import CrawledPage, Heading


def _page(
    url: str,
    *,
    title: str | None = None,
    headings: tuple[Heading, ...] = (),
    page_text: str = "",
    phone_candidates: tuple[str, ...] = (),
    has_tel_link: bool = True,
    has_review_schema: bool = False,
    has_faq_schema: bool = False,
    has_map_embed: bool = False,
    has_gbp_link: bool = False,
    nav_link_texts: tuple[str, ...] = (),
    ok: bool = True,
) -> CrawledPage:
    return CrawledPage(
        url=url,
        status_code=200 if ok else 404,
        ok=ok,
        error=None,
        redirected=False,
        history_urls=(),
        title=title,
        meta_description=None,
        h1_count=1,
        headings=headings,
        word_count=len(page_text.split()),
        canonical=None,
        noindex=False,
        internal_links=frozenset(),
        depth=0,
        in_sitemap=True,
        has_tel_link=has_tel_link,
        has_json_ld=has_review_schema or has_faq_schema,
        page_text=page_text,
        phone_candidates=phone_candidates,
        has_review_schema=has_review_schema,
        has_faq_schema=has_faq_schema,
        has_map_embed=has_map_embed,
        has_gbp_link=has_gbp_link,
        nav_link_texts=nav_link_texts,
    )


def test_service_page_found_and_missing() -> None:
    pages = [
        _page(
            "https://example.com/",
            title="Joe's Plumbing | Princeton",
            headings=(Heading(1, "Princeton Plumber"),),
        ),
        _page(
            "https://example.com/water-heater-repair",
            title="Water Heater Repair | Joe's Plumbing",
            headings=(Heading(1, "Water Heater Repair"),),
        ),
    ]
    plan = analyze_content_gaps(pages, services=["water heater repair", "drain cleaning"])

    found = {s.query: s for s in plan.services}
    assert found["water heater repair"].found
    assert found["water heater repair"].matched_url == "https://example.com/water-heater-repair"
    assert not found["drain cleaning"].found
    assert not plan.inferred_services


def test_services_are_inferred_when_not_given() -> None:
    pages = [
        _page(
            "https://example.com/",
            title="Home",
            headings=(
                Heading(1, "Welcome"),
                Heading(2, "Drain Cleaning"),
                Heading(2, "Water Heater Installation"),
            ),
            nav_link_texts=("Home", "About", "Contact"),
        )
    ]
    plan = analyze_content_gaps(pages)

    assert plan.inferred_services
    queries = {s.query for s in plan.services}
    assert "Drain Cleaning" in queries
    assert "Water Heater Installation" in queries
    assert "Home" not in queries  # stopword, filtered out


def test_infer_services_ignores_non_ok_pages() -> None:
    pages = [_page("https://example.com/broken", headings=(Heading(2, "Ignored"),), ok=False)]
    assert infer_services(pages) == []


def test_area_pages_are_checked_when_given() -> None:
    pages = [
        _page("https://example.com/", title="Home"),
        _page("https://example.com/princeton-nj", title="Serving Princeton, NJ"),
    ]
    plan = analyze_content_gaps(pages, areas=["Princeton", "Plainsboro"])

    statuses = {a.query: a for a in plan.areas}
    assert statuses["Princeton"].found
    assert not statuses["Plainsboro"].found


def test_nap_consistency_flags_conflicting_phone_numbers() -> None:
    pages = [
        _page(
            "https://example.com/", page_text="Call 609-555-0100", phone_candidates=("6095550100",)
        ),
        _page(
            "https://example.com/about",
            page_text="Call 609-555-9999",
            phone_candidates=("6095559999",),
        ),
    ]
    plan = analyze_content_gaps(pages)

    assert not plan.nap.phone_consistent
    assert len(plan.nap.distinct_phone_numbers) == 2
    assert any("inconsistent phone" in item.title.lower() for item in plan.plan)


def test_nap_consistency_uses_known_business_phone_as_canonical() -> None:
    pages = [
        _page("https://example.com/", page_text="Joe's Plumbing", phone_candidates=("6095550100",)),
        _page("https://example.com/about", page_text="About Joe's Plumbing", phone_candidates=()),
    ]
    business = Business(name="Joe's Plumbing", phone="609-555-0100")
    plan = analyze_content_gaps(pages, business=business)

    assert plan.nap.phone_consistent
    assert "https://example.com/about" in plan.nap.pages_missing_known_phone
    assert "https://example.com/about" not in plan.nap.pages_missing_known_name


def test_click_to_call_coverage_flags_pages_without_tel_link() -> None:
    pages = [
        _page("https://example.com/", has_tel_link=True),
        _page("https://example.com/blog/post-1", has_tel_link=False),
    ]
    plan = analyze_content_gaps(pages)

    assert not plan.click_to_call.complete
    assert "https://example.com/blog/post-1" in plan.click_to_call.pages_missing
    assert any("click-to-call" in item.title.lower() for item in plan.plan)


def test_schema_and_gbp_and_contact_map_checks() -> None:
    pages = [
        _page("https://example.com/", has_gbp_link=False),
        _page("https://example.com/contact", title="Contact Us", has_map_embed=False),
    ]
    plan = analyze_content_gaps(pages)

    assert not plan.schema.has_review_schema_anywhere
    assert not plan.schema.has_faq_schema_anywhere
    assert not plan.has_gbp_link
    assert plan.has_contact_page
    assert not plan.has_contact_page_map
    titles = [item.title for item in plan.plan]
    assert any("review/aggregaterating schema" in t.lower() for t in titles)
    assert any("faqpage schema" in t.lower() for t in titles)
    assert any("google business profile" in t.lower() for t in titles)
    assert any("embed a map" in t.lower() for t in titles)


def test_missing_contact_page_suggests_creating_one() -> None:
    pages = [_page("https://example.com/", title="Home")]
    plan = analyze_content_gaps(pages)

    assert not plan.has_contact_page
    assert any(item.suggested_path == "/contact" for item in plan.plan)


def test_good_site_has_a_clean_plan() -> None:
    pages = [
        _page(
            "https://example.com/",
            title="Joe's Plumbing",
            has_tel_link=True,
            has_review_schema=True,
            has_faq_schema=True,
            has_gbp_link=True,
        ),
        _page(
            "https://example.com/contact",
            title="Contact",
            has_tel_link=True,
            has_map_embed=True,
        ),
    ]
    plan = analyze_content_gaps(pages, services=[], areas=[])

    # No services/areas requested and none inferable from these bare pages -> no gaps for them.
    assert plan.schema.has_review_schema_anywhere
    assert plan.schema.has_faq_schema_anywhere
    assert plan.has_gbp_link
    assert plan.has_contact_page_map
    assert plan.click_to_call.complete


def test_service_and_area_gap_produces_combined_landing_page_suggestion() -> None:
    pages = [_page("https://example.com/", title="Home")]
    plan = analyze_content_gaps(pages, services=["water heater repair"], areas=["Princeton"])

    combined = next(
        (i for i in plan.plan if i.suggested_path == "/water-heater-repair-princeton"), None
    )
    assert combined is not None
    assert combined.priority == "high"
    assert "water heater repair" in combined.why
    assert "Princeton" in combined.why


def test_plan_is_sorted_by_priority() -> None:
    pages = [_page("https://example.com/", title="Home", has_tel_link=False)]
    plan = analyze_content_gaps(pages, services=["missing service"])

    priorities = [item.priority for item in plan.plan]
    rank = {"high": 0, "medium": 1, "low": 2}
    assert priorities == sorted(priorities, key=lambda p: rank[p])
