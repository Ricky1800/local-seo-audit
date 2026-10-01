from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from local_seo_audit import __version__
from local_seo_audit.cli import _parse_csv_list, main


def test_parse_csv_list() -> None:
    assert _parse_csv_list(None) is None
    assert _parse_csv_list("") is None
    assert _parse_csv_list(" , , ") is None
    assert _parse_csv_list("drain cleaning, water heater ,") == ["drain cleaning", "water heater"]


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


def test_compare_flag_adds_competitors_to_the_report(
    respx_mock: respx.MockRouter, good_site_html: str, bad_site_html: str
) -> None:
    origin = "https://www.joesplumbingnj.com"
    _mock_simple_site(respx_mock, origin, good_site_html)

    competitor_origin = "http://competitor.example"
    respx_mock.get(f"{competitor_origin}/").mock(
        return_value=httpx.Response(200, text=bad_site_html)
    )
    respx_mock.get(f"{competitor_origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{competitor_origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{competitor_origin}/favicon.ico").mock(return_value=httpx.Response(404))

    exit_code = main([f"{origin}/", "--compare", f"{competitor_origin}/", "--format", "json"])

    assert exit_code == 0


def test_compare_flag_rejects_too_many_urls(
    respx_mock: respx.MockRouter, good_site_html: str
) -> None:
    origin = "https://www.joesplumbingnj.com"
    _mock_simple_site(respx_mock, origin, good_site_html)

    exit_code = main(
        [
            f"{origin}/",
            "--compare",
            "https://c1.example/",
            "--compare",
            "https://c2.example/",
            "--compare",
            "https://c3.example/",
            "--compare",
            "https://c4.example/",
        ]
    )

    assert exit_code == 2


def test_services_and_areas_flags_are_parsed(
    respx_mock: respx.MockRouter, good_site_html: str
) -> None:
    origin = "https://www.joesplumbingnj.com"
    _mock_simple_site(respx_mock, origin, good_site_html)

    exit_code = main(
        [
            f"{origin}/",
            "--services",
            "drain cleaning, water heater",
            "--areas",
            "Princeton,Plainsboro",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0


def test_network_failure_returns_exit_code_one(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr("local_seo_audit.cli.audit", _boom)

    exit_code = main(["https://example.com/"])
    assert exit_code == 1


def test_batch_mode_success(
    respx_mock: respx.MockRouter, tmp_path: Path, good_site_html: str
) -> None:
    _mock_simple_site(respx_mock, "https://www.site1.com", good_site_html)
    _mock_simple_site(respx_mock, "https://www.site2.com", good_site_html)

    csv_file = tmp_path / "leads.csv"
    csv_file.write_text(
        "url,name,phone,city,address\n"
        "https://www.site1.com,Site One,609-555-0101,Princeton,123 Main St\n"
        "https://www.site2.com,Site Two,609-555-0102,Plainsboro,456 High St\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "reports"

    exit_code = main(
        [
            "--batch",
            str(csv_file),
            "--format",
            "html",
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "site1-com.html").exists()
    assert (out_dir / "site2-com.html").exists()
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "summary.csv").exists()

    summary_json = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary_json) == 2
    assert summary_json[0]["url"] == "https://www.site1.com"
    assert summary_json[0]["name"] == "Site One"
    assert "score" in summary_json[0]
    assert "grade" in summary_json[0]


def test_batch_mode_file_not_found(tmp_path: Path) -> None:
    exit_code = main(["--batch", str(tmp_path / "nonexistent.csv")])
    assert exit_code == 1


def test_batch_mode_empty_csv(tmp_path: Path) -> None:
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    exit_code = main(["--batch", str(empty_csv)])
    assert exit_code == 1
