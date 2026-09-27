"""JSON output for piping into other tools/dashboards."""

from __future__ import annotations

import json
from typing import Any

from local_seo_audit.crawler import CrawledPage, SiteCrawlReport
from local_seo_audit.models import Report
from local_seo_audit.vitals import LabData, Metric, StrategyResult, VitalsResult


def _metric_to_dict(metric: Metric | None) -> dict[str, Any] | None:
    if metric is None:
        return None
    return {
        "name": metric.name,
        "value": metric.value,
        "unit": metric.unit,
        "rating": metric.rating,
    }


def _lab_to_dict(lab: LabData | None) -> dict[str, Any] | None:
    if lab is None:
        return None
    return {
        "performance_score": lab.performance_score,
        "lcp": _metric_to_dict(lab.lcp),
        "tbt": _metric_to_dict(lab.tbt),
        "cls": _metric_to_dict(lab.cls),
        "opportunities": lab.opportunities,
    }


def _strategy_to_dict(result: StrategyResult) -> dict[str, Any]:
    field_data = result.field_data
    return {
        "strategy": result.strategy,
        "error": result.error,
        "field_data": (
            {
                "lcp": _metric_to_dict(field_data.lcp),
                "inp": _metric_to_dict(field_data.inp),
                "cls": _metric_to_dict(field_data.cls),
                "overall_category": field_data.overall_category,
            }
            if field_data is not None
            else None
        ),
        "lab_data": _lab_to_dict(result.lab_data),
    }


def _vitals_to_dict(vitals: VitalsResult | None) -> dict[str, Any] | None:
    if vitals is None:
        return None
    return {
        "mobile": _strategy_to_dict(vitals.mobile) if vitals.mobile is not None else None,
        "desktop": _strategy_to_dict(vitals.desktop) if vitals.desktop is not None else None,
    }


def _page_to_dict(page: CrawledPage) -> dict[str, Any]:
    return {
        "url": page.url,
        "status_code": page.status_code,
        "ok": page.ok,
        "error": page.error,
        "redirected": page.redirected,
        "history_urls": list(page.history_urls),
        "title": page.title,
        "meta_description": page.meta_description,
        "h1_count": page.h1_count,
        "word_count": page.word_count,
        "canonical": page.canonical,
        "noindex": page.noindex,
        "depth": page.depth,
        "in_sitemap": page.in_sitemap,
        "has_tel_link": page.has_tel_link,
        "has_json_ld": page.has_json_ld,
    }


def _site_crawl_to_dict(crawl: SiteCrawlReport | None) -> dict[str, Any] | None:
    if crawl is None:
        return None
    return {
        "start_url": crawl.start_url,
        "max_pages": crawl.max_pages,
        "pages_crawled": crawl.pages_crawled,
        "sitemap_url_count": len(crawl.sitemap_urls),
        "robots_disallowed": list(crawl.robots_disallowed),
        "pages": [_page_to_dict(p) for p in sorted(crawl.pages, key=lambda p: p.url)],
        "issues": {
            "duplicate_titles": [
                {"value": t, "urls": list(urls)} for t, urls in crawl.duplicate_titles
            ],
            "duplicate_descriptions": [
                {"value": d, "urls": list(urls)} for d, urls in crawl.duplicate_descriptions
            ],
            "missing_h1": list(crawl.missing_h1),
            "duplicate_h1": list(crawl.duplicate_h1_pages),
            "heading_order_issues": list(crawl.heading_order_issues),
            "thin_content": [{"url": u, "word_count": n} for u, n in crawl.thin_content],
            "canonical_issues": list(crawl.canonical_issues),
            "redirect_chains": list(crawl.redirect_chains),
            "error_pages": [{"url": u, "status_code": s} for u, s in crawl.error_pages],
            "orphan_pages": list(crawl.orphan_pages),
            "deep_pages": [{"url": u, "depth": d} for u, d in crawl.deep_pages],
            "missing_from_sitemap": list(crawl.missing_from_sitemap),
            "noindex_pages": list(crawl.noindex_pages),
        },
    }


def report_to_dict(report: Report) -> dict[str, Any]:
    """A plain, JSON-serializable representation of ``report``."""
    return {
        "url": report.url,
        "final_url": report.final_url,
        "business": {
            "name": report.business.name,
            "phone": report.business.phone,
            "city": report.business.city,
            "address": report.business.address,
        },
        "generated_at": report.generated_at.isoformat(),
        "tool_version": report.tool_version,
        "score": report.score,
        "grade": report.grade,
        "counts": {status.value: count for status, count in report.counts().items()},
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "weight": r.weight,
                "severity": r.severity.value,
                "status": r.status.value,
                "evidence": r.evidence,
                "fix": r.fix,
            }
            for r in report.sorted_results
        ],
        "vitals": _vitals_to_dict(report.vitals),
        "site_crawl": _site_crawl_to_dict(report.site_crawl),
    }


def render_json(report: Report, *, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent) + "\n"
