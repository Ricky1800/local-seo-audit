from __future__ import annotations

from local_seo_audit.business import Business


def test_has_any_false_when_empty() -> None:
    assert Business().has_any() is False


def test_has_any_true_with_one_field() -> None:
    assert Business(phone="609-555-0100").has_any() is True


def test_has_any_true_with_all_fields() -> None:
    biz = Business(
        name="Joe's Plumbing", phone="609-555-0100", city="Princeton", address="123 Main St"
    )
    assert biz.has_any() is True
