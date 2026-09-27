# Roadmap issues

Well-scoped, unimplemented ideas for `local-seo-audit`. Each is written so
it could be copy-pasted directly into a new GitHub issue. Nothing below is
implemented — see [CHANGELOG.md](CHANGELOG.md) for what actually ships in
v0.1.0.

---

## 1. Fuzzy, token-based address matching in the NAP checks

**Labels:** `good first issue`, `enhancement`

**Body:**

`checks/nap_visible.py` and `checks/json_ld.py` currently compare the
provided `--address` to the page/JSON-LD address with a plain case-insensitive
substring check (`_normalize_for_match` in `json_ld.py`). This produces
false negatives for trivial differences like `"St"` vs `"Street"`, `"Suite 4"`
vs `"Ste 4"`, or a different field order.

**Acceptance criteria:**
- Extract the normalization/matching logic into a shared helper in `utils.py`.
- Tokenize both strings, expand common abbreviations (`st`/`street`, `ave`/
  `avenue`, `rd`/`road`, `ste`/`suite`, `blvd`/`boulevard`), and match if the
  token sets overlap above a documented threshold.
- Add unit tests covering at least: abbreviation differences, extra unit/
  suite info, and a genuinely different address (must NOT match).
- Existing tests in `tests/checks/test_nap_visible.py` and
  `tests/checks/test_json_ld.py` continue to pass.

---

## 2. `--fail-under SCORE` flag for CI usage

**Labels:** `good first issue`, `enhancement`, `cli`

**Body:**

Right now `local-seo-audit` always exits 0 on a successful audit, regardless
of score. A business that wants to gate their own CI/CD pipeline on not
regressing their local-SEO score (e.g. after a redesign) has no way to do
that.

**Acceptance criteria:**
- Add `--fail-under SCORE` (float, 0-100) to the CLI.
- When the resulting `report.score < SCORE`, `main()` returns exit code 3
  instead of 0 (report is still printed/written normally).
- Document the new flag in `README.md`.
- Add CLI tests for: score above threshold (exit 0), below threshold
  (exit 3), and the flag being absent (unchanged behavior).

---

## 3. Batch mode: audit many businesses from a CSV

**Labels:** `help wanted`, `enhancement`

**Body:**

Agencies auditing many local-business leads at once currently have to script
around the library themselves. A built-in batch mode would let someone run
`local-seo-audit --batch leads.csv --format html --out-dir reports/` and get
one report per row plus a combined summary CSV/JSON (url, score, grade).

**Acceptance criteria:**
- New `--batch PATH` flag taking a CSV with columns `url,name,phone,city,address`
  (name/phone/city/address optional).
- New `--out-dir PATH` flag; with `--batch`, one report file per row is
  written there, named from a slugified URL.
- A `summary.json` (or `.csv`) is written to `--out-dir` with one row per
  business: url, score, grade, counts.
- Respect the existing `--crawl` flag for every row.
- Document a worked example in `README.md`.
- Tests cover: a 2-3 row CSV against mocked sites, verifying both the
  per-site files and the summary file are produced correctly.

---

## 4. Optional "broken external links" check

**Labels:** `good first issue`, `enhancement`

**Body:**

The current `--crawl N` check only follows *same-host* links (by design, to
avoid hammering someone else's server). A lighter-weight, opt-in
`--check-external-links` flag could additionally issue a single `HEAD`
request (not a full crawl) to each *external* link found on the homepage,
to catch e.g. a dead link to a since-closed supplier or an old Facebook page.

**Acceptance criteria:**
- New `--check-external-links` flag (off by default; capped at, say, 20
  links to stay polite).
- New check `external_links` reusing the same `CrawlResult`/`CrawlLinkStatus`
  shape as the existing internal-link crawl.
- Uses `HEAD` requests with a short timeout, falling back to `GET` only if
  the server rejects `HEAD` (405).
- Tests mock a mix of healthy/broken/unresponsive external links.

---

## 5. PDF report format (`--format pdf`)

**Labels:** `help wanted`, `enhancement`

**Body:**

The HTML report is printable from a browser, but some users want a real PDF
they can attach to an email without a "print to PDF" step.

**Acceptance criteria:**
- New optional dependency group `pdf` (e.g. `weasyprint`) — must NOT become
  a hard dependency of the base package.
- `--format pdf` reuses `render_html()` and converts it to PDF bytes; writing
  to stdout is not supported for this format (binary), so `--format pdf`
  requires `--out PATH` and errors clearly if `--out` is omitted.
- Clear error message if the `pdf` extra isn't installed (don't crash with a
  raw `ImportError`).
- Document the extra install (`pip install "local-seo-audit[pdf]"`) in
  `README.md`.
- Tests skip gracefully (`pytest.importorskip`) if the optional dependency
  isn't installed in the test environment, but must pass in CI where it is.

---

## 6. More robust JSON-LD extraction (common SEO-plugin patterns)

**Labels:** `good first issue`, `enhancement`

**Body:**

`checks/json_ld.py` handles `@graph` arrays and top-level arrays, but real
sites built with WordPress SEO plugins (Yoast, RankMath) sometimes emit
multiple separate `<script type="application/ld+json">` blocks that
cross-reference each other via `@id`, or wrap the LocalBusiness node inside
an `Organization`'s `subOrganization`/`department`. Real-world testing
against a sample of small-business WordPress sites would likely surface
more shapes worth handling.

**Acceptance criteria:**
- Survey (manually, not committed to the repo) 10-15 real local-business
  sites; document which JSON-LD shapes `local-seo-audit` currently misses.
- Extend `_flatten_nodes`/`_is_local_business_type` in `json_ld.py` to cover
  at least `subOrganization`/`department`/`makesOffer` nesting.
- Add a fixture + test per new shape supported.

---

## 7. Core Web Vitals / real-page-speed check (optional, headless-browser based)

**Labels:** `help wanted`, `enhancement`, `larger effort`

**Body:**

`page_weight` is a cheap proxy for page speed (HTML size, script/style
counts) but doesn't measure actual load performance. A real Core Web Vitals
check (LCP/CLS/INP) would need a headless browser, which is a much heavier
dependency than the rest of this tool and would meaningfully slow down a
run — so it should be strictly optional.

**Acceptance criteria:**
- New optional dependency group `perf` (e.g. `playwright`).
- New check only registered/run when `--perf` is passed AND the extra is
  installed; otherwise it's skipped with a clear message pointing at the
  install command (never a hard failure).
- Reports LCP, CLS, and INP (or documents why a subset isn't feasible)
  with pass/warn/fail thresholds matching Google's published Core Web
  Vitals thresholds.
- CI does not need to install the `perf` extra; document that this check is
  untested in the default CI matrix and why.

---

## 8. Localized/non-English LocalBusiness support

**Labels:** `help wanted`, `enhancement`

**Body:**

Checks like `title` (city/name relevance) and `nap_visible` currently assume
English text and Latin-script phone/address formatting. A Spanish-language
local-business site (common in NJ) should be auditable just as well.

**Acceptance criteria:**
- Verify (and fix if needed) that `normalize_phone`/text-matching in
  `utils.py` work correctly on non-ASCII business names/addresses (e.g.
  Spanish `ñ`, accented characters) — these should not need special-casing
  if handled correctly, but should be explicitly tested.
- Add fixtures with a Spanish-language local-business page and confirm all
  16 checks behave sensibly against it.
- Document any known limitations in `README.md`.
