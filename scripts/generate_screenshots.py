#!/usr/bin/env python3
"""Regenerate the README/docs screenshots under ``docs/images/`` and
``docs/social-preview.png`` from real tool output (no hand-made mockups).

Renders a real HTML report (with competitor-compare and content-gaps
sections) and a real colored terminal transcript, using the fixtures
already checked into ``tests/fixtures``, then screenshots both.

Requires Playwright's Python bindings, which are a docs-tooling
convenience, not a runtime dependency of local-seo-audit itself:

    pip install playwright
    playwright install chromium

Usage:
    python scripts/generate_screenshots.py
"""

from __future__ import annotations

import html
import http.server
import re
import shutil
import socket
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
IMAGES_DIR = REPO_ROOT / "docs" / "images"

sys.path.insert(0, str(REPO_ROOT / "src"))

ANSI_COLORS = {31: "#f87171", 32: "#4ade80", 33: "#fbbf24"}
ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")


def ansi_to_html(text: str) -> str:
    out: list[str] = []
    open_span = False
    state = {"bold": False, "dim": False, "italic": False, "color": None}
    pos = 0
    for m in ANSI_RE.finditer(text):
        out.append(html.escape(text[pos : m.start()]))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c] or [0]
        for code in codes:
            if code == 0:
                if open_span:
                    out.append("</span>")
                    open_span = False
                state = {"bold": False, "dim": False, "italic": False, "color": None}
            elif code == 1:
                state["bold"] = True
            elif code == 2:
                state["dim"] = True
            elif code == 3:
                state["italic"] = True
            elif code in ANSI_COLORS:
                state["color"] = ANSI_COLORS[code]
        if open_span:
            out.append("</span>")
            open_span = False
        styles = []
        if state["color"]:
            styles.append(f"color:{state['color']}")
        if state["bold"]:
            styles.append("font-weight:700")
        if state["dim"]:
            styles.append("opacity:.6")
        if state["italic"]:
            styles.append("font-style:italic")
        if styles:
            out.append(f'<span style="{";".join(styles)}">')
            open_span = True
    out.append(html.escape(text[pos:]))
    if open_span:
        out.append("</span>")
    return "".join(out)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def serve_dir(directory: Path):
    port = _free_port()
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(directory), **kw
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        thread.join()


def build_report() -> tuple[str, str]:
    """Runs the real audit + compare + content-gaps pipeline. Returns (html, text)."""
    from local_seo_audit.business import Business
    from local_seo_audit.compare import compare_competitors
    from local_seo_audit.core import audit
    from local_seo_audit.render import render

    with tempfile.TemporaryDirectory() as tmp:
        competitor_dir = Path(tmp) / "competitor"
        competitor_dir.mkdir()
        shutil.copy(
            FIXTURES / "competitors" / "strong.html", competitor_dir / "index.html"
        )

        with serve_dir(FIXTURES / "good_site") as site_url, serve_dir(
            competitor_dir
        ) as competitor_url:
            business = Business(
                name="Joe's Plumbing",
                phone="(609) 555-0100",
                city="Princeton, NJ",
                address="123 Main St, Princeton, NJ 08540",
            )
            report = audit(
                site_url,
                business=business,
                services=["drain cleaning", "water heater installation", "sewer line repair"],
                areas=["Princeton", "Plainsboro", "Lawrenceville"],
            )
            comparison = compare_competitors(report, [competitor_url], business=business)
            import dataclasses

            report = dataclasses.replace(report, competitors=comparison)

            html_out = render(report, "html")
            text_out = render(report, "text", color=True)
            return html_out, text_out


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "This script needs Playwright's Python bindings:\n"
            "  pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 1

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    report_html, report_text = build_report()

    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.html"
        report_path.write_text(report_html, encoding="utf-8")

        terminal_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
        body {{ margin:0; background:#0d1117; padding:28px; font-family: -apple-system, Segoe UI, Arial, sans-serif; }}
        .window {{ max-width:980px; margin:0 auto; background:#0b0e14; border-radius:10px; overflow:hidden;
                   box-shadow:0 20px 60px rgba(0,0,0,.5); border:1px solid #1f2733; }}
        .titlebar {{ display:flex; align-items:center; gap:8px; padding:10px 14px; background:#161b22;
                     border-bottom:1px solid #1f2733; }}
        .dot {{ width:12px; height:12px; border-radius:50%; }}
        .r {{ background:#ff5f56; }} .y {{ background:#ffbd2e; }} .g {{ background:#27c93f; }}
        .titletext {{ margin-left:10px; color:#8b949e; font-size:13px; font-family: SFMono-Regular, Consolas, monospace; }}
        pre {{ margin:0; padding:22px 24px; color:#c9d1d9;
               font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
               font-size:14px; line-height:1.55; white-space:pre-wrap; word-break:break-word; }}
        </style></head><body><div class="window">
        <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
        <div class="titletext">local-seo-audit https://www.joesplumbingnj.com/</div></div>
        <pre>{ansi_to_html(report_text)}</pre></div></body></html>"""
        terminal_path = Path(tmp) / "terminal.html"
        terminal_path.write_text(terminal_html, encoding="utf-8")

        with sync_playwright() as p:
            browser = p.chromium.launch()

            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            page.goto(report_path.as_uri())
            page.wait_for_timeout(200)
            page.screenshot(path=str(IMAGES_DIR / "report-top.png"))
            section = page.query_selector(".report-section.content-gaps")
            if section:
                section.scroll_into_view_if_needed()
                page.wait_for_timeout(150)
                section.screenshot(path=str(IMAGES_DIR / "report-content-plan.png"))
            page.close()

            page = browser.new_page(viewport={"width": 1040, "height": 800})
            page.goto(terminal_path.as_uri())
            page.wait_for_timeout(150)
            page.query_selector(".window").screenshot(
                path=str(IMAGES_DIR / "terminal-output.png")
            )
            page.close()

            browser.close()

    for name in ("report-top.png", "report-content-plan.png", "terminal-output.png"):
        f = IMAGES_DIR / name
        print(f"{name}: {f.stat().st_size / 1024:.1f} KB")

    print("Done. Regenerate docs/social-preview.png separately if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
