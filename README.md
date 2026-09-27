# local-seo-audit

A CLI and Python library that audits a local business's website for
**local-SEO and conversion basics**, and prints a prioritized, plain-English
fix list a non-technical owner can actually act on.

## The problem

Most local businesses (plumbers, dentists, restaurants, salons...) hire
someone to build them a website once, and then never touch it again. The
site quietly accumulates problems that cost them customers and search
ranking: no click-to-call link, a missing meta description, a phone number
that doesn't match what's in Google, no structured data telling Google it's
even a real local business. Generic SEO tools are built for e-commerce and
content sites and bury the handful of things that actually matter for a
five-page local-business site under a wall of jargon.

`local-seo-audit` runs ~16 targeted checks, scores the site 0-100, and
explains every issue in language an owner (not a developer) can understand
and hand to whoever manages their website.

## Install

```bash
pipx install local-seo-audit   # (once published to PyPI)
```

Until then (or if you prefer installing straight from source):

```bash
pipx install git+https://github.com/Ricky1800/local-seo-audit
```

Or, for local development:

```bash
git clone https://github.com/Ricky1800/local-seo-audit
cd local-seo-audit
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -e ".[dev,speedups]"
```

The `speedups` extra installs `lxml` for faster HTML parsing; the tool works
fine without it (it falls back to Python's built-in `html.parser`).

## Usage

```bash
local-seo-audit https://example.com \
  --name "Joe's Plumbing" \
  --phone "609-555-0100" \
  --city Princeton \
  --address "123 Main St, Princeton, NJ 08540" \
  --format text
```

```
local-seo-audit [-h] [--name NAME] [--phone PHONE] [--city CITY]
                 [--address ADDRESS] [--format {text,md,html,json}]
                 [--out PATH] [--crawl N] [--vitals] [--site]
                 [--max-pages N] [--compare URL] [--services LIST]
                 [--areas LIST] [--version]
                 url
```

- `--name` / `--phone` / `--city` / `--address` — the business's real NAP
  (Name, Address, Phone). Optional, but the more you give it, the more
  checks can actually verify (title relevance, JSON-LD NAP matching,
  on-page NAP visibility) instead of just noting something is present.
- `--format {text,md,html,json}` — output format (default `text`, colored
  terminal output via [`rich`](https://github.com/Textualize/rich)).
- `--out PATH` — write the report to a file instead of stdout. Use
  `--format html --out report.html` to generate a standalone, printable
  report you can hand directly to a business owner.
- `--crawl N` — also crawl up to `N` same-host internal links (capped at
  50) looking for broken (404/error) links.
- `--vitals` — also fetch Core Web Vitals (mobile + desktop) from Google's
  free PageSpeed Insights API. Off by default (slow, third-party network
  call). See [Core Web Vitals](#core-web-vitals---vitals) below.
- `--site` / `--max-pages N` — crawl the whole site (same host, breadth
  first, respecting `robots.txt`) for site-level SEO issues, instead of
  just the homepage. See [Full-site crawl](#full-site-crawl---site----max-pages-n).
- `--compare URL` — audit a competitor with the same checks and compare
  side by side. Repeatable, up to 3 times. See
  [Competitor compare](#competitor-compare---compare-url).
- `--services LIST` / `--areas LIST` — comma-separated service names and
  city/service-area names to check for a dedicated landing page. See
  [Local content gaps](#local-content-gaps---services----areas).

### Library usage

```python
from local_seo_audit import Business, audit
from local_seo_audit.render import render

report = audit(
    "https://example.com",
    business=Business(name="Joe's Plumbing", phone="609-555-0100", city="Princeton"),
    crawl=10,
)

print(report.score, report.grade)  # e.g. 82.5 "B"
for result in report.sorted_results:  # worst-first
    print(result.status.value, result.title, result.evidence)

print(render(report, "html"))  # or "text" / "md" / "json"
```

## Core Web Vitals (`--vitals`)

Fetches mobile + desktop Core Web Vitals from Google's free
[PageSpeed Insights v5 API](https://developers.google.com/speed/docs/insights/v5/get-started).
Off by default because it's slow and calls a third-party API. Reports:

- **Field data** (real-user Chrome UX Report data): LCP, INP, and CLS, each
  rated `good` / `needs-improvement` / `poor` against Google's published
  thresholds — only present once a URL has enough real Chrome traffic.
- **Lab data** (a single Lighthouse run): a 0–100 performance score, LCP,
  TBT, and CLS, plus the top load-time opportunities.

It works keyless with low rate limits. For a much higher quota, get a free
API key from the
[Google Cloud Console](https://console.cloud.google.com/apis/credentials)
(enable the "PageSpeed Insights API") and set it as an environment
variable:

```bash
export PSI_API_KEY="your-key-here"   # PowerShell: $env:PSI_API_KEY = "your-key-here"
local-seo-audit https://example.com --vitals
```

A timeout, quota error, or missing field data never crashes the audit —
it shows up as a per-strategy note instead. Sample output (`--format md`,
generated from `tests/fixtures/psi/mobile_good.json`):

```markdown
## Core Web Vitals

_Source: Google PageSpeed Insights._

### Mobile

- **Field data (real users):** LCP 2100ms 🟢 good, INP 150ms 🟢 good, CLS 0.05 🟢 good
- **Lab data (Lighthouse):** performance 94/100 — LCP 1900ms 🟢 good, TBT 80ms 🟢 good, CLS 0.03 🟢 good
- **Top opportunities:**
  - Eliminate render-blocking resources
  - Reduce unused CSS
```

## Full-site crawl (`--site` / `--max-pages N`)

Instead of auditing just the homepage, `--site` discovers and crawls the
whole site: pages come from `sitemap.xml` (following sitemap indexes) plus
internal links found on each page, breadth-first, same host only,
respecting `robots.txt`, capped at `--max-pages` (default 50, hard ceiling
500). It's polite (a concurrency cap and an optional per-request delay).

Beyond the per-page checks, it looks for problems only visible with the
whole site in view: duplicate titles/meta descriptions, missing or
duplicate H1s, heading-order problems, thin content, canonical mistakes
(pointing at another host or a broken page), redirect chains, 4xx/5xx
pages, orphan pages (in the sitemap but never internally linked), pages
more than 3 clicks deep, and crawled pages missing from the sitemap.

```bash
local-seo-audit https://example.com --site --max-pages 100 --format md
```

Sample summary (`--format md`, generated by crawling the
`tests/fixtures/site_crawl` fixture site):

```
Visited 9 page(s) (cap 50); 5 URL(s) in the sitemap; 22 site-level issue(s) found.
Duplicate titles: 1, missing H1: 2, orphan pages: 1, deep pages: 1
```

## Competitor compare (`--compare URL`)

Audits up to 3 competitor URLs with the exact same checks and builds a
side-by-side matrix (your status vs. each competitor's, per check) plus a
"they have it, you don't" gap list ranked by the weight of the check they
beat you on. Key metrics (page weight, JSON-LD schema types present, and
Core Web Vitals if `--vitals` is also passed) are shown per competitor.
Included in every renderer, with a full comparison table in HTML.

```bash
local-seo-audit https://example.com \
  --compare https://competitor-one.com \
  --compare https://competitor-two.com
```

Sample gaps (generated by comparing `tests/fixtures/bad_site` against
`tests/fixtures/competitors/strong.html`):

```
- HTTPS is enabled, and HTTP redirects to HTTPS (weight 12) - ahead: https://www.aceplumbingnj.com/
- LocalBusiness structured data (JSON-LD) (weight 12) - ahead: https://www.aceplumbingnj.com/
- Title tag is present, well-sized, and locally relevant (weight 8) - ahead: https://www.aceplumbingnj.com/
- Click-to-call (tel:) link (weight 8) - ahead: https://www.aceplumbingnj.com/
```

An unreachable competitor doesn't abort the comparison — `audit()` never
raises, so a dead competitor site just shows up with a very low score.

## Local content gaps (`--services` / `--areas`)

Checks whether the business has a dedicated landing page for each service
and each city/service-area it serves, given `--services "drain
cleaning,water heater"` and/or `--areas "Princeton,Plainsboro"`. When
`--services` is omitted, candidates are inferred from nav links and H2/H3
headings across the crawled pages (best-effort; pass `--services`
explicitly for accuracy). A missing service crossed with a missing area
produces a combined "create /service-area" suggestion, since that's what
local searchers actually click on.

Also checks, across every crawled page: NAP (phone) consistency, whether a
click-to-call (`tel:`) link is present on every page, Review/AggregateRating
and FAQPage schema, a Google Business Profile link, and an embedded map on
the contact page. Everything rolls up into a prioritized "content to
create" plan.

```bash
local-seo-audit https://example.com --site \
  --services "drain cleaning,water heater" --areas "Princeton"
```

Sample plan (generated from the `tests/fixtures/site_crawl` fixture site):

```
[HIGH] Create /drain-cleaning: dedicated drain cleaning page
  why: 'drain cleaning' has no dedicated landing page - it's likely buried
  in a generic services list, which ranks worse than a focused page for
  that specific search term.
[HIGH] Add a click-to-call link on every page
  why: 7 of 8 crawled page(s) have no tel: link - most local searches
  happen on a phone, and every page is a potential landing page.
[MEDIUM] Add Review/AggregateRating schema
  why: No page declares Review or AggregateRating structured data, so
  star ratings can't show up directly in Google search results even if
  real reviews exist.
```

`--services`/`--areas` also work without `--site` (a lighter, homepage-only
version of the same analysis).

## Sample report excerpt

Generated from the `tests/fixtures/partial_site` fixture (a deliberately
half-finished dentist site) via `--format md` — nothing below is invented:

```markdown
# Local SEO Audit — https://brightsmiledentalnj.com/

**Business:** Bright Smile Dental
**Generated:** 2026-09-26 23:04
**Score:** 62.5/100 — **Grade: D**

Pass: 6 · Warn: 6 · Fail: 3 · Skipped: 1

## Prioritized fix list

### ❌ Click-to-call (tel:) link `fail` · weight 8 · high

- **Evidence:** No tel: link found on the page.
- **Fix:** Wrap the phone number in a click-to-call link: <a href="tel:+16095550100">609-555-0100</a>.
  Most local-business searches happen on a phone; this turns the number into a one-tap call instead
  of forcing the visitor to dial manually.

### ❌ Images have descriptive alt text `fail` · weight 6 · medium

- **Evidence:** 1/3 images (33%) have non-empty alt text.
- **Fix:** Add descriptive alt text to every meaningful image. This helps screen-reader users and
  gives Google extra local-relevance context.

### ⚠️ LocalBusiness structured data (JSON-LD) `warn` · weight 12 · high

- **Evidence:** Found LocalBusiness JSON-LD (@type: Dentist). Missing fields: address, openingHours, geo.
  NAP comparison: name matches; phone matches.
- **Fix:** Add a <script type="application/ld+json"> block describing the business as a LocalBusiness,
  including name, address, telephone, openingHours, and geo coordinates.

### ✅ HTTPS is enabled, and HTTP redirects to HTTPS `pass` · weight 12 · critical

- **Evidence:** Final URL loads as https://brightsmiledentalnj.com/ (scheme: https). http:// correctly
  redirects to https://brightsmiledentalnj.com/.

...(13 more checks)
```

The `--format html` output is the same information rendered as a
standalone, printable page (inline CSS, no external requests) meant to be
emailed straight to the business owner.

## Checks

The 16 checks below always run against the homepage. `--vitals`, `--site`,
`--compare`, and `--services`/`--areas` add the additional analyses
documented above (Core Web Vitals, site-level SEO issues, competitor
comparison, and local content gaps) and are opt-in since they're slower
and/or need more network access.

| Check | Why it matters for a local business |
|---|---|
| **HTTPS + HTTP→HTTPS redirect** | Browsers flag non-HTTPS sites as "Not Secure," and Google ranks insecure sites lower. |
| **Title tag** (length, mentions city/service) | The headline shown in search results; local relevance is what wins "near me" searches. |
| **Meta description** | The snippet under the title in search results — the owner's one shot at a click. |
| **Exactly one H1** | Tells both visitors and search engines the page's main topic. |
| **Mobile viewport meta tag** | Most local searches happen on a phone; without it, pages render zoomed out. |
| **LocalBusiness JSON-LD** (name/address/phone/hours/geo, matched to the real NAP) | Lets Google show rich results (star ratings, hours, map pin) and confirms the site's NAP is machine-readable and correct. |
| **NAP visible in page text** (phone-format-normalized) | A human still has to be able to *read* a phone number to call it — structured data alone isn't enough. |
| **Click-to-call (`tel:`) link** | Turns a phone number into a one-tap call on mobile. |
| **Google Maps link/embed** | "How do I get there" is one of the first things a local visitor looks for. |
| **robots.txt + sitemap.xml** | How search engines are told what exists and what to crawl. |
| **Canonical tag** | Prevents Google from splitting ranking signals across URL variants of the same page. |
| **Image alt-text coverage** | Accessibility, plus extra local-relevance context Google can index. |
| **Page weight** (HTML size, script/style counts) | A bloated homepage loses impatient mobile visitors; page speed is a ranking factor. |
| **Open Graph tags** | Controls how the page looks when shared on Facebook/Instagram/iMessage. |
| **Favicon** | A small trust signal — its absence reads as unfinished or abandoned. |
| **Internal link crawl** (`--crawl N`, opt-in) | Capped, same-host crawl that flags broken (404/error) internal links. |

Every check is a small, independent class (`local_seo_audit.checks.base.Check`)
with an `id`, `title`, `weight`, `severity`, and a `run(ctx) -> CheckResult`
that returns a pass/warn/fail/skip status, the evidence observed on the
page, and a plain-English fix. Adding a new check means writing one class
and registering it in `local_seo_audit/checks/__init__.py` — nothing else
in the codebase has to change.

## Scoring

Each check contributes its `weight` to a running total: full weight for a
`pass`, half for a `warn`, zero for a `fail`. Checks that could not run
(e.g. no business info was given to compare NAP against) are marked `skip`
and excluded entirely, so an incomplete `--name/--phone/--city/--address`
input never unfairly drags the score down. The final score is
`100 * earned / possible`, mapped to a letter grade (A ≥ 90, B ≥ 80, C ≥ 70,
D ≥ 60, F below that).

## Development

```bash
pip install -e ".[dev,speedups]"
ruff check .
ruff format --check .
mypy --strict src
pytest   # runs with coverage; see pyproject.toml for the >=85% gate
```

Tests run entirely offline using `respx`/`httpx.MockTransport` against local
fixtures — no real network access, ever, during the test suite:

- `tests/fixtures/{good,bad,partial}_site` — single-page audit fixtures.
- `tests/fixtures/site_crawl` — a multi-page fixture site with a sitemap
  index, sub-sitemap, and `robots.txt` (with a disallowed path), used to
  test the full-site crawl and content-gap analysis.
- `tests/fixtures/competitors` — a second business's homepage, used to test
  `--compare`.
- `tests/fixtures/psi/*.json` — recorded PageSpeed Insights v5 API
  responses (good/poor scores, missing field data, a quota error), used to
  test `--vitals` without ever calling Google's real API.

## Roadmap

See [ROADMAP_ISSUES.md](ROADMAP_ISSUES.md) for well-scoped future issues
(new checks, output formats, and more), several tagged `good first issue`.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for how
to set up the project, the coding standards (ruff + mypy --strict + pytest),
and how to add a new check.

## Authors

- [@Ricky1800](https://github.com/Ricky1800)
- [@orbitwebsites-cloud](https://github.com/orbitwebsites-cloud) ([OrbitBoyzz](https://orbitboyzz.me))

## License

[MIT](LICENSE) © 2026 Ricky1800
