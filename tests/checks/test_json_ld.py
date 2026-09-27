from __future__ import annotations

from local_seo_audit.business import Business
from local_seo_audit.checks.json_ld import JsonLdLocalBusinessCheck
from local_seo_audit.models import Status
from tests.conftest import MakeCtx, MakeFetchResult

FULL_LOCAL_BUSINESS = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Plumber",
  "name": "Joe's Plumbing",
  "telephone": "+1-609-555-0100",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "Princeton",
    "addressRegion": "NJ",
    "postalCode": "08540"
  },
  "openingHours": "Mo-Su 00:00-23:59",
  "geo": {"@type": "GeoCoordinates", "latitude": 40.34, "longitude": -74.65}
}
</script>
"""


def test_pass_full_matching_nap(make_ctx: MakeCtx) -> None:
    ctx = make_ctx(
        FULL_LOCAL_BUSINESS,
        business=Business(
            name="Joe's Plumbing", phone="609-555-0100", address="123 Main St, Princeton"
        ),
    )
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.PASS


def test_fail_no_json_ld_at_all(make_ctx: MakeCtx) -> None:
    ctx = make_ctx("<html></html>")
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_invalid_json(make_ctx: MakeCtx) -> None:
    ctx = make_ctx('<script type="application/ld+json">{not valid json</script>')
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.FAIL


def test_fail_wrong_type(make_ctx: MakeCtx) -> None:
    html = """
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Person", "name": "Someone"}
    </script>
    """
    ctx = make_ctx(html)
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_missing_some_fields(make_ctx: MakeCtx) -> None:
    html = """
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Dentist", "name": "Bright Smile",
     "telephone": "609-555-0199"}
    </script>
    """
    ctx = make_ctx(html)
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.WARN
    assert "address" in result.evidence


def test_fail_missing_most_fields(make_ctx: MakeCtx) -> None:
    html = """
    <script type="application/ld+json">
    {"@type": "LocalBusiness", "name": "Bright Smile"}
    </script>
    """
    ctx = make_ctx(html)
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.FAIL


def test_warn_nap_mismatch(make_ctx: MakeCtx) -> None:
    ctx = make_ctx(FULL_LOCAL_BUSINESS, business=Business(phone="609-555-9999"))
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.WARN
    assert "does NOT match" in result.evidence


def test_supports_at_graph(make_ctx: MakeCtx) -> None:
    html = """
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [
      {"@type": "WebSite", "name": "irrelevant"},
      {"@type": "LocalBusiness", "name": "Joe's Plumbing", "telephone": "609-555-0100",
       "address": "123 Main St, Princeton, NJ", "openingHours": "Mo-Su 00:00-23:59",
       "geo": {"latitude": 1, "longitude": 2}}
    ]}
    </script>
    """
    ctx = make_ctx(html)
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.PASS


def test_supports_top_level_array(make_ctx: MakeCtx) -> None:
    html = """
    <script type="application/ld+json">
    [{"@type": "LocalBusiness", "name": "Joe's Plumbing", "telephone": "609-555-0100",
      "address": "123 Main St", "openingHours": "Mo-Su 00:00-23:59",
      "geo": {"latitude": 1, "longitude": 2}}]
    </script>
    """
    ctx = make_ctx(html)
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.PASS


def test_skip_when_unreachable(make_ctx: MakeCtx, make_fetch_result: MakeFetchResult) -> None:
    ctx = make_ctx("", primary=make_fetch_result("https://example.com/", "", status_code=500))
    result = JsonLdLocalBusinessCheck().run(ctx)
    assert result.status is Status.SKIP
