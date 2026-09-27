"""Integration tests: full audit() runs against mocked fixture sites."""

from __future__ import annotations

import httpx
import respx

from local_seo_audit.business import Business
from local_seo_audit.checks.https_redirect import HttpsRedirectCheck
from local_seo_audit.core import audit
from local_seo_audit.models import Status
from local_seo_audit.vitals import PSI_ENDPOINT


def _mock_common(
    respx_mock: respx.MockRouter,
    origin: str,
    html: str,
    *,
    robots: tuple[int, str] = (404, ""),
    sitemap: tuple[int, str] = (404, ""),
    favicon: tuple[int, str] = (404, ""),
    redirect_http_to_https: bool = True,
) -> None:
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get(f"{origin}/robots.txt").mock(
        return_value=httpx.Response(robots[0], text=robots[1])
    )
    respx_mock.get(f"{origin}/sitemap.xml").mock(
        return_value=httpx.Response(sitemap[0], text=sitemap[1])
    )
    respx_mock.get(f"{origin}/favicon.ico").mock(
        return_value=httpx.Response(favicon[0], text=favicon[1])
    )
    if origin.startswith("https://") and redirect_http_to_https:
        http_origin = "http://" + origin.removeprefix("https://")
        respx_mock.get(f"{http_origin}/").mock(
            return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
        )


def test_good_site_scores_high(respx_mock: respx.MockRouter, good_site_html: str) -> None:
    origin = "https://www.joesplumbingnj.com"
    _mock_common(
        respx_mock,
        origin,
        good_site_html,
        robots=(
            200,
            "User-agent: *\nAllow: /\nSitemap: https://www.joesplumbingnj.com/sitemap.xml",
        ),
        sitemap=(200, "<urlset></urlset>"),
    )

    report = audit(
        f"{origin}/",
        business=Business(
            name="Joe's Plumbing",
            phone="609-555-0100",
            city="Princeton",
            address="123 Main St, Princeton, NJ 08540",
        ),
    )

    assert report.score >= 90
    assert report.grade == "A"
    fails = [r for r in report.results if r.status is Status.FAIL]
    assert fails == []


def test_bad_site_scores_low(respx_mock: respx.MockRouter, bad_site_html: str) -> None:
    origin = "http://badsite.example"
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=bad_site_html))
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit(f"{origin}/", business=Business(name="Bad Co", phone="555-555-5555"))

    assert report.score < 40
    assert report.grade == "F"
    https_result = next(r for r in report.results if r.id == HttpsRedirectCheck.id)
    assert https_result.status is Status.FAIL


def test_partial_site_scores_middling(respx_mock: respx.MockRouter, partial_site_html: str) -> None:
    origin = "https://partial.example"
    _mock_common(
        respx_mock,
        origin,
        partial_site_html,
        robots=(404, ""),
        sitemap=(200, "<urlset></urlset>"),
    )

    report = audit(
        f"{origin}/",
        business=Business(
            name="Bright Smile Dental", phone="609-555-0199", city="Trenton", address="45 Elm St"
        ),
    )

    assert 30 < report.score < 90
    assert report.grade in ("B", "C", "D", "F")


def test_bare_host_defaults_to_https(respx_mock: respx.MockRouter) -> None:
    html = "<html></html>"
    respx_mock.get("https://example.com/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://example.com/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://example.com/"})
    )
    respx_mock.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://example.com/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get("https://example.com/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit("example.com")

    assert report.url == "https://example.com"
    assert report.final_url in ("https://example.com", "https://example.com/")


def test_unreachable_site_skips_content_checks(respx_mock: respx.MockRouter) -> None:
    error = httpx.ConnectError("no route")
    for path in ("", "robots.txt", "sitemap.xml", "favicon.ico"):
        respx_mock.get(f"https://down.example/{path}").mock(side_effect=error)
    respx_mock.get("http://down.example/").mock(side_effect=error)

    report = audit("https://down.example/")

    https_result = next(r for r in report.results if r.id == HttpsRedirectCheck.id)
    assert https_result.status is Status.FAIL
    title_result = next(r for r in report.results if r.id == "title")
    assert title_result.status is Status.SKIP


