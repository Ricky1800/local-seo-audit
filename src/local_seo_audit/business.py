"""The business "ground truth" (NAP) an audit is checked against."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Business:
    """Known-good facts about the business, supplied by its owner.

    Every field is optional: the more you provide, the more checks (title
    relevance, JSON-LD NAP matching, on-page NAP visibility) can actually
    verify instead of merely noting that *something* is present.
    """

    name: str | None = None
    phone: str | None = None
    city: str | None = None
    address: str | None = None

    def has_any(self) -> bool:
        """Whether any business fact was supplied at all."""
        return any((self.name, self.phone, self.city, self.address))
