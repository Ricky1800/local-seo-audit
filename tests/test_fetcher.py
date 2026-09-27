from __future__ import annotations

import httpx
import respx

from local_seo_audit.fetcher import USER_AGENT, fetch, new_client


def test_successful_fetch(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<html>hi</html>")
    )
    with new_client() as client:
        result = fetch(client, "https://example.com/")

    assert result.ok is True
    assert result.status_code == 200
    assert result.text == "<html>hi</html>"
    assert result.final_url == "https://example.com/"
    assert result.error is None


def test_sends_user_agent(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("https://example.com/").mock(return_value=httpx.Response(200, text="ok"))
    with new_client() as client:
        fetch(client, "https://example.com/")

    assert route.calls.last.request.headers["User-Agent"] == USER_AGENT
    assert "local-seo-audit" in USER_AGENT


def test_follows_redirects(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("http://example.com/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://example.com/"})
    )
    respx_mock.get("https://example.com/").mock(return_value=httpx.Response(200, text="secure"))

    with new_client() as client:
        result = fetch(client, "http://example.com/")

    assert result.final_url == "https://example.com/"
    assert result.redirected is True
    assert result.history_urls == ["http://example.com/"]


def test_4xx_status_is_not_ok(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://example.com/missing").mock(return_value=httpx.Response(404, text=""))
    with new_client() as client:
        result = fetch(client, "https://example.com/missing")

    assert result.status_code == 404
    assert result.ok is False


def test_network_error_is_captured_not_raised(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://unreachable.example.com/").mock(side_effect=httpx.ConnectError("boom"))
    with new_client() as client:
        result = fetch(client, "https://unreachable.example.com/")

    assert result.ok is False
    assert result.status_code == 0
    assert result.error is not None
    assert "ConnectError" in result.error


def test_byte_size(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://example.com/").mock(return_value=httpx.Response(200, text="hello"))
    with new_client() as client:
        result = fetch(client, "https://example.com/")

    assert result.byte_size == len(b"hello")
