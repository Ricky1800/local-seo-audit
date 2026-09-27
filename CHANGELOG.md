# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-27

### Added

- **Core Web Vitals (`--vitals`)**: mobile + desktop Core Web Vitals from
  Google's free PageSpeed Insights v5 API. Reports field data (CrUX LCP,
  INP, CLS rated against Google's published thresholds) when available,
  plus Lighthouse lab data (performance score, LCP, TBT, CLS) and the top
  load-time opportunities. Works keyless; an optional `PSI_API_KEY`
  environment variable raises the rate limit. Timeouts, quota errors, and
  missing/malformed data are handled gracefully (never crash the audit).
- **Full-site crawl (`--site` / `--max-pages N`, default 50)**: discovers
  pages from `sitemap.xml` (including sitemap indexes) plus internal
  links, breadth-first, same host only, respecting `robots.txt`, with a
  concurrency cap and optional delay. New site-level checks: duplicate
  titles/meta descriptions, missing/duplicate H1, heading-order problems,
  thin content, canonical mistakes, redirect chains, 4xx/5xx pages, orphan
  pages, pages deeper than 3 clicks, and pages missing from the sitemap.
- **Competitor compare (`--compare URL`, repeatable up to 3 times)**:
  audits each competitor with the same checks and renders a side-by-side
  matrix (score, per-check status, page weight, JSON-LD schema types,
  vitals if enabled) plus a "they have it, you don't" gap list ranked by
  impact.
- **Local content gaps (`--services LIST` / `--areas LIST`)**: detects
  whether each service and city/service-area has a dedicated landing page
  (inferred from nav/headings when `--services` is omitted), checks NAP
  consistency, click-to-call coverage, Review/AggregateRating and FAQPage
  schema, a Google Business Profile link, and an embedded map on the
  contact page - across every crawled page - and produces a prioritized
  "content to create" plan.
- A completely redesigned `--format html` report: a token-based design
  system, an inline SVG score gauge, an executive summary with the
  top critical/high findings, severity-colored findings, light + dark
  (`prefers-color-scheme`) themes, and print styles - still zero external
  assets.
- New `local_seo_audit.structured_data` module (shared JSON-LD parsing,
  recursing into nested properties like `aggregateRating`) backing both
  the compare and content-gap features.

[0.2.0]: https://github.com/Ricky1800/local-seo-audit/releases/tag/v0.2.0

## [0.1.0] - 2026-09-26

### Added

- Initial release: `local-seo-audit` CLI and `local_seo_audit` library.
- Fetcher built on `httpx` (polite User-Agent, bounded timeouts/redirects,
  never raises — network errors become part of the result).
- 16 pluggable checks covering HTTPS/redirects, title, meta description,
  H1 count, mobile viewport, LocalBusiness JSON-LD (with NAP matching),
  visible NAP text, click-to-call links, Google Maps links/embeds,
  robots.txt/sitemap.xml, canonical tags, image alt-text coverage, page
  weight, Open Graph tags, favicon, and an opt-in same-host internal-link
  crawl (`--crawl N`) for broken links.
- Weighted 0-100 scoring with A-F letter grades.
- Four renderers: colored terminal text (`rich`), Markdown, standalone
  printable HTML, and JSON.
- CLI (`local-seo-audit URL [options]`) and library API (`audit()`).
- Test suite (pytest, `respx`) with local HTML fixtures and >85% coverage;
  no test makes a real network request.
- CI (GitHub Actions): ruff, mypy --strict, pytest across Python 3.10-3.13.

[0.1.0]: https://github.com/Ricky1800/local-seo-audit/releases/tag/v0.1.0
