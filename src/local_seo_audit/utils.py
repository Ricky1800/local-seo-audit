"""Small, dependency-free helpers used across checks and renderers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_DIGITS_RE = re.compile(r"\d+")


def normalize_phone(raw: str) -> str:
    """Reduce a phone number to bare digits, dropping a leading country code 1.

    ``"(609) 555-0100"``, ``"609-555-0100"``, ``"609.555.0100"`` and
    ``"+1 609 555 0100"`` all normalize to ``"6095550100"`` so they can be
    compared regardless of how each was formatted.
    """
    digits = "".join(_DIGITS_RE.findall(raw))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def phone_variants_in_text(phone: str, text: str) -> bool:
    """Whether ``phone`` (in any common format) appears somewhere in ``text``."""
    needle = normalize_phone(phone)
    if not needle:
        return False
    haystack = normalize_phone(text)
    # normalize_phone on the whole page text collapses all digits together,
    # which risks false positives/negatives across separate numbers, so also
    # scan digit runs token by token as a stricter corroborating check.
    if needle in haystack:
        for token in re.findall(r"[\d()+.\-\s]{7,}", text):
            if normalize_phone(token) == needle:
                return True
    return False


def same_host(url_a: str, url_b: str) -> bool:
    """Whether two URLs share a scheme-less, www-insensitive host."""
    a = urlparse(url_a).netloc.lower().removeprefix("www.")
    b = urlparse(url_b).netloc.lower().removeprefix("www.")
    return a == b and a != ""


def ensure_scheme(url: str) -> str:
    """Default a bare host/URL (no ``http(s)://``) to ``https://``."""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", url):
        return f"https://{url}"
    return url


def human_bytes(num_bytes: int) -> str:
    """Render a byte count as a short human-readable string."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"  # pragma: no cover - unreachable for real pages
