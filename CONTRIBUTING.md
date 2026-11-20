# Contributing

Thanks for helping. The whole project is small scripts plus a spec format, so changes are easy to test.

## Setup

Requirements: Python 3.9+ and Node 18+. Playwright (`pip install playwright && playwright install chromium`) is optional and enables the browser layout check.

## Before you open a PR

```bash
cd skills/sankey-financials
./run_tests.sh      # must print ALL PASSED
```

## Adding or changing a flow type or visual behavior

1. Add or update a spec in `skills/sankey-financials/examples/` that exercises the change.
2. Edit the scripts in `skills/sankey-financials/scripts/` (`make.py` builds structure and checks the numbers, `engine.js` draws, `test.js` checks layout).
3. Run `./run_tests.sh` until it prints ALL PASSED.
4. If you add an example, regenerate its gallery page and screenshots (see `docs/regenerate-gallery.md`).

## Data rules

- Use figures from primary sources (SEC filings, earnings releases, fund holdings pages) and put the source in the spec's `source` field.
- Never adjust numbers to force a reconcile. If `make.py` reports a SPEC ERROR, the spec is wrong.
- Label any derived line as "Derived" in its `note`.
