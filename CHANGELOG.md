# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
