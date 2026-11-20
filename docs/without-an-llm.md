# Using it without an LLM

The chart engine is plain Python and Node. You only need a spec JSON, which is a short list of line items from a filing.

```bash
python3 skills/sankey-financials/scripts/make.py my_spec.json my.cfg.json   # builds the chart and reconciles the numbers
node    skills/sankey-financials/scripts/test.js my.cfg.json -q             # layout checks, expect 0 errors
python3 skills/sankey-financials/scripts/build.py my.cfg.json my.html --standalone
open my.html
```

Spec fields for each flow type are in [`skills/sankey-financials/references/spec-format.md`](../skills/sankey-financials/references/spec-format.md). Copy a file from `skills/sankey-financials/examples/` as a starting point.

If `make.py` prints a `SPEC ERROR`, your line items do not add up to the reported totals. Fix the figures, not the checks.
