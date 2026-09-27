"""LocalBusiness structured data (JSON-LD): the machine-readable NAP."""

from __future__ import annotations

import json
import re
from typing import Any

from local_seo_audit.checks.base import AuditContext, Check
from local_seo_audit.models import CheckResult, Severity, Status
from local_seo_audit.utils import normalize_phone

#: Common schema.org LocalBusiness subtypes, in addition to any type whose name
#: contains "Business" (which covers most of the rest, e.g. HomeAndConstructionBusiness).
KNOWN_LOCAL_BUSINESS_TYPES = {
    "LocalBusiness",
    "Restaurant",
    "CafeOrCoffeeShop",
    "BarOrPub",
    "Bakery",
    "Store",
    "ProfessionalService",
    "Plumber",
    "Electrician",
    "HVACBusiness",
    "Locksmith",
    "MovingCompany",
    "RoofingContractor",
    "GeneralContractor",
    "HousePainter",
    "Dentist",
    "Physician",
    "LegalService",
    "Attorney",
    "AutoRepair",
    "AutoDealer",
    "BeautySalon",
    "HairSalon",
    "DaySpa",
    "NailSalon",
    "Florist",
    "ChildCare",
    "VeterinaryCare",
    "RealEstateAgent",
    "InsuranceAgency",
    "AccountingService",
    "GymOrHealthClub",
    "SelfStorage",
    "LandscapingBusiness",
}

REQUIRED_FIELDS = ("name", "address", "telephone", "openingHours", "geo")


def _is_local_business_type(type_value: Any) -> bool:
    candidates = type_value if isinstance(type_value, list) else [type_value]
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        if candidate in KNOWN_LOCAL_BUSINESS_TYPES or "Business" in candidate:
            return True
    return False


def _flatten_nodes(data: Any) -> list[dict[str, Any]]:
    """Pull out every JSON-LD node, following ``@graph`` and top-level lists."""
    nodes: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            nodes.extend(_flatten_nodes(item))
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            nodes.extend(_flatten_nodes(data["@graph"]))
        else:
            nodes.append(data)
    return nodes


def _address_to_text(address: Any) -> str:
    if isinstance(address, str):
        return address
    if isinstance(address, dict):
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("postalCode"),
        ]
        return ", ".join(str(p) for p in parts if p)
    return ""


def _has_geo(node: dict[str, Any]) -> bool:
    geo = node.get("geo")
    if not isinstance(geo, dict):
        return False
    return "latitude" in geo and "longitude" in geo


def _has_opening_hours(node: dict[str, Any]) -> bool:
    if node.get("openingHours"):
        return True
    spec = node.get("openingHoursSpecification")
    return bool(spec)


def _present_fields(node: dict[str, Any]) -> dict[str, bool]:
    return {
        "name": bool(node.get("name")),
        "address": bool(_address_to_text(node.get("address"))),
        "telephone": bool(node.get("telephone")),
        "openingHours": _has_opening_hours(node),
        "geo": _has_geo(node),
    }


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


class JsonLdLocalBusinessCheck(Check):
    id = "json_ld_local_business"
    title = "LocalBusiness structured data (JSON-LD)"
    weight = 12
    severity = Severity.HIGH

    def run(self, ctx: AuditContext) -> CheckResult:
        if not ctx.primary.ok:
            return self.skip("Skipped: homepage could not be fetched.")

        fix = (
            'Add a <script type="application/ld+json"> block describing the business as a '
            'LocalBusiness (or a specific subtype like "Plumber"), including name, address, '
            "telephone, openingHours, and geo coordinates. This is what lets Google show rich "
            "results (star ratings, hours, map pin) directly in search."
        )

        scripts = ctx.soup.find_all("script", attrs={"type": "application/ld+json"})
        if not scripts:
            return self.make(Status.FAIL, "No JSON-LD structured data found on the page.", fix)

        parse_errors = 0
        candidate_nodes: list[dict[str, Any]] = []
        for script in scripts:
            raw = script.string or script.get_text()
            if not raw or not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            candidate_nodes.extend(_flatten_nodes(parsed))

        business_nodes = [n for n in candidate_nodes if _is_local_business_type(n.get("@type"))]

        if not business_nodes:
            if parse_errors and not candidate_nodes:
                return self.make(
                    Status.FAIL,
                    f"Found {len(scripts)} JSON-LD block(s) but none were valid JSON.",
                    fix,
                )
            return self.make(
                Status.FAIL,
                f"Found {len(candidate_nodes)} JSON-LD node(s), but none declare a LocalBusiness "
                "(or subtype) @type.",
                fix,
            )

        node = business_nodes[0]
        present = _present_fields(node)
        missing = [f for f in REQUIRED_FIELDS if not present[f]]

        nap_notes: list[str] = []
        nap_mismatch = False
        biz = ctx.business
        if biz.name and node.get("name"):
            match = _normalize_for_match(str(biz.name)) in _normalize_for_match(str(node["name"]))
            nap_notes.append("name matches" if match else "name does NOT match the provided NAP")
            nap_mismatch = nap_mismatch or not match
        if biz.phone and node.get("telephone"):
            match = normalize_phone(str(node["telephone"])) == normalize_phone(biz.phone)
            nap_notes.append("phone matches" if match else "phone does NOT match the provided NAP")
            nap_mismatch = nap_mismatch or not match
        if biz.address:
            addr_text = _address_to_text(node.get("address"))
            if addr_text:
                normalized_addr = _normalize_for_match(addr_text)
                normalized_given = _normalize_for_match(biz.address)
                match = normalized_given in normalized_addr or normalized_addr in normalized_given
                nap_notes.append("address matches" if match else "address does NOT match")
                nap_mismatch = nap_mismatch or not match

        type_value = node.get("@type")
        evidence_parts = [f"Found LocalBusiness JSON-LD (@type: {type_value})."]
        if missing:
            evidence_parts.append(f"Missing fields: {', '.join(missing)}.")
        else:
            evidence_parts.append("All of name/address/telephone/openingHours/geo are present.")
        if nap_notes:
            evidence_parts.append("NAP comparison: " + "; ".join(nap_notes) + ".")

        if not missing and not nap_mismatch:
            status = Status.PASS
        elif len(missing) >= 4:
            status = Status.FAIL
        else:
            status = Status.WARN

        return self.make(status, " ".join(evidence_parts), fix)
