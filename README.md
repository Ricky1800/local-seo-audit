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
                 [--out PATH] [--crawl N] [--version]
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

Tests run entirely offline against local HTML fixtures
(`tests/fixtures/{good,bad,partial}_site`) using `respx`/`httpx.MockTransport`
— no real network access, ever, during the test suite.

## Roadmap

See [ROADMAP_ISSUES.md](ROADMAP_ISSUES.md) for well-scoped future issues
(new checks, output formats, and more), several tagged `good first issue`.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for how
to set up the project, the coding standards (ruff + mypy --strict + pytest),
and how to add a new check.

## License

[MIT](LICENSE) © 2026 Ricky1800
