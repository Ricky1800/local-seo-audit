"""Unit tests for the PageSpeed Insights (Core Web Vitals) client.

Every test mocks the PSI endpoint with respx; none of them touch the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from local_seo_audit.vitals import PSI_ENDPOINT, fetch_core_web_vitals

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "psi"


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return data


def test_fetch_reports_field_and_lab_data_for_mobile(respx_mock: respx.MockRouter) -> None:
    mobile_payload = _load("mobile_good.json")
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json=mobile_payload)
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json=_load("desktop_poor_no_field.json"))
    )

    result = fetch_core_web_vitals("https://www.joesplumbingnj.com/")

    assert result.mobile is not None
    assert result.mobile.ok
    assert result.mobile.field_data is not None
    assert result.mobile.field_data.has_any()
    assert result.mobile.field_data.lcp is not None
    assert result.mobile.field_data.lcp.value == 2100
    assert result.mobile.field_data.lcp.rating == "good"
    assert result.mobile.field_data.cls is not None
    assert result.mobile.field_data.cls.value == pytest.approx(0.05)
    assert result.mobile.lab_data is not None
    assert result.mobile.lab_data.performance_score == 94.0
    assert result.mobile.lab_data.lcp is not None
    assert result.mobile.lab_data.lcp.rating == "good"
    assert len(result.mobile.lab_data.opportunities) == 2
    assert result.mobile.lab_data.opportunities[0] == "Eliminate render-blocking resources"


def test_fetch_handles_missing_field_data_and_poor_lab_scores(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json=_load("desktop_poor_no_field.json"))
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json=_load("desktop_poor_no_field.json"))
    )

    result = fetch_core_web_vitals("https://slow.example/")

    assert result.desktop is not None
    assert result.desktop.field_data is None
    assert result.desktop.lab_data is not None
    assert result.desktop.lab_data.performance_score == 31.0
    assert result.desktop.lab_data.lcp is not None
    assert result.desktop.lab_data.lcp.rating == "poor"
    assert result.desktop.lab_data.tbt is not None
    assert result.desktop.lab_data.tbt.rating == "poor"


def test_quota_error_becomes_a_readable_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(429, json=_load("quota_error.json"))
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(429, json=_load("quota_error.json"))
    )

    result = fetch_core_web_vitals("https://example.com/")

    assert result.mobile is not None
    assert not result.mobile.ok
    assert "quota" in (result.mobile.error or "").lower()


def test_generic_http_error_includes_message(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(400, json={"error": {"code": 400, "message": "Invalid URL"}})
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(400, json={"error": {"code": 400, "message": "Invalid URL"}})
    )

    result = fetch_core_web_vitals("not-a-real-url")

    assert result.mobile is not None
    assert result.mobile.error is not None
    assert "400" in result.mobile.error
    assert "Invalid URL" in result.mobile.error


def test_timeout_is_reported_gracefully(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    result = fetch_core_web_vitals("https://slow-server.example/")

    assert result.mobile is not None
    assert result.mobile.error is not None
    assert "timed out" in result.mobile.error.lower()


def test_unparseable_json_is_reported_gracefully(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, text="not json")
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, text="not json")
    )

    result = fetch_core_web_vitals("https://example.com/")

    assert result.mobile is not None
    assert result.mobile.error is not None


def test_no_usable_data_is_reported_as_error(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json={"id": "https://example.com/"})
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json={"id": "https://example.com/"})
    )

    result = fetch_core_web_vitals("https://example.com/")

    assert result.mobile is not None
    assert result.mobile.error is not None


def test_api_key_is_forwarded_as_query_param(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PSI_API_KEY", raising=False)
    route = respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json=_load("mobile_good.json"))
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json=_load("desktop_poor_no_field.json"))
    )

    fetch_core_web_vitals("https://example.com/", api_key="my-test-key")

    assert route.called
    request = route.calls.last.request
    assert "key=my-test-key" in str(request.url)


def test_env_var_supplies_key_when_not_passed_explicitly(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PSI_API_KEY", "env-key")
    route = respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json=_load("mobile_good.json"))
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json=_load("desktop_poor_no_field.json"))
    )

    fetch_core_web_vitals("https://example.com/")

    assert "key=env-key" in str(route.calls.last.request.url)


def test_single_strategy_can_be_requested(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json=_load("mobile_good.json"))
    )

    result = fetch_core_web_vitals("https://example.com/", strategies=("mobile",))

    assert result.mobile is not None
    assert result.desktop is None
