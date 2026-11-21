---
name: sankey-financials
description: Interactive Sankey of where a company's or fund's money comes from and goes. Use for revenue breakdowns, income statement, cash flow, balance sheet, ETF holdings or segment flows.
---

# Sankey financials

Builds an interactive, left-to-right Sankey that answers "where did the money come from, and where
did it go?" Link width is proportional to dollars.

**Your job is the judgment; the scripts do everything else.** You find the right filing, choose
the flow type and transcribe line items into a small spec. `scripts/make.py` builds the chart
structure and checks that the numbers reconcile, `scripts/test.js` checks the layout, and
`scripts/build.py` produces the chart. Never hand-write chart code or node/link lists, and never
edit `scripts/` during a normal request.

## When this applies and the default

Use it for a revenue breakdown, a Sankey, an income-statement flow, or how a company or fund's
money moves. If the user names only a ticker, make the **income statement for the latest reported
quarter, GAAP**, with Product, Business and Geography tabs where the filing supports them.

| User says | `flow` |
|---|---|
| revenue breakdown, income statement, P&L, margins | `income` |
| cash flow, free cash flow, buybacks, where cash went | `cashflow` |
| balance sheet, assets, debt, what it owns or owes | `balance` |
| ETF or fund holdings, what's in QQQ | `holdings` |
| segment profit, which segment makes money | `segments` |

## Workflow

1. **Find the numbers** in primary sources: the latest earnings release, 10-Q or 10-K (sec.gov or
   investor relations), or the fund's holdings page. Get the same period a year earlier for every
   line (for a balance sheet, the comparison date the filing uses). Confirm which period is the
   latest before you start; fiscal calendars differ (Marvell's FY27 Q2 ends in Aug 2026).
2. **Write the spec** in a working folder, following `references/spec-format.md`
   (read it the first time in a session). Copy labels from the filing, shortened sensibly
   ("R&D", "SG&A"), with the long name in `full`. Keep signs as filed. Add `source`, `end` and
   `prior_end` (the switch label comes from these dates), and `currency` for non-USD filers.
   - Tabs: always name them **Product**, **Business**, **Geography**, whatever the filing calls
     them ("end market", "platform"). If the company reports a single segment, use
     `"Business":{"same":"Product","note":"<Company> reports a single business segment, so this view matches the product split."}`.
     Never invent a split.
   - Geography by ship-to or billing location gets a note saying so.
   - Group small or technical lines with `group` (working capital, debt, "Other") so a column has
     no more than about 8 boxes.
3. **Generate**: `python3 scripts/make.py spec.json chart.cfg.json`.
   A `SPEC ERROR` means the figures don't reconcile with the reported totals. Do not adjust numbers
   to force a match: go back to the filing and find the missing or mistyped line. If a line truly
   isn't published, you may back it out from reported totals; label it "Derived" in its `note`
   and tell the user.
4. **Test**: `node scripts/test.js chart.cfg.json -q` must report 0 errors. Read every WARN.
   A very large change usually means a wrong prior figure; confirm it against the filing.
   If Playwright is installed, also run `python3 scripts/browser_check.py chart.html shot` after
   step 5 and look at the screenshots.
5. **Build and deliver**:
   - **Claude Code**: `python3 scripts/build.py chart.cfg.json <TICKER>_<period>_<flow>.html --standalone`,
     then `open` the file so it appears in the browser. Clicking a box copies a question to the
     clipboard to paste back into the chat.
   - **claude.ai**: `python3 scripts/build.py chart.cfg.json widget.html`, then pass the file's
     contents to the inline widget tool. Clicking a box asks Claude about that line.
6. **Reply briefly**: two or three takeaways (growth, margin change, the biggest mover), any caveats
   (derived lines, single segment, ship-to geography, sector mapping), and what isn't shown.
   Don't restate the chart.

## What the chart does (fixed by the scripts)

- Profit or the "kept" stream runs along the top; costs and outflows branch downward to the right.
- Colors: sources blue, profit green, costs orange, losses red, neutral gray.
- Tabs for each view, a Y/Y switch (hidden when there's no comparison data), hover tracing with
  tooltips, and click-to-ask.
- "n/m" when the prior value was zero, negative or of the opposite kind.
- Flows under about 0.3% of the total are drawn at a 2px minimum, and their tooltip says so.
- Not supported (make.py refuses with a message): zero revenue,
  tax above pretax income, total operating loss in the
  segment view, short or negative fund weights.
- make.py checks the prior column as well as the current one, and needs the reported totals
  (`operating_income`, `net_income`, `total_assets`, segment `revenue`); a balance sheet also needs
  `end`/`prior_end` or `cmp`. A refusal names the line that doesn't add up. Use a different
  flow type or describe the numbers in text.

## Changing the skill itself

Only when the user asks to change how charts look or behave: edit `scripts/`, add or update a spec
in `examples/` that exercises the change, and run `./run_tests.sh` until it prints ALL PASSED.
