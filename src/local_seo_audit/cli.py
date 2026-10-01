"""Command-line entry point: `local-seo-audit https://example.com ...`."""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from local_seo_audit import __version__
from local_seo_audit.business import Business
from local_seo_audit.compare import MAX_COMPETITORS, compare_competitors
from local_seo_audit.core import audit
from local_seo_audit.crawler import DEFAULT_MAX_PAGES
from local_seo_audit.models import Status
from local_seo_audit.render import Format, render
from local_seo_audit.utils import slugify_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-seo-audit",
        description=(
            "Audit a local business website for local-SEO and conversion basics, and print a "
            "prioritized fix list a non-technical owner can act on."
        ),
    )
    parser.add_argument(
        "url", nargs="?", default=None, help="Website URL to audit, e.g. https://example.com"
    )
    parser.add_argument(
        "--batch",
        default=None,
        metavar="PATH",
        help="CSV file with columns url,name,phone,city,address to audit in batch",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        metavar="PATH",
        help="Directory to write batch reports and summary",
    )
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
    parser.add_argument(
        "--services",
        default=None,
        metavar="LIST",
        help=(
            "Comma-separated services to check for a dedicated page, e.g. "
            '"drain cleaning,water heater". Inferred from nav/headings if omitted.'
        ),
    )
    parser.add_argument(
        "--areas",
        default=None,
        metavar="LIST",
        help=(
            "Comma-separated city/service-area names to check for a dedicated page, "
            'e.g. "Princeton,Plainsboro".'
        ),
    )
    parser.add_argument("--version", action="version", version=f"local-seo-audit {__version__}")
    return parser


def _parse_csv_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item] or None


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


def run_batch(args: argparse.Namespace) -> int:
    batch_path = Path(args.batch)
    if not batch_path.is_file():
        print(f"local-seo-audit: batch file not found: {args.batch}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir) if args.out_dir else Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with batch_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print(f"local-seo-audit: empty CSV batch file: {args.batch}", file=sys.stderr)
                return 1
            raw_rows = list(reader)
    except Exception as exc:
        print(f"local-seo-audit: error reading CSV {args.batch}: {exc}", file=sys.stderr)
        return 1

    ext_map = {"text": "txt", "md": "md", "html": "html", "json": "json"}
    fmt: Format = args.format
    ext = ext_map.get(fmt, "txt")

    summaries: list[dict[str, object]] = []
    used_filenames: set[str] = set()

    for idx, raw_row in enumerate(raw_rows, start=1):
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}
        url = row.get("url")
        if not url:
            continue

        name = row.get("name") or None
        phone = row.get("phone") or None
        city = row.get("city") or None
        address = row.get("address") or None

        business = Business(name=name, phone=phone, city=city, address=address)

        try:
            report = audit(
                url,
                business=business,
                crawl=max(args.crawl, 0),
                vitals=args.vitals,
                site=args.site,
                max_pages=args.max_pages,
                services=_parse_csv_list(args.services),
                areas=_parse_csv_list(args.areas),
            )
        except Exception as exc:  # pragma: no cover
            print(f"local-seo-audit: error auditing {url}: {exc}", file=sys.stderr)
            continue

        base_slug = slugify_url(url)
        filename = f"{base_slug}.{ext}"
        counter = 2
        while filename in used_filenames:
            filename = f"{base_slug}-{counter}.{ext}"
            counter += 1
        used_filenames.add(filename)

        report_path = out_dir / filename
        output = render(report, fmt, color=False)
        report_path.write_text(output, encoding="utf-8")

        counts = report.counts()
        passed = counts[Status.PASS]
        warned = counts[Status.WARN]
        failed = counts[Status.FAIL]

        summary_row = {
            "url": report.url,
            "name": name or "",
            "score": report.score,
            "grade": report.grade,
            "passed": passed,
            "warnings": warned,
            "failures": failed,
            "report_file": filename,
        }
        summaries.append(summary_row)
        print(
            f"[{idx}/{len(raw_rows)}] Audited {report.url} -> score {report.score}/100 "
            f"({report.grade}) -> {filename}"
        )

    summary_json_path = out_dir / "summary.json"
    summary_json_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")

    summary_csv_path = out_dir / "summary.csv"
    with summary_csv_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "url",
            "name",
            "score",
            "grade",
            "passed",
            "warnings",
            "failures",
            "report_file",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in summaries:
            writer.writerow(s)

    print(f"\nBatch complete: {len(summaries)} audited. Reports and summary written to {out_dir}/")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.batch:
        return run_batch(args)

    if not args.url:
        parser.error("the following arguments are required: url (or --batch PATH)")

    business = Business(name=args.name, phone=args.phone, city=args.city, address=args.address)

    try:
        report = audit(
            args.url,
            business=business,
            crawl=max(args.crawl, 0),
            vitals=args.vitals,
            site=args.site,
            max_pages=args.max_pages,
            services=_parse_csv_list(args.services),
            areas=_parse_csv_list(args.areas),
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
