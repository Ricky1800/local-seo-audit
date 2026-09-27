from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from local_seo_audit import __version__
from local_seo_audit.cli import main


def _mock_simple_site(respx_mock: respx.MockRouter, origin: str, html: str) -> None:
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    http_origin = "http://" + origin.removeprefix("https://")
    respx_mock.get(f"{http_origin}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_missing_url_is_usage_error() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_text_output_to_stdout(
    respx_mock: respx.MockRouter, capsys: pytest.CaptureFixture[str], good_site_html: str
) -> None:
    _mock_simple_site(respx_mock, "https://www.joesplumbingnj.com", good_site_html)

    exit_code = main(
        [
            "https://www.joesplumbingnj.com/",
            "--name",
            "Joe's Plumbing",
            "--city",
            "Princeton",
        ]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Local SEO Audit" in out
    assert "Score:" in out


def test_json_output_to_file(
    respx_mock: respx.MockRouter, tmp_path: Path, good_site_html: str
) -> None:
    _mock_simple_site(respx_mock, "https://www.joesplumbingnj.com", good_site_html)
    out_file = tmp_path / "report.json"

    exit_code = main(
        [
            "https://www.joesplumbingnj.com/",
            "--format",
            "json",
            "--out",
            str(out_file),
        ]
    )

    assert exit_code == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["url"] == "https://www.joesplumbingnj.com/"


def test_html_output_to_file(
    respx_mock: respx.MockRouter, tmp_path: Path, good_site_html: str
) -> None:
    _mock_simple_site(respx_mock, "https://www.joesplumbingnj.com", good_site_html)
    out_file = tmp_path / "report.html"

    exit_code = main(
        ["https://www.joesplumbingnj.com/", "--format", "html", "--out", str(out_file)]
    )

    assert exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>")


def test_crawl_flag_is_parsed(respx_mock: respx.MockRouter, good_site_html: str) -> None:
    _mock_simple_site(respx_mock, "https://www.joesplumbingnj.com", good_site_html)

    exit_code = main(["https://www.joesplumbingnj.com/", "--crawl", "3", "--format", "json"])

    assert exit_code == 0


def test_vitals_flag_is_parsed(respx_mock: respx.MockRouter, good_site_html: str) -> None:
    from local_seo_audit.vitals import PSI_ENDPOINT

    _mock_simple_site(respx_mock, "https://www.joesplumbingnj.com", good_site_html)
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json={"id": "x"})
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json={"id": "x"})
    )

    exit_code = main(["https://www.joesplumbingnj.com/", "--vitals", "--format", "json"])

    assert exit_code == 0


def test_site_and_max_pages_flags_are_parsed(
    respx_mock: respx.MockRouter, good_site_html: str
) -> None:
    origin = "https://www.joesplumbingnj.com"
    _mock_simple_site(respx_mock, origin, good_site_html)

    exit_code = main([f"{origin}/", "--site", "--max-pages", "2", "--format", "json"])

    assert exit_code == 0


def test_network_failure_returns_exit_code_one(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("local_seo_audit.cli.audit", _boom)

    exit_code = main(["https://example.com/"])
    assert exit_code == 1
