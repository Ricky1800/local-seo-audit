"""Command-line entry point: `local-seo-audit https://example.com ...`."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Sequence
from pathlib import Path

from local_seo_audit import __version__
from local_seo_audit.business import Business
from local_seo_audit.compare import MAX_COMPETITORS, compare_competitors
from local_seo_audit.core import audit
from local_seo_audit.crawler import DEFAULT_MAX_PAGES
from local_seo_audit.render import Format, render


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-seo-audit",
        description=(
            "Audit a local business website for local-SEO and conversion basics, and print a "
            "prioritized fix list a non-technical owner can act on."
        ),
    )
    parser.add_argument("url", help="Website URL to audit, e.g. https://example.com")
    parser.add_argument("--name", default=None, metavar="NAME", help="Business name")
    parser.add_argument("--phone", default=None, metavar="PHONE", help="Business phone number")
    parser.add_argument("--city", default=None, metavar="CITY", help="City the business serves")
    parser.add_argument("--address", default=None, metavar="ADDRESS", help="Full street address")
    parser.add_argument(
        "--format",
        choices=("text", "md", "html", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Write the report to this file instead of stdout",
    )
    parser.add_argument(
        "--crawl",
        type=int,
        default=0,
        metavar="N",
        help="Also crawl up to N same-host internal links, checking for broken links (max 50)",
    )
    parser.add_argument(
        "--vitals",
        action="store_true",
        help=(
            "Also fetch Core Web Vitals (mobile + desktop) from Google PageSpeed Insights. "
            "Off by default: slow, and calls a third-party API. Uses PSI_API_KEY if set."
        ),
    )
    parser.add_argument(
        "--site",
        action="store_true",
        help="Crawl the whole site (same host, respecting robots.txt) for site-level SEO issues.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        metavar="N",
        help=f"With --site, stop after visiting N pages (default {DEFAULT_MAX_PAGES}).",
    )
    parser.add_argument(
        "--compare",
        action="append",
        default=None,
        metavar="URL",
        dest="compare",
        help=(
            "Audit a competitor URL and compare it side-by-side with the same checks. "
            f"Repeatable, up to {MAX_COMPETITORS} times."
        ),
    )
    parser.add_argument("--version", action="version", version=f"local-seo-audit {__version__}")
    return parser


def _ensure_utf8_stdio() -> None:
    """Never let an emoji or special character crash the CLI on a legacy Windows console.

    Some Windows terminals default stdout/stderr to a non-UTF-8 codepage (e.g. cp1252),
    which raises UnicodeEncodeError on the checkmarks/emoji used in a couple of renderers.
    Reconfiguring to UTF-8 with a replace fallback keeps output readable everywhere.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    business = Business(name=args.name, phone=args.phone, city=args.city, address=args.address)

    try:
        report = audit(
            args.url,
            business=business,
            crawl=max(args.crawl, 0),
            vitals=args.vitals,
            site=args.site,
            max_pages=args.max_pages,
        )
    except Exception as exc:  # pragma: no cover - audit() itself does not raise in practice
        print(f"local-seo-audit: error auditing {args.url}: {exc}", file=sys.stderr)
        return 1

    if args.compare:
        try:
            comparison = compare_competitors(
                report, args.compare, business=business, vitals=args.vitals
            )
        except ValueError as exc:
            print(f"local-seo-audit: {exc}", file=sys.stderr)
            return 2
        report = dataclasses.replace(report, competitors=comparison)

    fmt: Format = args.format
    color = args.out is None and fmt == "text"
    output = render(report, fmt, color=color)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Report written to {args.out} (score: {report.score}/100, grade {report.grade}).")
    else:
        sys.stdout.write(output if output.endswith("\n") else output + "\n")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
