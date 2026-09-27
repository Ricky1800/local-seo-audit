"""Shared JSON-LD parsing helpers, used by competitor-compare and content-gap analysis.

Kept separate from ``checks/json_ld.py`` (which only cares about the first
LocalBusiness-shaped node) because these two features need *every* node and
*every* ``@type`` on the page, not just the business listing.
"""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup


def flatten_json_ld_nodes(data: Any) -> list[dict[str, Any]]:
    """Pull out every JSON-LD node, following ``@graph`` and top-level lists."""
    nodes: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            nodes.extend(flatten_json_ld_nodes(item))
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            nodes.extend(flatten_json_ld_nodes(data["@graph"]))
        else:
            nodes.append(data)
    return nodes


def extract_json_ld_nodes(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Every JSON-LD node found in ``<script type="application/ld+json">`` blocks."""
    nodes: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes.extend(flatten_json_ld_nodes(parsed))
    return nodes


def _walk_types(node: Any, out: set[str]) -> None:
    """Recursively collect every ``@type`` in ``node``, including nested property objects.

    Real-world markup very often nests a typed object (``aggregateRating``,
    ``review``, ``makesOffer``, ...) as a *property* of the main node rather than
    as a sibling in ``@graph``, so a shallow top-level scan would miss it.
    """
    if isinstance(node, dict):
        type_value = node.get("@type")
        if isinstance(type_value, str):
            out.add(type_value)
        elif isinstance(type_value, list):
            out.update(t for t in type_value if isinstance(t, str))
        for value in node.values():
            _walk_types(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk_types(item, out)


def extract_schema_types(soup: BeautifulSoup) -> set[str]:
    """Every distinct ``@type`` value declared anywhere in the page's JSON-LD.

    Unlike :func:`extract_json_ld_nodes` (which only follows ``@graph``/top-level
    lists), this recurses into every nested object so a type nested inside a
    property - e.g. an ``AggregateRating`` under a ``LocalBusiness``'s
    ``aggregateRating`` field - is still found.
    """
    types: set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        _walk_types(parsed, types)
    return types


def has_schema_type(soup: BeautifulSoup, *candidates: str) -> bool:
    """Whether any of ``candidates`` (case-insensitive) appears among the page's ``@type``s."""
    lowered_candidates = {c.lower() for c in candidates}
    return any(t.lower() in lowered_candidates for t in extract_schema_types(soup))
