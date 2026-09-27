from __future__ import annotations

from local_seo_audit.utils import (
    ensure_scheme,
    human_bytes,
    normalize_phone,
    phone_variants_in_text,
    same_host,
)


class TestNormalizePhone:
    def test_strips_formatting(self) -> None:
        assert normalize_phone("(609) 555-0100") == "6095550100"
        assert normalize_phone("609-555-0100") == "6095550100"
        assert normalize_phone("609.555.0100") == "6095550100"

    def test_drops_leading_country_code(self) -> None:
        assert normalize_phone("+1 609 555 0100") == "6095550100"
        assert normalize_phone("1-609-555-0100") == "6095550100"

    def test_empty_input(self) -> None:
        assert normalize_phone("") == ""
        assert normalize_phone("call us today") == ""


class TestPhoneVariantsInText:
    def test_matches_differently_formatted_number(self) -> None:
        text = "Reach Joe's Plumbing at (609) 555-0100 any time."
        assert phone_variants_in_text("609-555-0100", text) is True

    def test_no_match(self) -> None:
        text = "Reach us at (609) 555-9999."
        assert phone_variants_in_text("609-555-0100", text) is False

    def test_empty_phone(self) -> None:
        assert phone_variants_in_text("", "609-555-0100") is False


class TestSameHost:
    def test_same_host_ignores_www(self) -> None:
        assert same_host("https://www.example.com/a", "https://example.com/b") is True

    def test_different_host(self) -> None:
        assert same_host("https://example.com", "https://other.com") is False

    def test_empty_host(self) -> None:
        assert same_host("not-a-url", "also-not-a-url") is False


class TestEnsureScheme:
    def test_adds_https_when_missing(self) -> None:
        assert ensure_scheme("example.com") == "https://example.com"

    def test_leaves_existing_scheme(self) -> None:
        assert ensure_scheme("http://example.com") == "http://example.com"
        assert ensure_scheme("https://example.com") == "https://example.com"


class TestHumanBytes:
    def test_bytes(self) -> None:
        assert human_bytes(500) == "500 B"

    def test_kilobytes(self) -> None:
        assert human_bytes(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        assert human_bytes(5 * 1024 * 1024) == "5.0 MB"
