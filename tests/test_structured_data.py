"""Unit tests for the shared JSON-LD helpers used by compare and content-gap analysis."""

from __future__ import annotations

from bs4 import BeautifulSoup

from local_seo_audit.structured_data import (
    extract_json_ld_nodes,
    extract_schema_types,
    flatten_json_ld_nodes,
    has_schema_type,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_flatten_follows_graph_and_lists() -> None:
    data = {"@graph": [{"@type": "LocalBusiness"}, {"@type": "WebSite"}]}
    nodes = flatten_json_ld_nodes(data)
    assert len(nodes) == 2
    assert [n["@type"] for n in nodes] == ["LocalBusiness", "WebSite"]

    assert flatten_json_ld_nodes([{"@type": "A"}, {"@type": "B"}]) == [
        {"@type": "A"},
        {"@type": "B"},
    ]
    assert flatten_json_ld_nodes({"@type": "Solo"}) == [{"@type": "Solo"}]


def test_extract_json_ld_nodes_ignores_invalid_and_empty_blocks() -> None:
    html = """
    <script type="application/ld+json">not json</script>
    <script type="application/ld+json"></script>
    <script type="application/ld+json">{"@type": "LocalBusiness", "name": "Joe"}</script>
    """
    nodes = extract_json_ld_nodes(_soup(html))
    assert len(nodes) == 1
    assert nodes[0]["name"] == "Joe"


def test_extract_schema_types_finds_nested_property_types() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "Plumber",
      "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.9"},
      "review": [{"@type": "Review"}, {"@type": "Review"}]
    }
    </script>
    """
    types = extract_schema_types(_soup(html))
    assert types == {"Plumber", "AggregateRating", "Review"}


def test_extract_schema_types_handles_list_of_types() -> None:
    html = '<script type="application/ld+json">{"@type": ["LocalBusiness", "Store"]}</script>'
    assert extract_schema_types(_soup(html)) == {"LocalBusiness", "Store"}


def test_extract_schema_types_returns_empty_set_with_no_json_ld() -> None:
    assert extract_schema_types(_soup("<html><body>nothing here</body></html>")) == set()


def test_has_schema_type_is_case_insensitive() -> None:
    html = '<script type="application/ld+json">{"@type": "FAQPage"}</script>'
    soup = _soup(html)
    assert has_schema_type(soup, "faqpage")
    assert has_schema_type(soup, "FAQPage", "AggregateRating")
    assert not has_schema_type(soup, "Review")