def test_crawl_finds_broken_internal_link(respx_mock: respx.MockRouter) -> None:
    html = """
    <html><body>
      <a href="/about">About</a>
      <a href="/missing">Missing</a>
      <a href="https://other.example/">External</a>
      <a href="mailto:hi@example.com">Email</a>
    </body></html>
    """
    origin = "https://crawlsite.example"
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://crawlsite.example/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/about").mock(return_value=httpx.Response(200, text="ok"))
    respx_mock.get(f"{origin}/missing").mock(return_value=httpx.Response(404))

    report = audit(f"{origin}/", crawl=5)

    crawl_result = next(r for r in report.results if r.id == "crawl_broken_links")
    assert crawl_result.status is Status.WARN
    assert "missing" in crawl_result.evidence


def test_crawl_not_requested_is_skipped(respx_mock: respx.MockRouter) -> None:
    html = "<html></html>"
    respx_mock.get("https://nocrawl.example/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://nocrawl.example/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://nocrawl.example/"})
    )
    respx_mock.get("https://nocrawl.example/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://nocrawl.example/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get("https://nocrawl.example/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit("https://nocrawl.example/")

    crawl_result = next(r for r in report.results if r.id == "crawl_broken_links")
    assert crawl_result.status is Status.SKIP


def test_vitals_defaults_to_none(respx_mock: respx.MockRouter) -> None:
    html = "<html></html>"
    respx_mock.get("https://novitals.example/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://novitals.example/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://novitals.example/"})
    )
    respx_mock.get("https://novitals.example/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://novitals.example/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get("https://novitals.example/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit("https://novitals.example/")

    assert report.vitals is None


def test_vitals_true_fetches_core_web_vitals(respx_mock: respx.MockRouter) -> None:
    html = "<html></html>"
    origin = "https://vitalssite.example"
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get(f"http://{origin.removeprefix('https://')}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "mobile"}).mock(
        return_value=httpx.Response(200, json={"id": origin})
    )
    respx_mock.get(PSI_ENDPOINT, params={"strategy": "desktop"}).mock(
        return_value=httpx.Response(200, json={"id": origin})
    )

    report = audit(f"{origin}/", vitals=True)

    assert report.vitals is not None
    assert report.vitals.mobile is not None
    assert report.vitals.mobile.error is not None  # fixture has no usable field/lab data


def test_site_defaults_to_none(respx_mock: respx.MockRouter) -> None:
    html = "<html></html>"
    respx_mock.get("https://nosite.example/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://nosite.example/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://nosite.example/"})
    )
    respx_mock.get("https://nosite.example/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://nosite.example/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get("https://nosite.example/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit("https://nosite.example/")

    assert report.site_crawl is None


def test_site_true_runs_a_full_crawl(respx_mock: respx.MockRouter) -> None:
    origin = "https://fullsite.example"
    html = '<html><body><a href="/about">About</a></body></html>'
    about_html = "<html><body><h1>About</h1></body></html>"
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get(f"http://{origin.removeprefix('https://')}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/about").mock(return_value=httpx.Response(200, text=about_html))

    report = audit(f"{origin}/", site=True, max_pages=5)

    assert report.site_crawl is not None
    assert report.site_crawl.pages_crawled == 2
    assert report.site_crawl.max_pages == 5
    # A --site crawl automatically feeds the content-gap analysis.
    assert report.content_plan is not None


def test_content_plan_defaults_to_none_without_site_or_services(
    respx_mock: respx.MockRouter,
) -> None:
    html = "<html></html>"
    respx_mock.get("https://noplan.example/").mock(return_value=httpx.Response(200, text=html))
    respx_mock.get("http://noplan.example/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://noplan.example/"})
    )
    respx_mock.get("https://noplan.example/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get("https://noplan.example/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get("https://noplan.example/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit("https://noplan.example/")

    assert report.content_plan is None


def test_services_flag_runs_a_homepage_only_content_plan_without_site(
    respx_mock: respx.MockRouter, good_site_html: str
) -> None:
    origin = "https://serviceflag.example"
    respx_mock.get(f"{origin}/").mock(return_value=httpx.Response(200, text=good_site_html))
    respx_mock.get(f"http://{origin.removeprefix('https://')}/").mock(
        return_value=httpx.Response(301, headers={"Location": f"{origin}/"})
    )
    respx_mock.get(f"{origin}/robots.txt").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/sitemap.xml").mock(return_value=httpx.Response(404))
    respx_mock.get(f"{origin}/favicon.ico").mock(return_value=httpx.Response(404))

    report = audit(f"{origin}/", services=["drain cleaning"], areas=["Princeton"])

    assert report.site_crawl is None
    assert report.content_plan is not None
    assert report.content_plan.services[0].query == "drain cleaning"
    assert not report.content_plan.inferred_services
