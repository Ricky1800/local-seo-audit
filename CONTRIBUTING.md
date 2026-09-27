# Contributing

Thanks for considering a contribution to `local-seo-audit`! This is a small,
focused tool, so contributions of any size are welcome — from fixing a typo
in a fix message to adding a whole new check.

## Setup

```bash
git clone https://github.com/Ricky1800/local-seo-audit
cd local-seo-audit
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -e ".[dev,speedups]"
```

## Before you open a PR

Run the full quality gate locally — it's exactly what CI runs:

```bash
ruff check .
ruff format --check .
mypy --strict src
pytest
```

All four must pass. `pytest` runs with a coverage gate (`--cov-fail-under=85`
in `pyproject.toml`); please add tests for any new code path.

## Project layout

```
src/local_seo_audit/
  business.py       Business (NAP) dataclass
  models.py         CheckResult / Report / scoring
  fetcher.py         httpx wrapper (never raises; errors become a FetchResult)
  core.py           orchestrates fetch -> parse -> run every check -> Report
  checks/           one file per check, all implementing checks.base.Check
  render/           text (rich) / markdown / html / json renderers
  cli.py            argparse entry point
tests/
  fixtures/         good_site / bad_site / partial_site HTML used by tests
  checks/           one test file per check
```

No test ever makes a real network request — `respx`/`httpx.MockTransport`
intercept every `httpx` call.

## Adding a new check

1. Create `src/local_seo_audit/checks/your_check.py` implementing
   `local_seo_audit.checks.base.Check`:

   ```python
   from local_seo_audit.checks.base import AuditContext, Check
   from local_seo_audit.models import CheckResult, Severity, Status


   class YourCheck(Check):
       id = "your_check"
       title = "Short human-readable name"
       weight = 5  # relative importance for scoring
       severity = Severity.MEDIUM

       def run(self, ctx: AuditContext) -> CheckResult:
           if not ctx.primary.ok:
               return self.skip("Skipped: homepage could not be fetched.")
           # ... inspect ctx.soup / ctx.business / ctx.page_text ...
           return self.make(Status.PASS, "what you observed", "how to fix it if it fails")
   ```

2. Register an instance of it in `src/local_seo_audit/checks/__init__.py`
   (`ALL_CHECKS` list and the module's `__all__`).
3. Add `tests/checks/test_your_check.py` covering at least one pass, one
   fail, and the "unreachable page -> skip" case. Use the `make_ctx` /
   `make_fetch_result` fixtures from `tests/conftest.py` — no network needed.
4. If the check needs a new field on `AuditContext` or a new outbound
   request, wire it up in `core.py` and add it to the shared fixtures in
   `tests/fixtures/`.

## Style

- Every evidence/fix string should be understandable by a non-technical
  business owner — avoid jargon, explain *why* something matters.
- Keep checks independent: a check must not depend on another check's
  result.
- Type everything; `mypy --strict` has zero tolerance for untyped code in
  `src/`.

## Reporting bugs / requesting features

Please use the issue templates under `.github/ISSUE_TEMPLATE/`.
